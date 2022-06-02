import gettext
import html
import os
import uuid
from subprocess import Popen, PIPE, check_call, CalledProcessError

from celery.utils.log import get_task_logger
from jinja2 import Environment, FileSystemLoader
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.processes.email.send_async_email import send_async_email
from formshare.processes.sse.messaging import send_task_status_to_form

log = get_task_logger(__name__)


class EmptyFileError(Exception):
    """
    Exception raised when there is an error while creating the repository.
    """


class GeneratingFileError(Exception):
    """
    Exception raised when there is an error while creating the repository.
    """


def get_fields_from_table(create_file, selected_fields):
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='maintable']")
    result = []
    if table is not None:
        for field in table.getchildren():
            if field.tag == "field":
                if field.get("name") in selected_fields:
                    desc = field.get("desc")
                    if desc == "" or desc == "Without label":
                        desc = field.get("name") + " - Without description"
                    data = {
                        "name": field.get("name"),
                        "desc": html.escape(desc),
                        "type": "string",
                    }
                    result.append(data)
            else:
                break
    return result


def internal_build_kml(
    settings,
    form_schema,
    kml_file,
    locale,
    form_id,
    create_file,
    selected_fields,
    options,
    task_id,
    task_object=None,
):
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

    dir_name = os.path.dirname(__file__)

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(dir_name, "templates")),
        trim_blocks=False,
    )

    odk_tools_dir = settings["odktools.path"]
    paths = ["utilities", "createTemporaryTable", "createtemporarytable"]
    create_temporary_table = os.path.join(odk_tools_dir, *paths)

    uid = str(uuid.uuid4())
    paths = ["tmp", uid]
    temp_dir = os.path.join(settings["repository.path"], *paths)
    os.makedirs(temp_dir)
    temp_table_name = "TMP_" + uid.replace("-", "_")

    args = [
        create_temporary_table,
        "-H " + settings["mysql.host"],
        "-P " + settings["mysql.port"],
        "-u " + settings["mysql.user"],
        "-p " + settings["mysql.password"],
        "-s " + form_schema,
        "-x " + create_file,
        "-r {}".format(options),
        "-t maintable",
        "-f " + "|".join(selected_fields),
        "-n " + temp_table_name,
        "-T " + temp_dir,
    ]
    send_task_status_to_form(settings, task_id, _("Querying data"))
    log.info(" ".join(args))
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        engine = create_engine(settings["sqlalchemy.url"], poolclass=NullPool)
        sql = (
            "SELECT count(surveyid) as total FROM "
            + form_schema
            + "."
            + temp_table_name
            + " WHERE _geopoint IS NOT NULL"
        )
        submissions = engine.execute(sql).fetchone()
        total = submissions.total

        sql = (
            "SELECT * FROM "
            + form_schema
            + "."
            + temp_table_name
            + " WHERE _geopoint IS NOT NULL"
        )
        submissions = engine.execute(sql).fetchall()
        records = []

        index = 0
        send_25 = True
        send_50 = True
        send_75 = True

        for a_submission in submissions:
            if task_object is not None:
                if task_object.is_aborted():
                    return
            index = index + 1
            percentage = (index * 100) / total
            # We report chucks to not overload the messaging system
            if 25 <= percentage <= 50:
                if send_25:
                    send_task_status_to_form(settings, task_id, _("25% processed"))
                    send_25 = False
            if 50 <= percentage <= 75:
                if send_50:
                    send_task_status_to_form(settings, task_id, _("50% processed"))
                    send_50 = False
            if 75 <= percentage <= 100:
                if send_75:
                    send_task_status_to_form(settings, task_id, _("75% processed"))
                    send_75 = False

            dict_submission = dict(a_submission)
            record_data = {
                "long": dict_submission.get("_longitude", 0),
                "lati": dict_submission.get("_latitude", 0),
                "fields": [],
            }
            for key, value in dict_submission.items():
                record_data["fields"].append({"name": key, "value": value})
            records.append(record_data)
        fields = get_fields_from_table(create_file, selected_fields)
        context = {
            "form_id": form_id,
            "fields": fields,
            "records": records,
        }

        if total > 0:
            send_task_status_to_form(settings, task_id, _("Rendering KML file"))
            rendered_template = template_environment.get_template("kml.jinja2").render(
                context
            )
            with open(kml_file, "w") as f:
                f.write(rendered_template)
            engine.dispose()
            cnf_file = settings["mysql.cnf"]
            args = [
                "mysql",
                "--defaults-file=" + cnf_file,
                "--execute=DROP TABLE " + form_schema + "." + temp_table_name,
            ]
            try:
                check_call(args)
            except CalledProcessError as e:
                error_message = "Error dropping table \n"
                error_message = error_message + "Error: \n"
                if e.stderr is not None:
                    error_message = error_message + e.stderr.encode() + "\n"
                log.error(error_message)

                email_from = settings.get("mail.from", None)
                email_to = settings.get("mail.error", None)
                send_async_email(
                    settings,
                    email_from,
                    email_to,
                    "KML Error - Dropping table",
                    "Error while dropping table {} in schema {}".format(
                        temp_table_name, form_schema
                    ),
                    None,
                    locale,
                )

                raise GeneratingFileError(
                    _("There was an error while dropping the temporary table")
                )
        else:
            engine.dispose()
            raise EmptyFileError(
                _("The ODK form does not contain any submissions with GPS coordinates")
            )
    else:  # pragma: no cover
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "createTemporaryTable Error",
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
            "createTemporaryTable Error: "
            + stderr.decode()
            + "-"
            + stdout.decode()
            + ". Args: "
            + " ".join(args)
        )
        raise GeneratingFileError(
            _("There was an error while querying data for the KML")
        )


@celeryApp.task(bind=True, base=CeleryTask)
def build_kml(
    self,
    settings,
    form_schema,
    kml_file,
    locale,
    form_id,
    create_file,
    fields,
    options,
    test_task_id=None,
):
    if test_task_id is None:
        task_id = build_kml.request.id
    else:
        task_id = test_task_id
    internal_build_kml(
        settings,
        form_schema,
        kml_file,
        locale,
        form_id,
        create_file,
        fields,
        options,
        task_id,
        self,
    )
