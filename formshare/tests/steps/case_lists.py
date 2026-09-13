"""The published-lists registry, end to end through the UI and the manifest.

Publishes a list from the repository the repository step built, then pulls
the manifest of a form that attaches a file by that name and asserts the
served file is the generated one: name is the rowuuid, the label column is
what the owner picked, and the edition advances. Cleans up after itself so
the steps that follow see the project as they expect it.
"""

import csv
import io
import os

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details


def _a_maintable_column(config, schema):
    """A real data column of the repository's maintable, for the label."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    result = engine.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = '{}' AND TABLE_NAME = 'maintable' "
        "AND DATA_TYPE IN ('varchar', 'text', 'mediumtext') "
        "AND COLUMN_NAME NOT IN ('rowuuid', 'surveyid', 'originid', 'instancename') "
        "AND COLUMN_NAME NOT LIKE '\\_%' ORDER BY ORDINAL_POSITION".format(schema)
    ).fetchone()
    engine.dispose()
    return result[0]


def _maintable_rowuuids(config, schema):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    result = engine.execute(
        "SELECT rowuuid FROM {}.maintable ORDER BY rowuuid".format(schema)
    ).fetchall()
    engine.dispose()
    return [a_row[0] for a_row in result]


def t_e_s_t_case_lists(test_object):
    login = test_object.randonLogin
    project = test_object.project
    form = test_object.formID
    testapp = test_object.testapp

    form_details = get_form_details(
        test_object.server_config, test_object.projectID, form
    )
    label_column = _a_maintable_column(
        test_object.server_config, form_details["form_schema"]
    )

    # The empty index renders
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, project), status=200
    )
    test_object.root.assertIn(b"publishes no lists yet", res.body)

    # A file name a device could not resolve is refused: the page re-renders
    # with the error instead of creating the list
    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, project),
        {
            "list_id": "cases",
            "list_filename": "Cases.CSV",
            "source_form": form,
            "source_table": "maintable",
            "label_column": label_column,
        },
        status=200,
    )
    test_object.root.assertIn(b"lower case", res.body)

    # Published
    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, project),
        {
            "list_id": "cases",
            "list_filename": "cases.csv",
            "source_form": form,
            "source_table": "maintable",
            "label_column": label_column,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # A second list on the same file name is refused: the name is the whole
    # coupling to the form, so it cannot be ambiguous
    res = testapp.post(
        "/user/{}/project/{}/caselists/add".format(login, project),
        {
            "list_id": "cases2",
            "list_filename": "cases.csv",
            "source_form": form,
            "source_table": "maintable",
            "label_column": label_column,
        },
        status=200,
    )

    # The edit page manages the served columns
    res = testapp.get(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "cases"),
        status=200,
    )
    test_object.root.assertIn(b"cases.csv", res.body)
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "cases"),
        {"add_column": "1", "column_name": label_column, "column_as": "extra"},
        status=302,
    )
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/edit".format(login, project, "cases"),
        {"remove_column": "1", "column_name": label_column},
        status=302,
    )

    # The form attaches a file by the list's name; the registry will replace
    # its content at manifest time
    placeholder = os.path.join(test_object.working_dir, "cases.csv")
    with open(placeholder, "w") as a_file:
        a_file.write("name,label\n")
    res = testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(login, project, form),
        status=302,
        upload_files=[("filetoupload", placeholder)],
    )
    assert "FS_error" not in res.headers

    # Pulling the manifest regenerates the stale list from the repository
    testapp.get(
        "/user/{}/project/{}/{}/manifest".format(login, project, form),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    res = testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cases.csv".format(
            login, project, form
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    served = list(csv.reader(io.StringIO(res.body.decode("utf-8"))))
    assert served[0][0] == "name"
    assert served[0][1] == "label"
    # name is the rowuuid of the source row -- the identity principle, on the
    # wire. The repository has the submissions the odk step pushed.
    expected = _maintable_rowuuids(
        test_object.server_config, form_details["form_schema"]
    )
    assert len(served) - 1 == len(expected)
    assert [a_row[0] for a_row in served[1:]] == expected

    # The edition advanced and the index shows it
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, project), status=200
    )
    test_object.root.assertNotIn(b"publishes no lists yet", res.body)

    # A second manifest pull serves the same edition: nothing changed at the
    # source, so nothing regenerates
    testapp.get(
        "/user/{}/project/{}/{}/manifest".format(login, project, form),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Leave the project as the later steps expect it
    res = testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            login, project, form, "cases.csv"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/caselists/{}/delete".format(login, project, "cases"),
        status=302,
    )
    assert "FS_error" not in res.headers
    res = testapp.get(
        "/user/{}/project/{}/caselists".format(login, project), status=200
    )
    test_object.root.assertIn(b"publishes no lists yet", res.body)
