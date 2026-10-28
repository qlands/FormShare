"""A published list that serves each assistant their own cases (feature 7,
stage 8, formshare.md 3.8; processes/db/case_management.py).

The manifest and the download answer the assistant they authenticate with
that assistant's variant of the list, under the list's own name: in mode
submitted_by, the cases of the submissions they sent. A list in mode all is
served as before, the same file to everyone. A crowdsourcing project has no
assistants, so it cannot take the mode, and a request that names no
assistant receives no case.
"""

import csv
import io
import json
import os
import re
import threading
import time
import uuid
from hashlib import md5
from urllib.parse import urlparse

from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from formshare.processes.db.case_management import list_variant_clause, variant_key
from formshare.processes.list_lock import form_copy_key, list_lock, variant_lock_key
from formshare.products.block import get_redis_client

from .config_switches import settings_set_to, system_timezone
from .in_process import build_in_process, form_row

PROJECT = "perassistant"
FORM = "LB_Sequia_MAG_20190123"
LIST_ID = "households"
LIST_FILE = "households.csv"
ANA, BEN, CAROL = "pa_ana", "pa_ben", "pa_carol"
GROUP = "pagrp1"
OLD_FORM = "tormenta20201105"
OPENROSA_MANIFEST = "{http://openrosa.org/xforms/xformsManifest}"


def _as(assistant):
    """The environment of a request a device makes as an assistant; none for
    a request that names no assistant."""
    if assistant is None:
        return {}
    return dict(FS_for_testing="true", FS_user_for_testing=assistant)


def _list_entry(test_object, assistant):
    """(hash, download path) of the list in the form's manifest, as the
    assistant's device receives it."""
    res = test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, PROJECT, FORM
        ),
        status=200,
        extra_environ=_as(assistant),
    )
    for a_file in etree.fromstring(res.body).findall(OPENROSA_MANIFEST + "mediaFile"):
        if a_file.findtext(OPENROSA_MANIFEST + "filename") == LIST_FILE:
            return (
                a_file.findtext(OPENROSA_MANIFEST + "hash"),
                urlparse(a_file.findtext(OPENROSA_MANIFEST + "downloadUrl")).path,
            )
    raise AssertionError("The manifest does not carry the list")


def _received(test_object, assistant):
    """The cases the assistant's device receives -- the rowuuids in the
    file -- after checking that the file is the one the manifest hashed."""
    list_hash, path = _list_entry(test_object, assistant)
    body = test_object.testapp.get(path, status=200, extra_environ=_as(assistant)).body
    assert list_hash == "md5:" + md5(body).hexdigest()
    rows = list(csv.reader(io.StringIO(body.decode("utf-8"))))
    assert rows[0][:2] == ["name", "label"]
    return list_hash, sorted(a_row[0] for a_row in rows[1:])


def _push(test_object, assistant, primary_key, rowuuid=None):
    """A submission of the form, sent by the assistant to its repository.
    With a rowuuid, the device minted the case's identity (meta/rowuuid), as
    FormShare Collect does."""
    with open(
        os.path.join(
            test_object.path, "resources", "forms", "mimic_complex", "submission001.xml"
        ),
        encoding="utf-8",
    ) as a_file:
        xml = a_file.read()
    xml = re.sub(r"<I_D>[^<]*</I_D>", "<I_D>{}</I_D>".format(primary_key), xml)
    xml = re.sub(
        r"<instanceID>[^<]*</instanceID>",
        "<instanceID>uuid:{}</instanceID>".format(uuid.uuid4()),
        xml,
    )
    if rowuuid is not None:
        xml = xml.replace(
            "</instanceID>", "</instanceID><rowuuid>{}</rowuuid>".format(rowuuid)
        )
    path = os.path.join(test_object.working_dir, "pa_{}.xml".format(primary_key))
    with open(path, "w", encoding="utf-8") as a_file:
        a_file.write(xml)
    res = test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, PROJECT),
        status=201,
        upload_files=[("filetoupload", path)],
        extra_environ=_as(assistant),
    )
    assert "FS_error" not in res.headers


def _cases_by_assistant(config, schema):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        rows = engine.execute(
            "SELECT _submitted_by, rowuuid FROM `{}`.maintable".format(schema)
        ).fetchall()
    finally:
        engine.dispose()
    return {a_row[0]: a_row[1] for a_row in rows}


def _assign(config, schema, rowuuid, assistant):
    """Assigns a case to an assistant, by SQL: the Case Explorer, the one
    place that reassigns (reassign_case, owner 2026-10-18), is a private
    plugin the suite does not load."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        engine.execute(
            "UPDATE `{}`.maintable SET _assigned_to = %s WHERE rowuuid = %s".format(
                schema
            ),
            (assistant, rowuuid),
        )
    finally:
        engine.dispose()


def _assignee(config, schema, rowuuid):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return engine.execute(
            "SELECT _assigned_to FROM `{}`.maintable WHERE rowuuid = %s".format(schema),
            (rowuuid,),
        ).scalar()
    finally:
        engine.dispose()


def _logged(config, project_id):
    """The submissions of the form waiting in its logs."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return {
            a_row[0]
            for a_row in engine.execute(
                "SELECT submission_id FROM submission WHERE submission_status = 2 "
                "AND sameas IS NULL AND project_id = %s AND form_id = %s",
                (project_id, FORM),
            ).fetchall()
        }
    finally:
        engine.dispose()


def _copy_state(config, project_id):
    """The form's copy of the list: its MD5 and when it was generated."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return tuple(
            engine.execute(
                "SELECT file_md5, file_lastgen FROM mediafile WHERE project_id = %s "
                "AND form_id = %s AND file_name = %s",
                (project_id, FORM, LIST_FILE),
            ).fetchone()
        )
    finally:
        engine.dispose()


def _set_copy(config, project_id, assignments):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        engine.execute(
            "UPDATE mediafile SET {} WHERE project_id = %s AND form_id = %s "
            "AND file_name = %s".format(assignments),
            (project_id, FORM, LIST_FILE),
        )
    finally:
        engine.dispose()


def _set_variants(config, project_id, assignments, key=None):
    """Changes the list's variants, or the one named key."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        sql = "UPDATE listvariant SET {} WHERE project_id = %s AND list_id = %s".format(
            assignments
        )
        params = [project_id, LIST_ID]
        if key is not None:
            sql += " AND variant_key = %s"
            params.append(key)
        engine.execute(sql, tuple(params))
    finally:
        engine.dispose()


def _two_hours_behind_the_database(config):
    """A time zone for this process two hours behind the database's clock,
    as production's FormShare (UTC) ran behind its MySQL (CEST) until
    2026-10-19: POSIX counts the hours west of Greenwich."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        database = engine.execute(
            "SELECT TIMESTAMPDIFF(MINUTE, UTC_TIMESTAMP(), NOW())"
        ).scalar()
    finally:
        engine.dispose()
    west = 120 - database
    return "FST{}{}:{:02d}".format(
        "-" if west < 0 else "", abs(west) // 60, abs(west) % 60
    )


def _assigned(config, schema):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        rows = engine.execute(
            "SELECT _submitted_by, _assigned_to FROM `{}`.maintable".format(schema)
        ).fetchall()
    finally:
        engine.dispose()
    # Nobody's case (None) sorts before anyone's
    return sorted(
        ((a_row[0], a_row[1]) for a_row in rows),
        key=lambda pair: (pair[0], pair[1] or ""),
    )


def _i_d_is(value):
    """The rule set of a filter: the case whose I_D is value."""
    return json.dumps(
        {
            "condition": "AND",
            "rules": [
                {"id": "t.i_d", "field": "t.i_d", "operator": "equal", "value": value}
            ],
            "valid": True,
        }
    )


def _filter_id(config, project_id, name):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return engine.execute(
            "SELECT filter_id FROM listfilter WHERE project_id = %s "
            "AND list_id = %s AND filter_name = %s",
            (project_id, LIST_ID, name),
        ).scalar()
    finally:
        engine.dispose()


def _set_crowdsourcing(config, project_id, crowdsourcing):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        engine.execute(
            "UPDATE project SET project_formlist_auth = %s WHERE project_id = %s",
            (0 if crowdsourcing else 1, project_id),
        )
    finally:
        engine.dispose()


def _requires_authentication(config, project_id):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return (
            engine.execute(
                "SELECT project_formlist_auth FROM project WHERE project_id = %s",
                (project_id,),
            ).scalar()
            == 1
        )
    finally:
        engine.dispose()


def _project_form(authentication):
    """The project's edit form, with or without "Requires authentication to
    accept data"; without it, the project takes public submissions."""
    form = {
        "project_code": PROJECT,
        "project_name": "Each assistant their own cases",
        "project_abstract": "",
        "project_icon": "",
        "project_hexcolor": "",
    }
    if authentication:
        form["project_formlist_auth"] = 1
    return form


def t_e_s_t_per_assistant_lists(test_object):
    testapp = test_object.testapp
    config = test_object.server_config
    login = test_object.randonLogin
    project_id = str(uuid.uuid4())
    complex_form = os.path.join(test_object.path, "resources", "forms", "complex_form")

    res = testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": project_id,
            "project_code": PROJECT,
            "project_name": "Each assistant their own cases",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {"form_pkey": "I_D"},
        status=302,
        upload_files=[("xlsx", os.path.join(complex_form, "B.xlsx"))],
    )
    assert "FS_error" not in res.headers
    uuids = {}
    for assistant in (ANA, BEN, CAROL):
        assistant_uuid = str(uuid.uuid4())
        uuids[assistant] = assistant_uuid
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
            "/user/{}/project/{}/form/{}/assistants/add".format(login, PROJECT, FORM),
            {
                "coll_id": "{}|{}|{}".format(project_id, assistant, assistant_uuid),
                "coll_can_submit": "1",
                "coll_can_clean": "1",
            },
            status=302,
        )
        assert "FS_error" not in res.headers

    # A repository with one case from each assistant
    build_in_process(
        test_object,
        project_id,
        PROJECT,
        FORM,
        "I_D",
        [
            os.path.join(complex_form, name)
            for name in ("cantones.csv", "distritos.csv", "generated.csv")
        ],
    )
    _push(test_object, ANA, 801)
    _push(test_object, BEN, 802)
    schema = form_row(config, project_id, FORM)["form_schema"]
    cases = _cases_by_assistant(config, schema)
    assert sorted(cases) == [ANA, BEN]
    # Each case is assigned to whoever registered it
    assert _assigned(config, schema) == [(ANA, ANA), (BEN, BEN)]

    # A list of them, attached to the form by its name
    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, PROJECT),
        {
            "list_id": LIST_ID,
            "list_filename": LIST_FILE,
            "source_form": FORM,
            "source_table": "maintable",
            "label_column": "i_d",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    placeholder = os.path.join(test_object.working_dir, LIST_FILE)
    with open(placeholder, "w") as a_file:
        a_file.write("name,label\n")
    res = testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(login, PROJECT, FORM),
        status=302,
        upload_files=[("filetoupload", placeholder)],
    )
    assert "FS_error" not in res.headers
    edit = "/user/{}/project/{}/caselists/{}/edit".format(login, PROJECT, LIST_ID)

    # In mode all, everyone receives every case, the same file
    every_case = sorted(cases.values())
    all_hash, received = _received(test_object, ANA)
    assert received == every_case
    assert _received(test_object, BEN) == (all_hash, every_case)

    # One regeneration of a copy at a time (list_lock, 2026-10-19). A pull
    # that finds the list stale while another request regenerates it waits,
    # then serves what the other made instead of writing it again. The other
    # request is a thread here: it holds the lock, stamps the copy and
    # records a marker for its MD5 while the pull waits.
    #
    # It stamps two seconds on. A stamp in the second of the last submission
    # counts as older than it (list_is_stale): MySQL rounds _submitted_date
    # to the second and NOW() truncates, so a submission at 12:00:04.6 is
    # 12:00:05, and so is a stamp at 12:00:05.4. The pull then rightly
    # regenerates the copy, and the marker is gone. With half a second, the
    # step failed whenever it got here within a second of Ben's push
    # (2026-10-28).
    copy_key = form_copy_key(project_id, FORM, LIST_FILE)
    stale = "file_lastgen = '2000-01-01 00:00:00'"
    _set_copy(config, project_id, stale)
    marker = "feedface" * 4
    holding = threading.Event()

    def another_regeneration():
        with list_lock(config, copy_key) as held:
            assert held
            holding.set()
            time.sleep(2)
            _set_copy(
                config,
                project_id,
                "file_lastgen = NOW(), file_md5 = '{}'".format(marker),
            )

    other = threading.Thread(target=another_regeneration)
    other.start()
    holding.wait(10)
    assert _list_entry(test_object, ANA)[0] == "md5:" + marker
    other.join()
    regenerated_at = _copy_state(config, project_id)[1]
    assert _copy_state(config, project_id) == (marker, regenerated_at)
    # One kept past the wait: the list is served as it is, not regenerated
    _set_copy(config, project_id, stale)
    redis_client = get_redis_client(config)
    redis_client.set("list-lock:" + copy_key, "another request", ex=60)
    try:
        with settings_set_to({"lists.lock_wait": "0.3"}):
            assert _list_entry(test_object, ANA)[0] == "md5:" + marker
        assert _copy_state(config, project_id)[1].year == 2000
    finally:
        redis_client.delete("list-lock:" + copy_key)
        redis_client.close()
    # With the lock free the pull regenerates it, by caselistgen, as it was
    assert _received(test_object, ANA) == (all_hash, every_case)
    assert _copy_state(config, project_id)[0] == all_hash[len("md5:") :]
    res = testapp.get(edit, status=200)
    assert b'id="list_filter_mode"' in res.body

    # In mode submitted_by, each receives the cases they sent
    res = testapp.post(
        edit, {"list_filter_mode": "submitted_by", "change_mode": "1"}, status=302
    )
    assert "FS_error" not in res.headers
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, PROJECT), status=200
    )
    assert b"Per assistant: the cases they registered" in res.body
    ana_hash, received = _received(test_object, ANA)
    assert received == [cases[ANA]]
    # A device that downloads without asking for the manifest first gets its
    # variant made there and then. The path is everyone's; Ana's manifest
    # made Ana's variant only.
    _, path = _list_entry(test_object, ANA)
    body = testapp.get(path, status=200, extra_environ=_as(BEN)).body
    assert [a_row[0] for a_row in csv.reader(io.StringIO(body.decode()))][1:] == [
        cases[BEN]
    ]
    ben_hash, received = _received(test_object, BEN)
    assert received == [cases[BEN]]
    assert ben_hash == "md5:" + md5(body).hexdigest()
    assert len({all_hash, ana_hash, ben_hash}) == 3
    # The variant stays what it was while its source does not change, and
    # choosing the mode the list has changes nothing
    res = testapp.post(
        edit, {"list_filter_mode": "submitted_by", "change_mode": "1"}, status=302
    )
    assert "FS_error" not in res.headers
    assert _received(test_object, ANA) == (ana_hash, [cases[ANA]])

    # Per-assistant lists race too (list_lock, 2026-10-19). Each assistant's
    # variant is a file of its own with a lock of its own. While another
    # request -- Ana's first phone, a thread here -- regenerates hers, Ben's
    # pull is not kept waiting and brings his cases, and Ana's second phone
    # waits and serves what the first made.
    ana_key = variant_key(
        list_variant_clause(
            {"list_filter_mode": "submitted_by", "source_table": "maintable"},
            schema,
            ANA,
        )
    )
    variant_stale = "variant_lastgen = '2000-01-01 00:00:00'"
    _set_variants(config, project_id, variant_stale)
    variant_marker = "decafbad" * 4
    ana_holding = threading.Event()

    def anas_first_phone():
        with list_lock(config, variant_lock_key(project_id, LIST_ID, ana_key)) as held:
            assert held
            ana_holding.set()
            time.sleep(3)
            _set_variants(
                config,
                project_id,
                "variant_lastgen = NOW(), variant_md5 = '{}'".format(variant_marker),
                ana_key,
            )

    first_phone = threading.Thread(target=anas_first_phone)
    first_phone.start()
    ana_holding.wait(10)
    assert _received(test_object, BEN) == (ben_hash, [cases[BEN]])
    # Ben had his cases while Ana's list was still locked
    assert first_phone.is_alive()
    assert _list_entry(test_object, ANA)[0] == "md5:" + variant_marker
    first_phone.join()
    # Free again, Ana's list regenerates with her cases
    _set_variants(config, project_id, variant_stale, ana_key)
    assert _received(test_object, ANA) == (ana_hash, [cases[ANA]])

    # In mode assigned_to, each receives the cases assigned to them: at first
    # the ones they registered. A case assigned to nobody -- loaded before a
    # merge gave the repository the column -- goes to its registrar when the
    # mode is chosen.
    _assign(config, schema, cases[BEN], None)
    res = testapp.post(
        edit, {"list_filter_mode": "assigned_to", "change_mode": "1"}, status=302
    )
    assert "FS_error" not in res.headers
    assert _assigned(config, schema) == [(ANA, ANA), (BEN, BEN)]
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, PROJECT), status=200
    )
    assert b"Per assistant: the cases assigned to them" in res.body
    assert _received(test_object, ANA)[1] == [cases[ANA]]
    assert _received(test_object, BEN)[1] == [cases[BEN]]
    # A case assigned to Ben leaves Ana's device for his at their next pull
    _assign(config, schema, cases[ANA], BEN)
    assert _received(test_object, ANA)[1] == []
    assert _received(test_object, BEN)[1] == every_case
    res = testapp.get(edit, status=200)
    assert b"Every case of the list reaches an assistant" in res.body
    # One assigned to someone who cannot download the list reaches nobody,
    # and the page says which
    _assign(config, schema, cases[BEN], "someone_else")
    res = testapp.get(edit, status=200)
    assert b'id="coverage-cases"' in res.body
    assert b"assigned to nobody, or to someone" in res.body
    assert cases[BEN].encode() in res.body
    _assign(config, schema, cases[BEN], BEN)
    # Who registered it does not change
    res = testapp.post(
        edit, {"list_filter_mode": "submitted_by", "change_mode": "1"}, status=302
    )
    assert "FS_error" not in res.headers
    assert _received(test_object, ANA)[1] == [cases[ANA]]

    # In mode filters, each receives what the filters given to them, or to a
    # group they belong to, match. Ben is in the group; Carol has no filter.
    res = testapp.post(
        "/user/{}/project/{}/groups/add".format(login, PROJECT),
        {"group_desc": "Supervisors", "group_id": GROUP},
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/group/{}/members".format(login, PROJECT, GROUP),
        {"assistants": "{}|{}|{}".format(project_id, BEN, uuids[BEN])},
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        edit, {"list_filter_mode": "filters", "change_mode": "1"}, status=302
    )
    assert "FS_error" not in res.headers
    res = testapp.get(edit, status=200)
    assert b'id="list-filters-none"' in res.body
    assert _received(test_object, ANA)[1] == []
    add = "/user/{}/project/{}/caselists/{}/filters/add".format(login, PROJECT, LIST_ID)
    res = testapp.get(add, status=200)
    assert b'id="filter-builder"' in res.body
    assert "group:{}".format(GROUP).encode() in res.body
    assert "assistant:{}".format(uuids[CAROL]).encode() in res.body
    res = testapp.post(
        add,
        {
            "filter_name": "Ana only",
            "filter_rules": _i_d_is(801),
            "assignees": "assistant:" + uuids[ANA],
            "save_filter": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _received(test_object, ANA)[1] == [cases[ANA]]
    assert _received(test_object, BEN)[1] == []
    # Ben and Carol have no filter yet, and Ben's case no filter matches
    res = testapp.get(edit, status=200)
    assert b'id="coverage-assistants"' in res.body
    assert b"pa_ben (pa_ben)" in res.body and b"pa_carol (pa_carol)" in res.body
    assert b"No filter matches them" in res.body
    assert cases[BEN].encode() in res.body
    # A filter with no condition gives every case, here to the group
    res = testapp.post(
        add,
        {
            "filter_name": "Everything",
            "filter_rules": "",
            "assignees": "group:" + GROUP,
            "save_filter": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _received(test_object, BEN)[1] == every_case
    assert _received(test_object, ANA)[1] == [cases[ANA]]
    assert _received(test_object, CAROL)[1] == []
    res = testapp.get(edit, status=200)
    assert b'id="list-filters-table"' in res.body
    assert b"Supervisors" in res.body
    # Only Carol is left without a filter, and every case reaches someone
    coverage = res.body[res.body.index(b'id="coverage-assistants"') :]
    coverage = coverage[: coverage.index(b"</p>")]
    assert b"pa_carol (pa_carol)" in coverage and b"pa_ben" not in coverage
    assert b"Every case of the list reaches an assistant" in res.body
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, PROJECT), status=200
    )
    assert b"Per assistant: the cases of their filters" in res.body
    # A name is a filter of the list's once
    res = testapp.post(
        add,
        {"filter_name": "Everything", "filter_rules": "", "save_filter": "1"},
        status=200,
    )
    assert "FS_error" in res.headers
    # Changed, a filter serves its assistants what it matches now
    ana_only = "/user/{}/project/{}/caselists/{}/filters/{}/edit".format(
        login, PROJECT, LIST_ID, _filter_id(config, project_id, "Ana only")
    )
    res = testapp.get(ana_only, status=200)
    assert b'id="filter-cases"' in res.body
    res = testapp.post(
        ana_only,
        {
            "filter_name": "Ana only",
            "filter_rules": _i_d_is(802),
            "assignees": "assistant:" + uuids[ANA],
            "save_filter": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _received(test_object, ANA)[1] == [cases[BEN]]
    # Deleted, it serves nobody
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/filters/{}/delete".format(
            login, PROJECT, LIST_ID, _filter_id(config, project_id, "Everything")
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _received(test_object, BEN)[1] == []

    # A mode the server does not know is refused
    res = testapp.post(
        edit, {"list_filter_mode": "whoever", "change_mode": "1"}, status=200
    )
    assert "FS_error" in res.headers

    # Crowdsourcing has no assistant to serve, so a project is not turned to
    # it while a list serves each assistant their own cases. The switch says
    # so before it is tried, and the project stays as it is
    project_edit = "/user/{}/project/{}/edit".format(login, PROJECT)
    res = testapp.get(project_edit, status=200)
    assert b'id="lists-per-assistant"' in res.body
    assert LIST_FILE.encode() in res.body
    res = testapp.post(project_edit, _project_form(False), status=200)
    assert "FS_error" in res.headers
    assert b"cannot accept data without authentication" in res.body
    assert _requires_authentication(config, project_id)
    # and the page shown again shows the switch as it is: on
    assert re.search(rb'name="project_formlist_auth"[^>]*checked', res.body)

    # Without an assistant there is nobody's cases to serve: a project
    # changed outside FormShare's pages serves the list empty, and refuses
    # the mode
    _set_crowdsourcing(config, project_id, True)
    try:
        assert _received(test_object, None)[1] == []
        # No filter can be given to anyone either
        testapp.get(ana_only, status=404)
        # The page says why, and offers to serve everyone
        res = testapp.get(edit, status=200)
        assert b'id="list-mode-crowdsourcing"' in res.body
        assert b'id="list-mode-to-all"' in res.body
        res = testapp.post(
            edit, {"list_filter_mode": "all", "change_mode": "1"}, status=302
        )
        assert "FS_error" not in res.headers
        res = testapp.post(
            edit, {"list_filter_mode": "submitted_by", "change_mode": "1"}, status=200
        )
        assert "FS_error" in res.headers
        assert b"no assistants to tell apart" in res.body
        res = testapp.get(edit, status=200)
        assert b'id="list-mode-to-all"' not in res.body
    finally:
        _set_crowdsourcing(config, project_id, False)

    # Back in mode all, everyone receives every case again
    assert _received(test_object, BEN) == (all_hash, every_case)

    # Every list serving every case, the project may take public
    # submissions, and go back to assistants
    res = testapp.get(project_edit, status=200)
    assert b'id="lists-per-assistant"' not in res.body
    res = testapp.post(project_edit, _project_form(False), status=302)
    assert "FS_error" not in res.headers
    assert not _requires_authentication(config, project_id)
    res = testapp.post(project_edit, _project_form(True), status=302)
    assert "FS_error" not in res.headers
    assert _requires_authentication(config, project_id)

    # A repository built before stage 8 does not say who a case is assigned
    # to, so a list drawn from it cannot serve the cases assigned to each
    merge = os.path.join(test_object.path, "resources", "forms", "merge")
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {"form_pkey": "numero_de_cedula"},
        status=302,
        upload_files=[("xlsx", os.path.join(merge, "A", "A.xls"))],
    )
    assert "FS_error" not in res.headers
    build_in_process(
        test_object,
        project_id,
        PROJECT,
        OLD_FORM,
        "numero_de_cedula",
        [os.path.join(merge, "A", name) for name in ("cantones.csv", "distritos.csv")],
        assigns_cases=False,
    )
    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, PROJECT),
        {
            "list_id": "old_cases",
            "list_filename": "old_cases.csv",
            "source_form": OLD_FORM,
            "source_table": "maintable",
            "label_column": "numero_de_cedula",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    old_edit = "/user/{}/project/{}/caselists/old_cases/edit".format(login, PROJECT)
    res = testapp.post(
        old_edit, {"list_filter_mode": "assigned_to", "change_mode": "1"}, status=200
    )
    assert "FS_error" in res.headers
    assert b"built before cases could be assigned" in res.body
    # Who registered each case it does say
    res = testapp.post(
        old_edit, {"list_filter_mode": "submitted_by", "change_mode": "1"}, status=302
    )
    assert "FS_error" not in res.headers

    # A case sent with an older version of the form, whose manifest does not
    # map _assigned_to, is assigned to whoever registered it all the same
    manifest = os.path.join(
        config["repository.path"],
        "odk",
        "forms",
        form_row(config, project_id, FORM)["form_directory"],
        "repository",
        "manifest.xml",
    )
    with open(manifest, encoding="utf-8") as a_file:
        current = a_file.read()
    try:
        with open(manifest, "w", encoding="utf-8") as a_file:
            a_file.write(
                "\n".join(
                    line
                    for line in current.split("\n")
                    if 'xmlcode="_assigned_to"' not in line
                )
            )
        # Without the assignment after the load, such a case is nobody's: the
        # load does not store a key its manifest does not map
        from formshare.processes.odk import api as odk_api

        assign = odk_api.assign_case_to_registrar
        odk_api.assign_case_to_registrar = lambda request, schema, rowuuid: False
        try:
            _push(test_object, BEN, 803)
        finally:
            odk_api.assign_case_to_registrar = assign
        assert (BEN, None) in _assigned(config, schema)
        _push(test_object, ANA, 804)
    finally:
        with open(manifest, "w", encoding="utf-8") as a_file:
            a_file.write(current)
    # Ana's first case was given to Ben above, Ben's unassigned one stays
    # unassigned, and Ana's new one is hers
    assert _assigned(config, schema) == [
        (ANA, ANA),
        (ANA, BEN),
        (BEN, None),
        (BEN, BEN),
    ]

    # An edit of a case resolved on the logs page keeps the case's assignee
    # (owner, 2026-10-18). The edit's stamp names its sender, and the case
    # was given to someone else before it was edited. The case is the same
    # because the device minted its identity, which the edit keeps.
    edited = str(uuid.uuid4())
    _push(test_object, ANA, 805, rowuuid=edited)
    assert _assignee(config, schema, edited) == ANA
    _assign(config, schema, edited, BEN)
    before = _logged(config, project_id)
    _push(test_object, ANA, 805, rowuuid=edited)
    edit_ids = _logged(config, project_id) - before
    assert len(edit_ids) == 1, edit_ids
    # Resolved as the logs page resolves it: the submission it edits goes to
    # the logs, and the edit is pushed in its place
    res = testapp.post(
        "/user/{}/project/{}/form/{}/submissions/delete".format(login, PROJECT, FORM),
        {
            "move_submission": "",
            "rowuuid": edited,
            "coll_id": "{}|{}|{}".format(project_id, ANA, uuids[ANA]),
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _assignee(config, schema, edited) is None
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(login, PROJECT),
        {"login": ANA, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/push".format(
            login, PROJECT, FORM, edit_ids.pop()
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(login, PROJECT),
        status=302,
    )
    assert _assignee(config, schema, edited) == BEN

    # A list's stamp is the database's clock, a submission's date FormShare's
    # (2026-10-19). With FormShare two hours behind the database, as
    # production ran (MySQL in CEST, FormShare in UTC), a submission that
    # arrived after a regeneration was dated before its stamp, and the list
    # went without it for two hours. Its date is moved onto the database's
    # clock first now (database_clock_offset), for a form's copy and for a
    # variant alike.
    res = testapp.post(
        edit, {"list_filter_mode": "all", "change_mode": "1"}, status=302
    )
    assert "FS_error" not in res.headers
    with system_timezone(_two_hours_behind_the_database(config)):
        _set_copy(config, project_id, stale)
        _received(test_object, ANA)
        after_the_copy = str(uuid.uuid4())
        _push(test_object, ANA, 808, rowuuid=after_the_copy)
        assert after_the_copy in _received(test_object, ANA)[1]
        res = testapp.post(
            edit, {"list_filter_mode": "submitted_by", "change_mode": "1"}, status=302
        )
        assert "FS_error" not in res.headers
        _received(test_object, ANA)
        after_the_variant = str(uuid.uuid4())
        _push(test_object, ANA, 809, rowuuid=after_the_variant)
        assert after_the_variant in _received(test_object, ANA)[1]
