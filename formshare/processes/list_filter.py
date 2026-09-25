"""The filter of a published list (formshare.md 3.8 and 8.1).

A list serves the active rows of its source table. Its filter narrows that
to the rows the owner means -- the teachers still in post, the schools of
one district -- and it is the same for every assistant: the per-assistant
filters of feature 7 are another matter. The owner builds it in jQuery
QueryBuilder over the source table's columns and its properties. The rule
set is kept as the owner built it (``publishedlist.filter_rules``), and this
module compiles it to the WHERE fragment ``build_list_select`` appends
(``publishedlist.filter_sql``).

**Two databases run the fragment.** MySQL generates the list on the server,
and SQLite runs the same SELECT, served in ``lists.xml``, over a device's
mirror for the rows the device has not sent yet (``kotlincollect.md`` 5.3).
The two must answer the same, so the compiler writes only what both read
alike:

- **A text is compared by its UTF-8 bytes**, ``HEX(col) = '<hex>'``. The
  repository's collation (``utf8mb4_unicode_ci``) ignores case and trailing
  spaces, and SQLite's does neither, so ``'Left' = 'left '`` would hold on the
  server and not on the phone. Bytes are bytes on both.
  - For the same reason a text has no ordering operators.
  - A text has no "contains": a hex substring can straddle two characters.
  - "Begins with" and "ends with" are exact on the hex, which is aligned at
    either end.
  - "Is empty" is ``HEX(col) = ''``, so a value of spaces is not empty on
    either.
- **A number is a number**, unquoted.
- **A date, or a date and time, is its ISO text.** MySQL reads it as a date,
  and SQLite compares it as text in the same order.
- **A comparison with NULL is false**, as in SQL, on both: the negative
  operators say ``IS NOT NULL`` first, so that a row without the value is
  not let in by a "not".

**Nothing the owner types reaches the SQL as SQL.** The QueryBuilder JSON is
a closed grammar: every field is one of the table's columns or properties,
every operator one of a known set, and every value is checked against its
type and written as a hex, a number or an ISO date. That is why this is
admissible where free text is not.

The fragment names a column as ``{t}`name``` and a property as
``{p}`name```. ``build_list_select`` resolves the two markers to its own
aliases (``resolve``), and joins the properties table when the filter reads
a property (``uses_properties``).
"""

import datetime
import json
import re
from decimal import Decimal, InvalidOperation

__all__ = [
    "FilterError",
    "column_kind",
    "property_kind",
    "filter_fields",
    "compile_filter",
    "describe_filter",
    "querybuilder_filters",
    "referenced_properties",
    "uses_properties",
    "resolve",
]

TEXT, NUMBER, DATE, DATETIME, GEO = "text", "number", "date", "datetime", "geo"

# What each kind of field may be compared with, and how many values each
# operator takes ("list" for one or more).
_ARITY = {
    "equal": 1,
    "not_equal": 1,
    "less": 1,
    "less_or_equal": 1,
    "greater": 1,
    "greater_or_equal": 1,
    "between": 2,
    "not_between": 2,
    "in": "list",
    "not_in": "list",
    "begins_with": 1,
    "not_begins_with": 1,
    "ends_with": 1,
    "not_ends_with": 1,
    "is_empty": 0,
    "is_not_empty": 0,
    "is_null": 0,
    "is_not_null": 0,
}
_ORDERED = [
    "equal",
    "not_equal",
    "less",
    "less_or_equal",
    "greater",
    "greater_or_equal",
    "between",
    "not_between",
]
OPERATORS = {
    TEXT: [
        "equal",
        "not_equal",
        "in",
        "not_in",
        "begins_with",
        "not_begins_with",
        "ends_with",
        "not_ends_with",
        "is_empty",
        "is_not_empty",
        "is_null",
        "is_not_null",
    ],
    NUMBER: _ORDERED + ["in", "not_in", "is_null", "is_not_null"],
    DATE: _ORDERED + ["is_null", "is_not_null"],
    DATETIME: _ORDERED + ["is_null", "is_not_null"],
    GEO: ["is_empty", "is_not_empty", "is_null", "is_not_null"],
}

_WORDS = {
    "equal": "is",
    "not_equal": "is not",
    "less": "is less than",
    "less_or_equal": "is at most",
    "greater": "is greater than",
    "greater_or_equal": "is at least",
    "between": "is between",
    "not_between": "is not between",
    "in": "is one of",
    "not_in": "is none of",
    "begins_with": "begins with",
    "not_begins_with": "does not begin with",
    "ends_with": "ends with",
    "not_ends_with": "does not end with",
    "is_empty": "is empty",
    "is_not_empty": "is not empty",
    "is_null": "has no value",
    "is_not_null": "has a value",
}

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Columns the server and a device do not hold alike, which a filter may not
# read, or the list would answer differently on the phone: the server's own
# ids for a submission, the loader's bookkeeping, and -- by their leading
# underscore -- the clocks and the stamp (_lastupdate moves by each host's
# clock, _submitted_date is when each host saw the submission). An
# autoincrement key (<table>_rowid) is numbered by the server alone. The two
# links, parent_rowuuid and root_rowuuid, are derived from the nesting the
# same way on both, and stay: they are what a cascade filters on.
_NOT_THE_SAME = {"link_rowuuid", "surveyid", "originid", "instanceid", "rowindex"}
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DATETIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")
_GEO_TYPES = ("geopoint", "geotrace", "geoshape")


class FilterError(ValueError):
    """A rule the compiler cannot turn into SQL, with the reason in words
    the owner can act on."""


# ---------------------------------------------------------------------------
# The fields
# ---------------------------------------------------------------------------


def column_kind(field_type, odk_type=None):
    """The kind of a column of the source table, from the dictionary."""
    odk = (odk_type or "").strip().lower()
    if odk in _GEO_TYPES:
        return GEO
    kind = (field_type or "").strip().lower().split("(")[0]
    if kind in (
        "int",
        "integer",
        "bigint",
        "smallint",
        "tinyint",
        "decimal",
        "double",
        "float",
    ):
        return NUMBER
    if kind == "date":
        return DATE
    if kind in ("datetime", "timestamp"):
        return DATETIME
    return TEXT


def property_kind(property_type):
    """The kind of a property, from its FormShare type."""
    return {
        "integer": NUMBER,
        "decimal": NUMBER,
        "date": DATE,
        "datetime": DATETIME,
        "geopoint": GEO,
        "geotrace": GEO,
        "geoshape": GEO,
    }.get((property_type or "").strip().lower(), TEXT)


def filter_fields(columns, properties):
    """What a filter may read, by field id: ``t.<column>`` for a column of
    the source table and ``p.<property>`` for a property.

    ``columns`` are dictionary rows (``field_name``, ``field_type``,
    ``field_odktype``, ``field_generatedas``, ``field_rtable``), as
    ``get_table_columns`` returns them, and ``properties`` are
    ``get_table_properties`` rows (``property_name``, ``property_type``).

    Left out:
    - a column the server and a device do not hold alike (``_NOT_THE_SAME``,
      anything with a leading underscore, an autoincrement ``<table>_rowid``);
      ``_active`` has a setting of its own on the list anyway;
    - a column MySQL generates for itself (the ``_geom`` of a trace) does not
      exist in a device's mirror, so a filter on it could not run there.
    """
    fields = {}
    for a_column in columns or []:
        name = a_column.get("field_name") or ""
        if not _NAME.match(name) or name.startswith("_"):
            continue
        if name in _NOT_THE_SAME or name.endswith("_rowid"):
            continue
        if a_column.get("field_generatedas"):
            continue
        fields["t." + name] = {
            "name": name,
            "source": "table",
            "kind": column_kind(
                a_column.get("field_type"), a_column.get("field_odktype")
            ),
            "label": name,
            "lookup": a_column.get("field_rtable"),
            "integer": (a_column.get("field_type") or "").lower().startswith("int"),
        }
    for a_property in properties or []:
        name = a_property.get("property_name") or ""
        if not _NAME.match(name):
            continue
        fields["p." + name] = {
            "name": name,
            "source": "property",
            "kind": property_kind(a_property.get("property_type")),
            "label": name,
            "lookup": None,
            "integer": (a_property.get("property_type") or "") == "integer",
        }
    return fields


# ---------------------------------------------------------------------------
# The values
# ---------------------------------------------------------------------------


def _values(rule, operator):
    """The rule's values as a list, whatever shape QueryBuilder saved: a
    list, one value, or for "one of" a comma-separated text."""
    value = rule.get("value")
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [v for v in value if v is not None]
    if _ARITY[operator] == "list" and isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip() != ""]
    return [value]


def _hex(value):
    return "'" + str(value).encode("utf-8").hex().upper() + "'"


def _number(value, integer):
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise FilterError('"{}" is not a number'.format(value))
    if not number.is_finite():
        raise FilterError('"{}" is not a number'.format(value))
    if integer and number != number.to_integral_value():
        raise FilterError('"{}" is not a whole number'.format(value))
    return format(number, "f")


def _date(value, kind):
    text = str(value).strip()
    if kind == DATE:
        if not _DATE.fullmatch(text):
            raise FilterError('"{}" is not a date (YYYY-MM-DD)'.format(value))
        try:
            datetime.date.fromisoformat(text)
        except ValueError:
            raise FilterError('"{}" is not a date'.format(value))
    else:
        if not _DATETIME.fullmatch(text):
            raise FilterError(
                '"{}" is not a date and time (YYYY-MM-DD HH:MM:SS)'.format(value)
            )
        try:
            datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise FilterError('"{}" is not a date and time'.format(value))
    return "'" + text + "'"


def _literal(value, field):
    kind = field["kind"]
    if kind == NUMBER:
        return _number(value, field.get("integer"))
    if kind in (DATE, DATETIME):
        return _date(value, kind)
    return _hex(value)


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------


def _reference(field):
    marker = "{p}" if field["source"] == "property" else "{t}"
    return marker + "`" + field["name"] + "`"


def _rule_sql(rule, fields):
    field_id = rule.get("field") or rule.get("id")
    field = fields.get(field_id)
    if field is None:
        raise FilterError("The list's table has no field {}".format(field_id))
    operator = rule.get("operator", "equal")
    if operator not in OPERATORS[field["kind"]]:
        raise FilterError(
            '"{}" does not apply to {}'.format(
                _WORDS.get(operator, operator), field["label"]
            )
        )
    values = _values(rule, operator)
    arity = _ARITY[operator]
    if arity == "list":
        if not values:
            raise FilterError("{} needs at least one value".format(field["label"]))
    elif len(values) < arity:
        raise FilterError("{} needs {} value(s)".format(field["label"], arity))

    ref = _reference(field)
    kind = field["kind"]
    not_null = ref + " IS NOT NULL AND "

    if operator == "is_null":
        return ref + " IS NULL"
    if operator == "is_not_null":
        return ref + " IS NOT NULL"
    if operator == "is_empty":
        return "HEX(" + ref + ") = ''"
    if operator == "is_not_empty":
        return "(" + not_null + "HEX(" + ref + ") <> '')"

    literals = [_literal(v, field) for v in values]
    # A text is compared by its bytes; everything else as itself.
    left = "HEX(" + ref + ")" if kind == TEXT else ref

    if operator == "equal":
        return "{} = {}".format(left, literals[0])
    if operator == "not_equal":
        return "({}{} <> {})".format(not_null, left, literals[0])
    if operator == "in":
        return "{} IN ({})".format(left, ",".join(literals))
    if operator == "not_in":
        return "({}{} NOT IN ({}))".format(not_null, left, ",".join(literals))
    if operator in ("less", "less_or_equal", "greater", "greater_or_equal"):
        symbol = {
            "less": "<",
            "less_or_equal": "<=",
            "greater": ">",
            "greater_or_equal": ">=",
        }[operator]
        return "{} {} {}".format(left, symbol, literals[0])
    if operator == "between":
        return "({} >= {} AND {} <= {})".format(left, literals[0], left, literals[1])
    if operator == "not_between":
        return "({}({} < {} OR {} > {}))".format(
            not_null, left, literals[0], left, literals[1]
        )
    # The hex of a text is aligned at either end, so a prefix or a suffix of
    # the value's bytes is a prefix or a suffix of its hex, and never half a
    # character. Its digits are no LIKE wildcards.
    digits = literals[0][1:-1]
    if operator == "begins_with":
        return "{} LIKE '{}%'".format(left, digits)
    if operator == "not_begins_with":
        return "({}{} NOT LIKE '{}%')".format(not_null, left, digits)
    if operator == "ends_with":
        return "{} LIKE '%{}'".format(left, digits)
    if operator == "not_ends_with":
        return "({}{} NOT LIKE '%{}')".format(not_null, left, digits)
    raise FilterError("Unknown operator {}".format(operator))  # pragma: no cover


def _parse(rules):
    if rules is None or rules == "":
        return None
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except ValueError:
            raise FilterError("The filter is not valid JSON")
    if not isinstance(rules, dict):
        raise FilterError("The filter is not a rule set")
    return rules


def _group_sql(rules, fields):
    if "rules" in rules:
        parts = [_group_sql(r, fields) for r in rules.get("rules") or []]
        parts = [p for p in parts if p]
        if not parts:
            return None
        joiner = (
            " OR " if str(rules.get("condition", "AND")).upper() == "OR" else " AND "
        )
        sql = "(" + joiner.join(parts) + ")" if len(parts) > 1 else parts[0]
        if rules.get("not"):
            sql = "NOT (" + sql + ")"
        return sql
    return _rule_sql(rules, fields)


def compile_filter(rules, fields):
    """The WHERE fragment of a QueryBuilder rule set, with the ``{t}`` and
    ``{p}`` markers left for ``build_list_select``. None for no filter: an
    empty rule set, or none."""
    rules = _parse(rules)
    if rules is None:
        return None
    return _group_sql(rules, fields)


def describe_filter(rules, fields):
    """The filter in words, as the list's page shows it; "" for none."""
    rules = _parse(rules)
    if rules is None:
        return ""

    def words(node):
        if "rules" in node:
            parts = [w for w in (words(r) for r in node.get("rules") or []) if w]
            if not parts:
                return ""
            joiner = (
                " or " if str(node.get("condition", "AND")).upper() == "OR" else " and "
            )
            text = joiner.join(parts)
            if len(parts) > 1:
                text = "(" + text + ")"
            return "not " + text if node.get("not") else text
        field_id = node.get("field") or node.get("id")
        field = fields.get(field_id, {"label": field_id, "source": "table"})
        operator = node.get("operator", "equal")
        name = ("property " if field.get("source") == "property" else "") + str(
            field.get("label")
        )
        values = _values(node, operator) if operator in _ARITY else []
        shown = ", ".join("'{}'".format(v) for v in values)
        if operator in ("between", "not_between") and len(values) == 2:
            shown = "'{}' and '{}'".format(values[0], values[1])
        return " ".join(p for p in (name, _WORDS.get(operator, operator), shown) if p)

    return words(rules)


# ---------------------------------------------------------------------------
# The editor
# ---------------------------------------------------------------------------


def querybuilder_filters(fields, choices=None):
    """The ``filters`` option of QueryBuilder for the list's editor: every
    field with its type, its operators, and for a select column the codes
    of its choice list (``choices``: {field id: [{"code", "label"}]})."""
    choices = choices or {}
    out = []
    for field_id, field in fields.items():
        kind = field["kind"]
        item = {
            "id": field_id,
            "label": field["label"],
            "optgroup": "Properties" if field["source"] == "property" else "Columns",
            "operators": OPERATORS[kind],
        }
        if kind == NUMBER:
            item["type"] = "integer" if field.get("integer") else "double"
        elif kind == DATE:
            item["type"] = "date"
            item["placeholder"] = "YYYY-MM-DD"
        elif kind == DATETIME:
            item["type"] = "datetime"
            item["placeholder"] = "YYYY-MM-DD HH:MM:SS"
        else:
            item["type"] = "string"
        if kind in (TEXT, NUMBER):
            item["value_separator"] = ","
        if choices.get(field_id):
            item["input"] = "select"
            item["values"] = [
                {c["code"]: c.get("label") or c["code"]} for c in choices[field_id]
            ]
            item.pop("value_separator", None)
        out.append(item)
    return out


def referenced_properties(rules):
    """The names of the properties a rule set reads."""
    try:
        rules = _parse(rules)
    except FilterError:
        return set()
    found = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        if "rules" in node:
            for r in node.get("rules") or []:
                walk(r)
            return
        field_id = str(node.get("field") or node.get("id") or "")
        if field_id.startswith("p."):
            found.add(field_id[2:])

    if rules is not None:
        walk(rules)
    return found


def uses_properties(filter_sql):
    """Whether a compiled filter reads a property, so that the SELECT
    joins ``<table>_properties``."""
    return bool(filter_sql) and "{p}" in filter_sql


def resolve(filter_sql, table_prefix):
    """The fragment with its markers replaced by the SELECT's aliases:
    ``table_prefix`` for a column ("t." when the SELECT joins the
    properties, "" when it does not) and "p." for a property."""
    return filter_sql.replace("{t}", table_prefix).replace("{p}", "p.")
