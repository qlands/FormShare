import os


def t_e_s_t_external_select(test_object):
    # Upload a form requiring support CSV files
    paths = ["resources", "forms", "external", "select_one_external.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "I_D"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "cascading_select_test"
        ),
        status=200,
    )

    # Update a form a succeeds with external selects
    paths = ["resources", "forms", "external", "select_one_external_u.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "cascading_select_test"
        ),
        {"form_pkey": "I_D"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "cascading_select_test"
        ),
        status=200,
    )
