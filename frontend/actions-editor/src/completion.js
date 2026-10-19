// Completion: the members of s, api, api.case, its parent and a repeat's
// row after a dot; the names that go in a string argument (a property to
// set, a repeat, a multi-select and its choices, a lookup list, a column of
// a repeat); and the choices of a select compared with ===.
//
// Encrypted names are never offered: a module reads their envelopes, never
// the answers (docs/formshare_field_encryption). The checks still know them,
// to say why one cannot be used.

import {pickedCompletion, snippetCompletion, startCompletion} from "@codemirror/autocomplete";
import {analyse, commasBefore} from "./analysis.js";
import {MEMBERS} from "./model.js";

// Arguments written as text.
export const STRING_KINDS = new Set(["repeat", "nested", "multi", "choice", "list", "column", "target", "property", "casecol"]);

export function typeWord(phrases, entry) {
  if (!entry) return "";
  if (entry.multi) return phrases.typeMulti;
  // A select one whose choices come from a file has none listed.
  if (entry.select || (entry.choices && entry.choices.length)) return phrases.typeSelect;
  return {
    integer: phrases.typeInteger,
    double: phrases.typeDecimal,
    date: phrases.typeDate,
    datetime: phrases.typeDatetime,
  }[entry.type] || phrases.typeText;
}

export function argumentsText(m) {
  return "(" + (m.args || []).map(a => a.name).join(", ") + ")";
}

// Where the cursor is, if a member is being typed after a dot.
function memberContext(a, node, pos) {
  if (node.name === "PropertyName" && node.parent && node.parent.name === "MemberExpression") {
    return {object: node.parent.firstChild, from: node.from, to: node.to};
  }
  if ((node.name === "." || node.name === "?.") && node.to === pos && node.parent && node.parent.name === "MemberExpression") {
    return {object: node.parent.firstChild, from: pos, to: pos};
  }
  if (node.type.isError && node.parent && node.parent.name === "MemberExpression") {
    const prev = node.prevSibling;
    if (prev && (prev.name === "." || prev.name === "?.")) return {object: node.parent.firstChild, from: pos, to: pos};
  }
  return null;
}

// Where the cursor is, if inside a string: an argument of a call, or the
// value a select is compared with.
export function stringContext(a, node, pos) {
  let str = node;
  if (str.type.isError && str.parent && str.parent.name === "String") str = str.parent;
  if (str.name !== "String" || pos <= str.from) return null;
  const text = a.text(str);
  const quote = text[0];
  let broken = false;
  for (let c = str.firstChild; c; c = c.nextSibling) {
    if (c.type.isError) broken = true;
  }
  const closed = !broken && text.length >= 2 && text[text.length - 1] === quote;
  if (closed && pos >= str.to) return null;
  const base = {str, quote, closed, contentFrom: str.from + 1, contentTo: closed ? str.to - 1 : str.to};
  const parent = str.parent;
  if (parent && parent.name === "ArgList" && parent.parent && parent.parent.name === "CallExpression") {
    return Object.assign(base, {type: "arg", call: parent.parent, index: commasBefore(parent, str)});
  }
  if (parent && parent.name === "BinaryExpression") {
    const op = parent.getChild("CompareOp");
    if (op && ["===", "!==", "==", "!="].includes(a.text(op))) {
      // Nodes are made afresh on each access: compare positions.
      const other = parent.firstChild.from === str.from ? parent.lastChild : parent.firstChild;
      return Object.assign(base, {type: "compare", other});
    }
  }
  // case "…": in a switch over an answer
  if (parent && parent.name === "CaseLabel" && parent.parent && parent.parent.parent &&
      parent.parent.parent.name === "SwitchStatement") {
    const subject = parent.parent.parent.getChild("ParenthesizedExpression");
    const inner = subject && subject.firstChild && subject.firstChild.nextSibling;
    if (inner) return Object.assign(base, {type: "compare", other: inner});
  }
  return null;
}

// The question, or the repeat's column, an expression reads: s.q or row.q.
export function answerOf(a, node, catalogue, certain = false) {
  if (!node || node.name !== "MemberExpression") return null;
  const object = node.firstChild;
  const op = object && object.nextSibling;
  const prop = op && op.nextSibling;
  if (!op || op.name !== "." || !prop || prop.name !== "PropertyName") return null;
  const owner = a.classify(object, certain);
  if (!owner) return null;
  const name = a.text(prop);
  if (owner.kind === "s") return catalogue.questions.get(name) || null;
  if (owner.kind === "row") {
    const repeat = catalogue.repeats.get(owner.repeat);
    return repeat ? repeat.columns.get(name) || null : null;
  }
  return null;
}

function escapeFor(quote, value) {
  return value.replace(/\\/g, "\\\\").split(quote).join("\\" + quote);
}

// Picking a name inside quotes: the name, the closing quote, and when the
// call has no next argument yet but needs one, ", " -- with the quotes of
// the next argument too when it is text, whose completion then opens.
function pickString(ctx, next) {
  return (view, completion, from, to) => {
    const doc = view.state.doc;
    const after = ctx.closed ? to + 1 : to;
    const rest = doc.sliceString(after, Math.min(doc.length, after + 200));
    const moveOn = next && /^[ \t]*\)/.test(rest);
    const name = escapeFor(ctx.quote, completion.label);
    let insert = name + ctx.quote;
    let cursor = from + insert.length;
    if (moveOn) {
      if (STRING_KINDS.has(next.kind)) {
        insert += ", " + ctx.quote + ctx.quote;
        cursor = from + insert.length - 1;
      } else {
        insert += ", ";
        cursor = from + insert.length;
      }
    }
    view.dispatch({
      changes: {from, to: after, insert},
      selection: {anchor: cursor},
      userEvent: "input.complete",
      annotations: pickedCompletion.of(completion),
    });
    if (moveOn && STRING_KINDS.has(next.kind)) startCompletion(view);
  };
}

// Picking a method: its parentheses, with the cursor inside, or inside the
// quotes of a first argument that is text, whose completion then opens.
function pickMethod(m) {
  const textFirst = m.args.length > 0 && STRING_KINDS.has(m.args[0].kind);
  return (view, completion, from, to) => {
    const doc = view.state.doc;
    if (doc.sliceString(to, to + 1) === "(") {
      view.dispatch({changes: {from, to, insert: m.name}, selection: {anchor: from + m.name.length + 1},
        userEvent: "input.complete", annotations: pickedCompletion.of(completion)});
      return;
    }
    const insert = m.name + (m.args.length === 0 ? "()" : textFirst ? '("")' : "()");
    const cursor = from + m.name.length + (m.args.length === 0 ? 2 : textFirst ? 2 : 1);
    view.dispatch({changes: {from, to, insert}, selection: {anchor: cursor},
      userEvent: "input.complete", annotations: pickedCompletion.of(completion)});
    if (textFirst) startCompletion(view);
  };
}

function memberOptions(kind, section, rank) {
  return (MEMBERS[kind] || []).map((m, i) => (m.type === "method"
    ? {label: m.name, type: "method", detail: argumentsText(m), info: m.info, apply: pickMethod(m), section, order: rank + i}
    : {label: m.name, type: "property", detail: m.detail, info: m.info, section, order: rank + i}));
}

function answerOptions(entries, phrases, section, rank) {
  const options = [];
  for (const e of entries) {
    if (e.encrypted || e.system) continue;
    options.push({
      label: e.name, type: "variable", detail: typeWord(phrases, e),
      info: e.label && e.label !== e.name ? e.label : undefined, section, order: rank + e.order,
    });
  }
  return options;
}

function section(name, rank) {
  return {name, rank};
}

function membersAfterDot(a, ctx, config) {
  const receiver = a.classify(ctx.object, false);
  if (!receiver) return null;
  const {catalogue, phrases} = config;
  let options = [];
  switch (receiver.kind) {
    case "s":
      options = answerOptions(catalogue.questions.values(), phrases, section(phrases.sectionQuestions, 0), 0)
        .concat(memberOptions("s", section(phrases.sectionSubmission, 1), 100000));
      break;
    case "row": {
      const repeat = catalogue.repeats.get(receiver.repeat);
      options = (repeat ? answerOptions(repeat.columns.values(), phrases, section(phrases.sectionColumns, 0), 0) : [])
        .concat(memberOptions("row", section(phrases.sectionRow, 1), 100000));
      break;
    }
    case "lookupRow": {
      const list = catalogue.lookups.get(receiver.list);
      options = list ? list.columns.map((c, i) => ({label: c, type: "property", order: i})) : [];
      break;
    }
    case "api":
    case "case":
    case "parent":
    case "rows":
      options = memberOptions(receiver.kind, undefined, 0);
      break;
  }
  if (!options.length) return null;
  return {from: ctx.from, to: ctx.to, options, validFor: /^[\w$]*$/};
}

// The names an argument of the given kind takes.
function namesFor(kind, info, a, config) {
  const {catalogue, phrases} = config;
  const receiver = info.receiver;
  const rowRepeat = receiver.kind === "row" ? catalogue.repeats.get(receiver.repeat) : null;
  const target = receiver.kind === "case" ? catalogue.case : receiver.kind === "parent" ? catalogue.parent : null;
  switch (kind) {
    case "repeat":
    case "nested": {
      const parent = kind === "repeat" ? "maintable" : receiver.repeat;
      const out = [];
      for (const r of catalogue.repeats.values()) {
        if (r.parent === parent) {
          out.push({label: r.name, type: "class", detail: r.label && r.label !== r.name ? r.label : phrases.typeRepeat, order: r.order});
        }
      }
      return out;
    }
    case "multi": {
      const source = receiver.kind === "s" ? catalogue.questions.values() : rowRepeat ? rowRepeat.columns.values() : [];
      return answerOptions([...source].filter(e => e.multi), phrases, undefined, 0);
    }
    case "choice": {
      const variable = info.args.length ? a.stringValue(info.args[0]) : null;
      if (variable === null) return [];
      const entry = receiver.kind === "s" ? catalogue.questions.get(variable) : rowRepeat ? rowRepeat.columns.get(variable) : null;
      return entry && !entry.encrypted ? choiceOptions(entry) : [];
    }
    case "list":
      return [...catalogue.lookups.values()].map(l => ({
        label: l.name, type: "class", detail: phrases.typeList, info: l.columns.join(", "), order: l.order,
      }));
    case "column": {
      const rows = info.args.length ? a.classify(info.args[0], false) : null;
      const repeat = rows && rows.kind === "rows" ? catalogue.repeats.get(rows.repeat) : null;
      return repeat ? answerOptions(repeat.columns.values(), phrases, undefined, 0) : [];
    }
    case "target":
    case "property":
    case "casecol": {
      if (!target) return [];
      const out = [];
      if (kind !== "casecol") {
        for (const p of target.properties.values()) {
          out.push({label: p.name, type: "property", detail: typeWord(phrases, p), section: section(phrases.sectionProperties, 0), order: p.order});
        }
      }
      if (kind !== "property") {
        for (const c of target.columns.values()) {
          if (c.encrypted) continue;
          out.push({
            label: c.name, type: "variable", detail: typeWord(phrases, c), info: c.label && c.label !== c.name ? c.label : undefined,
            section: section(phrases.sectionCaseColumns, 1), order: 100000 + c.order,
          });
        }
      }
      return out;
    }
  }
  return [];
}

function choiceOptions(entry) {
  return entry.choices.map((c, i) => ({label: c.code, type: "constant", detail: c.label && c.label !== c.code ? c.label : undefined, order: i}));
}

function insideString(a, ctx, config) {
  let names = [];
  let next = null;
  if (ctx.type === "arg") {
    const info = a.call(ctx.call, false);
    if (!info || !info.spec || !info.spec.args) return null;
    const arg = info.spec.args[ctx.index];
    if (!arg || !STRING_KINDS.has(arg.kind)) return null;
    names = namesFor(arg.kind, info, a, config);
    next = info.spec.args[ctx.index + 1] || null;
  } else {
    const entry = answerOf(a, ctx.other, config.catalogue);
    if (!entry || entry.multi || entry.encrypted) return null;
    names = choiceOptions(entry);
  }
  if (!names.length) return null;
  const apply = pickString(ctx, next);
  return {
    from: ctx.contentFrom,
    to: ctx.contentTo,
    options: names.map(o => Object.assign(o, {apply})),
    validFor: /^[^"'`\\\n]*$/,
  };
}

// A module without its function is offered one, at the top level.
const RUN_SNIPPET = "export default function run(s, api) {\n\t${}\n}";
const NOT_TOP = new Set(["String", "TemplateString", "LineComment", "BlockComment", "RegExp"]);

function runSnippet(a, state, pos, config, explicit) {
  if (a.run) return null;
  for (let p = a.tree.resolveInner(pos, -1); p; p = p.parent) {
    if (NOT_TOP.has(p.name) || p.name === "Block" || p.name === "ParamList" || p.name === "ArgList") return null;
  }
  const word = /[\w$]*$/.exec(state.doc.sliceString(Math.max(0, pos - 40), pos))[0];
  if (!word && !explicit) return null;
  return {
    from: pos - word.length,
    options: [snippetCompletion(RUN_SNIPPET, {
      label: "export default function run(s, api)", type: "keyword", detail: config.phrases.runSnippet, boost: 99,
    })],
    validFor: /^[\w$]*$/,
  };
}

export function completeAt(state, pos, config, explicit = false) {
  const a = analyse(state);
  const node = a.tree.resolveInner(pos, -1);
  const member = memberContext(a, node, pos);
  if (member) return membersAfterDot(a, member, config);
  const ctx = stringContext(a, node, pos);
  if (ctx) return insideString(a, ctx, config);
  return runSnippet(a, state, pos, config, explicit);
}

export function actionsCompletionSource(config) {
  return context => completeAt(context.state, context.pos, config, context.explicit);
}

// Form order inside a section, then the name.
export function compareCompletions(a, b) {
  const x = a.order === undefined ? Infinity : a.order;
  const y = b.order === undefined ? Infinity : b.order;
  if (x !== y) return x < y ? -1 : 1;
  return a.label.localeCompare(b.label);
}
