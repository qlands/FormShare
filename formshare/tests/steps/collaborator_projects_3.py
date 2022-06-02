import secrets
import uuid


def t_e_s_t_collaborator_projects_3(test_object):
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
            "user_name": "Testing",
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

    test_object.testapp.get("/logout", status=302)

    # Collaborator 2 login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_2, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/logout", status=302)

    # Collaborator 1 login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_1, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Collaborator 1 removes collaborator 2
    # Remove the collaborator
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            collaborator_1, "collaborator_1_prj001", collaborator_2
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/logout", status=302)

    # Collaborator 2 login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_2, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get("/user/{}".format(collaborator_2), status=200)
    assert "FS_error" not in res.headers
