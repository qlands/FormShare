import gettext
import glob
import multiprocessing
import os
import time
import uuid
import zipfile
from subprocess import Popen, PIPE

from celery.utils.log import get_task_logger
from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.processes.email.send_async_email import send_async_email

log = get_task_logger(__name__)


class BuildFileError(Exception):
    """
    Exception raised when there is an error while creating the repository.
    """


class SheetNameError(Exception):
    """
    Exception raised when there is an error while creating the repository.
    """


def internal_build_zip_csv(
    settings,
    odk_dir,
    form_schema,
    form_id,
    create_xml,
    encryption_key,
    zip_file,
    protect_sensitive,
    locale,
    options=1,
    include_multiselect=False,
    include_lookups=False,
):
    if (
        os.environ.get("FORMSHARE_PYTEST_RUNNING", "false") == "true"
        and protect_sensitive
    ):
        print("In testing. Waiting 10 seconds so we can test cancelling the task")
        time.sleep(10)
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

    mysql_user = settings["mysql.user"]
    mysql_password = settings["mysql.password"]
    mysql_host = settings["mysql.host"]
    mysql_port = settings["mysql.port"]
    odk_tools_dir = settings["odktools.path"]

    paths = [odk_tools_dir, "utilities", "MySQLToCSV", "mysqltocsv"]
    mysql_to_csv = os.path.join(odk_dir, *paths)

    uid = str(uuid.uuid4())

    paths = ["tmp", uid]
    temp_dir = os.path.join(odk_dir, *paths)
    os.makedirs(temp_dir)

    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    output_path = os.path.join(odk_dir, *paths)
    os.makedirs(output_path)

    num_workers = (
        multiprocessing.cpu_count() - int(settings.get("server:threads", "1")) - 1
    )
    if num_workers <= 0:
        num_workers = 1

    args = [
        mysql_to_csv,
        "-H " + mysql_host,
        "-P " + mysql_port,
        "-u " + mysql_user,
        "-p " + mysql_password,
        "-s " + form_schema,
        "-x " + create_xml,
        "-o " + output_path,
        "-T " + temp_dir,
        "-e " + encryption_key,
        "-r {}".format(options),
        "-w {}".format(num_workers),
    ]
    if protect_sensitive:
        args.append("-c")
    if include_multiselect:
        args.append("-m")
    if include_lookups:
        args.append("-l")

    log.info(" ".join(args))

    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        with zipfile.ZipFile(
            file=zip_file, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as out_zip:
            for f in glob.glob(output_path + "/*.csv"):
                out_zip.write(f, arcname=os.path.basename(f))

        return True, zip_file
    else:
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "MySQLToCSV Error",
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
            "MySQLToCSV Error: "
            + stderr.decode()
            + "-"
            + stdout.decode()
            + ". Args: "
            + " ".join(args)
        )
        raise BuildFileError(
            _(
                "Unknown error while creating the CSV Zip. Sorry about this. "
                "Please report this error as an issue on https://github.com/qlands/FormShare"
            )
        )


@celeryApp.task(bind=True, base=CeleryTask)
def build_zip_csv(
    self,
    settings,
    odk_dir,
    form_schema,
    form_id,
    create_xml,
    encryption_key,
    zip_file,
    protect_sensitive,
    locale,
    options=1,
    include_multiselect=False,
    include_lookups=False,
):
    internal_build_zip_csv(
        settings,
        odk_dir,
        form_schema,
        form_id,
        create_xml,
        encryption_key,
        zip_file,
        protect_sensitive,
        locale,
        options,
        include_multiselect,
        include_lookups,
    )
