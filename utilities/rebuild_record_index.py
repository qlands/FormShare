import argparse
import glob
import os
import sys

import transaction
from formshare.models import Odkform
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models.meta import Base
from formshare.processes.elasticsearch.record_index import (
    create_record_index,
    add_record,
)
from pyramid.paster import get_appsettings, setup_logging


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
        try:
            repository_directory = settings.get("repository.path", "")
            forms = dbsession.query(Odkform).all()
            create_record_index(settings)
            total = 0
            for a_form in forms:
                if a_form.form_schema is not None:
                    form_directory = a_form.form_directory
                    parts = ["odk", "forms", form_directory, "submissions", "*.log"]
                    log_files = os.path.join(repository_directory, *parts)
                    files = glob.glob(log_files)
                    if files:
                        for a_file in files:
                            with open(a_file) as f:
                                lines = f.readlines()
                                for line in lines:
                                    parts = line.split(",")
                                    sql = "SELECT count(*) AS total_records FROM {}.{} WHERE rowuuid = '{}'".format(
                                        a_form.form_schema, parts[0], parts[1].strip()
                                    )
                                    records = dbsession.execute(sql).fetchone()
                                    if records.total_records > 0:
                                        total = total + 1
                                        add_record(
                                            settings,
                                            a_form.project_id,
                                            a_form.form_id,
                                            a_form.form_schema,
                                            parts[0],
                                            parts[1].replace("\n", ""),
                                        )
            print(total)

        except Exception as e:
            print("!!!! Error !!!!")
            print(str(e))
            sys.exit(1)
    engine.dispose()


if __name__ == "__main__":
    main()
