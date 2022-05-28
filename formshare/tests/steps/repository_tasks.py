import time
from .sql import get_form_details
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from .repository_downloads import t_e_s_t_repository_downloads


def t_e_s_t_repository_tasks(test_object):
    time.sleep(5)  # Wait 5 seconds to other tests to finish

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Get the tables in a repository
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Change the description of a table to nothing
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "table_name": "maintable",
            "table_desc": "",
        },
        status=200,
    )

    # Change the description of a table
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "table_name": "maintable",
            "table_desc": "New description of maintable",
        },
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin, "not_exist", test_object.formID, "maintable"
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin, test_object.project, "not_exist", "maintable"
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "not_exist",
        ),
        status=404,
    )

    # Get the fields of a table
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        status=200,
    )
    # Update the description of a field without description
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {
            "post_type": "change_desc",
            "field_name": "i_d",
            "field_desc": "",
        },
        status=200,
    )
    # Update the description of a field
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {
            "post_type": "change_desc",
            "field_name": "i_d",
            "field_desc": "ID of the farmer",
        },
        status=200,
    )
    # Update the primary key as sensitive
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {
            "post_type": "change_as_sensitive",
            "field_name": "i_d",
            "field_protection": "recode",
        },
        status=200,
    )

    # Get the tables in a repository
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Test the download with the ID as sensitive with recode
    t_e_s_t_repository_downloads(test_object)
    time.sleep(20)

    # Update the primary key as not sensitive
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {"post_type": "change_as_not_sensitive", "field_name": "i_d"},
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Get the submissions on a form
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "",
            "sord": "asc",
        },
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "",
            "sord": "asc",
        },
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Select the submissions rows
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "",
            "sord": "asc",
        },
        status=200,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "rowuuid",
            "sord": "asc",
        },
        status=200,
    )

    # Set form as inactive
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete a submission
    form_details = get_form_details(
        test_object.server_config, test_object.projectID, test_object.formID
    )
    engine = create_engine(
        test_object.server_config["sqlalchemy.url"], poolclass=NullPool
    )
    res = engine.execute(
        "SELECT rowuuid FROM {}.maintable".format(form_details["form_schema"])
    ).first()
    row_uuid = res[0]
    engine.dispose()

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/delete".format(
            test_object.randonLogin, "not_exit", test_object.formID
        ),
        {"oper": "del", "id": row_uuid},
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/delete".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        {"oper": "del", "id": row_uuid},
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions/delete".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/delete".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"oper": "del", "id": row_uuid},
        status=200,
    )
