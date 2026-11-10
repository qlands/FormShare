"""A form written for ODK Central's entities, through the web routes.

Such a form uploads like any other, and FormShare does nothing of its
entities (formshare.md 3.6). Its page says what to set up instead, in its
own names (processes/odk/foreign_entities.py, 2026-11-10):

- the registration, which creates the entities of the list trees, is told to
  publish trees.csv from itself, with the columns its save_to names;
- the follow-up, which updates them, is told to publish the list from the
  form that registers the cases, to link it, and to add an action for each
  value it saves;
- the names come from the workbook, so the page prints them as text.

The test of what each declaration says, and of when the steps are done, is
test_24_central_entities.py; this one proves the page shows it.
"""

import os
import shutil
import uuid

import openpyxl

PROJECT = "central001"


def _workbook(path, form_id, survey, entities, choices=None):
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "survey"
    for row in survey:
        sheet.append(row)
    if choices:
        sheet = wb.create_sheet("choices")
        for row in choices:
            sheet.append(row)
    sheet = wb.create_sheet("entities")
    for row in entities:
        sheet.append(row)
    sheet = wb.create_sheet("settings")
    sheet.append(["form_id", "form_title", "version"])
    sheet.append([form_id, form_id, "2026111001"])
    wb.save(path)


def t_e_s_t_central_entities(test_object):
    login = test_object.randonLogin
    testapp = test_object.testapp
    work = os.path.join(test_object.working_dir, "central_entities")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)

    # A project of its own, so no other step counts these forms
    res = testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": str(uuid.uuid4()),
            "project_code": PROJECT,
            "project_name": "Forms written for ODK Central",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # --- The registration ---------------------------------------------------
    xlsx = os.path.join(work, "trees_registration.xlsx")
    _workbook(
        xlsx,
        "trees_registration",
        [
            ["type", "name", "label", "save_to", "calculation"],
            ["calculate", "tree_id", "", "", "uuid()"],
            ["text", "species", "Species", "species", ""],
            ["integer", "height", "Height (m)", "height", ""],
            ["geopoint", "location", "Location", "geometry", ""],
        ],
        [["list_name", "label"], ["trees", "concat(${species}, ' <b>', ${height})"]],
    )
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {"form_pkey": "tree_id"},
        status=302,
        upload_files=[("xlsx", xlsx)],
    )
    assert "FS_error" not in res.headers

    res = testapp.get(
        "/user/{}/project/{}/form/{}".format(login, PROJECT, "trees_registration"),
        status=200,
    )
    test_object.root.assertIn(b"Written for ODK Central", res.body)
    test_object.root.assertIn(
        b"it creates entities in the list &#34;trees&#34;.", res.body
    )
    test_object.root.assertIn(
        b"Publish a list named &#34;trees.csv&#34; from this form.", res.body
    )
    test_object.root.assertIn(
        b"Serve these columns: species, height, location as geometry.", res.body
    )
    # The label is the workbook's: printed as text, never as markup
    test_object.root.assertIn(b"&#39; &lt;b&gt;&#39;", res.body)
    test_object.root.assertNotIn(b"' <b>'", res.body)
    test_object.root.assertIn(
        "/user/{}/project/{}/caselists".format(login, PROJECT).encode(), res.body
    )

    # --- The follow-up, which updates the trees -----------------------------
    xlsx = os.path.join(work, "trees_followup.xlsx")
    _workbook(
        xlsx,
        "trees_followup",
        [
            ["type", "name", "label", "save_to", "calculation"],
            ["calculate", "visit_id", "", "", "uuid()"],
            ["select_one_from_file trees.csv", "tree", "Tree", "", ""],
            ["select_one status", "status", "Status", "status", ""],
        ],
        [["list_name", "entity_id"], ["trees", "${tree}"]],
        [
            ["list_name", "name", "label"],
            ["status", "alive", "Alive"],
            ["status", "dead", "Dead"],
        ],
    )
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {"form_pkey": "visit_id"},
        status=302,
        upload_files=[("xlsx", xlsx)],
    )
    assert "FS_error" not in res.headers

    res = testapp.get(
        "/user/{}/project/{}/form/{}".format(login, PROJECT, "trees_followup"),
        status=200,
    )
    test_object.root.assertIn(
        b"it updates entities of the list &#34;trees&#34;, the one named by "
        b"${tree}.",
        res.body,
    )
    test_object.root.assertIn(
        b"Publish a list named &#34;trees.csv&#34; from the form that registers "
        b"these cases.",
        res.body,
    )
    test_object.root.assertIn(
        b"Add an action for each value it saves to the case: status.", res.body
    )
    test_object.root.assertIn(
        "/user/{}/project/{}/form/{}/caselinks".format(
            login, PROJECT, "trees_followup"
        ).encode(),
        res.body,
    )
    test_object.root.assertIn(
        "/user/{}/project/{}/form/{}/actions".format(
            login, PROJECT, "trees_followup"
        ).encode(),
        res.body,
    )
