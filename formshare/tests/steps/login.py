import secrets
import time
import uuid

from .sql import get_tokens_from_user


def t_e_s_t_login(test_object):
    # Login failed
    res = test_object.testapp.post(
        "/login", {"user": "", "email": "some", "passwd": "none"}, status=200
    )
    assert "FS_error" in res.headers

    # Register fail. Bad email
    res = test_object.testapp.post(
        "/join",
        {
            "user_address": "Costa Rica",
            "user_email": "some",
            "user_password": "test",
            "user_id": "test",
            "user_password2": "test",
            "user_name": "Testing",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Register fail. Empty password
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": "test@qlands.com",
            "user_password": "",
            "user_id": "test",
            "user_password2": "test",
            "user_name": "Testing",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Register fail. Invalid user id
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": "test@qlands.com",
            "user_password": "123",
            "user_id": "just@test",
            "user_password2": "123",
            "user_name": "Testing",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Register fail. Invalid email
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": "@test",
            "user_password": "123",
            "user_id": "test",
            "user_password2": "123",
            "user_name": "Testing",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Register fail. Passwords not the same
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": "test@qlands.com",
            "user_password": "123",
            "user_id": "test",
            "user_password2": "321",
            "user_name": "Testing",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    random_login = str(uuid.uuid4())
    test_object.randonLoginKey = random_login
    test_object.randonLoginSecret = secrets.token_hex(16)
    random_login = random_login[-12:]

    #  random_login = "formshare"
    test_object.randonLogin = random_login
    print("**************Random Login: {}".format(test_object.randonLogin))

    # Register user fails. Password is too long
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": random_login + "@qlands.com",
            "user_password": "qwNEDKztEmtv165VDdoE55UaW7ubx2fqWDOerGWwPyyjkJY7a1V8ESxRKA7G",
            "user_id": random_login,
            "user_password2": "qwNEDKztEmtv165VDdoE55UaW7ubx2fqWDOerGWwPyyjkJY7a1V8ESxRKA7G",
            "user_name": "Testing",
            "user_super": "1",
            "user_apikey": test_object.randonLoginKey,
            "user_apisecret": test_object.randonLoginSecret,
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Register succeed
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": random_login + "@qlands.com",
            "user_password": "123",
            "user_id": random_login,
            "user_password2": "123",
            "user_name": "Testing",
            "user_super": "1",
            "user_apikey": test_object.randonLoginKey,
            "user_apisecret": test_object.randonLoginSecret,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    random_login_partner = str(uuid.uuid4())
    random_login_partner_key = random_login_partner
    random_login_partner = random_login_partner[-12:]
    test_object.randonLoginPartner = random_login_partner

    # Logout
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    # Logout
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    # Register succeed of user for partner
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": random_login_partner + "@qlands.com",
            "user_password": "123",
            "user_id": random_login_partner,
            "user_password2": "123",
            "user_name": "Testing Testing",
            "user_super": "0",
            "user_apikey": random_login_partner_key,
            "user_apisecret": secrets.token_hex(16),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Logout
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    # Test recover the password
    res = test_object.testapp.post(
        "/recover",
        {"email": random_login + "@qlands.org", "user": "some_thing"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Test recover the password
    res = test_object.testapp.post(
        "/recover",
        {"email": random_login + "@qlands.com", "user": "some_thing"},
        status=302,
    )
    assert "FS_error" not in res.headers
    time.sleep(2)

    token_data = get_tokens_from_user(
        test_object.server_config, random_login + "@qlands.com"
    )

    # Password reset for a key that does not exist goes to 404
    test_object.testapp.get("/reset/{}/password".format("not_exist"), status=404)

    # Load the password reset
    test_object.testapp.get(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        status=200,
    )

    # Posting with empty email fails
    res = test_object.testapp.post(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        {"email": "", "user": "some_thing"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Posting with email not exist fails
    res = test_object.testapp.post(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        {"email": "not_exist@qlands.com", "user": "some_thing"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Posting empty token
    res = test_object.testapp.post(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        {
            "email": random_login + "@qlands.com",
            "user": "some_thing",
            "token": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Posting token not exist fails
    res = test_object.testapp.post(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        {
            "email": random_login + "@qlands.com",
            "user": "some_thing",
            "token": "not_exist",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Posting empty password fails
    res = test_object.testapp.post(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        {
            "email": random_login + "@qlands.com",
            "user": "some_thing",
            "token": token_data["user_password_reset_token"],
            "password": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Posting invalid password fails
    res = test_object.testapp.post(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        {
            "email": random_login + "@qlands.com",
            "user": "some_thing",
            "token": token_data["user_password_reset_token"],
            "password": "123",
            "password2": "321",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Password reset passes
    res = test_object.testapp.post(
        "/reset/{}/password".format(token_data["user_password_reset_key"]),
        {
            "email": random_login + "@qlands.com",
            "user": "some_thing",
            "token": token_data["user_password_reset_token"],
            "password": "123",
            "password2": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Register fail. Account already exists
    res = test_object.testapp.post(
        "/join",
        {
            "user_address": "Costa Rica",
            "user_email": random_login + "@qlands.com",
            "user_password": "123",
            "user_id": random_login,
            "user_password2": "123",
            "user_name": "Testing Testing Testing",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Login succeed
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": random_login, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/login",
        status=302,
    )
    assert "FS_error" not in res.headers

    # Logout
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login fails wrong pass
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": random_login, "passwd": "wrong_pass"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Login succeed
    res = test_object.testapp.post(
        "/login",
        {"user": "test", "email": random_login, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
