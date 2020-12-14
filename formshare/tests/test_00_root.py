import datetime
import json
import os
import shutil
import time
import unittest
import uuid

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
        "SELECT form_directory,form_schema,form_reptask,form_createxmlfile,form_insertxmlfile "
        "FROM odkform WHERE project_id = '{}' AND form_id = '{}'".format(project, form)
    ).fetchone()
    result = {
        "form_directory": result[0],
        "form_schema": result[1],
        "form_reptask": result[2],
        "form_createxmlfile": result[3],
        "form_insertxmlfile": result[4],
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
        from formshare.tests.config import server_config
        from formshare import main

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

        def test_dashboard():
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

            # Change assistant succeeds
            res = self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "123"},
                status=302,
            )
            assert "FS_error" not in res.headers

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

            # Delete the assistant
            res = self.testapp.post(
                "/user/{}/project/{}/group/{}/delete".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

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

        def test_forms():
            # Uploads a form fails. PyXForm conversion fails
            paths = ["resources", "forms", "form01.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Invalid ID
            paths = ["resources", "forms", "form02.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Invalid field name
            paths = ["resources", "forms", "form03.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Duplicated choices
            paths = ["resources", "forms", "form04.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Duplicated variables
            paths = ["resources", "forms", "form05.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Uploads a form fails. Duplicated options
            paths = ["resources", "forms", "form06.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a form fails. Too many selects
            paths = ["resources", "forms", "form07.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" in res.headers

            # Upload a form a succeeds
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # Upload a form fails. The form already exists
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
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

            # Update a form fails. The form is not the same
            paths = ["resources", "forms", "form09.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/updateodk".format(
                    self.randonLogin, self.project, "Justtest"
                ),
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

        def test_multilanguage_odk():
            # Upload a multi-language form succeeds
            paths = ["resources", "forms", "multi_language", "spanish_english.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
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

        def test_odk():

            # Upload a complex form succeeds
            paths = ["resources", "forms", "complex_form", "B.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            self.formID = "LB_Sequia_MAG_20190123"

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

            # Test getting the forms. Ask for credential
            self.testapp.get(
                "/user/{}/project/{}/formList".format(self.randonLogin, self.project),
                status=401,
            )

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
            paths = ["resources", "forms", "complex_form", "submission001.xml"]
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

        def test_repository():
            def mimic_create_repository_metalanguages():
                from formshare.products.repository.celery_task import (
                    create_mysql_repository,
                )

                form_details = get_form_details(
                    self.server_config, self.projectID, self.formMultiLanguageID
                )
                form_directory = form_details["form_directory"]
                form_reptask = form_details["form_reptask"]

                form_schema = "FS" + str(uuid.uuid4()).replace("-", "_")

                paths2 = [self.server_config["repository.path"], "odk"]
                odk_dir = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "create.sql",
                ]
                create_sql = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "insert.sql",
                ]
                insert_sql = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "create.xml",
                ]
                create_xml = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "insert.xml",
                ]
                insert_xml = os.path.join(self.path, *paths2)

                here = os.path.dirname(os.path.abspath(__file__)).split(
                    "/formshare/tests"
                )[0]
                paths2 = ["mysql.cnf"]
                mysql_cnf = os.path.join(here, *paths2)
                create_mysql_repository(
                    self.server_config,
                    self.randonLogin,
                    self.projectID,
                    self.project,
                    self.formMultiLanguageID,
                    odk_dir,
                    form_directory,
                    form_schema,
                    "QID",
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

            def mimic_create_repository():
                from formshare.products.repository.celery_task import (
                    create_mysql_repository,
                )

                form_details = get_form_details(
                    self.server_config, self.projectID, self.formID
                )
                form_directory = form_details["form_directory"]
                form_reptask = form_details["form_reptask"]

                form_schema = "FS" + str(uuid.uuid4()).replace("-", "_")

                paths2 = [self.server_config["repository.path"], "odk"]
                odk_dir = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "create.sql",
                ]
                create_sql = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "insert.sql",
                ]
                insert_sql = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "create.xml",
                ]
                create_xml = os.path.join(self.path, *paths2)

                paths2 = [
                    self.server_config["repository.path"],
                    "odk",
                    "forms",
                    form_directory,
                    "repository",
                    "insert.xml",
                ]
                insert_xml = os.path.join(self.path, *paths2)

                here = os.path.dirname(os.path.abspath(__file__)).split(
                    "/formshare/tests"
                )[0]
                paths2 = ["mysql.cnf"]
                mysql_cnf = os.path.join(here, *paths2)
                create_mysql_repository(
                    self.server_config,
                    self.randonLogin,
                    self.projectID,
                    self.project,
                    self.formID,
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
            time.sleep(2.5)
            get_repository_task(self.server_config, self.projectID, self.formID)

            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/stoprepository".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Generate the repository using celery
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/repository/create".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"form_pkey": "I_D", "start_stage1": ""},
                status=302,
            )
            assert "FS_error" not in res.headers

            time.sleep(40)  # Wait for Celery to finish

            # Mimic to create the repository again
            mimic_create_repository()
            mimic_create_repository_metalanguages()

            # Get the details of a form. The form now should have a repository
            res = self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )
            self.assertTrue(b"With repository" in res.body)

            # Test submission storing into repository
            paths = ["resources", "forms", "complex_form", "submission001.xml"]
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

            # Test submitting the same data into the repository storing it into the logs
            paths = ["resources", "forms", "complex_form", "submission001.xml"]
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
            paths = ["resources", "forms", "complex_form", "submission002.xml"]
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

        def test_repository_downloads():
            def mimic_celery_public_csv_process():
                from formshare.products.export.csv.celery_task import build_csv

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
                        "/home/cquiros/{}.csv".format(task_id),
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
                build_csv(
                    self.server_config,
                    maps_directory,
                    create_xml_file,
                    insert_xml_file,
                    form_schema,
                    "/home/cquiros/{}.csv".format(task_id),
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
                from formshare.products.export.csv.celery_task import build_csv

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
                        "/home/cquiros/{}.csv".format(task_id),
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
                build_csv(
                    self.server_config,
                    maps_directory,
                    create_xml_file,
                    insert_xml_file,
                    form_schema,
                    "/home/cquiros/{}.csv".format(task_id),
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
                from formshare.products.export.xlsx.celery_task import build_xlsx

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
                        "/home/cquiros/{}.xlsx".format(task_id),
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
                build_xlsx(
                    self.server_config,
                    self.server_config["repository.path"] + "/odk",
                    form_directory,
                    form_schema,
                    self.formID,
                    create_xml_file,
                    insert_xml_file,
                    "/home/cquiros/{}.xlsx".format(task_id),
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
                from formshare.products.export.kml.celery_task import build_kml

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
                        "/home/cquiros/{}.kml".format(task_id),
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
                build_kml(
                    self.server_config,
                    form_schema,
                    "/home/cquiros/{}.kml".format(task_id),
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
                        "kml_export",
                        task_id[-12:],
                    ),
                    status=200,
                )

            def mimic_celery_media_process():
                from formshare.products.export.media.celery_task import build_media_zip

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
                        "/home/cquiros/{}.zip".format(task_id),
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
                build_media_zip(
                    self.server_config,
                    self.server_config["repository.path"] + "/odk",
                    [form_directory],
                    form_schema,
                    "/home/cquiros/{}.zip".format(task_id),
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

            time.sleep(10)  # Wait 5 seconds so celery finished this

            # Get the details of a form. The form now should have a repository with products
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, self.formID
                ),
                status=200,
            )

            mimic_celery_public_csv_process()
            mimic_celery_private_csv_process()
            mimic_celery_xlsx_process()
            mimic_celery_kml_process()
            mimic_celery_media_process()

        def test_import_data():
            def mimic_celery_test_import():
                from formshare.products.fs1import.celery_task import import_json_files

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
                    "files",
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
                        "files",
                        "file1.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files",
                        "tmp",
                        "file1.json",
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
                        "files",
                        "file2.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files",
                        "tmp",
                        "file2.json",
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
                        "files",
                        "file3.json",
                    ]
                )
                file_to_import_target = os.path.join(
                    self.path,
                    *[
                        "resources",
                        "forms",
                        "complex_form",
                        "for_import",
                        "files",
                        "tmp",
                        "file3.json",
                    ]
                )
                shutil.copyfile(file_to_import, file_to_import_target)

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

                import_json_files(
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
                    True,
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
            res = engine.execute(
                "SELECT surveyid FROM {}.maintable WHERE i_d = '501890386'".format(
                    form_details["form_schema"]
                )
            ).first()
            survey_id = res[0]

            res = engine.execute(
                "SELECT submission_id FROM formshare.submission "
                "WHERE submission_status = 2 AND project_id = '{}'".format(
                    self.projectID
                )
            ).first()
            duplicated_id = res[0]

            engine.dispose()

            # Load compare submission
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=200,
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

            # Disregard passes
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the disregarded
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"status": "disregarded"},
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

            # Cancel disregard passes
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the disregard"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Checkout the submission
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Get the checkout
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                    self.randonLogin, self.project, self.formID
                ),
                {"status": "checkout"},
                status=200,
            )

            # Cancels the checkout
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # Checkout the submission again
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

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
            ] = "501890387B2"
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
                status=200,
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
            ] = "501890387B2"
            paths = ["tmp", duplicated_id + ".json"]
            submission_file = os.path.join(self.path, *paths)

            with open(submission_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # Checkin the file again
            res = self.testapp.post(
                "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                    self.randonLogin, self.project, self.formID, duplicated_id
                ),
                {"notes": "Some notes about the checkin", "sequence": "23a243c95548"},
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
                    "23a243c95548",
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

        def test_clean_interface():
            # Load the clean page
            self.testapp.get(
                "/user/{}/project/{}/assistantaccess/form/{}/clean".format(
                    self.randonLogin, self.project, self.formID
                ),
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

            print("********************************999")
            print(self.assistantLoginKey)
            print("********************************---")
            print(row_uuid)
            print("***********************************")
            print("{}-{}{}".format(self.randonLogin, self.project, self.formID))
            print("********************************999")
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

            time.sleep(10)  # Wait for celery to generate the repository

            # TODO: We need to test forms that cannot merge for different reasons

            # Upload B***********************************************

            paths = ["resources", "forms", "merge", "B", "B.xls"]
            b_resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
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
        test_repository()
        test_repository_downloads()
        test_import_data()
        test_assistant_access()
        test_json_logs()
        test_clean_interface()
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
