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
    print("***************_get_record_index_definition*********************")
    _json = {
        "settings": {
            "index": {
                "number_of_shards": number_of_shards,
                "number_of_replicas": number_of_replicas,
            }
        },
        "mappings": {
            "record": {
                "properties": {
                    "schema": {"type": "keyword"},
                    "table": {"type": "keyword"},
                }
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
    connection = Elasticsearch([cnt_params], max_retries=1)
    if connection.ping():
        return connection
    else:
        return None


def get_index_name(user, project, form):
    return (
        "formshare_records_" + user.lower() + "_" + project.lower() + "_" + form.lower()
    )


def create_record_index(settings, user, project, form):
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
        index_name = get_index_name(user, project, form)
        try:
            connection.indices.create(
                index_name,
                body=_get_record_index_definition(number_of_shards, number_of_replicas),
            )
        except RequestError as e:
            if e.status_code == 400:
                if e.error.find("already_exists") >= 0:
                    print("******************************XXX")
                    print("Index {} already exists".format(index_name))
                    print("******************************XXX")
                else:
                    raise e
            else:
                raise e
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def delete_record_index(settings, user, project, form):
    connection = create_connection(settings)
    if connection is not None:
        try:
            index_name = get_index_name(user, project, form)
            connection.indices.delete(index_name, ignore=[400, 404])
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


def delete_from_record_index(settings, user, project, form, record_uuid):
    connection = create_connection(settings)
    if connection is not None:
        try:
            index_name = get_index_name(user, project, form)
            connection.delete(index=index_name, doc_type="record", id=record_uuid)
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


def add_record(settings, user, project, form, schema, table, record_uuid):
    connection = create_connection(settings)
    if connection is not None:
        index_name = get_index_name(user, project, form)
        data_dict = {"schema": schema, "table": table}
        connection.index(
            index=index_name, doc_type="record", id=record_uuid, body=data_dict
        )
    else:
        raise RequestError("Cannot connect to ElasticSearch")


def _validate_uuid4(uuid_string):
    try:
        UUID(uuid_string, version=4)
    except ValueError:
        return False
    return True


def get_table(settings, user, project, form, record_uuid):
    if _validate_uuid4(record_uuid):
        connection = create_connection(settings)
        if connection is not None:
            index_name = get_index_name(user, project, form)
            query_dict = {"query": {"match": {"_id": record_uuid}}}
            es_result = connection.search(index=index_name, body=query_dict)
            if es_result["hits"]["total"] == 0:
                # If no results found then try with carry return at the end
                # because that is how was initially stored
                query_dict = {"query": {"match": {"_id": record_uuid + "\n"}}}
                es_result = connection.search(index=index_name, body=query_dict)
            if es_result["hits"]["total"] == 0:
                return None, None
            else:
                return (
                    es_result["hits"]["hits"][0]["_source"]["schema"],
                    es_result["hits"]["hits"][0]["_source"]["table"],
                )
        else:
            raise RequestError("Cannot connect to ElasticSearch")
    else:
        return None, None
