import datetime
import glob
import imghdr
import json
import logging
import os
import re
import shutil
import uuid
from decimal import Decimal
from subprocess import Popen, PIPE

import paginate
import pandas as pd
from PIL import Image
from formshare.models.formshare import Submission, Jsonlog
from formshare.processes.color_hash import ColorHash
from formshare.processes.db import (
    get_form_schema,
    get_form_directory,
    get_form_xml_create_file,
    get_project_form_colors,
    add_json_log,
    get_dictionary_fields,
    get_dictionary_table_desc,
    get_dictionary_tables,
    update_dictionary_table_desc,
    update_dictionary_field_desc,
    update_dictionary_field_sensitive,
    get_form_survey_columns,
)
from formshare.processes.elasticsearch.record_index import (
    delete_form_records,
    delete_from_record_index,
)
from formshare.processes.elasticsearch.repository_index import (
    delete_dataset_from_index,
    delete_from_dataset_index,
    get_datasets_from_form,
    get_datasets_from_project,
)
from formshare.processes.odk import get_odk_path
from lxml import etree
from pandas import read_csv
from sqlalchemy import create_engine
from sqlalchemy import exc
from sqlalchemy.orm.session import Session
from sqlalchemy.pool import NullPool
from webhelpers2.html import literal
from zope.sqlalchemy import mark_changed

__all__ = [
    "get_submission_media_files",
    "json_to_csv",
    "get_gps_points_from_form",
    "get_gps_points_from_project",
    "get_tables_from_form",
    "get_tables_from_original_form",
    "update_table_desc",
    "update_field_metadata",
    "update_field_sensitive",
    "get_fields_from_table",
    "get_table_desc",
    "update_data",
    "get_request_data_jqgrid",
    "delete_submission",
    "delete_all_submission",
    "update_record_with_id",
    "get_dataset_info_from_file",
    "list_submission_media_files",
    "get_submission_media_file",
]

log = logging.getLogger("formshare")


def get_submission_media_file(
    request, project, form, submission, file_name, thumbnail=False
):
    form_directory = get_form_directory(request, project, form)
    odk_dir = get_odk_path(request)
    if not thumbnail:
        submissions_file = os.path.join(
            odk_dir, *["forms", form_directory, "submissions", submission, file_name]
        )
    else:
        submissions_file = os.path.join(
            odk_dir,
            *[
                "forms",
                form_directory,
                "submissions",
                submission,
                "thumbnails",
                file_name,
            ]
        )
    if os.path.exists(submissions_file):
        return submissions_file
    else:
        return None


def list_submission_media_files(request, project, form, submission):
    form_directory = get_form_directory(request, project, form)
    odk_dir = get_odk_path(request)
    submissions_path = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", submission, "*.*"]
    )

    thumbnails_path = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", submission, "thumbnails"]
    )
    if not os.path.exists(thumbnails_path):
        os.makedirs(thumbnails_path)

    files_array = []
    files = glob.glob(submissions_path)
    if files:
        for file in files:
            image = imghdr.what(file)
            if image is None:
                image = False
            else:
                image = True
            files_array.append({"file": os.path.basename(file), "image": image})
            if image:
                thumbnail_file = os.path.join(
                    odk_dir,
                    *[
                        "forms",
                        form_directory,
                        "submissions",
                        submission,
                        "thumbnails",
                        os.path.basename(file),
                    ]
                )
                if not os.path.exists(thumbnail_file):
                    try:
                        im = Image.open(file)
                        im.thumbnail((100, 100))
                        im.save(thumbnail_file)
                    except Exception as e:
                        log.error(
                            "Unable to create thumbnail file for {}. Error: {}".format(
                                file, str(e)
                            )
                        )
    return files_array


def get_dataset_info_from_file(request, project_id, form, submission_id):
    form_directory = get_form_directory(request, project_id, form)
    odk_path = get_odk_path(request)
    submission_file = os.path.join(
        odk_path, *["forms", form_directory, "submissions", submission_id + ".json"]
    )
    if not os.path.exists(submission_file):
        return None
    result = {}
    with open(submission_file) as json_file:
        data = json.load(json_file)
        for key, value in data.items():
            if type(value) is not list:
                result[key] = value
    return result


def get_gps_points_from_project(request, project_id, query_from=None, query_size=None):
    total, datasets = get_datasets_from_project(
        request.registry.settings, project_id, query_from, query_size
    )
    data = []
    colors = get_project_form_colors(request, project_id)
    for dataset in datasets:
        if "_geopoint" in dataset.keys():
            parts = dataset["_geopoint"].split(" ")
            if len(parts) >= 2:
                try:
                    float(parts[0])
                    try:
                        float(parts[1])
                        if dataset["_xform_id_string"] not in colors.keys():
                            color = ColorHash(dataset["_xform_id_string"]).hex
                        else:
                            color = colors[dataset["_xform_id_string"]]
                        data.append(
                            {
                                "key": dataset["_xform_id_string"],
                                "lati": parts[0],
                                "long": parts[1],
                                "options": {
                                    "iconShape": "circle-dot",
                                    "borderWidth": 5,
                                    "borderColor": color,
                                },
                            }
                        )
                    except Exception as e:
                        log.error(str(e) + " in " + dataset["_xform_id_string"])
                except Exception as e:
                    log.error(str(e) + " in " + dataset["_xform_id_string"])
    return True, {"points": data}


def get_gps_points_from_form(
    request, project_id, form_id, query_from=None, query_size=None
):
    total, datasets = get_datasets_from_form(
        request.registry.settings, project_id, form_id, query_from, query_size
    )
    data = []
    for dataset in datasets:
        if "_geopoint" in dataset.keys():
            parts = dataset["_geopoint"].split(" ")
            if len(parts) >= 2:
                try:
                    float(parts[0])
                    try:
                        float(parts[1])
                        data.append(
                            {
                                "key": dataset["_submission_id"],
                                "lati": parts[0],
                                "long": parts[1],
                            }
                        )
                    except Exception as e:
                        log.error(str(e) + " in " + dataset["_xform_id_string"])
                except Exception as e:
                    log.error(str(e) + " in " + dataset["_xform_id_string"])
    return True, {"points": data}


def get_submission_media_files(request, project, form, just_for_submissions=None):
    if just_for_submissions is None:
        just_for_submissions = []
    _ = request.translate
    uid = str(uuid.uuid4())
    form_directory = get_form_directory(request, project, form)
    odk_dir = get_odk_path(request)

    submissions_path = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", "*.json"]
    )
    submissions = glob.glob(submissions_path)
    if submissions:
        created = False
        for submission in submissions:
            submission_id = os.path.basename(submission).replace(".json", "")
            if just_for_submissions:
                if submission_id not in just_for_submissions:
                    continue
            tmp_dir = os.path.join(odk_dir, *["tmp", uid, submission_id])
            os.makedirs(tmp_dir)
            submissions_path = os.path.join(
                odk_dir, *["forms", form_directory, "submissions", submission_id, "*.*"]
            )
            files = glob.glob(submissions_path)
            if files:
                for file in files:
                    shutil.copy(file, tmp_dir)
                    created = True
        if created:
            tmp_dir = os.path.join(odk_dir, *["tmp", uid])
            zip_file = os.path.join(odk_dir, *["tmp", uid])
            shutil.make_archive(zip_file, "zip", tmp_dir)
            return True, zip_file + ".zip"

    return False, _("There are no media files to download")


def gather_array_sizes(data, array_dict):
    if type(data) is dict:
        for key, value in data.items():
            if type(value) is list:
                current_size = array_dict.get(key, 0)
                if len(value) > current_size:
                    array_dict[key] = len(value)
                for an_item in value:
                    gather_array_sizes(an_item, array_dict)


# def flatten_json(y, separator="/"):
#     out = OrderedDict()
#
#     def flatten(x, name=""):
#         if type(x) is OrderedDict:
#             for a in x:
#                 flatten(x[a], name + a + separator)
#         elif type(x) is list:
#             i = 1
#             for a in x:
#                 flatten(a, name + "[" + str(i) + "]" + separator)
#                 i += 1
#         else:
#             out[name[:-1]] = x
#
#     flatten(y)
#     return out


def flatten_json_2(request, temp_directory, input_file):
    repository_path = request.registry.settings["repository.path"]
    paths = ["tmp", temp_directory]
    temp_dir = os.path.join(repository_path, *paths)
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    temp_id = str(uuid.uuid4())
    paths = ["tmp", temp_directory, temp_id + ".csv"]
    output_file = os.path.join(repository_path, *paths)

    args = [
        "json2csv",
        "--flatten-objects",
        "--flatten-arrays",
        "--flatten-separator",
        "/",
        "-i",
        input_file,
        "-o",
        output_file,
    ]

    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        return output_file
    else:
        print(stderr)
    return None


def separate_multi_selects(data, table_name, tree_root):
    target_table = tree_root.find(".//table[@name='" + table_name + "']")
    copy_of_data = dict(data)
    for key, value in copy_of_data.items():
        if key.find("/") > 0:
            parts = key.split("/")
            variable_name = parts[len(parts) - 1]
        else:
            variable_name = key

        if type(value) is list:
            for an_item in value:
                separate_multi_selects(an_item, variable_name, tree_root)
        else:
            if target_table is not None:
                target_field = target_table.find(
                    ".//field[@name='" + variable_name + "']"
                )
                if target_field is not None:
                    if target_field.get("isMultiSelect", "false") == "true":
                        values = value.split(" ")
                        for a_value in values:
                            data[key + "/" + a_value] = "true"
                        data.pop(key)


def json_to_csv(request, project, form):
    _ = request.translate
    uid = str(uuid.uuid4())
    form_directory = get_form_directory(request, project, form)
    odk_dir = get_odk_path(request)
    # Create temporary directory
    tmp_dir = os.path.join(odk_dir, *["tmp", uid])
    os.makedirs(tmp_dir)
    # Copy all submissions to the temporary directory
    paths = ["forms", form_directory, "submissions", "*.json"]
    path = os.path.join(odk_dir, *paths)
    files = glob.glob(path)
    if files:
        for aFile in files:
            shutil.copy(aFile, tmp_dir)
    # Get all submissions
    paths = ["tmp", uid, "*.json"]
    path = os.path.join(odk_dir, *paths)
    files = glob.glob(path)
    if files:
        array_dict = {}
        create_xml_file = get_form_xml_create_file(request, project, form)
        tree_create = etree.parse(create_xml_file)
        root_create = tree_create.getroot()

        for aFile in files:
            with open(aFile) as json_file:
                data = json.load(json_file)
                gather_array_sizes(data, array_dict)
                new_data = data
            if new_data is not None:
                with open(aFile, "w") as outfile:
                    json_string = json.dumps(new_data, indent=4, ensure_ascii=False)
                    outfile.write(json_string)

        array_sizes = []
        for key, value in array_dict.items():
            array_sizes.append(key + ":" + str(value))

        # Create the dummy file
        paths = ["utilities", "createDummyJSON", "createdummyjson"]

        create_dummy_json = os.path.join(
            request.registry.settings["odktools.path"], *paths
        )

        if not os.path.exists(create_xml_file):
            return (
                False,
                _(
                    "This form was uploaded using an old version of ODK Tools. Please upload it again."
                ),
            )

        paths = ["dummy.djson"]
        dummy_json = os.path.join(tmp_dir, *paths)

        args = [
            create_dummy_json,
            "-c " + create_xml_file,
            "-o " + dummy_json,
        ]
        if len(array_sizes) > 0:
            args.append("-a " + ",".join(array_sizes))

        p = Popen(args, stdout=PIPE, stderr=PIPE)
        p.communicate()
        if p.returncode == 0:
            # try:
            temp_directory = str(uuid.uuid4())
            dataframe_array = []
            # Adds the dummy
            csv_file = flatten_json_2(request, temp_directory, dummy_json)
            if csv_file is not None:
                temp = read_csv(csv_file)
                cols = []
                for col in temp.columns:
                    cols.append(col.replace(".", ""))
                temp.columns = cols
                dataframe_array.append(temp)

            for file in files:
                csv_file = flatten_json_2(request, temp_directory, file)
                if csv_file is not None:
                    temp = read_csv(csv_file)
                    cols = []
                    for col in temp.columns:
                        cols.append(col.replace(".", ""))
                    temp.columns = cols
                    dataframe_array.append(temp)
            join = pd.concat(dataframe_array, sort=False)
            join = join.iloc[1:]
            paths = ["tmp", uid + ".csv"]
            csv_file = os.path.join(odk_dir, *paths)

            join.to_csv(csv_file, index=False, encoding="utf-8")
            return True, csv_file
            # except Exception as e:
            #     return False, str(e)
        else:
            return False, _("Error while creating dummy file")
    else:
        return False, _("There are no submissions to download")


def get_tables_from_original_form(request, project, form, include_lookups=False):
    """
    Get the tables as an array of dict from the original create XML file (Before merging)
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param include_lookups: If include lookups
    :return: Return an array of tables as dict
    """
    _ = request.translate
    result = []
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(
        odk_dir, *["forms", form_directory, "repository", "create.xml"]
    )
    if not os.path.isfile(create_file):
        return []
    tree = etree.parse(create_file)
    root = tree.getroot()
    element_lkp_tables = root.find(".//lkptables")
    element_tables = root.find(".//tables")
    # Append all tables
    tables = element_tables.findall(".//table")
    if tables:
        for table in tables:
            fields = []
            sfields = []
            num_sensitive = 0
            for field in table.getchildren():
                if field.tag == "field":
                    desc = field.get("desc", "")
                    if desc == "":
                        desc = _("Without description")
                    fields.append({"name": field.get("name"), "desc": desc})
                    sfields.append(field.get("name") + "-" + desc)
                    sensitive = field.get("sensitive", "false")
                    if sensitive == "true":
                        num_sensitive = num_sensitive + 1
            if table.get("name").find("_msel_") >= 0:
                multi = True
            else:
                multi = False
            result.append(
                {
                    "name": table.get("name"),
                    "desc": table.get("desc"),
                    "fields": fields,
                    "lookup": False,
                    "multi": multi,
                    "sfields": ",".join(sfields),
                    "numsensitive": num_sensitive,
                }
            )
    if include_lookups:
        # Append all lookup tables
        tables = element_lkp_tables.findall(".//table")
        if tables:
            for table in tables:
                fields = []
                sfields = []
                num_sensitive = 0
                for field in table.getchildren():
                    if field.tag == "field":
                        desc = field.get("desc", "")
                        if desc == "":
                            desc = _("Without description")
                        fields.append({"name": field.get("name"), "desc": desc})
                        sfields.append(field.get("name") + "-" + desc)
                        sensitive = field.get("sensitive", "false")
                        if sensitive == "true":
                            num_sensitive = num_sensitive + 1
                result.append(
                    {
                        "name": table.get("name"),
                        "desc": table.get("desc"),
                        "fields": fields,
                        "lookup": True,
                        "multi": False,
                        "sfields": ",".join(sfields),
                        "numsensitive": num_sensitive,
                    }
                )

    return result


def get_tables_from_form(request, project, form):
    """
    Get the tables as an array of dict from the DB or the create XML file
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :return: Return an array of tables as dict
    """
    _ = request.translate
    result = []
    tables = get_dictionary_tables(request, project, form, 1)
    if tables:
        for table in tables:
            fields = []
            sfields = []
            num_sensitive = 0
            db_fields = get_dictionary_fields(
                request, project, form, table["table_name"]
            )
            for field in db_fields:
                desc = field.get("field_desc", "")
                if desc == "":
                    desc = _("Without description")
                fields.append({"name": field.get("field_name"), "desc": desc})
                sfields.append(field.get("field_name") + "-" + desc)
                sensitive = _to_string(field.get("field_sensitive", 0))
                if sensitive == "true":
                    num_sensitive = num_sensitive + 1
            if table.get("table_name").find("_msel_") >= 0:
                multi = True
            else:
                multi = False
            result.append(
                {
                    "name": table.get("table_name"),
                    "desc": table.get("table_desc"),
                    "fields": fields,
                    "lookup": False,
                    "multi": multi,
                    "sfields": ",".join(sfields),
                    "numsensitive": num_sensitive,
                }
            )
    tables = get_dictionary_tables(request, project, form, 2)
    if tables:
        for table in tables:
            fields = []
            sfields = []
            num_sensitive = 0
            db_fields = get_dictionary_fields(
                request, project, form, table["table_name"]
            )
            for field in db_fields:
                desc = field.get("field_desc", "")
                if desc == "":
                    desc = _("Without description")
                fields.append({"name": field.get("field_name"), "desc": desc})
                sfields.append(field.get("field_name") + "-" + desc)
                sensitive = _to_string(field.get("field_sensitive", 0))
                if sensitive == "true":
                    num_sensitive = num_sensitive + 1
            result.append(
                {
                    "name": table.get("table_name"),
                    "desc": table.get("table_desc"),
                    "fields": fields,
                    "lookup": True,
                    "multi": False,
                    "sfields": ",".join(sfields),
                    "numsensitive": num_sensitive,
                }
            )
    if len(result) > 0:
        return result

    # If result is empty then use the create XML file
    log.info(
        "get_tables_from_form using XML file for form {} in project {}".format(
            form, project
        )
    )
    create_file = get_form_xml_create_file(request, project, form)
    if not os.path.isfile(create_file):
        return []
    tree = etree.parse(create_file)
    root = tree.getroot()
    element_lkp_tables = root.find(".//lkptables")
    element_tables = root.find(".//tables")
    # Append all tables
    tables = element_tables.findall(".//table")
    if tables:
        for table in tables:
            fields = []
            sfields = []
            num_sensitive = 0
            for field in table.getchildren():
                if field.tag == "field":
                    desc = field.get("desc", "")
                    if desc == "":
                        desc = _("Without description")
                    fields.append({"name": field.get("name"), "desc": desc})
                    sfields.append(field.get("name") + "-" + desc)
                    sensitive = field.get("sensitive", "false")
                    if sensitive == "true":
                        num_sensitive = num_sensitive + 1
            if table.get("name").find("_msel_") >= 0:
                multi = True
            else:
                multi = False
            result.append(
                {
                    "name": table.get("name"),
                    "desc": table.get("desc"),
                    "fields": fields,
                    "lookup": False,
                    "multi": multi,
                    "sfields": ",".join(sfields),
                    "numsensitive": num_sensitive,
                }
            )
    # Append all lookup tables
    tables = element_lkp_tables.findall(".//table")
    if tables:
        for table in tables:
            fields = []
            sfields = []
            num_sensitive = 0
            for field in table.getchildren():
                if field.tag == "field":
                    desc = field.get("desc", "")
                    if desc == "":
                        desc = _("Without description")
                    fields.append({"name": field.get("name"), "desc": desc})
                    sfields.append(field.get("name") + "-" + desc)
                    sensitive = field.get("sensitive", "false")
                    if sensitive == "true":
                        num_sensitive = num_sensitive + 1
            result.append(
                {
                    "name": table.get("name"),
                    "desc": table.get("desc"),
                    "fields": fields,
                    "lookup": True,
                    "multi": False,
                    "sfields": ",".join(sfields),
                    "numsensitive": num_sensitive,
                }
            )

    return result


def update_table_desc(request, project, form, table_name, description):
    """
    Update the description of a table in the DB and XML file
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table_name: Table name
    :param description: New description
    :return: Return True if successful or False
    """
    update_dictionary_table_desc(request, project, form, table_name, description)
    create_file = get_form_xml_create_file(request, project, form)
    if os.path.exists(create_file):
        tree = etree.parse(create_file)
        root = tree.getroot()
        table = root.find(".//table[@name='" + table_name + "']")
        if table is not None:
            table.set("desc", description)
        else:
            log.error("updateTables. Cannot find table " + table_name)
            return False

        try:
            # Crete a backup the first time the file is edited
            if not os.path.exists(create_file + ".bk"):
                shutil.copy(create_file, create_file + ".bk")
            tree.write(
                create_file, pretty_print=True, xml_declaration=True, encoding="utf-8"
            )
            return True
        except Exception as e:
            log.error("updateTables. Error updating create XML. Error:" + str(e))
        return False
    else:
        return False


def update_field_metadata(request, project, form, table_name, field_name, new_metadata):
    """
    Update the description of a field in the DB and in the XML file
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table_name: Table name
    :param field_name: Field name
    :param new_metadata: New metadata
    :return:
    """
    new_field_data = {}
    new_xml_data = {}
    for key, value in new_metadata.items():
        if key == "desc":
            new_field_data["field_desc"] = value
            new_xml_data["desc"] = value
        else:
            if key == "ontology":
                new_field_data["field_ontology"] = value
                new_xml_data["formshare_ontological_term"] = value
            else:
                new_field_data[key] = value
                new_xml_data[key] = value

    update_dictionary_field_desc(
        request, project, form, table_name, field_name, new_field_data
    )
    create_file = get_form_xml_create_file(request, project, form)
    if os.path.exists(create_file):
        tree = etree.parse(create_file)
        root = tree.getroot()
        table = root.find(".//table[@name='" + table_name + "']")
        if table is not None:
            field = table.find(".//field[@name='" + field_name + "']")
            if field is not None:
                for key, value in new_xml_data.items():
                    field.set(key, value)
            try:
                # Crete a backup the first time the file is edited
                if not os.path.exists(create_file + ".bk"):
                    shutil.copy(create_file, create_file + ".bk")
                tree.write(
                    create_file,
                    pretty_print=True,
                    xml_declaration=True,
                    encoding="utf-8",
                )
                return True
            except Exception as e:
                log.error("updateField. Error updating create XML. Error:" + str(e))
            return False
        else:
            return False
    else:
        return False


def update_field_sensitive(
    request, project, form, table_name, field_name, sensitive, protection="None"
):
    """
    Updates the sensitivity of a field in the DB and XML file
    :param request: Pyramid request Object
    :param project: Project ID
    :param form: Form ID
    :param table_name: Table name
    :param field_name: Field name
    :param sensitive: New sensitivity
    :param protection: New type of protection
    :return:
    """
    if sensitive:
        sensitive = "true"
        update_dictionary_field_sensitive(
            request, project, form, table_name, field_name, 1, protection
        )
    else:
        sensitive = "false"
        protection = "None"
        update_dictionary_field_sensitive(
            request, project, form, table_name, field_name, 0, "None"
        )
    create_file = get_form_xml_create_file(request, project, form)
    if os.path.exists(create_file):
        tree = etree.parse(create_file)
        root = tree.getroot()
        table = root.find(".//table[@name='" + table_name + "']")
        if table is not None:
            field = table.find(".//field[@name='" + field_name + "']")
            if field is not None:
                field.set("sensitive", sensitive)
                field.set("protection", protection)
                if sensitive == "true":
                    field.set("formshare_sensitive", "yes")
                else:
                    field.set("formshare_sensitive", "no")
            try:
                # Crete a backup the first time the file is edited
                if not os.path.exists(create_file + ".bk"):
                    shutil.copy(create_file, create_file + ".bk")
                tree.write(
                    create_file,
                    pretty_print=True,
                    xml_declaration=True,
                    encoding="utf-8",
                )
                return True
            except Exception as e:
                log.error("updateField. Error updating create XML. Error:" + str(e))
            return False
        else:
            return False
    else:
        return False


def field_is_editable(field_name):
    read_only_fields = [
        "surveyid",
        "originid",
        "_submitted_by",
        "_xform_id_string",
        "_submitted_date",
        "_geopoint",
        "_longitude",
        "_latitude",
        "instanceid",
        "rowuuid",
        "rowindex",
    ]
    if field_name in read_only_fields:
        return "false"
    return "true"


def get_lookup_values(request, project, form, rtable, rfield):
    schema = get_form_schema(request, project, form)
    sql = (
        "SELECT "
        + rfield
        + ","
        + rfield.replace("_cod", "_des")
        + " FROM "
        + schema
        + "."
        + rtable
    )
    records = request.dbsession.execute(sql).fetchall()
    res_dict = {"": ""}
    for record in records:
        res_dict[record[0]] = record[1]
    return literal(json.dumps(res_dict))


def get_protection_desc(request, protection_code):
    _ = request.translate
    if protection_code == "exclude":
        return _("Exclude it")
    if protection_code == "recode":
        return _("Recode it")
    if protection_code == "unlink":
        return _("Unlink it")
    return ""


def _to_string(value):
    if value == 1:
        return "true"
    else:
        return "false"


def get_fields_from_table(
    request, project, form, table_name, current_fields, get_values=True
):
    """
    This function get the fields of a table from the DB or the XML file
    :param request: Pyramid request
    :param project: Project ID
    :param form: Form ID
    :param table_name: Table
    :param current_fields: Current selected fields
    :param get_values: Get lookup values
    :return: Dict array of fields, whether or not some fields are checked
    """
    result = []
    checked = 0
    dict_fields = get_dictionary_fields(request, project, form, table_name)
    survey_columns = get_form_survey_columns(request, project, form)
    if dict_fields:
        for field in dict_fields:
            found = False
            if len(current_fields) != 0:
                if "rowuuid" not in current_fields:
                    current_fields.append("rowuuid")
            for cfield in current_fields:
                if field.get("field_name") == cfield:
                    found = True
                    checked = checked + 1
            desc = field.get("field_desc", "")
            if desc == "" or desc == "Without label":
                desc = field.get("field_name") + " - Without description"
            if field.get("field_key", 0) == 1:
                editable = "false"
            else:
                editable = field_is_editable(field.get("field_name"))
            data = {
                "name": field.get("field_name"),
                "desc": desc,
                "type": field.get("field_type"),
                "xmlcode": field.get("field_xmlcode"),
                "size": field.get("field_size"),
                "decsize": field.get("field_decsize"),
                "checked": found,
                "sensitive": _to_string(field.get("field_sensitive", 0)),
                "encrypted": _to_string(field.get("field_encrypted", 0)),
                "unique": _to_string(field.get("field_unique", 0)),
                "protection": field.get("field_protection", "None"),
                "ontology": field.get("field_ontology", "None"),
                "protection_desc": get_protection_desc(
                    request, field.get("field_protection", "None")
                ),
                "key": _to_string(field.get("field_key", 0)),
                "rlookup": _to_string(field.get("field_rlookup", 0)),
                "rtable": field.get("field_rtable", "None"),
                "rfield": field.get("field_rfield", "None"),
                "editable": editable,
            }

            if survey_columns is not None:
                for a_column in survey_columns:
                    data[a_column] = field.get(a_column)

            if data["rlookup"] == "true" and get_values:
                data["lookupvalues"] = get_lookup_values(
                    request, project, form, data["rtable"], data["rfield"]
                )
            result.append(data)
        return result, checked

    # If the dictionary does not exists in DB then use the XML file
    log.info(
        "get_fields_from_table using XML file for form {} in project {}".format(
            form, project
        )
    )
    create_file = get_form_xml_create_file(request, project, form)
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='" + table_name + "']")
    if table is not None:
        for field in table.getchildren():
            if field.tag == "field":
                found = False
                if len(current_fields) != 0:
                    if "rowuuid" not in current_fields:
                        current_fields.append("rowuuid")
                for cfield in current_fields:
                    if field.get("name") == cfield:
                        found = True
                        checked = checked + 1
                desc = field.get("desc")
                if desc == "" or desc == "Without label":
                    desc = field.get("name") + " - Without description"
                if field.get("key", "false") == "true":
                    editable = "false"
                else:
                    editable = field_is_editable(field.get("name"))
                data = {
                    "name": field.get("name"),
                    "desc": desc,
                    "type": field.get("type"),
                    "xmlcode": field.get("xmlcode"),
                    "size": field.get("size"),
                    "decsize": field.get("decsize"),
                    "checked": found,
                    "sensitive": field.get("sensitive"),
                    "protection": field.get("protection", "None"),
                    "protection_desc": get_protection_desc(
                        request, field.get("protection", "None")
                    ),
                    "key": field.get("key", "false"),
                    "rlookup": field.get("rlookup", "false"),
                    "rtable": field.get("rtable", "None"),
                    "rfield": field.get("rfield", "None"),
                    "editable": editable,
                }

                if data["rlookup"] == "true" and get_values:
                    data["lookupvalues"] = get_lookup_values(
                        request, project, form, data["rtable"], data["rfield"]
                    )
                result.append(data)
            else:
                break
    return result, checked


def get_table_desc(request, project, form, table_name):
    """
    Return the description of a table from DB or XML file
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table_name: Table Name
    :return: Description of a table or ""
    """
    desc = get_dictionary_table_desc(request, project, form, table_name)
    if desc is not None:
        return desc
    create_file = get_form_xml_create_file(request, project, form)
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='" + table_name + "']")
    if table is not None:
        return table.get("desc")
    return ""


def get_request_data_jqgrid(
    request,
    project,
    form,
    table_name,
    fields,
    current_page,
    length,
    table_order,
    order_direction,
    search_field,
    search_string,
    search_operator,
):
    _ = request.translate
    schema = get_form_schema(request, project, form)
    sql_fields = ",".join(fields)

    if search_field is None or search_string == "":
        sql = "SELECT " + sql_fields + " FROM " + schema + "." + table_name
        where_clause = ""
    else:
        sql = "SELECT " + sql_fields + " FROM " + schema + "." + table_name
        if search_operator == "like":
            sql = (
                sql
                + " WHERE LOWER("
                + search_field
                + ") like '%"
                + search_string.lower()
                + "%'"
            )
            where_clause = (
                " WHERE LOWER("
                + search_field
                + ") like '%"
                + search_string.lower()
                + "%'"
            )
        else:
            sql = (
                sql
                + " WHERE LOWER("
                + search_field
                + ") not like '%"
                + search_string.lower()
                + "%'"
            )
            where_clause = (
                " WHERE LOWER("
                + search_field
                + ") not like '%"
                + search_string.lower()
                + "%'"
            )

    count_sql = (
        "SELECT count(*) as total FROM " + schema + "." + table_name + where_clause
    )
    records = request.dbsession.execute(count_sql).fetchone()
    total = records.total

    collection = list(range(total))
    page = paginate.Page(collection, current_page, length)
    if page.first_item is not None:
        start = page.first_item - 1
    else:
        start = 0

    if table_order is not None:
        sql = sql + " ORDER BY " + table_order + " " + order_direction
    sql = sql + " LIMIT " + str(start) + "," + str(length)

    mark_changed(request.dbsession)
    records = request.dbsession.execute(sql).fetchall()
    data = []

    for i in range(len(fields)):
        if fields[i].find(" as ") >= 0:
            parts = fields[i].split(" as ")
            fields[i] = parts[1]

    if records is not None:
        for record in records:
            a_record = {}
            for field in fields:
                try:
                    if (
                        isinstance(record[field], datetime.datetime)
                        or isinstance(record[field], datetime.date)
                        or isinstance(record[field], datetime.time)
                    ):
                        a_record[field] = record[field].isoformat().replace("T", " ")
                    else:
                        if isinstance(record[field], float):
                            a_record[field] = str(record[field])
                        else:
                            if isinstance(record[field], Decimal):
                                a_record[field] = str(record[field])
                            else:
                                if isinstance(record[field], datetime.timedelta):
                                    a_record[field] = str(record[field])
                                else:
                                    a_record[field] = record[field]
                except Exception as e:
                    a_record[field] = (
                        _("AJAX Data error. Report this error as an issue on ")
                        + "https://github.com/qlands/FormShare"
                    )
                    log.error("AJAX Error in field " + field + ". Error: " + str(e))
            data.append(a_record)

    result = {
        "records": total,
        "page": current_page,
        "total": page.page_count,
        "rows": data,
    }
    return result


def update_data(request, user, project, form, table_name, row_uuid, field, value):
    _ = request.translate
    sql_url = request.registry.settings.get("sqlalchemy.url")
    schema = get_form_schema(request, project, form)
    sql = "UPDATE " + schema + "." + table_name + " SET " + field + " = '" + value + "'"
    sql = sql + " WHERE rowuuid = '" + row_uuid + "'"
    sql = sql.replace("''", "null")

    log.info(sql)
    engine = create_engine(sql_url, poolclass=NullPool)
    try:
        session = Session(bind=engine)
        session.execute("SET @odktools_current_user = '" + user + "'")
        session.execute(sql)
        session.commit()
        engine.dispose()
        res = {"data": {field: value}}
        return res
    except exc.IntegrityError as e:
        engine.dispose()
        p1 = re.compile(r"`(\w+)`")
        m1 = p1.findall(str(e))
        if m1:
            if len(m1) == 6:
                lookup = get_table_desc(request, project, form, m1[4])
                return {
                    "fieldErrors": [
                        {
                            "name": field,
                            "status": _(
                                "Cannot update value. Check the valid values in lookup table "
                            )
                            + '"'
                            + lookup
                            + '"',
                        }
                    ]
                }
        return {
            "fieldErrors": [
                {
                    "name": field,
                    "status": _(
                        "Cannot update value. Check the valid " "values in lookup table"
                    ),
                }
            ]
        }
    except Exception as ex:
        log.error(str(ex))
        return {"fieldErrors": [{"name": field, "status": "Unknown error"}]}


def delete_submission(
    request,
    user,
    project,
    form,
    row_uuid,
    project_code,
    deleted_by,
    move_to_logs=False,
    project_of_assistant=None,
    assistant=None,
):
    schema = get_form_schema(request, project, form)
    sql = (
        "SELECT surveyid FROM "
        + schema
        + ".maintable WHERE rowuuid = '"
        + row_uuid
        + "'"
    )
    records = request.dbsession.execute(sql).fetchone()
    submission_id = records.surveyid

    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)

    # Remove the submissions from the submission DB created by ODK Tools
    # So the submission could enter later on
    paths = ["forms", form_directory, "submissions", "logs", "imported.sqlite"]
    imported_db = os.path.join(odk_dir, *paths)
    sqlite_engine = "sqlite:///{}".format(imported_db)
    engine = create_engine(sqlite_engine, poolclass=NullPool)
    try:
        engine.execute(
            "DELETE FROM submissions WHERE submission_id ='{}'".format(submission_id)
        )
    except Exception as e:
        log.error(
            "Error {} removing submission {} from {}".format(
                str(e), submission_id, imported_db
            )
        )
        return False
    engine.dispose()

    if not move_to_logs:
        log.info(
            "DeleteSubmission: Submission {} in form {} for project {} was deleted by {}".format(
                submission_id, form, project, deleted_by
            )
        )
        # Try to remove all associated files
        try:
            paths = ["forms", form_directory, "submissions", submission_id]
            submissions_dir = os.path.join(odk_dir, *paths)
            shutil.rmtree(submissions_dir)
        except Exception as e:
            log.error(
                "Error deleting submission directory for id {}. Error: {}".format(
                    submission_id, str(e)
                )
            )
        try:
            paths = ["forms", form_directory, "submissions", submission_id + ".xml"]
            xml_file = os.path.join(odk_dir, *paths)
            os.remove(xml_file)
        except Exception as e:
            log.error(
                "Error deleting submission xml file for id {}. Error: {}".format(
                    submission_id, str(e)
                )
            )
        try:
            paths = [
                "forms",
                form_directory,
                "submissions",
                submission_id + ".json",
            ]
            json_file = os.path.join(odk_dir, *paths)
            os.remove(json_file)
        except Exception as e:
            log.error(
                "Error deleting submission json file for id {}. Error: {}".format(
                    submission_id, str(e)
                )
            )
        try:
            paths = [
                "forms",
                form_directory,
                "submissions",
                submission_id + ".ordered.json",
            ]
            json_file = os.path.join(odk_dir, *paths)
            os.remove(json_file)
        except Exception as e:
            log.error(
                "Error deleting ordered submission json file for id {}. Error: {}".format(
                    submission_id, str(e)
                )
            )
        try:
            paths = [
                "forms",
                form_directory,
                "submissions",
                submission_id + ".original.json",
            ]
            json_file = os.path.join(odk_dir, *paths)
            os.remove(json_file)
        except Exception as e:
            log.error(
                "Error deleting ordered submission json file for id {}. Error: {}".format(
                    submission_id, str(e)
                )
            )

    # Final steps. Delete indexes and data
    # Delete the record indices

    paths = ["forms", form_directory, "submissions", submission_id + ".log"]
    log_file = os.path.join(odk_dir, *paths)
    if not os.path.exists(log_file):
        paths = ["forms", form_directory, "submissions", "logs", submission_id + ".log"]
        log_file = os.path.join(odk_dir, *paths)

    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
            for line in lines:
                parts = line.split(",")
                try:
                    delete_from_record_index(
                        request.registry.settings,
                        parts[1].replace("\n", ""),
                    )
                except Exception as e:
                    log.error(
                        "Error while deleting record index without carry return for id {}. User:{}. "
                        "Project: {}. Form: {}. Rowuuid: {}. Error: {}. Trying with carry return".format(
                            submission_id,
                            user,
                            project_code,
                            form,
                            parts[1].replace("\n", ""),
                            str(e),
                        )
                    )
                    try:
                        delete_from_record_index(
                            request.registry.settings,
                            parts[1],
                        )
                    except Exception as e:
                        log.error(
                            "Error while deleting record index for id {}. User:{}. "
                            "Project: {}. Form: {}. Rowuuid: {}. Error: {}.".format(
                                submission_id,
                                user,
                                project_code,
                                form,
                                parts[1].replace("\n", ""),
                                str(e),
                            )
                        )
        os.remove(log_file)
    else:
        log.error(
            "Log file not found while deleting submission {} of form {} in project {} by user {}. "
            "Record index will not be synchronized".format(
                submission_id, form, project, deleted_by
            )
        )

    # Delete the dataset index
    try:
        delete_from_dataset_index(
            request.registry.settings, project, form, submission_id
        )
    except Exception as e:
        log.error(
            "Error wile deleting dataset index. User: {}. Project: {}. "
            "Form: {}. Submission: {}. Error: {}".format(
                user, project_code, form, submission_id, str(e)
            )
        )

    # Remove the submission from the repository database
    sql = "SET @odktools_current_user = '" + user + "'"
    request.dbsession.execute(sql)
    sql = "DELETE FROM " + schema + ".maintable WHERE rowuuid = '" + row_uuid + "'"
    request.dbsession.execute(sql)

    if not move_to_logs:
        # Remove the submission from FormShare
        request.dbsession.query(Submission).filter(
            Submission.project_id == project
        ).filter(Submission.form_id == form).filter(
            Submission.submission_id == submission_id
        ).delete()

    # If the submission goes to longs then create a log file for it
    # and add it to the logs
    if move_to_logs:
        paths = [
            "forms",
            form_directory,
            "submissions",
            "logs",
            submission_id + ".xml",
        ]
        new_log_file = os.path.join(odk_dir, *paths)
        paths = [
            "forms",
            form_directory,
            "submissions",
            submission_id + ".json",
        ]
        submission_file = os.path.join(odk_dir, *paths)

        root = etree.Element("XMLErrorLog")
        errors = etree.Element("errors")
        an_error = etree.Element(
            "error",
            FileUUID=submission_id,
            Error="Moved to logs by {}".format(user),
            Table="maintable",
            JSONVariable="",
            Notes="",
            RowInJSON="1",
        )
        an_error.text = "Moved to logs by {}".format(user)
        errors.append(an_error)
        root.append(errors)
        tree = etree.ElementTree(root)
        tree.write(
            new_log_file,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
        )
        added, message = add_json_log(
            request,
            project,
            form,
            submission_id,
            submission_file,
            new_log_file,
            1,
            project_of_assistant,
            assistant,
            "",
        )

        if not added:
            log.error(message)
            return False
        else:
            return True
    return True


def delete_all_submission(request, user, project, form, deleted_by):
    schema = get_form_schema(request, project, form)
    try:
        request.dbsession.query(Submission).filter(
            Submission.project_id == project
        ).filter(Submission.form_id == form).delete()
        request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
            Jsonlog.form_id == form
        ).delete()
        mark_changed(request.dbsession)

        odk_dir = get_odk_path(request)
        form_directory = get_form_directory(request, project, form)
        paths = ["forms", form_directory, "submissions"]
        submissions_dir = os.path.join(odk_dir, *paths)
        string_date = datetime.datetime.now().strftime("%Y_%m_%d:%H_%M_%S")
        deleted_string = "_deleted_by_{}_on_{}".format(user, string_date)
        shutil.move(submissions_dir, submissions_dir + deleted_string)
        paths = ["forms", form_directory, "submissions"]
        os.makedirs(os.path.join(odk_dir, *paths))
        paths = ["forms", form_directory, "submissions", "logs"]
        os.makedirs(os.path.join(odk_dir, *paths))
        paths = ["forms", form_directory, "submissions", "maps"]
        os.makedirs(os.path.join(odk_dir, *paths))

        sql = "SET @odktools_current_user = '" + user + "'"
        request.dbsession.execute(sql)
        sql = "DELETE FROM " + schema + ".maintable"
        request.dbsession.execute(sql)
        mark_changed(request.dbsession)
        log.info(
            "ZapSubmissions: User {} has deleted all submissions in form {} for project {} on {}".format(
                deleted_by, form, project, string_date
            )
        )
        delete_dataset_from_index(request.registry.settings, project, form)
        delete_form_records(request.registry.settings, project, form)

        return True, ""
    except Exception as e:
        log.error("Unable to remove submissions. Error {}".format(str(e)))
        return False, str(e)


def update_record_with_id(request, user, schema, table, rowuuid, data):
    sql = "DESC {}.{}".format(schema, table)
    fields = request.dbsession.execute(sql).fetchall()
    field_array = []
    key_array = []
    for a_field in fields:
        field_array.append(a_field[0])
        if a_field[3] == "PRI":
            key_array.append(a_field[0])
    data.pop("rowuuid", None)
    data.pop("rowindex", None)
    data.pop("apikey", None)
    for a_key in key_array:
        data.pop(a_key, None)
    fields_not_found = []
    for a_key in data.keys():
        if a_key not in field_array:
            fields_not_found.append(a_key)
    if len(fields_not_found) == 0:
        sql = "UPDATE {}.{}".format(schema, table) + " SET "
        updates = []
        for a_key in data.keys():
            updates.append(a_key + " = '{}'".format(data[a_key]))
        sql = sql + ",".join(updates)
        sql = sql + " WHERE rowuuid = '" + rowuuid + "'"
        sql_url = request.registry.settings.get("sqlalchemy.url")
        engine = create_engine(sql_url, poolclass=NullPool)
        try:
            session = Session(bind=engine)
            session.execute("SET @odktools_current_user = '" + user + "'")
            session.execute(sql)
            session.commit()
            engine.dispose()
            return True, ""
        except Exception as e:
            engine.dispose()
            return False, str(e)
    else:
        return (
            False,
            request.translate(
                "The following fields where not found in table {}".format(table)
            )
            + ": "
            + ",".join(fields_not_found),
        )
