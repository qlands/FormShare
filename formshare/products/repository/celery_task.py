from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
import logging
from subprocess import Popen, PIPE, check_call, CalledProcessError
import glob
import os
import shutil
import transaction
from formshare.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    Odkform,
    map_to_schema,
    initialize_schema,
)
from formshare.processes.elasticsearch.repository_index import delete_dataset_index
from sqlalchemy.orm import configure_mappers
from formshare.processes.sse.messaging import send_task_status_to_form
import gettext
from formshare.processes.email.send_async_email import send_async_email
import traceback

log = logging.getLogger("formshare")


class BuildDataBaseError(Exception):
    """
        Exception raised when there is an error while creating the repository.
    """


def get_odk_path(settings):
    repository_path = settings["repository.path"]
    return os.path.join(repository_path, *["odk"])


def build_database(
    settings, cnf_file, create_file, insert_file, schema, form_directory, task_id, _
):
    error = False
    error_message = ""

    args = [
        "mysql",
        "--defaults-file=" + cnf_file,
        "--execute=CREATE SCHEMA "
        + schema
        + " DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci",
    ]
    try:
        check_call(args)
    except CalledProcessError as e:
        error_message = "Error dropping schema \n"
        error_message = error_message + "Error: \n"
        if e.stderr is not None:
            error_message = error_message + e.stderr.encode() + "\n"
        log.error(error_message)
        error = True

    if not error:
        send_task_status_to_form(settings, task_id, _("Creating new tables..."))
        args = ["mysql", "--defaults-file=" + cnf_file, schema]
        with open(create_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error = proc.communicate()
            if proc.returncode != 0:
                error_message = "Error creating database \n"
                error_message = error_message + "File: " + create_file + "\n"
                error_message = error_message + "Error: \n"
                if error is not None:
                    error_message = error_message + error.decode() + "\n"
                error_message = error_message + "Output: \n"
                if output is not None:
                    error_message = error_message + output.decode() + "\n"
                log.error(error_message)
                error = True

    if not error:
        send_task_status_to_form(settings, task_id, _("Inserting lookup values..."))
        with open(insert_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error = proc.communicate()
            if proc.returncode != 0:
                error_message = "Error loading lookup tables \n"
                error_message = error_message + "File: " + insert_file + "\n"
                error_message = error_message + "Error: \n"
                if error is not None:
                    error_message = error_message + error.decode() + "\n"
                error_message = error_message + "Output: \n"
                if output is not None:
                    error_message = error_message + output.decode() + "\n"
                log.error(error_message)
                error = True
    if not error:
        odk_dir = get_odk_path(settings)
        create_audit_triggers = os.path.join(
            settings["odktools.path"],
            *["utilities", "createAuditTriggers", "createaudittriggers"]
        )
        audit_path = os.path.join(odk_dir, *["forms", form_directory, "repository"])
        mysql_host = settings["mysql.host"]
        mysql_port = settings["mysql.port"]
        mysql_user = settings["mysql.user"]
        mysql_password = settings["mysql.password"]
        args = [
            create_audit_triggers,
            "-H " + mysql_host,
            "-P " + mysql_port,
            "-u " + mysql_user,
            "-p " + mysql_password,
            "-s " + schema,
            "-o " + audit_path,
        ]
        p = Popen(args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if p.returncode == 0:
            audit_file = os.path.join(
                odk_dir,
                *["forms", form_directory, "repository", "mysql_create_audit.sql"]
            )
            send_task_status_to_form(settings, task_id, _("Inserting lookup values..."))
            args = ["mysql", "--defaults-file=" + cnf_file, schema]
            with open(audit_file) as input_file:
                proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
                output, error = proc.communicate()
                if proc.returncode != 0:
                    error_message = "Error loading audit triggers \n"
                    error_message = error_message + "File: " + audit_file + "\n"
                    error_message = error_message + "Error: \n"
                    if error is not None:
                        error_message = error_message + error.decode() + "\n"
                    error_message = error_message + "Output: \n"
                    if output is not None:
                        error_message = error_message + output.decode() + "\n"
                    log.error(error_message)
                    error = True
        else:
            error = True
            error_message = (
                "Error while creating audit triggers: "
                + stdout.decode()
                + " - "
                + stderr.decode()
                + " - "
                + " ".join(args)
            )
            log.error(error_message)

    if error:
        raise BuildDataBaseError(error_message)


def update_form(db_session, project, form, form_data):
    mapped_data = map_to_schema(Odkform, form_data)
    try:
        db_session.query(Odkform).filter(Odkform.project_id == project).filter(
            Odkform.form_id == form
        ).update(mapped_data)
        db_session.flush()
        return True, ""
    except Exception as e:
        db_session.rollback()
        log.error(
            "Error {} while updating form {} in project {}".format(
                str(e), project, form
            )
        )
        raise BuildDataBaseError(str(e))


@celeryApp.task(base=CeleryTask)
def create_mysql_repository(
    settings,
    user,
    project_id,
    project_code,
    form,
    odk_dir,
    form_directory,
    schema,
    primary_key,
    cnf_file,
    create_file,
    insert_file,
    create_xml_file,
    repository_string,
    locale,
    testing_task=None,
):
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

    if testing_task is None:
        task_id = create_mysql_repository.request.id
    else:
        task_id = testing_task
    try:
        build_database(
            settings,
            cnf_file,
            create_file,
            insert_file,
            schema,
            form_directory,
            task_id,
            _,
        )
    except Exception as e:
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "Build repository error",
            "\n\nError: {}\n\nTraceback: {}\n\nMerge string {}".format(
                str(e), traceback.format_exc(), repository_string
            ),
            None,
            locale,
        )
        raise BuildDataBaseError(str(e))

    session_factory = get_session_factory(get_engine(settings))

    with transaction.manager:
        db_session = get_tm_session(session_factory, transaction.manager)
        configure_mappers()
        initialize_schema()
        form_data = {
            "form_schema": schema,
            "form_index": user.lower() + "_" + project_code.lower() + "_" + form,
            "form_pkey": primary_key,
            "form_createxmlfile": create_xml_file,
        }
        update_form(db_session, project_id, form, form_data)

    # Remove any test submissions if any. In try because nothing happens if they
    # don't get removed... just junk files
    submissions_path = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", "*.*"]
    )
    files = glob.glob(submissions_path)
    if files:
        for file in files:
            try:
                os.remove(file)
            except Exception as e:
                log.error(str(e))
    submissions_path = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", "*/"]
    )
    files = glob.glob(submissions_path)
    if files:
        for file in files:
            if file[-5:] != "logs/" and file[-5:] != "maps/":
                try:
                    shutil.rmtree(file)
                except Exception as e:
                    log.error(str(e))
    # Delete the dataset index
    delete_dataset_index(settings, user, project_code, form)
