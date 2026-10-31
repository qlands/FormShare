"""A submission's ODK audit, kept as a table of its form's repository
(docs/odk-audit.md; the owner, 2026-10-30: "the audit must be a table in
every form's repository").

A form with a row of type audit makes ODK Collect write audit.csv while the
form is filled in, and send it with the submission as one of its media: every
question shown, when it started and when it ended and, with the row's
options, the old and new answer (track-changes), where the device was
(location-priority), who held it (identify-user) and why an answer was
changed (track-changes-reasons). FormShare Collect writes the same file.
Enketo writes none.

FormShare keeps the file with the submission's other media, sealed where the
form encrypts (seal_audit), and its rows in odk_audit, one per event, keyed
by the submission (maintable.surveyid) and the event's line in the file.

The table is FormShare's own and outside create.xml, as a case's properties
table is: ODK fixes its columns, so nothing in it depends on the form, and
mergeversions, the audit triggers, the dictionary, Clean data and the
exporters never see it. Its foreign key to maintable.surveyid needs a unique
index there, which jxformtomysql does not make; make_audit_table adds it.

What Collect writes was read from its own code (AuditEventSaveTask,
AuditEventCSVLine and CSVUtils, May 2026):
- the header is event,node,start,end, then latitude,longitude,accuracy
  (location), old-value,new-value (track-changes), user (identify-user) and
  change-reason (track-changes-reasons), each group only when its option is
  set;
- start and end are milliseconds since 1970, end empty for an event of one
  moment;
- the node is the XPath with positions on repeats only:
  /data/group/repeat[3]/question;
- the values are quoted when they hold a comma, a quote or a line break,
  with quotes doubled;
- when the form's audit options change, Collect writes a new header over
  the rows it wrote before, so an older row can be shorter than the header.
  ODK warns that such an audit can be corrupt: rows are read by the header,
  a missing field is empty, and a number that does not read as one is NULL.
"""

import csv
import io
import logging
import math
import os
import re

from lxml import etree
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from formshare.processes.db.encryption import seal
from formshare.processes.logging.loggerclass import SecretLogger

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

AUDIT_FILE = "audit.csv"
AUDIT_TABLE = "odk_audit"

# A value of old-value or new-value can be a long answer, and the csv
# module refuses a field past 128 KB by default. The limit is the process's,
# so it is only ever raised; the columns hold 16 MB.
csv.field_size_limit(max(csv.field_size_limit(), 16 * 1024 * 1024))

# Each column of the file as Collect names it, and the column of odk_audit
# that keeps it: ODK's names, with _ for -.
COLUMNS = [
    ("event", "event"),
    ("node", "node"),
    ("start", "start"),
    ("end", "end"),
    ("latitude", "latitude"),
    ("longitude", "longitude"),
    ("accuracy", "accuracy"),
    ("old-value", "old_value"),
    ("new-value", "new_value"),
    ("user", "user"),
    ("change-reason", "change_reason"),
]
INTEGERS = ("start", "end")
DECIMALS = ("latitude", "longitude", "accuracy")
# The answers: what a form's encryption seals.
VALUES = ("old-value", "new-value")
EVENT_SIZE = 255

_POSITION = re.compile(r"\[\d+\]$")
_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class AuditFormatError(ValueError):
    """An audit.csv that cannot be read as one."""


def _name(identifier):
    """A schema, table, column, charset or collation name, refusing anything
    that is not one: every name here is FormShare's or MySQL's own, so a
    refusal is a bug."""
    if not _NAME.match(str(identifier or "")):
        raise ValueError("Not an identifier: {!r}".format(identifier))
    return identifier


def _quoted(identifier):
    return "`{}`".format(_name(identifier))


def audit_file_of(odk_dir, form_directory, submission_id):
    """Where a submission's audit.csv is kept: with its other media."""
    return os.path.join(
        odk_dir, "forms", form_directory, "submissions", submission_id, AUDIT_FILE
    )


# ---------------------------------------------------------------------------
# Reading the file
# ---------------------------------------------------------------------------


def read_audit(raw):
    """(header, records) of an audit.csv: the header as written and each
    event's fields, in order. A line with no field is left out. Raises
    AuditFormatError when it is not an audit: no CSV, or no event column."""
    if isinstance(raw, bytes):
        # Collect writes UTF-8; one stray byte does not lose the audit
        content = raw.decode("utf-8", errors="replace")
    else:
        content = raw
    if content.startswith("\ufeff"):
        content = content[1:]
    try:
        records = list(csv.reader(io.StringIO(content, newline="")))
    except csv.Error as e:
        raise AuditFormatError(str(e))
    records = [record for record in records if any(f.strip() for f in record)]
    if not records:
        return [], []
    header = records[0]
    if "event" not in [name.strip() for name in header]:
        raise AuditFormatError("it has no event column")
    return header, records[1:]


def _fields(header, record):
    """An event's fields by column name. A row shorter than the header,
    written before Collect rewrote it, has the rest empty."""
    return {
        name.strip(): (record[index] if index < len(record) else "")
        for index, name in enumerate(header)
    }


def _integer(value):
    value = value.strip()
    if re.fullmatch(r"-?\d{1,18}", value):
        return int(value)
    return None


def _decimal(value):
    try:
        number = float(value.strip())
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def audit_rows(raw):
    """The rows of odk_audit an audit.csv makes, as dictionaries by column,
    without the submission: event_order is the event's line after the
    header, from 1, counting only lines with something on them (Collect
    writes no blank one). An empty field is NULL, as is a number that does
    not read as one; the text of an answer is kept as it was written. A line
    with no event is left out, and keeps its number."""
    header, records = read_audit(raw)
    rows = []
    for order, record in enumerate(records, start=1):
        fields = _fields(header, record)
        event = fields.get("event", "").strip()
        if not event:
            continue
        row = {"event_order": order}
        for name, column in COLUMNS:
            value = fields.get(name, "")
            if name in INTEGERS:
                row[column] = _integer(value)
            elif name in DECIMALS:
                row[column] = _decimal(value)
            elif name == "node":
                row[column] = value.strip() or None
            else:
                row[column] = value if value != "" else None
        row["event"] = event[:EVENT_SIZE]
        rows.append(row)
    return rows


def node_xmlcode(node):
    """The key of the answer an event's node names, as xmltojson keys it and
    seal_xml reads it (processes/db/encryption.py): the names below the root,
    leaving out any ancestor named as the root is, joined by '/'. Collect
    writes /data/group/repeat[3]/question; the repeat's position goes, since
    one key names an answer in every instance."""
    names = [
        _POSITION.sub("", name.strip())
        for name in (node or "").strip().split("/")
        if name.strip()
    ]
    if len(names) < 2:
        return ""
    root = names[0]
    below = names[1:]
    return "/".join([name for name in below[:-1] if name != root] + [below[-1]])


# ---------------------------------------------------------------------------
# Sealing what the form encrypts
# ---------------------------------------------------------------------------


def seal_audit(raw, marked, public_key_text):
    """An audit.csv with the old and new values of every question the form
    marks sealed with the project's key: (the bytes to keep, how many values
    were sealed).

    With track-changes, Collect writes every answer into the file in clear,
    encrypted ones included. The file is sealed in memory before it is
    written anywhere, as a submission's XML is (seal_xml): the kept file is
    the sealed one. An envelope, and an empty value, stay as they are. When
    nothing is sealed the bytes come back as they arrived; otherwise the
    file is written again as CSV, quoted where Collect quotes. Raises
    AuditFormatError when it cannot be read, since its values could then not
    be sealed."""
    if not marked:
        return raw, 0
    header, records = read_audit(raw)
    names = [name.strip() for name in header]
    if "node" not in names:
        return raw, 0
    node_at = names.index("node")
    positions = [names.index(name) for name in VALUES if name in names]
    marked = set(marked)
    sealed = 0
    for record in records:
        if node_at >= len(record) or node_xmlcode(record[node_at]) not in marked:
            continue
        for position in positions:
            if position >= len(record):
                continue
            value = seal(record[position], public_key_text)
            if value != record[position]:
                record[position] = value
                sealed += 1
    if not sealed:
        return raw, 0
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(records)
    return output.getvalue().encode("utf-8"), sealed


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------


def audit_table_ddl(schema, charset, collation):
    """CREATE TABLE odk_audit. submission_id takes maintable.surveyid's
    charset and collation, as a case's properties table does rowuuid's:
    InnoDB refuses a key between strings that differ in either. Everything
    else is utf8mb4, so an answer with an emoji goes in (rstools.md 37), and
    the answers are MEDIUMTEXT, as in audit_log."""
    return (
        "CREATE TABLE {table} ("
        "`submission_id` VARCHAR(80) CHARACTER SET {charset} "
        "COLLATE {collation} NOT NULL, "
        "`event_order` INT UNSIGNED NOT NULL, "
        "`event` VARCHAR({event_size}) NOT NULL, "
        "`node` TEXT NULL, "
        "`start` BIGINT NULL, "
        "`end` BIGINT NULL, "
        "`latitude` DOUBLE NULL, "
        "`longitude` DOUBLE NULL, "
        "`accuracy` DOUBLE NULL, "
        "`old_value` MEDIUMTEXT NULL, "
        "`new_value` MEDIUMTEXT NULL, "
        "`user` TEXT NULL, "
        "`change_reason` TEXT NULL, "
        "PRIMARY KEY (`submission_id`, `event_order`), "
        "CONSTRAINT `fk_odk_audit_submission` FOREIGN KEY (`submission_id`) "
        "REFERENCES {maintable} (`surveyid`) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci "
        "COMMENT='The ODK audit (audit.csv) of each submission, kept by FormShare'"
    ).format(
        table="{}.{}".format(_quoted(schema), _quoted(AUDIT_TABLE)),
        charset=_name(charset),
        collation=_name(collation),
        event_size=EVENT_SIZE,
        maintable="{}.{}".format(_quoted(schema), _quoted("maintable")),
    )


def surveyid_index_ddl(schema):
    """The unique index on maintable.surveyid the audit's key needs: a
    foreign key needs an index on the column it names, and MySQL 8.4 refuses
    one to a column that is not unique (restrict_fk_on_non_standard_key).
    surveyid is the submission's ID, one per POST, so nothing repeats."""
    return "ALTER TABLE {}.{} ADD UNIQUE INDEX `fs_surveyid` (`surveyid`)".format(
        _quoted(schema), _quoted("maintable")
    )


def _tables(connection, schema):
    return {
        name.lower()
        for (name,) in connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema"
            ),
            {"schema": schema},
        )
    }


def _is_audit_table(connection, schema):
    """Whether the schema's odk_audit is this one, not a table of the form
    that happens to be called so."""
    columns = {
        name.lower()
        for (name,) in connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = :table"
            ),
            {"schema": schema, "table": AUDIT_TABLE},
        )
    }
    return {"submission_id", "event_order", "event", "node"} <= columns


def _has_unique_surveyid(connection, schema):
    """Whether maintable has a unique index on surveyid alone, whatever its
    name: RSTools may make one some day."""
    indexes = {}
    for name, column, sub_part in connection.execute(
        text(
            "SELECT index_name, column_name, sub_part "
            "FROM information_schema.statistics WHERE table_schema = :schema "
            "AND table_name = 'maintable' AND non_unique = 0"
        ),
        {"schema": schema},
    ):
        indexes.setdefault(name, []).append((column.lower(), sub_part))
    return [("surveyid", None)] in indexes.values()


def has_audit_table(connection, schema):
    """Whether a repository has its odk_audit table."""
    return AUDIT_TABLE in _tables(connection, schema) and _is_audit_table(
        connection, schema
    )


def make_audit_table(engine, schema):
    """Makes odk_audit in a repository without it, and the unique index on
    maintable.surveyid its key needs. Returns (True, "") when the table is
    there, made now or before, or (False, why) when it cannot be: no
    maintable, a table of the form called odk_audit, or two submissions
    with one ID.

    A repository gets it when it is built, and one built before it at its
    next merge, which is how a form gains an audit row. DDL commits on its
    own and waits for every transaction on maintable, so this runs on a
    connection of its own, in the worker, never in a request."""
    with engine.connect() as connection:
        tables = _tables(connection, schema)
        if "maintable" not in tables:
            return False, "the repository has no maintable"
        if AUDIT_TABLE in tables:
            if _is_audit_table(connection, schema):
                return True, ""
            return False, "a table of the form is called {}".format(AUDIT_TABLE)
        column = connection.execute(
            text(
                "SELECT character_set_name, collation_name "
                "FROM information_schema.columns WHERE table_schema = :schema "
                "AND table_name = 'maintable' AND column_name = 'surveyid'"
            ),
            {"schema": schema},
        ).fetchone()
        if column is None:
            return False, "maintable has no surveyid"
        if not _has_unique_surveyid(connection, schema):
            repeated = connection.execute(
                text(
                    "SELECT surveyid FROM {}.{} WHERE surveyid IS NOT NULL "
                    "GROUP BY surveyid HAVING COUNT(*) > 1 LIMIT 1".format(
                        _quoted(schema), _quoted("maintable")
                    )
                )
            ).fetchone()
            if repeated is not None:
                return False, "two submissions have the ID {}".format(repeated[0])
            connection.execute(text(surveyid_index_ddl(schema)))
        connection.execute(text(audit_table_ddl(schema, column[0], column[1])))
    return True, ""


def make_audit_table_for(settings, schema):
    """make_audit_table for a repository's build and merge, which have the
    settings and no engine. It says why the table could not be made, and
    never raises: a repository without it takes submissions as before, and
    keeps their audit.csv with their media."""
    engine = create_engine(settings["sqlalchemy.url"], poolclass=NullPool)
    try:
        made, why = make_audit_table(engine, schema)
        if not made:
            log.error(
                "Repository {} has no {} table: {}".format(schema, AUDIT_TABLE, why)
            )
        return made
    except Exception as e:
        log.error(
            "Repository {} has no {} table. Error: {}".format(
                schema, AUDIT_TABLE, str(e)
            )
        )
        return False
    finally:
        engine.dispose()


def audit_table_taken(create_xml_file):
    """Whether a form would make a table called odk_audit, a repeat of that
    name: its table and the audit's would be one. The upload check refuses
    such a form (check_jxform_file)."""
    try:
        root = etree.parse(create_xml_file).getroot()
    except (OSError, etree.XMLSyntaxError):
        return False
    return any(
        (table.get("name") or "").lower() == AUDIT_TABLE
        for table in root.iterfind(".//tables//table")
    )


# ---------------------------------------------------------------------------
# Loading a submission's audit
# ---------------------------------------------------------------------------

_INSERT_COLUMNS = ["submission_id", "event_order"] + [c for _, c in COLUMNS]


def _insert_sql(schema):
    return "INSERT INTO {}.{} ({}) VALUES ({})".format(
        _quoted(schema),
        _quoted(AUDIT_TABLE),
        ", ".join(_quoted(column) for column in _INSERT_COLUMNS),
        ", ".join(":" + column for column in _INSERT_COLUMNS),
    )


def load_audit(engine, schema, submission_id, audit_file, marked=None, key=None):
    """Writes a submission's audit into odk_audit: the rows its stored
    audit.csv makes, in place of any it had, in one transaction. A resend,
    a later part or a second load therefore change nothing. Returns how many
    rows were written, or None when nothing was:
    - the submission has no audit.csv, or its form no repository;
    - the repository has no odk_audit (built before it, until its next
      merge);
    - the submission is not in the repository: one that went to the logs
      gets its rows when it comes back (push_revision);
    - the file cannot be read, or the database refused it.

    marked are the xmlcodes the form encrypts and key the project's public
    key. A marked value still in clear (a file kept before FormShare sealed
    audits) is sealed before it is written, so the table never holds one;
    without the key such a file is not loaded at all.

    It never fails the submission: the audit is the submission's companion,
    and its file is kept whatever happens here."""
    if not schema or not os.path.isfile(audit_file):
        return None
    try:
        with open(audit_file, "rb") as a_file:
            raw = a_file.read()
        if marked:
            if key is None:
                log.error(
                    "The audit of submission {} in {} was not loaded: the form "
                    "encrypts answers and the project has no key".format(
                        submission_id, schema
                    )
                )
                return None
            raw, _sealed = seal_audit(raw, marked, key)
        rows = audit_rows(raw)
    except (OSError, AuditFormatError) as e:
        log.error(
            "The audit of submission {} in {} cannot be read: {}".format(
                submission_id, schema, str(e)
            )
        )
        return None
    connection = engine.connect()
    try:
        if not has_audit_table(connection, schema):
            log.info(
                "The audit of submission {} was not loaded: {} has no {} "
                "table".format(submission_id, schema, AUDIT_TABLE)
            )
            return None
        with connection.begin():
            stored = connection.execute(
                text(
                    "SELECT 1 FROM {}.{} WHERE surveyid = :submission LIMIT 1".format(
                        _quoted(schema), _quoted("maintable")
                    )
                ),
                {"submission": submission_id},
            ).first()
            if stored is None:
                return None
            connection.execute(
                text(
                    "DELETE FROM {}.{} WHERE submission_id = :submission".format(
                        _quoted(schema), _quoted(AUDIT_TABLE)
                    )
                ),
                {"submission": submission_id},
            )
            if rows:
                connection.execute(
                    text(_insert_sql(schema)),
                    [dict(row, submission_id=submission_id) for row in rows],
                )
        return len(rows)
    except Exception as e:
        log.error(
            "The audit of submission {} was not loaded into {}: {}".format(
                submission_id, schema, str(e)
            )
        )
        return None
    finally:
        connection.close()
