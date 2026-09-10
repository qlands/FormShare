import json
import logging
from formshare.processes.logging.loggerclass import SecretLogger
from formshare.processes.db.dictionary import (
    bindable_value,
    get_filter_columns_from_file,
    get_lookup_desc_field,
    get_merge_columns,
    get_name_and_label_from_file,
    get_references_from_file,
    merge_file_into_lookup,
    update_insert_xml_from_lookup,
)
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm.session import Session

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

# The column RSTools gives a GeoJSON lookup to hold the geometry of a feature
# exactly as the file wrote it. The "geometry" column beside it is derived from
# this one by MySQL and cannot be written at all. See appendGeometryFields in
# JXFormToMysql/main.cpp.
GEOMETRY_COLUMN = "geometry_json"

# The geometries ODK reads, and so the ones RSTools builds a lookup from. The
# authority is isSupportedGeometry in JXFormToMysql/main.cpp.
SUPPORTED_GEOMETRIES = ["Point", "LineString", "Polygon"]


def feature_code(a_feature, code_column):
    """
    The identifier of a feature, read the way RSTools reads it.

    The GeoJSON spec puts id on the Feature object, not in its properties, so
    the top level is asked first and properties is the fallback for the files
    that do it the other way round. A number is a valid identifier. The
    authority is featureCode in JXFormToMysql/main.cpp.

    :param a_feature: A feature of the file
    :param code_column: The column the form calls the code of the choice
    :return: The identifier as a string, or None when the feature has none
    """
    for value in [
        a_feature.get("id"),
        a_feature.get("properties", {}).get(code_column),
    ]:
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, str):
            if value != "":
                return value
            continue
        if isinstance(value, (int, float)):
            return "{:.0f}".format(value)
    return None


def check_geojson(request, file_name, name, label):
    """
    Whether a GeoJSON file may replace the one a lookup was built from.

    Checked the way RSTools checks it, so that a file the tool accepted when it
    built the repository is not refused here. Two things follow from that. A
    lookup holds points, lines and polygons, not points alone. And a feature is
    named by its top level id first, so a spec-compliant file whose features
    carry no properties at all is a perfectly good one.

    The label is not required either: a feature with no title is shown by its
    identifier, which is what Collect does.

    :param request: Pyramid request object
    :param file_name: Path of the file to read
    :param name: The column the form calls the code of the choice
    :param label: The column the form calls the description of the choice
    :return: (True, "") or (False, message)
    """
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
                        geometry_type = a_feature["geometry"].get("type", "")
                        if geometry_type not in SUPPORTED_GEOMETRIES:
                            return False, _(
                                "The GeoJSON file has features whose geometry is "
                                "not a point, a line or a polygon"
                            )
                    if feature_code(a_feature, name) is None:
                        return False, _("The GeoJSON file has features without an id")
            else:
                return False, _("The GeoJSON file does not have features")
        else:
            return False, _("The GeoJSON file is not a Feature Collection")
    except Exception as e:
        log.error("Error opening GeoJSON file {}. Error {}".format(file_name, str(e)))
        return False, _("Cannot open GeoJson file")
    return True, ""


def update_lookup_from_geo_json(
    request,
    user_id,
    project_id,
    form_id,
    form_schema,
    form_insert_file,
    file_name,
    file_path,
):
    rel_table, rel_field = get_references_from_file(
        request, project_id, form_id, file_name
    )
    rel_field_desc = get_lookup_desc_field(rel_field)
    filter_columns = get_filter_columns_from_file(
        request, project_id, form_id, file_name
    )
    identity = [rel_field] + filter_columns
    name, label = get_name_and_label_from_file(request, project_id, form_id, file_name)

    try:
        f = open(file_path)
        data = json.load(f)
        f.close()
    except Exception as e:
        log.error("Error opening GeoJSON file {}. Error {}".format(file_path, str(e)))
        return False, "Cannot open {}".format(file_name)
    features = data.get("features", [])

    # Every property any feature carries. A lookup column was made out of one
    # of these and carries its name, so this is what they are matched against.
    file_columns = []
    for a_feature in features:
        for a_property in a_feature.get("properties", {}).keys():
            if a_property not in file_columns:
                file_columns.append(a_property)

    # The code, the description and the geometry do not come from a property of
    # the same name, so they are named here and read out of the feature itself
    # below. Only their presence matters to get_merge_columns.
    sources = {rel_field: name, GEOMETRY_COLUMN: GEOMETRY_COLUMN}
    if rel_field_desc != rel_field:
        sources[rel_field_desc] = label
    columns, message = get_merge_columns(
        request,
        project_id,
        form_id,
        rel_table,
        rel_field,
        identity,
        file_columns,
        sources,
    )
    if columns is None:
        return False, "{}. {}".format(file_name, message)

    rows = []
    seen = set()
    for a_feature in features:
        properties = a_feature.get("properties", {})
        code = feature_code(a_feature, name)
        if code is None:
            return False, "{} has features without an id".format(file_name)
        geometry = a_feature.get("geometry", {})
        if geometry.get("type", "") not in SUPPORTED_GEOMETRIES:
            return (
                False,
                "{} has features whose geometry is not a point, a line or a polygon".format(
                    file_name
                ),
            )
        # RSTools stores a code with its apostrophes turned into backticks, so
        # the lookup holds it that way and this has to ask for it that way.
        code = code.replace("'", "`").replace('"', "")
        a_row = {}
        for a_field in columns:
            a_column = a_field["field_name"]
            if a_column == rel_field:
                a_row[a_column] = code
            elif a_column == rel_field_desc:
                # A feature with no title is shown by its identifier, which is
                # what Collect does and what RSTools stored when it built the
                # lookup.
                description = properties.get(label)
                if description is None or description == "":
                    description = code
                a_row[a_column] = str(description).replace('"', "")
            elif a_column == GEOMETRY_COLUMN:
                # Handed to MySQL exactly as it arrived. The geometry column
                # beside this one is derived from it, so nothing here has to
                # know how to build a geometry or which of a pair of numbers is
                # the latitude.
                a_row[a_column] = json.dumps(geometry)
            else:
                a_row[a_column] = bindable_value(properties.get(sources[a_column]))

        key = tuple(str(a_row[a_column]) for a_column in identity)
        if key in seen:
            return False, "You have a duplicated feature in {}: '{}'".format(
                file_name, code
            )
        seen.add(key)
        rows.append(a_row)

    sql_url = request.registry.settings.get("sqlalchemy.url")
    engine = create_engine(sql_url, poolclass=NullPool)
    session = Session(bind=engine)
    try:
        merge_file_into_lookup(
            session, user_id, form_schema, rel_table, columns, identity, rows
        )
        update_insert_xml_from_lookup(
            session,
            form_insert_file,
            form_schema,
            rel_table,
            columns,
            identity,
            rel_field_desc,
        )
        session.commit()
        engine.dispose()

        return True, ""
    except Exception as e:
        session.rollback()
        engine.dispose()
        log.error(
            "Unable to upload lookup connected to GeoJSON. Error: {}".format(str(e))
        )
        return False, str(e)
