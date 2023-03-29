import os
import time

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details


def t_e_s_t_case_management(test_object):
    # Upload a case creator pass.
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "hid", "form_caselabel": "fname"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=200,
    )
    test_object.root.assertIn(b"Case creator", res.body)

    # Edit a project. Get details. Cannot change project type
    res = test_object.testapp.get(
        "/user/{}/project/{}/edit".format(test_object.randonLogin, "case001"),
        status=200,
    )
    assert "FS_error" not in res.headers
    test_object.root.assertIn(b"Read-only because the project has forms", res.body)

    # Gets the details of a project. Upload Forms are inactive at the moment
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, "case001"), status=200
    )
    assert "FS_error" not in res.headers
    test_object.root.assertIn(
        b"You cannot add new forms while you have a case creator", res.body
    )

    # Add an assistant to a form succeeds fails. No privileges
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Uploads cantones
    paths = ["resources", "forms", "case", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads distritos
    paths = ["resources", "forms", "case", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Update a form fails. Invalid primary key variable
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {"form_pkey": "test", "form_caselabel": "test"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Invalid case label variable
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {"form_pkey": "hid", "form_caselabel": "test"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. label variable empty
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {"form_pkey": "hid", "form_caselabel": ""},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. label variable and key are the same
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {"form_pkey": "hid", "form_caselabel": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form pass
    paths = ["resources", "forms", "case", "case_start.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {"form_pkey": "hid", "form_caselabel": "fname"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # There are not case starts with repository
    test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        status=404,
    )

    # There are not case starts with repository
    test_object.testapp.get(
        "/user/{}/project/{}/caselookupcsv".format(test_object.randonLogin, "case001"),
        status=404,
    )

    # Creates the repository of the case creator
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {
            "form_pkey": "hid",
            "start_stage1": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing case management step 1 finished")
    time.sleep(40)  # Wait for the repository to finish

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=200,
    )
    test_object.root.assertIn(b"Case creator", res.body)
    test_object.root.assertIn(b"With repository", res.body)

    # Removes a rquired file fails
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin, "case001", "case_start_20210311", "distritos.csv"
        ),
        status=302,
    )
    assert "FS_error" in res.headers

    # Get details of the project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, "case001"),
        status=200,
    )
    assert "FS_error" not in res.headers
    test_object.root.assertIn(b"real-time CSV case file", res.body)
    test_object.root.assertIn(b"Create the real-time CSV case file before", res.body)

    # Open the case lookup table for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "not_exist"
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/caselookupcsv".format(
            test_object.randonLogin, "not_exist"
        ),
        status=404,
    )

    # Open the case lookup table for a project that does not have cases management goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # Open the case lookup table for a project that does not have cases management goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/caselookupcsv".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # Open the case lookup table
    res = test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Generates del case example CSV
    test_object.testapp.get(
        "/user/{}/project/{}/caselookupcsv".format(test_object.randonLogin, "case001"),
        status=200,
    )

    # Get details of the project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, "case001"),
        status=200,
    )
    assert "FS_error" not in res.headers
    test_object.root.assertIn(b"real-time CSV case file", res.body)
    test_object.root.assertNotIn(b"Create the real-time CSV case file before", res.body)

    # Adds the field distrito
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        {
            "add_field": "",
            "field_name": "distrito",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Removes the field distrito
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        {
            "remove_field": "",
            "field_name": "distrito",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Adds the field distrito again
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        {
            "add_field": "",
            "field_name": "distrito",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Adds the field canton
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        {
            "add_field": "",
            "field_name": "canton",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change alias of distrito with empty alias
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        {
            "change_alias": "",
            "field_name": "distrito",
            "field_alias": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change alias of distrito
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        {
            "change_alias": "",
            "field_name": "distrito",
            "field_alias": "distrito_id",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change alias of distrito fails field not found
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
        ),
        {
            "change_alias": "",
            "field_name": "distritos",
            "field_alias": "distrito_id",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Change alias of distrito fails invalid character
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
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
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
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
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
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
    res = test_object.testapp.post(
        "/user/{}/project/{}/caselookuptable".format(
            test_object.randonLogin, "case001"
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
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "survey_id", "form_caseselector": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case follow up. Invalid pkey
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {"form_pkey": "test", "form_caseselector": "hid", "form_casetype": "2"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case follow up. Empty case selector
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
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
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "test",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case follow up. Invalid case selector
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "start_date",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case follow up. case selector and primary key are the same
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "survey_id",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload case selected fails. The date or datetime variable is not given
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload case selected fails. The date or datetime variable is the same of case selector
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "hid",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload case selected fails. The date or datetime variable has invalid type
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "provincia",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a case follow up pass
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "start_date",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Uploads cantones
    paths = ["resources", "forms", "case", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads distritos
    paths = ["resources", "forms", "case", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads households
    paths = ["resources", "forms", "case", "households.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
    )
    test_object.root.assertIn(b"Linked to the real-time CSV case file", res.body)

    # Get the FormList. Empty list
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, "case001"),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
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
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Produces the household csv
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Does not produce the household csv
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Upload case 004
    paths = [
        "resources",
        "forms",
        "case",
        "data",
        "start_04.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Gets the manifest. households.csv is created
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )
    print("Waiting 10 seconds for ES to store submissions")
    time.sleep(30)
    form_details = get_form_details(
        test_object.server_config, test_object.case_project_id, "case_start_20210311"
    )
    engine = create_engine(
        test_object.server_config["sqlalchemy.url"], poolclass=NullPool
    )
    res = engine.execute(
        "SELECT rowuuid FROM {}.maintable".format(form_details["form_schema"])
    ).first()
    row_uuid = res[0]
    engine.dispose()

    test_object.testapp.post_json(
        "/api_update",
        {
            "apikey": test_object.caseassistantLoginKey,
            "rowuuid": row_uuid,
            "age": 14,
        },
        status=200,
    )

    # Gets the manifest. households.csv is created
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the FormList. households.csv is created
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, "case001"),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/households.csv".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the FormList. household.csv is not created
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, "case001"),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/households.csv".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Update a form fails. Invalid primary key variable
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {"form_pkey": "test", "form_caseselector": "hid", "form_casetype": "2"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. Invalid case selector variable
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
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
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {"form_pkey": "survey_id", "form_caseselector": "hid"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form. Empty case selector
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
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
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
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

    # Update a form fails. The date or datetime variable is empty
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. The date or datetime variable is is the same as the key selector
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "hid",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form fails. The date or datetime variable has an invalid type
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "provincia",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Update a form pass
    paths = ["resources", "forms", "case", "case_follow_up.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "start_date",
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
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertNotIn(b"[Manage errors]", res.body)

    # Creates the repository of the case follow up
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        {
            "form_pkey": "survey_id",
            "start_stage1": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing case management step 2 finished")
    time.sleep(40)  # Wait for the repository to finish

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
    )
    test_object.root.assertIn(b"With repository", res.body)

    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=404,
    )

    # Get the FormList. household.csv is created
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, "case001"),
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
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
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
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_follow_up_20210319"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertNotIn(b"[Manage errors]", res.body)

    # Upload a case deactivate pass
    paths = ["resources", "forms", "case", "case_deactivate.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "start_date",
            "form_casetype": "3",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Uploads cantones
    paths = ["resources", "forms", "case", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads distritos
    paths = ["resources", "forms", "case", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads households
    paths = ["resources", "forms", "case", "households.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"Linked to the real-time CSV case file", res.body)

    # Creates the repository of the case creator
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        {
            "form_pkey": "survey_id",
            "start_stage1": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing case management step 3 finished")
    time.sleep(40)  # Wait for the repository to finish

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"With repository", res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Deactivate case 001
    paths = [
        "resources",
        "forms",
        "case",
        "data",
        "deact_01.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertNotIn(b"[Manage errors]", res.body)

    creator_details = get_form_details(
        test_object.server_config, test_object.case_project_id, "case_start_20210311"
    )
    creator_schema = creator_details["form_schema"]
    engine = create_engine(
        test_object.server_config["sqlalchemy.url"], poolclass=NullPool
    )
    res = engine.execute(
        "SELECT _active FROM {}.maintable WHERE hid = '{}'".format(
            creator_schema, "001"
        )
    ).first()
    current_status = res[0]
    engine.dispose()
    assert current_status == 0

    # Get the FormList. household.csv is created
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, "case001"),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Upload a case activate pass
    paths = ["resources", "forms", "case", "case_activate.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "start_date",
            "form_casetype": "4",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Uploads cantones
    paths = ["resources", "forms", "case", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads distritos
    paths = ["resources", "forms", "case", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads households
    paths = ["resources", "forms", "case", "households.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"Linked to the real-time CSV case file", res.body)

    # Creates the repository of the case creator
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        {
            "form_pkey": "survey_id",
            "start_stage1": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing case management step 4 finished")
    time.sleep(40)  # Wait for the repository to finish

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"With repository", res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Activate case 001
    paths = [
        "resources",
        "forms",
        "case",
        "data",
        "activ_01.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertNotIn(b"[Manage errors]", res.body)

    creator_details = get_form_details(
        test_object.server_config, test_object.case_project_id, "case_start_20210311"
    )
    creator_schema = creator_details["form_schema"]
    engine = create_engine(
        test_object.server_config["sqlalchemy.url"], poolclass=NullPool
    )
    res = engine.execute(
        "SELECT _active FROM {}.maintable WHERE hid = '{}'".format(
            creator_schema, "001"
        )
    ).first()
    current_status = res[0]
    engine.dispose()
    assert current_status == 1

    # Activate case 001 B. Goes to logs because is already active
    paths = [
        "resources",
        "forms",
        "case",
        "data",
        "activ_01B.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_activate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertIn(b"[Manage errors]", res.body)

    # Get the FormList. household.csv is created
    test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, "case001"),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Check merging a case creator

    paths = ["resources", "forms", "case", "merge", "case_start.xlsx"]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.case_project_id,
            "parent_form": "case_start_20210311",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_start_20210331"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210331"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Merge check pending" in res.body)

    # Uploads cantones
    paths = ["resources", "forms", "case", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_start_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads distritos
    paths = ["resources", "forms", "case", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_start_20210331"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210331"
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Merge check pending" in res.body)

    # Show the merge repository page
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            "case001",
            "case_start_20210331",
            "case_start_20210311",
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Merge the new creator using Celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            "case001",
            "case_start_20210331",
            "case_start_20210311",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing case management step 5 finished")
    time.sleep(60)  # Wait for the merge to finish

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210331"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"This is the sub-version of" in res.body)

    # Get the details of a form tormenta20201105
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210311"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"is the sub-version of this form" in res.body)

    # Upload case 003
    paths = [
        "resources",
        "forms",
        "case",
        "merge",
        "data",
        "start_03.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_start_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertNotIn(b"[Manage errors]", res.body)

    # Deactivate case 003
    paths = [
        "resources",
        "forms",
        "case",
        "data",
        "deact_03.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
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
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.case_project_id,
            "parent_form": "case_deactivate_20210331",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_deactivate_20210401"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210401"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Merge check pending" in res.body)

    # Uploads cantones
    paths = ["resources", "forms", "case", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_deactivate_20210401"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads distritos
    paths = ["resources", "forms", "case", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_deactivate_20210401"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads households
    paths = ["resources", "forms", "case", "households.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, "case001", "case_deactivate_20210401"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210401"
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Merge check pending" in res.body)
    test_object.root.assertIn(b"Linked to the real-time CSV case file", res.body)

    # Show the merge repository page
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            "case001",
            "case_deactivate_20210401",
            "case_deactivate_20210331",
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Merge the new creator using Celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            "case001",
            "case_deactivate_20210401",
            "case_deactivate_20210331",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing case management step 7 finished")
    time.sleep(60)  # Wait for the merge to finish

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210401"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"This is the sub-version of" in res.body)

    # Get the details of a form tormenta20201105
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"is the sub-version of this form" in res.body)

    # Deactivate case 002 using the merged form
    paths = [
        "resources",
        "forms",
        "case",
        "merge",
        "data",
        "deact_02.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    print("Wait a bit more")
    time.sleep(60)
    print("After the merging of a form")
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the details of a form case_deactivate_20210331
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertNotIn(b"[Manage errors]", res.body)

    res = engine.execute(
        "SELECT _active FROM {}.maintable WHERE hid = '{}'".format(
            creator_schema, "002"
        )
    ).first()
    current_status = res[0]
    engine.dispose()
    assert current_status == 0

    # Deactivate case 002 using the merged form goes to logs
    paths = [
        "resources",
        "forms",
        "case",
        "merge",
        "data",
        "deact_02B.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the details of a form case_deactivate_20210331
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_deactivate_20210331"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertIn(b"[Manage errors]", res.body)

    # Upload a case follow up barcode passes.
    paths = ["resources", "forms", "case", "case_follow_up_barcode.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, "case001"),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "start_date",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Update the same form passes
    paths = ["resources", "forms", "case", "case_follow_up_barcode.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/updateodk".format(
            test_object.randonLogin, "case001", "case_follow_up_barcode_20210428"
        ),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "start_date",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, "case001", "case_follow_up_barcode_20210428"
        ),
        {
            "coll_id": "{}|{}".format(test_object.case_project_id, "caseassistant001"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Creates the repository of the case follow up
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, "case001", "case_follow_up_barcode_20210428"
        ),
        {
            "form_pkey": "survey_id",
            "start_stage1": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing case management step 8 finished")
    time.sleep(40)  # Wait for the repository to finish

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_follow_up_barcode_20210428"
        ),
        status=200,
    )
    test_object.root.assertIn(b"With repository", res.body)

    # Follow up 001 with QR Code
    paths = [
        "resources",
        "forms",
        "case",
        "data",
        "follow_bar_code_01.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_follow_up_barcode_20210428"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertNotIn(b"[Manage errors]", res.body)

    # Follow up 002 with QR Code goes to the logs
    paths = [
        "resources",
        "forms",
        "case",
        "data",
        "follow_bar_code_02.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, "case001"),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing="caseassistant001"
        ),
    )

    # Get the details of the form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "case001", "case_follow_up_barcode_20210428"
        ),
        status=200,
    )
    test_object.root.assertIn(b"[Clean data]", res.body)
    test_object.root.assertIn(b"[Manage errors]", res.body)
