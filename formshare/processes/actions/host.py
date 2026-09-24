"""The QuickJS host: runs a module over an input and says what it wrote.

Pure with respect to the database. The caller assembles the input -- the
submission as rows, the case with its properties and its parent, a lookup
callback, now and the user -- runs the module, and gets back the writes the
module asked for, the log lines, and the change report they amount to,
or the failure. Applying the writes is the caller's business (server.py on
the server, the Kotlin host on a device), so a dry run and a real run are
the same call here.

The input shape is the one the golden triples of actions-api.md section 12
use, so those files can be run through this host directly::

    {"submission": {"rowuuid": "...", "values": {...}, "repeats": {"meals": [row, ...]},
                    "selections": {"crops": ["c1", "c3"]},
                    "submitted_by": "...", "submitted_date": "..."},
     "case": {"table": "teachers", "rowuuid": "...", "active": true,
              "values": {...}, "properties": {...}, "parent": {...} | null} | null,
     "lookups": {"crop_list": {"c1": {...}}},
     "now": "2026-09-23 10:00:00", "user": "enumerator01"}

A row is ``{"rowuuid", "parent_rowuuid", "values", "repeats", "selections"}``,
values typed as actions-api.md section 6 says.
"""

import json
import re

import quickjs

__all__ = [
    "RunResult",
    "run_module",
    "load_module",
    "ModuleError",
    "LIMITS",
    "changes_of",
    "lookups_named",
    "PRELUDE",
]

# actions-api.md section 7, the same in every host.
LIMITS = {"source_bytes": 64 * 1024, "memory_bytes": 16 * 1024 * 1024, "seconds": 0.25}

_EXPORT = re.compile(r"^\s*export\s+default\s+(?=function\b)", re.M)
_RUN = re.compile(r"\bfunction\s+run\s*\(")


class ModuleError(ValueError):
    """The module could not be loaded or ran into a failure; the message is
    what the owner reads, with the line when QuickJS gives one."""


class RunResult:
    """What one run produced. ``error`` is None when it succeeded."""

    def __init__(self, writes, log, error=None):
        self.writes = writes
        self.log = log
        self.error = error

    @property
    def ok(self):
        return self.error is None


# The JavaScript the host evaluates before the module: builds s and api from
# the input, collects the writes, and takes away what would make a run
# depend on where it happens.
PRELUDE = r"""
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
  RealDate.now = function () { throw new Error("Date.now is not available; use api.now"); };
  Math.random = function () { throw new Error("Math.random is not available"); };
  globalThis.eval = undefined;
  globalThis.Function = undefined;
})();
"""


def load_module(source):
    """The module as a script: ``export default`` taken off the function,
    which is how every host loads it. Refuses a module without the function
    or over the size limit."""
    if source is None or str(source).strip() == "":
        raise ModuleError("The module is empty")
    if len(source.encode("utf-8")) > LIMITS["source_bytes"]:
        raise ModuleError(
            "The module is larger than {} KB".format(LIMITS["source_bytes"] // 1024)
        )
    script, count = _EXPORT.subn("", source, count=1)
    if count != 1 or not _RUN.search(script):
        raise ModuleError("The module must export a default function run(s, api)")
    return script


def _clean_message(exception):
    """QuickJS's message without the stack, keeping the line of the module
    when there is one."""
    text = str(exception)
    lines = text.splitlines()
    message = lines[0] if lines else text
    if "interrupted" in message:
        return "The module ran longer than its budget of {} seconds".format(
            LIMITS["seconds"]
        )
    if "out of memory" in message.lower():
        return "The module used more than its budget of {} MB".format(
            LIMITS["memory_bytes"] // (1024 * 1024)
        )
    # The first frame of the module itself: not the prelude's helpers, not
    # the runner's own eval, which would name their lines instead.
    line = None
    for a_line in lines[1:]:
        found = re.search(r"at (\S+) \(<input>:(\d+)\)", a_line)
        if not found:
            continue
        frame = found.group(1)
        if frame.startswith("__fs") or frame in ("construct", "apply", "<eval>"):
            continue
        line = int(found.group(2))
        break
    if line is not None:
        return "{} (line {})".format(message, line)
    return message


def lookups_named(source):
    """The lookup lists a module names as literals -- ``api.lookup("x", ...)``
    -- which is how the server knows what to load before the run: the
    QuickJS binding cannot call back into Python while a time limit is
    set, so a lookup is answered from the input, never from a callback. A
    list named any other way is reported by the run as not available."""
    return sorted(
        set(re.findall(r"""api\.lookup\(\s*["']([^"']+)["']""", source or ""))
    )


def run_module(source, input_data, limits=None):
    """Runs the module over the input and returns a RunResult.

    :param source: the module text (actions-api.md section 3)
    :param input_data: the input, a dict as this module's docstring shows;
        ``lookups`` holds every list the module may read
    :param limits: LIMITS, or the same keys with other values
    """
    limits = dict(LIMITS, **(limits or {}))
    try:
        script = load_module(source)
    except ModuleError as e:
        return RunResult([], [], str(e))

    context = quickjs.Context()
    context.set_memory_limit(int(limits["memory_bytes"]))
    context.set_time_limit(float(limits["seconds"]))
    try:
        context.eval(PRELUDE)
        context.eval(
            "var __fs_built = __fs_build({});".format(
                json.dumps(input_data, ensure_ascii=False)
            )
        )
        context.eval(script)
        context.eval("run(__fs_built.s, __fs_built.api);")
        raw = context.eval("JSON.stringify({writes: __fs.writes, log: __fs.log})")
    except quickjs.JSException as e:
        return RunResult([], [], _clean_message(e))
    except quickjs.StackOverflow:
        return RunResult([], [], "The module ran out of stack")
    except Exception as e:  # pragma: no cover - a binding fault, not the module's
        return RunResult([], [], "The engine failed: {}".format(e))
    result = json.loads(raw)
    return RunResult(result.get("writes", []), result.get("log", []))


def changes_of(writes, case):
    """The change report of actions-api.md section 9 for a list of writes,
    against the case (and parent) the input carried: old from the data,
    new from the last write to each name. A write the case has no home for
    -- a name that is neither a property nor a column -- is a ModuleError.
    A write that leaves the value as it was is not reported.
    """
    if case is None and writes:
        raise ModuleError("The module wrote to a case the form does not have")
    last = {}
    for write in writes:
        scope = write.get("scope", "case")
        key = (scope, "_active" if write.get("kind") == "active" else write.get("name"))
        last[key] = write
    changes = []
    for (scope, name), write in last.items():
        target = case if scope == "case" else (case or {}).get("parent")
        if target is None:
            raise ModuleError("The module wrote to the case's parent and it has none")
        table = target.get("table") or ""
        if write.get("kind") == "active":
            old = 1 if target.get("active", True) else 0
            new = int(write.get("value"))
            column, into = "_active", table
        else:
            properties = target.get("properties") or {}
            values = target.get("values") or {}
            if name in properties:
                old, into = properties.get(name), table + "_properties"
            elif name in values:
                old, into = values.get(name), table
            else:
                raise ModuleError(
                    "{} is neither a property nor a column of {}".format(name, table)
                )
            column, new = name, write.get("value")
        if _same(old, new):
            continue
        changes.append(
            {
                "scope": "source",
                "table": into,
                "rowuuid": target.get("rowuuid"),
                "column": column,
                "old": None if old is None else str(old),
                "new": None if new is None else str(new),
            }
        )
    changes.sort(key=lambda c: (c["table"], c["column"]))
    return changes


def _same(old, new):
    if old is None or new is None:
        return old is None and new is None
    try:
        return float(old) == float(new)
    except (TypeError, ValueError):
        return str(old) == str(new)
