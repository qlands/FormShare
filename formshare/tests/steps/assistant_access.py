import uuid


def t_e_s_t_assistant_access(test_object):
    # 404 login to project that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, "Not_exist"
        ),
        status=404,
    )

    # Test accessing the login page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )

    # Assistant login fails. Assistant not found
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": "123", "passwd": "123"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Assistant login fails. Password is not correct
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "321"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Assistant login succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login page goes to assistant dashboard
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Assistant logout succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Assistant login succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "123"},
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

    # Change the assistant password fails with get
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/changemypassword".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_password": ""},
        status=404,
    )

    # Change the assistant password fails. Empty password
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/changemypassword".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_password": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Change the assistant password fails. Password not the same
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/changemypassword".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_password": "123", "coll_password2": "321"},
        status=302,
    )
    assert "FS_error" in res.headers

    # Change the assistant password fails. Old password not correct
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/changemypassword".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_password": "123",
            "coll_password2": "123",
            "old_password": "321",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Change the assistant password succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/changemypassword".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_password": "123",
            "coll_password2": "123",
            "old_password": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Assistant login succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.assistantLoginKey = str(uuid.uuid4())

    # Change the assistant key fails with get
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/changemykey".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_apikey": test_object.assistantLoginKey},
        status=404,
    )

    # Change the assistant key.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/changemykey".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_apikey": test_object.assistantLoginKey},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change the assistant timezone with get fails
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/changemytimezone".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_timezone": "UTC"},
        status=404,
    )

    # Change the assistant key.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/changemytimezone".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_timezone": "UTC"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the assistant QR code
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/qrcode".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
