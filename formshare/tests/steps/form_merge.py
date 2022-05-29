import os
import time


def t_e_s_t_form_merge(test_object):
    # Upload B***********************************************

    paths = ["resources", "forms", "merge", "B", "B.xls"]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "tormenta20201105",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Merge check pending" in res.body)

    paths = ["resources", "forms", "merge", "B", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "merge", "B", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Removes a required file from a form to be merged
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201117",
            "distritos.csv",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add the file again
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Merge check pending" in res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            "not_exist",
            "tormenta20201117",
            "tormenta20201105",
        ),
        status=404,
    )

    # Show the merge repository page
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201117",
            "tormenta20201105",
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Merge the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201117",
            "tormenta20201105",
            "discard_testing_data",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for the merge to finish

    # Get the details of a form tormenta20201117
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"This is the sub-version of" in res.body)

    # Compare goes to 404 project not found
    test_object.testapp.get(
        "/user/{}/project/{}/compare/from/{}/to/{}".format(
            test_object.randonLogin,
            "Not_found",
            "tormenta20201105",
            "tormenta20201117",
        ),
        status=404,
    )

    # Compare goes to 404 form not found
    test_object.testapp.get(
        "/user/{}/project/{}/compare/from/{}/to/{}".format(
            test_object.randonLogin,
            test_object.project,
            "not_found",
            "tormenta20201117",
        ),
        status=404,
    )

    # Compare the changes between Forms
    res = test_object.testapp.get(
        "/user/{}/project/{}/compare/from/{}/to/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201105",
            "tormenta20201117",
        ),
        status=200,
    )
    test_object.root.assertTrue(
        b"This new version does not have any structural changes" not in res.body
    )

    # Get the details of a form tormenta20201105
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"is the sub-version of this form" in res.body)

    # Gets the details of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, test_object.project),
        status=200,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {"form_target": "", "form_hexcolor": "#c18097"},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/edit".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        {"form_target": "", "form_hexcolor": "#c18097"},
        status=302,
    )
    assert "FS_error" not in res.headers

    #  Merge C with an ignore string message *************************************
    paths = ["resources", "forms", "merge", "C", "C.xls"]
    c_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "tormenta20201117",
        },
        status=302,
        upload_files=[("xlsx", c_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Merge check pending" in res.body)

    paths = ["resources", "forms", "merge", "C", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "merge", "C", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Merge check pending" in res.body)

    # Merge the repository using celery fails with message about values to ignore
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201130",
            "tormenta20201117",
        ),
        status=200,
    )
    assert "FS_error" not in res.headers
    test_object.root.assertTrue(b"There are changes in the descriptions" in res.body)

    # Merge the repository using celery passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201130",
            "tormenta20201117",
        ),
        {"valuestoignore": "lkplista_de_bancos:8"},
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for the merge to finish

    # Get the details of a form tormenta20201117
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"This is the sub-version of" in res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, test_object.project),
        status=200,
    )

    res = test_object.testapp.get(
        "/user/{}".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, "not_exist", "tormenta20201130"
        ),
        {"owner_email": test_object.randonLogin + "@qlands.com"},
        status=404,
    )

    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        {"owner_email": test_object.randonLogin + "@qlands.com"},
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=404,
    )

    # Remove all submissions no email
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        {},
        status=302,
    )
    assert "FS_error" in res.headers

    # Remove all submissions
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/submissions/deleteall".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        {"owner_email": test_object.randonLogin + "@qlands.com"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the details of a form tormenta20201117
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Without submissions" in res.body)

    # Delete the form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "tormenta20201130"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
