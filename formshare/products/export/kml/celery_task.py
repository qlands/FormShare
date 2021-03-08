import gettext
from celery.utils.log import get_task_logger
from formshare.processes.sse.messaging import send_task_status_to_form
from lxml import etree
from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.models import get_engine
import os
from jinja2 import Environment, FileSystemLoader

log = get_task_logger(__name__)


class EmptyFileError(Exception):
    """
        Exception raised when there is an error while creating the repository.
    """


def get_lookup_values(engine, schema, rtable, rfield):
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
    records = engine.execute(sql).fetchall()
    res_dict = {}
    for record in records:
        res_dict[record[0]] = record[1]
    return res_dict


def get_fields_from_table(engine, schema, create_file):
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='maintable']")
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
                    # "type": field.get("type"),
                    "type": "string",
                    "xmlcode": field.get("xmlcode"),
                    "size": field.get("size"),
                    "decsize": field.get("decsize"),
                    "sensitive": field.get("sensitive"),
                    "protection": field.get("protection", "None"),
                    "key": field.get("key", "false"),
                    "rlookup": field.get("rlookup", "false"),
                    "rtable": field.get("rtable", "None"),
                    "rfield": field.get("rfield", "None"),
                }
                if data["rlookup"] == "true":
                    data["lookupvalues"] = get_lookup_values(
                        engine, schema, data["rtable"], data["rfield"]
                    )
                result.append(data)
            else:
                break
    return result


def internal_build_kml(settings, form_schema, kml_file, locale, task_id):
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

    engine = get_engine(settings)
    sql = (
        "SELECT count(surveyid) as total FROM "
        + form_schema
        + ".maintable WHERE _geopoint IS NOT NULL"
    )
    submissions = engine.execute(sql).fetchone()
    total = submissions.total

    sql = "SELECT form_createxmlfile,form_id FROM formshare.odkform WHERE form_schema = '{}'".format(
        form_schema
    )
    res = engine.execute(sql).fetchone()
    create_file = res.form_createxmlfile
    form_id = res.form_id

    fields = get_fields_from_table(engine, form_schema, create_file)

    sql = "SELECT * FROM " + form_schema + ".maintable WHERE _geopoint IS NOT NULL"
    submissions = engine.execute(sql).fetchall()
    records = []

    index = 0
    send_25 = True
    send_50 = True
    send_75 = True

    for a_submission in submissions:
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
            found = False
            is_key = "false"
            is_lookup = "false"
            lookup_values = {}
            for a_field in fields:
                if a_field["name"] == key:
                    found = True
                    is_key = a_field["key"]
                    is_lookup = a_field["rlookup"]
                    lookup_values = a_field.get("lookupvalues", {})
            if found:
                if is_key == "true":
                    if is_lookup == "false":
                        field_value = value
                    else:
                        field_value = lookup_values.get(value)
                    record_data["fields"].append({"name": key, "value": field_value})
                    record_data["id"] = value
        for key, value in dict_submission.items():
            found = False
            is_key = "false"
            is_lookup = "false"
            lookup_values = {}
            for a_field in fields:
                if a_field["name"] == key:
                    found = True
                    is_key = a_field["key"]
                    is_lookup = a_field["rlookup"]
                    lookup_values = a_field.get("lookupvalues", {})
            if found:
                if is_key == "false":
                    if is_lookup == "false":
                        field_value = value
                    else:
                        field_value = lookup_values.get(value)
                    record_data["fields"].append({"name": key, "value": field_value})
        records.append(record_data)

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
    else:
        engine.dispose()
        raise EmptyFileError(
            _("The ODK form does not contain any submissions with GPS coordinates")
        )


@celeryApp.task(base=CeleryTask)
def build_kml(settings, form_schema, kml_file, locale, test_task_id=None):
    if test_task_id is None:
        task_id = build_kml.request.id
    else:
        task_id = test_task_id
    internal_build_kml(settings, form_schema, kml_file, locale, task_id)
