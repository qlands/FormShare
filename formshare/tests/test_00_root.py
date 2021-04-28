import json
import os
import shutil
import time
import unittest
import uuid
import datetime
import glob
import pkg_resources
from sqlalchemy import create_engine

"""
This testing module test all routes. It launch start the server and test all the routes and processes
We allocated all in one massive test because separating them in different test functions load 
the environment processes multiple times and crash FormShare.
   
"""


def store_task_status(task, config):
    from sqlalchemy import create_engine

    message_id = str(uuid.uuid4())
    engine = create_engine(config["sqlalchemy.url"])
    engine.execute(
        "INSERT INTO finishedtask (task_id,task_enumber) VALUES ('{}',0)".format(task)
    )
    engine.execute(
        "INSERT INTO taskmessages (message_id, celery_taskid, message_date, message_content) "
        "VALUES ('{}','{}','{}','success')".format(
            message_id, task, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        )
    )
    engine.dispose()


def get_form_details(config, project, form):
    engine = create_engine(config["sqlalchemy.url"])
    result = engine.execute(
        "SELECT form_directory,form_schema,form_reptask,form_createxmlfile,form_insertxmlfile,form_hexcolor "
        "FROM odkform WHERE project_id = '{}' AND form_id = '{}'".format(project, form)
    ).fetchone()
    result = {
        "form_directory": result[0],
        "form_schema": result[1],
        "form_reptask": result[2],
        "form_createxmlfile": result[3],
        "form_insertxmlfile": result[4],
        "form_hexcolor": result[5],
    }
    engine.dispose()
    return result


def get_repository_task(config, project, form):
    engine = create_engine(config["sqlalchemy.url"])
    result = engine.execute(
        "SELECT celery_taskid FROM product WHERE project_id = '{}' "
        "AND form_id = '{}' AND product_id = 'repository'".format(project, form)
    ).fetchone()
    return result[0]


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get("FORMSHARE_PYTEST_RUNNING", "false") == "false":
            raise ValueError(
                "Environment variable FORMSHARE_PYTEST_RUNNING must be true. "
                "Do 'export FORMSHARE_PYTEST_RUNNING=true' before running PyTest"
            )
        config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), *["test_config.json"]
        )
        with open(config_file) as json_file:
            server_config = json.load(json_file)

        from formshare import main

        from pathlib import Path

        home = str(Path.home())

        paths2 = ["formshare_pytest"]
        working_dir = os.path.join(home, *paths2)
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)

        app = main(None, **server_config)
        from webtest import TestApp

        self.testapp = TestApp(app)

        self.randonLogin = ""
        self.randonLoginKey = ""
        self.server_config = server_config
        self.collaboratorLogin = ""
        self.project = ""
        self.projectID = ""
        self.assistantLogin = ""
        self.assistantLogin2 = ""
        self.assistantLoginKey = ""
        self.assistantGroupID = ""
        self.formID = ""
        self.formID2 = ""
        self.formMultiLanguageID = ""
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.working_dir = working_dir

    def test_all(self):
        def test_root():
            pkg_resources.require("formshare")
            # Test the root urls
            self.testapp.get("/", status=200)
            self.testapp.get("/refresh", status=200)
            self.testapp.get("/login", status=200)
            self.testapp.get("/join", status=200)
            self.testapp.get("/recover", status=200)
            self.testapp.get("/not_found", status=404)
            self.testapp.get("/gravatar?name=Carlos", status=200)

        def test_login():
            # Login failed
            res = self.testapp.post(
                "/login", {"user": "", "email": "some", "passwd": "none"}, status=200
            )
            assert "FS_error" in res.headers

            # Register fail. Bad email
            res = self.testapp.post(
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
            res = self.testapp.post(
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
            assert "FS_error" in res.headers

            # Register fail. Invalid user id
            res = self.testapp.post(
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
            assert "FS_error" in res.headers

            # Register fail. Invalid email
            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
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
            res = self.testapp.post(
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
            assert "FS_error" in res.headers

            random_login = str(uuid.uuid4())
            self.randonLoginKey = random_login
            random_login = random_login[-12:]

            #  random_login = "formshare"
            self.randonLogin = random_login
            print("**************Random Login: {}".format(self.randonLogin))

            # Join goes to 404
            res = self.testapp.post(
                "/join",
                {
                    "user_address": "",
                    "user_email": random_login + "@qlands.com",
                    "user_password": "123",
                    "user_id": random_login,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": self.randonLoginKey,
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Register user fails. Password is too long
            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": random_login + "@qlands.com",
                    "user_password": "qwNEDKztEmtv165VDdoE55UaW7ubx2fqWDOerGWwPyyjkJY7a1V8ESxRKA7G",
                    "user_id": random_login,
                    "user_password2": "qwNEDKztEmtv165VDdoE55UaW7ubx2fqWDOerGWwPyyjkJY7a1V8ESxRKA7G",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": self.randonLoginKey,
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Register succeed
            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": random_login + "@qlands.com",
                    "user_password": "123",
                    "user_id": random_login,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": self.randonLoginKey,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Recover goes to 404
            res = self.testapp.post(
                "/recover",
                {"email": random_login + "@qlands.com", "user": "something"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Test recover the password
            res = self.testapp.post(
                "/recover",
                {"email": random_login + "@qlands.com", "user": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Register fail. Account already exists
            res = self.testapp.post(
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
            assert "FS_error" in res.headers

            # Login succeed
            res = self.testapp.post(
                "/login",
                {"user": "", "email": random_login, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get(
                "/login",
                status=302,
            )
            assert "FS_error" not in res.headers

            # Logout
            res = self.testapp.post(
                "/logout",
                status=302,
            )
            assert "FS_error" not in res.headers

            # Login fails
            res = self.testapp.post(
                "/login",
                {"user": "test", "email": random_login, "passwd": "123"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Login fails wrong pass
            res = self.testapp.post(
                "/login",
                {"user": "", "email": random_login, "passwd": "wrong_pass"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Login succeed
            res = self.testapp.post(
                "/login",
                {"user": "", "email": random_login, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_dashboard():

            if os.environ.get("FORMSHARE_TEST_ERROR_PAGE", "false") == "true":
                # Test error screen
                self.testapp.get(
                    "/test/{}/test_error".format(self.randonLogin), status=500
                )

            # Test access to the dashboard
            res = self.testapp.get("/user/{}".format(self.randonLogin), status=200)
            assert "FS_error" not in res.headers

            # Add user fail. ID is not correct
            res = self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {"user_id": "some@test"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add user fail. ID already exists
            res = self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {"user_id": self.randonLogin},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add user fail. Password is empty
            res = self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {"user_id": "testuser2", "user_password": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add user fail. Passwords don't match
            res = self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {
                    "user_id": "testuser2",
                    "user_password": "123",
                    "user_password2": "321",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Add user fail. Email is not correct
            res = self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
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
            res = self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
                {
                    "user_id": "testuser2",
                    "user_password": "123",
                    "user_password2": "123",
                    "user_email": self.randonLogin + "@qlands.com",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            random_login = str(uuid.uuid4())
            random_login = random_login[-12:]
            # random_login = "collaborator"
            self.collaboratorLogin = random_login
            # Add user succeed
            res = self.testapp.post(
                "/user/{}/manage_users/add".format(self.randonLogin),
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

            # Edit an user fail. Email is invalid
            res = self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"modify": "", "user_email": "hola"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Edit an user fail. New email exists
            res = self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"modify": "", "user_email": self.randonLogin + "@qlands.com"},
                status=200,
            )
            assert "FS_error" in res.headers
            time.sleep(
                5
            )  # Wait 5 seconds for Elastic search to store the user before updating it

            # Edit an user pass.
            res = self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {
                    "modify": "",
                    "user_email": random_login + "@qlands.com",
                    "user_apikey": str(uuid.uuid4()),
                    "user_active": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Change user password fail. Password is empty
            res = self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"changepass": "", "user_password": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Change user password fail. Passwords are not the same
            res = self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"changepass": "", "user_password": "123", "user_password2": "321"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Change user password succeed
            res = self.testapp.post(
                "/user/{}/manage_user/{}/edit".format(self.randonLogin, random_login),
                {"changepass": "", "user_password": "123", "user_password2": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # List users
            res = self.testapp.get(
                "/user/{}/manage_users".format(self.randonLogin), status=200
            )
            assert "FS_error" not in res.headers

        def test_profile():
            # Access profile
            res = self.testapp.get(
                "/user/{}/profile".format(self.randonLogin), status=200
            )
            assert "FS_error" not in res.headers

            # Access profile in edit mode
            res = self.testapp.get(
                "/user/{}/profile/edit".format(self.randonLogin), status=200
            )
            assert "FS_error" not in res.headers

            # Edit profile fails. Name is empty
            res = self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"editprofile": "", "user_name": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Edit profile passes.
            res = self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"editprofile": "", "user_name": "FormShare"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Change password fails. Old password is empty
            res = self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"changepass": "", "old_pass": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Change password fails. New password is empty
            res = self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {"changepass": "", "old_pass": "123", "new_pass": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Change password fails. New passwords are not the same
            res = self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
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
            res = self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
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
            res = self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {
                    "changepass": "",
                    "old_pass": "123",
                    "new_pass": "123",
                    "conf_pass": "123",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_projects():
            # Add a project fails. The project id is empty
            res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {"project_code": "", "project_abstract": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add a project fails. The project id is not valid
            res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {"project_code": "some@test", "project_abstract": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add a project succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Adds a second project
            res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_code": "test002",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a project fails. The project already exists
            res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Edit a project. Get details
            res = self.testapp.get(
                "/user/{}/project/{}/edit".format(self.randonLogin, "test001"),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Edit a project fails. The project name is empty
            res = self.testapp.post(
                "/user/{}/project/{}/edit".format(self.randonLogin, "test001"),
                {"project_code": "test001", "project_abstract": "", "project_name": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # List the projects
            res = self.testapp.get(
                "/user/{}/projects".format(self.randonLogin), status=200
            )
            assert "FS_error" not in res.headers

            # Gets the details of a project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, "test001"), status=200
            )
            assert "FS_error" not in res.headers

            # Edit a project
            res = self.testapp.post(
                "/user/{}/project/{}/edit".format(self.randonLogin, "test001"),
                {
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Delete a project
            res = self.testapp.post(
                "/user/{}/project/{}/delete".format(self.randonLogin, "test001"),
                status=302,
            )
            assert "FS_error" not in res.headers

            self.project = "test001"
            self.projectID = str(uuid.uuid4())

            # Adds again a project.
            res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": self.projectID,
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Gets the QR of a project
            res = self.testapp.get(
                "/user/{}/project/{}/qr".format(self.randonLogin, "test001"), status=200
            )
            assert "FS_error" not in res.headers

            # Sets a project as active
            res = self.testapp.post(
                "/user/{}/project/{}/setactive".format(self.randonLogin, "test001"),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Uploads a file to the project
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/upload".format(self.randonLogin, "test001"),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads the same file reporting that already exists
            res = self.testapp.post(
                "/user/{}/project/{}/upload".format(self.randonLogin, "test001"),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" in res.headers

            # Overwrites the same file
            res = self.testapp.post(
                "/user/{}/project/{}/upload".format(self.randonLogin, "test001"),
                {"overwrite": ""},
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Returns a project file
            res = self.testapp.get(
                "/user/{}/project/{}/storage/{}".format(
                    self.randonLogin, "test001", "test1.dat"
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Remove the project file
            res = self.testapp.post(
                "/user/{}/project/{}/uploads/{}/remove".format(
                    self.randonLogin, "test001", "test1.dat"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Gets the GPS Points of a project
            res = self.testapp.get(
                "/user/{}/project/{}/download/gpspoints".format(
                    self.randonLogin, "test001"
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

        def test_collaborators():
            # Add a collaborator fails. Collaborator in empty
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add a collaborator succeed
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": self.collaboratorLogin},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a collaborator fails. Collaborator already exists
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": self.collaboratorLogin},
                status=200,
            )
            assert "FS_error" in res.headers

            # Change the role of a collaborator
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {
                    "change_role": "",
                    "collaborator_id": self.collaboratorLogin,
                    "role_collaborator": 2,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the collaborators
            res = self.testapp.get(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Remove the collaborator
            res = self.testapp.post(
                "/user/{}/project/{}/collaborator/{}/remove".format(
                    self.randonLogin, self.project, self.collaboratorLogin
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a collaborator again to be used later on
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": self.collaboratorLogin},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the available collaborators
            self.testapp.get(
                "/user/{}/api/select2_user?q={}".format(
                    self.randonLogin, self.collaboratorLogin
                ),
                status=200,
            )

        def test_assistants():
            # Shows th add page
            res = self.testapp.get(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {"coll_id": ""},
                status=200,
            )
            assert "FS_error" not in res.headers

            # Add an assistant fail. The assistant in empty
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {"coll_id": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add an assistant fail. The assistant is invalid
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {"coll_id": "some@test"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add an assistant fail. The passwords are not the same
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "321",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Add an assistant fail. The passwords are empty
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {"coll_id": "assistant001", "coll_password": "", "coll_password2": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add assistant to project that does not exist
            self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, "Not exist"
                ),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=404,
            )

            # Add an assistant succeed
            self.assistantLogin = "assistant001"
            self.assistantLogin2 = "assistant002"

            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add an assistant fail. The assistant already exists
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Get the assistants
            res = self.testapp.get(
                "/user/{}/project/{}/assistants".format(self.randonLogin, self.project),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Get the assistants of not active project
            res = self.testapp.get(
                "/user/{}/project/{}/assistants".format(self.randonLogin, "test002"),
                status=200,
            )
            assert "FS_error" not in res.headers

            # 404 for assistant in a project that does not exist
            self.testapp.get(
                "/user/{}/project/{}/assistants".format(self.randonLogin, "not_exist"),
                status=404,
            )

            # 404 for a project that does not exist
            self.testapp.get(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, "Not_exist", self.assistantLogin
                ),
                status=404,
            )

            # Get the details of an assistant in edit mode
            res = self.testapp.get(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Edit an assistant
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_active": "1", "coll_id": self.assistantLogin},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Edit an assistant
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {
                    "coll_prjshare": "",
                    "coll_active": "1",
                    "coll_id": self.assistantLogin,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Change assistant password fails. Password is empty
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": ""},
                status=302,
            )
            assert "FS_error" in res.headers

            # Change assistant password fails. Passwords are not the same
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "321"},
                status=302,
            )
            assert "FS_error" in res.headers

            # 404 for password change to a project that does not exist
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, "not_exist", self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "123"},
                status=404,
            )

            # 404 change password with get
            self.testapp.get(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "123"},
                status=404,
            )

            # Change assistant succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # 404 delete assistant project do not exits
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/delete".format(
                    self.randonLogin, "Not_exist", self.assistantLogin
                ),
                status=404,
            )

            # 404 delete assistant using get
            self.testapp.get(
                "/user/{}/project/{}/assistant/{}/delete".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=404,
            )

            # Delete the assistant
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/delete".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add the assistant again
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a second assistant
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "assistant002",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a second assistant to other project fails as an assistant name cannot be repeated within an account
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, "test002"
                ),
                {
                    "coll_id": "assistant002",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=200,
            )
            assert "FS_error" in res.headers

        def test_assistant_groups():
            # Show the add group page
            res = self.testapp.get(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Add an assistant group fail. The description is empty
            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add an assistant group succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if a group"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add an assistant group fails. Group name already exists
            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if a group"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Add an assistant group with code succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if a group 2", "group_id": "grp001"},
                status=302,
            )
            assert "FS_error" not in res.headers
            self.assistantGroupID = "grp001"

            # Delete the group
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/delete".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Delete the group using get
            self.testapp.get(
                "/user/{}/project/{}/group/{}/delete".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                status=404,
            )

            # Add an assistant group again
            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if a group 2", "group_id": "grp001"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the assistant groups
            res = self.testapp.get(
                "/user/{}/project/{}/groups".format(self.randonLogin, self.project),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Get the assistant groups in edit mode
            res = self.testapp.get(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Edit the assistant group fails. The name already exists
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"group_desc": "Test if a group", "group_active": "1"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Edit the assistant group fails. Empty name
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"group_desc": "", "group_active": "1"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Edit the assistant group succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"group_desc": "Test if a group 3", "group_active": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Edit the assistant group succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"group_desc": "Test if a group 3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Edit the assistant group succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"group_desc": "Test if a group 3", "group_active": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a member to a group fails. No assistant
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"add_assistant": ""},
                status=302,
            )
            assert "FS_error" in res.headers

            # Add a member to a group fails. Assistant is empty
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"add_assistant": "", "coll_id": ""},
                status=302,
            )
            assert "FS_error" in res.headers

            # Add a member to a group fails. Collaborator does not exists
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"add_assistant": "", "coll_id": "{}|hello2".format(self.projectID)},
                status=302,
            )
            assert "FS_error" in res.headers

            # Add a member to a group succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a second member to a group succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin2),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # List members
            res = self.testapp.get(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Remove a member
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
                    self.randonLogin,
                    self.project,
                    self.assistantGroupID,
                    self.assistantLogin,
                    self.projectID,
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Remove a member using get
            self.testapp.get(
                "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
                    self.randonLogin,
                    self.project,
                    self.assistantGroupID,
                    self.assistantLogin,
                    self.projectID,
                ),
                status=404,
            )

        def test_forms():

            # Uploads a form fails. No key
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Invalid format
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "test"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. PyXForm conversion fails
            paths = ["resources", "forms", "form01.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "test"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a form a fails. Invalid key
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "test"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Invalid ID
            paths = ["resources", "forms", "form02.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Invalid field name
            paths = ["resources", "forms", "form03.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Duplicated choices
            paths = ["resources", "forms", "form04.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Duplicated variables
            paths = ["resources", "forms", "form05.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Duplicated options
            paths = ["resources", "forms", "form06.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a form fails. Too many selects
            paths = ["resources", "forms", "form07.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a form a succeeds
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Upload a form fails. The form already exists
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=200,
            )

            # Edit a project. Get details with a form
            res = self.testapp.get(
                "/user/{}/project/{}/edit".format(self.randonLogin, self.project),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Test access to the dashboard with a form
            res = self.testapp.get("/user/{}".format(self.randonLogin), status=200)
            assert "FS_error" not in res.headers

            # Access profile
            res = self.testapp.get(
                "/user/{}/profile".format(self.randonLogin), status=200
            )
            assert "FS_error" not in res.headers

            # Update a form fails. The form file is not valid
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. The form is not the same
            paths = ["resources", "forms", "form09.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. PyXForm conversion fails
            paths = ["resources", "forms", "form01.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Invalid ID
            paths = ["resources", "forms", "form02.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Invalid field name
            paths = ["resources", "forms", "form03.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Duplicated choices
            paths = ["resources", "forms", "form04.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Duplicated variables
            paths = ["resources", "forms", "form05.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Duplicated options
            paths = ["resources", "forms", "form06.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Too many selects
            paths = ["resources", "forms", "form07.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form a succeeds
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Edit a form. Show details
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/edit".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Edit a form.
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/edit".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_target": "100", "form_hexcolor": "#663f3c"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Set form as active
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/activate".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Delete the form
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/delete".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Upload the form again
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Set form as inactive
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/deactivate".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Set form as inactive
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/activate".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Uploads a file to the form
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads the same file to the form
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" in res.headers

            # Overwrites the same file to the form
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                {"overwrite": ""},
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Removes a file from a form
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
                    self.randonLogin, "test001", "Justtest", "test1.dat"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Uploads the file again
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Gets the file
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
                    self.randonLogin, "test001", "Justtest", "test1.dat"
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form fails. Empty assistant
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"coll_id": ""},
                status=302,
            )
            assert "FS_error" in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Edit an assistant
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    "Justtest",
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Remove the assistant
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
                    self.randonLogin,
                    self.project,
                    "Justtest",
                    self.projectID,
                    self.assistantLogin,
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a group to a form fails. No group_id
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            assert "FS_error" in res.headers

            # Add a group to a form fails. The group_id is empty
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"group_id": ""},
                status=302,
            )
            assert "FS_error" in res.headers

            # Add a group to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"group_id": self.assistantGroupID, "group_privilege": 1},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Edit a group
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/group/{}/edit".format(
                    self.randonLogin, self.project, "Justtest", self.assistantGroupID
                ),
                {"group_privilege": 3},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Delete a group
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/group/{}/remove".format(
                    self.randonLogin, self.project, "Justtest", self.assistantGroupID
                ),
                {"group_privilege": 3},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form again
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_multilanguage_odk():
            # Upload a multi-language form succeeds
            paths = ["resources", "forms", "multi_language", "spanish_english.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "QID"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            self.formMultiLanguageID = "ADANIC_ALLMOD_20141020"

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, self.formMultiLanguageID
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Generate the repository using celery fails due to language
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, self.project, self.formMultiLanguageID
                ),
                {"form_pkey": "QID", "start_stage1": ""},
                status=200,
            )
            self.assertIn(b"form_deflang", res.body)

            # Generate the repository using celery pass
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, self.project, self.formMultiLanguageID
                ),
                {
                    "form_pkey": "QID",
                    "start_stage2": "",
                    "form_deflang": "Español",
                    "LNG-English": "en",
                    "LNG-Español": "es",
                    "languages_string": '[{"code": "", "name": "English"}, {"code": "", "name": "Español"}]',
                },
                status=302,
            )
            assert "FS_error" not in res.headers
            time.sleep(60)

        def test_support_zip_file():
            # Upload a form requiring support CSV files
            paths = ["resources", "forms", "support_zip_file", "support_zip_file.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "support_zip_file"
                ),
                status=200,
            )

            # Uploads a zip support file to the form
            paths = ["resources", "forms", "support_zip_file", "support_file.zip"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, "support_zip_file"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "support_zip_file"
                ),
                status=200,
            )

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, "support_zip_file"
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, self.project, "support_zip_file"
                ),
                {"form_pkey": "I_D", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers
            time.sleep(60)

        def test_external_select():
            # Upload a form requiring support CSV files
            paths = ["resources", "forms", "external", "select_one_external.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "cascading_select_test"
                ),
                status=200,
            )

            # Update a form a succeeds with external selects
            paths = ["resources", "forms", "external", "select_one_external.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "cascading_select_test"
                ),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "cascading_select_test"
                ),
                status=200,
            )

        def test_update_form_missing_files():
            # Upload a form requiring support CSV files
            paths = ["resources", "forms", "support_zip_file", "support_zip_fileB.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "support_zip_fileB"
                ),
                status=200,
            )

            # Update a form a succeeds even if support files are missing
            paths = ["resources", "forms", "support_zip_file", "support_zip_fileB.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "support_zip_fileB"
                ),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "support_zip_fileB"
                ),
                status=200,
            )

        def test_odk():

            # Upload a complex form succeeds
            paths = ["resources", "forms", "complex_form", "B.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            self.formID = "LB_Sequia_MAG_20190123"

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            self.assertTrue(b"Repository check pending" in res.body)

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            self.assertFalse(b"Repository check pending" in res.body)

            # Remove a support file
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
                    self.randonLogin, self.project, self.formID, "distritos.csv"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            self.assertTrue(b"Repository check pending" in res.body)

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            self.assertFalse(b"Repository check pending" in res.body)

            # Test getting the forms. Ask for credential
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, self.project),
                status=401,
            )

            # Test getting the forms.
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, self.project),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            # Test Download the form.
            self.testapp.get(
                "/user/{}/project/{}/{}/xmlform".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            # Get the manifest of a ODK without supporting files. Empty manifest
            self.testapp.get(
                "/user/{}/project/{}/{}/manifest".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            # Get the manifest
            self.testapp.get(
                "/user/{}/project/{}/{}/manifest".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            # Get the a media file
            self.testapp.get(
                "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            # Get head submission
            self.testapp.head(
                "/user/{}/project/{}/submission".format(self.randonLogin, self.project),
                status=204,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            # Test submission
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_norepo",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Test submission one again. Adding image2 to same place of image 1
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_norepo",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[
                    ("filetoupload", submission_file),
                    ("image2", image_file),
                ],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Test submission without precision in GPS
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_norepo",
                "submission002.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Test submission without elevation in GPS
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_norepo",
                "submission003.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Test duplicated submission that will be stored and then processed by the repository
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_norepo",
                "submission004.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Gets the GPS Points of a project
            res = self.testapp.get(
                "/user/{}/project/{}/download/gpspoints".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Gets the GPS Points of a Form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/get/gpspoints".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Test access to the dashboard
            res = self.testapp.get("/user/{}".format(self.randonLogin), status=200)
            assert "FS_error" not in res.headers

            # Gets the details of a project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, self.project), status=200
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Download the ODK form file
            self.testapp.get(
                "/user/{}/project/{}/form/{}/get/odk".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Download data in CSV format
            self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/csv".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Download submitted media files
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/media".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Download submitted media files. No media
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/media".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            assert "FS_error" in res.headers

            form_details = get_form_details(
                self.server_config, self.projectID, self.formID
            )
            form_directory = form_details["form_directory"]
            paths2 = [self.server_config["repository.path"], "odk"]
            odk_dir = os.path.join(self.path, *paths2)

            submissions_path = os.path.join(
                odk_dir, *["forms", form_directory, "submissions", "*.json"]
            )
            files = glob.glob(submissions_path)
            a_submission = None
            if files:
                for file in files:
                    a_submission = file
                    break
            submission_id = os.path.basename(a_submission)
            submission_id = submission_id.replace(".json", "")
            # Get the GeoInformation of the submission_id
            self.testapp.get(
                "/user/{}/project/{}/form/{}/{}/info".format(
                    self.randonLogin, self.project, self.formID, submission_id
                ),
                status=200,
            )

            image_path = os.path.join(
                odk_dir, *["forms", form_directory, "submissions", submission_id, "*.*"]
            )
            files = glob.glob(image_path)
            media_file = None
            if files:
                for file in files:
                    media_file = file
                    break
            media_file = os.path.basename(media_file)

            self.testapp.get(
                "/user/{}/project/{}/form/{}/{}/media/{}/get".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    submission_id,
                    media_file,
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/form/{}/{}/media/{}/get".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    submission_id,
                    "not_found",
                ),
                status=404,
            )

        def test_repository():
            def mimic_create_repository():
                from formshare.products.repository.celery_task import (
                    internal_create_mysql_repository,
                )

                # Adds a mimic project
                mimic_project = "mimic"
                mimic_project_id = str(uuid.uuid4())
                mimic_res = self.testapp.post(
                    "/user/{}/projects/add".format(self.randonLogin),
                    {
                        "project_id": mimic_project_id,
                        "project_code": mimic_project,
                        "project_name": "Test project",
                        "project_abstract": "",
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers
                # Add the mimic form
                mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
                resource_file = os.path.join(self.path, *mimic_paths)
                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/forms/add".format(
                        self.randonLogin, mimic_project
                    ),
                    {"form_pkey": "I_D"},
                    status=302,
                    upload_files=[("xlsx", resource_file)],
                )
                assert "FS_error" not in mimic_res.headers
                mimic_form = "LB_Sequia_MAG_20190123"

                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/assistants/add".format(
                        self.randonLogin, mimic_project
                    ),
                    {
                        "coll_id": "mimic000",
                        "coll_password": "123",
                        "coll_password2": "123",
                        "coll_prjshare": 1,
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers

                # Add an assistant to a form succeeds
                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/form/{}/assistants/add".format(
                        self.randonLogin, mimic_project, mimic_form
                    ),
                    {
                        "coll_id": "{}|{}".format(mimic_project_id, "mimic000"),
                        "coll_privileges": "3",
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers

                # Test submission
                paths4 = ["resources", "forms", "mimic_complex", "submission001.xml"]
                submission_file4 = os.path.join(self.path, *paths4)

                paths4 = ["resources", "forms", "complex_form", "image001.png"]
                image_file4 = os.path.join(self.path, *paths4)

                self.testapp.post(
                    "/user/{}/project/{}/push".format(self.randonLogin, mimic_project),
                    status=201,
                    upload_files=[
                        ("filetoupload", submission_file4),
                        ("image", image_file4),
                    ],
                    extra_environ=dict(
                        FS_for_testing="true", FS_user_for_testing="mimic000"
                    ),
                )
                time.sleep(5)  # Wait for ElasticSearch to store this

                form_details = get_form_details(
                    self.server_config, mimic_project_id, mimic_form
                )
                form_directory = form_details["form_directory"]

                form_reptask = str(uuid.uuid4())

                engine = create_engine(self.server_config["sqlalchemy.url"])
                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,"
                    "celery_taskid,datetime_added,created_by,process_only,output_id) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                        mimic_project_id,
                        mimic_form,
                        "repository",
                        form_reptask,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        1,
                        form_reptask[-12:],
                    )
                )
                engine.execute(sql)
                engine.dispose()

                form_schema = "FS_" + str(uuid.uuid4()).replace("-", "_")

                paths2 = ["resources", "forms", "mimic_complex", "create.sql"]
                create_sql = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "insert.sql"]
                insert_sql = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "create.xml"]
                create_xml = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "insert.xml"]
                insert_xml = os.path.join(self.path, *paths2)

                here = os.path.dirname(os.path.abspath(__file__)).split(
                    "/formshare/tests"
                )[0]
                paths2 = ["mysql.cnf"]
                mysql_cnf = os.path.join(here, *paths2)

                paths2 = [self.server_config["repository.path"], "odk"]
                odk_dir = os.path.join(self.path, *paths2)

                internal_create_mysql_repository(
                    self.server_config,
                    self.randonLogin,
                    mimic_project_id,
                    mimic_project,
                    mimic_form,
                    odk_dir,
                    form_directory,
                    form_schema,
                    "I_D",
                    mysql_cnf,
                    create_sql,
                    insert_sql,
                    create_xml,
                    insert_xml,
                    "",
                    "en",
                    True,
                    form_reptask,
                )

            def mimic_create_repository_with_data():
                from formshare.products.repository.celery_task import (
                    internal_create_mysql_repository,
                )

                # Adds a mimic2 project
                mimic_project = "mimic2"
                mimic_project_id = str(uuid.uuid4())
                mimic_res = self.testapp.post(
                    "/user/{}/projects/add".format(self.randonLogin),
                    {
                        "project_id": mimic_project_id,
                        "project_code": mimic_project,
                        "project_name": "Test project",
                        "project_abstract": "",
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers
                # Add the mimic form
                mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
                resource_file = os.path.join(self.path, *mimic_paths)
                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/forms/add".format(
                        self.randonLogin, mimic_project
                    ),
                    {"form_pkey": "I_D"},
                    status=302,
                    upload_files=[("xlsx", resource_file)],
                )
                assert "FS_error" not in mimic_res.headers
                mimic_form = "LB_Sequia_MAG_20190123"

                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/assistants/add".format(
                        self.randonLogin, mimic_project
                    ),
                    {
                        "coll_id": "mimic001",
                        "coll_password": "123",
                        "coll_password2": "123",
                        "coll_prjshare": 1,
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers

                # Add an assistant to a form succeeds
                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/form/{}/assistants/add".format(
                        self.randonLogin, mimic_project, mimic_form
                    ),
                    {
                        "coll_id": "{}|{}".format(mimic_project_id, "mimic001"),
                        "coll_privileges": "3",
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers

                # Test submission
                paths2 = ["resources", "forms", "mimic_complex", "submission001.xml"]
                submission_file3 = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "complex_form", "image001.png"]
                image_file3 = os.path.join(self.path, *paths2)

                self.testapp.post(
                    "/user/{}/project/{}/push".format(self.randonLogin, mimic_project),
                    status=201,
                    upload_files=[
                        ("filetoupload", submission_file3),
                        ("image", image_file3),
                    ],
                    extra_environ=dict(
                        FS_for_testing="true", FS_user_for_testing="mimic001"
                    ),
                )
                time.sleep(5)  # Wait for ElasticSearch to store this

                form_details = get_form_details(
                    self.server_config, mimic_project_id, mimic_form
                )
                form_directory = form_details["form_directory"]

                form_reptask = str(uuid.uuid4())

                engine = create_engine(self.server_config["sqlalchemy.url"])
                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,"
                    "celery_taskid,datetime_added,created_by,process_only,output_id) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                        mimic_project_id,
                        mimic_form,
                        "repository",
                        form_reptask,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        1,
                        form_reptask[-12:],
                    )
                )
                engine.execute(sql)
                engine.dispose()

                form_schema = "FS_" + str(uuid.uuid4()).replace("-", "_")

                paths2 = ["resources", "forms", "mimic_complex", "create.sql"]
                create_sql = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "insert.sql"]
                insert_sql = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "create.xml"]
                create_xml = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "insert.xml"]
                insert_xml = os.path.join(self.path, *paths2)

                here = os.path.dirname(os.path.abspath(__file__)).split(
                    "/formshare/tests"
                )[0]
                paths2 = ["mysql.cnf"]
                mysql_cnf = os.path.join(here, *paths2)

                paths2 = [self.server_config["repository.path"], "odk"]
                odk_dir = os.path.join(self.path, *paths2)

                internal_create_mysql_repository(
                    self.server_config,
                    self.randonLogin,
                    mimic_project_id,
                    mimic_project,
                    mimic_form,
                    odk_dir,
                    form_directory,
                    form_schema,
                    "I_D",
                    mysql_cnf,
                    create_sql,
                    insert_sql,
                    create_xml,
                    insert_xml,
                    "",
                    "en",
                    False,
                    form_reptask,
                )

            def mimic_create_repository_with_data_grp():
                from formshare.products.repository.celery_task import (
                    internal_create_mysql_repository,
                )

                # Adds a mimic3 project
                mimic_grp_project = "mimic3"
                mimic_grp_project_id = str(uuid.uuid4())
                mimic_res = self.testapp.post(
                    "/user/{}/projects/add".format(self.randonLogin),
                    {
                        "project_id": mimic_grp_project_id,
                        "project_code": mimic_grp_project,
                        "project_name": "Test project",
                        "project_abstract": "",
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers
                # Add the mimic form
                mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
                resource_file = os.path.join(self.path, *mimic_paths)
                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/forms/add".format(
                        self.randonLogin, mimic_grp_project
                    ),
                    {"form_pkey": "I_D"},
                    status=302,
                    upload_files=[("xlsx", resource_file)],
                )
                assert "FS_error" not in mimic_res.headers
                mimic_form = "LB_Sequia_MAG_20190123"

                mimic_res = self.testapp.post(
                    "/user/{}/project/{}/assistants/add".format(
                        self.randonLogin, mimic_grp_project
                    ),
                    {
                        "coll_id": "mimic003",
                        "coll_password": "123",
                        "coll_password2": "123",
                        "coll_prjshare": 1,
                    },
                    status=302,
                )
                assert "FS_error" not in mimic_res.headers

                res3 = self.testapp.post(
                    "/user/{}/project/{}/groups/add".format(
                        self.randonLogin, mimic_grp_project
                    ),
                    {"group_desc": "Mimic group 1", "group_id": "grpmimic001"},
                    status=302,
                )
                assert "FS_error" not in res3.headers

                res3 = self.testapp.post(
                    "/user/{}/project/{}/group/{}/members".format(
                        self.randonLogin, mimic_grp_project, "grpmimic001"
                    ),
                    {
                        "add_assistant": "",
                        "coll_id": "{}|{}".format(mimic_grp_project_id, "mimic003"),
                    },
                    status=302,
                )
                assert "FS_error" not in res3.headers

                # Add an group to a form succeeds
                res3 = self.testapp.post(
                    "/user/{}/project/{}/form/{}/groups/add".format(
                        self.randonLogin, mimic_grp_project, "LB_Sequia_MAG_20190123"
                    ),
                    {"group_id": "grpmimic001", "group_privilege": 3},
                    status=302,
                )
                assert "FS_error" not in res3.headers

                # Test submission
                paths5 = ["resources", "forms", "mimic_complex", "submission001.xml"]
                submission_file5 = os.path.join(self.path, *paths5)

                paths5 = ["resources", "forms", "complex_form", "image001.png"]
                image_file5 = os.path.join(self.path, *paths5)

                self.testapp.post(
                    "/user/{}/project/{}/push".format(
                        self.randonLogin, mimic_grp_project
                    ),
                    status=201,
                    upload_files=[
                        ("filetoupload", submission_file5),
                        ("image", image_file5),
                    ],
                    extra_environ=dict(
                        FS_for_testing="true", FS_user_for_testing="mimic003"
                    ),
                )
                time.sleep(5)  # Wait for ElasticSearch to store this

                form_details = get_form_details(
                    self.server_config, mimic_grp_project_id, mimic_form
                )
                form_directory = form_details["form_directory"]

                form_reptask = str(uuid.uuid4())

                engine = create_engine(self.server_config["sqlalchemy.url"])
                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,"
                    "celery_taskid,datetime_added,created_by,process_only,output_id) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                        mimic_grp_project_id,
                        mimic_form,
                        "repository",
                        form_reptask,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        1,
                        form_reptask[-12:],
                    )
                )
                engine.execute(sql)
                engine.dispose()

                form_schema = "FS_" + str(uuid.uuid4()).replace("-", "_")

                paths2 = ["resources", "forms", "mimic_complex", "create.sql"]
                create_sql = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "insert.sql"]
                insert_sql = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "create.xml"]
                create_xml = os.path.join(self.path, *paths2)

                paths2 = ["resources", "forms", "mimic_complex", "insert.xml"]
                insert_xml = os.path.join(self.path, *paths2)

                here = os.path.dirname(os.path.abspath(__file__)).split(
                    "/formshare/tests"
                )[0]
                paths2 = ["mysql.cnf"]
                mysql_cnf = os.path.join(here, *paths2)

                paths2 = [self.server_config["repository.path"], "odk"]
                odk_dir = os.path.join(self.path, *paths2)

                internal_create_mysql_repository(
                    self.server_config,
                    self.randonLogin,
                    mimic_grp_project_id,
                    mimic_grp_project,
                    mimic_form,
                    odk_dir,
                    form_directory,
                    form_schema,
                    "I_D",
                    mysql_cnf,
                    create_sql,
                    insert_sql,
                    create_xml,
                    insert_xml,
                    "",
                    "en",
                    False,
                    form_reptask,
                )

            # Gets the repository page
            self.testapp.get(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"form_pkey": "I_D", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for Celery to finish

            # Get the details of a form. The form now should have a repository
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            self.assertTrue(b"With repository" in res.body)

            # Removes a required file from a form fails as it is required by repository
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
                    self.randonLogin, self.project, self.formID, "distritos.csv"
                ),
                status=302,
            )
            assert "FS_error" in res.headers

            # Test submission storing into repository
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_repo",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Test submission storing a second identical submission to mimic an incomplete submission
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_repo",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image002.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[
                    ("filetoupload", submission_file),
                    ("image2", image_file),
                ],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Gets the GPS Points of a project
            res = self.testapp.get(
                "/user/{}/project/{}/download/gpspoints".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Gets the GPS Points of a Form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/get/gpspoints".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Test access to the dashboard
            res = self.testapp.get("/user/{}".format(self.randonLogin), status=200)
            assert "FS_error" not in res.headers

            # Gets the details of a project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, self.project), status=200
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Test submitting the same data into the repository storing it into the logs
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_repo",
                "submission004.xml",
            ]
            submission_file = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Add a second submission to test downloads
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_repo",
                "submission005.xml",
            ]
            submission_file2 = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file2 = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[
                    ("filetoupload", submission_file2),
                    ("image", image_file2),
                ],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Add a third submission without GPS precision
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_repo",
                "submission002.xml",
            ]
            submission_file2 = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file2 = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[
                    ("filetoupload", submission_file2),
                    ("image", image_file2),
                ],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )

            time.sleep(5)  # Wait for ElasticSearch to store this

            # Add a forth submission without elevation
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_repo",
                "submission003.xml",
            ]
            submission_file2 = os.path.join(self.path, *paths)

            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file2 = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, self.project),
                status=201,
                upload_files=[
                    ("filetoupload", submission_file2),
                    ("image", image_file2),
                ],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=self.assistantLogin
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this
            mimic_create_repository()
            mimic_create_repository_with_data()
            mimic_create_repository_with_data_grp()

        def test_repository_downloads():
            def mimic_celery_public_csv_process():
                from formshare.products.export.csv.celery_task import internal_build_csv

                engine = create_engine(self.server_config["sqlalchemy.url"])

                form_details = get_form_details(
                    self.server_config, self.projectID, self.formID
                )

                paths = [
                    "odk",
                    "forms",
                    form_details["form_directory"],
                    "submissions",
                    "maps",
                ]
                maps_directory = os.path.join(
                    self.server_config["repository.path"], *paths
                )
                create_xml_file = form_details["form_createxmlfile"]
                insert_xml_file = form_details["form_insertxmlfile"]
                form_schema = form_details["form_schema"]
                task_id = str(uuid.uuid4())
                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
                    "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                        self.projectID,
                        self.formID,
                        "csv_public_export",
                        self.working_dir + "/{}.csv".format(task_id),
                        "text/csv",
                        task_id,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        task_id[-12:],
                        0,
                        1,
                    )
                )
                engine.execute(sql)
                engine.dispose()
                internal_build_csv(
                    self.server_config,
                    maps_directory,
                    create_xml_file,
                    insert_xml_file,
                    form_schema,
                    self.working_dir + "/{}.csv".format(task_id),
                    True,
                    "en",
                    task_id,
                )
                store_task_status(task_id, self.server_config)

                # Download unpublished product fails
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_public_export",
                        task_id[-12:],
                    ),
                    status=404,
                )

                # Publish the product
                res2 = self.testapp.post(
                    "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_public_export",
                        task_id[-12:],
                    ),
                    status=302,
                )
                assert "FS_error" not in res2.headers

                # Download published product pass
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_public_export",
                        task_id[-12:],
                    ),
                    status=200,
                )

                self.testapp.get(
                    "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_public_export",
                        "latest",
                    ),
                    status=200,
                )

                # Unpublish the product
                res2 = self.testapp.post(
                    "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_public_export",
                        task_id[-12:],
                    ),
                    status=302,
                )
                assert "FS_error" not in res2.headers

                # Delete the product
                res2 = self.testapp.post(
                    "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_public_export",
                        task_id[-12:],
                    ),
                    status=302,
                )
                assert "FS_error" not in res2.headers

            def mimic_celery_private_csv_process():
                from formshare.products.export.csv.celery_task import internal_build_csv

                engine = create_engine(self.server_config["sqlalchemy.url"])

                form_details = get_form_details(
                    self.server_config, self.projectID, self.formID
                )

                paths = [
                    "odk",
                    "forms",
                    form_details["form_directory"],
                    "submissions",
                    "maps",
                ]
                maps_directory = os.path.join(
                    self.server_config["repository.path"], *paths
                )
                create_xml_file = form_details["form_createxmlfile"]
                insert_xml_file = form_details["form_insertxmlfile"]

                form_schema = form_details["form_schema"]
                task_id = str(uuid.uuid4())
                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
                    "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                        self.projectID,
                        self.formID,
                        "csv_private_export",
                        self.working_dir + "/{}.csv".format(task_id),
                        "text/csv",
                        task_id,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        task_id[-12:],
                        0,
                        1,
                    )
                )
                engine.execute(sql)
                engine.dispose()
                internal_build_csv(
                    self.server_config,
                    maps_directory,
                    create_xml_file,
                    insert_xml_file,
                    form_schema,
                    self.working_dir + "/{}.csv".format(task_id),
                    False,
                    "en",
                    task_id,
                )
                store_task_status(task_id, self.server_config)
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_private_export",
                        task_id[-12:],
                    ),
                    status=200,
                )
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_private_export",
                        "latest",
                    ),
                    status=200,
                )
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "csv_private_export",
                        task_id[-12:],
                        self.randonLoginKey,
                    ),
                    status=200,
                )

            def mimic_celery_xlsx_process():
                from formshare.products.export.xlsx.celery_task import (
                    internal_build_xlsx,
                )

                engine = create_engine(self.server_config["sqlalchemy.url"])
                form_details = get_form_details(
                    self.server_config, self.projectID, self.formID
                )
                form_directory = form_details["form_directory"]
                form_schema = form_details["form_schema"]
                create_xml_file = form_details["form_createxmlfile"]
                insert_xml_file = form_details["form_insertxmlfile"]
                task_id = str(uuid.uuid4())

                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
                    "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                        self.projectID,
                        self.formID,
                        "xlsx_public_export",
                        self.working_dir + "/{}.xlsx".format(task_id),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        task_id,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        task_id[-12:],
                        0,
                        1,
                    )
                )
                engine.execute(sql)
                engine.dispose()
                internal_build_xlsx(
                    self.server_config,
                    self.server_config["repository.path"] + "/odk",
                    form_directory,
                    form_schema,
                    self.formID,
                    create_xml_file,
                    insert_xml_file,
                    self.working_dir + "/{}.xlsx".format(task_id),
                    True,
                    "en",
                )
                store_task_status(task_id, self.server_config)
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "xlsx_public_export",
                        task_id[-12:],
                    ),
                    status=200,
                )

            def mimic_celery_kml_process():
                from formshare.products.export.kml.celery_task import internal_build_kml

                engine = create_engine(self.server_config["sqlalchemy.url"])

                form_details = get_form_details(
                    self.server_config, self.projectID, self.formID
                )

                form_schema = form_details["form_schema"]
                task_id = str(uuid.uuid4())

                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
                    "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                        self.projectID,
                        self.formID,
                        "kml_export",
                        self.working_dir + "/{}.kml".format(task_id),
                        "application/vnd.google-earth.kml+xml",
                        task_id,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        task_id[-12:],
                        0,
                        1,
                    )
                )
                engine.execute(sql)
                engine.dispose()
                internal_build_kml(
                    self.server_config,
                    form_schema,
                    self.working_dir + "/{}.kml".format(task_id),
                    "en",
                    task_id,
                )
                store_task_status(task_id, self.server_config)
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "kml_export",
                        task_id[-12:],
                    ),
                    status=200,
                )

            def mimic_celery_media_process():
                from formshare.products.export.media.celery_task import (
                    internal_build_media_zip,
                )

                engine = create_engine(self.server_config["sqlalchemy.url"])
                form_details = get_form_details(
                    self.server_config, self.projectID, self.formID
                )
                form_directory = form_details["form_directory"]
                form_schema = form_details["form_schema"]
                task_id = str(uuid.uuid4())

                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
                    "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                        self.projectID,
                        self.formID,
                        "media_export",
                        self.working_dir + "/{}.zip".format(task_id),
                        "application/zip",
                        task_id,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        task_id[-12:],
                        0,
                        1,
                    )
                )
                engine.execute(sql)
                engine.dispose()
                internal_build_media_zip(
                    self.server_config,
                    self.server_config["repository.path"] + "/odk",
                    [form_directory],
                    form_schema,
                    self.working_dir + "/{}.zip".format(task_id),
                    "I_D",
                    "en",
                    task_id,
                )
                store_task_status(task_id, self.server_config)
                self.testapp.get(
                    "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                        self.randonLogin,
                        self.project,
                        self.formID,
                        "media_export",
                        task_id[-12:],
                    ),
                    status=200,
                )

            # Generate submitted media files
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/media".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Generate public XLSX
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/public_xlsx".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Private public XLSX
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/private_xlsx".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # KML
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/kml".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Public CSV
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/repo_public_csv".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Private CSV
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/generate/repo_private_csv".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(40)  # Wait 5 seconds so celery finished this

            # Get the details of a form. The form now should have a repository with products
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            time.sleep(40)
            mimic_celery_public_csv_process()
            mimic_celery_private_csv_process()
            mimic_celery_xlsx_process()
            mimic_celery_kml_process()
            mimic_celery_media_process()

        def test_import_data():
            def mimic_celery_test_import():
                from formshare.products.fs1import.celery_task import (
                    internal_import_json_files,
                )

                engine = create_engine(self.server_config["sqlalchemy.url"])
                form_details = get_form_details(
                    self.server_config, self.projectID, self.formID
                )
                form_directory = form_details["form_directory"]
                form_schema = form_details["form_schema"]
                task_id = str(uuid.uuid4())
                odk_dir = self.server_config["repository.path"] + "/odk"

                file_paths = [
                    "resources",
                    "forms",
                    "complex_form",
                    "for_import",
                    "files2",
                    "tmp",
                ]
                path_to_files = os.path.join(self.path, *file_paths)

                file_to_import = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "file1B.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "tmp",
                        "file1B.json",
                    ]
                )
                shutil.copyfile(file_to_import, file_to_import_target)

                file_to_import = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "file2B.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "tmp",
                        "file2B.json",
                    ]
                )
                shutil.copyfile(file_to_import, file_to_import_target)

                file_to_import = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "file3B.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "tmp",
                        "file3B.json",
                    ]
                )
                shutil.copyfile(file_to_import, file_to_import_target)

                file_to_import = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "file4B.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "tmp",
                        "file4B.json",
                    ]
                )
                shutil.copyfile(file_to_import, file_to_import_target)

                # -------------------
                file_to_import = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "file5B.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files2",
                        "tmp",
                        "file5B.json",
                    ]
                )
                shutil.copyfile(file_to_import, file_to_import_target)
                # ---

                sql = (
                    "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
                    "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
                    "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                        self.projectID,
                        self.formID,
                        "fs1import",
                        None,
                        None,
                        task_id,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.randonLogin,
                        task_id[-12:],
                        1,
                        0,
                    )
                )
                engine.execute(sql)
                engine.dispose()

                internal_import_json_files(
                    self.randonLogin,
                    self.projectID,
                    self.formID,
                    odk_dir,
                    form_directory,
                    form_schema,
                    self.assistantLogin,
                    path_to_files,
                    self.project,
                    "si_participa/SECTION/GPS",
                    self.projectID,
                    self.server_config,
                    "en",
                    False,
                    task_id,
                )
                store_task_status(task_id, self.server_config)

            # Test import a simple file

            # Add a group to a form again
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"group_id": self.assistantGroupID, "group_privilege": 3},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin2),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/form/{}/import".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            paths = [
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "simple_file.json",
            ]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/import".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "import_type": "1",
                    "ignore_xform": "",
                    "assistant": "{}@{}".format(self.assistantLogin, self.projectID),
                },
                status=302,
                upload_files=[("file", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Test import a zip file
            paths = ["resources", "forms", "complex_form", "for_import", "zip_file.zip"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/import".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "import_type": "1",
                    "assistant": "{}@{}".format(self.assistantLogin, self.projectID),
                },
                status=302,
                upload_files=[("file", resource_file)],
            )
            assert "FS_error" not in res.headers
            time.sleep(40)
            mimic_celery_test_import()

        def test_repository_tasks():
            time.sleep(5)  # Wait 5 seconds to other tests to finish
            # Get the tables in a repository
            self.testapp.get(
                "/user/{}/project/{}/form/{}/dictionary/tables".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            # Change the description of a table
            self.testapp.post(
                "/user/{}/project/{}/form/{}/dictionary/tables".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "table_name": "maintable",
                    "table_desc": "New description of maintable",
                },
                status=200,
            )
            # Get the fields of a table
            self.testapp.get(
                "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                status=200,
            )
            # Update the description of a field
            self.testapp.post(
                "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "post_type": "change_desc",
                    "field_name": "i_d",
                    "field_desc": "ID of the farmer",
                },
                status=200,
            )
            # Update the primary key as sensitive
            self.testapp.post(
                "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "post_type": "change_as_sensitive",
                    "field_name": "i_d",
                    "field_protection": "recode",
                },
                status=200,
            )

            # Test the download with the ID as sensitive with recode
            test_repository_downloads()
            time.sleep(20)

            # Update the primary key as not sensitive
            self.testapp.post(
                "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {"post_type": "change_as_not_sensitive", "field_name": "i_d"},
                status=200,
            )

            # Get the submissions on a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}/submissions".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Select the submissions rows
            self.testapp.post(
                "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "",
                    "sord": "asc",
                },
                status=200,
            )

            # Set form as inactive
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/deactivate".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Delete a submission
            form_details = get_form_details(
                self.server_config, self.projectID, self.formID
            )
            engine = create_engine(self.server_config["sqlalchemy.url"])
            res = engine.execute(
                "SELECT rowuuid FROM {}.maintable".format(form_details["form_schema"])
            ).first()
            row_uuid = res[0]
            engine.dispose()
            self.testapp.post(
                "/user/{}/project/{}/form/{}/submissions/delete".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"oper": "del", "id": row_uuid},
                status=200,
            )

        def test_assistant_access():

            # 404 login to project that does not exist
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, "Not_exist"
                ),
                status=404,
            )

            # Test accessing the login page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )

            # Assistant login fails. Assistant not found
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": "123", "passwd": "123"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Assistant login fails. Password is not correct
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": self.assistantLogin, "passwd": "321"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Assistant login succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": self.assistantLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Login page goes to assistant dashboard
            res = self.testapp.get(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Assistant logout succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, self.project
                ),
                {"login": self.assistantLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Assistant login succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": self.assistantLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the assistant forms
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/forms".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )

            # Change the assistant password fails with get
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/changemypassword".format(
                    self.randonLogin, self.project
                ),
                {"coll_password": ""},
                status=404,
            )

            # Change the assistant password fails. Empty password
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/changemypassword".format(
                    self.randonLogin, self.project
                ),
                {"coll_password": ""},
                status=302,
            )
            assert "FS_error" in res.headers

            # Change the assistant password fails. Password not the same
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/changemypassword".format(
                    self.randonLogin, self.project
                ),
                {"coll_password": "123", "coll_password2": "321"},
                status=302,
            )
            assert "FS_error" in res.headers

            # Change the assistant password fails. Old password not correct
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/changemypassword".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_password": "123",
                    "coll_password2": "123",
                    "old_password": "321",
                },
                status=302,
            )
            assert "FS_error" in res.headers

            # Change the assistant password succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/changemypassword".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_password": "123",
                    "coll_password2": "123",
                    "old_password": "123",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Assistant login succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": self.assistantLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.assistantLoginKey = str(uuid.uuid4())

            # Change the assistant key fails with get
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/changemykey".format(
                    self.randonLogin, self.project
                ),
                {"coll_apikey": self.assistantLoginKey},
                status=404,
            )

            # Change the assistant key.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/changemykey".format(
                    self.randonLogin, self.project
                ),
                {"coll_apikey": self.assistantLoginKey},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the assistant QR code
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/qrcode".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

        def test_json_logs():
            # Get all logs
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Get all errors
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"status": "error"},
                status=200,
            )

            form_details = get_form_details(
                self.server_config, self.projectID, self.formID
            )
            engine = create_engine(self.server_config["sqlalchemy.url"])
            sql = "SELECT surveyid FROM {}.maintable WHERE i_d = '501890386'".format(
                form_details["form_schema"]
            )
            res = engine.execute(sql).first()
            survey_id = res[0]

            sql = (
                "SELECT submission_id FROM formshare.submission "
                "WHERE submission_status = 2 AND sameas IS NULL AND project_id = '{}' AND form_id = '{}'".format(
                    self.projectID, self.formID
                )
            )
            res = engine.execute(sql).first()
            duplicated_id = res[0]

            engine.dispose()

            # Get the GeoInformation of the duplicated ID
            self.testapp.get(
                "/user/{}/project/{}/form/{}/{}/info".format(
                    self.randonLogin, self.project, self.formID, survey_id
                ),
                status=200,
            )

            # Get the GeoInformation of submission ID that does not exists
            self.testapp.get(
                "/user/{}/project/{}/form/{}/{}/info".format(
                    self.randonLogin, self.project, self.formID, "not_exist"
                ),
                status=404,
            )

            # Get the media on an unknown submission goes to 404
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/media".format(
                    self.randonLogin, self.project, self.formID, "Not exist", "None"
                ),
                status=404,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # The use cannot get the media goes to 404
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/media".format(
                    self.randonLogin, self.project, self.formID, duplicated_id, "None"
                ),
                status=404,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the media files of the duplicated ID
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/media".format(
                    self.randonLogin, self.project, self.formID, duplicated_id, "None"
                ),
                status=200,
            )

            # Load compare submission
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
            )

            # Load compare submission with submissions that does not exists
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, "NotExist"
                ),
                status=404,
            )

            # Compare the against a submission fails. Same submission
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"submissionid": duplicated_id},
                status=200,
            )
            assert "FS_error" in res.headers

            # Compare the against a submission fails. Submission does not exits
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"submissionid": "test"},
                status=200,
            )
            assert "FS_error" in res.headers

            # Compare the against a submission
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"submissionid": survey_id},
                status=200,
            )
            assert "FS_error" not in res.headers

            # Load disregard submission
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
            )

            # Disregard fails. No note
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Assistant cannot disregard goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=404,
            )

            # Change the assistant to both
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Disregard an unknown submission goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
                    self.randonLogin, self.project, self.formID, "Not_exist"
                ),
                {"notes": "Some notes about the disregard"},
                status=404,
            )

            # Disregard passes
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Disregard again goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=404,
            )

            # Get the disregarded
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=disregarded".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Load cancel disregard submission
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
            )

            # Cancel disregard fails. No note
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": ""},
                status=200,
            )
            assert "FS_error" in res.headers

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # The assistant cannot cancel disregard goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=404,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Cancel an unknown submission goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
                    self.randonLogin, self.project, self.formID, "Not_exists"
                ),
                {"notes": "Some notes about the disregard"},
                status=404,
            )

            # Cancel disregard passes
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Cancel the disregard again goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=404,
            )

            # Checkout the submission that does not exist
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, "NotExist"
                ),
                status=404,
            )

            # Checkout the submission
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Checkout fails with get
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Get the checkout
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"status": "checkout"},
                status=200,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Cancels the checkout goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Change the assistant to clean and submit
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Cancels the checkout for a unknown submission
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
                    self.randonLogin, self.project, self.formID, "Not_Exists"
                ),
                status=404,
            )

            # Cancels the checkout with get goes to 404
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Cancels the checkout pass
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Cancels the checkout goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Gets the submission file that has not been checkout
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Checkout the submission again
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Gets the submission file goes to 404
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Gets the submission file that does not exist
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                    self.randonLogin, self.project, self.formID, "Not_exist"
                ),
                status=404,
            )

            # Gets the submission file
            res = self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
            )
            data = json.loads(res.body)
            data[
                "si_participa/section_household_info/RespondentDetails/I_D"
            ] = "501890387ABC2"
            tmp = os.path.join(self.path, *["tmp"])
            if not os.path.exists(tmp):
                os.makedirs(tmp)
            paths = ["tmp", duplicated_id + ".json"]
            submission_file = os.path.join(self.path, *paths)

            with open(submission_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # Loads the checkin page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
            )

            # Checkin a file fails. No notes
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "", "sequence": "23a243c95547"},
                status=200,
                upload_files=[("json", submission_file)],
            )
            assert "FS_error" in res.headers

            # Checkin a file passes.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the checkin", "sequence": "23a243c95547"},
                status=302,
                upload_files=[("json", submission_file)],
            )
            assert "FS_error" not in res.headers

            os.remove(submission_file)

            # Loads the revision review page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                {"pushed": ""},
                status=200,
            )

            # Loads the revision review page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                status=200,
            )

            # Loads the revision review page a second time
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                status=200,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # View goes to 404
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                status=404,
            )

            # Cancel goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                status=404,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    "Not_exist",
                    "23a243c95547",
                ),
                status=404,
            )

            # Cancel goes to 404 duplicated does not exist
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    "Not_exist",
                    "23a243c95547",
                ),
                status=404,
            )

            # Cancel a revision with get goes to 404
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                status=404,
            )

            # Cancel the revision.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Cancel the revision again goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95547",
                ),
                status=404,
            )

            # -----------------------
            # Checkout the submission again
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Gets the submission file again
            res = self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
            )
            data = json.loads(res.body)
            data["SECTION_META/interviewername"] = "CARLOS QUIROS CAMPOS"
            paths = ["tmp", duplicated_id + ".json"]
            submission_file = os.path.join(self.path, *paths)

            paths_error = ["tmp", duplicated_id + "B.json"]
            submission_file_error = os.path.join(self.path, *paths_error)

            with open(submission_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            with open(submission_file_error, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # Checkin the file again with different file name
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the checkin"},
                status=200,
                upload_files=[("json", submission_file_error)],
            )
            assert "FS_error" in res.headers

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Check in the file goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the checkin"},
                status=404,
                upload_files=[("json", submission_file)],
            )

            # Change the assistant to both
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Check in the file for a submission that does not exist
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, "Not_exist"
                ),
                {"notes": "Some notes about the checkin"},
                status=404,
                upload_files=[("json", submission_file)],
            )

            # Checkin the file again
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the checkin"},
                status=302,
                upload_files=[("json", submission_file)],
            )
            assert "FS_error" not in res.headers

            # Check in the file again goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the checkin"},
                status=404,
                upload_files=[("json", submission_file)],
            )

            os.remove(submission_file)
            os.remove(submission_file_error)

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Push goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95548",
                ),
                status=404,
            )

            # Change the assistant to both
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Push the revision. Goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    "Not_exists",
                    "23a243c95548",
                ),
                status=404,
            )

            # Push the revision. Get goes to 404
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95548",
                ),
                status=404,
            )

            # Push the revision. In this case the passes
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95548",
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Do it again goes to 404
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95548",
                ),
                status=404,
            )

            # Get the checkout
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"status": "fixed"},
                status=200,
            )

            # ----------------------------

            # Checkout the submission again
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Gets the submission file again
            res = self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
            )
            data = json.loads(res.body)
            data[
                "si_participa/section_household_info/RespondentDetails/I_D"
            ] = "501890387ABC2"
            paths = ["tmp", duplicated_id + ".json"]
            submission_file = os.path.join(self.path, *paths)

            with open(submission_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # Checkin the file again
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the checkin", "sequence": "23a243c95549"},
                status=302,
                upload_files=[("json", submission_file)],
            )
            assert "FS_error" not in res.headers

            os.remove(submission_file)

            # Push the revision.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    "23a243c95549",
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the checkout
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"status": "fixed"},
                status=200,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # The assistant cannot load the page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/compare".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    survey_id,
                ),
                status=404,
            )

            # Change the assistant to both
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Load the compare page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/compare".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    duplicated_id,
                    survey_id,
                ),
                status=200,
            )

            # Compare fails. Submission does not have a problem anymore
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"submissionid": survey_id},
                status=404,
            )

            # Checkout the submission that does not have a problem
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Edit an assistant to clean only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Compare fails. The assistant cannot clean anymore
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"submissionid": survey_id},
                status=404,
            )

            # Checkout the submission fails. The assistant cannot clean anymore
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=404,
            )

            # Edit an assistant to clean submmit and clean
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    self.project,
                    self.formID,
                    self.projectID,
                    self.assistantLogin,
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_json_logs_2():
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, self.project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Adds a mimic2 project
            json2_project = "json2"
            json2_project_id = str(uuid.uuid4())
            mimic_res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": json2_project_id,
                    "project_code": json2_project,
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers
            # Add the mimic form
            mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
            resource_file = os.path.join(self.path, *mimic_paths)
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, json2_project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in mimic_res.headers
            json2_form = "LB_Sequia_MAG_20190123"

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json2_project
                ),
                {
                    "coll_id": "json2001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {
                    "coll_id": "{}|{}".format(json2_project_id, "json2001"),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json2_project
                ),
                {
                    "coll_id": "json2002",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {
                    "coll_id": "{}|{}".format(json2_project_id, "json2002"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json2_project
                ),
                {
                    "coll_id": "json2003",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {
                    "coll_id": "{}|{}".format(json2_project_id, "json2003"),
                    "coll_privileges": "2",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {"form_pkey": "I_D", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for Celery to finish

            # Upload submission 1
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json2001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Upload submission 2 goes to logs
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission002.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json2001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Upload submission 3 goes to logs
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission003.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json2001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Upload submission 4 goes to logs
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission004.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json2001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json2_project
                ),
                {"login": "json2001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Assistant does not have access to a form
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=404,
            )

            # Load compare submission
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, ""
                ),
                status=404,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=error".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            form_details = get_form_details(
                self.server_config, json2_project_id, json2_form
            )

            engine = create_engine(self.server_config["sqlalchemy.url"])
            sql = "SELECT surveyid FROM {}.maintable WHERE i_d = '109750690'".format(
                form_details["form_schema"]
            )
            res = engine.execute(sql).first()
            survey_id = res[0]

            sql = (
                "SELECT submission_id FROM formshare.submission "
                "WHERE submission_status = 2 AND sameas IS NULL AND project_id = '{}' AND form_id = '{}'".format(
                    json2_project_id, json2_form
                )
            )
            res = engine.execute(sql).fetchall()
            duplicated_ids = []
            for a_duplicate in res:
                duplicated_ids.append(a_duplicate[0])
            engine.dispose()
            index = 0
            for a_duplicate in duplicated_ids:
                index = index + 1

                # Checkout with get goes to 404
                self.testapp.get(
                    "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                        self.randonLogin, json2_project, json2_form, a_duplicate
                    ),
                    status=404,
                )

                res = self.testapp.post(
                    "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                        self.randonLogin, json2_project, json2_form, a_duplicate
                    ),
                    status=302,
                )
                assert "FS_error" not in res.headers

                self.testapp.get(
                    "/user/{}/project/{}/assistantaccess/form/{}/errors?status=checkout".format(
                        self.randonLogin, json2_project, json2_form
                    ),
                    status=200,
                )

                res = self.testapp.get(
                    "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                        self.randonLogin, json2_project, json2_form, a_duplicate
                    ),
                    status=200,
                )
                data = json.loads(res.body)
                data[
                    "si_participa/section_household_info/RespondentDetails/I_D"
                ] = "109750690ABC{}".format(index)
                paths = ["tmp", a_duplicate + ".json"]
                submission_file = os.path.join(self.path, *paths)

                with open(submission_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

                sequence_id = str(uuid.uuid4())
                sequence_id = sequence_id[-12:]

                # Checkin the file
                res = self.testapp.post(
                    "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                        self.randonLogin, json2_project, json2_form, a_duplicate
                    ),
                    {
                        "notes": "This is not the same as submission: {}. Corrected ID".format(
                            survey_id
                        ),
                        "sequence": sequence_id,
                    },
                    status=302,
                    upload_files=[("json", submission_file)],
                )
                assert "FS_error" not in res.headers
                time.sleep(3)

                # Get the checked in only
                self.testapp.get(
                    "/user/{}/project/{}/assistantaccess/form/{}/errors?status=checkin".format(
                        self.randonLogin, json2_project, json2_form
                    ),
                    status=200,
                )

                # Get all logs
                self.testapp.get(
                    "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                        self.randonLogin, json2_project, json2_form
                    ),
                    status=200,
                )

                os.remove(submission_file)

                # Push the revision.
                res = self.testapp.post(
                    "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                        self.randonLogin,
                        json2_project,
                        json2_form,
                        a_duplicate,
                        sequence_id,
                    ),
                    status=302,
                )
                assert "FS_error" not in res.headers
                time.sleep(5)  # Wait for ElasticSearch to store this

            # Get all logs
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json2_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json2_project
                ),
                {"login": "json2002", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json2_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json2_project
                ),
                {"login": "json2003", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json2_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # ---- Groups
            # Add three groups
            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(
                    self.randonLogin, json2_project
                ),
                {"group_desc": "Test if a group 1", "group_id": "grp001"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(
                    self.randonLogin, json2_project
                ),
                {"group_desc": "Test if a group 2", "group_id": "grp002"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(
                    self.randonLogin, json2_project
                ),
                {"group_desc": "Test if a group 3", "group_id": "grp003"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add three assistants
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json2_project
                ),
                {
                    "coll_id": "jsongrp001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json2_project
                ),
                {
                    "coll_id": "jsongrp002",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json2_project
                ),
                {
                    "coll_id": "jsongrp003",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Add each assistant to each group
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, json2_project, "grp001"
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(json2_project_id, "jsongrp001"),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, json2_project, "grp002"
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(json2_project_id, "jsongrp002"),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, json2_project, "grp003"
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(json2_project_id, "jsongrp003"),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add each group to the form with different privileges
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {"group_id": "grp001", "group_privilege": 1},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {"group_id": "grp002", "group_privilege": 2},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {"group_id": "grp003", "group_privilege": 3},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Login and display with each assistant
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json2_project
                ),
                {"login": "jsongrp001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json2_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json2_project
                ),
                {"login": "jsongrp002", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json2_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json2_project
                ),
                {"login": "jsongrp003", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json2_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_json_logs_4():
            # Adds a mimic2 project
            json4_project = "json4"
            json4_project_id = str(uuid.uuid4())
            mimic_res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": json4_project_id,
                    "project_code": json4_project,
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers
            # Add the mimic form
            mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
            resource_file = os.path.join(self.path, *mimic_paths)
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, json4_project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in mimic_res.headers
            json4_form = "LB_Sequia_MAG_20190123"

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json4_project, json4_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json4_project, json4_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json4_project
                ),
                {
                    "coll_id": "json4001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, json4_project, json4_form
                ),
                {
                    "coll_id": "{}|{}".format(json4_project_id, "json4001"),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, json4_project, json4_form
                ),
                {"form_pkey": "I_D", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for Celery to finish

            # Upload submission 1
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json4_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json4001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Upload submission 2 goes to logs
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission003.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json4_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json4001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            form_details = get_form_details(
                self.server_config, json4_project_id, json4_form
            )

            engine = create_engine(self.server_config["sqlalchemy.url"])
            sql = "SELECT rowuuid FROM {}.maintable WHERE i_d = '109750690'".format(
                form_details["form_schema"]
            )
            res = engine.execute(sql).first()
            row_uuid = res[0]

            sql = (
                "SELECT submission_id FROM formshare.submission "
                "WHERE submission_status = 2 AND sameas IS NULL AND project_id = '{}' AND form_id = '{}'".format(
                    json4_project_id, json4_form
                )
            )
            res = engine.execute(sql).fetchall()
            duplicated_ids = []
            for a_duplicate in res:
                duplicated_ids.append(a_duplicate[0])
            engine.dispose()

            self.testapp.post(
                "/user/{}/project/{}/form/{}/submissions/delete".format(
                    self.randonLogin, json4_project, json4_form
                ),
                {
                    "move_submission": "",
                    "rowuuid": row_uuid,
                    "coll_id": "{}|{}".format(json4_project_id, "json4001"),
                },
                status=302,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json4_project
                ),
                {"login": "json4001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json4_project, json4_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=error".format(
                    self.randonLogin, json4_project, json4_form
                ),
                status=200,
            )

            # Change the assistant to submit only
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    json4_project,
                    json4_form,
                    json4_project_id,
                    "json4001",
                ),
                {"coll_privileges": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/push".format(
                    self.randonLogin, json4_project, json4_form, duplicated_ids[0]
                ),
                status=404,
            )

            # Change the assistant to both
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin,
                    json4_project,
                    json4_form,
                    json4_project_id,
                    "json4001",
                ),
                {"coll_privileges": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/push".format(
                    self.randonLogin, json4_project, json4_form, "Not_exist"
                ),
                status=404,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/push".format(
                    self.randonLogin, json4_project, json4_form, duplicated_ids[0]
                ),
                status=404,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/push".format(
                    self.randonLogin, json4_project, json4_form, duplicated_ids[0]
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/push".format(
                    self.randonLogin, json4_project, json4_form, duplicated_ids[0]
                ),
                status=404,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json4_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_json_logs_3():
            # Adds a mimic2 project
            json3_project = "json3"
            json3_project_id = str(uuid.uuid4())
            mimic_res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": json3_project_id,
                    "project_code": json3_project,
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers
            # Add the mimic form
            mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
            resource_file = os.path.join(self.path, *mimic_paths)
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, json3_project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in mimic_res.headers
            json3_form = "LB_Sequia_MAG_20190123"

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json3_project, json3_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json3_project, json3_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json3_project
                ),
                {
                    "coll_id": "json3001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, json3_project, json3_form
                ),
                {
                    "coll_id": "{}|{}".format(json3_project_id, "json3001"),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, json3_project, json3_form
                ),
                {"form_pkey": "I_D", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for Celery to finish

            # Upload submission 1
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json3_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json3001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Upload submission 2 goes to logs
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission003.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json3_project),
                status=201,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="json3001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            form_details = get_form_details(
                self.server_config, json3_project_id, json3_form
            )

            engine = create_engine(self.server_config["sqlalchemy.url"])
            sql = "SELECT rowuuid FROM {}.maintable WHERE i_d = '109750690'".format(
                form_details["form_schema"]
            )
            res = engine.execute(sql).first()
            row_uuid = res[0]

            sql = (
                "SELECT submission_id FROM formshare.submission "
                "WHERE submission_status = 2 AND sameas IS NULL AND project_id = '{}' AND form_id = '{}'".format(
                    json3_project_id, json3_form
                )
            )
            res = engine.execute(sql).fetchall()
            duplicated_ids = []
            for a_duplicate in res:
                duplicated_ids.append(a_duplicate[0])
            engine.dispose()

            self.testapp.post(
                "/user/{}/project/{}/form/{}/submissions/delete".format(
                    self.randonLogin, json3_project, json3_form
                ),
                {"oper": "del", "id": row_uuid},
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, json3_project
                ),
                {"login": "json3001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, json3_project, json3_form
                ),
                status=200,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors?status=error".format(
                    self.randonLogin, json3_project, json3_form
                ),
                status=200,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/push".format(
                    self.randonLogin, json3_project, json3_form, duplicated_ids[0]
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, json3_project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_clean_interface():

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": self.assistantLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Load the clean page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Load the clean page with a table
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintable".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Load the clean page with a table that does not exist
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintables".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Load the clean page with a table and fields
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintable&fields=provincia|canton".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Request a table
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "loadtable": "",
                    "table": "maintable",
                },
                status=302,
            )

            # Request a table that does not exists
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "loadtable": "",
                    "table": "maintables",
                },
                status=302,
            )

            # Request one field
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "loadfields": "",
                    "fields": "provincia",
                },
                status=302,
            )

            # Request two fields
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "loadfields": "",
                    "fields": ["provincia", "canton"],
                },
                status=302,
            )

            # Request empty fields
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "loadfields": "",
                    "fields": "",
                },
                status=302,
            )

            # Request without fields
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "loadfields": "",
                },
                status=302,
            )

            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
                "?callback=jQuery31104503466642261382_1578424030318".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "",
                    "sord": "asc",
                },
                status=404,
            )

            # Loads the data for the grid
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
                "?callback=jQuery31104503466642261382_1578424030318".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "respondentname",
                    "sord": "asc",
                },
                status=200,
            )

            # Loads the data for the grid
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
                "?callback=jQuery31104503466642261382_1578424030318".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "",
                    "sord": "asc",
                },
                status=200,
            )

            # Loads the data for the grid using a like search pattern
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
                "?callback=jQuery31104503466642261382_1578424030318".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "",
                    "sord": "asc",
                    "searchField": "respondentname",
                    "searchString": "ROGELIO",
                    "searchOper": "like",
                },
                status=200,
            )

            # Loads the data for the grid using a not like search pattern
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
                "?callback=jQuery31104503466642261382_1578424030318".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "",
                    "sord": "asc",
                    "searchField": "respondentname",
                    "searchString": "ROGELIO",
                    "searchOper": "not like",
                },
                status=200,
            )

            form_details = get_form_details(
                self.server_config, self.projectID, self.formID
            )
            engine = create_engine(self.server_config["sqlalchemy.url"])
            res = engine.execute(
                "SELECT rowuuid FROM {}.maintable".format(form_details["form_schema"])
            ).first()
            row_uuid = res[0]
            engine.dispose()

            # Emits a change into the database fails. Unknow operation
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {"landcultivated": "13.000", "oper": "edits", "id": row_uuid},
                status=404,
            )

            # Emits a change into the database fails wih get
            res = self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {"landcultivated": "13.000", "oper": "edit", "id": row_uuid},
                status=200,
            )
            assert "FS_error" in res.headers

            # Emits a change into the database
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {"landcultivated": "13.000", "oper": "edit", "id": row_uuid},
                status=200,
            )
            assert "FS_error" not in res.headers

            # Change data using API fails. No rowuuid
            self.testapp.post_json(
                "/user/{}/project/{}/form/{}/api_update".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"apikey": self.assistantLoginKey, "landcultivated": 14},
                status=400,
            )

            #  Change data using API fails. Field cannot be found
            self.testapp.post_json(
                "/user/{}/project/{}/form/{}/api_update".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "apikey": self.assistantLoginKey,
                    "rowuuid": row_uuid,
                    "some_file": 14,
                },
                status=400,
            )

            #  Change data fails rowuuid not found
            self.testapp.post_json(
                "/user/{}/project/{}/form/{}/api_update".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "apikey": self.assistantLoginKey,
                    "rowuuid": "test",
                    "landcultivated": 14,
                },
                status=400,
            )

            #  Change data fails. Invalid api key
            self.testapp.post_json(
                "/user/{}/project/{}/form/{}/api_update".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"apikey": "some", "rowuuid": "test", "landcultivated": 14},
                status=401,
            )

            #  Change data fails. No api key
            self.testapp.post_json(
                "/user/{}/project/{}/form/{}/api_update".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"rowuuid": "test", "landcultivated": 14},
                status=401,
            )

            #  Change data using API passes
            self.testapp.post_json(
                "/user/{}/project/{}/form/{}/api_update".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "apikey": self.assistantLoginKey,
                    "rowuuid": row_uuid,
                    "landcultivated": 14,
                },
                status=200,
            )

        def test_clean_interface_unauthorized():
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "clean001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, "clean001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": "clean001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Load the clean page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=404,
            )

            # Loads the data for the grid
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/request"
                "?callback=jQuery31104503466642261382_1578424030318".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "",
                    "sord": "asc",
                },
                status=404,
            )

            form_details = get_form_details(
                self.server_config, self.projectID, self.formID
            )
            engine = create_engine(self.server_config["sqlalchemy.url"])
            res = engine.execute(
                "SELECT rowuuid FROM {}.maintable".format(form_details["form_schema"])
            ).first()
            row_uuid = res[0]
            engine.dispose()

            # Emits a change into the database
            self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
                    self.randonLogin, self.project, self.formID, "maintable"
                ),
                {"landcultivated": "13.000", "oper": "edit", "id": row_uuid},
                status=404,
            )

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, self.project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": self.assistantLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_audit():
            # Load the audit page
            self.testapp.get(
                "/user/{}/project/{}/form/{}/audit".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            # Loads the audit data for the grid
            self.testapp.post(
                "/user/{}/project/{}/form/{}/audit/get"
                "?callback=jQuery31104503466642261382_1578424030318".format(
                    self.randonLogin, self.project, self.formID
                ),
                {
                    "_search": "false",
                    "nd": "1578156795454",
                    "rows": "10",
                    "page": "1",
                    "sidx": "",
                    "sord": "asc",
                },
                status=200,
            )

        def test_collaborator_access():
            # Test logout
            self.testapp.get("/logout", status=302)

            # Login succeed by collaborator
            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.collaboratorLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_helpers():
            import formshare.plugins.helpers as helpers
            import datetime

            h = helpers.helper_functions
            h.humanize_date(datetime.datetime.now())
            h.get_version()
            h.readble_date(datetime.datetime.now())
            h.readble_date(datetime.datetime.now(), "es")
            h.readble_date_with_time(datetime.datetime.now())
            h.readble_date_with_time(datetime.datetime.now(), "es")
            h.simple_date(datetime.datetime.now())
            h.simple_date_usa(datetime.datetime.now())
            h.pluralize("home", 1)
            h.pluralize("home", 2)
            h.pluralize("casa", 1, "es")
            h.pluralize("casa", 2, "es")
            h.is_valid_email("cquiros@qlands.com")
            h.is_valid_url("https://formshare.org")
            h.get_icon_from_mime_type("image")
            h.get_icon_from_mime_type("video")
            h.get_icon_from_mime_type("audio")
            h.get_icon_from_mime_type("text/csv")
            h.get_icon_from_mime_type("application/zip")

        def test_utility_functions():
            import formshare.plugins.utilities as u

            u.add_js_resource("test", "test", "test")
            u.add_css_resource("test", "test", "test")
            u.add_route("test", "test", "test", None)
            u.add_field_to_user_schema("test", "test")
            u.add_field_to_project_schema("test", "test")
            u.add_field_to_assistant_schema("test", "test")
            u.add_field_to_assistant_group_schema("test", "test")
            u.add_field_to_form_schema("test", "test")
            u.add_field_to_form_access_schema("test", "test")
            u.add_field_to_form_group_access_schema("test", "test")

        def test_avatar_generator():
            from formshare.processes.avatar import Avatar

            Avatar.generate(45, "Carlos Quiros", "PNG")
            Avatar.generate(45, "CarlosQurios", "PNG")
            Avatar.generate(45, "CQC", "PNG")
            Avatar.generate(45, "CQ", "PNG")
            Avatar.generate(45, "C", "PNG")
            Avatar.generate(45, "", "PNG")
            Avatar.generate(45, "A B C", "PNG")
            Avatar.generate(45, "A B", "PNG")

        def test_color_hash_hex():
            from formshare.processes.color_hash import ColorHash

            color = ColorHash("FormShare")
            a = color.hex
            b = color.rgb

        def test_one_user_assistant():
            random_login = str(uuid.uuid4())
            random_login = random_login[-12:]

            # Test logout
            self.testapp.get("/logout", status=302)

            # Register succeed
            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": random_login + "@qlands.com",
                    "user_password": "123",
                    "user_id": random_login,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": str(uuid.uuid4()),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Login succeed
            res = self.testapp.post(
                "/login",
                {"user": "", "email": random_login, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            project_id = str(uuid.uuid4())
            # Add a project succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(random_login),
                {
                    "project_id": project_id,
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add assistant
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(random_login, "test001"),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Upload a form a succeeds
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(random_login, "test001"),
                {"form_pkey": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    random_login, "test001", "Justtest"
                ),
                {
                    "coll_id": "{}|{}".format(project_id, "assistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    random_login, "test001"
                ),
                {"login": "assistant001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Assistant logout succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    random_login, "test001"
                ),
                {"login": "assistant001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add an second assistant to differentt project

            project_id = str(uuid.uuid4())
            # Add a project 2 succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(random_login),
                {
                    "project_id": project_id,
                    "project_code": "test002",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Ass assistant to project 2
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(random_login, "test002"),
                {
                    "coll_id": "assistant002",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add an assistant of project 2 to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    random_login, "test001", "Justtest"
                ),
                {
                    "coll_id": "{}|{}".format(project_id, "assistant002"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    random_login, "test001"
                ),
                {"login": "assistant002", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Test getting the forms.
            self.testapp.get(
                "/user/{}/project/{}/formList".format(random_login, "test001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="assistant002"
                ),
            )

            # Set the assistant as not shareable
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    random_login, "test001", "assistant002"
                ),
                {"coll_id": "assistant002"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    random_login, "test001"
                ),
                {"login": "assistant002", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Test getting the forms.
            self.testapp.get(
                "/user/{}/project/{}/formList".format(random_login, "test001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="assistant002"
                ),
            )

        def test_five_collaborators():
            collaborators = []
            collaborator_to_remove = ""
            for n in range(5):
                random_login = str(uuid.uuid4())
                random_login = random_login[-12:]
                collaborators.append(random_login)
                res = self.testapp.post(
                    "/join",
                    {
                        "user_address": "Costa Rica",
                        "user_email": random_login + "@qlands.com",
                        "user_password": "123",
                        "user_id": random_login,
                        "user_password2": "123",
                        "user_name": "Testing",
                        "user_super": "1",
                        "user_apikey": str(uuid.uuid4()),
                    },
                    status=302,
                )
                assert "FS_error" not in res.headers
                if n == 3:
                    collaborator_to_remove = random_login

            self.testapp.get("/logout", status=302)

            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.randonLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            for a_collaborator in collaborators:
                # Add a collaborator succeed
                res = self.testapp.post(
                    "/user/{}/project/{}/collaborators".format(
                        self.randonLogin, self.project
                    ),
                    {"add_collaborator": "", "collaborator": a_collaborator},
                    status=302,
                )
                assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_to_remove, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a new projec to the collaborator to be removed
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_to_remove),
                {
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Sets the original project as active
            res = self.testapp.post(
                "/user/{}/project/{}/setactive".format(self.randonLogin, self.project),
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.randonLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Gets the details of a project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, self.project), status=200
            )
            assert "FS_error" not in res.headers

            # Remove the collaborator
            res = self.testapp.post(
                "/user/{}/project/{}/collaborator/{}/remove".format(
                    self.randonLogin, self.project, collaborator_to_remove
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_form_merge():
            paths = ["resources", "forms", "merge", "A", "A.xls"]
            a_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                {"form_pkey": "numero_de_cedula"},
                status=302,
                upload_files=[("xlsx", a_resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, self.project, "tormenta20201105"
                ),
                {"form_pkey": "numero_de_cedula", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for celery to generate the repository

            # TODO: We need to test forms that cannot merge for different reasons

            # Upload B***********************************************

            paths = ["resources", "forms", "merge", "B", "B.xls"]
            b_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge".format(
                    self.randonLogin, self.project, "tormenta20201105"
                ),
                {
                    "for_merging": "",
                    "parent_project": self.projectID,
                    "parent_form": "tormenta20201105",
                },
                status=302,
                upload_files=[("xlsx", b_resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"Merge check pending" in res.body)

            paths = ["resources", "forms", "merge", "B", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "B", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertFalse(b"Merge check pending" in res.body)

            # Show the merge repository page
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    self.project,
                    "tormenta20201117",
                    "tormenta20201105",
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Merge the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    self.project,
                    "tormenta20201117",
                    "tormenta20201105",
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for the merge to finish

            # Get the details of a form tormenta20201117
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"This is the sub-version of" in res.body)

            # Get the details of a form tormenta20201105
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201105"
                ),
                status=200,
            )
            self.assertTrue(b"is the sub-version of this form" in res.body)

            # Gets the details of a project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, self.project), status=200
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/edit".format(
                    self.randonLogin, self.project, "tormenta20201105"
                ),
                {"form_target": "", "form_hexcolor": "#c18097"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/edit".format(
                    self.randonLogin, self.project, "tormenta20201117"
                ),
                {"form_target": "", "form_hexcolor": "#c18097"},
                status=302,
            )
            assert "FS_error" not in res.headers

            #  Merge C with an ignore string message *************************************
            paths = ["resources", "forms", "merge", "C", "C.xls"]
            c_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge".format(
                    self.randonLogin, self.project, "tormenta20201117"
                ),
                {
                    "for_merging": "",
                    "parent_project": self.projectID,
                    "parent_form": "tormenta20201117",
                },
                status=302,
                upload_files=[("xlsx", c_resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                status=200,
            )
            self.assertTrue(b"Merge check pending" in res.body)

            paths = ["resources", "forms", "merge", "C", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "C", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                status=200,
            )
            self.assertFalse(b"Merge check pending" in res.body)

            # Merge the repository using celery fails with message about values to ignore
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    self.project,
                    "tormenta20201130",
                    "tormenta20201117",
                ),
                status=200,
            )
            assert "FS_error" not in res.headers
            self.assertTrue(b"There are changes in the descriptions" in res.body)

            # Merge the repository using celery passes
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    self.project,
                    "tormenta20201130",
                    "tormenta20201117",
                ),
                {"valuestoignore": "lkplista_de_bancos:8"},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for the merge to finish

            # Get the details of a form tormenta20201117
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                status=200,
            )
            self.assertTrue(b"This is the sub-version of" in res.body)

            # Remove all submissions
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/submissions/deleteall".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                {"owner_email": self.randonLogin + "@qlands.com"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the details of a form tormenta20201117
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                status=200,
            )
            self.assertTrue(b"Without submissions" in res.body)

            # Delete the form
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/delete".format(
                    self.randonLogin, self.project, "tormenta20201130"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_form_merge_mimic():
            # Adds a mimic2 project
            merge_project = "mergemimic1"
            merge_project_id = str(uuid.uuid4())
            mimic_res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": merge_project_id,
                    "project_code": merge_project,
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            paths = ["resources", "forms", "merge", "A", "A.xls"]
            a_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, merge_project),
                {"form_pkey": "numero_de_cedula"},
                status=302,
                upload_files=[("xlsx", a_resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, merge_project
                ),
                {
                    "coll_id": "merge001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                {"form_pkey": "numero_de_cedula", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for celery to generate the repository

            # Upload B***********************************************

            paths = ["resources", "forms", "merge", "B", "B.xls"]
            b_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                {
                    "for_merging": "",
                    "parent_project": merge_project_id,
                    "parent_form": "tormenta20201105",
                },
                status=302,
                upload_files=[("xlsx", b_resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"Merge check pending" in res.body)

            paths = ["resources", "forms", "merge", "B", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "B", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                {
                    "coll_id": "{}|{}".format(merge_project_id, "merge001"),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Upload submission 1
            paths = [
                "resources",
                "forms",
                "merge",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, merge_project),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="merge001"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertFalse(b"Merge check pending" in res.body)

            # Show the merge repository page
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    merge_project,
                    "tormenta20201117",
                    "tormenta20201105",
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            from formshare.products.merge.celery_task import (
                internal_merge_into_repository,
            )

            form_details_a = get_form_details(
                self.server_config, merge_project_id, "tormenta20201117"
            )

            form_details_b = get_form_details(
                self.server_config, merge_project_id, "tormenta20201105"
            )

            engine = create_engine(self.server_config["sqlalchemy.url"])
            task_id = str(uuid.uuid4())
            sql = (
                "INSERT INTO product (project_id,form_id,product_id,"
                "celery_taskid,datetime_added,created_by,process_only,output_id) "
                "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                    merge_project_id,
                    "tormenta20201117",
                    "merge_form",
                    task_id,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    self.randonLogin,
                    1,
                    task_id[-12:],
                )
            )
            engine.execute(sql)
            engine.dispose()

            internal_merge_into_repository(
                self.server_config,
                self.randonLogin,
                merge_project_id,
                merge_project,
                "tormenta20201117",
                form_details_a["form_directory"],
                form_details_b["form_directory"],
                form_details_b["form_createxmlfile"],
                form_details_b["form_schema"],
                "",
                form_details_b["form_hexcolor"],
                "en",
                False,
                task_id,
            )

            # Get the details of a form tormenta20201117
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"This is the sub-version of" in res.body)

            # Get the details of a form tormenta20201105
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=200,
            )
            self.assertTrue(b"is the sub-version of this form" in res.body)

        def test_form_merge_mimic2():
            # Adds a mimic2 project
            merge_project = "mergemimic2"
            merge_project_id = str(uuid.uuid4())
            mimic_res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": merge_project_id,
                    "project_code": merge_project,
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            paths = ["resources", "forms", "merge", "A", "A.xls"]
            a_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, merge_project),
                {"form_pkey": "numero_de_cedula"},
                status=302,
                upload_files=[("xlsx", a_resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, merge_project
                ),
                {
                    "coll_id": "merge002",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(
                    self.randonLogin, merge_project
                ),
                {"group_desc": "Merge group 1", "group_id": "grpmerge001"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, merge_project, "grpmerge001"
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(merge_project_id, "merge002"),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                {"form_pkey": "numero_de_cedula", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for celery to generate the repository

            # Upload B***********************************************

            paths = ["resources", "forms", "merge", "B", "B.xls"]
            b_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                {
                    "for_merging": "",
                    "parent_project": merge_project_id,
                    "parent_form": "tormenta20201105",
                },
                status=302,
                upload_files=[("xlsx", b_resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"Merge check pending" in res.body)

            paths = ["resources", "forms", "merge", "B", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "B", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an group to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                {"group_id": "grpmerge001", "group_privilege": 3},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Upload submission 1
            paths = [
                "resources",
                "forms",
                "merge",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, merge_project),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="merge002"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertFalse(b"Merge check pending" in res.body)

            # Show the merge repository page
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    merge_project,
                    "tormenta20201117",
                    "tormenta20201105",
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            from formshare.products.merge.celery_task import (
                internal_merge_into_repository,
            )

            form_details_a = get_form_details(
                self.server_config, merge_project_id, "tormenta20201117"
            )

            form_details_b = get_form_details(
                self.server_config, merge_project_id, "tormenta20201105"
            )

            engine = create_engine(self.server_config["sqlalchemy.url"])
            task_id = str(uuid.uuid4())
            sql = (
                "INSERT INTO product (project_id,form_id,product_id,"
                "celery_taskid,datetime_added,created_by,process_only,output_id) "
                "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                    merge_project_id,
                    "tormenta20201117",
                    "merge_form",
                    task_id,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    self.randonLogin,
                    1,
                    task_id[-12:],
                )
            )
            engine.execute(sql)
            engine.dispose()

            internal_merge_into_repository(
                self.server_config,
                self.randonLogin,
                merge_project_id,
                merge_project,
                "tormenta20201117",
                form_details_a["form_directory"],
                form_details_b["form_directory"],
                form_details_b["form_createxmlfile"],
                form_details_b["form_schema"],
                "",
                form_details_b["form_hexcolor"],
                "en",
                False,
                task_id,
            )

            # Get the details of a form tormenta20201117
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"This is the sub-version of" in res.body)

            # Get the details of a form tormenta20201105
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=200,
            )
            self.assertTrue(b"is the sub-version of this form" in res.body)

        def test_form_merge_mimic3():
            # Adds a mimic2 project
            merge_project = "mergemimic3"
            merge_project_id = str(uuid.uuid4())
            mimic_res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": merge_project_id,
                    "project_code": merge_project,
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            paths = ["resources", "forms", "merge", "A", "A.xls"]
            a_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, merge_project),
                {"form_pkey": "numero_de_cedula"},
                status=302,
                upload_files=[("xlsx", a_resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "A", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, merge_project
                ),
                {
                    "coll_id": "merge003",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                {"form_pkey": "numero_de_cedula", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for celery to generate the repository

            # Upload B***********************************************

            paths = ["resources", "forms", "merge", "B", "B.xls"]
            b_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                {
                    "for_merging": "",
                    "parent_project": merge_project_id,
                    "parent_form": "tormenta20201105",
                },
                status=302,
                upload_files=[("xlsx", b_resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"Merge check pending" in res.body)

            paths = ["resources", "forms", "merge", "B", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            paths = ["resources", "forms", "merge", "B", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                {
                    "coll_id": "{}|{}".format(merge_project_id, "merge003"),
                    "coll_privileges": "3",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Upload submission 1
            paths = [
                "resources",
                "forms",
                "merge",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, merge_project),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="merge003"
                ),
            )
            time.sleep(5)  # Wait for ElasticSearch to store this

            # Get the details of a form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertFalse(b"Merge check pending" in res.body)

            # Show the merge repository page
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    merge_project,
                    "tormenta20201117",
                    "tormenta20201105",
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            from formshare.products.merge.celery_task import (
                internal_merge_into_repository,
            )

            form_details_a = get_form_details(
                self.server_config, merge_project_id, "tormenta20201117"
            )

            form_details_b = get_form_details(
                self.server_config, merge_project_id, "tormenta20201105"
            )

            engine = create_engine(self.server_config["sqlalchemy.url"])
            task_id = str(uuid.uuid4())
            sql = (
                "INSERT INTO product (project_id,form_id,product_id,"
                "celery_taskid,datetime_added,created_by,process_only,output_id) "
                "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                    merge_project_id,
                    "tormenta20201117",
                    "merge_form",
                    task_id,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    self.randonLogin,
                    1,
                    task_id[-12:],
                )
            )
            engine.execute(sql)
            engine.dispose()

            internal_merge_into_repository(
                self.server_config,
                self.randonLogin,
                merge_project_id,
                merge_project,
                "tormenta20201117",
                form_details_a["form_directory"],
                form_details_b["form_directory"],
                form_details_b["form_createxmlfile"],
                form_details_b["form_schema"],
                "",
                form_details_b["form_hexcolor"],
                "en",
                True,
                task_id,
            )

            # Get the details of a form tormenta20201117
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201117"
                ),
                status=200,
            )
            self.assertTrue(b"This is the sub-version of" in res.body)

            # Get the details of a form tormenta20201105
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, merge_project, "tormenta20201105"
                ),
                status=200,
            )
            self.assertTrue(b"is the sub-version of this form" in res.body)

        def test_group_assistant():
            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "agrpssistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add an assistant group again
            res = self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if an assistant group", "group_id": "assgrp003"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a member to a group succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, "assgrp003"
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(self.projectID, "agrpssistant001"),
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a group to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/groups/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"group_id": "assgrp003", "group_privilege": 1},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, self.project),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="agrpssistant001"
                ),
            )

            # Assistant logout succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, self.project
                ),
                {"login": "agrpssistant001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Assistant login succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/login".format(
                    self.randonLogin, self.project
                ),
                {"login": "agrpssistant001", "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the assistant forms
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/forms".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {
                    "coll_id": "{}|{}".format(self.projectID, "agrpssistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, self.project),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="agrpssistant001"
                ),
            )

            # Get the assistant forms
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/forms".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )

        def test_delete_form_with_repository():
            # Delete the form
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/delete".format(
                    self.randonLogin, self.project, "ADANIC_ALLMOD_20141020"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_api():

            collaborator_1 = str(uuid.uuid4())
            collaborator_1_key = collaborator_1
            collaborator_1 = collaborator_1[-12:]

            # Add a new collaborator
            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_1 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_1,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_1_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # API Call fails. User cannot change this project
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": collaborator_1_key,
                    "user_id": collaborator_1,
                    "project_user": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest",
                },
                upload_files=[("file_to_upload", resource_file)],
                status=400,
            )

            # New collaborator logout
            self.testapp.get("/logout", status=302)

            # Main user login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.randonLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add the collaborator to the project but just member
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": collaborator_1},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Main user logout
            self.testapp.get("/logout", status=302)

            # Collaborator login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            print(self.projectID)
            # API Call fails. User does not have editor or admin grants to this project
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": collaborator_1_key,
                    "user_id": collaborator_1,
                    "project_user": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest",
                },
                upload_files=[("file_to_upload", resource_file)],
                status=400,
            )

            # Collaborator logout
            self.testapp.get("/logout", status=302)

            # Main user login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.randonLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # API Call fails. Form not found
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": self.randonLoginKey,
                    "user_id": self.randonLogin,
                    "project_user": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest_not_found",
                },
                upload_files=[("file_to_upload", resource_file)],
                status=400,
            )

            # API Call fails. No file to upload
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": self.randonLoginKey,
                    "user_id": self.randonLogin,
                    "project_user": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest",
                },
                status=400,
            )

            # API Call fails. project_user key is missing
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": self.randonLoginKey,
                    "user_id": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest",
                },
                status=400,
            )

            # Add a file to a form using API pass
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": self.randonLoginKey,
                    "user_id": self.randonLogin,
                    "project_user": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest",
                },
                upload_files=[("file_to_upload", resource_file)],
                status=200,
            )

            # Add a file again fails. No overwrite
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": self.randonLoginKey,
                    "user_id": self.randonLogin,
                    "project_user": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest",
                },
                upload_files=[("file_to_upload", resource_file)],
                status=400,
            )

            # Add a file again pass. Overwrite
            paths = ["resources", "api_test.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/api/1/upload_file_to_form",
                {
                    "apikey": self.randonLoginKey,
                    "user_id": self.randonLogin,
                    "project_user": self.randonLogin,
                    "project_code": self.project,
                    "form_id": "Justtest",
                    "overwrite": "",
                },
                upload_files=[("file_to_upload", resource_file)],
                status=200,
            )

            # 404 for a get
            self.testapp.get(
                "/api/1/upload_file_to_form?apikey={}".format(self.randonLoginKey),
                status=404,
            )

        def test_plugin_utility_functions():
            self.testapp.get(
                "/test/{}".format(self.randonLogin),
                status=200,
            )
            self.testapp.get(
                "/test/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

        def test_collaborator_projects():
            # Create collaborator 1
            collaborator_1 = str(uuid.uuid4())
            collaborator_1_key = collaborator_1
            collaborator_1 = collaborator_1[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_1 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_1,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_1_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a project succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_1),
                {
                    "project_code": "collaborator_1_prj001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Create collaborator 2
            collaborator_2 = str(uuid.uuid4())
            collaborator_2_key = collaborator_2
            collaborator_2 = collaborator_2[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_2 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_2,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_2_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a project succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_2),
                {
                    "project_code": "collaborator_2_prj001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 1 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator 1 add Collaborator 2
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    collaborator_1, "collaborator_1_prj001"
                ),
                {"add_collaborator": "", "collaborator": collaborator_2},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Sets Collaborator 2 as Admin
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    collaborator_1, "collaborator_1_prj001"
                ),
                {
                    "change_role": "",
                    "collaborator_id": collaborator_2,
                    "role_collaborator": 2,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 2 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_2, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator remove itself as collaborator
            # Remove the collaborator
            res = self.testapp.post(
                "/user/{}/project/{}/collaborator/{}/remove".format(
                    collaborator_1, "collaborator_1_prj001", collaborator_2
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get("/user/{}".format(collaborator_2), status=200)
            assert "FS_error" not in res.headers

        def test_collaborator_projects_2():
            # Create collaborator 1
            collaborator_1 = str(uuid.uuid4())
            collaborator_1_key = collaborator_1
            collaborator_1 = collaborator_1[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_1 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_1,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_1_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a project succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_1),
                {
                    "project_code": "collaborator_1_prj001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Create collaborator 2
            collaborator_2 = str(uuid.uuid4())
            collaborator_2_key = collaborator_2
            collaborator_2 = collaborator_2[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_2 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_2,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_2_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 1 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator 1 add Collaborator 2
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    collaborator_1, "collaborator_1_prj001"
                ),
                {"add_collaborator": "", "collaborator": collaborator_2},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Sets Collaborator 2 as Admin
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    collaborator_1, "collaborator_1_prj001"
                ),
                {
                    "change_role": "",
                    "collaborator_id": collaborator_2,
                    "role_collaborator": 2,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 2 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_2, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator remove itself as collaborator
            # Remove the collaborator
            res = self.testapp.post(
                "/user/{}/project/{}/collaborator/{}/remove".format(
                    collaborator_1, "collaborator_1_prj001", collaborator_2
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get("/user/{}".format(collaborator_2), status=200)
            assert "FS_error" not in res.headers

        def test_collaborator_projects_3():
            # Create collaborator 1
            collaborator_1 = str(uuid.uuid4())
            collaborator_1_key = collaborator_1
            collaborator_1 = collaborator_1[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_1 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_1,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_1_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a project succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_1),
                {
                    "project_code": "collaborator_1_prj001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Create collaborator 2
            collaborator_2 = str(uuid.uuid4())
            collaborator_2_key = collaborator_2
            collaborator_2 = collaborator_2[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_2 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_2,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_2_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 1 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator 1 add Collaborator 2
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    collaborator_1, "collaborator_1_prj001"
                ),
                {"add_collaborator": "", "collaborator": collaborator_2},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 2 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_2, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 1 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator 1 removes collaborator 2
            # Remove the collaborator
            res = self.testapp.post(
                "/user/{}/project/{}/collaborator/{}/remove".format(
                    collaborator_1, "collaborator_1_prj001", collaborator_2
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 2 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_2, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get("/user/{}".format(collaborator_2), status=200)
            assert "FS_error" not in res.headers

        def test_collaborator_projects_4():
            # Create collaborator 1
            collaborator_1 = str(uuid.uuid4())
            collaborator_1_key = collaborator_1
            collaborator_1 = collaborator_1[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_1 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_1,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_1_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a project succeed.
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_1),
                {
                    "project_code": "collaborator_1_prj001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Create collaborator 2
            collaborator_2 = str(uuid.uuid4())
            collaborator_2_key = collaborator_2
            collaborator_2 = collaborator_2[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_2 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_2,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_2_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a project succeed to collaborator2.
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_2),
                {
                    "project_code": "collaborator_2_prj001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 1 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator 1 add Collaborator 2
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    collaborator_1, "collaborator_1_prj001"
                ),
                {"add_collaborator": "", "collaborator": collaborator_2},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 2 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_2, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Collaborator 2 add Collaborator 1
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    collaborator_2, "collaborator_2_prj001"
                ),
                {"add_collaborator": "", "collaborator": collaborator_1},
                status=302,
            )
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 1 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get("/user/{}".format(collaborator_1), status=200)
            assert "FS_error" not in res.headers

            self.testapp.get("/logout", status=302)

            # Collaborator 2 login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_2, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get("/user/{}".format(collaborator_2), status=200)
            assert "FS_error" not in res.headers

            time.sleep(5)  # Wait for elastic to finish adding the collaborator
            self.testapp.get(
                "/test/{}/remove".format(collaborator_2),
                status=200,
            )

            self.testapp.get("/logout", status=302)

        def test_delete_active_project():
            # Create collaborator 1
            collaborator_1 = str(uuid.uuid4())
            collaborator_1_key = collaborator_1
            collaborator_1 = collaborator_1[-12:]

            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_1 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_1,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_1_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a first project
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_1),
                {
                    "project_code": "collaborator_1_prj001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Add a second project
            res = self.testapp.post(
                "/user/{}/projects/add".format(collaborator_1),
                {
                    "project_code": "collaborator_1_prj002",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Delete a project
            res = self.testapp.post(
                "/user/{}/project/{}/delete".format(
                    collaborator_1, "collaborator_1_prj002"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Delete a project
            res = self.testapp.post(
                "/user/{}/project/{}/delete".format(
                    collaborator_1, "collaborator_1_prj001"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_form_access():

            # Assistant logout succeeds.
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/logout".format(
                    self.randonLogin, self.project
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Login succeed
            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.randonLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Adds a mimic2 project
            json2_project = "formaccess"
            json2_project_id = str(uuid.uuid4())
            mimic_res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": json2_project_id,
                    "project_code": json2_project,
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers
            # Add the mimic form
            mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
            resource_file = os.path.join(self.path, *mimic_paths)
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, json2_project),
                {"form_pkey": "I_D"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in mimic_res.headers
            json2_form = "LB_Sequia_MAG_20190123"

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads a file to the form
            paths = ["resources", "forms", "complex_form", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            access_assistant = str(uuid.uuid4())
            access_assistant = access_assistant[-12:]

            mimic_res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, json2_project
                ),
                {
                    "coll_id": access_assistant,
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Add an assistant to a form succeeds
            mimic_res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, json2_project, json2_form
                ),
                {
                    "coll_id": "{}|{}".format(json2_project_id, access_assistant),
                    "coll_privileges": "2",
                },
                status=302,
            )
            assert "FS_error" not in mimic_res.headers

            # Test getting the forms when the assistant does not have access
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, json2_project),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=access_assistant
                ),
            )

            # Upload submission fails assistant cannot submit
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=404,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=access_assistant
                ),
            )

            # Set form as inactive
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/deactivate".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Upload submission fails the form is inactive
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission001.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=404,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=access_assistant
                ),
            )

            # Set form as active
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/activate".format(
                    self.randonLogin, json2_project, json2_form
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Upload submission fails the form does not exists
            paths = [
                "resources",
                "forms",
                "complex_form",
                "submissions_logs2",
                "submission001_invalid.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=404,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=access_assistant
                ),
            )

            # Upload submission fails the upload does not have an xml file
            paths = ["resources", "api_test.dat"]
            submission_file = os.path.join(self.path, *paths)
            paths = ["resources", "forms", "complex_form", "image001.png"]
            image_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, json2_project),
                status=500,
                upload_files=[("filetoupload", submission_file), ("image", image_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing=access_assistant
                ),
            )

        def test_create_super_user():
            from formshare.scripts.createsuperuser import main as createsuperuser_main

            here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[
                0
            ]
            paths2 = ["development.ini"]
            ini_file = os.path.join(here, *paths2)

            random_admin = str(uuid.uuid4())
            random_admin = random_admin[-12:]
            res = createsuperuser_main(
                [
                    "--user_id",
                    random_admin,
                    "--user_email",
                    "info@qlandscom",
                    "--user_password",
                    "123",
                    ini_file,
                ]
            )
            assert res == 1
            res = createsuperuser_main(
                [
                    "--user_id",
                    random_admin,
                    "--user_email",
                    "{}@qlands.com".format(random_admin),
                    "--user_password",
                    "123",
                    ini_file,
                ]
            )
            assert res == 0
            res = createsuperuser_main(
                [
                    "--user_id",
                    random_admin,
                    "--user_email",
                    "{}@qlands.com".format(random_admin),
                    "--user_password",
                    "123",
                    ini_file,
                ]
            )
            assert res == 1
            random_admin2 = str(uuid.uuid4())
            random_admin2 = random_admin2[-12:]
            res = createsuperuser_main(
                [
                    "--user_id",
                    random_admin2,
                    "--user_email",
                    "{}@qlands.com".format(random_admin),
                    "--user_password",
                    "123",
                    ini_file,
                ]
            )
            assert res == 1

        def test_configure_alembic():
            from formshare.scripts.configurealembic import main as configurealembic_main
            from pathlib import Path

            here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[
                0
            ]
            paths2 = ["development.ini"]
            ini_file = os.path.join(here, *paths2)

            home = str(Path.home())
            paths2 = ["alembic.ini"]
            alembic_file = os.path.join(home, *paths2)

            res = configurealembic_main(["/not_exists", "/not_exists"])
            assert res == 1
            res = configurealembic_main([ini_file, "/not_exists"])
            assert res == 1
            res = configurealembic_main(
                ["--alembic_ini_file", alembic_file, ini_file, here]
            )
            assert res == 0
            assert os.path.exists(alembic_file)

        def test_configure_fluent():
            from formshare.scripts.configurefluent import main as configurefluent_main
            from pathlib import Path

            here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[
                0
            ]

            home = str(Path.home())
            paths2 = ["fluent.ini"]
            fluent_file = os.path.join(home, *paths2)

            res = configurefluent_main(
                [
                    "--formshare_path",
                    here,
                    "--formshare_log_file",
                    "log.ini",
                    "--elastic_search_host",
                    "localhost",
                    "--elastic_search_port",
                    "9200",
                    fluent_file,
                ]
            )
            assert res == 0
            assert os.path.exists(fluent_file)

        def test_configure_mysql():
            from formshare.scripts.configuremysql import main as configuremysql_main
            from pathlib import Path

            here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[
                0
            ]
            paths2 = ["development.ini"]
            ini_file = os.path.join(here, *paths2)

            home = str(Path.home())
            paths2 = ["mysql.cnf"]
            mysql_file = os.path.join(home, *paths2)

            res = configuremysql_main(["/not_exists", "/not_exists"])
            assert res == 1
            res = configuremysql_main([ini_file, "/not_exists"])
            assert res == 1
            res = configuremysql_main(["--mysql_cnf_file", mysql_file, ini_file, here])
            assert res == 0
            assert os.path.exists(mysql_file)

        def test_configure_tests():
            from formshare.scripts.configuretests import main as configuretests_main
            from pathlib import Path

            here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[
                0
            ]
            paths2 = ["development.ini"]
            ini_file = os.path.join(here, *paths2)

            home = str(Path.home())
            paths2 = ["test_config.json"]
            json_file = os.path.join(home, *paths2)

            res = configuretests_main(["/not_exists", "/not_exists"])
            assert res == 1
            res = configuretests_main([ini_file, "/not_exists"])
            assert res == 1
            res = configuretests_main(["--json_file", json_file, ini_file, here])
            assert res == 0
            assert os.path.exists(json_file)

        def test_modify_config():
            from formshare.scripts.modifyconfig import main as modifyconfig_main
            from pathlib import Path

            here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[
                0
            ]
            paths2 = ["development.ini"]
            ini_file = os.path.join(here, *paths2)

            home = str(Path.home())
            paths2 = ["development.ini"]
            target_file = os.path.join(home, *paths2)
            shutil.copyfile(ini_file, target_file)

            res = modifyconfig_main(
                [
                    "--ini_file",
                    target_file,
                    "--action",
                    "SET",
                    "--value",
                    "123",
                    "--section",
                    "app:formshare",
                    "--key",
                    "test",
                ]
            )
            assert res == 1

            res = modifyconfig_main(
                [
                    "--ini_file",
                    target_file,
                    "--action",
                    "ADD",
                    "--section",
                    "app:formshare",
                    "--key",
                    "test",
                ]
            )
            assert res == 1

            res = modifyconfig_main(
                [
                    "--ini_file",
                    "/not_found.ini",
                    "--action",
                    "ADD",
                    "--value",
                    "123",
                    "--section",
                    "app:formshare",
                    "--key",
                    "test",
                ]
            )
            assert res == 1

            res = modifyconfig_main(
                [
                    "--ini_file",
                    target_file,
                    "--action",
                    "ADD",
                    "--value",
                    "123",
                    "--section",
                    "notExist",
                    "--key",
                    "test",
                ]
            )
            assert res == 1

            res = modifyconfig_main(
                [
                    "--ini_file",
                    target_file,
                    "--action",
                    "ADD",
                    "--value",
                    "123",
                    "--section",
                    "app:formshare",
                    "--key",
                    "test",
                ]
            )
            assert res == 0

            res = modifyconfig_main(
                [
                    "--ini_file",
                    target_file,
                    "--action",
                    "REMOVE",
                    "--section",
                    "app:formshare",
                    "--key",
                    "test",
                ]
            )
            assert res == 0

        def test_unauthorized_access():

            # Collaborator groups ----------------------------------------

            # The assistant group does not exist
            self.testapp.get(
                "/user/{}/project/{}/groups".format(self.randonLogin, "NotExist"),
                status=404,
            )

            # Show the add group page does not exist
            self.testapp.get(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, "NotExist"),
                status=404,
            )

            # Edits a group of a project that does not exist
            self.testapp.get(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, "NotExist", "NotExist"
                ),
                status=404,
            )

            # Delete a group of a project that does not exist
            self.testapp.post(
                "/user/{}/project/{}/group/{}/delete".format(
                    self.randonLogin, "NotExist", "NotExist"
                ),
                status=404,
            )

            # List members of a project that does not exists
            self.testapp.get(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, "NotExist", "NotExist"
                ),
                status=404,
            )

            # Add a member of a project that does not exists
            self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, "NotExist", "NotExist"
                ),
                status=404,
            )

            # Remove a member of a project that does not exist
            self.testapp.post(
                "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
                    self.randonLogin,
                    "NotExist",
                    self.assistantGroupID,
                    self.assistantLogin,
                    self.projectID,
                ),
                status=404,
            )

            collaborator_1 = str(uuid.uuid4())
            collaborator_1_key = collaborator_1
            collaborator_1 = collaborator_1[-12:]

            # Add a new collaborator
            res = self.testapp.post(
                "/join",
                {
                    "user_address": "Costa Rica",
                    "user_email": collaborator_1 + "@qlands.com",
                    "user_password": "123",
                    "user_id": collaborator_1,
                    "user_password2": "123",
                    "user_name": "Testing",
                    "user_super": "1",
                    "user_apikey": collaborator_1_key,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # The user don't have access to such project
            self.testapp.get(
                "/user/{}/project/{}/groups".format(self.randonLogin, self.project),
                status=404,
            )

            # The user don't have access to the collaborators
            self.testapp.get(
                "/user/{}/project/{}/assistants".format(self.randonLogin, self.project),
                status=404,
            )

            # The user don't have access to add collaborators
            self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=404,
            )

            # 404 cannot access the project
            self.testapp.get(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=404,
            )

            # 404 no access to project
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/delete".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=404,
            )

            # 404 not access to project
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "123"},
                status=404,
            )

            # The user don't have access to add a group in project project
            self.testapp.get(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                status=404,
            )

            # Get the assistant groups in edit mode
            self.testapp.get(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, "NotExist"
                ),
                status=404,
            )

            # Delete a group of a project that does not have access
            self.testapp.post(
                "/user/{}/project/{}/group/{}/delete".format(
                    self.randonLogin, self.project, "NotExist"
                ),
                status=404,
            )

            # List members of a project that does not have access
            self.testapp.get(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, "NotExist"
                ),
                status=404,
            )

            # Add a member of a project that does not have access
            self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, "NotExist"
                ),
                status=404,
            )

            # Remove a member of a project that does not have access
            self.testapp.post(
                "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
                    self.randonLogin,
                    self.project,
                    self.assistantGroupID,
                    self.assistantLogin,
                    self.projectID,
                ),
                status=404,
            )

            # The collaborator logs out
            self.testapp.get("/logout", status=302)

            # Main user login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.randonLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Main user add collaborator as member
            res = self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": collaborator_1},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Main user logs out
            self.testapp.get("/logout", status=302)

            # Collaborator logs in
            res = self.testapp.post(
                "/login",
                {"user": "", "email": collaborator_1, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # The user don't have access to add a group in project project
            self.testapp.get(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                status=404,
            )

            # The user don have credentials for looking at assistants
            self.testapp.get(
                "/user/{}/project/{}/assistants".format(self.randonLogin, self.project),
                status=404,
            )

            # 404 Not credentials to add
            self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {
                    "coll_id": "assistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=404,
            )

            # 404 Not credentials to edit
            self.testapp.get(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=404,
            )

            # No credentials to remove
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/delete".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=404,
            )

            # No credentials to change password
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "123"},
                status=404,
            )

            # Get the assistant groups in edit mode
            self.testapp.get(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, "NotExist"
                ),
                status=404,
            )

            # Delete a group of a project that does not have grants
            self.testapp.post(
                "/user/{}/project/{}/group/{}/delete".format(
                    self.randonLogin, self.project, "NotExist"
                ),
                status=404,
            )

            # Remove a member of a project that does not have grants
            self.testapp.post(
                "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
                    self.randonLogin,
                    self.project,
                    self.assistantGroupID,
                    self.assistantLogin,
                    self.projectID,
                ),
                status=404,
            )

            # --------------Finally ----------------
            # New collaborator logout
            self.testapp.get("/logout", status=302)

            # Main user login
            res = self.testapp.post(
                "/login",
                {"user": "", "email": self.randonLogin, "passwd": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

        def test_case_management():
            # Add a project succeed.
            case_project_id = str(uuid.uuid4())
            res = self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": case_project_id,
                    "project_code": "case001",
                    "project_name": "Case project 001",
                    "project_abstract": "",
                    "project_case": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the project list
            res = self.testapp.get(
                "/user/{}/projects".format(self.randonLogin), status=200
            )
            assert "FS_error" not in res.headers
            self.assertIn(b"longitudinal workflow", res.body)

            # Gets the details of a project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, "case001"), status=200
            )
            assert "FS_error" not in res.headers
            self.assertIn(
                b"Which variable will be used to identify each case", res.body
            )

            # Edit a project. Get details
            res = self.testapp.get(
                "/user/{}/project/{}/edit".format(self.randonLogin, "case001"),
                status=200,
            )
            assert "FS_error" not in res.headers
            self.assertNotIn(b"Read-only because the project has forms", res.body)

            res = self.testapp.post(
                "/user/{}/project/{}/edit".format(self.randonLogin, "case001"),
                {
                    "project_name": "Case project 001",
                    "project_abstract": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/edit".format(self.randonLogin, "case001"),
                {
                    "project_name": "Case project 001",
                    "project_abstract": "",
                    "project_case": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, "case001"
                ),
                {
                    "coll_id": "caseassistant001",
                    "coll_password": "123",
                    "coll_password2": "123",
                    "coll_prjshare": 1,
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Upload a case creator fails. Invalid case key
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {"form_pkey": "test", "form_caselabel": "test"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case creator fails. Invalid case label
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {"form_pkey": "hid", "form_caselabel": "test"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case creator fails. Case label is empty
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {"form_pkey": "hid", "form_caselabel": ""},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case creator fails. Case label and key are the same
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {"form_pkey": "hid", "form_caselabel": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case creator pass.
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {"form_pkey": "hid", "form_caselabel": "fname"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                status=200,
            )
            self.assertIn(b"Case creator", res.body)

            # Edit a project. Get details. Cannot change project type
            res = self.testapp.get(
                "/user/{}/project/{}/edit".format(self.randonLogin, "case001"),
                status=200,
            )
            assert "FS_error" not in res.headers
            self.assertIn(b"Read-only because the project has forms", res.body)

            # Gets the details of a project. Upload Forms are inactive at the moment
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, "case001"), status=200
            )
            assert "FS_error" not in res.headers
            self.assertIn(
                b"You cannot add new forms while you have a case creator", res.body
            )

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {
                    "coll_id": "{}|{}".format(case_project_id, "caseassistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Uploads cantones
            paths = ["resources", "forms", "case", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads distritos
            paths = ["resources", "forms", "case", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Update a form fails. Invalid primary key variable
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {"form_pkey": "test", "form_caselabel": "test"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Invalid case label variable
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {"form_pkey": "hid", "form_caselabel": "test"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. label variable empty
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {"form_pkey": "hid", "form_caselabel": ""},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. label variable and key are the same
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {"form_pkey": "hid", "form_caselabel": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form pass
            paths = ["resources", "forms", "case", "case_start.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {"form_pkey": "hid", "form_caselabel": "fname"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Creates the repository of the case creator
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {
                    "form_pkey": "hid",
                    "start_stage1": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers
            time.sleep(40)  # Wait for the repository to finish

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                status=200,
            )
            self.assertIn(b"Case creator", res.body)
            self.assertIn(b"With repository", res.body)

            # Get details of the project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, "case001"),
                status=200,
            )
            assert "FS_error" not in res.headers
            self.assertIn(b"case lookup table", res.body)
            self.assertIn(b"Create the case lookup table before", res.body)

            # Open the case lookup table
            res = self.testapp.get(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Get details of the project
            res = self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, "case001"),
                status=200,
            )
            assert "FS_error" not in res.headers
            self.assertIn(b"case lookup table", res.body)
            self.assertNotIn(b"Create the case lookup table before", res.body)

            # Adds the field distrito
            res = self.testapp.post(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                {
                    "add_field": "",
                    "field_name": "distrito",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Removes the field distrito
            res = self.testapp.post(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                {
                    "remove_field": "",
                    "field_name": "distrito",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Change alias of distrito
            res = self.testapp.post(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                {
                    "change_alias": "",
                    "field_name": "distrito",
                    "field_alias": "distrito_id",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Change alias of distrito fails invalid character
            res = self.testapp.post(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                {
                    "change_alias": "",
                    "field_name": "distrito",
                    "field_alias": "distrito id",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Change alias of distrito fails invalid name
            res = self.testapp.post(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                {
                    "change_alias": "",
                    "field_name": "distrito",
                    "field_alias": "select",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Change alias of distrito fails numeric
            res = self.testapp.post(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                {
                    "change_alias": "",
                    "field_name": "distrito",
                    "field_alias": "123",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Change alias of distrito fails already exist
            res = self.testapp.post(
                "/user/{}/project/{}/caselookuptable".format(
                    self.randonLogin, "case001"
                ),
                {
                    "change_alias": "",
                    "field_name": "distrito",
                    "field_alias": "label",
                },
                status=200,
            )
            assert "FS_error" in res.headers

            # Upload a case follow up. Invalid case type not given
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {"form_pkey": "survey_id", "form_caseselector": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case follow up. Invalid pkey
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {"form_pkey": "test", "form_caseselector": "hid", "form_casetype": "2"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case follow up. Empty case selector
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case follow up. Invalid case selector
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "test",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case follow up. case selector and primary key are the same
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "survey_id",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a case follow up pass
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "hid",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {
                    "coll_id": "{}|{}".format(case_project_id, "caseassistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Uploads cantones
            paths = ["resources", "forms", "case", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads distritos
            paths = ["resources", "forms", "case", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads households
            paths = ["resources", "forms", "case", "households.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=200,
            )
            self.assertIn(b"Linked to case lookup table", res.body)

            # Get the FormList. Empty list
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, "case001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Upload case 001
            paths = [
                "resources",
                "forms",
                "case",
                "data",
                "start_01.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Get the FormList. households.csv is created
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, "case001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            self.testapp.get(
                "/user/{}/project/{}/{}/manifest/mediafile/households.csv".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            self.testapp.get(
                "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Get the FormList. household.csv is not created
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, "case001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            self.testapp.get(
                "/user/{}/project/{}/{}/manifest/mediafile/households.csv".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            self.testapp.get(
                "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Update a form fails. Invalid primary key variable
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {"form_pkey": "test", "form_caseselector": "hid", "form_casetype": "2"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. Invalid case selector variable
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "test",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form fails. No case case type
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {"form_pkey": "survey_id", "form_caseselector": "hid"},
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form. Empty case selector
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form. Case selector and primary key are the same
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "survey_id",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Update a form pass
            paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "hid",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Upload case 002
            paths = [
                "resources",
                "forms",
                "case",
                "data",
                "start_02.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                status=200,
            )
            self.assertIn(b"[Clean data]", res.body)
            self.assertNotIn(b"[Manage errors]", res.body)

            # Creates the repository of the case follow up
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                {
                    "form_pkey": "survey_id",
                    "start_stage1": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers
            time.sleep(40)  # Wait for the repository to finish

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=200,
            )
            self.assertIn(b"With repository", res.body)

            # Get the FormList. household.csv is created
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, "case001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Upload follow up 001
            paths = [
                "resources",
                "forms",
                "case",
                "data",
                "follow_01.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Upload follow up 002
            paths = [
                "resources",
                "forms",
                "case",
                "data",
                "follow_02.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_follow_up_20210319"
                ),
                status=200,
            )
            self.assertIn(b"[Clean data]", res.body)
            self.assertNotIn(b"[Manage errors]", res.body)

            # Upload a case deactivate pass
            paths = ["resources", "forms", "case", "case_deactivate.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "hid",
                    "form_casetype": "3",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                {
                    "coll_id": "{}|{}".format(case_project_id, "caseassistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Uploads cantones
            paths = ["resources", "forms", "case", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads distritos
            paths = ["resources", "forms", "case", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads households
            paths = ["resources", "forms", "case", "households.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                status=200,
            )
            self.assertIn(b"Linked to case lookup table", res.body)

            # Creates the repository of the case creator
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                {
                    "form_pkey": "survey_id",
                    "start_stage1": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers
            time.sleep(40)  # Wait for the repository to finish

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                status=200,
            )
            self.assertIn(b"With repository", res.body)

            # Deactivate case 001
            paths = [
                "resources",
                "forms",
                "case",
                "data",
                "deact_01.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                status=200,
            )
            self.assertIn(b"[Clean data]", res.body)
            self.assertNotIn(b"[Manage errors]", res.body)

            creator_details = get_form_details(
                self.server_config, case_project_id, "case_start_20210311"
            )
            creator_schema = creator_details["form_schema"]
            engine = create_engine(self.server_config["sqlalchemy.url"])
            res = engine.execute(
                "SELECT _active FROM {}.maintable WHERE hid = '{}'".format(
                    creator_schema, "001"
                )
            ).first()
            current_status = res[0]
            engine.dispose()
            assert current_status == 0

            # Get the FormList. household.csv is created
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, "case001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Upload a case activate pass
            paths = ["resources", "forms", "case", "case_activate.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "hid",
                    "form_casetype": "4",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                {
                    "coll_id": "{}|{}".format(case_project_id, "caseassistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Uploads cantones
            paths = ["resources", "forms", "case", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads distritos
            paths = ["resources", "forms", "case", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads households
            paths = ["resources", "forms", "case", "households.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                status=200,
            )
            self.assertIn(b"Linked to case lookup table", res.body)

            # Creates the repository of the case creator
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                {
                    "form_pkey": "survey_id",
                    "start_stage1": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers
            time.sleep(40)  # Wait for the repository to finish

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                status=200,
            )
            self.assertIn(b"With repository", res.body)

            # Activate case 001
            paths = [
                "resources",
                "forms",
                "case",
                "data",
                "activ_01.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_activate_20210331"
                ),
                status=200,
            )
            self.assertIn(b"[Clean data]", res.body)
            self.assertNotIn(b"[Manage errors]", res.body)

            creator_details = get_form_details(
                self.server_config, case_project_id, "case_start_20210311"
            )
            creator_schema = creator_details["form_schema"]
            engine = create_engine(self.server_config["sqlalchemy.url"])
            res = engine.execute(
                "SELECT _active FROM {}.maintable WHERE hid = '{}'".format(
                    creator_schema, "001"
                )
            ).first()
            current_status = res[0]
            engine.dispose()
            assert current_status == 1

            # Get the FormList. household.csv is created
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, "case001"),
                status=200,
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            # Check merging a case creator

            paths = ["resources", "forms", "case", "merge", "case_start.xlsx"]
            b_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                {
                    "for_merging": "",
                    "parent_project": case_project_id,
                    "parent_form": "case_start_20210311",
                },
                status=302,
                upload_files=[("xlsx", b_resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, "case001", "case_start_20210331"
                ),
                {
                    "coll_id": "{}|{}".format(case_project_id, "caseassistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210331"
                ),
                status=200,
            )
            self.assertTrue(b"Merge check pending" in res.body)

            # Uploads cantones
            paths = ["resources", "forms", "case", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_start_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads distritos
            paths = ["resources", "forms", "case", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_start_20210331"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210331"
                ),
                status=200,
            )
            self.assertFalse(b"Merge check pending" in res.body)

            # Show the merge repository page
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    "case001",
                    "case_start_20210331",
                    "case_start_20210311",
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Merge the new creator using Celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    "case001",
                    "case_start_20210331",
                    "case_start_20210311",
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for the merge to finish

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210331"
                ),
                status=200,
            )
            self.assertTrue(b"This is the sub-version of" in res.body)

            # Get the details of a form tormenta20201105
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210311"
                ),
                status=200,
            )
            self.assertTrue(b"is the sub-version of this form" in res.body)

            # Upload case 003
            paths = [
                "resources",
                "forms",
                "case",
                "merge",
                "data",
                "start_03.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_start_20210331"
                ),
                status=200,
            )
            self.assertIn(b"[Clean data]", res.body)
            self.assertNotIn(b"[Manage errors]", res.body)

            # Deactivate case 003
            paths = [
                "resources",
                "forms",
                "case",
                "data",
                "deact_03.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            res = engine.execute(
                "SELECT _active FROM {}.maintable WHERE hid = '{}'".format(
                    creator_schema, "003"
                )
            ).first()
            current_status = res[0]
            engine.dispose()
            assert current_status == 0

            # Check merging a case deactivate

            paths = ["resources", "forms", "case", "merge", "case_deactivate.xlsx"]
            b_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                {
                    "for_merging": "",
                    "parent_project": case_project_id,
                    "parent_form": "case_deactivate_20210331",
                },
                status=302,
                upload_files=[("xlsx", b_resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, "case001", "case_deactivate_20210401"
                ),
                {
                    "coll_id": "{}|{}".format(case_project_id, "caseassistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_deactivate_20210401"
                ),
                status=200,
            )
            self.assertTrue(b"Merge check pending" in res.body)

            # Uploads cantones
            paths = ["resources", "forms", "case", "cantones.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_deactivate_20210401"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads distritos
            paths = ["resources", "forms", "case", "distritos.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_deactivate_20210401"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Uploads households
            paths = ["resources", "forms", "case", "households.csv"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "case001", "case_deactivate_20210401"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )
            assert "FS_error" not in res.headers

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_deactivate_20210401"
                ),
                status=200,
            )
            self.assertFalse(b"Merge check pending" in res.body)
            self.assertIn(b"Linked to case lookup table", res.body)

            # Show the merge repository page
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    "case001",
                    "case_deactivate_20210401",
                    "case_deactivate_20210331",
                ),
                status=200,
            )
            assert "FS_error" not in res.headers

            # Merge the new creator using Celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/merge/into/{}".format(
                    self.randonLogin,
                    "case001",
                    "case_deactivate_20210401",
                    "case_deactivate_20210331",
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(60)  # Wait for the merge to finish

            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_deactivate_20210401"
                ),
                status=200,
            )
            self.assertTrue(b"This is the sub-version of" in res.body)

            # Get the details of a form tormenta20201105
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_deactivate_20210331"
                ),
                status=200,
            )
            self.assertTrue(b"is the sub-version of this form" in res.body)

            # Deactivate case 002 using the merged form
            paths = [
                "resources",
                "forms",
                "case",
                "merge",
                "data",
                "deact_02.xml",
            ]
            submission_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/push".format(self.randonLogin, "case001"),
                status=201,
                upload_files=[("filetoupload", submission_file)],
                extra_environ=dict(
                    FS_for_testing="true", FS_user_for_testing="caseassistant001"
                ),
            )

            res = engine.execute(
                "SELECT _active FROM {}.maintable WHERE hid = '{}'".format(
                    creator_schema, "002"
                )
            ).first()
            current_status = res[0]
            engine.dispose()
            assert current_status == 0

            # Upload a case follow up barcode passes.
            paths = ["resources", "forms", "case", "case_follow_up_barcode.xlsx"]
            resource_file = os.path.join(self.path, *paths)
            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, "case001"),
                {
                    "form_pkey": "survey_id",
                    "form_caseselector": "hid",
                    "form_casetype": "2",
                },
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Add an assistant to a form succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(
                    self.randonLogin, "case001", "case_follow_up_barcode_20210428"
                ),
                {
                    "coll_id": "{}|{}".format(case_project_id, "caseassistant001"),
                    "coll_privileges": "1",
                },
                status=302,
            )
            assert "FS_error" not in res.headers

            # Creates the repository of the case follow up
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, "case001", "case_follow_up_barcode_20210428"
                ),
                {
                    "form_pkey": "survey_id",
                    "start_stage1": "",
                },
                status=302,
            )
            assert "FS_error" not in res.headers
            time.sleep(40)  # Wait for the repository to finish

            # Get the details of the form
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, "case001", "case_follow_up_barcode_20210428"
                ),
                status=200,
            )
            self.assertIn(b"With repository", res.body)

        start_time = datetime.datetime.now()
        test_root()
        test_login()
        test_dashboard()
        test_profile()
        test_projects()
        test_collaborators()
        test_assistants()
        test_assistant_groups()
        test_forms()
        test_odk()
        test_multilanguage_odk()
        test_support_zip_file()
        test_external_select()
        test_update_form_missing_files()
        test_repository()
        test_repository_downloads()
        time.sleep(60)
        test_import_data()
        test_assistant_access()
        test_json_logs()
        test_json_logs_2()
        test_json_logs_3()
        test_json_logs_4()
        test_clean_interface()
        test_clean_interface_unauthorized()
        test_audit()
        test_repository_tasks()
        test_collaborator_access()
        test_helpers()
        test_utility_functions()
        test_avatar_generator()
        test_color_hash_hex()
        test_one_user_assistant()
        test_five_collaborators()
        test_form_merge()
        test_form_merge_mimic()
        test_form_merge_mimic2()
        test_form_merge_mimic3()
        test_group_assistant()
        test_delete_form_with_repository()
        test_api()
        test_plugin_utility_functions()
        test_collaborator_projects()
        test_collaborator_projects_2()
        test_collaborator_projects_3()
        test_collaborator_projects_4()
        test_delete_active_project()
        test_form_access()
        test_create_super_user()
        test_configure_alembic()
        test_configure_fluent()
        test_configure_mysql()
        test_configure_tests()
        test_modify_config()
        test_unauthorized_access()
        test_case_management()

        end_time = datetime.datetime.now()
        time_delta = end_time - start_time
        total_seconds = time_delta.total_seconds()
        minutes = total_seconds / 60
        print("Finished in {} minutes".format(minutes))
