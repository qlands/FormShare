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
    describe_when,
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


def test_first_match_wins_per_target(catalogue):
    module = compile_module(
        [
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
        ],
        catalogue,
    )
    assert module.startswith("export default function run(s, api) {\n")
    assert "  if (api.case === null) { return; }\n" in module
    # status: rows 1 and 3 form one chain; row 4 is unreachable after an always
    assert (
        '  if (s.trained === "yes") { api.case.set("status", "interviewed"); }\n'
        in module
    )
    assert '  else { api.case.set("status", "seen"); }\n' in module
    assert '"never"' not in module
    assert (
        "// Row 1: when trained equals 'yes', set property status of the case to 'interviewed'"
        in module
    )
    assert "// Row 3: otherwise, set property status of the case to 'seen'" in module
    # trained: its own chain, typed as a number
    assert (
        '  if (s.years !== null && s.years > 2) { api.case.set("trained", 1); }\n'
        in module
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
    assert '  else if (s.still_working === "back") { api.case.activate(); }\n' in module
    assert "// Row 1: when still_working equals 'no', deactivate the case" in module
    assert "// Row 2: when still_working equals 'back', reactivate the case" in module
    assert '  api.case.set("seen", api.now);\n' in module
    assert '  api.case.set("teacher_name", s.trained);\n' in module
    assert "  if (api.case.parent !== null) {\n" in module
    assert (
        '    if (api.case.parent.property("count") !== null && api.case.parent.property("count") < 7) { api.case.parent.set("count", 7); }'
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
    assert result.writes == [
        {"scope": "case", "kind": "active", "value": 0},
        {"scope": "case", "kind": "set", "name": "status", "value": "interviewed"},
        {"scope": "case", "kind": "set", "name": "index", "value": 3.5},
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
