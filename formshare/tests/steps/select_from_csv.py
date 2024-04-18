import os
import time


def t_e_s_t_select_from_csv(test_object):
    # Upload a form requiring support CSV files
    paths = ["resources", "forms", "select_from_csv", "ODK_super_simple_csv.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "id"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
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

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=200,
    )
    test_object.root.assertIn(b"Repository check pending", res.body)

    # Uploads provincias
    paths = ["resources", "forms", "select_from_csv", "provincias.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads prjs
    paths = ["resources", "forms", "select_from_csv", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"Repository check pending", res.body)
    test_object.root.assertNotIn(b"This form cannot create a repository", res.body)

    # Uploads bad provincias
    paths = ["resources", "forms", "select_from_csv", "bad", "provincias.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)
    test_object.root.assertIn(b"following options are duplicated in the ODK", res.body)

    # Uploads good provincias
    paths = ["resources", "forms", "select_from_csv", "provincias.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"This form cannot create a repository", res.body)

    # Uploads bad prjs
    paths = ["resources", "forms", "select_from_csv", "bad", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)
    test_object.root.assertIn(b"have multi-select variables with spaces", res.body)

    # Uploads good prjs
    paths = ["resources", "forms", "select_from_csv", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"This form cannot create a repository", res.body)

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"form_pkey": "id", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for celery to generate the repository

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        status=200,
    )
    test_object.root.assertIn(b"With repository", res.body)

    # Uploads good prjs
    paths = ["resources", "forms", "select_from_csv", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads good provinces
    paths = ["resources", "forms", "select_from_csv", "provincias.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads bad prjs
    paths = ["resources", "forms", "select_from_csv", "bad", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads bad provinces
    paths = ["resources", "forms", "select_from_csv", "bad", "provincias.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads other
    paths = ["resources", "forms", "select_from_csv", "other.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Upload two good
    paths = ["resources", "forms", "select_from_csv", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "select_from_csv", "provincias.csv"]
    resource_file_2 = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[
            ("filetoupload", resource_file),
            ("filetoupload", resource_file_2),
        ],
    )
    assert "FS_error" not in res.headers

    # Upload two bad
    paths = ["resources", "forms", "select_from_csv", "bad", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "select_from_csv", "bad", "provincias.csv"]
    resource_file_2 = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[
            ("filetoupload", resource_file),
            ("filetoupload", resource_file_2),
        ],
    )
    assert "FS_error" in res.headers

    # Upload one good and one bad
    paths = ["resources", "forms", "select_from_csv", "bad", "prjs.csv"]
    resource_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "select_from_csv", "provincias.csv"]
    resource_file_2 = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[
            ("filetoupload", resource_file),
            ("filetoupload", resource_file_2),
        ],
    )
    assert "FS_error" in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_form_csv"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[
            ("filetoupload", resource_file_2),
            ("filetoupload", resource_file),
        ],
    )
    assert "FS_error" in res.headers
