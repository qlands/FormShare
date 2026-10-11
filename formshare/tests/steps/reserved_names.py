"""A form whose questions are named after reserved words gets its repository.

jxformtomysql quotes every name since RSTools 2def84d (2026-09-11), so a
question called ``order`` or a repeat called ``index`` is legal. Until
rstools.md 29 (2026-10-11) createaudittriggers did not quote them: the
repository's audit triggers did not load (1064), the build stopped, and such
a form never got a repository.

The step first asks the installed tool whether it quotes -- CI's image may
predate it, and then there is nothing to test -- and then builds such a form,
loads a submission with a row in the repeat, edits the answer called order in
the cleaning interface, and finds the edit in the audit log.
"""

import json
import os
import shutil
import time
import uuid
from subprocess import PIPE, Popen

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details

FORM = "reserved_names"


def _query(config, sql):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return engine.execute(sql).fetchall()
    finally:
        engine.dispose()


def _execute(config, sql):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        engine.execute(sql)
    finally:
        engine.dispose()


def tool_quotes_names(config, work):
    """True when the installed createaudittriggers quotes the names in its
    triggers (rstools.md 29.2), False when it writes them bare. Asks it about
    a scratch table with a column called order."""
    schema = "fs_probe_" + uuid.uuid4().hex[:12]
    out_dir = os.path.join(work, "audit_probe")
    os.makedirs(out_dir, exist_ok=True)
    _execute(config, "CREATE SCHEMA `{}`".format(schema))
    try:
        _execute(
            config,
            "CREATE TABLE `{}`.maintable (rowuuid VARCHAR(80) PRIMARY KEY, "
            "`order` VARCHAR(20), _lastupdate DATETIME)".format(schema),
        )
        process = Popen(
            [
                os.path.join(
                    config["odktools.path"],
                    "utilities",
                    "createAuditTriggers",
                    "createaudittriggers",
                ),
                "-H " + config["mysql.host"],
                "-P " + str(config["mysql.port"]),
                "-u " + config["mysql.user"],
                "-p " + config["mysql.password"],
                "-s " + schema,
                "-o " + out_dir,
                "-t maintable",
            ],
            stdout=PIPE,
            stderr=PIPE,
        )
        process.communicate()
        sql_file = os.path.join(out_dir, "mysql_create_audit.sql")
        if process.returncode != 0 or not os.path.exists(sql_file):
            return False
        with open(sql_file) as a_file:
            return "OLD.`order`" in a_file.read()
    finally:
        _execute(config, "DROP SCHEMA IF EXISTS `{}`".format(schema))
        shutil.rmtree(out_dir, ignore_errors=True)


def _workbook(path):
    wb = openpyxl.Workbook()
    survey = wb.active
    survey.title = "survey"
    survey.append(["type", "name", "label"])
    survey.append(["text", "i_d", "ID"])
    survey.append(["text", "order", "Order"])
    survey.append(["begin_repeat", "index", "Index"])
    survey.append(["integer", "range", "Range"])
    survey.append(["end_repeat", "", ""])
    settings = wb.create_sheet("settings")
    settings.append(["form_title", "form_id", "version"])
    settings.append(["Reserved words as names", FORM, "1"])
    wb.save(path)


def t_e_s_t_reserved_names(test_object):
    login = test_object.randonLogin
    project = test_object.project
    testapp = test_object.testapp
    config = test_object.server_config
    work = os.path.join(test_object.working_dir, "reserved_names")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    if not tool_quotes_names(config, work):
        return

    # --- The form, its repository ------------------------------------------------
    xlsx = os.path.join(work, FORM + ".xlsx")
    _workbook(xlsx)
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, project),
        {"form_pkey": "i_d"},
        status=302,
        upload_files=[("xlsx", xlsx)],
    )
    assert "FS_error" not in res.headers
    testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(login, project, FORM),
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
    testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(login, project, FORM),
        {"form_pkey": "i_d", "start_stage1": ""},
        status=302,
    )
    schema = None
    for _ in range(100):
        schema = get_form_details(config, test_object.projectID, FORM)["form_schema"]
        if (
            schema
            and _query(
                config,
                "SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE "
                "TRIGGER_SCHEMA = '{}' AND EVENT_OBJECT_TABLE = 'index' "
                "AND TRIGGER_NAME LIKE 'audit\\_%'".format(schema),
            )[0][0]
        ):
            break
        time.sleep(3)
    assert schema, "the repository of a form with reserved words as names did not build"

    # --- A submission, with a row in the repeat called index ---------------------
    submission = os.path.join(work, "R1.json")
    with open(submission, "w") as a_file:
        json.dump(
            {
                "_xform_id_string": FORM,
                "i_d": "R1",
                "order": "first",
                "index": [{"index/range": "3"}],
                "meta/instanceID": "uuid:{}".format(uuid.uuid4()),
            },
            a_file,
        )
    res = testapp.post(
        "/user/{}/project/{}/push_json".format(login, project),
        status=201,
        upload_files=[("filetoupload", submission)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert "FS_error" not in res.headers
    main, order = _query(
        config, "SELECT rowuuid, `order` FROM `{}`.maintable".format(schema)
    )[0]
    assert order == "first"
    assert _query(config, "SELECT `range` FROM `{}`.`index`".format(schema)) == [(3,)]

    # --- The answer called order, edited and audited ------------------------------
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(login, project),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/maintable/action".format(
            login, project, FORM
        ),
        {"order": "second", "oper": "edit", "id": main},
        status=200,
    )
    assert "FS_error" not in res.headers
    assert _query(config, "SELECT `order` FROM `{}`.maintable".format(schema)) == [
        ("second",)
    ]
    assert _query(
        config,
        "SELECT audit_oldvalue, audit_newvalue FROM `{}`.audit_log WHERE "
        "audit_action = 'UPDATE' AND audit_column = 'order'".format(schema),
    ) == [("first", "second")]
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(login, project),
        status=302,
    )
    assert "FS_error" not in res.headers
