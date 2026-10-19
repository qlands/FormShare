// The checks made while typing. Each one says what the server, or every
// host, would do with the module, and only where that is certain:
//
// - errors are what refuses the module when it is saved (processes/actions/
//   host.py, load_module) or fails every run of it (the prelude's refusals,
//   processes/actions/prelude.js; a write the server cannot apply);
// - warnings are what runs but cannot be what was meant: a question the form
//   does not have reads undefined, a repeat it does not have gives [].
//
// The server stays the judge: the dry run and the run log report the rest.

import {linter} from "@codemirror/lint";
import {analyse, argsOf} from "./analysis.js";
import {closest, member, MEMBERS, OBJECT_MEMBERS} from "./model.js";

// load_module's two expressions (processes/actions/host.py), as they are.
const EXPORT = /^\s*export\s+default\s+(?=function\b)/m;
const RUN = /\bfunction\s+run\s*\(/;
const SOURCE_BYTES = 64 * 1024;

// The prelude's locale refusals, and what quickjs-ng does not have.
const LOCALE = new Set(["toLocaleString", "toLocaleDateString", "toLocaleTimeString", "localeCompare", "toLocaleUpperCase", "toLocaleLowerCase"]);
const TIMERS = new Set(["setTimeout", "setInterval", "setImmediate", "clearTimeout", "clearInterval", "queueMicrotask"]);
const ABSENT = new Set(["performance", "WeakRef", "FinalizationRegistry", "fetch", "XMLHttpRequest", "require", "process", "window", "document"]);
const AGGREGATES = new Set(["avg", "sum", "count", "min", "max"]);

// A phrase with its {names} filled in.
export function format(template, values = {}) {
  return String(template).replace(/\{(\w+)\}/g, (whole, key) => (key in values ? String(values[key]) : whole));
}

function utf8Length(text) {
  if (typeof TextEncoder !== "undefined") return new TextEncoder().encode(text).length;
  return unescape(encodeURIComponent(text)).length;
}

export function diagnose(state, config) {
  const {catalogue, phrases} = config;
  const a = analyse(state);
  const doc = state.doc;
  const text = doc.toString();
  const found = [];
  const seen = new Set();
  const add = (from, to, severity, message) => {
    if (to <= from) {
      if (from < doc.length) to = from + 1;
      else if (from > 0) from = from - 1;
    }
    const key = from + ":" + to + ":" + message;
    if (seen.has(key)) return;
    seen.add(key);
    found.push({from, to, severity, message, source: phrases.source});
  };
  const suggest = (message, name, names) => {
    const better = closest(name, names);
    return better ? message + " " + format(phrases.didYouMean, {name: better}) : message;
  };
  if (text.trim() === "") return found;

  // What cannot be read. Only the first place: what follows it is often the
  // same mistake seen again.
  let broken = null;
  a.tree.iterate({
    enter: ref => {
      if (broken) return false;
      if (ref.type.isError) {
        broken = {from: ref.from, to: ref.to};
        return false;
      }
      return undefined;
    },
  });
  if (broken) add(broken.from, broken.to, "error", phrases.syntax);

  // The module as the server loads it.
  const exported = EXPORT.exec(text);
  const script = exported ? text.slice(0, exported.index) + text.slice(exported.index + exported[0].length) : text;
  if (!exported || !RUN.test(script)) {
    let from = 0;
    let to = doc.line(1).to;
    for (let n = a.tree.topNode.firstChild; n; n = n.nextSibling) {
      if (n.name === "ExportDeclaration" && n.getChild("default")) {
        from = n.from;
        to = Math.min(n.to, doc.lineAt(n.from).to);
        break;
      }
    }
    add(from, to, "error", phrases.noRun);
  }
  if (utf8Length(text) > SOURCE_BYTES) add(doc.length - 1, doc.length, "error", format(phrases.tooLarge, {kb: SOURCE_BYTES / 1024}));

  const known = catalogue.known;
  const flaggedNoTarget = new Set();
  let defaults = 0;

  const isGlobal = (node, name) => a.text(node) === name && a.isGlobal(name, node.from);
  const assigned = node => {
    const p = node.parent;
    if (!p) return false;
    if (p.name === "AssignmentExpression" && p.firstChild && p.firstChild.from === node.from && p.firstChild.to === node.to) return true;
    return p.name === "UpdateExpression" || p.name === "PostfixExpression";
  };

  // No case, or no parent, where the module reads one: said once, on the
  // word case or parent.
  const noTarget = (kind, objectNode) => {
    if (!known) return false;
    if (kind === "case" ? catalogue.case : catalogue.parent) return false;
    const word = objectNode.lastChild && objectNode.lastChild.name === "PropertyName" ? objectNode.lastChild : objectNode;
    if (!flaggedNoTarget.has(word.from)) {
      flaggedNoTarget.add(word.from);
      add(word.from, word.to, "warning", kind === "case" ? phrases.noCase : phrases.noParent);
    }
    return true;
  };

  const checkMember = node => {
    const object = node.firstChild;
    const op = object && object.nextSibling;
    const prop = op && op.nextSibling;
    if (!op || (op.name !== "." && op.name !== "?.") || !prop || prop.name !== "PropertyName") return;
    const name = a.text(prop);
    if (object.name === "VariableName") {
      if (name === "now" && isGlobal(object, "Date")) add(node.from, node.to, "error", phrases.dateNow);
      if (name === "random" && isGlobal(object, "Math")) add(node.from, node.to, "error", phrases.mathRandom);
    }
    if (LOCALE.has(name)) add(prop.from, prop.to, "error", format(phrases.locale, {name}));

    const owner = a.classify(object, true);
    if (!owner) return;
    if (owner.kind === "s") {
      if (!known || !catalogue.questions.size || assigned(node)) return;
      if (member("s", name) || OBJECT_MEMBERS.has(name)) return;
      const question = catalogue.questions.get(name);
      if (question && question.encrypted) add(prop.from, prop.to, "warning", format(phrases.encryptedRead, {name}));
      else if (!question) {
        add(prop.from, prop.to, "warning", suggest(format(phrases.unknownQuestion, {name}), name, [...catalogue.questions.keys()]));
      }
      return;
    }
    if (owner.kind === "api") {
      if (assigned(node) || member("api", name) || OBJECT_MEMBERS.has(name)) return;
      add(prop.from, prop.to, "warning", suggest(format(phrases.unknownApiMember, {name}), name, MEMBERS.api.map(m => m.name)));
      return;
    }
    if (owner.kind === "case" || owner.kind === "parent") {
      if (noTarget(owner.kind, object)) return;
      if (assigned(node)) {
        add(node.from, node.to, "warning", phrases.assignCase);
        return;
      }
      if (member(owner.kind, name) || OBJECT_MEMBERS.has(name)) return;
      add(prop.from, prop.to, "warning", format(owner.kind === "case" ? phrases.unknownCaseMember : phrases.unknownParentMember, {name}));
    }
  };

  const checkCall = node => {
    const callee = node.firstChild;
    if (callee && callee.name === "VariableName" && isGlobal(callee, "Date")) {
      add(node.from, node.to, "error", phrases.dateCall);
      return;
    }
    const info = a.call(node, true);
    if (!info || !info.spec) return;
    const {receiver, method, args} = info;
    // An empty name is one being written: the quotes come before it.
    const literal = i => {
      const value = args[i] ? a.stringValue(args[i]) : null;
      return value === "" ? null : value;
    };
    const range = i => args[i];

    if (receiver.kind === "s") {
      if (!known) return;
      if (method === "repeat") {
        const name = literal(0);
        if (name === null || !catalogue.repeats.size) return;
        const repeat = catalogue.repeats.get(name);
        const top = [...catalogue.repeats.values()].filter(r => r.parent === "maintable").map(r => r.name);
        if (!repeat) add(range(0).from, range(0).to, "warning", suggest(format(phrases.unknownRepeat, {name}), name, top));
        else if (repeat.parent !== "maintable") add(range(0).from, range(0).to, "warning", format(phrases.nestedRepeat, {name, parent: repeat.parent}));
      }
      if (method === "selected" || method === "selections") {
        const name = literal(0);
        if (name === null || !catalogue.questions.size) return;
        const question = catalogue.questions.get(name);
        const multis = [...catalogue.questions.values()].filter(q => q.multi).map(q => q.name);
        if (!question) add(range(0).from, range(0).to, "warning", suggest(format(phrases.unknownMulti, {name}), name, multis));
        else if (!question.multi) add(range(0).from, range(0).to, "warning", format(phrases.notMulti, {name}));
        else if (method === "selected" && !question.encrypted && question.choices.length) {
          const code = literal(1);
          if (code !== null && !question.choices.some(c => c.code === code)) {
            add(range(1).from, range(1).to, "warning",
              suggest(format(phrases.unknownChoice, {name, code}), code, question.choices.map(c => c.code)));
          }
        }
      }
      return;
    }

    if (receiver.kind === "api") {
      if (method === "lookup" && args.length) {
        if (a.run && a.run.api !== "api") add(info.object.from, info.object.to, "warning", phrases.lookupApiName);
        if (args[0].name !== "String") add(args[0].from, args[0].to, "warning", phrases.lookupNotText);
        else {
          const name = literal(0);
          if (name !== null && known && !catalogue.lookups.has(name)) {
            add(args[0].from, args[0].to, "error", suggest(format(phrases.unknownList, {name}), name, [...catalogue.lookups.keys()]));
          }
        }
      }
      if (AGGREGATES.has(method) && args.length >= 2 && known) {
        const column = literal(1);
        const rows = args[0].name === "CallExpression" ? a.call(args[0], true) : null;
        const repeatName = rows && rows.receiver.kind === "s" && rows.method === "repeat" && rows.args.length ? a.stringValue(rows.args[0]) : null;
        const repeat = repeatName !== null ? catalogue.repeats.get(repeatName) : null;
        if (column !== null && repeat && repeat.columns.size && !repeat.columns.has(column)) {
          add(range(1).from, range(1).to, "warning",
            suggest(format(phrases.unknownRepeatColumn, {repeat: repeatName, name: column}), column, [...repeat.columns.keys()]));
        }
      }
      return;
    }

    if (receiver.kind === "case" || receiver.kind === "parent") {
      if (!known) return;
      const target = receiver.kind === "case" ? catalogue.case : catalogue.parent;
      if (!target) return;
      const name = literal(0);
      if (name === null) return;
      const parent = receiver.kind === "parent";
      const properties = target.properties;
      const columns = target.columns;
      if (method === "set") {
        if (properties.has(name)) return;
        const column = columns.get(name);
        if (column && column.encrypted) add(range(0).from, range(0).to, "error", format(phrases.encryptedWrite, {name}));
        else if (!column) {
          const names = [...properties.keys()].concat([...columns.values()].filter(c => !c.encrypted).map(c => c.name));
          add(range(0).from, range(0).to, "error",
            suggest(format(parent ? phrases.unknownParentTarget : phrases.unknownTarget, {name}), name, names));
        }
      } else if (method === "property") {
        if (!properties.has(name)) {
          add(range(0).from, range(0).to, "error",
            suggest(format(parent ? phrases.unknownParentProperty : phrases.unknownProperty, {name}), name, [...properties.keys()]));
        }
      } else if (method === "value") {
        const column = columns.get(name);
        if (!column) {
          add(range(0).from, range(0).to, "error",
            suggest(format(parent ? phrases.unknownParentColumn : phrases.unknownColumn, {name}), name, [...columns.keys()]));
        } else if (column.encrypted) {
          add(range(0).from, range(0).to, "warning", format(phrases.encryptedRead, {name}));
        }
      }
    }
  };

  a.tree.iterate({
    enter: ref => {
      const node = ref.node;
      switch (ref.name) {
        case "ImportDeclaration":
          add(node.from, Math.min(node.to, doc.lineAt(node.from).to), "error", phrases.noImports);
          return false;
        case "ExportDeclaration":
          if (node.getChild("default") && defaults++ === 0) break;
          add(node.from, node.from + 6, "error", phrases.onlyRun);
          break;
        case "DynamicImport":
          add(node.from, node.to, "error", phrases.dynamicImport);
          break;
        case "AwaitExpression":
          add(node.from, node.from + 5, "warning", phrases.await);
          break;
        case "NewExpression": {
          const callee = node.getChild("VariableName");
          const argList = node.getChild("ArgList");
          if (callee && isGlobal(callee, "Date") && (!argList || argsOf(argList).length === 0)) {
            add(node.from, node.to, "error", phrases.newDate);
          }
          break;
        }
        case "CallExpression":
          checkCall(node);
          break;
        case "MemberExpression":
          checkMember(node);
          break;
        case "VariableName": {
          const name = a.text(node);
          if ((name === "eval" || name === "Function") && a.isGlobal(name, node.from)) {
            add(node.from, node.to, "error", format(phrases.codeFromText, {name}));
          } else if (name === "Intl" && a.isGlobal(name, node.from)) {
            add(node.from, node.to, "error", format(phrases.locale, {name}));
          } else if (TIMERS.has(name) && a.isGlobal(name, node.from)) {
            add(node.from, node.to, "error", format(phrases.timers, {name}));
          } else if (ABSENT.has(name) && a.isGlobal(name, node.from)) {
            add(node.from, node.to, "error", format(phrases.absent, {name}));
          }
          break;
        }
      }
      return undefined;
    },
  });
  return found.sort((x, y) => x.from - y.from || x.to - y.to);
}

export function actionsLinter(config) {
  return linter(view => diagnose(view.state, config), {delay: 400});
}
