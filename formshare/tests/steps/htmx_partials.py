"""The form access pages answer htmx with a trigger instead of a redirect.

A request with HX-Request: true comes from a fragment of the form page. The
view does the same work but, instead of redirecting, it sets HX-Trigger so
the page reloads the fragment or shows the message.
"""

HTMX = {"HX-Request": "true"}


def t_e_s_t_htmx_partials(test_object):
    testapp = test_object.testapp
    form_url = "/user/{}/project/{}/form/{}".format(
        test_object.randonLogin, test_object.project, test_object.formID
    )
    assistant = "{}|{}|{}".format(
        test_object.projectID,
        test_object.assistantLogin2,
        test_object.assistantLogin2UUID,
    )

    # ---- assistants
    # No privilege at all
    res = testapp.post(
        form_url + "/assistants/add", {"coll_id": assistant}, headers=HTMX, status=200
    )
    assert "formshare:notify" in res.headers["HX-Trigger"]
    # No assistant at all
    res = testapp.post(
        form_url + "/assistants/add", {"coll_id": ""}, headers=HTMX, status=200
    )
    assert "formshare:notify" in res.headers["HX-Trigger"]
    # Added: the form already had one assistant, so the list is refreshed
    res = testapp.post(
        form_url + "/assistants/add",
        {"coll_id": assistant, "coll_can_submit": "1"},
        headers=HTMX,
        status=200,
    )
    assert "formshare:assistants-updated" in res.headers["HX-Trigger"]
    # Added again is an error
    res = testapp.post(
        form_url + "/assistants/add",
        {"coll_id": assistant, "coll_can_submit": "1"},
        headers=HTMX,
        status=200,
    )
    assert "formshare:notify" in res.headers["HX-Trigger"]

    edit_url = form_url + "/assistant/{}/edit".format(test_object.assistantLogin2UUID)
    # Edited with no privilege
    res = testapp.post(edit_url, {}, headers=HTMX, status=200)
    assert "formshare:notify" in res.headers["HX-Trigger"]
    # Edited
    res = testapp.post(edit_url, {"coll_can_clean": "1"}, headers=HTMX, status=200)
    assert "formshare:assistants-updated" in res.headers["HX-Trigger"]

    remove_url = form_url + "/assistant/{}/remove".format(
        test_object.assistantLogin2UUID
    )
    # Removed: one assistant is left, so the list is refreshed
    res = testapp.post(remove_url, {}, headers=HTMX, status=200)
    assert "formshare:assistants-updated" in res.headers["HX-Trigger"]

    # ---- groups
    group = test_object.assistantGroupID
    # No privilege at all
    res = testapp.post(
        form_url + "/groups/add", {"group_id": group}, headers=HTMX, status=200
    )
    assert "formshare:notify" in res.headers["HX-Trigger"]
    # No group at all, and no group field at all
    res = testapp.post(
        form_url + "/groups/add", {"group_id": ""}, headers=HTMX, status=200
    )
    assert "formshare:notify" in res.headers["HX-Trigger"]
    res = testapp.post(form_url + "/groups/add", {}, headers=HTMX, status=200)
    assert "formshare:notify" in res.headers["HX-Trigger"]
    # Added: the first group, so the page reloads
    res = testapp.post(
        form_url + "/groups/add",
        {"group_id": group, "group_can_submit": "1"},
        headers=HTMX,
        status=200,
    )
    assert "formshare:full-reload" in res.headers["HX-Trigger"]
    # Added again is an error
    res = testapp.post(
        form_url + "/groups/add",
        {"group_id": group, "group_can_submit": "1"},
        headers=HTMX,
        status=200,
    )
    assert "formshare:notify" in res.headers["HX-Trigger"]

    group_edit_url = form_url + "/group/{}/edit".format(group)
    # Edited with no privilege
    res = testapp.post(group_edit_url, {}, headers=HTMX, status=200)
    assert "formshare:notify" in res.headers["HX-Trigger"]
    # Edited
    res = testapp.post(
        group_edit_url, {"group_can_clean": "1"}, headers=HTMX, status=200
    )
    assert "formshare:groups-updated" in res.headers["HX-Trigger"]

    group_remove_url = form_url + "/group/{}/remove".format(group)
    # Removed: no group is left, so the page reloads
    res = testapp.post(group_remove_url, {}, headers=HTMX, status=200)
    assert "formshare:full-reload" in res.headers["HX-Trigger"]
