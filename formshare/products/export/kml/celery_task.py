import gettext
import logging

import simplekml

from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.models import get_engine
from formshare.processes.sse.messaging import send_task_status_to_form

log = logging.getLogger("formshare")


class EmptyFileError(Exception):
    """
        Exception raised when there is an error while creating the repository.
    """


def internal_build_kml(settings, form_schema, kml_file, primary_key, locale, test_task_id=None):
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

    if test_task_id is None:
        task_id = build_kml.request.id
    else:
        task_id = test_task_id
    engine = get_engine(settings)
    sql = (
        "SELECT count(surveyid) as total FROM "
        + form_schema
        + ".maintable WHERE _geopoint IS NOT NULL"
    )
    submissions = engine.execute(sql).fetchone()
    total = submissions.total

    sql = (
        "SELECT "
        + primary_key
        + ",_geopoint FROM "
        + form_schema
        + ".maintable WHERE _geopoint IS NOT NULL"
    )
    submissions = engine.execute(sql).fetchall()
    index = 0
    send_25 = True
    send_50 = True
    send_75 = True
    if total > 0:
        kml = simplekml.Kml()
        for submission in submissions:
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
            geo_point = submission["_geopoint"]
            parts = geo_point.split(" ")
            if len(parts) >= 2:
                try:
                    key = submission[primary_key]
                    if not type(key) == str:
                        key = str(key)
                    kml.newpoint(name=key, coords=[(float(parts[1]), float(parts[0]))])
                except Exception as e:
                    log.error(
                        "Cannot process point for {}. Error {}".format(
                            submission[primary_key], str(e)
                        )
                    )
        engine.dispose()
        kml.save(kml_file)
    else:
        engine.dispose()
        raise EmptyFileError(
            _("The ODK form does not contain any submissions with GPS coordinates")
        )


@celeryApp.task(base=CeleryTask)
def build_kml(settings, form_schema, kml_file, primary_key, locale, test_task_id=None):
    internal_build_kml(settings, form_schema, kml_file, primary_key, locale, test_task_id)
