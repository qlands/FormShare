"""The ElasticSearch indices are created by FormShare itself, the first time
it starts against an empty cluster. The suite's cluster has had them for
years, so the creation never runs: here it runs against index names of this
run, which are deleted again at the end.
"""

import uuid

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from formshare.processes.elasticsearch.partner_index import (
    configure_partner_index_manager,
)
from formshare.processes.elasticsearch.record_index import create_record_index
from formshare.processes.elasticsearch.repository_index import (
    create_dataset_index,
    delete_dataset_index_by_project,
)
from formshare.processes.elasticsearch.user_index import configure_user_index_manager

GROUPS = ["repository", "records", "user", "partner"]


def t_e_s_t_es_indexes(test_object):
    config = test_object.server_config
    suffix = "_pytest_" + uuid.uuid4().hex[:6]
    settings = dict(config)
    names = []
    for group in GROUPS:
        key = "elasticsearch.{}.index_name".format(group)
        settings[key] = config[key] + suffix
        names.append(settings[key])

    client = Elasticsearch(
        "http://{}:9200".format(config["elasticsearch.user.host"]),
        basic_auth=(
            config["elasticsearch.user.name"],
            config["elasticsearch.user.password"],
        ),
    )
    try:
        # Created on the first call, found on the second
        for _ in range(2):
            create_dataset_index(settings)
            create_record_index(settings)
            configure_user_index_manager(settings)
            configure_partner_index_manager(settings)
        for name in names:
            assert client.indices.exists(index=name)

        # Emptying an index of a project that put nothing in it
        delete_dataset_index_by_project(settings, "no_such_project")

        # A server that is not there, over TLS and behind a prefix: no
        # connection, and the index cannot be created. The client's
        # ConnectionError says so; RequestError, which used to be raised
        # here, cannot even be built without a response since elasticsearch 8
        unreachable = dict(settings)
        for group in GROUPS:
            unreachable["elasticsearch.{}.port".format(group)] = "9"
            unreachable["elasticsearch.{}.use_ssl".format(group)] = "True"
            unreachable["elasticsearch.{}.url_prefix".format(group)] = "es"
        for create in [
            create_dataset_index,
            create_record_index,
            configure_user_index_manager,
            configure_partner_index_manager,
        ]:
            refused = False
            try:
                create(unreachable)
            except ESConnectionError:
                refused = True
            assert refused
    finally:
        for name in names:
            client.indices.delete(index=name, ignore_unavailable=True)
        client.close()
