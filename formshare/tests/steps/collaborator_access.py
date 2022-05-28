def t_e_s_t_collaborator_access(test_object):
    # Test logout
    test_object.testapp.get("/logout", status=302)

    # Login succeed by collaborator
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.collaboratorLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
