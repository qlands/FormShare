import uuid


def t_e_s_t_users_management(test_object):
    random_managed_user = str(uuid.uuid4())[-12:]
    random_managed_email = random_managed_user + "@qlands.com"

    # Get manage_users list
    res = test_object.testapp.get(
        "/user/{}/manage_users".format(test_object.randonLogin),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Another user tries to access manage_users → 404
    test_object.testapp.get(
        "/user/{}/manage_users".format("not_me"),
        status=404,
    )

    # Get add user page
    res = test_object.testapp.get(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Add user fails: invalid user id (special chars)
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": "bad!user",
            "user_email": random_managed_email,
            "user_password": "123",
            "user_password2": "123",
            "user_name": "Test Managed",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fails: user already exists (randonLogin user)
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": test_object.randonLogin,
            "user_email": random_managed_email,
            "user_password": "123",
            "user_password2": "123",
            "user_name": "Test Managed",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fails: empty password
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": random_managed_user,
            "user_email": random_managed_email,
            "user_password": "",
            "user_password2": "",
            "user_name": "Test Managed",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fails: passwords don't match
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": random_managed_user,
            "user_email": random_managed_email,
            "user_password": "123",
            "user_password2": "321",
            "user_name": "Test Managed",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user fails: invalid email
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": random_managed_user,
            "user_email": "not_an_email",
            "user_password": "123",
            "user_password2": "123",
            "user_name": "Test Managed",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add user succeeds
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": random_managed_user,
            "user_email": random_managed_email,
            "user_password": "123",
            "user_password2": "123",
            "user_name": "Test Managed",
            "user_super": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add user fails: email already exists
    res = test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {
            "user_id": "another_" + random_managed_user[:8],
            "user_email": random_managed_email,
            "user_password": "123",
            "user_password2": "123",
            "user_name": "Test Managed",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Get the edit page for the new user
    res = test_object.testapp.get(
        "/user/{}/manage_user/{}/edit".format(
            test_object.randonLogin, random_managed_user
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Edit non-existent user → 404
    test_object.testapp.get(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, "not_exist"),
        status=404,
    )

    # Edit user fails: invalid email in modify action
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(
            test_object.randonLogin, random_managed_user
        ),
        {
            "modify": "",
            "user_id": random_managed_user,
            "user_email": "not_valid_email",
            "user_name": "Test Managed Updated",
            "user_apisecret": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Edit user succeeds (includes user_super, user_tenant, pops user_id, pops empty apisecret)
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(
            test_object.randonLogin, random_managed_user
        ),
        {
            "modify": "",
            "user_id": random_managed_user,
            "user_email": random_managed_email,
            "user_name": "Test Managed Updated",
            "user_super": "1",
            "user_tenant": "main",
            "user_apikey": str(uuid.uuid4()),
            "user_apisecret": "",
            "user_active": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change password fails: empty password
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(
            test_object.randonLogin, random_managed_user
        ),
        {
            "changepass": "",
            "user_password": "",
            "user_password2": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password fails: passwords don't match
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(
            test_object.randonLogin, random_managed_user
        ),
        {
            "changepass": "",
            "user_password": "new_pass",
            "user_password2": "different_pass",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password succeeds
    res = test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(
            test_object.randonLogin, random_managed_user
        ),
        {
            "changepass": "",
            "user_password": "new_pass_123",
            "user_password2": "new_pass_123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
