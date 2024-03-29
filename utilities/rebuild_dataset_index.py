import argparse
import glob
import json
import os
import sys
from pathlib import Path

import transaction
from formshare.models import Odkform
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models.meta import Base
from formshare.processes.db.project import get_project_owner, get_project_code_from_id
from formshare.processes.elasticsearch.repository_index import (
    create_dataset_index,
    add_dataset,
)
from pyramid.paster import get_appsettings, setup_logging


class Request(object):
    def __init__(self, dbsession):
        self.dbsession = dbsession


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    args = parser.parse_args()
    config_uri = args.ini_path
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, "formshare")

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        request = Request(dbsession)
        try:
            repository_directory = settings.get("repository.path", "")
            forms = dbsession.query(Odkform).all()
            create_dataset_index(settings)
            for a_form in forms:
                project_owner = get_project_owner(request, a_form.project_id)
                project_code = get_project_code_from_id(
                    request, project_owner, a_form.project_id
                )
                if a_form.form_schema is not None:
                    sql = (
                        "SELECT surveyid,_submitted_date,_xform_id_string,_submitted_by,"
                        "_geopoint,_latitude,_longitude FROM {}.maintable".format(
                            a_form.form_schema
                        )
                    )
                    submissions = dbsession.execute(sql).fetchall()
                    for a_submission in submissions:
                        try:
                            index_data = {
                                "_submitted_date": a_submission._submitted_date.isoformat(),
                                "_xform_id_string": a_submission._xform_id_string,
                                "_submitted_by": a_submission._submitted_by,
                                "_user_id": project_owner,
                                "_project_code": project_code,
                            }
                            if a_submission._geopoint is not None:
                                index_data["_geopoint"] = a_submission._geopoint
                                if (
                                    a_submission._latitude is not None
                                    and a_submission._longitude is not None
                                ):
                                    index_data["_geolocation"] = {
                                        "lat": a_submission._latitude,
                                        "lon": a_submission._longitude,
                                    }
                                else:
                                    parts = index_data["_geopoint"].split(" ")
                                    if len(parts) > 1:
                                        index_data["_geolocation"] = {
                                            "lat": parts[0],
                                            "lon": parts[1],
                                        }
                                    else:
                                        index_data["_geopoint"] = ""
                            else:
                                index_data["_geopoint"] = ""
                            print(index_data)
                            add_dataset(
                                settings,
                                a_form.project_id,
                                a_form.form_id,
                                a_submission.surveyid,
                                index_data,
                            )
                        except Exception as e:
                            print(
                                "Error {} while recreating index form ID {}".format(
                                    str(e), ""
                                )
                            )
                else:
                    form_directory = a_form.form_directory
                    parts = ["odk", "forms", form_directory, "submissions", "*.json"]
                    submissions = os.path.join(repository_directory, *parts)
                    files = glob.glob(submissions)
                    if files:
                        for a_file in files:
                            if (
                                a_file.find(".original.") < 0
                                and a_file.find(".ordered.") < 0
                            ):
                                f = open(a_file, "r")
                                data = json.load(f)
                                submission_id = Path(a_file).stem
                                index_data = {
                                    "_submitted_date": data.get("_submitted_date"),
                                    "_xform_id_string": data.get("_xform_id_string"),
                                    "_submitted_by": data.get("_submitted_by"),
                                    "_user_id": data.get("_user_id"),
                                    "_project_code": data.get("_project_code"),
                                }
                                if data.get("_geopoint", None) is not None:
                                    index_data["_geopoint"] = data["_geopoint"]
                                    if (
                                        data.get("_latitude", None) is not None
                                        and data.get("_longitude", None) is not None
                                    ):
                                        index_data["_geolocation"] = {
                                            "lat": data.get("_latitude"),
                                            "lon": data.get("_longitude"),
                                        }
                                    else:
                                        parts = data["_geopoint"].split(" ")
                                        if len(parts) > 1:
                                            index_data["_geolocation"] = {
                                                "lat": parts[0],
                                                "lon": parts[1],
                                            }
                                        else:
                                            index_data["_geopoint"] = ""
                                else:
                                    index_data["_geopoint"] = ""
                                print(index_data)
                                add_dataset(
                                    settings,
                                    a_form.project_id,
                                    a_form.form_id,
                                    submission_id,
                                    index_data,
                                )

        except Exception as e:
            print("!!!! Error !!!!")
            print(str(e))
            sys.exit(1)
    engine.dispose()


if __name__ == "__main__":
    main()
