"""The server side of a run: the input from the repository, the writes into
it, the record of what happened (actions-api.md; formshare.md section 3.3).

``run_for_submission`` is the one entry point: called by ``store_json_file``
and ``push_revision`` right after JSONToMySQL returned 0, by the logs page
for a retry, and by the actions screen for a dry run. It assembles the
input from the repository (typed as the contract says), runs the module --
in RSTools' runactions when it is installed, in the interim engine
otherwise -- validates each write against the type of its target and turns
it into the value MySQL will hold, applies the writes that change something
in one transaction with the audit user set -- or, for a dry run, applies
nothing -- and records the run with a report of what is stored. A failure
after a successful load never reaches the submission: it is recorded and
shown beside the load errors, with a retry.

The input is built the way RSTools' MirrorInput builds it over the device's
SQLite (rstools.md 13.4), so that a module sees the same objects on both:
every stored column of a row but the control columns and the ``_rowid``
keys -- never what MySQL generates -- a continuation's columns folded into
the row it continues, a multi-select's codes in their order, repeat rows in
the order of their ``_rowid``, the lookups by code with the last row winning.
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
    js_string,
    lookups_named,
    run_module,
    writes_from_changes,
    _same,
)
from formshare.processes.db.actions import (
    CONTROL_COLUMNS,
    case_source_of,
    continuations_of,
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
    "store_value",
    "engine_path",
]

log = logging.getLogger("formshare")

_MSEL = re.compile(r"_msel_")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# ASCII digits, the whole text: \d is any script's digit in Python 3, and $
# lets a final newline through (rstools.md 15.4 b). Used with fullmatch.
_DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")
_DATETIME = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})"
)
_INT_MIN, _INT_MAX = -2147483648, 2147483647

# A property's type as a column: what the module sees, the characters a text
# holds, the places a number keeps and the digits before its point
# (processes/db/case_management.py, PROPERTY_TYPES).
_PROPERTY_COLUMN = {
    "string": ("string", 255, 0, 0),
    "integer": ("integer", 0, 0, 0),
    "decimal": ("double", 0, 3, 7),
    "date": ("date", 0, 0, 0),
    "datetime": ("datetime", 0, 0, 0),
    "geopoint": ("geopoint", 80, 0, 0),
    "geotrace": ("geotrace", 0, 0, 0),
    "geoshape": ("geoshape", 0, 0, 0),
}


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
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value).decode("utf-8", "replace")
    if js_type == "integer":
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                number = float(value)
            except (TypeError, ValueError):
                return None
            return int(number) if number.is_integer() else None
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
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, decimal.Decimal):
        return float(value)
    return str(value)


def render(value):
    """A value as JavaScript's String() spells it, for the change report;
    a date as its ISO text; NULL as None."""
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, decimal.Decimal):
        return js_string(float(value))
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return js_string(value)


# ---------------------------------------------------------------------------
# The dictionary and the stored columns
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


class _Reader:
    """What one run reads, with what it learns about a table kept for the
    rest of the run: the columns MySQL stores (never the ones it generates:
    the geometry of a trace or of a GeoJSON lookup would come back as WKB,
    rstools.md 13.4) and the type a module sees each one as."""

    def __init__(self, request):
        self.request = request
        self._columns = {}
        self._types = {}

    def columns(self, schema, table):
        """[(column, data type)] a table stores, in order; [] when there is
        no such table."""
        key = (schema, table)
        if key not in self._columns:
            rows = self.request.dbsession.execute(
                text(
                    "SELECT COLUMN_NAME, DATA_TYPE, EXTRA FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = :s AND TABLE_NAME = :t ORDER BY ORDINAL_POSITION"
                ),
                {"s": schema, "t": table},
            ).fetchall()
            self._columns[key] = [
                (r[0], r[1]) for r in rows if "GENERATED" not in (r[2] or "").upper()
            ]
        return self._columns[key]

    def types(self, project_id, form_id, schema, table):
        """{column: js type}, by the dictionary; a column the dictionary does
        not name is typed by what MySQL stores."""
        key = (project_id, form_id, schema, table)
        if key not in self._types:
            out = {}
            for column, data_type in self.columns(schema, table):
                out[column] = js_type_of(data_type)
            for a_field in _fields(self.request, project_id, form_id, table):
                name = a_field["field_name"]
                odk_type = (a_field.get("field_odktype") or "").lower()
                if odk_type == "select all that apply":
                    out[name] = "string"
                elif name in out:
                    out[name] = js_type_of(a_field.get("field_type"), odk_type)
            self._types[key] = out
        return self._types[key]

    def select(self, schema, table, where, params, order_by=None):
        """The stored columns of the rows of a table, as dicts."""
        columns = [c for c, _ in self.columns(schema, table)]
        if not columns:
            raise ModuleError("The repository has no table {}".format(table))
        sql = "SELECT {} FROM {}.{} WHERE {}".format(
            ",".join(_q(c) for c in columns), _q(schema), _q(table), where
        )
        if order_by:
            sql = sql + " ORDER BY " + _q(order_by)
        result = self.request.dbsession.execute(text(sql), params)
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def has_column(self, schema, table, column):
        return any(c == column for c, _ in self.columns(schema, table))


def _row_values(row, types):
    """{column: typed} of a row, the control columns and the keys left out."""
    values = {}
    for column, value in row.items():
        if column in CONTROL_COLUMNS or column.endswith("_rowid"):
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


def _submission_input(reader, project_id, form_id, schema, main_rowuuid):
    request = reader.request
    tables = _tables(request, project_id, form_id)
    extended = continuations_of(request, project_id, form_id)
    main_rows = reader.select(schema, "maintable", "rowuuid = :r", {"r": main_rowuuid})
    if not main_rows:
        raise ModuleError(
            "The submission's row {} is not in the repository".format(main_rowuuid)
        )
    main = main_rows[0]

    # A continuation row is not one a module meets: what it holds belongs to
    # the row it continues, named by link_rowuuid.
    continued_by = {}
    extra = {}
    for ext_table in sorted(extended):
        types = reader.types(project_id, form_id, schema, ext_table)
        for row in reader.select(
            schema, ext_table, "root_rowuuid = :r", {"r": main_rowuuid}
        ):
            link = row.get("link_rowuuid")
            if not link:
                continue
            continued_by[row.get("rowuuid")] = link
            extra.setdefault(link, {}).update(_row_values(row, types))

    # A multi-select's codes, in their order, attributed to the row they hang
    # off -- through link_rowuuid when that row is a continuation's.
    selections = {}
    for a_table in tables:
        name = a_table["table_name"]
        if a_table.get("table_lkp") or not _MSEL.search(name):
            continue
        variable = name.split("_msel_", 1)[1]
        if not reader.has_column(schema, name, variable):
            continue
        order = "rowindex" if reader.has_column(schema, name, "rowindex") else None
        sql = "SELECT parent_rowuuid, {} FROM {}.{} WHERE root_rowuuid = :r".format(
            _q(variable), _q(schema), _q(name)
        )
        if order:
            sql = sql + " ORDER BY rowindex"
        for parent, code in request.dbsession.execute(
            text(sql), {"r": main_rowuuid}
        ).fetchall():
            if parent is None:
                continue
            owner = continued_by.get(parent, parent)
            selections.setdefault(owner, {}).setdefault(variable, []).append(
                "" if code is None else str(code)
            )

    repeats = [
        a_table
        for a_table in tables
        if a_table["table_name"] != "maintable"
        and not a_table.get("table_lkp")
        and not _MSEL.search(a_table["table_name"])
        and a_table["table_name"] not in extended
        and a_table.get("parent_table")
    ]

    def module_parent(a_table):
        """What a repeat hangs off in the module's eyes: a continuation
        stands for the table it continues."""
        parent = a_table.get("parent_table")
        while parent in extended:
            parent = extended[parent]
        return parent

    def node(row, types):
        uuid_ = row.get("rowuuid")
        values = _row_values(row, types)
        values.update(extra.get(uuid_, {}))
        return {
            "rowuuid": uuid_,
            "parent_rowuuid": row.get("parent_rowuuid"),
            "values": values,
            "repeats": {},
            "selections": selections.get(uuid_, {}),
        }

    children = {}
    for a_table in repeats:
        name = a_table["table_name"]
        types = reader.types(project_id, form_id, schema, name)
        order = (
            name + "_rowid"
            if reader.has_column(schema, name, name + "_rowid")
            else None
        )
        for row in reader.select(
            schema, name, "root_rowuuid = :r", {"r": main_rowuuid}, order
        ):
            parent = row.get("parent_rowuuid")
            children.setdefault((name, continued_by.get(parent, parent)), []).append(
                node(row, types)
            )

    def attach(a_node, table_name):
        for a_table in repeats:
            if module_parent(a_table) != table_name:
                continue
            rows = children.get((a_table["table_name"], a_node["rowuuid"]), [])
            for a_row in rows:
                attach(a_row, a_table["table_name"])
            a_node["repeats"][a_table["table_name"]] = rows

    submission = node(main, reader.types(project_id, form_id, schema, "maintable"))
    submission["parent_rowuuid"] = None
    attach(submission, "maintable")
    submission["submitted_by"] = main.get("_submitted_by")
    submission["submitted_date"] = render(main.get("_submitted_date"))
    return submission, main


def _case_row(reader, source, table_name, rowuuid):
    """A row of the source repository with its properties, as the module's
    case object, or None."""
    schema = source["schema"]
    rows = reader.select(schema, table_name, "rowuuid = :r", {"r": rowuuid})
    if not rows:
        return None
    row = rows[0]
    types = reader.types(source["project"], source["form"], schema, table_name)
    properties = {}
    defined = get_table_properties(
        reader.request, source["project"], source["form"], table_name
    )
    if defined:
        prop_rows = reader.select(
            schema, table_name + "_properties", "rowuuid = :r", {"r": rowuuid}
        )
        prop_row = prop_rows[0] if prop_rows else {}
        for a_property in defined:
            name = a_property["property_name"]
            properties[name] = typed(
                prop_row.get(name),
                {
                    "integer": "integer",
                    "decimal": "double",
                    "date": "date",
                    "datetime": "datetime",
                }.get(a_property["property_type"], "string"),
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


def _case_input(reader, source, main):
    if source is None or not source.get("schema"):
        return None
    if source.get("selector_field"):
        selector = main.get(source["selector_field"])
        if selector is None or str(selector).strip() == "":
            return None
        rowuuid = str(selector).strip()
    else:
        # A form without a case link acts on its own rows.
        rowuuid = main.get("rowuuid")
    case = _case_row(reader, source, source["table"], rowuuid)
    if case is None:
        return None
    if source.get("parent_table") and case.get("parent_rowuuid"):
        case["parent"] = _case_row(
            reader, source, source["parent_table"], case["parent_rowuuid"]
        )
        if case["parent"] is not None:
            case["parent"].pop("parent_rowuuid", None)
    case.pop("parent_rowuuid", None)
    return case


def _lookup_tables(reader, module, places):
    """{list: {code: row}} for every list the module names, from the first
    place -- (schema, project, form) -- whose repository has it.

    A row is its data columns: the code, the label, the filter columns and
    whatever else the list carries -- not rowuuid, not the surrogate
    ``<list>_rowid`` a list with repeated codes is keyed by, and not what
    MySQL generates. Where a code repeats, the last row in the list's order
    is the one a code finds (actions-api.md 4.3)."""
    out = {}
    for name in lookups_named(module):
        if not _IDENT.match(name):
            continue
        table = "lkp" + name
        for schema, project_id, form_id in places:
            if not schema or not reader.columns(schema, table):
                continue
            code_column = name + "_cod"
            rowid = name + "_rowid"
            if reader.has_column(schema, table, rowid):
                order = rowid
            elif reader.has_column(schema, table, code_column):
                order = code_column
            else:
                order = None
            types = reader.types(project_id, form_id, schema, table)
            by_code = {}
            for row in reader.select(schema, table, "1 = 1", {}, order):
                code = row.get(code_column)
                if code is None:
                    continue
                by_code[str(code)] = {
                    column: typed(value, types.get(column, "string"))
                    for column, value in row.items()
                    if column != "rowuuid" and not column.endswith("_rowid")
                }
            out[name] = by_code
            break
    return out


def build_input(
    request, project_id, form_id, schema, main_rowuuid, module, user, now=None
):
    """The input of a run, assembled from the repository."""
    reader = _Reader(request)
    submission, main = _submission_input(
        reader, project_id, form_id, schema, main_rowuuid
    )
    source = case_source_of(request, project_id, form_id)
    if source is not None and source.get("own") and not source.get("schema"):
        source = dict(source, schema=schema)
    case = _case_input(reader, source, main)
    places = [(schema, project_id, form_id)]
    if source is not None and source.get("schema") and source["schema"] != schema:
        places.append((source["schema"], source["project"], source["form"]))
    lookups = _lookup_tables(reader, module, places)
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


def _real_date(year, month, day):
    try:
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        return False
    return True


def _round_to(number, places):
    """The Kotlin host's rounding, to the letter (Writes.roundTo): half to
    even on the scaled value, so that both hosts store the same digits."""
    factor = 1.0
    for _ in range(places):
        factor *= 10.0
    return round(number * factor) / factor


def store_value(js_type, value, what, name, size=0, decimals=0, digits=0):
    """What MySQL will hold for a write, or a ModuleError in the words the
    owner reads (actions-api.md 5).

    The same outcome as the Kotlin host's Writes.validate for every value
    both hosts are given (formshare/tests/resources/actions/store_values.json):
    a boolean is 1 or 0 for a number and true or false for a text; an integer
    must be whole and fit a MySQL int; a decimal is rounded to its places and
    must fit its digits; a date is YYYY-MM-DD and a date and time YYYY-MM-DD
    HH:MM:SS, both real; a text is spelled as JavaScript spells it and must
    fit its characters; a geopoint, trace or shape property is checked as its
    default is; null clears.
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        # Neither JavaScript's String() of it (1,2 and [object Object]) nor
        # Python's is anything a module means (rstools.md 15.4 c).
        raise ModuleError(
            "{} is not a value for {} {}".format(
                json.dumps(value, separators=(",", ":"), ensure_ascii=False),
                what,
                name,
            )
        )
    if isinstance(value, bool):
        as_text = (
            ("1" if value else "0")
            if js_type in ("integer", "double")
            else ("true" if value else "false")
        )
    elif isinstance(value, str):
        as_text = value
    else:
        as_text = js_string(value)
    if js_type in ("integer", "double"):
        stripped = as_text.strip()
        number = None
        if "_" not in stripped:
            try:
                number = float(stripped)
            except ValueError:
                number = None
        if (
            number is None
            or number != number
            or number in (float("inf"), float("-inf"))
        ):
            raise ModuleError(
                "{} is not {} for {} {}".format(
                    as_text,
                    "a whole number" if js_type == "integer" else "a number",
                    what,
                    name,
                )
            )
        if js_type == "integer":
            if not number.is_integer():
                raise ModuleError(
                    "{} is not a whole number for {} {}".format(as_text, what, name)
                )
            if not _INT_MIN <= number <= _INT_MAX:
                raise ModuleError(
                    "{} does not fit the {} {}, a whole number between {} and {}".format(
                        as_text, what, name, _INT_MIN, _INT_MAX
                    )
                )
            return int(number)
        rounded = _round_to(number, decimals or 3)
        if digits and abs(rounded) >= 10**digits:
            raise ModuleError(
                "{} does not fit the {} {}, which holds {} digits before the point".format(
                    as_text, what, name, digits
                )
            )
        return rounded
    if js_type == "date":
        found = _DATE.fullmatch(as_text)
        if not found or not _real_date(*found.groups()):
            raise ModuleError(
                "{} is not a date: use YYYY-MM-DD for {} {}".format(as_text, what, name)
            )
        return as_text
    if js_type == "datetime":
        found = _DATETIME.fullmatch(as_text)
        if (
            not found
            or not _real_date(*found.groups()[:3])
            or int(found.group(4)) > 23
            or int(found.group(5)) > 59
            or int(found.group(6)) > 59
        ):
            raise ModuleError(
                "{} is not a date and time: use YYYY-MM-DD HH:MM:SS for {} {}".format(
                    as_text, what, name
                )
            )
        return as_text
    if js_type in ("geopoint", "geotrace", "geoshape"):
        ok, normalised, message = validate_property_default(js_type, as_text)
        if not ok:
            raise ModuleError("{} for {} {}".format(message, what, name))
        return normalised
    if size and len(as_text) > size:
        raise ModuleError(
            "{} is longer than the {} characters {} {} holds".format(
                as_text, size, what, name
            )
        )
    return as_text


def _plan_writes(request, source, case, writes):
    """Every write validated and turned into what MySQL will hold, with the
    last write to a name winning, as dicts (table, rowuuid, column, value,
    old). A write that leaves the stored value as it was is left out: it
    would change nothing, and its UPDATE would still move _lastupdate and
    the audit log, and with them the list. Raises ModuleError; nothing is
    applied."""
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
            value = write.get("value")
            if isinstance(value, bool):
                value = 1 if value else 0
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = None
            if value not in (0.0, 1.0):
                raise ModuleError("_active takes 0 or 1")
            entry = {
                "table": table,
                "rowuuid": target["rowuuid"],
                "column": "_active",
                "value": int(value),
                "old": 1 if target.get("active", True) else 0,
                "numeric": True,
            }
        else:
            properties = {
                p["property_name"]: p["property_type"]
                for p in get_table_properties(
                    request, source["project"], source["form"], table
                )
            }
            if name in properties:
                js_type, size, decimals, digits = _PROPERTY_COLUMN.get(
                    properties[name], ("string", 255, 0, 0)
                )
                entry = {
                    "table": table + "_properties",
                    "rowuuid": target["rowuuid"],
                    "column": name,
                    "value": store_value(
                        js_type,
                        write.get("value"),
                        "property",
                        name,
                        size,
                        decimals,
                        digits,
                    ),
                    "old": (target.get("properties") or {}).get(name),
                    "numeric": js_type in ("integer", "double"),
                }
            else:
                fields = {
                    f["field_name"]: f
                    for f in _fields(request, source["project"], source["form"], table)
                }
                field = fields.get(name)
                if (
                    field is None
                    or field.get("field_generatedas")
                    or name in CONTROL_COLUMNS
                    or name.endswith("_rowid")
                ):
                    raise ModuleError(
                        "{} is neither a property nor a column of {}".format(
                            name, table
                        )
                    )
                decimals = int(field.get("field_decsize") or 0)
                size = int(field.get("field_size") or 0)
                field_type = (field.get("field_type") or "").lower()
                entry = {
                    "table": table,
                    "rowuuid": target["rowuuid"],
                    "column": name,
                    "value": store_value(
                        js_type_of(field_type),
                        write.get("value"),
                        "column",
                        name,
                        size if field_type.startswith("varchar") else 0,
                        decimals,
                        (size - decimals) if field_type == "decimal" and size else 0,
                    ),
                    "old": (target.get("values") or {}).get(name),
                    "numeric": js_type_of(field_type) in ("integer", "double"),
                }
        if not _same(entry["old"], entry["value"], entry.pop("numeric")):
            plan.append(entry)
    plan.sort(key=lambda e: (e["table"], e["column"]))
    return plan


def _stored_report(plan):
    """The change report of what the run stores (actions-api.md 9)."""
    return [
        {
            "scope": "source",
            "table": entry["table"],
            "rowuuid": entry["rowuuid"],
            "column": entry["column"],
            "old": render(entry["old"]),
            "new": render(entry["value"]),
        }
        for entry in plan
    ]


def _apply(request, schema, plan, user):
    """The writes, in one transaction, audited as the assistant."""
    request.dbsession.execute(text("SET @odktools_current_user = :u"), {"u": user})
    for entry in plan:
        request.dbsession.execute(
            text(
                "UPDATE {}.{} SET {} = :v WHERE rowuuid = :r".format(
                    _q(schema), _q(entry["table"]), _q(entry["column"])
                )
            ),
            {"v": entry["value"], "r": entry["rowuuid"]},
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
    Whatever goes wrong -- the module, the input, the database -- ends as a
    failure with its reason, never as an exception (actions-api.md 8).
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

    def fail(message, log_lines):
        try:
            request.dbsession.rollback()
        except Exception:  # pragma: no cover
            pass
        return _finish(
            request,
            project_id,
            form_id,
            submission_id,
            main_rowuuid,
            dry_run,
            run_id,
            message,
            [],
            log_lines,
        )

    try:
        inputs = build_input(
            request, project_id, form_id, schema, main_rowuuid, module, user
        )
    except ModuleError as e:
        return fail(str(e), [])
    except Exception as e:
        log.error(
            "The input of the actions of form {} could not be built for {}: {}".format(
                form_id, main_rowuuid, e
            )
        )
        return fail("The input could not be built: {}".format(e), [])
    source = inputs.pop("_source")
    try:
        result = run_module(module, inputs, engine=engine_path(request))
    except Exception as e:
        return fail("The engine failed: {}".format(e), [])
    if not result.ok:
        return fail(result.error, result.log)
    try:
        writes = result.writes
        if not writes and result.changes:
            writes = writes_from_changes(result.changes, inputs.get("case"))
        plan = _plan_writes(request, source, inputs.get("case"), writes)
        changes = _stored_report(plan)
    except ModuleError as e:
        return fail(str(e), result.log)
    except Exception as e:
        return fail("The writes could not be planned: {}".format(e), result.log)
    if not dry_run and plan:
        try:
            _apply(request, source["schema"], plan, user)
        except Exception as e:
            return fail("The writes could not be applied: {}".format(e), result.log)
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
