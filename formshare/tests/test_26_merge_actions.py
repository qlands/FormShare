"""A new version keeps the actions of the version it replaces (2026-11-21).

A merge carried a follow-up's case links and properties over to the new
version and left its actions behind: the rows (propertyaction) and the
composed module (odkform.action_module) are kept per version, so the version
that receives the follow-ups changed no case. inherit_actions copies them
when the merge goes ahead.

No database: a stand-in session holds two versions of a follow-up and the
actions of the first. The functional step case_journey checks the same
through the merge pages, and that a follow-up sent to the merged version
runs them.
"""

from types import SimpleNamespace

from sqlalchemy.sql import operators

from formshare.models import Odkform, PropertyAction
from formshare.models.schema import initialize_schema
from formshare.processes.db.actions import inherit_actions


class _Query:
    """Rows held in memory, filtered by equality and sorted as the ORM
    would."""

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

    def order_by(self, column):
        self.rows = sorted(self.rows, key=lambda row: getattr(row, column.key))
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class _Session:
    """The forms and actions of a project. A commit keeps what was added, or
    raises when told to, as MySQL refusing a row would."""

    def __init__(self, rows, failing=False):
        self.rows = rows
        self.failing = failing
        self.pending = []
        self.rolled_back = 0

    def query(self, model):
        return _Query([row for row in self.rows if isinstance(row, model)])

    def add(self, row):
        self.pending.append(row)

    def commit(self):
        if self.failing:
            raise RuntimeError("Duplicate entry")
        self.rows += self.pending
        self.pending = []

    def rollback(self):
        self.pending = []
        self.rolled_back += 1


MODULE = "export default function run(s, api) {}\n"


def _forms():
    return [
        Odkform(
            project_id="p",
            form_id="visit",
            action_module=MODULE,
            action_mode="expert",
        ),
        Odkform(
            project_id="p", form_id="visit_v2", action_module=None, action_mode="table"
        ),
    ]


def _parent_actions():
    """Two actions of the first version, stored out of order: a rule and
    code."""
    return [
        PropertyAction(
            action_id="code-1",
            project_id="p",
            form_id="visit",
            action_order=2,
            action_kind="code",
            action_code=MODULE,
            action_desc="Counts each visit",
            target_scope="case",
        ),
        PropertyAction(
            action_id="rule-1",
            project_id="p",
            form_id="visit",
            action_order=1,
            action_kind="rule",
            action_desc="Deactivates a worker who left",
            target_scope="case",
            target_kind="active",
            target_name="0",
            value_kind=None,
            value=None,
            when_rules='{"condition": "AND", "rules": []}',
        ),
    ]


def _actions_of(session, form_id):
    return [
        row
        for row in session.query(PropertyAction)
        .filter(PropertyAction.form_id == form_id)
        .order_by(PropertyAction.action_order)
        .all()
    ]


def _form_of(session, form_id):
    return session.query(Odkform).filter(Odkform.form_id == form_id).first()


def test_a_new_version_starts_with_its_parents_actions():
    initialize_schema()
    session = _Session(_forms() + _parent_actions())
    request = SimpleNamespace(dbsession=session)
    assert inherit_actions(request, "p", "visit", "visit_v2") == 2
    copied = _actions_of(session, "visit_v2")
    assert [
        (a.action_order, a.action_kind, a.action_desc, a.target_kind, a.when_rules)
        for a in copied
    ] == [
        (
            1,
            "rule",
            "Deactivates a worker who left",
            "active",
            '{"condition": "AND", "rules": []}',
        ),
        (2, "code", "Counts each visit", None, None),
    ]
    assert copied[1].action_code == MODULE
    # Each copy is an action of its own: the parent keeps its rows
    assert {a.action_id for a in copied}.isdisjoint({"code-1", "rule-1"})
    assert len(_actions_of(session, "visit")) == 2
    # The module that runs, and its mode, come with them
    child = _form_of(session, "visit_v2")
    assert (child.action_module, child.action_mode) == (MODULE, "expert")


def test_a_second_call_copies_nothing():
    """The version keeps what it was given, and what its owner did after."""
    initialize_schema()
    session = _Session(_forms() + _parent_actions())
    request = SimpleNamespace(dbsession=session)
    assert inherit_actions(request, "p", "visit", "visit_v2") == 2
    assert inherit_actions(request, "p", "visit", "visit_v2") == 0
    assert len(_actions_of(session, "visit_v2")) == 2


def test_a_version_with_actions_of_its_own_keeps_them():
    initialize_schema()
    own = PropertyAction(
        action_id="own-1",
        project_id="p",
        form_id="visit_v2",
        action_order=1,
        action_kind="code",
        action_code=MODULE,
        action_desc="Its own",
        target_scope="case",
    )
    session = _Session(_forms() + _parent_actions() + [own])
    request = SimpleNamespace(dbsession=session)
    assert inherit_actions(request, "p", "visit", "visit_v2") == 0
    assert [a.action_id for a in _actions_of(session, "visit_v2")] == ["own-1"]
    assert _form_of(session, "visit_v2").action_module is None


def test_a_parent_without_actions_gives_nothing():
    initialize_schema()
    session = _Session(_forms())
    request = SimpleNamespace(dbsession=session)
    assert inherit_actions(request, "p", "visit", "visit_v2") == 0
    child = _form_of(session, "visit_v2")
    assert (child.action_module, child.action_mode) == (None, "table")


def test_a_refused_copy_is_rolled_back():
    initialize_schema()
    session = _Session(_forms() + _parent_actions(), failing=True)
    request = SimpleNamespace(dbsession=session)
    assert inherit_actions(request, "p", "visit", "visit_v2") == 0
    assert session.rolled_back == 1
    assert _actions_of(session, "visit_v2") == []
