"""How a submission's files are written (processes/odk/api.py), without a
server.

tidy runs over every XML submission before anything reads it, and what it
writes is what xmltojson reads: an answer it changes is changed in the
repository too.
"""

import shutil
import subprocess

import pytest
from lxml import etree

from formshare.processes.odk.api import TIDY_XML

LONG = (
    "The farmer said the well dried up in March and they now walk two hours "
    "to the river every day"
)


@pytest.mark.skipif(shutil.which("tidy") is None, reason="tidy is not installed")
def test_tidy_keeps_a_long_answer_as_it_was_typed(tmp_path):
    received = tmp_path / "submission.xml~"
    received.write_text(
        '<?xml version="1.0"?>\n<data id="t" version="1"><note>{}</note>'
        "<meta><instanceID>uuid:1</instanceID></meta></data>".format(LONG)
    )
    tidied = subprocess.run(TIDY_XML + [str(received)], capture_output=True)
    assert tidied.returncode == 0, tidied.stderr
    assert etree.fromstring(tidied.stdout).find("note").text == LONG
