"""Removes a project's field encryption, from the server's command line
(docs/formshare_field_encryption/formshare.md 16.2).

    remove_project_encryption [--reason <text>] [--yes] <ini file> <user id> <project code>

Two cases call for it:
- an owner whom FormShare told that encryption was set up for their project,
  when they did not set it up: someone used their session, and holds the key;
- a project set up before key versions were signed, or with grants of an
  older version, which can no longer be rotated or granted.

It removes every version of the project's key, their grants, and its recovery
kit, so that the owner can set encryption up again. Answers sealed with the
removed versions can no longer be opened through FormShare, and nothing gets
them back. It shows what it would remove, and changes nothing without --yes.

No page does this: a session that could remove a project's key could put in
one of its own.
"""

import argparse
import getpass
import logging
import os
import socket
from types import SimpleNamespace

from formshare.app import load_settings_from_ini
from formshare.models import DictField, EncryptionGrant, get_engine, get_session_factory
from formshare.processes.db.encryption import (
    get_project_keys,
    remove_project_encryption,
)
from formshare.processes.db.project import get_project_id_from_name


def _who():
    """Who ran it, for the project's record."""
    try:
        return "{}@{}".format(getpass.getuser(), socket.gethostname())
    except Exception:
        return "the server's administrator"


def main(raw_args=None):
    parser = argparse.ArgumentParser(
        description="Remove a project's field encryption, so that its owner can "
        "set it up again. Answers sealed with it can no longer be opened."
    )
    parser.add_argument("--reason", help="Why, for the project's record")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Remove it. Without this, it only shows what it would remove",
    )
    parser.add_argument("ini_path", help="Path to ini file")
    parser.add_argument("user_id", help="The project's owner")
    parser.add_argument("project_code", help="The project's code")
    args = parser.parse_args(raw_args)
    if not os.path.exists(args.ini_path):
        logging.error("Ini file does not exists")
        return 1

    settings = load_settings_from_ini(os.path.abspath(args.ini_path))
    engine = get_engine(settings)
    session = get_session_factory(engine)()
    request = SimpleNamespace(
        dbsession=session,
        translate=lambda text: text,
        client_addr=None,
        user_agent="remove_project_encryption",
    )
    try:
        project_id = get_project_id_from_name(request, args.user_id, args.project_code)
        if project_id is None:
            print(
                "{} has no project {}: nothing was changed.".format(
                    args.user_id, args.project_code
                )
            )
            return 1
        keys = get_project_keys(request, project_id)
        if not keys:
            print("Encryption is not set up for this project: nothing to remove.")
            return 1
        grants = (
            session.query(EncryptionGrant)
            .filter(EncryptionGrant.project_id == project_id)
            .count()
        )
        forms = sorted(
            {
                row[0]
                for row in session.query(DictField.form_id)
                .filter(DictField.project_id == project_id)
                .filter(DictField.field_encrypted == 1)
                .all()
            }
        )
        print(
            "Project {} of {} ({})".format(args.project_code, args.user_id, project_id)
        )
        for a_key in keys:
            print(
                "  key {} ({}, set up {})".format(
                    a_key["key_id"], a_key["key_status"], a_key["created_date"]
                )
            )
        print("  {} grants, and the recovery kit".format(grants))
        print("  forms that encrypt answers: {}".format(", ".join(forms) or "none yet"))
        print(
            "Answers sealed with these keys can no longer be opened through "
            "FormShare once they are removed, and nothing gets them back. Until "
            "the owner sets encryption up again, a form that encrypts takes no "
            "submission."
        )
        if not args.yes:
            print("Nothing was changed. Run it again with --yes to remove them.")
            return 1
        removed, result = remove_project_encryption(
            request, project_id, _who(), args.reason
        )
        if not removed:
            print(result)
            return 1
        print(
            "Removed the keys {}. The owner can set encryption up again.".format(
                ", ".join(result)
            )
        )
        return 0
    finally:
        session.close()
        engine.dispose()
