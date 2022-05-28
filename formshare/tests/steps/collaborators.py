def t_e_s_t_collaborators(test_object):
    # Add a collaborator fails. Collaborator in empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add collaborator fails. Collaborators is not found or inactive
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": "", "collaborator": "not_exist"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a collaborato to an project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, "not_exist_project"
        ),
        {"add_collaborator": "", "collaborator": test_object.collaboratorLogin},
        status=404,
    )

    # Add a collaborator succeed
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": "", "collaborator": test_object.collaboratorLogin},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a collaborator fails. Collaborator already exists
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": "", "collaborator": test_object.collaboratorLogin},
        status=200,
    )
    assert "FS_error" in res.headers

    # Change the role of a collaborator
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "change_role": "",
            "collaborator_id": test_object.collaboratorLogin,
            "role_collaborator": 2,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the collaborators
    res = test_object.testapp.get(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Remove the collaborator of a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            test_object.randonLogin, "not_exist_project", test_object.collaboratorLogin
        ),
        status=404,
    )

    # Remove collaborator with GET goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.collaboratorLogin
        ),
        status=404,
    )

    # Remove the collaborator
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborator/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.collaboratorLogin
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a collaborator again to be used later on
    res = test_object.testapp.post(
        "/user/{}/project/{}/collaborators".format(
            test_object.randonLogin, test_object.project
        ),
        {"add_collaborator": "", "collaborator": test_object.collaboratorLogin},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the available collaborators
    test_object.testapp.get(
        "/user/{}/api/select2_user?q={}".format(
            test_object.randonLogin, test_object.collaboratorLogin
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/api/select2_user?q={}".format(test_object.randonLogin, "not_exists"),
        status=200,
    )

    # Get the available collaborators
    test_object.testapp.get(
        "/user/{}/api/select2_user".format(test_object.randonLogin),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/api/select2_user?include_me=True".format(
            test_object.randonLogin, test_object.collaboratorLogin
        ),
        status=200,
    )
