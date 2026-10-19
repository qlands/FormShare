"""The store of FormShare's files, without a server.

PTOFS was taken from ofs 0.4.3 into processes/storage/ptofs.py: ofs imports
pkg_resources, which setuptools 81 removed, and FormShare could not be
imported with a current setuptools. Every file stored before must read the
same, so the folders pairtree gives each bucket and the bytes of a bucket's
persisted_state.json are pinned here as ofs wrote them. Checked against ofs
itself when the class was taken (2026-10-18).
"""

import datetime as real_datetime
import io
import json
import os
import subprocess
import sys

import pytest
from pairtree import FileNotFoundException

from formshare.processes.storage import ptofs
from formshare.processes.storage import local_storage

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))


class _FrozenClock(real_datetime.datetime):
    moment = real_datetime.datetime(2026, 10, 18, 15, 30, 45, 123456)

    @classmethod
    def now(cls, tz=None):
        return cls.moment


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setattr(ptofs, "datetime", _FrozenClock)
    _FrozenClock.moment = real_datetime.datetime(2026, 10, 18, 15, 30, 45, 123456)
    return _FrozenClock


def _folder(root, *pairs):
    return os.path.join(root, "storage", "pairtree_root", *pairs)


def test_a_bucket_holds_files_and_their_record(tmp_path, clock):
    store = ptofs.PTOFS(storage_dir=str(tmp_path / "storage"))
    bucket = "db7eb5813e8a1b322dbf2166521c0468"
    assert store.claim_bucket(bucket) == bucket
    with pytest.raises(ptofs.BucketExists):
        store.claim_bucket(bucket)

    record = store.put_stream(bucket, "a.csv", io.BytesIO(b"x,y\n1,2\n"))
    assert record == {
        "_label": "a.csv",
        "_content_length": 8,
        "_creation_date": "2026-10-18T15:30:45",
        "_last_modified": "2026-10-18T15:30:45",
        "_checksum": "md5:344fd2323dd33d5c058b7cf27de029e8",
    }
    assert store.get_stream(bucket, "a.csv").read() == b"x,y\n1,2\n"

    # Replaced: created when it was, modified now
    clock.moment += real_datetime.timedelta(seconds=7)
    record = store.put_stream(bucket, "a.csv", io.BytesIO(b"x,y\n3,4\n"))
    assert record["_creation_date"] == "2026-10-18T15:30:45"
    assert record["_last_modified"] == "2026-10-18T15:30:52"
    assert store.get_stream(bucket, "a.csv").read() == b"x,y\n3,4\n"

    store.put_stream(
        bucket, "b.txt", io.BytesIO(b"b"), params={"note": "kept", "_x": "no"}
    )
    assert store.get_metadata(bucket, "b.txt")["note"] == "kept"
    assert "_x" not in store.get_metadata(bucket, "b.txt")
    assert sorted(store.list_labels(bucket)) == ["a.csv", "b.txt"]

    store.del_stream(bucket, "b.txt")
    assert not store.exists(bucket, "b.txt")
    assert list(store.list_labels(bucket)) == ["a.csv"]
    with pytest.raises(FileNotFoundException):
        store.get_stream(bucket, "b.txt")
    with pytest.raises(FileNotFoundException):
        store.del_stream(bucket, "b.txt")
    with pytest.raises(FileNotFoundException):
        store.get_stream("nobody_claimed_this", "a.csv")


def test_the_files_are_where_ofs_put_them(tmp_path, clock):
    """pairtree's folders, two characters a level, the id's own characters,
    and the record's JSON as ofs wrote it, byte for byte."""
    store = ptofs.PTOFS(storage_dir=str(tmp_path / "storage"))
    for bucket in (
        "db7eb5813e8a1b322dbf2166521c0468",
        "437e9bc6-8f9c-44ef-a57b-f01f1f91f0a4",
    ):
        store.claim_bucket(bucket)
        store.put_stream(bucket, "a.csv", io.BytesIO(b"x,y\n1,2\n"))
        store.put_stream(bucket, "ñandú.csv", io.BytesIO("ñandú\n".encode("utf-8")))
    hexadecimal = _folder(
        str(tmp_path), *"db 7e b5 81 3e 8a 1b 32 2d bf 21 66 52 1c 04 68".split()
    )
    hyphenated = _folder(
        str(tmp_path),
        *"43 7e 9b c6 -8 f9 c- 44 ef -a 57 b- f0 1f 1f 91 f0 a4".split(),
    )
    for folder in (hexadecimal, hyphenated):
        assert sorted(os.listdir(folder)) == [
            "a.csv",
            "persisted_state.json",
            "ñandú.csv",
        ]
    assert sorted(os.listdir(str(tmp_path / "storage"))) == [
        "pairtree_prefix",
        "pairtree_root",
        "pairtree_version0_1",
    ]
    with open(os.path.join(hexadecimal, "persisted_state.json"), "rb") as a_file:
        assert a_file.read() == (
            b'{"a.csv": {"_label": "a.csv", "_content_length": 8, '
            b'"_creation_date": "2026-10-18T15:30:45", '
            b'"_last_modified": "2026-10-18T15:30:45", '
            b'"_checksum": "md5:344fd2323dd33d5c058b7cf27de029e8"}, '
            b'"\\u00f1and\\u00fa.csv": {"_label": "\\u00f1and\\u00fa.csv", '
            b'"_content_length": 8, "_creation_date": "2026-10-18T15:30:45", '
            b'"_last_modified": "2026-10-18T15:30:45", '
            b'"_checksum": "md5:' + _md5("ñandú\n".encode("utf-8")) + b'"}}'
        )


def _md5(data):
    import hashlib

    return hashlib.md5(data).hexdigest().encode()


def test_a_record_that_cannot_be_read_is_empty(tmp_path):
    folder = tmp_path / "bucket"
    folder.mkdir()
    (folder / "persisted_state.json").write_text("")
    assert ptofs.PersistentState(str(folder)).state == {}
    # A folder that is not there keeps nothing, and says so
    missing = ptofs.PersistentState(str(tmp_path / "nowhere"))
    assert missing.filepath is None and missing.state == {}
    missing.sync()


class _Registry:
    def __init__(self, settings):
        self.settings = settings


class _Request:
    def __init__(self, repository):
        self.registry = _Registry({"repository.path": repository})


def test_formshare_stores_reads_and_deletes_files(tmp_path):
    request = _Request(str(tmp_path / "repository"))
    local_storage.store_file(request, "project1", "list.csv", io.BytesIO(b"a\n"))
    # Storing into a bucket claimed before
    local_storage.store_file(request, "project1", "logo.png", io.BytesIO(b"\x89PNG"))
    stream = local_storage.get_stream(request, "project1", "list.csv")
    assert stream.read() == b"a\n"
    stream.close()
    assert local_storage.get_stream(request, "project1", "missing.csv") is None
    assert local_storage.delete_stream(request, "project1", "list.csv")
    assert not local_storage.delete_stream(request, "project1", "list.csv")
    local_storage.delete_bucket(request, "project1")
    assert local_storage.get_stream(request, "project1", "logo.png") is None
    # A bucket that is not there is deleted quietly
    local_storage.delete_bucket(request, "nobody")


def test_formshare_imports_without_pkg_resources_or_ofs():
    """What an image built today has: no pkg_resources, which setuptools 81
    removed, and no ofs. formshare_enterprise:20261018 could not import
    FormShare at all (alembic, uvicorn, Celery)."""
    code = (
        "import sys\n"
        "class Missing:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in ('pkg_resources', 'ofs'):\n"
        "            raise ModuleNotFoundError('No module named %r' % name)\n"
        "sys.meta_path.insert(0, Missing())\n"
        "import formshare\n"
        "import formshare.processes.storage\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr[-2000:]


def test_what_plugins_may_call_on_the_store(tmp_path, clock):
    """IFileStorage's hooks hand plugins the PTOFS itself, so the methods
    FormShare does not call are kept, and work as ofs's did."""
    store = ptofs.PTOFS(storage_dir=str(tmp_path / "storage"))
    bucket = store.claim_bucket()
    assert len(bucket) == 32 and store.exists(bucket)
    assert bucket in list(store.list_buckets())
    record = store.put_stream(
        bucket, "a.csv", io.BytesIO(b"a"), params={"_label": "Shown", "note": "n"}
    )
    assert record["_label"] == "Shown" and record["note"] == "n"
    assert store.update_metadata(bucket, "a.csv", {"other": "o", "_size": 9}) == dict(
        record, other="o"
    )
    assert "other" not in store.del_metadata_keys(bucket, "a.csv", ["other", "_label"])
    for refused in (
        lambda: store.get_metadata(bucket, "missing.csv"),
        lambda: store.update_metadata(bucket, "missing.csv", {}),
        lambda: store.del_metadata_keys(bucket, "missing.csv", []),
    ):
        with pytest.raises(FileNotFoundException):
            refused()
    assert store.list_labels("nobody") is None
    # Without hashing, files carry no checksum
    plain = ptofs.PTOFS(storage_dir=str(tmp_path / "plain"), hashing_type=None)
    plain.claim_bucket("b1")
    assert "_checksum" not in plain.put_stream("b1", "f.txt", io.BytesIO(b"f"))


def test_a_record_behaves_as_a_dictionary(tmp_path):
    folder = tmp_path / "bucket"
    folder.mkdir()
    state = ptofs.PersistentState(str(folder))
    state.update({"a": 1, "b": 2})
    state["c"] = 3
    del state["b"]
    assert len(state) == 2 and state.has_key("a") and not state.has_key("b")
    assert dict(state.items()) == {"a": 1, "c": 3}
    assert sorted(state.values()) == [1, 3]
    assert repr(state) == "{'a': 1, 'c': 3}"
    state.sync()
    assert json.loads((folder / "persisted_state.json").read_text()) == {"a": 1, "c": 3}
    state.clear()
    assert len(state) == 0
    with pytest.raises(KeyError):
        state["a"]
    # Not created on request, a record that is not there reads empty
    other = tmp_path / "other"
    other.mkdir()
    assert ptofs.PersistentState(str(other), create=False).state == {}
