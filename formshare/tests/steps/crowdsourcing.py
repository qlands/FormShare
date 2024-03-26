import json
import os
import time
import uuid

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details


def t_e_s_t_crowdsourcing(test_object):
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(
            test_object.randonLogin, test_object.project
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login succeed
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Adds a mimic2 project
    json2_project = "crowdsourcing"
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
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers
    # Add form
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

    # Uploads a file to the form
    paths = ["resources", "forms", "complex_form", "generated.csv"]
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
            "coll_id": "crowdsourcing",
            "coll_name": "crowdsourcing",
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
            "coll_id": "{}|{}".format(json2_project_id, "crowdsourcing"),
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Get the XML Form
    test_object.testapp.get(
        "/user/{}/project/{}/{}/xmlform".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    # Get the manifest pass
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    # Gets a media file
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest/mediafile/cantones.csv".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    # Test the head
    test_object.testapp.head(
        "/user/{}/project/{}/submission".format(test_object.randonLogin, json2_project),
        status=204,
    )

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
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {"form_pkey": "I_D", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Crowdsourcing. Waiting for repository")
    time.sleep(60)  # Wait for Celery to finish

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
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(
            test_object.randonLogin, json2_project
        ),
        {"login": "crowdsourcing", "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Load all the errors
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        status=200,
    )

    # Load only those that are errors
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
    res = engine.execute(sql).first()
    duplicated_id = res[0]
    engine.dispose()

    # Load compare submission
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            json2_project,
            json2_form,
            duplicated_id,
        ),
        status=200,
    )

    # Compare the against a submission
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            json2_project,
            json2_form,
            duplicated_id,
        ),
        {"submissionid": survey_id},
        status=200,
    )
    assert "FS_error" not in res.headers

    # Checkout the submission
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            json2_project,
            json2_form,
            duplicated_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
            test_object.randonLogin,
            json2_project,
            json2_form,
            duplicated_id,
        ),
        status=200,
    )
    data = json.loads(res.body)
    data["si_participa/section_household_info/RespondentDetails/I_D"] = "5018D5S387ABC2"
    tmp = os.path.join(test_object.path, *["tmp"])
    if not os.path.exists(tmp):
        os.makedirs(tmp)
    paths = ["tmp", duplicated_id + ".json"]
    submission_file = os.path.join(test_object.path, *paths)

    with open(submission_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Checkin a file passes.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            json2_project,
            json2_form,
            duplicated_id,
        ),
        {
            "notes": "Some notes about the checkin submission {}".format(duplicated_id),
            "sequence": "23a243c95547",
        },
        status=302,
        upload_files=[("json", submission_file)],
    )
    assert "FS_error" not in res.headers

    os.remove(submission_file)

    # Push the revision.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
            test_object.randonLogin,
            json2_project,
            json2_form,
            duplicated_id,
            "23a243c95547",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the checkout
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, json2_project, json2_form
        ),
        {"status": "fixed"},
        status=200,
    )
