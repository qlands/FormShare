import datetime
import glob
import io
import json
import logging
import mimetypes
import os
import re
import shutil
import traceback
import uuid
import zipfile
from hashlib import md5
from subprocess import Popen, PIPE
from uuid import uuid4

import formshare.plugins as plugins
from bs4 import BeautifulSoup
from formshare.processes.color_hash import ColorHash
from formshare.processes.db import (
    assistant_has_form,
    get_assistant_forms,
    get_project_id_from_name,
    add_new_form,
    form_exists,
    get_form_directory,
    update_form_directory,
    get_form_xml_file,
    get_form_survey_file,
    update_form,
    get_form_data,
    get_form_schema,
    get_submission_data,
    add_submission,
    add_json_log,
    update_json_status,
    add_json_history,
    form_file_exists,
    get_project_from_assistant,
    get_form_files,
    get_project_code_from_id,
    get_form_geopoints,
    get_media_files,
    add_file_to_form,
    add_submission_same_as,
    get_case_lookup_file,
    get_case_schema,
    get_last_clean_date_from_schema,
    get_last_submission_date_from_schema,
    generate_lookup_file,
    get_case_form,
    get_field_details,
    get_assistant_password,
    project_has_crowdsourcing,
    get_all_project_forms,
)
from formshare.processes.elasticsearch.record_index import (
    add_record,
)
from formshare.processes.elasticsearch.repository_index import (
    add_dataset,
    get_dataset_stats_for_form,
)
from formshare.processes.email.send_email import send_error_to_technical_team
from formshare.processes.odk.processes import update_form_repository_info
from formshare.processes.storage import (
    get_stream,
    response_stream,
    store_file,
    delete_stream,
)
from formshare.products.fs1import.fs1import import formshare_one_import_json
from formshare.products.repository import create_database_repository
from formshare.products.xmlimport.xmlimport import xml_import
from lxml import etree
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import FileResponse
from pyramid.response import Response
from pyxform import xls2xform
from pyxform.errors import PyXFormError
from pyxform.xls2json import parse_file_to_json

log = logging.getLogger("formshare")

__all__ = [
    "generate_form_list",
    "generate_manifest",
    "get_form_list",
    "get_manifest",
    "get_xml_form",
    "get_media_file",
    "get_submission_file",
    "move_media_files",
    "convert_xml_to_json",
    "store_submission",
    "store_json_submission",
    "get_html_from_diff",
    "generate_diff",
    "store_new_version",
    "restore_from_revision",
    "push_revision",
    "upload_odk_form",
    "retrieve_form_file",
    "get_odk_path",
    "store_file_in_directory",
    "update_odk_form",
    "import_external_data",
    "store_json_file",
    "check_jxform_file",
    "get_missing_support_files",
    "create_repository",
    "merge_versions",
    "get_fields_from_table_in_file",
]

_GPS_types = [
    "add location prompt",
    "geopoint",
    "start-geopoint",
    "gps",
    "location",
    "q geopoint",
    "q location",
]


def report_critical_error(
    request, user, project, form, error_code, message
):  # pragma: no cover
    send_error_to_technical_team(
        request,
        "Error while creating the repository for form {} in "
        "project {}. \nURL:{} \nAccount: {}\nError: {}\nMessage: {}\n".format(
            form, project, request.url, user, error_code, message
        ),
    )


def get_fields_from_table_in_file(create_file, table_name):
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='" + table_name + "']")
    result = []
    if table is not None:
        for field in table.getchildren():
            if field.tag == "field":
                desc = field.get("desc")
                if desc == "" or desc == "Without label":
                    desc = field.get("name") + " - Without description"
                data = {
                    "name": field.get("name"),
                    "desc": desc,
                    "type": field.get("type"),
                    "xmlcode": field.get("xmlcode"),
                    "size": field.get("size"),
                    "odktype": field.get("odktype"),
                    "selecttype": field.get("selecttype", "0"),
                    "externalfilename": field.get("externalfilename", ""),
                    "decsize": field.get("decsize"),
                    "sensitive": field.get("sensitive"),
                    "protection": field.get("protection", "None"),
                    "key": field.get("key", "false"),
                    "rlookup": field.get("rlookup", "false"),
                    "rtable": field.get("rtable", "None"),
                    "rfield": field.get("rfield", "None"),
                }
                result.append(data)
            else:
                break
    return result


def get_odk_path(request):
    repository_path = request.registry.settings["repository.path"]
    if not os.path.exists(repository_path):
        os.makedirs(repository_path)
    return os.path.join(repository_path, *["odk"])


def store_file_in_directory(request, project, form, file_name, directory):
    if form_file_exists(request, project, form, file_name):
        bucket_id = project + form
        bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
        stream = get_stream(request, bucket_id, file_name)
        if stream is not None:
            target_file = os.path.join(directory, *[file_name])
            file = open(target_file, "wb")
            file.write(stream.read())
            file.close()


def retrieve_form_file_stream(request, project, form, file_name):
    bucket_id = project + form
    bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
    stream = get_stream(request, bucket_id, file_name)
    return stream


def retrieve_form_file(request, project, form, file_name):
    """
    Gets a resource file for ODK collect from the file storage or the a generated case lookup file
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param file_name: File name
    :return: A response Object for the file
    """
    if form_file_exists(request, project, form, file_name):
        stream = retrieve_form_file_stream(request, project, form, file_name)
        if stream is not None:
            response = Response()
            return response_stream(stream, file_name, response)
        else:
            raise HTTPNotFound
    else:
        raise HTTPNotFound


def get_missing_support_files(request, project, form, required_files, form_files):
    missing_files = []
    current_form_files = []
    for form_file in form_files:
        stream = retrieve_form_file_stream(
            request, project, form, form_file["file_name"]
        )
        if stream is not None:
            try:
                zip_file = zipfile.ZipFile(io.BytesIO(stream.read()))
                if form_file not in zip_file.namelist():
                    current_form_files.append(form_file["file_name"])
            except Exception as e:
                log.info(str(e))
                if form_file not in required_files:
                    current_form_files.append(form_file["file_name"])
    for required_file in required_files:
        if required_file not in current_form_files:
            missing_files.append(required_file)

    return missing_files


def get_geopoint_variables_from_json(json_dict, parent_array, variables):
    if json_dict["type"] == "survey" or json_dict["type"] == "group":
        if json_dict["type"] == "group":
            parent_array.append(json_dict["name"])
        for child in json_dict["children"]:
            get_geopoint_variables_from_json(child, parent_array, variables)
        if json_dict["type"] == "group":
            parent_array.pop()
    else:
        if json_dict["type"] in _GPS_types:
            form_geo_point = "/".join(parent_array) + "/" + json_dict["name"]
            if form_geo_point[0] == "/":
                form_geo_point = form_geo_point[1:]
            variables.append(form_geo_point)


def import_external_data(
    request,
    user,
    project,
    form,
    odk_dir,
    form_directory,
    schema,
    assistant,
    import_type,
    ignore_xform,
    form_post_data,
):
    input_file_name = request.POST["file"].filename
    if os.path.isabs(input_file_name):
        input_file_name = os.path.basename(input_file_name)
    slash_index = input_file_name.find("\\")
    if slash_index >= 0:
        input_file_name = input_file_name[slash_index + 1 :]
    input_file_name = input_file_name.lower()

    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    temp_dir = os.path.join(odk_dir, *paths)
    os.makedirs(temp_dir)

    input_file = request.POST["file"].file

    paths = ["tmp", uid, input_file_name]
    file_name = os.path.join(odk_dir, *paths)

    input_file.seek(0)
    with open(file_name, "wb") as permanent_file:
        shutil.copyfileobj(input_file, permanent_file)

    input_file.close()
    if input_file_name[-3:] == "zip":
        if zipfile.is_zipfile(file_name):
            with zipfile.ZipFile(file_name, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
        else:
            return False, "Invalid Zip file", None
    else:
        if import_type == 2:
            return False, "The import file must be Zip", None

    project_code = get_project_code_from_id(request, user, project)
    geopoint_variables = get_form_geopoints(request, project, form)
    project_of_assistant = get_project_from_assistant(request, user, project, assistant)

    if import_type == 1:
        # Call the background Celery task
        formshare_one_import_json(
            request,
            user,
            project,
            form,
            odk_dir,
            form_directory,
            schema,
            assistant,
            temp_dir,
            project_code,
            geopoint_variables,
            project_of_assistant,
            ignore_xform,
        )
        next_page = request.route_url(
            "form_details",
            userid=user,
            projcode=project_code,
            formid=form,
            _query={"tab": "task", "product": "fs1import"},
            _anchor="products_and_tasks",
        )
    if import_type == 2:
        assistant_password = get_assistant_password(
            request, user, project_of_assistant, assistant
        )
        xml_import(
            request,
            user,
            project,
            project_code,
            form,
            assistant,
            assistant_password,
            temp_dir,
        )
        next_page = request.route_url(
            "form_details",
            userid=user,
            projcode=project_code,
            formid=form,
            _query={"tab": "task", "product": "xmlimport"},
            _anchor="products_and_tasks",
        )

    if import_type > 2:
        # We call connected plugins to see if there is other ways to import
        next_page = None
        for a_plugin in plugins.PluginImplementations(plugins.IImportExternalData):
            next_page = a_plugin.import_external_data(
                request,
                user,
                project,
                form,
                odk_dir,
                form_directory,
                schema,
                assistant,
                temp_dir,
                project_code,
                geopoint_variables,
                project_of_assistant,
                import_type,
                form_post_data,
                ignore_xform,
            )
            break

    return True, "", next_page


def check_jxform_file(
    request,
    json_file,
    create_xml_file,
    insert_xml_file,
    primary_key,
    external_files=None,
    get_languages=False,
):
    if external_files is None:
        external_files = []
    _ = request.translate
    jxform_to_mysql = os.path.join(
        request.registry.settings["odktools.path"], *["JXFormToMysql", "jxformtomysql"]
    )
    args = [
        jxform_to_mysql,
        "-j " + json_file,
        "-C " + create_xml_file,
        "-I " + insert_xml_file,
        "-t maintable",
        "-v " + primary_key,
        "-e " + os.path.join(os.path.dirname(json_file), *["tmp"]),
        "-o m",
        "-K",
    ]
    if get_languages:
        args.append("-L")
    for a_file in external_files:
        args.append(a_file)
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()

    log.info(" ".join(args))

    if p.returncode == 0:
        try:
            if not get_languages:
                root = etree.fromstring(stdout)
                files_array = []
                missing_files = root.findall(".//missingFile")
                for a_file in missing_files:
                    files_array.append(a_file.get("fileName"))
                if len(files_array) > 0:
                    return 0, ",".join(files_array)
                else:
                    return 0, ""
            else:
                root = etree.fromstring(stdout)
                language_array = []
                languages = root.findall(".//language")
                if languages:
                    for a_language in languages:
                        lng_code = a_language.get("code", "")
                        if lng_code != "":
                            if len(lng_code) > 2:
                                lng_code = ""
                        language_array.append(
                            {
                                "code": lng_code,
                                "name": a_language.get("name")
                                or a_language.get("description"),
                            }
                        )
                return 0, language_array

        except Exception as e:
            log.info(
                "Checking JXForm returned 0 with no addition messages: {}".format(
                    str(e)
                )
            )
            return 0, ""
    else:
        if p.returncode == 10:
            return (
                10,
                _("The primary key variable does not exist or is inside a repeat"),
            )
        if p.returncode == 19:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            duplicated_tables = root.findall(".//duplicatedTable")
            message = (
                _("FormShare thoroughly checks your ODK for inconsistencies.") + "\n"
            )
            message = (
                message
                + _(
                    "The following variables are duplicated within repeats or outside repeats "
                    "in the ODK you just submitted:"
                )
                + "\n"
            )
            if duplicated_tables:
                for a_table in duplicated_tables:
                    table_name = a_table.get("tableName")
                    if table_name == "maintable":
                        table_name = _("Outside any repeat")
                    message = (
                        message + "\t" + _("In repeat: {}").format(table_name) + ": \n"
                    )
                    duplicated_fields = a_table.findall(".//duplicatedField")
                    if duplicated_fields:
                        for a_field in duplicated_fields:
                            field_name = a_field.get("fieldName")
                            message = (
                                message
                                + "\t\t"
                                + _("Variable: {}").format(field_name)
                                + "\n"
                            )
                message = (
                    message
                    + "\n"
                    + _(
                        "Please note that FormShare only allows basic Latin letters, digits 0-9, dollar and underscore "
                        "in repeat, group and variable names."
                    )
                )
            return 19, message
        if p.returncode == 20:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            invalid_names = root.findall(".//invalidName")
            message = (
                _("FormShare thoroughly checks your ODK for inconsistencies.") + "\n"
            )
            message = message + _("The following variables have invalid names:") + "\n"
            if invalid_names:
                for a_name in invalid_names:
                    variable_name = a_name.get("name")
                    message = message + "\t" + variable_name + " \n"

                message = message + "\n" + _("Please change those names and try again.")
            return 20, message
        if p.returncode == 21:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            duplicated_tables = root.findall(".//table")
            message = (
                _("FormShare thoroughly checks your ODK for inconsistencies.") + "\n"
            )
            message = message + _("The following choice lists are identical:") + "\n"
            if duplicated_tables:
                for a_table in duplicated_tables:
                    choice_name = a_table.get("name")
                    same_array = []
                    duplicated_names = a_table.findall(".//duplicate")
                    if duplicated_names:
                        for a_name in duplicated_names:
                            same_array.append(a_name.get("name"))
                    message = (
                        message
                        + "\t"
                        + choice_name
                        + _(" with the following duplicates: ")
                        + ", ".join(same_array)
                        + " \n"
                    )

                message = (
                    message
                    + "\n"
                    + _("Please remove the duplicated choices and try again.")
                )
            return 21, message

        if p.returncode == 25:
            message = _(
                "This ODK form mixes coded and not coded languages. "
                "For example label::English (en) and label::Español. "
                "You need to code all the labels that are marked for translation."
            )
            return 25, message

        if p.returncode == 17:
            message = _(
                "The variable to control duplicate submissions has an invalid type. "
                "E.g., the variable cannot be note, picture, video, sound, select_multiple, or geospatial. "
                "It cannot be instanceID. The most appropriate types are text, datetime, barcode, calculate, "
                "select_one, or integer"
            )
            return 17, message

        if p.returncode == 24:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            tables_with_name_error = root.findall(".//table")
            message = (
                _("FormShare needs you to shorten the name of some of your tables.")
                + "\n"
            )
            message = (
                message
                + _("The following tables have a name longer than 64 characters:")
                + "\n"
            )
            if tables_with_name_error:
                for a_table in tables_with_name_error:
                    table_name = a_table.get("name")
                    table_msel = a_table.get("msel")
                    if table_msel == "false":
                        message = message + "\t" + table_name + "\n"
                    else:
                        parts = table_name.split("_msel_")
                        message = (
                            message
                            + "\t"
                            + parts[0]
                            + " with select "
                            + parts[1]
                            + "\n"
                        )
                message = (
                    message
                    + "\n"
                    + _(
                        "Please shorten the name of the tables and/or the selects and try again."
                    )
                )
            return 24, message

        if (
            p.returncode == 18
        ):  # pragma: no cover . This only happens with old versions of PyXForm
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            duplicated_tables = root.findall(".//duplicatedItem")
            message = (
                _("FormShare thoroughly checks your ODK for inconsistencies.") + "\n"
            )
            message = (
                message
                + _(
                    "The following repeats are duplicated in the ODK you just submitted:"
                )
                + "\n"
            )
            if duplicated_tables:
                for a_table in duplicated_tables:
                    table_name = a_table.get("tableName")
                    message = message + "\t" + _("Repeat: {}").format(table_name) + "\n"
                message = (
                    message
                    + "\n"
                    + _(
                        "Please note that FormShare only allows basic Latin letters, digits 0-9, dollar and underscore "
                        "in repeat, group and variable names."
                    )
                )
            return 18, message
        if p.returncode == 14:
            message = (
                "The following CSV files have invalid characters in column headers. "
                'For example, like extra spaces". '
                "Only _ is allowed : \n"
            )
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = (
                        message + "\t" + os.path.basename(a_file.get("name", "")) + "\n"
                    )
            return 14, message
        if p.returncode == 15:
            message = "The following files have an invalid structure: \n"
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 15, message
        if p.returncode == 9:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            duplicated_items = root.findall(".//duplicatedItem")
            message = (
                _("FormShare thoroughly checks your ODK for inconsistencies.") + "\n"
            )
            message = (
                message
                + _(
                    "The following options are duplicated in the ODK you just submitted:"
                )
                + "\n"
            )
            if duplicated_items:
                for a_item in duplicated_items:
                    variable_name = a_item.get("variableName")
                    duplicated_option = a_item.get("duplicatedValue")
                    message = (
                        message
                        + "\t"
                        + _("Option {} in variable {}").format(
                            duplicated_option, variable_name
                        )
                        + "\n"
                    )
            return 9, message

        if p.returncode == 7:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            return (
                7,
                _(
                    "Malformed language in your ODK. Labels must be translated in this way: label::Language (Language_code). "
                    "For example, label::English (en), or label::English-Australia (es-au), or label::Gikuyu (kik)"
                ),
            )

        if p.returncode == 8:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            return (
                8,
                _(
                    "You have choice lists with names but not labels. "
                    "Did you missed the :: between label and language? "
                    "Like label:English (en)"
                ),
            )
        if p.returncode == 26:
            message = "The following GeoJSON file cannot be opened: \n"
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 26, message
        if p.returncode == 27:
            message = "The following GeoJSON file is not a FeatureCollection: \n"
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 27, message
        if p.returncode == 28:
            message = "The following GeoJSON file does not have features: \n"
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 28, message
        if p.returncode == 29:
            message = "The following GeoJSON file does not have properties: \n"
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 29, message
        if p.returncode == 30:
            message = (
                "The following GeoJSON file does not have the id or title columns: \n"
            )
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 30, message
        if p.returncode == 31:
            message = "The following GeoJSON file has features without geometry: \n"
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 31, message
        if p.returncode == 32:
            message = "The following GeoJSON file has features that are not point: \n"
            root = etree.fromstring(stdout)
            files_with_problems = root.findall(".//file")
            if files_with_problems:
                for a_file in files_with_problems:
                    message = message + "\t" + a_file.get("name", "") + "\n"
            return 32, message
        if p.returncode == 2:
            log.error(
                ". Error: "
                + str(p.returncode)
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            message = (
                "\n"
                + _(
                    "FormShare manages your data in a better way but by doing so it has more restrictions."
                )
                + "\n"
            )
            message = (
                message + _("The following tables have more than 60 selects: ") + "\n"
            )
            root = etree.fromstring(stdout)
            tables_with_errors = root.findall(".//table")
            for a_table in tables_with_errors:
                table_name = a_table.get("name")
                num_selects = a_table.get("selects")
                message = (
                    message + table_name + _(" with ") + num_selects + _(" selects")
                )
            message = message + "\n\n"
            message = (
                message
                + _("Some information on this restriction and how to correct it:")
                + "\n\n"
            )
            message = (
                message
                + _(
                    "We tend to organize our ODK forms in sections with questions around a topic. "
                    'For example: "livestock inputs" or "crops sales".'
                )
                + "\n\n"
            )
            message = (
                message
                + _(
                    'These sections have type = "begin/end group". We also organize questions that '
                    'must be repeated in sections with type = "begin/end repeat."'
                )
                + "\n\n"
            )
            message = (
                message
                + _(
                    "FormShare stores repeats as separate tables (like different Excel sheets) "
                    "however groups are not stored as repeats. FormShare stores all items "
                    "(questions, notes, calculations, etc.) outside repeats into a table called "
                    '"maintable". Thus "maintable" usually end up with several items and if '
                    'your ODK form has many selects, then the "maintable" could potentially '
                    "have more than 60 selects. FormShare can only handle 60 selects per table."
                )
                + "\n\n"
            )
            message = (
                message
                + _(
                    "You can bypass this restriction by creating groups of items inside repeats "
                    "BUT WITH repeat_count = 1. A repeat with repeat_count = 1 will behave "
                    "in the same way as a group, but FormShare will create a new table for it "
                    "to store all its items. Eventually if you export the data to Excel your "
                    "items will be organized in different sheets each representing a table."
                )
                + "\n\n"
            )
            message = message + _(
                "Please edit your ODK XLSX/XLS file, group several items inside repeats with "
                "repeat_count = 1 and try to upload the form again."
            )
            return 2, message

        log.error(
            ". Error: "
            + "-"
            + stderr.decode()
            + " while checking PyXForm. Command line: "
            + " ".join(args)
        )
        return p.returncode, stderr.decode()


def upload_odk_form(
    request,
    project_id,
    user_id,
    odk_dir,
    form_data,
    primary_key,
    for_merging=False,
    project_case=0,
    form_casetype=None,
    form_caselabel=None,
    form_caseselector=None,
    form_casedatetime=None,
):
    _ = request.translate
    uid = str(uuid.uuid4())
    form_directory = uid
    paths = ["tmp", uid]
    os.makedirs(os.path.join(odk_dir, *paths))

    try:
        input_file = request.POST["xlsx"].file
        input_file_name = request.POST["xlsx"].filename.lower()
        if os.path.isabs(input_file_name):
            input_file_name = os.path.basename(input_file_name)
        slash_index = input_file_name.find("\\")
        if slash_index >= 0:
            input_file_name = input_file_name[slash_index + 1 :]
    except Exception as e:
        log.error("The post xlsx elements is empty. Error {}".format(str(e)))
        return False, _("No file was attached")
    input_file_name = input_file_name.replace(" ", "_")
    paths = ["tmp", uid, input_file_name.lower()]
    file_name = os.path.join(odk_dir, *paths)

    input_file.seek(0)
    with open(file_name, "wb") as permanent_file:
        shutil.copyfileobj(input_file, permanent_file)

    input_file.close()

    parts = os.path.splitext(input_file_name)

    paths = ["tmp", uid, parts[0] + ".xml"]
    xml_file = os.path.join(odk_dir, *paths)

    try:
        if (
            file_name.find(".xls") == -1
            and file_name.find(".xlsx") == -1
            and file_name.find(".xlsm") == -1
        ):
            return False, _("Invalid file type")

        xls2xform.xls2xform_convert(file_name, xml_file)

        warnings = []
        json_dict = parse_file_to_json(file_name, warnings=warnings)
        paths = ["tmp", uid, parts[0] + ".srv"]
        survey_file = os.path.join(odk_dir, *paths)

        paths = ["tmp", uid, "create.xml"]
        create_file = os.path.join(odk_dir, *paths)

        paths = ["tmp", uid, "insert.xml"]
        insert_file = os.path.join(odk_dir, *paths)

        with open(survey_file, "w") as outfile:
            json_string = json.dumps(json_dict, indent=4, ensure_ascii=False)
            outfile.write(json_string)

        # Check if the conversion created itemsets.csv
        output_dir = os.path.split(xml_file)[0]
        itemsets_csv = os.path.join(output_dir, "itemsets.csv")
        if not os.path.isfile(itemsets_csv):
            itemsets_csv = None

        tree = etree.parse(xml_file)
        root = tree.getroot()
        nsmap = root.nsmap[None]
        h_nsmap = root.nsmap["h"]
        eid = root.findall(".//{" + nsmap + "}data")
        if eid:
            form_id = eid[0].get("id")
            if re.match(r"^[A-Za-z0-9_]+$", form_id):
                form_title = root.findall(".//{" + h_nsmap + "}title")
                if not form_exists(request, project_id, form_id):
                    external_files = []
                    if itemsets_csv is not None:
                        external_files.append(itemsets_csv)
                    error, message = check_jxform_file(
                        request,
                        survey_file,
                        create_file,
                        insert_file,
                        primary_key,
                        external_files,
                    )
                    form_caseselector_file = None
                    if project_case == 1:
                        if error == 0:
                            if form_casetype == 1:
                                fields = get_fields_from_table_in_file(
                                    create_file, "maintable"
                                )
                                case_id_type_correct = False
                                for a_field in fields:
                                    if a_field["name"] == primary_key:
                                        if (
                                            a_field["type"] == "varchar"
                                            or a_field["type"] == "text"
                                            or (
                                                a_field["type"] == "integer"
                                                and a_field["decsize"] == 0
                                            )
                                        ):
                                            case_id_type_correct = True
                                if not case_id_type_correct:
                                    error = 1
                                    message = _(
                                        "The variable {} used to identify the cases is invalid. "
                                        "Only text, calculates or integers are allowed.".format(
                                            form_caselabel
                                        )
                                    )

                                case_label_found = False
                                for a_field in fields:
                                    if a_field["name"] == form_caselabel:
                                        if (
                                            a_field["type"] == "varchar"
                                            or a_field["type"] == "text"
                                            or (
                                                a_field["type"] == "integer"
                                                and a_field["decsize"] == 0
                                            )
                                        ):
                                            case_label_found = True
                                if not case_label_found:
                                    error = 1
                                    message = _(
                                        "The variable {} used to label cases was not found or is invalid. "
                                        "Only text, calculates or integers are allowed.".format(
                                            form_caselabel
                                        )
                                    )

                                case_datetime_found = False
                                for a_field in fields:
                                    if a_field["name"] == form_casedatetime:
                                        if (
                                            a_field["type"] == "date"
                                            or a_field["type"] == "datetime"
                                        ):
                                            case_datetime_found = True

                                if not case_datetime_found:
                                    error = 1
                                    message = _(
                                        "The variable {} used to record a date or date and time was not found"
                                        " or is invalid. The variable must be date or datetime.".format(
                                            form_casedatetime
                                        )
                                    )
                            else:
                                fields = get_fields_from_table_in_file(
                                    create_file, "maintable"
                                )
                                case_selector_found = False
                                for a_field in fields:
                                    if a_field["name"] == form_caseselector:
                                        if (
                                            a_field["odktype"] == "select one"
                                            and a_field["selecttype"] == "3"
                                        ):
                                            case_selector_found = True
                                            form_caseselector_file = a_field[
                                                "externalfilename"
                                            ]
                                        if a_field["odktype"] == "barcode":
                                            case_selector_found = True
                                            form_caseselector_file = "barcode"

                                if not case_selector_found:
                                    error = 1
                                    message = _(
                                        "The variable {} used to search and select cases was not found or is invalid. "
                                        "The variable must be select_one_from_file using a CSV file "
                                        "or a barcode".format(form_caseselector)
                                    )
                                case_datetime_found = False
                                for a_field in fields:
                                    if a_field["name"] == form_casedatetime:
                                        if (
                                            a_field["type"] == "date"
                                            or a_field["type"] == "datetime"
                                        ):
                                            case_datetime_found = True

                                if not case_datetime_found:
                                    error = 1
                                    message = _(
                                        "The variable {} used to record a date or date and time was not found"
                                        " or is invalid. The variable must be date or datetime.".format(
                                            form_casedatetime
                                        )
                                    )

                    if error == 0:
                        continue_creation = True
                        plugin_message = ""
                        for a_plugin in plugins.PluginImplementations(plugins.IForm):
                            if continue_creation:
                                (
                                    continue_creation,
                                    plugin_message,
                                ) = a_plugin.after_odk_form_checks(
                                    request,
                                    user_id,
                                    project_id,
                                    form_id,
                                    form_data,
                                    form_directory,
                                    survey_file,
                                    create_file,
                                    insert_file,
                                    itemsets_csv,
                                )
                        if continue_creation:
                            paths = ["forms", form_directory, "media"]
                            if not os.path.exists(os.path.join(odk_dir, *paths)):
                                os.makedirs(os.path.join(odk_dir, *paths))

                                paths = ["forms", form_directory, "submissions"]
                                os.makedirs(os.path.join(odk_dir, *paths))

                                paths = ["forms", form_directory, "submissions", "logs"]
                                os.makedirs(os.path.join(odk_dir, *paths))

                                paths = ["forms", form_directory, "submissions", "maps"]
                                os.makedirs(os.path.join(odk_dir, *paths))

                                paths = ["forms", form_directory, "repository"]
                                os.makedirs(os.path.join(odk_dir, *paths))
                                paths = ["forms", form_directory, "repository", "temp"]
                                os.makedirs(os.path.join(odk_dir, *paths))

                            xls_file_fame = os.path.basename(file_name)
                            xml_file_name = os.path.basename(xml_file)
                            survey_file_name = os.path.basename(survey_file)
                            paths = ["forms", form_directory, xls_file_fame]
                            final_xls = os.path.join(odk_dir, *paths)
                            paths = ["forms", form_directory, xml_file_name]
                            final_xml = os.path.join(odk_dir, *paths)
                            paths = ["forms", form_directory, survey_file_name]
                            final_survey = os.path.join(odk_dir, *paths)
                            paths = [
                                "forms",
                                form_directory,
                                "repository",
                                "create.xml",
                            ]
                            final_create_xml = os.path.join(odk_dir, *paths)
                            paths = [
                                "forms",
                                form_directory,
                                "repository",
                                "insert.xml",
                            ]
                            final_insert_xml = os.path.join(odk_dir, *paths)
                            shutil.copyfile(file_name, final_xls)
                            shutil.copyfile(xml_file, final_xml)
                            shutil.copyfile(survey_file, final_survey)
                            shutil.copyfile(create_file, final_create_xml)
                            shutil.copyfile(insert_file, final_insert_xml)
                            parent_array = []
                            try:
                                geo_variables = []
                                get_geopoint_variables_from_json(
                                    json_dict, parent_array, geo_variables
                                )
                            except Exception as e:
                                geo_variables = []
                                log.warning(
                                    "Unable to extract GeoPoint from file {}. Error: {}".format(
                                        final_survey, str(e)
                                    )
                                )
                            form_data["project_id"] = project_id
                            form_data["form_id"] = form_id
                            if for_merging:
                                form_data["form_incversion"] = 1
                            form_data["form_name"] = form_title[0].text
                            form_data["form_cdate"] = datetime.datetime.now()
                            form_data["form_directory"] = form_directory
                            project_code = request.matchdict["projcode"]
                            form_data["form_index"] = (
                                user_id.lower()
                                + "_"
                                + project_code.lower()
                                + "_"
                                + form_id.lower()
                            )
                            form_data["form_accsub"] = 1
                            form_data["form_testing"] = 1
                            form_data["form_xlsfile"] = final_xls
                            form_data["form_xmlfile"] = final_xml
                            form_data["form_jsonfile"] = final_survey
                            form_data["form_createxmlfile"] = final_create_xml
                            form_data["form_insertxmlfile"] = final_insert_xml
                            form_data["form_pubby"] = user_id
                            form_data["form_hexcolor"] = ColorHash(form_id).hex
                            if geo_variables:
                                form_geo_points = ",".join(geo_variables)
                                form_data["form_geopoint"] = form_geo_points
                            if message != "":
                                form_data["form_reqfiles"] = message

                            if project_case == 1:
                                form_data["form_case"] = 1
                                form_data["form_casetype"] = form_casetype
                                form_data["form_caselabel"] = form_caselabel
                                form_data["form_caseselector"] = form_caseselector
                                form_data["form_casedatetime"] = form_casedatetime
                                form_data[
                                    "form_caseselectorfilename"
                                ] = form_caseselector_file

                            continue_adding = True
                            for a_plugin in plugins.PluginImplementations(
                                plugins.IForm
                            ):
                                if continue_adding:
                                    (
                                        continue_adding,
                                        message,
                                        form_data,
                                    ) = a_plugin.before_adding_form(
                                        request,
                                        "ODK",
                                        user_id,
                                        project_id,
                                        form_id,
                                        form_data,
                                    )
                            if continue_adding:
                                added, message = add_new_form(request, form_data)
                                if not added:
                                    paths = ["forms", form_directory]
                                    dir_to_delete = os.path.join(odk_dir, *paths)
                                    shutil.rmtree(dir_to_delete)
                                    return added, message
                                else:
                                    for a_plugin in plugins.PluginImplementations(
                                        plugins.IForm
                                    ):
                                        a_plugin.after_adding_form(
                                            request,
                                            "ODK",
                                            user_id,
                                            project_id,
                                            form_id,
                                            form_data,
                                        )
                            else:
                                paths = ["forms", form_directory]
                                dir_to_delete = os.path.join(odk_dir, *paths)
                                shutil.rmtree(dir_to_delete)
                                return False, message

                            # If we have itemsets.csv add it as media files
                            if itemsets_csv is not None:
                                with open(itemsets_csv, "rb") as itemset_file:
                                    md5sum = md5(itemset_file.read()).hexdigest()
                                    added, message = add_file_to_form(
                                        request,
                                        project_id,
                                        form_id,
                                        "itemsets.csv",
                                        True,
                                        md5sum,
                                    )
                                    if added:
                                        itemset_file.seek(0)
                                        bucket_id = project_id + form_id
                                        bucket_id = md5(
                                            bucket_id.encode("utf-8")
                                        ).hexdigest()
                                        store_file(
                                            request,
                                            bucket_id,
                                            "itemsets.csv",
                                            itemset_file,
                                        )

                            paths = ["forms", form_directory, parts[0] + ".json"]
                            json_file = os.path.join(odk_dir, *paths)

                            metadata = {
                                "formID": form_id,
                                "name": form_title[0].text,
                                "majorMinorVersion": "",
                                "version": datetime.datetime.now().strftime("%Y%m%d"),
                                "hash": "md5:"
                                + md5(open(final_xml, "rb").read()).hexdigest(),
                                "descriptionText": form_title[0].text,
                            }

                            with open(json_file, "w") as outfile:
                                json_string = json.dumps(
                                    metadata, indent=4, ensure_ascii=False
                                )
                                outfile.write(json_string)
                            return True, form_id
                        else:
                            paths = ["forms", form_directory]
                            dir_to_delete = os.path.join(odk_dir, *paths)
                            shutil.rmtree(dir_to_delete)
                            return False, plugin_message
                    else:
                        return False, message
                else:
                    return False, _("The form already exists in this project")
            else:
                return (
                    False,
                    _(
                        "The form ID has especial characters. FormShare only allows letters, numbers and underscores(_)"
                    ),
                )
        else:
            return (
                False,
                _("Cannot find XForm ID. Please include this ODK form in an issue on  ")
                + "https://github.com/qlands/FormShare",
            )
    except PyXFormError as e:
        traceback.print_exc()
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e).replace("'", "").replace('"', "").replace("\n", "")
    except Exception as e:
        traceback.print_exc()
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e).replace("'", "").replace('"', "").replace("\n", "")


def update_odk_form(
    request,
    user_id,
    project_id,
    for_form_id,
    odk_dir,
    form_data,
    primary_key,
    project_case=0,
    form_casetype=None,
    form_caselabel=None,
    form_caseselector=None,
    form_casedatetime=None,
):
    _ = request.translate
    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    os.makedirs(os.path.join(odk_dir, *paths))

    try:
        input_file = request.POST["xlsx"].file
        input_file_name = request.POST["xlsx"].filename.lower()
        if os.path.isabs(input_file_name):
            input_file_name = os.path.basename(input_file_name)
        slash_index = input_file_name.find("\\")
        if slash_index >= 0:
            input_file_name = input_file_name[slash_index + 1 :]
    except Exception as e:
        log.error("The post xlsx elements is empty. Error {}".format(str(e)))
        return False, _("No file was attached")
    input_file_name = input_file_name.replace(" ", "_")
    paths = ["tmp", uid, input_file_name]
    file_name = os.path.join(odk_dir, *paths)
    file_name = file_name.lower()

    input_file.seek(0)
    with open(file_name, "wb") as permanent_file:
        shutil.copyfileobj(input_file, permanent_file)

    input_file.close()

    parts = os.path.splitext(input_file_name)

    paths = ["tmp", uid, parts[0] + ".xml"]
    xml_file = os.path.join(odk_dir, *paths)

    try:
        if (
            file_name.find(".xls") == -1
            and file_name.find(".xlsx") == -1
            and file_name.find(".xlsm") == -1
        ):
            return False, _("Invalid file type")

        xls2xform.xls2xform_convert(file_name, xml_file)

        warnings = []
        json_dict = parse_file_to_json(file_name, warnings=warnings)
        paths = ["tmp", uid, parts[0] + ".srv"]
        survey_file = os.path.join(odk_dir, *paths)

        paths = ["tmp", uid, "create.xml"]
        create_file = os.path.join(odk_dir, *paths)

        paths = ["tmp", uid, "insert.xml"]
        insert_file = os.path.join(odk_dir, *paths)

        with open(survey_file, "w") as outfile:
            json_string = json.dumps(json_dict, indent=4, ensure_ascii=False)
            outfile.write(json_string)

        # Check if the conversion created itemsets.csv
        output_dir = os.path.split(xml_file)[0]
        itemsets_csv = os.path.join(output_dir, "itemsets.csv")
        if not os.path.isfile(itemsets_csv):
            itemsets_csv = None

        tree = etree.parse(xml_file)
        root = tree.getroot()
        nsmap = root.nsmap[None]
        h_nsmap = root.nsmap["h"]
        eid = root.findall(".//{" + nsmap + "}data")
        if eid:
            form_id = eid[0].get("id")
            if re.match(r"^[A-Za-z0-9_]+$", form_id):
                if form_id == for_form_id:
                    form_title = root.findall(".//{" + h_nsmap + "}title")
                    if form_exists(request, project_id, form_id):
                        external_files = []
                        if itemsets_csv is not None:
                            external_files.append(itemsets_csv)
                        error, message = check_jxform_file(
                            request,
                            survey_file,
                            create_file,
                            insert_file,
                            primary_key,
                            external_files,
                        )

                        form_caseselector_file = None
                        if project_case == 1:
                            if error == 0:
                                if form_casetype == 1:
                                    fields = get_fields_from_table_in_file(
                                        create_file, "maintable"
                                    )
                                    case_id_type_correct = False
                                    for a_field in fields:
                                        if a_field["name"] == primary_key:
                                            if (
                                                a_field["type"] == "varchar"
                                                or a_field["type"] == "text"
                                                or (
                                                    a_field["type"] == "integer"
                                                    and a_field["decsize"] == 0
                                                )
                                            ):
                                                case_id_type_correct = True
                                    if not case_id_type_correct:
                                        error = 1
                                        message = _(
                                            "The variable {} used to identify the cases is invalid. "
                                            "Only text, calculates or integers are allowed.".format(
                                                form_caselabel
                                            )
                                        )

                                    case_label_found = False
                                    for a_field in fields:
                                        if a_field["name"] == form_caselabel:
                                            if (
                                                a_field["type"] == "varchar"
                                                or a_field["type"] == "text"
                                                or (
                                                    a_field["type"] == "integer"
                                                    and a_field["decsize"] == 0
                                                )
                                            ):
                                                case_label_found = True
                                    if not case_label_found:
                                        error = 1
                                        message = _(
                                            "The variable {} used to label cases was not found or is invalid. "
                                            "Only text, calculates or integers are allowed.".format(
                                                form_caselabel
                                            )
                                        )

                                    case_datetime_found = False
                                    for a_field in fields:
                                        if a_field["name"] == form_casedatetime:
                                            if (
                                                a_field["type"] == "date"
                                                or a_field["type"] == "datetime"
                                            ):
                                                case_datetime_found = True

                                    if not case_datetime_found:
                                        error = 1
                                        message = _(
                                            "The variable {} used to record a date or date and time was not found"
                                            " or is invalid. The variable must be date or datetime.".format(
                                                form_casedatetime
                                            )
                                        )
                                else:
                                    fields = get_fields_from_table_in_file(
                                        create_file, "maintable"
                                    )
                                    case_selector_found = False
                                    for a_field in fields:
                                        if a_field["name"] == form_caseselector:
                                            if (
                                                a_field["odktype"] == "select one"
                                                and a_field["selecttype"] == "3"
                                            ):
                                                case_selector_found = True
                                                form_caseselector_file = a_field[
                                                    "externalfilename"
                                                ]
                                            if a_field["odktype"] == "barcode":
                                                case_selector_found = True
                                                form_caseselector_file = "barcode"
                                    if not case_selector_found:
                                        error = 1
                                        message = _(
                                            "The variable {} used to search and select cases was not found or "
                                            "is invalid. "
                                            "The variable must be select_one_from_file using a CSV file "
                                            "or a barcode.".format(form_caseselector)
                                        )

                                    case_datetime_found = False
                                    for a_field in fields:
                                        if a_field["name"] == form_casedatetime:
                                            if (
                                                a_field["type"] == "date"
                                                or a_field["type"] == "datetime"
                                            ):
                                                case_datetime_found = True

                                    if not case_datetime_found:
                                        error = 1
                                        message = _(
                                            "The variable {} used to record a date or date and time was not found"
                                            " or is invalid. The variable must be date or datetime.".format(
                                                form_casedatetime
                                            )
                                        )

                        if error == 0:
                            old_form_directory = get_form_directory(
                                request, project_id, form_id
                            )
                            form_directory = uid
                            continue_creation = True
                            for a_plugin in plugins.PluginImplementations(
                                plugins.IForm
                            ):
                                if continue_creation:
                                    (
                                        continue_creation,
                                        message,
                                    ) = a_plugin.after_odk_form_checks(
                                        request,
                                        user_id,
                                        project_id,
                                        form_id,
                                        form_data,
                                        form_directory,
                                        survey_file,
                                        create_file,
                                        insert_file,
                                        itemsets_csv,
                                    )
                            if continue_creation:
                                paths = ["forms", form_directory, "media"]
                                if not os.path.exists(os.path.join(odk_dir, *paths)):
                                    os.makedirs(os.path.join(odk_dir, *paths))

                                    paths = ["forms", form_directory, "submissions"]
                                    os.makedirs(os.path.join(odk_dir, *paths))

                                    paths = [
                                        "forms",
                                        form_directory,
                                        "submissions",
                                        "logs",
                                    ]
                                    os.makedirs(os.path.join(odk_dir, *paths))

                                    paths = [
                                        "forms",
                                        form_directory,
                                        "submissions",
                                        "maps",
                                    ]
                                    os.makedirs(os.path.join(odk_dir, *paths))

                                    paths = ["forms", form_directory, "repository"]
                                    os.makedirs(os.path.join(odk_dir, *paths))
                                    paths = [
                                        "forms",
                                        form_directory,
                                        "repository",
                                        "temp",
                                    ]
                                    os.makedirs(os.path.join(odk_dir, *paths))

                                xls_file_fame = os.path.basename(file_name)
                                xml_file_name = os.path.basename(xml_file)
                                survey_file_name = os.path.basename(survey_file)
                                paths = ["forms", form_directory, xls_file_fame]
                                final_xls = os.path.join(odk_dir, *paths)
                                paths = ["forms", form_directory, xml_file_name]
                                final_xml = os.path.join(odk_dir, *paths)
                                paths = ["forms", form_directory, survey_file_name]
                                final_survey = os.path.join(odk_dir, *paths)
                                paths = [
                                    "forms",
                                    form_directory,
                                    "repository",
                                    "create.xml",
                                ]
                                final_create_xml = os.path.join(odk_dir, *paths)
                                paths = [
                                    "forms",
                                    form_directory,
                                    "repository",
                                    "insert.xml",
                                ]
                                final_insert_xml = os.path.join(odk_dir, *paths)
                                shutil.copyfile(file_name, final_xls)
                                shutil.copyfile(xml_file, final_xml)
                                shutil.copyfile(survey_file, final_survey)
                                shutil.copyfile(create_file, final_create_xml)
                                shutil.copyfile(insert_file, final_insert_xml)
                                parent_array = []
                                try:
                                    geo_point_variables = []
                                    get_geopoint_variables_from_json(
                                        json_dict, parent_array, geo_point_variables
                                    )
                                except Exception as e:
                                    geo_point_variables = []
                                    log.warning(
                                        "Unable to extract GeoPoint from file {}. Error: {}".format(
                                            final_survey, str(e)
                                        )
                                    )
                                form_data["project_id"] = project_id
                                form_data["form_id"] = form_id
                                form_data["form_directory"] = form_directory
                                form_data["form_name"] = form_title[0].text
                                form_data["form_lupdate"] = datetime.datetime.now()
                                form_data["form_xlsfile"] = final_xls
                                form_data["form_xmlfile"] = final_xml
                                form_data["form_createxmlfile"] = final_create_xml
                                form_data["form_insertxmlfile"] = final_insert_xml
                                form_data["form_jsonfile"] = final_survey
                                form_data["form_abletomerge"] = -1
                                form_data["form_repositorypossible"] = -1
                                form_data["form_mergerrors"] = None
                                form_data["form_mergetask"] = None
                                form_data["form_reptask"] = None
                                if geo_point_variables:
                                    form_geo_points = ",".join(geo_point_variables)
                                    form_data["form_geopoint"] = form_geo_points
                                if message != "":
                                    form_data["form_reqfiles"] = message

                                if project_case == 1:
                                    form_data["form_case"] = 1
                                    form_data["form_casetype"] = form_casetype
                                    form_data["form_caselabel"] = form_caselabel
                                    form_data["form_caseselector"] = form_caseselector
                                    form_data["form_casedatetime"] = form_casedatetime
                                    form_data[
                                        "form_caseselectorfilename"
                                    ] = form_caseselector_file

                                continue_updating = True
                                for a_plugin in plugins.PluginImplementations(
                                    plugins.IForm
                                ):
                                    if continue_updating:
                                        (
                                            continue_updating,
                                            message,
                                            form_data,
                                        ) = a_plugin.before_updating_form(
                                            request,
                                            "ODK",
                                            user_id,
                                            project_id,
                                            form_id,
                                            form_data,
                                        )
                                if continue_updating:
                                    updated, message = update_form(
                                        request, project_id, for_form_id, form_data
                                    )
                                    if not updated:
                                        # Rollbacks the form directory
                                        update_form_directory(
                                            request,
                                            project_id,
                                            for_form_id,
                                            old_form_directory,
                                        )
                                        return updated, message

                                    for a_plugin in plugins.PluginImplementations(
                                        plugins.IForm
                                    ):
                                        a_plugin.after_updating_form(
                                            request,
                                            "ODK",
                                            user_id,
                                            project_id,
                                            form_id,
                                            form_data,
                                        )

                                    # If we have itemsets.csv add it as media files
                                    if itemsets_csv is not None:
                                        bucket_id = project_id + form_id
                                        bucket_id = md5(
                                            bucket_id.encode("utf-8")
                                        ).hexdigest()
                                        try:
                                            delete_stream(
                                                request, bucket_id, "itemsets.csv"
                                            )
                                        except Exception as e:
                                            log.error(
                                                "Error {} removing filename {} from bucket {}".format(
                                                    str(e), "itemsets.csv", bucket_id
                                                )
                                            )
                                        with open(itemsets_csv, "rb") as itemset_file:
                                            md5sum = md5(
                                                itemset_file.read()
                                            ).hexdigest()
                                            added, message = add_file_to_form(
                                                request,
                                                project_id,
                                                form_id,
                                                "itemsets.csv",
                                                True,
                                                md5sum,
                                            )
                                            if added:
                                                itemset_file.seek(0)
                                                store_file(
                                                    request,
                                                    bucket_id,
                                                    "itemsets.csv",
                                                    itemset_file,
                                                )

                                    paths = [
                                        "forms",
                                        form_directory,
                                        parts[0] + ".json",
                                    ]
                                    json_file = os.path.join(odk_dir, *paths)

                                    metadata = {
                                        "formID": form_id,
                                        "name": form_title[0].text,
                                        "majorMinorVersion": "",
                                        "version": datetime.datetime.now().strftime(
                                            "%Y%m%d"
                                        ),
                                        "hash": "md5:"
                                        + md5(open(final_xml, "rb").read()).hexdigest(),
                                        "descriptionText": form_title[0].text,
                                    }

                                    with open(json_file, "w") as outfile:
                                        json_string = json.dumps(
                                            metadata, indent=4, ensure_ascii=False
                                        )
                                        outfile.write(json_string)
                                    return True, form_id
                                else:
                                    paths = ["forms", form_directory]
                                    dir_to_delete = os.path.join(odk_dir, *paths)
                                    shutil.rmtree(dir_to_delete)
                                    return False, message
                            else:
                                paths = ["forms", form_directory]
                                dir_to_delete = os.path.join(odk_dir, *paths)
                                shutil.rmtree(dir_to_delete)
                                return False, message
                        else:
                            return False, message
                    else:
                        return False, _("The form does not exist in this project")
                else:
                    return (
                        False,
                        _(
                            'The "form_id" of the current form does not match the "form_id" of '
                            "the one you uploaded. You cannot update a form with another form."
                        ),
                    )
            else:
                return (
                    False,
                    _(
                        "The form ID has especial characters. FormShare only allows letters, numbers and underscores(_)"
                    ),
                )
        else:
            return (
                False,
                _("Cannot find XForm ID. Please post the form as an issue on ")
                + "https://github.com/qlands/FormShare",
            )
    except PyXFormError as e:
        traceback.print_exc()
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e)
    except Exception as e:
        traceback.print_exc()
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e)


def generate_form_list(project_array):
    root = etree.Element("xforms", xmlns="http://openrosa.org/xforms/xformsList")
    for project in project_array:
        xform_tag = etree.Element("xform")
        for key, value in project.items():
            atag = etree.Element(key)
            atag.text = value
            xform_tag.append(atag)
        root.append(xform_tag)
    return etree.tostring(root, encoding="utf-8")


def generate_manifest(media_file_array):
    root = etree.Element("manifest", xmlns="http://openrosa.org/xforms/xformsManifest")
    for file in media_file_array:
        xform_tag = etree.Element("mediaFile")
        for key, value in file.items():
            atag = etree.Element(key)
            atag.text = value
            xform_tag.append(atag)
        root.append(xform_tag)
    return etree.tostring(root, encoding="utf-8")


def get_form_list(request, user, project_code, assistant, api=False):
    project_id = get_project_id_from_name(request, user, project_code)
    assistant_project = get_project_from_assistant(request, user, project_id, assistant)
    prj_list = []
    odk_dir = get_odk_path(request)
    if not project_has_crowdsourcing(request, project_id):
        if not api:
            forms = get_assistant_forms(
                request, project_id, assistant_project, assistant
            )
        else:
            forms = get_all_project_forms(request, project_id)
    else:
        forms = get_all_project_forms(request, project_id)
    for form in forms:
        path = os.path.join(odk_dir, *["forms", form["form_directory"], "*.json"])
        files = glob.glob(path)
        if files:
            with io.open(files[0], encoding="utf8") as data_file:
                data = json.load(data_file)
                data["downloadUrl"] = request.route_url(
                    "odkxmlform",
                    userid=user,
                    projcode=project_code,
                    formid=form["form_id"],
                )
                data["manifestUrl"] = request.route_url(
                    "odkmanifest",
                    userid=user,
                    projcode=project_code,
                    formid=form["form_id"],
                )
            prj_list.append(data)
    return generate_form_list(prj_list)


def get_manifest(request, user, project, project_id, form):
    form_files = get_form_files(request, project_id, form)
    if form_files:
        file_array = []
        case_lookup_file, last_gen, case_type = get_case_lookup_file(
            request, project_id, form
        )
        if case_lookup_file is not None:
            for file in form_files:
                if case_lookup_file == file["file_name"]:
                    generate_file = False
                    schema = get_case_schema(request, project_id)
                    log.info(
                        "File {} was generated last {}".format(
                            file["file_name"], last_gen
                        )
                    )
                    if last_gen is None:
                        generate_file = True
                    else:
                        last_submission_date = get_last_submission_date_from_schema(
                            request, schema
                        )
                        last_clean_date = get_last_clean_date_from_schema(
                            request, schema
                        )
                        outdated = False
                        if last_submission_date is not None:
                            if last_submission_date > last_gen:
                                outdated = True
                        if last_clean_date is not None:
                            if last_clean_date > last_gen:
                                outdated = True
                        if outdated:
                            generate_file = True
                    if generate_file:
                        log.info("Generating file {}".format(file["file_name"]))
                        odk_dir = get_odk_path(request)
                        uid = str(uuid.uuid4())
                        paths = ["tmp", uid]
                        temp_dir = os.path.join(odk_dir, *paths)
                        os.makedirs(temp_dir)
                        paths = ["tmp", uid, file["file_name"]]
                        temp_csv = os.path.join(odk_dir, *paths)
                        if case_type == 4:
                            generated = generate_lookup_file(
                                request, project_id, schema, temp_csv, True
                            )
                        else:
                            generated = generate_lookup_file(
                                request, project_id, schema, temp_csv, False
                            )
                        if generated:
                            log.info("File {} generated".format(file["file_name"]))
                            try:
                                csv_file = open(temp_csv, "rb")
                                md5sum = md5(csv_file.read()).hexdigest()
                                added, message = add_file_to_form(
                                    request,
                                    project_id,
                                    form,
                                    file["file_name"],
                                    True,
                                    md5sum,
                                )
                                if added:
                                    csv_file.seek(0)
                                    bucket_id = project_id + form
                                    bucket_id = md5(
                                        bucket_id.encode("utf-8")
                                    ).hexdigest()
                                    store_file(
                                        request, bucket_id, file["file_name"], csv_file
                                    )
                                    csv_file.close()
                                    update_form(
                                        request,
                                        project_id,
                                        form,
                                        {
                                            "form_caseselectorlastgen": datetime.datetime.now()
                                        },
                                    )
                                    file_name = file["file_name"]
                                    file_array.append(
                                        {
                                            "filename": file_name,
                                            "hash": "md5:" + md5sum,
                                            "downloadUrl": request.route_url(
                                                "odkmediafile",
                                                userid=user,
                                                projcode=project,
                                                formid=form,
                                                fileid=file_name,
                                            ),
                                        }
                                    )
                                else:
                                    file_name = file["file_name"]
                                    file_array.append(
                                        {
                                            "filename": file_name,
                                            "hash": "md5:" + file["file_md5"],
                                            "downloadUrl": request.route_url(
                                                "odkmediafile",
                                                userid=user,
                                                projcode=project,
                                                formid=form,
                                                fileid=file_name,
                                            ),
                                        }
                                    )
                            except Exception as e:
                                log.error(
                                    "Error while storing case lookup file for project {}. Error: {}".format(
                                        project_id, str(e)
                                    )
                                )
                                file_name = file["file_name"]
                                file_array.append(
                                    {
                                        "filename": file_name,
                                        "hash": "md5:" + file["file_md5"],
                                        "downloadUrl": request.route_url(
                                            "odkmediafile",
                                            userid=user,
                                            projcode=project,
                                            formid=form,
                                            fileid=file_name,
                                        ),
                                    }
                                )
                        else:
                            file_name = file["file_name"]
                            file_array.append(
                                {
                                    "filename": file_name,
                                    "hash": "md5:" + file["file_md5"],
                                    "downloadUrl": request.route_url(
                                        "odkmediafile",
                                        userid=user,
                                        projcode=project,
                                        formid=form,
                                        fileid=file_name,
                                    ),
                                }
                            )
                    else:
                        log.info(
                            "File {} will not be generated. Using stored file".format(
                                file["file_name"]
                            )
                        )
                        file_name = file["file_name"]
                        file_array.append(
                            {
                                "filename": file_name,
                                "hash": "md5:" + file["file_md5"],
                                "downloadUrl": request.route_url(
                                    "odkmediafile",
                                    userid=user,
                                    projcode=project,
                                    formid=form,
                                    fileid=file_name,
                                ),
                            }
                        )
                else:
                    file_name = file["file_name"]
                    file_array.append(
                        {
                            "filename": file_name,
                            "hash": "md5:" + file["file_md5"],
                            "downloadUrl": request.route_url(
                                "odkmediafile",
                                userid=user,
                                projcode=project,
                                formid=form,
                                fileid=file_name,
                            ),
                        }
                    )
        else:
            for file in form_files:
                file_name = file["file_name"]
                file_array.append(
                    {
                        "filename": file_name,
                        "hash": "md5:" + file["file_md5"],
                        "downloadUrl": request.route_url(
                            "odkmediafile",
                            userid=user,
                            projcode=project,
                            formid=form,
                            fileid=file_name,
                        ),
                    }
                )
        return generate_manifest(file_array)
    else:
        return generate_manifest([])


def get_xml_form(request, project, form):
    xml_file = get_form_xml_file(request, project, form)
    if xml_file is not None:
        content_type, content_enc = mimetypes.guess_type(xml_file)
        file_name = os.path.basename(xml_file)
        response = FileResponse(xml_file, request=request, content_type=content_type)
        response.content_disposition = 'attachment; filename="' + file_name + '"'
        return response
    else:
        raise HTTPNotFound()


def get_media_file(request, project_id, form_id, file_id):
    return retrieve_form_file(request, project_id, form_id, file_id)


def get_submission_file(request, project, form, submission):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    if form_directory is not None:
        path = os.path.join(
            odk_dir, *["forms", form_directory, "submissions", submission + ".json"]
        )
        if os.path.isfile(path):
            content_type, content_enc = mimetypes.guess_type(path)
            file_name = os.path.basename(path)
            response = FileResponse(path, request=request, content_type=content_type)
            response.content_disposition = 'attachment; filename="' + file_name + '"'
            return response
        else:
            raise HTTPNotFound()
    else:
        raise HTTPNotFound()


def merge_versions(
    request,
    odk_dir,
    xform_directory,
    a_create,
    a_insert,
    b_create,
    b_insert,
    ignore_string=None,
):
    odk_tools_merge_versions = os.path.join(
        request.registry.settings["odktools.path"],
        *["utilities", "mergeVersions", "mergeversions"]
    )
    merge_directory = os.path.join(
        odk_dir, *["forms", xform_directory, "merging_files"]
    )
    if not os.path.exists(merge_directory):
        os.makedirs(merge_directory)
    args = [
        odk_tools_merge_versions,
        "-a " + a_create,
        "-b " + b_create,
        "-A " + a_insert,
        "-B " + b_insert,
        "-c "
        + os.path.join(
            odk_dir, *["forms", xform_directory, "merging_files", "create.xml"]
        ),
        "-C "
        + os.path.join(
            odk_dir, *["forms", xform_directory, "merging_files", "insert.xml"]
        ),
        "-d "
        + os.path.join(
            odk_dir, *["forms", xform_directory, "merging_files", "create.sql"]
        ),
        "-D "
        + os.path.join(
            odk_dir, *["forms", xform_directory, "merging_files", "insert.sql"]
        ),
        "-s",
        "-o "
        + os.path.join(
            odk_dir, *["forms", xform_directory, "merging_files", "output.xml"]
        ),
        "-t m",
    ]
    if ignore_string is not None:
        args.append("-i " + ignore_string)

    log.info(" ".join(args))

    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        return 0, " ".join(args)
    else:
        return p.returncode, stdout.decode()


def create_repository(
    request,
    user,
    project,
    form,
    odk_dir,
    xform_directory,
    primary_key,
    discard_testing_data,
    default_language=None,
    other_languages=None,
    for_merging=False,
):
    jxform_to_mysql = os.path.join(
        request.registry.settings["odktools.path"], *["JXFormToMysql", "jxformtomysql"]
    )
    _ = request.translate
    form_data = get_form_data(request, project, form)
    survey_file = get_form_survey_file(request, project, form)
    if survey_file is not None:
        args = [
            jxform_to_mysql,
            "-j " + survey_file,
            "-t maintable",
            "-v " + primary_key,
            "-c "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "create.sql"]
            ),
            "-C "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "create.xml"]
            ),
            "-i "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "insert.sql"]
            ),
            "-D "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "drop.sql"]
            ),
            "-I "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "insert.xml"]
            ),
            "-m "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "metadata.sql"]
            ),
            "-f "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "manifest.xml"]
            ),
        ]

        if other_languages is not None:
            args.append("-l '" + other_languages + "'")
        if default_language is not None:
            args.append("-d '" + default_language + "'")
        args.append(
            "-T "
            + os.path.join(
                odk_dir, *["forms", xform_directory, "repository", "iso639.sql"]
            )
        )
        args.append(
            "-e "
            + os.path.join(odk_dir, *["forms", xform_directory, "repository", "temp"])
        )
        args.append("-L")
        args.append("-o m")

        # Append all media files

        media_files = get_media_files(request, project, form)
        tmp_uid = str(uuid.uuid4())
        target_dir = os.path.join(odk_dir, *["tmp", tmp_uid])
        os.makedirs(target_dir)
        for media_file in media_files:
            store_file_in_directory(
                request, project, form, media_file.file_name, target_dir
            )
        path = os.path.join(odk_dir, *["tmp", tmp_uid, "*.*"])
        files = glob.glob(path)
        if files:
            for aFile in files:
                args.append(aFile)
        p = Popen(args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()

        log.info(" ".join(args))
        args_create = args

        if p.returncode == 0:
            if not for_merging:
                if default_language is None:
                    root = etree.fromstring(stdout.decode())
                    language_array = root.findall(".//language")
                    if language_array:
                        return 3, stdout.decode()
                    #     default_language = "(en)english"
                    # other_languages_array = []
                    # for a_language in language_array:
                    #     if a_language.get("code", "") != "en":
                    #         other_languages_array.append(
                    #             "({}){}".format(
                    #                 a_language.get("code", ""),
                    #                 a_language.get("description", ""),
                    #             )
                    #         )
                    # if other_languages_array:
                    #     other_languages = ",".join(other_languages_array)

                update_form_repository_info(
                    request,
                    project,
                    form,
                    {
                        "form_pkey": primary_key,
                        "form_deflang": default_language,
                        "form_othlangs": other_languages,
                    },
                )

                schema = "FS_" + str(uuid.uuid4()).replace("-", "_")
                create_file = os.path.join(
                    odk_dir, *["forms", xform_directory, "repository", "create.sql"]
                )
                insert_file = os.path.join(
                    odk_dir, *["forms", xform_directory, "repository", "insert.sql"]
                )
                create_xml_file = os.path.join(
                    odk_dir, *["forms", xform_directory, "repository", "create.xml"]
                )
                insert_xml_file = os.path.join(
                    odk_dir, *["forms", xform_directory, "repository", "insert.xml"]
                )

                # If it is a case form and its follow up, activate or deactivate then
                # we modify the create XML file to:
                # - Link the form_caseselector of the form with the form_pkey of the creator form.
                # - For activate and deactivate, Indicate in the maintable of the form
                #   information that we need to create an after insert trigger to activate or deactivate a case.
                # - Then we call createFromXML to generate a new SQL file with such changes
                if form_data["form_case"] == 1 and form_data["form_casetype"] > 1:
                    form_creator = get_case_form(request, project)
                    form_creator_data = get_form_data(request, project, form_creator)
                    creator_pkey_data = get_field_details(
                        request,
                        project,
                        form_creator,
                        "maintable",
                        form_creator_data["form_pkey"],
                    )
                    tree = etree.parse(create_xml_file)
                    root = tree.getroot()
                    table = root.find(".//table[@name='maintable']")
                    if form_data["form_casetype"] >= 2:
                        table.set("case_followup", "true")
                        if form_data["form_casetype"] > 2:
                            table.set("case_action", "true")
                        table.set(
                            "creator_table",
                            form_creator_data["form_schema"] + ".maintable",
                        )
                        table.set("creator_field", form_creator_data["form_pkey"])
                        table.set("selector_field", form_data["form_caseselector"])
                        table.set(
                            "block_trigger", "T" + str(uuid.uuid4()).replace("-", "_")
                        )
                        if form_data["form_casetype"] > 2:
                            table.set(
                                "action_trigger",
                                "T" + str(uuid.uuid4()).replace("-", "_"),
                            )
                            if form_data["form_casetype"] == 3:
                                table.set("case_action_type", "deactivate")
                            else:
                                table.set("case_action_type", "activate")
                    if table is not None:
                        field = root.find(
                            ".//field[@name='" + form_data["form_caseselector"] + "']"
                        )
                        if field is not None:
                            field.set("type", creator_pkey_data["field_type"])
                            field.set("size", str(creator_pkey_data["field_size"]))
                            field.set(
                                "rtable",
                                form_creator_data["form_schema"] + ".maintable",
                            )
                            field.set("rfield", form_creator_data["form_pkey"])
                            field.set(
                                "rname", "fk_" + str(uuid.uuid4()).replace("-", "_")
                            )
                            field.set("rlookup", "false")
                            # Save the changes in the XML Create file
                            if not os.path.exists(create_xml_file + ".case.bk"):
                                shutil.copy(
                                    create_xml_file, create_xml_file + ".case.bk"
                                )
                            tree.write(
                                create_xml_file,
                                pretty_print=True,
                                xml_declaration=True,
                                encoding="utf-8",
                            )
                            # Run CreateFromXML
                            create_from_xml = os.path.join(
                                request.registry.settings["odktools.path"],
                                *["utilities", "createFromXML", "createfromxml"]
                            )
                            args = [
                                create_from_xml,
                                "-i " + create_xml_file,
                                "-o " + create_file,
                            ]
                            p = Popen(args, stdout=PIPE, stderr=PIPE)
                            stdout, stderr = p.communicate()
                            if p.returncode != 0:
                                log.error(
                                    "Case createFromXML error {}. Message: {}. Command: {}".format(
                                        p.returncode,
                                        stdout.decode() + " - " + stderr.decode(),
                                        " ".join(args),
                                    )
                                )
                                return (
                                    p.returncode,
                                    stdout.decode()
                                    + " - "
                                    + stderr.decode()
                                    + " - "
                                    + " ".join(args),
                                )
                        else:
                            log.error(
                                "The selector field {} was not found in {}".format(
                                    form_data["form_caseselector"], create_xml_file
                                )
                            )
                            return (
                                1,
                                "The selector field {} was not found in {}".format(
                                    form_data["form_caseselector"], create_xml_file
                                ),
                            )
                    else:
                        log.error(
                            "Main table was not found in {}".format(create_xml_file)
                        )
                        return (
                            1,
                            "Main table was not found in {}".format(create_xml_file),
                        )

                formshare_create_repository = True
                cnf_file = request.registry.settings["mysql.cnf"]
                for a_plugin in plugins.PluginImplementations(plugins.IRepository):
                    formshare_create_repository = a_plugin.before_creating_repository(
                        request,
                        user,
                        project,
                        form,
                        cnf_file,
                        create_file,
                        insert_file,
                        schema,
                    )
                    break
                if formshare_create_repository:
                    # Calls the Celery task
                    task = create_database_repository(
                        request,
                        user,
                        project,
                        form,
                        odk_dir,
                        xform_directory,
                        schema,
                        primary_key,
                        cnf_file,
                        create_file,
                        insert_file,
                        create_xml_file,
                        insert_xml_file,
                        " ".join(args_create),
                        discard_testing_data,
                    )
                    form_data = {"form_reptask": task}
                    update_form(request, project, form, form_data)
                    for a_plugin in plugins.PluginImplementations(plugins.IRepository):
                        a_plugin.on_creating_repository(
                            request, user, project, form, task
                        )
                else:  # pragma: no cover because we cannot test both at the same time
                    custom_task = None
                    for a_plugin in plugins.PluginImplementations(plugins.IRepository):
                        custom_task = a_plugin.custom_repository_process(
                            request,
                            user,
                            project,
                            form,
                            odk_dir,
                            xform_directory,
                            schema,
                            primary_key,
                            cnf_file,
                            create_file,
                            insert_file,
                            create_xml_file,
                            " ".join(args),
                        )
                        break  # Only one plugin implementing custom_repository_process will be called

                    form_data = {"form_reptask": custom_task}
                    update_form(request, project, form, form_data)
                    for a_plugin in plugins.PluginImplementations(plugins.IRepository):
                        a_plugin.on_creating_repository(
                            request, user, project, form, custom_task
                        )

                return 0, ""
            else:
                update_form_repository_info(
                    request,
                    project,
                    form,
                    {
                        "form_pkey": primary_key,
                        "form_deflang": default_language,
                        "form_othlangs": other_languages,
                    },
                )
                if default_language is not None:
                    df_language = default_language.replace(")", "|")
                    df_language = df_language.replace("(", "")
                    parts = df_language.split("|")
                    root = etree.fromstring(stdout.decode())
                    language_array = root.findall(".//language")  # language
                    language_found = False
                    if language_array:
                        for a_language in language_array:
                            if (
                                a_language.get("description", "").lower()
                                == parts[1].lower()
                            ):
                                language_found = True
                                break
                    if not language_found:
                        lng_message = _(
                            'The language "{}" is missing in this version of the form '
                            'and cannot be merged.\n\nUse the "Fix language" button to set the languages '
                            "in this version of the ODK Form.".format(parts[1])
                        )
                        if parts[1] == "default":
                            lng_message = (
                                lng_message
                                + "\n\n"
                                + _(
                                    'The language called "default" appears when you have a '
                                    '"label" without indicating a language. '
                                    'For example if you had a column called "label" '
                                    'and another called "label:English (es)" then "default" '
                                    'refers to the language of "label" which was not '
                                    "indicated in the previous version of this ODK Form."
                                    '\n\nIn this new version you added the language to the "label" therefore "default" '
                                    "does not exists"
                                )
                            )
                        return 22, lng_message
                else:
                    root = etree.fromstring(stdout.decode())
                    language_array = root.findall(".//language")  # language
                    if language_array:
                        return 23, _(
                            "This version of the form is in multiple languages but the previous one "
                            'was not and therefore and cannot be merged.\n\nUse the "Fix language" '
                            "button to set the languages in this version of the ODK Form."
                        )

                return 0, ""
        else:
            if p.returncode == 1 or p.returncode < 0:
                return (
                    p.returncode,
                    stdout.decode() + " - " + stderr.decode() + " - " + " ".join(args),
                )
            else:
                return p.returncode, stdout.decode()
    else:
        return -1, "Form data cannot be found"


def move_media_files(odk_dir, xform_directory, src_submission, trg_submission):
    source_path = os.path.join(
        odk_dir, *["forms", xform_directory, "submissions", src_submission, "*.*"]
    )
    target_path = os.path.join(
        odk_dir, *["forms", xform_directory, "submissions", trg_submission]
    )
    files = glob.glob(source_path)
    for file in files:
        try:
            shutil.move(file, target_path)
        except Exception as e:
            log.error(
                "moveMediaFiles. Error moving from "
                + src_submission
                + " to "
                + trg_submission
                + " . Message: "
                + str(e)
            )


def store_json_file(
    request,
    submission_id,
    temp_json_file,
    json_file,
    ordered_json_file,
    odk_dir,
    xform_directory,
    schema,
    user,
    project,
    form,
    assistant,
):
    if schema is not None:
        if schema != "":
            # Add the controlling fields to the JSON file
            project_code = get_project_code_from_id(request, user, project)
            original_file = ordered_json_file.replace(".ordered.json", ".original.json")
            shutil.copyfile(temp_json_file, original_file)
            with open(temp_json_file, "r") as f:
                submission_data = json.load(f)
                submission_data["_submitted_by"] = assistant
                submission_data["_submitted_date"] = datetime.datetime.now().isoformat()
                submission_data["_user_id"] = user
                submission_data.pop("_version", "")
                submission_data.pop("_id", "")
                submission_data["_submission_id"] = submission_id
                submission_data["_project_code"] = project_code
                submission_data["_active"] = 1
                geopoint_variables = get_form_geopoints(request, project, form)
                if geopoint_variables:
                    for geopoint_variable in geopoint_variables:
                        if geopoint_variable in submission_data.keys():
                            submission_data[geopoint_variable] = submission_data[
                                geopoint_variable
                            ].replace("\\n", " ")
                            submission_data[geopoint_variable] = submission_data[
                                geopoint_variable
                            ].replace("\n", " ")
                            if submission_data[geopoint_variable] != "":
                                submission_data["_geopoint"] = submission_data[
                                    geopoint_variable
                                ]
                                parts = submission_data["_geopoint"].split(" ")
                                if len(parts) >= 4:
                                    submission_data["_latitude"] = parts[0]
                                    submission_data["_longitude"] = parts[1]
                                    submission_data["_elevation"] = parts[2]
                                    submission_data["_precision"] = parts[3]
                                else:
                                    if len(parts) == 3:
                                        submission_data["_latitude"] = parts[0]
                                        submission_data["_longitude"] = parts[1]
                                        submission_data["_elevation"] = parts[2]
                                    else:
                                        if len(parts) == 2:
                                            submission_data["_latitude"] = parts[0]
                                            submission_data["_longitude"] = parts[1]
                                if len(parts) >= 2:
                                    submission_data["_geolocation"] = {
                                        "lat": submission_data["_latitude"],
                                        "lon": submission_data["_longitude"],
                                    }
                                break  # Only one gps point is stored
                # pkey_variable = get_form_primary_key(request, project, form)
                # if pkey_variable is not None:
                #     if geopoint_variable in submission_data.keys():
                #         submission_data["_geopoint"] = submission_data[geopoint_variable]

            with open(temp_json_file, "w") as outfile:
                json_string = json.dumps(submission_data, indent=4, ensure_ascii=False)
                outfile.write(json_string)

            # Second we pass the temporal JSON to jQ to order its elements
            # this will help later on if we want to compare between JSONs
            args = ["jq", "-S", ".", temp_json_file]

            final = open(ordered_json_file, "w")
            p = Popen(args, stdout=final, stderr=PIPE)
            stdout, stderr = p.communicate()
            final.close()
            if p.returncode == 0:
                try:
                    shutil.copyfile(temp_json_file, json_file)
                    os.remove(temp_json_file)
                except Exception as e:
                    log.error(
                        "XMLToJSON error. Temporary file "
                        + temp_json_file
                        + " might not exist! Error: "
                        + str(e)
                    )
                    return 1, ""

                # Get the MD5Sum of the JSON file and looks for it in the submissions
                # This will get an exact match that will not move into the database
                original_md5 = md5(open(original_file, "rb").read()).hexdigest()
                md5sum = md5(open(json_file, "rb").read()).hexdigest()
                sameas = get_submission_data(request, project, form, original_md5)
                if sameas is None:
                    # Third we try to move the JSON data into the database
                    mysql_user = request.registry.settings["mysql.user"]
                    mysql_password = request.registry.settings["mysql.password"]
                    mysql_host = request.registry.settings["mysql.host"]
                    mysql_port = request.registry.settings["mysql.port"]
                    log_file_name = os.path.splitext(json_file)[0] + ".xml"
                    uuid_file_name = os.path.splitext(json_file)[0] + ".log"
                    log_file = os.path.join(
                        odk_dir,
                        *[
                            "forms",
                            xform_directory,
                            "submissions",
                            "logs",
                            os.path.basename(log_file_name),
                        ]
                    )
                    imported_file = os.path.join(
                        odk_dir,
                        *[
                            "forms",
                            xform_directory,
                            "submissions",
                            "logs",
                            "imported.sqlite",
                        ]
                    )
                    uuid_file = os.path.join(
                        odk_dir,
                        *["forms", xform_directory, "submissions", uuid_file_name]
                    )
                    maps_directory = os.path.join(
                        odk_dir, *["forms", xform_directory, "submissions", "maps"]
                    )
                    manifest_file = os.path.join(
                        odk_dir,
                        *["forms", xform_directory, "repository", "manifest.xml"]
                    )
                    args = []
                    json_to_mysql = os.path.join(
                        request.registry.settings["odktools.path"],
                        *["JSONToMySQL", "jsontomysql"]
                    )
                    args.append(json_to_mysql)
                    args.append("-H " + mysql_host)
                    args.append("-P " + mysql_port)
                    args.append("-u " + mysql_user)
                    args.append("-p " + mysql_password)
                    args.append("-s " + schema)
                    args.append("-o " + log_file)
                    args.append("-j " + json_file)
                    args.append("-i " + imported_file)
                    args.append("-M " + maps_directory)
                    args.append("-m " + manifest_file)
                    args.append("-U " + uuid_file)
                    args.append("-O m")
                    args.append("-w")

                    json_file_name = os.path.basename(json_file)
                    json_file_base = os.path.splitext(json_file_name)[0]
                    submission_files = os.path.join(
                        odk_dir,
                        *[
                            "forms",
                            xform_directory,
                            "submissions",
                            json_file_base,
                            "*.osm",
                        ]
                    )
                    files = glob.glob(submission_files)
                    if files:
                        for file in files:
                            args.append(file)
                    # log.error(" ".join(args))
                    p = Popen(args, stdout=PIPE, stderr=PIPE)
                    stdout, stderr = p.communicate()
                    # An error 2 is an SQL error that goes to the logs
                    if p.returncode == 0 or p.returncode == 2:
                        if not project_has_crowdsourcing(request, project):
                            project_of_assistant = get_project_from_assistant(
                                request, user, project, assistant
                            )
                        else:
                            project_of_assistant = None
                            assistant = None
                        added, message = add_submission(
                            request,
                            project,
                            form,
                            project_of_assistant,
                            assistant,
                            submission_id,
                            md5sum,
                            original_md5,
                            p.returncode,
                        )

                        if not added:
                            log.error(message)
                            return 1, message

                        media_path = os.path.join(
                            odk_dir,
                            *[
                                "forms",
                                xform_directory,
                                "submissions",
                                submission_id,
                                "*.*",
                            ]
                        )
                        files = glob.glob(media_path)
                        for file in files:
                            for a_plugin in plugins.PluginImplementations(
                                plugins.IMediaSubmission
                            ):
                                a_plugin.after_storing_media_in_repository(
                                    request,
                                    user,
                                    project,
                                    form,
                                    assistant,
                                    submission_id,
                                    json_file,
                                    file,
                                )

                        if p.returncode == 2:
                            log.error(
                                "Submission ID {} did not enter the repository. Command executed: {}".format(
                                    submission_id, " ".join(args)
                                )
                            )
                            added, message = add_json_log(
                                request,
                                project,
                                form,
                                submission_id,
                                json_file,
                                log_file,
                                1,
                                project_of_assistant,
                                assistant,
                                " ".join(args),
                            )
                            if not added:
                                log.error(message)
                                return 1, message
                        else:
                            # Add the JSON to the Elastic Search index but only submissions without error

                            index_data = {
                                "_submitted_date": submission_data.get(
                                    "_submitted_date", ""
                                ),
                                "_xform_id_string": submission_data.get(
                                    "_xform_id_string", ""
                                ),
                                "_submitted_by": submission_data.get(
                                    "_submitted_by", ""
                                ),
                                "_user_id": submission_data.get("_user_id", ""),
                                "_project_code": submission_data.get(
                                    "_project_code", ""
                                ),
                                "_geopoint": submission_data.get("_geopoint", ""),
                            }
                            if submission_data.get("_geolocation", "") != "":
                                index_data["_geolocation"] = submission_data.get(
                                    "_geolocation", ""
                                )
                            add_dataset(
                                request.registry.settings,
                                project,
                                form,
                                submission_id,
                                index_data,
                            )
                            # Add the inserted records in the record index
                            with open(uuid_file) as f:
                                lines = f.readlines()
                                for line in lines:
                                    parts = line.split(",")
                                    add_record(
                                        request.registry.settings,
                                        project,
                                        form,
                                        schema,
                                        parts[0],
                                        parts[1].replace("\n", ""),
                                    )

                        for a_plugin in plugins.PluginImplementations(
                            plugins.IJSONSubmission
                        ):
                            a_plugin.after_processing_submission_in_repository(
                                request,
                                user,
                                project,
                                form,
                                assistant,
                                submission_id,
                                p.returncode,
                                json_file,
                            )

                        return p.returncode, ""
                    else:
                        log.error(
                            "JSONToMySQL error. Inserting "
                            + json_file
                            + ". Error: "
                            + stdout.decode()
                            + "-"
                            + stderr.decode()
                            + ". Command line: "
                            + " ".join(args)
                        )
                        return 1, ""
                else:
                    # If the MD5Sum is the same then add it to the submission table
                    # indicating the "sameas" field. Any media files of the
                    # duplicated submission moves to the "sameas" submission.
                    # This will fix the issue when the media files are so big
                    # that multiple posts are done by ODK Collect for the same
                    # submission
                    project_of_assistant = get_project_from_assistant(
                        request, user, project, assistant
                    )
                    added, message = add_submission_same_as(
                        request,
                        project,
                        form,
                        project_of_assistant,
                        assistant,
                        submission_id,
                        md5sum,
                        0,
                        sameas.submission_id,
                    )
                    if not added:
                        log.error(message)
                        return 1, message

                    media_path = os.path.join(
                        odk_dir,
                        *["forms", xform_directory, "submissions", submission_id, "*.*"]
                    )
                    files = glob.glob(media_path)
                    for file in files:
                        for a_plugin in plugins.PluginImplementations(
                            plugins.IMediaSubmission
                        ):
                            a_plugin.after_storing_media_in_repository(
                                request,
                                user,
                                project,
                                form,
                                assistant,
                                sameas.submission_id,
                                json_file,
                                file,
                            )

                    move_media_files(
                        odk_dir, xform_directory, submission_id, sameas.submission_id
                    )

                    for a_plugin in plugins.PluginImplementations(
                        plugins.IJSONSubmission
                    ):
                        a_plugin.after_processing_submission_in_repository(
                            request,
                            user,
                            project,
                            form,
                            assistant,
                            sameas.submission_id,
                            0,
                            json_file,
                        )

                    return 0, ""
            else:
                log.error(
                    "jQ error. Converting "
                    + temp_json_file
                    + "  to "
                    + json_file
                    + ". Error: "
                    + "-"
                    + stderr.decode()
                    + ". Command line: "
                    + " ".join(args)
                )
                return 1, ""
    else:
        # We compare the MD5Sum of the testing submissions so the
        # media files are stored in the proper way if ODK Collect
        # send the media files in separate submissions when such
        # file are so big that separation is required
        try:
            shutil.move(temp_json_file, json_file)
            original_file = json_file.replace(".json", ".original")
            shutil.copyfile(json_file, original_file)
            project_code = get_project_code_from_id(request, user, project)
            with open(json_file, "r") as f:
                submission_data = json.load(f)
                submission_data["_submitted_by"] = assistant
                submission_data["_submitted_date"] = datetime.datetime.now().isoformat()
                submission_data["_user_id"] = user
                submission_data["_submission_id"] = submission_id
                submission_data["_project_code"] = project_code
                geopoint_variables = get_form_geopoints(request, project, form)
                if geopoint_variables:
                    for geopoint_variable in geopoint_variables:
                        if geopoint_variable in submission_data.keys():
                            submission_data[geopoint_variable] = submission_data[
                                geopoint_variable
                            ].replace("\\n", " ")
                            submission_data[geopoint_variable] = submission_data[
                                geopoint_variable
                            ].replace("\n", " ")
                            if submission_data[geopoint_variable] != "":
                                submission_data["_geopoint"] = submission_data[
                                    geopoint_variable
                                ]
                                parts = submission_data["_geopoint"].split(" ")
                                if len(parts) >= 4:
                                    submission_data["_latitude"] = parts[0]
                                    submission_data["_longitude"] = parts[1]
                                    submission_data["_elevation"] = parts[2]
                                    submission_data["_precision"] = parts[3]
                                else:
                                    if len(parts) == 3:
                                        submission_data["_latitude"] = parts[0]
                                        submission_data["_longitude"] = parts[1]
                                        submission_data["_elevation"] = parts[2]
                                    else:
                                        if len(parts) == 2:
                                            submission_data["_latitude"] = parts[0]
                                            submission_data["_longitude"] = parts[1]
                                if len(parts) >= 2:
                                    submission_data["_geolocation"] = {
                                        "lat": submission_data["_latitude"],
                                        "lon": submission_data["_longitude"],
                                    }
                                break  # Only one gps point will be stored

            submission_exists = None
            submissions_path = os.path.join(
                odk_dir, *["forms", xform_directory, "submissions", "*.original"]
            )
            files = glob.glob(submissions_path)
            md5sum = md5(open(original_file, "rb").read()).hexdigest()
            for aFile in files:
                if aFile != original_file:
                    other_md5sum = md5(open(aFile, "rb").read()).hexdigest()
                    if md5sum == other_md5sum:
                        submission_exists = aFile
                        break

            if submission_exists is None:
                # Adds the dataset to the Elastic Search index
                index_data = {
                    "_submitted_date": submission_data.get("_submitted_date", ""),
                    "_xform_id_string": submission_data.get("_xform_id_string", ""),
                    "_submitted_by": submission_data.get("_submitted_by", ""),
                    "_user_id": submission_data.get("_user_id", ""),
                    "_project_code": submission_data.get("_project_code", ""),
                    "_geopoint": submission_data.get("_geopoint", ""),
                }
                if submission_data.get("_geolocation", "") != "":
                    index_data["_geolocation"] = submission_data.get("_geolocation", "")
                add_dataset(
                    request.registry.settings,
                    project,
                    form,
                    submission_id,
                    index_data,
                )

                with open(json_file, "w") as outfile:
                    json_string = json.dumps(
                        submission_data, indent=4, ensure_ascii=False
                    )
                    outfile.write(json_string)

                media_path = os.path.join(
                    odk_dir,
                    *["forms", xform_directory, "submissions", submission_id, "*.*"]
                )
                files = glob.glob(media_path)
                for file in files:
                    for a_plugin in plugins.PluginImplementations(
                        plugins.IMediaSubmission
                    ):
                        a_plugin.after_storing_media_not_in_repository(
                            request,
                            user,
                            project,
                            form,
                            assistant,
                            submission_id,
                            json_file,
                            file,
                        )

                for a_plugin in plugins.PluginImplementations(plugins.IJSONSubmission):
                    a_plugin.after_processing_submission_not_in_repository(
                        request,
                        user,
                        project,
                        form,
                        assistant,
                        submission_id,
                        json_file,
                    )

            else:
                target_submission_id = os.path.basename(submission_exists)
                target_submission_id = target_submission_id.replace(".original", "")
                log.error(
                    "Submission {source} and {target} are the same. Moving media from {source} to {target}".format(
                        source=submission_id, target=target_submission_id
                    )
                )

                media_path = os.path.join(
                    odk_dir,
                    *["forms", xform_directory, "submissions", submission_id, "*.*"]
                )
                files = glob.glob(media_path)
                for file in files:
                    for a_plugin in plugins.PluginImplementations(
                        plugins.IMediaSubmission
                    ):
                        a_plugin.after_storing_media_not_in_repository(
                            request,
                            user,
                            project,
                            form,
                            assistant,
                            target_submission_id,
                            json_file,
                            file,
                        )

                move_media_files(
                    odk_dir, xform_directory, submission_id, target_submission_id
                )
                # Remove the submission files because already exist
                os.remove(original_file)
                os.remove(json_file)
                submission_path = os.path.join(
                    odk_dir, *["forms", xform_directory, "submissions", submission_id]
                )
                shutil.rmtree(submission_path)

                for a_plugin in plugins.PluginImplementations(plugins.IJSONSubmission):
                    a_plugin.after_processing_submission_not_in_repository(
                        request,
                        user,
                        project,
                        form,
                        assistant,
                        target_submission_id,
                        json_file,
                    )

            return 0, ""
        except Exception as e:
            log.error(
                "Store JSON error. Temporary file "
                + temp_json_file
                + " might not exist! Error: "
                + str(e)
            )
            return 1, ""


def convert_xml_to_json(
    odk_dir,
    xml_file,
    xform_directory,
    schema,
    xml_form_file,
    user,
    project,
    form,
    assistant,
    request,
):
    xml_to_json = os.path.join(
        request.registry.settings["odktools.path"], *["XMLtoJSON", "xmltojson"]
    )
    temp_json_file = xml_file.replace(".xml", ".tmp.json")
    ordered_json_file = xml_file.replace(".xml", ".ordered.json")
    json_file = xml_file.replace(".xml", ".json")
    submission_id = os.path.basename(xml_file)
    submission_id = submission_id.replace(".xml", "")

    # First we convert the XML to a temporal JSON
    args = [
        xml_to_json,
        "-i " + xml_file,
        "-o " + temp_json_file,
        "-x " + xml_form_file,
    ]
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        continue_processing = 0
        for a_plugin in plugins.PluginImplementations(plugins.IJSONSubmission):
            continue_processing, message = a_plugin.before_processing_submission(
                request,
                user,
                project,
                form,
                assistant,
                temp_json_file,
            )
        if continue_processing == 0:
            stored, message = store_json_file(
                request,
                submission_id,
                temp_json_file,
                json_file,
                ordered_json_file,
                odk_dir,
                xform_directory,
                schema,
                user,
                project,
                form,
                assistant,
            )
            return stored, message
        else:
            return continue_processing, message
    else:
        log.error(
            "XMLToJSON error. Converting "
            + xml_file
            + "  to "
            + json_file
            + ". Error: "
            + stdout.decode()
            + "-"
            + stderr.decode()
            + ". Command line: "
            + " ".join(args)
        )
        return 1, ""


def store_json_submission(request, user, project, assistant):
    odk_dir = get_odk_path(request)
    unique_id = uuid4()
    path = os.path.join(odk_dir, *["submissions", str(unique_id)])
    os.makedirs(path)
    json_file = ""
    for key in request.POST.keys():
        try:
            if key != "*isIncomplete*":
                filename = request.POST[key].filename
                if os.path.isabs(filename):
                    filename = os.path.basename(filename)
                slash_index = filename.find("\\")
                if slash_index >= 0:
                    filename = filename[slash_index + 1 :]
                if filename.upper().find(".JSON") >= 0:
                    filename = str(unique_id) + ".json"
                else:
                    if filename == "xml_submission_file":
                        filename = str(unique_id) + ".json"
                input_file = request.POST[key].file
                file_path = os.path.join(path, filename)
                if file_path.upper().find(".JSON") >= 0:
                    json_file = file_path
                temp_file_path = file_path + "~"
                input_file.seek(0)
                with open(temp_file_path, "wb") as output_file:
                    shutil.copyfileobj(input_file, output_file)
                os.rename(temp_file_path, file_path)
            else:
                log.error(
                    "Incomplete submission {} in project {} of user {} with assistant {}".format(
                        unique_id, project, user, assistant
                    )
                )
        except Exception as e:
            log.error(
                "Submission "
                + str(unique_id)
                + " has POST error key: "
                + key
                + " Error: "
                + str(e)
                + ". URL: "
                + request.url
            )
    if json_file != "":
        f = open(json_file)
        json_file_data = json.load(f)
        f.close()
        xform_id = json_file_data.get("_xform_id_string")
        if xform_id is not None:
            form_data = get_form_data(request, project, xform_id)
            if form_data is not None:
                if form_data["form_accsub"] == 1:
                    total, t1, t2 = get_dataset_stats_for_form(
                        request.registry.settings, project, xform_id
                    )
                    if (
                        total
                        >= int(request.registry.settings.get("maximum.testing", "200"))
                        and form_data["form_schema"] is None
                    ):
                        form_data["form_blocked"] = 1
                    if form_data["form_blocked"] == 0:
                        if assistant_has_form(
                            request, user, project, xform_id, assistant
                        ) or project_has_crowdsourcing(request, project):
                            media_path = os.path.join(
                                odk_dir,
                                *[
                                    "forms",
                                    form_data["form_directory"],
                                    "submissions",
                                    str(unique_id),
                                    "diffs",
                                ]
                            )
                            os.makedirs(media_path)
                            media_path = os.path.join(
                                odk_dir,
                                *[
                                    "forms",
                                    form_data["form_directory"],
                                    "submissions",
                                    str(unique_id),
                                ]
                            )
                            target_path = os.path.join(
                                odk_dir,
                                *["forms", form_data["form_directory"], "submissions"]
                            )
                            path = os.path.join(path, *["*.*"])
                            files = glob.glob(path)
                            json_file = ""
                            for file in files:
                                base_file = os.path.basename(file)
                                if base_file.upper().find(".JSON") >= 0:
                                    target_file = os.path.join(target_path, base_file)
                                    json_file = target_file
                                    shutil.move(file, target_file)

                            for file in files:
                                base_file = os.path.basename(file)
                                if base_file.upper().find(".JSON") < 0:
                                    target_file = os.path.join(media_path, base_file)
                                    shutil.move(file, target_file)

                            if json_file != "":
                                # ---------
                                temp_json_file = json_file.replace(".json", ".tmp.json")
                                shutil.copyfile(json_file, temp_json_file)
                                ordered_json_file = json_file.replace(
                                    ".json", ".ordered.json"
                                )
                                submission_id = os.path.basename(json_file)
                                submission_id = submission_id.replace(".json", "")
                                continue_processing = 0
                                for a_plugin in plugins.PluginImplementations(
                                    plugins.IJSONSubmission
                                ):
                                    (
                                        continue_processing,
                                        message,
                                    ) = a_plugin.before_processing_submission(
                                        request,
                                        user,
                                        project,
                                        xform_id,
                                        assistant,
                                        temp_json_file,
                                    )
                                if continue_processing == 0:
                                    res_code, message = store_json_file(
                                        request,
                                        submission_id,
                                        temp_json_file,
                                        json_file,
                                        ordered_json_file,
                                        odk_dir,
                                        form_data["form_directory"],
                                        form_data["form_schema"],
                                        user,
                                        project,
                                        xform_id,
                                        assistant,
                                    )
                                else:
                                    res_code = continue_processing
                                if res_code == 0:
                                    return True, 201
                                else:
                                    if res_code == 1:
                                        return False, 500
                                    else:
                                        return True, 201
                            else:
                                return False, 404
                        else:
                            log.error(
                                "Enumerator %s cannot submit data to %s",
                                assistant,
                                xform_id,
                            )
                            return False, 404
                    else:
                        log.error(
                            "The form {} is blocked and cannot accept submissions at the moment".format(
                                xform_id
                            )
                        )
                        return False, 404
                else:
                    log.error(
                        "The form {} does not accept submissions".format(xform_id)
                    )
                    return False, 404
            else:
                log.error(
                    "Submission for ID %s does not exist in the database", xform_id
                )
                return False, 404
        else:
            log.error("Submission does not have and ID")
            return False, 404
    else:
        log.error("Submission does not have an JSON file")
        return False, 500


def store_submission(request, user, project, assistant):
    odk_dir = get_odk_path(request)
    unique_id = uuid4()
    path = os.path.join(odk_dir, *["submissions", str(unique_id)])
    os.makedirs(path)
    xml_file = ""
    for key in request.POST.keys():
        try:
            if key != "*isIncomplete*":
                filename = request.POST[key].filename
                if os.path.isabs(filename):
                    filename = os.path.basename(filename)
                slash_index = filename.find("\\")
                if slash_index >= 0:
                    filename = filename[slash_index + 1 :]
                if filename.upper().find(".XML") >= 0:
                    filename = str(unique_id) + ".xml"
                else:
                    if filename == "xml_submission_file":
                        filename = str(unique_id) + ".xml"
                input_file = request.POST[key].file
                file_path = os.path.join(path, filename)
                if file_path.upper().find(".XML") >= 0:
                    xml_file = file_path
                temp_file_path = file_path + "~"
                input_file.seek(0)
                with open(temp_file_path, "wb") as output_file:
                    shutil.copyfileobj(input_file, output_file)
                # Now that we know the file has been fully saved to disk move it into place.
                if temp_file_path.find(".xml") >= 0:
                    final = open(file_path, "w")
                    args = ["tidy", "-xml", temp_file_path]
                    p = Popen(args, stdout=final, stderr=PIPE)
                    stdout, stderr = p.communicate()
                    final.close()
                    if p.returncode != 0:
                        log.error(
                            "Tidy error. Formatting "
                            + file_path
                            + "  to "
                            + temp_file_path
                            + ". Error: "
                            + "-"
                            + stderr.decode()
                            + ". Command line: "
                            + " ".join(args)
                        )
                        return False, 500
                    else:
                        os.remove(temp_file_path)
                else:
                    os.rename(temp_file_path, file_path)
            else:
                log.error(
                    "Incomplete submission {} in project {} of user {} with assistant {}".format(
                        unique_id, project, user, assistant
                    )
                )
        except Exception as e:
            log.error(
                "Submission "
                + str(unique_id)
                + " has POST error key: "
                + key
                + " Error: "
                + str(e)
                + ". URL: "
                + request.url
            )
    if xml_file != "":
        tree = etree.parse(xml_file)
        root = tree.getroot()
        xform_id = root.get("id")
        if xform_id is not None:
            form_data = get_form_data(request, project, xform_id)
            if form_data is not None:
                if form_data["form_accsub"] == 1:
                    if form_data["form_schema"] is None:
                        total, t1, t2 = get_dataset_stats_for_form(
                            request.registry.settings, project, xform_id
                        )
                        if total >= int(
                            request.registry.settings.get("maximum.testing", "200")
                        ):
                            form_data["form_blocked"] = 1
                    if form_data["form_blocked"] == 0:
                        if assistant_has_form(
                            request, user, project, xform_id, assistant
                        ) or project_has_crowdsourcing(request, project):
                            media_path = os.path.join(
                                odk_dir,
                                *[
                                    "forms",
                                    form_data["form_directory"],
                                    "submissions",
                                    str(unique_id),
                                    "diffs",
                                ]
                            )
                            os.makedirs(media_path)
                            media_path = os.path.join(
                                odk_dir,
                                *[
                                    "forms",
                                    form_data["form_directory"],
                                    "submissions",
                                    str(unique_id),
                                ]
                            )
                            target_path = os.path.join(
                                odk_dir,
                                *["forms", form_data["form_directory"], "submissions"]
                            )
                            path = os.path.join(path, *["*.*"])
                            files = glob.glob(path)
                            xml_file = ""
                            for file in files:
                                base_file = os.path.basename(file)
                                if base_file.upper().find(".XML") >= 0:
                                    target_file = os.path.join(target_path, base_file)
                                    xml_file = target_file
                                    shutil.move(file, target_file)

                            for file in files:
                                base_file = os.path.basename(file)
                                if base_file.upper().find(".XML") < 0:
                                    target_file = os.path.join(media_path, base_file)
                                    shutil.move(file, target_file)

                            if xml_file != "":
                                continue_processing = True
                                res_code = 0
                                for a_plugin in plugins.PluginImplementations(
                                    plugins.IXMLSubmission
                                ):
                                    (
                                        continue_processing,
                                        res_code,
                                    ) = a_plugin.before_processing_submission(
                                        request,
                                        user,
                                        project,
                                        xform_id,
                                        assistant,
                                        xml_file,
                                    )
                                if continue_processing:
                                    res_code, message = convert_xml_to_json(
                                        odk_dir,
                                        xml_file,
                                        form_data["form_directory"],
                                        form_data["form_schema"],
                                        form_data["form_xmlfile"],
                                        user,
                                        project,
                                        xform_id,
                                        assistant,
                                        request,
                                    )
                                    for a_plugin in plugins.PluginImplementations(
                                        plugins.IXMLSubmission
                                    ):
                                        a_plugin.after_processing_submission(
                                            request,
                                            user,
                                            project,
                                            xform_id,
                                            assistant,
                                            res_code,
                                            xml_file,
                                        )
                                if res_code == 0:
                                    return True, 201
                                else:
                                    if res_code == 1:
                                        return False, 500
                                    else:
                                        return True, 201
                            else:
                                return False, 404
                        else:
                            log.error(
                                "Enumerator %s cannot submit data to %s",
                                assistant,
                                xform_id,
                            )
                            return False, 404
                    else:
                        log.error(
                            "The form {} is blocked and cannot accept submissions at the moment".format(
                                xform_id
                            )
                        )
                        return False, 404
                else:
                    log.error(
                        "The form {} does not accept submissions".format(xform_id)
                    )
                    return False, 404
            else:
                log.error(
                    "Submission for ID %s does not exist in the database", xform_id
                )
                return False, 404
        else:
            log.error("Submission does not have and ID")
            return False, 404
    else:
        log.error("Submission does not have an XML file")
        return False, 500


def get_html_from_diff(request, project, form, submission, revision):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    _ = request.translate
    diff_file = os.path.join(
        odk_dir,
        *[
            "forms",
            form_directory,
            "submissions",
            submission,
            "diffs",
            revision,
            revision + ".diff",
        ]
    )
    html_file = os.path.join(
        odk_dir,
        *[
            "forms",
            form_directory,
            "submissions",
            submission,
            "diffs",
            revision,
            revision + ".html",
        ]
    )

    if not os.path.exists(diff_file):
        message = (
            "Generating Diff HTML file error. Diff file for commit {} "
            "does not exist".format(diff_file)
        )
        log.error(message)
        return 1, _(
            "Generating Diff HTML file error. Diff file for such commit does not exist"
        )

    if not os.path.exists(html_file):
        args = ["diff2html", "-s", "side", "-o", "stdout", "-i", "file", diff_file]

        final = open(html_file, "w")
        p = Popen(args, stdout=final, stderr=PIPE)
        nada, stderr = p.communicate()
        final.close()
        if p.returncode == 0:
            soup = BeautifulSoup(open(html_file), "html.parser")
            for diff in soup.find_all("div", {"class": "d2h-files-diff"}):
                return 0, diff
            log.error(
                "BeautifulSoup was not able to find difference data in file {}".format(
                    html_file
                )
            )
            return 1, "BeautifulSoup was not able to find difference data"
        else:
            message = (
                "Generating HTML "
                + html_file
                + ". Error: "
                + "-"
                + stderr.decode()
                + ". Command line: "
                + " ".join(args)
            )
            log.error(message)
            return 1, message
    else:
        soup = BeautifulSoup(open(html_file), "html.parser")
        for diff in soup.find_all("div", {"class": "d2h-files-diff"}):
            return 0, diff
        log.error(
            "BeautifulSoup was not able to find difference data in file {}".format(
                html_file
            )
        )
        return 1, "BeautifulSoup was not able to find difference data"


def generate_diff(request, project, form, json_file_a, json_file_b):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    file_a = os.path.join(
        odk_dir,
        *["forms", form_directory, "submissions", json_file_a + ".ordered.json"]
    )
    file_b = os.path.join(
        odk_dir,
        *["forms", form_directory, "submissions", json_file_b + ".ordered.json"]
    )

    diff_id = str(uuid.uuid4())
    temp_dir = os.path.join(odk_dir, *["tmp", diff_id])
    os.makedirs(temp_dir)
    diff_file = os.path.join(odk_dir, *["tmp", diff_id, diff_id + ".diff"])
    html_file = os.path.join(odk_dir, *["tmp", diff_id, diff_id + ".html"])

    args = ["diff", "-u", file_a, file_b]

    final = open(diff_file, "w")
    p = Popen(args, stdout=final, stderr=PIPE)
    nada, stderr = p.communicate()
    final.close()
    if p.returncode == 1:
        args = ["diff2html", "-s", "side", "-o", "stdout", "-i", "file", diff_file]

        final = open(html_file, "w")
        p = Popen(args, stdout=final, stderr=PIPE)
        nada, stderr = p.communicate()
        final.close()
        if p.returncode == 0:
            soup = BeautifulSoup(open(html_file), "html.parser")
            for diff in soup.find_all("div", {"class": "d2h-files-diff"}):
                return 0, diff
            return 0, ""
        else:
            message = (
                "Generating HTML "
                + html_file
                + ". Error: "
                + "-"
                + stderr.decode()
                + ". Command line: "
                + " ".join(args)
            )
            log.error(message)
            return 1, message
    else:
        if p.returncode != 0:
            message = (
                "DIFF Error. Comparing "
                + file_a
                + "  to "
                + file_b
                + ". Error: "
                + "-"
                + stderr.decode()
                + ". Command line: "
                + " ".join(args)
            )
            log.error(message)
            return 1, message
        else:
            return 1, "The files are the same"


def store_new_version(
    request, user, project, form, submission, assistant, sequence, new_file, notes
):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    diff_path = os.path.join(
        odk_dir,
        *["forms", form_directory, "submissions", submission, "diffs", sequence]
    )
    try:
        os.makedirs(diff_path)
        current_file = os.path.join(
            odk_dir, *["forms", form_directory, "submissions", submission + ".json"]
        )
        backup_file = os.path.join(
            odk_dir,
            *[
                "forms",
                form_directory,
                "submissions",
                submission,
                "diffs",
                sequence,
                submission + ".json",
            ]
        )
        diff_file = os.path.join(
            odk_dir,
            *[
                "forms",
                form_directory,
                "submissions",
                submission,
                "diffs",
                sequence,
                sequence + ".diff",
            ]
        )
        try:
            shutil.copyfile(current_file, backup_file)
            temp_file_path = current_file + "~"
            try:
                with open(temp_file_path, "wb") as output_file:
                    shutil.copyfileobj(new_file, output_file)
                os.remove(current_file)
                os.rename(temp_file_path, current_file)

                args = ["diff", "-u", backup_file, current_file]

                final = open(diff_file, "w")
                p = Popen(args, stdout=final, stderr=PIPE)
                nada, stderr = p.communicate()
                final.close()
                if p.returncode == 1:
                    update_json_status(request, project, form, submission, 3)
                    project_of_assistant = get_project_from_assistant(
                        request, user, project, assistant
                    )
                    added, message = add_json_history(
                        request,
                        project,
                        form,
                        submission,
                        sequence,
                        3,
                        project_of_assistant,
                        assistant,
                        notes,
                    )
                    if not added:
                        return 1, message

                    return 0, ""
                else:
                    shutil.copyfile(backup_file, current_file)
                    if p.returncode != 0:
                        message = (
                            "DIFF Error. Comparing "
                            + current_file
                            + "  to "
                            + backup_file
                            + ". Error: "
                            + "-"
                            + stderr.decode()
                            + ". Command line: "
                            + " ".join(args)
                        )
                        log.error(message)
                        return 1, message
                    else:
                        return 1, "The files are the same"
            except Exception as e:
                log.error(str(e))
                if not os.path.exists(current_file):
                    shutil.copyfile(backup_file, current_file)
                return 1, "Cannot save new submission"
        except Exception as e:
            log.error(str(e))
            return 1, "Cannot create backup of current submission"
    except Exception as e:
        log.error(str(e))
        return 1, "Cannot created path for submission"


def restore_from_revision(request, project, form, submission, sequence):
    dok_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    current_file = os.path.join(
        dok_dir, *["forms", form_directory, "submissions", submission + ".json"]
    )
    backup_file = os.path.join(
        dok_dir,
        *[
            "forms",
            form_directory,
            "submissions",
            submission,
            "diffs",
            sequence,
            submission + ".json",
        ]
    )
    try:
        shutil.copyfile(backup_file, current_file)
        return 0, ""
    except Exception as e:
        log.error(str(e))
        return 1, "Cannot restore from revision " + sequence


def push_revision(
    request, user, project, form, submission, project_of_assistant, assistant
):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    schema = get_form_schema(request, project, form)
    current_file = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", submission + ".json"]
    )

    # Third we try to move the JSON data into the database
    mysql_user = request.registry.settings["mysql.user"]
    mysql_password = request.registry.settings["mysql.password"]
    mysql_host = request.registry.settings["mysql.host"]
    mysql_port = request.registry.settings["mysql.port"]
    log_file = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", "logs", submission + ".xml"]
    )
    imported_file = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", "logs", "imported.sqlite"]
    )
    maps_directory = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", "maps"]
    )
    manifest_file = os.path.join(
        odk_dir, *["forms", form_directory, "repository", "manifest.xml"]
    )
    uuid_file = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", submission + ".log"]
    )

    args = []
    json_to_mysql = os.path.join(
        request.registry.settings["odktools.path"], *["JSONToMySQL", "jsontomysql"]
    )

    with open(current_file, "r") as f:
        submission_data = json.load(f)
        try:
            submission_data["_geopoint"] = submission_data["_geopoint"].replace(
                "\\n", " "
            )
            submission_data["_geopoint"] = submission_data["_geopoint"].replace(
                "\n", " "
            )
            parts = submission_data["_geopoint"].split(" ")
            if len(parts) >= 4:
                submission_data["_latitude"] = parts[0]
                submission_data["_longitude"] = parts[1]
                submission_data["_elevation"] = parts[2]
                submission_data["_precision"] = parts[3]
            else:
                if len(parts) == 3:
                    submission_data["_latitude"] = parts[0]
                    submission_data["_longitude"] = parts[1]
                    submission_data["_elevation"] = parts[2]
                else:
                    if len(parts) == 2:
                        submission_data["_latitude"] = parts[0]
                        submission_data["_longitude"] = parts[1]
            if len(parts) >= 2:
                submission_data["_geolocation"] = {
                    "lat": submission_data["_latitude"],
                    "lon": submission_data["_longitude"],
                }
        except KeyError:
            pass
    with open(current_file, "w") as outfile:
        json_string = json.dumps(submission_data, indent=4, ensure_ascii=False)
        outfile.write(json_string)

    args.append(json_to_mysql)
    args.append("-H " + mysql_host)
    args.append("-P " + mysql_port)
    args.append("-u " + mysql_user)
    args.append("-p " + mysql_password)
    args.append("-s " + schema)
    args.append("-o " + log_file)
    args.append("-j " + current_file)
    args.append("-i " + imported_file)
    args.append("-M " + maps_directory)
    args.append("-m " + manifest_file)
    args.append("-U " + uuid_file)
    args.append("-O m")
    args.append("-w")
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:

        # Add the JSON to the Elastic Search index
        index_data = {
            "_submitted_date": submission_data.get("_submitted_date", ""),
            "_xform_id_string": submission_data.get("_xform_id_string", ""),
            "_submitted_by": submission_data.get("_submitted_by", ""),
            "_user_id": submission_data.get("_user_id", ""),
            "_project_code": submission_data.get("_project_code", ""),
            "_geopoint": submission_data.get("_geopoint", ""),
        }
        if submission_data.get("_geolocation", "") != "":
            index_data["_geolocation"] = submission_data.get("_geolocation", "")
        try:
            add_dataset(
                request.registry.settings,
                project,
                form,
                submission,
                index_data,
            )
        except Exception as e:
            message = (
                "ES Error while inserting on the dataset index. "
                "Project: {}. Form {}. Submission: {}.".format(
                    project, form, submission
                )
            )
            report_critical_error(request, user, project, form, "ES01", message)
            log.error(
                'ES Error "{}" with ID while inserting on the dataset index. '
                "Project: {}. Form {}. Submission: {}. Index data {}".format(
                    str(e), project, form, submission, index_data
                )
            )

        # Add the inserted records in the record index
        with open(uuid_file) as f:
            lines = f.readlines()
            for line in lines:
                parts = line.split(",")
                try:
                    add_record(
                        request.registry.settings,
                        project,
                        form,
                        schema,
                        parts[0],
                        parts[1].replace("\n", ""),
                    )
                except Exception as e:
                    message = (
                        "ES Error while inserting on the record index. "
                        "Project: {}. Form {}. Schema: {}. Table: {}. RowUUID: {}".format(
                            project, form, schema, parts[0], parts[1].replace("\n", "")
                        )
                    )
                    report_critical_error(request, user, project, form, "ES01", message)
                    log.error(
                        'ES Error "{}" while inserting on the record index. '
                        "Project: {}. Form {}. Schema: {}. Table: {}. RowUUID: {}".format(
                            str(e),
                            project,
                            form,
                            schema,
                            parts[0],
                            parts[1].replace("\n", ""),
                        )
                    )

        return 0, ""
    else:
        log.error(
            "JSONToMySQL error. Pushing "
            + current_file
            + ". Error: "
            + stdout.decode()
            + "-"
            + stderr.decode()
            + ". Command line: "
            + " ".join(args)
        )
        return 2, ""
