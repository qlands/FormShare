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

import hashlib
import csv
import io

from lxml import etree
import json
import os
import re
import sqlite3
import time
import uuid
from urllib.parse import urlparse

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


def _one_roster_pair(config, schema):
    """A (worker rowuuid, parent school rowuuid) pair from Tool 1's roster."""
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT rowuuid, root_rowuuid FROM {}.roster "
            "WHERE root_rowuuid IS NOT NULL LIMIT 1".format(schema)
        ).fetchone()
        return (r[0], r[1]) if r else (None, None)
    finally:
        engine.dispose()


def _maintable_count(config, schema):
    engine = _engine(config)
    try:
        return engine.execute(
            "SELECT COUNT(*) FROM {}.maintable".format(schema)
        ).fetchone()[0]
    finally:
        engine.dispose()


def _worker_of(config, schema2, schema1, worker_id):
    """The worker_name reached by joining Tool 2's row to Tool 1's roster."""
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT r.worker_name FROM {}.maintable m "
            "JOIN {}.roster r ON r.rowuuid = m.worker_id "
            "WHERE m.worker_id = %s".format(schema2, schema1),
            (worker_id,),
        ).fetchone()
        return r[0] if r else None
    finally:
        engine.dispose()


def _write_second_school(resources, working_dir):
    """The example Tool 1 submission as a different school in the same
    district: a fresh instance id, a fresh primary key, another name."""
    with io.open(
        os.path.join(resources, "tool1_submission.json"), encoding="utf-8"
    ) as a_file:
        data = json.load(a_file)
    data["_uuid"] = str(uuid.uuid4())
    data["g0_consent/consent_form_serial"] = "second-" + uuid.uuid4().hex[:8]
    data["g1/s1/centre_school"] = "SECOND SCHOOL, SAME DISTRICT"
    out = os.path.join(working_dir, "tool1_second_school.json")
    with io.open(out, "w", encoding="utf-8") as a_file:
        json.dump(data, a_file)
    return out


def _csv_data_rows(body):
    return len([l for l in body.decode("utf-8").splitlines() if l.strip()]) - 1


def _merge_check(config, project_id, form_id):
    """(form_abletomerge, form_mergerrors) -- -1 while the check is pending."""
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT form_abletomerge, form_mergerrors FROM odkform "
            "WHERE project_id=%s AND form_id=%s",
            (project_id, form_id),
        ).fetchone()
        return (r[0], r[1]) if r else (None, None)
    finally:
        engine.dispose()


def _merge_errors_on_page(body):
    """The refusals the form's page shows: a refusal is not stored, only a pass."""
    text = body.decode("utf-8")
    start = text.find("<textarea readonly")
    if start == -1:
        return "no merge errors shown on the page"
    start = text.find(">", start) + 1
    return text[start : text.find("</textarea>", start)].strip()


def _list_edition(config, project_id, list_id):
    """(list_seq, list_lastgen) of a published list: its generated edition."""
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT list_seq, list_lastgen FROM publishedlist "
            "WHERE project_id=%s AND list_id=%s",
            (project_id, list_id),
        ).fetchone()
        return (r[0], r[1]) if r else (None, None)
    finally:
        engine.dispose()


def _copy_stamp(config, project_id, form_id, file_name):
    """file_lastgen of a form's copy of a served list; None = never generated."""
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT file_lastgen FROM mediafile "
            "WHERE project_id=%s AND form_id=%s AND file_name=%s",
            (project_id, form_id, file_name),
        ).fetchone()
        return r[0] if r else None
    finally:
        engine.dispose()


def _pull_manifest(test_object, login, project, form_id):
    """Pull a form's manifest as a device would; returns its body."""
    return test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(login, project, form_id),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    ).body


FS_NS = "https://formshare.org/xforms/extensions"
OPENROSA_MANIFEST = "{http://openrosa.org/xforms/xformsManifest}"
OPENROSA_LIST = "{http://openrosa.org/xforms/xformsList}"


def _manifest_entries(manifest):
    """{filename: (hash, downloadUrl)} of a manifest."""
    root = etree.fromstring(manifest)
    return {
        e.findtext(OPENROSA_MANIFEST + "filename"): (
            e.findtext(OPENROSA_MANIFEST + "hash"),
            e.findtext(OPENROSA_MANIFEST + "downloadUrl"),
        )
        for e in root.findall(OPENROSA_MANIFEST + "mediaFile")
    }


def _form_list(test_object, login, project):
    """{formID: xform element} of the project's formList, as a device sees it."""
    body = test_object.testapp.get(
        "/user/{}/project/{}/formList".format(login, project),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    ).body
    root = etree.fromstring(body)
    return {
        x.findtext(OPENROSA_LIST + "formID"): x
        for x in root.findall(OPENROSA_LIST + "xform")
    }


def _sqlite_table_from_create_xml(db, create_xml, table_name):
    """What the device library does with one table of create.xml: a SQLite
    table with the same columns, types by affinity, no keys, no triggers."""
    root = etree.fromstring(create_xml)
    table = root.find(".//table[@name='{}']".format(table_name))
    assert table is not None, table_name
    affinity = {"int": "INTEGER", "integer": "INTEGER", "decimal": "NUMERIC"}
    columns = []
    for field in table.findall("field"):
        if field.get("generatedas"):
            continue
        columns.append(
            "`{}` {}".format(field.get("name"), affinity.get(field.get("type"), "TEXT"))
        )
    db.execute("CREATE TABLE `{}` ({})".format(table_name, ", ".join(columns)))


def _manifest_hash(manifest, file_name):
    """The md5 the manifest advertises for a file -- what ODK Collect compares
    with its local copy to decide the form has an update."""
    found = re.search(
        r"<filename>{}</filename>\s*<hash>md5:([^<]*)</hash>".format(
            re.escape(file_name)
        ),
        manifest.decode("utf-8"),
    )
    assert found, manifest
    return found.group(1)


def _served_file(test_object, manifest, file_name):
    """Download a manifest entry through its own downloadUrl, as a device."""
    found = re.search(
        r"<filename>{}</filename>\s*<hash>[^<]*</hash>\s*"
        r"<downloadUrl>([^<]*)</downloadUrl>".format(re.escape(file_name)),
        manifest.decode("utf-8"),
    )
    assert found, manifest
    return test_object.testapp.get(
        urlparse(found.group(1)).path,
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    ).body


def _table_count(config, schema, table):
    engine = _engine(config)
    try:
        return engine.execute(
            "SELECT COUNT(*) FROM `{}`.`{}`".format(schema, table)
        ).fetchone()[0]
    finally:
        engine.dispose()


def _scalar(config, sql):
    engine = _engine(config)
    try:
        return engine.execute(sql).fetchone()[0]
    finally:
        engine.dispose()


def _triggers_on(config, schema, table):
    engine = _engine(config)
    try:
        return [
            r[0]
            for r in engine.execute(
                "SELECT trigger_name FROM information_schema.triggers "
                "WHERE trigger_schema=%s AND event_object_table=%s",
                (schema, table),
            ).fetchall()
        ]
    finally:
        engine.dispose()


def _case_link_of(config, project_id, form_id):
    engine = _engine(config)
    try:
        r = engine.execute(
            "SELECT list_id FROM listconsumer WHERE consumer_project=%s "
            "AND consumer_form=%s AND consumer_is_link=1",
            (project_id, form_id),
        ).fetchone()
        return r[0] if r else None
    finally:
        engine.dispose()


def _write_tool2_submission(
    resources, working_dir, centre_id, worker_id, form_id=None, version=None
):
    """Patch the example Tool 2 XML with a chosen case, a fresh id and a fresh
    primary key (consent_form_serial: a reused one is a duplicate row, not a
    second follow-up) -- and, for a merged version, with that version's form
    id and version."""
    with io.open(
        os.path.join(resources, "tool2_submission.xml"), encoding="utf-8"
    ) as a_file:
        xml = a_file.read()
    xml = re.sub(
        r"<centre_id>[^<]*</centre_id>",
        "<centre_id>{}</centre_id>".format(centre_id),
        xml,
    )
    xml = re.sub(
        r"<worker_id>[^<]*</worker_id>",
        "<worker_id>{}</worker_id>".format(worker_id),
        xml,
    )
    xml = re.sub(
        r"<instanceID>[^<]*</instanceID>",
        "<instanceID>uuid:{}</instanceID>".format(uuid.uuid4()),
        xml,
    )
    xml = re.sub(
        r"<consent_form_serial>[^<]*</consent_form_serial>",
        "<consent_form_serial>E4-{}</consent_form_serial>".format(uuid.uuid4().hex[:6]),
        xml,
    )
    if form_id:
        xml = re.sub(r'id="ecce_tool2"', 'id="{}"'.format(form_id), xml, count=1)
    if version:
        xml = re.sub(r'version="[^"]*"', 'version="{}"'.format(version), xml, count=1)
    out = os.path.join(
        working_dir, "tool2_submission_{}.xml".format(uuid.uuid4().hex[:8])
    )
    with io.open(out, "w", encoding="utf-8") as a_file:
        a_file.write(xml)
    return out


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

    # A real submission: one school and its staff roster. The roster rows get
    # server-minted rowuuids, which is what the roster list will serve and what
    # a follow-up will reference.
    res = testapp.post(
        "/user/{}/project/{}/push_json".format(login, project),
        status=201,
        upload_files=[
            (
                "filetoupload",
                os.path.join(resources, "tool1_submission.json"),
            )
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert "FS_error" not in res.headers
    assert (
        _maintable_count(test_object.server_config, schema1) == 1
    ), "school not stored"
    worker_id, centre_id = _one_roster_pair(test_object.server_config, schema1)
    assert worker_id and centre_id, "roster did not populate"

    # A second school in the same district, so a list of districts has
    # something to deduplicate.
    res = testapp.post(
        "/user/{}/project/{}/push_json".format(login, project),
        status=201,
        upload_files=[
            (
                "filetoupload",
                _write_second_school(resources, test_object.working_dir),
            )
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert "FS_error" not in res.headers
    assert _maintable_count(test_object.server_config, schema1) == 2

    # --- Before any list exists, nothing changes on the wire ----------------
    # The mirror artefacts and the fs: elements are served only to projects
    # that publish a list. A project that never does -- a team collecting
    # with stock ODK Collect -- sees no "form updated" and downloads nothing
    # after an upgrade.
    manifest = _pull_manifest(test_object, login, project, TOOL1)
    entries = _manifest_entries(manifest)
    assert not set(entries) & {
        "create.xml",
        "insert.xml",
        "manifest.xml",
        "properties.xml",
        "lists.xml",
    }, entries
    tool1_entry = _form_list(test_object, login, project)[TOOL1]
    assert not [e for e in tool1_entry if e.tag.startswith("{" + FS_NS + "}")]
    testapp.get(
        "/user/{}/project/{}/{}/manifest/repository/create.xml".format(
            login, project, TOOL1
        ),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # --- Two published lists from Tool 1 -----------------------------------
    # No list yet: no Properties button, and the properties page offers no
    # form, since a property belongs only on a table a list draws from.
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, project), status=200
    )
    assert b"caseproperties" not in res.body
    testapp.get(
        "/user/{}/project/{}/caseproperties?form={}".format(login, project, TOOL1),
        status=404,
    )
    school_label = _pick_text_column(test_object.server_config, schema1, "maintable")
    worker_label = _pick_text_column(test_object.server_config, schema1, "roster")
    assert school_label and worker_label

    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, project),
        {
            "list_id": "centre_list",
            "list_filename": "centre_list.csv",
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
    # A served column named after the selector itself, as the tosin roster
    # does (its worker_id column holds the worker's name). This is the shape
    # that, frozen into a lookup table, once caught the link on the wrong
    # field.
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "roster"),
        {"add_column": "1", "column_name": worker_label, "column_as": "worker_id"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # A value list: the districts of the schools, keyed by the district
    # itself. Two schools share one district, so the list serves it once
    # while the school list serves two rows -- name is the district's value,
    # which is what a choice_filter on centre_district compares against.
    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, project),
        {
            "list_id": "district_list",
            "list_filename": "district_list.csv",
            "source_form": TOOL1,
            "source_table": "maintable",
            "label_column": "centre_district",
            "list_key_column": "centre_district",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.get(
        "/user/{}/project/{}/caselists/{}/sample".format(
            login, project, "district_list"
        ),
        status=200,
    )
    assert _csv_data_rows(res.body) == 1, res.body
    res = testapp.get(
        "/user/{}/project/{}/caselists/{}/sample".format(login, project, "centre_list"),
        status=200,
    )
    assert _csv_data_rows(res.body) == 2, res.body

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

    # A form that feeds published lists nobody consumes yet cannot be deleted
    # either: the lists go first. The registry's foreign key on the source
    # would refuse it anyway; the page says so instead of failing.
    res = testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, project, TOOL1),
        status=302,
    )
    assert "FS_error" in res.headers
    assert _has_table(test_object.server_config, schema1, "maintable")

    # --- The device mirror: the build files travel in the manifest ---------
    # A FormShare Collect device builds a SQLite copy of the repository from
    # create.xml, insert.xml and manifest.xml, and its properties tables from
    # properties.xml (formshare.md 3.10). Tool 1 has no media files, so this
    # is also the manifest that used to be empty.
    manifest = _pull_manifest(test_object, login, project, TOOL1)
    entries = _manifest_entries(manifest)
    for name in (
        "create.xml",
        "insert.xml",
        "manifest.xml",
        "properties.xml",
        "lists.xml",
    ):
        assert name in entries and entries[name][0].startswith("md5:"), (name, entries)
    # Tool 1 attaches no list; the three it feeds are the whole of its
    # lists.xml, each in the feeds role (the rules are checked once Tool 2
    # attaches them).
    tool1_lists = etree.fromstring(_served_file(test_object, manifest, "lists.xml"))
    assert {(a.get("id"), a.get("role")) for a in tool1_lists.findall("list")} == {
        ("centre_list", "feeds"),
        ("district_list", "feeds"),
        ("roster", "feeds"),
    }, tool1_lists
    create_xml = _served_file(test_object, manifest, "create.xml")
    assert b"<XMLSchemaStructure" in create_xml and b'name="roster"' in create_xml
    etree.fromstring(_served_file(test_object, manifest, "insert.xml"))
    etree.fromstring(_served_file(test_object, manifest, "manifest.xml"))
    props = _served_file(test_object, manifest, "properties.xml")
    assert b"<tables/>" in props, props
    assert hashlib.md5(props).hexdigest() == entries["properties.xml"][0][len("md5:") :]
    props_hash_before = entries["properties.xml"][0]
    # Only the four names are served through that route.
    testapp.get(
        urlparse(entries["create.xml"][1].replace("create.xml", "drop.sql")).path,
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    # The formList says which mirror the form belongs to and where its
    # geopoints are; the stock elements are untouched.
    tool1_entry = _form_list(test_object, login, project)[TOOL1]
    assert tool1_entry.findtext("{" + FS_NS + "}repository") == schema1
    assert tool1_entry.find("{" + FS_NS + "}parent") is None
    assert tool1_entry.findtext(OPENROSA_LIST + "manifestUrl")
    stored_geopoints = _scalar(
        test_object.server_config,
        "SELECT IFNULL(form_geopoint, '') FROM odkform WHERE project_id = '{}' "
        "AND form_id = '{}'".format(test_object.projectID, TOOL1),
    )
    assert [e.text for e in tool1_entry.findall("{" + FS_NS + "}geopoint")] == [
        g.strip() for g in stored_geopoints.split(",") if g.strip()
    ]

    # --- Properties (feature 2): a typed column beside the roster ----------
    # Defined by a type and a default, born with each row through a trigger,
    # given to the rows that exist, audited like the rest of the schema, and
    # served by any list of the table.
    properties = "/user/{}/project/{}/caseproperties".format(login, project)
    roster_props = properties + "?form={}&table=roster".format(TOOL1)
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, project), status=200
    )
    test_object.root.assertIn(b"caseproperties", res.body)
    testapp.get(properties, status=200)
    res = testapp.get(properties + "?form={}".format(TOOL1), status=200)
    # Tool 1's lists draw from maintable and roster; ext_visits, which no
    # list serves, is not offered and cannot be reached.
    test_object.root.assertIn(b'value="roster"', res.body)
    assert b'value="ext_visits"' not in res.body
    testapp.get(properties + "?form={}&table=ext_visits".format(TOOL1), status=404)
    testapp.get(properties + "?form=no_such_form", status=404)
    res = testapp.get(roster_props, status=200)
    test_object.root.assertIn(b"The server time now is", res.body)
    # A bad name, a column's own name, and a default the type refuses.
    for bad in (
        {
            "property_name": "Bad Name",
            "property_type": "integer",
            "property_default": "",
        },
        {
            "property_name": worker_label,
            "property_type": "integer",
            "property_default": "",
        },
        {
            "property_name": "risk_factor",
            "property_type": "integer",
            "property_default": "AAA",
        },
        {
            "property_name": "next_visit",
            "property_type": "date",
            "property_default": "0",
        },
        {
            "property_name": "next_visit",
            "property_type": "datetime",
            "property_default": "2026-09-17",
        },
        {
            "property_name": "risk_factor",
            "property_type": "nonsense",
            "property_default": "",
        },
    ):
        res = testapp.post(roster_props, dict(bad, add_property="1"), status=302)
        assert "FS_error" in res.headers, bad
    config = test_object.server_config
    assert not _has_table(config, schema1, "roster_properties")
    res = testapp.post(
        roster_props,
        {
            "add_property": "1",
            "property_name": "risk_factor",
            "property_type": "integer",
            "property_default": "0",
            "property_desc": "raised by each follow-up",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _has_table(config, schema1, "roster_properties")
    assert _column_type(config, schema1, "roster_properties", "risk_factor") == "int"
    assert _foreign_keys(config, schema1, "roster_properties").get("rowuuid") == (
        schema1,
        "roster",
        "rowuuid",
    )
    roster_rows = _table_count(config, schema1, "roster")
    assert _table_count(config, schema1, "roster_properties") == roster_rows
    assert (
        _scalar(
            config,
            "SELECT COUNT(*) FROM `{}`.`roster_properties` WHERE risk_factor = 0".format(
                schema1
            ),
        )
        == roster_rows
    ), "the rows that exist did not get the default"
    assert "fs_cm_roster_properties" in _triggers_on(config, schema1, "roster")
    assert [
        t
        for t in _triggers_on(config, schema1, "roster_properties")
        if t.startswith("audit_")
    ], "no audit triggers on the properties table"
    # A second property, a date with no default, joins the same table.
    res = testapp.post(
        roster_props,
        {
            "add_property": "1",
            "property_name": "next_visit",
            "property_type": "date",
            "property_default": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _column_type(config, schema1, "roster_properties", "next_visit") == "date"
    assert (
        _scalar(
            config,
            "SELECT COUNT(*) FROM `{}`.`roster_properties` WHERE next_visit IS NULL".format(
                schema1
            ),
        )
        == roster_rows
    )
    res = testapp.get(roster_props, status=200)
    test_object.root.assertIn(b"risk_factor", res.body)
    test_object.root.assertIn(b"next_visit", res.body)
    # properties.xml now carries the table, with its hash changed in the
    # manifest so the device rebuilds its mirror on the next pull.
    manifest = _pull_manifest(test_object, login, project, TOOL1)
    entries = _manifest_entries(manifest)
    assert entries["properties.xml"][0] != props_hash_before
    props = etree.fromstring(_served_file(test_object, manifest, "properties.xml"))
    (table,) = props.findall("./tables/table")
    assert (
        table.get("name") == "roster_properties" and table.get("properties") == "true"
    )
    fields = {f.get("name"): f for f in table.findall("field")}
    assert fields["rowuuid"].get("key") == "true"
    assert (
        fields["risk_factor"].get("type"),
        fields["risk_factor"].get("default"),
    ) == ("int", "0")
    assert (fields["next_visit"].get("type"), fields["next_visit"].get("default")) == (
        "date",
        None,
    )
    assert "_lastupdate" in fields

    # Served by the roster list once added as a column, at its default.
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "roster"),
        {"add_column": "1", "column_name": "property:risk_factor", "column_as": ""},
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.get(
        "/user/{}/project/{}/caselists/{}/sample".format(login, project, "roster"),
        status=200,
    )
    rows = list(csv.reader(io.StringIO(res.body.decode("utf-8"))))
    assert rows[0][-1] == "risk_factor", rows[0]
    assert len(rows) > 1 and all(r[-1] == "0" for r in rows[1:]), rows

    # Not deletable while a list serves it.
    res = testapp.post(
        roster_props,
        {"delete_property": "1", "property_name": "risk_factor"},
        status=302,
    )
    assert "FS_error" in res.headers
    assert _has_table(config, schema1, "roster_properties")

    # A new school's workers get their property row, at the defaults, from
    # the trigger, and the audit log records the properties table like any
    # other.
    res = testapp.post(
        "/user/{}/project/{}/push_json".format(login, project),
        status=201,
        upload_files=[
            ("filetoupload", _write_second_school(resources, test_object.working_dir))
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert "FS_error" not in res.headers
    assert _table_count(config, schema1, "roster") > roster_rows
    assert _scalar(
        config,
        "SELECT COUNT(*) FROM `{s}`.`roster` r JOIN `{s}`.`roster_properties` p "
        "ON p.rowuuid = r.rowuuid WHERE p.risk_factor = 0 AND p.next_visit IS NULL".format(
            s=schema1
        ),
    ) == _table_count(config, schema1, "roster")
    assert (
        _scalar(
            config,
            "SELECT COUNT(*) FROM `{}`.`audit_log` "
            "WHERE audit_table = 'roster_properties'".format(schema1),
        )
        > 0
    )

    # Removed from the list it can go; the other one keeps the table; with
    # the last property the table and the creation trigger go too.
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "roster"),
        {"remove_column": "1", "column_name": "risk_factor"},
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        roster_props,
        {"delete_property": "1", "property_name": "risk_factor"},
        status=302,
    )
    assert "FS_error" not in res.headers
    assert _has_table(config, schema1, "roster_properties")
    assert _column_type(config, schema1, "roster_properties", "risk_factor") is None
    res = testapp.post(
        roster_props,
        {"delete_property": "1", "property_name": "next_visit"},
        status=302,
    )
    assert "FS_error" not in res.headers
    assert not _has_table(config, schema1, "roster_properties")
    assert "fs_cm_roster_properties" not in _triggers_on(config, schema1, "roster")

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
    for name in ("centre_list.csv", "roster.csv"):
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
    test_object.root.assertIn(b"centre_list", res.body)
    test_object.root.assertIn(b"roster", res.body)
    res = testapp.post(
        "/user/{}/project/{}/form/{}/caselinks".format(login, project, TOOL2),
        {"case_link": "1", "list_id": "roster"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Pull Tool 2's manifest first, as a device would: the placeholders are
    # replaced by the real generated lists, rows and all. Building with those
    # attached is the production path -- and the one where RSTools used to
    # freeze each list into a lookup table and the link landed on it.
    testapp.get(
        "/user/{}/project/{}/{}/manifest".format(login, project, TOOL2),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # No workflow yet: Tool 2 consumes the lists but is not built, so nothing
    # links two schemas and the project page offers no diagram.
    res = testapp.get("/user/{}/project/{}".format(login, project), status=200)
    assert b"Workflow diagram" not in res.body

    # --- lists.xml: the rule behind each list Tool 2 attaches ----------------
    # Tool 2 is still in testing, and a device keeps a scratch mirror of it
    # from the same files: they are served before the build, without an
    # fs:repository. lists.xml names both lists, their source and the SELECT
    # a device runs over its mirror to put a newly registered worker into the
    # SQLite Collect made from roster.csv.
    manifest = _pull_manifest(test_object, login, project, TOOL2)
    entries = _manifest_entries(manifest)
    # All five, before the build: the check keeps manifest.xml since it is
    # told where to put it (rstools.md 10.1), so a scratch mirror can load.
    for name in (
        "create.xml",
        "insert.xml",
        "manifest.xml",
        "properties.xml",
        "lists.xml",
    ):
        assert name in entries, (name, entries)
    etree.fromstring(_served_file(test_object, manifest, "manifest.xml"))
    lists = etree.fromstring(_served_file(test_object, manifest, "lists.xml"))
    by_id = {a_list.get("id"): a_list for a_list in lists.findall("list")}
    assert set(by_id) == {"centre_list", "roster"}, by_id
    roster_rule = by_id["roster"]
    assert (
        roster_rule.get("file"),
        roster_rule.get("kind"),
        roster_rule.get("active"),
    ) == (
        "roster.csv",
        "row",
        "1",
    )
    # Tool 2 attaches both: which field selects from each, and that the
    # roster is its case link -- what its device reads to know which case a
    # follow-up is about (README decision 14).
    assert (
        roster_rule.get("role"),
        roster_rule.get("selector"),
        roster_rule.get("link"),
    ) == (
        "updates",
        "worker_id",
        "true",
    )
    assert (by_id["centre_list"].get("role"), by_id["centre_list"].get("selector")) == (
        "reads",
        "centre_id",
    )
    assert by_id["centre_list"].get("link") == "false"
    # Tool 1 feeds both: its own lists.xml now names them with role feeds,
    # which is what its device runs at finalize.
    tool1_lists = etree.fromstring(
        _served_file(
            test_object, _pull_manifest(test_object, login, project, TOOL1), "lists.xml"
        )
    )
    assert {
        (a.get("id"), a.get("role"), a.get("table"))
        for a in tool1_lists.findall("list")
    } == {
        ("centre_list", "feeds", "maintable"),
        ("district_list", "feeds", "maintable"),
        ("roster", "feeds", "roster"),
    }
    assert {a.get("id"): a.get("kind") for a in tool1_lists.findall("list")}[
        "district_list"
    ] == "value"
    assert all(a.get("selector") is None for a in tool1_lists.findall("list"))
    assert (
        roster_rule.get("repository"),
        roster_rule.get("form"),
        roster_rule.get("table"),
    ) == (
        schema1,
        TOOL1,
        "roster",
    )
    assert roster_rule.get("label") == worker_label
    select = roster_rule.findtext("select")
    assert "{source.roster}" in select and "FS_" not in select
    # The claim the file rests on: a mirror built from the served create.xml,
    # one locally registered worker in it, and the rule's SELECT over it
    # yields a row shaped exactly like the served roster.csv.
    served_roster = csv.reader(
        io.StringIO(_served_file(test_object, manifest, "roster.csv").decode("utf-8"))
    )
    served_header = next(served_roster)
    tool1_create_xml = _served_file(
        test_object, _pull_manifest(test_object, login, project, TOOL1), "create.xml"
    )
    mirror = sqlite3.connect(":memory:")
    _sqlite_table_from_create_xml(mirror, tool1_create_xml, "roster")
    mirror.execute(
        "INSERT INTO `roster` (`rowuuid`, `{}`, `root_rowuuid`, `parent_rowuuid`, "
        "`_active`) VALUES ('local-1', 'Registered offline', 'school-1', 'school-1', 1)".format(
            worker_label
        )
    )
    rows = mirror.execute(
        "SELECT * FROM ({}) WHERE name IN ('local-1')".format(
            select.replace("{source.roster}", "`roster`")
        )
    )
    assert [d[0] for d in rows.description] == served_header, served_header
    (row,) = rows.fetchall()
    assert row[0] == "local-1" and row[1] == "Registered offline"
    assert row[served_header.index("school_id")] == "school-1"
    assert row[served_header.index("worker_id")] == "Registered offline"

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

    # --- The workflow diagram: offered once two schemas are linked ----------
    res = testapp.get("/user/{}/project/{}".format(login, project), status=200)
    test_object.root.assertIn(b"Workflow diagram", res.body)
    res = testapp.get("/user/{}/project/{}/workflow".format(login, project), status=200)
    test_object.root.assertIn(b"jsplumb.min.js", res.body)
    test_object.root.assertIn(b"worker_id", res.body)
    # Kept on disk so the drawing can be looked at after the run.
    with open(
        os.path.join(test_object.working_dir, "workflow_page.html"), "wb"
    ) as page:
        page.write(res.body)
    res = testapp.get(
        "/user/{}/project/{}/workflow/model".format(login, project), status=200
    )
    model = res.json
    ranks = {f["id"]: f["rank"] for f in model["forms"]}
    assert ranks[TOOL1] == 0 and ranks[TOOL2] == 1, ranks
    link_edges = [e for e in model["edges"] if e["kind"] == "link"]
    assert [e["to"]["field"] for e in link_edges] == ["worker_id"], link_edges
    assert "must be _active" in link_edges[0]["label"], link_edges[0]["label"]
    assert {l["id"]: l["rank"] for l in model["lists"]}["roster"] == 0.5
    # The auxiliary: centre_id references Tool 1's maintable.
    assert fks.get("centre_id") == (schema1, "maintable", "rowuuid"), fks
    # The selectors were retyped from int to the rowuuid type.
    assert (
        _column_type(test_object.server_config, schema2, "maintable", "worker_id")
        == "varchar(80)"
    )

    # No list was frozen into a lookup table: the build handed RSTools
    # header-only copies of the registry-served files.
    assert not _has_table(test_object.server_config, schema2, "lkpworker_id")
    assert not _has_table(test_object.server_config, schema2, "lkpcentre_id")

    # The case link carries the _active-aware membership trigger.
    triggers = _maintable_membership_trigger(test_object.server_config, schema2)
    membership = [
        t for t in triggers if "roster" in t and "_active" in t and "worker_id" in t
    ]
    assert membership, "no membership trigger on the case link"

    # A real follow-up on a worker that exists: it stores and joins back to
    # the roster row Tool 1 created.
    before = _maintable_count(test_object.server_config, schema2)
    valid = _write_tool2_submission(
        resources, test_object.working_dir, centre_id, worker_id
    )
    res = testapp.post(
        "/user/{}/project/{}/push".format(login, project),
        status=201,
        upload_files=[("filetoupload", valid)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert "FS_error" not in res.headers
    assert _maintable_count(test_object.server_config, schema2) == before + 1
    assert (
        _worker_of(test_object.server_config, schema2, schema1, worker_id) is not None
    ), "the follow-up did not join back to the roster"

    # A follow-up on a worker that does not exist: the membership trigger
    # refuses it, so no row is stored. (The push may report any status; what
    # matters is that the row never lands.)
    after_valid = _maintable_count(test_object.server_config, schema2)
    bogus = _write_tool2_submission(
        resources, test_object.working_dir, centre_id, str(uuid.uuid4())
    )
    testapp.post(
        "/user/{}/project/{}/push".format(login, project),
        status="*",
        upload_files=[("filetoupload", bogus)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert (
        _maintable_count(test_object.server_config, schema2) == after_valid
    ), "a follow-up on a non-existent worker was stored"

    # --- A column added to a list reaches the devices -----------------------
    # A form's copy is regenerated at manifest time only when stale, and stale
    # is decided against the source's data; a change to the list's own
    # definition did not count, so a column added after deployment was served
    # only once Tool 1 got new data. The edit view now clears the copies'
    # generation stamp, which the gate reads as "never generated".
    roster_seq, roster_gen = _list_edition(
        test_object.server_config, test_object.projectID, "roster"
    )
    assert roster_seq >= 1 and roster_gen is not None
    # Nothing changed: a pull leaves the edition, the stamp and the hash alone.
    manifest = _pull_manifest(test_object, login, project, TOOL2)
    roster_hash = _manifest_hash(manifest, "roster.csv")
    assert _list_edition(
        test_object.server_config, test_object.projectID, "roster"
    ) == (roster_seq, roster_gen)
    assert (
        _copy_stamp(
            test_object.server_config, test_object.projectID, TOOL2, "roster.csv"
        )
        is not None
    )
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "roster"),
        {"add_column": "1", "column_name": "rowuuid", "column_as": "worker_uuid"},
        status=302,
    )
    assert "FS_error" not in res.headers
    # The edit marks the copies stale; the list's own edition moves only when
    # a copy is actually generated, on the next pull.
    assert _list_edition(
        test_object.server_config, test_object.projectID, "roster"
    ) == (roster_seq, roster_gen)
    assert (
        _copy_stamp(
            test_object.server_config, test_object.projectID, TOOL2, "roster.csv"
        )
        is None
    )
    manifest = _pull_manifest(test_object, login, project, TOOL2)
    assert (
        _list_edition(test_object.server_config, test_object.projectID, "roster")[0]
        == roster_seq + 1
    )
    assert (
        _copy_stamp(
            test_object.server_config, test_object.projectID, TOOL2, "roster.csv"
        )
        is not None
    )
    served = _served_file(test_object, manifest, "roster.csv")
    header = served.decode("utf-8").splitlines()[0]
    assert "worker_uuid" in header, header
    assert _csv_data_rows(served) >= 1, served
    # The same pull advertises the new hash -- ODK Collect flags a form as
    # updated when a manifest hash differs from its local file -- and it is
    # the hash of what the device then downloads.
    new_hash = _manifest_hash(manifest, "roster.csv")
    assert new_hash != roster_hash, "the manifest kept the old hash"
    assert new_hash == hashlib.md5(served).hexdigest()
    # A further pull with nothing changed keeps that hash and the edition.
    again = _pull_manifest(test_object, login, project, TOOL2)
    assert _manifest_hash(again, "roster.csv") == new_hash
    assert (
        _list_edition(test_object.server_config, test_object.projectID, "roster")[0]
        == roster_seq + 1
    )

    # A published list a built form consumes cannot be deleted: the foreign
    # key and membership trigger depend on its source. The route refuses it
    # (404) and the list stays.
    testapp.post(
        "/user/{}/project/{}/caselists/{}/delete".format(login, project, "roster"),
        status=404,
    )
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, project), status=200
    )
    test_object.root.assertIn(b"roster.csv", res.body)

    # The delete guard: Tool 1 feeds lists Tool 2 links to, so it cannot be
    # deleted -- the database would refuse it, and so does the app, first.
    res = testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, project, TOOL1),
        status=302,
    )
    assert "FS_error" in res.headers
    # Tool 1 is still there.
    assert _has_table(test_object.server_config, schema1, "maintable")

    # The published-lists workflow is for non-case projects only. On a classic
    # case project (project_case = 1) every registry route is 404.
    classic = "journey_classic"
    res = testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": str(uuid.uuid4()),
            "project_code": classic,
            "project_name": "Classic case project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_case": "1",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    testapp.get("/user/{}/project/{}/caselists".format(login, classic), status=404)
    testapp.get("/user/{}/project/{}/caselists/add".format(login, classic), status=404)
    testapp.get("/user/{}/project/{}/workflow".format(login, classic), status=404)
    testapp.get(
        "/user/{}/project/{}/caselists/tablesof/{}".format(login, classic, TOOL1),
        status=404,
    )

    # --- A new version of Tool 2 is merged: it keeps its parent's links -----
    tool2_v6 = "ecce_tool2_v6"
    res = testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(login, project, TOOL2),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": TOOL2,
        },
        status=302,
        upload_files=[("xlsx", os.path.join(resources, "tool2_v6.xlsx"))],
    )
    assert "FS_error" not in res.headers
    for name in ("centre_list.csv", "roster.csv"):
        placeholder = os.path.join(test_object.working_dir, name)
        with open(placeholder, "w") as a_file:
            a_file.write("name,label\n")
        res = testapp.post(
            "/user/{}/project/{}/form/{}/upload".format(login, project, tool2_v6),
            status=302,
            upload_files=[("filetoupload", placeholder)],
        )
        assert "FS_error" not in res.headers
    _assign_assistant(test_object, tool2_v6)
    # In testing, the new version tells the device which form it will merge
    # into and has no repository of its own yet.
    v6_entry = _form_list(test_object, login, project)[tool2_v6]
    assert v6_entry.findtext("{" + FS_NS + "}parent") == TOOL2
    assert v6_entry.find("{" + FS_NS + "}repository") is None

    # The new version inherited the links and cannot change them: roster is
    # the case link, the page is read-only, a POST is refused.
    assert (
        _case_link_of(test_object.server_config, test_object.projectID, tool2_v6)
        == "roster"
    )
    res = testapp.get(
        "/user/{}/project/{}/form/{}/caselinks".format(login, project, tool2_v6),
        status=200,
    )
    test_object.root.assertIn(b"roster", res.body)
    test_object.root.assertIn(b"keeps that version", res.body)
    assert b'type="radio"' not in res.body
    res = testapp.post(
        "/user/{}/project/{}/form/{}/caselinks".format(login, project, tool2_v6),
        {"case_link": "1", "list_id": "centre_list"},
        status=200,
    )
    assert (
        _case_link_of(test_object.server_config, test_object.projectID, tool2_v6)
        == "roster"
    )

    # The merge check runs, synchronously, when the new version's page is
    # viewed with all its files in place: it re-runs jxformtomysql on the new
    # version, gives that create.xml the parent's links (link_merge_child) and
    # compares the two. A pass is stored as form_abletomerge = 1; a refusal is
    # only shown on the page, so read it from there.
    res = testapp.get(
        "/user/{}/project/{}/form/{}".format(login, project, tool2_v6), status=200
    )
    verdict, _unused = _merge_check(
        test_object.server_config, test_object.projectID, tool2_v6
    )
    assert int(verdict) == 1, "merge check refused v6: {}".format(
        _merge_errors_on_page(res.body)
    )

    # Merge it. The child's create.xml gets the same links before
    # mergeversions compares it with the parent's.
    testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            login, project, tool2_v6, TOOL2
        ),
        status=200,
    )
    res = testapp.post(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            login, project, tool2_v6, TOOL2
        ),
        {"discard_testing_data": ""},
        status=302,
    )
    assert "FS_error" not in res.headers
    merged_schema = None
    for _ in range(60):
        fd = get_form_details(
            test_object.server_config, test_object.projectID, tool2_v6
        )
        if fd["form_schema"] == schema2:
            merged_schema = fd["form_schema"]
            break
        time.sleep(3)
    assert (
        merged_schema == schema2
    ), "the merge did not hand the schema to the new version"
    # Merged, it belongs to the repository it merged into: the device keeps
    # one mirror for both versions.
    v6_entry = _form_list(test_object, login, project)[tool2_v6]
    assert v6_entry.findtext("{" + FS_NS + "}repository") == schema2
    assert v6_entry.find("{" + FS_NS + "}parent") is None

    # The links survived the merge, on the schema the new version now owns.
    fks = _foreign_keys(test_object.server_config, schema2, "maintable")
    assert fks.get("worker_id") == (schema1, "roster", "rowuuid"), fks
    assert fks.get("centre_id") == (schema1, "maintable", "rowuuid"), fks
    assert [
        t
        for t in _maintable_membership_trigger(test_object.server_config, schema2)
        if "roster" in t and "_active" in t and "worker_id" in t
    ], "the membership trigger did not survive the merge"
    assert (
        _case_link_of(test_object.server_config, test_object.projectID, tool2_v6)
        == "roster"
    )

    # And the merged version takes a follow-up on a real worker, through the
    # same trigger.
    before = _maintable_count(test_object.server_config, schema2)
    merged_submission = _write_tool2_submission(
        resources,
        test_object.working_dir,
        centre_id,
        worker_id,
        form_id=tool2_v6,
        version="20260915v6",
    )
    res = testapp.post(
        "/user/{}/project/{}/push".format(login, project),
        status=201,
        upload_files=[("filetoupload", merged_submission)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert "FS_error" not in res.headers
    assert _maintable_count(test_object.server_config, schema2) == before + 1
