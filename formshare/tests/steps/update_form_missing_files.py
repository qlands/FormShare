import os


def t_e_s_t_update_form_missing_files(test_object):
    # Upload a form requiring support CSV files
    paths = ["resources", "forms", "support_zip_file", "support_zip_fileB.xlsx"]
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
            test_object.randonLogin, test_object.project, "support_zip_fileB"
        ),
        status=200,
    )

    # Update a form a succeeds even if support files are missing
    paths = ["resources", "forms", "support_zip_file", "support_zip_fileB.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, "support_zip_fileB"
        ),
        {"form_pkey": "I_D"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "support_zip_fileB"
        ),
        status=200,
    )
