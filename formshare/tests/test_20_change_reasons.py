"""The reason a person gives for changing answers or deleting a submission,
and the plugins told of a cleaning (processes/submission/api.py), without a
server: what is kept of a reason, how long it may be, and that a plugin
failing after the change neither undoes it nor keeps the others from hearing
of it. The steps change_reasons.py run the same through the application.

A deletion runs here against a session that runs no SQL and remembers every
statement, as test_02 does: a submission that is not there, and the reason
cleared from the request's pooled connection after a deletion, refused or
not, and even when clearing it fails. So does the multi-select editor's
search for its row, which the address names, and its refusals that need no
connection; and a multi-select's answer is read as the API reads it.
"""

import types

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from formshare import plugins as p
from formshare.processes.submission import api
from formshare.processes.submission.api import (
    REASON_FIELD,
    REASON_MAX_LENGTH,
    change_reason,
    reason_too_long,
    multiselect_options,
    reason_too_long_message,
    submission_cleaned,
)


def test_a_reason_is_kept_as_given_without_the_spaces_around_it():
    assert change_reason(None) is None
    assert change_reason("") is None
    assert change_reason("   \n") is None
    assert change_reason("  The officer's typo  ") == "The officer's typo"
    assert change_reason(42) == "42"
    # Within it, nothing is changed.
    assert change_reason(" a\nb ") == "a\nb"


def test_a_reason_is_held_to_a_thousand_characters():
    assert REASON_MAX_LENGTH == 1000
    assert not reason_too_long(None)
    assert not reason_too_long("x" * REASON_MAX_LENGTH)
    assert reason_too_long("x" * (REASON_MAX_LENGTH + 1))
    # Characters, not bytes: audit_reason is utf8mb4 TEXT, 65,535 bytes.
    assert not reason_too_long("é" * REASON_MAX_LENGTH)
    assert reason_too_long_message(lambda text: text) == (
        "A reason can have at most 1000 characters"
    )
    # It is posted beside the answers under a name of FormShare's own.
    assert REASON_FIELD == "_reason"


def test_a_multiselect_answer_is_its_options_once_each_in_order():
    # ODK separates them by spaces; any run of spaces does
    assert multiselect_options("maize  beans\tmaize ") == ["maize", "beans"]
    # A list from an API client is the options themselves
    assert multiselect_options(["maize", " beans ", None, ""]) == ["maize", "beans"]
    assert multiselect_options(7) == ["7"]
    # No answer is no option, and the answer is then stored as NULL
    assert multiselect_options(None) == []
    assert multiselect_options("   ") == []


def test_every_plugin_hears_of_a_cleaning_even_when_one_fails():
    heard = []

    class FailingPlugin(p.SingletonPlugin):
        p.implements(p.ICleanSubmission)

        def after_cleaning_submission(
            self, request, user, project, form, table, row_uuid, changes, reason
        ):
            raise RuntimeError("this plugin fails")

    class ListeningPlugin(p.SingletonPlugin):
        p.implements(p.ICleanSubmission)

        def after_cleaning_submission(
            self, request, user, project, form, table, row_uuid, changes, reason
        ):
            heard.append((user, project, form, table, row_uuid, changes, reason))

    try:
        submission_cleaned(
            None,
            "ana",
            "project-1",
            "form-1",
            "maintable",
            "row-1",
            {"landcultivated": "13.000"},
            "The officer's typo",
        )
    finally:
        FailingPlugin().deactivate()
        ListeningPlugin().deactivate()
    assert heard == [
        (
            "ana",
            "project-1",
            "form-1",
            "maintable",
            "row-1",
            {"landcultivated": "13.000"},
            "The officer's typo",
        )
    ]


class RecordingSession:
    """The request's session as delete_submission uses it, running no SQL. It
    remembers each statement with its parameters, answers the SELECT of the
    submission with row, and raises refusals[start] for a statement that
    starts so."""

    def __init__(self, row, refusals=None):
        self.row = row
        self.refusals = refusals or {}
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))
        for a_start, an_error in self.refusals.items():
            if sql.startswith(a_start):
                raise an_error
        return types.SimpleNamespace(fetchone=lambda: self.row)

    def commit(self):
        self.statements.append(("COMMIT", None))

    def rollback(self):
        self.statements.append(("ROLLBACK", None))

    def query(self, *entities):
        # FormShare's own record of the submission, deleted last
        return RecordingQuery(self)


class RecordingQuery:
    def __init__(self, session):
        self.session = session

    def filter(self, *criteria):
        return self

    def delete(self):
        self.session.statements.append(("DELETE submission", None))


class RecordingRequest:
    def __init__(self, session):
        self.dbsession = session
        self.registry = types.SimpleNamespace(settings={})

    @staticmethod
    def translate(text):
        return text


@pytest.fixture
def deletion(monkeypatch, tmp_path):
    """delete_submission with nothing around it: the form's schema and
    directory are given, the take-back of the actions' runs and the dataset
    index are stand-ins, and the errors it logs are kept."""
    state = {"errors": [], "taken_back": [], "unindexed": []}

    def take_back_runs(request, project, main_rowuuid):
        state["taken_back"].append(main_rowuuid)

    def delete_from_dataset_index(settings, project, form, submission_id):
        state["unindexed"].append(submission_id)

    monkeypatch.setattr(api, "get_form_schema", lambda request, project, form: "FS_f")
    monkeypatch.setattr(api, "get_form_directory", lambda request, project, form: "f")
    monkeypatch.setattr(api, "get_odk_path", lambda request: str(tmp_path))
    monkeypatch.setattr(api, "take_back_runs", take_back_runs)
    monkeypatch.setattr(api, "delete_from_dataset_index", delete_from_dataset_index)
    monkeypatch.setattr(
        api,
        "log",
        types.SimpleNamespace(error=state["errors"].append, info=lambda message: None),
    )
    return state


def delete(session):
    return api.delete_submission(
        RecordingRequest(session),
        "owner",
        "project-1",
        "form-1",
        "row-1",
        "project",
        "ana",
        reason="Registered twice",
    )


SELECT = (
    "SELECT surveyid FROM `FS_f`.maintable WHERE rowuuid = :rowuuid",
    {"rowuuid": "row-1"},
)
DELETE = (
    "DELETE FROM `FS_f`.maintable WHERE rowuuid = :rowuuid",
    {"rowuuid": "row-1"},
)
CLEAR = ("SET @odktools_update_reason = NULL", None)


def test_a_submission_that_is_not_there_is_said_so_and_nothing_is_written(
    deletion,
):
    heard = []

    class DeletionListener(p.SingletonPlugin):
        p.implements(p.IDeleteSubmission)

        def before_deleting_submission(self, request, user, project, form, submission):
            heard.append(submission)
            return True, ""

        def after_deleting_submission(
            self,
            request,
            user,
            project,
            form,
            submission,
            submission_directory,
            row_uuid,
            deleted_by,
            moved_to_logs,
            reason,
        ):
            heard.append(submission)

    session = RecordingSession(row=None)
    try:
        assert delete(session) == (False, "This submission does not exist")
    finally:
        DeletionListener().deactivate()
    # It was looked for, and that is all: no user or reason was set on the
    # connection, nothing was deleted or taken back, no plugin was asked.
    assert session.statements == [SELECT]
    assert deletion["taken_back"] == []
    assert heard == []


def test_a_reason_that_cannot_be_cleared_is_logged_and_the_deletion_stands(
    deletion,
):
    lost = OperationalError(CLEAR[0], {}, Exception("Lost connection to MySQL"))
    session = RecordingSession(
        row=types.SimpleNamespace(surveyid="sub-1"), refusals={CLEAR[0]: lost}
    )
    assert delete(session) == (True, "")
    # Deleted and committed with who and why; then the reason cleared, which
    # failed; then FormShare's record of the submission deleted.
    assert session.statements == [
        SELECT,
        ("SET @odktools_current_user = :user", {"user": "ana"}),
        ("SET @odktools_update_reason = :reason", {"reason": "Registered twice"}),
        DELETE,
        ("COMMIT", None),
        CLEAR,
        ("DELETE submission", None),
        ("COMMIT", None),
    ]
    assert deletion["taken_back"] == ["row-1"]
    assert deletion["unindexed"] == ["sub-1"]
    assert [
        an_error
        for an_error in deletion["errors"]
        if an_error.startswith("Could not clear the reason")
    ] == ["Could not clear the reason after deleting submission row-1: {}".format(lost)]


def test_a_reason_is_cleared_after_a_refused_deletion_too(deletion):
    refused = IntegrityError(DELETE[0], {}, Exception("1451 a follow-up refers to it"))
    session = RecordingSession(
        row=types.SimpleNamespace(surveyid="sub-1"), refusals={DELETE[0]: refused}
    )
    allowed, message = delete(session)
    assert not allowed
    assert message.startswith("Cannot delete submission row-1.")
    # A rollback leaves a connection's variables as they are, and the
    # connection goes back to the pool: without the last statement, the next
    # change made on it would be recorded with this reason.
    assert session.statements[-3:] == [DELETE, ("ROLLBACK", None), CLEAR]
    assert deletion["errors"] == ["Cannot delete submission row-1"]


def removal_listener():
    """A plugin that hears of each removal, as the DQ plugin does
    (2026-11-03). A plugin class is active once defined, so each test
    defines it when it should start listening."""

    class RemovalListener(p.SingletonPlugin):
        p.implements(p.IDeleteSubmission)

        heard = []

        def before_deleting_submission(self, request, user, project, form, submission):
            return True, ""

        def after_deleting_submission(
            self,
            request,
            user,
            project,
            form,
            submission,
            submission_directory,
            row_uuid,
            deleted_by,
            moved_to_logs,
            reason,
        ):
            self.heard.append(
                {
                    "user": user,
                    "submission": submission,
                    "directory": submission_directory,
                    "row": row_uuid,
                    "by": deleted_by,
                    "to_logs": moved_to_logs,
                    "reason": reason,
                }
            )

    return RemovalListener


def test_plugins_hear_which_row_was_deleted_by_whom_and_why(deletion, tmp_path):
    listener = removal_listener()
    session = RecordingSession(row=types.SimpleNamespace(surveyid="sub-1"))
    try:
        assert delete(session) == (True, "")
    finally:
        listener().deactivate()
    # The project's owner is still user; who deleted it is ana, as the audit
    # log records her. A plugin used to read that, and the reason, back from
    # the audit log, and could not tell a deletion from a move to the logs.
    assert listener.heard == [
        {
            "user": "owner",
            "submission": "sub-1",
            "directory": str(tmp_path / "forms" / "f" / "submissions" / "sub-1"),
            "row": "row-1",
            "by": "ana",
            "to_logs": False,
            "reason": "Registered twice",
        }
    ]


def test_plugins_hear_of_a_move_to_the_logs_which_names_who_moved_it(
    deletion, monkeypatch, tmp_path
):
    logged = []

    def add_json_log(request, project, form, submission, json_file, log_file, *rest):
        logged.append(log_file)
        return True, ""

    monkeypatch.setattr(api, "add_json_log", add_json_log)
    (tmp_path / "forms" / "f" / "submissions" / "logs").mkdir(parents=True)
    listener = removal_listener()
    session = RecordingSession(row=types.SimpleNamespace(surveyid="sub-1"))
    try:
        assert api.delete_submission(
            RecordingRequest(session),
            "owner",
            "project-1",
            "form-1",
            "row-1",
            "project",
            "ana",
            move_to_logs=True,
            assistant_uuid="officer-1",
            reason="The household is in another district",
        ) == (True, "")
    finally:
        listener().deactivate()
    assert [(a["by"], a["to_logs"], a["reason"]) for a in listener.heard] == [
        ("ana", True, "The household is in another district")
    ]
    # A move keeps FormShare's record of the submission, to push it again
    assert ("DELETE submission", None) not in session.statements
    # The logs name who moved it: they used to name the project's owner
    with open(logged[0], encoding="utf-8") as a_log:
        entry = a_log.read()
    assert 'Error="Moved to logs by ana"' in entry
    assert "owner" not in entry


def test_a_plugin_failing_after_a_removal_neither_undoes_it_nor_stops_the_rest(
    deletion,
):
    # PyUtilib calls the plugins in an order of its own: one listens on each
    # side of the plugin that fails
    before = removal_listener()

    class FailingRemovalPlugin(p.SingletonPlugin):
        p.implements(p.IDeleteSubmission)

        def before_deleting_submission(self, request, user, project, form, submission):
            return True, ""

        # A plugin written before 2026-11-03 takes six arguments
        def after_deleting_submission(
            self, request, user, project, form, submission, submission_directory
        ):
            raise AssertionError("never called with six")

    after = removal_listener()
    session = RecordingSession(row=types.SimpleNamespace(surveyid="sub-1"))
    try:
        assert delete(session) == (True, "")
    finally:
        before().deactivate()
        FailingRemovalPlugin().deactivate()
        after().deactivate()
    # The others heard of it, and FormShare's record of the submission and
    # its index went: a plugin failing used to stop the rest half way
    assert [an_entry["row"] for an_entry in before.heard + after.heard] == [
        "row-1",
        "row-1",
    ]
    assert session.statements[-3:] == [
        ("ROLLBACK", None),
        ("DELETE submission", None),
        ("COMMIT", None),
    ]
    assert deletion["unindexed"] == ["sub-1"]
    failed = [
        an_error
        for an_error in deletion["errors"]
        if an_error.startswith("Plugin FailingRemovalPlugin")
    ]
    assert len(failed) == 1
    assert failed[0].startswith(
        "Plugin FailingRemovalPlugin failed after submission sub-1 of form form-1 "
        "in project project-1 was removed: "
    )
    assert "takes 7 positional arguments but 11 were given" in failed[0]


def test_the_multiselect_editor_finds_its_row_by_a_parameter(monkeypatch):
    monkeypatch.setattr(api, "get_form_schema", lambda request, project, form: "FS_f")
    session = RecordingSession(row=None)
    request = RecordingRequest(session)
    row = "x' OR '1'='1"
    assert (
        api.get_primary_key_data(request, "p", "f", "maintable", ["i_d"], row) is None
    )
    # The row comes with the editor's address: a parameter, never part of the
    # statement, as it used to be
    assert session.statements == [
        (
            "SELECT `i_d` FROM `FS_f`.`maintable` WHERE rowuuid = :rowuuid",
            {"rowuuid": row},
        )
    ]
    session.row = ("1026",)
    assert api.get_primary_key_data(request, "p", "f", "maintable", ["i_d"], "r") == {
        "i_d": "1026"
    }
    # Neither a name that is not one nor a table without keys reaches MySQL
    del session.statements[:]
    assert api.get_primary_key_data(request, "p", "f", "a`b", ["i_d"], "r") is None
    assert api.get_primary_key_data(request, "p", "f", "maintable", [], "r") is None
    assert session.statements == []


def test_the_multiselect_editor_refuses_a_row_gone_or_a_table_not_the_grids(
    monkeypatch,
):
    monkeypatch.setattr(api, "get_form_schema", lambda request, project, form: "FS_f")
    monkeypatch.setattr(
        api,
        "_grid_tables",
        lambda request, project, form: {"maintable", "maintable_msel_crops"},
    )
    request = RecordingRequest(RecordingSession(row=None))

    def update(options_table, keys):
        return api.update_multiselect_data(
            request,
            "ana",
            "p",
            "f",
            "r",
            "maintable",
            "crops",
            options_table,
            "crops",
            keys,
            ["maize"],
        )

    # Both are answered before any connection is made
    assert update("maintable_properties", {"i_d": "1026"}) == (
        False,
        "This multi-select cannot be changed",
    )
    assert update("maintable_msel_crops", None) == (
        False,
        "This submission does not exist",
    )
