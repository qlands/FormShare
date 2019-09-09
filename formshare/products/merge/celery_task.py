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
import uuid
from lxml import etree

log = logging.getLogger("formshare")


class BuildDataBaseError(Exception):
    """
        Exception raised when there is an error while creating the repository.
    """


def get_odk_path(settings):
    repository_path = settings["repository.path"]
    return os.path.join(repository_path, *["odk"])


def make_database_changes(settings, cnf_file, a_schema, b_schema, merge_create_file, merge_insert_file,
                          merge_log_file, a_create_xml_file, b_create_xml_file, b_backup_file, a_form_directory,
                          task_id, _):
    pass
    error = False
    error_message = ""

    args = [
        "mysql",
        "--defaults-file=" + cnf_file,
        "--execute=CREATE SCHEMA "
        + a_schema
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
        send_task_status_to_form(settings, task_id, _("Creating database backup..."))
        args = ["mysqldump", "--defaults-file=" + cnf_file, b_schema]
        with open(b_backup_file, "w") as backup_file:
            proc = Popen(args, stdin=PIPE, stderr=PIPE, stdout=backup_file)
            output, error = proc.communicate()
            if proc.returncode != 0:
                error_message = "Error creating database backup \n"
                error_message = error_message + "File: " + b_backup_file + "\n"
                error_message = error_message + "Error: \n"
                if error is not None:
                    error_message = error_message + error.decode() + "\n"
                error_message = error_message + "Output: \n"
                if output is not None:
                    error_message = error_message + output.decode() + "\n"
                log.error(error_message)
                error = True

    if not error:
        send_task_status_to_form(settings, task_id, _("Moving backup into new schema..."))
        args = ["mysql", "--defaults-file=" + cnf_file, a_schema]
        with open(b_backup_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error = proc.communicate()
            if proc.returncode != 0:
                error_message = "Error creating database \n"
                error_message = error_message + "File: " + b_backup_file + "\n"
                error_message = error_message + "Error: \n"
                if error is not None:
                    error_message = error_message + error.decode() + "\n"
                error_message = error_message + "Output: \n"
                if output is not None:
                    error_message = error_message + output.decode() + "\n"
                log.error(error_message)
                error = True

    if not error:
        send_task_status_to_form(settings, task_id, _("Applying structure changes in the new schema..."))
        args = ["mysql", "--defaults-file=" + cnf_file, a_schema]
        with open(merge_create_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error = proc.communicate()
            if proc.returncode != 0:
                error_message = "Error creating database \n"
                error_message = error_message + "File: " + merge_create_file + "\n"
                error_message = error_message + "Error: \n"
                if error is not None:
                    error_message = error_message + error.decode() + "\n"
                error_message = error_message + "Output: \n"
                if output is not None:
                    error_message = error_message + output.decode() + "\n"
                log.error(error_message)
                error = True

    if not error:
        send_task_status_to_form(settings, task_id, _("Applying lookup value changes in the new schema..."))
        args = ["mysql", "--defaults-file=" + cnf_file, a_schema]
        with open(merge_insert_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error = proc.communicate()
            if proc.returncode != 0:
                error_message = "Error creating database \n"
                error_message = error_message + "File: " + merge_insert_file + "\n"
                error_message = error_message + "Error: \n"
                if error is not None:
                    error_message = error_message + error.decode() + "\n"
                error_message = error_message + "Output: \n"
                if output is not None:
                    error_message = error_message + output.decode() + "\n"
                log.error(error_message)
                error = True

    try:
        root = etree.parse(merge_log_file)
        error_list = root.findall(".//error")

        new_table_list = []
        rebuild_table_list = []
        if error_list:
            for an_error in error_list:
                if an_error.get("code") == "FNF":
                    if an_error.get("table") not in rebuild_table_list:
                        rebuild_table_list.append(an_error.get("table"))
                if an_error.get("code") == "TNF":
                    new_table_list.append(an_error.get("to"))
        if len(new_table_list) >= 0 or len(rebuild_table_list) >= 0:
            send_task_status_to_form(settings, task_id, _("Modifying audit triggers"))


    except Exception as e:
        log.error("Error processing merge log file: {}. Error: {}".format(merge_log_file, str(e)))


    odk_dir = get_odk_path(settings)


    #
    # if not error:
    #     send_task_status_to_form(settings, task_id, _("Inserting lookup values..."))
    #     with open(insert_file) as input_file:
    #         proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
    #         output, error = proc.communicate()
    #         if proc.returncode != 0:
    #             error_message = "Error loading lookup tables \n"
    #             error_message = error_message + "File: " + insert_file + "\n"
    #             error_message = error_message + "Error: \n"
    #             if error is not None:
    #                 error_message = error_message + error.decode() + "\n"
    #             error_message = error_message + "Output: \n"
    #             if output is not None:
    #                 error_message = error_message + output.decode() + "\n"
    #             log.error(error_message)
    #             error = True
    #
    # if not error:
    #     odk_dir = get_odk_path(settings)
    #     create_audit_triggers = os.path.join(
    #         settings["odktools.path"],
    #         *["utilities", "createAuditTriggers", "createaudittriggers"]
    #     )
    #     audit_path = os.path.join(odk_dir, *["forms", form_directory, "repository"])
    #     mysql_host = settings["mysql.host"]
    #     mysql_port = settings["mysql.port"]
    #     mysql_user = settings["mysql.user"]
    #     mysql_password = settings["mysql.password"]
    #     args = [
    #         create_audit_triggers,
    #         "-H " + mysql_host,
    #         "-P " + mysql_port,
    #         "-u " + mysql_user,
    #         "-p " + mysql_password,
    #         "-s " + schema,
    #         "-o " + audit_path,
    #     ]
    #     p = Popen(args, stdout=PIPE, stderr=PIPE)
    #     stdout, stderr = p.communicate()
    #     if p.returncode == 0:
    #         audit_file = os.path.join(
    #             odk_dir,
    #             *["forms", form_directory, "repository", "mysql_create_audit.sql"]
    #         )
    #         send_task_status_to_form(settings, task_id, _("Inserting lookup values..."))
    #         args = ["mysql", "--defaults-file=" + cnf_file, schema]
    #         with open(audit_file) as input_file:
    #             proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
    #             output, error = proc.communicate()
    #             if proc.returncode != 0:
    #                 error_message = "Error loading audit triggers \n"
    #                 error_message = error_message + "File: " + audit_file + "\n"
    #                 error_message = error_message + "Error: \n"
    #                 if error is not None:
    #                     error_message = error_message + error.decode() + "\n"
    #                 error_message = error_message + "Output: \n"
    #                 if output is not None:
    #                     error_message = error_message + output.decode() + "\n"
    #                 log.error(error_message)
    #                 error = True
    #     else:
    #         error = True
    #         error_message = (
    #             "Error while creating audit triggers: "
    #             + stdout.decode()
    #             + " - "
    #             + stderr.decode()
    #             + " - "
    #             + " ".join(args)
    #         )
    #         log.error(error_message)
    #
    # if error:
    #     raise BuildDataBaseError(error_message)


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
def merge_into_repository(
        settings,
        user,
        project_id,
        project_code,
        a_form_id,
        a_form_directory,
        b_form_directory,
        b_schema_name,
        locale,
):
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

    odk_dir = get_odk_path(settings)

    merge_create_file = os.path.join(
        odk_dir, *["forms", a_form_directory, "merging_files", "create.sql"]
    )

    merge_insert_file = os.path.join(
        odk_dir, *["forms", a_form_directory, "merging_files", "insert.sql"]
    )

    merge_log_file = os.path.join(
        odk_dir, *["forms", a_form_directory, "merging_files", "output.xml"]
    )

    a_create_xml_file = os.path.join(
        odk_dir, *["forms", a_form_directory, "repository", "create.xml"]
    )

    b_create_xml_file = os.path.join(
        odk_dir, *["forms", b_form_directory, "repository", "create.xml"]
    )

    b_backup_directory = os.path.join(
        odk_dir, *["forms", b_form_directory, "repository_bks"]
    )
    os.makedirs(b_backup_directory)

    b_backup_file = os.path.join(
        odk_dir, *["forms", b_form_directory, "repository_bks", b_schema_name + ".sql"]
    )

    a_schema_name = "FS_" + str(uuid.uuid4()).replace("-", "_")

    task_id = merge_into_repository.request.id
    cnf_file = settings["mysql.cnf"]
    make_database_changes(settings, cnf_file, a_schema_name, b_schema_name, merge_create_file, merge_insert_file,
                          merge_log_file, a_create_xml_file, b_create_xml_file, b_backup_file, a_form_directory,
                          task_id, _)

    session_factory = get_session_factory(get_engine(settings))

    with transaction.manager:
        db_session = get_tm_session(session_factory, transaction.manager)
        configure_mappers()
        initialize_schema()
        form_data = {"form_schema": a_schema_name}
        update_form(db_session, project_id, a_form_id, form_data)

    # Remove any test submissions if any. In try because nothing happens if they
    # don't get removed... just junk files
    submissions_path = os.path.join(
        odk_dir, *["forms", a_form_directory, "submissions", "*.*"]
    )
    files = glob.glob(submissions_path)
    if files:
        for file in files:
            try:
                os.remove(file)
            except Exception as e:
                log.error(str(e))
    submissions_path = os.path.join(
        odk_dir, *["forms", a_form_directory, "submissions", "*/"]
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
    delete_dataset_index(settings, user, project_code, a_form_id)
