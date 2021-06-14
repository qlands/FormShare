import gettext
import glob
import json
from celery.utils.log import get_task_logger
import os
import uuid
from collections import OrderedDict
from subprocess import Popen, PIPE

import pandas as pd
from pandas import json_normalize

from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.processes.email.send_async_email import send_async_email
from formshare.processes.sse.messaging import send_task_status_to_form

log = get_task_logger(__name__)


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


def internal_build_csv(
    settings,
    maps_directory,
    create_xml_file,
    insert_xml_file,
    form_schema,
    csv_file,
    protect_sensitive,
    locale,
    task_id,
):
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

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

    args = [
        mysql_denormalize,
        "-H " + settings["mysql.host"],
        "-P " + settings["mysql.port"],
        "-u " + settings["mysql.user"],
        "-p " + settings["mysql.password"],
        "-s " + form_schema,
        "-t maintable",
        "-x " + create_xml_file,
        "-m " + maps_directory,
        "-o " + out_path,
        "-T " + temp_path,
    ]
    if protect_sensitive:
        args.append("-c")
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

            paths = ["dummy.djson"]
            dummy_json = os.path.join(out_path, *paths)

            args = [
                create_dummy_json,
                "-c " + create_xml_file,
                "-o " + dummy_json,
                "-r",
            ]
            if len(array_sizes) > 0:
                args.append("-a " + ",".join(array_sizes))

            log.info(" ".join(args))

            p = Popen(args, stdout=PIPE, stderr=PIPE)

            stdout, stderr = p.communicate()
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

                    flat = flatten_json(data)
                    temp = json_normalize(flat)
                    cols = []
                    for col in temp.columns:
                        cols.append(col.replace(".", ""))
                    temp.columns = cols
                    dataframe_array.append(temp)
                send_task_status_to_form(settings, task_id, _("Joining submissions"))
                join = pd.concat(dataframe_array, sort=False)
                join = join.iloc[1:]
                send_task_status_to_form(settings, task_id, _("Saving CSV"))
                join.to_csv(csv_file, index=False, encoding="utf-8")
            else:
                email_from = settings.get("mail.from", None)
                email_to = settings.get("mail.error", None)
                send_async_email(
                    settings,
                    email_from,
                    email_to,
                    "Error while creating the dummy JSON file",
                    "Error: "
                    + stderr.decode("utf-8")
                    + "-"
                    + stdout.decode("utf-8")
                    + ":"
                    + " ".join(args),
                    None,
                    locale,
                )
                raise DummyError(_("Error while creating the dummy JSON file"))

        else:
            raise EmptyFileError(_("The ODK form does not contain any submissions"))
    else:
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "MySQLDenormalize Error",
            "Error: "
            + stderr.decode("utf-8")
            + "-"
            + stdout.decode("utf-8")
            + ":"
            + " ".join(args),
            None,
            locale,
        )
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


@celeryApp.task(base=CeleryTask)
def build_csv(
    settings,
    maps_directory,
    create_xml_file,
    insert_xml_file,
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
    internal_build_csv(
        settings,
        maps_directory,
        create_xml_file,
        insert_xml_file,
        form_schema,
        csv_file,
        protect_sensitive,
        locale,
        task_id,
    )
