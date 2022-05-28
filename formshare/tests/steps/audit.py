def t_e_s_t_audit(test_object):
    # Load the audit page

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/audit".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/audit".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/audit".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin, "not_exit", test_object.formID
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
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
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
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Loads the audit data for the grid
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
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

    # Change the timezone of the user to other any
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {
            "editprofile": "",
            "api_changed": "0",
            "user_name": "FormShare",
            "user_about": "FormShare testing account",
            "user_timezone": "Pacific/Fiji",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.set_cookie("_TIMEZONE_", "user")

    # Loads the audit data for the grid
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
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

    # Change the timezone of the user to FormShares
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {
            "editprofile": "",
            "api_changed": "0",
            "user_name": "FormShare",
            "user_about": "FormShare testing account",
            "user_timezone": "UTC",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Loads the audit data for the grid
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
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
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "_search": "false",
            "nd": "1578156795454",
            "rows": "10",
            "page": "1",
            "sidx": "audit_date",
            "sord": "asc",
        },
        status=200,
    )
