import secrets
import uuid


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

    # Collaborator logout
    test_object.testapp.get("/logout", status=302)

    # Main user login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
