import os
import time


def t_e_s_t_multilanguage_odk(test_object):
    # Upload a multi-language form fails because the language is malformed
    paths = ["resources", "forms", "multi_language", "ODK_simple_lng_bad.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "cedula"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" in res.headers

    # Upload a multi-language form succeeds
    paths = ["resources", "forms", "multi_language", "spanish_english.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "QID"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    test_object.formMultiLanguageID = "ADANIC_ALLMOD_20141020"

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formMultiLanguageID,
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

    # Generate the repository using celery fails due to language
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formMultiLanguageID,
        ),
        {"form_pkey": "QID", "start_stage1": ""},
        status=200,
    )
    test_object.root.assertIn(b"English", res.body)

    # Generate the repository using celery pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formMultiLanguageID,
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
    time.sleep(60)  # Waiting for Celery to create the repository

    # Get the details of a form. The form now should have a repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formMultiLanguageID,
        ),
        status=200,
    )
    test_object.root.assertTrue(b"With repository" in res.body)

    # Upload a multi-language form with complex languages succeeds
    paths = ["resources", "forms", "multi_language", "ODK_simple_lng_ext.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "cedula"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin,
            test_object.project,
            "prueba_simple_lng_ext",
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

    # Generate the repository using celery fails due to language
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin,
            test_object.project,
            "prueba_simple_lng_ext",
        ),
        {"form_pkey": "cedula", "start_stage1": ""},
        status=200,
    )
    test_object.root.assertIn(b"Texmelucan", res.body)

    # Generate the repository using celery pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin,
            test_object.project,
            "prueba_simple_lng_ext",
        ),
        {
            "form_pkey": "cedula",
            "start_stage2": "",
            "form_deflang": "Zapotec-Texmelucan",
            "LNG-English-USA": "en-us",
            "LNG-Spanish": "es",
            "LNG-Zapotec-Texmelucan": "zpz",
            "languages_string": '[{"code": "en-us", "name": "English-USA"}, '
            '{"code": "es", "name": "Spanish"}, '
            '{"code": "zpz", "name": "Zapotec-Texmelucan"}]',
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    time.sleep(60)  # Waiting for Celery to create the repository

    # Get the details of a form. The form now should have a repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "prueba_simple_lng_ext"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"With repository" in res.body)
