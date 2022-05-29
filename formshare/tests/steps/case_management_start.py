import os
import uuid


def t_e_s_t_case_management_start(test_object):
    # Add a project succeed.
    case_project_id = str(uuid.uuid4())
    test_object.case_project_id = case_project_id
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_id": case_project_id,
            "project_code": "case001",
            "project_name": "Case project 001",
            "project_abstract": "",
            "project_case": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # At this point there are no case creators
    test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        status=404,
    )

    # At this point there are no case creators
    test_object.testapp.get(
        "/user/{}/project/{}/caselookupcsv".format(test_object.randonLogin, "case001"),
        status=404,
    )

    # Get the project list
    res = test_object.testapp.get(
        "/user/{}/projects".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers
    test_object.root.assertIn(b"longitudinal workflow", res.body)

    # Gets the details of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, "case001"), status=200
    )
    assert "FS_error" not in res.headers
    test_object.root.assertIn(b"form_caselabel", res.body)

    # Edit a project. Get details
    res = test_object.testapp.get(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "case001"),
        status=200,
    )
    assert "FS_error" not in res.headers
    test_object.root.assertNotIn(b"Read-only because the project has forms", res.body)

    res = test_object.testapp.post(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "case001"),
        {
            "project_name": "Case project 001",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "case001"),
        {
            "project_name": "Case project 001",
            "project_abstract": "",
            "project_case": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(test_object.randonLogin, "case001"),
        {
            "coll_id": "caseassistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 3,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.caseassistantLoginKey = str(uuid.uuid4())

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, "case001"
        ),
        {"login": "caseassistant001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/changemykey".format(
            test_object.randonLogin, "case001"
        ),
        {"coll_apikey": test_object.caseassistantLoginKey},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Upload a case creator fails. Invalid case key
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "test", "form_caselabel": "test"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case creator fails. Invalid case label
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "hid", "form_caselabel": "test"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case creator fails. Case label is empty
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "hid", "form_caselabel": ""},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case creator fails. Case label and key are the same
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "hid", "form_caselabel": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case creator pass fails. Invalid type
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "coll_date", "form_caselabel": "fname"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case creator pass.
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "hid", "form_caselabel": "fname"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {"form_pkey": "coll_date", "form_caselabel": "fname"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=200,
    )
    test_object.root.assertIn(b"Case creator", res.body)

    # Delete the case form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
