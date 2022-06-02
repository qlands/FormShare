import secrets
import uuid


def t_e_s_t_profile(test_object):
    # Access profile
    res = test_object.testapp.get(
        "/user/{}/profile".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Access profile in edit mode
    res = test_object.testapp.get(
        "/user/{}/profile/edit".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Edit profile fails. Name is empty
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {"editprofile": "", "user_name": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Edit profile passes.
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {
            "api_changed": "0",
            "editprofile": "",
            "user_name": "FormShare",
            "user_about": "FormShare testing account",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Generate a API Token fails. Get was used
    test_object.testapp.get(
        "/api/1/get_token".format(test_object.randonLogin), status=400
    )

    # Generate API token fails. No key or secret
    test_object.testapp.post(
        "/api/1/get_token",
        {
            "some": "1",
        },
        status=400,
    )

    # Generate API token fails. API key does not exist
    test_object.testapp.post(
        "/api/1/get_token",
        {
            "X-API-Key": "some",
            "X-API-Secret": "some",
        },
        status=401,
    )

    test_object.testapp.post(
        "/api/1/get_token",
        {
            "X-API-Key": test_object.randonLoginKey,
            "X-API-Secret": test_object.randonLoginSecret,
        },
        status=200,
    )

    test_object.randonLoginKey = str(uuid.uuid4())
    test_object.randonLoginSecret = secrets.token_hex(16)
    # Edit profile passes. Changing API key and secret
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {
            "api_changed": "1",
            "user_apikey": test_object.randonLoginKey,
            "user_apisecret": test_object.randonLoginSecret,
            "editprofile": "",
            "user_name": "FormShare",
            "user_about": "FormShare testing account",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change password fails. Old password is empty
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {"changepass": "", "old_pass": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password fails. New password is empty
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {"changepass": "", "old_pass": "123", "new_pass": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password fails. New passwords are not the same
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {
            "changepass": "",
            "old_pass": "123",
            "new_pass": "123",
            "conf_pass": "321",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password fails. Old password is incorrect
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {
            "changepass": "",
            "old_pass": "321",
            "new_pass": "123",
            "conf_pass": "123",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password succeeds
    res = test_object.testapp.post(
        "/user/{}/profile/edit".format(test_object.randonLogin),
        {
            "changepass": "",
            "old_pass": "123",
            "new_pass": "123",
            "conf_pass": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
