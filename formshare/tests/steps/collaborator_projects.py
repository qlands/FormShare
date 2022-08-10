import os
import secrets
import uuid


def t_e_s_t_collaborator_projects(test_object):
    # Create collaborator 1
    collaborator_1 = str(uuid.uuid4())
    collaborator_1_key = collaborator_1
    collaborator_1 = collaborator_1[-12:]

    res = test_object.testapp.post(
        "/join",
        {
            "user_email": collaborator_1 + "@qlands.com",
            "user_password": "123",
            "user_id": collaborator_1,
            "user_password2": "123",
            "user_name": "TTTT",
            "user_super": "1",
            "user_apikey": collaborator_1_key,
            "user_apisecret": secrets.token_hex(16),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a project succeed.
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(collaborator_1),
        {
            "project_code": "collaborator_1_prj001",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/logout", status=302)

    # Create collaborator 2
    collaborator_2 = str(uuid.uuid4())
    collaborator_2_key = collaborator_2
    collaborator_2 = collaborator_2[-12:]

    res = test_object.testapp.post(
        "/join",
        {
            "user_email": collaborator_2 + "@qlands.com",
            "user_password": "123",
            "user_id": collaborator_2,
            "user_password2": "123",
            "user_name": "Testing",
            "user_super": "1",
            "user_apikey": collaborator_2_key,
            "user_apisecret": secrets.token_hex(16),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a project succeed.
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(collaborator_2),
        {
            "project_code": "collaborator_2_prj001",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/logout", status=302)

    # Create collaborator 3
    collaborator_3 = str(uuid.uuid4())
    collaborator_3_key = collaborator_3
    collaborator_3 = collaborator_3[-12:]

    res = test_object.testapp.post(
        "/join",
        {
            "user_email": collaborator_3 + "@qlands.com",
            "user_password": "123",
            "user_id": collaborator_3,
            "user_password2": "123",
            "user_name": "Testing",
            "user_super": "1",
            "user_apikey": collaborator_3_key,
            "user_apisecret": secrets.token_hex(16),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # We add a project to collaborator 3
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(collaborator_3),
        {
            "project_code": "test001",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "😁",
            "project_hexcolor": "#9bbb59",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a project that does not belong to him goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
        },
        status=404,
    )

    # Get the details of a form in a project that does not belong to him
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    #  Upload a form to a project that does not belong to it goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=404,
        upload_files=[("xlsx", resource_file)],
    )

    test_object.testapp.get("/logout", status=302)

    # Collaborator 1 login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_1, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Collaborator 1 add Collaborator 2
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            collaborator_1, "collaborator_1_prj001"
        ),
        {"add_collaborator": "", "collaborator": collaborator_2},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Sets Collaborator 2 as Admin
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            collaborator_1, "collaborator_1_prj001"
        ),
        {
            "change_role": "",
            "collaborator_id": collaborator_2,
            "role_collaborator": 2,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/logout", status=302)

    # Collaborator 3 login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_3, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Collaborator 3 tries to remove collaborator 2. Goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            collaborator_1, "collaborator_1_prj001", collaborator_2
        ),
        status=404,
    )

    # Collaborator 3 tries to add collaborator 2. Goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": "", "collaborator": collaborator_2},
        status=404,
    )

    # Collaborator 3 tries to go to dashboard of collaborator 1
    test_object.testapp.get("/user/{}".format(collaborator_1), status=404)

    test_object.testapp.get("/logout", status=302)

    # Collaborator 2 login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_2, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Collaborator 2 goes to dashboard of collaborator 1
    test_object.testapp.get("/user/{}".format(collaborator_1), status=404)

    # Collaborator remove itself as collaborator
    # Remove the collaborator
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            collaborator_1, "collaborator_1_prj001", collaborator_2
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get("/user/{}".format(collaborator_2), status=200)
    assert "FS_error" not in res.headers
