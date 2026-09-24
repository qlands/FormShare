// The prelude of the actions host: what runs before a module, everywhere.
//
// It builds `s` and `api` from the input (actions-api.md sections 4 and 5),
// collects what the module writes, and takes away what would make a run depend
// on where it happens (section 7). It is evaluated as a script, then the input
// as `var __fs_built = __fs_build(<input>);`, then the module with its
// `export default` taken off, then `run(__fs_built.s, __fs_built.api);`, and
// what is read back is `{writes: __fs.writes, log: __fs.log}`.
//
// This file is the one copy. The Kotlin host embeds it at build time
// (generatePrelude in build.gradle.kts) and runs it on the JVM, Android, iOS and
// as the runactions tool on Linux; FormShare's interim in-process engine ran the
// same text under the name PRELUDE in processes/actions/host.py, which this took
// over on 2026-09-23. A change here is a change to the contract: say so in
// FormShare's roadmap (rstools.md) before making one.
//
// It must stay within ES2020 for as long as an ES2020 engine runs it anywhere.

"use strict";
var __fs = { writes: [], log: [], input: null };

function __fs_row(data) {
  var row = {};
  var values = data.values || {};
  for (var key in values) { if (Object.prototype.hasOwnProperty.call(values, key)) row[key] = values[key]; }
  var repeats = data.repeats || {};
  var selections = data.selections || {};
  Object.defineProperty(row, "rowuuid", { value: data.rowuuid === undefined ? null : data.rowuuid, enumerable: true });
  Object.defineProperty(row, "parent_rowuuid", { value: data.parent_rowuuid === undefined ? null : data.parent_rowuuid, enumerable: true });
  Object.defineProperty(row, "repeat", { value: function __fs_repeat (name) {
    var rows = repeats[name];
    return rows ? rows.map(__fs_row) : [];
  }});
  Object.defineProperty(row, "selected", { value: function __fs_selected (variable, code) {
    var chosen = selections[variable] || [];
    return chosen.indexOf(String(code)) >= 0;
  }});
  Object.defineProperty(row, "selections", { value: function __fs_selections (variable) {
    return (selections[variable] || []).slice();
  }});
  return row;
}

function __fs_case(data, scope) {
  if (!data) return null;
  var values = data.values || {};
  var properties = data.properties || {};
  var obj = {
    rowuuid: data.rowuuid === undefined ? null : data.rowuuid,
    table: data.table === undefined ? null : data.table,
    active: data.active === undefined ? true : !!data.active,
    parent: scope === "case" ? __fs_case(data.parent, "parent") : null,
    value: function __fs_value (column) {
      if (!Object.prototype.hasOwnProperty.call(values, column)) throw new Error("The " + (scope === "parent" ? "parent" : "case") + " has no column " + column);
      return values[column] === undefined ? null : values[column];
    },
    property: function __fs_property (name) {
      if (!Object.prototype.hasOwnProperty.call(properties, name)) throw new Error("The " + (scope === "parent" ? "parent" : "case") + " has no property " + name);
      return properties[name] === undefined ? null : properties[name];
    },
    set: function __fs_set (name, value) {
      if (value === undefined) value = null;
      __fs.writes.push({ scope: scope, kind: "set", name: String(name), value: value });
    },
    activate: function __fs_activate () { __fs.writes.push({ scope: scope, kind: "active", value: 1 }); },
    deactivate: function __fs_deactivate () { __fs.writes.push({ scope: scope, kind: "active", value: 0 }); }
  };
  return obj;
}

function __fs_numbers(rows, column) {
  var out = [];
  for (var i = 0; i < rows.length; i++) {
    var v = rows[i][column];
    if (v === null || v === undefined || v === "") continue;
    var n = typeof v === "number" ? v : Number(v);
    if (isNaN(n)) continue;
    out.push(n);
  }
  return out;
}

function __fs_days(a, b) {
  function __fs_parse(text) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(text));
    if (!m) throw new Error("Not a date: " + text);
    return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }
  return Math.floor((__fs_parse(b) - __fs_parse(a)) / 86400000);
}

function __fs_build(input) {
  __fs.input = input;
  var s = __fs_row(input.submission || {});
  Object.defineProperty(s, "submittedBy", { value: (input.submission || {}).submitted_by || null, enumerable: true });
  Object.defineProperty(s, "submittedDate", { value: (input.submission || {}).submitted_date || null, enumerable: true });
  var api = {
    case: __fs_case(input.case, "case"),
    now: input.now === undefined ? null : input.now,
    user: input.user === undefined ? null : input.user,
    lookup: function __fs_lookup (list, code) {
      var tables = input.lookups || {};
      if (!Object.prototype.hasOwnProperty.call(tables, String(list))) throw new Error("The lookup list " + list + " is not available to the module");
      var found = tables[String(list)][String(code)];
      return found === undefined ? null : found;
    },
    avg: function __fs_avg (rows, column) { var n = __fs_numbers(rows, column); if (!n.length) return null; var t = 0; for (var i = 0; i < n.length; i++) t += n[i]; return t / n.length; },
    sum: function __fs_sum (rows, column) { var n = __fs_numbers(rows, column); if (!n.length) return null; var t = 0; for (var i = 0; i < n.length; i++) t += n[i]; return t; },
    count: function __fs_count (rows, column) { var c = 0; for (var i = 0; i < rows.length; i++) { var v = rows[i][column]; if (v !== null && v !== undefined && v !== "") c++; } return c; },
    min: function __fs_min (rows, column) { var n = __fs_numbers(rows, column); return n.length ? Math.min.apply(null, n) : null; },
    max: function __fs_max (rows, column) { var n = __fs_numbers(rows, column); return n.length ? Math.max.apply(null, n) : null; },
    days: __fs_days,
    log: function __fs_log (message) { __fs.log.push(String(message)); }
  };
  return { s: s, api: api };
}

// Determinism (actions-api.md 7): nothing a run can read from where it runs.
(function () {
  var RealDate = Date;
  var SafeDate = new Proxy(RealDate, {
    construct: function (target, args) {
      if (args.length === 0) throw new Error("new Date() without arguments is not available; use api.now");
      return new target(...args);
    },
    apply: function () { throw new Error("Date() is not available; use api.now"); }
  });
  globalThis.Date = SafeDate;
  // Every date reaches the real constructor as its own .constructor, which
  // would be the clock again: new (new Date(0)).constructor().
  Object.defineProperty(RealDate.prototype, "constructor", { value: SafeDate, writable: true, configurable: true });
  RealDate.now = function () { throw new Error("Date.now is not available; use api.now"); };
  Math.random = function () { throw new Error("Math.random is not available"); };
  globalThis.eval = undefined;
  globalThis.Function = undefined;
  // Function by another road: the constructor of any function, generator or
  // async function evaluates text, (function () {}).constructor("...").
  var refuseConstructor = function Function() { throw new Error("Function is not available"); };
  [function () {}, function* () {}, async function () {}, async function* () {}].forEach(function (f) {
    Object.defineProperty(Object.getPrototypeOf(f), "constructor", { value: refuseConstructor, writable: false, configurable: false });
  });
})();

// The locale (actions-api.md 7): no function whose answer depends on where
// it runs. The engine has no Intl; these are the members that would reach a
// locale without it, made to say so instead.
(function () {
  function refuse(name) {
    return function () { throw new Error(name + " is not available: formatting is the module's own or api's"); };
  }
  var targets = [
    [Object.prototype, "toLocaleString"],
    [Number.prototype, "toLocaleString"],
    [Array.prototype, "toLocaleString"],
    [Date.prototype, "toLocaleString"],
    [Date.prototype, "toLocaleDateString"],
    [Date.prototype, "toLocaleTimeString"],
    [String.prototype, "localeCompare"],
    [String.prototype, "toLocaleUpperCase"],
    [String.prototype, "toLocaleLowerCase"]
  ];
  if (typeof BigInt !== "undefined") targets.push([BigInt.prototype, "toLocaleString"]);
  for (var i = 0; i < targets.length; i++) {
    Object.defineProperty(targets[i][0], targets[i][1], { value: refuse(targets[i][1]), writable: true, configurable: true });
  }
})();
