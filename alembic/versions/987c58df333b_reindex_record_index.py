"""Reindex record index

Revision ID: 987c58df333b
Revises: 5e28705dda28
Create Date: 2021-08-24 10:36:10.714706

"""
from pyramid.paster import get_appsettings
from alembic import context
from formshare.processes.elasticsearch.record_index import (
    create_connection,
    index_exists,
    create_record_index,
)
from sqlalchemy.orm.session import Session
from formshare.models.formshare import Odkform, Userproject, User, Project
from alembic import op
import time
import requests
import json

# revision identifiers, used by Alembic.
revision = "987c58df333b"
down_revision = "5e28705dda28"
branch_labels = None
depends_on = None


def check_es_ready(settings):
    es_host = settings.get("elasticsearch.records.host", "localhost")
    es_port = settings.get("elasticsearch.records.port", 9200)
    use_ssl = settings.get("elasticsearch.records.use_ssl", "False")
    ready = False
    print("Waiting for ES to be ready")
    while not ready:
        if use_ssl == "False":
            resp = requests.get("http://{}:{}/_cluster/health".format(es_host, es_port))
        else:
            resp = requests.get(
                "https://{}:{}/_cluster/health".format(es_host, es_port)
            )
        data = resp.json()
        if data["status"] == "yellow" or data["status"] == "green":
            ready = True
        else:
            time.sleep(30)
    print("ES is ready")


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
    settings = get_appsettings(config_uri, "formshare")

    es_host = settings.get("elasticsearch.records.host", "localhost")
    es_port = settings.get("elasticsearch.records.port", 9200)
    use_ssl = settings.get("elasticsearch.records.use_ssl", "False")

    session = Session(bind=op.get_bind())
    forms = (
        session.query(
            Odkform.project_id,
            Odkform.form_id,
            Project.project_code,
            User.user_id,
            Odkform.form_schema,
        )
        .filter(Odkform.project_id == Project.project_id)
        .filter(Odkform.project_id == Userproject.project_id)
        .filter(Userproject.access_type == 1)
        .filter(Userproject.user_id == User.user_id)
        .filter(Odkform.form_schema.isnot(None))
        .all()
    )
    if forms:
        check_es_ready(settings)

        create_record_index(settings)
        time.sleep(10)
        es_connection = create_connection(settings)
        check_es_ready(settings)
        for a_form in forms:
            index_name = "formshare_records_{}_{}_{}".format(
                a_form[3], a_form[2], a_form[1]
            )
            if index_exists(es_connection, index_name):
                reindex_dict = {
                    "source": {"index": index_name},
                    "dest": {
                        "index": settings.get(
                            "elasticsearch.records.index_name", "formshare_records"
                        )
                    },
                    "script": {
                        "inline": "ctx._source['project_id'] = '{}'; ctx._source['form_id'] = '{}';".format(
                            a_form[0], a_form[1]
                        )
                    },
                }
                json_data = json.dumps(reindex_dict)
                if use_ssl == "False":
                    result = requests.post(
                        "http://{}:{}/_reindex".format(es_host, es_port),
                        data=json_data,
                        headers={"Content-Type": "application/json"},
                    )
                else:
                    result = requests.post(
                        "https://{}:{}/_reindex".format(es_host, es_port),
                        data=json_data,
                        headers={"Content-Type": "application/json"},
                    )
                if result.status_code != 200:
                    exit(1)
                print("Index: {} . Has been reindex".format(index_name))
            else:
                print("Index: {} . Does not exist".format(index_name))
        check_es_ready(settings)
    session.commit()


def downgrade():
    print("Downgrade not possible")
