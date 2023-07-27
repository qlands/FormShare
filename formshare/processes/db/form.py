import csv
import datetime
import glob
import json
import logging
import mimetypes
import os
import shutil
import uuid

from formshare.models import (
    map_from_schema,
    Odkform,
    User,
    Collingroup,
    Formgrpacces,
    map_to_schema,
    MediaFile,
    Formacces,
    Collaborator,
    Collgroup,
    Submission,
    Jsonlog,
    Project,
    Userproject,
    Jsonhistory,
    CaseLookUp,
    DictField,
)
from formshare.processes.color_hash import ColorHash
from formshare.processes.db.assistant import (
    get_project_from_assistant,
    get_assistant_data,
)
from formshare.processes.elasticsearch.repository_index import (
    get_dataset_stats_for_form,
)
from sqlalchemy.exc import IntegrityError

__all__ = [
    "get_form_details",
    "assistant_has_form",
    "get_assistant_forms",
    "get_form_directory",
    "get_form_xml_create_file",
    "get_form_xml_insert_file",
    "is_form_blocked",
    "add_new_form",
    "form_exists",
    "get_form_xml_file",
    "get_form_xls_file",
    "update_form",
    "get_form_data",
    "get_form_schema",
    "delete_form",
    "add_file_to_form",
    "get_form_files",
    "remove_file_from_form",
    "form_file_exists",
    "add_assistant_to_form",
    "get_form_assistants",
    "get_form_assistants_through_groups",
    "update_assistant_privileges",
    "remove_assistant_from_form",
    "add_group_to_form",
    "get_form_groups",
    "update_group_privileges",
    "remove_group_from_form",
    "get_project_forms",
    "get_number_of_submissions_in_database",
    "get_by_details",
    "get_form_geopoints",
    "get_number_of_submissions_by_assistant",
    "get_media_files",
    "set_form_status",
    "get_form_survey_file",
    "get_project_form_colors",
    "get_assistant_forms_for_cleaning",
    "update_form_directory",
    "get_last_clean_info",
    "get_last_clean_date_from_schema",
    "get_form_size",
    "collect_maps_for_schema",
    "get_create_xml_for_schema",
    "get_insert_xml_for_schema",
    "get_last_submission_date",
    "get_last_submission_date_from_schema",
    "get_form_directories_for_schema",
    "get_forms_for_schema",
    "get_project_for_schema",
    "get_last_fixed_date",
    "get_maintable_information",
    "get_case_lookup_fields",
    "add_case_lookup_field",
    "remove_case_lookup_field",
    "update_case_lookup_field_alias",
    "get_case_lookup_file",
    "generate_lookup_file",
    "get_field_details",
    "delete_case_lookup_table",
    "alias_exists",
    "form_has_subversion",
    "field_exists",
    "get_all_project_forms",
    "get_form_survey_columns",
]

log = logging.getLogger("formshare")


def field_exists(request, project, field_name):
    res = (
        request.dbsession.query(CaseLookUp)
        .filter(CaseLookUp.project_id == project)
        .filter(CaseLookUp.field_name == field_name)
        .count()
    )
    if res == 0:
        return False
    else:
        return True


def alias_exists(request, project, field_name, alias):
    res = (
        request.dbsession.query(CaseLookUp)
        .filter(CaseLookUp.project_id == project)
        .filter(CaseLookUp.field_name != field_name)
        .filter(CaseLookUp.field_as == alias)
        .count()
    )
    if res == 0:
        return False
    else:
        return True


def delete_case_lookup_table(request, project):
    """
    Deletes the case lookup table
    :param request: Pyramid request object
    :param project: Project ID
    :return:
    """
    try:
        request.dbsession.query(CaseLookUp).filter(
            CaseLookUp.project_id == project
        ).delete()
        request.dbsession.flush()
        return True
    except IntegrityError as e:
        log.error("Error {} while removing lookup table".format(str(e)))
        request.dbsession.rollback()
        return False
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while removing lookup table".format(str(e)))
        return False


def get_field_details(request, project, form, table, field):
    """
    This gets the details of a field from the database
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table: Table name
    :param field: Field name
    :return: Dict with the details of the field
    """
    res = (
        request.dbsession.query(DictField)
        .filter(DictField.project_id == project)
        .filter(DictField.form_id == form)
        .filter(DictField.table_name == table)
        .filter(DictField.field_name == field)
        .first()
    )
    res = map_from_schema(res)
    return res


def generate_lookup_file(request, project, schema, file_name, only_inactive):
    """
    Generates a temporary CSV file based on the case lookup field definition.
    :param request: Pyramid request object
    :param project: Project ID
    :param schema: Schema
    :param file_name: File to generate
    :param only_inactive: Just generate inactive cases
    :return: True or False
    """
    try:
        select_field = ["'list_caseselector' as list_name"]
        heading = ["list_name", "name", "label"]
        empty = ["list_caseselector", "empty", "empty"]

        res = (
            request.dbsession.query(CaseLookUp.field_name)
            .filter(CaseLookUp.project_id == project)
            .filter(CaseLookUp.field_as == "name")
            .filter(CaseLookUp.field_editable == 0)
            .first()
        )
        select_field.append(res[0] + " as name")

        res = (
            request.dbsession.query(CaseLookUp.field_name)
            .filter(CaseLookUp.project_id == project)
            .filter(CaseLookUp.field_as == "label")
            .filter(CaseLookUp.field_editable == 0)
            .first()
        )
        select_field.append(res[0] + " as label")
        label_field = res[0]

        fields = (
            request.dbsession.query(CaseLookUp)
            .filter(CaseLookUp.project_id == project)
            .filter(CaseLookUp.field_editable == 1)
            .all()
        )
        for a_field in fields:
            if a_field.field_name == a_field.field_as:
                select_field.append(a_field.field_name)
                heading.append(a_field.field_name)
                empty.append("empty")
            else:
                select_field.append(a_field.field_name + " as " + a_field.field_as)
                heading.append(a_field.field_as)
                empty.append("empty")

        outfile = open(file_name, "w")
        out_csv = csv.writer(outfile)
        out_csv.writerow(x for x in heading)

        sql = "SELECT count(surveyid) FROM {}.maintable".format(schema)
        res = request.dbsession.execute(sql).fetchone()
        if res[0] > 0:
            sql = (
                "SELECT " + ",".join(select_field) + " from {}.maintable".format(schema)
            )
            if only_inactive:
                sql = sql + " WHERE _active = 0"
            else:
                sql = sql + " WHERE _active = 1"
            sql = sql + " AND {} IS NOT NULL ORDER BY _submitted_date".format(
                label_field
            )
            cursor = request.dbsession.execute(sql)
            out_csv.writerows(cursor.fetchall())
        else:
            out_csv.writerow(x for x in empty)
        outfile.close()
        return True
    except Exception as e:
        log.error(
            "Error while generating case lookup CSV file for project {}. Error:{}".format(
                project, str(e)
            )
        )
        return False


def get_case_lookup_file(request, project, form):
    """
    Gets the case lookup file and the last generation date
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :return: case_file, datetime and type or None, None and None
    """
    res = (
        request.dbsession.query(
            Odkform.form_caseselectorfilename,
            Odkform.form_caseselectorlastgen,
            Odkform.form_casetype,
        )
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .filter(Odkform.form_case == 1)
        .filter(Odkform.form_casetype > 1)
        .first()
    )
    if res is not None:
        return res[0], res[1], res[2]
    return None, None, None


def update_case_lookup_field_alias(request, project, case_field, case_alias):
    """
    Updates the alias of a field
    :param request: Pyramid request object
    :param project: Project ID
    :param case_field: Case field
    :param case_alias: New alias
    :return: True or False
    """
    try:
        request.dbsession.query(CaseLookUp).filter(
            CaseLookUp.project_id == project
        ).filter(CaseLookUp.field_name == case_field).filter(
            CaseLookUp.field_editable == 1
        ).update(
            {"field_as": case_alias.lower()}
        )
        request.dbsession.flush()
        return True
    except IntegrityError as e:
        log.error("Error {} while adding a new lookup field".format(str(e)))
        request.dbsession.rollback()
        return False
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding a new lookup field".format(str(e)))
        return False


def remove_case_lookup_field(request, project, case_field):
    """
    Removes a field from the lookup table
    :param request: Pyramid request object
    :param project: Project ID
    :param case_field: Case field
    :return: True or False
    """
    try:
        request.dbsession.query(CaseLookUp).filter(
            CaseLookUp.project_id == project
        ).filter(CaseLookUp.field_name == case_field).filter(
            CaseLookUp.field_editable == 1
        ).delete()
        request.dbsession.flush()
        return True
    except IntegrityError as e:
        log.error("Error {} while removing lookup field".format(str(e)))
        request.dbsession.rollback()
        return False
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while removing lookup field".format(str(e)))
        return False


def add_case_lookup_field(request, project, case_field):
    new_field_dict = {
        "project_id": project,
        "field_name": case_field,
        "field_as": case_field,
        "field_editable": 1,
    }
    new_field = CaseLookUp(**new_field_dict)
    try:
        request.dbsession.add(new_field)
        request.dbsession.flush()
        return True
    except IntegrityError as e:
        log.error("Error {} while adding a new lookup field".format(str(e)))
        request.dbsession.rollback()
        return False
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding a new lookup field".format(str(e)))
        return False


def get_case_lookup_fields(request, project, case_id_field, case_label_field):
    """
    This function returns the current case fields. Creates the first two fields if empty
    :param request: Pyramid request object
    :param project: Project ID
    :param case_id_field: Field to identify cases
    :param case_label_field: Field to label cases
    :return:
    """
    res = (
        request.dbsession.query(CaseLookUp)
        .filter(CaseLookUp.project_id == project)
        .all()
    )
    if not res:
        name_field_dict = {
            "project_id": project,
            "field_name": case_id_field,
            "field_as": "name",
            "field_editable": 0,
        }
        name_field = CaseLookUp(**name_field_dict)
        label_field_dict = {
            "project_id": project,
            "field_name": case_label_field,
            "field_as": "label",
            "field_editable": 0,
        }
        label_field = CaseLookUp(**label_field_dict)
        try:
            request.dbsession.add(name_field)
            request.dbsession.add(label_field)
            request.dbsession.flush()
        except IntegrityError as e:
            log.error("Error {} while adding a new lookup field".format(str(e)))
            request.dbsession.rollback()
            return [], False
        except Exception as e:
            request.dbsession.rollback()
            log.error("Error {} while adding a new lookup field".format(str(e)))
            return [], False
        new_fields = [name_field_dict, label_field_dict]
        return new_fields, True
    return map_from_schema(res), False


def get_last_fixed_date(request, project, form):
    res = (
        request.dbsession.query(Jsonhistory.log_dtime)
        .filter(Jsonhistory.project_id == project)
        .filter(Jsonhistory.form_id == form)
        .filter(Jsonhistory.log_action == 0)
        .order_by(Jsonhistory.log_dtime.desc())
        .first()
    )
    if res is not None:
        return res.log_dtime
    else:
        return None


def collect_maps_for_schema(request, schema):
    """
    Collect all maps for a schema and place them in a temporary directory
    :param request: Pyramid request object
    :param schema: Schema
    :return: Temporary directory with map files
    """
    res = request.dbsession.query(Odkform).filter(Odkform.form_schema == schema).all()
    settings = request.registry.settings

    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    temp_path = os.path.join(settings["repository.path"], *paths)
    os.makedirs(temp_path)

    for a_form in res:
        paths = ["odk", "forms", a_form.form_directory, "submissions", "maps", "*.xml"]
        maps_path = os.path.join(settings["repository.path"], *paths)
        files = glob.glob(maps_path)
        if files:
            for aFile in files:
                shutil.copy(aFile, temp_path)
    return temp_path


def get_create_xml_for_schema(request, schema):
    """
    Returns the XML create file for the last form using a schema
    :param request: Pyramid request object
    :param schema: Schema
    :return: Path to XML Create file
    """
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.form_schema == schema)
        .order_by(Odkform.form_cdate.desc())
        .first()
    )
    return res.form_createxmlfile


def get_insert_xml_for_schema(request, schema):
    """
    Returns the XML insert file for the last form using a schema
    :param request: Pyramid request object
    :param schema: Schema
    :return: Path to XML Insert file
    """
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.form_schema == schema)
        .order_by(Odkform.form_cdate.desc())
        .first()
    )
    return res.form_insertxmlfile


def get_form_directories_for_schema(request, schema):
    forms = request.dbsession.query(Odkform).filter(Odkform.form_schema == schema).all()
    res = []
    for a_form in forms:
        res.append(a_form.form_directory)
    return res


def get_forms_for_schema(request, schema):
    forms = request.dbsession.query(Odkform).filter(Odkform.form_schema == schema).all()
    res = []
    for a_form in forms:
        res.append(a_form.form_id)
    return res


def get_project_for_schema(request, schema):
    return (
        request.dbsession.query(Odkform.project_id)
        .filter(Odkform.form_schema == schema)
        .first()[0]
    )


def _get_path_size(start_path="."):
    total_size = 0
    for dir_path, dir_names, file_names in os.walk(start_path):
        for f in file_names:
            fp = os.path.join(dir_path, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size


def get_form_size(request, project_id, form_id):
    repository_path = request.registry.settings["repository.path"]
    if not os.path.exists(repository_path):
        os.makedirs(repository_path)
    odk_dir = os.path.join(repository_path, *["odk"])
    form_directory = get_form_directory(request, project_id, form_id)
    path = os.path.join(odk_dir, *["forms", form_directory])
    return _get_path_size(path)


def get_project_code_from_id(request, user, project_id):
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Project.project_id == project_id)
        .filter(Userproject.access_type == 1)
        .first()
    )
    if res is not None:
        return res.project_code
    return None


def get_number_of_submissions(request, project_id, form_id):
    return get_dataset_stats_for_form(request.registry.settings, project_id, form_id)


def get_last_clean_info(request, project, form):
    schema = get_form_schema(request, project, form)
    if schema is not None:
        sql = "SELECT audit_date,audit_user from {}.audit_log ORDER BY audit_date DESC LIMIT 1".format(
            schema
        )
        res = request.dbsession.execute(sql).fetchone()
        if res is not None:
            return res[0], res[1]
        else:
            return None, None
    else:
        return None, None


def get_last_clean_date_from_schema(request, schema):
    if schema is not None:
        sql = "SELECT audit_date from {}.audit_log ORDER BY audit_date DESC LIMIT 1".format(
            schema
        )
        res = request.dbsession.execute(sql).fetchone()
        if res is not None:
            return res[0]
        else:
            return None
    else:
        return None


def get_last_submission_date(request, project, form):
    schema = get_form_schema(request, project, form)
    if schema is not None:
        sql = "SELECT _submitted_date from {}.maintable ORDER BY _submitted_date DESC LIMIT 1".format(
            schema
        )
        res = request.dbsession.execute(sql).fetchone()
        if res is not None:
            return res[0]
        else:
            return None
    else:
        return None


def get_last_submission_date_from_schema(request, schema):
    if schema is not None:
        sql = "SELECT _submitted_date from {}.maintable ORDER BY _submitted_date DESC LIMIT 1".format(
            schema
        )
        res = request.dbsession.execute(sql).fetchone()
        if res is not None:
            return res[0]
        else:
            return None
    else:
        return None


def get_maintable_information(request, project, form, submission_id):
    schema = get_form_schema(request, project, form)
    sql = "SELECT * from {}.maintable WHERE surveyid = '{}'".format(
        schema, submission_id
    )
    res = request.dbsession.execute(sql).fetchone()
    if res is None:
        return None
    dict_data = dict(res)
    json_data = json.dumps(dict_data, default=str)
    return json.loads(json_data)


def get_number_of_submissions_in_database(request, project, form):
    total = (
        request.dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.sameas.is_(None))
        .count()
    )

    schema = get_form_schema(request, project, form)
    if schema is not None:
        sql = "SELECT count(*) from {}.maintable".format(schema)
        res = request.dbsession.execute(sql).fetchone()
        in_db = res[0]
    else:
        in_db = 0

    in_db_from_logs = (
        request.dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .count()
    )
    in_error = (
        request.dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.status != 0, Jsonlog.status != 4)
        .count()
    )

    res = (
        request.dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.sameas.is_(None))
        .order_by(Submission.submission_dtime.desc())
        .first()
    )
    if res is not None:
        last = res.submission_dtime
        by = res.coll_id
        return total, last, in_db, in_db_from_logs, in_error, by
    else:
        return 0, None, in_db, in_db_from_logs, in_error, None


def get_number_of_submissions_by_assistant(
    request, project, form, assistant_project, assistant
):
    total = (
        request.dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.sameas.is_(None))
        .filter(Submission.enum_project == assistant_project)
        .filter(Submission.coll_id == assistant)
        .count()
    )

    in_db = (
        request.dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.submission_status == 0)
        .filter(Submission.sameas.is_(None))
        .filter(Submission.enum_project == assistant_project)
        .filter(Submission.coll_id == assistant)
        .count()
    )

    fixed = (
        request.dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.status == 0)
        .filter(Jsonlog.enum_project == assistant_project)
        .filter(Jsonlog.coll_id == assistant)
        .count()
    )

    in_db_from_logs = (
        request.dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.enum_project == assistant_project)
        .filter(Jsonlog.coll_id == assistant)
        .count()
    )

    in_error = (
        request.dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.status != 0, Jsonlog.status != 4)
        .filter(Jsonlog.enum_project == assistant_project)
        .filter(Jsonlog.coll_id == assistant)
        .count()
    )

    res = (
        request.dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.sameas.is_(None))
        .filter(Submission.enum_project == assistant_project)
        .filter(Submission.coll_id == assistant)
        .order_by(Submission.submission_dtime.desc())
        .first()
    )

    if res is not None:
        last = res.submission_dtime
    else:
        last = None

    return total, last, in_db + fixed, in_db_from_logs, in_error


def get_creator_data(request, user):
    res = request.dbsession.query(User).filter(User.user_id == user).first()
    return map_from_schema(res)


def get_form_data(request, project, form):
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if res is not None:
        return map_from_schema(res)
    else:
        return None


def get_project_form_colors(request, project):
    res = {}
    records = (
        request.dbsession.query(Odkform).filter(Odkform.project_id == project).all()
    )
    for record in records:
        res[record.form_id] = record.form_hexcolor
    return res


def form_has_subversion(request, user, project, form):
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.parent_project == project)
        .filter(Odkform.parent_form == form)
        .first()
    )
    if res is not None:
        return {
            "child_project": res.project_id,
            "child_form": res.form_id,
            "child_project_code": get_project_code_from_id(request, user, project),
            "child_data": get_form_data(request, res.project_id, res.form_id),
        }
    else:
        return None


def simple_form_has_subversion(request, project, form):
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.parent_project == project)
        .filter(Odkform.parent_form == form)
        .first()
    )
    if res is not None:
        return True
    else:
        return False


def form_has_parent(request, project, form):
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if res.parent_form is not None:
        return True
    else:
        return False


def get_form_details(request, user, project, form):
    result = get_form_data(request, project, form)
    if result is not None:
        result["pubby"] = get_creator_data(request, result["form_pubby"])
        if result["form_schema"] is None:
            submissions, last, by = get_number_of_submissions(
                request, project, result["form_id"]
            )
            result["submissions"] = submissions

            result["maximum"] = int(
                request.registry.settings.get("maximum.testing", "200")
            )
            if submissions >= int(
                request.registry.settings.get("maximum.testing", "200")
            ):
                result["maximum_reached"] = True
            else:
                result["maximum_reached"] = False

            result["last"] = last
            result["cleanedlast"] = None
            result["fixedlast"] = None
            result["lastindb"] = None
            result["cleanedby"] = "NA"
            result["by"] = by
            result["bydetails"] = get_by_details(request, user, project, by)
            result["indb"] = 0
            result["inlogs"] = 0
            result["inerror"] = 0
            result["has_sub_version"] = None
            if result["parent_form"] is not None:
                result["parent_form_data"] = get_form_data(
                    request, result["parent_project"], result["parent_form"]
                )
            else:
                result["parent_form_data"] = None
        else:
            (
                submissions,
                last,
                in_database,
                in_logs,
                in_error,
                by,
            ) = get_number_of_submissions_in_database(
                request, project, result["form_id"]
            )
            cleaned_last, cleaned_by = get_last_clean_info(request, project, form)
            last_submission_in_db = get_last_submission_date(request, project, form)
            fixed_last = get_last_fixed_date(request, project, form)
            result["submissions"] = submissions
            result["last"] = last
            result["lastindb"] = last_submission_in_db
            result["cleanedlast"] = cleaned_last
            result["fixedlast"] = fixed_last
            cleaned_by_details = get_by_details(request, user, project, cleaned_by)
            if not cleaned_by_details:
                result["cleanedby"] = cleaned_by
            else:
                result["cleanedby"] = cleaned_by_details["coll_name"]
            result["bydetails"] = get_by_details(request, user, project, by)
            result["indb"] = in_database
            result["inlogs"] = in_logs
            result["inerror"] = in_error
            result["has_sub_version"] = form_has_subversion(
                request, user, project, form
            )
            if result["has_sub_version"] is None:
                if result["parent_form"] is not None:
                    result["parent_form_data"] = get_form_data(
                        request, result["parent_project"], result["parent_form"]
                    )
                else:
                    result["parent_form_data"] = None
            else:
                if result["parent_form"] is not None:
                    result["parent_form_data"] = get_form_data(
                        request, result["parent_project"], result["parent_form"]
                    )
                else:
                    result["parent_form_data"] = None
        return result
    else:
        return None


def get_by_details(request, user, project, assistant):
    project_assistant = get_project_from_assistant(request, user, project, assistant)
    return get_assistant_data(request, project_assistant, assistant)


def get_project_forms(request, user, project):
    # Get all just parent forms in descending order
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .order_by(Odkform.form_cdate.desc())
        .all()
    )
    forms = map_from_schema(res)

    for form in forms:
        form["pubby"] = get_creator_data(request, form["form_pubby"])
        color = ColorHash(form["form_id"])
        if form["form_hexcolor"] is None:
            form["_xid_color"] = color.hex
        else:
            form["_xid_color"] = form["form_hexcolor"]
        if form["form_schema"] is None:
            submissions, last, by = get_number_of_submissions(
                request, form["project_id"], form["form_id"]
            )
            form["submissions"] = submissions
            form["maximum"] = int(
                request.registry.settings.get("maximum.testing", "200")
            )
            if submissions >= int(
                request.registry.settings.get("maximum.testing", "200")
            ):
                form["maximum_reached"] = True
            else:
                form["maximum_reached"] = False
            form["last"] = last
            form["by"] = by
            form["bydetails"] = get_by_details(request, user, form["project_id"], by)
            form["size"] = get_form_size(request, form["project_id"], form["form_id"])
            form["indb"] = 0
            form["inlogs"] = 0
            form["has_sub_version"] = None
            if form["parent_form"] is not None:
                form["parent_form_data"] = get_form_data(
                    request, form["parent_project"], form["parent_form"]
                )
            else:
                form["parent_form_data"] = None

        else:
            (
                submissions,
                last,
                in_database,
                in_logs,
                in_error,
                by,
            ) = get_number_of_submissions_in_database(
                request, form["project_id"], form["form_id"]
            )
            form["submissions"] = submissions
            form["maximum_reached"] = False
            form["maximum"] = 1
            form["last"] = last
            form["indb"] = in_database
            form["inlogs"] = in_logs
            form["inerror"] = in_error
            form["bydetails"] = get_by_details(request, user, form["project_id"], by)
            form["has_sub_version"] = form_has_subversion(
                request, user, form["project_id"], form["form_id"]
            )
            if form["has_sub_version"] is None:
                if form["parent_form"] is not None:
                    form["parent_form_data"] = get_form_data(
                        request, form["parent_project"], form["parent_form"]
                    )
                else:
                    form["parent_form_data"] = None
            else:
                if form["parent_form"] is not None:
                    form["parent_form_data"] = get_form_data(
                        request, form["parent_project"], form["parent_form"]
                    )
                else:
                    form["parent_form_data"] = None

    return forms


def get_all_project_forms(request, project_id):
    res = (
        request.dbsession.query(Odkform).filter(Odkform.project_id == project_id).all()
    )
    forms = map_from_schema(res)
    return forms


def get_assistant_forms(request, requested_project, assistant_project, assistant):
    # Get all the forms that the user can submit data to and are active
    assistant_forms = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == Formacces.form_project)
        .filter(Odkform.form_id == Formacces.form_id)
        .filter(Formacces.project_id == assistant_project)
        .filter(Formacces.coll_id == assistant)
        .filter(Formacces.form_project == requested_project)
        .filter(Formacces.coll_can_submit == 1)
        .filter(Odkform.form_accsub == 1)
        .all()
    )

    forms = map_from_schema(assistant_forms)

    # Select the groups that user belongs to
    groups = (
        request.dbsession.query(Collingroup)
        .filter(Collingroup.project_id == requested_project)
        .filter(Collingroup.enum_project == assistant_project)
        .filter(Collingroup.coll_id == assistant)
        .all()
    )
    for group in groups:
        res = (
            request.dbsession.query(Odkform)
            .filter(Odkform.project_id == Formgrpacces.form_project)
            .filter(Odkform.form_id == Formgrpacces.form_id)
            .filter(Formgrpacces.project_id == group.project_id)
            .filter(Formgrpacces.group_id == group.group_id)
            .filter(Formgrpacces.group_can_submit == 1)
            .filter(Odkform.form_accsub == 1)
            .all()
        )
        group_forms = map_from_schema(res)

        # Append only new forms accessible by the groups of the assistant
        for aForm in group_forms:
            found = False
            for cform in forms:
                if (
                    cform["project_id"] == aForm["project_id"]
                    and cform["form_id"] == aForm["form_id"]
                ):
                    found = True
                    break
            if not found:
                forms.append(aForm)

    return forms


def get_assistant_forms_for_cleaning(
    request, requested_project, assistant_project, assistant
):
    # Get all the forms that the user can submit data to and are active
    assistant_forms = (
        request.dbsession.query(
            Odkform,
            Formacces.coll_can_clean.label("can_clean"),
            Formacces.coll_can_submit.label("can_submit"),
        )
        .filter(Odkform.project_id == Formacces.form_project)
        .filter(Odkform.form_id == Formacces.form_id)
        .filter(Formacces.project_id == assistant_project)
        .filter(Formacces.coll_id == assistant)
        .filter(Formacces.form_project == requested_project)
        .filter(Odkform.form_accsub == 1)
        .all()
    )

    forms = map_from_schema(assistant_forms)

    # Select the groups that user belongs to
    groups = (
        request.dbsession.query(Collingroup)
        .filter(Collingroup.project_id == requested_project)
        .filter(Collingroup.enum_project == assistant_project)
        .filter(Collingroup.coll_id == assistant)
        .all()
    )

    for group in groups:
        res = (
            request.dbsession.query(
                Odkform,
                Formgrpacces.group_can_clean.label("can_clean"),
                Formgrpacces.group_can_submit.label("can_submit"),
            )
            .filter(Odkform.project_id == Formgrpacces.form_project)
            .filter(Odkform.form_id == Formgrpacces.form_id)
            .filter(Formgrpacces.project_id == group.project_id)
            .filter(Formgrpacces.group_id == group.group_id)
            .filter(Odkform.form_accsub == 1)
            .all()
        )
        group_forms = map_from_schema(res)

        # Append only new forms accessible by the groups of the assistant
        for aForm in group_forms:
            found = False
            for cform in forms:
                if (
                    cform["project_id"] == aForm["project_id"]
                    and cform["form_id"] == aForm["form_id"]
                ):
                    found = True
                    break
            if not found:
                forms.append(aForm)

    return forms


def assistant_has_form(request, user, project, form, assistant):
    assistant_project = get_project_from_assistant(request, user, project, assistant)
    forms = get_assistant_forms(request, project, assistant_project, assistant)
    found = False
    for cform in forms:
        if cform["project_id"] == project and cform["form_id"] == form:
            found = True
            break
    return found


def get_form_geopoints(request, project, form):
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if res is not None:
        if res.form_geopoint is not None:
            return res.form_geopoint.split(",")
    return []


def get_form_directory(request, project, form):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        return form_data.form_directory
    else:
        return None


def is_form_blocked(request, project, form):
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        return False
    else:
        return True


def get_form_xml_create_file(request, project, form):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        return form_data.form_createxmlfile
    else:
        return None


def get_form_xml_insert_file(request, project, form):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        return form_data.form_insertxmlfile
    else:
        return None


def get_form_xml_file(request, project, form):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        return form_data.form_xmlfile
    else:
        return None


def get_form_survey_file(request, project, form):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        return form_data.form_jsonfile
    else:
        return None


def get_form_survey_columns(request, project, form, filter_columns=True):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        if form_data.form_surveycolumns is not None:
            res = form_data.form_surveycolumns.split("|")
            if filter_columns:
                if "formshare_ontological_term" in res:
                    res.remove("formshare_ontological_term")
                if "formshare_encrypted" in res:
                    res.remove("formshare_encrypted")
                if "formshare_unique" in res:
                    res.remove("formshare_unique")
                if "formshare_sensitive" in res:
                    res.remove("formshare_sensitive")
            return res
    else:
        return []


def get_form_xls_file(request, project, form):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        return form_data.form_xlsfile
    else:
        return None


def get_form_schema(request, project, form):
    form_data = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if form_data is not None:
        return form_data.form_schema
    else:
        return None


def get_form_files(request, project, form):
    files = (
        request.dbsession.query(MediaFile)
        .filter(MediaFile.project_id == project)
        .filter(MediaFile.form_id == form)
        .all()
    )
    return map_from_schema(files)


def add_new_form(request, form_data):
    mapped_data = map_to_schema(Odkform, form_data)
    new_form = Odkform(**mapped_data)
    try:
        request.dbsession.add(new_form)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        request.dbsession.rollback()
        return False, str(e)
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding a new form".format(str(e)))
        return False, str(e)


def form_exists(request, project, form):
    res = (
        request.dbsession.query(Odkform)
        .filter(Odkform.form_id == form)
        .filter(Odkform.project_id == project)
        .first()
    )
    if res is None:
        return False
    else:
        return True


def update_form_color_by_database(request, database, hex_color):
    request.dbsession.query(Odkform).filter(Odkform.form_schema == database).update(
        {"form_hexcolor": hex_color}
    )


def delete_form_by_database(request, database):
    result = []
    log.warning("BEGIN BIG DATABASE DELETE")
    log.warning("Database: {}".format(database))
    res = request.dbsession.query(Odkform).filter(Odkform.form_schema == database).all()
    for a_form in res:
        log.warning(
            "Form ID: {} in project: {} will be deleted".format(
                a_form.form_id, a_form.project_id
            )
        )
        result.append(
            {
                "project_id": a_form.project_id,
                "form_id": a_form.form_id,
                "form_directory": a_form.form_directory,
            }
        )
    log.warning("END BIG DATABASE DELETE")
    request.dbsession.query(Odkform).filter(Odkform.form_schema == database).update(
        {"parent_project": None, "parent_form": None}
    )
    request.dbsession.query(Odkform).filter(Odkform.form_schema == database).delete()
    return result


def update_form_directory(request, project, form, directory):  # pragma: no cover
    # This function has no coverage because it should not happen. Cannot be covered by unitTest
    request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_id == form
    ).update({"form_directory": directory})


def update_form(request, project, form, form_data):
    _ = request.translate
    mapped_data = map_to_schema(Odkform, form_data)

    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
            Odkform.form_id == form
        ).update(mapped_data)

        if "form_hexcolor" in form_data.keys():
            this_form_schema = get_form_schema(request, project, form)
            if this_form_schema is not None:
                has_subversion = simple_form_has_subversion(request, project, form)
                has_parent = form_has_parent(request, project, form)
                if has_subversion or has_parent:
                    this_form_color = form_data["form_hexcolor"]
                    update_form_color_by_database(
                        request, this_form_schema, this_form_color
                    )
        try:
            request.dbsession.flush()
            return True, ""
        except IntegrityError as e:
            request.dbsession.rollback()
            return False, str(e)
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while updating form {} in project {}".format(
                    str(e), project, form
                )
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def delete_form(request, project, form):
    _ = request.translate

    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        this_form_schema = get_form_schema(request, project, form)
        if this_form_schema is not None:
            if form_has_parent(request, project, form):
                deleted = delete_form_by_database(request, this_form_schema)
                return True, deleted, ""
            else:
                form_directory = get_form_directory(request, project, form)
                request.dbsession.query(Odkform).filter(
                    Odkform.project_id == project
                ).filter(Odkform.form_id == form).delete()

        else:
            form_directory = get_form_directory(request, project, form)
            request.dbsession.query(Odkform).filter(
                Odkform.project_id == project
            ).filter(Odkform.form_id == form).delete()
        try:
            request.dbsession.flush()
            return (
                True,
                [
                    {
                        "project_id": project,
                        "form_id": form,
                        "form_directory": form_directory,
                    }
                ],
                "",
            )
        except IntegrityError as e:
            request.dbsession.rollback()
            return False, [], str(e)
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while deleting form {} in project {}".format(
                    str(e), project, form
                )
            )
            return False, [], str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def set_form_status(request, project, form, status):
    _ = request.translate

    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
            Odkform.form_id == form
        ).update({"form_accsub": status})
        try:
            request.dbsession.flush()
            return True, ""
        except IntegrityError as e:
            request.dbsession.rollback()
            return False, str(e)
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while updating status of form {} in project {}".format(
                    str(e), project, form
                )
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def get_media_files(request, project, form):
    res = (
        request.dbsession.query(MediaFile)
        .filter(MediaFile.project_id == project)
        .filter(MediaFile.form_id == form)
        .all()
    )
    return res


def add_file_to_form(request, project, form, file_name, overwrite=False, md5sum=None):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        res = (
            request.dbsession.query(MediaFile)
            .filter(MediaFile.project_id == project)
            .filter(MediaFile.form_id == form)
            .filter(MediaFile.file_name == file_name)
            .first()
        )
        if res is None:
            new_file_id = str(uuid.uuid4())
            content_type, content_enc = mimetypes.guess_type(file_name)
            if content_type is None:
                content_type = "application/binary"
            new_file = MediaFile(
                file_id=new_file_id,
                project_id=project,
                form_id=form,
                file_name=file_name,
                file_udate=datetime.datetime.now(),
                file_md5=md5sum,
                file_mimetype=content_type,
            )
            try:
                request.dbsession.add(new_file)
                request.dbsession.flush()
            except Exception as e:
                request.dbsession.rollback()
                log.error(
                    "Error {} while adding file {} in "
                    "form {} of project {} ".format(str(e), file_name, form, project)
                )
                return False, str(e)
            return True, new_file_id
        else:
            if not overwrite:
                return False, _("The file {} already exist").format(file_name)
            else:
                try:
                    request.dbsession.query(MediaFile).filter(
                        MediaFile.project_id == project
                    ).filter(MediaFile.form_id == form).filter(
                        MediaFile.file_name == file_name
                    ).update(
                        {"file_md5": md5sum}
                    )
                    request.dbsession.flush()
                except Exception as e:
                    request.dbsession.rollback()
                    log.error(
                        "Error {} while adding file {} in form {} of project {} ".format(
                            str(e), file_name, form, project
                        )
                    )
                    return False, str(e)
                return True, ""
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def remove_file_from_form(request, project, form, file_name):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        try:
            request.dbsession.query(MediaFile).filter(
                MediaFile.project_id == project
            ).filter(MediaFile.form_id == form).filter(
                MediaFile.file_name == file_name
            ).delete()
            request.dbsession.flush()
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while deleting file {} in form {} of project {} ".format(
                    str(e), file_name, form, project
                )
            )
            return False, str(e)
        return True, ""
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def form_file_exists(request, project, form, file_name):
    res = (
        request.dbsession.query(MediaFile)
        .filter(MediaFile.project_id == project)
        .filter(MediaFile.form_id == form)
        .filter(MediaFile.file_name == file_name)
        .first()
    )
    if res is not None:
        return True
    else:
        return False


def add_assistant_to_form(request, project, form, privilege_data):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        try:
            privilege_data["access_date"] = datetime.datetime.now()
            privilege_data["form_project"] = project
            privilege_data["form_id"] = form
            mapped_data = map_to_schema(Formacces, privilege_data)
            new_access = Formacces(**mapped_data)
            request.dbsession.add(new_access)
            request.dbsession.flush()
            return True, ""
        except IntegrityError as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while adding access to assistant {} of "
                "project {} to form {} in project {}".format(
                    str(e),
                    privilege_data["coll_id"],
                    privilege_data["project_id"],
                    project,
                    form,
                )
            )
            return False, "The assistant already exists in this form"
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while adding access to assistant {} of "
                "project {} to form {} in project {}".format(
                    str(e),
                    privilege_data["coll_id"],
                    privilege_data["project_id"],
                    project,
                    form,
                )
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def get_form_assistants(request, project, form):
    res = (
        request.dbsession.query(Collaborator, Formacces)
        .filter(Collaborator.project_id == Formacces.project_id)
        .filter(Collaborator.coll_id == Formacces.coll_id)
        .filter(Formacces.form_project == project)
        .filter(Formacces.form_id == form)
        .all()
    )
    mapped_data = map_from_schema(res)
    return mapped_data


def get_form_assistants_through_groups(request, project, form):
    res = (
        request.dbsession.query(Collaborator)
        .distinct(Collaborator.coll_id)
        .filter(Formgrpacces.project_id == Collingroup.project_id)
        .filter(Formgrpacces.group_id == Collingroup.group_id)
        .filter(Collingroup.enum_project == Collaborator.project_id)
        .filter(Collingroup.coll_id == Collaborator.coll_id)
        .filter(Formgrpacces.form_project == project)
        .filter(Formgrpacces.form_id == form)
        .all()
    )
    mapped_data = map_from_schema(res)
    return mapped_data


def update_assistant_privileges(
    request, project, form, from_project, assistant, privilege_data
):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        try:
            mapped_data = map_to_schema(Formacces, privilege_data)
            request.dbsession.query(Formacces).filter(
                Formacces.project_id == from_project
            ).filter(Formacces.coll_id == assistant).filter(
                Formacces.form_project == project
            ).filter(
                Formacces.form_id == form
            ).update(
                mapped_data
            )
            request.dbsession.flush()
            return True, ""
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while updating access to assistant {} of "
                "project {} to form {} in project {}".format(
                    str(e), assistant, from_project, project, form
                )
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def remove_assistant_from_form(request, project, form, from_project, assistant):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        try:
            request.dbsession.query(Formacces).filter(
                Formacces.project_id == from_project
            ).filter(Formacces.coll_id == assistant).filter(
                Formacces.form_project == project
            ).filter(
                Formacces.form_id == form
            ).delete()
            request.dbsession.flush()
            return True, ""
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while removing assistant {} of "
                "project {} from form {} in project {}".format(
                    str(e), assistant, from_project, project, form
                )
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def add_group_to_form(request, project, form, group, can_submit, can_clean):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        try:
            new_access = Formgrpacces(
                project_id=project,
                group_id=group,
                form_project=project,
                form_id=form,
                group_can_submit=can_submit,
                group_can_clean=can_clean,
                access_date=datetime.datetime.now(),
            )
            request.dbsession.add(new_access)
            request.dbsession.flush()
            return True, ""
        except IntegrityError as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while adding access to group {} of "
                "project {} to form {}".format(str(e), group, project, form)
            )
            return False, "The group already exists in this form"
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while adding access to group {} of "
                "project {} to form {}".format(str(e), group, project, form)
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def get_form_groups(request, project, form):
    res = (
        request.dbsession.query(Collgroup, Formgrpacces)
        .filter(Collgroup.project_id == Formgrpacces.project_id)
        .filter(Collgroup.group_id == Formgrpacces.group_id)
        .filter(Formgrpacces.form_project == project)
        .filter(Formgrpacces.form_id == form)
        .all()
    )
    mapped_data = map_from_schema(res)
    return mapped_data


def update_group_privileges(request, project, form, group, can_submit, can_clean):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        try:
            request.dbsession.query(Formgrpacces).filter(
                Formgrpacces.project_id == project
            ).filter(Formgrpacces.group_id == group).filter(
                Formgrpacces.form_project == project
            ).filter(
                Formgrpacces.form_id == form
            ).update(
                {"group_can_submit": can_submit, "group_can_clean": can_clean}
            )
            request.dbsession.flush()
            return True, ""
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while updating access to group {} of "
                "to form {} in project {}".format(str(e), group, project, form)
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")


def remove_group_from_form(request, project, form, group):
    _ = request.translate
    blocked = (
        request.dbsession.query(Odkform.form_blocked)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .one()
    )
    if blocked[0] == 0:
        try:
            request.dbsession.query(Formgrpacces).filter(
                Formgrpacces.project_id == project
            ).filter(Formgrpacces.group_id == group).filter(
                Formgrpacces.form_project == project
            ).filter(
                Formgrpacces.form_id == form
            ).delete()
            request.dbsession.flush()
            return True, ""
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while removing access to group {} of "
                "to form {} in project {}".format(str(e), group, project, form)
            )
            return False, str(e)
    else:
        return False, _("This form is blocked and cannot be changed at the moment.")
