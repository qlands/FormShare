from uuid import UUID

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError


def _get_record_index_definition(number_of_shards, number_of_replicas):
    """
    Constructs the record index with a given number of shards and replicas.
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
                "number_of_replicas": number_of_replicas,
            }
        },
        "mappings": {
            "properties": {
                "project_id": {"type": "keyword"},
                "form_id": {"type": "keyword"},
                "schema": {"type": "keyword"},
                "table": {"type": "keyword"},
            }
        },
    }
    return _json


def create_connection(settings):
    """
    Creates a connection to ElasticSearch and pings it.
    :return: A tested (pinged) connection to ElasticSearch
    """
    try:
        host = settings["elasticsearch.records.host"]
    except KeyError:
        host = "localhost"

    try:
        port = int(settings["elasticsearch.records.port"])
    except KeyError:
        port = 9200

    try:
        url_prefix = settings["elasticsearch.records.url_prefix"]
    except KeyError:
        url_prefix = None

    try:
        use_ssl = settings["elasticsearch.records.use_ssl"]
        if use_ssl == "True":
            use_ssl = True
        else:
            use_ssl = False
    except KeyError:
        use_ssl = False

    cnt_params = {"host": host, "port": port}
    if url_prefix is not None:
        cnt_params["url_prefix"] = url_prefix
    if use_ssl:
        cnt_params["use_ssl"] = use_ssl
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


def get_index_name(settings):
    return settings.get("elasticsearch.records.index_name", "formshare_records")


def _get_record_search_dict(project_id, form_id):
    """
    Constructs a ES search that will be used to search records in the index
    :param project_id: The project_id to search
    :param form_id: The form_id to search
    :return: A dict that will be passes to ES
    """
    _dict = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"project_id": project_id}},
                    {"term": {"form_id": form_id}},
                ]
            }
        }
    }
    return _dict


def index_exists(connection, index_name):
    if connection is not None:
        if connection.indices.exists(index_name):
            return True
        else:
            return False
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def create_record_index(settings):
    try:
        number_of_shards = int(settings["elasticsearch.records.number_of_shards"])
    except KeyError:
        number_of_shards = 5

    try:
        number_of_replicas = int(settings["elasticsearch.records.number_of_replicas"])
    except KeyError:
        number_of_replicas = 1

    connection = create_connection(settings)
    if connection is not None:
        index_name = get_index_name(settings)
        if not index_exists(connection, index_name):
            try:
                connection.indices.create(
                    index_name,
                    body=_get_record_index_definition(
                        number_of_shards, number_of_replicas
                    ),
                )
                connection.close()
            except RequestError as e:
                connection.close()
                if e.status_code == 400:
                    if e.error.find("already_exists") >= 0:
                        pass
                    else:
                        raise e
                else:
                    raise e
        else:
            connection.close()
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def delete_form_records(settings, project_id, form_id):
    connection = create_connection(settings)
    if connection is not None:
        try:
            index_name = get_index_name(settings)
            connection.delete_by_query(
                index=index_name,
                body=_get_record_search_dict(project_id, form_id),
            )
            connection.close()
        except RequestError as e:
            connection.close()
            if e.status_code == 400:
                if e.error.find("already_exists") >= 0:
                    pass
                else:
                    raise e
            else:
                raise e
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def delete_from_record_index(settings, record_uuid):
    connection = create_connection(settings)
    if connection is not None:
        try:
            index_name = get_index_name(settings)
            connection.delete(index=index_name, id=record_uuid)
            connection.close()
        except RequestError as e:
            connection.close()
            if e.status_code == 400:
                if e.error.find("already_exists") >= 0:
                    pass
                else:
                    raise e
            else:
                raise e
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def add_record(settings, project_id, form_id, schema, table, record_uuid):
    connection = create_connection(settings)
    if connection is not None:
        index_name = get_index_name(settings)
        data_dict = {
            "project_id": project_id,
            "form_id": form_id,
            "schema": schema,
            "table": table,
        }
        connection.index(index=index_name, id=record_uuid, body=data_dict)
        connection.close()
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def _validate_uuid4(uuid_string):
    try:
        UUID(uuid_string, version=4)
    except ValueError:
        return False
    return True


def get_table(settings, record_uuid):
    if _validate_uuid4(record_uuid):
        connection = create_connection(settings)
        if connection is not None:
            index_name = get_index_name(settings)
            query_dict = {"query": {"match": {"_id": record_uuid}}}
            es_result = connection.search(index=index_name, body=query_dict)
            if es_result["hits"]["total"]["value"] == 0:
                # If no results found then try with carry return at the end
                # because that is how was initially stored
                query_dict = {"query": {"match": {"_id": record_uuid + "\n"}}}
                es_result = connection.search(index=index_name, body=query_dict)
            if es_result["hits"]["total"]["value"] == 0:
                connection.close()
                return None, None
            else:
                connection.close()
                return (
                    es_result["hits"]["hits"][0]["_source"]["schema"],
                    es_result["hits"]["hits"][0]["_source"]["table"],
                )
        else:
            raise RequestError("Cannot connect to ElasticSearch")
    else:
        return None, None


def get_project_and_form(settings, record_uuid):
    if _validate_uuid4(record_uuid):
        connection = create_connection(settings)
        if connection is not None:
            index_name = get_index_name(settings)
            query_dict = {"query": {"match": {"_id": record_uuid}}}
            es_result = connection.search(index=index_name, body=query_dict)
            if es_result["hits"]["total"]["value"] == 0:
                # If no results found then try with carry return at the end
                # because that is how was initially stored
                query_dict = {"query": {"match": {"_id": record_uuid + "\n"}}}
                es_result = connection.search(index=index_name, body=query_dict)
            if es_result["hits"]["total"]["value"] == 0:
                connection.close()
                return None, None
            else:
                connection.close()
                return (
                    es_result["hits"]["hits"][0]["_source"]["project_id"],
                    es_result["hits"]["hits"][0]["_source"]["form_id"],
                )
        else:
            raise RequestError("Cannot connect to ElasticSearch")
    else:
        return None, None
