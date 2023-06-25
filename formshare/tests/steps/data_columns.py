import os
import time


def t_e_s_t_data_columns(test_object):
    paths = [
        "resources",
        "forms",
        "data_columns",
        "data_columns.xlsx",
    ]
    a_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "collection_date"},
        status=302,
        upload_files=[("xlsx", a_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"climmob" in res.body)

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # The form has no schema
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
            "maintable",
            "hr_qst_007",
        ),
        status=404,
    )

    # Generate the repository using celery fails due to language
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
        ),
        status=200,
    )
    test_object.root.assertIn(b"climmob", res.body)

    # Generate the repository using celery fails due to language
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
        ),
        {
            "form_pkey": "collection_date",
            "start_stage1": "",
            "survey_data_columns": "climmob",
            "choices_data_columns": ["admlevel1", "admlevel2", "factor", "sequence"],
        },
        status=200,
    )
    test_object.root.assertIn(b"Swahili", res.body)
    test_object.root.assertIn(
        b"climmob|formshare_sensitive|formshare_encrypted|formshare_ontological_term",
        res.body,
    )
    test_object.root.assertIn(
        b"admlevel1|admlevel2|factor|sequence|formshare_ontological_term", res.body
    )

    # Generate the repository using celery pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
        ),
        {
            "form_pkey": "collection_date",
            "start_stage2": "",
            "form_deflang": "English",
            "LNG-English": "en",
            "LNG-Swahili": "sw",
            "languages_string": '[{"code": "en", "name": "English"}, {"code": "sw", "name": "Swahili"}]',
            "survey_data_columns": "climmob|formshare_sensitive|formshare_encrypted|formshare_ontological_term",
            "choices_data_columns": "admlevel1|admlevel2|factor|sequence|formshare_ontological_term",
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    time.sleep(60)  # Waiting for Celery to create the repository

    # Get the details of a form. The form now should have a repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"With repository" in res.body)

    # Get the fields of a table
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
            "maintable",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Edit metadata" in res.body)
    test_object.root.assertTrue(b"post_not_sensitive_change('hr_qst_005')" in res.body)

    # Get the fields of a table
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
            "maintable",
            "hr_qst_007",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"climmob" in res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            "not_found",
            "data_columns_20230614",
            "maintable",
            "not_found",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            "not_found",
            "data_columns_20230614",
            "maintable",
            "not_found",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            test_object.project,
            "not_found",
            "maintable",
            "not_found",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
            "maintable",
            "not_found",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
            "not_found",
            "not_found",
        ),
        status=404,
    )

    # Update the description of a field without description
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
            "maintable",
            "hr_qst_007",
        ),
        {
            "desc": "Gender changed",
            "climmob": "QST000",
            "ontology": "c_34835@cropontology",
        },
        status=302,
    )

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/{}/metadata".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230614",
            "maintable",
            "hr_qst_007",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Gender changed" in res.body)
    test_object.root.assertTrue(b"c_34835@cropontology" in res.body)
    test_object.root.assertTrue(b"QST008" in res.body)

    paths = [
        "resources",
        "forms",
        "data_columns",
        "data_columns_a.xlsx",
    ]
    b_resource_file = os.path.join(test_object.path, *paths)

    # Merge a new version
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "data_columns_20230614"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "data_columns_20230614",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230623",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"climmob" in res.body)
    test_object.root.assertTrue(b"meld" in res.body)

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230623",
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show the merge repository page
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230623",
            "data_columns_20230614",
        ),
        status=200,
    )
    assert "FS_error" not in res.headers
    test_object.root.assertTrue(b"meld" in res.body)
    test_object.root.assertFalse(b"climmob" in res.body)

    # Merge the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "data_columns_20230623",
            "data_columns_20230614",
        ),
        {
            "survey_data_columns": "meld",
            "discard_testing_data": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for the merge to finish

    # Get the details of a form data_columns_20230623
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "data_columns_20230623"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"This is the sub-version of" in res.body)
