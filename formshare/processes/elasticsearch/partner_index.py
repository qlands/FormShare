from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError


class PartnerExistError(Exception):
    """
    Exception raised when ElasticSearch checks whether a partner already exists in the index.
    """

    def __str__(self):
        return "Link object already exists in network"


class PartnerNotExistError(Exception):
    """
    Exception raised when ElasticSearch checks whether a partner doesn't exists in the index.
    """

    def __str__(self):
        return "Link object does not exists in network"


def _get_partner_index_definition(number_of_shards, number_of_replicas):
    """
    Constructs the Partner index with a given number of shards and replicas.
    Each connection is stored as individual ES documents
    :param number_of_shards: Number of shards for the network index.
    :param number_of_replicas: Number of replicas for the network index.

    The index has the following parts:
         partner_id: Text. The ID of the partner
         partner_email: Text. The email of the partner
         parner_name: Text. The name of the partner
         partner_organization: Text. The organization of the partner

    :return: A dict object with the definition of the Partner index.
    """
    _json = {
        "settings": {
            "index": {
                "number_of_shards": number_of_shards,
                "number_of_replicas": number_of_replicas,
            },
            "analysis": {
                "filter": {
                    "email": {
                        "type": "pattern_capture",
                        "preserve_original": True,
                        "patterns": ["([^@]+)", "(\\p{L}+)", "(\\d+)", "@(.+)"],
                    }
                },
                "analyzer": {
                    "email": {
                        "tokenizer": "uax_url_email",
                        "filter": ["email", "lowercase", "unique"],
                    }
                },
            },
        },
        "mappings": {
            "properties": {
                "partner_id": {"type": "text"},
                "partner_email": {
                    "type": "text",
                    "copy_to": ["all_data", "partner_email2"],
                },
                "partner_name": {"type": "text", "copy_to": "all_data"},
                "partner_organization": {"type": "text", "copy_to": "all_data"},
                "all_data": {"type": "text", "analyzer": "standard"},
                "partner_email2": {"type": "text", "analyzer": "email"},
            }
        },
    }
    return _json


def _get_partner_search_dict(partner_id):
    """
    Constructs a ES search that will be used to search partners in the index
    :param partner_id: The partner to search if it exists
    :return: A dict that will be passes to ES
    """
    _dict = {"query": {"bool": {"must": {"term": {"_id": partner_id}}}}}
    return _dict


def get_partner_index_manager(request):
    return PartnerIndexManager(request.registry.settings)


def configure_partner_index_manager(settings):
    return PartnerIndexManager(settings)


class PartnerIndexManager(object):
    """
    The Manager class handles all partner operations.
    """

    def create_connection(self):
        """
        Creates a connection to ElasticSearch and pings it.
        :return: A tested (pinged) connection to ElasticSearch
        """
        if not isinstance(self.port, int):
            raise ValueError("Port must be an integer")
        if not isinstance(self.host, str):
            raise ValueError("Host must be string")
        if self.url_prefix is not None:
            if not isinstance(self.url_prefix, str):
                raise ValueError("URL prefix must be string")
        if not isinstance(self.use_ssl, bool):
            raise ValueError("Use SSL must be boolean")
        cnt_params = {"host": self.host, "port": self.port}
        if self.url_prefix is not None:
            cnt_params["url_prefix"] = self.url_prefix
        if self.use_ssl:
            cnt_params["use_ssl"] = self.use_ssl
        connection = Elasticsearch(
            [cnt_params],
            max_retries=100,
            retry_on_timeout=True,
            timeout=700,
            request_timeout=800,
        )
        if connection.ping():
            return connection
        else:
            return None

    def __init__(self, settings):
        """
        The constructor of the partner index manager. It creates the partner index if it doesn't exist. See
        https://www.elastic.co/guide/en/elasticsearch/reference/current/_basic_concepts.html#getting-started-shards-and-replicas
        for more information about shards and replicas
        :param settings: Pyramid settings.
        """

        try:
            self.host = settings["elasticsearch.partner.host"]
        except KeyError:
            self.host = "localhost"

        try:
            self.port = int(settings["elasticsearch.partner.port"])
        except KeyError:
            self.port = 9200

        try:
            self.index_name = settings["elasticsearch.partner.index_name"]
        except KeyError:
            self.index_name = "formshare_partners"

        try:
            self.url_prefix = settings["elasticsearch.partner.url_prefix"]
        except KeyError:
            self.url_prefix = None

        try:
            use_ssl = settings["elasticsearch.partner.use_ssl"]
            if use_ssl == "True":
                self.use_ssl = True
            else:
                self.use_ssl = False
        except KeyError:
            self.use_ssl = False

        try:
            number_of_shards = int(settings["elasticsearch.partner.number_of_shards"])
        except KeyError:
            number_of_shards = 5

        try:
            number_of_replicas = int(
                settings["elasticsearch.partner.number_of_replicas"]
            )
        except KeyError:
            number_of_replicas = 1

        connection = self.create_connection()
        if connection is not None:
            if not connection.indices.exists(self.index_name):
                try:
                    connection.indices.create(
                        self.index_name,
                        body=_get_partner_index_definition(
                            number_of_shards, number_of_replicas
                        ),
                    )
                except RequestError as e:
                    if e.status_code == 400:
                        if e.error.find("already_exists") >= 0:
                            pass
                        else:
                            raise e
                    else:
                        raise e

        else:
            raise RequestError("Cannot connect to ElasticSearch")

    def partner_exists(self, partner_id):
        """
        Check whether a partner already exists in the index
        :param partner_id: The link object to check if exists
        :return: True if exists otherwise False
        """
        connection = self.create_connection()
        if connection is not None:
            res = connection.search(
                index=self.index_name, body=_get_partner_search_dict(partner_id)
            )
            if res["hits"]["total"]["value"] > 0:
                return True
        else:
            raise RequestError("Cannot connect to ElasticSearch")
        return False

    def add_partner(self, partner_id, data_dict):
        """
        Adds a use to the index
        :param partner_id: The partner to add into the index
        :param data_dict: The data related to the partner as dict
        :return: The unique ID give to the link
        """

        if not self.partner_exists(partner_id):
            connection = self.create_connection()
            if connection is not None:
                connection.index(
                    index=self.index_name,
                    id=partner_id,
                    body=data_dict,
                )
            else:
                raise RequestError("Cannot connect to ElasticSearch")
        else:
            raise PartnerExistError()

    def remove_partner(self, partner_id):
        """
        Removes an partner from the index
        :param partner_id: The partner to be removed.
        :return: Bool
        """

        if self.partner_exists(partner_id):
            connection = self.create_connection()
            if connection is not None:
                connection.delete_by_query(
                    index=self.index_name,
                    body=_get_partner_search_dict(partner_id),
                )
                return True
            else:
                raise RequestError("Cannot connect to ElasticSearch")
        else:
            raise PartnerNotExistError()

    def update_partner(self, partner_id, data_dict):
        """
        Updates an partner in the index
        :param partner_id: The partner to be updated.
        :param data_dict: New partner data
        :return: Bool
        """
        if self.partner_exists(partner_id):
            connection = self.create_connection()
            if connection is not None:
                es_data_dict = {"doc": data_dict}
                connection.update(
                    index=self.index_name,
                    id=partner_id,
                    body=es_data_dict,
                )
                return True
            else:
                raise RequestError("Cannot connect to ElasticSearch")
        else:
            raise PartnerNotExistError()

    def query_partner(self, q, query_from, query_size):
        query = q.replace("*", "")
        if query.find("@") == -1:
            query_dict = {
                "query": {"wildcard": {"all_data": {"value": "*" + query + "*"}}}
            }
        else:
            query_dict = {
                "query": {"wildcard": {"partner_email2": {"value": "*" + query + "*"}}}
            }
        if query_from is not None:
            query_dict["from"] = query_from
        if query_size is not None:
            query_dict["size"] = query_size

        result = []
        connection = self.create_connection()
        if connection is not None:
            es_result = connection.search(index=self.index_name, body=query_dict)
            if es_result["hits"]["total"]["value"] > 0:
                total = es_result["hits"]["total"]["value"]
                for hit in es_result["hits"]["hits"]:
                    result.append(hit["_source"])
                return result, total
        else:
            raise RequestError("Cannot connect to ElasticSearch")
        return result, 0
