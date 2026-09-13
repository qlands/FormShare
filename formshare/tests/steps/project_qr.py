def t_e_s_t_project_qr(test_object):
    """The QR settings of a project: the page, a save, and a reset.

    The QR carries the ODK Collect settings the project hands out, and this
    is the only place they are edited.
    """
    # The QR image itself
    test_object.testapp.get(
        "/user/{}/project/{}/qr".format(test_object.randonLogin, test_object.project),
        status=200,
    )

    # Editing the QR of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/qr/edit".format(test_object.randonLogin, "not_exist"),
        status=404,
    )

    # The edit page
    res = test_object.testapp.get(
        "/user/{}/project/{}/qr/edit".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Save every option ticked
    res = test_object.testapp.post(
        "/user/{}/project/{}/qr/edit".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "odk_delete_after_send": "on",
            "odk_update_auto": "on",
            "odk_hide_old": "on",
            "odk_high_res_video": "on",
            "odk_audio_app": "on",
            "odk_auto_send": "1",
            "odk_update_mode": "2",
            "odk_update_period": "2",
            "odk_navigation": "1",
            "odk_image_size": "2",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Save with every option cleared
    res = test_object.testapp.post(
        "/user/{}/project/{}/qr/edit".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "odk_auto_send": "0",
            "odk_update_mode": "3",
            "odk_update_period": "3",
            "odk_navigation": "2",
            "odk_image_size": "3",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Back to the defaults
    res = test_object.testapp.post(
        "/user/{}/project/{}/qr/edit".format(
            test_object.randonLogin, test_object.project
        ),
        {"set_default": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    # The QR with the defaults back in place
    test_object.testapp.get(
        "/user/{}/project/{}/qr".format(test_object.randonLogin, test_object.project),
        status=200,
    )
