import unittest
import time
import uuid
import os

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
        self.project = ""
        self.projectID = ""
        self.assistantLogin = ""
        self.assistantGroupID = ""
        self.path = os.path.dirname(os.path.abspath(__file__))

    def test_all(self):
        def test_root():
            # Test the root urls
            self.testapp.get("/", status=200)
            self.testapp.get("/login", status=200)
            self.testapp.get("/join", status=200)
            self.testapp.get("/not_found", status=404)

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
                },
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
                    "user_apikey": "newkey",
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
            res = self.testapp.get("/user/{}/profile".format(self.randonLogin), status=200)
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
            res = self.testapp.get("/user/{}/projects".format(self.randonLogin), status=200)
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
            # TODO: This has to be done twice later on for project with GPS points with and without repository
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

            # TODO: We need to test accept and declined collaboration.
            #  This need to logout and login with the collaborator

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
            res = self.testapp.get("/user/{}/profile".format(self.randonLogin), status=200)
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
            # TODO: We need to update a form when is a subversion

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
            # TODO: Delete a form with our without schema. Delete when merged

            # Upload the form again
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "FS_error" not in res.headers

            # TODO: Test form_sse
            # TODO: Test stop_task
            # TODO: Test stop_repository

            # Set form as inactive
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/deactivate".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            assert "FS_error" not in res.headers

            # TODO: Test import_data

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
                {"coll_id": "{}|{}".format(self.projectID, self.assistantLogin), "privilege": "1"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Edit an assistant
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
                    self.randonLogin, self.project, "Justtest", self.projectID, self.assistantLogin
                ),
                {"privilege": "3"},
                status=302,
            )
            assert "FS_error" not in res.headers

            # Remove the assistant
            res = self.testapp.post(
                "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
                    self.randonLogin, self.project, "Justtest", self.projectID, self.assistantLogin
                ),
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
