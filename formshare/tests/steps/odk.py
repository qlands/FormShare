import time
import os
import glob
from .sql import get_form_details


def t_e_s_t_odk(test_object):
    # Upload a complex form succeeds with bad structure
    paths = ["resources", "forms", "complex_form", "B_bad_structure.xlsx"]
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

    test_object.formID = "LB_Sequia_MAG_20190123"

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
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
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Repository check pending" in res.body)

    # Uploads a bad file to the form
    paths = ["resources", "forms", "complex_form", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, test_object.formID
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
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Upload a complex form succeeds
    paths = ["resources", "forms", "complex_form", "B.xlsx"]
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

    test_object.formID = "LB_Sequia_MAG_20190123"

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
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
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Repository check pending" in res.body)

    # Uploads a bad file to the form
    paths = ["resources", "forms", "complex_form", "bad_csv", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, test_object.formID
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
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Remove a support file
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "cantones.csv",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Uploads a file to the form
    paths = ["resources", "forms", "complex_form", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Repository check pending" in res.body)

    # Remove a support file
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "distritos.csv",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Repository check pending" in res.body)

    # Uploads a file to the form
    paths = ["resources", "forms", "complex_form", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Repository check pending" in res.body)

    # Test getting the forms goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, "not_exist"),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Deactivate the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Test getting the forms goes to 401 the assistant is not active
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(
            test_object.randonLogin, test_object.project
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Edit the form as crowdsourcing
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, test_object.project),
        {
            "project_code": test_object.project,
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Test getting the forms goes to 200 the assistant is not active but crowdsourcing
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Edit the form as not crowdsourcing
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, test_object.project),
        {
            "project_code": test_object.project,
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Activate the assistant
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

    # Test getting the forms. Ask for credential
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(
            test_object.randonLogin, test_object.project
        ),
        status=401,
    )

    # Test getting the forms.
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Test Download the form for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/{}/xmlform".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Deactivate the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Test Download the form for a deactivated assistant goes to 401
    test_object.testapp.get(
        "/user/{}/project/{}/{}/xmlform".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Activate the assistant
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

    # Remove the assistant from the form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Test Download the form for assistant that does not have the form goes to 401
    test_object.testapp.get(
        "/user/{}/project/{}/{}/xmlform".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
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

    # Test Download the form.
    test_object.testapp.get(
        "/user/{}/project/{}/{}/xmlform".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Get the manifest of a ODK without supporting files. Empty manifest
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Get the manifest of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "not exist", test_object.formID
        ),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Deactivate the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the manifest of an inactive assistant goes to 401
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Activate the assistant
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

    # Remove the assistant from the form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the manifest with an assistant that does not have the form goes to 401
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
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

    # Get the manifest pass
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Get the a media file for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Deactivate the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the a media file for a deactivated assisstant goes to 401
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Activate the assistant
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

    # Remove the assistant from the form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the a media file for an assistant that does not have the form goes to 401
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
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

    # Get the a media file
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Get head submission of a project that does not exist goes to 404
    test_object.testapp.head(
        "/user/{}/project/{}/submission".format(test_object.randonLogin, "not_exist"),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Deactivate the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get head submission with an deactivated assistant goes to 401
    test_object.testapp.head(
        "/user/{}/project/{}/submission".format(
            test_object.randonLogin, test_object.project
        ),
        status=401,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Activate the assistant
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

    # Get head submission
    test_object.testapp.head(
        "/user/{}/project/{}/submission".format(
            test_object.randonLogin, test_object.project
        ),
        status=204,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Test submission
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_norepo",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    # Push to /submission
    # Push to a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/submission".format(test_object.randonLogin, "not exist"),
        status=404,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Push using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/submission".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Deactivate the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Push with inactive assistant goes to 401
    test_object.testapp.post(
        "/user/{}/project/{}/submission".format(
            test_object.randonLogin, test_object.project
        ),
        status=401,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Activate the assistant
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

    test_object.testapp.post(
        "/user/{}/project/{}/submission".format(
            test_object.randonLogin, test_object.project
        ),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Push to /push
    # Push to a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "not exist"),
        status=404,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Push using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=404,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Deactivate the assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {
            "coll_prjshare": "",
            "coll_id": test_object.assistantLogin,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Push with inactive assistant goes to 401
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=401,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    # Activate the assistant
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

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Test submission one again. Adding image2 to same place of image 1
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_norepo",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image2", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Test submission without precision in GPS
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_norepo",
        "submission002.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Test submission without elevation in GPS
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_norepo",
        "submission003.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    # Test duplicated submission that will be stored and then processed by the repository
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_norepo",
        "submission004.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    # Gets the GPS Points of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}/download/gpspoints".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Gets the GPS Points of a Form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Test access to the dashboard
    res = test_object.testapp.get(
        "/user/{}".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Gets the details of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, test_object.project),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Download the ODK form file for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/odk".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Download the ODK form file for a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/odk".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Download the ODK form file
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/odk".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Download data in CSV format of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/csv".format(
            test_object.randonLogin, "project_not_exist", test_object.formID
        ),
        status=404,
    )

    # Download data in CSV format of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/csv".format(
            test_object.randonLogin, test_object.project, "form_not_exist"
        ),
        status=404,
    )

    # Download data in CSV format
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Download submitted media files for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/media".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Download submitted media files for a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/media".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Download submitted media files
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/media".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Download submitted media files. No media
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/media".format(
            test_object.randonLogin, test_object.project, "Justtest"
        ),
        status=302,
    )
    assert "FS_error" in res.headers

    form_details = get_form_details(
        test_object.server_config, test_object.projectID, test_object.formID
    )
    form_directory = form_details["form_directory"]
    paths2 = [test_object.server_config["repository.path"], "odk"]
    odk_dir = os.path.join(test_object.path, *paths2)

    submissions_path = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", "*.json"]
    )
    files = glob.glob(submissions_path)
    a_submission = None
    if files:
        for file in files:
            a_submission = file
            break
    submission_id = os.path.basename(a_submission)
    submission_id = submission_id.replace(".json", "")

    # Get the GeoInformation of the submission_id of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin, "not_exist", test_object.formID, submission_id
        ),
        status=404,
    )

    # Get the GeoInformation of the submission_id of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin, test_object.project, "not_exist", submission_id
        ),
        status=404,
    )

    # Get the GeoInformation of the submission_id
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            submission_id,
        ),
        status=200,
    )

    image_path = os.path.join(
        odk_dir, *["forms", form_directory, "submissions", submission_id, "*.*"]
    )
    files = glob.glob(image_path)
    media_file = None
    if files:
        for file in files:
            media_file = file
            break
    media_file = os.path.basename(media_file)

    image_file = None
    if files:
        for file in files:
            if file.find(".png") >= 0:
                image_file = file
                break
    image_file = os.path.basename(image_file)

    # Get media files of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/media/{}/get".format(
            test_object.randonLogin,
            "not_exist",
            test_object.formID,
            submission_id,
            media_file,
        ),
        status=404,
    )

    # Get media files of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/media/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            "not_exist",
            submission_id,
            media_file,
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/media/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            submission_id,
            media_file,
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/media/{}/get?thumbnail=true".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            submission_id,
            image_file,
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/media/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            submission_id,
            "not_found",
        ),
        status=404,
    )
