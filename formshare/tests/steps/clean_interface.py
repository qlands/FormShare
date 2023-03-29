from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details


def t_e_s_t_clean_interface(test_object):
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Load the clean page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Load the clean page with a table
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintable".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Load the clean page with a table that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintables".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Load the clean page with a table and fields
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintable&fields=provincia|canton".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Request a table
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "loadtable": "",
            "table": "maintable",
        },
        status=302,
    )

    # Request a table that does not exists
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "loadtable": "",
            "table": "maintables",
        },
        status=302,
    )

    # Request one field
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "loadfields": "",
            "fields": "provincia",
        },
        status=302,
    )

    # Request two fields
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "loadfields": "",
            "fields": ["provincia", "canton"],
        },
        status=302,
    )

    # Request empty fields
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "loadfields": "",
            "fields": "",
        },
        status=302,
    )

    # Request without fields
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "loadfields": "",
        },
        status=302,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
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

    # Loads the data for the grid
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "respondentname",
            "sord": "asc",
        },
        status=200,
    )

    # Loads the data for the grid
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
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

    # Loads the data for the grid using a like search pattern
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "",
            "sord": "asc",
            "searchField": "respondentname",
            "searchString": "ROGELIO",
            "searchOper": "like",
        },
        status=200,
    )

    # Loads the data for the grid using a not like search pattern
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "",
            "sord": "asc",
            "searchField": "respondentname",
            "searchString": "ROGELIO",
            "searchOper": "not like",
        },
        status=200,
    )

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

    # Emits a change into the database fails. Unknow operation
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {"landcultivated": "13.000", "oper": "edits", "id": row_uuid},
        status=404,
    )

    # Emits a change into the database fails wih get
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {"landcultivated": "13.000", "oper": "edit", "id": row_uuid},
        status=200,
    )
    assert "FS_error" in res.headers

    # Emits a change into the database
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {"landcultivated": "13.000", "oper": "edit", "id": row_uuid},
        status=200,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Change data using API fails. No API key
    test_object.testapp.post_json(
        "/api_update",
        {"landcultivated": 14},
        status=400,
    )

    # Change data using API fails. No rowuuid
    test_object.testapp.post_json(
        "/api_update",
        {"apikey": test_object.assistantLoginKey, "landcultivated": 14},
        status=400,
    )

    #  Change data using API fails. Field cannot be found
    test_object.testapp.post_json(
        "/api_update",
        {
            "apikey": test_object.assistantLoginKey,
            "rowuuid": row_uuid,
            "some_file": 14,
        },
        status=500,
    )

    #  Change data fails rowuuid does not exists
    test_object.testapp.post_json(
        "/api_update",
        {
            "apikey": test_object.assistantLoginKey,
            "rowuuid": "test",
            "landcultivated": 14,
        },
        status=404,
    )

    #  Change data fails. Invalid api key
    test_object.testapp.post_json(
        "/api_update",
        {"apikey": "some", "rowuuid": row_uuid, "landcultivated": 14},
        status=401,
    )

    # Set the assistant as nothing fails
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {},
        status=302,
    )
    assert "FS_error" in res.headers

    # Set the assistant as only submit
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # User cannot update
    test_object.testapp.post_json(
        "/api_update",
        {
            "apikey": test_object.assistantLoginKey,
            "rowuuid": row_uuid,
            "landcultivated": 14,
        },
        status=401,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    #  Change data using API passes
    test_object.testapp.post_json(
        "/api_update",
        {
            "apikey": test_object.assistantLoginKey,
            "rowuuid": row_uuid,
            "landcultivated": 14,
        },
        status=200,
    )
