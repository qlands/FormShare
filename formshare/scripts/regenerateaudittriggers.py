"""Writes again the audit triggers of the repository tables that hold a column
MySQL generates, once, after RSTools' createaudittriggers stopped naming such
columns (docs/formshare_case_management/rstools.md 29, 2026-10-11).

    regenerate_audit_triggers [--project <project id>] [--form <form id>] <ini file>

In a repository built before it, the UPDATE audit trigger copied a generated
geometry's bytes into audit_log's TEXT columns, and MySQL refused the whole
UPDATE (1366): every edit of a geotrace or geoshape answer, every write of a
geo property, every moved GeoJSON feature failed. A repository keeps the
triggers it was built with, so each table with a generated column gets its
audit and _lastupdate triggers written again by the installed tool
(processes/audit_triggers.py); every other table and trigger is left alone.
It stops before changing anything if the installed tool still names generated
columns. Running it again changes nothing that matters: the triggers are
written once more, alike.
"""

import argparse
import logging
import os

from formshare.app import load_settings_from_ini
from formshare.models import Odkform, get_engine, get_session_factory
from formshare.processes.audit_triggers import (
    generated_columns,
    regenerate_table_audit,
)


def main(raw_args=None):
    parser = argparse.ArgumentParser(
        description="Write again the audit triggers of the repository tables "
        "that hold a generated column"
    )
    parser.add_argument("--project", help="Only the repositories of this project id")
    parser.add_argument("--form", help="Only the repository of this form id")
    parser.add_argument("ini_path", help="Path to ini file")
    args = parser.parse_args(raw_args)
    if not os.path.exists(args.ini_path):
        logging.error("Ini file does not exists")
        return 1

    settings = load_settings_from_ini(os.path.abspath(args.ini_path))
    engine = get_engine(settings)
    session = get_session_factory(engine)()
    try:
        forms = session.query(Odkform.form_schema).filter(
            Odkform.form_schema.isnot(None)
        )
        if args.project:
            forms = forms.filter(Odkform.project_id == args.project)
        if args.form:
            forms = forms.filter(Odkform.form_id == args.form)
        # The versions of a form share one repository.
        schemas = sorted({row[0] for row in forms.all() if row[0]})
    finally:
        session.close()

    counts = {"repositories": 0, "regenerated": 0, "none": 0}
    failed = []
    try:
        with engine.connect() as connection:
            for schema in schemas:
                tables = generated_columns(connection, schema)
                if not tables:
                    continue
                counts["repositories"] += 1
                for table, columns in tables.items():
                    status, message = regenerate_table_audit(
                        settings, connection, schema, table, columns
                    )
                    if status == "old tool":
                        print(message)
                        return 1
                    if status == "failed":
                        failed.append(message)
                        print(message)
                    else:
                        counts[status] += 1
    finally:
        engine.dispose()
    print(
        "Wrote again the audit triggers of {regenerated} table(s) in "
        "{repositories} repository(ies) with a generated column; {none} "
        "table(s) had none to write.".format(**counts)
    )
    if failed:
        print("{} table(s) failed, and keep their triggers.".format(len(failed)))
        return 1
    return 0
