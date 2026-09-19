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
    # active is on by default, so a filter is ANDed after it.
    sql, _ = cm.build_list_select(
        "FS_abc", "maintable", "hh_name", [], "status = 'open'"
    )
    assert " WHERE _active = 1 AND status = 'open' " in sql


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
        MediaFile,
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
            MediaFile.__table__,
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


# ---------------------------------------------------------------------------
# Active / inactive rows (2026-09-13): a list serves one or the other
# ---------------------------------------------------------------------------


def test_a_list_serves_active_rows_by_default():
    sql, _ = cm.build_list_select("FS_abc", "maintable", "hh_name", [])
    assert " WHERE _active = 1 " in sql


def test_a_list_can_serve_inactive_rows():
    sql, _ = cm.build_list_select("FS_abc", "maintable", "hh_name", [], active=0)
    assert " WHERE _active = 0 " in sql


def test_active_and_a_filter_combine():
    sql, _ = cm.build_list_select(
        "FS_abc", "maintable", "hh_name", [], "status = 'open'", active=1
    )
    assert " WHERE _active = 1 AND status = 'open' " in sql


def test_active_none_serves_both():
    """The rare list that wants active and inactive together."""
    sql, _ = cm.build_list_select("FS_abc", "maintable", "hh_name", [], active=None)
    assert "_active" not in sql
    assert sql.endswith(" ORDER BY rowuuid")


# ---------------------------------------------------------------------------
# The create.xml link attributes: FK for all, membership trigger for the
# active case link only (2026-09-13)
# ---------------------------------------------------------------------------

_CREATE_XML = (
    "<XMLSchemaStructure><tables><table name='maintable'>"
    "<field name='centre_id' type='int'/>"
    "<field name='worker_id' type='int'/>"
    "</table></tables></XMLSchemaStructure>"
)


def _linked_root(sources):
    from lxml import etree

    root = etree.fromstring(_CREATE_XML)
    key_types = {
        "FS_src.maintable.rowuuid": ("varchar", "80"),
        "FS_src.roster.rowuuid": ("varchar", "80"),
    }
    ok, message = cm.apply_link_attributes(root, sources, key_types)
    assert ok, message
    return root


def test_every_selector_gets_a_foreign_key_and_the_rowuuid_type():
    root = _linked_root(
        [
            {
                "selector_field": "worker_id",
                "source_schema": "FS_src",
                "source_table": "roster",
                "is_link": True,
                "list_active": 1,
            },
            {
                "selector_field": "centre_id",
                "source_schema": "FS_src",
                "source_table": "maintable",
                "is_link": False,
                "list_active": 1,
            },
        ]
    )
    for name, ref in [
        ("worker_id", "FS_src.roster"),
        ("centre_id", "FS_src.maintable"),
    ]:
        field = root.find(".//field[@name='" + name + "']")
        assert field.get("type") == "varchar"
        assert field.get("size") == "80"
        assert field.get("rtable") == ref
        assert field.get("rfield") == "rowuuid"
        assert field.get("on_delete") == "RESTRICT"


def test_the_active_case_link_gets_the_membership_trigger():
    root = _linked_root(
        [
            {
                "selector_field": "worker_id",
                "source_schema": "FS_src",
                "source_table": "roster",
                "is_link": True,
                "list_active": 1,
            }
        ]
    )
    table = root.find(".//table[@name='maintable']")
    assert table.get("case_followup") == "true"
    assert table.get("creator_table") == "FS_src.roster"
    assert table.get("creator_field") == "rowuuid"
    assert table.get("selector_field") == "worker_id"
    assert table.get("block_trigger") is not None


def test_an_auxiliary_link_gets_no_membership_trigger():
    root = _linked_root(
        [
            {
                "selector_field": "centre_id",
                "source_schema": "FS_src",
                "source_table": "maintable",
                "is_link": False,
                "list_active": 1,
            }
        ]
    )
    table = root.find(".//table[@name='maintable']")
    assert table.get("case_followup") is None
    # but the foreign key is still there
    assert root.find(".//field[@name='centre_id']").get("rtable") == "FS_src.maintable"


def test_an_inactive_case_link_gets_a_trigger_that_checks_for_inactive_rows():
    """RSTools chooses the _active the membership trigger checks by
    case_action_type (rstools.md 6.5): a link over an inactive-serving list
    asks for "activate", so the trigger refuses an active or unknown case;
    case_action stays false, the trigger being a check and never a write."""
    root = _linked_root(
        [
            {
                "selector_field": "worker_id",
                "source_schema": "FS_src",
                "source_table": "roster",
                "is_link": True,
                "list_active": 0,
            }
        ]
    )
    table = root.find(".//table[@name='maintable']")
    assert table.get("case_followup") == "true"
    assert table.get("case_action_type") == "activate"
    assert table.get("case_action") == "false"
    assert root.find(".//field[@name='worker_id']").get("rtable") == "FS_src.roster"


def test_an_active_case_link_asks_the_trigger_to_follow():
    root = _linked_root(
        [
            {
                "selector_field": "worker_id",
                "source_schema": "FS_src",
                "source_table": "roster",
                "is_link": True,
                "list_active": 1,
            }
        ]
    )
    table = root.find(".//table[@name='maintable']")
    assert table.get("case_followup") == "true"
    assert table.get("case_action_type") == "follow"
    assert table.get("case_action") == "false"


# ---------------------------------------------------------------------------
# Predicate helpers: is a project/form/list part of a longitudinal workflow
# ---------------------------------------------------------------------------


def test_project_is_longitudinal_when_a_published_list_is_used(db_request):
    # Lists exist, but until a form references one the project is not yet
    # running a longitudinal workflow.
    assert cm.project_is_longitudinal(db_request, "p") is False
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    assert cm.project_is_longitudinal(db_request, "p") is True
    assert cm.project_is_longitudinal(db_request, "no_such_project") is False


def test_form_creates_cases_when_its_list_is_used(db_request):
    # tool1 sources both lists, but only once a form uses one does it create
    # cases; tool2 sources none.
    assert cm.form_creates_cases(db_request, "p", "tool1") is False
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    assert cm.form_creates_cases(db_request, "p", "tool1") is True
    assert cm.form_creates_cases(db_request, "p", "tool2") is False


def test_form_consumes_cases_when_it_references_a_list(db_request):
    assert cm.form_consumes_cases(db_request, "p", "tool2") is False
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    assert cm.form_consumes_cases(db_request, "p", "tool2") is True
    # the source form is not a consumer
    assert cm.form_consumes_cases(db_request, "p", "tool1") is False


def test_list_has_active_consumers_only_once_the_consumer_is_built(db_request):
    from formshare.models.formshare import Odkform

    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    # tool2 consumes the roster list but has no repository yet
    assert cm.list_has_active_consumers(db_request, "p", "roster") is False
    # build tool2: now the consumer is wired into the schema
    db_request.dbsession.query(Odkform).filter(Odkform.form_id == "tool2").update(
        {"form_schema": "FS_tool2"}
    )
    db_request.dbsession.flush()
    assert cm.list_has_active_consumers(db_request, "p", "roster") is True
    # a list no form consumes at all
    assert cm.list_has_active_consumers(db_request, "p", "no_such_list") is False


def test_the_link_lands_on_the_maintable_not_a_same_named_lookup_column():
    """The tosin failure: the served roster.csv carried a column named
    worker_id, RSTools froze the CSV into lkpworker_id, and that lookup's
    same-named field came first in document order. The link must land on
    maintable.worker_id and leave the lookup column alone."""
    from lxml import etree

    root = etree.fromstring(
        "<XMLSchemaStructure><tables>"
        "<table name='lkpworker_id'>"
        "<field name='worker_id_cod' type='varchar'/>"
        "<field name='worker_id' type='varchar'/>"
        "</table>"
        "<table name='maintable'>"
        "<field name='worker_id' type='int'/>"
        "</table>"
        "</tables></XMLSchemaStructure>"
    )
    ok, message = cm.apply_link_attributes(
        root,
        [
            {
                "selector_field": "worker_id",
                "source_schema": "FS_src",
                "source_table": "roster",
                "is_link": True,
                "list_active": 1,
            }
        ],
        {"FS_src.roster.rowuuid": ("varchar", "80")},
    )
    assert ok, message
    main_field = root.find(".//table[@name='maintable']/field[@name='worker_id']")
    lookup_field = root.find(".//table[@name='lkpworker_id']/field[@name='worker_id']")
    assert main_field.get("rtable") == "FS_src.roster"
    assert main_field.get("type") == "varchar"
    assert lookup_field.get("rtable") is None


# ---------------------------------------------------------------------------
# Value lists (2026-09-16): a list keyed by a column -- districts from schools
# ---------------------------------------------------------------------------


def test_a_value_list_serves_each_distinct_value_once_as_name():
    sql, headers = cm.build_list_select(
        "FS_abc", "maintable", "centre_district", [], key_column="centre_district"
    )
    assert sql.startswith("SELECT DISTINCT `centre_district` AS name,")
    assert "rowuuid" not in sql
    assert sql.endswith(" ORDER BY name")
    assert headers == ["name", "label"]


def test_a_value_list_still_serves_only_active_rows():
    sql, _ = cm.build_list_select(
        "FS_abc", "maintable", "centre_district", [], key_column="centre_district"
    )
    assert " WHERE _active = 1 " in sql


def test_a_row_list_is_unchanged_by_the_value_list_feature():
    sql, _ = cm.build_list_select("FS_abc", "maintable", "hh_name", [])
    assert sql.startswith("SELECT rowuuid AS name,")
    assert "DISTINCT" not in sql
    assert sql.endswith(" ORDER BY rowuuid")


def test_a_value_list_consumer_is_retyped_but_never_linked():
    """The selector holds a district name, so it needs the key column's type
    (RSTools emits int for an external select) and nothing else: no foreign
    key -- the key is neither unique nor a rowuuid -- and no trigger."""
    from lxml import etree

    root = etree.fromstring(
        "<XMLSchemaStructure><tables><table name='maintable'>"
        "<field name='district_filter' type='int'/>"
        "</table></tables></XMLSchemaStructure>"
    )
    ok, message = cm.apply_link_attributes(
        root,
        [
            {
                "selector_field": "district_filter",
                "source_schema": "FS_src",
                "source_table": "maintable",
                "is_link": True,  # even if someone stored it, it cannot link
                "list_active": 1,
                "key_column": "centre_district",
            }
        ],
        {"FS_src.maintable.centre_district": ("text", "65535")},
    )
    assert ok, message
    field = root.find(".//field[@name='district_filter']")
    assert field.get("type") == "text"
    assert field.get("rtable") is None
    assert root.find(".//table[@name='maintable']").get("case_followup") is None


def _publish_districts(db_request):
    from formshare.models.formshare import PublishedList

    db_request.dbsession.add(
        PublishedList(
            project_id="p",
            list_id="districts",
            list_filename="districts.csv",
            list_format="csv",
            source_project="p",
            source_form="tool1",
            source_table="maintable",
            label_column="centre_district",
            list_key_column="centre_district",
        )
    )
    db_request.dbsession.flush()


def test_a_value_list_cannot_become_the_case_link(db_request):
    _publish_districts(db_request)
    fields = [_select_field("district_filter", "districts.csv")]
    cm.sync_form_consumers(db_request, "p", "tool2", fields)
    # A lone value-list consumer is not auto-linked...
    assert cm.get_case_link_consumer(db_request, "p", "tool2") is None
    # ...and cannot be linked on purpose either.
    ok, message = cm.set_case_link(db_request, "p", "tool2", "districts")
    assert ok is False and "value list" in message
    # The build sees the key column and no link.
    sources = cm.get_consumer_sources(db_request, "p", "tool2")
    assert sources[0]["key_column"] == "centre_district"
    assert sources[0]["is_link"] is False


def test_a_merge_child_inherits_its_parents_links(db_request):
    from formshare.models.formshare import Odkform

    db_request.dbsession.add(
        Odkform(
            project_id="p",
            form_id="tool2_v6",
            form_name="Tool2 v6",
            form_directory="d3",
            form_pubby="u",
            parent_form="tool2",
        )
    )
    db_request.dbsession.flush()
    cm.sync_form_consumers(db_request, "p", "tool2", _two_list_fields())
    cm.set_case_link(db_request, "p", "tool2", "roster")
    ok, _ = cm.inherit_consumers(db_request, "p", "tool2", "tool2_v6")
    assert ok
    child = {
        c["list_id"]: c for c in cm.get_form_consumers(db_request, "p", "tool2_v6")
    }
    assert set(child) == {"centre_lists", "roster"}
    assert child["roster"]["consumer_is_link"] == 1
    assert child["roster"]["selector_field"] == "worker_id"
    # Idempotent: a second inheritance adds nothing.
    cm.inherit_consumers(db_request, "p", "tool2", "tool2_v6")
    assert len(cm.get_form_consumers(db_request, "p", "tool2_v6")) == 2
    # A sync against the child's own fields keeps the inherited link.
    cm.sync_form_consumers(db_request, "p", "tool2_v6", _two_list_fields())
    assert cm.get_case_link_consumer(db_request, "p", "tool2_v6")["list_id"] == "roster"


def test_a_definition_change_invalidates_every_served_copy(db_request):
    """Adding a column (or any definition change) clears file_lastgen on
    every copy of the list in its project -- the stamp the manifest gate reads
    as "never generated" -- and on nothing else."""
    from formshare.models.formshare import MediaFile

    stamp = datetime.datetime(2026, 9, 1, 12, 0, 0)
    copies = [
        ("p", "tool2", "roster.csv"),
        ("p", "tool3", "roster.csv"),
        ("p", "tool2", "centre_lists.csv"),
        ("q", "tool9", "roster.csv"),
    ]
    for an_index, (project, form, name) in enumerate(copies):
        db_request.dbsession.add(
            MediaFile(
                file_id="f{}".format(an_index),
                project_id=project,
                form_id=form,
                file_name=name,
                file_udate=stamp,
                file_mimetype="text/csv",
                file_lastgen=stamp,
            )
        )
    db_request.dbsession.flush()

    done, message = cm.invalidate_list_copies(db_request, "p", "roster")
    assert done, message
    stamps = {
        (a_copy.project_id, a_copy.form_id, a_copy.file_name): a_copy.file_lastgen
        for a_copy in db_request.dbsession.query(MediaFile)
    }
    assert stamps[("p", "tool2", "roster.csv")] is None
    assert stamps[("p", "tool3", "roster.csv")] is None
    # Another list's copy and another project's file are untouched.
    assert stamps[("p", "tool2", "centre_lists.csv")] == stamp
    assert stamps[("q", "tool9", "roster.csv")] == stamp
    assert cm.invalidate_list_copies(db_request, "p", "no_such_list")[0] is False


def test_the_workflow_model_folds_versions_ranks_the_chain_and_reads_the_schema():
    """The diagram's model: a merged-away version and its consumers fold into
    the version that owns the schema, forms are ranked along the chain, only
    tables that take part are shown, and the edge labels come from the built
    schema (foreign key rule, membership trigger), not from the registry."""
    forms = [
        {
            "form_id": "tool1",
            "form_name": "Tool 1",
            "form_version": "8",
            "form_schema": "FS_11111111_a",
            "parent_form": None,
            "form_pkey": "form_key",
        },
        {
            "form_id": "tool2",
            "form_name": "Tool 2",
            "form_version": "5",
            "form_schema": "FS_22222222_b",
            "parent_form": None,
            "form_pkey": "form_key",
        },
        {
            "form_id": "tool2_v6",
            "form_name": "Tool 2",
            "form_version": "6",
            "form_schema": "FS_22222222_b",
            "parent_form": "tool2",
            "form_pkey": "form_key",
        },
        {
            "form_id": "tool3",
            "form_name": "Tool 3",
            "form_version": "4",
            "form_schema": None,
            "parent_form": None,
            "form_pkey": "form_key",
        },
    ]
    lists = [
        {
            "list_id": "centre_list",
            "list_filename": "centre_list.csv",
            "source_form": "tool1",
            "source_table": "maintable",
            "label_column": "centre_school",
            "list_key_column": None,
        },
        {
            "list_id": "roster",
            "list_filename": "roster.csv",
            "source_form": "tool1",
            "source_table": "roster",
            "label_column": "worker_name",
            "list_key_column": None,
        },
        {
            "list_id": "centre_list2",
            "list_filename": "centre_list2.csv",
            "source_form": "tool2",
            "source_table": "maintable",
            "label_column": "centre_school",
            "list_key_column": "centre_school",
        },
    ]
    list_columns = [
        {"list_id": "roster", "column_name": "worker_name", "column_as": "worker_id"},
        {"list_id": "roster", "column_name": "eligible", "column_as": None},
    ]
    consumers = [
        {
            "list_id": "centre_list",
            "consumer_form": "tool2",
            "consumer_role": "reads",
            "selector_field": "centre_id",
            "consumer_is_link": 0,
        },
        {
            "list_id": "roster",
            "consumer_form": "tool2",
            "consumer_role": "updates",
            "selector_field": "worker_id",
            "consumer_is_link": 1,
        },
        {
            "list_id": "centre_list",
            "consumer_form": "tool2_v6",
            "consumer_role": "reads",
            "selector_field": "centre_id",
            "consumer_is_link": 0,
        },
        {
            "list_id": "roster",
            "consumer_form": "tool2_v6",
            "consumer_role": "updates",
            "selector_field": "worker_id",
            "consumer_is_link": 1,
        },
        {
            "list_id": "centre_list2",
            "consumer_form": "tool3",
            "consumer_role": "reads",
            "selector_field": "centre_id",
            "consumer_is_link": 0,
        },
    ]
    tables = [
        {
            "form_id": "tool1",
            "table_name": "maintable",
            "parent_table": None,
            "table_desc": "Main",
        },
        {
            "form_id": "tool1",
            "table_name": "roster",
            "parent_table": "maintable",
            "table_desc": "Staff",
        },
        {
            "form_id": "tool1",
            "table_name": "ext_visits",
            "parent_table": "maintable",
            "table_desc": "Visits",
        },
        {
            "form_id": "tool2_v6",
            "table_name": "maintable",
            "parent_table": None,
            "table_desc": "Main",
        },
        {
            "form_id": "tool2_v6",
            "table_name": "cpd",
            "parent_table": "maintable",
            "table_desc": "CPD",
        },
    ]
    fks = [
        {
            "s": "FS_22222222_b",
            "t": "maintable",
            "c": "centre_id",
            "rs": "FS_11111111_a",
            "rt": "maintable",
            "rc": "rowuuid",
            "rule": "RESTRICT",
        },
        {
            "s": "FS_22222222_b",
            "t": "maintable",
            "c": "worker_id",
            "rs": "FS_11111111_a",
            "rt": "roster",
            "rc": "rowuuid",
            "rule": "RESTRICT",
        },
    ]
    triggers = [
        {
            "s": "FS_22222222_b",
            "t": "maintable",
            "body": "BEGIN SELECT COUNT(*) INTO rowcount FROM FS_11111111_a.roster WHERE _active = 1 AND rowuuid = new.worker_id; END",
        }
    ]
    model = cm.build_workflow_model(
        {"code": "dd", "name": "ECCE"},
        forms,
        lists,
        list_columns,
        consumers,
        tables,
        fks,
        triggers,
    )

    by_id = {f["id"]: f for f in model["forms"]}
    assert list(by_id) == ["tool1", "tool2_v6", "tool3"]  # v5 folded into v6
    assert [by_id[k]["rank"] for k in by_id] == [0, 1, 2]
    assert [t["name"] for t in by_id["tool1"]["tables"]] == [
        "maintable",
        "roster",
    ]  # ext_visits takes no part
    assert [x["name"] for x in by_id["tool1"]["tables"][1]["fields"]] == [
        "rowuuid",
        "parent_rowuuid",
    ]
    assert [x["name"] for x in by_id["tool2_v6"]["tables"][0]["fields"]] == [
        "rowuuid",
        "form_key",
        "centre_id",
        "worker_id",
    ]
    assert by_id["tool3"]["schema"] is None and [
        t["name"] for t in by_id["tool3"]["tables"]
    ] == ["maintable"]

    kinds = {}
    for e in model["edges"]:
        kinds.setdefault(e["kind"], []).append(e)
    assert len(kinds["publishes"]) == 3 and len(kinds["repeat"]) == 1
    assert kinds["repeat"][0]["from"] == {
        "form": "tool1",
        "table": "roster",
        "field": "parent_rowuuid",
    }
    (link,) = kinds["link"]
    assert link["to"] == {
        "form": "tool2_v6",
        "table": "maintable",
        "field": "worker_id",
    }
    assert (
        link["label"]
        == "case link\nFK ON DELETE RESTRICT\ntrigger: roster.rowuuid must be _active"
    )
    reads = {e["to"]["form"]: e["label"] for e in kinds["reads"]}
    assert reads["tool2_v6"] == "reads\nFK ON DELETE RESTRICT"
    assert reads["tool3"] == "reads"  # no repository yet: nothing to say about a key
    # centre_list2 is published by the version that owns the schema now
    assert kinds["publishes"][-1]["from"] == {
        "form": "tool2_v6",
        "table": "maintable",
        "field": "rowuuid",
    }

    lists_by_id = {l["id"]: l for l in model["lists"]}
    assert (
        lists_by_id["roster"]["rank"] == 0.5
        and lists_by_id["centre_list2"]["rank"] == 1.5
    )
    assert (
        lists_by_id["centre_list2"]["value_list"]
        and "DISTINCT centre_school" in lists_by_id["centre_list2"]["kind"]
    )
    assert lists_by_id["roster"]["columns"] == ["worker_name → worker_id", "eligible"]


def test_a_default_is_checked_against_its_type():
    """Empty is NULL; a number must be one; dates are real dates in the two
    formats; the geo types are ODK's textual forms."""
    ok = cm.validate_property_default
    assert ok("integer", "  ") == (True, None, "")
    assert ok("integer", "42") == (True, "42", "")
    assert ok("integer", "AAA")[0] is False
    assert ok("integer", "1.5")[0] is False
    assert ok("decimal", "12.345") == (True, "12.345", "")
    assert ok("decimal", "AAA")[0] is False
    assert ok("decimal", "1.2345")[0] is False  # decimal(10,3)
    assert ok("date", "2026-09-17") == (True, "2026-09-17", "")
    assert ok("date", "0")[0] is False
    assert ok("date", "AAA")[0] is False
    assert ok("date", "2026-02-30")[0] is False
    assert ok("datetime", "2026-09-17 08:30:00") == (True, "2026-09-17 08:30:00", "")
    assert ok("datetime", "0")[0] is False
    assert ok("datetime", "2026-09-17")[0] is False
    assert ok("string", "x" * 255)[0] is True
    assert ok("string", "x" * 256)[0] is False
    assert ok("geopoint", "0.31 32.58 1200 5") == (True, "0.31 32.58 1200 5", "")
    assert ok("geopoint", "95 32")[0] is False
    assert ok("geotrace", "0.31 32.58;0.32 32.59")[0] is True
    assert ok("geotrace", "0.31 32.58")[0] is False
    assert ok("geoshape", "0 0;0 1;1 1;0 0")[0] is True
    assert ok("geoshape", "0 0;0 1;1 1;1 0")[0] is False  # not closed
    assert ok("nonsense", "1")[0] is False


def test_properties_ddl_creates_the_table_once_and_adds_columns_after():
    """The first property creates <table>_properties, keyed and foreign-keyed
    on rowuuid with the source column's charset and collation; the next ones
    add a column of the type's MySQL shape, with the default every row
    starts at; a trace or shape carries RSTools' derived geometry beside it."""
    create = cm.properties_ddl(
        "FS_s",
        "roster",
        "risk_factor",
        "integer",
        "0",
        True,
        "utf8mb3",
        "utf8mb3_general_ci",
    )
    assert create == (
        "CREATE TABLE `FS_s`.`roster_properties` (rowuuid VARCHAR(80) CHARACTER SET "
        "utf8mb3 COLLATE utf8mb3_general_ci NOT NULL, `risk_factor` int DEFAULT 0, "
        "_lastupdate DATETIME NULL, PRIMARY KEY (rowuuid), "
        "CONSTRAINT `fk_roster_properties` FOREIGN KEY (rowuuid) "
        "REFERENCES `FS_s`.`roster` (rowuuid) ON DELETE CASCADE) ENGINE=InnoDB"
    )
    assert cm.properties_ddl(
        "FS_s", "roster", "next_visit", "date", None, False, "x", "y"
    ) == (
        "ALTER TABLE `FS_s`.`roster_properties` ADD COLUMN `next_visit` date DEFAULT NULL"
    )
    assert cm.properties_ddl(
        "FS_s", "roster", "status", "string", "it's new", False, "x", "y"
    ) == (
        "ALTER TABLE `FS_s`.`roster_properties` ADD COLUMN `status` varchar(255) DEFAULT 'it''s new'"
    )
    route = cm.properties_ddl(
        "FS_s", "roster", "route", "geotrace", None, False, "x", "y"
    )
    assert route.startswith(
        "ALTER TABLE `FS_s`.`roster_properties` ADD COLUMN `route` text DEFAULT NULL, "
        "ADD COLUMN `route_geom` geometry GENERATED ALWAYS AS (CASE WHEN "
    )
    assert route.endswith(") STORED SRID 4326")
    assert "LINESTRING(" in route and "POLYGON((" not in route
    assert "POLYGON((" in cm.geometry_expression("area", True)
    assert cm.drop_property_ddl("FS_s", "roster", "route", "geotrace") == (
        "ALTER TABLE `FS_s`.`roster_properties` DROP COLUMN `route_geom`, DROP COLUMN `route`"
    )
    assert cm.drop_property_ddl("FS_s", "roster", "risk_factor", "integer") == (
        "ALTER TABLE `FS_s`.`roster_properties` DROP COLUMN `risk_factor`"
    )
    assert dict((c, t) for c, _, t in cm.PROPERTY_TYPES) == {
        "string": "varchar(255)",
        "integer": "int",
        "decimal": "decimal(10,3)",
        "date": "date",
        "datetime": "datetime",
        "geopoint": "varchar(80)",
        "geotrace": "text",
        "geoshape": "text",
    }


def test_the_creation_trigger_and_the_backfill_give_a_row_its_defaults():
    name, sql = cm.creation_trigger_sql("FS_s", "roster")
    assert name == "fs_cm_roster_properties"
    assert sql == (
        "CREATE TRIGGER `FS_s`.`fs_cm_roster_properties` AFTER INSERT ON `FS_s`.`roster` "
        "FOR EACH ROW INSERT IGNORE INTO `FS_s`.`roster_properties` (rowuuid) "
        "VALUES (NEW.rowuuid)"
    )
    assert cm.backfill_sql("FS_s", "roster") == (
        "INSERT IGNORE INTO `FS_s`.`roster_properties` (rowuuid) "
        "SELECT rowuuid FROM `FS_s`.`roster`"
    )


def test_a_served_property_joins_the_properties_table_and_a_plain_list_does_not():
    sql, headers = cm.build_list_select(
        "FS_s",
        "roster",
        "worker_name",
        [("eligible", None, "table"), ("registered_name", "reg_name", "property")],
    )
    assert headers == ["name", "label", "eligible", "reg_name"]
    assert sql == (
        "SELECT t.rowuuid AS name,t.`worker_name` AS label,t.`eligible` AS `eligible`,"
        "p.`registered_name` AS `reg_name` FROM `FS_s`.`roster` AS t "
        "LEFT JOIN `FS_s`.`roster_properties` AS p ON p.rowuuid = t.rowuuid "
        "WHERE t._active = 1 ORDER BY t.rowuuid"
    )
    # without a property the SELECT is what it always was: no alias, no join
    plain, plain_headers = cm.build_list_select(
        "FS_s", "roster", "worker_name", [("eligible", None)]
    )
    assert plain == (
        "SELECT rowuuid AS name,`worker_name` AS label,`eligible` AS `eligible` "
        "FROM `FS_s`.`roster` WHERE _active = 1 ORDER BY rowuuid"
    )
    assert plain_headers == ["name", "label", "eligible"]


def test_a_source_form_names_the_lists_it_feeds_for_the_delete_guard(db_request):
    """Before a consumer exists the consumer guard is silent, yet the source's
    foreign key would still refuse the delete: the lists are named instead."""
    fed = cm.lists_fed_by_form(db_request, "p", "tool1")
    assert [a_list["list_id"] for a_list in fed] == ["centre_lists", "roster"]
    assert fed[0]["list_filename"] == "centre_lists.csv"
    assert cm.lists_fed_by_form(db_request, "p", "tool2") == []


def test_only_the_tables_a_list_draws_from_can_carry_properties(db_request):
    """The fixture publishes two lists from tool1 (maintable and roster) and
    none from tool2: tool2 is not offered, and each table appears once."""
    assert cm.get_list_source_tables(db_request, "p") == {
        "tool1": ["maintable", "roster"]
    }
