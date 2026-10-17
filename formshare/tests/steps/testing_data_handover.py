"""A form's testing data goes when the form gets a repository, and nothing
else does (processes/testing_data.py).

The repository build and the merge hand a form its schema in a commit, and
from that moment the form takes real submissions. The testing data is
discarded or imported after. Both tasks used to take whatever the form's
submissions directory and index documents held by then, so a submission that
arrived in between went with the testing data. CI build 880 (2026-10-16)
failed that way: the case journey's first submission to a merged version
arrived while the merge task updated the dictionary, and got a 500.

Both tasks run here in the test process, so that moment can be reached on
purpose: the cleanup is wrapped so that a submission arrives first -- files in
the submissions directory and a document in the index. That submission must
survive the cleanup, and the testing data must not.
"""

import datetime
import os
import uuid
from contextlib import contextmanager

from formshare.processes.elasticsearch.repository_index import (
    add_dataset,
    create_connection,
    get_dataset_ids,
    get_index_name,
)
from formshare.processes.testing_data import RecordedTestingData
from .in_process import add_task, build_in_process, form_row

PROJECT = "handover"
PARENT = "tormenta20201105"
VERSION = "tormenta20201117"
ASSISTANT = "handover001"
SURVEY_COLUMNS = [
    "formshare_sensitive",
    "formshare_encrypted",
    "formshare_ontological_term",
    "formshare_unique",
]


def _submissions(test_object, form_directory):
    return os.path.join(
        test_object.server_config["repository.path"],
        "odk",
        "forms",
        form_directory,
        "submissions",
    )


def _files_of(test_object, form_directory, submission_id):
    return sorted(
        name
        for name in os.listdir(_submissions(test_object, form_directory))
        if name.split(".")[0] == submission_id
    )


def _plant_submission(test_object, project_id, form_id, form_directory):
    """A submission as the pipeline leaves it -- its files and its index
    document -- without the pipeline. Returns its id."""
    submission_id = str(uuid.uuid4())
    submissions = _submissions(test_object, form_directory)
    os.makedirs(os.path.join(submissions, submission_id))
    for name in (
        submission_id + ".xml",
        submission_id + ".json",
        submission_id + ".original",
        os.path.join(submission_id, "image001.png"),
    ):
        with open(os.path.join(submissions, name), "w") as a_file:
            a_file.write("{}")
    # The document store_json_file indexes for a testing submission: the
    # dashboard reads the latest one of each project, and a document without
    # these fields breaks it
    add_dataset(
        test_object.server_config,
        project_id,
        form_id,
        submission_id,
        {
            "_submitted_date": datetime.datetime.now().isoformat(),
            "_xform_id_string": form_id,
            "_submitted_by": ASSISTANT,
            "_user_id": test_object.randonLogin,
            "_project_code": PROJECT,
            "_geopoint": "",
        },
    )
    return submission_id


def _indexed(test_object, project_id, form_id):
    """The form's documents in the index, once it has caught up."""
    connection = create_connection(test_object.server_config)
    connection.indices.refresh(index=get_index_name(test_object.server_config))
    connection.close()
    return set(get_dataset_ids(test_object.server_config, project_id, form_id))


@contextmanager
def _a_submission_arrives_after_the_handover(
    test_object, project_id, form_id, form_directory
):
    """Runs a task with a submission arriving after the commit that hands the
    form its schema, and before the testing data is dealt with."""
    late = []
    forget_documents = RecordedTestingData.forget_documents

    def arrive_then_forget(self, settings):
        late.append(_plant_submission(test_object, project_id, form_id, form_directory))
        return forget_documents(self, settings)

    RecordedTestingData.forget_documents = arrive_then_forget
    try:
        yield late
    finally:
        RecordedTestingData.forget_documents = forget_documents


def _check_the_cleanup(test_object, project_id, form_id, testing_id, late):
    form_directory = form_row(test_object.server_config, project_id, form_id)[
        "form_directory"
    ]
    assert len(late) == 1, "the task never dealt with the testing data"
    late_id = late[0]
    assert _files_of(test_object, form_directory, testing_id) == []
    assert _files_of(test_object, form_directory, late_id) == [
        late_id,
        late_id + ".json",
        late_id + ".original",
        late_id + ".xml",
    ], "the submission that arrived after the hand-over lost its files"
    indexed = _indexed(test_object, project_id, form_id)
    assert testing_id not in indexed, "the testing document is still indexed"
    assert late_id in indexed, "the late submission lost its index document"


def t_e_s_t_testing_data_handover(test_object):
    testapp = test_object.testapp
    config = test_object.server_config
    login = test_object.randonLogin
    project_id = str(uuid.uuid4())
    merge = os.path.join(test_object.path, "resources", "forms", "merge")

    res = testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_id": project_id,
            "project_code": PROJECT,
            "project_name": "Testing data at the hand-over",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    assistant_uuid = str(uuid.uuid4())
    res = testapp.post(
        "/user/{}/project/{}/assistants/add".format(login, PROJECT),
        {
            "coll_uuid": assistant_uuid,
            "coll_id": ASSISTANT,
            "coll_name": ASSISTANT,
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # --- The build ----------------------------------------------------------
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, PROJECT),
        {"form_pkey": "numero_de_cedula"},
        status=302,
        upload_files=[("xlsx", os.path.join(merge, "A", "A.xls"))],
    )
    assert "FS_error" not in res.headers
    parent_files = [
        os.path.join(merge, "A", n) for n in ("cantones.csv", "distritos.csv")
    ]
    for a_file in parent_files:
        res = testapp.post(
            "/user/{}/project/{}/form/{}/upload".format(login, PROJECT, PARENT),
            status=302,
            upload_files=[("filetoupload", a_file)],
        )
        assert "FS_error" not in res.headers

    # The build blocks the form for its hand-over, so one that fails there
    # must unblock it: the form stays in testing and takes submissions
    from formshare.products.repository import celery_task as repository_task

    def a_failing_record(*args):
        raise RuntimeError("the hand-over failed")

    record = repository_task.record_testing_data
    repository_task.record_testing_data = a_failing_record
    try:
        build_in_process(
            test_object, project_id, PROJECT, PARENT, "numero_de_cedula", parent_files
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("the build did not fail")
    finally:
        repository_task.record_testing_data = record
    parent = form_row(config, project_id, PARENT)
    assert parent["form_schema"] is None
    assert parent["form_blocked"] == 0, "a failed build left the form blocked"

    parent = form_row(config, project_id, PARENT)
    testing_id = _plant_submission(
        test_object, project_id, PARENT, parent["form_directory"]
    )
    with _a_submission_arrives_after_the_handover(
        test_object, project_id, PARENT, parent["form_directory"]
    ) as late:
        build_in_process(
            test_object, project_id, PROJECT, PARENT, "numero_de_cedula", parent_files
        )
    parent = form_row(config, project_id, PARENT)
    assert parent["form_schema"] is not None
    assert parent["form_blocked"] == 0, "the build left the form blocked"
    _check_the_cleanup(test_object, project_id, PARENT, testing_id, late)

    # --- The merge ----------------------------------------------------------
    res = testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(login, PROJECT, PARENT),
        {"for_merging": "", "parent_project": project_id, "parent_form": PARENT},
        status=302,
        upload_files=[("xlsx", os.path.join(merge, "B", "B.xls"))],
    )
    assert "FS_error" not in res.headers
    for name in ("cantones.csv", "distritos.csv"):
        res = testapp.post(
            "/user/{}/project/{}/form/{}/upload".format(login, PROJECT, VERSION),
            status=302,
            upload_files=[("filetoupload", os.path.join(merge, "B", name))],
        )
        assert "FS_error" not in res.headers
    res = testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(login, PROJECT, VERSION),
        {
            "coll_id": "{}|{}|{}".format(project_id, ASSISTANT, assistant_uuid),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # A real testing submission this time, through the pipeline
    version = form_row(config, project_id, VERSION)
    submissions = _submissions(test_object, version["form_directory"])
    testapp.post(
        "/user/{}/project/{}/push".format(login, PROJECT),
        status=201,
        upload_files=[("filetoupload", os.path.join(merge, "submission001.xml"))],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=ASSISTANT),
    )
    pushed = [n for n in os.listdir(submissions) if n.endswith(".xml")]
    assert len(pushed) == 1, pushed
    testing_id = pushed[0].split(".")[0]
    assert testing_id in _indexed(test_object, project_id, VERSION)

    # The merge check runs as the form's page opens, and the merge page
    # writes the merging files the task reads
    res = testapp.get(
        "/user/{}/project/{}/form/{}".format(login, PROJECT, VERSION), status=200
    )
    assert b"Merge check pending" not in res.body
    res = testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            login, PROJECT, VERSION, PARENT
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    from formshare.products.merge.celery_task import internal_merge_into_repository

    with _a_submission_arrives_after_the_handover(
        test_object, project_id, VERSION, version["form_directory"]
    ) as late:
        internal_merge_into_repository(
            config,
            login,
            project_id,
            PROJECT,
            VERSION,
            version["form_directory"],
            parent["form_directory"],
            parent["form_createxmlfile"],
            parent["form_schema"],
            "",
            parent["form_hexcolor"],
            "en",
            True,
            SURVEY_COLUMNS,
            add_task(config, project_id, VERSION, "merge_form", login),
        )
    version = form_row(config, project_id, VERSION)
    assert version["form_schema"] == parent["form_schema"]
    assert version["form_blocked"] == 0
    assert form_row(config, project_id, PARENT)["form_blocked"] == 0
    _check_the_cleanup(test_object, project_id, VERSION, testing_id, late)

    # What the step leaves behind -- the planted submissions survive by
    # design -- must not break the pages that read the index
    testapp.get("/user/{}".format(login), status=200)
    testapp.get("/user/{}/project/{}".format(login, PROJECT), status=200)
