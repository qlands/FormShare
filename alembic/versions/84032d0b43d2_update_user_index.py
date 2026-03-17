"""Update user index

Revision ID: 84032d0b43d2
Revises: 6c4832148100
Create Date: 2025-08-06 05:38:28.138245

"""

import time

import requests
from alembic import context
from formshare.processes.elasticsearch.user_index import configure_user_index_manager
import logging
from formshare.app import load_settings_from_ini
import json
from requests.auth import HTTPBasicAuth

# revision identifiers, used by Alembic.
revision = "84032d0b43d2"
down_revision = "6c4832148100"
branch_labels = None
depends_on = None


def upgrade():
    new_mapping = {"properties": {"tenant_id": {"type": "text", "copy_to": "all_data"}}}

    config_uri = context.config.get_main_option("formshare.ini.file", None)
    if config_uri is None:
        print(
            "This migration needs parameter 'formshare.ini.file' in the alembic ini file."
        )
        print(
            "The parameter 'formshare.ini.file' must point to the full path of the FormShare ini file"
        )
        exit(1)

    logging.basicConfig(level=logging.INFO)
    settings = load_settings_from_ini(config_uri)

    es_host = settings.get("elasticsearch.user.host", "localhost")
    es_port = settings.get("elasticsearch.user.port", 9200)
    use_ssl = settings.get("elasticsearch.user.use_ssl", "False")
    es_user = settings.get("elasticsearch.user.name", "empty")
    es_password = settings.get("elasticsearch.user.password", "empty")
    es_scheme = settings.get("elasticsearch.user.scheme", "http")

    ready = False
    print("Waiting for ES to be ready")
    while not ready:
        resp = requests.get(
            "{}://{}:{}/_cluster/health".format(es_scheme, es_host, es_port),
            auth=HTTPBasicAuth(es_user, es_password),
        )
        data = resp.json()
        if data["status"] == "yellow" or data["status"] == "green":
            ready = True
        else:
            time.sleep(30)
    print("ES is ready")
    resp = requests.get(
        "{}://{}:{}/_cat/indices?format=json".format(es_scheme, es_host, es_port),
        auth=HTTPBasicAuth(es_user, es_password),
    )
    indexes = resp.json()
    user_index_found = False
    for an_index in indexes:
        if an_index["index"] == settings["elasticsearch.user.index_name"]:
            user_index_found = True

    if user_index_found:
        user_index = configure_user_index_manager(settings)
        es_connection = user_index.create_connection()
        es_connection.indices.put_mapping(
            new_mapping,
            index=user_index.index_name,
        )

        update_by_query_body = {
            "script": {"source": "ctx._source.tenant_id = ''", "lang": "painless"},
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
