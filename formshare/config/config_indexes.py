import logging
from formshare.processes.logging.loggerclass import SecretLogger
import time

import requests
from formshare.config.elasticfeeds import configure_manager
from formshare.processes.elasticsearch.partner_index import (
    configure_partner_index_manager,
)
from formshare.processes.elasticsearch.record_index import create_record_index
from formshare.processes.elasticsearch.repository_index import create_dataset_index
from formshare.processes.elasticsearch.user_index import configure_user_index_manager
from requests.auth import HTTPBasicAuth

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def configure_indexes(settings):
    es_host = settings.get("elasticsearch.repository.host", "localhost")
    es_port = settings.get("elasticsearch.repository.port", 9200)

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
        "{}://{}:{}/".format(es_scheme, es_host, es_port),
        auth=HTTPBasicAuth(es_user, es_password),
    )
    data = resp.json()
    version = data["version"]["number"].split(".")
    if version[0] != "9":
        log.error("This version of FormShare requires ElasticSearch version 9.2.X")
    else:
        if version[1] != "2":
            log.error("This version of FormShare requires ElasticSearch version 9.2.X")

    # Load the feeds manager
    configure_manager(settings)
    # Load the user index manager
    configure_user_index_manager(settings)
    # Load the partner index
    configure_partner_index_manager(settings)
    # Creates the record index
    create_record_index(settings)
    # Creates the dataset index
    create_dataset_index(settings)
