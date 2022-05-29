import os
import time


def t_e_s_t_form_merge_language_control_3(test_object):
    # Uploads a form with a default language
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica.xlsx",
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

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        {
            "form_pkey": "control",
            "start_stage2": "",
            "form_deflang": "default",
            "LNG-default": "es",
            "LNG-English": "en",
            "languages_string": '[{"code": "", "name": "default"}, {"code": "", "name": "English"}]',
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for celery to generate the repository

    print("Testing merge of language cases")

    # Merge a form that changes the language
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "asistencia_tecnica_2_complete_language.xlsx",
    ]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "asistencia_tecnica",
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
            "asistencia_tecnica_2_complete_language",
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Merge check pending" in res.body)

    # Uploads an external file that label::
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "bad",
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
    test_object.root.assertFalse(b"Fix language" in res.body)

    # Removes a file from a form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
            "provincia.csv",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # ---------------------------
    # Uploads an external file that label::
    paths = [
        "resources",
        "forms",
        "merge_multilanguaje",
        "duplicated",
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
    test_object.root.assertFalse(b"Fix language" in res.body)

    # Removes a file from a form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
            "provincia.csv",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    # -------------------------

    # Uploads an external file that is fine
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

    # Get the page for fixing the language pass
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=200,
    )
    test_object.root.assertTrue(
        b"without indicating a language. For example if you have a column called"
        in res.body
    )

    # Setting the language passes OK
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/fix_languages".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        {
            "form_deflang": "Español",
            "LNG-Español": "es",
            "LNG-English": "en",
        },
        status=302,
    )

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=200,
    )
    test_object.root.assertTrue(b" Merge repository " in res.body)

    # Delete the form asistencia_tecnica
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            "asistencia_tecnica_2_complete_language",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete the form asistencia_tecnica
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "asistencia_tecnica"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
