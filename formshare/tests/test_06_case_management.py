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
