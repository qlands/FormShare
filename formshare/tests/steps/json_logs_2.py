import json
import os
import time
import uuid

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details


def t_e_s_t_json_logs_2(test_object):
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Adds a mimic2 project
    json2_project = "json2"
    json2_project_id = str(uuid.uuid4())
    mimic_res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_id": json2_project_id,
            "project_code": json2_project,
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers
    # Add the mimic form
    mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
    resource_file = os.path.join(test_object.path, *mimic_paths)
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, json2_project),
        {"form_pkey": "I_D"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in mimic_res.headers
    json2_form = "LB_Sequia_MAG_20190123"

    # Uploads a file to the form
    paths = ["resources", "forms", "complex_form", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Uploads a file to the form
    paths = ["resources", "forms", "complex_form", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, json2_project
        ),
        {
            "coll_id": "json2001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Add an assistant to a form succeeds
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {
            "coll_id": "{}|{}".format(json2_project_id, "json2001"),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, json2_project
        ),
        {
            "coll_id": "json2002",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Add an assistant to a form succeeds
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {
            "coll_id": "{}|{}".format(json2_project_id, "json2002"),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, json2_project
        ),
        {
            "coll_id": "json2003",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Add an assistant to a form succeeds
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {
            "coll_id": "{}|{}".format(json2_project_id, "json2003"),
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {"form_pkey": "I_D", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for Celery to finish

    # Upload submission 1
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_logs2",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing="json2001"),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    # Upload submission 2 goes to logs
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_logs2",
        "submission002.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing="json2001"),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    # Upload submission 3 goes to logs
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_logs2",
        "submission003.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing="json2001"),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    # Upload submission 4 goes to logs
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_logs2",
        "submission004.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, json2_project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing="json2001"),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, json2_project
        ),
        {"login": "json2001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Assistant does not have access to a form
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Load compare submission
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin, test_object.project, test_object.formID, ""
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=error".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    form_details = get_form_details(
        test_object.server_config, json2_project_id, json2_form
    )

    engine = create_engine(
        test_object.server_config["sqlalchemy.url"], poolclass=NullPool
    )
    sql = "SELECT surveyid FROM {}.maintable WHERE i_d = '109750690'".format(
        form_details["form_schema"]
    )
    res = engine.execute(sql).first()
    survey_id = res[0]

    sql = (
        "SELECT submission_id FROM formshare.submission "
        "WHERE submission_status = 2 AND sameas IS NULL AND project_id = '{}' AND form_id = '{}'".format(
            json2_project_id, json2_form
        )
    )
    res = engine.execute(sql).fetchall()
    duplicated_ids = []
    for a_duplicate in res:
        duplicated_ids.append(a_duplicate[0])
    engine.dispose()
    index = 0
    for a_duplicate in duplicated_ids:
        index = index + 1

        # Checkout with get goes to 404
        test_object.testapp.get(
            "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                test_object.randonLogin, json2_project, json2_form, a_duplicate
            ),
            status=404,
        )

        res = test_object.testapp.post(
            "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
                test_object.randonLogin, json2_project, json2_form, a_duplicate
            ),
            status=302,
        )
        assert "FS_error" not in res.headers

        test_object.testapp.get(
            "/user/{}/project/{}/assistantaccess/form/{}/errors?status=checkout".format(
                test_object.randonLogin, json2_project, json2_form
            ),
            status=200,
        )

        res = test_object.testapp.get(
            "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
                test_object.randonLogin, json2_project, json2_form, a_duplicate
            ),
            status=200,
        )
        data = json.loads(res.body)
        data[
            "si_participa/section_household_info/RespondentDetails/I_D"
        ] = "109750690ABC{}".format(index)
        paths = ["tmp", a_duplicate + ".json"]
        submission_file = os.path.join(test_object.path, *paths)

        with open(submission_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        sequence_id = str(uuid.uuid4())
        sequence_id = sequence_id[-12:]

        # Checkin the file
        res = test_object.testapp.post(
            "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
                test_object.randonLogin, json2_project, json2_form, a_duplicate
            ),
            {
                "notes": "This is not the same as submission: {}. Corrected ID".format(
                    survey_id
                ),
                "sequence": sequence_id,
            },
            status=302,
            upload_files=[("json", submission_file)],
        )
        assert "FS_error" not in res.headers
        time.sleep(3)

        # Get the checked in only
        test_object.testapp.get(
            "/user/{}/project/{}/assistantaccess/form/{}/errors?status=checkin".format(
                test_object.randonLogin, json2_project, json2_form
            ),
            status=200,
        )

        # Get all logs
        test_object.testapp.get(
            "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
                test_object.randonLogin, json2_project, json2_form
            ),
            status=200,
        )

        os.remove(submission_file)

        # Push the revision.
        res = test_object.testapp.post(
            "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
                test_object.randonLogin,
                json2_project,
                json2_form,
                a_duplicate,
                sequence_id,
            ),
            status=302,
        )
        assert "FS_error" not in res.headers
        time.sleep(5)  # Wait for ElasticSearch to store this

    # Get all logs
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, json2_project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, json2_project
        ),
        {"login": "json2002", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, json2_project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, json2_project
        ),
        {"login": "json2003", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, json2_project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # ---- Groups
    # Add three groups
    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(test_object.randonLogin, json2_project),
        {"group_desc": "Test if a group 1", "group_id": "grp001"},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(test_object.randonLogin, json2_project),
        {"group_desc": "Test if a group 2", "group_id": "grp002"},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/groups/add".format(test_object.randonLogin, json2_project),
        {"group_desc": "Test if a group 3", "group_id": "grp003"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add three assistants
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, json2_project
        ),
        {
            "coll_id": "jsongrp001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, json2_project
        ),
        {
            "coll_id": "jsongrp002",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, json2_project
        ),
        {
            "coll_id": "jsongrp003",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Add each assistant to each group
    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, json2_project, "grp001"
        ),
        {
            "add_assistant": "",
            "coll_id": "{}|{}".format(json2_project_id, "jsongrp001"),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, json2_project, "grp002"
        ),
        {
            "add_assistant": "",
            "coll_id": "{}|{}".format(json2_project_id, "jsongrp002"),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/group/{}/members".format(
            test_object.randonLogin, json2_project, "grp003"
        ),
        {
            "add_assistant": "",
            "coll_id": "{}|{}".format(json2_project_id, "jsongrp003"),
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add each group to the form with different privileges
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {"group_id": "grp001", "group_can_submit": 1},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {"group_id": "grp002", "group_can_clean": 1},
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {"group_id": "grp003", "group_can_submit": 1, "group_can_clean": 1},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login and display with each assistant
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, json2_project
        ),
        {"login": "jsongrp001", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, json2_project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, json2_project
        ),
        {"login": "jsongrp002", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, json2_project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, json2_project
        ),
        {"login": "jsongrp003", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=fixed".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, json2_project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
