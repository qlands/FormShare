"""What a new version keeps of its parent's access: "Keep assistants", when a
version is uploaded for merging (2026-11-03).

copy_assistants gave the new version each assistant's access and left the
assistant groups behind. Their members could no longer submit to the new
version or clean it, and the DQ plugin, whose supervisors are marked on each
version's access (coll_is_supervisor, group_is_supervisor), lost the groups
that supervised the form. It now copies both, with their privileges and their
marks.

No database: a stand-in session holds the access rows of two forms and keeps
what is added. The functional step form_merge_delete checks the same through
the merge page.
"""

from types import SimpleNamespace

from sqlalchemy.sql import operators

from formshare.models import Formacces, Formgrpacces
from formshare.models.schema import initialize_schema
from formshare.processes.db.form import copy_assistants


class _Query:
    """Rows held in memory, filtered by equality as the ORM would."""

    def __init__(self, rows):
        self.rows = rows

    def filter(self, criterion):
        assert criterion.operator is operators.eq
        self.rows = [
            row
            for row in self.rows
            if getattr(row, criterion.left.key) == criterion.right.value
        ]
        return self

    def all(self):
        return self.rows


class _Session:
    """The access rows of the project's forms. A commit keeps what was added;
    commits named in failing raise instead, as MySQL refusing a row would."""

    def __init__(self, rows, failing=()):
        self.rows = rows
        self.failing = list(failing)
        self.pending = []
        self.added = []
        self.rolled_back = 0

    def query(self, model):
        return _Query([row for row in self.rows if isinstance(row, model)])

    def add(self, row):
        self.pending.append(row)

    def commit(self):
        if self.failing and self.failing[0] == len(self.added) + len(self.pending):
            self.failing.pop(0)
            raise RuntimeError("Duplicate entry")
        self.added += self.pending
        self.pending = []

    def rollback(self):
        self.pending = []
        self.rolled_back += 1


def _rows():
    return [
        Formacces(
            coll_uuid="ana",
            form_project="p",
            form_id="reg",
            coll_can_submit=1,
            coll_can_clean=1,
            coll_can_query=0,
            coll_is_supervisor=1,
        ),
        Formgrpacces(
            project_id="p",
            group_id="north",
            form_project="p",
            form_id="reg",
            group_can_submit=1,
            group_can_clean=1,
            group_is_supervisor=1,
        ),
        Formgrpacces(
            project_id="p",
            group_id="south",
            form_project="p",
            form_id="reg",
            group_can_submit=1,
            group_can_clean=0,
            group_is_supervisor=0,
        ),
        # Another form's group is not the parent's
        Formgrpacces(
            project_id="p",
            group_id="east",
            form_project="p",
            form_id="other",
            group_can_submit=1,
            group_can_clean=1,
            group_is_supervisor=1,
        ),
    ]


def _copied(session):
    assistants = {
        row.coll_uuid: (
            row.form_project,
            row.form_id,
            row.coll_can_submit,
            row.coll_can_clean,
            row.coll_is_supervisor,
        )
        for row in session.added
        if isinstance(row, Formacces)
    }
    groups = {
        row.group_id: (
            row.project_id,
            row.form_project,
            row.form_id,
            row.group_can_submit,
            row.group_can_clean,
            row.group_is_supervisor,
        )
        for row in session.added
        if isinstance(row, Formgrpacces)
    }
    return assistants, groups


def test_a_new_version_keeps_the_assistants_and_the_groups():
    initialize_schema()
    session = _Session(_rows())
    request = SimpleNamespace(dbsession=session)
    assert copy_assistants(request, "p", "reg", "reg_v2") == (True, "")
    assistants, groups = _copied(session)
    assert assistants == {"ana": ("p", "reg_v2", 1, 1, 1)}
    # Each group of the parent, with what it may do and whether it
    # supervises; the other form's group stays where it is
    assert groups == {
        "north": ("p", "p", "reg_v2", 1, 1, 1),
        "south": ("p", "p", "reg_v2", 1, 0, 0),
    }


def test_a_row_refused_is_said_and_the_others_are_still_copied():
    initialize_schema()
    # The assistant's row is refused
    session = _Session(_rows(), failing=[1])
    request = SimpleNamespace(dbsession=session)
    copied, message = copy_assistants(request, "p", "reg", "reg_v2")
    assert (copied, message) == (False, "Duplicate entry")
    # Rolled back at once: the session would refuse the next row otherwise
    assert session.rolled_back == 1
    assistants, groups = _copied(session)
    assert assistants == {}
    assert sorted(groups) == ["north", "south"]
