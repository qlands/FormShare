"""An index on the device each submission came from, for plugins that read a
repository by device.

FormShare Collect writes its installation's _device_uuid into the <meta> of
every submission, and RSTools keeps it in maintable._device_uuid, always in
maintable itself even when a form splits. RSTools indexes nothing on it. A
plugin that reads a device's submissions on each request, as a journey does
for each form list (docs/device-journeys.md 7.3), asks for this index when a
form joins it. Core adds it to no repository by itself.

The index is FormShare's, as fs_surveyid is (processes/odk_audit.py). A merge
alters the table and keeps it.
"""

import logging
import re

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

log = logging.getLogger("formshare")

DEVICE_INDEX = "fs_device"
_IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")


def _quoted(name):
    if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
        raise ValueError("{} is not a name".format(name))
    return "`{}`".format(name)


def device_index_ddl(schema):
    """The index: a device's submissions, by arrival."""
    return "CREATE INDEX {} ON {}.{} ({}, {})".format(
        _quoted(DEVICE_INDEX),
        _quoted(schema),
        _quoted("maintable"),
        _quoted("_device_uuid"),
        _quoted("_submitted_date"),
    )


def has_device_index(connection, schema):
    """Whether maintable already has the index, by its name."""
    return (
        connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = :schema AND table_name = 'maintable' "
                "AND index_name = :index"
            ),
            {"schema": schema, "index": DEVICE_INDEX},
        ).scalar()
        > 0
    )


def has_device_column(connection, schema):
    """Whether the repository has _device_uuid at all: one built before
    RSTools added the column does not, until its next merge."""
    return (
        connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = 'maintable' "
                "AND column_name = '_device_uuid'"
            ),
            {"schema": schema},
        ).scalar()
        > 0
    )


def ensure_device_index(settings, schema):
    """Adds the index to a repository unless it is there. DDL commits on its
    connection, so this runs on one of its own and never in the caller's
    session. Returns (done, why): it never raises, and a repository without
    _device_uuid says so."""
    engine = create_engine(settings["sqlalchemy.url"], poolclass=NullPool)
    try:
        with engine.connect() as connection:
            if not has_device_column(connection, schema):
                return False, "the repository has no _device_uuid column"
            if not has_device_index(connection, schema):
                connection.execute(text(device_index_ddl(schema)))
        return True, ""
    except Exception as e:
        log.error(
            "Repository {} has no {} index. Error: {}".format(
                schema, DEVICE_INDEX, str(e)
            )
        )
        return False, str(e)
    finally:
        engine.dispose()
