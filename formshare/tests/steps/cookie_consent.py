def t_e_s_t_cookie_consent(test_object):
    # Save consent for the first time (new record path)
    res = test_object.testapp.post(
        "/cookie/consent",
        {"functional": "1", "analytical": "1", "marketing": "1"},
        status=200,
    )
    assert "FS_error" not in res.headers

    # Save consent again from same session/IP (update existing record path)
    res = test_object.testapp.post(
        "/cookie/consent",
        {"functional": "1", "analytical": "0", "marketing": "0"},
        status=200,
    )
    assert "FS_error" not in res.headers

    # Save consent with action field
    res = test_object.testapp.post(
        "/cookie/consent",
        {
            "functional": "1",
            "analytical": "1",
            "marketing": "1",
            "action": "all",
        },
        status=200,
    )
    assert "FS_error" not in res.headers
