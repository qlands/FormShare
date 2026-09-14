"""The whole case-management journey, over HTTP, with the real ECCE forms.

Tool 1 registers schools and, in a repeat, their staff roster. Tool 2 is a
follow-up on a single staff member: it selects the school from one published
list and the worker from another, filtered by school. This step drives the
entire path through the web routes:

    upload Tool 1 -> build its repository
    publish two lists (schools from the maintable, roster from the repeat,
        carrying the parent school's rowuuid as school_id)
    upload Tool 2 -> mark which list is the case link
    build Tool 2's repository

and then asserts the schema it produced: Tool 2's maintable is a child of
Tool 1's *roster* (the case link) and of Tool 1's *maintable* (the auxiliary
school reference), both by foreign key to rowuuid, and the case link carries
the _active-aware membership trigger. This is feature 5 -- a follow-up whose
rows hang off a repeat table in another form -- proven end to end.
"""

import os
import time

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details

TOOL1 = "ecce_tool1"
TOOL2 = "ecce_tool2"


def _engine(config):
    return create_engine(config["sqlalchemy.url"], poolclass=NullPool)


def _pick_text_column(config, schema, table):
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s "
            "AND DATA_TYPE IN ('varchar','text','mediumtext') "
            "AND COLUMN_NAME NOT LIKE '\\_%' "
            "AND COLUMN_NAME NOT IN ('rowuuid','instancename','surveyid','originid') "
            "ORDER BY ORDINAL_POSITION",
            (schema, table),
        ).fetchone()
        return r[0] if r else None
    finally:
        engine.dispose()


def _has_table(config, schema, table):
    if not schema:
        return False
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
            (schema, table),
        ).fetchone()
        return r[0] > 0
    finally:
        engine.dispose()


def _wait_for_build(test_object, form_id, timeout=180):
    """Poll until the form's repository maintable exists; return its schema."""
    for _ in range(timeout // 3):
        fd = get_form_details(test_object.server_config, test_object.projectID, form_id)
        schema = fd["form_schema"]
        if _has_table(test_object.server_config, schema, "maintable"):
            return schema
        time.sleep(3)
    return None


def _foreign_keys(config, schema, table):
    engine = _engine(config)
    try:
        rows = engine.execute(
            "SELECT COLUMN_NAME, REFERENCED_TABLE_SCHEMA, REFERENCED_TABLE_NAME, "
            "REFERENCED_COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND REFERENCED_TABLE_NAME IS NOT NULL",
            (schema, table),
        ).fetchall()
        return {r[0]: (r[1], r[2], r[3]) for r in rows}
    finally:
        engine.dispose()


def _column_type(config, schema, table, column):
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
            (schema, table, column),
        ).fetchone()
        return r[0] if r else None
    finally:
        engine.dispose()


def _maintable_membership_trigger(config, schema):
    """The BEFORE INSERT trigger body on maintable that checks a case link."""
    engine = _engine(config)
    try:
        rows = engine.execute(
            "SELECT ACTION_STATEMENT FROM INFORMATION_SCHEMA.TRIGGERS "
            "WHERE EVENT_OBJECT_SCHEMA=%s AND EVENT_OBJECT_TABLE='maintable' "
            "AND EVENT_MANIPULATION='INSERT'",
            (schema,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        engine.dispose()


def _assign_assistant(test_object, form_id):
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, form_id
        ),
        {
            "coll_id": "{}|{}|{}".format(
                test_object.projectID,
                test_object.assistantLogin,
                test_object.assistantLoginUUID,
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )


def t_e_s_t_case_journey(test_object):
    login = test_object.randonLogin
    project = test_object.project
    testapp = test_object.testapp
    resources = os.path.join(test_object.path, *["resources", "forms", "case_journey"])

    # --- Tool 1: the case creator with a staff roster repeat ---------------
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, project),
        {"form_pkey": "consent_form_serial"},
        status=302,
        upload_files=[("xlsx", os.path.join(resources, "tool1.xlsx"))],
    )
    assert "FS_error" not in res.headers
    _assign_assistant(test_object, TOOL1)
    testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(login, project, TOOL1),
        {"form_pkey": "consent_form_serial", "start_stage1": ""},
        status=302,
    )
    schema1 = _wait_for_build(test_object, TOOL1)
    assert schema1 is not None, "Tool 1 repository did not build"
    assert _has_table(test_object.server_config, schema1, "roster"), "no roster table"

    # --- Two published lists from Tool 1 -----------------------------------
    school_label = _pick_text_column(test_object.server_config, schema1, "maintable")
    worker_label = _pick_text_column(test_object.server_config, schema1, "roster")
    assert school_label and worker_label

    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, project),
        {
            "list_id": "centre_lists",
            "list_filename": "centre_lists.csv",
            "source_form": TOOL1,
            "source_table": "maintable",
            "label_column": school_label,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, project),
        {
            "list_id": "roster",
            "list_filename": "roster.csv",
            "source_form": TOOL1,
            "source_table": "roster",
            "label_column": worker_label,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    # The cascade key: the parent school's rowuuid, served as school_id, so a
    # follow-up can filter the roster by the chosen school.
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "roster"),
        {"add_column": "1", "column_name": "root_rowuuid", "column_as": "school_id"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # --- The wizard's JSON endpoints and the sample download ---------------
    res = testapp.get(
        "/user/{}/project/{}/caselists/tablesof/{}".format(login, project, TOOL1),
        status=200,
    )
    tables = [t["table_name"] for t in res.json["tables"]]
    assert "roster" in tables and "maintable" in tables

    res = testapp.get(
        "/user/{}/project/{}/caselists/fieldsof/{}/{}".format(
            login, project, TOOL1, "roster"
        ),
        status=200,
    )
    assert len(res.json["fields"]) > 0

    res = testapp.get(
        "/user/{}/project/{}/caselists/{}/sample".format(login, project, "roster"),
        status=200,
    )
    assert res.body.decode("utf-8").splitlines()[0].startswith('"name","label"')

    # --- Tool 2: the follow-up that consumes both lists --------------------
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, project),
        {"form_pkey": "consent_form_serial"},
        status=302,
        upload_files=[("xlsx", os.path.join(resources, "tool2.xlsx"))],
    )
    assert "FS_error" not in res.headers
    # Attach placeholder media so the form is complete; the registry replaces
    # their content at manifest time.
    for name in ("centre_lists.csv", "roster.csv"):
        placeholder = os.path.join(test_object.working_dir, name)
        with open(placeholder, "w") as a_file:
            a_file.write("name,label\n")
        res = testapp.post(
            "/user/{}/project/{}/form/{}/upload".format(login, project, TOOL2),
            status=302,
            upload_files=[("filetoupload", placeholder)],
        )
        assert "FS_error" not in res.headers
    _assign_assistant(test_object, TOOL2)

    # The case-links page detects both consumers; mark the roster the link.
    res = testapp.get(
        "/user/{}/project/{}/form/{}/caselinks".format(login, project, TOOL2),
        status=200,
    )
    test_object.root.assertIn(b"centre_lists", res.body)
    test_object.root.assertIn(b"roster", res.body)
    res = testapp.post(
        "/user/{}/project/{}/form/{}/caselinks".format(login, project, TOOL2),
        {"case_link": "1", "list_id": "roster"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # --- Build Tool 2: the FKs and the membership trigger are created ------
    testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(login, project, TOOL2),
        {"form_pkey": "consent_form_serial", "start_stage1": ""},
        status=302,
    )
    schema2 = _wait_for_build(test_object, TOOL2)
    assert schema2 is not None, "Tool 2 repository did not build"

    fks = _foreign_keys(test_object.server_config, schema2, "maintable")
    # The case link: worker_id is a child of Tool 1's roster (a repeat table).
    assert fks.get("worker_id") == (schema1, "roster", "rowuuid"), fks
    # The auxiliary: centre_id references Tool 1's maintable.
    assert fks.get("centre_id") == (schema1, "maintable", "rowuuid"), fks
    # The selectors were retyped from int to the rowuuid type.
    assert (
        _column_type(test_object.server_config, schema2, "maintable", "worker_id")
        == "varchar(80)"
    )

    # The case link carries the _active-aware membership trigger.
    triggers = _maintable_membership_trigger(test_object.server_config, schema2)
    membership = [
        t for t in triggers if "roster" in t and "_active" in t and "worker_id" in t
    ]
    assert membership, "no membership trigger on the case link"

    # The delete guard: Tool 1 feeds lists Tool 2 links to, so it cannot be
    # deleted -- the database would refuse it, and so does the app, first.
    res = testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, project, TOOL1),
        status=302,
    )
    assert "FS_error" in res.headers
    # Tool 1 is still there.
    assert _has_table(test_object.server_config, schema1, "maintable")
