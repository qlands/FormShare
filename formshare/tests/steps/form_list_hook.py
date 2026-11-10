"""A plugin chooses a form list for the device asking (IFormList).

FormShare Collect names its installation in every request
(X-FormShare-Device). Once core has chosen a list's forms, it hands them, with
the project, the assistant and that device, to every IFormList plugin
(docs/device-journeys.md 7.2). The test plugin stands in for a journey: of the
forms named hook_*, the device hook-device-1 is not offered hook_hidden, and
each of them names the device and the assistant in FormShare's namespace.

- a crowdsourcing project: with the device, with another, without one, and
  with a value no device has;
- a project with assistants: the assistant's forms, then the plugin;
- the answer says it varies with the header.
"""

import os
import shutil
import uuid

import openpyxl

FS_NAMESPACE = b"https://formshare.org/xforms/extensions"


def _workbook(path, form_id):
    wb = openpyxl.Workbook()
    survey = wb.active
    survey.title = "survey"
    survey.append(["type", "name", "label", "calculation"])
    survey.append(["calculate", "visit_id", "", "uuid()"])
    survey.append(["text", "note_text", "A note", ""])
    settings = wb.create_sheet("settings")
    settings.append(["form_id", "form_title", "version"])
    settings.append([form_id, form_id, "2026111001"])
    wb.save(path)


def _project(test_object, code, authentication):
    form = {
        "project_id": str(uuid.uuid4()),
        "project_code": code,
        "project_name": "A list chosen by a plugin",
        "project_abstract": "",
        "project_icon": "",
        "project_hexcolor": "",
    }
    if authentication:
        form["project_formlist_auth"] = 1
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin), form, status=302
    )
    assert "FS_error" not in res.headers
    return form["project_id"]


def _upload(test_object, work, code, form_id):
    xlsx = os.path.join(work, form_id + ".xlsx")
    _workbook(xlsx, form_id)
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, code),
        {"form_pkey": "visit_id"},
        status=302,
        upload_files=[("xlsx", xlsx)],
    )
    assert "FS_error" not in res.headers


def _form_list(test_object, code, device=None, **environ):
    headers = {"X-FormShare-Device": device} if device is not None else {}
    return test_object.testapp.get(
        "/user/{}/project/{}/formList".format(test_object.randonLogin, code),
        headers=headers,
        status=200,
        extra_environ=environ or None,
    )


def t_e_s_t_form_list_hook(test_object):
    work = os.path.join(test_object.working_dir, "form_list_hook")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)

    # --- A crowdsourcing project: no assistant asks --------------------------
    _project(test_object, "hook001", authentication=False)
    for form_id in ("hook_shown", "hook_hidden"):
        _upload(test_object, work, "hook001", form_id)

    res = _form_list(test_object, "hook001", "hook-device-1")
    assert b"<formID>hook_shown</formID>" in res.body
    assert b"<formID>hook_hidden</formID>" not in res.body
    assert b"hookdevice>hook-device-1</" in res.body
    assert b"hookassistant>none</" in res.body
    assert FS_NAMESPACE in res.body
    assert "X-FormShare-Device" in res.headers["Vary"]

    res = _form_list(test_object, "hook001", "hook-device-2")
    assert b"<formID>hook_shown</formID>" in res.body
    assert b"<formID>hook_hidden</formID>" in res.body
    assert res.body.count(b"hookdevice>hook-device-2</") == 2

    # No device named: the plugin passes every form as it came
    unnamed = _form_list(test_object, "hook001")
    assert b"<formID>hook_hidden</formID>" in unnamed.body
    assert FS_NAMESPACE not in unnamed.body
    # A value no device has counts as none
    res = _form_list(test_object, "hook001", "not a device!")
    assert res.body == unnamed.body

    # --- A project with assistants: the assistant's forms, then the plugin ---
    project_id = _project(test_object, "hook002", authentication=True)
    for form_id in ("hook_shown", "hook_hidden"):
        _upload(test_object, work, "hook002", form_id)
    assistant_uuid = str(uuid.uuid4())
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(test_object.randonLogin, "hook002"),
        {
            "coll_uuid": assistant_uuid,
            "coll_id": "hookassistant001",
            "coll_name": "hookassistant001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 3,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    for form_id in ("hook_shown", "hook_hidden"):
        res = test_object.testapp.post(
            "/user/{}/project/{}/form/{}/assistants/add".format(
                test_object.randonLogin, "hook002", form_id
            ),
            {
                "coll_id": "{}|{}|{}".format(
                    project_id, "hookassistant001", assistant_uuid
                ),
                "coll_can_submit": "1",
                "coll_can_clean": "0",
            },
            status=302,
        )
        assert "FS_error" not in res.headers

    res = _form_list(
        test_object,
        "hook002",
        "hook-device-1",
        FS_for_testing="true",
        FS_user_for_testing="hookassistant001",
    )
    assert b"<formID>hook_shown</formID>" in res.body
    assert b"<formID>hook_hidden</formID>" not in res.body
    assert "hookassistant>{}</".format(assistant_uuid).encode() in res.body
