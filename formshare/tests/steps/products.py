from .sql import get_last_task


def t_e_s_t_products(test_object):
    # Private download: non-existent project goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
            test_object.randonLogin,
            "not_exist",
            test_object.formID,
            "xlsx_public_export",
            "not_exist",
        ),
        status=404,
    )

    # Private download: non-existent output_id goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "not_exist",
        ),
        status=404,
    )

    # Get the last xlsx product created during repository_downloads
    last_task = get_last_task(
        test_object.server_config,
        test_object.projectID,
        test_object.formID,
        "xlsx_public_export",
    )
    output_id = last_task[-12:]

    # Publish the product (non-existent project → 404)
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
            test_object.randonLogin,
            "not_exist",
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=404,
    )

    # Publish the product (non-existent output → 404)
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "not_exist",
        ),
        status=404,
    )

    # Publish with GET → 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=404,
    )

    # Publish succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Public download: non-existent output → 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "not_exist",
        ),
        status=404,
    )

    # Public download succeeds (product is now published)
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=200,
    )

    # Unpublish: non-existent project → 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
            test_object.randonLogin,
            "not_exist",
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=404,
    )

    # Unpublish: non-existent output → 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "not_exist",
        ),
        status=404,
    )

    # Unpublish with GET → 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=404,
    )

    # Unpublish succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete: non-existent project → 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
            test_object.randonLogin,
            "not_exist",
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=404,
    )

    # Delete: non-existent output → 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "not_exist",
        ),
        status=404,
    )

    # Delete with GET → 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=404,
    )

    # Delete succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            output_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
