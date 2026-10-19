// node --test test/: the editor's analysis, completion, signature help and
// checks, against the source. The shipped bundle is tested by the suite
// (formshare/tests/test_18_actions_editor.py).

import {test} from "node:test";
import assert from "node:assert/strict";
import "../src/bundle.js";

const T = globalThis.FormShareActionsEditor.testing;

const catalogue = {
  known: true,
  questions: [
    {name: "teacher_id", type: "string", label: "Teacher", select: true},
    {name: "still_working", type: "string", label: "Still working?", choices: [{code: "yes", label: "Yes"}, {code: "no", label: "No"}]},
    {name: "years_experience", type: "integer", label: "Years of experience"},
    {name: "visit_date", type: "date"},
    {name: "crops", type: "string", multi: true, choices: [{code: "c1", label: "Maize"}, {code: "c2", label: "Beans"}, {code: "c3", label: "Rice"}]},
    {name: "secret", type: "string", encrypted: true},
  ],
  repeats: [
    {name: "meals", parent: "maintable", columns: [
      {name: "meal_name", type: "string"}, {name: "score", type: "integer"},
      {name: "foods", type: "string", multi: true, choices: [{code: "f1", label: "Fish"}, {code: "f2", label: "Rice"}]},
    ]},
    {name: "dishes", parent: "meals", columns: [{name: "dish", type: "string"}]},
  ],
  case: {
    table: "teachers",
    properties: [{name: "status", type: "string"}, {name: "visits", type: "integer"}, {name: "last_visit", type: "date"}],
    columns: [{name: "teacher_name", type: "string"}, {name: "national_id", type: "string", encrypted: true}],
  },
  parent: {table: "maintable", properties: [{name: "trained_teachers", type: "integer"}], columns: [{name: "school_name", type: "string"}]},
  lookups: [{name: "crop_list", columns: ["crop_list_cod", "crop_list_des", "crop_list_group"]}],
};

const wrap = body => "export default function run(s, api) {\n" + body + "\n}\n";
const messages = (body, cat = catalogue) => T.check(wrap(body), cat).map(d => d[2] + ": " + d[3]);
// The text with | at the cursor.
const at = text => ({text: text.replace("|", ""), pos: text.indexOf("|")});
const complete = (body, cat = catalogue, explicit = false) => {
  const {text, pos} = at(wrap(body));
  return T.complete(text, pos, cat, explicit);
};

test("a module FormShare writes is clean", () => {
  const module = `export default function run(s, api) {
  // Row 1: when still_working = 'no', deactivate the case
  if ((s.still_working === "no")) { api.case.deactivate(); }
  // Row 2: always, set status to 'interviewed'
  api.case.set("status", "interviewed");
  // Row 3: set visits to the count of meals.score
  api.case.set("visits", api.count(s.repeat("meals"), "score"));
  if ((s.selected("crops", "c1") || s.selected("crops", "c3"))) { api.case.parent.set("trained_teachers", 1); }
  if ((api.case.property("last_visit") === null ? null : api.days(api.case.property("last_visit"), api.now)) > 20) { api.case.set("last_visit", api.now); }
}
`;
  assert.deepEqual(T.check(module, catalogue), []);
});

test("an empty module is no module at all", () => {
  assert.deepEqual(T.check("  \n", catalogue), []);
});

test("what the server refuses when it saves", () => {
  assert.deepEqual(T.check("function run(s, api) {}", catalogue).map(d => d[3]),
    ["The module must export a default function run(s, api)."]);
  assert.deepEqual(T.check("export default function main(s, api) {}", catalogue).map(d => d[3]),
    ["The module must export a default function run(s, api)."]);
  const big = wrap("// " + "x".repeat(70 * 1024));
  assert.ok(T.check(big, catalogue).some(d => d[3] === "The module is larger than 64 KB."));
  assert.deepEqual(T.check('import x from "y";\n' + wrap(""), catalogue).map(d => d[3]),
    ["A module has no imports: what it reads comes in s and api."]);
  assert.deepEqual(T.check(wrap("") + "export function helper() {}\n", catalogue).map(d => d[3]),
    ["A module exports one thing: its default function run."]);
});

test("what cannot be read is said once", () => {
  const found = T.check(wrap("if (s.still_working === ) { api.case.deactivate(); } }"), catalogue);
  assert.equal(found.filter(d => d[3].startsWith("This part can't be read")).length, 1);
});

test("what would make a run depend on where it runs", () => {
  assert.deepEqual(messages("var d = new Date();"), ["error: new Date() without arguments is not available: use api.now."]);
  assert.deepEqual(messages("var d = new Date;"), ["error: new Date() without arguments is not available: use api.now."]);
  assert.deepEqual(messages('var d = new Date("2026-01-01");'), []);
  assert.deepEqual(messages("var d = Date();"), ["error: Date() is not available: use api.now."]);
  assert.deepEqual(messages("var d = Date.now();"), ["error: Date.now is not available: use api.now."]);
  assert.deepEqual(messages('var d = Date.UTC(2026, 0, 1);'), []);
  assert.deepEqual(messages("var r = Math.random();"), ["error: Math.random is not available: a run must give the same answer on every host."]);
  assert.deepEqual(messages('eval("1");'), ["error: eval is not available to a module."]);
  assert.deepEqual(messages('var f = new Function("return 1");'), ["error: Function is not available to a module."]);
  assert.deepEqual(messages("api.log((1.5).toLocaleString());"), ["error: toLocaleString is not available: formatting is the module's own or api's."]);
  assert.deepEqual(messages('api.log("a".localeCompare("b"));'), ["error: localeCompare is not available: formatting is the module's own or api's."]);
  assert.deepEqual(messages("setTimeout(function () {}, 1);"), ["error: setTimeout is not available: a module runs at once, with no timers."]);
  assert.deepEqual(messages("var p = performance;"), ["error: performance is not available to a module."]);
  assert.deepEqual(messages('import("x");'), ["error: import() loads nothing: no host has a module loader."]);
  // The server refuses an async run when it is saved: load_module wants
  // "export default function".
  assert.deepEqual(T.check("export default async function run(s, api) {\n  await f();\n}\n", catalogue).map(d => d[3]),
    ["The module must export a default function run(s, api).", "A module runs at once: nothing after an await runs."]);
  assert.deepEqual(messages("async function helper() { await f(); }"), ["warning: A module runs at once: nothing after an await runs."]);
});

test("a name declared in the module is the module's own", () => {
  assert.deepEqual(messages("function Date() { return 1; }\n var d = new Date();"), []);
  assert.deepEqual(messages("var Math = {random: function () { return 4; }}; Math.random();"), []);
  assert.deepEqual(messages("const setTimeout = 1; api.log(setTimeout);"), []);
});

test("questions the form does not have", () => {
  assert.deepEqual(messages("api.log(s.years_experiance);"),
    ["warning: This form has no question named “years_experiance”. Did you mean “years_experience”?"]);
  assert.deepEqual(messages("api.log(s.Teacher_ID);"),
    ["warning: This form has no question named “Teacher_ID”. Did you mean “teacher_id”?"]);
  assert.deepEqual(messages("api.log(s.zzz);"), ["warning: This form has no question named “zzz”."]);
  assert.deepEqual(messages("api.log(s.rowuuid, s.submittedBy, s.submittedDate, s.hasOwnProperty);"), []);
  assert.deepEqual(messages("api.log(s.secret);"), ["warning: “secret” is encrypted: the module reads its envelope, never the answer."]);
  // A scratch value of the module's own
  assert.deepEqual(messages("s.total = 1;"), []);
});

test("another s is not the submission", () => {
  assert.deepEqual(messages('s.repeat("meals").forEach(function (s) { api.log(s.score); });'), []);
  assert.deepEqual(messages("var s = {}; api.log(s.zzz);"), []);
  const renamed = "export default function run(sub, a) {\n  a.log(sub.zzz);\n  a.case.set(\"zzz\", 1);\n}\n";
  assert.deepEqual(T.check(renamed, catalogue).map(d => d[3]),
    ["This form has no question named “zzz”.", "The case has no property or column named “zzz”."]);
});

test("nothing is said of names while the form has no repository", () => {
  assert.deepEqual(messages('api.log(s.zzz); api.case.set("zzz", 1); s.repeat("zzz"); api.lookup("zzz", 1);', {known: false}), []);
});

test("the case: what it can be given, what it holds", () => {
  assert.deepEqual(messages('api.case.set("statsu", 1);'),
    ["error: The case has no property or column named “statsu”. Did you mean “status”?"]);
  assert.deepEqual(messages('api.case.set("teacher_name", "Ann");'), []);
  assert.deepEqual(messages('api.case.set("national_id", "1");'),
    ["error: “national_id” is encrypted: an action can only copy an envelope into it, not write an answer in clear."]);
  assert.deepEqual(messages('api.log(api.case.property("teacher_name"));'), ["error: The case has no property “teacher_name”."]);
  assert.deepEqual(messages('api.log(api.case.value("status"));'), ["error: The case has no column “status”."]);
  assert.deepEqual(messages('api.log(api.case.value("national_id"));'),
    ["warning: “national_id” is encrypted: the module reads its envelope, never the answer."]);
  assert.deepEqual(messages('api.case.parent.set("school_name", 1); api.case.parent.set("trained_teachers", 2);'), []);
  assert.deepEqual(messages('api.case.parent.set("status", 1);'), ["error: The case's parent has no property or column named “status”."]);
  assert.deepEqual(messages("api.case.active = false;"),
    ["warning: Assigning to the case changes nothing: use set(), activate() or deactivate()."]);
  assert.deepEqual(messages("api.log(api.case.status);"),
    ["warning: The case has no member “status”: read a property with property(\"…\") and a column with value(\"…\")."]);
  assert.deepEqual(messages("const c = api.case; c.set(\"zzz\", 1);"), ["error: The case has no property or column named “zzz”."]);
  const noParent = Object.assign({}, catalogue, {parent: null});
  // At each place it is read
  assert.deepEqual(messages('api.case.parent.set("x", 1); api.case.parent.deactivate();', noParent),
    ["warning: The case has no parent: api.case.parent is null.", "warning: The case has no parent: api.case.parent is null."]);
});

test("an empty name is one being written", () => {
  assert.deepEqual(messages('api.case.set("", 1); api.case.property(""); s.repeat(""); s.selected("crops", ""); api.lookup("", 1);'), []);
});

test("repeats, multi-selects and choices", () => {
  assert.deepEqual(messages('s.repeat("mealz");'), ["warning: This form has no repeat named “mealz”. Did you mean “meals”?"]);
  assert.deepEqual(messages('s.repeat("dishes");'),
    ["warning: “dishes” is a repeat inside “meals”: read it from one of that repeat's rows, as row.repeat(\"…\")."]);
  assert.deepEqual(messages('s.selected("still_working", "yes");'), ["warning: “still_working” is not a multi-select, so this finds no code."]);
  assert.deepEqual(messages('s.selected("crop", "c1");'), ["warning: This form has no multi-select named “crop”. Did you mean “crops”?"]);
  assert.deepEqual(messages('s.selected("crops", "C1");'), ["warning: “crops” has no choice “C1”. Did you mean “c1”?"]);
  assert.deepEqual(messages('api.log(api.avg(s.repeat("meals"), "scores"));'),
    ["warning: The repeat “meals” has no column “scores”. Did you mean “score”?"]);
});

test("lookups load only when named as text, through api", () => {
  assert.deepEqual(messages('api.log(api.lookup("crop_list", "c1").crop_list_des);'), []);
  assert.deepEqual(messages('api.lookup("crops_list", "c1");'), ["error: This form has no lookup list named “crops_list”. Did you mean “crop_list”?"]);
  assert.deepEqual(messages('var l = "crop_list"; api.lookup(l, "c1");'),
    ["warning: Name the list as text, as in api.lookup(\"list\", code): the server loads only the lists named that way."]);
  const renamed = "export default function run(s, a) {\n  a.lookup(\"crop_list\", \"c1\");\n}\n";
  assert.deepEqual(T.check(renamed, catalogue).map(d => d[3]),
    ["Name run's second parameter api: the server finds the lists to load by api.lookup(…)."]);
});

test("members after a dot", () => {
  const sub = complete("s.|");
  assert.deepEqual(sub.labels, ["teacher_id", "still_working", "years_experience", "visit_date", "crops",
    "rowuuid", "submittedBy", "submittedDate", "repeat", "selected", "selections"]);
  assert.deepEqual(sub.sections.slice(0, 2), ["Questions", "Questions"]);
  assert.equal(sub.details[0], "select one");
  assert.equal(sub.details[1], "select one");
  assert.equal(sub.details[2], "integer");
  assert.equal(sub.details[4], "multi-select");
  assert.equal(complete("s.ye|").from, at(wrap("s.ye|")).pos - 2);
  assert.deepEqual(complete("api.|").labels, ["case", "lookup", "now", "user", "avg", "sum", "count", "min", "max", "days", "log"]);
  assert.ok(complete("api.case.|").labels.includes("parent"));
  assert.ok(!complete("api.case.parent.|").labels.includes("parent"));
  assert.deepEqual(complete('api.log(api.lookup("crop_list", s.crops).|)').labels, ["crop_list_cod", "crop_list_des", "crop_list_group"]);
});

test("a repeat's rows and a row", () => {
  const row = ["meal_name", "score", "foods", "rowuuid", "parent_rowuuid", "repeat", "selected", "selections"];
  assert.deepEqual(complete('for (const m of s.repeat("meals")) { api.log(m.|); }').labels, row);
  assert.deepEqual(complete('s.repeat("meals").forEach(function (m) { api.log(m.|); });').labels, row);
  assert.deepEqual(complete('s.repeat("meals").filter(m => m.|);').labels, row);
  assert.deepEqual(complete('var meals = s.repeat("meals"); meals.forEach(function (m) { m.| });').labels, row);
  assert.deepEqual(complete('s.repeat("meals").reduce(function (t, m) { return t + m.|; }, 0);').labels, row);
  assert.ok(complete('s.repeat("meals").|').labels.includes("forEach"));
});

test("names inside quotes", () => {
  assert.deepEqual(complete('api.case.set("|")').labels, ["status", "visits", "last_visit", "teacher_name"]);
  assert.deepEqual(complete('api.case.set("|")').sections, ["Properties", "Properties", "Properties", "Columns"]);
  assert.deepEqual(complete('api.case.parent.set("|")').labels, ["trained_teachers", "school_name"]);
  assert.deepEqual(complete('api.case.property("|")').labels, ["status", "visits", "last_visit"]);
  assert.deepEqual(complete('api.case.value("|")').labels, ["teacher_name"]);
  assert.deepEqual(complete('s.repeat("|")').labels, ["meals"]);
  assert.deepEqual(complete('s.repeat("meals").forEach(function (m) { m.repeat("|"); });').labels, ["dishes"]);
  assert.deepEqual(complete('s.selected("|")').labels, ["crops"]);
  assert.deepEqual(complete('s.selected("crops", "|")').labels, ["c1", "c2", "c3"]);
  assert.deepEqual(complete('s.selected("crops", "|")').details, ["Maize", "Beans", "Rice"]);
  assert.deepEqual(complete('s.repeat("meals").forEach(function (m) { m.selected("foods", "|"); });').labels, ["f1", "f2"]);
  assert.deepEqual(complete('api.lookup("|")').labels, ["crop_list"]);
  assert.deepEqual(complete('api.avg(s.repeat("meals"), "|")').labels, ["meal_name", "score", "foods"]);
  assert.deepEqual(complete('if (s.still_working === "|") {}').labels, ["yes", "no"]);
  assert.deepEqual(complete('if ("|" !== s.still_working) {}').labels, ["yes", "no"]);
  assert.deepEqual(complete('switch (s.still_working) { case "|": break; }').labels, ["yes", "no"]);
  // An unterminated string, and one with text in it
  assert.deepEqual(complete('api.case.set("st|').labels, ["status", "visits", "last_visit", "teacher_name"]);
  const partial = complete('api.case.set("st|atus")');
  const {text} = at(wrap('api.case.set("st|atus")'));
  assert.equal(text.slice(partial.from, partial.to), "status");
  // Nothing to offer: an expression argument, a string that is not a name
  assert.equal(complete('api.case.set("status", "|")'), null);
  assert.equal(complete('api.log("|")'), null);
});

test("the module's function, offered while it is missing", () => {
  const empty = T.complete("exp", 3, catalogue, false);
  assert.deepEqual(empty.labels, ["export default function run(s, api)"]);
  assert.equal(T.complete(wrap("exp"), wrap("exp").indexOf("exp") + 3, catalogue, false), null);
});

test("signature help", () => {
  const call = body => {
    const {text, pos} = at(wrap(body));
    return T.signature(text, pos);
  };
  assert.deepEqual(call('api.case.set("status", |)'), {call: "api.case.set(name, value)", argument: "value"});
  assert.deepEqual(call('api.case.set(|)'), {call: "api.case.set(name, value)", argument: "name"});
  assert.deepEqual(call('s.selected("crops", |'), {call: "s.selected(variable, code)", argument: "code"});
  assert.deepEqual(call('api.case.parent.property(|)'), {call: "api.case.parent.property(name)", argument: "name"});
  assert.deepEqual(call('api.case.set("x", api.avg(s.repeat("meals"), "s|"))'), {call: "api.avg(rows, column)", argument: "column"});
  assert.equal(call('api.log(String(|))'), null);
  assert.equal(call('api.case.set("x", 1)|'), null);
});

test("did you mean", () => {
  assert.equal(T.closest("statsu", ["status", "visits"]), "status");
  assert.equal(T.closest("ab", ["ac", "ad"]), null);
  assert.equal(T.closest("STATUS", ["status"]), "status");
});
