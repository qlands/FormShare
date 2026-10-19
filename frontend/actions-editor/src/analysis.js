// What the module's syntax tree says about the API: which names the run's
// parameters have, which declarations shadow them, and what an expression is
// as far as the API goes (the submission, the case, the rows of a repeat…).
//
// Completion and signature help take the likeliest reading: a variable is
// followed to what it was given. The checks take only the certain one: the
// name is the run's own parameter, or a const given it, with nothing
// declaring the same name around the use. A check that is not certain is
// not made, since a false alarm costs more than a miss (the server's run
// reports the rest).

import {syntaxTree, ensureSyntaxTree} from "@codemirror/language";
import {member} from "./model.js";

const FUNCTIONS = new Set(["FunctionDeclaration", "FunctionExpression", "ArrowFunction", "MethodDeclaration"]);
const PATTERNS = new Set(["ObjectPattern", "ArrayPattern", "PatternProperty"]);
const FOR_SPECS = new Set(["ForSpec", "ForInSpec", "ForOfSpec"]);
const BLOCKS = new Set(["Block", "ForStatement", "SwitchBody", "ClassBody", "Script"]);
// Array methods whose callback receives a row, and at which parameter.
const CALLBACK_ROW = {forEach: 0, map: 0, filter: 0, some: 0, every: 0, find: 0, findIndex: 0, flatMap: 0, reduce: 1};
// Array methods that give rows back.
const STILL_ROWS = new Set(["filter", "slice", "concat", "reverse", "sort"]);

function isFunction(node) {
  return FUNCTIONS.has(node.name) || (node.name === "Property" && !!node.getChild("ParamList"));
}

// The function, or the script, a node is in (not the node itself).
function enclosingFunction(node) {
  for (let p = node.parent; p; p = p.parent) {
    if (isFunction(p) || p.name === "Script") return p;
  }
  return node;
}

function enclosingBlock(node) {
  for (let p = node.parent; p; p = p.parent) {
    if (BLOCKS.has(p.name) || isFunction(p)) return p;
  }
  return node;
}

// How many arguments, or parameters, come before a child of a list.
function commasBefore(list, child) {
  let count = 0;
  for (let c = list.firstChild; c && c.from < child.from; c = c.nextSibling) {
    if (c.name === ",") count++;
  }
  return count;
}

export function fullTree(state) {
  return ensureSyntaxTree(state, state.doc.length, 400) || syntaxTree(state);
}

const cache = new WeakMap();

// One analysis per editor state, shared by completion, signature help and
// the checks.
export function analyse(state) {
  let analysis = cache.get(state);
  if (!analysis) {
    analysis = new Analysis(state);
    cache.set(state, analysis);
  }
  return analysis;
}

class Analysis {
  constructor(state) {
    this.state = state;
    this.tree = fullTree(state);
    this.decls = new Map();
    this.tree.iterate({
      enter: ref => {
        if (ref.name !== "VariableDefinition") return;
        const decl = this.declaration(ref.node);
        if (!decl) return;
        if (!this.decls.has(decl.name)) this.decls.set(decl.name, []);
        this.decls.get(decl.name).push(decl);
      },
    });
    this.run = this.findRun();
  }

  text(node) {
    return this.state.doc.sliceString(node.from, node.to);
  }

  // A declared name, with two scopes: `exact`, where the name means this
  // declaration (for completion), and `wide`, where it might (for the
  // checks: var is hoisted, and a let anywhere in a function is taken to
  // cover all of it).
  declaration(node) {
    const name = this.text(node);
    let child = node;
    let p = node.parent;
    while (p && PATTERNS.has(p.name)) {
      child = p;
      p = p.parent;
    }
    if (!p) return null;
    const direct = child === node;
    const range = n => ({from: n.from, to: n.to, node: n});
    const decl = {name, node, kind: "other", direct};
    if (p.name === "ParamList") {
      const fn = p.parent;
      Object.assign(decl, {kind: "param", fn, index: commasBefore(p, child), exact: range(fn), wide: range(fn)});
      // A row handed to the callback of an array method.
      const call = fn && fn.parent && fn.parent.name === "ArgList" ? fn.parent.parent : null;
      if (call && call.name === "CallExpression" && (fn.name === "FunctionExpression" || fn.name === "ArrowFunction")) {
        decl.callbackOf = call;
      }
      return decl;
    }
    if (p.name === "VariableDeclaration") {
      const keyword = p.firstChild ? p.firstChild.name : "var";
      decl.kind = keyword === "let" || keyword === "const" ? keyword : "var";
      if (direct && child.nextSibling && child.nextSibling.name === "Equals") decl.init = child.nextSibling.nextSibling;
      const inFor = p.parent && FOR_SPECS.has(p.parent.name);
      const exact = inFor ? p.parent.parent : decl.kind === "var" ? enclosingFunction(p) : enclosingBlock(p);
      decl.exact = range(exact || p);
      decl.wide = range(enclosingFunction(p));
      return decl;
    }
    if (FOR_SPECS.has(p.name)) {
      let keyword = "var";
      for (let c = p.firstChild; c; c = c.nextSibling) {
        if (c.name === "let" || c.name === "const" || c.name === "var") keyword = c.name;
      }
      decl.kind = keyword;
      if (p.name === "ForOfSpec" && direct) {
        for (let c = child.nextSibling; c; c = c.nextSibling) {
          if (c.name === "of") {
            decl.iterable = c.nextSibling;
            break;
          }
        }
      }
      decl.exact = range(keyword === "var" ? enclosingFunction(p) : p.parent || p);
      decl.wide = range(enclosingFunction(p));
      return decl;
    }
    if (p.name === "CatchClause") {
      return Object.assign(decl, {kind: "catch", exact: range(p), wide: range(enclosingFunction(p))});
    }
    if (p.name === "FunctionDeclaration" || p.name === "ClassDeclaration") {
      const container = enclosingBlock(p.parent && p.parent.name === "ExportDeclaration" ? p.parent : p);
      return Object.assign(decl, {kind: "function", exact: range(container), wide: range(enclosingFunction(p))});
    }
    if (p.name === "FunctionExpression" || p.name === "ClassExpression") {
      return Object.assign(decl, {kind: "fname", exact: range(p), wide: range(p)});
    }
    const top = this.tree.topNode;
    if (p.name === "ImportDeclaration") {
      return Object.assign(decl, {kind: "import", exact: range(top), wide: range(top)});
    }
    const around = enclosingFunction(p);
    return Object.assign(decl, {exact: range(around), wide: range(around)});
  }

  // export default function run(s, api) { … }
  findRun() {
    for (let n = this.tree.topNode.firstChild; n; n = n.nextSibling) {
      if (n.name !== "ExportDeclaration" || !n.getChild("default")) continue;
      const fn = n.getChild("FunctionDeclaration");
      const nameNode = fn && fn.getChild("VariableDefinition");
      if (!nameNode || this.text(nameNode) !== "run") continue;
      const params = [];
      const list = fn.getChild("ParamList");
      if (list) {
        for (let c = list.firstChild; c; c = c.nextSibling) {
          if (c.name === "VariableDefinition") params[commasBefore(list, c)] = this.text(c);
        }
      }
      return {fn, async: !!fn.getChild("async"), params, s: params[0] || null, api: params[1] || null};
    }
    return null;
  }

  declsOf(name) {
    return this.decls.get(name) || [];
  }

  // The declaration a name means at a position: the innermost exact scope.
  bindingAt(name, pos) {
    let best = null;
    for (const d of this.declsOf(name)) {
      if (d.exact.from <= pos && pos <= d.exact.to) {
        if (!best || d.exact.to - d.exact.from < best.exact.to - best.exact.from ||
            (d.exact.to - d.exact.from === best.exact.to - best.exact.from && d.node.from > best.node.from && d.node.from <= pos)) {
          best = d;
        }
      }
    }
    return best;
  }

  // Which parameter of run a name certainly is at a position, or -1: the
  // only innermost declaration that might cover it is run's own.
  certainParam(name, pos) {
    if (!this.run) return -1;
    let inner = [];
    let size = Infinity;
    for (const d of this.declsOf(name)) {
      if (d.wide.from > pos || pos > d.wide.to) continue;
      const s = d.wide.to - d.wide.from;
      if (s < size) {
        inner = [d];
        size = s;
      } else if (s === size) {
        inner.push(d);
      }
    }
    if (inner.length !== 1) return -1;
    const d = inner[0];
    return d.kind === "param" && d.direct && d.fn && d.fn.from === this.run.fn.from ? d.index : -1;
  }

  // Whether a name means the global object of that name at a position.
  isGlobal(name, pos) {
    return !this.declsOf(name).some(d => d.wide.from <= pos && pos <= d.wide.to);
  }

  // A string literal's value, or null for anything else (a template, a
  // string with escapes, one not closed).
  stringValue(node) {
    if (!node || node.name !== "String") return null;
    const t = this.text(node);
    if (t.length < 2 || t[t.length - 1] !== t[0] || t.indexOf("\\") >= 0) return null;
    for (let c = node.firstChild; c; c = c.nextSibling) {
      if (c.type.isError) return null;
    }
    return t.slice(1, -1);
  }

  // What an expression is: {kind: "s" | "api" | "case" | "parent" | "row" |
  // "rows" | "lookupRow", repeat, list}, or null. Certain readings follow the
  // run's parameters and const declarations only.
  classify(node, certain = false, depth = 0) {
    if (!node || depth > 12) return null;
    switch (node.name) {
      case "VariableName": {
        const name = this.text(node);
        if (certain) {
          const index = this.certainParam(name, node.from);
          if (index === 0) return {kind: "s"};
          if (index === 1) return {kind: "api"};
          const d = this.bindingAt(name, node.from);
          if (d && d.kind === "const" && d.init && this.declsOf(name).length === 1) {
            const c = this.classify(d.init, true, depth + 1);
            return c && (c.kind === "case" || c.kind === "parent") ? c : null;
          }
          return null;
        }
        const d = this.bindingAt(name, node.from);
        if (!d) return null;
        if (d.kind === "param" && this.run && d.fn && d.fn.from === this.run.fn.from && d.direct) {
          return d.index === 0 ? {kind: "s"} : d.index === 1 ? {kind: "api"} : null;
        }
        if (d.iterable) {
          const it = this.classify(d.iterable, false, depth + 1);
          return it && it.kind === "rows" ? {kind: "row", repeat: it.repeat} : null;
        }
        if (d.callbackOf && d.direct) {
          const callee = d.callbackOf.firstChild;
          if (callee && callee.name === "MemberExpression") {
            const method = callee.lastChild && callee.lastChild.name === "PropertyName" ? this.text(callee.lastChild) : "";
            if (CALLBACK_ROW[method] === d.index) {
              const rows = this.classify(callee.firstChild, false, depth + 1);
              if (rows && rows.kind === "rows") return {kind: "row", repeat: rows.repeat};
            }
          }
          return null;
        }
        if (d.init) return this.classify(d.init, false, depth + 1);
        return null;
      }
      case "ParenthesizedExpression":
        return this.classify(node.firstChild && node.firstChild.nextSibling, certain, depth + 1);
      case "MemberExpression": {
        const object = node.firstChild;
        const op = object && object.nextSibling;
        if (!op) return null;
        if (op.name === "." || op.name === "?.") {
          const prop = op.nextSibling;
          if (!prop || prop.name !== "PropertyName") return null;
          const o = this.classify(object, certain, depth + 1);
          if (!o) return null;
          const p = this.text(prop);
          if (o.kind === "api" && p === "case") return {kind: "case"};
          if (o.kind === "case" && p === "parent") return {kind: "parent"};
          return null;
        }
        if (op.name === "[") {
          const o = this.classify(object, certain, depth + 1);
          return o && o.kind === "rows" ? {kind: "row", repeat: o.repeat} : null;
        }
        return null;
      }
      case "CallExpression": {
        const info = this.call(node, certain, depth + 1);
        if (!info) return null;
        const {receiver, method, args} = info;
        const first = args.length ? this.stringValue(args[0]) : null;
        if ((receiver.kind === "s" || receiver.kind === "row") && method === "repeat" && first !== null) {
          return {kind: "rows", repeat: first, of: receiver};
        }
        if (receiver.kind === "api" && method === "lookup" && first !== null) return {kind: "lookupRow", list: first};
        if (receiver.kind === "rows" && STILL_ROWS.has(method)) return {kind: "rows", repeat: receiver.repeat};
        if (receiver.kind === "rows" && method === "find") return {kind: "row", repeat: receiver.repeat};
        return null;
      }
    }
    return null;
  }

  // A call of a method on something classify knows: {receiver, method, spec,
  // args, argList, object, property}, or null.
  call(node, certain = false, depth = 0) {
    if (!node || node.name !== "CallExpression") return null;
    const callee = node.firstChild;
    const argList = node.getChild("ArgList");
    if (!callee || !argList || callee.name !== "MemberExpression") return null;
    const object = callee.firstChild;
    const op = object && object.nextSibling;
    const prop = op && op.nextSibling;
    if (!op || (op.name !== "." && op.name !== "?.") || !prop || prop.name !== "PropertyName") return null;
    const receiver = this.classify(object, certain, depth);
    if (!receiver) return null;
    const method = this.text(prop);
    return {receiver, method, spec: member(receiver.kind, method), args: argsOf(argList), argList, object, property: prop};
  }
}

export function argsOf(argList) {
  const args = [];
  for (let c = argList.firstChild; c; c = c.nextSibling) {
    if (c.name === "(" || c.name === ")" || c.name === ",") continue;
    args.push(c);
  }
  return args;
}

export {commasBefore};
