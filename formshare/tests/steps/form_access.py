import os
import uuid


def t_e_s_t_form_access(test_object):
    # Assistant logout succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login succeed
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Adds a mimic2 project
    json2_project = "formaccess"
    json2_project_id = str(uuid.uuid4())
    mimic_res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_id": json2_project_id,
            "project_code": json2_project,
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers
    # Add the mimic form
    mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
    resource_file = os.path.join(test_object.path, *mimic_paths)
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, json2_project),
        {"form_pkey": "I_D"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in mimic_res.headers
    json2_form = "LB_Sequia_MAG_20190123"

    # Uploads a file to the form
    paths = ["resources", "forms", "complex_form", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads a file to the form
    paths = ["resources", "forms", "complex_form", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    access_assistant = str(uuid.uuid4())
    access_assistant = access_assistant[-12:]

    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, json2_project
        ),
        {
            "coll_id": access_assistant,
            "coll_name": access_assistant,
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Add an assistant to a form succeeds
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {
            "coll_id": "{}|{}".format(json2_project_id, access_assistant),
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Test getting the forms when the assistant does not have access
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, json2_project),
        status=200,
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=access_assistant),
    )

    # Upload submission fails assistant cannot submit
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_logs2",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=404,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=access_assistant),
    )

    # Set form as inactive
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Upload submission fails the form is inactive
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_logs2",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=404,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=access_assistant),
    )

    # Set form as active
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Upload submission fails the form does not exists
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_logs2",
        "submission001_invalid.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=404,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=access_assistant),
    )

    # Upload submission fails the upload does not have an xml file
    paths = ["resources", "api_test.dat"]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=500,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=access_assistant),
    )
