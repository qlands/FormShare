"""Resumes the deletion of a form that stopped (2026-10-28).

    resume_form_deletion <ini file>
    resume_form_deletion <ini file> <project id> <form id>

A form is deleted by a Celery task users cannot cancel
(processes/db/form_deletion.py). When the task stops -- mysqldump failed,
the disk filled, a repository a deleted form's leftover refers to could not
be dropped -- the form stays inactive, blocked and being deleted, the reason
is recorded, and the technical team is emailed. Only they resume it (owner,
2026-10-28), with this, once the cause is dealt with.

With the ini file alone, it lists the forms being deleted and why each one
stopped. With a project and a form, it runs the deletion here, in this
process, from the step that stopped: each step skips what is done already.
The Celery plugins' IFormDeletionProcess runs as it does in the worker.
"""

import argparse
import logging
import os
import sys

import formshare.plugins as plugins
from formshare.app import load_settings_from_ini
from formshare.models import get_engine, get_session_factory
from formshare.processes.db.form_deletion import forms_being_deleted


def main(raw_args=None):
    parser = argparse.ArgumentParser(
        description="List the forms being deleted, or resume the deletion of one"
    )
    parser.add_argument("ini_path", help="Path to ini file")
    parser.add_argument("project_id", nargs="?", help="The form's project id")
    parser.add_argument("form_id", nargs="?", help="The form's id")
    args = parser.parse_args(raw_args)
    if not os.path.exists(args.ini_path):
        logging.error("Ini file does not exists")
        return 1
    settings = load_settings_from_ini(os.path.abspath(args.ini_path))
    if args.project_id is None or args.form_id is None:
        engine = get_engine(settings)
        session = get_session_factory(engine)()
        try:
            rows = forms_being_deleted(session)
        finally:
            session.close()
            engine.dispose()
        if not rows:
            print("No form is being deleted")
            return 0
        for project_id, project_code, form_id, deleted_by, error in rows:
            print(
                "{} ({}) {}: deleted by {}; {}".format(
                    project_id,
                    project_code,
                    form_id,
                    deleted_by,
                    "stopped: " + error if error else "no stop recorded (running?)",
                )
            )
        return 0
    # The plugins the worker runs after a deletion, as the worker loads them
    plugins.load_all_celery(settings.get("formshare.celery.plugins", ""))
    from formshare.products.deletion.celery_task import internal_delete_form

    deleted, reason = internal_delete_form(
        settings,
        args.project_id,
        args.form_id,
        settings.get("pyramid.default_locale_name", "en"),
    )
    if deleted:
        print("Form {} of project {} is deleted".format(args.form_id, args.project_id))
        return 0
    print(
        "Form {} of project {} is not deleted: {}".format(
            args.form_id, args.project_id, reason
        )
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
