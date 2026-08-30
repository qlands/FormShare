"""Offline entities, all the way through.

The parts that need no server are in `test_01_entities.py` and run in seconds.
This is the workflow: a project that opts in, a case creator form FormShare
declares an entity list in, a repository, a case registered the way a device
registers one offline, and follow-ups against it.

The point it exists to prove is the one that cannot be checked any other way:

    a case created offline is known to the device by a uuid the *device* minted,
    so that uuid has to become the row's rowuuid, and the follow-up trigger has
    to link on rowuuid, or a follow-up made offline is refused on arrival.

It is **not** part of the gate by default. `test_00_root` calls it only when

    export FORMSHARE_TEST_ENTITIES=true

Everything is built here rather than kept as fixtures, because the name of the
case list is derived from the project code -- a form that hard-coded it would
stop testing the contract the moment the derivation changed.

Uses its own project, `entity001`, so it cannot disturb `case001`.
"""

import os
import time
import uuid

from openpyxl import Workbook, load_workbook

PROJECT = "entity001"
CREATOR_ID = "entity_start_2026"
FOLLOWUP_ID = "entity_follow_up_2026"
WRONG_ID = "entity_wrong_file_2026"


def _write_workbook(path, survey_header, survey_rows, settings_row):
    workbook = Workbook()
    survey = workbook.active
    survey.title = "survey"
    survey.append(survey_header)
    for row in survey_rows:
        survey.append(row)
    settings = workbook.create_sheet("settings")
    settings.append(["form_title", "form_id", "version"])
    settings.append(settings_row)
    workbook.save(path)
    return path


def _creator_form(work_dir):
    """A case creator. No entities sheet: FormShare writes that itself."""
    return _write_workbook(
        os.path.join(work_dir, "entity_start.xlsx"),
        ["type", "name", "label", "required"],
        [
            ["text", "hid", "Household ID", "yes"],
            ["text", "fname", "Farmer name", "yes"],
            ["integer", "age", "Age", ""],
            ["date", "coll_date", "Date of collection", "yes"],
        ],
        ["Entity Household Start", CREATOR_ID, "1"],
    )


def _followup_form(work_dir, case_file, form_id, file_name):
    """A follow-up. The file it selects from is the contract under test."""
    return _write_workbook(
        os.path.join(work_dir, file_name),
        ["type", "name", "label", "required", "calculation"],
        [
            ["select_one_from_file " + case_file, "hid", "Case", "yes", ""],
            ["date", "fu_date", "Follow-up date", "yes", ""],
            ["calculate", "survey_id", "Survey ID", "", "concat(${hid},${fu_date})"],
            ["integer", "score", "Score", "", ""],
        ],
        ["Entity Household Follow-up", form_id, "1"],
    )


def _creator_submission(work_dir, dataset, case_uuid, hid, fname, name):
    """A registration as a device that made an entity sends one.

    The entity block is what a form carrying an entities sheet puts in its meta,
    and `id` is minted on the device at first load -- which is exactly why a case
    registered offline is referable before the server has ever seen it.
    """
    path = os.path.join(work_dir, name)
    with open(path, "w", encoding="utf8") as submission:
        submission.write(
            "<?xml version='1.0' ?>\n"
            '<data id="{form}" version="1">'
            "<hid>{hid}</hid><fname>{fname}</fname><age>25</age>"
            "<coll_date>2026-08-15</coll_date>"
            "<meta><instanceID>uuid:{instance}</instanceID>"
            '<entity dataset="{dataset}" create="1" id="{case}">'
            "<label>{fname}</label></entity></meta></data>".format(
                form=CREATOR_ID,
                hid=hid,
                fname=fname,
                instance=uuid.uuid4(),
                dataset=dataset,
                case=case_uuid,
            )
        )
    return path


def _followup_submission(work_dir, selector, fu_date, name):
    """A follow-up. `selector` is what the device stored from the select, which
    for an entity list is the entity's id."""
    path = os.path.join(work_dir, name)
    with open(path, "w", encoding="utf8") as submission:
        submission.write(
            "<?xml version='1.0' ?>\n"
            '<data id="{form}" version="1">'
            "<hid>{sel}</hid><fu_date>{date}</fu_date>"
            "<survey_id>{sel}{date}</survey_id><score>7</score>"
            "<meta><instanceID>uuid:{instance}</instanceID></meta></data>".format(
                form=FOLLOWUP_ID,
                sel=selector,
                date=fu_date,
                instance=uuid.uuid4(),
            )
        )
    return path


def t_e_s_t_entities(test_object):
    from formshare.processes.odk.entities import case_list_file_name, case_list_name

    login = test_object.randonLogin
    work = test_object.working_dir
    dataset = case_list_name(PROJECT)
    case_file = case_list_file_name(PROJECT)
    assistant = "entityassistant001"
    project_id = str(uuid.uuid4())
    assistant_uuid = str(uuid.uuid4())
    as_device = dict(FS_for_testing="true", FS_user_for_testing=assistant)

    # ------------------------------------------------------------ opting in
    res = test_object.testapp.get("/user/{}/projects/add".format(login), status=200)
    test_object.root.assertIn(b"project_entities", res.body)

    res = test_object.testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": project_id,
            "project_code": PROJECT,
            "project_name": "Entity project 001",
            "project_abstract": "",
            "project_case": "",
            "project_entities": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Entities without a case project is meaningless, and the view settles that
    # rather than trusting the form.
    res = test_object.testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": str(uuid.uuid4()),
            "project_code": "entity002",
            "project_name": "Not a case project",
            "project_abstract": "",
            "project_entities": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # ------------------------------------------------------------- assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(login, PROJECT),
        {
            "coll_uuid": assistant_uuid,
            "coll_id": assistant,
            "coll_name": assistant,
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 3,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # -------------------------------------------------- the case creator form
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {
            "form_pkey": "hid",
            "form_caselabel": "fname",
            "form_casedatetime": "coll_date",
        },
        status=302,
        upload_files=[("xlsx", _creator_form(work))],
    )
    assert "FS_error" not in res.headers

    # The declaration has to have reached the stored workbook, because that is
    # what the XForm the device downloads was built from.
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/odk".format(login, PROJECT, CREATOR_ID),
        status=200,
    )
    stored = os.path.join(work, "downloaded_creator.xlsx")
    with open(stored, "wb") as downloaded:
        downloaded.write(res.body)
    workbook = load_workbook(stored)
    assert "entities" in workbook.sheetnames, (
        "FormShare did not declare an entity list in the case creator. "
        "Sheets: {}".format(workbook.sheetnames)
    )
    assert workbook["entities"].cell(row=2, column=1).value == dataset

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(login, PROJECT, CREATOR_ID),
        {
            "coll_id": "{}|{}|{}".format(project_id, assistant, assistant_uuid),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            login, PROJECT, CREATOR_ID
        ),
        {"form_pkey": "hid", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Entities: waiting for the case creator repository")
    time.sleep(40)

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(login, PROJECT, CREATOR_ID), status=200
    )
    test_object.root.assertIn(b"With repository", res.body)

    # Settles which column is the case identifier and which labels it.
    test_object.testapp.get(
        "/user/{}/project/{}/caselookuptable".format(login, PROJECT), status=200
    )

    # ----------------------------------------------- a follow-up pointing away
    # It resolves no list at all and nothing reports it, so the upload is
    # refused instead, naming the file it should have used.
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "fu_date",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[
            ("xlsx", _followup_form(work, "somewhere_else.csv", WRONG_ID, "wrong.xlsx"))
        ],
    )
    assert "FS_error" in res.headers, (
        "A follow-up selecting from somewhere_else.csv was accepted. It should "
        "have been refused and told to select from {}".format(case_file)
    )

    # ------------------------------------------------------ the follow-up form
    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {
            "form_pkey": "survey_id",
            "form_caseselector": "hid",
            "form_casedatetime": "fu_date",
            "form_casetype": "2",
        },
        status=302,
        upload_files=[
            ("xlsx", _followup_form(work, case_file, FOLLOWUP_ID, "followup.xlsx"))
        ],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            login, PROJECT, FOLLOWUP_ID
        ),
        {
            "coll_id": "{}|{}|{}".format(project_id, assistant, assistant_uuid),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # The case list is a required file until FormShare starts generating it.
    placeholder = os.path.join(work, case_file)
    with open(placeholder, "w", encoding="utf8") as csv_file:
        csv_file.write("list_name,name,label,__version\n")
        csv_file.write("list_caseselector,empty,empty,1\n")
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(login, PROJECT, FOLLOWUP_ID),
        status=302,
        upload_files=[("filetoupload", placeholder)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(login, PROJECT, FOLLOWUP_ID), status=200
    )
    test_object.root.assertIn(b"Linked to the real-time CSV case file", res.body)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            login, PROJECT, FOLLOWUP_ID
        ),
        {"form_pkey": "survey_id", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Entities: waiting for the follow-up repository")
    time.sleep(40)

    # ------------------------------------ registering a case the offline way
    # The device mints the identity. This is the value the whole chain turns on.
    case_uuid = str(uuid.uuid4())
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(login, PROJECT),
        status=201,
        upload_files=[
            (
                "filetoupload",
                _creator_submission(
                    work, dataset, case_uuid, "HH-042", "Carlos", "start_01.xml"
                ),
            )
        ],
        extra_environ=as_device,
    )

    # ------------------------------------------------- what the device is sent
    res = test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(login, PROJECT, FOLLOWUP_ID),
        status=200,
        extra_environ=as_device,
    )
    manifest = res.body.decode()
    assert 'type="entityList"' in manifest, (
        "The manifest does not mark the case list as an entity list, so the "
        "client will treat it as an ordinary attachment:\n{}".format(manifest)
    )

    res = test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/{}".format(
            login, PROJECT, FOLLOWUP_ID, case_file
        ),
        status=200,
        extra_environ=as_device,
    )
    csv_body = res.body.decode()
    header = csv_body.splitlines()[0].split(",")
    for column in ("name", "label", "__version"):
        assert column in header, (
            "The case list is missing {!r}. A client that cannot find it "
            "discards the whole list without reporting anything. Header: "
            "{}".format(column, header)
        )
    assert case_uuid in csv_body, (
        "The case went out under a name the device does not know it by, so the "
        "device would register it a second time and keep both.\n{}".format(csv_body)
    )

    # ------------------------------------------------------- following it up
    # The selector carries what the device stored from the select: the entity
    # id. It reaches the trigger as the creator's rowuuid, and matches.
    res = test_object.testapp.post(
        "/user/{}/project/{}/push".format(login, PROJECT),
        status=201,
        upload_files=[
            (
                "filetoupload",
                _followup_submission(work, case_uuid, "2026-08-16", "follow_01.xml"),
            )
        ],
        extra_environ=as_device,
    )
    # An accepted-but-quarantined submission comes back with a message. This one
    # reached the repository, so there is nothing to say -- and if there is, the
    # trigger refused a follow-up made against the case that was just created.
    assert b"OpenRosaResponse" not in res.body, (
        "The follow-up did not reach the repository. The trigger is most likely "
        "still linking on the case identifier rather than on rowuuid.\n"
        "Body: {!r}".format(res.body)
    )

    # A follow-up for a case that does not exist is still accepted -- it is put
    # in the logs to be cleaned -- but the enumerator is told why.
    res = test_object.testapp.post(
        "/user/{}/project/{}/push".format(login, PROJECT),
        status=201,
        upload_files=[
            (
                "filetoupload",
                _followup_submission(
                    work, str(uuid.uuid4()), "2026-08-17", "follow_missing.xml"
                ),
            )
        ],
        extra_environ=as_device,
    )
    body = res.body.decode()
    assert "OpenRosaResponse" in body and "<message>" in body, (
        "A follow-up against a case that does not exist was accepted silently. "
        "The enumerator has no way to know it did not land.\nBody: {!r}".format(body)
    )
