"""Where a submission is on the map: the processing behind the location
fields of the dataset index.

FormShare indexes one location per submission in Elasticsearch (the dataset
index), and the map plugin draws what it finds there. Until 2026-10 that was
the form's first geopoint only, so a submission located by a geotrace or a
geoshape was not on the map at all. Its document now carries:

- ``_geolocation``, a geo_point, as before: the first geopoint, or, for a
  submission located by a trace or a shape alone, a point on it. The map
  counts and clusters by this. Geotile aggregations are free on a geo_point
  field and need a paid licence on a geo_shape one, and nobody reads a
  million polygons at a country's zoom anyway.
- ``_geoshape``, a geo_shape: the first trace or shape of the main table, as
  GeoJSON, which the map draws when few features are in view.
- ``_geotype``: point, trace or shape.

ODK collects a trace or a shape as text, ``lat lon alt acc`` points
separated by ``;`` (by ``|`` once JSONToMySQL has stored it), and nothing
stops an enumerator walking a boundary that crosses itself. Elasticsearch
refuses such a polygon, so it is repaired here, for the index only: GEOS's
make-valid, which Shapely bundles, splits a bow-tie at its crossing into a
MultiPolygon. The repository keeps the shape as it was collected.

Pure functions only: the indexing code and the map plugin call them.
"""

import json

import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon, shape

__all__ = [
    "GEOTRACE",
    "GEOSHAPE",
    "odk_points",
    "shape_of",
    "index_fields",
    "geoshape_variables_of",
    "parse_geoshape_variables",
    "add_location",
    "simplified",
]

GEOTRACE = "geotrace"
GEOSHAPE = "geoshape"
_KINDS = {GEOTRACE: "trace", GEOSHAPE: "shape"}


def odk_points(text):
    """The (longitude, latitude) pairs of an ODK trace or shape, in order.

    A point that is not two numbers on the earth is left out, and so is a
    repeat of the point before it: a GPS standing still records the same
    position twice, which only adds a zero-length edge.
    """
    points = []
    for part in str(text or "").replace("|", ";").split(";"):
        bits = part.split()
        if len(bits) < 2:
            continue
        try:
            latitude, longitude = float(bits[0]), float(bits[1])
        except ValueError:
            continue
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            continue
        if points and points[-1] == (longitude, latitude):
            continue
        points.append((longitude, latitude))
    return points


def shape_of(text, odk_type):
    """The geometry of an ODK trace or shape as Elasticsearch takes it, or
    None when there is nothing to draw.

    A trace is a LineString. A shape is a Polygon, closed if ODK left it
    open. One whose boundary crosses itself is made valid: a bow-tie splits
    at its crossing into a MultiPolygon, and a small loop where the walk
    backtracked folds into the rest. A shape with no area left at all is
    kept as its boundary, a LineString, which may cross itself and still be
    valid. Fewer than two distinct points is nothing.
    """
    points = odk_points(text)
    if len(set(points)) < 2:
        return None
    if odk_type == GEOTRACE:
        return LineString(points)
    if points[0] != points[-1]:
        points.append(points[0])
    if len(set(points)) < 3:
        return LineString(points)
    polygon = Polygon(points)
    if polygon.is_valid:
        return polygon
    fixed = shapely.make_valid(polygon)
    polygons = []
    for part in getattr(fixed, "geoms", [fixed]):
        if part.is_empty:
            continue
        if part.geom_type == "Polygon":
            polygons.append(part)
        elif part.geom_type == "MultiPolygon":
            polygons.extend(part.geoms)
    if not polygons:
        return LineString(points)
    return polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)


def _geojson(geometry):
    return json.loads(shapely.to_geojson(geometry))


def index_fields(text, odk_type):
    """What a trace or shape gives a submission's document in the dataset
    index: ``_geoshape`` (GeoJSON), ``_geotype``, and ``point``, a
    ``{"lat", "lon"}`` on the geometry -- inside a polygon, never outside a
    U-shaped one as its centroid could be. {} when there is nothing to draw.
    """
    geometry = shape_of(text, odk_type)
    if geometry is None:
        return {}
    point = geometry.representative_point()
    return {
        "_geoshape": _geojson(geometry),
        "_geotype": _KINDS[odk_type],
        "point": {"lat": point.y, "lon": point.x},
    }


def geoshape_variables_of(json_dict):
    """The geotrace and geoshape variables of a form's main table, in the
    order of the form, as pyxform's JSON names them: ``group/name:type``.

    The same walk as the geopoints (get_geopoint_variables_from_json): the
    survey and its groups, never into a repeat, whose rows are not the
    submission's own.
    """
    found = []

    def walk(node, path):
        node_type = node.get("type")
        if node_type in ("survey", "group"):
            if node_type == "group":
                path = path + [node["name"]]
            for child in node.get("children", []):
                walk(child, path)
        elif node_type in (GEOTRACE, GEOSHAPE):
            found.append("/".join(path + [node["name"]]) + ":" + node_type)

    walk(json_dict, [])
    return found


def parse_geoshape_variables(text):
    """[(variable, odk_type)] from Odkform.form_geoshape."""
    variables = []
    for entry in str(text or "").split(","):
        variable, _, odk_type = entry.strip().rpartition(":")
        if variable and odk_type in (GEOTRACE, GEOSHAPE):
            variables.append((variable, odk_type))
    return variables


def add_location(index_data, submission_data, shape_variables):
    """Adds to a submission's index document the location its first trace or
    shape gives, and returns the document.

    ``_geoshape`` and ``_geotype`` come from the first trace or shape that has
    something to draw; ``_geolocation`` from it too when no geopoint gave one,
    so that a submission located by a shape alone is counted on the map. A
    document located by a geopoint alone is ``_geotype`` point.
    """
    for variable, odk_type in shape_variables:
        value = submission_data.get(variable)
        if not value:
            continue
        fields = index_fields(value, odk_type)
        if not fields:
            continue
        index_data["_geoshape"] = fields["_geoshape"]
        index_data["_geotype"] = fields["_geotype"]
        if not index_data.get("_geolocation"):
            index_data["_geolocation"] = fields["point"]
        return index_data
    if index_data.get("_geolocation"):
        index_data["_geotype"] = "point"
    return index_data


def simplified(geojson, zoom):
    """A geometry of the index as the map can show it at that zoom:
    simplified to about one screen pixel, keeping it valid. A point, or a
    geometry that would simplify away, is returned as it is.

    A boundary walked with four hundred points needs a few dozen at a
    district's zoom; the rest is bytes to the browser and nothing on screen.
    """
    geometry = shape(geojson)
    if geometry.geom_type == "Point":
        return geojson
    zoom = max(0, min(22, int(zoom)))
    # Degrees one 256-pixel tile's pixel spans at the equator.
    tolerance = 360.0 / (256 * 2**zoom)
    simple = geometry.simplify(tolerance, preserve_topology=True)
    if simple.is_empty:
        return geojson
    return _geojson(simple)
