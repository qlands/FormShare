"""Indexes on who sent each submission, for plugins that read a repository by
device or by assistant.

FormShare Collect writes its installation's _device_uuid into the <meta> of
every submission, and RSTools keeps it in maintable._device_uuid, always in
maintable itself even when a form splits. FormShare stamps every submission
with the assistant who sent it, in maintable._submitted_by. RSTools indexes
neither. A plugin that reads someone's submissions on each request, as a
journey does for each form list (docs/device-journeys.md 7.3), asks for these
indexes when a form joins it. Core adds them to no repository by itself.

The indexes are FormShare's, as fs_surveyid is (processes/odk_audit.py). A
merge alters the table and keeps them.
"""

import logging
import re

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

log = logging.getLogger("formshare")

DEVICE_INDEX = "fs_device"
ASSISTANT_INDEX = "fs_assistant"

# Whose submissions each index reads, by arrival
_COLUMNS = {
    DEVICE_INDEX: "_device_uuid",
    ASSISTANT_INDEX: "_submitted_by",
}

_IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")


def _quoted(name):
    if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
        raise ValueError("{} is not a name".format(name))
    return "`{}`".format(name)


def index_ddl(schema, index):
    """The index: a device's or an assistant's submissions, by arrival."""
    return "CREATE INDEX {} ON {}.{} ({}, {})".format(
        _quoted(index),
        _quoted(schema),
        _quoted("maintable"),
        _quoted(_COLUMNS[index]),
        _quoted("_submitted_date"),
    )


def has_index(connection, schema, index):
    """Whether maintable already has the index, by its name."""
    return (
        connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = :schema AND table_name = 'maintable' "
                "AND index_name = :index"
            ),
            {"schema": schema, "index": index},
        ).scalar()
        > 0
    )


def has_column(connection, schema, column):
    """Whether maintable has the column at all: a repository built before
    RSTools kept _device_uuid (2026-10-15) does not, until its next merge."""
    return (
        connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = 'maintable' "
                "AND column_name = :column"
            ),
            {"schema": schema, "column": column},
        ).scalar()
        > 0
    )


def _ensure_index(settings, schema, index):
    """Adds the index to a repository unless it is there. DDL commits on its
    connection, so this runs on one of its own and never in the caller's
    session. Returns (done, why): it never raises, and a repository without
    the column says so."""
    column = _COLUMNS[index]
    engine = create_engine(settings["sqlalchemy.url"], poolclass=NullPool)
    try:
        with engine.connect() as connection:
            if not has_column(connection, schema, column):
                return False, "the repository has no {} column".format(column)
            if not has_index(connection, schema, index):
                connection.execute(text(index_ddl(schema, index)))
        return True, ""
    except Exception as e:
        log.error(
            "Repository {} has no {} index. Error: {}".format(schema, index, str(e))
        )
        return False, str(e)
    finally:
        engine.dispose()


def ensure_device_index(settings, schema):
    """maintable(_device_uuid, _submitted_date): a device's submissions."""
    return _ensure_index(settings, schema, DEVICE_INDEX)


def ensure_assistant_index(settings, schema):
    """maintable(_submitted_by, _submitted_date): an assistant's
    submissions, from any device."""
    return _ensure_index(settings, schema, ASSISTANT_INDEX)
