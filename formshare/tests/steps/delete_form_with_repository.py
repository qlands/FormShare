def t_e_s_t_delete_form_with_repository(test_object):
    # Delete the form
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(
            test_object.randonLogin, test_object.project, "ADANIC_ALLMOD_20141020"
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
