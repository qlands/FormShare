import uuid
import secrets


def t_e_s_t_delete_active_project(test_object):
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

    # Add a first project
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

    # Add a second project
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(collaborator_1),
        {
            "project_code": "collaborator_1_prj002",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete a project
    res = test_object.testapp.post(
        "/user/{}/project/{}/delete".format(collaborator_1, "collaborator_1_prj002"),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete a project
    res = test_object.testapp.post(
        "/user/{}/project/{}/delete".format(collaborator_1, "collaborator_1_prj001"),
        status=302,
    )
    assert "FS_error" not in res.headers
