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
import os
import re
import subprocess
import tempfile

__all__ = [
    "RunResult",
    "run_module",
    "load_module",
    "ModuleError",
    "LIMITS",
    "changes_of",
    "lookups_named",
    "PRELUDE",
    "writes_from_changes",
    "js_string",
    "BINARY",
]

# The engine of record (actions-api.md 1; rstools.md 12.5): RSTools' Kotlin
# host with quickjs-ng, built for Linux and shipped like every other tool.
# Until it is there, the archived `quickjs` binding on PyPI runs the module
# in-process, at ES2020. run_module takes the binary's path when the caller
# has one and falls back to the binding.
BINARY = os.path.join("utilities", "RunActions", "runactions")

# actions-api.md section 7, the same in every host.
LIMITS = {
    "source_bytes": 64 * 1024,
    "memory_bytes": 16 * 1024 * 1024,
    "seconds": 0.25,
    # A deep recursion must meet the engine's limit before the thread's own
    # stack runs out; 256 KB is what every host sets (rstools.md 13.2).
    "stack_bytes": 256 * 1024,
}

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
        # The change report when the engine computed it (the binary does);
        # None when the caller derives it from the writes (changes_of).
        self.changes = None

    @property
    def ok(self):
        return self.error is None


# The JavaScript the host evaluates before the module: builds s and api from
# the input, collects the writes, and takes away what would make a run depend
# on where it happens. RSTools owns it (kotlinrstools/actions/prelude.js); the
# file beside this one is a verbatim copy for the interim engine, and a test
# compares the two whenever RSTools is beside FormShare (rstools.md 13.3).
PRELUDE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prelude.js")
with open(PRELUDE_FILE, encoding="utf-8") as _prelude:
    PRELUDE = _prelude.read()


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


def run_module(source, input_data, limits=None, engine=None):
    """Runs the module over the input and returns a RunResult.

    :param source: the module text (actions-api.md section 3)
    :param input_data: the input, a dict as this module's docstring shows;
        ``lookups`` holds every list the module may read
    :param limits: LIMITS, or the same keys with other values
    :param engine: the path of RSTools' runactions binary; None or a path
        that does not exist means the in-process binding
    """
    limits = dict(LIMITS, **(limits or {}))
    try:
        script = load_module(source)
    except ModuleError as e:
        return RunResult([], [], str(e))
    if engine and os.path.exists(engine):
        return _run_binary(engine, source, input_data)
    return _run_in_process(script, input_data, limits)


def _run_binary(engine, source, input_data):
    """RSTools' host as a subprocess (rstools.md 12.5): the module and the
    input as files, changes.json back. Exit 0: the report and the log, and
    the writes when the host lists them; 1: the module failed, the message
    in the file; 2: the input could not be read. The report alone is
    enough to apply from (writes_from_changes)."""
    workdir = tempfile.mkdtemp(prefix="fs_actions_")
    module_file = os.path.join(workdir, "module.js")
    input_file = os.path.join(workdir, "input.json")
    output_file = os.path.join(workdir, "changes.json")
    try:
        with open(module_file, "w", encoding="utf-8") as a_file:
            a_file.write(source)
        with open(input_file, "w", encoding="utf-8") as a_file:
            json.dump(input_data, a_file, ensure_ascii=False)
        process = subprocess.run(
            [engine, "-m", module_file, "-i", input_file, "-o", output_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        output = {}
        if os.path.exists(output_file):
            with open(output_file, encoding="utf-8") as a_file:
                output = json.load(a_file)
        if process.returncode == 0:
            result = RunResult(output.get("writes", []), output.get("log", []))
            result.changes = output.get("changes")
            return result
        if process.returncode == 1:
            return RunResult(
                [],
                output.get("log", []),
                output.get("failure")
                or process.stderr.decode("utf-8", "replace").strip()
                or "The module failed",
            )
        return RunResult(
            [],
            [],
            "The engine could not read the input: {}".format(
                process.stderr.decode("utf-8", "replace").strip() or process.returncode
            ),
        )
    except subprocess.TimeoutExpired:
        return RunResult([], [], "The engine did not answer in 30 seconds")
    except (OSError, ValueError) as e:
        return RunResult([], [], "The engine failed: {}".format(e))
    finally:
        for name in (module_file, input_file, output_file):
            try:
                os.remove(name)
            except OSError:
                pass
        try:
            os.rmdir(workdir)
        except OSError:
            pass


def _run_in_process(script, input_data, limits):
    """The interim engine: the archived quickjs binding, ES2020."""
    try:
        import quickjs
    except ImportError:
        return RunResult(
            [],
            [],
            "No JavaScript engine is available: RSTools' runactions is not "
            "installed and the quickjs package is missing",
        )
    context = quickjs.Context()
    context.set_memory_limit(int(limits["memory_bytes"]))
    context.set_time_limit(float(limits["seconds"]))
    context.set_max_stack_size(int(limits["stack_bytes"]))
    try:
        context.eval(PRELUDE)
        context.eval(
            "var __fs_built = __fs_build({});".format(
                json.dumps(input_data, ensure_ascii=False)
            )
        )
        # A module is strict (actions-api.md 3). The directive goes on the
        # module's first line, so that no line number a failure names moves.
        context.eval('"use strict";' + script)
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
                "old": js_string(old),
                "new": js_string(new),
            }
        )
    changes.sort(key=lambda c: (c["table"], c["column"]))
    return changes


def _number_of(value):
    """A value as a number the way the Kotlin host reads one: a boolean is
    1 or 0, a number is itself, a text is a number when it reads as one."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if "_" in text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _same(old, new, numeric=None):
    """Whether a write leaves a value as it was (actions-api.md 9).

    Both null, or equal as numbers when the target holds numbers and both
    read as one, or else equal as JavaScript text. A text target compares as
    text: "1" over "01" is a change, since the column would hold other
    characters (rstools.md 15.4 a). ``numeric`` says what the target holds;
    when it is not given -- the engine's report, which has no dictionary --
    the old value says it, being typed by the target's type in the input.
    """
    if old is None or new is None:
        return old is None and new is None
    if numeric is None:
        numeric = isinstance(old, (int, float)) and not isinstance(old, bool)
    if numeric:
        a, b = _number_of(old), _number_of(new)
        if a is not None and b is not None:
            return a == b
    return js_string(old) == js_string(new)


def js_string(value):
    """A value as JavaScript's String() spells it (actions-api.md 9).

    Python's str() differs for three things a module writes: a boolean
    (True, not true), a whole float (3.0, not 3) and exponents (1e-07 and
    1e+16, not 1e-7 and 10000000000000000). repr() gives the shortest digits
    that read back as the float, as JavaScript does; only the layout differs.
    Taken from rstools.md 13.3, where it agrees with quickjs-ng's own
    String() on 4,513 numbers.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, float):
        return str(value)
    if value != value:
        return "NaN"
    if value in (float("inf"), float("-inf")):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "0"
    text = repr(abs(value))
    mantissa, _, exponent = text.partition("e")
    whole, _, fraction = mantissa.partition(".")
    all_digits = whole + fraction
    leading = len(all_digits) - len(all_digits.lstrip("0"))
    point = len(whole) + int(exponent or 0) - leading
    digits = all_digits.lstrip("0").rstrip("0") or "0"
    k, n = len(digits), point
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * -n + digits
    else:
        e = n - 1
        body = (
            (digits if k == 1 else digits[0] + "." + digits[1:])
            + "e"
            + ("+" if e >= 0 else "-")
            + str(abs(e))
        )
    return "-" + body if value < 0 else body


def writes_from_changes(changes, case):
    """The writes a change report amounts to, for a host that reports
    changes but not the writes behind them: the table says whether a name
    is a property, the rowuuid says whether the row is the case or its
    parent."""
    writes = []
    parent = (case or {}).get("parent") or {}
    for change in changes or []:
        scope = (
            "parent"
            if change.get("rowuuid") == parent.get("rowuuid") and parent
            else "case"
        )
        table = change.get("table") or ""
        column = change.get("column")
        if column == "_active":
            writes.append(
                {"scope": scope, "kind": "active", "value": int(change.get("new") or 0)}
            )
            continue
        writes.append(
            {"scope": scope, "kind": "set", "name": column, "value": change.get("new")}
        )
    return writes
