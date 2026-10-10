"""The location fields of the dataset index, without a server
(processes/geometry.py): reading ODK's traces and shapes, repairing a shape
that crosses itself, the point a shape is counted by, and the simplification
the map asks for.
"""

from shapely.geometry import Point, shape

from formshare.processes.geometry import (
    GEOSHAPE,
    GEOTRACE,
    add_location,
    geoshape_variables_of,
    index_fields,
    odk_points,
    parse_geoshape_variables,
    shape_of,
    simplified,
)

BOWTIE = (
    "-1.000 36.000 0 0;-1.000 36.002 0 0;-1.002 36.000 0 0;"
    "-1.002 36.002 0 0;-1.000 36.000 0 0"
)
SQUARE = "0 0 0 0;0 1 0 0;1 1 0 0;1 0 0 0;0 0 0 0"


def test_odk_points_read_both_separators_and_drop_what_is_not_a_point():
    # JSONToMySQL stores a trace with | where ODK wrote ;
    assert odk_points("1 2 0 0;3 4 0 0") == [(2.0, 1.0), (4.0, 3.0)]
    assert odk_points("1 2 0 0|3 4 0 0") == [(2.0, 1.0), (4.0, 3.0)]
    # Not numbers, off the earth, and a GPS standing still.
    assert odk_points("x y;1 2;95 2;1 200;1 2 5 5;3 4") == [(2.0, 1.0), (4.0, 3.0)]
    assert odk_points("") == []
    assert odk_points(None) == []


def test_a_trace_is_a_line():
    assert shape_of("1 2 0 0;3 4 0 0", GEOTRACE).geom_type == "LineString"
    assert shape_of("1 2 0 0", GEOTRACE) is None


def test_a_shape_is_closed_and_kept_when_valid():
    geometry = shape_of("0 0 0 0;0 1 0 0;1 1 0 0;1 0 0 0", GEOSHAPE)
    assert geometry.geom_type == "Polygon" and geometry.is_valid
    assert geometry.exterior.coords[0] == geometry.exterior.coords[-1]
    assert shape_of(SQUARE, GEOSHAPE).equals(geometry)


def test_a_bow_tie_splits_at_its_crossing():
    geometry = shape_of(BOWTIE, GEOSHAPE)
    assert geometry.geom_type == "MultiPolygon" and geometry.is_valid
    assert len(geometry.geoms) == 2
    # Both triangles meet at the crossing, as near as floating point allows.
    for part in geometry.geoms:
        assert part.distance(Point(36.001, -1.001)) < 1e-9


def test_a_walk_that_backtracks_folds_into_one_polygon():
    walk = "-1.0 36.0;-1.0 36.01;-1.01 36.01;-1.01 36.0001;-1.0095 36.0005;-1.0102 36.0"
    geometry = shape_of(walk, GEOSHAPE)
    assert geometry.is_valid and geometry.geom_type == "Polygon"


def test_a_shape_without_area_is_drawn_as_its_boundary():
    # Two points, and three in a line: valid lines, no polygon.
    assert shape_of("0 0;1 1", GEOSHAPE).geom_type == "LineString"
    collinear = shape_of("0 0;1 1;2 2;0 0", GEOSHAPE)
    assert collinear.geom_type == "LineString" and collinear.is_valid
    assert shape_of("0 0", GEOSHAPE) is None


def test_the_point_of_a_shape_is_inside_it():
    # A U whose centroid falls in the gap between its arms.
    u_shape = "0 0;0 3;3 3;3 0;2 0;2 2;1 2;1 0;0 0"
    fields = index_fields(u_shape, GEOSHAPE)
    geometry = shape(fields["_geoshape"])
    assert not geometry.contains(geometry.centroid)
    assert geometry.contains(Point(fields["point"]["lon"], fields["point"]["lat"]))
    assert fields["_geotype"] == "shape"
    assert index_fields("1 2;3 4", GEOTRACE)["_geotype"] == "trace"
    assert index_fields("1 2", GEOTRACE) == {}


def test_index_fields_are_geojson_longitude_first():
    fields = index_fields("1 2 0 0;3 4 0 0", GEOTRACE)
    assert fields["_geoshape"] == {
        "type": "LineString",
        "coordinates": [[2.0, 1.0], [4.0, 3.0]],
    }


def test_the_variables_of_the_main_table_in_form_order():
    survey = {
        "type": "survey",
        "children": [
            {"type": "geotrace", "name": "route"},
            {
                "type": "group",
                "name": "farm",
                "children": [{"type": "geoshape", "name": "parcel"}],
            },
            {
                "type": "repeat",
                "name": "plots",
                "children": [{"type": "geoshape", "name": "plot"}],
            },
            {"type": "geopoint", "name": "home"},
        ],
    }
    variables = geoshape_variables_of(survey)
    assert variables == ["route:geotrace", "farm/parcel:geoshape"]
    assert parse_geoshape_variables(",".join(variables)) == [
        ("route", GEOTRACE),
        ("farm/parcel", GEOSHAPE),
    ]
    assert parse_geoshape_variables(None) == []
    assert parse_geoshape_variables("odd,also:colour") == []


def test_a_document_located_by_a_shape_alone_is_counted_by_a_point_on_it():
    document = add_location({}, {"plot": BOWTIE}, [("plot", GEOSHAPE)])
    assert document["_geotype"] == "shape"
    assert document["_geoshape"]["type"] == "MultiPolygon"
    point = Point(document["_geolocation"]["lon"], document["_geolocation"]["lat"])
    assert shape(document["_geoshape"]).contains(point)


def test_a_geopoint_still_places_the_document():
    home = {"lat": "-1.5", "lon": "36.5"}
    document = add_location(
        {"_geolocation": home}, {"plot": SQUARE}, [("plot", GEOSHAPE)]
    )
    assert document["_geolocation"] == home
    assert document["_geotype"] == "shape"
    only_point = add_location({"_geolocation": home}, {}, [("plot", GEOSHAPE)])
    assert only_point == {"_geolocation": home, "_geotype": "point"}
    assert add_location({}, {}, [("plot", GEOSHAPE)]) == {}


def test_the_first_trace_or_shape_with_something_to_draw():
    document = add_location(
        {},
        {"plot": "", "route": "1 2;3 4"},
        [("plot", GEOSHAPE), ("route", GEOTRACE)],
    )
    assert document["_geotype"] == "trace"


def test_simplified_for_the_zoom():
    import math

    circle = ";".join(
        "{} {}".format(-1 + 0.01 * math.sin(a / 100.0), 36 + 0.01 * math.cos(a / 100.0))
        for a in range(628)
    )
    geojson = index_fields(circle, GEOSHAPE)["_geoshape"]
    far = simplified(geojson, 12)
    near = simplified(geojson, 22)
    vertices = len(geojson["coordinates"][0])
    assert len(far["coordinates"][0]) < vertices / 10
    assert len(near["coordinates"][0]) > len(far["coordinates"][0])
    assert shape(far).is_valid
    point = {"type": "Point", "coordinates": [36.0, -1.0]}
    assert simplified(point, 3) == point


def test_a_submission_located_by_a_trace_or_a_shape_counts_as_with_gps():
    from formshare.processes.elasticsearch.repository_index import (
        get_datasets_with_gps,
        get_projects_with_gps,
    )

    located = {
        "bool": {
            "should": [
                {"exists": {"field": "_geolocation"}},
                {"exists": {"field": "_geoshape"}},
            ],
            "minimum_should_match": 1,
        }
    }
    form = get_datasets_with_gps("p", "f")
    assert form["size"] == 0
    conditions = form["query"]["constant_score"]["filter"]["bool"]["filter"]
    assert located in conditions
    assert {"term": {"project_id": "p"}} in conditions
    assert {"term": {"form_id": "f"}} in conditions
    project = get_projects_with_gps("p", 5)
    assert project["size"] == 5
    assert located in project["query"]["constant_score"]["filter"]["bool"]["filter"]


def test_the_core_map_places_a_trace_or_a_shape_by_its_point():
    from formshare.processes.submission.api import map_point

    assert map_point({"_geopoint": "-1.5 36.5 0 0"}) == ("-1.5", "36.5")
    # Located by a shape alone: the index's point on it.
    shape_only = {"_geopoint": "", "_geolocation": {"lat": 40.3, "lon": -76.04}}
    assert map_point(shape_only) == ("40.3", "-76.04")
    garbled = {
        "_geopoint": "x y",
        "_geolocation": {"lat": "1", "lon": "2"},
        "_xform_id_string": "f",
    }
    assert map_point(garbled) == ("1", "2")
    assert map_point({"_geopoint": ""}) is None
    assert map_point({"_geolocation": {"lat": "", "lon": ""}}) is None
    assert map_point({}) is None


# Every location of the main table: the home, the farm, the path to water.
HOME = "40.3127 -76.0459 120 4"
FARM = (
    "40.3130 -76.0470 120 4;40.3130 -76.0450 120 4;40.3120 -76.0450 120 4;"
    "40.3120 -76.0470 120 4;40.3130 -76.0470 120 4"
)
PATH = "40.3127 -76.0459 120 4;40.3140 -76.0440 120 4;40.3150 -76.0420 120 4"
WATER = "40.3150 -76.0420 118 5"


def test_the_home_the_farm_and_the_path_are_drawn_together():
    home = {"lat": "40.3127", "lon": "-76.0459"}
    document = add_location(
        {"_geolocation": home},
        {"home": HOME, "farm": FARM, "path": PATH},
        [("farm", GEOSHAPE), ("path", GEOTRACE)],
        ["home"],
    )
    assert document["_geoshape"]["type"] == "GeometryCollection"
    assert [g["type"] for g in document["_geoshape"]["geometries"]] == [
        "Point",
        "Polygon",
        "LineString",
    ]
    assert document["_geoshape"]["geometries"][0]["coordinates"] == [-76.0459, 40.3127]
    assert document["_geotype"] == ["point", "shape", "trace"]
    # Still counted once, at the home.
    assert document["_geolocation"] == home


def test_two_points_are_both_drawn_and_one_counts():
    home = {"lat": "40.3127", "lon": "-76.0459"}
    document = add_location(
        {"_geolocation": home}, {"home": HOME, "water": WATER}, [], ["home", "water"]
    )
    assert [g["type"] for g in document["_geoshape"]["geometries"]] == [
        "Point",
        "Point",
    ]
    assert document["_geotype"] == "point"
    assert document["_geolocation"] == home


def test_one_point_alone_is_indexed_as_it_always_was():
    home = {"lat": "40.3127", "lon": "-76.0459"}
    document = add_location({"_geolocation": home}, {"home": HOME}, [], ["home"])
    assert document == {"_geolocation": home, "_geotype": "point"}
    # An answer left blank is no location.
    document = add_location(
        {"_geolocation": home},
        {"home": HOME, "farm": ""},
        [("farm", GEOSHAPE)],
        ["home"],
    )
    assert "_geoshape" not in document


def test_without_a_geopoint_the_first_trace_or_shape_places_the_submission():
    second = FARM.replace("40.3130", "40.3200").replace("40.3120", "40.3190")
    document = add_location(
        {},
        {"farm": FARM, "garden": second, "path": PATH},
        [("farm", GEOSHAPE), ("garden", GEOSHAPE), ("path", GEOTRACE)],
        ["home"],
    )
    assert [g["type"] for g in document["_geoshape"]["geometries"]] == [
        "Polygon",
        "Polygon",
        "LineString",
    ]
    assert document["_geotype"] == ["shape", "trace"]
    farm = shape(document["_geoshape"]["geometries"][0])
    point = Point(document["_geolocation"]["lon"], document["_geolocation"]["lat"])
    assert farm.contains(point)


def test_a_repeat_or_an_unreadable_answer_is_left_out():
    # A repeat's rows arrive as a list; they are not the submission's own.
    document = add_location(
        {},
        {"home": "not a point", "plots": [{"plots/plot": FARM}], "path": PATH},
        [("plots", GEOSHAPE), ("path", GEOTRACE)],
        ["home"],
    )
    assert document["_geoshape"]["type"] == "LineString"
    assert document["_geotype"] == "trace"


def test_a_collection_is_simplified_member_by_member():
    document = add_location(
        {},
        {"home": HOME, "farm": FARM, "path": PATH},
        [("farm", GEOSHAPE), ("path", GEOTRACE)],
        ["home"],
    )
    far = simplified(document["_geoshape"], 8)
    assert far["type"] == "GeometryCollection"
    assert far["geometries"][0] == document["_geoshape"]["geometries"][0]
    assert shape(far).is_valid


def test_the_core_map_places_every_point_of_a_submission():
    from formshare.processes.submission.api import map_points

    both = add_location(
        {"_geolocation": {"lat": "40.3127", "lon": "-76.0459"}},
        {"home": HOME, "water": WATER, "farm": FARM},
        [("farm", GEOSHAPE)],
        ["home", "water"],
    )
    both["_geopoint"] = HOME
    assert map_points(both) == [("40.3127", "-76.0459"), ("40.315", "-76.042")]
    # A shape alone: the point on it; one geopoint alone: that point.
    farm_only = add_location({}, {"farm": FARM}, [("farm", GEOSHAPE)], [])
    assert map_points(farm_only) == [
        (str(farm_only["_geolocation"]["lat"]), str(farm_only["_geolocation"]["lon"]))
    ]
    assert map_points({"_geopoint": HOME}) == [("40.3127", "-76.0459")]
    assert map_points({}) == []
