from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
import logging
from subprocess import Popen, PIPE
import os
import uuid
import gettext
from formshare.processes.email.send_async_email import send_async_email

log = logging.getLogger("formshare")


class BuildFileError(Exception):
    """
        Exception raised when there is an error while creating the repository.
    """


class SheetNameError(Exception):
    """
        Exception raised when there is an error while creating the repository.
    """


@celeryApp.task(base=CeleryTask)
def build_xlsx(
    settings,
    odk_dir,
    form_directory,
    form_schema,
    form_id,
    xlsx_file,
    protect_sensitive,
    locale,
):
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

    paths = ["forms", form_directory, "repository", "create.xml"]
    create_xml = os.path.join(odk_dir, *paths)

    paths = ["forms", form_directory, "repository", "insert.xml"]
    insert_xml = os.path.join(odk_dir, *paths)

    paths = [odk_tools_dir, "utilities", "MySQLToXLSX", "mysqltoxlsx"]
    mysql_to_xlsx = os.path.join(odk_dir, *paths)

    uid = str(uuid.uuid4())

    paths = ["tmp", uid]
    temp_dir = os.path.join(odk_dir, *paths)
    os.makedirs(temp_dir)

    args = [
        mysql_to_xlsx,
        "-H " + mysql_host,
        "-P " + mysql_port,
        "-u " + mysql_user,
        "-p " + mysql_password,
        "-s " + form_schema,
        "-x " + create_xml,
        "-I " + insert_xml,
        "-o " + xlsx_file,
        "-T " + temp_dir,
        "-f " + form_id,
        "-S",
    ]
    if protect_sensitive:
        args.append("-c")

    log.info(" ".join(args))

    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        return True, xlsx_file
    else:
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "MySQLToXLSX Error",
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
            "MySQLToXLSX Error: "
            + stderr.decode()
            + "-"
            + stdout.decode()
            + ". Args: "
            + " ".join(args)
        )
        error = stdout.decode() + stderr.decode()
        if error.find("Worksheet name is already in use") >= 0:
            raise SheetNameError(
                _(
                    "A worksheet name has been repeated. Excel only allow 30 characters in the worksheet name. "
                    "You can fix this by editing the dictionary and change the description of the tables to a maximum of "
                    "30 characters."
                )
            )
        else:
            raise BuildFileError(
                _(
                    "Unknown error while creating the XLSX. Sorry about this. "
                    "Please report this error as an issue on https://github.com/qlands/FormShare"
                )
            )
