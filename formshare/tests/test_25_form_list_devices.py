"""The device a request names, and the indexes a plugin asks for to read a
repository by device or by assistant (docs/device-journeys.md 6.1, 7.3).

FormShare Collect names its installation in every request, in
X-FormShare-Device: the _device_uuid it writes into each submission's <meta>.
A form list a plugin chooses by device (IFormList) gets it from device_of, and
a plugin that reads someone's submissions on each request asks core for an
index on maintable(_device_uuid, _submitted_date) or on
maintable(_submitted_by, _submitted_date), the assistant FormShare stamps.
"""

import pytest

from formshare.processes.device_index import ASSISTANT_INDEX, DEVICE_INDEX, index_ddl
from formshare.processes.odk.api import DEVICE_HEADER, device_of


class _Request:
    def __init__(self, headers):
        self.headers = headers


def test_a_device_is_named_by_its_uuid():
    uuid = "3f0c2b9e-4d1a-4c55-9a7e-2b8f6d1e0a34"
    assert device_of(_Request({DEVICE_HEADER: uuid})) == uuid
    assert device_of(_Request({DEVICE_HEADER: "  " + uuid + "\n"})) == uuid


def test_a_value_no_device_has_names_none():
    """The column holds 64 characters, letters, digits and hyphens: anything
    else would never match a submission's _device_uuid."""
    assert device_of(_Request({})) is None
    assert device_of(_Request({DEVICE_HEADER: ""})) is None
    assert device_of(_Request({DEVICE_HEADER: "not a device!"})) is None
    assert device_of(_Request({DEVICE_HEADER: "a" * 65})) is None
    assert device_of(_Request({DEVICE_HEADER: "a" * 64})) == "a" * 64
    assert device_of(_Request({DEVICE_HEADER: "x'; DROP TABLE y; --"})) is None


def test_the_device_index_reads_a_device_by_arrival():
    assert index_ddl("FS_ab12", DEVICE_INDEX) == (
        "CREATE INDEX `fs_device` ON `FS_ab12`.`maintable` "
        "(`_device_uuid`, `_submitted_date`)"
    )
    with pytest.raises(ValueError):
        index_ddl("FS_ab12`; DROP DATABASE x; --", DEVICE_INDEX)


def test_the_assistant_index_reads_an_assistant_by_arrival():
    """A journey that follows the assistant reads what they sent from any
    device: _submitted_by is the login FormShare stamps."""
    assert index_ddl("FS_ab12", ASSISTANT_INDEX) == (
        "CREATE INDEX `fs_assistant` ON `FS_ab12`.`maintable` "
        "(`_submitted_by`, `_submitted_date`)"
    )
    with pytest.raises(ValueError):
        index_ddl("FS_ab12`; DROP DATABASE x; --", ASSISTANT_INDEX)
    with pytest.raises(KeyError):
        index_ddl("FS_ab12", "fs_other")
