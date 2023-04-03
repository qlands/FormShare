def t_e_s_t_group_assistant(test_object):
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "agrpssistant001",
            "coll_name": "agrpssistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an assistant group again
    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"group_desc": "Test if an assistant group", "group_id": "assgrp003"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a member to a group succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, "assgrp003"
        ),
        {
            "assistants": "{}|{}".format(test_object.projectID, "agrpssistant001"),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a group to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"group_id": "assgrp003", "group_can_submit": 1},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="agrpssistant001"
        ),
    )

    # Assistant logout succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": "agrpssistant001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Assistant login succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": "agrpssistant001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the assistant forms
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/forms".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {
            "coll_id": "{}|{}".format(test_object.projectID, "agrpssistant001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="agrpssistant001"
        ),
    )

    # Get the assistant forms
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/forms".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
