import gettext
import glob
import json
import os
import shutil
import time
import traceback
import uuid
from subprocess import Popen, PIPE, check_call, CalledProcessError

import transaction
from celery.utils.log import get_task_logger
from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    Odkform,
    map_to_schema,
    initialize_schema,
    Formacces,
    Formgrpacces,
    Collingroup,
    DictTable,
    DictField,
    Project,
)
from formshare.processes.elasticsearch.repository_index import delete_dataset_from_index
from formshare.processes.email.send_async_email import send_async_email
from formshare.processes.sse.messaging import send_task_status_to_form
from formshare.products.fs1import.celery_task import internal_import_json_files
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers
from sqlalchemy.pool import NullPool

log = get_task_logger(__name__)


class MergeDataBaseError(Exception):
    """
    Exception raised when there is an error while creating the repository.
    """


def get_odk_path(settings):
    repository_path = settings["repository.path"]
    return os.path.join(repository_path, *["odk"])


def move_changes(node_b, root_a):
    target_table = None
    for tag in node_b.iter():
        if not len(tag):
            field_name = tag.get("name")
            field_sensitive = tag.get("sensitive")
            field_protection = tag.get("protection")
            formshare_encrypted = tag.get("formshare_encrypted", "no")
            target_field = target_table.find(".//field[@name='" + field_name + "']")
            if target_field is not None:
                target_field.set("formshare_encrypted", formshare_encrypted)
                if field_sensitive is not None:
                    if field_sensitive == "true":
                        target_field.set("sensitive", field_sensitive)
                        target_field.set("protection", field_protection)
                        target_field.set("formshare_sensitive", "yes")
        else:
            current_table = tag.get("name")
            if current_table is not None:
                table_desc = tag.get("desc")
                target_table = root_a.find(".//table[@name='" + current_table + "']")
                if target_table is not None:
                    target_table.set("desc", table_desc)


def log_message(message, error_str, output, command):
    if error_str is not None:
        error_str = error_str.decode()
    if output is not None:
        output = output.decode()
    log.error(
        message
        + "\nError: {} \n Output: {} \nCommand {}\n".format(error_str, output, command)
    )


def make_database_changes(
    settings,
    cnf_file,
    a_schema,
    b_schema,
    merge_create_file,
    merge_insert_file,
    merge_log_file,
    c_create_xml_file,
    b_create_xml_file,
    b_backup_file,
    a_form_directory,
    task_id,
    _,
):
    error = False
    error_message = ""

    args = [
        "mysql",
        "--defaults-file=" + cnf_file,
        "--execute=CREATE SCHEMA "
        + a_schema
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
        args = ["mysqldump", "--defaults-file=" + cnf_file, b_schema]
        log.info(b_backup_file)
        log.info(" ".join(args))
        with open(b_backup_file, "w") as backup_file:
            proc = Popen(args, stdin=PIPE, stderr=PIPE, stdout=backup_file)
            output, error_str = proc.communicate()
            log.info("Result is {}".format(proc.returncode))
            if proc.returncode != 0:
                log_message("Error creating backup", error_str, output, " ".join(args))
                error = True
    if not error:
        log.info("Creating schema {} as backup of {}".format(a_schema, b_schema))
        send_task_status_to_form(settings, task_id, _("Creating backup of schema"))
        args = ["mysql", "--defaults-file=" + cnf_file, a_schema]
        with open(b_backup_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error_str = proc.communicate()
            if proc.returncode != 0:  # pragma: no cover
                log_message(
                    "Error creating database from backup",
                    error_str,
                    output,
                    " ".join(args),
                )
                error = True

    if not error:
        log.info("Applying structure changes in the schema...")
        send_task_status_to_form(
            settings, task_id, _("Applying structure changes in the schema...")
        )
        args = ["mysql", "--defaults-file=" + cnf_file, b_schema]
        with open(merge_create_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error_str = proc.communicate()
            if proc.returncode != 0:  # pragma: no cover
                log_message(
                    "Error applying changes to schema",
                    error_str,
                    output,
                    " ".join(args),
                )
                error = True

    if not error:
        log.info("Applying lookup value changes in the schema...")
        send_task_status_to_form(
            settings, task_id, _("Applying lookup value changes in the schema...")
        )
        args = ["mysql", "--defaults-file=" + cnf_file, b_schema]
        with open(merge_insert_file) as input_file:
            proc = Popen(args, stdin=input_file, stderr=PIPE, stdout=PIPE)
            output, error_str = proc.communicate()
            if proc.returncode != 0:  # pragma: no cover
                log_message(
                    "Error applying lookup changes to schema",
                    error_str,
                    output,
                    " ".join(args),
                )
                error = True

    if not error:
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
                if len(rebuild_table_list) > 0:
                    log.info("Dropping old triggers")
                    send_task_status_to_form(
                        settings, task_id, _("Dropping old triggers")
                    )
                    engine = create_engine(
                        settings.get("sqlalchemy.url"), poolclass=NullPool
                    )
                    for a_table in rebuild_table_list:
                        if not error:
                            sql = (
                                "SELECT TRIGGER_NAME FROM information_schema.triggers "
                                "WHERE TRIGGER_SCHEMA = '{}' "
                                "AND EVENT_OBJECT_TABLE = '{}' "
                                "AND TRIGGER_NAME LIKE 'audit_%'".format(
                                    b_schema, a_table
                                )
                            )
                            try:
                                res = engine.execute(sql).fetchall()
                                for a_trigger in res:
                                    sql = "DROP TRIGGER {}.{}".format(
                                        b_schema, a_trigger[0]
                                    )
                                    try:
                                        engine.execute(sql)
                                    except Exception as e:
                                        log.error(
                                            "Error {} while dropping trigger {} from database {}".format(
                                                str(e), a_trigger[0], b_schema
                                            )
                                        )
                                        error = True
                                        break
                            except Exception as e:
                                log.error(
                                    "Error {} while loading triggers from schema {}, table {}".format(
                                        str(e), b_schema, a_table
                                    )
                                )
                                error = True
                    engine.dispose()
                    if not error:
                        odk_dir = get_odk_path(settings)

                        str_all_tables = ",".join(rebuild_table_list + new_table_list)

                        create_audit_triggers = os.path.join(
                            settings["odktools.path"],
                            *["utilities", "createAuditTriggers", "createaudittriggers"]
                        )
                        audit_path = os.path.join(
                            odk_dir, *["forms", a_form_directory, "merging_files"]
                        )
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
                            "-s " + b_schema,
                            "-o " + audit_path,
                            "-t " + str_all_tables,
                        ]
                        p = Popen(args, stdout=PIPE, stderr=PIPE)
                        stdout, stderr = p.communicate()
                        if p.returncode == 0:
                            audit_file = os.path.join(
                                odk_dir,
                                *[
                                    "forms",
                                    a_form_directory,
                                    "merging_files",
                                    "mysql_create_audit.sql",
                                ]
                            )
                            log.info("Creating new triggers")
                            send_task_status_to_form(
                                settings, task_id, _("Creating new triggers")
                            )
                            args = ["mysql", "--defaults-file=" + cnf_file, b_schema]
                            with open(audit_file) as input_file:
                                proc = Popen(
                                    args, stdin=input_file, stderr=PIPE, stdout=PIPE
                                )
                                output, error_str = proc.communicate()
                                if proc.returncode != 0:  # pragma: no cover
                                    log_message(
                                        "Error applying triggers",
                                        error_str,
                                        output,
                                        " ".join(args),
                                    )
                                    error = True
                        else:  # pragma: no cover
                            log_message(
                                "Error creating triggers",
                                stderr,
                                stdout,
                                " ".join(args),
                            )
                            error = True
        except Exception as e:
            log.error(
                "Error processing merge log file: {}. Error: {}".format(
                    merge_log_file, str(e)
                )
            )
            error = True

    if not error:
        try:
            # Move all metadata changes made to b into c
            tree_b = etree.parse(b_create_xml_file)
            tree_c = etree.parse(c_create_xml_file)
            root_b = tree_b.getroot()
            root_c = tree_c.getroot()
            move_changes(root_b, root_c)
            tree_c.write(
                c_create_xml_file,
                pretty_print=True,
                xml_declaration=True,
                encoding="utf-8",
            )
        except Exception as e:
            log.error(
                "Error while moving metadata changes from {} to {}. Error: {}".format(
                    b_create_xml_file, c_create_xml_file, str(e)
                )
            )
            error = True
    if error:
        raise MergeDataBaseError(error_message)


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


def update_dictionary_tables(db_session, form_id, xml_create_file, survey_data_columns):
    def create_new_field_dict(a_table, a_field, project, form):
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
        formshare_sensitive = a_field.get("formshare_sensitive", "no")
        if (
            field_sensitive == "true"
            or formshare_sensitive == "yes"
            or formshare_sensitive == "1"
        ):
            field_sensitive = 1
            if field_key == 0:
                field_protection = a_field.get("protection", "exclude")
            else:
                field_protection = a_field.get("protection", "recode")
        else:
            field_sensitive = 0
            field_protection = None

        if (
            a_field.get("formshare_encrypted", "no") == "yes"
            or a_field.get("formshare_encrypted", "no") == "1"
        ):
            field_encrypted = 1
        else:
            field_encrypted = 0

        field_ontology = a_field.get("formshare_ontological_term")

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
            "field_protection": field_protection,
            "field_encrypted": field_encrypted,
            "field_ontology": field_ontology,
        }
        if a_field.get("selecttype") == "2":
            if new_field_dict["field_externalfilename"].upper().find(".CSV") == -1:
                new_field_dict["field_externalfilename"] = (
                    new_field_dict["field_externalfilename"] + ".csv"
                )

        if "formshare_ontological_term" in survey_data_columns:
            survey_data_columns.remove("formshare_ontological_term")
        if "formshare_encrypted" in survey_data_columns:
            survey_data_columns.remove("formshare_encrypted")
        if "formshare_sensitive" in survey_data_columns:
            survey_data_columns.remove("formshare_sensitive")

        for a_column in survey_data_columns:
            if a_field.get(a_column) is not None:
                new_field_dict[a_column] = a_field.get(a_column)

        mapped_data = map_to_schema(DictField, new_field_dict)

        return mapped_data

    def store_tables(element, project, form, lookup):
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
                                    new_field_dict = create_new_field_dict(
                                        table, field, project, form
                                    )
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
                                new_field_dict = create_new_field_dict(
                                    table, field, project, form
                                )
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
    forms = db_session.query(Odkform).filter(Odkform.form_id == form_id).all()
    for a_form in forms:
        store_tables(element_lkp_tables, a_form.project_id, a_form.form_id, 1)
        store_tables(element_tables, a_form.project_id, a_form.form_id, 0)


def update_form(db_session, project, form, form_data):
    mapped_data = map_to_schema(Odkform, form_data)
    try:
        db_session.query(Odkform).filter(Odkform.project_id == project).filter(
            Odkform.form_id == form
        ).update(mapped_data)
        return True, ""
    except Exception as e:
        log.error(
            "Error {} while updating form {} in project {}".format(
                str(e), project, form
            )
        )
        raise MergeDataBaseError(str(e))


def internal_merge_into_repository(
    settings,
    user,
    project_id,
    project_code,
    a_form_id,
    a_form_directory,
    b_form_directory,
    b_create_xml_file,
    b_schema_name,
    odk_merge_string,
    b_hex_color,
    locale,
    discard_testing_data,
    survey_data_columns,
    task_id,
):
    log.info(
        "Merging process for form {} in project {} has started".format(
            a_form_id, project_id
        )
    )
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

    c_create_xml_file = os.path.join(
        odk_dir, *["forms", a_form_directory, "merging_files", "create.xml"]
    )

    c_insert_xml_file = os.path.join(
        odk_dir, *["forms", a_form_directory, "merging_files", "insert.xml"]
    )

    b_backup_directory = os.path.join(
        odk_dir, *["forms", b_form_directory, "repository_bks"]
    )
    if not os.path.exists(b_backup_directory):
        os.makedirs(b_backup_directory)

    b_backup_file = os.path.join(
        odk_dir, *["forms", b_form_directory, "repository_bks", b_schema_name + ".sql"]
    )

    a_schema_name = "FS_" + str(uuid.uuid4()).replace("-", "_")

    cnf_file = settings["mysql.cnf"]

    engine = get_engine(settings)
    session_factory = get_session_factory(engine)
    critical_part = False
    form_with_changes = []
    with transaction.manager:
        db_session = get_tm_session(session_factory, transaction.manager)
        configure_mappers()
        initialize_schema()

        # Block all forms using the old schema so they cannot accept any changes
        db_session.query(Odkform).filter(Odkform.form_schema == b_schema_name).update(
            {"form_blocked": 1}
        )
        update_form(db_session, project_id, a_form_id, {"form_blocked": 1})
        transaction.commit()
        time.sleep(5)  # Sleep for 5 seconds just to allow any pending updates to finish
        try:
            make_database_changes(
                settings,
                cnf_file,
                a_schema_name,
                b_schema_name,
                merge_create_file,
                merge_insert_file,
                merge_log_file,
                c_create_xml_file,
                b_create_xml_file,
                b_backup_file,
                a_form_directory,
                task_id,
                _,
            )
            # At this stage all changes were made to the new schema and C XML create file. Now we need to update
            # the FormShare forms with the new schema. This is a critical part. If something goes wrong
            # in between the critical parts then all the involved forms are broken and then technical team will need
            # to deal with them. A log indicating the involved forms are posted

            log.info("Updating related forms")
            send_task_status_to_form(settings, task_id, _("Updating related forms"))

            critical_part = True
            # Move all forms using the old schema to the new schema, replace their create file with C and unblock them
            res = (
                db_session.query(Odkform)
                .filter(Odkform.form_schema == b_schema_name)
                .all()
            )
            for a_form in res:
                form_with_changes.append(
                    {
                        "id": a_form.form_id,
                        "project_id": a_form.project_id,
                    }
                )

            db_session.query(Odkform).filter(
                Odkform.form_schema == b_schema_name
            ).update(
                {
                    "form_blocked": 0,
                    "form_createxmlfile": c_create_xml_file,
                    "form_insertxmlfile": c_insert_xml_file,
                    "form_hexcolor": b_hex_color,
                }
            )

            form_data = {
                "form_schema": b_schema_name,
                "form_blocked": 0,
                "form_createxmlfile": c_create_xml_file,
                "form_insertxmlfile": c_insert_xml_file,
                "form_hexcolor": b_hex_color,
                "form_hasdictionary": 1,
            }
            update_form(db_session, project_id, a_form_id, form_data)
            transaction.commit()
            if not discard_testing_data:
                log.info("Storing testing data")
                send_task_status_to_form(settings, task_id, _("Storing testing data"))
                assistant, project_of_assistant = get_one_assistant(
                    db_session, project_id, a_form_id
                )
                geo_point_variables = get_geopoint_variables(
                    db_session, project_id, a_form_id
                )
            log.info("Updating dictionary")
            send_task_status_to_form(settings, task_id, _("Updating dictionary"))
            update_dictionary_tables(
                db_session,
                a_form_id,
                c_create_xml_file,
                survey_data_columns,
            )
            transaction.commit()
            critical_part = False
        except Exception as e:
            if critical_part:
                status = "Critical error with merging"
            else:
                status = "Non Critical error with merging"
            email_from = settings.get("mail.from", None)
            email_to = settings.get("mail.error", None)
            error_dict = {"errors": form_with_changes}
            if critical_part:
                log.error("BEGIN CRITICAL MERGE ERROR")
                log.error(error_dict)
                log.error(odk_merge_string)
                log.error("END CRITICAL MERGE ERROR")
            send_async_email(
                settings,
                email_from,
                email_to,
                status,
                json.dumps(error_dict)
                + "\n\nError: {}\n\nTraceback: {}\n\nMerge string {}".format(
                    str(e), traceback.format_exc(), odk_merge_string
                ),
                None,
                locale,
            )
            log.error("Error while merging the form: {}".format(str(e)))
            db_session.query(Odkform).filter(
                Odkform.form_schema == b_schema_name
            ).update({"form_blocked": 0})
            update_form(db_session, project_id, a_form_id, {"form_blocked": 0})
            transaction.commit()
            raise MergeDataBaseError(str(e))
    # Delete the dataset index
    engine.dispose()
    delete_dataset_from_index(settings, project_id, a_form_id)
    if discard_testing_data:
        # Remove any test submissions if any
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
    else:
        unique_id = str(uuid.uuid4())
        temp_path = os.path.join(settings["repository.path"], *["tmp", unique_id])
        os.makedirs(temp_path)

        submissions_path = os.path.join(
            odk_dir, *["forms", a_form_directory, "submissions", "*.json"]
        )
        files = glob.glob(submissions_path)
        if files:
            for file in files:
                shutil.copy(file, temp_path)
            if assistant is not None and project_of_assistant is not None:
                internal_import_json_files(
                    user,
                    project_id,
                    a_form_id,
                    odk_dir,
                    a_form_directory,
                    a_schema_name,
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
            else:  # pragma: no cover
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
                    "The testing files for form {} of project {} are in {}. You can import them later on".format(
                        a_form_id, project_id, temp_path
                    ),
                    None,
                    locale,
                )
    log.info("Merging successful")


@celeryApp.task(bind=True, base=CeleryTask)
def merge_into_repository(
    self,
    settings,
    user,
    project_id,
    project_code,
    a_form_id,
    a_form_directory,
    b_form_directory,
    b_create_xml_file,
    b_schema_name,
    odk_merge_string,
    b_hex_color,
    locale,
    discard_testing_data,
    survey_data_columns,
    test_task_id=None,
):
    if test_task_id is None:
        task_id = merge_into_repository.request.id
    else:
        task_id = test_task_id
    try:
        internal_merge_into_repository(
            settings,
            user,
            project_id,
            project_code,
            a_form_id,
            a_form_directory,
            b_form_directory,
            b_create_xml_file,
            b_schema_name,
            odk_merge_string,
            b_hex_color,
            locale,
            discard_testing_data,
            survey_data_columns,
            task_id,
        )
    except Exception as e:
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "Merge repository error",
            "\n\nError: {}\n\nTraceback: {}\n\nMerge form {} in project {} of user {}".format(
                str(e), traceback.format_exc(), a_form_id, project_id, user
            ),
            None,
            locale,
        )
        raise MergeDataBaseError(str(e))
