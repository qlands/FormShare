"""The reason a person gives for changing answers or deleting a submission,
and the plugins told of a cleaning (processes/submission/api.py), without a
server: what is kept of a reason, how long it may be, and that a plugin
failing after the change neither undoes it nor keeps the others from hearing
of it. The steps change_reasons.py run the same through the application.
"""

from formshare import plugins as p
from formshare.processes.submission.api import (
    REASON_FIELD,
    REASON_MAX_LENGTH,
    change_reason,
    reason_too_long,
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
