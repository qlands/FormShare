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
import uuid
from hashlib import md5
from urllib.parse import urlparse

from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

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


def _push(test_object, assistant, primary_key):
    """A submission of the form, sent by the assistant to its repository."""
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
    """Assigns a case to an assistant. By hand for now: how a case is
    reassigned is decided with the rest of stage 8."""
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

    # Without an assistant there is nobody's cases to serve: a project
    # turned to crowdsourcing serves the list empty, and refuses the mode
    _set_crowdsourcing(config, project_id, True)
    try:
        assert _received(test_object, None)[1] == []
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
