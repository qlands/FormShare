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
  time the form stays marked with the reason, and its repository whole.
- resume_form_deletion finishes it: the dump of each attempt in the renamed
  directory, the repository dropped, the form gone, and the Celery plugins
  told, one that fails included.

Every deletion made to stop here runs with the suite's settings, which send
no email: resume_form_deletion reads development.ini, so it only runs those
that succeed or stop before emailing anyone.

The refusals of the longitudinal study are in case_journey.py, where the
cases and their follow-ups are.
"""

import contextlib
import glob
import gzip
import io
import os
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
    # The page says so, and offers nothing to do with the form
    res = testapp.get(
        "/user/{}/project/{}/form/{}".format(login, PROJECT, PARENT), status=200
    )
    assert b"form-deleting" in res.body
    assert b"update_form_btn" not in res.body
    assert b"formdetails_files_container" not in res.body
    res = testapp.get("/user/{}/project/{}".format(login, PROJECT), status=200)
    assert b"Being deleted" in res.body
    # Nor can it be deleted again
    page = _refused(test_object, login, PARENT, confirmed(PARENT))
    assert b"This form is being deleted" in page.body
    # Nor replaced, nor given a new version: a version made now would go with
    # it, by the cascade of its row, and leave its files behind
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
        res = testapp.post(
            "/user/{}/project/{}/form/{}/{}".format(login, PROJECT, PARENT, route),
            data,
            status=302,
            upload_files=[("xlsx", workbook)],
        )
        assert "FS_error" in res.headers
        assert b"This form is being deleted" in res.follow().body
    versions = _execute(
        config,
        "SELECT COUNT(*) FROM odkform WHERE parent_project = %s AND parent_form = %s",
        project_id,
        PARENT,
    )
    assert versions[0][0] == 0

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

    # The team deals with the leftover and resumes the deletion, on the
    # server. The Celery plugins hear of it, after one that fails
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
    assert told == [(login, project_id, PARENT, schema)]
    assert deletion_state(config, login, PROJECT, PARENT) is None
    assert not _repository_exists(config, schema)
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

    # A name that is no repository's is never dropped, and a directory that
    # is not there is not renamed
    try:
        drop_repository(None, "not a repository`; DROP DATABASE mysql")
    except FormDeletionError:
        pass
    else:
        raise AssertionError("a name that is no repository's was dropped")
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
