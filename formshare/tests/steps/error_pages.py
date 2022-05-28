def t_e_s_t_error_pages(test_object):
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/partneraccess/logout",
        {},
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

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/test".format(
            test_object.randonLogin, test_object.project
        ),
        status=500,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/partneraccess/login",
        {
            "login": "e{}@qlands.com".format(test_object.partner),
            "passwd": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/partneraccess/test", status=500)

    res = test_object.testapp.post(
        "/partneraccess/logout",
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/user/{}".format(test_object.randonLogin), status=302)

    res = test_object.testapp.post(
        "/partneraccess/login",
        {
            "login": "e{}@qlands.com".format(test_object.partner),
            "passwd": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/user/{}".format(test_object.randonLogin), status=302)

    res = test_object.testapp.post(
        "/partneraccess/logout",
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/test".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )

    res = test_object.testapp.post(
        "/partneraccess/login",
        {
            "login": "e{}@qlands.com".format(test_object.partner),
            "passwd": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/test".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )

    res = test_object.testapp.post(
        "/partneraccess/logout",
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/partneraccess/test", status=302)

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, test_object.project
        ),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/partneraccess/test", status=302)

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
