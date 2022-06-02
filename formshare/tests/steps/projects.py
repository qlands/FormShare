import os
import uuid


def t_e_s_t_projects(test_object):
    # Show the add screen
    test_object.testapp.get(
        "/user/{}/projects/add".format(test_object.randonLogin),
        status=200,
    )

    # Add a project fails. The project id is empty
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_code": "",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a project fails. The project id is not valid
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_code": "some@test",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a project succeed.
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_code": "test001",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "😁",
            "project_hexcolor": "#9bbb59",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Adds a second project
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
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

    # Add a project fails. The project already exists
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_code": "test001",
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Edit a project. Get details
    res = test_object.testapp.get(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "test001"),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Edit a that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "not_exist"),
        status=404,
    )

    # Edit a project fails. The project name is empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "test001"),
        {
            "project_code": "test001",
            "project_abstract": "",
            "project_name": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # List the projects
    res = test_object.testapp.get(
        "/user/{}/projects".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Project don't exist
    test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, "not_exist"), status=404
    )

    # Gets the details of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, "test001"), status=200
    )
    assert "FS_error" not in res.headers

    # Edit a project
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "test001"),
        {
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

    # Delete a project with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/delete".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Delete a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/delete".format(test_object.randonLogin, "no_exist"),
        status=404,
    )

    # Delete a project
    res = test_object.testapp.post(
        "/user/{}/project/{}/delete".format(test_object.randonLogin, "test001"),
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.project = "test001"
    test_object.projectID = str(uuid.uuid4())

    # Adds again a project.
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_id": test_object.projectID,
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

    test_object.testapp.get(
        "/user/{}/project/{}/qr".format(test_object.randonLogin, "not_exist"),
        status=404,
    )

    # Gets the QR of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}/qr".format(test_object.randonLogin, "test001"), status=200
    )
    assert "FS_error" not in res.headers

    # Activate a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/setactive".format(test_object.randonLogin, "not_exist"),
        status=404,
    )

    # Activate a project with GET goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/setactive".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Sets a project as active
    res = test_object.testapp.post(
        "/user/{}/project/{}/setactive".format(test_object.randonLogin, "test001"),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Uploads a file to the project
    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "test2.dat"]
    resource_file_2 = os.path.join(test_object.path, *paths)

    # Upload a file with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Upload a file to a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "not_exist"),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "test001"),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Removes a file of a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/uploads/{}/remove".format(
            test_object.randonLogin, "not_exist", "test1.dat"
        ),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    # Removes a file with get exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "test1.dat"
        ),
        status=404,
    )

    # Remove the file
    res = test_object.testapp.post(
        "/user/{}/project/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "test1.dat"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Upload two files
    res = test_object.testapp.post(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "test001"),
        status=302,
        upload_files=[
            ("filetoupload", resource_file),
            ("filetoupload", resource_file_2),
        ],
    )
    assert "FS_error" not in res.headers

    # Uploads the same file reporting that already exists
    res = test_object.testapp.post(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "test001"),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" in res.headers

    # Overwrites the same file
    res = test_object.testapp.post(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "test001"),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # File of a project that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/storage/{}".format(
            test_object.randonLogin, "not_exist", "test1.dat"
        ),
        status=404,
    )

    # Get a file that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/storage/{}".format(
            test_object.randonLogin, "test001", "not_exist"
        ),
        status=404,
    )

    # Returns a project file
    res = test_object.testapp.get(
        "/user/{}/project/{}/storage/{}".format(
            test_object.randonLogin, "test001", "test1.dat"
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Remove the project file
    res = test_object.testapp.post(
        "/user/{}/project/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "test1.dat"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get GPS points of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/download/gpspoints".format(
            test_object.randonLogin, "not_exist"
        ),
        status=404,
    )

    # Gets the GPS Points of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}/download/gpspoints".format(
            test_object.randonLogin, "test001"
        ),
        status=200,
    )
    assert "FS_error" not in res.headers
