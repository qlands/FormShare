import gettext
from celery.utils.log import get_task_logger
from webhelpers2.html import literal
from lxml import etree
from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.models import get_engine
import json
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
    res_dict = {"": ""}
    for record in records:
        res_dict[record[0]] = record[1]
    return literal(json.dumps(res_dict))


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


def internal_build_kml(settings, form_schema, kml_file, locale):
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
    dict_data = dict(submissions)
    json_data = json.dumps(dict_data, default=str)
    submissions = json.loads(json_data)
    print("*******************************999")
    print(submissions)
    print("*******************************999")
    context = {
        "form_id": form_id,
        "fields": fields,
        "records": [],
    }

    if total > 0:
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
def build_kml(settings, form_schema, kml_file, locale):
    internal_build_kml(settings, form_schema, kml_file, locale)
