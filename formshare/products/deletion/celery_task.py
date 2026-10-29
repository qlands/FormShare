"""The Celery task that deletes a form (owner, 2026-10-28). The request has
marked the form and its versions inactive, blocked and being deleted
(processes/db/form_deletion.py, which tells the whole story).

Its steps, each skipped when it is done already, so that a deletion that
stopped can be resumed (resume_form_deletion):

1. what is still granted on the repository, revoked. MySQL keeps a
   database's privileges when it drops it, and the dump makes the schema
   again under its name, so restoring it would give the accounts of the
   analytics plugin their access back (checked on 8.4, 2026-10-28). A grant
   that cannot be revoked is reported to the technical team, and the
   deletion goes on: the schema is dropped either way;
2. a gzipped dump of the repository, mysqldump's, in the form's repository
   directory, checked whole before anything is dropped;
3. the repository dropped. MySQL drops a database whole or not at all, so a
   resume finds the repository whole or gone: whole, it is dumped again, and
   the dump of each attempt stays;
4. each version's directory renamed, as deleting a form always did;
5. the forms' documents deleted from the index, and their buckets;
6. the forms deleted from FormShare's database, with what cascades from
   their rows;
7. IFormDeletionProcess.after_deleting_form, for the Celery plugins, once for
   each form deleted.

Any other step that fails stops the task. The forms stay inactive, blocked
and being deleted, the reason goes in form_deleteerror, and the technical
team is emailed: only they resume it (owner, 2026-10-28). A repository a
deleted form's leftover still refers to is one such stop. Users cannot
cancel it: the task is no AbortableTask, and no page offers to stop it.
"""

import datetime
import gettext
import gzip
import logging
import os
import re
import shutil
import tempfile
import traceback
from hashlib import md5
from subprocess import PIPE, Popen
from types import SimpleNamespace

import formshare.plugins as plugins
from celery.utils.log import get_task_logger
from formshare.config.celery_app import celeryApp
from formshare.models import Odkform, map_from_schema
from formshare.processes.db.form import delete_case_lookup_table
from formshare.processes.db.form_deletion import (
    forms_of_deletion,
    record_deletion_error,
)
from formshare.processes.elasticsearch.record_index import delete_form_records
from formshare.processes.elasticsearch.repository_index import (
    delete_dataset_from_index,
)
from formshare.processes.email.send_async_email import send_async_email
from formshare.processes.storage.local_storage import delete_bucket
from sqlalchemy import create_engine
from sqlalchemy import text as sqlalchemy_text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

log = get_task_logger(__name__)
form_log = logging.getLogger("formshare")

# The dump restores the repository as it was, schema included: its tables,
# triggers and routines, in one consistent read
DUMP_OPTIONS = [
    "--set-gtid-purged=OFF",
    "--no-tablespaces",
    "--column-statistics=0",
    "--single-transaction",
    "--routines",
    "--triggers",
    "--databases",
]
# The last line of a dump mysqldump finished
DUMP_COMPLETED = b"-- Dump completed"
SCHEMA_NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")
CHUNK = 1 << 20


class FormDeletionError(Exception):
    """A step of a deletion that failed: the deletion stops there."""


class TaskRequest:
    """What delete_bucket and delete_case_lookup_table read of a request."""

    def __init__(self, session, settings, translate):
        self.dbsession = session
        self.registry = SimpleNamespace(settings=settings)
        self.translate = translate


def translator(locale):
    directory = __file__.split("/products/")[0] + "/locale"
    return gettext.translation(
        "formshare", localedir=directory, languages=[locale or "en"], fallback=True
    ).gettext


def repository_exists(session, schema):
    return bool(
        session.execute(
            sqlalchemy_text(
                "SELECT COUNT(*) FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = :schema"
            ),
            {"schema": schema},
        ).scalar()
    )


def dump_is_whole(path):
    """Whether a gzipped dump reads to its end, which mysqldump writes last."""
    tail = b""
    with gzip.open(path, "rb") as dump:
        for chunk in iter(lambda: dump.read(CHUNK), b""):
            tail = (tail + chunk)[-4096:]
    return DUMP_COMPLETED in tail


def dump_repository(settings, schema, directory, stamp):
    """A gzipped mysqldump of the repository in directory, checked whole.
    Returns its path. It is written beside its name and moved there once
    checked, so a dump under its name is a whole one."""
    os.makedirs(directory, exist_ok=True)
    target = os.path.join(directory, "{}_{}.sql.gz".format(schema, stamp))
    part = target + ".part"
    args = ["mysqldump", "--defaults-file=" + settings["mysql.cnf"]]
    args += DUMP_OPTIONS + [schema]
    # stderr goes to a file: a pipe left unread could fill and hang mysqldump
    with tempfile.TemporaryFile() as errors:
        with gzip.open(part, "wb") as out:
            process = Popen(args, stdout=PIPE, stderr=errors)
            for chunk in iter(lambda: process.stdout.read(CHUNK), b""):
                out.write(chunk)
            process.wait()
        errors.seek(0)
        message = errors.read().decode("utf-8", "replace").strip()
    if process.returncode != 0:
        os.remove(part)
        raise FormDeletionError(
            "mysqldump of {} failed ({}): {}".format(
                schema, process.returncode, message
            )
        )
    if not dump_is_whole(part):
        os.remove(part)
        raise FormDeletionError("The dump of {} is not whole".format(schema))
    os.replace(part, target)
    return target


def revoke_repository_grants(session, schema):
    """Revokes what each account holds on the repository itself, and returns
    the accounts, as user@host. A grant on a pattern that matches other
    schemas too is left alone. mysql.db keeps the name as it was granted,
    with its underscores escaped or not."""
    if not SCHEMA_NAME.match(schema):
        raise FormDeletionError("Not a repository name: {}".format(schema))
    rows = session.execute(
        sqlalchemy_text(
            "SELECT User, Host, Db, Grant_priv FROM mysql.db "
            "WHERE Db = :schema OR Db = :escaped"
        ),
        {"schema": schema, "escaped": schema.replace("_", "\\_")},
    ).fetchall()
    revoked = []
    for user, host, name, grant_option in rows:
        on = "`{}`.*".format(name.replace("`", "``"))
        account = {"user": user, "host": host}
        # MySQL revokes ALL PRIVILEGES and GRANT OPTION in one statement only
        # on every database at once
        session.execute(
            sqlalchemy_text("REVOKE ALL PRIVILEGES ON " + on + " FROM :user@:host"),
            account,
        )
        if grant_option == "Y":
            session.execute(
                sqlalchemy_text("REVOKE GRANT OPTION ON " + on + " FROM :user@:host"),
                account,
            )
        revoked.append("{}@{}".format(user, host))
    return revoked


def drop_repository(session, schema):
    if not SCHEMA_NAME.match(schema):
        raise FormDeletionError("Not a repository name: {}".format(schema))
    session.execute(sqlalchemy_text("DROP DATABASE `{}`".format(schema)))


def rename_directory(odk_dir, directory, user, stamp):
    """Renames a form's directory as deleting a form always did. Returns the
    new path, or None when there is nothing left to rename."""
    if not directory:
        return None
    source = os.path.join(odk_dir, "forms", directory)
    if not os.path.exists(source):
        return None
    target = source + "_deleted_by_{}_on_{}".format(user, stamp)
    shutil.move(source, target)
    return target


def _email_technical_team(settings, subject, message, locale):
    email_from = settings.get("mail.from", None)
    email_to = settings.get("mail.error", None)
    if not email_from or not email_to:
        return
    try:
        send_async_email(settings, email_from, email_to, subject, message, None, locale)
    except Exception as e:
        log.error("The email to the technical team could not be sent: {}".format(e))


def internal_delete_form(settings, project_id, form_id, locale="en"):
    """Deletes a form marked for deletion, and its versions. Returns (True,
    "") when it is gone, or (False, why) when it stopped: then the forms stay
    marked, with the reason, for the technical team. A form not marked is
    left as it is."""
    _ = translator(locale)
    engine = create_engine(settings["sqlalchemy.url"], poolclass=NullPool)
    session = Session(bind=engine)
    keys = [(project_id, form_id)]
    try:
        forms = forms_of_deletion(session, project_id, form_id)
        if not forms:
            return True, ""
        if any((a_row.form_deleting or 0) != 1 for a_row in forms):
            # A live form, say a resume given the wrong ID: nothing is
            # recorded on it, and nobody is emailed
            return False, "it is not marked for deletion"
        keys = [(a_row.project_id, a_row.form_id) for a_row in forms]
        forms_data = [map_from_schema(a_row) for a_row in forms]
        form_data = forms_data[0]
        directories = [a_row.form_directory for a_row in forms]
        schema = form_data["form_schema"]
        user = form_data["form_deletedby"] or "unknown"
        stamp = datetime.datetime.now().strftime("%Y_%m_%d:%H_%M_%S")
        odk_dir = os.path.join(settings["repository.path"], "odk")
        # Nothing of the read is kept open across what follows
        session.rollback()

        # 1: what is still granted on the repository, revoked, whether it is
        # still there or a resume finds it dropped
        if schema:
            try:
                revoked = revoke_repository_grants(session, schema)
                if revoked:
                    log.info(
                        "Form {}: what {} held on repository {} revoked".format(
                            form_id, ", ".join(revoked), schema
                        )
                    )
            except Exception as e:
                session.rollback()
                log.error(
                    "Form {}: what is granted on repository {} could not be "
                    "revoked. {}".format(form_id, schema, e)
                )
                _email_technical_team(
                    settings,
                    "A deleted form's repository is still granted",
                    "The deletion of form {} of project {} could not revoke what "
                    "is granted on its repository, {}. MySQL keeps those grants "
                    "when it drops the repository, and restoring the repository's "
                    "dump would give those accounts their access back: revoke "
                    "them by hand.\n\nError: {}".format(form_id, project_id, schema, e),
                    locale,
                )

        # 2 and 3: the repository, kept as a dump, then dropped
        if schema and repository_exists(session, schema):
            directory = os.path.join(
                odk_dir, "forms", form_data["form_directory"] or form_id, "repository"
            )
            dump = dump_repository(settings, schema, directory, stamp.replace(":", "_"))
            log.info("Form {}: repository {} kept in {}".format(form_id, schema, dump))
            drop_repository(session, schema)
            log.info("Form {}: repository {} dropped".format(form_id, schema))

        # 4: the directories, renamed
        for directory in directories:
            rename_directory(odk_dir, directory, user, stamp)

        # 5: the index documents and the buckets
        request = TaskRequest(session, settings, _)
        for project, form in keys:
            delete_dataset_from_index(settings, project, form)
            delete_form_records(settings, project, form)
            delete_bucket(request, md5((project + form).encode("utf-8")).hexdigest())
        if form_data["form_case"] == 1 and form_data["form_casetype"] == 1 and schema:
            delete_case_lookup_table(request, project_id)

        # 6: the rows, with what cascades from them
        for project, form in keys:
            session.query(Odkform).filter(Odkform.project_id == project).filter(
                Odkform.form_id == form
            ).update({"parent_project": None, "parent_form": None})
        for project, form in keys:
            session.query(Odkform).filter(Odkform.project_id == project).filter(
                Odkform.form_id == form
            ).delete()
        session.commit()
        form_log.info(
            "FormDelete: Form {} in project {} was deleted by {} on {}".format(
                form_id, project_id, user, stamp
            )
        )

        # 7: the Celery plugins, once for each form deleted, the form asked
        # for first. What a plugin keeps of a version is under the version's
        # own ID: the Superset plugin's chart suggestions are
        deletion_plugins = list(
            plugins.PluginImplementations(plugins.IFormDeletionProcess)
        )
        for a_form in forms_data:
            for a_plugin in deletion_plugins:
                try:
                    a_plugin.after_deleting_form(
                        settings,
                        user,
                        a_form["project_id"],
                        a_form["form_id"],
                        a_form,
                        log,
                    )
                except Exception as e:
                    log.error(
                        "A plugin failed after deleting form {}: {}".format(
                            a_form["form_id"], e
                        )
                    )
        return True, ""
    except Exception as e:
        session.rollback()
        reason = "{}: {}".format(type(e).__name__, str(e))
        log.error(
            "The deletion of form {} of project {} stopped. {}".format(
                form_id, project_id, reason
            )
        )
        try:
            record_deletion_error(session, keys, reason)
        except Exception as recording_error:
            session.rollback()
            log.error("The reason could not be recorded: {}".format(recording_error))
        _email_technical_team(
            settings,
            "A form deletion stopped",
            "The deletion of form {} of project {} stopped. The form stays blocked "
            "until it is resumed on the server (resume_form_deletion).\n\n"
            "Error: {}\n\nTraceback: {}".format(
                form_id, project_id, reason, traceback.format_exc()
            ),
            locale,
        )
        return False, reason
    finally:
        session.close()
        engine.dispose()


# Runs in the Celery worker, which coverage does not measure
@celeryApp.task(bind=True)
def delete_form_task(self, settings, project_id, form_id, locale):  # pragma: no cover
    internal_delete_form(settings, project_id, form_id, locale)
