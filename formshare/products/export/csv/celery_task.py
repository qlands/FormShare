from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
import logging
import os
import gettext
import uuid
from subprocess import Popen, PIPE
import glob
from formshare.processes.sse.messaging import send_task_status_to_form
import json
from pandas import json_normalize
from collections import OrderedDict
import pandas as pd
from lxml import etree

log = logging.getLogger("formshare")


class EmptyFileError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """


class DummyError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """


class MySQLDenormalizeError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """


def flatten_json(y, separator="/"):
    out = OrderedDict()

    def flatten(x, name=""):
        if type(x) is OrderedDict:
            for a in x:
                flatten(x[a], name + a + separator)
        elif type(x) is list:
            i = 1
            for a in x:
                flatten(a, name + "[" + str(i) + "]" + separator)
                i += 1
        else:
            out[name[:-1]] = x.replace("\r\n", "").replace("\n", "").replace(",", "")

    flatten(y)
    return out


def gather_array_sizes(data, array_dict):
    for key, value in data.items():
        if type(value) is list:
            current_size = array_dict.get(key, 0)
            if len(value) > current_size:
                array_dict[key] = len(value)
            for an_item in value:
                gather_array_sizes(an_item, array_dict)


@celeryApp.task(base=CeleryTask)
def build_csv(
    settings,
    form_directory,
    form_schema,
    csv_file,
    protect_sensitive,
    locale,
    test_task_id=None,
):
    if test_task_id is None:
        task_id = build_csv.request.id
    else:
        task_id = test_task_id
    tables = {}
    keys = []
    replace_values = []

    def protect_field(table_name, field_name, field_value):
        for a_key in keys:
            if a_key["name"] == field_name:
                for a_value in replace_values:
                    if (
                        a_value["table"] == "all"
                        and a_value["field"] == field_name
                        and a_value["value"] == field_value
                    ):
                        return a_value["new_value"]
                unique_id = str(uuid.uuid4())
                replace_values.append(
                    {
                        "table": "all",
                        "field": field_name,
                        "value": field_value,
                        "new_value": unique_id,
                    }
                )
                return unique_id
        from_table = table_name
        if from_table == "":
            from_table = "maintable"
        fields = tables.get(from_table, [])
        for a_field in fields:
            if a_field["name"] == field_name:
                if a_field["protection"] == "exclude":
                    return "exclude"
                for a_value in replace_values:
                    if (
                        a_value["table"] == from_table
                        and a_value["field"] == field_name
                        and a_value["value"] == field_value
                    ):
                        return a_value["new_value"]
                unique_id = str(uuid.uuid4())
                replace_values.append(
                    {
                        "table": from_table,
                        "field": field_name,
                        "value": field_value,
                        "new_value": unique_id,
                    }
                )
                return unique_id
        return field_value

    def protect_sensitive_fields(json_data, table_name):
        for a_key, a_value in OrderedDict(json_data).items():
            if type(a_value) is list:
                for an_item in a_value:
                    if (
                        a_key != "_attachments"
                        and a_key != "_notes"
                        and a_key != "_tags"
                        and a_key != "_geolocation"
                    ):
                        protect_sensitive_fields(an_item, a_key)
            if a_key == "_geolocation":
                json_data.pop(a_key)
            else:
                new_value = protect_field(table_name, a_key, a_value)
                if new_value == "exclude":
                    json_data.pop(a_key)
                else:
                    json_data[a_key] = new_value

    def get_sensitive_fields(root, table_name):
        for child in root.iterchildren():
            if child.tag == "table":
                a_table = child.get("name")
                tables[a_table] = []
                get_sensitive_fields(child, a_table)
            else:
                if child.get("sensitive", "false") == "true":
                    is_key = child.get("key", "false")
                    is_lookup = child.get("rlookup", "false")
                    if is_key == "true":
                        is_key = True
                    else:
                        is_key = False
                    if is_lookup == "true":
                        is_lookup = True
                    else:
                        is_lookup = False
                    if not is_key:
                        tables[table_name].append(
                            {
                                "name": child.get("name"),
                                "protection": child.get("protection", "exclude"),
                                "lookup": is_lookup,
                            }
                        )
                    else:
                        keys.append({"name": child.get("name")})

    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

    paths = ["odk", "forms", form_directory, "submissions", "maps"]
    maps_path = os.path.join(settings["repository.path"], *paths)

    paths = ["utilities", "MySQLDenormalize", "mysqldenormalize"]
    mysql_denormalize = os.path.join(settings["odktools.path"], *paths)

    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    temp_path = os.path.join(settings["repository.path"], *paths)
    os.makedirs(temp_path)

    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    out_path = os.path.join(settings["repository.path"], *paths)
    os.makedirs(out_path)

    create_xml_file = os.path.join(
        settings["repository.path"],
        *["odk", "forms", form_directory, "repository", "create.xml"]
    )

    args = [
        mysql_denormalize,
        "-H " + settings["mysql.host"],
        "-P " + settings["mysql.port"],
        "-u " + settings["mysql.user"],
        "-p " + settings["mysql.password"],
        "-s " + form_schema,
        "-t maintable",
        "-c " + create_xml_file,
        "-m " + maps_path,
        "-o " + out_path,
        "-T " + temp_path,
        "-S",
    ]

    log.info(" ".join(args))

    send_task_status_to_form(settings, task_id, _("Denormalizing database"))
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:

        paths = ["*.json"]
        out_path2 = os.path.join(out_path, *paths)
        files = glob.glob(out_path2)
        if files:
            send_task_status_to_form(
                settings, task_id, _("Calculating the number of columns")
            )
            array_dict = {}
            for aFile in files:
                with open(aFile) as json_file:
                    data = json.load(json_file)
                    gather_array_sizes(data, array_dict)
            array_sizes = []
            for key, value in array_dict.items():
                array_sizes.append(key + ":" + str(value))

            paths = ["utilities", "createDummyJSON", "createdummyjson"]
            create_dummy_json = os.path.join(settings["odktools.path"], *paths)

            insert_xml_file = os.path.join(
                settings["repository.path"],
                *["odk", "forms", form_directory, "repository", "insert.xml"]
            )

            if protect_sensitive:
                tree = etree.parse(create_xml_file)
                element_root = tree.getroot()
                if len(element_root[0]):
                    get_sensitive_fields(element_root[0], "")
                if len(element_root[1]):
                    get_sensitive_fields(element_root[1], "")

            paths = ["dummy.djson"]
            dummy_json = os.path.join(out_path, *paths)

            args = [
                create_dummy_json,
                "-c " + create_xml_file,
                "-o " + dummy_json,
                "-i " + insert_xml_file,
                "-s",
                "-r",
            ]
            if len(array_sizes) > 0:
                args.append("-a " + ",".join(array_sizes))

            log.info(" ".join(args))

            p = Popen(args, stdout=PIPE, stderr=PIPE)

            p.communicate()
            if p.returncode == 0:
                dataframe_array = []

                # Adds the dummy
                with open(dummy_json) as json_file:
                    data = json.load(json_file, object_pairs_hook=OrderedDict)
                flat = flatten_json(data)
                temp = json_normalize(flat)
                cols = []
                for col in temp.columns:
                    cols.append(col.replace(".", ""))
                temp.columns = cols
                dataframe_array.append(temp)
                send_task_status_to_form(
                    settings, task_id, _("Flattening the JSON files")
                )
                for file in files:
                    with open(file) as json_file:
                        data = json.load(json_file, object_pairs_hook=OrderedDict)
                    replace_values = []
                    protect_sensitive_fields(data, "")
                    flat = flatten_json(data)
                    temp = json_normalize(flat)
                    cols = []
                    for col in temp.columns:
                        cols.append(col.replace(".", ""))
                    temp.columns = cols
                    dataframe_array.append(temp)
                send_task_status_to_form(
                    settings, task_id, _("Concatenating submissions")
                )
                join = pd.concat(dataframe_array, sort=False)
                join = join.iloc[1:]
                send_task_status_to_form(settings, task_id, _("Saving CSV"))
                join.to_csv(csv_file, index=False, encoding="utf-8")

            else:
                raise DummyError(_("Error while creating the dummy JSON file"))

        else:
            raise EmptyFileError(_("The ODK form does not contain any submissions"))
    else:
        log.error(
            "MySQLDenormalize Error: "
            + stderr.decode("utf-8")
            + "-"
            + stdout.decode("utf-8")
            + ":"
            + " ".join(args)
        )
        raise MySQLDenormalizeError(
            "MySQLDenormalize Error: "
            + stderr.decode("utf-8")
            + "-"
            + stdout.decode("utf-8")
        )
