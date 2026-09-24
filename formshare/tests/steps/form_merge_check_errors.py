import os

from .sql import get_form_details
from .unwritable_output import (
    make_unwritable,
    make_writable,
    tool_reports_unwritable_files,
)


def _unwritable_merge_files(test_object):
    """38 on both merge paths (rstools.md 17.2), with a directory where the
    new version's manifest goes. The merge check names the file and keeps no
    verdict, so the version is checked again once the server can write; the
    merge page says the same and merges nothing."""
    login = test_object.randonLogin
    project = test_object.project
    testapp = test_object.testapp
    form_url = "/user/{}/project/{}/form/{}".format(login, project, "tormenta20201117")
    res = testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(login, project, "tormenta20201105"),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "tormenta20201105",
        },
        status=302,
        upload_files=[
            (
                "xlsx",
                os.path.join(
                    test_object.path, "resources", "forms", "merge", "B", "B.xls"
                ),
            )
        ],
    )
    assert "FS_error" not in res.headers
    for a_file in ("cantones.csv", "distritos.csv"):
        res = testapp.post(
            form_url + "/upload",
            status=302,
            upload_files=[
                (
                    "filetoupload",
                    os.path.join(
                        test_object.path, "resources", "forms", "merge", "B", a_file
                    ),
                )
            ],
        )
        assert "FS_error" not in res.headers
    directory = get_form_details(
        test_object.server_config, test_object.projectID, "tormenta20201117"
    )["form_directory"]
    manifest = os.path.join(
        test_object.server_config["repository.path"],
        "odk",
        "forms",
        directory,
        "repository",
        "manifest.xml",
    )

    # The merge check
    make_unwritable(manifest)
    try:
        res = testapp.get(form_url, status=200)
    finally:
        make_writable(manifest)
    test_object.root.assertTrue(b"Unable to merge" in res.body)
    assert b"not with your form" in res.body
    assert b"manifest.xml" in res.body and b"Is a directory" in res.body
    assert manifest.encode("utf-8") not in res.body
    res = testapp.get(form_url, status=200)
    test_object.root.assertFalse(b"Unable to merge" in res.body)

    # The merge itself
    make_unwritable(manifest)
    try:
        res = testapp.post(
            form_url + "/merge/into/tormenta20201105",
            {"discard_testing_data": ""},
            status=302,
        )
    finally:
        make_writable(manifest)
    assert "FS_error" in res.headers
    res = res.follow(status=200)
    assert b"not with your form" in res.body
    assert b"manifest.xml" in res.body and b"Is a directory" in res.body
    assert manifest.encode("utf-8") not in res.body
    assert (
        get_form_details(
            test_object.server_config, test_object.projectID, "tormenta20201117"
        )["form_schema"]
        is None
    )

    res = testapp.post(form_url + "/delete", status=302)
    assert "FS_error" not in res.headers


def t_e_s_t_form_merge_check_errors(test_object):
    # Check upload form for merge is bad
    paths = ["resources", "forms", "merge", "B", "B_bad.xls"]
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
    assert "FS_error" in res.headers

    # Check table not the same
    paths = ["resources", "forms", "merge", "B", "B_TNS.xls"]
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

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Unable to merge" in res.body)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    #  Checks for field not the same
    paths = ["resources", "forms", "merge", "B", "B_FNS.xls"]
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

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Unable to merge" in res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201117",
            "tormenta20201105",
        ),
        status=404,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    #  Checks for relation not the same
    paths = ["resources", "forms", "merge", "B", "B_RNS.xls"]
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

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Unable to merge" in res.body)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # 38: a file of the new version could not be written (rstools.md 17.2)
    if tool_reports_unwritable_files(
        test_object.server_config["odktools.path"], test_object.working_dir
    ):
        _unwritable_merge_files(test_object)
