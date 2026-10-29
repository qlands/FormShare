"""Actions without a server: the compiler, the QuickJS host and the golden
triples (docs/formshare_case_management/actions-api.md).

The compiler is a pure function of the decision table and a catalogue; the
host runs a module over an input dict and never touches a database. So
everything the contract promises about the generated code, the sandbox and
the change report is checked here in a fraction of a second, and the
golden triples under tests/resources/actions/golden are the same files the
Kotlin host is checked against.
"""

import json
import os

import pytest

from formshare.processes.actions.compiler import (
    AGGREGATES,
    Catalogue,
    CompileError,
    EMPTY_MODULE,
    OPERATORS,
    compile_module,
    compile_when,
    describe_action,
    describe_when,
    explain_failure,
    locate_line,
    names_read,
    rule_module,
)
from formshare.processes.actions.host import (
    LIMITS,
    ModuleError,
    changes_of,
    load_module,
    lookups_named,
    run_module,
)

GOLDEN = os.path.join(os.path.dirname(__file__), "resources", "actions", "golden")


def rule(field, operator, value=None):
    return {"id": field, "field": field, "operator": operator, "value": value}


def group(*rules, condition="AND", negate=False):
    out = {"condition": condition, "rules": list(rules)}
    if negate:
        out["not"] = True
    return out


@pytest.fixture
def catalogue():
    return Catalogue(
        fields={
            "v.still_working": {
                "js": "s.still_working",
                "type": "string",
                "label": "still_working",
            },
            "v.trained": {"js": "s.trained", "type": "string", "label": "trained"},
            "v.years": {"js": "s.years", "type": "integer", "label": "years"},
            "v.weight": {"js": "s.weight", "type": "double", "label": "weight"},
            "v.when": {"js": "s.when", "type": "date", "label": "when"},
            "v.crops": {
                "js": "s.crops",
                "type": "string",
                "label": "crops",
                "multi": True,
                "variable": "crops",
            },
            "v.odd-name": {
                "js": 's["odd-name"]',
                "type": "string",
                "label": "odd-name",
            },
            "p.status": {
                "js": 'api.case.property("status")',
                "type": "string",
                "label": "case status",
            },
            "pp.count": {
                "js": 'api.case.parent.property("count")',
                "type": "integer",
                "label": "parent count",
            },
        },
        targets={
            ("case", "property", "status"): "string",
            ("case", "property", "trained"): "integer",
            ("case", "property", "index"): "decimal",
            ("case", "property", "seen"): "date",
            ("case", "column", "teacher_name"): "string",
            ("parent", "property", "count"): "integer",
        },
        repeats={"meals": {"score": "decimal", "weight": "decimal", "kind": "string"}},
    )


def row(order, kind, name, value_kind="constant", value=None, when=None, scope="case"):
    return {
        "action_order": order,
        "target_scope": scope,
        "target_kind": kind,
        "target_name": name,
        "value_kind": value_kind,
        "value": value,
        "when_rules": json.dumps(when) if when is not None else None,
    }


# ---------------------------------------------------------------------------
# compile_when
# ---------------------------------------------------------------------------


def test_a_failure_names_the_line_as_written():
    """Taking export default off a module keeps every line where it was,
    blank lines above it included: the editor marks the line a failure
    names."""
    body = (
        "export default function run(s, api) {\n"
        "  api.log(1);\n"
        '  throw new Error("here");\n'
        "}\n"
    )
    a_input = {
        "submission": {"rowuuid": "r", "values": {}},
        "case": None,
        "lookups": {},
        "now": "2026-10-19 10:00:00",
        "user": "u",
    }
    for above in ("", "\n\n", "  \n\t\n", "// a comment\n\n"):
        result = run_module(above + body, a_input)
        assert result.error == "Error: here (line {})".format(3 + above.count("\n")), (
            above,
            result.error,
        )


def test_every_operator_compiles_and_is_null_safe(catalogue):
    expectations = {
        "equal": "(s.years === 3)",
        "not_equal": "(s.years !== null && s.years !== 3)",
        "less": "(s.years !== null && s.years < 3)",
        "less_or_equal": "(s.years !== null && s.years <= 3)",
        "greater": "(s.years !== null && s.years > 3)",
        "greater_or_equal": "(s.years !== null && s.years >= 3)",
        "is_null": "(s.years === null)",
        "is_not_null": "(s.years !== null)",
    }
    for operator, expected in expectations.items():
        assert compile_when(group(rule("v.years", operator, 3)), catalogue) == expected
    assert compile_when(group(rule("v.years", "between", [1, 5])), catalogue) == (
        "(s.years !== null && s.years >= 1 && s.years <= 5)"
    )
    assert compile_when(group(rule("v.years", "not_between", [1, 5])), catalogue) == (
        "(s.years !== null && (s.years < 1 || s.years > 5))"
    )
    assert compile_when(group(rule("v.years", "in", [1, 2])), catalogue) == (
        "(s.years !== null && [1, 2].includes(s.years))"
    )
    assert compile_when(group(rule("v.years", "not_in", [1, 2])), catalogue) == (
        "(s.years !== null && ![1, 2].includes(s.years))"
    )
    strings = {
        "begins_with": '(s.trained !== null && String(s.trained).startsWith("y"))',
        "not_begins_with": '(s.trained !== null && !String(s.trained).startsWith("y"))',
        "ends_with": '(s.trained !== null && String(s.trained).endsWith("y"))',
        "not_ends_with": '(s.trained !== null && !String(s.trained).endsWith("y"))',
        "contains": '(s.trained !== null && String(s.trained).includes("y"))',
        "not_contains": '(s.trained !== null && !String(s.trained).includes("y"))',
    }
    for operator, expected in strings.items():
        assert (
            compile_when(group(rule("v.trained", operator, "y")), catalogue) == expected
        )
    assert (
        compile_when(group(rule("v.trained", "is_empty")), catalogue)
        == '(s.trained === "")'
    )
    assert compile_when(group(rule("v.trained", "is_not_empty")), catalogue) == (
        '(s.trained !== null && s.trained !== "")'
    )
    assert set(expectations) | set(strings) | {
        "between",
        "not_between",
        "in",
        "not_in",
        "is_empty",
        "is_not_empty",
    } == set(OPERATORS)


def test_groups_nest_and_negate(catalogue):
    rules = group(
        rule("p.status", "equal", "pending"),
        group(
            rule("v.trained", "equal", "yes"),
            rule("v.years", "greater_or_equal", 3),
            condition="OR",
        ),
        group(rule("v.still_working", "equal", "no"), negate=True),
    )
    assert compile_when(rules, catalogue) == (
        '((api.case.property("status") === "pending") && '
        '((s.trained === "yes") || (s.years !== null && s.years >= 3)) && '
        '!(s.still_working === "no"))'
    )
    assert describe_when(rules, catalogue) == (
        "(case status equals 'pending' and (trained equals 'yes' or years is at least 3) "
        "and not still_working equals 'no')"
    )


def test_when_accepts_json_text_and_always(catalogue):
    assert compile_when(None, catalogue) == "true"
    assert compile_when("", catalogue) == "true"
    assert describe_when(None, catalogue) == "always"
    assert compile_when(
        json.dumps(group(rule("v.trained", "equal", "yes"))), catalogue
    ) == ('(s.trained === "yes")')
    with pytest.raises(CompileError):
        compile_when("{not json", catalogue)


def test_multi_select_is_membership(catalogue):
    assert compile_when(group(rule("v.crops", "in", ["c1", "c3"])), catalogue) == (
        '(s.selected("crops", "c1") || s.selected("crops", "c3"))'
    )
    assert compile_when(group(rule("v.crops", "not_in", ["c1"])), catalogue) == (
        '!(s.selected("crops", "c1"))'
    )
    assert compile_when(group(rule("v.crops", "equal", "c2")), catalogue) == (
        '(s.selected("crops", "c2"))'
    )
    assert compile_when(group(rule("v.crops", "is_empty")), catalogue) == (
        '(s.selections("crops").length === 0)'
    )
    with pytest.raises(CompileError):
        compile_when(group(rule("v.crops", "greater", "c2")), catalogue)


def test_literals_follow_the_field_type(catalogue):
    assert compile_when(group(rule("v.when", "greater", "2026-01-01")), catalogue) == (
        '(s.when !== null && s.when > "2026-01-01")'
    )
    assert compile_when(group(rule("v.weight", "less", "2.5")), catalogue) == (
        "(s.weight !== null && s.weight < 2.5)"
    )
    assert compile_when(group(rule("v.odd-name", "equal", "x")), catalogue) == (
        '(s["odd-name"] === "x")'
    )
    with pytest.raises(CompileError):
        compile_when(group(rule("v.years", "equal", "three")), catalogue)
    with pytest.raises(CompileError):
        compile_when(group(rule("v.years", "equal", "2.5")), catalogue)
    with pytest.raises(CompileError):
        compile_when(group(rule("v.nope", "equal", "x")), catalogue)
    with pytest.raises(CompileError):
        compile_when(group(rule("v.years", "between", [1])), catalogue)
    with pytest.raises(CompileError):
        compile_when(group(rule("v.years", "in", [])), catalogue)
    with pytest.raises(CompileError):
        compile_when(group(rule("v.years", "like", 1)), catalogue)


# ---------------------------------------------------------------------------
# compile_module
# ---------------------------------------------------------------------------


def test_empty_table_is_the_empty_module(catalogue):
    assert compile_module([], catalogue) == EMPTY_MODULE


def _host_input(values, properties=None, parent=None):
    return {
        "submission": {"rowuuid": "S", "values": values, "repeats": {}},
        "case": {
            "table": "teachers",
            "rowuuid": "T1",
            "active": True,
            "values": {"teacher_name": "A"},
            "properties": dict({"status": None}, **(properties or {})),
            "parent": parent,
        },
        "now": "2026-10-20 10:00:00",
        "user": "u",
        "lookups": {},
    }


def _kept(result):
    """What a host applies: the last write to each name (actions-api.md 5)."""
    kept = {}
    for write in result.writes:
        name = "_active" if write["kind"] == "active" else write["name"]
        kept[(write["scope"], name)] = write["value"]
    return kept


def test_the_first_action_wins_a_target(catalogue):
    rows = [
        row(
            1,
            "property",
            "status",
            value="interviewed",
            when=group(rule("v.trained", "equal", "yes")),
        ),
        row(
            2,
            "property",
            "trained",
            value="1",
            when=group(rule("v.years", "greater", 2)),
        ),
        row(3, "property", "status", value="seen"),
        row(
            4,
            "property",
            "status",
            value="never",
            when=group(rule("v.trained", "equal", "no")),
        ),
    ]
    module = compile_module(rows, catalogue)
    assert module.startswith("export default function run(s, api) {\n")
    # Each action is a function of its own, and run calls them from the last
    # to the first, so that the first one's write is the one kept.
    calls = [line.strip() for line in module.split("\n")[3:7]]
    assert calls == [
        "__fs_action_4(s, api);",
        "__fs_action_3(s, api);",
        "__fs_action_2(s, api);",
        "__fs_action_1(s, api);",
    ]
    assert (
        "// Action 1: when trained equals 'yes', set property status of the case "
        "to 'interviewed'\nfunction __fs_action_1(s, api) {\n"
        "  if (api.case === null) { return; }\n"
        '  if (s.trained === "yes") { api.case.set("status", "interviewed"); }\n}'
        in module
    )
    assert "// Action 3: always, set property status of the case to 'seen'" in module
    assert (
        '  if (s.years !== null && s.years > 2) { api.case.set("trained", 1); }'
        in module
    )
    # Rule 1 when it holds; else rule 3, an always above rule 4's "never" --
    # the table's rule as it always was.
    yes = run_module(module, _host_input({"trained": "yes", "years": 1}))
    no = run_module(module, _host_input({"trained": "no", "years": 3}))
    assert yes.ok and no.ok, (yes.error, no.error)
    assert _kept(yes) == {("case", "status"): "interviewed"}
    assert _kept(no) == {("case", "status"): "seen", ("case", "trained"): 1}


def test_code_composes_with_rules(catalogue):
    helper = (
        "function label(x) { return 'from code ' + x; }\n"
        "export default function run(s, api) {\n"
        '  api.case.set("status", label(1));\n'
        "  api.log(label(2));\n"
        "}\n"
    )
    other = (
        "function label(x) { return 'other ' + x; }\n"
        "export default function run(s, api) {\n"
        '  api.case.set("status", label(3));\n'
        "}\n"
    )
    rows = [
        row(
            1,
            "property",
            "status",
            value="rule",
            when=group(rule("v.years", "greater", 2)),
        ),
        dict(
            action_order=2,
            action_kind="code",
            action_code=helper,
            action_desc="a\nhelper",
        ),
        dict(action_order=3, action_kind="code", action_code=other),
    ]
    module = compile_module(rows, catalogue)
    # Code keeps its helpers to itself: two of the same name do not collide.
    assert (
        "// Action 2, written by hand: a helper\nconst __fs_action_2 = (function () {"
        in module
    )
    assert (
        "// Action 3, written by hand\nconst __fs_action_3 = (function () {" in module
    )
    assert "export default" not in module.split("\n", 1)[1]
    ruled = run_module(module, _host_input({"years": 3}))
    coded = run_module(module, _host_input({"years": 1}))
    assert ruled.ok and coded.ok, (ruled.error, coded.error)
    assert _kept(ruled) == {("case", "status"): "rule"}
    assert _kept(coded) == {("case", "status"): "from code 1"}
    assert coded.log == ["from code 2"]
    assert describe_action(rows[1], catalogue) == "a helper"
    assert describe_action(rows[2], catalogue) == ""


def test_a_failure_names_its_action_and_line(catalogue):
    code = (
        "export default function run(s, api) {\n"
        "  api.log('before');\n"
        "  throw new Error('stop here');\n"
        "}\n"
    )
    rows = [
        row(1, "property", "status", value="x"),
        dict(action_order=2, action_kind="code", action_code=code),
    ]
    module = compile_module(rows, catalogue)
    result = run_module(module, _host_input({}))
    assert not result.ok
    assert result.error.startswith("Error: stop here (line ")
    assert explain_failure(module, result.error) == (
        "Error: stop here (action 2, line 3)",
        2,
        3,
    )
    # An action tested alone keeps the number the list gives it.
    alone = compile_module([dict(rows[1], action_number=5)], catalogue)
    failed = run_module(alone, _host_input({}))
    assert explain_failure(alone, failed.error)[0] == (
        "Error: stop here (action 5, line 3)"
    )
    # A rule has no line of its own; a module that marks no action, its own.
    assert locate_line(
        module, module.split("\n").index("function __fs_action_1(s, api) {") + 2
    ) == (1, None)
    assert explain_failure(code, "Error: x (line 3)") == ("Error: x (line 3)", None, 3)
    assert explain_failure(module, "no line here") == ("no line here", None, None)


def test_a_comment_like_an_action_inside_code_is_not_one(catalogue):
    code = (
        "export default function run(s, api) {\n"
        "// Action 1: when this, that\n"
        "  throw new Error('x');\n"
        "}\n"
    )
    module = compile_module(
        [dict(action_order=1, action_kind="code", action_code=code)], catalogue
    )
    line = module.split("\n").index("  throw new Error('x');") + 1
    assert locate_line(module, line) == (1, 3)


def test_what_an_action_says_cannot_become_code(catalogue):
    # A comment that a line break ended would make the rest of the line code:
    # JavaScript ends a line at U+2028 and U+2029 too.
    sneaky = "x\n}; api.case.deactivate(); {\u2028y\u2029z"
    module = compile_module(
        [
            dict(row(1, "property", "status", value=sneaky), action_desc=sneaky),
            dict(
                action_order=2,
                action_kind="code",
                action_desc="said\ntwice",
                action_code="export default function run(s, api) {}",
            ),
        ],
        catalogue,
    )
    lines = module.split("\n")
    first = [i for i, line in enumerate(lines) if line.startswith("// Action 1:")][0]
    assert lines[first] == "// Action 1: x }; api.case.deactivate(); { y z"
    assert lines[first + 1] == "function __fs_action_1(s, api) {"
    assert "// Action 2, written by hand: said twice" in lines
    assert "\u2028" not in module and "\u2029" not in module
    result = run_module(module, _host_input({}))
    assert result.ok, result.error
    assert _kept(result) == {("case", "status"): sneaky}


def test_a_rule_as_a_module_of_its_own(catalogue):
    a_rule = row(1, "active", "0", when=group(rule("v.still_working", "equal", "no")))
    module = rule_module(a_rule, catalogue)
    assert module == (
        "export default function run(s, api) {\n"
        "  // when still_working equals 'no', deactivate the case\n"
        "  if (api.case === null) { return; }\n"
        '  if (s.still_working === "no") { api.case.deactivate(); }\n'
        "}\n"
    )
    result = run_module(module, _host_input({"still_working": "no"}))
    assert result.ok and result.writes == [
        {"scope": "case", "kind": "active", "value": 0}
    ]


def test_what_an_action_does_is_what_its_author_said(catalogue):
    a_rule = row(1, "active", "0", when=group(rule("v.still_working", "equal", "no")))
    said = dict(a_rule, action_desc="Deactivates a teacher\nwho left")
    assert describe_action(said, catalogue) == "Deactivates a teacher who left"
    # The module says it above the action, and so does See code
    lines = compile_module([said], catalogue).split("\n")
    first = lines.index("// Action 1: Deactivates a teacher who left")
    assert lines[first + 1] == "function __fs_action_1(s, api) {"
    assert rule_module(said, catalogue).split("\n")[1] == (
        "  // Deactivates a teacher who left"
    )
    # A rule saved before a description was asked for reads in its own words
    assert describe_action(a_rule, catalogue) == (
        "when still_working equals 'no', deactivate the case"
    )


class _Translating:
    @staticmethod
    def translate(text):
        return text


def test_an_action_must_say_what_it_does(catalogue):
    from formshare.processes.db.actions import _check_code, _check_row, _rule_values

    data = {
        "action_desc": "  Deactivates a teacher\r\n who left  ",
        "target_kind": "active",
        "target_name": "0",
        "when_rules": json.dumps(group(rule("v.still_working", "equal", "no"))),
    }
    ok, a_row, message = _check_row(_Translating(), "P", "visit", data, catalogue)
    assert ok, message
    # One line, of at most 255 characters
    assert _rule_values(a_row)["action_desc"] == "Deactivates a teacher who left"
    ok, a_row, message = _check_row(
        _Translating(), "P", "visit", dict(data, action_desc="x" * 300), catalogue
    )
    assert ok and a_row["action_desc"] == "x" * 255, message
    code = "export default function run(s, api) {}"
    ok, values, message = _check_code(_Translating(), code, " Counts\na visit ")
    assert ok and values["action_desc"] == "Counts a visit", message
    # Neither a rule nor code is kept without one
    for given in ("   ", "", None):
        assert _check_row(
            _Translating(), "P", "visit", dict(data, action_desc=given), catalogue
        ) == (False, None, "Describe the action in a few words")
        assert _check_code(_Translating(), code, given) == (
            False,
            None,
            "Describe the action in a few words",
        )


def test_what_an_action_reads():
    assert names_read(
        row(
            1,
            "property",
            "status",
            value_kind="variable",
            value="name",
            when=group(
                rule("v.q", "equal", "1"),
                rule("d.v.visit", "greater", 3),
                rule("c.avg.meals.score", "greater", 3),
                rule("p.status", "equal", "x"),
            ),
        )
    ) == (["q", "visit", "name"], ["meals"])
    code = (
        "export default function run(sub, a) {\n"
        '  if (sub.age > 3 && sub.selected("crops", "c1")) {\n'
        '    a.case.set("x", a.avg(sub.repeat("meals"), "score"));\n'
        "  }\n"
        "  var other = {}; other.zzz; sub.rowuuid;\n"
        "  if (sub[\"odd-name\"] === 'x' || sub[ 'rowuuid' ]) { other['q']; }\n"
        "}\n"
    )
    # A name that is not an identifier is read through brackets
    assert names_read(dict(action_kind="code", action_code=code)) == (
        ["age", "odd-name", "crops"],
        ["meals"],
    )
    # A form without a case link is its own case: a column of the case is
    # then one of the answers typed for the test, and asked for first
    by_column = row(1, "active", "0", when=group(rule("k.district", "equal", "N")))
    assert names_read(by_column) == ([], [])
    assert names_read(by_column, own=True) == (["district"], [])
    code = (
        "export default function run(s, api) {\n"
        '  if (api.case.value("district") === "N") { api.case.deactivate(); }\n'
        "}\n"
    )
    assert names_read(dict(action_kind="code", action_code=code)) == ([], [])
    assert names_read(dict(action_kind="code", action_code=code), own=True) == (
        ["district"],
        [],
    )


def test_targets_values_and_the_parent(catalogue):
    module = compile_module(
        [
            row(1, "active", "0", when=group(rule("v.still_working", "equal", "no"))),
            row(2, "active", "1", when=group(rule("v.still_working", "equal", "back"))),
            row(3, "property", "seen", value_kind="now"),
            row(4, "column", "teacher_name", value_kind="variable", value="trained"),
            row(
                5,
                "property",
                "count",
                value="7",
                scope="parent",
                when=group(rule("pp.count", "less", 7)),
            ),
            row(
                6,
                "property",
                "index",
                value_kind="computed",
                value=json.dumps(
                    {
                        "aggregate": "avg",
                        "repeat": "meals",
                        "column": "score",
                        "filter": group(
                            rule("r.weight", "greater", 0),
                            rule("r.kind", "equal", "main"),
                        ),
                    }
                ),
            ),
        ],
        catalogue,
    )
    assert '  if (s.still_working === "no") { api.case.deactivate(); }\n' in module
    assert '  if (s.still_working === "back") { api.case.activate(); }\n' in module
    assert "// Action 1: when still_working equals 'no', deactivate the case" in module
    assert (
        "// Action 2: when still_working equals 'back', reactivate the case" in module
    )
    assert '  api.case.set("seen", api.now);\n' in module
    assert '  api.case.set("teacher_name", s.trained);\n' in module
    assert (
        "function __fs_action_5(s, api) {\n"
        "  if (api.case === null || api.case.parent === null) { return; }\n" in module
    )
    assert (
        '  if (api.case.parent.property("count") !== null && api.case.parent.property("count") < 7) { api.case.parent.set("count", 7); }'
        in module
    )
    assert (
        '  const avg_meals_score = api.avg(s.repeat("meals").filter(r => ((r.weight !== null && r.weight > 0) && (r.kind === "main"))), "score");\n'
        in module
    )
    assert '  api.case.set("index", avg_meals_score);\n' in module
    assert "the average of meals.score where ..." in module


def test_rows_the_compiler_refuses(catalogue):
    bad = [
        row(1, "property", "nope", value="x"),
        row(1, "column", "nope", value="x"),
        row(1, "property", "count", value="x", scope="parent"),
        row(1, "property", "trained", value="many"),
        row(1, "property", "status", value_kind="variable", value="nope"),
        row(1, "property", "status", value_kind="magic", value="x"),
        row(
            1,
            "property",
            "index",
            value_kind="computed",
            value=json.dumps(
                {"aggregate": "median", "repeat": "meals", "column": "score"}
            ),
        ),
        row(
            1,
            "property",
            "index",
            value_kind="computed",
            value=json.dumps({"aggregate": "avg", "repeat": "nope", "column": "score"}),
        ),
        row(
            1,
            "property",
            "index",
            value_kind="computed",
            value=json.dumps({"aggregate": "avg", "repeat": "meals", "column": "nope"}),
        ),
        row(1, "property", "index", value_kind="computed", value="{bad"),
        row(1, "wish", "status", value="x"),
    ]
    for a_row in bad:
        with pytest.raises(CompileError):
            compile_module([a_row], catalogue)
    assert AGGREGATES == ("avg", "sum", "count", "min", "max")


def test_generated_module_runs_in_the_host(catalogue):
    module = compile_module(
        [
            row(1, "active", "0", when=group(rule("v.still_working", "equal", "no"))),
            row(
                2,
                "property",
                "status",
                value="interviewed",
                when=group(rule("p.status", "equal", "pending")),
            ),
            row(
                3,
                "property",
                "index",
                value_kind="computed",
                value=json.dumps(
                    {"aggregate": "sum", "repeat": "meals", "column": "score"}
                ),
            ),
            row(4, "property", "count", value_kind="now", scope="parent"),
        ],
        catalogue,
    )
    inputs = {
        "submission": {
            "rowuuid": "S",
            "values": {"still_working": "no", "trained": "yes", "years": 4},
            "repeats": {
                "meals": [
                    {"rowuuid": "m1", "values": {"score": 1.5, "weight": 1}},
                    {"rowuuid": "m2", "values": {"score": None, "weight": 1}},
                    {"rowuuid": "m3", "values": {"score": 2, "weight": 1}},
                ]
            },
        },
        "case": {
            "table": "teachers",
            "rowuuid": "T1",
            "active": True,
            "values": {"teacher_name": "A"},
            "properties": {"status": "pending", "index": None},
            "parent": None,
        },
        "now": "2026-09-23 10:00:00",
        "user": "u",
        "lookups": {},
    }
    result = run_module(module, inputs)
    assert result.ok, result.error
    # From the last action to the first; the parent's has no parent to write.
    assert result.writes == [
        {"scope": "case", "kind": "set", "name": "index", "value": 3.5},
        {"scope": "case", "kind": "set", "name": "status", "value": "interviewed"},
        {"scope": "case", "kind": "active", "value": 0},
    ]


# ---------------------------------------------------------------------------
# The host
# ---------------------------------------------------------------------------


def base_input(**extra):
    inputs = {
        "submission": {
            "rowuuid": "S1",
            "values": {"a": 1, "name": "x"},
            "repeats": {},
            "selections": {"crops": ["c1", "c3"]},
            "submitted_by": "tester",
            "submitted_date": "2026-09-23 09:00:00",
        },
        "case": {
            "table": "t",
            "rowuuid": "C1",
            "active": True,
            "values": {"col": "v"},
            "properties": {"p": 0, "q": "old"},
            "parent": {
                "table": "m",
                "rowuuid": "P1",
                "active": True,
                "values": {},
                "properties": {"n": 1},
            },
        },
        "lookups": {"crop_list": {"c1": {"crop_list_des": "Maize", "tlu": 2.5}}},
        "now": "2026-09-23 10:00:00",
        "user": "u",
    }
    inputs.update(extra)
    return inputs


def run(source, **extra):
    return run_module(
        "export default function run(s, api) {\n" + source + "\n}", base_input(**extra)
    )


def test_load_module_takes_export_default_off():
    assert (
        load_module("export default function run(s, api) { }").strip()
        == "function run(s, api) { }"
    )
    assert (
        load_module("  export default function run(s, api) {}\n").strip()
        == "function run(s, api) {}"
    )
    for bad in (
        "",
        None,
        "function run(s, api) {}",
        "export default function go(s, api) {}",
    ):
        with pytest.raises(ModuleError):
            load_module(bad)
    with pytest.raises(ModuleError):
        load_module(
            "export default function run(s, api) {" + " " * LIMITS["source_bytes"] + "}"
        )


def test_reads_are_what_the_contract_says():
    result = run(
        "api.log(s.a); api.log(s.name); api.log(s.rowuuid); api.log(s.submittedBy);"
        'api.log(s.selected("crops", "c3")); api.log(s.selected("crops", "c2")); api.log(s.selections("crops").join(","));'
        'api.log(s.repeat("none").length);'
        'api.log(api.case.value("col")); api.log(api.case.property("p")); api.log(api.case.active);'
        'api.log(api.case.parent.property("n")); api.log(api.case.parent.parent);'
        'api.log(api.lookup("crop_list", "c1").tlu); api.log(api.lookup("crop_list", "zz"));'
        "api.log(api.now); api.log(api.user);"
    )
    assert result.ok, result.error
    assert result.log == [
        "1",
        "x",
        "S1",
        "tester",
        "true",
        "false",
        "c1,c3",
        "0",
        "v",
        "0",
        "true",
        "1",
        "null",
        "2.5",
        "null",
        "2026-09-23 10:00:00",
        "u",
    ]


def test_helpers_are_null_aware():
    result = run(
        'const rows = [{v: 1}, {v: null}, {v: "3"}, {v: ""}];'
        'api.log(api.avg(rows, "v")); api.log(api.sum(rows, "v")); api.log(api.count(rows, "v"));'
        'api.log(api.min(rows, "v")); api.log(api.max(rows, "v")); api.log(api.avg([], "v"));'
        'api.log(api.days("2026-01-01", "2026-03-01")); api.log(api.days("2026-03-01 10:00:00", "2026-02-28"));'
    )
    assert result.ok, result.error
    assert result.log == ["2", "4", "2", "1", "3", "null", "59", "-1"]


def test_writes_are_collected_not_applied():
    result = run(
        'api.case.set("p", 5); api.case.deactivate(); api.case.parent.set("n", 2); api.case.parent.activate(); api.case.set("p", undefined);'
    )
    assert result.ok
    assert result.writes == [
        {"scope": "case", "kind": "set", "name": "p", "value": 5},
        {"scope": "case", "kind": "active", "value": 0},
        {"scope": "parent", "kind": "set", "name": "n", "value": 2},
        {"scope": "parent", "kind": "active", "value": 1},
        {"scope": "case", "kind": "set", "name": "p", "value": None},
    ]


def test_the_sandbox_takes_the_clock_and_chance_away():
    for source in (
        "Date.now()",
        "new Date()",
        "Math.random()",
        'eval("1")',
        'new Function("return 1")()',
    ):
        result = run(source)
        assert not result.ok, source
    assert run('api.log(new Date("2026-01-01T00:00:00Z").getUTCFullYear())').log == [
        "2026"
    ]


def test_failures_name_the_line_and_apply_nothing():
    result = run('api.case.set("p", 1);\n  throw new Error("boom");')
    assert result.error == "Error: boom (line 3)"
    assert result.writes == [] and result.log == []
    assert (
        run('api.case.property("zz")').error
        == "Error: The case has no property zz (line 2)"
    )
    assert (
        run('api.case.value("zz")').error == "Error: The case has no column zz (line 2)"
    )
    assert run('api.lookup("other", "c1")').error == (
        "Error: The lookup list other is not available to the module (line 2)"
    )
    assert (
        run("while (true) {}").error
        == "The module ran longer than its budget of 0.25 seconds"
    )
    assert run_module("function run() {}", base_input()).error == (
        "The module must export a default function run(s, api)"
    )


def test_a_form_without_a_case_hands_null():
    result = run_module(
        "export default function run(s, api) { api.log(api.case); }",
        base_input(case=None),
    )
    assert result.ok and result.log == ["null"]


def test_lookups_named_in_the_source():
    assert lookups_named(
        "api.lookup(\"a\", 1); api.lookup('b', x); api.lookup(name, 1)"
    ) == ["a", "b"]
    assert lookups_named("") == [] and lookups_named(None) == []


# ---------------------------------------------------------------------------
# changes_of
# ---------------------------------------------------------------------------


def test_changes_last_write_wins_and_unchanged_is_silent():
    case = base_input()["case"]
    writes = [
        {"scope": "case", "kind": "set", "name": "p", "value": 5},
        {"scope": "case", "kind": "set", "name": "p", "value": 7},
        {"scope": "case", "kind": "set", "name": "q", "value": "old"},
        {"scope": "case", "kind": "set", "name": "col", "value": "w"},
        {"scope": "case", "kind": "active", "value": 0},
        {"scope": "parent", "kind": "set", "name": "n", "value": 1.0},
        {"scope": "parent", "kind": "active", "value": 1},
    ]
    assert changes_of(writes, case) == [
        {
            "scope": "source",
            "table": "t",
            "rowuuid": "C1",
            "column": "_active",
            "old": "1",
            "new": "0",
        },
        {
            "scope": "source",
            "table": "t",
            "rowuuid": "C1",
            "column": "col",
            "old": "v",
            "new": "w",
        },
        {
            "scope": "source",
            "table": "t_properties",
            "rowuuid": "C1",
            "column": "p",
            "old": "0",
            "new": "7",
        },
    ]
    assert changes_of([], case) == []


def test_changes_refuse_what_the_case_has_no_home_for():
    case = base_input()["case"]
    with pytest.raises(ModuleError):
        changes_of([{"scope": "case", "kind": "set", "name": "risk", "value": 1}], case)
    with pytest.raises(ModuleError):
        changes_of([{"scope": "case", "kind": "set", "name": "p", "value": 1}], None)
    orphan = dict(case, parent=None)
    with pytest.raises(ModuleError):
        changes_of(
            [{"scope": "parent", "kind": "set", "name": "n", "value": 1}], orphan
        )


# ---------------------------------------------------------------------------
# The golden triples
# ---------------------------------------------------------------------------


def golden_names():
    return sorted(
        d for d in os.listdir(GOLDEN) if os.path.isdir(os.path.join(GOLDEN, d))
    )


@pytest.mark.parametrize("name", golden_names())
def test_golden_triple(name):
    folder = os.path.join(GOLDEN, name)
    program = open(os.path.join(folder, "program.js")).read()
    inputs = json.load(open(os.path.join(folder, "input.json")))
    expected = json.load(open(os.path.join(folder, "changes.json")))
    result = run_module(program, inputs)
    if "failure" in expected:
        failure = result.error
        if failure is None:
            try:
                changes_of(result.writes, inputs.get("case"))
            except ModuleError as e:
                failure = str(e)
        assert failure == expected["failure"]
        return
    assert result.ok, result.error
    assert changes_of(result.writes, inputs.get("case")) == expected["changes"]
    assert result.log == expected.get("log", [])


# ---------------------------------------------------------------------------
# The engine seam: RSTools' runactions binary (rstools.md 12.5)
# ---------------------------------------------------------------------------

FAKE_ENGINE = r'''#!/usr/bin/env python3
"""A stand-in for RSTools' runactions: the protocol, not the engine."""
import json, sys
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
module = open(args["-m"]).read()
inputs = json.load(open(args["-i"]))
if "bad input" in json.dumps(inputs):
    sys.stderr.write("input.json: no submission")
    sys.exit(2)
if "throw" in module:
    json.dump({"failure": "Error: boom (line 2)", "log": ["before"]}, open(args["-o"], "w"))
    sys.exit(1)
case = inputs["case"]
json.dump({"changes": [{"scope": "source", "table": case["table"] + "_properties", "rowuuid": case["rowuuid"],
                        "column": "p", "old": str(case["properties"]["p"]), "new": "5"},
                       {"scope": "source", "table": case["parent"]["table"], "rowuuid": case["parent"]["rowuuid"],
                        "column": "_active", "old": "1", "new": "0"}],
           "log": ["ran in the fake engine"]}, open(args["-o"], "w"))
sys.exit(0)
'''


@pytest.fixture
def fake_engine(tmp_path):
    import stat

    path = tmp_path / "runactions"
    path.write_text(FAKE_ENGINE)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def test_the_binary_is_used_when_present_and_its_report_applies(fake_engine):
    from formshare.processes.actions.host import writes_from_changes

    result = run_module(
        "export default function run(s, api) { api.case.set('p', 5); }",
        base_input(),
        engine=fake_engine,
    )
    assert result.ok, result.error
    assert result.log == ["ran in the fake engine"]
    assert result.changes[0]["new"] == "5"
    writes = writes_from_changes(result.changes, base_input()["case"])
    assert writes == [
        {"scope": "case", "kind": "set", "name": "p", "value": "5"},
        {"scope": "parent", "kind": "active", "value": 0},
    ]


def test_the_binary_reports_a_failure_and_a_bad_input(fake_engine):
    result = run_module(
        "export default function run(s, api) { throw new Error('boom'); }",
        base_input(),
        engine=fake_engine,
    )
    assert result.error == "Error: boom (line 2)" and result.log == ["before"]
    result = run_module(
        "export default function run(s, api) {}",
        base_input(submission={"values": {"note": "bad input"}}),
        engine=fake_engine,
    )
    assert result.error.startswith("The engine could not read the input")


def test_a_missing_binary_means_the_in_process_engine(tmp_path):
    result = run_module(
        "export default function run(s, api) { api.log('here'); }",
        base_input(),
        engine=str(tmp_path / "nope"),
    )
    assert result.ok and result.log == ["here"] and result.changes is None


# ---------------------------------------------------------------------------
# What MySQL holds for a write (actions-api.md 5): the table both appliers run
# ---------------------------------------------------------------------------


def test_store_values_table():
    from formshare.processes.actions.server import store_value, render

    doc = json.load(
        open(
            os.path.join(os.path.dirname(GOLDEN), "store_values.json"), encoding="utf-8"
        )
    )
    for case in doc["cases"]:
        args = (
            case["type"],
            case["value"],
            "property",
            "p",
            case.get("size", 0),
            case.get("decimals", 0),
            case.get("digits", 0),
        )
        if case.get("failure"):
            with pytest.raises(ModuleError):
                store_value(*args)
            continue
        assert render(store_value(*args)) == case["stored"], case


def test_same_table():
    from formshare.processes.actions.host import _same

    doc = json.load(
        open(
            os.path.join(os.path.dirname(GOLDEN), "store_values.json"), encoding="utf-8"
        )
    )
    for case in doc["same"]:
        assert _same(case["old"], case["new"], case["numeric"]) is case["same"], case


# ---------------------------------------------------------------------------
# The interim engine answers as runactions does (rstools.md 13.3)
# ---------------------------------------------------------------------------

SIBLING = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
RSTOOLS = os.environ.get("FORMSHARE_RSTOOLS_DIR", os.path.join(SIBLING, "RSTools"))
RUNACTIONS = os.environ.get(
    "FORMSHARE_RUNACTIONS",
    os.path.join(RSTOOLS, "build", "utilities", "RunActions", "runactions"),
)
ENGINES = [None] + ([RUNACTIONS] if os.path.exists(RUNACTIONS) else [])


@pytest.mark.parametrize(
    "engine", ENGINES, ids=lambda e: "runactions" if e else "interim"
)
def test_what_a_module_cannot_reach(engine):
    """The six places the interim engine used to answer differently."""
    refused = {
        "a date's constructor is the clock": "String(new (new Date(0)).constructor())",
        "a function's constructor evaluates text": '(function () {}).constructor("return 7")()',
        "the locale": "(1234.5).toLocaleString()",
        "an undeclared variable (strict mode)": "undeclared_thing = 3",
    }
    for what, expression in refused.items():
        result = run_module(
            "export default function run(s, api) {\n  api.log(" + expression + ");\n}",
            base_input(),
            engine=engine,
        )
        assert not result.ok and "(line 2)" in result.error, (what, result.error)
    for value, spelled in (("true", "true"), ("1e-7", "1e-7"), ("3.0", "3")):
        result = run_module(
            "export default function run(s, api) { api.case.set('q', " + value + "); }",
            base_input(),
            engine=engine,
        )
        report = (
            result.changes
            if result.changes is not None
            else changes_of(result.writes, base_input()["case"])
        )
        assert [c["new"] for c in report] == [spelled], (value, report)


def test_js_string_is_javascripts_spelling():
    from formshare.processes.actions.host import js_string

    # A list, not a dict: True, 1 and 1.0 (False, 0, -0.0) are one dict key.
    spelled = [
        (True, "true"),
        (False, "false"),
        (3.0, "3"),
        (-0.0, "0"),
        (1e-7, "1e-7"),
        (1e21, "1e+21"),
        (123456789012345680000.0, "123456789012345680000"),
        (0.1, "0.1"),
        (1.5e-6, "0.0000015"),
        (2.5e-7, "2.5e-7"),
        (float("nan"), "NaN"),
        (float("-inf"), "-Infinity"),
        (7, "7"),
        (None, None),
        ("x", "x"),
    ]
    for value, text in spelled:
        assert js_string(value) == text, (value, js_string(value))


def _days_catalogue():
    """A catalogue with a date of each group, as build_catalogue makes it,
    and what _add_days_since adds to it (formshare.md 8.2)."""
    from formshare.processes.db.actions import _add_days_since

    cat = Catalogue(
        fields={
            "v.when": {
                "js": "s.when",
                "type": "date",
                "label": "when",
                "group": "submission",
            },
            "v.at": {
                "js": "s.at",
                "type": "datetime",
                "label": "at",
                "group": "submission",
            },
            "v.name": {
                "js": "s.name",
                "type": "string",
                "label": "name",
                "group": "submission",
            },
            "p.last_visit": {
                "js": 'api.case.property("last_visit")',
                "type": "date",
                "label": "case last_visit",
                "group": "case",
            },
            "pp.opened": {
                "js": 'api.case.parent.property("opened")',
                "type": "date",
                "label": "parent opened",
                "group": "parent",
            },
            "c.max.visits.day": {
                "js": 'api.max(s.repeat("visits"), "day")',
                "type": "date",
                "label": "maximum of visits.day",
                "group": "computed",
            },
        },
        targets={("case", "property", "status"): "string"},
    )
    cat.ui = [
        {"id": "p.last_visit", "label": "case property last_visit", "type": "date"}
    ]
    _add_days_since(cat)
    return cat


def test_every_date_has_a_days_since_field():
    cat = _days_catalogue()
    days = {k: v for k, v in cat.fields.items() if k.startswith("d.")}
    assert set(days) == {"d.v.when", "d.v.at", "d.p.last_visit", "d.pp.opened"}
    assert days["d.p.last_visit"]["type"] == "integer"
    assert days["d.p.last_visit"]["js"] == (
        '(api.case.property("last_visit") === null ? null : '
        'api.days(api.case.property("last_visit"), api.now))'
    )
    ui = {u["id"]: u for u in cat.ui if u["id"].startswith("d.")}
    assert ui["d.p.last_visit"]["label"] == "days since case property last_visit"
    assert ui["d.p.last_visit"]["optgroup"] == "The case, days since"
    assert ui["d.v.when"]["optgroup"] == "This submission, days since"
    assert ui["d.pp.opened"]["optgroup"] == "The case's parent, days since"


def test_a_day_count_compiles_to_api_days():
    cat = _days_catalogue()
    expression = compile_when(rule("d.v.when", "greater", 20), cat)
    assert "api.days(s.when, api.now)" in expression
    assert describe_when(rule("d.v.when", "greater", 20), cat) == (
        "days since when is greater than 20"
    )


@pytest.mark.parametrize(
    "last_visit, status",
    [("2026-09-01", "overdue"), ("2026-09-10", "recent"), (None, None)],
)
def test_a_day_count_runs_against_the_hosts_date(last_visit, status):
    cat = _days_catalogue()
    rows = [
        row(
            1,
            "property",
            "status",
            value="overdue",
            when=rule("d.p.last_visit", "greater", 20),
        ),
        row(
            2,
            "property",
            "status",
            value="recent",
            when=rule("d.p.last_visit", "less_or_equal", 20),
        ),
    ]
    module = compile_module(rows, cat)
    inputs = base_input()
    inputs["case"]["properties"] = {"status": "new", "last_visit": last_visit}
    # A date and time: api.days reads its date and leaves the time.
    inputs["now"] = "2026-09-24 23:59:59"
    result = run_module(module, inputs)
    assert result.ok, result.error
    written = [w["value"] for w in result.writes if w["name"] == "status"]
    assert written == ([status] if status else [])


def test_js_json_is_json_stringify():
    """How an array or an object a module wrote is named when it is refused:
    as the device names it, JSON.stringify's spelling (rstools.md 17.1)."""
    from formshare.processes.actions.host import js_json

    spelled = [
        ([1e-07], "[1e-7]"),
        ([1, 2], "[1,2]"),
        ({"a": 1e21, "b": [True, None, "x"]}, '{"a":1e+21,"b":[true,null,"x"]}'),
        ([float("nan"), float("inf")], "[null,null]"),
        ([-0.0, 0.1], "[0,0.1]"),
        ({"é": "ñ\n"}, '{"é":"ñ\\n"}'),
        ([], "[]"),
        ({}, "{}"),
    ]
    for value, text in spelled:
        assert js_json(value) == text, (value, js_json(value))


def test_a_refused_array_is_named_as_the_device_names_it():
    from formshare.processes.actions.server import store_value

    with pytest.raises(ModuleError) as refused:
        store_value("double", [1e-07], "property", "ratio")
    assert str(refused.value) == "[1e-7] is not a value for property ratio"


@pytest.mark.skipif(
    not os.path.exists(os.path.join(RSTOOLS, "kotlinrstools", "actions", "prelude.js")),
    reason="RSTools is not beside FormShare (set FORMSHARE_RSTOOLS_DIR)",
)
def test_the_prelude_is_rstools():
    """The interim engine runs a copy of RSTools' prelude; a copy goes stale
    without anyone noticing."""
    from formshare.processes.actions.host import PRELUDE

    theirs = open(
        os.path.join(RSTOOLS, "kotlinrstools", "actions", "prelude.js"),
        encoding="utf-8",
    ).read()
    assert PRELUDE == theirs


@pytest.mark.skipif(not os.path.exists(RUNACTIONS), reason="runactions is not built")
@pytest.mark.parametrize("name", golden_names())
def test_golden_triple_through_runactions(name):
    folder = os.path.join(GOLDEN, name)
    program = open(os.path.join(folder, "program.js")).read()
    inputs = json.load(open(os.path.join(folder, "input.json")))
    expected = json.load(open(os.path.join(folder, "changes.json")))
    result = run_module(program, inputs, engine=RUNACTIONS)
    if "failure" in expected:
        assert result.error == expected["failure"]
        return
    assert result.ok, result.error
    assert result.changes == expected["changes"]
    assert changes_of(result.writes, inputs.get("case")) == expected["changes"]
    assert result.log == expected.get("log", [])


# ---------------------------------------------------------------------------
# A take-back puts back what the column held, exactly (rstools.md 24.1)
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        return self.rows


class _Session:
    """Answers every SELECT with what the column holds and records every
    statement, so the server's applier runs without a database."""

    def __init__(self, held, runs=()):
        self.held = held
        self.runs = list(runs)
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((str(sql), dict(params or {})))
        return _Result(self.held if str(sql).startswith("SELECT") else None)

    def query(self, *args):
        return _Query(self.runs)


class _ServerRequest:
    def __init__(self, session):
        self.dbsession = session


class _Run:
    def __init__(self, restore):
        self.run_id = "run1"
        self.form_id = "follow_up"
        self.run_status = 0
        self.run_restore = restore
        self.run_changes = json.dumps(
            [
                {
                    "scope": "source",
                    "table": "roster",
                    "rowuuid": "r1",
                    "column": "amount",
                    "old": "12345678901234.566",
                    "new": "1",
                }
            ]
        )


def test_the_report_cannot_carry_a_large_decimal_back():
    """Why a run keeps the old values apart: the report spells the double
    the module was handed, which a decimal(17,3) with thirteen or fourteen
    digits before the point does not survive."""
    import decimal

    from formshare.processes.actions.server import render

    assert render(decimal.Decimal("12345678901234.567")) == "12345678901234.566"
    assert render(decimal.Decimal("99999999999999.999")) == "100000000000000"


def test_a_plan_keeps_each_column_as_mysql_spells_it():
    from formshare.processes.actions.server import _exact_olds

    session = _Session(("12345678901234.567",))
    plan = [
        {
            "table": "roster",
            "rowuuid": "r1",
            "column": "amount",
            "value": 1.0,
            "old": 12345678901234.566,
        }
    ]
    assert _exact_olds(_ServerRequest(session), "FS_x", plan) == [
        {
            "table": "roster",
            "rowuuid": "r1",
            "column": "amount",
            "old": "12345678901234.567",
        }
    ]
    assert session.statements == [
        (
            "SELECT CAST(`amount` AS CHAR) FROM `FS_x`.`roster` WHERE rowuuid = :r",
            {"r": "r1"},
        )
    ]


@pytest.mark.parametrize(
    "restore, expected",
    [
        (
            json.dumps(
                [
                    {
                        "table": "roster",
                        "rowuuid": "r1",
                        "column": "amount",
                        "old": "12345678901234.567",
                    }
                ]
            ),
            "12345678901234.567",
        ),
        # A run recorded before run_restore goes back to the report's old.
        (None, "12345678901234.566"),
    ],
)
def test_the_take_back_writes_the_exact_old_value(monkeypatch, restore, expected):
    import decimal

    from formshare.processes.actions import server

    a_run = _Run(restore)
    # The column still holds what the run stored, so it goes back.
    session = _Session((decimal.Decimal("1.000"),), runs=[a_run])
    monkeypatch.setattr(
        server, "case_source_of", lambda request, project, form: {"schema": "FS_x"}
    )
    assert server.take_back_runs(_ServerRequest(session), "P", main_rowuuid="m1") == 1
    sql, params = session.statements[-1]
    assert sql == "UPDATE `FS_x`.`roster` SET `amount` = :v WHERE rowuuid = :r"
    assert params == {"v": expected, "r": "r1"}
    assert a_run.run_status == 2


# ---------------------------------------------------------------------------
# A test with typed answers acts on a stand-in for the case
# ---------------------------------------------------------------------------


class _StandInReader:
    """The stored columns of each table, typed, as _Reader reads them from
    MySQL and the dictionary: a follow-up (FS_visit) whose case is a teacher,
    a repeat of a school's registration (FS_school)."""

    columns = {
        ("FS_visit", "maintable"): {
            "rowuuid": "string",
            "_submitted_by": "string",
            "teacher_id": "string",
            "still_working": "string",
        },
        ("FS_school", "teachers"): {
            "rowuuid": "string",
            "parent_rowuuid": "string",
            "_active": "integer",
            "teacher_name": "string",
            "years": "integer",
        },
        ("FS_school", "maintable"): {
            "rowuuid": "string",
            "_active": "integer",
            "school_name": "string",
        },
    }

    def __init__(self, request):
        self.request = request

    def types(self, project_id, form_id, schema, table):
        return dict(self.columns[(schema, table)])

    def has_column(self, schema, table, column):
        return column in self.columns[(schema, table)]


@pytest.fixture
def teacher_visit(monkeypatch):
    """sample_input's reads, for a follow-up of the list of teachers: its
    list_active is set by each test."""
    from formshare.processes.actions import server

    source = {
        "list_id": "teachers",
        "selector_field": "teacher_id",
        "project": "P",
        "form": "school_registration",
        "schema": "FS_school",
        "table": "teachers",
        "parent_table": "maintable",
        "list_active": 1,
        "own": False,
    }
    monkeypatch.setattr(server, "_Reader", _StandInReader)
    monkeypatch.setattr(server, "case_source_of", lambda request, p, f: source)
    monkeypatch.setattr(server, "continuations_of", lambda request, p, f: {})
    monkeypatch.setattr(
        server, "_tables", lambda request, p, f: [{"table_name": "maintable"}]
    )
    monkeypatch.setattr(
        server,
        "get_table_properties",
        lambda request, p, f, table: (
            [
                {
                    "property_name": "visits",
                    "property_type": "integer",
                    "property_default": "0",
                }
            ]
            if table == "teachers"
            else []
        ),
    )
    monkeypatch.setattr(server, "engine_path", lambda request: None)
    return source


def test_a_test_with_answers_acts_on_a_stand_in_case(teacher_visit):
    """A real submission always names a case its list serves, the
    follow-up's membership trigger refusing any other and none: the test
    asks for no case, and acts on one as a new one stands."""
    from formshare.processes.actions import server

    inputs = server.sample_input(
        _ServerRequest(None),
        "P",
        "teacher_visit",
        "FS_visit",
        "",
        "ana",
        {"answers": {"still_working": "no"}, "repeats": {}},
    )
    assert inputs["case"] == {
        "table": "teachers",
        "rowuuid": "sample-case",
        "active": True,
        "values": {"teacher_name": None, "years": None},
        "properties": {"visits": 0},
        "parent": {
            "table": "maintable",
            "rowuuid": "sample-parent",
            "active": True,
            "values": {"school_name": None},
            "properties": {},
            "parent": None,
        },
    }
    # The selector answers it, as in a real submission
    assert inputs["submission"]["values"] == {
        "teacher_id": "sample-case",
        "still_working": "no",
    }


@pytest.mark.parametrize(
    "list_active, still_working, changes",
    [
        (
            1,
            "no",
            [
                {
                    "scope": "source",
                    "table": "teachers",
                    "rowuuid": "sample-case",
                    "column": "_active",
                    "old": "1",
                    "new": "0",
                }
            ],
        ),
        # The answers decide
        (1, "yes", []),
        (1, None, []),
        # A list of inactive cases serves a case already inactive
        (0, "no", []),
    ],
)
def test_a_rule_tested_with_answers_changes_the_stand_in(
    teacher_visit, catalogue, list_active, still_working, changes
):
    from formshare.processes.actions import server

    teacher_visit["list_active"] = list_active
    module = compile_module(
        [row(1, "active", "0", when=group(rule("v.still_working", "equal", "no")))],
        catalogue,
    )
    assert "if (api.case === null) { return; }" in module
    answers = {} if still_working is None else {"still_working": still_working}
    outcome = server.dry_run_sample(
        _ServerRequest(None),
        "P",
        "teacher_visit",
        "FS_visit",
        "ana",
        {"answers": answers},
        module=module,
    )
    assert outcome["ok"], outcome
    assert outcome["changes"] == changes


def test_a_property_starts_at_its_default_in_the_stand_in(teacher_visit):
    from formshare.processes.actions import server

    outcome = server.dry_run_sample(
        _ServerRequest(None),
        "P",
        "teacher_visit",
        "FS_visit",
        "ana",
        {"answers": {}},
        module=(
            "export default function run(s, api) {\n"
            '  api.case.set("visits", api.case.property("visits") + 1);\n'
            "}\n"
        ),
    )
    assert outcome["ok"], outcome
    assert outcome["changes"] == [
        {
            "scope": "source",
            "table": "teachers_properties",
            "rowuuid": "sample-case",
            "column": "visits",
            "old": "0",
            "new": "1",
        }
    ]


def test_a_decimal_can_be_typed_in_the_rule_builder():
    """A number input steps by 1 unless told otherwise, and the browser
    refuses to submit the action's page while one holds 0.75."""
    from types import SimpleNamespace

    from formshare.processes.db.actions import catalogue_for_querybuilder

    filters = {
        a_filter["id"]: a_filter
        for a_filter in catalogue_for_querybuilder(
            SimpleNamespace(
                ui=[
                    {"id": "s.weight", "label": "weight", "type": "double"},
                    {"id": "s.age", "label": "age", "type": "integer"},
                    {"id": "s.seen", "label": "seen", "type": "date"},
                ]
            )
        )
    }
    assert filters["s.weight"]["validation"] == {"step": "any"}
    assert "validation" not in filters["s.age"]
    assert "validation" not in filters["s.seen"]
