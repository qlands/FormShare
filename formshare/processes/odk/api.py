from lxml import etree
import os
import io
import json
import mimetypes
import shutil
from hashlib import md5
from pyramid.httpexceptions import HTTPNotFound
from uuid import uuid4
from subprocess import Popen, PIPE
from pyramid.response import FileResponse
from formshare.processes.db import (
    assistant_has_form,
    get_assistant_forms,
    get_project_id_from_name,
    add_new_form,
    form_exists,
    get_form_directory,
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
    get_form_geopoint,
    get_media_files,
    add_file_to_form,
    add_submission_same_as,
)
import uuid
import datetime
import re
from bs4 import BeautifulSoup
from pyxform import xls2xform
from pyxform.xls2json import parse_file_to_json
from pyxform.errors import PyXFormError
from formshare.processes.storage import (
    get_stream,
    response_stream,
    store_file,
    delete_stream,
)
from pyramid.response import Response
from formshare.processes.elasticsearch.repository_index import (
    create_dataset_index,
    add_dataset,
)
from formshare.processes.elasticsearch.record_index import (
    create_record_index,
    add_record,
)
import logging
import zipfile
import glob
from formshare.products.fs1import.fs1import import formshare_one_import_json
from formshare.processes.color_hash import ColorHash
import formshare.plugins as plugin
from formshare.products.repository import create_database_repository


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
    "get_html_from_diff",
    "generate_diff",
    "store_new_version",
    "restore_from_revision",
    "push_revision",
    "upload_odk_form",
    "update_form_title",
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
]

_GPS_types = [
    "add location prompt",
    "geopoint",
    "gps",
    "location",
    "q geopoint",
    "q location",
]


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


def update_form_title(request, project, form, title):
    xml_file = get_form_xml_file(request, project, form)
    tree = etree.parse(xml_file)
    root = tree.getroot()
    h_nsmap = root.nsmap["h"]
    form_title = root.findall(".//{" + h_nsmap + "}title")
    if form_title:
        form_title[0].text = title
    tree.write(xml_file, pretty_print=True, xml_declaration=True, encoding="utf-8")

    form_directory = get_form_directory(request, project, form)
    md5(open(xml_file, "rb").read()).hexdigest()
    odk_dir = get_odk_path(request)
    json_file = os.path.join(
        odk_dir, *["forms", form_directory, form.lower() + ".json"]
    )
    with open(json_file, "r") as f:
        json_metadata = json.load(f)
        json_metadata["name"] = title
        json_metadata["hash"] = "md5:" + md5(open(xml_file, "rb").read()).hexdigest()
        json_metadata["descriptionText"] = title
    with open(json_file, "w") as outfile:
        json_string = json.dumps(json_metadata, indent=4, ensure_ascii=False)
        outfile.write(json_string)


def get_geopoint_variable_from_json(json_dict, parent_array):
    result = None
    if json_dict["type"] == "survey" or json_dict["type"] == "group":
        if json_dict["type"] == "group":
            parent_array.append(json_dict["name"])
        for child in json_dict["children"]:
            result = get_geopoint_variable_from_json(child, parent_array)
            if result is not None:
                break
        if result is None:
            parent_array.pop()
    else:
        if json_dict["type"] in _GPS_types:
            result = json_dict["name"]
    return result


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
            return False, "Invalid Zip file"

    project_code = get_project_code_from_id(request, user, project)
    geopoint_variable = get_form_geopoint(request, project, form)
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
            geopoint_variable,
            project_of_assistant,
            ignore_xform,
        )
    if import_type == 2:
        pass  # We need to implement the BriefCase Import
    if import_type > 2:
        # We call connected plugins to see if there is other ways to import
        for a_plugin in plugin.PluginImplementations(plugin.IImportExternalData):
            a_plugin.import_external_data(
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
                geopoint_variable,
                project_of_assistant,
                import_type,
                form_post_data,
                ignore_xform,
            )

    return True, ""


def check_jxform_file(request, json_file, external_file=None):
    _ = request.translate
    jxform_to_mysql = os.path.join(
        request.registry.settings["odktools.path"], *["JXFormToMysql", "jxformtomysql"]
    )
    args = [
        jxform_to_mysql,
        "-j " + json_file,
        "-t maintable",
        "-v dummy",
        "-e " + os.path.join(os.path.dirname(json_file), *["tmp"]),
        "-o m",
        "-K",
    ]
    if external_file is not None:
        args.append(external_file)
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        try:
            root = etree.fromstring(stdout)
            files_array = []
            missing_files = root.findall(".//missingFile")
            for a_file in missing_files:
                files_array.append(a_file.get("fileName"))
            if len(files_array) > 0:
                return 0, ",".join(files_array)
            else:
                return 0, ""
        except Exception as e:
            log.info(
                "Checking JXForm returned 0 with no addition messages: {}".format(
                    str(e)
                )
            )
            return 0, ""
    else:
        if p.returncode == 23:
            log.error(
                ". Error: "
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            duplicated_tables = root.findall(".//duplicatedTable")
            message = (
                _("FormShare checks a little bit more your ODK for inconsistencies.")
                + "\n"
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
            return 23, message
        if p.returncode == 24:
            log.error(
                ". Error: "
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            invalid_names = root.findall(".//invalidName")
            message = (
                _("FormShare checks a little bit more your ODK for inconsistencies.")
                + "\n"
            )
            message = (
                message + _("The following variables are have invalid names:") + "\n"
            )
            if invalid_names:
                for a_name in invalid_names:
                    variable_name = a_name.get("name")
                    message = message + "\t" + variable_name + " \n"

                message = message + "\n" + _("Please change those names and try again.")
            return 24, message
        if p.returncode == 22:
            log.error(
                ". Error: "
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            duplicated_tables = root.findall(".//duplicatedItem")
            message = (
                _("FormShare checks a little bit more your ODK for inconsistencies.")
                + "\n"
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
            return 22, message
        if p.returncode == 9:
            log.error(
                ". Error: "
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            root = etree.fromstring(stdout)
            duplicated_items = root.findall(".//duplicatedItem")
            message = (
                _("FormShare checks a little bit more your ODK for inconsistencies.")
                + "\n"
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
        if p.returncode == 16:
            log.error(
                ". Error: "
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            message = (
                _("FormShare checks a little bit more your ODK for inconsistencies.")
                + "\n"
            )
            message = (
                message
                + _(
                    "The ODK you just submitted has a search statement in the appearance "
                    "column with a syntax that is not recognized by FormShare. Please "
                    "go to {} an raise an issue so the technical team can inspect your ODK and "
                    "find a solution."
                ).format("https://github.com/qlands/FormShare")
                + "\n"
            )
            return 9, message

        if p.returncode == 2:
            log.error(
                ". Error: "
                + "-"
                + stderr.decode()
                + " while checking PyXForm. Command line: "
                + " ".join(args)
            )
            message = (
                "\n"
                + _(
                    "FormShare manage your data in a better way but by doing so it has more "
                    "restrictions."
                )
                + "\n"
            )
            message = (
                message + _("The following tables have more than 64 selects: ") + "\n"
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
                    "We tent to organize our ODK forms in sections with questions around a topic. "
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
                    "FormShare store repeats as separate tables (like different Excel sheets) however "
                    "groups are not. FormShare store all items (questions, notes, calculations, etc.) "
                    'outside repeats into a table called "maintable". Thus "maintable" usually end up '
                    'with several items and if your ODK form have many selects then the "maintable" '
                    "could potentially have more than 64 selects. FormShare can only handle 64 selects "
                    "per table."
                )
                + "\n\n"
            )
            message = (
                message
                + _(
                    "You can bypass this restriction by creating groups of items inside repeats "
                    "BUT WITH repeat_count = 1. A repeat with repeat_count = 1 will behave in the same "
                    "way as a group but FormShare will create a new table for it to store all its items. "
                    "Eventually if you export the data to Excel your items will be organized in "
                    "different sheets each representing a table."
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


def upload_odk_form(request, project_id, user_id, odk_dir, form_data):
    _ = request.translate
    uid = str(uuid.uuid4())
    form_directory = uid
    paths = ["tmp", uid]
    os.makedirs(os.path.join(odk_dir, *paths))

    try:
        input_file = request.POST["xlsx"].file
        input_file_name = request.POST["xlsx"].filename.lower()
    except Exception as e:
        log.error("The post xlsx elements is empty. Error {}".format(str(e)))
        return False, _("No file was attached")

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
        eid = root.findall(".//{" + nsmap + "}" + parts[0])
        if eid:
            form_id = eid[0].get("id")
            if re.match(r"^[A-Za-z0-9_]+$", form_id):
                form_title = root.findall(".//{" + h_nsmap + "}title")
                if not form_exists(request, project_id, form_id):
                    error, message = check_jxform_file(
                        request, survey_file, itemsets_csv
                    )
                    if error == 0:
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
                        shutil.copyfile(file_name, final_xls)
                        shutil.copyfile(xml_file, final_xml)
                        shutil.copyfile(survey_file, final_survey)
                        parent_array = []
                        try:
                            geopoint = get_geopoint_variable_from_json(
                                json_dict, parent_array
                            )
                        except Exception as e:
                            geopoint = None
                            log.warning(
                                "Unable to extract GeoPoint from file {}. Error: {}".format(
                                    final_survey, str(e)
                                )
                            )
                        form_data["project_id"] = project_id
                        form_data["form_id"] = form_id
                        form_data["form_name"] = form_title[0].text
                        form_data["form_cdate"] = datetime.datetime.now()
                        form_data["form_directory"] = form_directory
                        form_data["form_accsub"] = 1
                        form_data["form_testing"] = 1
                        form_data["form_xlsfile"] = final_xls
                        form_data["form_xmlfile"] = final_xml
                        form_data["form_jsonfile"] = final_survey
                        form_data["form_pubby"] = user_id
                        form_data["form_hexcolor"] = ColorHash(form_id).hex
                        if geopoint is not None:
                            form_geopoint = "/".join(parent_array) + "/" + geopoint
                            if form_geopoint[0] == "/":
                                form_geopoint = form_geopoint[1:]

                            form_data["form_geopoint"] = form_geopoint
                        if message != "":
                            form_data["form_reqfiles"] = message

                        added, message = add_new_form(request, form_data)
                        if not added:
                            return added, message

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
                                        request, bucket_id, "itemsets.csv", itemset_file
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
                _("Cannot find XForm ID. Please post this ODK form in an issue on ")
                + "https://github.com/qlands/FormShare",
            )
    except PyXFormError as e:
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e).replace("'", "").replace('"', "").replace("\n", "")
    except Exception as e:
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e).replace("'", "").replace('"', "").replace("\n", "")


def update_odk_form(request, project_id, for_form_id, odk_dir, form_data):
    _ = request.translate
    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    os.makedirs(os.path.join(odk_dir, *paths))

    try:
        input_file = request.POST["xlsx"].file
        input_file_name = request.POST["xlsx"].filename.lower()
    except Exception as e:
        log.error("The post xlsx elements is empty. Error {}".format(str(e)))
        return False, _("No file was attached")

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
        eid = root.findall(".//{" + nsmap + "}" + parts[0])
        if eid:
            form_id = eid[0].get("id")
            if re.match(r"^[A-Za-z0-9_]+$", form_id):
                if form_id == for_form_id:
                    form_title = root.findall(".//{" + h_nsmap + "}title")
                    if form_exists(request, project_id, form_id):
                        error, message = check_jxform_file(
                            request, survey_file, itemsets_csv
                        )
                        if error == 0:
                            form_directory = get_form_directory(
                                request, project_id, form_id
                            )
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
                            shutil.copyfile(file_name, final_xls)
                            shutil.copyfile(xml_file, final_xml)
                            shutil.copyfile(survey_file, final_survey)
                            parent_array = []
                            try:
                                geopoint = get_geopoint_variable_from_json(
                                    json_dict, parent_array
                                )
                            except Exception as e:
                                geopoint = None
                                log.warning(
                                    "Unable to extract GeoPoint from file {}. Error: {}".format(
                                        final_survey, str(e)
                                    )
                                )
                            form_data["project_id"] = project_id
                            form_data["form_id"] = form_id
                            form_data["form_name"] = form_title[0].text
                            form_data["form_lupdate"] = datetime.datetime.now()
                            form_data["form_xlsfile"] = final_xls
                            form_data["form_xmlfile"] = final_xml
                            form_data["form_jsonfile"] = final_survey
                            if geopoint is not None:
                                form_geopoint = "/".join(parent_array) + "/" + geopoint
                                if form_geopoint[0] == "/":
                                    form_geopoint = form_geopoint[1:]
                                form_data["form_geopoint"] = form_geopoint
                            if message != "":
                                form_data["form_reqfiles"] = message

                            updated, message = update_form(
                                request, project_id, for_form_id, form_data
                            )
                            if not updated:
                                return updated, message

                            # If we have itemsets.csv add it as media files
                            if itemsets_csv is not None:
                                bucket_id = project_id + form_id
                                bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
                                try:
                                    delete_stream(request, bucket_id, "itemsets.csv")
                                except Exception as e:
                                    log.error(
                                        "Error {} removing filename {} from bucket {}".format(
                                            str(e), "itemsets.csv", bucket_id
                                        )
                                    )
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
                            return False, message
                    else:
                        return False, _("The form does not exists in this project")
                else:
                    return (
                        False,
                        _(
                            'The "form_id" of the current form does not match the "form_id" of the one you '
                            "uploaded. You cannot update a form with another form"
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
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e)
    except Exception as e:
        log.error(
            "Error {} while adding form {} in project {}".format(
                str(e), input_file_name, project_id
            )
        )
        return False, str(e)


class FileIterator(object):
    chunk_size = 4096

    def __init__(self, filename):
        self.filename = filename
        self.fileobj = open(self.filename, "rb")

    def __iter__(self):
        return self

    def next(self):
        chunk = self.fileobj.read(self.chunk_size)
        if not chunk:
            raise StopIteration
        return chunk

    __next__ = next  # py3 compat


# An Object containing the file download iterator
class FileIterable(object):
    def __init__(self, filename):
        self.filename = filename

    def __iter__(self):
        return FileIterator(self.filename)


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


def get_form_list(request, user, project_code, assistant):
    project_id = get_project_id_from_name(request, user, project_code)
    assistant_project = get_project_from_assistant(request, user, project_id, assistant)
    prj_list = []
    odk_dir = get_odk_path(request)
    forms = get_assistant_forms(request, project_id, assistant_project, assistant)
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


class ChangeDir:
    def __init__(self, new_path):
        self.newPath = os.path.expanduser(new_path)

    # Change directory with the new path
    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    # Return back to previous directory
    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


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
    os.makedirs(os.path.join(odk_dir, *["forms", xform_directory, "merging_files"]))
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

    print("*****************************101")
    print(" ".join(args))
    print("*****************************101")

    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        return 0, stdout.decode()
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
    default_language=None,
    other_languages=None,
    yes_no_strings=None,
    for_merging=False,
    merge_create_file=None,
    merge_insert_file=None,
):
    jxform_to_mysql = os.path.join(
        request.registry.settings["odktools.path"], *["JXFormToMysql", "jxformtomysql"]
    )

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
        if yes_no_strings == "":
            yes_no_strings = None
        if yes_no_strings is not None:
            args.append("-y '" + yes_no_strings + "'")
        args.append(
            "-e "
            + os.path.join(odk_dir, *["forms", xform_directory, "repository", "temp"])
        )
        args.append("-o m")
        if for_merging:
            args.append("-M")
            args.append("-r " + merge_create_file)
            args.append("-n " + merge_insert_file)

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

        print("*****************************100")
        print(" ".join(args))
        print("*****************************100")

        p = Popen(args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if p.returncode == 0:
            if not for_merging:
                schema = "P" + project[-12:] + "_D" + str(uuid.uuid4())[-12:]
                create_file = os.path.join(
                    odk_dir, *["forms", xform_directory, "repository", "create.sql"]
                )
                insert_file = os.path.join(
                    odk_dir, *["forms", xform_directory, "repository", "insert.sql"]
                )

                formshare_create_repository = True
                cnf_file = request.registry.settings["mysql.cnf"]
                for a_plugin in plugin.PluginImplementations(plugin.IRepository):
                    if formshare_create_repository:
                        formshare_create_repository = a_plugin.before_creating_repository(
                            request,
                            project,
                            form,
                            cnf_file,
                            create_file,
                            insert_file,
                            schema,
                        )
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
                    )
                    form_data = {"form_reptask": task}
                    update_form(request, project, form, form_data)
                    for a_plugin in plugin.PluginImplementations(plugin.IRepository):
                        a_plugin.on_creating_repository(request, project, form, task)

                custom_repository_process = False
                custom_task = None
                for a_plugin in plugin.PluginImplementations(plugin.IRepository):
                    custom_task = a_plugin.custom_repository_process(
                        request,
                        project,
                        form,
                        cnf_file,
                        create_file,
                        insert_file,
                        schema,
                        primary_key,
                    )
                    custom_repository_process = True
                    break  # Only one plugin implementing custom_repository_process will be called
                if custom_repository_process:
                    form_data = {"form_reptask": custom_task}
                    update_form(request, project, form, form_data)
                    for a_plugin in plugin.PluginImplementations(plugin.IRepository):
                        a_plugin.on_creating_repository(
                            request, project, form, custom_task
                        )

                return 0, ""
            else:
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
            with open(temp_json_file, "r") as f:
                submission_data = json.load(f)
                submission_data["_submitted_by"] = assistant
                submission_data["_submitted_date"] = datetime.datetime.now().isoformat()
                submission_data["_user_id"] = user
                submission_data.pop("_version", "")
                submission_data.pop("_id", "")
                submission_data["_submission_id"] = submission_id
                submission_data["_project_code"] = project_code
                geopoint_variable = get_form_geopoint(request, project, form)
                if geopoint_variable is not None:
                    if geopoint_variable in submission_data.keys():
                        submission_data["_geopoint"] = submission_data[
                            geopoint_variable
                        ]
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
                md5sum = md5(open(json_file, "rb").read()).hexdigest()
                sameas = get_submission_data(request, project, form, md5sum)
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
                        *[
                            "forms",
                            xform_directory,
                            "submissions",
                            "logs",
                            uuid_file_name,
                        ]
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
                    log.error(" ".join(args))
                    p = Popen(args, stdout=PIPE, stderr=PIPE)
                    stdout, stderr = p.communicate()
                    # An error 2 is an SQL error that goes to the logs
                    if p.returncode == 0 or p.returncode == 2:
                        project_of_assistant = get_project_from_assistant(
                            request, user, project, assistant
                        )
                        added, message = add_submission(
                            request,
                            project,
                            form,
                            project_of_assistant,
                            assistant,
                            submission_id,
                            md5sum,
                            p.returncode,
                        )

                        if not added:
                            log.error(message)
                            return 1, message

                        if p.returncode == 2:
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
                            )
                            if not added:
                                log.error(message)
                                return 1, message
                        else:
                            # Add the JSON to the Elastic Search index but only submissions without error
                            create_dataset_index(
                                request.registry.settings, user, project_code, form
                            )
                            add_dataset(
                                request.registry.settings,
                                user,
                                project_code,
                                form,
                                submission_id,
                                submission_data,
                            )
                            # Add the inserted records in the record index
                            create_record_index(
                                request.registry.settings, user, project_code, form
                            )
                            with open(uuid_file) as f:
                                lines = f.readlines()
                                for line in lines:
                                    parts = line.split(",")
                                    add_record(
                                        request.registry.settings,
                                        user,
                                        project_code,
                                        form,
                                        schema,
                                        parts[0],
                                        parts[1],
                                    )

                        return 0, ""
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
                        return 2, ""
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

                    move_media_files(
                        odk_dir, xform_directory, submission_id, sameas.submission_id
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
                    + stderr
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
            project_code = get_project_code_from_id(request, user, project)
            with open(json_file, "r") as f:
                submission_data = json.load(f)
                submission_data["_submitted_by"] = assistant
                submission_data["_submitted_date"] = datetime.datetime.now().isoformat()
                submission_data["_user_id"] = user
                submission_data["_submission_id"] = submission_id
                submission_data["_project_code"] = project_code
                geopoint_variable = get_form_geopoint(request, project, form)
                if geopoint_variable is not None:
                    try:
                        submission_data["_geopoint"] = submission_data[
                            geopoint_variable
                        ]
                    except KeyError:
                        pass

            # Adds the dataset to the Elastic Search index
            create_dataset_index(request.registry.settings, user, project_code, form)
            add_dataset(
                request.registry.settings,
                user,
                project_code,
                form,
                submission_id,
                submission_data,
            )

            with open(json_file, "w") as outfile:
                json_string = json.dumps(submission_data, indent=4, ensure_ascii=False)
                outfile.write(json_string)

            submissions_path = os.path.join(
                odk_dir, *["forms", xform_directory, "submissions", "*.json"]
            )
            files = glob.glob(submissions_path)
            md5sum = md5(open(json_file, "rb").read()).hexdigest()
            for aFile in files:
                if aFile != json_file:
                    othmd5sum = md5(open(aFile, "rb").read()).hexdigest()
                    if md5sum == othmd5sum:
                        target_submission_id = os.path.basename(aFile)
                        target_submission_id = target_submission_id.replace(".json", "")
                        move_media_files(
                            odk_dir,
                            xform_directory,
                            target_submission_id,
                            submission_id,
                        )
                        os.remove(aFile)
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


def store_submission(request, user, project, assistant):
    odk_dir = get_odk_path(request)
    unique_id = uuid4()
    path = os.path.join(odk_dir, *["submissions", str(unique_id)])
    os.makedirs(path)
    xml_file = ""
    for key in request.POST.keys():
        try:
            filename = request.POST[key].filename
            if filename.upper().find(".XML") >= 0:
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
            os.rename(temp_file_path, file_path)
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
                if assistant_has_form(request, user, project, xform_id, assistant):
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
                        odk_dir, *["forms", form_data["form_directory"], "submissions"]
                    )
                    path = os.path.join(path, *["*.*"])
                    files = glob.glob(path)
                    xml_file = ""
                    for file in files:
                        base_file = os.path.basename(file)
                        if base_file.upper().find(".XML") >= 0:
                            target_file = os.path.join(target_path, base_file)
                            xml_file = target_file
                        else:
                            target_file = os.path.join(media_path, base_file)
                        shutil.move(file, target_file)
                    if xml_file != "":
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
                        "Enumerator %s cannot submit data to %s", assistant, xform_id
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
        soup = BeautifulSoup(open(html_file), "html.parser")
        for diff in soup.find_all("div", {"class": "d2h-files-diff"}):
            return 0, diff


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


def push_revision(request, user, project, form, submission):
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
    args = []
    json_to_mysql = os.path.join(
        request.registry.settings["odktools.path"], *["JSONToMySQL", "jsontomysql"]
    )
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
    args.append("-O m")
    args.append("-w")
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        with open(current_file, "r") as f:
            submission_data = json.load(f)

            # Add the JSON to the Elastic Search index
            project_code = get_project_code_from_id(request, user, project)
            create_dataset_index(request.registry.settings, user, project_code, form)
            add_dataset(
                request.registry.settings,
                user,
                project_code,
                form,
                submission,
                submission_data,
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
