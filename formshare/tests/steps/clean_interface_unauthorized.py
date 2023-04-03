from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details


def t_e_s_t_clean_interface_unauthorized(test_object):
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "clean001",
            "coll_name": "clean001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "coll_id": "{}|{}".format(test_object.projectID, "clean001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": "clean001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Load the clean page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=403,
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
        status=403,
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

    # Emits a change into the database
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        {"landcultivated": "13.000", "oper": "edit", "id": row_uuid},
        status=403,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
