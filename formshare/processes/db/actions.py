"""The actions registry: a form's actions, rules and code, and the catalogue
of what a rule may name (feature 3, decision 16).

The actions live in PropertyAction, each a rule of the decision table (When,
Target, Value) or code its author wrote; the form keeps the module they
compose into (Odkform.action_module), which is what the server runs and
actions.json serves. Adding or changing an action composes the module again,
and stores the action and the module in one commit, or nothing at all
(2026-10-20: before, a form had one mode, the table or a module written by
hand).

The catalogue is built from the dictionary of the acting form (its
variables, typed, with the choices of its selects), the registry (the case
link's source table, its properties and columns, and the parent table of a
repeat source) and the repeats of the form (for computed values). The
compiler reads it to spell and type a rule; the screen reads the same
catalogue to configure QueryBuilder, so a rule that the screen can build is
one the compiler can compile.

docs/formshare_case_management/actions-api.md, formshare.md sections 2.5,
3.3 and 4.2.
"""

import datetime
import json
import logging
import re
import uuid

from sqlalchemy import text

from formshare.models import (
    Odkform,
    PropertyAction,
    DictField,
    DictTable,
    map_from_schema,
)
from formshare.processes.db.encryption import encrypted_column_message
from formshare.processes.actions.compiler import (
    AGGREGATES,
    Catalogue,
    CompileError,
    EMPTY_MODULE,
    compile_module,
)
from formshare.processes.actions.host import LIMITS, ModuleError, load_module
from formshare.processes.db.case_management import (
    get_case_link_consumer,
    get_published_list,
    get_list_source_schema,
    get_table_properties,
    validate_property_default,
)

__all__ = [
    "get_form_actions",
    "get_form_action",
    "add_form_action",
    "update_form_action",
    "delete_form_action",
    "move_form_action",
    "add_code_action",
    "update_code_action",
    "get_action_mode",
    "get_action_module",
    "recompile_form_module",
    "actions_json",
    "build_catalogue",
    "catalogue_for_editor",
    "catalogue_for_querybuilder",
    "case_source_of",
    "continuations_of",
    "js_type_of",
    "CONTROL_COLUMNS",
]

log = logging.getLogger("formshare")

# Columns of a data table that are the repository's, not the form's: not
# offered as fields, not served as s.<variable> the way a variable is.
CONTROL_COLUMNS = (
    "rowuuid",
    "root_rowuuid",
    "parent_rowuuid",
    "link_rowuuid",
    "surveyid",
    "originid",
    "instanceid",
    "rowindex",
    "_active",
    "_lastupdate",
    "_submitted_by",
    "_submitted_date",
    "_user_id",
    "_xform_id_string",
    "_project_code",
    "_geopoint",
    "_latitude",
    "_longitude",
    "_cellid",
    "_cellxpos",
    "_cellypos",
    "_dqscore",
    "_assigned_to",
)

_MSEL = re.compile(r"_msel_")
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


def js_type_of(dictionary_type, odk_type=None):
    """The type a rule sees (actions-api.md section 6): integer, double,
    date, datetime or string, from the dictionary's column type."""
    kind = (dictionary_type or "").lower().split("(")[0].strip()
    if kind.startswith("int") or kind in ("bigint", "smallint", "tinyint"):
        return "integer"
    if kind in ("decimal", "double", "float", "numeric"):
        return "double"
    if kind == "date":
        return "date"
    if kind in ("datetime", "timestamp"):
        return "datetime"
    return "string"


def property_js_type(property_type):
    return {
        "integer": "integer",
        "decimal": "double",
        "date": "date",
        "datetime": "datetime",
    }.get(property_type, "string")


# ---------------------------------------------------------------------------
# The rows
# ---------------------------------------------------------------------------


def get_form_actions(request, project_id, form_id):
    res = (
        request.dbsession.query(PropertyAction)
        .filter(PropertyAction.project_id == project_id)
        .filter(PropertyAction.form_id == form_id)
        .order_by(PropertyAction.action_order)
        .all()
    )
    return map_from_schema(res)


def get_form_action(request, project_id, form_id, action_id):
    res = (
        request.dbsession.query(PropertyAction)
        .filter(PropertyAction.project_id == project_id)
        .filter(PropertyAction.form_id == form_id)
        .filter(PropertyAction.action_id == action_id)
        .first()
    )
    return map_from_schema(res) if res is not None else None


# A description is one line: in the list of actions, and in the comment above
# the action in the module.
_BREAKS = re.compile(r"\s+")


def _description(text):
    """What the author says an action does (action_desc): one line of at
    most 255 characters, or None."""
    return _BREAKS.sub(" ", text or "").strip()[:255] or None


def _check_row(request, project_id, form_id, data, catalogue):
    """Validates one row against the catalogue and normalises it; returns
    (ok, row, message). The compiler is the judge: a row it cannot compile
    is refused here with its reason, before anything is stored."""
    _ = request.translate
    row = {
        "target_scope": (data.get("target_scope") or "case").strip(),
        "target_kind": (data.get("target_kind") or "").strip(),
        "target_name": (data.get("target_name") or "").strip(),
        "value_kind": (data.get("value_kind") or "constant").strip(),
        "value": data.get("value"),
        "when_rules": data.get("when_rules"),
        "action_desc": _description(data.get("action_desc")),
    }
    if row["action_desc"] is None:
        return False, None, _("Describe the action in a few words")
    if row["target_scope"] not in ("case", "parent"):
        return False, None, _("The target must be the case or its parent")
    if row["target_kind"] not in ("property", "column", "active"):
        return False, None, _("Choose what the row sets")
    if row["target_kind"] == "active":
        row["target_name"] = "1" if str(row["target_name"]).strip() == "1" else "0"
        row["value_kind"] = "constant"
        row["value"] = None
    elif row["target_name"] == "":
        return False, None, _("Choose the property or column the row sets")
    if row["value_kind"] not in ("constant", "variable", "now", "computed"):
        return False, None, _("Choose where the value comes from")
    if row["value_kind"] == "constant" and row["target_kind"] == "property":
        # A constant is checked exactly as a default of the property is.
        key = (row["target_scope"], "property", row["target_name"])
        property_type = catalogue.property_types.get(key)
        ok, normalised, message = validate_property_default(
            property_type, row["value"] or "", _
        )
        if not ok:
            return False, None, message
        row["value"] = normalised
    if row["value_kind"] == "computed":
        value = row["value"]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return False, None, _("The computed value is not valid")
        if not isinstance(value, dict) or value.get("aggregate") not in AGGREGATES:
            return False, None, _("Choose the aggregate, the repeat and the column")
        row["value"] = json.dumps(value)
    when = row["when_rules"]
    if isinstance(when, dict):
        when = json.dumps(when) if when.get("rules") else None
    elif isinstance(when, str):
        when = when.strip() or None
        if when is not None:
            try:
                parsed = json.loads(when)
            except ValueError:
                return False, None, _("The condition is not valid")
            when = json.dumps(parsed) if parsed.get("rules") else None
    row["when_rules"] = when
    refusal = _encrypted_refusal(row, catalogue, _)
    if refusal is not None:
        return False, None, refusal
    try:
        compile_module([dict(row, action_order=0)], catalogue)
    except CompileError as e:
        return False, None, str(e)
    return True, row, ""


def _rule_ids(when_rules):
    """The ids of the fields a condition reads."""
    try:
        rules = json.loads(when_rules) if when_rules else None
    except ValueError:
        return set()
    found = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        if "rules" in node:
            for a_rule in node.get("rules") or []:
                walk(a_rule)
            return
        field_id = str(node.get("field") or node.get("id") or "")
        if field_id:
            found.add(field_id)

    walk(rules)
    return found


def _encrypted_refusal(row, catalogue, translate):
    """Why a row cannot be kept when it writes a column that holds
    envelopes, copies one, or decides by one (formshare.md 6.7); None when
    it does none of that. A write would be refused by MySQL (3819), and a
    copy or a comparison would read only the envelope."""
    _ = translate
    encrypted = getattr(catalogue, "encrypted", set())
    target = (row["target_scope"], row["target_kind"], row["target_name"])
    if target in getattr(catalogue, "encrypted_targets", set()):
        return encrypted_column_message(
            _, row["target_name"], _("written by an action")
        )
    if row["value_kind"] == "variable" and "v." + str(row["value"] or "") in encrypted:
        return encrypted_column_message(_, row["value"], _("copied by an action"))
    for field_id in sorted(_rule_ids(row["when_rules"])):
        if field_id in encrypted:
            return encrypted_column_message(
                _, field_id.split(".", 1)[1], _("read by an action's condition")
            )
    return None


def _compose(rows, catalogue, translate):
    """The form's module from its actions: (True, module), or (False, why
    not). The 64 KB every host allows a module (actions-api.md 7) is for the
    form's actions together."""
    try:
        module = compile_module(rows, catalogue)
    except CompileError as e:
        return False, str(e)
    if len(module.encode("utf-8")) > LIMITS["source_bytes"]:
        return False, translate(
            "The form's actions together are larger than {} KB"
        ).format(LIMITS["source_bytes"] // 1024)
    return True, module


def _set_module(form, rows, module):
    """The composed module on the form. Its mode, which actions.json serves
    for information, says whether any action is code (actions-api.md 2)."""
    form.action_module = module
    form.action_mode = (
        "expert"
        if any((a_row.get("action_kind") or "rule") == "code" for a_row in rows)
        else "table"
    )


def _save_action(request, project_id, form_id, action_id, values, catalogue, kind):
    """Stores a new action (action_id None) or new values for one, and the
    form's module composed again, in one commit. Nothing is stored when the
    module cannot be composed with it. Returns (ok, action_id or message)."""
    _ = request.translate
    form = _form(request, project_id, form_id)
    if form is None:
        return False, _("No such form")
    rows = get_form_actions(request, project_id, form_id)
    order = None
    if action_id is None:
        action_id = str(uuid.uuid4())
        order = max([int(a["action_order"] or 0) for a in rows] + [0]) + 1
        rows = rows + [dict(values, action_id=action_id, action_order=order)]
    else:
        current = [a for a in rows if a["action_id"] == action_id]
        if not current:
            return False, _("No such action")
        if (current[0].get("action_kind") or "rule") != kind:
            return False, _("This action is of another kind")
        rows = [dict(a, **values) if a["action_id"] == action_id else a for a in rows]
    ok, module = _compose(rows, catalogue, _)
    if not ok:
        return False, module
    try:
        if order is not None:
            request.dbsession.add(
                PropertyAction(
                    action_id=action_id,
                    project_id=project_id,
                    form_id=form_id,
                    action_order=order,
                    action_cdate=datetime.datetime.now(),
                    **values
                )
            )
        else:
            request.dbsession.query(PropertyAction).filter(
                PropertyAction.project_id == project_id
            ).filter(PropertyAction.form_id == form_id).filter(
                PropertyAction.action_id == action_id
            ).update(
                values
            )
        _set_module(form, rows, module)
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} storing action {} of form {}".format(e, action_id, form_id))
        return False, str(e)
    return True, action_id


def _rule_values(row):
    return dict(row, action_kind="rule", action_code=None)


def add_form_action(request, project_id, form_id, data):
    """Adds a rule at the end of the form's actions. Returns (ok, action_id
    or message)."""
    catalogue = build_catalogue(request, project_id, form_id)
    ok, row, message = _check_row(request, project_id, form_id, data, catalogue)
    if not ok:
        return False, message
    return _save_action(
        request, project_id, form_id, None, _rule_values(row), catalogue, "rule"
    )


def update_form_action(request, project_id, form_id, action_id, data):
    """New When, Target and Value for a rule. Returns (ok, action_id or
    message)."""
    catalogue = build_catalogue(request, project_id, form_id)
    ok, row, message = _check_row(request, project_id, form_id, data, catalogue)
    if not ok:
        return False, message
    return _save_action(
        request, project_id, form_id, action_id, _rule_values(row), catalogue, "rule"
    )


def _check_code(request, code, description):
    """Normalises the code of an action and refuses one no host could load,
    or one without a description; returns (ok, values, message).

    A browser posts a textarea's lines ended with CR LF. Stored as they
    come, the code would not be the text its author saw, and its size, which
    load_module limits, would count a byte more per line than the editor's
    check does (frontend/actions-editor)."""
    _ = request.translate
    description = _description(description)
    if description is None:
        return False, None, _("Describe the action in a few words")
    code = re.sub(r"\r\n?", "\n", code or "")
    if code.strip() == "":
        return False, None, _("Write the action's code")
    try:
        load_module(code)
    except ModuleError as e:
        return False, None, str(e)
    return (
        True,
        {
            "action_kind": "code",
            "action_code": code,
            "action_desc": description,
            "target_scope": "case",
            "target_kind": None,
            "target_name": None,
            "value_kind": None,
            "value": None,
            "when_rules": None,
        },
        "",
    )


def add_code_action(request, project_id, form_id, code, description=""):
    """Adds code at the end of the form's actions. Returns (ok, action_id or
    message)."""
    ok, values, message = _check_code(request, code, description)
    if not ok:
        return False, message
    catalogue = build_catalogue(request, project_id, form_id)
    return _save_action(request, project_id, form_id, None, values, catalogue, "code")


def update_code_action(request, project_id, form_id, action_id, code, description=""):
    """New code for a code action. Returns (ok, action_id or message)."""
    ok, values, message = _check_code(request, code, description)
    if not ok:
        return False, message
    catalogue = build_catalogue(request, project_id, form_id)
    return _save_action(
        request, project_id, form_id, action_id, values, catalogue, "code"
    )


def delete_form_action(request, project_id, form_id, action_id):
    try:
        request.dbsession.query(PropertyAction).filter(
            PropertyAction.project_id == project_id
        ).filter(PropertyAction.form_id == form_id).filter(
            PropertyAction.action_id == action_id
        ).delete()
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} deleting action {}".format(str(e), action_id))
        return False, str(e)
    _renumber(request, project_id, form_id)
    return recompile_form_module(request, project_id, form_id)


def move_form_action(request, project_id, form_id, action_id, direction):
    """Moves a row up (-1) or down (+1) and recompiles: the order is the
    order of the chains, and inside a target's chain it decides which row
    wins."""
    rows = get_form_actions(request, project_id, form_id)
    ids = [a["action_id"] for a in rows]
    if action_id not in ids:
        return False, "No such row"
    index = ids.index(action_id)
    other = index + (1 if direction > 0 else -1)
    if other < 0 or other >= len(ids):
        return True, ""
    ids[index], ids[other] = ids[other], ids[index]
    try:
        for order, an_id in enumerate(ids, 1):
            request.dbsession.query(PropertyAction).filter(
                PropertyAction.action_id == an_id
            ).update({"action_order": order})
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        return False, str(e)
    return recompile_form_module(request, project_id, form_id)


def _renumber(request, project_id, form_id):
    rows = get_form_actions(request, project_id, form_id)
    for order, a_row in enumerate(rows, 1):
        if int(a_row["action_order"] or 0) != order:
            request.dbsession.query(PropertyAction).filter(
                PropertyAction.action_id == a_row["action_id"]
            ).update({"action_order": order})
    request.dbsession.commit()


# ---------------------------------------------------------------------------
# The module on the form
# ---------------------------------------------------------------------------


def _form(request, project_id, form_id):
    return (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project_id)
        .filter(Odkform.form_id == form_id)
        .first()
    )


def get_action_mode(request, project_id, form_id):
    form = _form(request, project_id, form_id)
    if form is None:
        return "table"
    return form.action_mode or "table"


def get_action_module(request, project_id, form_id):
    """The module the server runs and actions.json serves: empty when the
    form has no actions."""
    form = _form(request, project_id, form_id)
    if form is None:
        return EMPTY_MODULE
    return form.action_module or EMPTY_MODULE


def recompile_form_module(request, project_id, form_id, catalogue=None):
    """Composes the form's actions into its module again: after one is
    removed or moved, or when what they name may have changed."""
    form = _form(request, project_id, form_id)
    if form is None:
        return False, "No such form"
    rows = get_form_actions(request, project_id, form_id)
    if catalogue is None:
        catalogue = build_catalogue(request, project_id, form_id)
    ok, module = _compose(rows, catalogue, request.translate)
    if not ok:
        return False, module
    try:
        _set_module(form, rows, module)
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        return False, str(e)
    return True, ""


def actions_json(mode, module):
    """The served file (actions-api.md section 2)."""
    return json.dumps(
        {
            "version": 1,
            "language": "js",
            "mode": mode or "table",
            "module": module or "",
        },
        indent=1,
        ensure_ascii=False,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# The catalogue
# ---------------------------------------------------------------------------


def _fields_of(request, project_id, form_id, table_name):
    res = (
        request.dbsession.query(DictField)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.table_name == table_name)
        .order_by(DictField.field_index)
        .all()
    )
    return map_from_schema(res)


def _tables_of(request, project_id, form_id):
    res = (
        request.dbsession.query(DictTable)
        .filter(DictTable.project_id == project_id)
        .filter(DictTable.form_id == form_id)
        .order_by(DictTable.table_index)
        .all()
    )
    return map_from_schema(res)


def _choices(request, schema, lookup_table, list_name):
    """The codes and labels of a lookup, for the select widget."""
    if not schema or not lookup_table:
        return []
    try:
        rows = request.dbsession.execute(
            text(
                "SELECT `{cod}`, `{des}` FROM `{schema}`.`{table}` ORDER BY `{cod}`".format(
                    cod=list_name + "_cod",
                    des=list_name + "_des",
                    schema=schema,
                    table=lookup_table,
                )
            )
        ).fetchall()
    except Exception as e:
        log.warning("The choices of {} could not be read: {}".format(lookup_table, e))
        return []
    return [
        {"code": str(r[0]), "label": "" if r[1] is None else str(r[1])} for r in rows
    ]


def continuations_of(request, project_id, form_id):
    """{continuation: the table it continues} for a form split across
    continuation tables (rstools.md 13.4).

    JXFormToMysql splits a table MySQL cannot hold into a chain: maintable,
    maintable_ext1 and so on, each row of a continuation holding more columns
    of one row of the table it continues and naming that row in
    link_rowuuid. The dictionary records every field of every table, so a
    table with a link_rowuuid field is a continuation, and the table it is
    nested in (walking up through continuations) is the one it continues.
    A continuation is never a repeat: its columns belong to the row it
    continues.
    """
    extended = set(
        a_row[0]
        for a_row in request.dbsession.query(DictField.table_name)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.field_name == "link_rowuuid")
        .all()
    )
    if not extended:
        return {}
    parents = {
        a_table["table_name"]: a_table.get("parent_table")
        for a_table in _tables_of(request, project_id, form_id)
    }
    out = {}
    for name in extended:
        parent = parents.get(name)
        while parent in extended:
            parent = parents.get(parent)
        if parent:
            out[name] = parent
    return out


def case_source_of(request, project_id, form_id):
    """Where the form's case lives: the case link's list and its source
    (project, form, schema, table), the parent table when the source is a
    repeat. A form without a case link acts on its own rows -- each
    submission's main row is its case (actions-api.md 4.2), as the device
    does with CaseLink.own() -- and gets ``own: True`` with no selector.
    None only for a form that does not exist."""
    link = get_case_link_consumer(request, project_id, form_id)
    if link is None:
        form = _form(request, project_id, form_id)
        if form is None:
            return None
        return {
            "list_id": None,
            "selector_field": None,
            "project": project_id,
            "form": form_id,
            "schema": form.form_schema,
            "table": "maintable",
            "parent_table": None,
            "own": True,
        }
    a_list = get_published_list(request, link["list_project"], link["list_id"])
    if a_list is None:
        return None
    schema = get_list_source_schema(request, a_list)
    extended = continuations_of(
        request, a_list["source_project"], a_list["source_form"]
    )
    parent_table = None
    for a_table in _tables_of(request, a_list["source_project"], a_list["source_form"]):
        if a_table["table_name"] == a_list["source_table"]:
            parent_table = a_table.get("parent_table")
    # A repeat nested in a continuation belongs to the row it continues.
    while parent_table in extended:
        parent_table = extended[parent_table]
    return {
        "list_id": a_list["list_id"],
        "selector_field": link["selector_field"],
        "project": a_list["source_project"],
        "form": a_list["source_form"],
        "schema": schema,
        "table": a_list["source_table"],
        "parent_table": parent_table,
        # The _active of the cases it serves, as get_consumer_sources hands
        # it to the follow-up's membership trigger
        "list_active": int(a_list.get("list_active", 1) or 0),
        "own": False,
    }


def build_catalogue(request, project_id, form_id):
    """The Catalogue the compiler reads for this form, with the extras the
    screen needs hung on it: ``ui`` (QueryBuilder filters) and
    ``property_types`` (for checking a constant)."""
    catalogue = Catalogue()
    catalogue.ui = []
    catalogue.property_types = {}
    catalogue.variables = []
    # What holds envelopes (field encryption): the ids of fields no condition
    # or copy can read, and the columns no row can write. They stay in the
    # catalogue, so that a row naming one is refused with its reason rather
    # than as unknown, and are left off the screen.
    catalogue.encrypted = set()
    catalogue.encrypted_targets = set()
    form = _form(request, project_id, form_id)
    schema = form.form_schema if form is not None else None

    def member(base, name):
        if _NAME.match(name):
            return "{}.{}".format(base, name)
        return '{}["{}"]'.format(base, name)

    extended = continuations_of(request, project_id, form_id)
    main_fields = _fields_of(request, project_id, form_id, "maintable")
    for ext_table, continued in sorted(extended.items()):
        if continued == "maintable":
            main_fields = main_fields + _fields_of(
                request, project_id, form_id, ext_table
            )

    # This submission: the variables of the main table and its continuations.
    for a_field in main_fields:
        name = a_field["field_name"]
        if name in CONTROL_COLUMNS or name.startswith("_"):
            continue
        odk_type = (a_field.get("field_odktype") or "").lower()
        multi = odk_type == "select all that apply"
        js_type = "string" if multi else js_type_of(a_field.get("field_type"), odk_type)
        entry = {
            "js": member("s", name),
            "type": js_type,
            "label": name,
            "group": "submission",
        }
        if multi:
            entry["multi"] = True
            entry["variable"] = name
        catalogue.fields["v." + name] = entry
        if a_field.get("field_encrypted") == 1:
            catalogue.encrypted.add("v." + name)
            continue
        catalogue.variables.append({"name": name, "type": js_type, "multi": multi})
        ui = {
            "id": "v." + name,
            "label": name,
            "type": js_type,
            "optgroup": "This submission",
        }
        lookup_table = a_field.get("field_rtable")
        if lookup_table and lookup_table.startswith("lkp") and not multi:
            values = _choices(request, schema, lookup_table, lookup_table[3:])
            if values:
                ui["input"] = "select"
                ui["values"] = values
                ui["operators"] = [
                    "equal",
                    "not_equal",
                    "in",
                    "not_in",
                    "is_null",
                    "is_not_null",
                ]
        if multi:
            msel = _tables_of(request, project_id, form_id)
            values = []
            for a_table in msel:
                if a_table["table_name"] == "maintable_msel_" + name:
                    # The msel table's own select field names the lookup.
                    for f in _fields_of(
                        request, project_id, form_id, a_table["table_name"]
                    ):
                        if f["field_name"] == name and (
                            f.get("field_rtable") or ""
                        ).startswith("lkp"):
                            values = _choices(
                                request,
                                schema,
                                f["field_rtable"],
                                f["field_rtable"][3:],
                            )
            ui["input"] = "select" if values else "text"
            if values:
                ui["values"] = values
            ui["multiple"] = True
            ui["operators"] = ["in", "not_in", "is_empty", "is_not_empty"]
        catalogue.ui.append(ui)

    # The repeats, for computed values, and their numeric columns as fields.
    for a_table in _tables_of(request, project_id, form_id):
        name = a_table["table_name"]
        if name == "maintable" or a_table.get("table_lkp") or _MSEL.search(name):
            continue
        if not a_table.get("parent_table") or name in extended:
            continue
        columns = {}
        repeat_fields = _fields_of(request, project_id, form_id, name)
        for ext_table, continued in sorted(extended.items()):
            if continued == name:
                repeat_fields = repeat_fields + _fields_of(
                    request, project_id, form_id, ext_table
                )
        for a_field in repeat_fields:
            fname = a_field["field_name"]
            if (
                fname in CONTROL_COLUMNS
                or fname.startswith("_")
                or fname.endswith("_rowid")
            ):
                continue
            columns[fname] = js_type_of(
                a_field.get("field_type"), a_field.get("field_odktype")
            )
        catalogue.repeats[name] = columns
        for column, ctype in columns.items():
            if ctype not in ("integer", "double"):
                continue
            for aggregate in AGGREGATES:
                field_id = "c.{}.{}.{}".format(aggregate, name, column)
                label = "{} of {}.{}".format(
                    {
                        "avg": "average",
                        "sum": "sum",
                        "count": "count",
                        "min": "minimum",
                        "max": "maximum",
                    }[aggregate],
                    name,
                    column,
                )
                catalogue.fields[field_id] = {
                    "js": 'api.{}(s.repeat("{}"), "{}")'.format(
                        aggregate, name, column
                    ),
                    "type": "double" if aggregate != "count" else "integer",
                    "label": label,
                    "group": "computed",
                }
                catalogue.ui.append(
                    {
                        "id": field_id,
                        "label": label,
                        "type": "double" if aggregate != "count" else "integer",
                        "optgroup": "This submission, computed",
                    }
                )

    # The case and its parent.
    source = case_source_of(request, project_id, form_id)
    catalogue.source = source
    if source is not None:
        for a_property in get_table_properties(
            request, source["project"], source["form"], source["table"]
        ):
            pname = a_property["property_name"]
            ptype = a_property["property_type"]
            catalogue.property_types[("case", "property", pname)] = ptype
            catalogue.targets[("case", "property", pname)] = property_js_type(ptype)
            catalogue.fields["p." + pname] = {
                "js": 'api.case.property("{}")'.format(pname),
                "type": property_js_type(ptype),
                "label": "case " + pname,
                "group": "case",
            }
            catalogue.ui.append(
                {
                    "id": "p." + pname,
                    "label": "case property " + pname,
                    "type": property_js_type(ptype),
                    "optgroup": "The case",
                }
            )
        for a_field in _fields_of(
            request, source["project"], source["form"], source["table"]
        ):
            cname = a_field["field_name"]
            if (
                cname in CONTROL_COLUMNS
                or cname.startswith("_")
                or cname.endswith("_rowid")
            ):
                continue
            ctype = js_type_of(a_field.get("field_type"), a_field.get("field_odktype"))
            catalogue.targets[("case", "column", cname)] = ctype
            catalogue.fields["k." + cname] = {
                "js": 'api.case.value("{}")'.format(cname),
                "type": ctype,
                "label": "case " + cname,
                "group": "case",
            }
            if a_field.get("field_encrypted") == 1:
                catalogue.encrypted.add("k." + cname)
                catalogue.encrypted_targets.add(("case", "column", cname))
                continue
            catalogue.ui.append(
                {
                    "id": "k." + cname,
                    "label": "case column " + cname,
                    "type": ctype,
                    "optgroup": "The case",
                }
            )
        if source.get("parent_table"):
            for a_property in get_table_properties(
                request, source["project"], source["form"], source["parent_table"]
            ):
                pname = a_property["property_name"]
                ptype = a_property["property_type"]
                catalogue.property_types[("parent", "property", pname)] = ptype
                catalogue.targets[("parent", "property", pname)] = property_js_type(
                    ptype
                )
                catalogue.fields["pp." + pname] = {
                    "js": 'api.case.parent.property("{}")'.format(pname),
                    "type": property_js_type(ptype),
                    "label": "parent " + pname,
                    "group": "parent",
                }
                catalogue.ui.append(
                    {
                        "id": "pp." + pname,
                        "label": "parent property " + pname,
                        "type": property_js_type(ptype),
                        "optgroup": "The case's parent",
                    }
                )
    _add_days_since(catalogue)
    return catalogue


# Where a day count of a date is offered, by the group of the date.
_DAYS_SINCE_GROUPS = {
    "submission": "This submission, days since",
    "case": "The case, days since",
    "parent": "The case's parent, days since",
}


def _add_days_since(catalogue):
    """A field "days since <date>" for every date, or date and time, the
    module can read: the submission's, the case's, its parent's.

    It counts whole days from the date to ``api.now`` with ``api.days``
    (actions-api.md 4.5 and 7), which reads the date and leaves the time, so
    "30 days since the last visit" is a rule of the table rather than a
    module written by hand. The count is relative to each host's own date,
    as ``api.now`` is: the server's on the server, the phone's on the phone.
    A date that is not there counts nothing: the field is null, and a
    comparison with null is false.
    """
    ui_labels = {entry["id"]: entry["label"] for entry in catalogue.ui}
    for field_id, entry in list(catalogue.fields.items()):
        if entry.get("multi") or entry.get("type") not in ("date", "datetime"):
            continue
        optgroup = _DAYS_SINCE_GROUPS.get(entry.get("group"))
        if optgroup is None:
            continue
        days_id = "d." + field_id
        catalogue.fields[days_id] = {
            "js": "({date} === null ? null : api.days({date}, api.now))".format(
                date=entry["js"]
            ),
            "type": "integer",
            "label": "days since " + entry["label"],
            "group": "days",
        }
        catalogue.ui.append(
            {
                "id": days_id,
                "label": "days since " + ui_labels.get(field_id, entry["label"]),
                "type": "integer",
                "optgroup": optgroup,
            }
        )


# What JXFormToMysql writes as the description of a field that has no label.
_NO_LABEL = "Without label"


def catalogue_for_editor(request, project_id, form_id, catalogue):
    """What the expert mode's editor completes and checks names against
    (frontend/actions-editor): the names a module meets when it runs, by
    the rules the run's input is built with (processes/actions/server.py).

    - **questions**: the stored columns of the main table and its
      continuations, less the control columns, the keys and what MySQL
      generates. ``system`` marks a column of the repository's own (a name
      starting with _), which the run hands over but the editor does not
      offer. A select carries its choices.
    - **repeats**: each with the table it hangs off and its columns.
    - **case** and **parent**: the properties and the columns of the case's
      row and of its parent's, or None when there is none.
    - **lookups**: the lists api.lookup can read, from the form's
      repository and then the case's source's, as the run looks for them.

    Encrypted names are kept and marked, so that the editor says why one
    cannot be used rather than that it does not exist. ``known`` is False
    for a form with no repository yet, and the editor then checks no name.
    """
    form = _form(request, project_id, form_id)
    schema = form.form_schema if form is not None else None
    out = {
        "known": bool(schema),
        "questions": [],
        "repeats": [],
        "case": None,
        "parent": None,
        "lookups": [],
    }
    if not schema:
        return out
    tables = _tables_of(request, project_id, form_id)
    extended = continuations_of(request, project_id, form_id)
    choices = {}

    def choices_of(lookup_table):
        if not lookup_table or not lookup_table.startswith("lkp"):
            return []
        if lookup_table not in choices:
            choices[lookup_table] = _choices(
                request, schema, lookup_table, lookup_table[3:]
            )
        return choices[lookup_table]

    def stored(a_field):
        name = a_field["field_name"]
        return not (
            name in CONTROL_COLUMNS
            or name.endswith("_rowid")
            or a_field.get("field_generatedas")
        )

    def answers_of(table_name):
        """The answers of a table and of the continuations of it."""
        fields = _fields_of(request, project_id, form_id, table_name)
        for ext_table, continued in sorted(extended.items()):
            if continued == table_name:
                fields = fields + _fields_of(request, project_id, form_id, ext_table)
        entries = []
        for a_field in fields:
            if not stored(a_field):
                continue
            name = a_field["field_name"]
            odk_type = (a_field.get("field_odktype") or "").lower()
            multi = odk_type == "select all that apply"
            label = (a_field.get("field_desc") or "").strip()
            entry = {
                "name": name,
                "type": (
                    "string"
                    if multi
                    else js_type_of(a_field.get("field_type"), odk_type)
                ),
                "label": "" if label == _NO_LABEL else label,
            }
            if odk_type == "select one":
                # Its choices may come from a file, with no lookup table.
                entry["select"] = True
            if multi:
                entry["multi"] = True
                # The msel table's own field names the lookup.
                for f in _fields_of(
                    request, project_id, form_id, table_name + "_msel_" + name
                ):
                    if f["field_name"] == name:
                        entry["choices"] = choices_of(f.get("field_rtable"))
            else:
                values = choices_of(a_field.get("field_rtable"))
                if values:
                    entry["choices"] = values
            if a_field.get("field_encrypted") == 1:
                entry["encrypted"] = True
                entry.pop("choices", None)
            if name.startswith("_"):
                entry["system"] = True
            entries.append(entry)
        return entries

    out["questions"] = answers_of("maintable")

    def module_parent(table_name):
        while table_name in extended:
            table_name = extended[table_name]
        return table_name

    for a_table in tables:
        name = a_table["table_name"]
        if name == "maintable" or a_table.get("table_lkp") or _MSEL.search(name):
            continue
        if not a_table.get("parent_table") or name in extended:
            continue
        out["repeats"].append(
            {
                "name": name,
                "parent": module_parent(a_table["parent_table"]),
                "columns": answers_of(name),
            }
        )

    def case_row(source, table_name):
        properties = [
            {
                "name": a_property["property_name"],
                "type": property_js_type(a_property["property_type"]),
            }
            for a_property in get_table_properties(
                request, source["project"], source["form"], table_name
            )
        ]
        columns = []
        for a_field in _fields_of(
            request, source["project"], source["form"], table_name
        ):
            if not stored(a_field):
                continue
            label = (a_field.get("field_desc") or "").strip()
            column = {
                "name": a_field["field_name"],
                "type": js_type_of(
                    a_field.get("field_type"), a_field.get("field_odktype")
                ),
                "label": "" if label == _NO_LABEL else label,
            }
            if a_field.get("field_encrypted") == 1:
                column["encrypted"] = True
            columns.append(column)
        return {"table": table_name, "properties": properties, "columns": columns}

    source = getattr(catalogue, "source", None)
    # A source with no repository gives the run no case: api.case is null.
    if source is not None and source.get("schema"):
        out["case"] = case_row(source, source["table"])
        if source.get("parent_table"):
            out["parent"] = case_row(source, source["parent_table"])

    places = [(project_id, form_id)]
    if source is not None and (source["project"], source["form"]) != places[0]:
        places.append((source["project"], source["form"]))
    named = set()
    for place_project, place_form in places:
        for a_table in _tables_of(request, place_project, place_form):
            if not a_table.get("table_lkp"):
                continue
            name = a_table["table_name"][3:]
            if name in named or not _NAME.match(name):
                continue
            named.add(name)
            out["lookups"].append(
                {
                    "name": name,
                    "columns": [
                        f["field_name"]
                        for f in _fields_of(
                            request, place_project, place_form, a_table["table_name"]
                        )
                        if f["field_name"] != "rowuuid"
                        and not f["field_name"].endswith("_rowid")
                        and not f.get("field_generatedas")
                    ],
                }
            )
    return out


def catalogue_for_querybuilder(catalogue):
    """The QueryBuilder ``filters`` option, as JSON-ready dicts: id, label,
    type, optgroup, and for a select its values, for a multi-select the
    membership operators."""
    filters = []
    for entry in catalogue.ui:
        item = {
            "id": entry["id"],
            "label": entry["label"],
            "type": entry["type"],
            "optgroup": entry.get("optgroup"),
        }
        if entry.get("input"):
            item["input"] = entry["input"]
        if entry.get("values"):
            item["values"] = [
                {v["code"]: v["label"] or v["code"]} for v in entry["values"]
            ]
        if entry.get("multiple"):
            item["multiple"] = True
        if entry.get("operators"):
            item["operators"] = entry["operators"]
        if entry["type"] == "double":
            # A number input steps by 1 unless told otherwise, and the
            # browser refuses to submit a form that holds 0.75 in it
            item["validation"] = {"step": "any"}
        if entry["type"] in ("date", "datetime"):
            item["placeholder"] = (
                "YYYY-MM-DD" if entry["type"] == "date" else "YYYY-MM-DD HH:MM:SS"
            )
        filters.append(item)
    return filters
