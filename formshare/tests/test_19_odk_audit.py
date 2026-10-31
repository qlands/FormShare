"""A submission's ODK audit (formshare/processes/odk_audit.py): reading
audit.csv as Collect writes it, sealing what the form encrypts, and the SQL
of the table. No database: the functional step odk_audit loads it.

The lines are Collect's own, from its AuditEventCSVLineTest (May 2026), so a
change in how Collect writes the file shows here first."""

import csv

import nacl.bindings
import pytest
from lxml import etree
from nacl.public import PrivateKey, SealedBox

from formshare.processes.db.encryption import (
    b64u_decode,
    format_public_key,
    is_envelope,
    seal,
    seal_xml,
)
from formshare.processes.odk_audit import (
    AUDIT_TABLE,
    AuditFormatError,
    _insert_sql,
    audit_file_of,
    audit_rows,
    audit_table_ddl,
    audit_table_taken,
    node_xmlcode,
    read_audit,
    seal_audit,
    surveyid_index_ddl,
)


def _new_key():
    private = PrivateKey.generate()
    return bytes(private), format_public_key(bytes(private.public_key))


def _open(envelope, private_key):
    box = b64u_decode(envelope.split(":")[3])
    padded = SealedBox(PrivateKey(private_key)).decrypt(box)
    return nacl.bindings.sodium_unpad(padded, 32).decode("utf-8")


def _audit(header, *lines):
    return ("\n".join([header] + list(lines)) + "\n").encode("utf-8")


# --- Reading what Collect writes ------------------------------------------------


def test_the_four_columns_every_audit_has():
    rows = audit_rows(
        _audit(
            "event,node,start,end",
            "form start,,1545392727685,",
            "question,/data/text1,1545392727685,1545392728527",
        )
    )
    assert rows[0]["event"] == "form start"
    assert rows[0]["node"] is None
    assert rows[0]["start"] == 1545392727685 and rows[0]["end"] is None
    assert rows[1] == {
        "event_order": 2,
        "event": "question",
        "node": "/data/text1",
        "start": 1545392727685,
        "end": 1545392728527,
        "latitude": None,
        "longitude": None,
        "accuracy": None,
        "old_value": None,
        "new_value": None,
        "user": None,
        "change_reason": None,
    }


def test_each_option_adds_its_columns_and_they_are_read_by_name():
    header = (
        "event,node,start,end,latitude,longitude,accuracy,old-value,new-value,"
        "user,change-reason"
    )
    rows = audit_rows(
        _audit(
            header,
            "question,/data/text1,1545392727685,1545392728527,54.35202520000001,"
            '18.64663840000003,10,First answer,"Second, answer",ana,typo',
        )
    )
    assert rows[0]["latitude"] == 54.35202520000001
    assert rows[0]["longitude"] == 18.64663840000003
    assert rows[0]["accuracy"] == 10.0
    assert rows[0]["old_value"] == "First answer"
    assert rows[0]["new_value"] == "Second, answer"
    assert rows[0]["user"] == "ana"
    assert rows[0]["change_reason"] == "typo"
    # Without location, the values come right after the times
    rows = audit_rows(
        _audit(
            "event,node,start,end,old-value,new-value",
            "question,/data/text1,1545392727685,1545392728527,First answer,"
            "Second answer",
        )
    )
    assert rows[0]["latitude"] is None
    assert (rows[0]["old_value"], rows[0]["new_value"]) == (
        "First answer",
        "Second answer",
    )


@pytest.mark.parametrize(
    "line, values",
    [
        (
            'question,/data/text1,1,2,"a, b","g, h","c, d","e, f"',
            ("a, b", "g, h", "c, d", "e, f"),
        ),
        (
            'question,/data/text1,1,2,"a\nb","g\nh","c\nd","e\nf"',
            ("a\nb", "g\nh", "c\nd", "e\nf"),
        ),
        (
            'question,/data/text1,1,2,"a""b","g""h","c""d","e""f"',
            ('a"b', 'g"h', 'c"d', 'e"f'),
        ),
    ],
)
def test_a_value_is_read_as_collect_quoted_it(line, values):
    # Collect quotes a value with a comma, a line break or a quote, and
    # doubles the quote (CSVUtils.getEscapedValueForCsv)
    rows = audit_rows(
        _audit("event,node,start,end,old-value,new-value,user,change-reason", line)
    )
    row = rows[0]
    assert (
        row["old_value"],
        row["new_value"],
        row["user"],
        row["change_reason"],
    ) == values


def test_a_row_written_before_the_header_changed_is_shorter():
    # Collect writes a new header over the rows it wrote before the form's
    # audit options changed (AuditEventSaveTask.updateHeaderIfNeeded).
    rows = audit_rows(
        _audit(
            "event,node,start,end,old-value,new-value",
            "question,/data/name,1,2",
            "question,/data/name,3,4,John,John Smith",
        )
    )
    assert rows[0]["old_value"] is None and rows[0]["new_value"] is None
    assert rows[1]["new_value"] == "John Smith"


def test_a_number_that_does_not_read_is_null():
    rows = audit_rows(
        _audit(
            "event,node,start,end,latitude,longitude,accuracy",
            "question,/data/a,x,2.5,null,NaN,inf",
            "question,/data/b,1,,,,",
        )
    )
    assert rows[0]["start"] is None and rows[0]["end"] is None
    assert rows[0]["latitude"] is None
    assert rows[0]["longitude"] is None and rows[0]["accuracy"] is None
    assert rows[1]["start"] == 1 and rows[1]["latitude"] is None


def test_an_unknown_column_and_an_event_less_line_are_left_out():
    rows = audit_rows(
        _audit(
            "event,node,start,end,question-label",
            "form start,,1,,",
            ",,2,,",
            "",
            "form exit,,3,,The end",
        )
    )
    # The blank line is not a line of the audit; the event-less one is, and
    # keeps its number
    assert [(row["event_order"], row["event"]) for row in rows] == [
        (1, "form start"),
        (3, "form exit"),
    ]
    assert "question-label" not in rows[1]


def test_what_is_not_an_audit_says_so():
    with pytest.raises(AuditFormatError):
        audit_rows(b"name,age\nJohn,34\n")
    assert audit_rows(b"") == []
    assert audit_rows(b"\n\n") == []
    # Text reads as the bytes do
    assert read_audit("event,node\nform start,\n") == (
        ["event", "node"],
        [["form start", ""]],
    )
    # A byte order mark and a stray byte do not lose the audit
    rows = audit_rows(
        b"\xef\xbb\xbfevent,node,start,end\nform start,,1,\nquestion,/data/x\xff,2,3\n"
    )
    assert [row["event"] for row in rows] == ["form start", "question"]


def test_a_value_past_the_readers_limit_is_not_an_audit():
    # The module raises the csv module's limit to the 16 MB the columns hold;
    # past it the reader refuses the file. A small limit stands in for it.
    limit = csv.field_size_limit(10)
    try:
        with pytest.raises(AuditFormatError):
            audit_rows(
                _audit("event,node,start,end", "question,/data/" + "x" * 20 + ",1,2")
            )
    finally:
        csv.field_size_limit(limit)


def test_an_event_is_kept_whole_up_to_its_column():
    rows = audit_rows(_audit("event,node,start,end", "x" * 300 + ",,1,"))
    assert rows[0]["event"] == "x" * 255


# --- Which question an event names -------------------------------------------------


@pytest.mark.parametrize(
    "node, xmlcode",
    [
        ("/data/name", "name"),
        ("/data/grp/name", "grp/name"),
        ("/data/grp/member[3]/mem_name", "grp/member/mem_name"),
        ("/data/member[2]/visit[1]/date", "member/visit/date"),
        # xmltojson's quirk, kept: an ancestor named as the root is not in a key
        ("/data/data/x", "x"),
        ("/data/grp/data", "grp/data"),
        (" /data/name ", "name"),
        ("/data", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_a_node_is_the_key_of_its_answer(node, xmlcode):
    assert node_xmlcode(node) == xmlcode


def test_a_node_names_what_seal_xml_seals():
    # The audit's values are sealed for the questions the XML's are: one key
    private, public = _new_key()
    xml = b"<data><grp><member><mem_name>Ann</mem_name></member></grp></data>"
    marked = {node_xmlcode("/data/grp/member[1]/mem_name")}
    sealed, count = seal_xml(xml, marked, public)
    assert count == 1
    assert _open(etree.fromstring(sealed).findtext("grp/member/mem_name"), private) == (
        "Ann"
    )


# --- Sealing what the form encrypts -----------------------------------------------


HEADER = "event,node,start,end,latitude,longitude,accuracy,old-value,new-value"


def test_the_marked_answers_are_sealed_and_the_rest_kept():
    private, public = _new_key()
    already = seal("Before", public)
    raw = _audit(
        HEADER,
        "form start,,1,,,,,,",
        'question,/data/farmer_name,2,3,37.42,-122.08,14.0,,"Smith, John"',
        'question,/data/notes,3,4,,,,"he said ""hi""",kept in clear',
        "question,/data/member[2]/mem_name,4,5,,,,Ann,Anne",
        "question,/data/farmer_name,5,6,,,,{},After".format(already),
        "question,/data/age,6,7,,,,,",
    )
    sealed, count = seal_audit(raw, {"farmer_name", "member/mem_name", "age"}, public)
    assert count == 4
    header, records = read_audit(sealed)
    assert ",".join(header) == HEADER
    farmer = records[1]
    assert farmer[7] == "" and _open(farmer[8], private) == "Smith, John"
    assert farmer[4:7] == ["37.42", "-122.08", "14.0"]
    assert records[2][7:9] == ['he said "hi"', "kept in clear"]
    assert [_open(value, private) for value in records[3][7:9]] == ["Ann", "Anne"]
    # An envelope stays as it was; the value after it is sealed
    assert records[4][7] == already and _open(records[4][8], private) == "After"
    # An answer that did not change has nothing to seal
    assert records[5][7:9] == ["", ""]
    # What is sealed reads back as rows, an envelope per sealed value
    rows = audit_rows(sealed)
    assert is_envelope(rows[1]["new_value"]) and rows[1]["old_value"] is None
    assert rows[2]["new_value"] == "kept in clear"
    assert len(rows) == 6


def test_an_audit_with_nothing_to_seal_keeps_its_bytes():
    private, public = _new_key()
    raw = _audit(HEADER, "question,/data/notes,1,2,,,,a,b")
    assert seal_audit(raw, set(), public) == (raw, 0)
    assert seal_audit(raw, {"farmer_name"}, public) == (raw, 0)
    # Without track-changes there are no answers in the file
    raw = _audit("event,node,start,end", "question,/data/farmer_name,1,2")
    assert seal_audit(raw, {"farmer_name"}, public) == (raw, 0)
    raw = _audit("event,start,end", "form start,1,")
    assert seal_audit(raw, {"farmer_name"}, public) == (raw, 0)


def test_an_audit_that_cannot_be_read_cannot_be_sealed():
    private, public = _new_key()
    with pytest.raises(AuditFormatError):
        seal_audit(b"name,age\nJohn,34\n", {"name"}, public)
    # Nothing marked: nothing to read, the bytes are kept as they came
    assert seal_audit(b"name,age\n", set(), public) == (b"name,age\n", 0)


def test_a_sealed_short_row_stays_short():
    private, public = _new_key()
    raw = _audit(
        "event,node,start,end,old-value,new-value",
        "question,/data/farmer_name,1,2",
        "question,/data/farmer_name,3,4,,Wanjiru",
    )
    sealed, count = seal_audit(raw, {"farmer_name"}, public)
    assert count == 1
    header, records = read_audit(sealed)
    assert records[0] == ["question", "/data/farmer_name", "1", "2"]
    assert _open(records[1][5], private) == "Wanjiru"


# --- The table and its SQL -----------------------------------------------------------


def test_the_table_takes_surveyids_charset_and_names_its_key():
    ddl = audit_table_ddl("FS_x", "utf8mb4", "utf8mb4_unicode_ci")
    assert ddl.startswith("CREATE TABLE `FS_x`.`odk_audit` (")
    assert (
        "`submission_id` VARCHAR(80) CHARACTER SET utf8mb4 COLLATE "
        "utf8mb4_unicode_ci NOT NULL" in ddl
    )
    assert "PRIMARY KEY (`submission_id`, `event_order`)" in ddl
    assert (
        "FOREIGN KEY (`submission_id`) REFERENCES `FS_x`.`maintable` (`surveyid`) "
        "ON DELETE CASCADE" in ddl
    )
    assert "DEFAULT CHARSET=utf8mb4" in ddl
    for column in ("`start` BIGINT", "`end` BIGINT", "`old_value` MEDIUMTEXT"):
        assert column in ddl
    assert surveyid_index_ddl("FS_x") == (
        "ALTER TABLE `FS_x`.`maintable` ADD UNIQUE INDEX `fs_surveyid` (`surveyid`)"
    )
    with pytest.raises(ValueError):
        audit_table_ddl("FS_x`; DROP SCHEMA y; --", "utf8mb4", "utf8mb4_unicode_ci")
    with pytest.raises(ValueError):
        audit_table_ddl("FS_x", "utf8mb4 COLLATE x", "utf8mb4_unicode_ci")


def test_every_value_is_bound():
    sql = _insert_sql("FS_x")
    assert sql.startswith("INSERT INTO `FS_x`.`odk_audit` (`submission_id`, ")
    for column in ("submission_id", "event_order", "start", "end", "user"):
        assert "`{}`".format(column) in sql and ":" + column in sql
    assert "'" not in sql


def test_a_repeat_called_odk_audit_takes_the_tables_name(tmp_path):
    def create_xml(*repeats):
        path = tmp_path / "create.xml"
        tables = "".join('<table name="{}"/>'.format(name) for name in repeats)
        path.write_text(
            '<XMLSchemaStructure><tables><table name="maintable">{}</table>'
            '</tables><lkptables><table name="lkpodk_audit"/></lkptables>'
            "</XMLSchemaStructure>".format(tables)
        )
        return str(path)

    assert not audit_table_taken(create_xml("members"))
    assert audit_table_taken(create_xml("members", AUDIT_TABLE))
    assert audit_table_taken(create_xml("ODK_Audit"))
    assert not audit_table_taken(str(tmp_path / "missing.xml"))


def test_an_audit_is_kept_with_the_submissions_media():
    assert (
        audit_file_of("/odk", "form1", "s1")
        == "/odk/forms/form1/submissions/s1/audit.csv"
    )


# --- What the plugins see --------------------------------------------------------------


def test_a_plugin_sees_the_audit_sealed_or_not_at_all():
    from formshare.processes.odk.api import post_with_sealed_parts

    class Part:
        def __init__(self, filename, data):
            self.filename = filename
            self.file = data

    post = {
        "xml_submission_file": Part("submission.xml", b"<data>clear</data>"),
        "audit.csv": Part("audit.csv", b"event,node\n"),
        "image": Part("photo.jpg", b"jpeg"),
    }
    seen = post_with_sealed_parts(
        post, {"xml_submission_file": b"<data>sealed</data>", "audit.csv": b"sealed"}
    )
    assert seen["audit.csv"].file.read() == b"sealed"
    assert seen["audit.csv"].filename == "audit.csv"
    assert seen["image"] is post["image"]
    seen = post_with_sealed_parts(
        post, {"xml_submission_file": b"<data>sealed</data>"}, ["audit.csv"]
    )
    assert "audit.csv" not in seen and seen["image"] is post["image"]
