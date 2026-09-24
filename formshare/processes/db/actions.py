"""The actions registry: a form's decision table, its module, and the
catalogue of what a rule may name (feature 3, decision 16).

The rows live in PropertyAction, the module on the form (Odkform.action_mode,
Odkform.action_module). In table mode the module is recompiled here every
time a row changes, so what the server runs and what actions.json serves is
always the table as last saved; in expert mode the module is what the owner
wrote and the rows are left alone.

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
from formshare.processes.actions.compiler import (
    AGGREGATES,
    Catalogue,
    CompileError,
    EMPTY_MODULE,
    compile_module,
)
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
    "get_action_mode",
    "set_action_mode",
    "get_action_module",
    "set_expert_module",
    "recompile_form_module",
    "actions_json",
    "build_catalogue",
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
    }
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
    try:
        compile_module([dict(row, action_order=0)], catalogue)
    except CompileError as e:
        return False, None, str(e)
    return True, row, ""


def add_form_action(request, project_id, form_id, data):
    """Adds a row at the end of the table and recompiles. Returns
    (ok, action_id or message)."""
    catalogue = build_catalogue(request, project_id, form_id)
    ok, row, message = _check_row(request, project_id, form_id, data, catalogue)
    if not ok:
        return False, message
    existing = get_form_actions(request, project_id, form_id)
    order = max([int(a["action_order"] or 0) for a in existing] + [0]) + 1
    action_id = str(uuid.uuid4())
    try:
        request.dbsession.add(
            PropertyAction(
                action_id=action_id,
                project_id=project_id,
                form_id=form_id,
                action_order=order,
                action_cdate=datetime.datetime.now(),
                **row
            )
        )
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} adding an action to form {}".format(str(e), form_id))
        return False, str(e)
    ok, message = recompile_form_module(request, project_id, form_id, catalogue)
    if not ok:
        return False, message
    return True, action_id


def update_form_action(request, project_id, form_id, action_id, data):
    catalogue = build_catalogue(request, project_id, form_id)
    ok, row, message = _check_row(request, project_id, form_id, data, catalogue)
    if not ok:
        return False, message
    try:
        request.dbsession.query(PropertyAction).filter(
            PropertyAction.project_id == project_id
        ).filter(PropertyAction.form_id == form_id).filter(
            PropertyAction.action_id == action_id
        ).update(
            row
        )
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} updating action {}".format(str(e), action_id))
        return False, str(e)
    return recompile_form_module(request, project_id, form_id, catalogue)


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


def set_action_mode(request, project_id, form_id, mode):
    """Switches the form between table and expert mode. Going to expert
    seeds the editor with the compiled module when nothing was written yet;
    going back to table recompiles from the rows as last saved -- a module
    never becomes rows (decision 16)."""
    if mode not in ("table", "expert"):
        return False, "Unknown mode"
    form = _form(request, project_id, form_id)
    if form is None:
        return False, "No such form"
    try:
        form.action_mode = mode
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        return False, str(e)
    if mode == "table":
        return recompile_form_module(request, project_id, form_id)
    return True, ""


def set_expert_module(request, project_id, form_id, module):
    """Stores a module written by hand; the form is in expert mode from
    then on. The module is loaded once to refuse one that no host could run
    (no default function, too large)."""
    from formshare.processes.actions.host import load_module, ModuleError

    module = module or ""
    if module.strip() != "":
        try:
            load_module(module)
        except ModuleError as e:
            return False, str(e)
    form = _form(request, project_id, form_id)
    if form is None:
        return False, "No such form"
    try:
        form.action_mode = "expert"
        form.action_module = module
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        return False, str(e)
    return True, ""


def recompile_form_module(request, project_id, form_id, catalogue=None):
    """Compiles the rows into the form's module, in table mode. In expert
    mode the module is the owner's and is left alone."""
    form = _form(request, project_id, form_id)
    if form is None:
        return False, "No such form"
    if (form.action_mode or "table") == "expert":
        return True, ""
    rows = get_form_actions(request, project_id, form_id)
    if catalogue is None:
        catalogue = build_catalogue(request, project_id, form_id)
    try:
        module = compile_module(rows, catalogue)
    except CompileError as e:
        return False, str(e)
    try:
        form.action_module = module
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
    return catalogue


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
        if entry["type"] in ("date", "datetime"):
            item["placeholder"] = (
                "YYYY-MM-DD" if entry["type"] == "date" else "YYYY-MM-DD HH:MM:SS"
            )
        filters.append(item)
    return filters
