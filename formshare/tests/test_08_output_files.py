"""How FormShare reports a file jxformtomysql could not write (exit 38).

Since rstools.md 17.2 jxformtomysql ends with 38 when one of the files it was
told to write -- the SQL, the translation file, manifest.xml, create.xml,
insert.xml -- cannot be opened or is not written whole. Before, the run ended
with 0 and the file was missing, which surfaced later as a file-not-found in
whatever read it. It is the server's fault and never the form's: the owner is
told which file and why, the technical team where.

The XML in here is the tool's own output, captured from the jxformtomysql of
rstools.md 17 with a directory where the manifest goes. The last test runs
the installed tool, when it knows the code.
"""

import json
import os
import types

import pytest

from formshare.processes.odk.api import (
    check_jxform_file,
    describe_output_file_errors,
    output_file_error_heading,
    output_file_error_report,
    output_file_errors,
)
from formshare.tests.steps.unwritable_output import (
    make_unwritable,
    small_form,
    tool_reports_unwritable_files,
)
from formshare.views.repository import REPOSITORY_CODES_HANDLED

# A check (-K) with a directory at -f. XMLLanguageNotFound comes first, as
# in every refusal.
MANIFEST_IS_A_DIRECTORY = """<!DOCTYPE XMLResult>
<XMLResult>
 <XMLLanguageNotFound>
  <languages/>
 </XMLLanguageNotFound>
 <XMLOutputFileError>
  <file name="manifest.xml" path="/srv/odk/tmp/0f1e/manifest.xml" reason="Is a directory"/>
 </XMLOutputFileError>
</XMLResult>
"""

# A write the system took part of and refused the rest: a full disk or a
# size limit, which reaches Qt with no reason of its own.
CUT_SHORT = """<XMLResult>
 <XMLLanguageNotFound>
  <languages/>
 </XMLLanguageNotFound>
 <XMLOutputFileError>
  <file name="create.sql" path="/srv/odk/forms/a1/repository/create.sql" reason="only part of it could be written"/>
 </XMLOutputFileError>
</XMLResult>
"""


def translate(message):
    """Stand in for request.translate, which returns the msgid untranslated."""
    return message


def test_the_file_is_read_with_its_name_path_and_reason():
    assert output_file_errors(MANIFEST_IS_A_DIRECTORY) == [
        {
            "name": "manifest.xml",
            "path": "/srv/odk/tmp/0f1e/manifest.xml",
            "reason": "Is a directory",
        }
    ]


def test_bytes_are_read_as_the_tool_writes_them():
    assert output_file_errors(MANIFEST_IS_A_DIRECTORY.encode("utf-8")) == (
        output_file_errors(MANIFEST_IS_A_DIRECTORY)
    )


def test_a_note_before_the_xml_does_not_hide_the_file():
    # The split note once printed on stdout before the XML (rstools.md 14)
    noted = (
        "Note: table maintable was split into 2 tables because it does not "
        "fit in a MySQL row.\n" + MANIFEST_IS_A_DIRECTORY
    )
    assert output_file_errors(noted)[0]["name"] == "manifest.xml"


def test_output_without_the_report_names_no_file():
    assert output_file_errors("") == []
    assert output_file_errors(b"") == []
    assert (
        output_file_errors(
            "The output file /srv/odk/manifest.xml could not be written: Is a directory"
        )
        == []
    )
    assert output_file_errors("<XMLResult><XMLLanguageNotFound/></XMLResult>") == []


def test_the_owner_reads_the_file_and_the_reason_but_not_the_path():
    lines = describe_output_file_errors(
        output_file_errors(MANIFEST_IS_A_DIRECTORY), translate
    )
    assert lines == ['The file "manifest.xml" could not be written: Is a directory']
    assert "/srv/odk" not in " ".join(lines)


def test_a_write_cut_short_reads_as_a_sentence():
    lines = describe_output_file_errors(output_file_errors(CUT_SHORT), translate)
    assert lines == [
        'The file "create.sql" could not be written: only part of it could be written'
    ]


def test_the_technical_team_reads_the_path():
    assert output_file_error_report(output_file_errors(CUT_SHORT)) == (
        "/srv/odk/forms/a1/repository/create.sql could not be written: "
        "only part of it could be written"
    )
    assert output_file_error_report([]) == ""


def test_the_heading_blames_the_server_not_the_form():
    heading = output_file_error_heading(translate)
    assert "not with your form" in heading
    assert "try again" in heading


def test_the_repository_page_has_a_branch_for_38():
    assert 38 in REPOSITORY_CODES_HANDLED


def _request(odktools_path):
    """What check_jxform_file reads of a request. Without mail settings the
    report to the technical team is logged rather than sent."""
    return types.SimpleNamespace(
        translate=translate,
        registry=types.SimpleNamespace(settings={"odktools.path": odktools_path}),
    )


def _odktools_path():
    """Where the suite's configuration says RSTools is: ODKTOOLS_PATH, as CI
    sets it, or the generated test_config.json."""
    if os.environ.get("ODKTOOLS_PATH"):
        return os.environ["ODKTOOLS_PATH"]
    config = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_config.json"
    )
    if not os.path.exists(config):
        return ""
    with open(config) as config_file:
        return json.load(config_file).get("odktools.path", "")


def test_the_upload_check_refuses_with_the_file_and_the_reason(tmp_path):
    tools = _odktools_path()
    if not os.path.exists(os.path.join(tools, "JXFormToMysql", "jxformtomysql")):
        pytest.skip("jxformtomysql is not installed")
    if not tool_reports_unwritable_files(tools, str(tmp_path)):
        pytest.skip("this jxformtomysql predates exit 38 (rstools.md 17.2)")
    work = str(tmp_path)
    srv = small_form(work)
    make_unwritable(os.path.join(work, "manifest.xml"))
    code, message = check_jxform_file(
        _request(tools),
        "owner",
        "project",
        "unwritable_output",
        srv,
        os.path.join(work, "create.xml"),
        os.path.join(work, "insert.xml"),
        "hid",
    )
    assert code == 38
    assert message.startswith(output_file_error_heading(translate))
    assert 'The file "manifest.xml" could not be written: Is a directory' in message
    assert work not in message
