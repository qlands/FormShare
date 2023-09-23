import os


def t_e_s_t_assistants(test_object):
    # Shows th add page
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_id": ""},
        status=200,
    )
    assert "FS_error" not in res.headers

    # Add an assistant fail. The assistant in empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_id": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add an assistant fail. The assistant in empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_id": "some", "coll_name": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add an assistant fail. The assistant is invalid
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"coll_id": "some@test", "coll_name": "some"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add an assistant fail. The passwords are not the same
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "assistant001",
            "coll_name": "assistant001",
            "coll_password": "123",
            "coll_password2": "321",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add an assistant fail. The passwords are empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "assistant001",
            "coll_name": "assistant001",
            "coll_password": "",
            "coll_password2": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add an assistant fail. The name is empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "assistant001",
            "coll_name": "",
            "coll_password": "123",
            "coll_password2": "123",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add assistant to project that does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, "Not exist"
        ),
        {
            "coll_id": "assistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=404,
    )

    # Download a CSV of a project that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/assistants/downloadcsv".format(
            test_object.randonLogin, "Not exist"
        ),
        status=404,
    )

    # Download a CSV of a project that does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "Not exist"
        ),
        status=404,
    )

    test_object.assistantLogin = "assistant001"
    test_object.assistantLogin2 = "assistant002"

    # Add an assistant succeed
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "assistant001",
            "coll_name": "assistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Upload a file with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=404,
    )

    # Upload a CSV file fails. Bad format
    paths = ["resources", "assistants_csv", "bad_file.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Bad columns
    paths = ["resources", "assistants_csv", "bad_columns.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Bad id
    paths = ["resources", "assistants_csv", "bad_id.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Empty name
    paths = ["resources", "assistants_csv", "empty_name.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Empty password
    paths = ["resources", "assistants_csv", "empty_password.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Bad email
    paths = ["resources", "assistants_csv", "bad_email.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Bad phone
    paths = ["resources", "assistants_csv", "bad_phone.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Duplicate ids
    paths = ["resources", "assistants_csv", "duplicate_ids.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test001"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file fails. Duplicate in account
    paths = ["resources", "assistants_csv", "duplicate_in_account.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test002"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a CSV file pass.
    paths = ["resources", "assistants_csv", "ok.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/uploadcsv".format(
            test_object.randonLogin, "test002"
        ),
        status=302,
        upload_files=[("csv_file", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant fail. The assistant already exists
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "assistant001",
            "coll_name": "assistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Get the assistants
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistants".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Get the assistants of not active project
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistants".format(test_object.randonLogin, "test002"),
        status=200,
    )
    assert "FS_error" not in res.headers

    # 404 for assistant in a project that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/assistants".format(test_object.randonLogin, "not_exist"),
        status=404,
    )

    # 404 for a project that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, "Not_exist", test_object.assistantLogin
        ),
        status=404,
    )

    # Get the details of an assistant in edit mode
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Edit an assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {"coll_active": "1", "coll_id": test_object.assistantLogin},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Edit an assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_active": "1",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change assistant password fails. Password is empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {"change_password": "", "coll_password": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Change assistant password fails. Passwords are not the same
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {"change_password": "", "coll_password": "123", "coll_password2": "321"},
        status=200,
    )
    assert "FS_error" in res.headers

    # 404 for password change to a project that does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, "not_exist", test_object.assistantLogin
        ),
        {"change_password": "", "coll_password": "123", "coll_password2": "123"},
        status=404,
    )

    # Change assistant succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {"change_password": "", "coll_password": "123", "coll_password2": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # 404 delete assistant project do not exits
    test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/delete".format(
            test_object.randonLogin, "Not_exist", test_object.assistantLogin
        ),
        status=404,
    )

    # 404 delete assistant using get
    test_object.testapp.get(
        "/user/{}/project/{}/assistant/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        status=404,
    )

    # Delete the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add the assistant again
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "assistant001",
            "coll_name": "assistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a second assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "coll_id": "assistant002",
            "coll_name": "assistant002",
            "coll_password": "123",
            "coll_password2": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a second assistant to other project fails as an assistant name cannot be repeated within an account
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(test_object.randonLogin, "test002"),
        {
            "coll_id": "assistant002",
            "coll_name": "assistant002",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=200,
    )
    assert "FS_error" in res.headers
