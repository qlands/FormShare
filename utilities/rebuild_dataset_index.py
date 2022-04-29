import argparse
import sys

import transaction
from pyramid.paster import get_appsettings, setup_logging
from formshare.processes.elasticsearch.repository_index import (
    create_dataset_index,
    add_dataset,
)
from formshare.models import Odkform
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models.meta import Base
from formshare.processes.db.project import get_project_owner, get_project_code_from_id


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
                                index_data["_geolocation"] = {
                                    "lat": a_submission._latitude,
                                    "lon": a_submission._longitude,
                                }
                            print(index_data)
                            add_dataset(
                                settings,
                                a_form.project_id,
                                a_form.form_id,
                                a_submission.surveyid,
                                index_data,
                            )

                            pass
                        except Exception as e:
                            print(
                                "Error {} while recreating index form ID {}".format(
                                    str(e), ""
                                )
                            )
                else:
                    pass
        except Exception as e:
            print(str(e))
            sys.exit(1)
    engine.dispose()


if __name__ == "__main__":
    main()
