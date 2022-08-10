import os
import secrets
import uuid


def t_e_s_t_unauthorized_access(test_object):
    # Collaborator groups ----------------------------------------

    # The assistant group does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/groups".format(test_object.randonLogin, "NotExist"),
        status=404,
    )

    # Show the add group page does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/groups/add".format(test_object.randonLogin, "NotExist"),
        status=404,
    )

    # Edits a group of a project that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, "NotExist", "NotExist"
        ),
        status=404,
    )

    # Delete a group of a project that does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/delete".format(
            test_object.randonLogin, "NotExist", "NotExist"
        ),
        status=404,
    )

    # List members of a project that does not exists
    test_object.testapp.get(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, "NotExist", "NotExist"
        ),
        status=404,
    )

    # Add a member of a project that does not exists
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, "NotExist", "NotExist"
        ),
        status=404,
    )

    # Remove a member of a project that does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
            test_object.randonLogin,
            "NotExist",
            test_object.assistantGroupID,
            test_object.assistantLogin,
            test_object.projectID,
        ),
        status=404,
    )

    collaborator_1 = str(uuid.uuid4())
    collaborator_1_key = collaborator_1
    collaborator_1 = collaborator_1[-12:]

    # Add a new collaborator
    res = test_object.testapp.post(
        "/join",
        {
            "user_email": collaborator_1 + "@qlands.com",
            "user_password": "123",
            "user_id": collaborator_1,
            "user_password2": "123",
            "user_name": "Testing",
            "user_apikey": collaborator_1_key,
            "user_apisecret": secrets.token_hex(16),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a project to a user that is not the logged user goes to 404
    test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_code": "coll1_test001",
            "project_name": "Test project collaborator 1",
            "project_abstract": "",
            "project_icon": "😁",
            "project_hexcolor": "#9bbb59",
            "project_formlist_auth": 1,
        },
        status=404,
    )

    # Add a project to collaborator 1
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(collaborator_1),
        {
            "project_code": "coll1_test001",
            "project_name": "Test project collaborator 1",
            "project_abstract": "",
            "project_icon": "😁",
            "project_hexcolor": "#9bbb59",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the page for fixing the language goes to 404. Project does not belong to him
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=404,
    )

    # Compare goes to 404 form not found
    test_object.testapp.get(
        "/user/{}/project/{}/compare/from/{}/to/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201105",
            "tormenta20201117",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/manage_users".format(test_object.randonLogin), status=404
    )

    test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(test_object.randonLogin, "NA"),
        {"modify": "", "user_email": "hola"},
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/manage_user/{}/edit".format(collaborator_1, "na"),
        {"modify": "", "user_email": "hola"},
        status=404,
    )

    test_object.testapp.get("/user/{}/manage_users".format(collaborator_1), status=404)

    test_object.testapp.post(
        "/user/{}/manage_users/add".format(test_object.randonLogin),
        {"user_id": "some@test"},
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/manage_users/add".format(collaborator_1),
        {"user_id": "some@test"},
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201117",
            "tormenta20201105",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/audit".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, test_object.project, test_object.formID
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

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/audit/get"
        "?callback=jQuery31104503466642261382_1578424030318".format(
            test_object.randonLogin, test_object.project, test_object.formID
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

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        {"owner_email": test_object.randonLogin + "@qlands.com"},
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/delete".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"oper": "del", "id": "na"},
        status=404,
    )

    # Opens other user profile
    test_object.testapp.get(
        "/user/{}/profile".format(test_object.randonLogin), status=404
    )

    # Edit others profile
    test_object.testapp.get(
        "/user/{}/profile/edit".format(test_object.randonLogin), status=404
    )

    # Add partner to a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"partner_id": ""},
        status=404,
    )

    # Edit a partner of a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID, "na"
        ),
        {
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=404,
    )

    # Remove a partner from a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.formID, "na"
        ),
        {},
        status=404,
    )

    # Download a private xls for a form that does not have access goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download a private zip csv for a form that does not have access goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Generate public XLSX when don't have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Generate public zip csv when don't have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Gets a file of a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/uploads/{}/retrieve".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "test1.dat",
        ),
        status=404,
    )

    # Add assistant to a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
        },
        status=404,
    )

    # Edit an assistant of a form the does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=404,
    )

    # Remove an assistant that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=404,
    )

    # Add a group of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"group_id": test_object.assistantGroupID, "group_can_submit": 1},
        status=404,
    )

    # Edit a group of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.assistantGroupID,
        ),
        {"group_can_submit": 1, "group_can_clean": 1},
        status=404,
    )

    # Delete a group of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.assistantGroupID,
        ),
        {"group_can_submit": 1, "group_can_clean": 1},
        status=404,
    )

    # Download data in CSV format of a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download the ODK form file for a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/odk".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download submitted media files for a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/media".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Get the partner GPS info of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Export data of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download KML of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/kml".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download XLSX of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download Zip CSV of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download XLSX of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Public CSV of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_public_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Private CSV of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_private_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Loads import data for a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Stop task for a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/task/{}/stop".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "not_exist",
        ),
        status=404,
    )

    # Get the partner Marker info for a submission in a project without access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "not_exist",
        ),
        status=404,
    )

    # Get media files of a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/media/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "na",
            "na",
        ),
        status=404,
    )

    # Open the case lookup table for a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        status=404,
    )

    # Example case csv for a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/caselookupcsv".format(test_object.randonLogin, "case001"),
        status=404,
    )

    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    # Updates a form to a project that does not has access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"form_pkey": "hid"},
        status=404,
        upload_files=[("xlsx", resource_file)],
    )

    # Activate a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Set form as inactive in a project that don't have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Upload a file to a project that does have access goes to 404
    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    # Removes a file from a form in a project that des not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "distritos.csv",
        ),
        status=404,
    )

    # Edit a form for a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Delete the form of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # The user don't have access to such project
    test_object.testapp.get(
        "/user/{}/project/{}/groups".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # The user don't have access to the collaborators
    test_object.testapp.get(
        "/user/{}/project/{}/assistants".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # The user don't have access to add collaborators
    test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
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
    test_object.testapp.get(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        status=404,
    )

    # 404 no access to project
    test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        status=404,
    )

    # 404 not access to project
    test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/change".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {"coll_password": "123", "coll_password2": "123"},
        status=404,
    )

    # The user don't have access to add a group in project project
    test_object.testapp.get(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # Get the assistant groups in edit mode
    test_object.testapp.get(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, "NotExist"
        ),
        status=404,
    )

    # Delete a group of a project that does not have access
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/delete".format(
            test_object.randonLogin, test_object.project, "NotExist"
        ),
        status=404,
    )

    # List members of a project that does not have access
    test_object.testapp.get(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, "NotExist"
        ),
        status=404,
    )

    # Add a member of a project that does not have access
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, "NotExist"
        ),
        status=404,
    )

    # Remove a member of a project that does not have access
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.assistantGroupID,
            test_object.assistantLogin,
            test_object.projectID,
        ),
        status=404,
    )

    # Download a product from a project that does not have access
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_private_export",
            "na",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_private_export",
            "na",
            collaborator_1_key,
        ),
        status=404,
    )

    # Publish product without access
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_public_export",
            "na",
        ),
        status=404,
    )

    # Unpublish product with not have access project goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_public_export",
            "na",
        ),
        status=404,
    )

    # Delete product goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_public_export",
            "na",
        ),
        status=404,
    )

    # File of a project that does not have access
    test_object.testapp.get(
        "/user/{}/project/{}/storage/{}".format(
            test_object.randonLogin, "test001", "test1.dat"
        ),
        status=404,
    )

    # Activate a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/setactive".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Delete a project with that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/delete".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Get a list of project of a user that is not the same as logged
    test_object.testapp.get(
        "/user/{}/projects".format(test_object.randonLogin), status=404
    )

    # Project details of a project that not have access
    test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, "test001"), status=404
    )

    # Edit a project that don't have access
    test_object.testapp.get(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Upload a file to a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "test001"),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    # Get GPS points of a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/download/gpspoints".format(
            test_object.randonLogin, "test001"
        ),
        status=404,
    )

    # Removes a file of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "test1.dat"
        ),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    test_object.testapp.get(
        "/user/{}/project/{}/qr".format(test_object.randonLogin, "test001"), status=404
    )

    test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "partner_id": "some",
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2021-08-05",
        },
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, test_object.project, "NA"
        ),
        {
            "time_bound": 1,
            "access_from": "2021-08-19",
            "access_to": "2021-10-19",
        },
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/remove_partner/{}".format(
            test_object.randonLogin, test_object.project, "na"
        ),
        {},
        status=404,
    )

    # The collaborator logs out
    test_object.testapp.get("/logout", status=302)

    # Main user login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Main user add collaborator as member
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": "", "collaborator": collaborator_1},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Main user logs out
    test_object.testapp.get("/logout", status=302)

    # Collaborator logs in
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": collaborator_1, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # ---------------Section to test editor unauthorized access ---------------

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "maintable",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201117",
            "tormenta20201105",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, test_object.project, test_object.formID
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

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        {"owner_email": test_object.randonLogin + "@qlands.com"},
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/delete".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"oper": "del", "id": "na"},
        status=404,
    )

    # Upload a file to a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/upload".format(test_object.randonLogin, "test001"),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    # Delete a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/delete".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Edit a project that don't have access
    test_object.testapp.get(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "test001"),
        status=404,
    )

    # Removes a file of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/uploads/{}/remove".format(
            test_object.randonLogin, "test001", "test1.dat"
        ),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "partner_id": "some",
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2021-08-05",
        },
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, test_object.project, "NA"
        ),
        {
            "time_bound": 1,
            "access_from": "2021-08-19",
            "access_to": "2021-10-19",
        },
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/remove_partner/{}".format(
            test_object.randonLogin, test_object.project, "na"
        ),
        {},
        status=404,
    )

    # Get the page for fixing the language goes to 404. Project does not belong has access
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=404,
    )

    # Publish product without access
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_public_export",
            "na",
        ),
        status=404,
    )

    # Unpublish product with not have access project goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_public_export",
            "na",
        ),
        status=404,
    )

    # Delete product goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "csv_public_export",
            "na",
        ),
        status=404,
    )

    # Add partner to a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"partner_id": ""},
        status=404,
    )

    # Edit a partner of a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID, "na"
        ),
        {
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=404,
    )

    # Remove a partner from a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.formID, "na"
        ),
        {},
        status=404,
    )

    # Add assistant to a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
        },
        status=404,
    )

    # Edit an assistant of a form the does not have acess goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=404,
    )

    # Remove an assistant that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        status=404,
    )

    # Add a group to a form without access get goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"group_id": test_object.assistantGroupID, "group_can_submit": 1},
        status=404,
    )

    # Edit a group of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.assistantGroupID,
        ),
        {"group_can_submit": 1, "group_can_clean": 1},
        status=404,
    )

    # Delete a group of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.assistantGroupID,
        ),
        {"group_can_submit": 1, "group_can_clean": 1},
        status=404,
    )

    # Generate public XLSX when don't have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Generate public XLSX when don't have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download a private xls for a form that does not have access goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download a private zip CSV for a form that does not have access goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download submitted media files for a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/media".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Export data of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download KML of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/kml".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download XLSX of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download XLSX of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Download CSV of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Public CSV of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_public_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Private CSV of a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_private_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Loads import data for a form that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Stop task for a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/task/{}/stop".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "not_exist",
        ),
        status=404,
    )

    # Open the case lookup table for a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # Open the case lookup table for a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/caselookupcsv".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # Activate a form that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/activate".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Set form as inactive in a project that don't have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/deactivate".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Upload a file to a project that does have access goes to 404
    paths = ["resources", "test1.dat"]
    resource_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
        upload_files=[("filetoupload", resource_file)],
    )

    # Removes a file from a form in a project that des not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "distritos.csv",
        ),
        status=404,
    )

    # The user don't have access to add a group in project project
    test_object.testapp.get(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # The user don't have access to add a form to the project
    paths = ["resources", "forms", "form08_OK.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    #  Upload a form to a project that does not has access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "hid"},
        status=404,
        upload_files=[("xlsx", resource_file)],
    )

    # Updates a form to a project that does not has access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"form_pkey": "hid"},
        status=404,
        upload_files=[("xlsx", resource_file)],
    )

    # Edit a form for a project that does not have access goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Delete the form of a project that does not have access goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # The user don have credentials for looking at assistants
    test_object.testapp.get(
        "/user/{}/project/{}/assistants".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # 404 Not credentials to add
    test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, test_object.project
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
    test_object.testapp.get(
        "/user/{}/project/{}/assistant/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        status=404,
    )

    # No credentials to remove
    test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        status=404,
    )

    # No credentials to change password
    test_object.testapp.post(
        "/user/{}/project/{}/assistant/{}/change".format(
            test_object.randonLogin, test_object.project, test_object.assistantLogin
        ),
        {"coll_password": "123", "coll_password2": "123"},
        status=404,
    )

    # Get the assistant groups in edit mode
    test_object.testapp.get(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, "NotExist"
        ),
        status=404,
    )

    # Delete a group of a project that does not have grants
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/delete".format(
            test_object.randonLogin, test_object.project, "NotExist"
        ),
        status=404,
    )

    # Remove a member of a project that does not have grants
    test_object.testapp.post(
        "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.assistantGroupID,
            test_object.assistantLogin,
            test_object.projectID,
        ),
        status=404,
    )

    # --------------Finally ----------------
    # New collaborator logout
    test_object.testapp.get("/logout", status=302)

    # Main user login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
