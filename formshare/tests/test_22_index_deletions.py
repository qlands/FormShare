"""Deleting from FormShare's search indexes (2026-11-03).

Elasticsearch deletes by query what it read at the index's last refresh,
each document by its version then. A document indexed or changed since is a
version conflict, and the request stopped there with a 409, part of it done.
"Delete all submissions" right after a submission arrived failed so in CI
(builds 904 and 906): Elasticsearch said total 2, deleted 1, 1 version
conflict, and FormShare said the deletion had failed while the repository
was already empty.

- delete_matching refreshes the index first, goes on past a conflict, and
  deletes again what conflicted, on a fresh read. Every deletion by query
  goes through it.
- "Delete all submissions" says the submissions went when the index still
  cannot be cleared.

No Elasticsearch and no database: stand-ins say what they would.
"""

import os
import types

import pytest

from formshare.processes import elasticsearch as indexes
from formshare.processes.elasticsearch import (
    DELETE_ATTEMPTS,
    DeletionConflict,
    delete_matching,
)
from formshare.processes.submission import api


class Connection:
    """Elasticsearch as delete_matching talks to it: each deletion answers
    the next of answers, and what is called is kept, in order."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []
        self.indices = types.SimpleNamespace(refresh=self.refresh)

    def refresh(self, index):
        self.calls.append(("refresh", index))

    def delete_by_query(self, index, body, **params):
        self.calls.append(("delete", index, body, params))
        return self.answers.pop(0)


QUERY = {"query": {"term": {"form_id": "f1"}}}


def test_a_deletion_refreshes_the_index_first_and_never_stops_at_a_conflict():
    connection = Connection([{"total": 2, "deleted": 2, "version_conflicts": 0}])
    assert delete_matching(connection, "formshare_datasets", QUERY)["deleted"] == 2
    assert connection.calls == [
        ("refresh", "formshare_datasets"),
        (
            "delete",
            "formshare_datasets",
            QUERY,
            # A conflict is counted, not a reason to stop; the deletions are
            # visible when it returns
            {"conflicts": "proceed", "refresh": True},
        ),
    ]


def test_what_conflicted_is_deleted_again_on_a_fresh_read():
    # What CI's Elasticsearch said, then the document deleted on a new read
    connection = Connection(
        [
            {"total": 2, "deleted": 1, "version_conflicts": 1},
            {"total": 1, "deleted": 1, "version_conflicts": 0},
        ]
    )
    assert delete_matching(connection, "formshare_datasets", QUERY)["total"] == 1
    assert [call[0] for call in connection.calls] == [
        "refresh",
        "delete",
        "refresh",
        "delete",
    ]


def test_a_deletion_that_keeps_conflicting_says_so():
    connection = Connection(
        [{"total": 1, "deleted": 0, "version_conflicts": 1}] * DELETE_ATTEMPTS
    )
    with pytest.raises(DeletionConflict, match="kept changing"):
        delete_matching(connection, "formshare_datasets", QUERY)
    assert DELETE_ATTEMPTS == 5
    assert [call[0] for call in connection.calls].count("delete") == 5


def test_the_answer_is_read_as_the_client_gives_it():
    # The client answers with an object that holds the JSON in body
    answer = types.SimpleNamespace(body={"total": 0, "deleted": 0})
    connection = Connection([answer])
    assert delete_matching(connection, "formshare_records", QUERY) == {
        "total": 0,
        "deleted": 0,
    }


def test_every_deletion_by_query_goes_through_it():
    # FormShare's own code, not its tests' stand-ins
    package = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(indexes.__file__)))
    )
    calling = []
    for directory, folders, files in os.walk(package):
        folders[:] = [name for name in folders if name != "tests"]
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(directory, name)
                with open(path) as a_file:
                    if "delete_by_query(" in a_file.read():
                        calling.append(os.path.relpath(path, package))
    assert calling == [os.path.join("processes", "elasticsearch", "__init__.py")]


# --- Delete all submissions -------------------------------------------------


class Session:
    """The request's session as delete_all_submission uses it, running no
    SQL: it keeps each statement, and the repository has a data table and a
    lookup."""

    def __init__(self):
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append(sql)
        return types.SimpleNamespace(
            fetchall=lambda: (
                [("maintable",), ("lkpsex",)] if sql.startswith("SHOW TABLES") else []
            )
        )

    def query(self, *entities):
        session = self

        class Query:
            def filter(self, *criteria):
                return self

            def delete(self):
                session.statements.append("DELETE {}".format(entities[0].__tablename__))

        return Query()

    def commit(self):
        self.statements.append("COMMIT")

    def rollback(self):
        self.statements.append("ROLLBACK")


@pytest.fixture
def zap(monkeypatch, tmp_path):
    """delete_all_submission with nothing around it: the form's schema and
    directory are given, its submissions folder exists, and the take-back of
    the actions' runs and the indexes are stand-ins."""
    os.makedirs(os.path.join(str(tmp_path), "forms", "f", "submissions"))
    state = {"errors": [], "unindexed": [], "refuse": None}

    def unindex(what):
        def deletion(settings, project, form):
            if state["refuse"] == what:
                raise DeletionConflict("Documents of the index kept changing")
            state["unindexed"].append(what)

        return deletion

    monkeypatch.setattr(api, "get_form_schema", lambda request, project, form: "FS_f")
    monkeypatch.setattr(api, "get_form_directory", lambda request, project, form: "f")
    monkeypatch.setattr(api, "get_odk_path", lambda request: str(tmp_path))
    monkeypatch.setattr(api, "take_back_runs", lambda *args, **kw: None)
    monkeypatch.setattr(api, "delete_dataset_from_index", unindex("datasets"))
    monkeypatch.setattr(api, "delete_form_records", unindex("records"))
    monkeypatch.setattr(
        api,
        "log",
        types.SimpleNamespace(error=state["errors"].append, info=lambda message: None),
    )
    session = Session()
    request = types.SimpleNamespace(
        dbsession=session,
        registry=types.SimpleNamespace(settings={}),
        translate=lambda text: text,
    )
    state["session"] = session
    state["delete"] = lambda: api.delete_all_submission(
        request, "owner", "project-1", "form-1", "ana"
    )
    return state


def test_all_submissions_go_and_so_do_their_documents(zap):
    assert zap["delete"]() == (True, "")
    assert zap["unindexed"] == ["datasets", "records"]
    # The data tables are emptied, never the lookups
    assert "TRUNCATE TABLE `FS_f`.`maintable`" in zap["session"].statements
    assert not any("lkpsex" in sql for sql in zap["session"].statements)


def test_an_index_that_cannot_be_cleared_is_said_and_the_deletion_stands(zap):
    zap["refuse"] = "datasets"
    deleted, message = zap["delete"]()
    # Deleted: the repository was emptied and committed before the indexes
    assert deleted is True
    statements = zap["session"].statements
    assert statements.index("TRUNCATE TABLE `FS_f`.`maintable`") < len(statements)
    assert statements[-1] == "COMMIT"
    assert message == (
        "All submissions were deleted, but they could not be removed from the "
        "search index, which may still count them."
    )
    # A message the page shows in a script's quotes: no apostrophe
    assert "'" not in message
    [logged] = zap["errors"]
    assert logged.startswith(
        "All submissions of form form-1 in project project-1 were deleted, but "
        "the search index still lists them: Documents of the index kept changing"
    )
