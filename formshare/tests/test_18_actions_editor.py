"""The code editor of a form's actions in expert mode (frontend/actions-editor).

The page runs the shipped bundle, never the source, so these tests run that
file in Node, against what the server gives it:

- the page loads the bundle that ships, and every phrase it translates is
  the bundle's English, with the same names to fill in;
- every module FormShare's compiler writes comes out of the checks clean, and
  so does every program of the golden set but the one every host fails for a
  name the case does not have: the editor never cries wolf over code that
  runs;
- catalogue_for_editor gives the names a run meets, by the rules the run's
  input is built with.

The bundle's own tests run against its source: npm test in
frontend/actions-editor. The tests that need node are skipped without one
that reads the bundle (an ES2020 script).
"""

import json
import os
import re
import shutil
import subprocess

import pytest

from formshare.processes.actions.compiler import (
    Catalogue,
    CompileError,
    OPERATORS,
    compile_module,
    rule_module,
)
from formshare.processes.db import actions as actions_db

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)
BUNDLE = os.path.join(
    PACKAGE, "jsandcss", "js", "plugins", "codemirror6", "actions_editor.min.js"
)
PAGES = os.path.join(PACKAGE, "templates", "dashboard", "projects", "case_management")
PHRASES = os.path.join(PAGES, "snippets", "actions_editor_phrases.jinja2")
GOLDEN = os.path.join(HERE, "resources", "actions", "golden")
NODE = shutil.which("node")


def _node_reads(path):
    """Whether the installed node can read the bundle, which is ES2020 (?.
    and ??). The node of Ubuntu 22.04's apt, 12, cannot, and CI's image had
    it until it installed a current one (rstools' circleci.Dockerfile)."""
    if NODE is None:
        return False
    try:
        checked = subprocess.run(
            [NODE, "--check", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return checked.returncode == 0


needs_node = pytest.mark.skipif(
    not _node_reads(BUNDLE), reason="no node on the PATH that reads ES2020"
)

# Loads the shipped bundle as a page would, then runs one function over the
# JSON on stdin.
_HARNESS = """
const fs = require("fs");
global.window = {};
require("vm").runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const E = window.FormShareActionsEditor;
const T = E.testing;
const input = JSON.parse(fs.readFileSync(0, "utf8"));
console.log(JSON.stringify((__FN__)(input)));
"""


def in_node(function, data=None):
    script = _HARNESS.replace("__FN__", function)
    process = subprocess.run(
        [NODE, "-e", script, BUNDLE],
        input=json.dumps(data).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
    return json.loads(process.stdout.decode("utf-8"))


def check_all(items):
    """[(text, catalogue)] -> the checks of each, as [from, to, severity,
    message] lists."""
    return in_node(
        "input => input.map(item => T.check(item[0], item[1]))",
        [list(item) for item in items],
    )


# ---------------------------------------------------------------------------
# What ships
# ---------------------------------------------------------------------------


def test_the_pages_load_the_shipped_bundle():
    with open(os.path.join(PACKAGE, "config", "mainresources.py")) as a_file:
        resources = a_file.read()
    assert '"js/plugins/codemirror6/actions_editor.min.js"' in resources
    assert os.path.getsize(BUNDLE) > 100 * 1024
    assert os.path.exists(
        os.path.join(os.path.dirname(BUNDLE), "THIRD_PARTY_LICENSES.txt")
    )
    # Where code is written and where it is tested; the list does without.
    loads = "{% jsresource request,'formshare','actions_editor' %}"
    for page, expected in (
        ("action_code.jinja2", True),
        ("action_test.jinja2", True),
        ("actions.jinja2", False),
    ):
        with open(os.path.join(PAGES, page)) as a_file:
            assert (loads in a_file.read()) is expected, page


def _template_phrases():
    """{key: English} of the phrases the template hands the editor.

    A phrase names what it is about as the bundle does, {name}, inside the
    msgid: a template's _() here is the request's translator, which fills
    nothing in (the dispatcher puts it in the context), and Jinja's own
    newstyle gettext would %-format the text, which leaves {name} alone.
    """
    with open(PHRASES) as a_file:
        template = a_file.read()
    block = template.split("var actEditorPhrases = {", 1)[1].split("};", 1)[0]
    phrases = {}
    for key, quote, text in re.findall(
        r"(\w+): \{\{ _\((['\"])((?:\\.|(?!\2).)*)\2\)\|tojson \}\}", block
    ):
        assert "%" not in text, text
        phrases[key] = text.replace("\\'", "'")
    assert len(phrases) == block.count("_(")
    return phrases


@needs_node
def test_the_template_translates_the_bundles_own_english():
    bundle = in_node(
        "() => ({version: E.version, create: typeof E.create, phrases: E.phrases})"
    )
    assert bundle["create"] == "function"
    english = dict(bundle["phrases"])
    # The name of the checker in a message's corner is not translated.
    english.pop("source")
    assert _template_phrases() == english


# ---------------------------------------------------------------------------
# No false alarm over code that runs
# ---------------------------------------------------------------------------


def _type_of(value):
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return "string"
    return "integer" if isinstance(value, int) else "double"


def _answers(rows):
    """The columns of rows as a run's input gives them."""
    columns = {}
    for a_row in rows:
        for name, value in a_row.get("values", {}).items():
            if name not in columns or columns[name]["type"] == "string":
                columns[name] = {"name": name, "type": _type_of(value)}
        for name in a_row.get("selections", {}):
            columns[name] = {"name": name, "type": "string", "multi": True}
    return list(columns.values())


def _catalogue_of(input_data, empty_repeats=()):
    """The editor's catalogue of a golden input: the names its run meets."""
    submission = input_data["submission"]
    repeats = {}

    def walk(rows, parent):
        for a_row in rows:
            for name, children in a_row.get("repeats", {}).items():
                repeats.setdefault(name, {"name": name, "parent": parent, "rows": []})
                repeats[name]["rows"].extend(children)
                walk(children, name)

    walk([submission], "maintable")
    for name in empty_repeats:
        repeats[name] = {"name": name, "parent": "maintable", "rows": []}

    def target(case):
        if not case:
            return None
        return {
            "table": case.get("table", ""),
            "properties": [{"name": n} for n in case.get("properties", {})],
            "columns": [{"name": n} for n in case.get("values", {})],
        }

    case = input_data.get("case") or None
    lookups = []
    for name, by_code in (input_data.get("lookups") or {}).items():
        columns = []
        for a_row in by_code.values():
            columns.extend(c for c in a_row if c not in columns)
        lookups.append({"name": name, "columns": columns})
    return {
        "known": True,
        "questions": _answers([submission]),
        "repeats": [
            {"name": r["name"], "parent": r["parent"], "columns": _answers(r["rows"])}
            for r in repeats.values()
        ],
        "case": target(case),
        "parent": target(case.get("parent") if case else None),
        "lookups": lookups,
    }


# A run's input lists every repeat of the form, with its rows or none
# (_submission_input). This one's input, written by hand, leaves out the
# repeat it reads to find empty.
EMPTY_REPEATS = {"nobody": ["rpt_visits"]}


@needs_node
def test_the_golden_programs_are_clean_but_the_one_every_host_fails():
    names = sorted(os.listdir(GOLDEN))
    items = []
    for name in names:
        with open(os.path.join(GOLDEN, name, "program.js")) as a_file:
            program = a_file.read()
        with open(os.path.join(GOLDEN, name, "input.json")) as a_file:
            catalogue = _catalogue_of(json.load(a_file), EMPTY_REPEATS.get(name, ()))
        items.append((program, catalogue))
    found = dict(zip(names, check_all(items)))
    assert len(names) >= 16
    with open(os.path.join(GOLDEN, "failure_no_property", "changes.json")) as a_file:
        assert json.load(a_file)["failure"] == (
            "risk is neither a property nor a column of teachers"
        )
    assert [d[2:] for d in found.pop("failure_no_property")] == [
        ["error", "The case has no property or column named “risk”."]
    ]
    assert found == {name: [] for name in found}


def rule(field, operator, value=None):
    return {"id": field, "field": field, "operator": operator, "value": value}


def group(*rules, condition="AND"):
    return {"condition": condition, "rules": list(rules)}


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


@needs_node
def test_every_module_the_compiler_writes_is_clean():
    fields = {
        "v.still_working": {"js": "s.still_working", "type": "string"},
        "v.years": {"js": "s.years", "type": "integer"},
        "v.weight": {"js": "s.weight", "type": "double"},
        "v.when": {"js": "s.when", "type": "date"},
        "v.seen_at": {"js": "s.seen_at", "type": "datetime"},
        "v.crops": {
            "js": "s.crops",
            "type": "string",
            "multi": True,
            "variable": "crops",
        },
        "v.odd-name": {"js": 's["odd-name"]', "type": "string"},
        "c.avg.meals.score": {
            "js": 'api.avg(s.repeat("meals"), "score")',
            "type": "double",
        },
        "p.status": {"js": 'api.case.property("status")', "type": "string"},
        "k.teacher_name": {"js": 'api.case.value("teacher_name")', "type": "string"},
        "pp.count": {"js": 'api.case.parent.property("count")', "type": "integer"},
        "d.v.when": {
            "js": "(s.when === null ? null : api.days(s.when, api.now))",
            "type": "integer",
        },
    }
    catalogue = Catalogue(
        fields=fields,
        targets={
            ("case", "property", "status"): "string",
            ("case", "property", "index"): "double",
            ("case", "column", "teacher_name"): "string",
            ("parent", "property", "count"): "integer",
        },
        repeats={"meals": {"score": "double", "kind": "string"}},
    )
    values = {
        "string": "yes",
        "integer": 3,
        "double": 2.5,
        "date": "2026-01-02",
        "datetime": "2026-01-02 08:00:00",
    }
    rows = []
    for field_id, field in fields.items():
        for operator, arity in OPERATORS.items():
            value = values[field["type"]]
            if arity == "list":
                value = [value, value]
            elif arity == 2:
                value = [value, value]
            elif arity == 0:
                value = None
            a_row = row(
                len(rows) + 1,
                "property",
                "status",
                value="x",
                when=group(rule(field_id, operator, value)),
            )
            try:
                compile_module([a_row], catalogue)
            except CompileError:
                continue
            rows.append(a_row)
    rows += [
        row(len(rows) + 1, "property", "status", "variable", "still_working"),
        row(
            len(rows) + 2,
            "property",
            "index",
            "computed",
            json.dumps({"aggregate": "avg", "repeat": "meals", "column": "score"}),
        ),
        row(len(rows) + 3, "column", "teacher_name", "now"),
        row(len(rows) + 4, "property", "count", "constant", "1", scope="parent"),
        row(len(rows) + 5, "active", "0", when=group(rule("v.years", "greater", 3))),
        row(len(rows) + 6, "active", "1", scope="parent"),
    ]
    module = compile_module(rows, catalogue)
    assert module.count("// Action ") == len(rows) > 60
    editor_catalogue = {
        "known": True,
        "questions": [
            {"name": "still_working", "type": "string"},
            {"name": "years", "type": "integer"},
            {"name": "weight", "type": "double"},
            {"name": "when", "type": "date"},
            {"name": "seen_at", "type": "datetime"},
            {"name": "crops", "type": "string", "multi": True},
            {"name": "odd-name", "type": "string"},
        ],
        "repeats": [
            {
                "name": "meals",
                "parent": "maintable",
                "columns": [{"name": "score", "type": "double"}, {"name": "kind"}],
            }
        ],
        "case": {
            "table": "teachers",
            "properties": [{"name": "status"}, {"name": "index", "type": "double"}],
            "columns": [{"name": "teacher_name"}],
        },
        "parent": {
            "table": "schools",
            "properties": [{"name": "count", "type": "integer"}],
            "columns": [],
        },
        "lookups": [],
    }
    # The module that runs, and each rule as See code shows it: there, run's
    # own s and api read every name, so the checks are certain of each. All
    # the rules together pass the 64 KB a host takes, which the checks say,
    # rightly: a form's module is checked with sixty of them.
    assert "The module is larger than 64 KB." in [
        d[3] for d in check_all([(module, editor_catalogue)])[0]
    ]
    within = compile_module(rows[:60], catalogue)
    standalone = [rule_module(a_row, catalogue) for a_row in rows]
    found = check_all(
        [(within, editor_catalogue)] + [(m, editor_catalogue) for m in standalone]
    )
    assert found == [[]] * (1 + len(standalone)), [
        (m, f) for m, f in zip([within] + standalone, found) if f
    ][:3]


# ---------------------------------------------------------------------------
# The names a run meets (catalogue_for_editor)
# ---------------------------------------------------------------------------


class _Form:
    def __init__(self, schema):
        self.form_schema = schema


def _field(
    name,
    field_type="varchar",
    odk="text",
    rtable=None,
    generated=None,
    encrypted=0,
    desc="",
):
    return {
        "field_name": name,
        "field_type": field_type,
        "field_odktype": odk,
        "field_rtable": rtable,
        "field_generatedas": generated,
        "field_encrypted": encrypted,
        "field_desc": desc,
    }


FORM_TABLES = [
    {"table_name": "lkpyes_no", "table_lkp": 1, "parent_table": None},
    {"table_name": "lkpcrops", "table_lkp": 1, "parent_table": None},
    {"table_name": "maintable", "table_lkp": 0, "parent_table": None},
    {"table_name": "maintable_ext1", "table_lkp": 0, "parent_table": "maintable"},
    {"table_name": "maintable_msel_crops", "table_lkp": 0, "parent_table": "maintable"},
    {"table_name": "meals", "table_lkp": 0, "parent_table": "maintable_ext1"},
    {"table_name": "dishes", "table_lkp": 0, "parent_table": "meals"},
]
SOURCE_TABLES = [
    {"table_name": "lkpcrops", "table_lkp": 1, "parent_table": None},
    {"table_name": "lkpregions", "table_lkp": 1, "parent_table": None},
    {"table_name": "maintable", "table_lkp": 0, "parent_table": None},
    {"table_name": "teachers", "table_lkp": 0, "parent_table": "maintable"},
]
FIELDS = {
    ("F", "maintable"): [
        _field("rowuuid"),
        _field("surveyid"),
        _field("_submitted_by"),
        _field("_elevation", "decimal", "decimal"),
        _field(
            "still_working", odk="select one", rtable="lkpyes_no", desc="Still working?"
        ),
        _field("crops", odk="select all that apply", desc="Crops"),
        _field("trace", "text", "geotrace", desc="Way"),
        _field("trace_geom", "geometry", "geotrace", generated="ST_GeomFromText(...)"),
        _field("secret", odk="select one", rtable="lkpyes_no", encrypted=1),
        _field("visit_date", "date", "date", desc="Without label"),
    ],
    ("F", "maintable_ext1"): [
        _field("rowuuid"),
        _field("link_rowuuid"),
        _field("q125", "int", "integer"),
    ],
    ("F", "maintable_msel_crops"): [_field("crops", rtable="lkpcrops")],
    ("F", "meals"): [
        _field("meals_rowid", "int"),
        _field("score", "decimal", "decimal"),
    ],
    ("F", "dishes"): [_field("dish")],
    ("F", "lkpyes_no"): [_field("yes_no_cod"), _field("yes_no_des"), _field("rowuuid")],
    ("F", "lkpcrops"): [
        _field("crops_cod"),
        _field("crops_des"),
        _field("crops_rowid", "int"),
    ],
    ("S", "lkpcrops"): [_field("crops_cod"), _field("crops_des")],
    ("S", "lkpregions"): [
        _field("regions_cod"),
        _field("regions_des"),
        _field("geometry", generated="x"),
        _field("geometry_json"),
    ],
    ("S", "maintable"): [
        _field("rowuuid"),
        _field("school_name"),
        _field("_active", "int"),
    ],
    ("S", "teachers"): [
        _field("rowuuid"),
        _field("parent_rowuuid"),
        _field("teacher_name", desc="Teacher's name"),
        _field("national_id", encrypted=1),
        _field("teachers_rowid", "int"),
    ],
}
CHOICES = {
    "lkpyes_no": [{"code": "1", "label": "Yes"}, {"code": "2", "label": "No"}],
    "lkpcrops": [{"code": "c1", "label": "Maize"}],
}
PROPERTIES = {
    ("S", "teachers"): [{"property_name": "status", "property_type": "string"}],
    ("S", "maintable"): [{"property_name": "trained", "property_type": "integer"}],
}


@pytest.fixture
def dictionary(monkeypatch):
    """catalogue_for_editor over a dictionary in memory: the form F, which
    follows up teachers, a repeat of the form S. The form's lookups are read
    before the source's."""
    schemas = {"F": "FS_form", "S": "FS_source"}
    monkeypatch.setattr(actions_db, "_form", lambda r, p, f: _Form(schemas.get(f)))
    monkeypatch.setattr(
        actions_db,
        "_tables_of",
        lambda r, p, f: FORM_TABLES if f == "F" else SOURCE_TABLES,
    )
    monkeypatch.setattr(
        actions_db,
        "continuations_of",
        lambda r, p, f: {"maintable_ext1": "maintable"} if f == "F" else {},
    )
    monkeypatch.setattr(
        actions_db, "_fields_of", lambda r, p, f, t: FIELDS.get((f, t), [])
    )
    monkeypatch.setattr(actions_db, "_choices", lambda r, s, t, n: CHOICES.get(t, []))
    monkeypatch.setattr(
        actions_db,
        "get_table_properties",
        lambda r, p, f, t: PROPERTIES.get((f, t), []),
    )
    source = {
        "project": "P",
        "form": "S",
        "schema": "FS_source",
        "table": "teachers",
        "parent_table": "maintable",
    }
    return type("CatalogueStandIn", (), {"source": source})()


def test_the_names_a_run_meets(dictionary):
    out = actions_db.catalogue_for_editor(None, "P", "F", dictionary)
    assert out["known"] is True
    assert out["questions"] == [
        {"name": "_elevation", "type": "double", "label": "", "system": True},
        {
            "name": "still_working",
            "type": "string",
            "label": "Still working?",
            "select": True,
            "choices": CHOICES["lkpyes_no"],
        },
        {
            "name": "crops",
            "type": "string",
            "label": "Crops",
            "multi": True,
            "choices": CHOICES["lkpcrops"],
        },
        {"name": "trace", "type": "string", "label": "Way"},
        {
            "name": "secret",
            "type": "string",
            "label": "",
            "select": True,
            "encrypted": True,
        },
        {"name": "visit_date", "type": "date", "label": ""},
        {"name": "q125", "type": "integer", "label": ""},
    ]
    assert out["repeats"] == [
        {
            "name": "meals",
            "parent": "maintable",
            "columns": [{"name": "score", "type": "double", "label": ""}],
        },
        {
            "name": "dishes",
            "parent": "meals",
            "columns": [{"name": "dish", "type": "string", "label": ""}],
        },
    ]
    assert out["case"] == {
        "table": "teachers",
        "properties": [{"name": "status", "type": "string"}],
        "columns": [
            {"name": "teacher_name", "type": "string", "label": "Teacher's name"},
            {"name": "national_id", "type": "string", "label": "", "encrypted": True},
        ],
    }
    assert out["parent"] == {
        "table": "maintable",
        "properties": [{"name": "trained", "type": "integer"}],
        "columns": [{"name": "school_name", "type": "string", "label": ""}],
    }
    assert out["lookups"] == [
        {"name": "yes_no", "columns": ["yes_no_cod", "yes_no_des"]},
        {"name": "crops", "columns": ["crops_cod", "crops_des"]},
        {"name": "regions", "columns": ["regions_cod", "regions_des", "geometry_json"]},
    ]


def test_no_names_without_a_repository(dictionary, monkeypatch):
    monkeypatch.setattr(actions_db, "_form", lambda r, p, f: _Form(None))
    out = actions_db.catalogue_for_editor(None, "P", "F", dictionary)
    assert out == {
        "known": False,
        "questions": [],
        "repeats": [],
        "case": None,
        "parent": None,
        "lookups": [],
    }


def test_no_case_while_its_source_has_no_repository(dictionary):
    dictionary.source = dict(dictionary.source, schema=None)
    out = actions_db.catalogue_for_editor(None, "P", "F", dictionary)
    assert out["known"] is True
    assert out["case"] is None and out["parent"] is None
