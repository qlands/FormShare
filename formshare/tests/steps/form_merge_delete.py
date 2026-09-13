import os


def t_e_s_t_form_merge_delete(test_object):
    paths = ["resources", "forms", "merge", "B", "B.xls"]
    b_resource_file = os.path.join(test_object.path, *paths)

    # An assistant on the head form, for the new version to inherit
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {
            "coll_id": "{}|{}|{}".format(
                test_object.projectID,
                test_object.assistantLogin,
                test_object.assistantLoginUUID,
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # A new version that keeps the assistants and the files of its parent
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "tormenta20201105",
            "keep_assistants": "",
            "keep_files": "",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # The assistant came along: it cannot be added a second time
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        {
            "coll_id": "{}|{}|{}".format(
                test_object.projectID,
                test_object.assistantLogin,
                test_object.assistantLoginUUID,
            ),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # So did the files: the same file is refused without overwrite
    paths = ["resources", "forms", "merge", "B", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" in res.headers

    # Delete this version and the assistant, then start over without them
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201105",
            test_object.assistantLoginUUID,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

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

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Merge check pending" in res.body)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
