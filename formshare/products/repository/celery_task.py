import gettext
import glob
import os
import shutil
import traceback
import uuid
from subprocess import Popen, PIPE, check_call, CalledProcessError

import formshare.plugins as p
import transaction
from celery.utils.log import get_task_logger
from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    Odkform,
    Formacces,
    Formgrpacces,
    Collingroup,
    map_to_schema,
    initialize_schema,
    DictTable,
    DictField,
    Project,
)
from formshare.processes.elasticsearch.repository_index import delete_dataset_from_index
from formshare.processes.email.send_async_email import send_async_email
from formshare.processes.sse.messaging import send_task_status_to_form
from formshare.products.fs1import.celery_task import internal_import_json_files
from lxml import etree
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers

log = get_task_logger(__name__)


class BuildDataBaseError(Exception):
    """
    Exception raised when there is an error while creating the repository.
    """


def log_message(message, error_str, output, command):
    if error_str is not None:
        error_str = error_str.decode()
    if output is not None:
        output = output.decode()
    log.error(
        message
        + "\nError: {} \n Output: {} \nCommand {}\n".format(error_str, output, command)
    )


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
        + " DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci",
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
            output, error_str = proc.communicate()
            if proc.returncode != 0:
                log_message(
                    "Error creating new tables", error_str, output, " ".join(args)
                )
                error = True

    if not error:
        send_task_status_to_form(settings, task_id, _("Inserting lookup values..."))
        with open(insert_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error_str = proc.communicate()
            if proc.returncode != 0:
                log_message(
                    "Error inserting into lookup tables",
                    error_str,
                    output,
                    " ".join(args),
                )
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
                output, error_str = proc.communicate()
                if proc.returncode != 0:
                    log_message(
                        "Error loading triggers", error_str, output, " ".join(args)
                    )
                    error = True
        else:
            error = True
            log_message("Error creating triggers", stderr, stdout, " ".join(args))

    if error:
        raise BuildDataBaseError(error_message)


def get_geopoint_variables(db_session, project, form):
    res = (
        db_session.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if res.form_geopoint is not None:
        return res.form_geopoint.split(",")
    return []


def get_one_assistant(db_session, project, form):
    res = (
        db_session.query(Project.project_formlist_auth)
        .filter(Project.project_id == project)
        .first()
    )
    if res[0] == 0:
        return "public", "public"
    res = (
        db_session.query(Formacces)
        .filter(Formacces.form_project == project)
        .filter(Formacces.form_id == form)
        .filter(Formacces.coll_can_submit == 1)
        .first()
    )
    if res is not None:
        return res.coll_id, res.project_id
    else:
        res = (
            db_session.query(Formgrpacces)
            .filter(Formgrpacces.form_project == project)
            .filter(Formgrpacces.form_id == form)
            .filter(Formgrpacces.group_can_submit == 1)
            .first()
        )
        if res is not None:
            project_id = res.project_id
            group_id = res.group_id
            res = (
                db_session.query(Collingroup)
                .filter(Collingroup.project_id == project_id)
                .filter(Collingroup.group_id == group_id)
                .first()
            )
            if res is not None:
                return (
                    res.coll_id,
                    res.enum_project,
                )
            else:
                return None, None
        else:
            return None, None


def update_dictionary_tables(db_session, project, form, xml_create_file):
    def create_new_field_dict(a_table, a_field):
        field_desc = a_field.get("desc", "")
        field_rlookup = a_field.get("rlookup", "false")
        if field_rlookup == "true":
            field_rlookup = 1
        else:
            field_rlookup = 0
        field_key = a_field.get("key", "false")
        if field_key == "true":
            field_key = 1
        else:
            field_key = 0
        field_sensitive = a_field.get("sensitive", "false")
        if field_sensitive == "true":
            field_sensitive = 1
        else:
            field_sensitive = 0
        if field_desc == "":
            field_desc = "Without a description"
        new_field_dict = {
            "project_id": project,
            "form_id": form,
            "table_name": a_table.get("name"),
            "field_name": a_field.get("name"),
            "field_desc": field_desc,
            "field_key": field_key,
            "field_xmlcode": a_field.get("xmlcode"),
            "field_type": a_field.get("type"),
            "field_odktype": a_field.get("odktype"),
            "field_rtable": a_field.get("rtable"),
            "field_rfield": a_field.get("rfield"),
            "field_rlookup": field_rlookup,
            "field_rname": a_field.get("rname"),
            "field_selecttype": a_field.get("selecttype"),
            "field_externalfilename": a_field.get("externalfilename"),
            "field_codecolumn": a_field.get("codeColumn"),
            "field_desccolumn": a_field.get("descColumn"),
            "field_size": a_field.get("size", 0),
            "field_decsize": a_field.get("decsize", 0),
            "field_sensitive": field_sensitive,
            "field_protection": a_field.get("protection"),
        }
        if a_field.get("selecttype") == "2":
            if new_field_dict["field_externalfilename"].upper().find(".CSV") == -1:
                new_field_dict["field_externalfilename"] = (
                    new_field_dict["field_externalfilename"] + ".csv"
                )
        return new_field_dict

    def store_tables(element, lookup):
        tables = element.findall(".//table")
        if tables:
            for table in tables:
                res = (
                    db_session.query(DictTable.table_name)
                    .filter(DictTable.project_id == project)
                    .filter(DictTable.form_id == form)
                    .filter(DictTable.table_name == table.get("name"))
                    .count()
                )
                if res == 0:
                    new_table_dict = {
                        "project_id": project,
                        "form_id": form,
                        "table_name": table.get("name"),
                        "table_desc": table.get("desc"),
                        "table_lkp": lookup,
                        "table_inserttrigger": table.get("inserttrigger"),
                        "table_xmlcode": table.get("xmlcode"),
                    }
                    parent = table.getparent()
                    if parent.tag == "table":
                        new_table_dict["parent_project"] = project
                        new_table_dict["parent_form"] = form
                        new_table_dict["parent_table"] = parent.get("name")
                    new_table = DictTable(**new_table_dict)
                    try:
                        db_session.add(new_table)
                        for field in table.getchildren():
                            if field.tag == "field":
                                res = (
                                    db_session.query(DictField.field_name)
                                    .filter(DictField.project_id == project)
                                    .filter(DictField.form_id == form)
                                    .filter(DictField.table_name == table.get("name"))
                                    .filter(DictField.field_name == field.get("name"))
                                    .count()
                                )
                                if res == 0:
                                    new_field_dict = create_new_field_dict(table, field)
                                    new_field = DictField(**new_field_dict)
                                    try:
                                        db_session.add(new_field)
                                    except IntegrityError:
                                        log.error(
                                            "Duplicated field {} in table {} in project {} form {}".format(
                                                field.get("name"),
                                                table.get("name"),
                                                project,
                                                form,
                                            )
                                        )
                                        return False
                    except IntegrityError:
                        log.error(
                            "Duplicated table {} in project {} form {}".format(
                                table.get("name"), project, form
                            )
                        )
                        return False
                else:
                    for field in table.getchildren():
                        if field.tag == "field":
                            res = (
                                db_session.query(DictField.field_name)
                                .filter(DictField.project_id == project)
                                .filter(DictField.form_id == form)
                                .filter(DictField.table_name == table.get("name"))
                                .filter(DictField.field_name == field.get("name"))
                                .count()
                            )
                            if res == 0:
                                new_field_dict = create_new_field_dict(table, field)
                                new_field = DictField(**new_field_dict)
                                try:
                                    db_session.add(new_field)
                                except IntegrityError:
                                    log.error(
                                        "Duplicated field {} in table {} in project {} form {}".format(
                                            field.get("name"),
                                            table.get("name"),
                                            project,
                                            form,
                                        )
                                    )
                                    return False
        return True

    if not os.path.isfile(xml_create_file):
        return
    tree = etree.parse(xml_create_file)
    root = tree.getroot()
    element_lkp_tables = root.find(".//lkptables")
    element_tables = root.find(".//tables")
    store_tables(element_lkp_tables, 1)
    store_tables(element_tables, 0)


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


def internal_create_mysql_repository(
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
    insert_xml_file,
    repository_string,
    locale,
    discard_testing_data,
    task_id,
):
    log.info(
        "Repository process for form {} in project {} has started".format(
            form, project_id
        )
    )
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

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

    engine = get_engine(settings)
    session_factory = get_session_factory(engine)

    with transaction.manager:
        db_session = get_tm_session(session_factory, transaction.manager)
        configure_mappers()
        initialize_schema()
        form_data = {
            "form_schema": schema,
            "form_pkey": primary_key,
            "form_createxmlfile": create_xml_file,
            "form_insertxmlfile": insert_xml_file,
            "form_hasdictionary": 1,
        }
        update_form(db_session, project_id, form, form_data)
        if not discard_testing_data:
            assistant, project_of_assistant = get_one_assistant(
                db_session, project_id, form
            )
            geo_point_variables = get_geopoint_variables(db_session, project_id, form)
        update_dictionary_tables(db_session, project_id, form, create_xml_file)
    engine.dispose()
    delete_dataset_from_index(settings, project_id, form)
    if discard_testing_data:
        # Remove any test submissions if any.
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
    else:
        unique_id = str(uuid.uuid4())
        temp_path = os.path.join(settings["repository.path"], *["tmp", unique_id])
        os.makedirs(temp_path)

        submissions_path = os.path.join(
            odk_dir, *["forms", form_directory, "submissions", "*.json"]
        )
        files = glob.glob(submissions_path)
        if files:
            for file in files:
                shutil.copy(file, temp_path)
            if assistant is not None and project_of_assistant is not None:
                internal_import_json_files(
                    user,
                    project_id,
                    form,
                    odk_dir,
                    form_directory,
                    schema,
                    assistant,
                    temp_path,
                    project_code,
                    geo_point_variables,
                    project_of_assistant,
                    settings,
                    locale,
                    False,
                    None,
                    False,
                    None,
                )
            else:
                log.error(
                    "Error while importing testing files. "
                    "The process was not able to find an assistant. "
                    "The testing files are in {} You can import them later on".format(
                        temp_path
                    )
                )
                email_from = settings.get("mail.from", None)
                email_to = settings.get("mail.error", None)
                send_async_email(
                    settings,
                    email_from,
                    email_to,
                    "Error while importing testing files",
                    "The process was not able to find an assistant. \n\n"
                    "The testing files are in {}. You can import them later on".format(
                        temp_path
                    ),
                    None,
                    locale,
                )

    try:
        for plugin in p.PluginImplementations(p.IRepositoryProcess):  # pragma: no cover
            plugin.after_creating_repository(
                settings,
                user,
                project_id,
                form,
                cnf_file,
                create_file,
                insert_file,
                schema,
                log,
            )
    except Exception as e:
        log.error("Repository Plugin Error: {}".format(str(e)))
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "Repository Plugin Error: {}".format(str(e)),
            None,
            locale,
        )


@celeryApp.task(bind=True, base=CeleryTask)
def create_mysql_repository(
    self,
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
    insert_xml_file,
    repository_string,
    locale,
    discard_testing_data,
    testing_task=None,
):
    if testing_task is None:
        task_id = create_mysql_repository.request.id
    else:
        task_id = testing_task
    internal_create_mysql_repository(
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
        insert_xml_file,
        repository_string,
        locale,
        discard_testing_data,
        task_id,
    )
