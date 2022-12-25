import json
import logging
import uuid
from formshare.processes.db.dictionary import (
    get_dictionary_fields,
    get_references_from_file,
    get_name_and_label_from_file,
)
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm.session import Session

log = logging.getLogger("formshare")


def check_geojson(request, file_name, name, label):
    _ = request.translate
    try:
        f = open(file_name)
        data = json.load(f)
        f.close()
        if data.get("type", "") == "FeatureCollection":
            features = data.get("features", [])
            if len(features) > 0:
                for a_feature in features:
                    if a_feature.get("type", "") != "Feature":
                        return False, _(
                            "The GeoJSON file has features that are not feature"
                        )
                    if "geometry" not in a_feature.keys():
                        return False, _(
                            "The GeoJSON file has features without geometry"
                        )
                    else:
                        if a_feature["geometry"].get("type", "") != "Point":
                            return False, _(
                                "The GeoJSON file has features that are not point"
                            )
                    if "properties" not in a_feature.keys():
                        return False, _(
                            "The GeoJSON file has features without properties"
                        )
                    else:
                        if (
                            name not in a_feature["properties"].keys()
                            or label not in a_feature["properties"].keys()
                        ):
                            return False, _(
                                "The GeoJSON file has features with properties without id or label"
                            )
            else:
                return False, _("The GeoJSON file does not have features")
        else:
            return False, _("The GeoJSON file is not a Feature Collection")
    except Exception as e:
        log.error("Error opening GeoJSON file {}. Error {}".format(file_name, str(e)))
        return False, _("Cannot open GeoJson file")
    return True, ""


def update_lookup_from_geo_json(
    request, user_id, project_id, form_id, form_schema, file_name, file_path
):
    uid = str(uuid.uuid4())
    uid = "TMP_" + uid.replace("-", "_")
    rel_table, rel_field = get_references_from_file(
        request, project_id, form_id, file_name
    )
    fields = get_dictionary_fields(request, project_id, form_id, rel_table)
    sql = "CREATE TABLE {}.{} (".format(form_schema, uid)
    field_array = []
    field_name_array = []
    table_key = ""
    rel_desc = rel_field.replace("_cod", "_des")
    for a_field in fields:
        field_name = a_field["field_name"]
        if field_name != "rowuuid":
            field_type = a_field["field_type"]
            if a_field["field_type"] == "varchar":
                field_type = "varchar({})".format(a_field["field_size"])
            if a_field["field_type"] == "int":
                field_type = "int({})".format(a_field["field_size"])
            if a_field["field_key"] == 1:
                field_array.append(field_name + " " + field_type + " PRIMARY KEY")
                table_key = field_name
            else:
                if field_name != rel_desc:
                    field_name_array.append(field_name)
                field_array.append(field_name + " " + field_type)
    sql = sql + ",".join(field_array) + ")"

    sql_url = request.registry.settings.get("sqlalchemy.url")
    engine = create_engine(sql_url, poolclass=NullPool)
    name, label = get_name_and_label_from_file(request, project_id, form_id, file_name)
    session = Session(bind=engine)
    temp_table_created = False
    try:
        session.execute(sql)
        temp_table_created = True
        f = open(file_path)
        data = json.load(f)
        f.close()
        for a_feature in data["features"]:
            sql = "INSERT INTO {}.{} ({},{},".format(
                form_schema, uid, table_key, rel_desc
            )
            sql = (
                sql
                + ",".join(field_name_array)
                + ") VALUES ('{}',".format(a_feature["properties"][name])
            )
            sql = sql + "'{}',".format(a_feature["properties"][label])
            for a_field in field_name_array:
                if a_field != "coordinates":
                    sql = sql + "'{}',".format(a_feature["properties"].get(a_field, ""))
                else:
                    lati = a_feature["geometry"]["coordinates"][0]
                    long = a_feature["geometry"]["coordinates"][1]
                    sql = sql + "'{} {}',".format(lati, long)
            sql = sql[: len(sql) - 1] + ")"
            session.execute(sql)

        # Update the description, properties, and coordinates
        session.execute("SET @odktools_current_user = '" + user_id + "'")
        sql = "UPDATE {}.{} TA, {}.{} TB SET TA.{} = TB.{},".format(
            form_schema, rel_table, form_schema, uid, rel_desc, rel_desc
        )
        for a_field in field_name_array:
            sql = sql + "TA.{} = TB.{},".format(a_field, a_field)
        sql = sql[: len(sql) - 1]
        sql = sql + " WHERE TA.{} = TB.{}".format(table_key, table_key)
        session.execute(sql)

        # Delete items that do not exist
        sql = "DELETE IGNORE FROM {}.{} WHERE {} NOT IN (SELECT {} FROM {}.{})".format(
            form_schema, rel_table, rel_field, rel_field, form_schema, uid
        )
        session.execute(sql)

        # Insert new items
        sql = "INSERT IGNORE INTO {}.{} ({},{},".format(
            form_schema, rel_table, table_key, rel_desc
        )
        for a_field in field_name_array:
            sql = sql + a_field + ","
        sql = sql[: len(sql) - 1] + ")"
        sql = sql + " SELECT {},{},".format(table_key, rel_desc)
        for a_field in field_name_array:
            sql = sql + a_field + ","
        sql = sql[: len(sql) - 1]
        sql = sql + " FROM {}.{}".format(form_schema, uid)
        session.execute(sql)

        sql = "DROP TABLE {}.{}".format(form_schema, uid)
        session.execute(sql)

        session.commit()
        engine.dispose()

        return True, ""
    except Exception as e:
        if temp_table_created:
            sql = "DROP TABLE {}.{}".format(form_schema, uid)
            session.execute(sql)
        session.commit()
        engine.dispose()
        log.error(
            "Unable to upload lookup connected to GeoJSON. Error: {}".format(str(e))
        )
        return False, str(e)
