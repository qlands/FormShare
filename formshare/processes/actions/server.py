"""The server side of a run: the input from the repository, the writes into
it, the record of what happened (actions-api.md; formshare.md section 3.3).

``run_for_submission`` is the one entry point: called by ``store_json_file``
and ``push_revision`` right after JSONToMySQL returned 0, by the logs page
for a retry, and by the actions screen for a dry run. It assembles the
input from the repository (typed as the contract says), runs the module in
the QuickJS host, turns the writes into the change report, validates each
write against the type of its target, applies them in one transaction with
the audit user set -- or, for a dry run, applies nothing -- and records the
run. A failure after a successful load never reaches the submission: it is
recorded and shown beside the load errors, with a retry.

What the module reads is what the mirror holds too (actions-api.md
section 4), which is what keeps the device run equal to this one.
"""

import datetime
import decimal
import json
import logging
import os
import re
import uuid

from sqlalchemy import text

from formshare.models import ActionRun, DictField, DictTable, map_from_schema
from formshare.processes.actions.host import (
    BINARY,
    ModuleError,
    changes_of,
    lookups_named,
    run_module,
    writes_from_changes,
)
from formshare.processes.db.actions import (
    CONTROL_COLUMNS,
    case_source_of,
    get_action_module,
    js_type_of,
)
from formshare.processes.db.case_management import (
    get_table_properties,
    validate_property_default,
)

__all__ = [
    "run_for_submission",
    "run_after_load",
    "retry_run",
    "build_input",
    "get_form_runs",
    "get_run",
    "main_rowuuid_of",
    "render",
]

log = logging.getLogger("formshare")

_MSEL = re.compile(r"_msel_")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _q(name):
    if not _IDENT.match(name or ""):
        raise ModuleError("Not an identifier: {}".format(name))
    return "`" + name + "`"


# ---------------------------------------------------------------------------
# Typing (actions-api.md section 6)
# ---------------------------------------------------------------------------


def typed(value, js_type):
    """A repository value as the module sees it."""
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if js_type == "integer":
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    if js_type == "double":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if js_type == "date":
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime("%Y-%m-%d")
        return str(value)[:10]
    if js_type == "datetime":
        if isinstance(value, datetime.datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat(sep=" ")
    if isinstance(value, decimal.Decimal):
        return float(value)
    return str(value)


def render(value):
    """A value as JavaScript's String() spells it, for the change report:
    whole numbers without a decimal point, NULL as None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, (float, decimal.Decimal)):
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return repr(number)
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


# ---------------------------------------------------------------------------
# The dictionary
# ---------------------------------------------------------------------------


def _tables(request, project_id, form_id):
    res = (
        request.dbsession.query(DictTable)
        .filter(DictTable.project_id == project_id)
        .filter(DictTable.form_id == form_id)
        .order_by(DictTable.table_index)
        .all()
    )
    return map_from_schema(res)


def _fields(request, project_id, form_id, table_name):
    res = (
        request.dbsession.query(DictField)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.table_name == table_name)
        .all()
    )
    return map_from_schema(res)


def _types_of(request, project_id, form_id, table_name):
    """{column: js type} for a table, and the multi-select variables."""
    types = {}
    multi = []
    for a_field in _fields(request, project_id, form_id, table_name):
        name = a_field["field_name"]
        odk_type = (a_field.get("field_odktype") or "").lower()
        if odk_type == "select all that apply":
            multi.append(name)
            types[name] = "string"
        else:
            types[name] = js_type_of(a_field.get("field_type"), odk_type)
    return types, multi


def _rows(request, sql, **params):
    result = request.dbsession.execute(text(sql), params)
    keys = list(result.keys())
    return [dict(zip(keys, row)) for row in result.fetchall()]


def _row_values(row, types, keep_control=False):
    values = {}
    for column, value in row.items():
        if not keep_control and (
            column in CONTROL_COLUMNS or column.endswith("_rowid")
        ):
            continue
        values[column] = typed(value, types.get(column, "string"))
    return values


# ---------------------------------------------------------------------------
# The input
# ---------------------------------------------------------------------------


def main_rowuuid_of(uuid_file):
    """The main row's rowuuid from the file JSONToMySQL writes (-U): one
    ``table,rowuuid`` line per row, the main table's first."""
    try:
        with open(uuid_file) as a_file:
            for line in a_file:
                parts = line.strip().split(",")
                if len(parts) >= 2 and parts[0] == "maintable":
                    return parts[1]
    except OSError:
        return None
    return None


def _selections(request, schema, msel_tables, root_rowuuid):
    """{parent_rowuuid: {variable: [codes]}} for every msel table of the
    submission."""
    out = {}
    for a_table, variable in msel_tables:
        for row in _rows(
            request,
            "SELECT parent_rowuuid, {} AS code FROM {}.{} WHERE root_rowuuid = :r".format(
                _q(variable), _q(schema), _q(a_table)
            ),
            r=root_rowuuid,
        ):
            out.setdefault(row["parent_rowuuid"], {}).setdefault(variable, []).append(
                "" if row["code"] is None else str(row["code"])
            )
    return out


def _submission_input(request, project_id, form_id, schema, main_rowuuid):
    tables = _tables(request, project_id, form_id)
    by_name = {t["table_name"]: t for t in tables}
    main_types, main_multi = _types_of(request, project_id, form_id, "maintable")
    main_rows = _rows(
        request,
        "SELECT * FROM {}.maintable WHERE rowuuid = :r".format(_q(schema)),
        r=main_rowuuid,
    )
    if not main_rows:
        raise ModuleError(
            "The submission's row {} is not in the repository".format(main_rowuuid)
        )
    main = main_rows[0]

    msel_tables = []
    repeat_tables = []
    for a_table in tables:
        name = a_table["table_name"]
        if name == "maintable" or a_table.get("table_lkp"):
            continue
        if _MSEL.search(name):
            variable = name.split("_msel_", 1)[1]
            msel_tables.append((name, variable))
        elif a_table.get("parent_table"):
            repeat_tables.append(a_table)
    selections = _selections(request, schema, msel_tables, main_rowuuid)

    # Every repeat row of the submission, typed, keyed by its parent.
    children = {}
    for a_table in repeat_tables:
        name = a_table["table_name"]
        types, _multi = _types_of(request, project_id, form_id, name)
        for row in _rows(
            request,
            "SELECT * FROM {}.{} WHERE root_rowuuid = :r ORDER BY {}".format(
                _q(schema), _q(name), _q(name + "_rowid")
            ),
            r=main_rowuuid,
        ):
            entry = {
                "rowuuid": row.get("rowuuid"),
                "parent_rowuuid": row.get("parent_rowuuid"),
                "values": _row_values(row, types),
                "repeats": {},
                "selections": selections.get(row.get("rowuuid"), {}),
            }
            children.setdefault((name, row.get("parent_rowuuid")), []).append(entry)

    def attach(node, table_name):
        for a_table in repeat_tables:
            if a_table.get("parent_table") == table_name:
                rows = children.get((a_table["table_name"], node["rowuuid"]), [])
                for a_row in rows:
                    attach(a_row, a_table["table_name"])
                node["repeats"][a_table["table_name"]] = rows

    submission = {
        "rowuuid": main_rowuuid,
        "parent_rowuuid": None,
        "values": _row_values(main, main_types),
        "repeats": {},
        "selections": selections.get(main_rowuuid, {}),
        "submitted_by": main.get("_submitted_by"),
        "submitted_date": render(main.get("_submitted_date")),
    }
    attach(submission, "maintable")
    return submission, main


def _case_row(request, source, table_name, rowuuid):
    """A row of the source repository with its properties, as the module's
    case object, or None."""
    rows = _rows(
        request,
        "SELECT * FROM {}.{} WHERE rowuuid = :r".format(
            _q(source["schema"]), _q(table_name)
        ),
        r=rowuuid,
    )
    if not rows:
        return None
    row = rows[0]
    types, _multi = _types_of(request, source["project"], source["form"], table_name)
    properties = {}
    defined = get_table_properties(
        request, source["project"], source["form"], table_name
    )
    if defined:
        prop_types = {p["property_name"]: p["property_type"] for p in defined}
        prop_rows = _rows(
            request,
            "SELECT * FROM {}.{} WHERE rowuuid = :r".format(
                _q(source["schema"]), _q(table_name + "_properties")
            ),
            r=rowuuid,
        )
        prop_row = prop_rows[0] if prop_rows else {}
        for name, ptype in prop_types.items():
            properties[name] = typed(
                prop_row.get(name),
                {
                    "integer": "integer",
                    "decimal": "double",
                    "date": "date",
                    "datetime": "datetime",
                }.get(ptype, "string"),
            )
    active = row.get("_active")
    return {
        "table": table_name,
        "rowuuid": rowuuid,
        "active": True if active is None else int(active) == 1,
        "values": _row_values(row, types),
        "properties": properties,
        "parent_rowuuid": row.get("parent_rowuuid"),
        "parent": None,
    }


def _case_input(request, source, main):
    if source is None:
        return None
    selector = main.get(source["selector_field"])
    if selector is None or str(selector) == "":
        return None
    case = _case_row(request, source, source["table"], str(selector))
    if case is None:
        return None
    if source.get("parent_table") and case.get("parent_rowuuid"):
        case["parent"] = _case_row(
            request, source, source["parent_table"], case["parent_rowuuid"]
        )
        if case["parent"] is not None:
            case["parent"].pop("parent_rowuuid", None)
    case.pop("parent_rowuuid", None)
    return case


def _lookup_tables(request, module, schemas):
    """{list: {code: row}} for every list the module names, read from the
    first schema of ``schemas`` that has the table."""
    out = {}
    for name in lookups_named(module):
        if not _IDENT.match(name):
            continue
        for schema in schemas:
            if not schema:
                continue
            try:
                rows = _rows(
                    request,
                    "SELECT * FROM {}.{}".format(_q(schema), _q("lkp" + name)),
                )
            except Exception:
                request.dbsession.rollback()
                continue
            code_column = name + "_cod"
            table = {}
            for row in rows:
                code = row.get(code_column)
                if code is None:
                    continue
                table[str(code)] = {
                    k: (
                        render(v)
                        if isinstance(v, (datetime.date, datetime.datetime))
                        else (float(v) if isinstance(v, decimal.Decimal) else v)
                    )
                    for k, v in row.items()
                    if k != "rowuuid"
                }
            out[name] = table
            break
    return out


def build_input(
    request, project_id, form_id, schema, main_rowuuid, module, user, now=None
):
    """The input of a run, assembled from the repository."""
    submission, main = _submission_input(
        request, project_id, form_id, schema, main_rowuuid
    )
    source = case_source_of(request, project_id, form_id)
    case = _case_input(request, source, main)
    lookups = _lookup_tables(
        request, module, [schema, source["schema"] if source else None]
    )
    return {
        "submission": submission,
        "case": case,
        "lookups": lookups,
        "now": now or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "_source": source,
    }


# ---------------------------------------------------------------------------
# The writes
# ---------------------------------------------------------------------------


def _validate_column(field, value):
    """A column value checked against its dictionary type; returns the value
    to store or raises ModuleError."""
    if value is None:
        return None
    js_type = js_type_of(field.get("field_type"), field.get("field_odktype"))
    name = field["field_name"]
    if js_type == "integer":
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ModuleError(
                "{} is not a whole number for column {}".format(value, name)
            )
        if not number.is_integer():
            raise ModuleError(
                "{} is not a whole number for column {}".format(value, name)
            )
        return int(number)
    if js_type == "double":
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ModuleError("{} is not a number for column {}".format(value, name))
        return round(number, int(field.get("field_decsize") or 0) or 3)
    if js_type == "date":
        ok, normalised, message = validate_property_default("date", str(value))
        if not ok:
            raise ModuleError("{} for column {}".format(message, name))
        return normalised
    if js_type == "datetime":
        ok, normalised, message = validate_property_default("datetime", str(value))
        if not ok:
            raise ModuleError("{} for column {}".format(message, name))
        return normalised
    text_value = str(value)
    size = int(field.get("field_size") or 0)
    if (
        (field.get("field_type") or "").lower().startswith("varchar")
        and size
        and len(text_value) > size
    ):
        raise ModuleError(
            "{} is longer than the {} characters column {} holds".format(
                text_value, size, name
            )
        )
    return text_value


def _validate_property(property_type, value, name):
    if value is None:
        return None
    if isinstance(value, bool):
        value = 1 if value else 0
    if isinstance(value, float) and value.is_integer() and property_type == "integer":
        value = int(value)
    ok, normalised, message = validate_property_default(property_type, str(value))
    if not ok:
        raise ModuleError("{} for property {}".format(message, name))
    return normalised


def _plan_writes(request, source, case, writes):
    """Every write validated, as (table, rowuuid, column, value) with the
    last write to a name winning. Raises ModuleError; nothing is applied."""
    last = {}
    for write in writes:
        scope = write.get("scope", "case")
        key = (scope, "_active" if write.get("kind") == "active" else write.get("name"))
        last[key] = write
    plan = []
    for (scope, name), write in last.items():
        target = case if scope == "case" else (case or {}).get("parent")
        if target is None:
            raise ModuleError(
                "The module wrote to the case's parent and it has none"
                if scope == "parent"
                else "The module wrote to a case the form does not have"
            )
        table = target["table"]
        if write.get("kind") == "active":
            value = int(write.get("value"))
            if value not in (0, 1):
                raise ModuleError("_active takes 0 or 1")
            plan.append((table, target["rowuuid"], "_active", value))
            continue
        properties = {
            p["property_name"]: p["property_type"]
            for p in get_table_properties(
                request, source["project"], source["form"], table
            )
        }
        if name in properties:
            plan.append(
                (
                    table + "_properties",
                    target["rowuuid"],
                    name,
                    _validate_property(properties[name], write.get("value"), name),
                )
            )
            continue
        fields = {
            f["field_name"]: f
            for f in _fields(request, source["project"], source["form"], table)
        }
        if (
            name in fields
            and name not in CONTROL_COLUMNS
            and not name.endswith("_rowid")
        ):
            plan.append(
                (
                    table,
                    target["rowuuid"],
                    name,
                    _validate_column(fields[name], write.get("value")),
                )
            )
            continue
        raise ModuleError(
            "{} is neither a property nor a column of {}".format(name, table)
        )
    return plan


def _apply(request, schema, plan, user):
    """The writes, in one transaction, audited as the assistant."""
    request.dbsession.execute(text("SET @odktools_current_user = :u"), {"u": user})
    for table, rowuuid, column, value in plan:
        request.dbsession.execute(
            text(
                "UPDATE {}.{} SET {} = :v WHERE rowuuid = :r".format(
                    _q(schema), _q(table), _q(column)
                )
            ),
            {"v": value, "r": rowuuid},
        )
    request.dbsession.commit()


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


def _record(
    request,
    project_id,
    form_id,
    submission_id,
    main_rowuuid,
    status,
    message,
    changes,
    log_lines,
    run_id=None,
):
    try:
        if run_id is not None:
            request.dbsession.query(ActionRun).filter(
                ActionRun.run_id == run_id
            ).update(
                {
                    "run_dtime": datetime.datetime.now(),
                    "run_status": status,
                    "run_message": message,
                    "run_changes": json.dumps(changes),
                    "run_log": json.dumps(log_lines),
                }
            )
        else:
            run_id = str(uuid.uuid4())
            request.dbsession.add(
                ActionRun(
                    run_id=run_id,
                    project_id=project_id,
                    form_id=form_id,
                    submission_id=submission_id,
                    main_rowuuid=main_rowuuid,
                    run_dtime=datetime.datetime.now(),
                    run_status=status,
                    run_message=message,
                    run_changes=json.dumps(changes),
                    run_log=json.dumps(log_lines),
                )
            )
        request.dbsession.commit()
    except Exception as e:  # pragma: no cover
        request.dbsession.rollback()
        log.error(
            "The action run of {} could not be recorded: {}".format(main_rowuuid, e)
        )
    return run_id


def get_form_runs(request, project_id, form_id, status=None, limit=200):
    query = (
        request.dbsession.query(ActionRun)
        .filter(ActionRun.project_id == project_id)
        .filter(ActionRun.form_id == form_id)
    )
    if status is not None:
        query = query.filter(ActionRun.run_status == status)
    res = query.order_by(ActionRun.run_dtime.desc()).limit(limit).all()
    runs = map_from_schema(res)
    for a_run in runs:
        for key in ("run_changes", "run_log"):
            try:
                a_run[key] = json.loads(a_run.get(key) or "[]")
            except ValueError:
                a_run[key] = []
    return runs


def get_run(request, run_id):
    res = request.dbsession.query(ActionRun).filter(ActionRun.run_id == run_id).first()
    return map_from_schema(res) if res is not None else None


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def engine_path(request):
    """RSTools' runactions binary under odktools.path, or None while it is
    not installed, in which case the in-process engine runs."""
    tools = request.registry.settings.get("odktools.path", "")
    if not tools:
        return None
    path = os.path.join(tools, BINARY)
    return path if os.path.exists(path) else None


def run_for_submission(
    request,
    project_id,
    form_id,
    schema,
    main_rowuuid,
    submission_id,
    user,
    dry_run=False,
    module=None,
    run_id=None,
):
    """Runs the form's module for one loaded submission.

    Returns {"ok", "skipped", "changes", "log", "error", "run_id"}. A real
    run applies the writes and records itself; a dry run applies nothing
    and records nothing. ``module`` overrides the form's stored module, for
    testing unsaved code. ``run_id`` names an earlier failed run to update.
    """
    if module is None:
        module = get_action_module(request, project_id, form_id)
    if module is None or module.strip() == "":
        return {
            "ok": True,
            "skipped": True,
            "changes": [],
            "log": [],
            "error": None,
            "run_id": None,
        }
    try:
        inputs = build_input(
            request, project_id, form_id, schema, main_rowuuid, module, user
        )
    except ModuleError as e:
        return _finish(
            request,
            project_id,
            form_id,
            submission_id,
            main_rowuuid,
            dry_run,
            run_id,
            str(e),
            [],
            [],
        )
    source = inputs.pop("_source")
    result = run_module(module, inputs, engine=engine_path(request))
    if not result.ok:
        return _finish(
            request,
            project_id,
            form_id,
            submission_id,
            main_rowuuid,
            dry_run,
            run_id,
            result.error,
            [],
            result.log,
        )
    try:
        if result.changes is not None:
            # The engine reported the changes itself (RSTools' host); the
            # writes to apply are read back from the report.
            changes = result.changes
            writes = result.writes or writes_from_changes(changes, inputs.get("case"))
        else:
            changes = changes_of(result.writes, inputs.get("case"))
            writes = result.writes
        plan = (
            _plan_writes(request, source, inputs.get("case"), writes) if changes else []
        )
    except ModuleError as e:
        return _finish(
            request,
            project_id,
            form_id,
            submission_id,
            main_rowuuid,
            dry_run,
            run_id,
            str(e),
            [],
            result.log,
        )
    if not dry_run and plan:
        try:
            _apply(request, source["schema"], plan, user)
        except Exception as e:
            request.dbsession.rollback()
            return _finish(
                request,
                project_id,
                form_id,
                submission_id,
                main_rowuuid,
                dry_run,
                run_id,
                "The writes could not be applied: {}".format(e),
                [],
                result.log,
            )
    return _finish(
        request,
        project_id,
        form_id,
        submission_id,
        main_rowuuid,
        dry_run,
        run_id,
        None,
        changes,
        result.log,
    )


def _finish(
    request,
    project_id,
    form_id,
    submission_id,
    main_rowuuid,
    dry_run,
    run_id,
    error,
    changes,
    log_lines,
):
    if not dry_run:
        run_id = _record(
            request,
            project_id,
            form_id,
            submission_id,
            main_rowuuid,
            1 if error else 0,
            error,
            changes,
            log_lines,
            run_id,
        )
    return {
        "ok": error is None,
        "skipped": False,
        "changes": changes,
        "log": log_lines,
        "error": error,
        "run_id": run_id,
    }


def run_after_load(
    request, project_id, form_id, schema, submission_id, uuid_file, user
):
    """What the loaders call after JSONToMySQL returned 0. Never raises:
    the submission is stored whatever the module does."""
    try:
        main_rowuuid = main_rowuuid_of(uuid_file)
        if main_rowuuid is None:
            return
        outcome = run_for_submission(
            request, project_id, form_id, schema, main_rowuuid, submission_id, user
        )
        if outcome.get("error"):
            log.error(
                "The actions of form {} failed for submission {}: {}".format(
                    form_id, submission_id, outcome["error"]
                )
            )
    except Exception as e:  # pragma: no cover
        log.error(
            "The actions of form {} could not run for submission {}: {}".format(
                form_id, submission_id, e
            )
        )
        try:
            request.dbsession.rollback()
        except Exception:
            pass


def retry_run(request, run_id, schema, user):
    """Runs a recorded run again, in place."""
    a_run = get_run(request, run_id)
    if a_run is None:
        return {"ok": False, "error": "No such run", "changes": [], "log": []}
    return run_for_submission(
        request,
        a_run["project_id"],
        a_run["form_id"],
        schema,
        a_run["main_rowuuid"],
        a_run["submission_id"],
        user,
        run_id=run_id,
    )
