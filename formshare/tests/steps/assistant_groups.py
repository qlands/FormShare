def t_e_s_t_assistant_groups(test_object):
    # Show the add group page
    res = test_object.testapp.get(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Add an assistant group fail. The description is empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"group_desc": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add an assistant group succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"group_desc": "Test if a group"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an assistant group fails. Group name already exists
    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"group_desc": "Test if a group"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Add an assistant group with code succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"group_desc": "Test if a group 2", "group_id": "grp001"},
        status=302,
    )
    assert "FS_error" not in res.headers
    test_object.assistantGroupID = "grp001"

    # Delete the group
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete the group using get
    test_object.testapp.get(
        "/user/{}/project/{}/group/{}/delete".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        status=404,
    )

    # Add an assistant group again
    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"group_desc": "Test if a group 2", "group_id": "grp001"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the assistant groups
    res = test_object.testapp.get(
        "/user/{}/project/{}/groups".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Get the assistant groups in edit mode
    res = test_object.testapp.get(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Edit the assistant group fails. The name already exists
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"group_desc": "Test if a group", "group_active": "1"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Edit the assistant group fails. Empty name
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"group_desc": "", "group_active": "1"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Edit the assistant group succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"group_desc": "Test if a group 3", "group_active": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Edit the assistant group succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"group_desc": "Test if a group 3"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Edit the assistant group succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"group_desc": "Test if a group 3", "group_active": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a member to a group fails. No assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"assistants": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Add a member to a group fails. Assistant is empty
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"assistants": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Add a member to a group fails. Collaborator does not exist
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {"assistants": "{}|hello2".format(test_object.projectID)},
        status=302,
    )
    assert "FS_error" in res.headers

    # Add a member to a group succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {
            "assistants": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Adding the same member to a group fails
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {
            "assistants": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Add a second member to a group succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        {
            "assistants": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin2
            ),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # List members
    res = test_object.testapp.get(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, test_object.project, test_object.assistantGroupID
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Remove a member
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.assistantGroupID,
            test_object.assistantLogin,
            test_object.projectID,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Remove a member using get
    test_object.testapp.get(
        "/user/{}/project/{}/group/{}/member/{}/of/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.assistantGroupID,
            test_object.assistantLogin,
            test_object.projectID,
        ),
        status=404,
    )
