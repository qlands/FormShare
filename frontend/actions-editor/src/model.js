// What a module can read and write: the actions API, version 1
// (docs/formshare_case_management/actions-api.md, sections 4 and 5), and the
// form's own names, from the catalogue the page hands over.
//
// An argument's `kind` says what completes it and what it is checked
// against:
//   repeat   a repeat of the submission        s.repeat("…")
//   nested   a repeat inside the row's repeat   row.repeat("…")
//   multi    a multi-select question            s.selected("…", code)
//   choice   a code of the multi-select named by the argument before it
//   list     a lookup list                      api.lookup("…", code)
//   rows     rows of a repeat (an expression)
//   column   a column of the rows of the argument before it
//   target   a property or column the case can be given   api.case.set("…", v)
//   property a property of the case             api.case.property("…")
//   casecol  a column of the case's row          api.case.value("…")
// An argument with no kind is any expression.

const SUBMISSION = [
  {name: "rowuuid", type: "property", detail: "text", info: "The main row's identity."},
  {name: "submittedBy", type: "property", detail: "text", info: "Who submitted it: the assistant's login (_submitted_by)."},
  {name: "submittedDate", type: "property", detail: "date and time", info: "When it was submitted, YYYY-MM-DD HH:MM:SS (_submitted_date)."},
  {name: "repeat", type: "method", args: [{name: "name", kind: "repeat"}],
   info: "The rows of a repeat, in submission order, each with its answers, rowuuid and parent_rowuuid. [] when the repeat has no rows."},
  {name: "selected", type: "method", args: [{name: "variable", kind: "multi"}, {name: "code", kind: "choice"}],
   info: "Whether a multi-select answer includes the code."},
  {name: "selections", type: "method", args: [{name: "variable", kind: "multi"}],
   info: "The codes chosen in a multi-select, in the order they were chosen."},
];

const ROW = [
  {name: "rowuuid", type: "property", detail: "text", info: "The row's identity."},
  {name: "parent_rowuuid", type: "property", detail: "text", info: "The identity of the row this one belongs to."},
  {name: "repeat", type: "method", args: [{name: "name", kind: "nested"}],
   info: "The rows of a repeat inside this one, in submission order. [] when it has none."},
  {name: "selected", type: "method", args: [{name: "variable", kind: "multi"}, {name: "code", kind: "choice"}],
   info: "Whether a multi-select answer of this row includes the code."},
  {name: "selections", type: "method", args: [{name: "variable", kind: "multi"}],
   info: "The codes chosen in a multi-select of this row, in order."},
];

const aggregate = (name, words) => ({
  name, type: "method", args: [{name: "rows", kind: "rows"}, {name: "column", kind: "column"}],
  info: words + " Rows come from s.repeat(\"name\") or a row's repeat(\"name\").",
});

const API = [
  {name: "case", type: "property", detail: "the case",
   info: "The case this form acts on: the row its case link points at, or the submission's own main row for a form without one. null when the link names a row the source does not have."},
  {name: "lookup", type: "method", args: [{name: "list", kind: "list"}, {name: "code"}],
   info: "The row of a lookup list by its code, as an object of its columns, or null. Name the list as text: the server loads the lists a module names that way."},
  {name: "now", type: "property", detail: "date and time",
   info: "The host's clock at the run, YYYY-MM-DD HH:MM:SS, in the server's time zone on the server and the device's on the device."},
  {name: "user", type: "property", detail: "text", info: "The assistant's login."},
  aggregate("avg", "The average of a column over rows, skipping nulls; null when no row has a number."),
  aggregate("sum", "The sum of a column over rows, skipping nulls; null when no row has a number."),
  aggregate("count", "How many rows have the column answered (not null, not empty)."),
  aggregate("min", "The smallest number of a column over rows; null when no row has one."),
  aggregate("max", "The largest number of a column over rows; null when no row has one."),
  {name: "days", type: "method", args: [{name: "from"}, {name: "to"}],
   info: "Whole days from one date to another, both ISO text (YYYY-MM-DD…); api.days(date, api.now) counts the days since."},
  {name: "log", type: "method", args: [{name: "message"}], info: "A line kept with the run, for the owner, never for the enumerator."},
];

const caseMembers = parent => [
  {name: "rowuuid", type: "property", detail: "text", info: "The identity of the " + (parent ? "parent's" : "case's") + " row."},
  {name: "table", type: "property", detail: "text", info: "The table the " + (parent ? "parent" : "case") + " is a row of."},
  {name: "active", type: "property", detail: "true or false", info: "Whether _active is 1. Change it with activate() and deactivate()."},
  ...(parent ? [] : [{name: "parent", type: "property", detail: "the case's parent",
    info: "The row the case belongs to, when the case is a repeat row: the same members, one level only. null for a case of a main table."}]),
  {name: "value", type: "method", args: [{name: "column", kind: "casecol"}], info: "A column of the " + (parent ? "parent's" : "case's") + " row, typed."},
  {name: "property", type: "method", args: [{name: "name", kind: "property"}], info: "A property of the " + (parent ? "parent" : "case") + ", typed; null when it holds NULL."},
  {name: "set", type: "method", args: [{name: "name", kind: "target"}, {name: "value"}],
   info: "Sets a property of the " + (parent ? "parent" : "case") + ", or a column of its row. Applied after run returns, all writes or none; the last write to a name wins."},
  {name: "activate", type: "method", args: [], info: "Sets _active to 1."},
  {name: "deactivate", type: "method", args: [], info: "Sets _active to 0."},
];

// What an array of rows offers that a module commonly uses.
const ROWS = [
  {name: "length", type: "property", detail: "number", info: "How many rows."},
  ...["forEach", "map", "filter", "some", "every", "find", "reduce", "concat", "slice"].map(name => ({
    name, type: "method", args: name === "concat" || name === "slice" ? [{name: "…"}] : [{name: "callback"}], info: "Array.prototype." + name + ".",
  })),
];

export const MEMBERS = {
  s: SUBMISSION,
  row: ROW,
  api: API,
  case: caseMembers(false),
  parent: caseMembers(true),
  rows: ROWS,
};

export function member(kind, name) {
  const list = MEMBERS[kind];
  return list ? list.find(m => m.name === name) || null : null;
}

// What every object has: never reported as a name the form lacks.
export const OBJECT_MEMBERS = new Set([
  "constructor", "hasOwnProperty", "isPrototypeOf", "propertyIsEnumerable", "toString", "valueOf",
  "__proto__", "__defineGetter__", "__defineSetter__", "__lookupGetter__", "__lookupSetter__",
]);

// The page's catalogue, made total: whatever is missing reads as empty, and
// `known` false (a form with no repository yet) turns every check of a name
// off, since nothing can be said to be missing.
export function makeCatalogue(raw) {
  raw = raw && typeof raw === "object" ? raw : {};
  const arr = v => (Array.isArray(v) ? v : []);
  const str = v => (v === null || v === undefined ? "" : String(v));
  const choicesOf = list => arr(list).map(c => ({code: str(c && c.code), label: str(c && c.label)})).filter(c => c.code !== "");
  const named = list => arr(list).filter(x => x && typeof x.name === "string" && x.name !== "");

  const questions = new Map();
  // `system`: a column of the repository's own (_elevation…), which the run
  // hands over but nobody writes rules about: known, never offered.
  named(raw.questions).forEach((q, index) => questions.set(q.name, {
    name: q.name, type: str(q.type) || "string", label: str(q.label), multi: !!q.multi,
    select: !!q.select, encrypted: !!q.encrypted, system: !!q.system, choices: choicesOf(q.choices), order: index,
  }));

  const repeats = new Map();
  named(raw.repeats).forEach((r, index) => {
    const columns = new Map();
    named(r.columns).forEach((c, i) => columns.set(c.name, {
      name: c.name, type: str(c.type) || "string", label: str(c.label), multi: !!c.multi,
      select: !!c.select, encrypted: !!c.encrypted, system: !!c.system, choices: choicesOf(c.choices), order: i,
    }));
    repeats.set(r.name, {name: r.name, parent: str(r.parent) || "maintable", label: str(r.label), columns, order: index});
  });

  const target = t => {
    if (!t || typeof t !== "object") return null;
    const properties = new Map();
    named(t.properties).forEach((p, i) => properties.set(p.name, {name: p.name, type: str(p.type) || "string", order: i}));
    const columns = new Map();
    named(t.columns).forEach((c, i) => columns.set(c.name, {
      name: c.name, type: str(c.type) || "string", label: str(c.label), encrypted: !!c.encrypted, order: i,
    }));
    return {table: str(t.table), properties, columns};
  };

  const lookups = new Map();
  named(raw.lookups).forEach((l, index) => lookups.set(l.name, {
    name: l.name, columns: arr(l.columns).map(str).filter(Boolean), order: index,
  }));

  return {
    known: !!raw.known,
    questions,
    repeats,
    case: target(raw.case),
    parent: target(raw.parent),
    lookups,
  };
}

// The name meant, for "did you mean": the same name in another case, or a
// name one edit away (two for a name of five letters or more), where a
// swap of two letters is one edit. Nothing when two are equally close.
export function closest(name, names) {
  const lower = name.toLowerCase();
  const limit = name.length <= 2 ? 0 : name.length <= 4 ? 1 : 2;
  let best = null;
  let bestDistance = Infinity;
  let tie = false;
  for (const candidate of names) {
    if (candidate === name) return null;
    if (candidate.toLowerCase() === lower) return candidate;
    if (limit < 1 || Math.abs(candidate.length - name.length) > limit) continue;
    const d = distance(lower, candidate.toLowerCase());
    if (d > limit) continue;
    if (d < bestDistance) {
      best = candidate;
      bestDistance = d;
      tie = false;
    } else if (d === bestDistance) {
      tie = true;
    }
  }
  return tie ? null : best;
}

// Edits from one name to another: insertions, deletions, substitutions and
// swaps of two letters side by side (optimal string alignment).
function distance(a, b) {
  const d = [];
  for (let i = 0; i <= a.length; i++) d.push([i]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
    }
  }
  return d[a.length][b.length];
}
