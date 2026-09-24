"""The decision table becomes the module (actions-api.md section 10).

Pure: rows and a field catalogue in, JavaScript text out. Nothing here
reads a database or a request; the catalogue says what every field is (its
JavaScript spelling and its type) and what every target is (its type), so
that the compiler can refuse a row it cannot spell rather than emit code
that fails at run time on a device.

The code is written to be read: one block per row with a comment restating
the row in words, one ``if / else if`` chain per target so that the
table's rule -- first match wins per target -- holds by construction.

The *when* of a row is jQuery QueryBuilder's rule JSON::

    {"condition": "AND", "rules": [
        {"id": "v.still_working", "operator": "equal", "value": "no"},
        {"condition": "OR", "not": true, "rules": [...]}]}

compiled to one boolean expression. A null on either side of a comparison
makes the rule false, never an error, which is SQL's answer and the one a
survey designer expects: an unanswered question matches nothing.
"""

import json
import re

__all__ = [
    "CompileError",
    "compile_module",
    "compile_when",
    "describe_when",
    "EMPTY_MODULE",
    "AGGREGATES",
    "OPERATORS",
]

# What a computed value may be, over a column of one repeat.
AGGREGATES = ("avg", "sum", "count", "min", "max")

# QueryBuilder's operators, the ones the compiler accepts, with how many
# values each takes.
OPERATORS = {
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
    "contains": 1,
    "not_contains": 1,
    "is_empty": 0,
    "is_not_empty": 0,
    "is_null": 0,
    "is_not_null": 0,
}

_WORDS = {
    "equal": "equals",
    "not_equal": "does not equal",
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
    "contains": "contains",
    "not_contains": "does not contain",
    "is_empty": "is empty",
    "is_not_empty": "is not empty",
    "is_null": "is not answered",
    "is_not_null": "is answered",
}

# The types a field or a target may declare, and whether a literal of that
# type is a number in the module.
_NUMERIC = ("integer", "double", "decimal", "int")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# What a form without actions serves: nothing to run (actions-api.md 2).
EMPTY_MODULE = ""


class CompileError(ValueError):
    """A row the compiler cannot turn into code, with the reason in words
    the owner can act on."""


# ---------------------------------------------------------------------------
# Spelling
# ---------------------------------------------------------------------------


def _js_string(value):
    """A JavaScript string literal (JSON's is one)."""
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def _literal(value, field_type):
    """A literal of the field's type, or a CompileError."""
    if value is None:
        return "null"
    if field_type in _NUMERIC:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise CompileError('"{}" is not a number'.format(value))
        if field_type in ("integer", "int"):
            if number != int(number):
                raise CompileError('"{}" is not a whole number'.format(value))
            return str(int(number))
        return repr(number) if not number.is_integer() else str(int(number))
    if field_type == "boolean":
        return "true" if str(value).lower() in ("1", "true", "yes") else "false"
    return _js_string(value)


def _member(base, name):
    """``base.name`` when the name is an identifier, ``base["name"]`` otherwise."""
    if _IDENTIFIER.match(name or ""):
        return "{}.{}".format(base, name)
    return "{}[{}]".format(base, _js_string(name))


def _target_object(scope):
    if scope == "parent":
        return "api.case.parent"
    return "api.case"


# ---------------------------------------------------------------------------
# The catalogue
# ---------------------------------------------------------------------------


class Catalogue:
    """What the compiler may spell.

    ``fields``: {field_id: {"js": expression, "type": type, "multi": bool,
    "label": words}} -- every field QueryBuilder may name, by its id.
    ``targets``: {(scope, kind, name): type}. ``repeats``: {repeat_name:
    {column: type}} for computed values. Built by processes/db/actions.py
    from the dictionary and the registry; the compiler only reads it.
    """

    def __init__(self, fields=None, targets=None, repeats=None):
        self.fields = fields or {}
        self.targets = targets or {}
        self.repeats = repeats or {}

    def field(self, field_id):
        if field_id not in self.fields:
            raise CompileError("The form has no field {}".format(field_id))
        return self.fields[field_id]

    def target_type(self, scope, kind, name):
        if kind == "active":
            return "integer"
        key = (scope, kind, name)
        if key not in self.targets:
            what = "property" if kind == "property" else "column"
            where = "the case's parent" if scope == "parent" else "the case"
            raise CompileError("{} has no {} {}".format(where, what, name))
        return self.targets[key]


# ---------------------------------------------------------------------------
# The when
# ---------------------------------------------------------------------------


def _values(rule):
    """The rule's values as a list, whatever shape QueryBuilder saved."""
    value = rule.get("value")
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _rule_js(rule, catalogue):
    field_id = rule.get("field") or rule.get("id")
    field = catalogue.field(field_id)
    operator = rule.get("operator", "equal")
    if operator not in OPERATORS:
        raise CompileError("Unknown operator {}".format(operator))
    js = field["js"]
    ftype = field.get("type", "string")
    values = _values(rule)
    arity = OPERATORS[operator]
    if arity == "list":
        if not values:
            raise CompileError("{} needs at least one value".format(operator))
    elif len(values) < arity:
        raise CompileError("{} needs {} value(s)".format(operator, arity))
    literals = [_literal(v, ftype) for v in values]

    if field.get("multi"):
        # A multi-select: membership, never a comparison.
        variable = field["variable"]
        sel = "s.selections({})".format(_js_string(variable))
        one = lambda lit: "s.selected({}, {})".format(_js_string(variable), lit)
        if operator in ("equal", "contains", "in"):
            return "(" + " || ".join(one(lit) for lit in literals) + ")"
        if operator in ("not_equal", "not_contains", "not_in"):
            return "!(" + " || ".join(one(lit) for lit in literals) + ")"
        if operator in ("is_empty", "is_null"):
            return "({}.length === 0)".format(sel)
        if operator in ("is_not_empty", "is_not_null"):
            return "({}.length > 0)".format(sel)
        raise CompileError("{} does not apply to a multi-select".format(operator))

    guard = "{} !== null".format(js)
    if operator == "equal":
        return "({} === {})".format(js, literals[0])
    if operator == "not_equal":
        return "({} && {} !== {})".format(guard, js, literals[0])
    if operator == "less":
        return "({} && {} < {})".format(guard, js, literals[0])
    if operator == "less_or_equal":
        return "({} && {} <= {})".format(guard, js, literals[0])
    if operator == "greater":
        return "({} && {} > {})".format(guard, js, literals[0])
    if operator == "greater_or_equal":
        return "({} && {} >= {})".format(guard, js, literals[0])
    if operator == "between":
        return "({} && {} >= {} && {} <= {})".format(
            guard, js, literals[0], js, literals[1]
        )
    if operator == "not_between":
        return "({} && ({} < {} || {} > {}))".format(
            guard, js, literals[0], js, literals[1]
        )
    if operator == "in":
        return "({} && [{}].includes({}))".format(guard, ", ".join(literals), js)
    if operator == "not_in":
        return "({} && ![{}].includes({}))".format(guard, ", ".join(literals), js)
    text = "String({})".format(js)
    if operator == "begins_with":
        return "({} && {}.startsWith({}))".format(guard, text, literals[0])
    if operator == "not_begins_with":
        return "({} && !{}.startsWith({}))".format(guard, text, literals[0])
    if operator == "ends_with":
        return "({} && {}.endsWith({}))".format(guard, text, literals[0])
    if operator == "not_ends_with":
        return "({} && !{}.endsWith({}))".format(guard, text, literals[0])
    if operator == "contains":
        return "({} && {}.includes({}))".format(guard, text, literals[0])
    if operator == "not_contains":
        return "({} && !{}.includes({}))".format(guard, text, literals[0])
    if operator == "is_empty":
        return '({} === "")'.format(js)
    if operator == "is_not_empty":
        return '({} && {} !== "")'.format(guard, js)
    if operator == "is_null":
        return "({} === null)".format(js)
    if operator == "is_not_null":
        return "({})".format(guard)
    raise CompileError("Unknown operator {}".format(operator))  # pragma: no cover


def compile_when(rules, catalogue):
    """One boolean expression for a QueryBuilder rule set; ``true`` for
    None (always)."""
    if not rules:
        return "true"
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except ValueError:
            raise CompileError("The condition is not valid JSON")
    if "rules" in rules:
        parts = [compile_when(r, catalogue) for r in rules.get("rules", [])]
        if not parts:
            return "true"
        joiner = (
            " || " if str(rules.get("condition", "AND")).upper() == "OR" else " && "
        )
        expression = "(" + joiner.join(parts) + ")" if len(parts) > 1 else parts[0]
        if rules.get("not"):
            expression = "!" + expression
        return expression
    return _rule_js(rules, catalogue)


def describe_when(rules, catalogue):
    """The condition in words, for the comment above the row."""
    if not rules:
        return "always"
    if isinstance(rules, str):
        rules = json.loads(rules)
    if "rules" in rules:
        inner = rules.get("rules", [])
        words = " {} ".format(str(rules.get("condition", "AND")).lower()).join(
            describe_when(r, catalogue) for r in inner
        )
        if len(inner) > 1:
            words = "(" + words + ")"
        return ("not " + words) if rules.get("not") else words
    field = catalogue.field(rules.get("field") or rules.get("id"))
    operator = rules.get("operator", "equal")
    values = _values(rules)
    label = field.get("label") or (rules.get("field") or rules.get("id"))
    if OPERATORS.get(operator) == 0:
        return "{} {}".format(label, _WORDS[operator])
    quote = "" if field.get("type") in _NUMERIC else "'"
    shown = ", ".join("{0}{1}{0}".format(quote, v) for v in values)
    if operator in ("between", "not_between") and len(values) == 2:
        shown = "{0}{1}{0} and {0}{2}{0}".format(quote, values[0], values[1])
    return "{} {} {}".format(label, _WORDS[operator], shown)


# ---------------------------------------------------------------------------
# The value and the target
# ---------------------------------------------------------------------------


def _computed(spec, catalogue, hoisted):
    """An aggregate over a repeat as a hoisted constant; returns its name."""
    if isinstance(spec, str):
        try:
            spec = json.loads(spec)
        except ValueError:
            raise CompileError("The computed value is not valid JSON")
    aggregate = spec.get("aggregate")
    repeat = spec.get("repeat")
    column = spec.get("column")
    if aggregate not in AGGREGATES:
        raise CompileError("Unknown aggregate {}".format(aggregate))
    if repeat not in catalogue.repeats:
        raise CompileError("The form has no repeat {}".format(repeat))
    if column not in catalogue.repeats[repeat]:
        raise CompileError("The repeat {} has no column {}".format(repeat, column))
    rows = "s.repeat({})".format(_js_string(repeat))
    condition = spec.get("filter")
    if condition:
        # The filter reads the repeat's own columns, spelled on the row.
        inner = Catalogue(
            fields={
                "r." + name: {"js": _member("r", name), "type": ctype, "label": name}
                for name, ctype in catalogue.repeats[repeat].items()
            }
        )
        rows = "{}.filter(r => {})".format(rows, compile_when(condition, inner))
    name = "{}_{}_{}".format(aggregate, repeat, column)
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    expression = "api.{}({}, {})".format(aggregate, rows, _js_string(column))
    hoisted[name] = expression
    return name


def _value_js(row, target_type, catalogue, hoisted):
    kind = row.get("value_kind")
    value = row.get("value")
    if kind == "constant":
        if value is None or str(value) == "":
            return "null"
        return _literal(value, target_type)
    if kind == "variable":
        if not value or ("v." + str(value)) not in catalogue.fields:
            raise CompileError("The form has no variable {}".format(value))
        return catalogue.fields["v." + str(value)]["js"]
    if kind == "now":
        return "api.now"
    if kind == "computed":
        return _computed(value, catalogue, hoisted)
    raise CompileError("Unknown value kind {}".format(kind))


def _value_words(row):
    kind = row.get("value_kind")
    value = row.get("value")
    if kind == "constant":
        return "'{}'".format(value) if value not in (None, "") else "empty"
    if kind == "variable":
        return "the answer to {}".format(value)
    if kind == "now":
        return "now"
    if kind == "computed":
        spec = json.loads(value) if isinstance(value, str) else (value or {})
        words = "the {} of {}.{}".format(
            {
                "avg": "average",
                "sum": "sum",
                "count": "count",
                "min": "minimum",
                "max": "maximum",
            }.get(spec.get("aggregate"), spec.get("aggregate")),
            spec.get("repeat"),
            spec.get("column"),
        )
        if spec.get("filter"):
            words += " where ..."
        return words
    return str(value)


def _condition(expression):
    """``if (x)`` without a second pair of parentheses when the expression
    already wears one."""
    if expression.startswith("(") and expression.endswith(")"):
        depth = 0
        for index, char in enumerate(expression):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(expression) - 1:
                    return "(" + expression + ")"
        return expression
    return "(" + expression + ")"


def _target_key(row):
    scope = row.get("target_scope") or "case"
    kind = row.get("target_kind")
    if kind == "active":
        return (scope, "active", "")
    return (scope, kind, row.get("target_name") or "")


def _action_js(row, catalogue, hoisted):
    scope = row.get("target_scope") or "case"
    kind = row.get("target_kind")
    obj = _target_object(scope)
    if kind == "active":
        wanted = str(row.get("target_name") or "0").strip()
        return "{}.{}();".format(obj, "activate" if wanted == "1" else "deactivate")
    if kind not in ("property", "column"):
        raise CompileError("Unknown target kind {}".format(kind))
    name = row.get("target_name") or ""
    target_type = catalogue.target_type(scope, kind, name)
    return "{}.set({}, {});".format(
        obj, _js_string(name), _value_js(row, target_type, catalogue, hoisted)
    )


def _action_words(row):
    scope = "the case's parent" if (row.get("target_scope") == "parent") else "the case"
    kind = row.get("target_kind")
    if kind == "active":
        wanted = str(row.get("target_name") or "0").strip()
        return "{} {}".format("reactivate" if wanted == "1" else "deactivate", scope)
    return "set {} {} of {} to {}".format(
        "property" if kind == "property" else "column",
        row.get("target_name"),
        scope,
        _value_words(row),
    )


# ---------------------------------------------------------------------------
# The module
# ---------------------------------------------------------------------------


def compile_module(rows, catalogue):
    """The module for the rows of a decision table, in action_order.

    Rows are grouped by target, keeping their order inside each group, and
    each group is one if / else if chain: the first row whose condition
    holds is the one applied to that target. Every row is restated in words
    above its code. Raises CompileError for a row that cannot be spelled.
    """
    rows = sorted(rows, key=lambda r: int(r.get("action_order") or 0))
    if not rows:
        return EMPTY_MODULE
    groups = []
    by_key = {}
    for number, row in enumerate(rows, 1):
        key = _target_key(row)
        if key not in by_key:
            by_key[key] = []
            groups.append(key)
        by_key[key].append((number, row))

    hoisted = {}
    blocks = []
    for key in groups:
        scope = key[0]
        lines = []
        first = True
        for number, row in by_key[key]:
            rules = row.get("when_rules")
            if isinstance(rules, str) and rules.strip() == "":
                rules = None
            condition = compile_when(rules, catalogue)
            words = describe_when(rules, catalogue)
            action = _action_js(row, catalogue, hoisted)
            if condition == "true":
                lines.append(
                    "  // Row {}: {}, {}".format(
                        number, "always" if first else "otherwise", _action_words(row)
                    )
                )
                if first:
                    lines.append("  {}".format(action))
                else:
                    lines.append("  else {{ {} }}".format(action))
                # A row that always matches ends its target's chain.
                break
            lines.append(
                "  // Row {}: when {}, {}".format(number, words, _action_words(row))
            )
            lines.append(
                "  {}if {} {{ {} }}".format(
                    "" if first else "else ", _condition(condition), action
                )
            )
            first = False
        block = "\n".join(lines)
        if scope == "parent":
            block = (
                "  if (api.case.parent !== null) {\n"
                + "\n".join("  " + line for line in lines)
                + "\n  }"
            )
        blocks.append(block)

    out = ["export default function run(s, api) {"]
    out.append("  if (api.case === null) { return; }")
    for name, expression in hoisted.items():
        out.append("  const {} = {};".format(name, expression))
    for block in blocks:
        out.append(block)
    out.append("}")
    return "\n".join(out) + "\n"
