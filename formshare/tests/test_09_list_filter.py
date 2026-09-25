"""The filter of a published list (formshare.md 3.8 and 8.1).

The filter is compiled to a fragment of the list's SELECT, which MySQL runs
on the server and SQLite runs on a device over its mirror. These tests pin
the compiler's text, what it refuses, and -- over a SQLite database shaped
like a mirror -- that the SELECT answers exactly: a text by its bytes, so
that neither case nor a trailing space nor an accent lets a row in, which
the server's collation would.
"""

import json
import sqlite3

import pytest

from formshare.processes.db.case_management import build_list_select
from formshare.processes.list_filter import (
    FilterError,
    compile_filter,
    describe_filter,
    filter_fields,
    querybuilder_filters,
    referenced_properties,
    resolve,
    uses_properties,
)

COLUMNS = [
    {"field_name": "name", "field_type": "varchar", "field_odktype": "text"},
    {"field_name": "district", "field_type": "varchar", "field_rtable": "lkpdistrict"},
    {"field_name": "age", "field_type": "int"},
    {"field_name": "joined", "field_type": "date"},
    {"field_name": "seen", "field_type": "datetime"},
    {"field_name": "spot", "field_type": "varchar", "field_odktype": "geopoint"},
    {"field_name": "spot_geom", "field_type": "geometry", "field_generatedas": "x"},
    {"field_name": "_active", "field_type": "int"},
    {"field_name": "_lastupdate", "field_type": "datetime"},
    {"field_name": "_submitted_date", "field_type": "datetime"},
    {"field_name": "teachers_rowid", "field_type": "int"},
    {"field_name": "surveyid", "field_type": "varchar"},
    {"field_name": "parent_rowuuid", "field_type": "varchar"},
    {"field_name": "root_rowuuid", "field_type": "varchar"},
]
PROPERTIES = [
    {"property_name": "status", "property_type": "string"},
    {"property_name": "visits", "property_type": "integer"},
    {"property_name": "index", "property_type": "decimal"},
]


@pytest.fixture
def fields():
    return filter_fields(COLUMNS, PROPERTIES)


def rule(field, operator, value=None):
    return {"id": field, "field": field, "operator": operator, "value": value}


def rules(*items, condition="AND", negate=False):
    out = {"condition": condition, "rules": list(items)}
    if negate:
        out["not"] = True
    return out


def hexed(text):
    return "'" + text.encode("utf-8").hex().upper() + "'"


# ---------------------------------------------------------------------------
# The fields
# ---------------------------------------------------------------------------


def test_the_fields_are_the_columns_and_the_properties(fields):
    assert set(fields) == {
        "t.name",
        "t.district",
        "t.age",
        "t.joined",
        "t.seen",
        "t.spot",
        "t.parent_rowuuid",
        "t.root_rowuuid",
        "p.status",
        "p.visits",
        "p.index",
    }
    assert fields["t.age"]["kind"] == "number"
    assert fields["t.joined"]["kind"] == "date"
    assert fields["t.seen"]["kind"] == "datetime"
    assert fields["t.spot"]["kind"] == "geo"
    assert fields["p.status"]["kind"] == "text"


def test_what_the_two_hosts_do_not_hold_alike_is_not_offered(fields):
    # The mirror has no derived _geom; _active is the list's own setting;
    # the clocks, the stamp, the server's ids and its autoincrement keys
    # differ between the server and a device. The links do not.
    for name in ("spot_geom", "_active", "_lastupdate", "_submitted_date"):
        assert "t." + name not in fields
    assert "t.teachers_rowid" not in fields and "t.surveyid" not in fields
    assert "t.parent_rowuuid" in fields and "t.root_rowuuid" in fields


def test_querybuilder_gets_types_operators_and_choices(fields):
    filters = {
        f["id"]: f
        for f in querybuilder_filters(
            fields, {"t.district": [{"code": "KJD", "label": "Kajiado"}]}
        )
    }
    assert filters["t.age"]["type"] == "integer"
    assert filters["p.index"]["type"] == "double"
    assert filters["t.joined"]["type"] == "date"
    assert filters["p.status"]["optgroup"] == "Properties"
    assert "less" not in filters["t.name"]["operators"]
    assert "contains" not in filters["t.name"]["operators"]
    assert filters["t.district"]["input"] == "select"
    assert filters["t.district"]["values"] == [{"KJD": "Kajiado"}]


# ---------------------------------------------------------------------------
# The compiler's text
# ---------------------------------------------------------------------------


def test_no_rules_is_no_filter(fields):
    assert compile_filter(None, fields) is None
    assert compile_filter("", fields) is None
    assert compile_filter(rules(), fields) is None
    assert describe_filter(None, fields) == ""


def test_a_text_is_compared_by_its_bytes(fields):
    assert compile_filter(rule("t.name", "equal", "Ann"), fields) == (
        "HEX({t}`name`) = " + hexed("Ann")
    )
    assert compile_filter(rule("p.status", "not_equal", "left"), fields) == (
        "({p}`status` IS NOT NULL AND HEX({p}`status`) <> " + hexed("left") + ")"
    )
    assert compile_filter(rule("t.district", "in", "KJD, NRB"), fields) == (
        "HEX({t}`district`) IN (" + hexed("KJD") + "," + hexed("NRB") + ")"
    )
    assert compile_filter(rule("t.name", "begins_with", "Ñ"), fields) == (
        "HEX({t}`name`) LIKE 'C391%'"
    )
    assert compile_filter(rule("t.name", "is_empty"), fields) == "HEX({t}`name`) = ''"


def test_a_number_a_date_and_a_group(fields):
    assert compile_filter(rule("t.age", "between", [25, 40]), fields) == (
        "({t}`age` >= 25 AND {t}`age` <= 40)"
    )
    assert compile_filter(rule("p.index", "less", "0.0000001"), fields) == (
        "{p}`index` < 0.0000001"
    )
    assert compile_filter(rule("t.joined", "greater", "2020-12-31"), fields) == (
        "{t}`joined` > '2020-12-31'"
    )
    assert (
        compile_filter(
            rules(
                rule("t.age", "is_null"),
                rule("p.visits", "greater", 2),
                condition="OR",
                negate=True,
            ),
            fields,
        )
        == "NOT (({t}`age` IS NULL OR {p}`visits` > 2))"
    )


def test_what_the_owner_types_never_reaches_the_sql(fields):
    sly = "x' OR '1'='1'; DROP TABLE teachers; --`"
    sql = compile_filter(rule("t.name", "equal", sly), fields)
    assert sql == "HEX({t}`name`) = " + hexed(sly)
    assert "DROP" not in sql and "'1'" not in sql


@pytest.mark.parametrize(
    "a_rule, reason",
    [
        (rule("t.nope", "equal", "a"), "no field t.nope"),
        (rule("t.name", "less", "a"), "does not apply to name"),
        (rule("t.name", "contains", "a"), "does not apply to name"),
        (rule("t.spot", "equal", "1 2"), "does not apply to spot"),
        (rule("t.age", "equal", "ten"), "is not a number"),
        (rule("p.visits", "equal", "2.5"), "is not a whole number"),
        (rule("t.age", "equal", "inf"), "is not a number"),
        (rule("t.joined", "equal", "2026-02-30"), "is not a date"),
        (rule("t.joined", "equal", "2026-02-03 10:00:00"), "is not a date"),
        (rule("t.seen", "equal", "2026-02-03"), "is not a date and time"),
        (rule("t.district", "in", ""), "needs at least one value"),
        (rule("t.age", "between", [1]), "needs 2 value(s)"),
    ],
)
def test_what_the_compiler_refuses(fields, a_rule, reason):
    with pytest.raises(FilterError) as refused:
        compile_filter(a_rule, fields)
    assert reason in str(refused.value)


def test_a_rule_set_that_is_not_one_is_refused(fields):
    with pytest.raises(FilterError):
        compile_filter("{not json", fields)
    with pytest.raises(FilterError):
        compile_filter("[1, 2]", fields)


def test_the_words(fields):
    words = describe_filter(
        rules(
            rule("p.status", "not_equal", "left"), rule("t.age", "between", [25, 40])
        ),
        fields,
    )
    assert words == "(property status is not 'left' and age is between '25' and '40')"


def test_the_markers(fields):
    sql = compile_filter(
        rules(rule("t.name", "is_not_null"), rule("p.status", "is_null")), fields
    )
    assert uses_properties(sql)
    assert not uses_properties(compile_filter(rule("t.age", "equal", 1), fields))
    assert resolve(sql, "t.") == "(t.`name` IS NOT NULL AND p.`status` IS NULL)"
    assert resolve("{t}`age` = 1", "") == "`age` = 1"


def test_the_properties_a_filter_reads(fields):
    stored = json.dumps(
        rules(rule("p.status", "equal", "a"), rules(rule("p.visits", "is_null")))
    )
    assert referenced_properties(stored) == {"status", "visits"}
    assert referenced_properties(None) == set()
    assert referenced_properties("{not json") == set()


# ---------------------------------------------------------------------------
# What the device runs: the SELECT over a SQLite mirror
# ---------------------------------------------------------------------------

ROWS = [
    # rowuuid, name, district, age, joined, seen, active, status, visits
    ("r1", "Ann", "KJD", 30, "2020-01-01", "2026-09-01 10:00:00", 1, "left", 3),
    ("r2", "ann", "kjd", 45, "2021-06-01", "2026-09-02 10:00:00", 1, "Left", 0),
    ("r3", "Ann ", "KJD ", None, None, None, 1, None, None),
    ("r4", "Ñandú", "NRB", 25, "2019-03-03", "2026-09-03 08:00:00", 1, "active", 1),
    ("r5", "", "NRB", 50, "2018-01-01", None, 1, "", 2),
    ("r6", "   ", "NRB", 60, "2017-01-01", None, 1, "left", 9),
    ("r7", "Ann", "KJD", 30, "2020-01-01", None, 0, "left", 3),
]


@pytest.fixture
def mirror():
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE teachers (rowuuid varchar(80), name varchar(120), "
        "district varchar(10), age int, joined date, seen datetime, _active int)"
    )
    db.execute(
        "CREATE TABLE teachers_properties (rowuuid varchar(80), status varchar(64), "
        "visits int)"
    )
    for r in ROWS:
        db.execute("INSERT INTO teachers VALUES (?,?,?,?,?,?,?)", r[:7])
        db.execute("INSERT INTO teachers_properties VALUES (?,?,?)", (r[0], r[7], r[8]))
    yield db
    db.close()


def served(mirror, fields, a_filter, columns=None):
    """The rowuuids the list serves: the SELECT lists.xml carries, with its
    tables resolved to the mirror's, as a device runs it."""
    sql, _ = build_list_select(
        "unused",
        "teachers",
        "name",
        columns or [],
        compile_filter(a_filter, fields),
        symbolic=True,
    )
    sql = sql.replace("{source.teachers_properties}", "teachers_properties").replace(
        "{source.teachers}", "teachers"
    )
    return sorted(row[0] for row in mirror.execute(sql).fetchall())


def test_the_device_compares_a_text_exactly(mirror, fields):
    # Not ann, not "Ann ", not the inactive one.
    assert served(mirror, fields, rule("t.name", "equal", "Ann")) == ["r1"]
    assert served(mirror, fields, rule("t.district", "in", "KJD,NRB")) == [
        "r1",
        "r4",
        "r5",
        "r6",
    ]


def test_a_negative_leaves_out_what_has_no_value(mirror, fields):
    # r3 has no status: "is not left" does not let it in.
    assert served(mirror, fields, rule("p.status", "not_equal", "left")) == [
        "r2",
        "r4",
        "r5",
    ]


def test_an_accent_a_prefix_and_a_suffix(mirror, fields):
    assert served(mirror, fields, rule("t.name", "begins_with", "Ñ")) == ["r4"]
    assert served(mirror, fields, rule("t.name", "ends_with", "n ")) == ["r3"]
    assert served(mirror, fields, rule("t.name", "not_begins_with", "A")) == [
        "r2",
        "r4",
        "r5",
        "r6",
    ]


def test_empty_is_empty_and_spaces_are_not(mirror, fields):
    assert served(mirror, fields, rule("t.name", "is_empty")) == ["r5"]
    assert "r6" in served(mirror, fields, rule("t.name", "is_not_empty"))


def test_numbers_and_dates(mirror, fields):
    assert served(mirror, fields, rule("t.age", "between", [25, 40])) == ["r1", "r4"]
    assert served(mirror, fields, rule("t.joined", "greater", "2020-12-31")) == ["r2"]
    assert served(mirror, fields, rule("t.seen", "less", "2026-09-02 10:00:00")) == [
        "r1"
    ]
    assert served(mirror, fields, rule("p.visits", "in", "0,1")) == ["r2", "r4"]


def test_a_property_filter_joins_the_properties_it_does_not_serve(mirror, fields):
    # No property column is served, and the SELECT joins the table anyway.
    assert served(mirror, fields, rule("p.visits", "greater", 2)) == ["r1", "r6"]


def test_groups(mirror, fields):
    either = rules(
        rule("t.age", "is_null"), rule("p.visits", "greater", 8), condition="OR"
    )
    assert served(mirror, fields, either) == ["r3", "r6"]
    assert served(mirror, fields, dict(either, **{"not": True})) == [
        "r1",
        "r2",
        "r4",
        "r5",
    ]
