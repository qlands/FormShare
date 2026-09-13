"""Forms the form checker refuses with codes no other form in the suite
produces.

The checker is jxformtomysql. Each exit code has a handler in
formshare/processes/odk/api.py that turns the checker's XML report into the
message the user reads, and the forms here are the smallest that make the
checker return that code. The checker still returns them: pyxform rewrites
"or other" selects before the checker sees them, so code 35 is not among
these, and codes 2, 21 and 29 are no longer returned at all.
"""

import os


def t_e_s_t_exit_codes(test_object):
    login = test_object.randonLogin
    project = test_object.project
    testapp = test_object.testapp
    resources = os.path.join(test_object.path, "resources", "forms", "exit_codes")

    # 20: a question called rowuuid, a name FormShare keeps for itself, and
    # one with a hyphen, which no column can carry
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, project),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", os.path.join(resources, "reserved_names.xlsx"))],
    )
    assert "FS_error" in res.headers

    # 14: a CSV whose column heading has a space in it. The form is accepted
    # and so is the file; the check that runs once the file is there is not
    form_url = "/user/{}/project/{}/form/{}".format(login, project, "bad_csv_form")
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, project),
        {"form_pkey": "hid"},
        status=302,
        upload_files=[("xlsx", os.path.join(resources, "bad_csv.xlsx"))],
    )
    assert "FS_error" not in res.headers
    # The check is only shown once someone could collect data with the form
    res = testapp.post(
        form_url + "/assistants/add",
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
    assert "FS_error" not in res.headers
    res = testapp.get(form_url, status=200)
    assert b"Repository check pending" in res.body
    res = testapp.post(
        form_url + "/upload",
        status=302,
        upload_files=[("filetoupload", os.path.join(resources, "bad.csv"))],
    )
    assert "FS_error" not in res.headers
    res = testapp.get(form_url, status=200)
    assert b"This form cannot create a repository" in res.body
    assert b"invalid characters in column headers" in res.body

    res = testapp.post(form_url + "/delete", status=302)
    assert "FS_error" not in res.headers
