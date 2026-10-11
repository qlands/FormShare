"""Writing a repository table's audit triggers again with RSTools'
createaudittriggers.

At a repository's build the tool writes, on every table, an ``audit_<uuid>_*``
set of triggers that logs each change into audit_log, and a ``TLU_<uuid>``
one that stamps _lastupdate. Until rstools.md 29 (2026-10-11) they named every
column, the ones MySQL generates included: the UPDATE trigger copied a
geometry's bytes into audit_log's TEXT columns, and MySQL refused the whole
UPDATE (1366). Every edit of a geotrace or geoshape answer, every write of a
geo property and every moved GeoJSON feature failed in a repository built
with it, and a repository keeps the triggers it was built with.

regenerate_table_audit writes one table's set again with the installed tool:

- it refuses, changing nothing, when that tool still names a generated column
  of the table -- it predates rstools.md 29 and would write the same;
- it drops only the table's ``audit_*`` and ``TLU_*`` triggers. ``TDQS_<uuid>``,
  which copies maintable's _dqscore down to its child tables, names no other
  column, and the tool writes it only when it runs over the whole schema --
  with ``-t maintable`` its list of child tables comes out empty -- so it is
  kept as it is. Every other trigger on the table is FormShare's or the
  schema's own and is not touched;
- if the new set does not load, the previous one is put back;
- a table another session holds -- an open transaction that touched it --
  makes the drop and the load wait for its lock. They give up after
  LOCK_WAIT seconds rather than MySQL's default of a year, and the table
  keeps its triggers.

regenerate_properties_audit (processes/db/case_management.py) does the same
for a properties table each time a property is added, without the refusal.
"""

import os
import re
import shutil
import tempfile
from subprocess import PIPE, Popen

from sqlalchemy import text

__all__ = [
    "generated_columns",
    "audit_triggers",
    "names_generated",
    "without_definer",
    "regenerate_table_audit",
]

_PATTERNS = ("audit\\_%", "TLU\\_%")
LOCK_WAIT = 60
_DEFINER = re.compile(
    r"\s+DEFINER\s*=\s*(`[^`]*`|'[^']*'|[^\s@]+)@(`[^`]*`|'[^']*'|\S+)",
    re.IGNORECASE,
)


def _quoted(name):
    return "`" + str(name).replace("`", "``") + "`"


def generated_columns(connection, schema):
    """{table: [column]}: the columns MySQL generates in a schema -- every
    ``<name>_geom`` beside a geotrace or geoshape, a GeoJSON lookup's
    ``geometry``, a geo property's twin. Told by GENERATION_EXPRESSION, not by
    EXTRA, which MySQL also marks for an ordinary column whose default is an
    expression, as a geo property's is (rstools.md 29.1)."""
    found = {}
    for table, column in connection.execute(
        text(
            "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = :schema AND GENERATION_EXPRESSION <> '' "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION"
        ),
        {"schema": schema},
    ).fetchall():
        found.setdefault(table, []).append(column)
    return found


def audit_triggers(connection, schema, table):
    """[(name, statement)]: a table's ``audit_*`` and ``TLU_*`` triggers, each
    with the statement that creates it."""
    names = [
        row[0]
        for row in connection.execute(
            text(
                "SELECT TRIGGER_NAME FROM information_schema.TRIGGERS "
                "WHERE TRIGGER_SCHEMA = :schema AND EVENT_OBJECT_TABLE = :table "
                "AND (TRIGGER_NAME LIKE :audit OR TRIGGER_NAME LIKE :stamp) "
                "ORDER BY TRIGGER_NAME"
            ),
            {
                "schema": schema,
                "table": table,
                "audit": _PATTERNS[0],
                "stamp": _PATTERNS[1],
            },
        ).fetchall()
    ]
    found = []
    for name in names:
        row = connection.execute(
            text("SHOW CREATE TRIGGER {}.{}".format(_quoted(schema), _quoted(name)))
        ).fetchone()
        found.append((name, row[2]))
    return found


def names_generated(sql, columns):
    """The generated columns that a set of triggers' SQL names, as an
    identifier or as the column audit_log is told about. A createaudittriggers
    from before rstools.md 29 names them all; one since, none."""
    named = []
    for column in sorted(set(columns)):
        pattern = r"(?<![A-Za-z0-9_])`?" + re.escape(column) + r"`?(?![A-Za-z0-9_])"
        if re.search(pattern, sql):
            named.append(column)
    return named


def without_definer(statement):
    """A CREATE TRIGGER statement without its DEFINER clause, so that it is
    created as the user who runs it -- a managed MySQL without SUPER refuses a
    DEFINER other than oneself."""
    return _DEFINER.sub("", statement, count=1)


def _drop(connection, schema, name):
    connection.execute(
        text("DROP TRIGGER IF EXISTS {}.{}".format(_quoted(schema), _quoted(name)))
    )


def _load(settings, schema, sql_file):
    with open(sql_file) as a_file:
        process = Popen(
            [
                "mysql",
                "--defaults-file=" + settings["mysql.cnf"],
                "--init-command=SET SESSION lock_wait_timeout = {}".format(LOCK_WAIT),
                schema,
            ],
            stdin=a_file,
            stdout=PIPE,
            stderr=PIPE,
        )
        _, error = process.communicate()
    return process.returncode == 0, error.decode("utf-8", "replace").strip()


def regenerate_table_audit(settings, connection, schema, table, columns):
    """Writes a table's audit triggers again with the installed
    createaudittriggers. columns are the table's generated columns.

    Returns (status, message):

    - "regenerated";
    - "none": the table had no audit triggers, and is left without;
    - "old tool": the installed tool still names one of columns, and nothing
      was changed;
    - "failed": the tool or the load failed, and the previous triggers are as
      they were.
    """
    previous = audit_triggers(connection, schema, table)
    if not previous:
        return "none", ""
    out_dir = tempfile.mkdtemp(prefix="fs_audit_")
    try:
        tool = os.path.join(
            settings["odktools.path"],
            *["utilities", "createAuditTriggers", "createaudittriggers"]
        )
        args = [
            tool,
            "-H " + settings["mysql.host"],
            "-P " + str(settings["mysql.port"]),
            "-u " + settings["mysql.user"],
            "-p " + settings["mysql.password"],
            "-s " + schema,
            "-o " + out_dir,
            "-t " + table,
        ]
        process = Popen(args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        sql_file = os.path.join(out_dir, "mysql_create_audit.sql")
        if process.returncode != 0 or not os.path.exists(sql_file):
            return "failed", "createaudittriggers failed on {}.{}: {}".format(
                schema, table, (stderr or stdout).decode("utf-8", "replace").strip()
            )
        with open(sql_file) as a_file:
            named = names_generated(a_file.read(), columns)
        if named:
            return (
                "old tool",
                "The installed createaudittriggers still audits the generated "
                "column(s) {} of {}.{}: it predates RSTools' rstools.md 29 and "
                "would write the same triggers. Update RSTools and run this "
                "again.".format(", ".join(named), schema, table),
            )
        connection.execute(text("SET SESSION lock_wait_timeout = {}".format(LOCK_WAIT)))
        try:
            for name, _ in previous:
                _drop(connection, schema, name)
            loaded, error = _load(settings, schema, sql_file)
        except Exception as e:
            loaded, error = False, str(e)
        if loaded:
            return "regenerated", ""
        # Whatever loaded of the new set goes, and whatever of the previous
        # set is missing comes back.
        restore_error = ""
        try:
            kept = {name for name, _ in previous}
            now = {name for name, _ in audit_triggers(connection, schema, table)}
            for name in now - kept:
                _drop(connection, schema, name)
            missing = [(n, sql) for n, sql in previous if n not in now]
            if missing:
                restore_file = os.path.join(out_dir, "restore.sql")
                with open(restore_file, "w") as a_file:
                    for _, statement in missing:
                        a_file.write(
                            "DELIMITER $$\n{}$$\nDELIMITER ;\n".format(
                                without_definer(statement)
                            )
                        )
                restored, restore_error = _load(settings, schema, restore_file)
                if not restored:
                    raise RuntimeError(restore_error)
        except Exception as e:
            restore_error = str(e) or restore_error
            return "failed", (
                "The new triggers of {}.{} did not load ({}), and putting the "
                "previous ones back failed too ({}): the table may be left "
                "unaudited until regenerate_audit_triggers runs again for "
                "it.".format(schema, table, error, restore_error)
            )
        return "failed", (
            "The new triggers of {}.{} did not load ({}); it keeps the "
            "previous ones.".format(schema, table, error)
        )
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
