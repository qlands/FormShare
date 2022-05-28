import os
import uuid
import secrets


def t_e_s_t_api(test_object):
    collaborator_1 = str(uuid.uuid4())
    collaborator_1_key = collaborator_1
    collaborator_1 = collaborator_1[-12:]

    # Add a new collaborator
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": collaborator_1 + "@qlands.com",
            "user_password": "123",
            "user_id": collaborator_1,
            "user_password2": "123",
            "user_name": "TTT",
            "user_super": "1",
            "user_apikey": collaborator_1_key,
            "user_apisecret": secrets.token_hex(16),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # API Call fails. User cannot change this project
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": collaborator_1_key,
            "user_id": collaborator_1,
            "project_user": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest",
        },
        upload_files=[("file_to_upload", resource_file)],
        status=400,
    )

    # New collaborator logout
    test_object.testapp.get("/logout", status=302)

    # Main user login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add the collaborator to the project but just member
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": "", "collaborator": collaborator_1},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Main user logout
    test_object.testapp.get("/logout", status=302)

    # Collaborator login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_1, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # The collaborator does not have access to remove a collaborator
    test_object.testapp.post(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            test_object.randonLogin, test_object.project, "NA"
        ),
        status=404,
    )

    # The collaborator does not have access to the collaborator page
    test_object.testapp.get(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    print(test_object.projectID)
    # API Call fails. User does not have editor or admin grants to this project
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": collaborator_1_key,
            "user_id": collaborator_1,
            "project_user": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest",
        },
        upload_files=[("file_to_upload", resource_file)],
        status=400,
    )

    # Collaborator logout
    test_object.testapp.get("/logout", status=302)

    # Main user login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # API Call fails. Form not found
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": test_object.randonLoginKey,
            "user_id": test_object.randonLogin,
            "project_user": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest_not_found",
        },
        upload_files=[("file_to_upload", resource_file)],
        status=400,
    )

    # API Call fails. No file to upload
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": test_object.randonLoginKey,
            "user_id": test_object.randonLogin,
            "project_user": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest",
        },
        status=400,
    )

    # API Call fails. project_user key is missing
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": test_object.randonLoginKey,
            "user_id": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest",
        },
        status=400,
    )

    # Add a file to a form using API pass
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": test_object.randonLoginKey,
            "user_id": test_object.randonLogin,
            "project_user": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest",
        },
        upload_files=[("file_to_upload", resource_file)],
        status=200,
    )

    # Add a file again fails. No overwrite
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": test_object.randonLoginKey,
            "user_id": test_object.randonLogin,
            "project_user": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest",
        },
        upload_files=[("file_to_upload", resource_file)],
        status=400,
    )

    # Add a file again pass. Overwrite
    paths = ["resources", "api_test.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/api/1/upload_file_to_form",
        {
            "apikey": test_object.randonLoginKey,
            "user_id": test_object.randonLogin,
            "project_user": test_object.randonLogin,
            "project_code": test_object.project,
            "form_id": "Justtest",
            "overwrite": "",
        },
        upload_files=[("file_to_upload", resource_file)],
        status=200,
    )

    # 404 for a get
    test_object.testapp.get(
        "/api/1/upload_file_to_form?apikey={}".format(test_object.randonLoginKey),
        status=404,
    )
