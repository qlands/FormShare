"""The HTTP API: a Bearer token instead of a session.

A token is issued by /api/1/security/login for an API key and secret. Sent
as Authorization: Bearer, it authenticates the request and turns the view's
result into a JSON envelope. Users and assistants each have their own key.
"""

import json
import os
import secrets
import uuid


def t_e_s_t_api_token_user(test_object):
    testapp = test_object.testapp
    login = test_object.randonLogin

    # A token cannot be requested with GET, nor without a key and secret
    testapp.get("/api/1/security/login", status=400)
    testapp.post("/api/1/security/login", {}, status=400)

    # The key and secret as a JSON body
    res = testapp.post_json(
        "/api/1/security/login",
        {
            "X-API-Key": test_object.randonLoginKey,
            "X-API-Secret": test_object.randonLoginSecret,
        },
        status=200,
    )
    token = res.json["result"]["token"]
    bearer = {"Authorization": "Bearer " + token}

    # A token nobody was issued
    res = testapp.get(
        "/user/{}/projects".format(login),
        headers={"Authorization": "Bearer " + secrets.token_hex(16)},
        status=401,
    )
    assert res.json["status"] == "401"

    # A header with no token after the word is not an API call at all
    testapp.get("/logout", status=302)
    testapp.get(
        "/user/{}/projects".format(login),
        headers={"Authorization": "Bearer"},
        status=302,
    )

    # A user who has a key but left the secret empty is told to set one
    keyed_user = uuid.uuid4().hex[-12:]
    keyed_key = str(uuid.uuid4())
    res = testapp.post(
        "/join",
        {
            "user_email": keyed_user + "@qlands.com",
            "user_password": "123",
            "user_id": keyed_user,
            "user_password2": "123",
            "user_name": "Keyed",
            "user_apikey": keyed_key,
            "user_apisecret": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    testapp.get("/logout", status=302)
    res = testapp.post_json(
        "/api/1/security/login",
        {"X-API-Key": keyed_key, "X-API-Secret": "anything"},
        status=401,
    )
    assert "API secret" in res.json["error"]

    # A page that renders a dictionary comes back as JSON
    res = testapp.get("/user/{}/projects".format(login), headers=bearer, status=200)
    assert res.json["error"] is False
    assert "userProjects" in res.json["result"]

    # A page that would redirect comes back as JSON too
    project_code = "api" + uuid.uuid4().hex[:8]
    project = {
        "project_id": str(uuid.uuid4()),
        "project_code": project_code,
        "project_name": "Created through the API",
        "project_abstract": "",
        "project_hexcolor": "",
        "project_formlist_auth": 1,
    }
    res = testapp.post_json(
        "/user/{}/projects/add".format(login), project, headers=bearer, status=200
    )
    assert res.json["error"] is False

    # The same project again is an error: 400 and the messages
    res = testapp.post_json(
        "/user/{}/projects/add".format(login), project, headers=bearer, status=400
    )
    assert res.json["error"] is True
    assert len(res.json["errors"]) > 0

    # A multipart body is decoded like a browser form
    resource_file = os.path.join(
        test_object.path, *["resources", "forms", "form03_OK.xlsx"]
    )
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, project_code),
        {"form_pkey": "hid", "form_target": ""},
        upload_files=[("xlsx", resource_file)],
        headers=bearer,
        status=200,
    )
    assert res.json["error"] is False

    # An upload with no file is an error through a redirecting view
    res = testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(login, project_code, "Justtest_3"),
        {},
        headers=bearer,
        status=400,
    )
    assert res.json["error"] is True

    # A file attached to the form, and read back: a raw result stays raw
    resource_file = os.path.join(
        test_object.path, *["resources", "forms", "complex_form", "image001.png"]
    )
    res = testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(login, project_code, "Justtest_3"),
        upload_files=[("filetoupload", resource_file)],
        headers=bearer,
        status=200,
    )
    assert res.json["error"] is False
    res = testapp.get(
        "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
            login, project_code, "Justtest_3", "image001.png"
        ),
        headers=bearer,
        status=200,
    )
    assert res.content_type == "image/png"

    # A page that does not exist is still a 404
    testapp.get(
        "/user/{}/project/{}".format(login, "not_exist"), headers=bearer, status=404
    )

    # Clean up through the API
    res = testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, project_code, "Justtest_3"),
        {},
        headers=bearer,
        status=200,
    )
    assert res.json["error"] is False
    res = testapp.post(
        "/user/{}/project/{}/delete".format(login, project_code),
        {},
        headers=bearer,
        status=200,
    )
    assert res.json["error"] is False

    # The browser session is still the way in for the rest of the suite
    res = testapp.post(
        "/login", {"user": "", "email": login, "passwd": "123"}, status=302
    )
    assert "FS_error" not in res.headers


def t_e_s_t_api_token_assistant(test_object):
    testapp = test_object.testapp
    login = test_object.randonLogin
    project = test_object.project
    base = "/user/{}/project/{}/assistantaccess".format(login, project)

    # The assistant signs in and sets a key and secret of its own
    res = testapp.post(
        base + "/login",
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
    key = str(uuid.uuid4())
    secret = secrets.token_hex(16)
    res = testapp.post(
        base + "/changemykey",
        {"coll_apikey": key, "coll_apisecret": secret},
        status=302,
    )
    assert "FS_error" not in res.headers
    test_object.assistantLoginKey = key
    testapp.get(base + "/logout", status=302)

    res = testapp.post_json(
        "/api/1/security/login",
        {"X-API-Key": key, "X-API-Secret": secret},
        status=200,
    )
    token = res.json["result"]["token"]
    bearer = {"Authorization": "Bearer " + token}

    # A token nobody was issued
    res = testapp.get(
        base + "/forms",
        headers={"Authorization": "Bearer " + secrets.token_hex(16)},
        status=401,
    )
    assert res.json["status"] == "401"

    # The assistant's forms as JSON
    res = testapp.get(base + "/forms", headers=bearer, status=200)
    assert res.json["error"] is False
    assert "forms" in json.dumps(res.json["result"])

    # A change that would redirect comes back as JSON
    res = testapp.post_json(
        base + "/changemytimezone", {"coll_timezone": "UTC"}, headers=bearer, status=200
    )
    assert res.json["error"] is False

    # And so does one that fails
    res = testapp.post_json(
        base + "/changemypassword",
        {"coll_password": "1", "coll_password2": "2"},
        headers=bearer,
        status=400,
    )
    assert res.json["error"] is True

    # A file stays a file
    res = testapp.get(
        base + "/form/{}/qrcode".format(test_object.formID), headers=bearer, status=200
    )
    assert res.content_type.startswith("image/")

    # The steps that follow expect the assistant signed in, as it was
    res = testapp.post(
        base + "/login",
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
