"""What a form's testing left, recorded before the form gets a repository and
dealt with after (formshare/processes/testing_data.py), and the two index
functions it uses. No database and no index: the files are made here, and the
index is a stand-in."""

import os

import pytest

from formshare.processes import testing_data
from formshare.processes.elasticsearch import repository_index


def submissions_of(odk_dir):
    return os.path.join(odk_dir, "forms", "form1", "submissions")


def a_submission(submissions, submission_id, media=True):
    """The files a testing submission leaves (store_json_file)."""
    os.makedirs(submissions, exist_ok=True)
    for extension in (".xml", ".json", ".original"):
        with open(os.path.join(submissions, submission_id + extension), "w") as a_file:
            a_file.write("{}")
    if media:
        os.makedirs(os.path.join(submissions, submission_id))
        with open(
            os.path.join(submissions, submission_id, "image001.png"), "wb"
        ) as a_file:
            a_file.write(b"png")


def recorded(odk_dir):
    return testing_data.record_testing_data({}, odk_dir, "form1", "p1", "f1")


@pytest.fixture
def index(monkeypatch):
    """The dataset index as testing_data sees it: the ids it holds, and the
    ids deleted from it."""
    state = {"ids": [], "deleted": [], "unreachable": False}

    def get_dataset_ids(settings, project_id, form_id):
        if state["unreachable"]:
            raise repository_index.ESConnectionError("no index")
        return list(state["ids"])

    def delete_datasets_by_id(settings, project_id, form_id, submission_ids):
        state["deleted"].append((project_id, form_id, list(submission_ids)))

    monkeypatch.setattr(testing_data, "get_dataset_ids", get_dataset_ids)
    monkeypatch.setattr(testing_data, "delete_datasets_by_id", delete_datasets_by_id)
    return state


def test_the_record_lists_each_submission_but_not_the_logs_and_maps(tmp_path, index):
    submissions = submissions_of(str(tmp_path))
    a_submission(submissions, "s1")
    a_submission(submissions, "s2", media=False)
    os.makedirs(os.path.join(submissions, "logs"))
    os.makedirs(os.path.join(submissions, "maps"))
    testing = recorded(str(tmp_path))
    assert [os.path.basename(f) for f in testing.files] == [
        "s1.json",
        "s1.original",
        "s1.xml",
        "s2.json",
        "s2.original",
        "s2.xml",
    ]
    assert [os.path.basename(os.path.normpath(d)) for d in testing.directories] == [
        "s1"
    ]
    assert [os.path.basename(f) for f in testing.json_files] == [
        "s1.json",
        "s2.json",
    ]
    assert testing.submission_ids == ["s1", "s2"]


def test_the_documents_come_from_the_index_and_from_the_files(tmp_path, index):
    # s1 is indexed and its files are gone; s2 has files, and its document
    # is not searchable yet
    a_submission(submissions_of(str(tmp_path)), "s2")
    index["ids"] = ["s1"]
    assert recorded(str(tmp_path)).submission_ids == ["s1", "s2"]


def test_an_index_that_cannot_be_read_leaves_the_documents_of_the_files(
    tmp_path, index
):
    a_submission(submissions_of(str(tmp_path)), "s1")
    index["unreachable"] = True
    assert recorded(str(tmp_path)).submission_ids == ["s1"]


def test_a_form_that_was_never_tested_records_nothing(tmp_path, index):
    testing = recorded(str(tmp_path))
    assert testing.files == testing.directories == testing.submission_ids == []
    testing.remove_files()
    testing.forget_documents({})
    assert index["deleted"] == [("p1", "f1", [])]


def test_what_arrives_after_the_record_is_neither_removed_nor_forgotten(
    tmp_path, index
):
    """CI build 880: a submission that reached the merged version while the
    merge task was updating the dictionary was deleted with the testing data."""
    submissions = submissions_of(str(tmp_path))
    a_submission(submissions, "testing")
    os.makedirs(os.path.join(submissions, "logs"))
    index["ids"] = ["testing"]
    testing = recorded(str(tmp_path))

    a_submission(submissions, "real")  # after the hand-over
    testing.forget_documents({})
    testing.remove_files()

    assert sorted(os.listdir(submissions)) == [
        "logs",
        "real",
        "real.json",
        "real.original",
        "real.xml",
    ]
    assert index["deleted"] == [("p1", "f1", ["testing"])]


def test_a_file_already_gone_does_not_stop_the_rest(tmp_path, index):
    submissions = submissions_of(str(tmp_path))
    a_submission(submissions, "s1")
    testing = recorded(str(tmp_path))
    os.remove(testing.files[0])
    testing.remove_files()
    assert os.listdir(submissions) == []


class FakeConnection:
    def __init__(self):
        self.deleted = []
        self.closed = False

    def delete_by_query(self, index, body):
        self.deleted.append((index, body))

    def close(self):
        self.closed = True


def test_the_index_lists_a_forms_documents(monkeypatch):
    connection = FakeConnection()
    seen = {}

    def scan(a_connection, index, query, _source):
        seen.update(connection=a_connection, index=index, query=query, source=_source)
        return iter([{"_id": "a"}, {"_id": "b"}])

    monkeypatch.setattr(repository_index, "create_connection", lambda s: connection)
    monkeypatch.setattr(repository_index, "scan", scan)
    assert repository_index.get_dataset_ids({}, "p1", "f1") == ["a", "b"]
    assert seen["connection"] is connection and seen["source"] is False
    assert seen["index"] == "formshare_datasets"
    assert seen["query"]["query"]["bool"]["must"] == [
        {"term": {"project_id": "p1"}},
        {"term": {"form_id": "f1"}},
    ]
    assert connection.closed


def test_the_index_deletes_the_named_submissions_and_no_other(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(repository_index, "create_connection", lambda s: connection)
    repository_index.delete_datasets_by_id(
        {}, "p1", "f1", ["id{}".format(n) for n in range(2500)]
    )
    musts = [body["query"]["bool"]["must"] for _, body in connection.deleted]
    assert [len(must[2]["terms"]["submission_id"]) for must in musts] == [
        1000,
        1000,
        500,
    ]
    assert musts[2][2]["terms"]["submission_id"][-1] == "id2499"
    assert all(
        must[:2] == [{"term": {"project_id": "p1"}}, {"term": {"form_id": "f1"}}]
        for must in musts
    )
    assert connection.closed


def test_nothing_to_delete_does_not_reach_the_index(monkeypatch):
    def no_connection(settings):
        raise AssertionError("the index was reached")

    monkeypatch.setattr(repository_index, "create_connection", no_connection)
    repository_index.delete_datasets_by_id({}, "p1", "f1", [])


def test_an_index_that_does_not_answer_says_so(monkeypatch):
    monkeypatch.setattr(repository_index, "create_connection", lambda s: None)
    with pytest.raises(repository_index.ESConnectionError):
        repository_index.get_dataset_ids({}, "p1", "f1")
    with pytest.raises(repository_index.ESConnectionError):
        repository_index.delete_datasets_by_id({}, "p1", "f1", ["a"])
