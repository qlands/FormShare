import os
import time


def t_e_s_t_form_merge_language_control(test_object):
    # Uploads a form with duplicated options fails even using allow_choice_duplicates=yes in ODK
    # FormShare does not allow duplicated options.
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_duplicated_options.xlsx",
    ]
    a_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "control"},
        status=302,
        upload_files=[("xlsx", a_resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form with malformed language fails
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_malformed_language.xlsx",
    ]
    a_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "control"},
        status=302,
        upload_files=[("xlsx", a_resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form with options without labels fails
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_options_no_label.xlsx",
    ]
    a_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "control"},
        status=302,
        upload_files=[("xlsx", a_resource_file)],
    )
    assert "FS_error" in res.headers

    # Uploads a form with no language definition pass
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_no_lng.xlsx",
    ]
    a_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "control"},
        status=302,
        upload_files=[("xlsx", a_resource_file)],
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/tables".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/dictionary/table/{}/fields".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_no_lng",
            "maintable",
        ),
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/delete".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        {"oper": "del", "id": "na"},
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        {"owner_email": test_object.randonLogin + "@qlands.com"},
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/audit".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/get?callback=jQuery311038923674830152466_1578156795294".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
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
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
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

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        {
            "form_pkey": "control",
            "start_stage1": "",
            "discard_testing_data": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for celery to generate the repository

    print("Testing merge of language cases")

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        status=302,
    )

    # Tries to merge a form with malformed language fails
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_malformed_language.xlsx",
    ]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "asistencia_tecnica_no_lng",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" in res.headers

    # Tries to merge a form with options with no labels fails
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_options_no_label.xlsx",
    ]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "asistencia_tecnica_no_lng",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" in res.headers

    # -------------------------------
    # Merge a form with full language pass
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_2_complete_language.xlsx",
    ]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "asistencia_tecnica_no_lng",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "provincia.csv",
    ]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Fix language" in res.body)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # ---------------------

    # Merge a form with default language pass
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica.xlsx",
    ]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "asistencia_tecnica_no_lng",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Fix language" in res.body)

    # Get the fix language page of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, "not_exist", "asistencia_tecnica"
        ),
        status=404,
    )

    # Get the fix language page of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Get the fix language page of a form that is not merging
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        status=404,
    )

    # Get the page for fixing the language pass
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"WAS NOT in multiple languages" in res.body)

    # Post without setting the language does not pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        {
            "form_deflang": "",
        },
        status=200,
    )
    test_object.root.assertTrue(
        b"You need to indicate the primary language" in res.body
    )

    # Post without setting one of the languages code does not pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        {
            "form_deflang": "default",
            "LNG-default": "es",
        },
        status=200,
    )
    test_object.root.assertTrue(
        b"You need to indicate a ISO 639-1 code for each language" in res.body
    )

    # Post without setting two languages with the same code fails
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        {
            "form_deflang": "default",
            "LNG-default": "es",
            "LNG-English": "es",
        },
        status=200,
    )
    test_object.root.assertTrue(
        b"Each language needs to have an unique ISO 639-1 code" in res.body
    )

    # Setting the language passes OK
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        {
            "form_deflang": "default",
            "LNG-default": "es",
            "LNG-English": "en",
        },
        status=302,
    )

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        status=200,
    )
    test_object.root.assertTrue(b" Merge repository " in res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica",
            "asistencia_tecnica",
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica",
            test_object.formID,
        ),
        status=404,
    )

    # Delete the form asistencia_tecnica
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete the form asistencia_tecnica
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica_no_lng"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
