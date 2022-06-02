import secrets
import uuid


def t_e_s_t_five_collaborators(test_object):
    collaborators = []
    collaborator_to_remove = ""
    for n in range(5):
        random_login = str(uuid.uuid4())
        random_login = random_login[-12:]
        collaborators.append(random_login)
        res = test_object.testapp.post(
            "/join",
            {
                "user_email": random_login + "@qlands.com",
                "user_password": "123",
                "user_id": random_login,
                "user_password2": "123",
                "user_name": "TT",
                "user_super": "1",
                "user_apikey": str(uuid.uuid4()),
                "user_apisecret": secrets.token_hex(16),
            },
            status=302,
        )
        assert "FS_error" not in res.headers
        if n == 3:
            collaborator_to_remove = random_login

    test_object.testapp.get("/logout", status=302)

    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    for a_collaborator in collaborators:
        # Add a collaborator succeed
        res = test_object.testapp.post(
            "/user/{}/project/{}/collaborators".format(
                test_object.randonLogin, test_object.project
            ),
            {"add_collaborator": "", "collaborator": a_collaborator},
            status=302,
        )
        assert "FS_error" not in res.headers

    # Change the role of a collaborator
    test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "change_role": "",
            "collaborator_id": collaborator_to_remove,
            "role_collaborator": 3,
        },
        status=302,
    )

    test_object.testapp.get("/logout", status=302)

    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_to_remove, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a new projec to the collaborator to be removed
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(collaborator_to_remove),
        {
            "project_code": "test001",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Sets the original project as active
    res = test_object.testapp.post(
        "/user/{}/project/{}/setactive".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get("/logout", status=302)

    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Gets the details of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, test_object.project),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Remove the collaborator
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            test_object.randonLogin, test_object.project, collaborator_to_remove
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
