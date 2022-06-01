import os
import json
from .sql import get_form_details
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def t_e_s_t_json_logs(test_object):
    # Get all logs
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Get all errors
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"status": "error"},
        status=200,
    )

    form_details = get_form_details(
        test_object.server_config, test_object.projectID, test_object.formID
    )
    engine = create_engine(
        test_object.server_config["sqlalchemy.url"], poolclass=NullPool
    )
    sql = "SELECT surveyid FROM {}.maintable WHERE i_d = '501890386'".format(
        form_details["form_schema"]
    )
    res = engine.execute(sql).first()
    survey_id = res[0]

    sql = (
        "SELECT submission_id FROM formshare.submission "
        "WHERE submission_status = 2 AND sameas IS NULL AND project_id = '{}' AND form_id = '{}'".format(
            test_object.projectID, test_object.formID
        )
    )
    res = engine.execute(sql).first()
    duplicated_id = res[0]

    engine.dispose()

    # Get the GeoInformation of the duplicated ID
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin, test_object.project, test_object.formID, survey_id
        ),
        status=200,
    )

    # Get the GeoInformation of submission ID that does not exists
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "not_exist",
        ),
        status=404,
    )

    # Get the media on an unknown submission goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/media".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not exist",
            "None",
        ),
        status=404,
    )

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # The use cannot get the media goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/media".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "None",
        ),
        status=404,
    )

    # Change the assistant to both
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the media files of the duplicated ID
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/media".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "None",
        ),
        status=200,
    )

    # Load compare submission
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=200,
    )

    # Load compare submission with submissions that does not exists
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin, test_object.project, test_object.formID, "NotExist"
        ),
        status=404,
    )

    # Compare the against a submission fails. Same submission
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"submissionid": duplicated_id},
        status=200,
    )
    assert "FS_error" in res.headers

    # Compare the against a submission fails. Submission does not exits
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"submissionid": "test"},
        status=200,
    )
    assert "FS_error" in res.headers

    # Compare the against a submission
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"submissionid": survey_id},
        status=200,
    )
    assert "FS_error" not in res.headers

    # Load disregard submission
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=200,
    )

    # Disregard fails. No note
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Assistant cannot disregard goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the disregard"},
        status=404,
    )

    # Change the assistant to both
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Disregard an unknown submission goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_exist",
        ),
        {"notes": "Some notes about the disregard"},
        status=404,
    )

    # Disregard passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the disregard"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Disregard again goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/disregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the disregard"},
        status=404,
    )

    # Get the disregarded
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors?status=disregarded".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Load cancel disregard submission
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=200,
    )

    # Cancel disregard fails. No note
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": ""},
        status=200,
    )
    assert "FS_error" in res.headers

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # The assistant cannot cancel disregard goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the disregard"},
        status=404,
    )

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Cancel an unknown submission goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_exists",
        ),
        {"notes": "Some notes about the disregard"},
        status=404,
    )

    # Cancel disregard passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the disregard"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Cancel the disregard again goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/canceldisregard".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the disregard"},
        status=404,
    )

    # Checkout the submission that does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin, test_object.project, test_object.formID, "NotExist"
        ),
        status=404,
    )

    # Checkout the submission
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Checkout fails with get
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Get the checkout
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"status": "checkout"},
        status=200,
    )

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Cancels the checkout goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Change the assistant to clean and submit
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Cancels the checkout for a unknown submission
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_Exists",
        ),
        status=404,
    )

    # Cancels the checkout with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Cancels the checkout pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Cancels the checkout goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Gets the submission file that has not been checkout
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Checkout the submission again
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Gets the submission file goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Gets the submission file that does not exist
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_exist",
        ),
        status=404,
    )

    # Gets the submission file
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=200,
    )
    data = json.loads(res.body)
    data["si_participa/section_household_info/RespondentDetails/I_D"] = "501890387ABC2"
    tmp = os.path.join(test_object.path, *["tmp"])
    if not os.path.exists(tmp):
        os.makedirs(tmp)
    paths = ["tmp", duplicated_id + ".json"]
    submission_file = os.path.join(test_object.path, *paths)

    with open(submission_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Loads the checkin page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=200,
    )

    # Checkin a file fails. No notes
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "", "sequence": "23a243c95547"},
        status=200,
        upload_files=[("json", submission_file)],
    )
    assert "FS_error" in res.headers

    # Checkin a file passes.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
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

    # Loads the revision review page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        {"pushed": ""},
        status=200,
    )

    # Loads the revision review page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        status=200,
    )

    # Loads the revision review page a second time
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        status=200,
    )

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # View goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        status=404,
    )

    # Cancel goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        status=404,
    )

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/view".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_exist",
            "23a243c95547",
        ),
        status=404,
    )

    # Cancel goes to 404 duplicated does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_exist",
            "23a243c95547",
        ),
        status=404,
    )

    # Cancel a revision with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        status=404,
    )

    # Cancel the revision.
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Cancel the revision again goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/cancel".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95547",
        ),
        status=404,
    )

    # -----------------------
    # Checkout the submission again
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Gets the submission file again
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=200,
    )
    data = json.loads(res.body)
    data["SECTION_META/interviewername"] = "CARLOS QUIROS CAMPOS"
    paths = ["tmp", duplicated_id + ".json"]
    submission_file = os.path.join(test_object.path, *paths)

    paths_error = ["tmp", duplicated_id + "B.json"]
    submission_file_error = os.path.join(test_object.path, *paths_error)

    with open(submission_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    with open(submission_file_error, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Checkin the file again with different file name
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the checkin {}".format(duplicated_id)},
        status=200,
        upload_files=[("json", submission_file_error)],
    )
    assert "FS_error" in res.headers

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Check in the file goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the checkin"},
        status=404,
        upload_files=[("json", submission_file)],
    )

    # Change the assistant to both
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Check in the file for a submission that does not exist
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_exist",
        ),
        {"notes": "Some notes about the checkin"},
        status=404,
        upload_files=[("json", submission_file)],
    )

    # Checkin the file again
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the checkin {}".format(duplicated_id)},
        status=302,
        upload_files=[("json", submission_file)],
    )
    assert "FS_error" not in res.headers

    # Check in the file again goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"notes": "Some notes about the checkin"},
        status=404,
        upload_files=[("json", submission_file)],
    )

    os.remove(submission_file)
    os.remove(submission_file_error)

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Push goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95548",
        ),
        status=404,
    )

    # Change the assistant to both
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Push the revision. Goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "Not_exists",
            "23a243c95548",
        ),
        status=404,
    )

    # Push the revision. Get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95548",
        ),
        status=404,
    )

    # Push the revision. In this case the passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95548",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Do it again goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/push".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95548",
        ),
        status=404,
    )

    # Get the checkout
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"status": "fixed"},
        status=200,
    )

    # ----------------------------

    # Checkout the submission again
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Gets the submission file again
    res = test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=200,
    )
    data = json.loads(res.body)
    data["si_participa/section_household_info/RespondentDetails/I_D"] = "501890387ABC2"
    paths = ["tmp", duplicated_id + ".json"]
    submission_file = os.path.join(test_object.path, *paths)

    with open(submission_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Checkin the file again
    res = test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkin".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {
            "notes": "Some notes about the checkin {}".format(duplicated_id),
            "sequence": "23a243c95549",
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
            test_object.project,
            test_object.formID,
            duplicated_id,
            "23a243c95549",
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the checkout
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/errors".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"status": "fixed"},
        status=200,
    )

    # Change the assistant to submit only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # The assistant cannot load the page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            survey_id,
        ),
        status=404,
    )

    # Change the assistant to both
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Load the compare page
    test_object.testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
            survey_id,
        ),
        status=200,
    )

    # Compare fails. Submission does not have a problem anymore
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"submissionid": survey_id},
        status=404,
    )

    # Checkout the submission that does not have a problem
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Edit an assistant to clean only
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Compare fails. The assistant cannot clean anymore
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/compare".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        {"submissionid": survey_id},
        status=404,
    )

    # Checkout the submission fails. The assistant cannot clean anymore
    test_object.testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/{}/checkout".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            duplicated_id,
        ),
        status=404,
    )

    # Edit an assistant to clean submmit and clean
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/{}/edit".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            test_object.projectID,
            test_object.assistantLogin,
        ),
        {"coll_can_submit": "1", "coll_can_clean": "1"},
        status=302,
    )
    assert "FS_error" not in res.headers
