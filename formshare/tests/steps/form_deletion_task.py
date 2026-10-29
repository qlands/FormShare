"""Deleting a form in the background (owner, 2026-10-28):
processes/db/form_deletion.py, products/deletion and resume_form_deletion.

In a project of its own:
- a form in testing (form08_OK, Justtest_b): its ID must be typed, and the
  worker deletes it;
- a form with a repository (merge A), built here. A newer version, a task
  running on it, being blocked and a live repository with a foreign key into
  its own each refuse its deletion.
- Then its deletion runs here, in this process, and stops three times: a
  dump that mysqldump cut short, a mysqldump that fails, and the leftover of
  a form deleted before 2026-10-28, whose foreign key the drop refuses. Each
  time the form stays marked with the reason, and its repository whole. The
  first attempt has already revoked what an account held on the repository,
  but not a grant on a pattern that covers other schemas too.
- While it is marked, every address that names it answers 404, to the
  owner, its assistant, its partner and devices; the project's map draws
  none of its points; no list can start drawing from it; and the update API
  writes none of its rows.
- resume_form_deletion finishes it, with a version that shares the
  repository: the dump of each attempt in the renamed directory, the
  repository dropped, both forms gone, and the Celery plugins told of each,
  one that fails included.
- In a classic case project (2021), no follow-up can be added while the
  form that creates the cases is being deleted.

Every deletion made to stop here runs with the suite's settings, which send
no email: resume_form_deletion reads development.ini, so it only runs those
that succeed or stop before emailing anyone. The grants are revoked before
then, so a resume has none to revoke, nor a failure to email.

The refusals of the longitudinal study are in case_journey.py, where the
cases and their follow-ups are.
"""

import contextlib
import glob
import gzip
import io
import os
import re
import shutil
import tempfile
import time
import uuid
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from .form_deletion import confirmed, delete_form, deletion_state
from .in_process import add_task, build_in_process, finish_task, form_row

PROJECT = "form_deletion"
TESTING_FORM = "Justtest_b"
PARENT = "tormenta20201105"
VERSION = "tormenta20201117"


def _execute(config, sql, *params):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        result = engine.execute(sql, params) if params else engine.execute(sql)
        return result.fetchall() if result.returns_rows else result.rowcount
    finally:
        engine.dispose()


def _repository_exists(config, schema):
    rows = _execute(
        config,
        "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
        schema,
    )
    return rows[0][0] == 1


def _refused(test_object, login, form_id, data):
    """A deletion refused: the page it goes back to, which shows why. A page
    shows the first error queued and drops the rest, so each is read."""
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, PROJECT, form_id),
        data,
        status=302,
    )
    assert "FS_error" in res.headers
    return res.follow()


def _add_testing_form(test_object, login, resources):
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", os.path.join(resources, "form08_OK.xlsx"))],
    )
    assert "FS_error" not in res.headers


def _referring_repository(config, schema):
    """A repository with a foreign key into this one's maintable, as a
    follow-up's has into its cases. Returns its name."""
    key = _execute(
        config,
        "SELECT c.COLUMN_NAME, c.COLUMN_TYPE, c.CHARACTER_SET_NAME, c.COLLATION_NAME "
        "FROM information_schema.KEY_COLUMN_USAGE k "
        "JOIN information_schema.COLUMNS c ON c.TABLE_SCHEMA = k.TABLE_SCHEMA "
        "AND c.TABLE_NAME = k.TABLE_NAME AND c.COLUMN_NAME = k.COLUMN_NAME "
        "WHERE k.TABLE_SCHEMA = %s AND k.TABLE_NAME = 'maintable' "
        "AND k.CONSTRAINT_NAME = 'PRIMARY' ORDER BY k.ORDINAL_POSITION",
        schema,
    )
    assert key
    columns = ", ".join(
        "`{}` {}{}".format(
            name,
            column_type,
            (
                " CHARACTER SET {} COLLATE {}".format(charset, collation)
                if charset
                else ""
            ),
        )
        for name, column_type, charset, collation in key
    )
    names = ", ".join("`{}`".format(a_row[0]) for a_row in key)
    referring = "FS_" + str(uuid.uuid4()).replace("-", "_")
    _execute(config, "CREATE DATABASE `{}`".format(referring))
    _execute(
        config,
        "CREATE TABLE `{0}`.`maintable` ({1}, FOREIGN KEY ({2}) REFERENCES "
        "`{3}`.`maintable` ({2}) ON DELETE RESTRICT) ENGINE=InnoDB".format(
            referring, columns, names, schema
        ),
    )
    return referring


def _dumps(directory, schema):
    return sorted(glob.glob(os.path.join(directory, schema + "_*.sql.gz*")))


def _addresses_of(login, form_id):
    """Every address that names a form, FormShare's and the loaded plugins',
    filled in for this one: [(view class, path)]. What else an address
    names is made up: the form being deleted answers before it is read."""
    from formshare.config.routes import route_list
    from formshare.views.classes import FORM_KEYS

    found = []
    for a_route in route_list:
        names = re.findall(r"{(\w+)}", a_route["path"])
        if not any(a_name in FORM_KEYS for a_name in names):
            continue
        path = a_route["path"]
        for a_name in names:
            if a_name == "userid":
                value = login
            elif a_name == "projcode":
                value = PROJECT
            elif a_name in FORM_KEYS:
                value = form_id
            else:
                value = "x"
            path = path.replace("{" + a_name + "}", value)
        found.append((a_route["view"], path))
    return found


def _gone_for_everyone(test_object, login, assistant, partner_email):
    """Asks every address of the form being deleted, as the owner, as its
    assistant and its partner signed in, and as a device with credentials
    and without: each answers 404, and each because the form is being
    deleted, not because of what else the address names. Returns how many
    were asked."""
    from formshare.middleware.httpexceptions import HTTPNotFound
    from formshare.views import classes

    testapp = test_object.testapp
    kinds = (
        classes.PrivateView,
        classes.AssistantView,
        classes.PartnerView,
        classes.ODKView,
        classes.PublicView,
    )
    paths = {a_kind: [] for a_kind in kinds}
    for view, path in _addresses_of(login, PARENT):
        served = [a_kind for a_kind in kinds if issubclass(view, a_kind)]
        assert served, "{} is served by {}, which does not refuse it".format(path, view)
        paths[served[0]].append(path)

    refused = []
    guard = classes.refuse_form_being_deleted

    def counted(request, project_id=None):
        try:
            guard(request, project_id)
        except HTTPNotFound:
            refused.append(request.url)
            raise

    classes.refuse_form_being_deleted = counted
    asked = 0
    try:
        for path in paths[classes.PrivateView] + paths[classes.PublicView]:
            testapp.get(path, status=404)
            asked += 1
        # A device is refused before it is asked who it is, so in a project
        # of crowdsourcing too, where nobody is asked
        device = dict(FS_for_testing="true", FS_user_for_testing=assistant)
        for path in paths[classes.ODKView]:
            testapp.get(path, status=404)
            testapp.get(path, status=404, extra_environ=device)
            asked += 2
        res = testapp.post(
            "/user/{}/project/{}/assistantaccess/login".format(login, PROJECT),
            {"login": assistant, "passwd": "123"},
            status=302,
        )
        assert "FS_error" not in res.headers
        for path in paths[classes.AssistantView]:
            testapp.get(path, status=404)
            asked += 1
        testapp.post(
            "/user/{}/project/{}/assistantaccess/logout".format(login, PROJECT),
            status=302,
        )
        res = testapp.post(
            "/partneraccess/login",
            {"login": partner_email, "passwd": "123"},
            status=302,
        )
        assert "FS_error" not in res.headers
        for path in paths[classes.PartnerView]:
            testapp.get(path, status=404)
            asked += 1
        # Nor is it among the partner's forms
        res = testapp.get("/partneraccess/dashboard", status=200)
        assert PARENT.encode() not in res.body
        testapp.post("/partneraccess/logout", {}, status=302)
    finally:
        classes.refuse_form_being_deleted = guard
        res = testapp.post(
            "/login", {"user": "", "email": login, "passwd": "123"}, status=302
        )
        assert "FS_error" not in res.headers
    # Every kind of view was asked, and every answer was the deletion's
    assert all(paths[a_kind] for a_kind in kinds)
    assert len(refused) == asked
    return asked


def t_e_s_t_form_deletion_task(test_object):
    testapp = test_object.testapp
    config = test_object.server_config
    login = test_object.randonLogin
    project_id = str(uuid.uuid4())
    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    ini_file = os.path.join(here, "development.ini")
    resources = os.path.join(test_object.path, "resources", "forms")
    merge = os.path.join(resources, "merge")

    from formshare.processes.db.form_deletion import (
        forms_of_deletion,
        mark_for_deletion,
    )
    from formshare.products.deletion.celery_task import (
        FormDeletionError,
        _email_technical_team,
        drop_repository,
        dump_is_whole,
        internal_delete_form,
        rename_directory,
        revoke_repository_grants,
    )
    from formshare.scripts.resumeformdeletion import main as resume_main

    res = testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": project_id,
            "project_code": PROJECT,
            "project_name": "Deleting forms",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # --- A form in testing ---------------------------------------------------
    _add_testing_form(test_object, login, resources)
    testing_directory = form_row(config, project_id, TESTING_FORM)["form_directory"]

    # Its ID must be typed, exactly
    page = _refused(test_object, login, TESTING_FORM, {})
    assert b"Type the ID of the form, Justtest_b, to delete it" in page.body
    _refused(test_object, login, TESTING_FORM, confirmed("justtest_b"))
    assert deletion_state(config, login, PROJECT, TESTING_FORM) == (0, None)

    # Typed, the worker deletes it, and its directory is renamed
    delete_form(test_object, PROJECT, TESTING_FORM)
    odk_dir = os.path.join(config["repository.path"], "odk", "forms")
    assert not os.path.exists(os.path.join(odk_dir, testing_directory))
    assert glob.glob(
        os.path.join(odk_dir, testing_directory + "_deleted_by_{}_on_*".format(login))
    )
    # A form that is not there is not found, its ID typed or not
    testapp.post(
        "/user/{}/project/{}/form/no_such_form/delete".format(login, PROJECT),
        confirmed("no_such_form"),
        status=404,
    )

    # --- A form with a repository --------------------------------------------
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {"form_pkey": "numero_de_cedula"},
        status=302,
        upload_files=[("xlsx", os.path.join(merge, "A", "A.xls"))],
    )
    assert "FS_error" not in res.headers
    parent_files = [
        os.path.join(merge, "A", n) for n in ("cantones.csv", "distritos.csv")
    ]
    for a_file in parent_files:
        res = testapp.post(
            "/user/{}/project/{}/form/{}/upload".format(login, PROJECT, PARENT),
            status=302,
            upload_files=[("filetoupload", a_file)],
        )
        assert "FS_error" not in res.headers
    build_in_process(
        test_object, project_id, PROJECT, PARENT, "numero_de_cedula", parent_files
    )
    parent = form_row(config, project_id, PARENT)
    schema = parent["form_schema"]
    assert schema is not None and _repository_exists(config, schema)
    repository_dir = os.path.join(odk_dir, parent["form_directory"], "repository")

    # An assistant who cleans it and a partner who reads it: what they reach
    # of it while it is being deleted is asked below
    assistant = "fsdel_" + uuid.uuid4().hex[:8]
    assistant_uuid = str(uuid.uuid4())
    res = testapp.post(
        "/user/{}/project/{}/assistants/add".format(login, PROJECT),
        {
            "coll_uuid": assistant_uuid,
            "coll_id": assistant,
            "coll_name": assistant,
            "coll_password": "123",
            "coll_password2": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(login, PROJECT, PARENT),
        {
            "coll_id": "{}|{}|{}".format(project_id, assistant, assistant_uuid),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    partner_id = str(uuid.uuid4())
    partner_email = "fsdel{}@qlands.com".format(partner_id[-12:])
    res = testapp.post(
        "/user/{}/manage_partners/add".format(login),
        {
            "partner_id": partner_id,
            "partner_email": partner_email,
            "partner_name": "Deleting forms",
            "partner_organization": "QLands",
            "partner_telephone": "22390771",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(login, PROJECT, PARENT),
        {"partner_id": partner_id},
        status=302,
    )
    assert "FS_error" not in res.headers

    # A newer version waiting to be merged: the newest is the one to delete
    res = testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(login, PROJECT, PARENT),
        {"for_merging": "", "parent_project": project_id, "parent_form": PARENT},
        status=302,
        upload_files=[("xlsx", os.path.join(merge, "B", "B.xls"))],
    )
    assert "FS_error" not in res.headers
    page = _refused(test_object, login, PARENT, confirmed(PARENT))
    assert b"has a newer version" in page.body
    # The version has no repository: it goes alone
    delete_form(test_object, PROJECT, VERSION)
    assert form_row(config, project_id, PARENT)["form_schema"] == schema

    # A task running on the form: an export, an import, a build or a merge
    task_id = add_task(config, project_id, PARENT, "xlsx_private_export", login)
    page = _refused(test_object, login, PARENT, confirmed(PARENT))
    assert b"A task is running on this form" in page.body
    finish_task(config, task_id)

    # A blocked form: a merge, or one that failed. A form blocked since the
    # request read it is not marked either
    _execute(
        config,
        "UPDATE odkform SET form_blocked = 1 WHERE project_id = %s AND form_id = %s",
        project_id,
        PARENT,
    )
    _refused(test_object, login, PARENT, confirmed(PARENT))
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    session = Session(bind=engine)
    try:
        forms = forms_of_deletion(session, project_id, PARENT)
        request = SimpleNamespace(dbsession=session)
        assert not mark_for_deletion(request, project_id, forms, login)
    finally:
        session.close()
        engine.dispose()
    assert deletion_state(config, login, PROJECT, PARENT) == (0, None)
    _execute(
        config,
        "UPDATE odkform SET form_blocked = 0 WHERE project_id = %s AND form_id = %s",
        project_id,
        PARENT,
    )

    # A live repository with a foreign key into this one's, however that came
    # about: dropping this one would fail. Here a form in testing stands in
    # for that repository's form while the request is refused
    referring = _referring_repository(config, schema)
    _add_testing_form(test_object, login, resources)
    _execute(
        config,
        "UPDATE odkform SET form_schema = %s WHERE project_id = %s AND form_id = %s",
        referring,
        project_id,
        TESTING_FORM,
    )
    res = testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, PROJECT, PARENT),
        confirmed(PARENT),
        status=302,
    )
    assert "FS_error" in res.headers
    _execute(
        config,
        "UPDATE odkform SET form_schema = NULL WHERE project_id = %s "
        "AND form_id = %s",
        project_id,
        TESTING_FORM,
    )
    page = res.follow()
    assert b"refer to the repository of this one" in page.body
    assert b"(Justtest_b). Delete them first" in page.body
    # The technical team cannot resume what was never asked: a live form is
    # left as it is, with nothing recorded on it
    assert resume_main([ini_file, project_id, TESTING_FORM]) == 1
    assert deletion_state(config, login, PROJECT, TESTING_FORM) == (0, None)
    delete_form(test_object, PROJECT, TESTING_FORM)
    # The repository stays, as the leftover of a form deleted before
    # 2026-10-28 would: nothing names it

    # A submission of it, which the project's map draws until the form is
    # marked. The map names no form in its address for the guard to read, so
    # it leaves the form out itself (get_gps_points_from_project)
    from formshare.processes.elasticsearch import repository_index as dataset_index

    located = str(uuid.uuid4())
    dataset_index.add_dataset(
        config,
        project_id,
        PARENT,
        located,
        {
            "_xform_id_string": PARENT,
            "_submitted_date": "2026-10-29T08:00:00.000001",
            "_submitted_by": assistant,
            "_geopoint": "9.9281 -84.0907 1150 5",
        },
    )
    connection = dataset_index.create_connection(config)
    connection.indices.refresh(index=dataset_index.get_index_name(config))
    connection.close()
    gps_points = "/user/{}/project/{}/download/gpspoints".format(login, PROJECT)
    points = testapp.get(gps_points, status=200).json["points"]
    assert [a_point["key"] for a_point in points] == [PARENT]

    # --- The task, here, stopping --------------------------------------------
    # The request marks the form as being deleted before it queues the task;
    # here it is marked as the request does, and the task runs in this process
    _execute(
        config,
        "UPDATE odkform SET form_accsub = 0, form_blocked = 1, form_deleting = 1, "
        "form_deletedby = %s WHERE project_id = %s AND form_id = %s",
        login,
        project_id,
        PARENT,
    )
    # What accounts hold on the repository: MySQL keeps it when it drops a
    # database, and restoring the dump would make the schema again under its
    # name. A grant on the name, as the analytics plugin makes; one with its
    # underscores escaped; and one on a pattern that covers every
    # repository, which is not the repository's to revoke
    role = "fsdel_" + uuid.uuid4().hex[:12]
    escaped = schema.replace("_", "\\_")
    _execute(config, "CREATE ROLE '{}'".format(role))
    _execute(
        config,
        "GRANT SELECT ON `{}`.* TO '{}' WITH GRANT OPTION".format(schema, role),
    )
    _execute(config, "GRANT SELECT ON `{}`.* TO '{}'".format(escaped, role))
    _execute(config, "GRANT SELECT ON `FS\\_%`.* TO '{}'".format(role))

    def granted():
        rows = _execute(
            config, "SELECT Db FROM mysql.db WHERE User = %s ORDER BY Db", role
        )
        return [a_row[0] for a_row in rows]

    assert granted() == sorted([schema, escaped, "FS\\_%"])

    # A dump that mysqldump cut short is not kept, and nothing is dropped
    fake_bin = tempfile.mkdtemp()
    with open(os.path.join(fake_bin, "mysqldump"), "w") as fake:
        fake.write("#!/bin/sh\necho '-- A dump cut short'\n")
    os.chmod(os.path.join(fake_bin, "mysqldump"), 0o755)
    path = os.environ["PATH"]
    os.environ["PATH"] = fake_bin + os.pathsep + path
    try:
        deleted, reason = internal_delete_form(dict(config), project_id, PARENT, "en")
    finally:
        os.environ["PATH"] = path
        shutil.rmtree(fake_bin)
    assert not deleted and "is not whole" in reason
    assert _repository_exists(config, schema)
    assert not _dumps(repository_dir, schema)
    # The task revoked the repository's grants before anything else, stopped
    # or not, and left the pattern's
    assert granted() == ["FS\\_%"]

    # A mysqldump that fails
    settings = dict(config)
    settings["mysql.cnf"] = os.path.join(here, "no_such_mysql.cnf")
    deleted, reason = internal_delete_form(settings, project_id, PARENT, "en")
    assert not deleted and "mysqldump" in reason
    # It stopped before anything was lost: marked, with the reason, and the
    # repository whole
    state = deletion_state(config, login, PROJECT, PARENT)
    assert state[0] == 1 and "mysqldump" in state[1]
    assert _repository_exists(config, schema)
    assert not _dumps(repository_dir, schema)
    # Nothing of it answers any more, to anyone (owner, 2026-10-28): every
    # address that names it is 404 -- its page, its repository's pages, its
    # downloads, the assistant's and the partner's pages, and what devices
    # download, the cases its lists serve included
    assert _gone_for_everyone(test_object, login, assistant, partner_email) > 80
    # The project's page says so, and leads to none of it
    res = testapp.get("/user/{}/project/{}".format(login, PROJECT), status=200)
    assert b"Being deleted" in res.body
    assert '/form/{}"'.format(PARENT).encode() not in res.body
    # and its map draws none of its points, which the index still holds
    total, datasets = dataset_index.get_datasets_from_project(config, project_id)
    assert PARENT in [a_dataset["_xform_id_string"] for a_dataset in datasets]
    points = testapp.get(gps_points, status=200).json["points"]
    assert PARENT not in [a_point["key"] for a_point in points]
    dataset_index.delete_from_dataset_index(config, project_id, PARENT, located)
    # Nor can it be deleted again, nor replaced, nor given a new version: a
    # version made now would go with it, by the cascade of its row, and
    # leave its files behind
    testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, PROJECT, PARENT),
        confirmed(PARENT),
        status=404,
    )
    for route, data, workbook in (
        (
            "merge",
            {"for_merging": "", "parent_project": project_id, "parent_form": PARENT},
            os.path.join(merge, "B", "B.xls"),
        ),
        (
            "updateodk",
            {"form_pkey": "numero_de_cedula"},
            os.path.join(merge, "A", "A.xls"),
        ),
    ):
        testapp.post(
            "/user/{}/project/{}/form/{}/{}".format(login, PROJECT, PARENT, route),
            data,
            status=404,
            upload_files=[("xlsx", workbook)],
        )
    versions = _execute(
        config,
        "SELECT COUNT(*) FROM odkform WHERE parent_project = %s AND parent_form = %s",
        project_id,
        PARENT,
    )
    assert versions[0][0] == 0

    # No list can start drawing its cases from it: the wizard does not offer
    # it, and refuses it when asked. The import refuses it too
    # (test_10_list_transfer)
    lists = "/user/{}/project/{}/caselists/add".format(login, PROJECT)
    res = testapp.get(lists, status=200)
    assert 'value="{}"'.format(PARENT).encode() not in res.body
    res = testapp.post(
        lists,
        {
            "list_id": "deleted_cases",
            "list_filename": "deleted_cases.csv",
            "source_form": PARENT,
            "source_table": "maintable",
            "label_column": "numero_de_cedula",
        },
        status=200,
    )
    assert b"is being deleted: a list cannot draw its cases from it" in res.body
    assert not _execute(
        config,
        "SELECT list_id FROM publishedlist WHERE project_id = %s",
        project_id,
    )

    # The update API reads the form from the row, not from its address: a
    # row of a form being deleted is not written
    from formshare.processes.elasticsearch.record_index import (
        add_record,
        create_connection,
        delete_from_record_index,
        get_index_name,
    )

    row = str(uuid.uuid4())
    add_record(config, project_id, PARENT, "none", schema, "maintable", row)
    connection = create_connection(config)
    connection.indices.refresh(index=get_index_name(config))
    connection.close()
    api_key = str(uuid.uuid4())
    _execute(
        config,
        "UPDATE collaborator SET coll_apikey = %s WHERE project_id = %s "
        "AND coll_id = %s",
        api_key,
        project_id,
        assistant,
    )
    res = testapp.post_json(
        "/api_update",
        {"apikey": api_key, "rowuuid": row, "numero_de_cedula": "1"},
        status=404,
    )
    assert res.json["error_type"] == "form_not_found"
    delete_from_record_index(config, row)

    # The technical team lists it
    with contextlib.redirect_stdout(io.StringIO()) as listed:
        assert resume_main([ini_file]) == 0
    assert "{} ({}) {}".format(project_id, PROJECT, PARENT) in listed.getvalue()
    assert resume_main([os.path.join(here, "no_such.ini")]) == 1

    # The leftover's foreign key: the dump is whole, the drop refused, and
    # MySQL drops a database whole or not at all
    deleted, reason = internal_delete_form(dict(config), project_id, PARENT, "en")
    assert not deleted and "foreign key" in reason
    state = deletion_state(config, login, PROJECT, PARENT)
    assert state[0] == 1 and "foreign key" in state[1]
    assert _repository_exists(config, schema)
    first_dump = _dumps(repository_dir, schema)
    assert len(first_dump) == 1 and dump_is_whole(first_dump[0])

    # A version that shares the repository goes with the form. A form in
    # testing stands in for it, marked as the request marks every version
    _add_testing_form(test_object, login, resources)
    version_directory = form_row(config, project_id, TESTING_FORM)["form_directory"]
    _execute(
        config,
        "UPDATE odkform SET form_schema = %s, form_accsub = 0, form_blocked = 1, "
        "form_deleting = 1, form_deletedby = %s "
        "WHERE project_id = %s AND form_id = %s",
        schema,
        login,
        project_id,
        TESTING_FORM,
    )

    # The team deals with the leftover and resumes the deletion, on the
    # server. The Celery plugins hear of each form, after one that fails:
    # what a plugin keeps of a version is under the version's own ID
    _execute(config, "DROP DATABASE `{}`".format(referring))
    # A dump is named by the second it was made in, and the team comes back
    # later than that
    time.sleep(1.1)
    import formshare.plugins as fs_plugins

    told = []

    class FailingPlugin:
        def after_deleting_form(self, *args):
            raise RuntimeError("A plugin that fails")

    class Plugin:
        def after_deleting_form(self, settings, user, project, form, form_data, log):
            told.append((user, project, form, form_data["form_schema"]))

    implementations = fs_plugins.PluginImplementations

    def with_plugins(interface):
        if interface is fs_plugins.IFormDeletionProcess:
            return [FailingPlugin(), Plugin()]
        return implementations(interface)

    fs_plugins.PluginImplementations = with_plugins
    try:
        assert resume_main([ini_file, project_id, PARENT]) == 0
    finally:
        fs_plugins.PluginImplementations = implementations
    assert told == [
        (login, project_id, PARENT, schema),
        (login, project_id, TESTING_FORM, schema),
    ]
    assert deletion_state(config, login, PROJECT, PARENT) is None
    assert deletion_state(config, login, PROJECT, TESTING_FORM) is None
    assert not _repository_exists(config, schema)
    assert granted() == ["FS\\_%"]
    _execute(config, "DROP ROLE '{}'".format(role))
    assert (
        len(glob.glob(os.path.join(odk_dir, version_directory + "_deleted_by_*_on_*")))
        == 1
    )
    renamed = glob.glob(
        os.path.join(odk_dir, parent["form_directory"] + "_deleted_by_*_on_*")
    )
    assert len(renamed) == 1
    # The dump of each attempt that got that far, each one whole
    dumps = _dumps(os.path.join(renamed[0], "repository"), schema)
    assert len(dumps) == 2 and all(dump_is_whole(a_dump) for a_dump in dumps)
    with gzip.open(dumps[-1], "rt") as dump:
        text = dump.read()
    assert "CREATE DATABASE" in text and "CREATE TABLE `maintable`" in text
    # A deletion already done is done: resuming it again changes nothing
    assert resume_main([ini_file, project_id, PARENT]) == 0

    # A name that is no repository's is never dropped nor revoked, and a
    # directory that is not there is not renamed
    for a_step in (drop_repository, revoke_repository_grants):
        try:
            a_step(None, "not a repository`; DROP DATABASE mysql")
        except FormDeletionError:
            pass
        else:
            raise AssertionError("a name that is no repository's was used")
    assert rename_directory(os.path.dirname(odk_dir), None, login, "now") is None
    assert (
        rename_directory(os.path.dirname(odk_dir), "no_such_form", login, "now") is None
    )
    # Without an address to write to, nobody is emailed
    assert _email_technical_team({}, "Subject", "Message", "en") is None

    # The project, empty, can go, and the list no longer names its forms
    res = testapp.post("/user/{}/project/{}/delete".format(login, PROJECT), status=302)
    assert "FS_error" not in res.headers
    with contextlib.redirect_stdout(io.StringIO()) as listed:
        assert resume_main([ini_file]) == 0
    assert project_id not in listed.getvalue()
    res = testapp.post(
        "/user/{}/manage_partner/{}/delete".format(login, partner_id), status=302
    )
    assert "FS_error" not in res.headers

    # --- A classic case project (2021) ---------------------------------------
    # While the form that creates its cases is being deleted, no follow-up
    # can be added: it would read its cases from a repository being dropped
    case_project_id = str(uuid.uuid4())
    case_project = "form_deletion_cases"
    creator = "case_start_20210311"
    res = testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": case_project_id,
            "project_code": case_project,
            "project_name": "Deleting the form that creates the cases",
            "project_abstract": "",
            "project_case": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    case_forms = os.path.join(test_object.path, "resources", "forms", "case")
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, case_project),
        {
            "form_pkey": "hid",
            "form_caselabel": "fname",
            "form_casedatetime": "coll_date",
        },
        status=302,
        upload_files=[("xlsx", os.path.join(case_forms, "case_start.xlsx"))],
    )
    assert "FS_error" not in res.headers
    _execute(
        config,
        "UPDATE odkform SET form_accsub = 0, form_blocked = 1, form_deleting = 1 "
        "WHERE project_id = %s AND form_id = %s",
        case_project_id,
        creator,
    )
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, case_project),
        {"form_pkey": "survey_id", "form_caseselector": "hid", "form_casetype": "2"},
        status=302,
        upload_files=[("xlsx", os.path.join(case_forms, "case_follow_up.xlsx"))],
    )
    assert "FS_error" in res.headers
    assert (
        b"The form that creates the cases of this project is being deleted"
        in res.follow().body
    )
    assert _execute(
        config, "SELECT form_id FROM odkform WHERE project_id = %s", case_project_id
    ) == [(creator,)]
    # It is gone, and the project with it
    _execute(
        config,
        "UPDATE odkform SET form_accsub = 1, form_blocked = 0, form_deleting = 0 "
        "WHERE project_id = %s",
        case_project_id,
    )
    delete_form(test_object, case_project, creator)
    res = testapp.post(
        "/user/{}/project/{}/delete".format(login, case_project), status=302
    )
    assert "FS_error" not in res.headers
