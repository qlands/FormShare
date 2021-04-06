"""Update _geolocation in index data

Revision ID: d9e72a903f87
Revises: e494ffd5ec8c
Create Date: 2020-04-21 13:38:28.047231

"""
import time

from pyramid.paster import get_appsettings, setup_logging
from sqlalchemy.orm.session import Session

from alembic import context
from alembic import op
from formshare.models.formshare import Odkform
from formshare.processes.elasticsearch.repository_index import (
    create_connection,
    get_all_datasets_with_gps,
)

# revision identifiers, used by Alembic.
revision = "d9e72a903f87"
down_revision = "e494ffd5ec8c"
branch_labels = None
depends_on = None


def upgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    if config_uri is None:
        print(
            "This migration needs parameter 'formshare.ini.file' in the alembic ini file."
        )
        print(
            "The parameter 'formshare.ini.file' must point to the full path of the FormShare ini file"
        )
        exit(1)

    setup_logging(config_uri)
    settings = get_appsettings(config_uri, "formshare")
    es_connection = create_connection(settings)
    if es_connection is None:
        print("Cannot connect to ElasticSearch")
        exit(1)
    session = Session(bind=op.get_bind())
    forms = session.query(Odkform.form_index).all()
    for a_form in forms:
        try:
            datasets = get_all_datasets_with_gps(settings, a_form.form_index, 10000)
            for a_dataset in datasets:
                dataset_id = a_dataset.get("_id")
                geo_point = a_dataset["_source"].get("_geopoint", "")
                parts = geo_point.split(" ")
                longitude = "null"
                latitude = "null"
                if len(parts) >= 4:
                    latitude = parts[0]
                    longitude = parts[1]
                else:
                    if len(parts) == 3:
                        latitude = parts[0]
                        longitude = parts[1]
                    else:
                        if len(parts) == 2:
                            latitude = parts[0]
                            longitude = parts[1]
                if longitude != "null" and latitude != "null":
                    new_loc = {
                        "doc": {"_geolocation": {"lat": latitude, "lon": longitude,}}
                    }

                    try:
                        es_connection.update(
                            index=a_form.form_index,
                            id=dataset_id,
                            body=new_loc,
                            doc_type="_doc",
                            request_timeout=1200,
                        )
                    except Exception as e:
                        print("********************************E")
                        print(str(e))
                        print("---------------------------------")
                        print(a_form.form_index)
                        print("----------------------------------")
                        print(dataset_id)
                        print("----------------------------------")
                        print("{},{}".format(latitude, longitude))
                        print("********************************E")

        except Exception as e:
            print(str(e))
        time.sleep(10)  # Allow ElasticSearch to apply the update across shards
    session.commit()


def downgrade():
    print("No downgrade necessary")
