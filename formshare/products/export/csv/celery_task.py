import gettext
import glob
import json
import os
import uuid
from subprocess import Popen, PIPE

from celery.utils.log import get_task_logger

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
    task_object=None,
    options=1,
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
        "-r {}".format(options),
    ]
    if protect_sensitive:
        args.append("-c")
    log.info(" ".join(args))
    if task_object is not None:
        if task_object.is_aborted():
            return
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
                "-l {}".format(options),
            ]
            if len(array_sizes) > 0:
                args.append("-a " + ",".join(array_sizes))

            if task_object is not None:
                if task_object.is_aborted():
                    return
            log.info(" ".join(args))
            p = Popen(args, stdout=PIPE, stderr=PIPE)
            send_task_status_to_form(settings, task_id, _("Creating CSV file"))
            stdout, stderr = p.communicate()
            if p.returncode == 0:
                parts = __file__.split("/products/")
                this_file_path = parts[0]
                flatten_json = os.path.join(
                    this_file_path, *["scripts", "flatten_jsons.py"]
                )

                args = [
                    flatten_json,
                    "--dummy_json",
                    dummy_json,
                    "--path_to_jsons",
                    out_path,
                    "--csv_file",
                    csv_file,
                ]
                log.info(" ".join(args))
                if task_object is not None:
                    if task_object.is_aborted():
                        return
                p = Popen(args, stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()
                if p.returncode != 0:  # pragma: no cover
                    email_from = settings.get("mail.from", None)
                    email_to = settings.get("mail.error", None)
                    send_async_email(
                        settings,
                        email_from,
                        email_to,
                        "Error while creating the flattening the JSON files",
                        "Error: "
                        + stderr.decode("utf-8")
                        + "-"
                        + stdout.decode("utf-8")
                        + ":"
                        + " ".join(args),
                        None,
                        locale,
                    )
                    raise DummyError(
                        _("Error while creating the flattening the JSON files")
                    )
            else:  # pragma: no cover
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


@celeryApp.task(bind=True, base=CeleryTask)
def build_csv(
    self,
    settings,
    maps_directory,
    create_xml_file,
    insert_xml_file,
    form_schema,
    csv_file,
    protect_sensitive,
    locale,
    test_task_id=None,
    options=1,
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
        self,
        options,
    )
