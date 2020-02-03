from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError


class UserExistError(Exception):
    """
        Exception raised when ElasticSearch checks whether a user already exists in the index.
    """

    def __str__(self):
        return "Link object already exists in network"


class UserNotExistError(Exception):
    """
        Exception raised when ElasticSearch checks whether a user doesn't exists in the index.
    """

    def __str__(self):
        return "Link object does not exists in network"


def _get_user_index_definition(number_of_shards, number_of_replicas):
    """
       Constructs the User index with a given number of shards and replicas.
       Each connection is stored as individual ES documents
       :param number_of_shards: Number of shards for the network index.
       :param number_of_replicas: Number of replicas for the network index.

       The index has the following parts:
            user_id: Single word. The ID of the user
            user_email: Text. The email of the user
            user_name: Text. The name of the user
            user_about: Text. The about of the user
            user_cdate: Date. The date when the user was created

       :return: A dict object with the definition of the User index.
    """
    _json = {
        "settings": {
            "index": {
                "number_of_shards": number_of_shards,
                "number_of_replicas": number_of_replicas,
            }
        },
        "mappings": {
            "user": {
                "properties": {
                    "user_id": {"type": "keyword", "copy_to": "all_data"},
                    "user_email": {"type": "text", "copy_to": "all_data"},
                    "user_name": {"type": "text", "copy_to": "all_data"},
                    "all_data": {"type": "text", "analyzer": "standard"},
                }
            }
        },
    }
    return _json


def _get_user_search_dict(user_id):
    """
    Constructs a ES search that will be used to search users in the index
    :param user_id: The user to search if it exists
    :return: A dict that will be passes to ES
    """
    _dict = {"query": {"bool": {"must": {"term": {"user_id": user_id}}}}}
    return _dict


def get_user_index_manager(request):
    return UserIndexManager(request.registry.settings)


def configure_user_index_manager(settings):
    return UserIndexManager(settings)


class UserIndexManager(object):
    """
    The Manager class handles all activity feed operations.
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
        connection = Elasticsearch([cnt_params], max_retries=1)
        if connection.ping():
            return connection
        else:
            return None

    def __init__(self, settings):
        """
        The constructor of the user index manager. It creates the user index if it doesn't exist. See
        https://www.elastic.co/guide/en/elasticsearch/reference/current/_basic_concepts.html#getting-started-shards-and-replicas
        for more information about shards and replicas
        :param settings: Pyramid settings.
        """

        try:
            self.host = settings["elasticsearch.user.host"]
        except KeyError:
            self.host = "localhost"

        try:
            self.port = int(settings["elasticsearch.user.port"])
        except KeyError:
            self.port = 9200

        try:
            self.index_name = settings["elasticsearch.user.index_name"]
        except KeyError:
            self.index_name = "formshare_users"

        try:
            self.url_prefix = settings["elasticsearch.user.url_prefix"]
        except KeyError:
            self.url_prefix = None

        try:
            use_ssl = settings["elasticsearch.user.use_ssl"]
            if use_ssl == "True":
                self.use_ssl = True
            else:
                self.use_ssl = False
        except KeyError:
            self.use_ssl = False

        try:
            number_of_shards = int(settings["elasticsearch.user.number_of_shards"])
        except KeyError:
            number_of_shards = 5

        try:
            number_of_replicas = int(settings["elasticsearch.user.number_of_replicas"])
        except KeyError:
            number_of_replicas = 1

        connection = self.create_connection()
        if connection is not None:
            if not connection.indices.exists(self.index_name):
                try:
                    connection.indices.create(
                        self.index_name,
                        body=_get_user_index_definition(
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

    def user_exists(self, user_id):
        """
        Check whether a user already exists in the index
        :param user_id: The link object to check if exists
        :return: True if exists otherwise False
        """
        connection = self.create_connection()
        if connection is not None:
            res = connection.search(
                index=self.index_name, body=_get_user_search_dict(user_id)
            )
            if res["hits"]["total"] > 0:
                return True
        else:
            raise RequestError("Cannot connect to ElasticSearch")
        return False

    def add_user(self, user_id, data_dict):
        """
        Adds a use to the index
        :param user_id: The user to add into the index
        :param data_dict: The data related to the user as dict
        :return: The unique ID give to the link
        """

        if not self.user_exists(user_id):
            connection = self.create_connection()
            if connection is not None:
                connection.index(
                    index=self.index_name, doc_type="user", id=user_id, body=data_dict
                )
            else:
                raise RequestError("Cannot connect to ElasticSearch")
        else:
            raise UserExistError()

    def remove_user(self, user_id):
        """
        Removes an user from the index
        :param user_id: The user to be removed.
        :return: Bool
        """

        if self.user_exists(user_id):
            connection = self.create_connection()
            if connection is not None:
                connection.delete_by_query(
                    index=self.index_name,
                    doc_type="user",
                    body=_get_user_search_dict(user_id),
                )
                return True
            else:
                raise RequestError("Cannot connect to ElasticSearch")
        else:
            raise UserNotExistError()

    def update_user(self, user_id, data_dict):
        """
        Removes an user from the index
        :param user_id: The user to be removed.
        :param data_dict: New user data
        :return: Bool
        """
        if self.user_exists(user_id):
            connection = self.create_connection()
            if connection is not None:
                es_data_dict = {"doc": data_dict}
                connection.update(
                    index=self.index_name,
                    id=user_id,
                    doc_type="user",
                    body=es_data_dict,
                )
                return True
            else:
                raise RequestError("Cannot connect to ElasticSearch")
        else:
            raise UserNotExistError()

    def query_user(self, q, query_from, query_size):
        query = q.replace("*", "")
        query_dict = {"query": {"wildcard": {"all_data": {"value": "*" + query + "*"}}}}
        if query_from is not None:
            query_dict["from"] = query_from
        if query_size is not None:
            query_dict["size"] = query_size

        result = []
        connection = self.create_connection()
        if connection is not None:
            es_result = connection.search(index=self.index_name, body=query_dict)
            if es_result["hits"]["total"] > 0:
                total = es_result["hits"]["total"]
                for hit in es_result["hits"]["hits"]:
                    result.append(hit["_source"])
                return result, total
        else:
            raise RequestError("Cannot connect to ElasticSearch")
        return result, 0
