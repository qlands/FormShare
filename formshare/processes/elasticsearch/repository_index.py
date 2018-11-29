from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError

def _get_dataset_index_definition(number_of_shards, number_of_replicas):
    """
       Constructs the dataset index with a given number of shards and replicas.
       Each connection is stored as individual ES documents
       :param number_of_shards: Number of shards for the network index.
       :param number_of_replicas: Number of replicas for the network index.

       The index has the following parts:
            _xform_id_string: Keyword. The ID of the form
            _submitted_by: Keyword. The assistant submitting the data 
            _user_id: Text. The user used in the submission as part of the URL
            _project_id: Text. The project used in the submission as part of the URL
            _submitted_date: Date. The date when the submission was done

       :return: A dict object with the definition of the dataset index.
    """
    _json = {
        "settings": {
            "index": {
                "number_of_shards": number_of_shards,
                "number_of_replicas": number_of_replicas
            }
        },
        "mappings": {
            "dataset": {
                "properties": {
                    "_submitted_date": {
                        "type": "date"
                    },
                    "_xform_id_string": {
                        "type": "keyword"
                    },
                    "_submitted_by": {
                        "type": "keyword"
                    },
                    "_user_id": {
                        "type": "keyword"
                    },
                    "_project_id": {
                        "type": "keyword"
                    }
                }
            }
        }
    }
    return _json


def get_search_dict_by_form(project_id, form_id):
    """
    Constructs a ES search that will be used to search for the datasets related to a form in a project
    :param project_id: The project to search for its datasets
    :param form_id: The form to search for its datasets
    :return: A dict that will be passes to ES
    """
    _dict = {
        "size": 1,
        "query": {
            "bool": {
                "must": [
                    {
                        "term": {
                            "_project_id": project_id
                        }
                    },
                    {
                        "term": {
                            "_xform_id_string": form_id
                        }
                    }
                ]
            }
        },
        "sort": [
            {
                "_submitted_date": {
                    "order": "desc"
                }
            }
        ]
    }
    return _dict


def get_search_dict_by_project(project_id):
    """
    Constructs a ES search that will be used to search for the datasets related to a form in a project
    :param project_id: The project to search for its datasets
    :return: A dict that will be passes to ES
    """
    _dict = {
        "size": 1,
        "query": {
            "bool": {
                "must": {
                    "term": {
                        "_project_id": project_id
                    }
                }
            }
        },
        "sort": [
            {
                "_submitted_date": {
                    "order": "desc"
                }
            }
        ]
    }
    return _dict


def get_dataset_index_manager(request):
    project_code = request.matchdict['projcode']
    user_id = request.matchdict['userid']
    return DatasetIndexManager(request.registry.settings, user_id, project_code)


def get_dataset_index_manager2(request, project_code, user_id):
    return DatasetIndexManager(request.registry.settings, user_id, project_code)


class DatasetIndexManager(object):
    """
    The Manager class handles all activity feed operations.
    """
    def create_connection(self):
        """
        Creates a connection to ElasticSearch and pings it.
        :return: A tested (pinged) connection to ElasticSearch
        """
        if not isinstance(self.port, int):
            raise ValueError('Port must be an integer')
        if not isinstance(self.host, str):
            raise ValueError('Host must be string')
        if self.url_prefix is not None:
            if not isinstance(self.url_prefix, str):
                raise ValueError('URL prefix must be string')
        if not isinstance(self.use_ssl, bool):
            raise ValueError('Use SSL must be boolean')
        cnt_params = {'host': self.host, 'port': self.port}
        if self.url_prefix is not None:
            cnt_params["url_prefix"] = self.url_prefix
        if self.use_ssl:
            cnt_params["use_ssl"] = self.use_ssl
        connection = Elasticsearch([cnt_params], max_retries=1)
        if connection.ping():
            return connection
        else:
            return None

    def __init__(self, settings, user_id, project_code):
        """
        The constructor of the dataset index manager. It creates the index if it doesn't exist. See
        https://www.elastic.co/guide/en/elasticsearch/reference/current/_basic_concepts.html#getting-started-shards-and-replicas
        for more information about shards and replicas
        :param settings: Pyramid settings.
        """
        self.user_id = user_id
        self.project_code = project_code

        try:
            self.host = settings['elasticsearch.repository.host']
        except KeyError:
            self.host = "localhost"

        try:
            self.port = int(settings['elasticsearch.repository.port'])
        except KeyError:
            self.port = 9200

        try:
            self.url_prefix = settings['elasticsearch.repository.url_prefix']
        except KeyError:
            self.url_prefix = None

        try:
            use_ssl = settings['elasticsearch.repository.use_ssl']
            if use_ssl == 'True':
                self.use_ssl = True
            else:
                self.use_ssl = False
        except KeyError:
            self.use_ssl = False

        try:
            number_of_shards = int(settings['elasticsearch.repository.number_of_shards'])
        except KeyError:
            number_of_shards = 5

        try:
            number_of_replicas = int(settings['elasticsearch.repository.number_of_replicas'])
        except KeyError:
            number_of_replicas = 1

        connection = self.create_connection()
        if connection is not None:
            try:
                connection.indices.create(self.user_id + "_" + self.project_code,
                                          body=_get_dataset_index_definition(number_of_shards, number_of_replicas))
            except RequestError as e:
                if e.status_code == 400:
                    if e.error.find('already_exists') >= 0:
                        pass
                    else:
                        raise e
                else:
                    raise e

        else:
            raise RequestError("Cannot connect to ElasticSearch")

    def add_dataset(self, dataset_id, data_dict):
        """
        Adds a use to the index
        :param dataset_id: The dataset to add into the index
        :param data_dict: The data related to the dataset as dict
        :return: The unique ID give to the link
        """

        connection = self.create_connection()
        if connection is not None:
            connection.index(index=self.user_id + "_" + self.project_code, doc_type='dataset', id=dataset_id,
                             body=data_dict)
        else:
            raise RequestError("Cannot connect to ElasticSearch")

    def get_dataset_stats_for_form(self, project_id, form_id):
        """
        Returns the number of datasets and the last dataset datetime and by from a form or project
        :return: Dict array
        """
        connection = self.create_connection()
        if connection is not None:
            es_result = connection.search(index=self.user_id + "_" + self.project_code,
                                          body=get_search_dict_by_form(project_id, form_id))
            if es_result['hits']['total'] > 0:
                for hit in es_result['hits']['hits']:
                    return es_result['hits']['total'], hit['_source']['_submitted_date'], hit['_source'][
                        '_submitted_by']
            else:
                return 0, None, None
        else:
            raise RequestError("Cannot connect to ElasticSearch")

    def get_dataset_stats_for_project(self, project_id):
        """
        Returns the number of datasets and the last dataset datetime and by from a form or project
        :return: Dict array
        """
        connection = self.create_connection()
        if connection is not None:
            es_result = connection.search(index=self.user_id + "_" + self.project_code,
                                          body=get_search_dict_by_project(project_id))
            if es_result['hits']['total'] > 0:
                for hit in es_result['hits']['hits']:
                    return es_result['hits']['total'], hit['_source']['_submitted_date'], hit['_source'][
                        '_submitted_by'], hit['_source']['_xform_id_string']
            else:
                return 0, None, None, None
        else:
            raise RequestError("Cannot connect to ElasticSearch")
