import unittest
import time

"""
This testing module test all routes. It launch start the server and test all the routes and processes
We allocated all in one massive test because separating them in different test functions load 
the environment processes multiple times and crash FormShare.
   
"""


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        from formshare import start
        from .config import server_config

        app = start.start(server_config)
        from webtest import TestApp

        self.testapp = TestApp(app)
        self.randonLogin = ""
        self.collaboratorLogin = ""

    def test_all(self):
        def test_root():
            # Test the root urls
            self.testapp.get("/", status=200)
            self.testapp.get("/login", status=200)
            self.testapp.get("/join", status=200)
            self.testapp.get("/not_found", status=404)

        def test_login():
            # Login failed
            self.testapp.post(
                "/login", {"user": "", "email": "some", "passwd": "none"}, status=200
            )

            # Register fail. Bad email
            self.testapp.post(
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

            # Register fail. Empty password
            self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": "test@qlands.com",
                    "user_password": "",
                    "user_id": "test",
                    "user_password2": "test",
                    "user_name": "Testing",
                },
                status=200,
            )

            # Register fail. Invalid user id
            self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": "test@qlands.com",
                    "user_password": "123",
                    "user_id": "just@test",
                    "user_password2": "123",
                    "user_name": "Testing",
                },
                status=200,
            )

            # Register fail. Passwords not the same
            self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": "test@qlands.com",
                    "user_password": "123",
                    "user_id": "test",
                    "user_password2": "321",
                    "user_name": "Testing",
                },
                status=200,
            )

            random_login = "formshare"
            self.randonLogin = random_login

            # Register succeed
            self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": random_login + "@qlands.com",
                    "user_password": "123",
                    "user_id": random_login,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                },
                status=302,
            )

            # Register fail. Account already exists
            self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": random_login + "@qlands.com",
                    "user_password": "123",
                    "user_id": random_login,
                    "user_password2": "123",
                    "user_name": "Testing",
                },
                status=200,
            )

            # Login succeed
            self.testapp.post(
                "/login",
                {"user": "", "email": random_login, "passwd": "123"},
                status=302,
            )

        def test_dashboard():
            # Test access to the dashboard
            self.testapp.get("/user/{}".format(self.randonLogin), status=200)

            # Add user fail. ID is not correct
            self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {"user_id": "some@test"},
                status=200,
            )

            # Add user fail. ID already exists
            self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {"user_id": self.randonLogin},
                status=200,
            )

            # Add user fail. Password is empty
            self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {"user_id": "testuser2", "user_password": ""},
                status=200,
            )

            # Add user fail. Passwords don't match
            self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {
                    "user_id": "testuser2",
                    "user_password": "123",
                    "user_password2": "321",
                },
                status=200,
            )

            # Add user fail. Email is not correct
            self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {
                    "user_id": "testuser2",
                    "user_password": "123",
                    "user_password2": "123",
                    "user_email": "hello",
                },
                status=200,
            )

            # Add user fail. Email exists
            self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {
                    "user_id": "testuser2",
                    "user_password": "123",
                    "user_password2": "123",
                    "user_email": self.randonLogin + "@qlands.com",
                },
                status=200,
            )

            random_login = "collaborator"
            self.collaboratorLogin = random_login
            # Add user succeed
            self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {
                    "user_id": random_login,
                    "user_password": "123",
                    "user_password2": "123",
                    "user_email": random_login + "@qlands.com",
                },
                status=302,
            )

            # Edit an user fail. Email is invalid
            self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"modify": "", "user_email": "hola"},
                status=200,
            )

            # Edit an user fail. New email exists
            self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"modify": "", "user_email": self.randonLogin + "@qlands.com"},
                status=200,
            )
            time.sleep(
                5
            )  # Wait 5 seconds for Elastic search to store the user before updating it

            # Edit an user pass.
            self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {
                    "modify": "",
                    "user_email": random_login + "@qlands.com",
                    "user_apikey": "newkey",
                },
                status=302,
            )

            # Change user password fail. Password is empty
            self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"changepass": "", "user_password": ""},
                status=200,
            )

            # Change user password fail. Passwords are not the same
            self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"changepass": "", "user_password": "123", "user_password2": "321"},
                status=200,
            )

            # Change user password succeed
            self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"changepass": "", "user_password": "123", "user_password2": "123"},
                status=302,
            )

            # List users
            self.testapp.get(
                "/user/{}/manage_users".format(self.randonLogin), status=200
            )

        def test_profile():
            # Access profile
            self.testapp.get("/user/{}/profile".format(self.randonLogin), status=200)

            # Edit profile fails. Name is empty
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"editprofile": "", "user_name": ""},
                status=200,
            )

            # Edit profile passes.
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"editprofile": "", "user_name": "FormShare"},
                status=302,
            )

            # Change password fails. Old password is empty
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"changepass": "", "old_pass": ""},
                status=200,
            )

            # Change password fails. New password is empty
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"changepass": "", "old_pass": "123", "new_pass": ""},
                status=200,
            )

            # Change password fails. New passwords are not the same
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"changepass": "", "old_pass": "123", "new_pass": "123", "conf_pass": "321"},
                status=200,
            )

            # Change password fails. Old password is incorrect
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"changepass": "", "old_pass": "321", "new_pass": "123", "conf_pass": "123"},
                status=200,
            )

            # Change password succeeds
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"changepass": "", "old_pass": "123", "new_pass": "123", "conf_pass": "123"},
                status=302,
            )

        def test_projects():
            pass

        test_root()
        test_login()
        test_dashboard()
        test_profile()
        test_projects()
