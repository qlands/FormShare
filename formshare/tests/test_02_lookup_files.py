"""What a replaced CSV or GeoJSON does to a schema format 3.0 lookup.

A form that declares allow_choice_duplicates gets lookups keyed by a surrogate,
so the code alone no longer names a row, and a GeoJSON lookup carries a
geometry column MySQL derives for itself. Both changed what a file update is
allowed to do, and neither is visible from the return value of the functions
that do it - an insert MySQL discards still reports success.

These tests stand in for the database with a session that records what it was
asked to run, so what reaches the lookup can be asserted on directly: the rows,
the columns they carry, and the shape of the merge.
"""

import io
import json

import pandas as pd
import pytest
from lxml import etree

from formshare.processes.db import dictionary
from formshare.processes.odk import geojson


def a_field(
    name, field_type, size=0, key=0, autoincrement=0, notnull=0, generatedas=None
):
    return {
        "field_name": name,
        "field_type": field_type,
        "field_size": size,
        "field_decsize": 0,
        "field_key": key,
        "field_autoincrement": autoincrement,
        "field_notnull": notnull,
        "field_generatedas": generatedas,
    }


# The villages lookup of a form declaring allow_choice_duplicates: keyed by a
# surrogate, with sub_location as the column the choice_filter names.
VILLAGES = [
    a_field("villages_rowid", "int", 12, key=1, autoincrement=1),
    a_field("villages_cod", "varchar", 128),
    a_field("villages_des", "text"),
    a_field("sub_location", "text"),
    a_field("rowuuid", "varchar", 80),
]

# A lookup built from a GeoJSON: every property a column, plus the geometry as
# MySQL is given it and as MySQL derives it.
PLACES = [
    a_field("place_rowid", "int", 12, key=1, autoincrement=1),
    a_field("place_cod", "varchar", 128),
    a_field("place_des", "text"),
    a_field("annual_visits", "text"),
    a_field("geometry_json", "json", notnull=1),
    a_field(
        "geometry",
        "geometry",
        notnull=1,
        generatedas="ST_GeomFromGeoJSON(geometry_json,1,4326)",
    ),
    a_field("rowuuid", "varchar", 80),
]

# A list whose name is spelled with _cod inside it, as a Spanish form writes
# one: only the last four characters say which column is the code and which
# the description.
HOGAR_CODIGO = [
    a_field("hogar_codigo_rowid", "int", 12, key=1, autoincrement=1),
    a_field("hogar_codigo_cod", "varchar", 128),
    a_field("hogar_codigo_des", "text"),
    a_field("rowuuid", "varchar", 80),
]

LOOKUPS = {
    "lkpvillages": VILLAGES,
    "lkpplace": PLACES,
    "lkphogar_codigo": HOGAR_CODIGO,
}


class RecordingSession(object):
    """A session that runs nothing and remembers everything."""

    def __init__(self, select_rows=None):
        self.statements = []
        self.bound = []
        self.select_rows = select_rows or []

    def execute(self, statement, params=None):
        self.statements.append(str(statement))
        if params is not None:
            self.bound.append(dict(params))
        return self

    def fetchall(self):
        return self.select_rows

    def commit(self):
        pass

    def rollback(self):
        self.statements.append("ROLLBACK")

    def statements_starting(self, prefix):
        return [a_sql for a_sql in self.statements if a_sql.startswith(prefix)]

    @property
    def sql(self):
        return "\n".join(self.statements)


class FakeRequest(object):
    registry = type("Registry", (), {"settings": {"sqlalchemy.url": "mysql://x/y"}})()

    @staticmethod
    def translate(message):
        return message


@pytest.fixture
def lookup(monkeypatch):
    """Stand in for the dictionary and the database.

    Returns a function that says which lookup a file is attached to and what
    the lookup already holds, and hands back the session that will record the
    merge.
    """

    def _install(rel_table, rel_field, filter_columns, name, label, select_rows=None):
        session = RecordingSession(select_rows)
        monkeypatch.setattr(
            dictionary,
            "get_dictionary_fields",
            lambda request, project, form, table: LOOKUPS[table],
        )
        for a_module in [dictionary, geojson]:
            monkeypatch.setattr(
                a_module, "get_references_from_file", lambda *a: (rel_table, rel_field)
            )
            monkeypatch.setattr(
                a_module,
                "get_filter_columns_from_file",
                lambda *a: list(filter_columns),
            )
            monkeypatch.setattr(
                a_module, "get_name_and_label_from_file", lambda *a: (name, label)
            )
            monkeypatch.setattr(
                a_module,
                "create_engine",
                lambda *a, **k: type("Engine", (), {"dispose": lambda self: None})(),
            )
            monkeypatch.setattr(a_module, "Session", lambda bind=None: session)
        return session

    return _install


@pytest.fixture
def insert_file(tmp_path):
    """An insert XML file holding the values given, as RSTools writes them."""

    def _write(table_name, values):
        path = str(tmp_path / "insert.xml")
        root = etree.Element("insert")
        table = etree.SubElement(root, "table", name=table_name)
        for a_value in values:
            etree.SubElement(table, "value", a_value)
        etree.ElementTree(root).write(path, pretty_print=True, encoding="UTF-8")
        return path

    return _write


@pytest.fixture
def geojson_file(tmp_path):
    def _write(features):
        path = str(tmp_path / "places.geojson")
        with open(path, "w") as a_file:
            json.dump({"type": "FeatureCollection", "features": features}, a_file)
        return path

    return _write


def villages_csv(rows):
    return pd.DataFrame(rows)


def test_repeated_code_is_told_apart_by_its_filter_column(lookup, insert_file):
    """A code may repeat when a choice_filter tells the repeats apart, and each
    row has to reach the lookup with that column filled in."""
    session = lookup(
        "lkpvillages",
        "villages_cod",
        ["sub_location"],
        "name",
        "label",
        # In the order the merge selects them back
        select_rows=[("v001", "Ntemba", "SL1"), ("v009", "Brand new", "SL2")],
    )
    path = insert_file(
        "lkpvillages",
        [{"code": "v001", "sub_location": "SL1", "description": "Ntemba"}],
    )
    result, message = dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        path,
        "villages.csv",
        villages_csv(
            [
                {"name": "v001", "label": "Ntemba", "sub_location": "SL1"},
                {"name": "v002", "label": "Kalunga", "sub_location": "SL1"},
                {"name": "v001", "label": "Mwansa", "sub_location": "SL2"},
                {"name": "v009", "label": "Brand new", "sub_location": "SL2"},
            ]
        ),
        1,
    )
    assert (result, message) == (True, "")
    assert session.bound == [
        {"villages_cod": "v001", "villages_des": "Ntemba", "sub_location": "SL1"},
        {"villages_cod": "v002", "villages_des": "Kalunga", "sub_location": "SL1"},
        {"villages_cod": "v001", "villages_des": "Mwansa", "sub_location": "SL2"},
        {"villages_cod": "v009", "villages_des": "Brand new", "sub_location": "SL2"},
    ]


def test_the_merge_is_keyed_on_the_whole_identity(lookup, insert_file):
    """Joined on the code alone, renaming one v001 would rename the other."""
    session = lookup("lkpvillages", "villages_cod", ["sub_location"], "name", "label")
    dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpvillages", []),
        "villages.csv",
        villages_csv([{"name": "v001", "label": "Ntemba", "sub_location": "SL1"}]),
        1,
    )
    identity = (
        "TA.villages_cod <=> TB.villages_cod AND TA.sub_location <=> TB.sub_location"
    )
    update = session.statements_starting("UPDATE")
    assert len(update) == 1
    assert update[0].endswith("WHERE " + identity)
    assert update[0].count("SET TA.villages_des = TB.villages_des") == 1

    insert = session.statements_starting("INSERT INTO myschema.lkpvillages")
    assert len(insert) == 1
    assert insert[0].endswith(
        "WHERE NOT EXISTS (SELECT 1 FROM myschema.lkpvillages TA WHERE {})".format(
            identity
        )
    )
    # INSERT IGNORE deduplicated on a unique index the code column no longer
    # has, so the whole file was appended again on every upload.
    assert "INSERT IGNORE" not in session.sql


def test_a_choice_that_left_the_file_is_kept(lookup, insert_file):
    """Submissions reference it, and since 3.0 the referential integrity guard
    fails the whole delete rather than skipping the rows in use."""
    session = lookup("lkpvillages", "villages_cod", ["sub_location"], "name", "label")
    dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpvillages", []),
        "villages.csv",
        villages_csv([{"name": "v001", "label": "Ntemba", "sub_location": "SL1"}]),
        1,
    )
    assert "DELETE" not in session.sql


def test_two_rows_naming_the_same_choice_are_refused(lookup, insert_file):
    session = lookup("lkpvillages", "villages_cod", ["sub_location"], "name", "label")
    result, message = dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpvillages", []),
        "villages.csv",
        villages_csv(
            [
                {"name": "v001", "label": "Ntemba", "sub_location": "SL1"},
                {"name": "v001", "label": "Ntemba again", "sub_location": "SL1"},
            ]
        ),
        1,
    )
    assert result is False
    assert message == "You have a duplicated option in villages.csv: 'v001'"
    assert session.statements == []


def test_a_file_without_the_filter_column_is_refused(lookup, insert_file):
    """Without it the merge cannot tell which row it is looking at, and the
    rows it inserted would be unreachable from a submission."""
    lookup("lkpvillages", "villages_cod", ["sub_location"], "name", "label")
    result, message = dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpvillages", []),
        "villages.csv",
        villages_csv([{"name": "v001", "label": "Ntemba"}]),
        1,
    )
    assert result is False
    assert "sub_location" in message


def test_a_list_with_no_filter_merges_on_its_code(lookup, insert_file):
    session = lookup("lkpvillages", "villages_cod", [], "name", "label", select_rows=[])
    result, message = dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpvillages", []),
        "villages.csv",
        villages_csv([{"name": "v001", "label": "Ntemba"}]),
        1,
    )
    assert (result, message) == (True, "")
    assert session.statements_starting("UPDATE")[0].endswith(
        "WHERE TA.villages_cod <=> TB.villages_cod"
    )


def test_a_list_spelled_with_cod_inside_its_name_keeps_its_description(
    lookup, insert_file
):
    """hogar_codigo becomes hogar_codigo_cod and hogar_codigo_des. Deriving
    the description column by replacing every _cod asked for hogar_desigo_des,
    which no lookup has, so the labels were quietly left out of the merge."""
    session = lookup(
        "lkphogar_codigo", "hogar_codigo_cod", [], "name", "label", select_rows=[]
    )
    result, message = dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkphogar_codigo", []),
        "hogares.csv",
        villages_csv([{"name": "h001", "label": "Casa Ntemba"}]),
        1,
    )
    assert (result, message) == (True, "")
    assert session.bound == [
        {"hogar_codigo_cod": "h001", "hogar_codigo_des": "Casa Ntemba"}
    ]


def test_a_multiselect_still_refuses_a_code_with_spaces(lookup, insert_file):
    lookup("lkpvillages", "villages_cod", [], "name", "label")
    result, message = dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpvillages", []),
        "villages.csv",
        villages_csv([{"name": "v 001", "label": "Ntemba"}]),
        2,
    )
    assert result is False
    assert "spaces in the column" in message


def test_the_insert_file_follows_the_lookup(lookup, insert_file):
    """The insert file is what a repository is seeded from when it is built
    again, so a choice that only reached the table would come back missing."""
    lookup(
        "lkpvillages",
        "villages_cod",
        ["sub_location"],
        "name",
        "label",
        select_rows=[("v001", "Ntemba", "SL1"), ("v009", "Brand new", "SL2")],
    )
    path = insert_file(
        "lkpvillages",
        [{"code": "v001", "sub_location": "SL1", "description": "Ntemba"}],
    )
    dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        path,
        "villages.csv",
        villages_csv([{"name": "v001", "label": "Ntemba", "sub_location": "SL1"}]),
        1,
    )
    values = etree.parse(path).findall(".//value")
    assert [
        (a_value.get("code"), a_value.get("sub_location"), a_value.get("description"))
        for a_value in values
    ] == [("v001", "SL1", "Ntemba"), ("v009", "SL2", "Brand new")]


def test_a_failed_merge_is_rolled_back_before_the_temporary_table_is_dropped(
    lookup, insert_file
):
    """Dropping the table is DDL, and MySQL commits the open transaction before
    it runs. Rolled back afterwards, an update that got as far as the UPDATE
    and then failed would be committed on the way out."""
    session = lookup("lkpvillages", "villages_cod", [], "name", "label")

    ran = session.execute

    def failing(statement, params=None):
        if str(statement).startswith("INSERT INTO myschema.lkpvillages"):
            ran(statement, params)
            raise Exception("1451 Cannot add or update a child row")
        return ran(statement, params)

    session.execute = failing
    result, message = dictionary.update_lookup_from_csv(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpvillages", []),
        "villages.csv",
        villages_csv([{"name": "v001", "label": "Ntemba"}]),
        1,
    )
    assert result is False
    assert "1451" in message
    order = [
        a_sql
        for a_sql in session.statements
        if a_sql in ["ROLLBACK"] or a_sql.startswith("DROP TABLE")
    ]
    assert order[0] == "ROLLBACK"
    assert order[1].startswith("DROP TABLE")


# ------------------------------------------------------------------- GeoJSON

POINT = {
    "type": "Feature",
    "id": "m1",
    "geometry": {"type": "Point", "coordinates": [7.08, 46.58]},
    "properties": {"title": "HR Giger Museum", "annual_visits": 40000},
}
POLYGON = {
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
    "properties": {"place_id": "m2", "title": "A parcel"},
}


def test_a_feature_is_named_by_its_top_level_id():
    """The spec puts id on the Feature, not in its properties, and RSTools
    reads it there first."""
    assert geojson.feature_code(POINT, "place_id") == "m1"
    assert geojson.feature_code(POLYGON, "place_id") == "m2"
    assert geojson.feature_code({"id": 12}, "place_id") == "12"
    assert geojson.feature_code({"properties": {}}, "place_id") is None


def test_check_geojson_accepts_what_rstools_accepts(geojson_file):
    """A file the tool built the repository from must not be refused here."""
    path = geojson_file([POINT, POLYGON])
    assert geojson.check_geojson(FakeRequest(), path, "place_id", "title") == (True, "")


def test_check_geojson_refuses_a_geometry_odk_does_not_read(geojson_file):
    path = geojson_file(
        [
            {
                "type": "Feature",
                "id": "m1",
                "geometry": {"type": "Shape"},
                "properties": {},
            }
        ]
    )
    result, message = geojson.check_geojson(FakeRequest(), path, "place_id", "title")
    assert result is False
    assert "point, a line or a polygon" in message


def test_check_geojson_refuses_a_feature_with_no_id(geojson_file):
    path = geojson_file(
        [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "properties": {"title": "No id here"},
            }
        ]
    )
    result, message = geojson.check_geojson(FakeRequest(), path, "place_id", "title")
    assert result is False
    assert "without an id" in message


def test_geojson_writes_the_geometry_it_was_given(lookup, insert_file, geojson_file):
    """geometry_json is written and the geometry column beside it is left to
    MySQL. Writing it raises 3105; leaving both out makes MySQL discard the row
    and say nothing."""
    session = lookup("lkpplace", "place_cod", [], "place_id", "title", select_rows=[])
    result, message = geojson.update_lookup_from_geo_json(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpplace", []),
        "places.geojson",
        geojson_file([POINT, POLYGON]),
    )
    assert (result, message) == (True, "")
    assert session.bound == [
        {
            "place_cod": "m1",
            "place_des": "HR Giger Museum",
            "annual_visits": 40000,
            "geometry_json": '{"type": "Point", "coordinates": [7.08, 46.58]}',
        },
        {
            "place_cod": "m2",
            "place_des": "A parcel",
            "annual_visits": None,
            "geometry_json": (
                '{"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}'
            ),
        },
    ]
    # The surrogate key, the row identifier and the derived geometry belong to
    # MySQL. So does the coordinates column the old code wrote, which RSTools
    # stopped creating.
    assert "place_rowid" not in session.sql
    assert "rowuuid" not in session.sql
    assert "coordinates" not in session.sql
    assert "TB.geometry," not in session.sql
    assert "INSERT IGNORE" not in session.sql
    assert "DELETE" not in session.sql


def test_a_feature_with_no_title_is_shown_by_its_id(lookup, insert_file, geojson_file):
    session = lookup("lkpplace", "place_cod", [], "place_id", "title", select_rows=[])
    untitled = dict(POINT, properties={"annual_visits": 1})
    geojson.update_lookup_from_geo_json(
        FakeRequest(),
        "auser",
        "aproject",
        "aform",
        "myschema",
        insert_file("lkpplace", []),
        "places.geojson",
        geojson_file([untitled]),
    )
    assert session.bound[0]["place_des"] == "m1"


# --------------------------------------------- the plugin-generated file path


def test_a_generated_geojson_is_read_before_it_reaches_a_device(tmp_path):
    """A plugin can generate a form's GeoJSON the way it can generate its CSV.
    What it produces is checked before it is offered for download, because a
    file that will not parse is worse on the device than a missing one."""
    from formshare.processes.odk.api import is_geojson_usable

    good = tmp_path / "good.geojson"
    good.write_text(json.dumps({"type": "FeatureCollection", "features": [POINT]}))
    assert is_geojson_usable(str(good)) is True

    not_json = tmp_path / "bad.geojson"
    not_json.write_text("{ not json at all")
    assert is_geojson_usable(str(not_json)) is False

    not_a_collection = tmp_path / "wrong.geojson"
    not_a_collection.write_text(json.dumps({"type": "Feature"}))
    assert is_geojson_usable(str(not_a_collection)) is False

    empty = tmp_path / "empty.geojson"
    empty.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    assert is_geojson_usable(str(empty)) is False

    assert is_geojson_usable(str(tmp_path / "missing.geojson")) is False


def test_a_generated_geojson_that_the_form_refuses_does_not_reach_the_lookup(
    lookup, insert_file, geojson_file
):
    """is_geojson_usable only says the file parses. Whether its features suit
    the lookup is check_geojson's question, and the merge must not run when the
    answer is no - which is how the CSV path behaves."""
    session = lookup("lkpplace", "place_cod", [], "place_id", "title", select_rows=[])
    unsupported = {
        "type": "Feature",
        "id": "m9",
        "geometry": {"type": "Shape", "coordinates": [0, 0]},
        "properties": {"title": "Not a shape ODK reads"},
    }
    path = geojson_file([unsupported])

    from formshare.processes.odk.api import is_geojson_usable

    assert is_geojson_usable(path) is True
    result, message = geojson.check_geojson(FakeRequest(), path, "place_id", "title")
    assert result is False

    # The branch only merges when check_geojson agrees, so nothing is run.
    assert session.statements == []


# ------------------------------------------------- a file that was never sent


def test_a_name_that_is_not_a_file_reads_as_a_missing_file(tmp_path, monkeypatch):
    """An upload posted with nothing chosen used to be stored as a form file
    called "". Pairtree resolves that to the bucket's own directory, and
    opening it raises IsADirectoryError rather than saying the file is absent -
    which took down every later read of the form's files, not just the upload.
    """
    from formshare.processes.storage import local_storage

    class DirectoryBucket(object):
        """Stands in for the store, raising what pairtree raises for ""."""

        def claim_bucket(self, bucket_id):
            return None

        def get_stream(self, bucket_id, file_name):
            if file_name == "":
                raise IsADirectoryError(21, "Is a directory", str(tmp_path))
            return io.BytesIO(b"contents")

    monkeypatch.setattr(
        local_storage, "get_storage_object", lambda request: DirectoryBucket()
    )
    assert local_storage.get_stream(None, "abucket", "") is None
    assert local_storage.get_stream(None, "abucket", "real.csv").read() == b"contents"


# ------------------------------------------------------------------- helpers


def test_a_lookup_column_is_found_under_the_name_the_file_gives_it():
    """RSTools lowercases a header and turns a dash or a colon into an
    underscore before it becomes a column."""
    assert dictionary.fix_field_name("Sub-Location") == "sub_location"
    assert dictionary.fix_field_name("label::English") == "label__english"
    assert (
        dictionary.find_source_column("sub_location", ["name", "Sub-Location"])
        == "Sub-Location"
    )
    assert dictionary.find_source_column("missing", ["name"]) is None


def test_the_description_column_is_named_by_its_suffix_alone():
    """A list may be called anything, including a word spelled with _cod or
    _des inside it. The authority is LookupColumns::descColumn in RSTools: the
    last four characters are swapped, and a name that does not end in _cod is
    not a code column and comes back as it is."""
    assert dictionary.get_lookup_desc_field("villages_cod") == "villages_des"
    assert dictionary.get_lookup_desc_field("hogar_codigo_cod") == "hogar_codigo_des"
    assert (
        dictionary.get_lookup_desc_field("form_description_cod")
        == "form_description_des"
    )
    assert dictionary.get_lookup_desc_field("villages_rowid") == "villages_rowid"


def test_a_derived_or_assigned_column_is_never_written(monkeypatch):
    monkeypatch.setattr(
        dictionary,
        "get_dictionary_fields",
        lambda request, project, form, table: PLACES,
    )
    fields = dictionary.get_lookup_merge_fields(
        None, "aproject", "aform", "lkpplace", "place_cod"
    )
    assert [a_column["field_name"] for a_column in fields] == [
        "place_cod",
        "place_des",
        "annual_visits",
        "geometry_json",
    ]


def test_a_column_the_file_must_fill_is_refused_when_it_is_missing(monkeypatch):
    """A NOT NULL column with no default cannot be left out: MySQL discards the
    row and reports a warning, so the upload would succeed and change nothing."""
    monkeypatch.setattr(
        dictionary,
        "get_dictionary_fields",
        lambda request, project, form, table: PLACES,
    )
    fields, message = dictionary.get_merge_columns(
        None,
        "aproject",
        "aform",
        "lkpplace",
        "place_cod",
        ["place_cod"],
        ["place_id", "title"],
        {"place_cod": "place_id", "place_des": "title"},
    )
    assert fields is None
    assert "geometry_json" in message


def test_the_join_matches_a_null_filter_value():
    assert dictionary.get_identity_join(["villages_cod", "sub_location"]) == (
        "TA.villages_cod <=> TB.villages_cod AND TA.sub_location <=> TB.sub_location"
    )


def test_a_temporary_column_is_declared_the_way_rstools_declares_it():
    assert dictionary.sql_column_type(a_field("a", "varchar", 128)) == "varchar(128)"
    assert dictionary.sql_column_type(a_field("a", "int", 12)) == "int(12)"
    assert dictionary.sql_column_type(a_field("a", "text")) == "text"
    assert dictionary.sql_column_type(a_field("a", "json")) == "json"
