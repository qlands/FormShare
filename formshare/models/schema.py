from .meta import metadata
import json
from sqlalchemy import inspect
from future.utils import iteritems

__all__ = [
    'initialize_schema','addColumnToSchema','mapToSchema','mapFromSchema',
]

_SCHEMA = []

def initialize_schema():
    for table in metadata.sorted_tables:
        fields = []
        for column in table.c:
            fields.append({'name':column.name,'storage':'db','comment':column.comment})
        _SCHEMA.append({'name':table.name,'fields':fields})

# This function add new columns to the schema in the extra field
def addColumnToSchema(tableName,fieldName,fieldComment):
    for pos in range(len(_SCHEMA)):
        if _SCHEMA[pos]["name"] == tableName:
            found = False
            for field in _SCHEMA[pos]["fields"]:
                if field["name"] == fieldName:
                    found = True
            if not found:
                _SCHEMA[pos]["fields"].append({'name':fieldName,'storage':'extra','comment':fieldComment})
            else:
                raise Exception("Field {} is already defined in table {}".format(fieldName,tableName))

def getStorageType(tableName,fieldName):
    storageType = None
    for table in _SCHEMA:
        if table["name"] == tableName:
            for field in table["fields"]:
                if field["name"] == fieldName:
                    storageType = field["storage"]
    return storageType

# This function maps a data dict to the schema
# Data fields that are mapped to the extra storage are converted to JSON and stored in _extra
# Data fields that are not present in the schema are discarded
# The function returns a mapped dict that can be used to add or update data
def mapToSchema(modelClass,data):
    mappedData = {}
    extraData = {}
    for key,value in iteritems(data):
        storageType = getStorageType(modelClass.__table__.name,key)
        if storageType is not None:
            if storageType == "db":
                mappedData[key] = value
            else:
                extraData[key] = value
    if bool(extraData):
        mappedData["extras"] = json.dumps(extraData)
    if not bool(mappedData):
        raise Exception("The mapping for table {} is empty!".format(modelClass.name))
    return mappedData


# This function maps a row/list of raw data from de database to the schema
# Data fields that resided in the extra storage are separated into independent fields
# The function returns the data in a dict form or an array of dict
def mapFromSchema(data):
    if type(data) is not list:
        mappedData = {}
        if data is not None:
            if data.__class__.__name__ != 'result' :
                for c in inspect(data).mapper.column_attrs:
                    if c.key != "extras":
                        mappedData[c.key] = getattr(data, c.key)
                    else:
                        if getattr(data, c.key) is not None:
                            jsondata = json.loads(getattr(data, c.key))
                            if bool(jsondata):
                                for key,value in iteritems(jsondata):
                                    mappedData[key] = value
            else:
                for tupleItem in data:
                    for c in inspect(tupleItem).mapper.column_attrs:
                        if c.key != "extras":
                            mappedData[c.key] = getattr(tupleItem, c.key)
                        else:
                            if getattr(tupleItem, c.key) is not None:
                                jsondata = json.loads(getattr(tupleItem, c.key))
                                if bool(jsondata):
                                    for key, value in iteritems(jsondata):
                                        mappedData[key] = value

        return mappedData
    else:
        mappedData = []
        for row in data:
            temp = {}
            if row.__class__.__name__ != 'result':
                for c in inspect(row).mapper.column_attrs:
                    if c.key != "extras":
                        temp[c.key] = getattr(row, c.key)
                    else:
                        if getattr(row, c.key) is not None:
                            jsondata = json.loads(getattr(row, c.key))
                            if bool(jsondata):
                                for key, value in iteritems(jsondata):
                                    temp[key] = value
            else:
                for tupleItem in row:
                    for c in inspect(tupleItem).mapper.column_attrs:
                        if c.key != "extras":
                            temp[c.key] = getattr(tupleItem, c.key)
                        else:
                            if getattr(tupleItem, c.key) is not None:
                                jsondata = json.loads(getattr(tupleItem, c.key))
                                if bool(jsondata):
                                    for key, value in iteritems(jsondata):
                                        temp[key] = value

            mappedData.append(temp)
        return mappedData