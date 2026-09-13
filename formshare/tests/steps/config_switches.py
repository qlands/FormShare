"""Code that a deployment setting switches on or off.

The test configuration fixes each setting one way, so the other side of the
switch never runs. The settings dict the views read is a process-wide one,
so a test can flip a key for a few requests and put it back.
"""

import contextlib
import os
import time
import uuid

from formshare.middleware.settings import get_settings


@contextlib.contextmanager
def settings_set_to(overrides):
    """Apply *overrides* to the live settings and restore them afterwards."""
    settings = get_settings()
    missing = object()
    previous = {key: settings.get(key, missing) for key in overrides}
    settings.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is missing:
                settings.pop(key, None)
            else:
                settings[key] = value


@contextlib.contextmanager
def system_timezone(name):
    """Run with the process in time zone *name*, as the server may be."""
    previous = os.environ.get("TZ")
    os.environ["TZ"] = name
    time.tzset()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


def t_e_s_t_config_switches(test_object):
    login = test_object.randonLogin
    testapp = test_object.testapp
    dashboard = "/user/{}".format(login)

    # A partial whose markers are not in the page comes back whole
    testapp.get(dashboard + "?partial=no_such_partial", status=200)

    # secure.javascript moves inline scripts into an ephemeral file
    with settings_set_to({"secure.javascript": "true"}):
        res = testapp.get(dashboard, status=200)
        assert b"/fstatic/ephemeral/" in res.body
        # A partial skips it, the fragment has no body to attach a script to
        testapp.get(dashboard + "?partial=main", status=200)
        # The public, assistant and partner pages register it too
        testapp.get("/", status=200)
        testapp.get(
            "/user/{}/project/{}/assistantaccess/login".format(
                login, test_object.project
            ),
            status=200,
        )
        testapp.get("/partneraccess/login", status=200)

    # The server clock in a zone the time zone table knows
    with system_timezone("EST"):
        testapp.get(dashboard, status=200)
        testapp.get(
            "/user/{}/project/{}/assistantaccess/login".format(
                login, test_object.project
            ),
            status=200,
        )

    # User management is only for deployments that add users by hand
    with settings_set_to(
        {
            "always_add_user": "false",
            "auth.register_users_via_web": "true",
            "formshare.saas.mode": "False",
        }
    ):
        testapp.get("/user/{}/manage_users".format(login), status=404)
        testapp.get("/user/{}/manage_users/add".format(login), status=404)
        testapp.get("/user/{}/manage_user/{}/edit".format(login, login), status=404)

    # Roles and tenants change what the user pages offer
    with settings_set_to({"auth.use_roles": "true", "auth.use_tenants": "true"}):
        testapp.get("/user/{}/manage_users/add".format(login), status=200)
        testapp.get("/user/{}/manage_users".format(login), status=200)
        testapp.get("/user/{}/manage_user/{}/edit".format(login, login), status=200)
        # Self registration is off when roles are on outside SaaS mode
        testapp.get("/join", status=404)

    # Self registration switched off
    with settings_set_to({"auth.register_users_via_web": "false"}):
        testapp.get("/join", status=404)

    # The post checks refuse a form that carries no CSRF token
    testapp.get("/logout", status=302)
    with settings_set_to({"perform_post_checks": "true"}):
        res = testapp.post(
            "/login", {"user": "", "email": login, "passwd": "123"}, status=302
        )
        assert "FS_error" in res.headers
        testapp.post(
            "/join",
            {
                "user_email": "csrf@qlands.com",
                "user_password": "123",
                "user_id": "csrfuser",
                "user_password2": "123",
                "user_name": "CSRF",
            },
            status=404,
        )
        testapp.post("/recover", {"user": "", "email": login}, status=404)
        testapp.post(
            "/user/{}/project/{}/assistantaccess/login".format(
                login, test_object.project
            ),
            {"login": "nobody", "passwd": "123"},
            status=404,
        )
        testapp.post(
            "/partneraccess/login", {"login": "nobody", "passwd": "123"}, status=404
        )
    res = testapp.post(
        "/login", {"user": "", "email": login, "passwd": "123"}, status=302
    )
    assert "FS_error" not in res.headers

    # The form checker is told to ignore tables that do not fit a row
    with settings_set_to({"ignore_too_many_selects": "true"}):
        resource_file = os.path.join(
            test_object.path, *["resources", "forms", "form05.xlsx"]
        )
        res = testapp.post(
            "/user/{}/project/{}/forms/add".format(login, test_object.project),
            {"form_pkey": "hid"},
            status=302,
            upload_files=[("xlsx", resource_file)],
        )
        assert "FS_error" in res.headers

    # The health page reports a full disk
    with settings_set_to({"max_disk_usage": "0"}):
        testapp.get("/health", status=500)

    # Password recovery is off without a mail server, unless the deployment
    # says to ignore that
    with settings_set_to({"ignore_email_check": "false"}):
        testapp.get("/recover", status=404)
        testapp.get("/reset/some_key/password", status=404)

    # Recovery with no sender address, and with an empty one: the mail
    # cannot go out, and the request still ends on the login page
    for sender in [None, ""]:
        with settings_set_to({"mail.from": sender}):
            testapp.post("/recover", {"user": "", "email": login}, status=302)

    # A user id is generated for a new user when the deployment says so
    with settings_set_to({"auth.auto_gen_user_id": "true"}):
        testapp.get("/join", status=200)
        testapp.get("/logout", status=302)
        auto_user = uuid.uuid4().hex[-12:]
        res = testapp.post(
            "/join",
            {
                "user_email": auto_user + "@qlands.com",
                "user_password": "123",
                "user_password2": "123",
                "user_name": "Auto",
            },
            status=302,
        )
        assert "FS_error" not in res.headers
        testapp.get("/logout", status=302)
    res = testapp.post(
        "/login", {"user": "", "email": login, "passwd": "123"}, status=302
    )
    assert "FS_error" not in res.headers

    # Slow requests are reported when asked
    with settings_set_to({"report_processing_time": "true"}):
        testapp.get(dashboard, status=200)

    # In SaaS mode the user search stays within the tenant
    with settings_set_to({"formshare.saas.mode": "True"}):
        testapp.get("/user/{}/api/select2_user?q=a".format(login), status=200)
