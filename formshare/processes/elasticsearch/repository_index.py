from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from elasticsearch.exceptions import NotFoundError


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
                    "_project_code": {
                        "type": "keyword"
                    },
                    "_geopoint": {
                        "type": "text"
                    }
                }
            }
        }
    }
    return _json


def get_search_dict_by_form():
    _dict = {
        "size": 1,
        "query": {
            "match_all": {}
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


def get_datasets_dict(query_from=None, query_size=None):
    _dict = {
        "query": {
            "match_all": {}
        },
        "sort": [
            {
                "_submitted_date": {
                    "order": "desc"
                }
            }
        ]
    }
    if query_size is not None:
        _dict["size"] = query_size
    else:
        _dict["size"] = 10000  # Bring 10,000 records in no size is specified
    if query_from is not None:
        _dict["from"] = query_from
    return _dict


def get_datasets_with_gps():
    _dict = {
        "size": 0,
        "query": {
            "constant_score": {
                "filter": {
                    "exists": {"field": "_geopoint"}
                }
            }
        }
    }
    return _dict


def get_search_dict_by_project(project):
    """
    Constructs a ES search that will be used to search for the datasets related to a form in a project
    :param project: The project to search for its datasets
    :return: A dict that will be passes to ES
    """
    _dict = {
        "size": 1,
        "query": {
            "bool": {
                "must": {
                    "term": {
                        "_project_code": project
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


def create_connection(request):
    """
    Creates a connection to ElasticSearch and pings it.
    :return: A tested (pinged) connection to ElasticSearch
    """
    try:
        host = request.registry.settings['elasticsearch.repository.host']
    except KeyError:
        host = "localhost"

    try:
        port = int(request.registry.settings['elasticsearch.repository.port'])
    except KeyError:
        port = 9200

    try:
        url_prefix = request.registry.settings['elasticsearch.repository.url_prefix']
    except KeyError:
        url_prefix = None

    try:
        use_ssl = request.registry.settings['elasticsearch.repository.use_ssl']
        if use_ssl == 'True':
            use_ssl = True
        else:
            use_ssl = False
    except KeyError:
        use_ssl = False

    cnt_params = {'host': host, 'port': port}
    if url_prefix is not None:
        cnt_params["url_prefix"] = url_prefix
    if use_ssl:
        cnt_params["use_ssl"] = use_ssl
    connection = Elasticsearch([cnt_params], max_retries=1)
    if connection.ping():
        return connection
    else:
        return None


def get_index_name(user, project, form):
    return user.lower() + "_" + project.lower() + "_" + form.lower()


def create_dataset_index(request, user, project, form):
    try:
        number_of_shards = int(request.registry.settings['elasticsearch.repository.number_of_shards'])
    except KeyError:
        number_of_shards = 5

    try:
        number_of_replicas = int(request.registry.settings['elasticsearch.repository.number_of_replicas'])
    except KeyError:
        number_of_replicas = 1

    connection = create_connection(request)
    if connection is not None:
        try:
            index_name = get_index_name(user, project, form)
            connection.indices.create(index_name,
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


def delete_dataset_index(request, user, project, form):
    connection = create_connection(request)
    if connection is not None:
        try:
            index_name = get_index_name(user, project, form)
            connection.indices.delete(index_name, ignore=[400, 404])
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


def delete_dataset_index_by_project(request, user, project):
    connection = create_connection(request)
    if connection is not None:
        try:
            index_name = user.lower() + "_" + project.lower() + "_*"
            connection.indices.delete(index_name, ignore=[400, 404])
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


def add_dataset(request, user, project, form, dataset_id, data_dict):
    index_name = get_index_name(user, project, form)
    connection = create_connection(request)
    if connection is not None:
        connection.index(index=index_name, doc_type='dataset', id=dataset_id, body=data_dict)
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def get_dataset_stats_for_form(request, user, project, form):
    index_name = get_index_name(user, project, form)
    connection = create_connection(request)
    if connection is not None:
        try:
            es_result = connection.search(index=index_name, body=get_search_dict_by_form())
            if es_result['hits']['total'] > 0:
                for hit in es_result['hits']['hits']:
                    return es_result['hits']['total'], hit['_source']['_submitted_date'], hit['_source'][
                        '_submitted_by']
            else:
                return 0, None, None
        except NotFoundError:
            return 0, None, None
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def get_number_of_datasets_with_gps(request, user, project, form):
    index_name = get_index_name(user, project, form)
    connection = create_connection(request)
    if connection is not None:
        try:
            es_result = connection.search(index=index_name, body=get_datasets_with_gps())
            if es_result['hits']['total'] > 0:
                return es_result['hits']['total']
            else:
                return 0
        except NotFoundError:
            return 0
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def get_number_of_datasets_with_gps_in_project(request, user, project):
    index_name = user.lower() + "_" + project.lower() + "_*"
    connection = create_connection(request)
    if connection is not None:
        try:
            es_result = connection.search(index=index_name, body=get_datasets_with_gps())
            if es_result['hits']['total'] > 0:
                return es_result['hits']['total']
            else:
                return 0
        except NotFoundError:
            return 0
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def get_datasets_from_form(request, user, project, form, query_from=None, query_size=None):
    index_name = get_index_name(user, project, form)
    connection = create_connection(request)
    if connection is not None:
        try:
            es_result = connection.search(index=index_name, body=get_datasets_dict(query_from, query_size))
            result = []
            if es_result['hits']['total'] > 0:
                for hit in es_result['hits']['hits']:
                    result.append(hit['_source'])
                return len(result), result
            else:
                return 0, []
        except NotFoundError:
            return 0, []
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def get_datasets_from_project(request, user, project, query_from=None, query_size=None):
    index_name = user.lower() + "_" + project.lower() + "_*"
    connection = create_connection(request)
    if connection is not None:
        try:
            es_result = connection.search(index=index_name, body=get_datasets_dict(query_from, query_size))
            result = []
            if es_result['hits']['total'] > 0:
                for hit in es_result['hits']['hits']:
                    result.append(hit['_source'])
                return len(result), result
            else:
                return 0, []
        except NotFoundError:
            return 0, []
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def get_dataset_stats_for_project(request, user, project):
    index_name = user.lower() + "_" + project.lower() + "_*"
    connection = create_connection(request)
    if connection is not None:
        try:
            es_result = connection.search(index=index_name,
                                          body=get_search_dict_by_project(project))
            if es_result['hits']['total'] > 0:
                for hit in es_result['hits']['hits']:
                    return es_result['hits']['total'], hit['_source']['_submitted_date'], hit['_source'][
                        '_submitted_by'], hit['_source']['_xform_id_string']
            else:
                return 0, None, None, None
        except NotFoundError:
            return 0, None, None, None
    else:
        raise RequestError("Cannot connect to ElasticSearch")
