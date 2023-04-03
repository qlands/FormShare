import os
import secrets
import uuid


def t_e_s_t_one_user_assistant(test_object):
    random_login = str(uuid.uuid4())
    random_login = random_login[-12:]

    # Test logout
    test_object.testapp.get("/logout", status=302)

    # Register succeed
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": random_login + "@qlands.com",
            "user_password": "123",
            "user_id": random_login,
            "user_password2": "123",
            "user_name": "T",
            "user_super": "1",
            "user_apikey": str(uuid.uuid4()),
            "user_apisecret": secrets.token_hex(16),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login succeed
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": random_login, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    project_id = str(uuid.uuid4())
    # Add a project succeed.
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(random_login),
        {
            "project_id": project_id,
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

    # Add assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(random_login, "test001"),
        {
            "coll_id": "assistant001",
            "coll_name": "assistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Upload a form a succeeds
    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(random_login, "test001"),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            random_login, "test001", "Justtest"
        ),
        {
            "coll_id": "{}|{}".format(project_id, "assistant001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(random_login, "test001"),
        {"login": "assistant001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Assistant logout succeeds.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(random_login, "test001"),
        {"login": "assistant001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an second assistant to differentt project

    project_id = str(uuid.uuid4())
    # Add a project 2 succeed.
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(random_login),
        {
            "project_id": project_id,
            "project_code": "test002",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Ass assistant to project 2
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(random_login, "test002"),
        {
            "coll_id": "assistant002",
            "coll_name": "assistant002",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an assistant of project 2 to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            random_login, "test001", "Justtest"
        ),
        {
            "coll_id": "{}|{}".format(project_id, "assistant002"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(random_login, "test001"),
        {"login": "assistant002", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Test getting the forms.
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(random_login, "test001"),
        status=200,
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing="assistant002"),
    )

    # Set the assistant as not shareable
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/edit".format(
            random_login, "test001", "assistant002"
        ),
        {"coll_id": "assistant002"},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(random_login, "test001"),
        {"login": "assistant002", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Test getting the forms.
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(random_login, "test001"),
        status=200,
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing="assistant002"),
    )
