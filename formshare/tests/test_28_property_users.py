"""A property cannot be deleted while an action or a filter given to
assistants uses it (2026-11-23).

delete_table_property checked the lists that serve the property and the
lists' own filters. An action that read or wrote the property then failed
on every run of its form, and no other action of the form could be saved;
a filter given to assistants that read it broke their copies of the list.
Both now refuse the deletion, naming what uses the property.

No database: the checks are given stand-in rows.
"""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy.sql import operators

from formshare.models import ListFilter, PropertyAction, PublishedList
from formshare.models.schema import initialize_schema
from formshare.processes.db import actions as actions_db
from formshare.processes.db import case_management
from formshare.processes.db.actions import actions_using_property, uses_property
from formshare.processes.db.case_management import (
    delete_table_property,
    property_filters_assistants,
)


def rule(**fields):
    base = {
        "action_kind": "rule",
        "target_scope": "case",
        "target_kind": "property",
        "target_name": "status",
        "value_kind": "constant",
        "value": "x",
        "when_rules": None,
    }
    base.update(fields)
    return base


def condition(field_id):
    return json.dumps(
        {
            "condition": "AND",
            "rules": [
                {"id": field_id, "field": field_id, "operator": "equal", "value": "x"}
            ],
        }
    )


@pytest.mark.parametrize(
    "a_row, scopes, expected",
    [
        (rule(target_name="risk"), {"case"}, True),
        (rule(target_name="risk", target_scope="parent"), {"case"}, False),
        (rule(target_name="risk", target_scope="parent"), {"parent"}, True),
        (rule(when_rules=condition("p.risk")), {"case"}, True),
        (rule(when_rules=condition("pp.risk")), {"parent"}, True),
        (rule(when_rules=condition("pp.risk")), {"case"}, False),
        (rule(when_rules=condition("v.risk")), {"case"}, False),
        (rule(value_kind="variable", value="p.risk"), {"case"}, True),
        (rule(target_name="risky"), {"case"}, False),
        (
            {"action_kind": "code", "action_code": 'api.case.set("risk", 1);'},
            {"case"},
            True,
        ),
        (
            {"action_kind": "code", "action_code": "api.case.property('risk')"},
            {"parent"},
            True,
        ),
        (
            {"action_kind": "code", "action_code": 'api.case.set("risky", 1);'},
            {"case"},
            False,
        ),
    ],
)
def test_what_uses_a_property(a_row, scopes, expected):
    assert uses_property(a_row, scopes, "risk") is expected


class _Query:
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

    def all(self):
        return list(self.rows)


class _Session:
    def __init__(self, rows):
        self.rows = rows

    def query(self, model):
        return _Query([row for row in self.rows if isinstance(row, model)])


def _request(rows):
    initialize_schema()
    return SimpleNamespace(dbsession=_Session(rows), translate=lambda text: text)


def _action(project, form, order, name, desc):
    return PropertyAction(
        action_id="{}-{}".format(form, order),
        project_id=project,
        form_id=form,
        action_order=order,
        action_kind="rule",
        action_desc=desc,
        target_scope="case",
        target_kind="property",
        target_name=name,
        value_kind="constant",
        value="1",
    )


def test_the_actions_of_the_forms_that_follow_the_table(monkeypatch):
    """A follow-up of the roster writes its property; a follow-up of
    another table writes one of the same name; a follow-up of a repeat of
    the roster reads it as its parent's."""
    sources = {
        "visit": {
            "project": "p",
            "form": "reg",
            "table": "roster",
            "parent_table": "maintable",
        },
        "other": {
            "project": "p",
            "form": "reg",
            "table": "schools",
            "parent_table": None,
        },
        "child": {
            "project": "p",
            "form": "reg",
            "table": "kids",
            "parent_table": "roster",
        },
    }
    monkeypatch.setattr(
        actions_db, "case_source_of", lambda request, project, form: sources.get(form)
    )
    parent_rule = _action("p", "child", 1, "risk", "Raises the worker's risk")
    parent_rule.target_scope = "parent"
    request = _request(
        [
            _action("p", "visit", 1, "risk", "Raises the risk"),
            _action("p", "visit", 2, "status", "Marks it visited"),
            _action("p", "other", 1, "risk", "A risk of another table"),
            parent_rule,
        ]
    )
    assert actions_using_property(request, "p", "reg", "roster", "risk") == [
        ("p", "child", 1, "Raises the worker's risk"),
        ("p", "visit", 1, "Raises the risk"),
    ]
    assert actions_using_property(request, "p", "reg", "roster", "gone") == []


def test_a_filter_given_to_assistants_that_reads_the_property():
    request = _request(
        [
            PublishedList(
                project_id="p",
                list_id="workers",
                source_project="p",
                source_form="reg",
                source_table="roster",
            ),
            PublishedList(
                project_id="p",
                list_id="schools",
                source_project="p",
                source_form="reg",
                source_table="maintable",
            ),
            ListFilter(
                project_id="p",
                list_id="schools",
                filter_id="f0",
                filter_name="Big schools",
                filter_rules=condition("p.risk"),
            ),
            ListFilter(
                project_id="p",
                list_id="workers",
                filter_id="f1",
                filter_name="North",
                filter_rules=condition("t.district"),
            ),
            ListFilter(
                project_id="p",
                list_id="workers",
                filter_id="f2",
                filter_name="At risk",
                filter_rules=condition("p.risk"),
            ),
        ]
    )
    assert property_filters_assistants(request, "p", "reg", "roster", "risk") == (
        "At risk",
        "workers",
    )
    assert property_filters_assistants(request, "p", "reg", "roster", "status") is None


@pytest.fixture
def unserved(monkeypatch):
    monkeypatch.setattr(case_management, "property_is_served", lambda *args: False)
    monkeypatch.setattr(case_management, "property_filters_a_list", lambda *args: None)


def test_the_deletion_is_refused_while_a_filter_given_to_assistants_reads_it(
    monkeypatch, unserved
):
    monkeypatch.setattr(
        case_management,
        "property_filters_assistants",
        lambda *args: ("At risk", "workers"),
    )
    ok, message = delete_table_property(_request([]), "p", "reg", "roster", "risk")
    assert not ok
    assert message == (
        'The filter "At risk" of the published list "workers", given to assistants, '
        "reads this property. Change the filter first."
    )


def test_the_deletion_is_refused_while_an_action_uses_it(monkeypatch, unserved):
    monkeypatch.setattr(
        case_management, "property_filters_assistants", lambda *args: None
    )
    monkeypatch.setattr(
        actions_db,
        "actions_using_property",
        lambda *args: [("p", "visit", 2, "Raises the risk")],
    )
    ok, message = delete_table_property(_request([]), "p", "reg", "roster", "risk")
    assert not ok
    assert message == (
        'Action 2 of the form "visit" uses this property (Raises the risk). '
        "Change or remove the action first."
    )
