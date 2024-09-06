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

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def configure_indexes(settings):
    es_host = settings.get("elasticsearch.repository.host", "localhost")
    es_port = settings.get("elasticsearch.repository.port", 9200)
    use_ssl = settings.get("elasticsearch.repository.use_ssl", "False")
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

    resp = requests.get("http://{}:{}/".format(es_host, es_port))
    data = resp.json()
    version = data["version"]["number"].split(".")
    if version[0] != "7":
        log.error("This version of FormShare requires ElasticSearch version 7.14.X")
    else:
        if version[1] != "14":
            log.error("This version of FormShare requires ElasticSearch version 7.14.X")

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
