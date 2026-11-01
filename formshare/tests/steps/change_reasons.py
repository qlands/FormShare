"""The reason for a change, and the plugins told of a cleaning (2026-11-01).

A person may say why they change answers -- in the cleaning grid, the
multi-select editor or the API -- and FormShare sets it as
@odktools_update_reason beside @odktools_current_user. The repository's audit
triggers record it in audit_log.audit_reason since RSTools f0757d9
(rstools.md 42 and 43). A table whose triggers are older records no reason,
without an error, so FormShare asks a table's own trigger before it asks for a
reason (reason_kept), and regenerate_audit_triggers --all-tables writes such
triggers again.

The installed createaudittriggers decides which branch runs: with one from
before f0757d9 nothing records a reason, nothing asks for one, and the script
refuses to write triggers that would not record it. CI's image may lag.

After a change is stored, the plugins that implement ICleanSubmission hear of
it once per row, with what was written and the reason. A plugin defined here
listens.

Needs the cleaning interface's state: the assistant cleans the form.
"""

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from formshare import plugins as p
from formshare.processes.audit_triggers import (
    audit_log_has_reason,
    reason_kept,
    without_definer,
)
from formshare.scripts.regenerateaudittriggers import main as regenerate_audit_triggers
from .sql import get_form_details


def _query(config, sql, params=None):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        with engine.connect() as connection:
            return connection.exec_driver_sql(sql, params or ()).fetchall()
    finally:
        engine.dispose()


def _kept(config, schema, table="maintable", event="UPDATE"):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        with engine.connect() as connection:
            return reason_kept(connection, schema, table, event)
    finally:
        engine.dispose()


def _has_column(config, schema):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        with engine.connect() as connection:
            return audit_log_has_reason(connection, schema)
    finally:
        engine.dispose()


def _last_change(config, schema, row_uuid, column):
    """(audit_user, audit_newvalue, audit_reason) of the last change of a
    column of a row; the reason is None where audit_log has no column for
    it."""
    reason = "audit_reason" if _has_column(config, schema) else "NULL"
    rows = _query(
        config,
        "SELECT audit_user, audit_newvalue, {} FROM `{}`.audit_log "
        "WHERE audit_action = 'UPDATE' AND audit_key = %s AND audit_column = %s "
        "ORDER BY audit_date DESC LIMIT 1".format(reason, schema),
        (row_uuid, column),
    )
    return tuple(rows[0]) if rows else None


def _audit_without_reason(config, schema):
    """Writes maintable's UPDATE audit trigger as a createaudittriggers from
    before RSTools f0757d9 wrote it: what every older repository keeps until
    its triggers are written again."""
    name = _query(
        config,
        "SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE "
        "TRIGGER_SCHEMA = %s AND EVENT_OBJECT_TABLE = 'maintable' "
        "AND EVENT_MANIPULATION = 'UPDATE' AND ACTION_TIMING = 'AFTER' "
        "AND TRIGGER_NAME LIKE 'audit\\\\_%%'",
        (schema,),
    )[0][0]
    statement = _query(config, "SHOW CREATE TRIGGER `{}`.`{}`".format(schema, name))[0][
        2
    ]
    older = statement.replace(",audit_reason)", ")").replace(
        ",@odktools_update_reason)", ")"
    )
    assert "audit_reason" not in older
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("DROP TRIGGER `{}`.`{}`".format(schema, name))
            connection.exec_driver_sql("USE `{}`".format(schema))
            connection.exec_driver_sql(without_definer(older))
    finally:
        engine.dispose()


def t_e_s_t_change_reasons(test_object):
    config = test_object.server_config
    testapp = test_object.testapp
    login = test_object.randonLogin
    project = test_object.project
    form_id = test_object.formID
    schema = get_form_details(config, test_object.projectID, form_id)["form_schema"]
    row_uuid = _query(config, "SELECT rowuuid FROM `{}`.maintable".format(schema))[0][0]
    clean_page = (
        "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintable".format(
            login, project, form_id
        )
    )
    action = "/user/{}/project/{}/assistantaccess/form/{}/maintable/action".format(
        login, project, form_id
    )
    multiselect = (
        "/user/{}/project/{}/assistantaccess/form/{}/clean/maintable/"
        "multiselect/maintable_msel_crops/{}".format(login, project, form_id, row_uuid)
    )
    crop = _query(
        config,
        "SELECT crop_list_cod FROM `{}`.lkpcrop_list ORDER BY crop_list_cod "
        "LIMIT 1".format(schema),
    )[0][0]

    # What the installed tool wrote decides the branch
    kept = _kept(config, schema)
    assert kept == _kept(config, schema, event="DELETE")
    if kept:
        assert _has_column(config, schema)

    heard = []

    class CleaningListener(p.SingletonPlugin):
        p.implements(p.ICleanSubmission)

        def after_cleaning_submission(
            self, request, user, project, form, table, row_uuid, changes, reason
        ):
            heard.append(
                {
                    "user": user,
                    "project": project,
                    "form": form,
                    "table": table,
                    "row": row_uuid,
                    "changes": changes,
                    "reason": reason,
                }
            )

    try:
        res = testapp.post(
            "/user/{}/project/{}/assistantaccess/login".format(login, project),
            {"login": test_object.assistantLogin, "passwd": "123"},
            status=302,
        )
        assert "FS_error" not in res.headers

        # The grid asks for a reason where the table's trigger records it
        res = testapp.get(clean_page, status=200)
        assert ("Reason for the change" in res.text) == kept

        # --- The grid ---------------------------------------------------------
        res = testapp.post(
            action,
            {
                "landcultivated": "16.000",
                "oper": "edit",
                "id": row_uuid,
                "_reason": "  The officer's typo  ",
            },
            status=200,
        )
        assert "FS_error" not in res.headers
        assert not res.json.get("errors"), res.json
        user, value, reason = _last_change(config, schema, row_uuid, "landcultivated")
        assert value == "16.000"
        assert reason == ("The officer's typo" if kept else None)
        # Once per row, with what was written, as the audit log names who
        assert heard == [
            {
                "user": user,
                "project": test_object.projectID,
                "form": form_id,
                "table": "maintable",
                "row": row_uuid,
                "changes": {"landcultivated": "16.000"},
                "reason": "The officer's typo",
            }
        ]

        # No reason, none recorded
        del heard[:]
        testapp.post(
            action,
            {"landcultivated": "17.000", "oper": "edit", "id": row_uuid},
            status=200,
        )
        assert _last_change(config, schema, row_uuid, "landcultivated")[1:] == (
            "17.000",
            None,
        )
        assert [an_entry["reason"] for an_entry in heard] == [None]

        # A reason past a thousand characters: nothing is written, nobody hears
        del heard[:]
        res = testapp.post(
            action,
            {
                "landcultivated": "18.000",
                "oper": "edit",
                "id": row_uuid,
                "_reason": "x" * 1001,
            },
            status=200,
        )
        assert res.json["errors"][0]["field"] == "Reason"
        assert _last_change(config, schema, row_uuid, "landcultivated")[1] == "17.000"
        assert heard == []

        # A value refused is not heard of; the one stored is
        res = testapp.post(
            action,
            {
                "landcultivated": "19.000",
                "_submitted_by": "nobody",
                "oper": "edit",
                "id": row_uuid,
            },
            status=200,
        )
        assert res.json["errors"][0]["field"] == "_submitted_by"
        assert [an_entry["changes"] for an_entry in heard] == [
            {"landcultivated": "19.000"}
        ]

        # --- The multi-select editor -------------------------------------------
        del heard[:]
        res = testapp.post(
            multiselect, {"to[]": crop, "_reason": "Crops confirmed"}, status=200
        )
        assert res.json["status"] == 200
        assert _last_change(config, schema, row_uuid, "crops")[1:] == (
            crop,
            "Crops confirmed" if kept else None,
        )
        assert heard[0]["changes"] == {"crops": crop}
        assert heard[0]["reason"] == "Crops confirmed"
        del heard[:]
        res = testapp.post(multiselect, {"to[]": crop, "_reason": "y" * 1001})
        assert res.json["status"] == 400
        assert heard == []

        # --- The API -------------------------------------------------------------
        del heard[:]
        res = testapp.post_json(
            "/api_update",
            {
                "apikey": test_object.assistantLoginKey,
                "rowuuid": row_uuid,
                "landcultivated": 20,
                "_reason": "Fixed through the API",
            },
            status=200,
        )
        # The answer says whether the reason was kept
        assert res.json["reason_kept"] == kept
        user, value, reason = _last_change(config, schema, row_uuid, "landcultivated")
        assert float(value) == 20
        assert reason == ("Fixed through the API" if kept else None)
        assert heard == [
            {
                "user": user,
                "project": test_object.projectID,
                "form": form_id,
                "table": "maintable",
                "row": row_uuid,
                "changes": {"landcultivated": 20},
                "reason": "Fixed through the API",
            }
        ]
        # Without a reason the answer is as it was
        res = testapp.post_json(
            "/api_update",
            {
                "apikey": test_object.assistantLoginKey,
                "rowuuid": row_uuid,
                "landcultivated": 21,
            },
            status=200,
        )
        assert "reason_kept" not in res.json
        # Too long: refused, and nothing changes
        del heard[:]
        res = testapp.post_json(
            "/api_update",
            {
                "apikey": test_object.assistantLoginKey,
                "rowuuid": row_uuid,
                "landcultivated": 22,
                "_reason": "z" * 1001,
            },
            status=400,
        )
        assert res.json["error_type"] == "reason_too_long"
        assert float(_last_change(config, schema, row_uuid, "landcultivated")[1]) == 21
        assert heard == []

        # --- Deleting asks too, and refuses a reason too long before anything --
        res = testapp.get(
            "/user/{}/project/{}/form/{}/submissions".format(login, project, form_id),
            status=200,
        )
        assert ("Reason for deleting it" in res.text) == kept
        res = testapp.post(
            "/user/{}/project/{}/form/{}/submissions/delete".format(
                login, project, form_id
            ),
            {"oper": "del", "id": row_uuid, "_reason": "w" * 1001},
            status=400,
        )
        res = testapp.post(
            "/user/{}/project/{}/form/{}/submissions/delete".format(
                login, project, form_id
            ),
            {
                "move_submission": "",
                "rowuuid": row_uuid,
                "coll_id": "||",
                "_reason": "w" * 1001,
            },
            status=302,
        )
        assert "FS_error" in res.headers
        assert _query(
            config,
            "SELECT COUNT(*) FROM `{}`.maintable WHERE rowuuid = %s".format(schema),
            (row_uuid,),
        )[0][0]
        # The audit page shows the reason where audit_log keeps it
        res = testapp.get(
            "/user/{}/project/{}/form/{}/audit".format(login, project, form_id),
            status=200,
        )
        assert ('"Reason"' in res.text) == _has_column(config, schema)
    finally:
        CleaningListener().deactivate()

    # --- A table whose triggers are older ------------------------------------------
    write_again = [
        "--all-tables",
        "--project",
        test_object.projectID,
        "--form",
        form_id,
        config["global:config:file"],
    ]
    if kept:
        _audit_without_reason(config, schema)
        assert not _kept(config, schema)
        # Nothing asks for a reason the table would drop
        res = testapp.get(clean_page, status=200)
        assert "Reason for the change" not in res.text
        # Written again, the table records it, and every other table is left
        assert regenerate_audit_triggers(write_again) == 0
        assert _kept(config, schema)
        testapp.post(
            action,
            {
                "landcultivated": "23.000",
                "oper": "edit",
                "id": row_uuid,
                "_reason": "After the triggers were written again",
            },
            status=200,
        )
        assert _last_change(config, schema, row_uuid, "landcultivated")[2] == (
            "After the triggers were written again"
        )
        # Again: nothing left to write
        assert regenerate_audit_triggers(write_again) == 0
    else:
        # The installed tool would write triggers without the reason: the
        # script says so and changes nothing
        assert regenerate_audit_triggers(write_again) == 1
        assert not _kept(config, schema)
