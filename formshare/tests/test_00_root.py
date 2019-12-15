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

            random_login = str(uuid.uuid4())
            random_login = random_login[-12:]

            #  random_login = "formshare"
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

            random_login = str(uuid.uuid4())
            random_login = random_login[-12:]
            # random_login = "collaborator"
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

            # Access profile in edit mode
            self.testapp.get(
                "/user/{}/profile/edit".format(self.randonLogin), status=200
            )

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
                {
                    "changepass": "",
                    "old_pass": "123",
                    "new_pass": "123",
                    "conf_pass": "321",
                },
                status=200,
            )

            # Change password fails. Old password is incorrect
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {
                    "changepass": "",
                    "old_pass": "321",
                    "new_pass": "123",
                    "conf_pass": "123",
                },
                status=200,
            )

            # Change password succeeds
            self.testapp.post(
                "/user/{}/profile/edit".format(self.randonLogin),
                {
                    "changepass": "",
                    "old_pass": "123",
                    "new_pass": "123",
                    "conf_pass": "123",
                },
                status=302,
            )

        def test_projects():
            # Add a project fails. The project id is empty
            self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {"project_code": "", "project_abstract": ""},
                status=200,
            )
            # Add a project fails. The project id is not valid
            self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {"project_code": "some@test", "project_abstract": ""},
                status=200,
            )

            # Add a project succeed.
            self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )

            # Add a project fails. The project already exists
            self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=200,
            )

            # Edit a project. Get details
            self.testapp.get(
                "/user/{}/project/{}/edit".format(self.randonLogin, "test001"),
                status=200,
            )

            # Edit a project fails.
            self.testapp.post(
                "/user/{}/project/{}/edit".format(self.randonLogin, "test001"),
                {"project_code": "test001", "project_abstract": ""},
                status=302,
            )

            # List the projects
            self.testapp.get("/user/{}/projects".format(self.randonLogin), status=200)

            # Gets the details of a project
            self.testapp.get(
                "/user/{}/project/{}".format(self.randonLogin, "test001"), status=200
            )

            # Edit a project
            self.testapp.post(
                "/user/{}/project/{}/edit".format(self.randonLogin, "test001"),
                {
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )

            # Delete a project
            self.testapp.post(
                "/user/{}/project/{}/delete".format(self.randonLogin, "test001"),
                status=302,
            )

            self.project = "test001"
            self.projectID = str(uuid.uuid4())

            # Adds again a project.
            self.testapp.post(
                "/user/{}/projects/add".format(self.randonLogin),
                {
                    "project_id": self.projectID,
                    "project_code": "test001",
                    "project_name": "Test project",
                    "project_abstract": "",
                },
                status=302,
            )

            # Gets the QR of a project
            self.testapp.get(
                "/user/{}/project/{}/qr".format(self.randonLogin, "test001"), status=200
            )

            # Sets a project as active
            self.testapp.post(
                "/user/{}/project/{}/setactive".format(self.randonLogin, "test001"),
                status=302,
            )

            # Uploads a file to the project
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)

            self.testapp.post(
                "/user/{}/project/{}/upload".format(self.randonLogin, "test001"),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Uploads the same file reporting that already exists
            self.testapp.post(
                "/user/{}/project/{}/upload".format(self.randonLogin, "test001"),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Overwrites the same file
            self.testapp.post(
                "/user/{}/project/{}/upload".format(self.randonLogin, "test001"),
                {"overwrite": ""},
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Returns a project file
            self.testapp.get(
                "/user/{}/project/{}/storage/{}".format(
                    self.randonLogin, "test001", "test1.dat"
                ),
                status=200,
            )

            # Remove the project file
            self.testapp.post(
                "/user/{}/project/{}/uploads/{}/remove".format(
                    self.randonLogin, "test001", "test1.dat"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Gets the QR of a project
            # TODO: This has to be done twice later on for project with GPS points with and without repository
            self.testapp.get(
                "/user/{}/project/{}/download/gpspoints".format(
                    self.randonLogin, "test001"
                ),
                status=200,
            )

        def test_collaborators():
            # Add a collaborator fails. Collaborator in empty
            self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": ""},
                status=200,
            )

            # Add a collaborator succeed
            self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": self.collaboratorLogin},
                status=302,
            )

            # Add a collaborator fails. Collaborator already exists
            self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": self.collaboratorLogin},
                status=200,
            )

            # Change the role of a collaborator
            self.testapp.post(
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

            # Get the collaborators
            self.testapp.get(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                status=200,
            )

            # Remove the collaborator
            self.testapp.post(
                "/user/{}/project/{}/collaborator/{}/remove".format(
                    self.randonLogin, self.project, self.collaboratorLogin
                ),
                status=302,
            )

            # Add a collaborator again to be used later on
            self.testapp.post(
                "/user/{}/project/{}/collaborators".format(
                    self.randonLogin, self.project
                ),
                {"add_collaborator": "", "collaborator": self.collaboratorLogin},
                status=302,
            )

            # TODO: We need to test accept and declined collaboration.
            #  This need to logout and login with the collaborator

        def test_assistants():
            # Add an assistant fail. The assistant in empty
            self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {"coll_id": ""},
                status=200,
            )

            # Add an assistant fail. The assistant is invalid
            self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {"coll_id": "some@test"},
                status=200,
            )

            # Add an assistant fail. The passwords are not the same
            self.testapp.post(
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

            # Add an assistant fail. The passwords are empty
            self.testapp.post(
                "/user/{}/project/{}/assistants/add".format(
                    self.randonLogin, self.project
                ),
                {"coll_id": "assistant001", "coll_password": "", "coll_password2": ""},
                status=200,
            )

            # Add an assistant succeed
            self.assistantLogin = "assistant001"

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
                status=302,
            )

            # Add an assistant fail. The assistant already exists
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
                status=200,
            )

            # Get the assistants
            self.testapp.get(
                "/user/{}/project/{}/assistants".format(self.randonLogin, self.project),
                status=200,
            )

            # Get the details of an assistant in edit mode
            self.testapp.get(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=200,
            )

            # Edit an assistant
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/edit".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_active": "1", "coll_id": self.assistantLogin},
                status=302,
            )

            # Change assistant password fails. Password is empty
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": ""},
                status=302,
            )

            # Change assistant password fails. Passwords are not the same
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "321"},
                status=302,
            )

            # Change assistant succeeds
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/change".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                {"coll_password": "123", "coll_password2": "123"},
                status=302,
            )

            # Delete the assistant
            self.testapp.post(
                "/user/{}/project/{}/assistant/{}/delete".format(
                    self.randonLogin, self.project, self.assistantLogin
                ),
                status=302,
            )

            # Add the assistant again
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
                status=302,
            )

        def test_assistant_groups():
            # Add an assistant group fail. The description is empty
            self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": ""},
                status=200,
            )

            # Add an assistant group succeeds
            self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if a group"},
                status=302,
            )

            # Add an assistant group fails. Group name already exists
            self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if a group"},
                status=200,
            )

            # Add an assistant group with code succeeds
            self.testapp.post(
                "/user/{}/project/{}/groups/add".format(self.randonLogin, self.project),
                {"group_desc": "Test if a group 2", "group_id": "grp001"},
                status=302,
            )
            self.assistantGroupID = "grp001"

            # Get the assistant groups
            self.testapp.get(
                "/user/{}/project/{}/groups".format(self.randonLogin, self.project),
                status=200,
            )

            # Get the assistant groups in edit mode
            self.testapp.get(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                status=200,
            )

            # Edit the assistant group fails. The name already exists
            self.testapp.post(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"group_desc": "Test if a group", "group_active": "1"},
                status=200,
            )

            # Edit the assistant group succeeds
            self.testapp.post(
                "/user/{}/project/{}/group/{}/edit".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"group_desc": "Test if a group 3", "group_active": "1"},
                status=302,
            )

            # Add a member to a group fails. No assistant
            self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"add_assistant": ""},
                status=302,
            )

            # Add a member to a group fails. Assistant is empty
            self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"add_assistant": "", "coll_id": ""},
                status=302,
            )

            # Add a member to a group fails. Collaborator does not exists
            self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {"add_assistant": "", "coll_id": "{}|hello2".format(self.projectID)},
                status=302,
            )

            # Add a member to a group succeeds
            self.testapp.post(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                {
                    "add_assistant": "",
                    "coll_id": "{}|{}".format(self.projectID, self.assistantLogin),
                },
                status=302,
            )

            # List members
            self.testapp.get(
                "/user/{}/project/{}/group/{}/members".format(
                    self.randonLogin, self.project, self.assistantGroupID
                ),
                status=200,
            )

            # Remove a member
            self.testapp.post(
                "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
                    self.randonLogin,
                    self.project,
                    self.assistantGroupID,
                    self.assistantLogin,
                    self.projectID,
                ),
                status=302,
            )

        def test_forms():
            # Uploads a form fails. PyXForm conversion fails
            paths = ["resources", "forms", "form01.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Uploads a form fails. Invalid ID
            paths = ["resources", "forms", "form02.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Uploads a form fails. Invalid field name
            paths = ["resources", "forms", "form03.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Uploads a form fails. Duplicated choices
            paths = ["resources", "forms", "form04.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Uploads a form fails. Duplicated variables
            paths = ["resources", "forms", "form05.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Uploads a form fails. Duplicated options
            paths = ["resources", "forms", "form06.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Upload a form fails. Too many selects
            paths = ["resources", "forms", "form07.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Upload a form a succeeds
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" not in res.headers

            # Upload a form fails. The form already exists
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" in res.headers

            # Get the details of a form
            self.testapp.get(
                "/user/{}/project/{}/form/{}".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=200,
            )

            # Edit a project. Get details with a form
            self.testapp.get(
                "/user/{}/project/{}/edit".format(self.randonLogin, self.project),
                status=200,
            )

            # Test access to the dashboard with a form
            self.testapp.get("/user/{}".format(self.randonLogin), status=200)

            # Access profile
            self.testapp.get("/user/{}/profile".format(self.randonLogin), status=200)

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
            assert "UploadError" in res.headers

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
            assert "UploadError" in res.headers

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
            assert "UploadError" in res.headers

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
            assert "UploadError" in res.headers

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
            assert "UploadError" in res.headers

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
            assert "UploadError" in res.headers

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
            assert "UploadError" in res.headers

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
            assert "UploadError" in res.headers

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
            assert "UploadError" not in res.headers

            # Edit a form. Show details
            self.testapp.get(
                "/user/{}/project/{}/form/{}/edit".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=200,
            )

            # Edit a form.
            self.testapp.post(
                "/user/{}/project/{}/form/{}/edit".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                {"form_target": "100", "form_hexcolor": "#663f3c"},
                status=302,
            )
            # TODO: We need to update a form when is a subversion

            # Set form as active
            self.testapp.post(
                "/user/{}/project/{}/form/{}/activate".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )

            # Delete the form
            self.testapp.post(
                "/user/{}/project/{}/form/{}/delete".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )
            # TODO: Delete a form with our without schema. Delete when merged

            # Upload the form again
            paths = ["resources", "forms", "form08_OK.xlsx"]
            resource_file = os.path.join(self.path, *paths)

            res = self.testapp.post(
                "/user/{}/project/{}/forms/add".format(self.randonLogin, self.project),
                status=302,
                upload_files=[("xlsx", resource_file)],
            )
            assert "UploadError" not in res.headers

            # TODO: Test form_sse
            # TODO: Test stop_task
            # TODO: Test stop_repository

            # Set form as inactive
            self.testapp.post(
                "/user/{}/project/{}/form/{}/deactivate".format(
                    self.randonLogin, self.project, "Justtest"
                ),
                status=302,
            )

            # TODO: Test import_data

            # Uploads a file to the form
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Uploads the same file to the form
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Overwrites the same file to the form
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                {"overwrite": ""},
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Removes a file from a form
            self.testapp.post(
                "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
                    self.randonLogin, "test001", "Justtest", "test1.dat"
                ),
                status=302,
            )

            # Uploads the file again
            paths = ["resources", "test1.dat"]
            resource_file = os.path.join(self.path, *paths)
            self.testapp.post(
                "/user/{}/project/{}/form/{}/upload".format(
                    self.randonLogin, "test001", "Justtest"
                ),
                status=302,
                upload_files=[("filetoupload", resource_file)],
            )

            # Gets the file
            self.testapp.get(
                "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
                    self.randonLogin, "test001", "Justtest", "test1.dat"
                ),
                status=200,
            )
            

        test_root()
        test_login()
        test_dashboard()
        test_profile()
        test_projects()
        test_collaborators()
        test_assistants()
        test_assistant_groups()
        test_forms()
