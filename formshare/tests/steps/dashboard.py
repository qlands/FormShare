import uuid
import time
import secrets


def t_e_s_t_dashboard(test_object):
    # Test error screen
    test_object.testapp.get(
        "/test/{}/test_error".format(test_object.randonLogin), status=500
    )

    # Test access to the dashboard
    res = test_object.testapp.get(
        "/user/{}".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Add user fail. ID is not correct
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {"user_id": "some@test"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fail. ID already exists
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {"user_id": test_object.randonLogin},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fail. Password is empty
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {"user_id": "testuser2", "user_password": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fail. Passwords don't match
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": "testuser2",
            "user_password": "123",
            "user_password2": "321",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fail. Email is not correct
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": "testuser2",
            "user_password": "123",
            "user_password2": "123",
            "user_email": "hello",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fail. Email exists
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": "testuser2",
            "user_password": "123",
            "user_password2": "123",
            "user_email": test_object.randonLogin + "@qlands.com",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    random_login = str(uuid.uuid4())
    random_login = random_login[-12:]
    # random_login = "collaborator"
    test_object.collaboratorLogin = random_login
    # Add user succeed
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": random_login,
            "user_password": "123",
            "user_password2": "123",
            "user_email": random_login + "@qlands.com",
            "user_name": random_login,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add user as super user
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": random_login + "_b",
            "user_password": "123",
            "user_password2": "123",
            "user_email": random_login + "_b@qlands.com",
            "user_name": random_login + "_b",
            "user_super": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Edit an user fail. Email is invalid
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, random_login),
        {"modify": "", "user_email": "hola"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Edit an user fail. New email exists
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, random_login),
        {"modify": "", "user_email": test_object.randonLogin + "@qlands.com"},
        status=200,
    )
    assert "FS_error" in res.headers
    time.sleep(
        5
    )  # Wait 5 seconds for Elastic search to store the user before updating it

    # Edit an user pass.
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, random_login),
        {
            "modify": "",
            "user_email": random_login + "@qlands.com",
            "user_apikey": str(uuid.uuid4()),
            "user_apisecret": secrets.token_hex(16),
            "user_active": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change user password fail. Password is empty
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, random_login),
        {"changepass": "", "user_password": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Change user password fail. Passwords are not the same
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, random_login),
        {"changepass": "", "user_password": "123", "user_password2": "321"},
        status=200,
    )
    assert "FS_error" in res.headers

    test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, "not_exist"),
        {"changepass": "", "user_password": "123", "user_password2": "123"},
        status=404,
    )

    res = test_object.testapp.get(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, random_login),
        status=200,
    )

    # Change user password succeed
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, random_login),
        {"changepass": "", "user_password": "123", "user_password2": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # List users
    res = test_object.testapp.get(
        "/user/{}/manage_users".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers
