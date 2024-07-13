import os


def t_e_s_t_forms(test_object):
    # Uploads a form fails. No key
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form fails. Invalid format
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "test"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form fails. PyXForm conversion fails
    paths = ["resources", "forms", "form01.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "test"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a form a fails. Invalid key
    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "test"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a form a fails. Invalid key type
    paths = ["resources", "forms", "form10.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "qid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form fails. Invalid ID
    paths = ["resources", "forms", "form02.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form fails. Invalid field name
    paths = ["resources", "forms", "form03.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form fails. Duplicated choices
    paths = ["resources", "forms", "form04.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form fails. Duplicated variables
    paths = ["resources", "forms", "form05.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form fails. Duplicated options
    paths = ["resources", "forms", "form06.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a form fails. Too many selects
    paths = ["resources", "forms", "form07.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a form fails. Bad language
    paths = ["resources", "forms", "bad_language", "bad_language.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "cedula"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a form that has too many fields.
    paths = ["resources", "forms", "too_big", "vendor_survey_20230910.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "starttime"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a form that has select with "or other" fails.
    paths = ["resources", "forms", "or_other", "consumers.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "id"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a form fails. Tables with more than 64 characters
    paths = ["resources", "forms", "bad_size", "bad_size.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hhid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload form with 64 characters fixed pass.
    paths = ["resources", "forms", "bad_size", "good_size.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hhid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    #  Upload a form to a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "not_exist"),
        {"form_pkey": "hid"},
        status=404,
        upload_files=[("xlsx", resource_file)],
    )

    # Upload a form with a get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # Upload a form a succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid", "form_target": ""},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Upload a form fails. The form already exists
    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Get the details of a form
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
    )

    # Get the details of a form of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "not_exist_project", "Justtest"
        ),
        status=404,
    )

    # Get the details of a form that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "justtest_not_exist"
        ),
        status=404,
    )

    # Edit a project. Get details with a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, test_object.project),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Test access to the dashboard with a form
    res = test_object.testapp.get(
        "/user/{}".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Access profile
    res = test_object.testapp.get(
        "/user/{}/profile".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Update a form fails. The form file is not valid
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. The form is not the same
    paths = ["resources", "forms", "form09.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. PyXForm conversion fails
    paths = ["resources", "forms", "form01.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Invalid ID
    paths = ["resources", "forms", "form02.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Invalid field name
    paths = ["resources", "forms", "form03.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Duplicated choices
    paths = ["resources", "forms", "form04.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Duplicated variables
    paths = ["resources", "forms", "form05.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Duplicated options
    paths = ["resources", "forms", "form06.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Too many selects
    paths = ["resources", "forms", "form07.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Tables with more than 64 characters
    paths = ["resources", "forms", "bad_size", "bad_size.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin,
            test_object.project,
            "Gender_Analysis_JOOUST_VLIR_OUS_Project_2021_Vers1",
        ),
        {"form_pkey": "hhid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    paths = ["resources", "forms", "form08_OK_u.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    # Update to a project that does not exists fails
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "not_exist_project", "justtest"
        ),
        {"form_pkey": "hid"},
        status=404,
        upload_files=[("xlsx", resource_file)],
    )

    # Update a form with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=404,
    )

    # Update a form without pkey fails
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form a succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # The form does not have data columns
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"See data columns", res.body)

    # Update the form with one having data columns
    paths = ["resources", "forms", "form08_OK_dc.xlsx"]
    resource_file_dc = os.path.join(test_object.path, *paths)
    # Update a form a succeeds with data columns
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file_dc)],
    )
    assert "FS_error" not in res.headers

    # The form have data columns
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
    )
    test_object.root.assertIn(b"See data columns", res.body)

    # Update a form a succeeds with a form that does not have data columns
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # The form does not have data columns
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"See data columns", res.body)

    # Update the form with one that requires a csv files and has data columns
    paths = ["resources", "forms", "form08_OK_external.xlsx"]
    resource_file_external = os.path.join(test_object.path, *paths)
    # Update a form a succeeds with data columns
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file_external)],
    )
    assert "FS_error" not in res.headers

    # The form have data columns and external files
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
    )
    test_object.root.assertIn(b"See data columns", res.body)
    test_object.root.assertIn(b"You need to attach the following", res.body)

    # Update the form with one without data columns or CSV files
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # The form does not have data columns
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"See data columns", res.body)
    test_object.root.assertNotIn(b"You need to attach the following", res.body)

    # ----

    # Edit a form for a project that does not exists goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, "project_not_exist", "Justtest"
        ),
        status=404,
    )

    # Edit a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, "justtest_dont_exist"
        ),
        status=404,
    )

    # Edit a form. Show details
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Edit a form. Without form_accsub
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_target": "100", "form_hexcolor": "#663f3c"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Edit a form. With form_accsub
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"form_target": "100", "form_hexcolor": "#663f3c", "form_accsub": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Activate a form of a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, "not_exist_project", "Justtest"
        ),
        status=404,
    )

    # Activate a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, test_object.project, "justtest_not_exist"
        ),
        status=404,
    )

    # Activate using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=404,
    )

    # Set form as active
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete the form of a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, "project_not_exist", "Justtest"
        ),
        status=404,
    )

    # Delete a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "not_exists_justtest"
        ),
        status=404,
    )

    # Delete the form with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=404,
    )

    # Delete the form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Upload the form again
    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Set form as inactive of a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, "not_exist_project", "Justtest"
        ),
        status=404,
    )

    # Set form as inactive of a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, test_object.project, "justtest_not_exist"
        ),
        status=404,
    )

    # Set form as inactive of a form using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=404,
    )

    # Set form as inactive
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Set form as active
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)

    # Upload a file to a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001_not_exist", "Justtest"
        ),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    # Upload a file to a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001", "justtest_not_exist"
        ),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    # Upload a file to a form using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001", "Justtest"
        ),
        status=404,
    )

    # Uploads a file to the form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001", "Justtest"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads the same file to the form
    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001", "Justtest"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" in res.headers

    # Overwrites the same file to the form
    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001", "Justtest"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Overwrites the same files to the form
    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "test2.dat"]
    resource_file_2 = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001", "Justtest"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[
            ("filetoupload", resource_file),
            ("filetoupload", resource_file_2),
        ],
    )
    assert "FS_error" not in res.headers

    # Removes a file from a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin, "project_not_exist", "Justtest", "test1.dat"
        ),
        status=404,
    )

    # Removes a file from a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "form_not_exist", "test1.dat"
        ),
        status=404,
    )

    # Removes a file from a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "Justtest", "not_exist.dat"
        ),
        status=404,
    )

    # Removes a file using get goes to get
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "Justtest", "test1.dat"
        ),
        status=404,
    )

    # Removes a file from a form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "Justtest", "test1.dat"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Uploads the file again
    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "test001", "Justtest"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Gets a file of a project that does not exits goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
            test_object.randonLogin, "not_exist_project", "Justtest", "test1.dat"
        ),
        status=404,
    )

    # Gets a file of a form that does not exits goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
            test_object.randonLogin, "test001", "not_exist_justtest", "test1.dat"
        ),
        status=404,
    )

    # Gets a file that does not exits goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
            test_object.randonLogin, "test001", "Justtest", "test_not_exist.dat"
        ),
        status=404,
    )

    # Gets the file
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
            test_object.randonLogin, "test001", "Justtest", "test1.dat"
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form fails. Empty assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"coll_id": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Add assistant to a project that does not exists goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "project_not_exist", "Justtest"
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
        },
        status=404,
    )

    # Add assistant to a form that does not exists goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "justtest_dont_exist"
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
        },
        status=404,
    )

    # Add assistant with a get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=404,
    )

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an assistant again fails
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit an assistant of a project the does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            "project_dont_exist",
            "Justtest",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=404,
    )

    # Edit an assistant of a form the does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            "justtest_dont_exist",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=404,
    )

    # Edit an assistant with get gees to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=404,
    )

    # Edit an assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Remove assistant of a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            "project_dont_exist",
            "Justtest",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=404,
    )

    # Remove assistant of a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "justtest_not_exist",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=404,
    )

    # Remove assistant with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=404,
    )

    # Remove the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a group to a form fails. No group_id
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=302,
    )
    assert "FS_error" in res.headers

    # Add a group to a form fails. The group_id is empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"group_id": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Add a group to a form in a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, "project_dont_exist", "Justtest"
        ),
        {"group_id": test_object.assistantGroupID, "group_can_submit": 1},
        status=404,
    )

    # Add a group to a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "justtest_not_exist"
        ),
        {"group_id": test_object.assistantGroupID, "group_can_submit": 1},
        status=404,
    )

    # Add a group to a form using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=404,
    )

    # Add a group to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"group_id": test_object.assistantGroupID, "group_can_submit": 1},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a group again fails
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {"group_id": test_object.assistantGroupID, "group_can_submit": 1},
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit a group of a project that does not exists goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/edit".format(
            test_object.randonLogin,
            "project_dont_exist",
            "Justtest",
            test_object.assistantGroupID,
        ),
        {"group_can_submit": 1, "group_can_clean": 1},
        status=404,
    )

    # Edit a group of a form that does not exists goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            "justtest_not_exist",
            test_object.assistantGroupID,
        ),
        {"group_can_submit": 1, "group_can_clean": 1},
        status=404,
    )

    # Edit the project with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/group/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.assistantGroupID,
        ),
        status=404,
    )

    # Edit a group fails. Empty privileges
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.assistantGroupID,
        ),
        {},
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit a group
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.assistantGroupID,
        ),
        {"group_can_submit": 1, "group_can_clean": 1},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete a group of a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/remove".format(
            test_object.randonLogin,
            "project_not_exist",
            "Justtest",
            test_object.assistantGroupID,
        ),
        status=404,
    )

    # Delete a group of a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "justtest_not_exist",
            test_object.assistantGroupID,
        ),
        status=404,
    )

    # Delete a group using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/group/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.assistantGroupID,
        ),
        status=404,
    )

    # Delete a group
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "Justtest",
            test_object.assistantGroupID,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form again
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
