"""The CSV handshake with RSTools' caselistgen.

caselistgen writes CSV lists since 2026-10-19 (stage 7, write_list_csv_file),
in place of write_list_csv. It must write the same bytes, or the swap churns
every list's hash for nothing. RSTools' suite makes
tests/data/caselist/expected.csv from fixture.sql and query.sql through a copy
of write_list_csv and asserts caselistgen matches it
(docs/formshare_case_management/rstools.md, 6.4).

This step is the other half. The three files are vendored and the fixture is
loaded into a scratch schema. The query runs through FormShare's old path --
SQLAlchemy rows into write_list_csv -- and through the new one, the installed
caselistgen, and both files are compared with expected.csv byte for byte. A
difference is a true fact about what the driver or the tool returns, and it
belongs to whoever changed it.
"""

import io
import os
import uuid

from sqlalchemy import create_engine

from formshare.processes.db.case_management import run_caselistgen, write_list_csv


def t_e_s_t_caselist_handshake(test_object):
    resources = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "resources", "caselist"
    )
    with io.open(os.path.join(resources, "fixture.sql"), encoding="utf-8") as a_file:
        statements = [s.strip() for s in a_file.read().split(";\n") if s.strip()]
    with io.open(os.path.join(resources, "query.sql"), encoding="utf-8") as a_file:
        query = a_file.read().strip().rstrip(";")
    with open(os.path.join(resources, "expected.csv"), "rb") as a_file:
        expected = a_file.read()

    engine = create_engine(test_object.server_config["sqlalchemy.url"])
    schema = "FS_handshake_" + uuid.uuid4().hex[:8]
    try:
        engine.execute(
            "CREATE DATABASE `{}` CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci".format(schema)
        )
        connection = engine.connect()
        try:
            connection.execute("USE `{}`".format(schema))
            for a_statement in statements:
                connection.execute(a_statement)
            result = connection.execute(query)
            headers = list(result.keys())
            rows = result.fetchall()
        finally:
            connection.close()
        out = os.path.join(test_object.working_dir, "caselist_handshake.csv")
        write_list_csv(headers, rows, out)
        with open(out, "rb") as a_file:
            produced = a_file.read()
        assert (
            produced == expected
        ), "write_list_csv and caselistgen disagree:\n{!r}\n!=\n{!r}".format(
            produced, expected
        )
        # What a list is written with now
        out = os.path.join(test_object.working_dir, "caselist_handshake_tool.csv")
        written, message, _ = run_caselistgen(
            test_object.server_config, query, out, "csv", schema=schema
        )
        assert written, message
        with open(out, "rb") as a_file:
            produced = a_file.read()
        assert (
            produced == expected
        ), "the installed caselistgen does not write expected.csv:\n{!r}\n!=\n{!r}".format(
            produced, expected
        )
    finally:
        engine.execute("DROP DATABASE IF EXISTS `{}`".format(schema))
        engine.dispose()
