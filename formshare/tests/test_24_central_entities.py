"""A form written for ODK Central's entities, and what its page says.

FormShare does not create or update entities (formshare.md 3.6): such a form
uploads, its answers are kept, and its page says what to set up instead, in
the form's own names (processes/odk/foreign_entities.py, 2026-11-10). The
workbooks here go through pyxform's parse_file_to_json and are written as the
upload writes them, so the declaration is read from the JSON a real upload
keeps.
"""

import json

import openpyxl
from pyxform.xls2json import parse_file_to_json

from formshare.processes.odk.foreign_entities import (
    declared_entity,
    entity_notice,
    list_file_name,
)


def _same(text):
    return text


def _kept_json(tmp_path, name, survey, entities=None, choices=None):
    """The JSON the upload keeps of a workbook (upload_odk_form writes it so)."""
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "survey"
    for row in survey:
        sheet.append(row)
    if choices:
        sheet = wb.create_sheet("choices")
        for row in choices:
            sheet.append(row)
    if entities:
        sheet = wb.create_sheet("entities")
        for row in entities:
            sheet.append(row)
    sheet = wb.create_sheet("settings")
    sheet.append(["form_id", "version"])
    sheet.append([name, "2026111001"])
    xlsx = tmp_path / (name + ".xlsx")
    wb.save(str(xlsx))
    kept = tmp_path / (name + ".srv")
    kept.write_text(
        json.dumps(
            parse_file_to_json(str(xlsx), warnings=[]), indent=4, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    return str(kept)


def _registration(tmp_path):
    return _kept_json(
        tmp_path,
        "trees_registration",
        [
            ["type", "name", "label", "save_to", "calculation"],
            ["calculate", "tree_id", "", "", "uuid()"],
            ["text", "species", "Species", "species", ""],
            ["integer", "height", "Height (m)", "height", ""],
            ["geopoint", "location", "Location", "geometry", ""],
        ],
        [["list_name", "label"], ["trees", "concat(${species}, ' ', ${height})"]],
    )


def _follow_up(tmp_path, update_if=None):
    entities = [["list_name", "entity_id"], ["trees", "${tree}"]]
    if update_if:
        entities = [
            ["list_name", "entity_id", "update_if"],
            ["trees", "${tree}", update_if],
        ]
    return _kept_json(
        tmp_path,
        "trees_followup",
        [
            ["type", "name", "label", "save_to", "calculation"],
            ["calculate", "visit_id", "", "", "uuid()"],
            ["select_one_from_file trees.csv", "tree", "Tree", "", ""],
            ["select_one status", "status", "Status", "status", ""],
        ],
        entities,
        [
            ["list_name", "name", "label"],
            ["status", "alive", "Alive"],
            ["status", "dead", "Dead"],
        ],
    )


# ---------------------------------------------------------------------------
# What the entities sheet declares, as the upload keeps it
# ---------------------------------------------------------------------------


def test_a_registration_declares_its_list_label_and_values(tmp_path):
    assert declared_entity(_registration(tmp_path)) == {
        "dataset": "trees",
        "creates": True,
        "create_if": None,
        "updates": False,
        "update_if": None,
        "entity_id": None,
        "label": "concat(${species}, ' ', ${height})",
        "repeat": None,
        "saves": [
            {"question": "species", "property": "species"},
            {"question": "height", "property": "height"},
            {"question": "location", "property": "geometry"},
        ],
    }


def test_a_follow_up_declares_the_entity_it_updates(tmp_path):
    declaration = declared_entity(_follow_up(tmp_path, "${status} = 'dead'"))
    assert declaration["dataset"] == "trees"
    assert declaration["updates"] and not declaration["creates"]
    assert declaration["entity_id"] == "${tree}"
    assert declaration["update_if"] == "${status} = 'dead'"
    assert declaration["saves"] == [{"question": "status", "property": "status"}]
    assert list_file_name(declaration) == "trees.csv"


def test_a_form_without_entities_declares_nothing(tmp_path):
    kept = _kept_json(
        tmp_path,
        "plain",
        [["type", "name", "label"], ["text", "entity", "A question named so"]],
    )
    assert declared_entity(kept) is None
    assert declared_entity(str(tmp_path / "missing.srv")) is None
    assert declared_entity(None) is None
    broken = tmp_path / "broken.srv"
    broken.write_text('{"type": "entity", ', encoding="utf-8")
    assert declared_entity(str(broken)) is None


# ---------------------------------------------------------------------------
# What the page says, in the form's own names
# ---------------------------------------------------------------------------


def test_a_registration_is_told_which_list_to_publish(tmp_path):
    notice = entity_notice(
        _same, declared_entity(_registration(tmp_path)), True, False, False, False
    )
    assert notice["paragraphs"][0] == (
        "This form was written for ODK Central: it creates entities in the list "
        '"trees".'
    )
    assert notice["steps"] == [
        {
            "text": 'Publish a list named "trees.csv" from this form.',
            "details": [
                "Serve these columns: species, height, location as geometry.",
                "ODK Central labels each case with concat(${species}, ' ', "
                "${height}). A list takes its label from one column: choose one "
                "of species, height.",
            ],
            "link": "lists",
        }
    ]


def test_a_registration_whose_list_is_published_says_nothing(tmp_path):
    declaration = declared_entity(_registration(tmp_path))
    assert entity_notice(_same, declaration, True, True, False, False) is None


def test_a_follow_up_is_told_to_link_the_list_and_add_actions(tmp_path):
    declaration = declared_entity(_follow_up(tmp_path, "${status} = 'dead'"))
    notice = entity_notice(_same, declaration, True, False, False, False)
    assert notice["paragraphs"][0] == (
        "This form was written for ODK Central: it updates entities of the list "
        '"trees", the one named by ${tree}.'
    )
    assert [step["link"] for step in notice["steps"]] == ["lists", "links", "actions"]
    assert notice["steps"][0]["text"] == (
        'Publish a list named "trees.csv" from the form that registers these cases.'
    )
    assert notice["steps"][1]["text"] == (
        'Attach "trees.csv", with the header of the list, as a file of this form, '
        "then confirm its case link."
    )
    assert notice["steps"][2] == {
        "text": "Add an action for each value it saves to the case: status.",
        "details": [
            "Each one must be a column or a property of the cases.",
            "ODK Central saves them only when ${status} = 'dead'. Use that "
            "condition as the When of each action.",
        ],
        "link": "actions",
    }
    # Each step leaves the page once it is done, and the notice with the last
    published = entity_notice(_same, declaration, True, True, False, False)
    assert [step["link"] for step in published["steps"]] == ["links", "actions"]
    linked = entity_notice(_same, declaration, True, True, True, False)
    assert [step["link"] for step in linked["steps"]] == ["actions"]
    assert entity_notice(_same, declaration, True, True, True, True) is None


def test_a_repeat_and_a_condition_are_named(tmp_path):
    kept = _kept_json(
        tmp_path,
        "orchard",
        [
            ["type", "name", "label", "save_to"],
            ["begin_repeat", "trees_rep", "Trees", ""],
            ["text", "species", "Species", "species"],
            ["select_one yesno", "keep", "Keep it?", ""],
            ["end_repeat", "", "", ""],
        ],
        [
            ["list_name", "label", "create_if", "repeat"],
            ["trees", "${species}", "${keep} = 'yes'", "${trees_rep}"],
        ],
        [
            ["list_name", "name", "label"],
            ["yesno", "yes", "Yes"],
            ["yesno", "no", "No"],
        ],
    )
    notice = entity_notice(_same, declared_entity(kept), True, False, False, False)
    assert notice["steps"] == [
        {
            "text": 'Publish a list named "trees.csv" from the repeat "trees_rep" of '
            "this form.",
            "details": [
                "Serve these columns: species.",
                'Label each case with "species".',
                "ODK Central creates an entity only when ${keep} = 'yes'. Give the "
                "list that condition as its filter.",
            ],
            "link": "lists",
        }
    ]


def test_where_no_list_can_be_published_it_only_says_what_happens(tmp_path):
    """A classic case project, or a server without the workflows feature:
    there is nothing to set up, so the page says only what happens."""
    declaration = declared_entity(_registration(tmp_path))
    assert entity_notice(_same, declaration, False, False, False, False) == {
        "paragraphs": [
            "This form was written for ODK Central: it creates entities in the "
            'list "trees".',
            "FormShare keeps its answers, but it does not create or update "
            "entities.",
        ],
        "steps": [],
    }
