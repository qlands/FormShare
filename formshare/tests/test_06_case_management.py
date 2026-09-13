"""The shape of a published list, asserted without a database.

The registry (docs/formshare_case_management/) generates real-time files from
repository tables. What matters about a list is decided in pure functions --
the SELECT it runs, the order of its columns, when it is stale, what its file
name may be -- so those are asserted here directly, the way
test_02_lookup_files.py asserts the shape of a lookup merge.
"""

import csv
import datetime
import io

import pytest

from formshare.processes.db import case_management as cm

# ---------------------------------------------------------------------------
# The file name is the entire coupling to the form designer
# ---------------------------------------------------------------------------


def test_list_filenames_are_boring_on_purpose():
    assert cm.valid_list_filename("cases.csv")
    assert cm.valid_list_filename("hh_members.geojson")
    assert cm.valid_list_filename("a2.csv")


def test_list_filenames_refuse_what_devices_would_choke_on():
    # Case matters: the manifest name and the form's reference must agree
    # byte for byte, so only one spelling is representable.
    assert not cm.valid_list_filename("Cases.csv")
    assert not cm.valid_list_filename("cases.CSV")
    assert not cm.valid_list_filename("2cases.csv")  # starts with a digit
    assert not cm.valid_list_filename("cases.txt")
    assert not cm.valid_list_filename("cases")
    assert not cm.valid_list_filename("my cases.csv")
    assert not cm.valid_list_filename("")
    assert not cm.valid_list_filename(None)


# ---------------------------------------------------------------------------
# The SELECT
# ---------------------------------------------------------------------------


def test_name_is_rowuuid_and_always_first():
    """The identity principle: the key of every list is rowuuid, served as
    name, not configurable."""
    sql, headers = cm.build_list_select("FS_abc", "maintable", "hh_name", [])
    assert sql.startswith("SELECT rowuuid AS name,")
    assert headers[0] == "name"
    assert headers[1] == "label"


def test_columns_keep_their_order_and_aliases():
    sql, headers = cm.build_list_select(
        "FS_abc",
        "maintable",
        "hh_name",
        [("hh_id", None), ("status", "condition")],
    )
    assert headers == ["name", "label", "hh_id", "condition"]
    assert "`hh_id` AS `hh_id`" in sql
    assert "`status` AS `condition`" in sql


def test_membership_filter_lands_in_the_where():
    sql, _ = cm.build_list_select("FS_abc", "maintable", "hh_name", [], "_active = 1")
    assert " WHERE _active = 1 " in sql


def test_rows_are_ordered_by_rowuuid():
    """Stable order makes two generations of an unchanged table
    byte-identical, which is what lets the manifest hash say nothing
    changed -- and a repeat table has no _submitted_date to order by."""
    sql, _ = cm.build_list_select("FS_abc", "rpt_members", "member_name", [])
    assert sql.endswith(" ORDER BY rowuuid")


def test_a_repeat_table_is_as_good_a_source_as_maintable():
    sql, _ = cm.build_list_select("FS_abc", "rpt_members", "member_name", [])
    assert "FROM `FS_abc`.`rpt_members`" in sql


def test_a_duplicated_alias_is_refused_not_shifted():
    """The CSV would shift a column silently; the builder refuses instead."""
    with pytest.raises(ValueError):
        cm.build_list_select("FS_abc", "maintable", "hh_name", [("label", None)])
    with pytest.raises(ValueError):
        cm.build_list_select(
            "FS_abc",
            "maintable",
            "hh_name",
            [("status", "cond"), ("old_status", "cond")],
        )


def test_an_identifier_that_is_not_one_is_refused():
    """The UI only offers dictionary columns; this is the backstop."""
    for bad in ["a b", "a;drop", "a`b", "", None]:
        with pytest.raises(ValueError):
            cm.build_list_select("FS_abc", "maintable", bad, [])


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------


def test_a_list_never_generated_is_stale():
    assert cm.list_is_stale(None)
    assert cm.list_is_stale(None, None)


def test_a_change_after_generation_makes_it_stale():
    generated = datetime.datetime(2026, 9, 1, 12, 0, 0)
    before = datetime.datetime(2026, 9, 1, 11, 0, 0)
    after = datetime.datetime(2026, 9, 1, 13, 0, 0)
    assert not cm.list_is_stale(generated, before)
    assert cm.list_is_stale(generated, after)
    # any one changed source is enough
    assert cm.list_is_stale(generated, before, after)


def test_an_unknown_change_date_is_ignored():
    """A source without submissions reports None; that is not a change."""
    generated = datetime.datetime(2026, 9, 1, 12, 0, 0)
    assert not cm.list_is_stale(generated, None, None)


# ---------------------------------------------------------------------------
# The CSV
# ---------------------------------------------------------------------------


def test_the_csv_is_what_the_select_produced(tmp_path):
    out = str(tmp_path / "cases.csv")
    cm.write_list_csv(
        ["name", "label", "status"],
        [("uuid-1", "Maria", "registered"), ("uuid-2", "Juan", None)],
        out,
    )
    with io.open(out, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["name", "label", "status"]
    assert rows[1] == ["uuid-1", "Maria", "registered"]
    # NULL goes out as empty, never as the string None
    assert rows[2] == ["uuid-2", "Juan", ""]


def test_every_field_is_double_quoted(tmp_path):
    """Data can carry commas, so nothing is left for a parser to guess:
    every field goes out quoted, headers included."""
    out = str(tmp_path / "cases.csv")
    cm.write_list_csv(
        ["name", "label"],
        [("uuid-1", "Perez, Maria"), ("uuid-2", None)],
        out,
    )
    with io.open(out, encoding="utf-8", newline="") as f:
        raw = f.read().splitlines()
    assert raw[0] == '"name","label"'
    assert raw[1] == '"uuid-1","Perez, Maria"'
    assert raw[2] == '"uuid-2",""'


def test_the_csv_survives_commas_and_quotes(tmp_path):
    out = str(tmp_path / "cases.csv")
    cm.write_list_csv(
        ["name", "label"],
        [("uuid-1", 'Maria "La China", de Lima')],
        out,
    )
    with io.open(out, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1] == ["uuid-1", 'Maria "La China", de Lima']


def test_a_sample_is_limited_and_a_full_list_is_not():
    sql, _ = cm.build_list_select("FS_abc", "maintable", "hh_name", [], limit=10)
    assert sql.endswith(" ORDER BY rowuuid LIMIT 10")
    sql, _ = cm.build_list_select("FS_abc", "maintable", "hh_name", [])
    assert "LIMIT" not in sql


# ---------------------------------------------------------------------------
# Consumer detection (feature 5 / stage 4): which list a form links to
# ---------------------------------------------------------------------------

LISTS = [
    {
        "list_id": "centre_lists",
        "list_filename": "centre_lists.csv",
        "source_table": "maintable",
    },
    {
        "list_id": "roster",
        "list_filename": "roster.csv",
        "source_table": "roster",
    },
]


def _select_field(name, filename):
    return {"name": name, "selecttype": "3", "externalfilename": filename}


def test_a_form_consuming_two_lists_detects_both_with_selectors():
    """The schools/staff follow-up: centre_id picks a school, worker_id picks
    a staff member from the roster."""
    fields = [
        {"name": "note1", "selecttype": "0", "externalfilename": ""},
        _select_field("centre_id", "centre_lists.csv"),
        _select_field("worker_id", "roster.csv"),
    ]
    consumers = cm.detect_consumers(fields, LISTS)
    by_list = {c["list_id"]: c for c in consumers}
    assert by_list["centre_lists"]["selector_field"] == "centre_id"
    assert by_list["roster"]["selector_field"] == "worker_id"


def test_a_select_not_matching_any_list_is_not_a_consumer():
    fields = [_select_field("species", "species.csv")]
    assert cm.detect_consumers(fields, LISTS) == []


def test_an_ordinary_select_one_is_not_a_consumer():
    """selecttype 1 is a choices-sheet select; only 3 (from file) can match a
    published list."""
    fields = [{"name": "sex", "selecttype": "1", "externalfilename": ""}]
    assert cm.detect_consumers(fields, LISTS) == []


# ---------------------------------------------------------------------------
# Consumer persistence and the case-link choice, against a real (SQLite) DB
# ---------------------------------------------------------------------------


class _Req:
    """Minimal request: just a dbsession and translate, like the fast files use."""

    def __init__(self, session):
        self.dbsession = session

    @staticmethod
    def translate(message):
        return message


@pytest.fixture
def db_request():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.mysql import MEDIUMTEXT, BIGINT
    from formshare.models.formshare import (
        Base,
        Odkform,
        PublishedList,
        PublishedListColumn,
        ListConsumer,
    )

    # The models use MySQL-specific column types; teach SQLite to build them so
    # the registry tables can be created for a pure-Python test.
    @compiles(MEDIUMTEXT, "sqlite")
    def _mediumtext(element, compiler, **kw):  # noqa
        return "TEXT"

    @compiles(BIGINT, "sqlite")
    def _bigint(element, compiler, **kw):  # noqa
        return "BIGINT"

    engine = create_engine("sqlite://")
    # Only the tables these tests touch -- create_all would pull in every model
    # and more MySQL-only types than are worth teaching SQLite.
    Base.metadata.create_all(
        engine,
        tables=[
            Odkform.__table__,
            PublishedList.__table__,
            PublishedListColumn.__table__,
            ListConsumer.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    # A project with a source form (built) and a follow-up form.
    # FK enforcement is off by default in SQLite, so only the rows the queries
    # read are needed: the two forms and the two lists.
    session.add(
        Odkform(
            project_id="p",
            form_id="tool1",
            form_name="Tool1",
            form_schema="FS_src",
            form_directory="d1",
            form_pkey="school_id",
            form_pubby="u",
        )
    )
    session.add(
        Odkform(
            project_id="p",
            form_id="tool2",
            form_name="Tool2",
            form_directory="d2",
            form_pubby="u",
        )
    )
    session.add(
        PublishedList(
            project_id="p",
            list_id="centre_lists",
            list_filename="centre_lists.csv",
            list_format="csv",
            source_project="p",
            source_form="tool1",
            source_table="maintable",
            label_column="school",
        )
    )
    session.add(
        PublishedList(
            project_id="p",
            list_id="roster",
            list_filename="roster.csv",
            list_format="csv",
            source_project="p",
            source_form="tool1",
            source_table="roster",
            label_column="worker_name",
        )
    )
    session.commit()
    return _Req(session)


def _two_list_fields():
    return [
        _select_field("centre_id", "centre_lists.csv"),
        _select_field("worker_id", "roster.csv"),
    ]


def test_sync_stores_both_consumers_and_leaves_the_link_unset(db_request):
    ok, _ = cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    assert ok
    consumers = {
        c["list_id"]: c for c in cm.get_form_consumers(db_request, "p", "tool2")
    }
    assert set(consumers) == {"centre_lists", "roster"}
    assert consumers["roster"]["selector_field"] == "worker_id"
    # Two consumers: the choice is the owner's, so none is auto-linked.
    assert cm.get_case_link_consumer(db_request, "p", "tool2") is None


def test_a_single_consumer_is_auto_linked(db_request):
    ok, _ = cm.sync_form_consumers(
        db_request, "p", "tool2", [_select_field("worker_id", "roster.csv")]
    )
    assert ok
    link = cm.get_case_link_consumer(db_request, "p", "tool2")
    assert link is not None and link["list_id"] == "roster"


def test_setting_the_case_link_is_exclusive(db_request):
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    cm.set_case_link(db_request, "p", "tool2", "roster")
    assert cm.get_case_link_consumer(db_request, "p", "tool2")["list_id"] == "roster"
    # Choosing another clears the first.
    cm.set_case_link(db_request, "p", "tool2", "centre_lists")
    link = cm.get_case_link_consumer(db_request, "p", "tool2")
    assert link["list_id"] == "centre_lists"
    assert (
        sum(
            int(c["consumer_is_link"] or 0)
            for c in cm.get_form_consumers(db_request, "p", "tool2")
        )
        == 1
    )


def test_sync_drops_a_reference_the_form_no_longer_makes(db_request):
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    # The form is edited to drop the school selector.
    cm.sync_form_consumers(
        db_request, "p", "tool2", [_select_field("worker_id", "roster.csv")]
    )
    consumers = cm.get_form_consumers(db_request, "p", "tool2")
    assert [c["list_id"] for c in consumers] == ["roster"]


def test_the_case_link_resolves_to_its_source_table(db_request):
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    cm.set_case_link(db_request, "p", "tool2", "roster")
    schema, table = cm.get_case_link_source(db_request, "p", "tool2")
    assert schema == "FS_src"
    assert table == "roster"


def test_consumer_sources_lists_every_built_source(db_request):
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    cm.set_case_link(db_request, "p", "tool2", "roster")
    sources = {
        s["selector_field"]: s
        for s in cm.get_consumer_sources(db_request, "p", "tool2")
    }
    assert sources["worker_id"]["source_table"] == "roster"
    assert sources["worker_id"]["is_link"] is True
    assert sources["centre_id"]["source_table"] == "maintable"
    assert sources["centre_id"]["is_link"] is False


def test_the_source_form_is_seen_as_having_consumers(db_request):
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    assert cm.source_form_has_consumers(db_request, "p", "tool1") is True
    assert cm.source_form_has_consumers(db_request, "p", "tool2") is False
