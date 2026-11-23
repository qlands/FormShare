"""Removing or moving an action stores the module with it, or nothing
(2026-11-23).

delete_form_action deleted the row and committed, then composed the module
again; when another action was broken, the composition failed and the old
module, with the removed action in it, kept running on the server and in
the actions.json devices download. A move did the same with the order. Both
now compose first and store the rows and the module in one commit, and
refuse, saying why, when the form's actions cannot be put together.

No database: a stand-in session holds a form and its actions, and applies
deletes and updates only when committed.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy.sql import operators

from formshare.models import Odkform, PropertyAction
from formshare.models.schema import initialize_schema
from formshare.processes.actions.compiler import Catalogue, compile_module
from formshare.processes.db import actions as actions_db
from formshare.processes.db.actions import delete_form_action, move_form_action


class _Query:
    def __init__(self, session, rows):
        self.session = session
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
        return list(self.rows)

    def delete(self):
        self.session.pending.append(("delete", list(self.rows), None))

    def update(self, values):
        self.session.pending.append(("update", list(self.rows), values))


class _Session:
    """A form and its actions. Deletes and updates wait for the commit."""

    def __init__(self, rows):
        self.rows = rows
        self.pending = []
        self.commits = 0

    def query(self, model):
        return _Query(self, [row for row in self.rows if isinstance(row, model)])

    def commit(self):
        for what, rows, values in self.pending:
            for row in rows:
                if what == "delete":
                    self.rows.remove(row)
                else:
                    for key, value in values.items():
                        setattr(row, key, value)
        self.pending = []
        self.commits += 1

    def rollback(self):
        self.pending = []


CATALOGUE = Catalogue(
    fields={
        "v.still_working": {
            "js": "s.still_working",
            "type": "string",
            "label": "still_working",
        }
    },
    targets={("case", "property", "status"): "string"},
    repeats={},
)


def _action(action_id, order, name, value, desc):
    return PropertyAction(
        action_id=action_id,
        project_id="p",
        form_id="visit",
        action_order=order,
        action_kind="rule",
        action_desc=desc,
        target_scope="case",
        target_kind="property",
        target_name=name,
        value_kind="constant",
        value=value,
        when_rules=None,
    )


def _setup(monkeypatch, *actions):
    initialize_schema()
    monkeypatch.setattr(
        actions_db, "build_catalogue", lambda request, project, form: CATALOGUE
    )
    form = Odkform(
        project_id="p", form_id="visit", action_module="OLD", action_mode="table"
    )
    session = _Session([form] + list(actions))
    request = SimpleNamespace(dbsession=session, translate=lambda text: text)
    return request, session, form


def _orders(session):
    return {
        row.action_id: row.action_order
        for row in session.rows
        if isinstance(row, PropertyAction)
    }


def _module(*pairs):
    """The module the compiler makes of (order, name, value, desc) rows."""
    return compile_module(
        [
            {
                "action_order": order,
                "action_kind": "rule",
                "action_desc": desc,
                "target_scope": "case",
                "target_kind": "property",
                "target_name": name,
                "value_kind": "constant",
                "value": value,
                "when_rules": None,
            }
            for order, name, value, desc in pairs
        ],
        CATALOGUE,
    )


def test_a_removal_stores_the_module_without_the_action(monkeypatch):
    request, session, form = _setup(
        monkeypatch,
        _action("a", 1, "status", "first", "Sets it first"),
        _action("b", 2, "status", "second", "Sets it second"),
    )
    assert delete_form_action(request, "p", "visit", "a") == (True, "")
    assert _orders(session) == {"b": 1}
    assert form.action_module == _module((1, "status", "second", "Sets it second"))
    assert session.commits == 1


def test_a_removal_the_others_cannot_survive_is_refused(monkeypatch):
    """The second action names a property the case does not have: without
    the first, the module cannot be composed, so nothing is removed and the
    module that runs is the one the list shows."""
    request, session, form = _setup(
        monkeypatch,
        _action("a", 1, "status", "first", "Sets it"),
        _action("b", 2, "gone", "x", "Sets a property that was deleted"),
    )
    ok, message = delete_form_action(request, "p", "visit", "a")
    assert not ok
    assert message.startswith("The action was not removed")
    assert _orders(session) == {"a": 1, "b": 2}
    assert form.action_module == "OLD"
    assert session.commits == 0


def test_the_broken_action_itself_can_be_removed(monkeypatch):
    request, session, form = _setup(
        monkeypatch,
        _action("a", 1, "status", "first", "Sets it"),
        _action("b", 2, "gone", "x", "Sets a property that was deleted"),
    )
    assert delete_form_action(request, "p", "visit", "b") == (True, "")
    assert _orders(session) == {"a": 1}
    assert form.action_module == _module((1, "status", "first", "Sets it"))


def test_a_move_stores_the_module_in_the_new_order(monkeypatch):
    request, session, form = _setup(
        monkeypatch,
        _action("a", 1, "status", "first", "Sets it first"),
        _action("b", 2, "status", "second", "Sets it second"),
    )
    assert move_form_action(request, "p", "visit", "b", -1) == (True, "")
    assert _orders(session) == {"b": 1, "a": 2}
    assert form.action_module == _module(
        (1, "status", "second", "Sets it second"),
        (2, "status", "first", "Sets it first"),
    )
    assert session.commits == 1


def test_a_move_that_cannot_be_composed_is_refused(monkeypatch):
    request, session, form = _setup(
        monkeypatch,
        _action("a", 1, "status", "first", "Sets it"),
        _action("b", 2, "gone", "x", "Sets a property that was deleted"),
    )
    ok, message = move_form_action(request, "p", "visit", "b", -1)
    assert not ok
    assert message.startswith("The action was not moved")
    assert _orders(session) == {"a": 1, "b": 2}
    assert form.action_module == "OLD"
    assert session.commits == 0


@pytest.mark.parametrize("direction", [-1, 1])
def test_a_move_past_either_end_changes_nothing(monkeypatch, direction):
    request, session, form = _setup(
        monkeypatch, _action("a", 1, "status", "x", "Sets it")
    )
    assert move_form_action(request, "p", "visit", "a", direction) == (True, "")
    assert session.commits == 0 and form.action_module == "OLD"


def test_an_unknown_action_or_form_is_said(monkeypatch):
    request, session, form = _setup(
        monkeypatch, _action("a", 1, "status", "x", "Sets it")
    )
    assert delete_form_action(request, "p", "visit", "nope") == (
        False,
        "No such action",
    )
    assert delete_form_action(request, "p", "other", "a") == (False, "No such form")
    assert move_form_action(request, "p", "other", "a", 1) == (False, "No such form")


def test_a_refusal_names_the_broken_action_as_the_list_shows_it(monkeypatch):
    """Removing the first of three, the broken third would be the second of
    what is left: the message names it as the page does, action 3."""
    request, session, form = _setup(
        monkeypatch,
        _action("a", 1, "status", "first", "Sets it first"),
        _action("b", 2, "status", "second", "Sets it second"),
        _action("c", 3, "gone", "x", "Sets a property that was deleted"),
    )
    ok, message = delete_form_action(request, "p", "visit", "a")
    assert not ok
    assert "Action 3: the case has no property gone" in message
    ok, message = move_form_action(request, "p", "visit", "a", 1)
    assert not ok
    assert "Action 3: the case has no property gone" in message
