"""update_record_with_id refuses in words when nothing it may write remains."""

import types

import pytest

from formshare.processes.submission import api


class Written(Exception):
    """Raised by the stand-in engine: the update got as far as writing."""


def stand_in_engine(*args, **kwargs):
    raise Written()


@pytest.fixture
def update(monkeypatch):
    columns = {
        "hh_id": False,
        "county": False,
        "_submitted_by": False,
        "track_geom": True,
    }
    monkeypatch.setattr(api, "_table_columns", lambda request, schema, table: columns)
    monkeypatch.setattr(api, "_multiselects", lambda *args: ([], {}))
    monkeypatch.setattr(api, "create_engine", stand_in_engine)
    keys = types.SimpleNamespace(fetchall=lambda: [("hh_id",)])
    request = types.SimpleNamespace(
        dbsession=types.SimpleNamespace(execute=lambda *args: keys),
        translate=lambda text: text,
        registry=types.SimpleNamespace(settings={}),
    )

    def run(data):
        return api.update_record_with_id(
            request, "ana", "p1", "f1", "FS_1", "maintable", "r1", dict(data)
        )

    return run


def test_only_a_key_is_refused(update):
    done, message = update({"rowuuid": "r1", "hh_id": None})
    assert done is False
    assert message.startswith("Nothing was updated: hh_id cannot be changed")


def test_only_columns_formshare_keeps_or_mysql_derives_are_refused(update):
    done, message = update({"_submitted_by": "x", "track_geom": "x"})
    assert done is False
    assert "_submitted_by, track_geom cannot be changed" in message


def test_a_request_naming_no_field_is_refused(update):
    done, message = update({"rowuuid": "r1", "apikey": "k"})
    assert (done, message) == (
        False,
        "Nothing was updated: the request names no field to change",
    )


def test_an_editable_field_beside_a_key_is_still_written(update):
    with pytest.raises(Written):
        update({"hh_id": "007", "county": "2"})
