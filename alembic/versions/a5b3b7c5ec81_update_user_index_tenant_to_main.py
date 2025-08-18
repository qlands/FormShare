"""Update user index tenant to main

Revision ID: a5b3b7c5ec81
Revises: e7a8c6148f51
Create Date: 2025-08-17 16:44:21.908882

"""

import time

import requests
from alembic import context
from formshare.processes.elasticsearch.user_index import configure_user_index_manager
from pyramid.paster import get_appsettings, setup_logging
import json


# revision identifiers, used by Alembic.
revision = "a5b3b7c5ec81"
down_revision = "e7a8c6148f51"
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

    es_host = settings.get("elasticsearch.user.host", "localhost")
    es_port = settings.get("elasticsearch.user.port", 9200)
    use_ssl = settings.get("elasticsearch.user.use_ssl", "False")

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

    if use_ssl == "False":
        resp = requests.get(
            "http://{}:{}/_cat/indices?format=json".format(es_host, es_port)
        )
    else:
        resp = requests.get(
            "https://{}:{}/_cat/indices?format=json".format(es_host, es_port)
        )
    indexes = resp.json()
    user_index_found = False
    for an_index in indexes:
        if an_index["index"] == settings["elasticsearch.user.index_name"]:
            user_index_found = True

    if user_index_found:
        user_index = configure_user_index_manager(settings)

        update_by_query_body = {
            "script": {"source": "ctx._source.tenant_id = 'main'", "lang": "painless"},
            "query": {"match_all": {}},
        }
        headers = {"Content-Type": "application/json"}
        if use_ssl == "False":
            r = requests.post(
                "http://{}:{}/{}/_update_by_query?conflicts=proceed".format(
                    user_index.host, user_index.port, user_index.index_name
                ),
                data=json.dumps(update_by_query_body),
                headers=headers,
            )
        else:
            r = requests.post(
                "https://{}:{}/{}/_update_by_query?conflicts=proceed".format(
                    user_index.host, user_index.port, user_index.index_name
                ),
                data=json.dumps(update_by_query_body),
                headers=headers,
            )
        if r.status_code != 200:
            print("Cannot update with query")
            print(r.text)
            exit(1)


def downgrade():
    pass
