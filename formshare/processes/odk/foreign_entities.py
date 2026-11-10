"""A form written for ODK Central's entities (formshare.md 3.6).

FormShare parted ways with ODK entities in 2026-09: it keeps a form's answers,
serves cases to other forms through published lists, and changes them with
actions. A workbook with an ``entities`` sheet still uploads. RSTools skips
the declaration, and jsontomysql reads only the fields the manifest names, so
the ``meta/entity`` of each submission goes nowhere. Until 2026-11-10 nothing
said so. The owner chose then to accept such a form and say what to set up
instead: the form page does, in the form's own names, until it is set up.

The declaration is read from the JSON the upload keeps (``form_jsonfile``,
pyxform's), never from the workbook. So a form uploaded before reads the same,
and so does every route that takes a workbook.
"""

import json
import re

# pyxform's entity element is named and typed "entity". The form page looks
# for the word before parsing anything, so a form without an entities sheet
# costs a scan of its text, whatever spacing the JSON was written with.
_MARK = '"entity"'
_REFERENCE = re.compile(r"\$\{([^}]+)\}")


def _walk(node):
    yield node
    for child in node.get("children") or []:
        if isinstance(child, dict):
            yield from _walk(child)


def entity_declaration(survey):
    """What a form's entities sheet declares, read from pyxform's JSON, or None.

    pyxform takes one entity per form. Its element carries the list
    (``dataset``), ``create`` and ``update`` with their conditions, the id an
    update names, and the label a creation computes. ``save_to`` is a bind of
    each question it fills. ``repeat`` names the repeat whose every instance
    is an entity.
    """
    entity = None
    saves = []
    for node in _walk(survey):
        if node.get("type") == "entity" and entity is None:
            entity = node
        save_to = (node.get("bind") or {}).get("entities:saveto")
        if save_to:
            saves.append({"question": node.get("name"), "property": save_to})
    if entity is None:
        return None
    declaration = {
        "dataset": None,
        "creates": False,
        "create_if": None,
        "updates": False,
        "update_if": None,
        "entity_id": None,
        "label": None,
        "repeat": entity.get("repeat"),
        "saves": saves,
    }
    for child in entity.get("children") or []:
        name = child.get("name")
        calculate = (child.get("bind") or {}).get("calculate")
        if name == "dataset":
            declaration["dataset"] = child.get("value")
        elif name == "create":
            declaration["creates"] = True
            declaration["create_if"] = calculate
        elif name == "update":
            declaration["updates"] = True
            declaration["update_if"] = calculate
        elif name == "id":
            declaration["entity_id"] = calculate
        elif name == "label":
            declaration["label"] = calculate
    if not declaration["dataset"]:
        return None
    return declaration


def declared_entity(json_file):
    """The entity declaration of the form whose upload kept this JSON. None
    when it declares none, and when the file cannot be read: the page that
    asks must open all the same."""
    try:
        with open(json_file, encoding="utf-8") as f:
            text = f.read()
    except (OSError, TypeError):
        return None
    if _MARK not in text:
        return None
    try:
        return entity_declaration(json.loads(text))
    except (ValueError, AttributeError):
        return None


def list_file_name(declaration):
    """The file a follow-up written for Central selects its entity from."""
    return declaration["dataset"] + ".csv"


def _served_columns(_, saves):
    columns = []
    for a_save in saves:
        if a_save["question"] == a_save["property"]:
            columns.append(a_save["question"])
        else:
            columns.append(
                _("{question} as {name}").format(
                    question=a_save["question"], name=a_save["property"]
                )
            )
    return ", ".join(columns)


def _saved_values(_, saves):
    values = []
    for a_save in saves:
        if a_save["question"] == a_save["property"]:
            values.append(a_save["property"])
        else:
            values.append(
                _("{name} from {question}").format(
                    name=a_save["property"], question=a_save["question"]
                )
            )
    return ", ".join(values)


def _label_detail(_, label):
    references = _REFERENCE.findall(label or "")
    if not references:
        return None
    if label.strip() == "${" + references[0] + "}":
        return _('Label each case with "{column}".').format(column=references[0])
    return _(
        "ODK Central labels each case with {expression}. A list takes its "
        "label from one column: choose one of {columns}."
    ).format(expression=label, columns=", ".join(dict.fromkeys(references)))


def entity_notice(_, declaration, can_publish, list_published, linked, has_actions):
    """What the form page says about a form's entity declaration, in its own
    names: the paragraphs, and the steps left to set it up in FormShare
    (``text``, ``details`` and the page that does it, ``link``). None once
    every step is done.

    can_publish: the project may publish lists (not a classic case project,
    and the workflows feature exists); list_published: the project serves a
    list under the file name Central would have served; linked: this form
    has its case link; has_actions: this form has an action.
    """
    file_name = list_file_name(declaration)
    dataset = declaration["dataset"]
    if declaration["creates"] and declaration["updates"]:
        lead = _(
            "This form was written for ODK Central: it creates or updates "
            'entities of the list "{list}".'
        ).format(list=dataset)
    elif declaration["updates"]:
        lead = _(
            "This form was written for ODK Central: it updates entities of "
            'the list "{list}", the one named by {entity_id}.'
        ).format(list=dataset, entity_id=declaration["entity_id"])
    else:
        lead = _(
            "This form was written for ODK Central: it creates entities in "
            'the list "{list}".'
        ).format(list=dataset)
    if not can_publish:
        return {
            "paragraphs": [
                lead,
                _(
                    "FormShare keeps its answers, but it does not create or "
                    "update entities."
                ),
            ],
            "steps": [],
        }

    steps = []
    if declaration["creates"] and not list_published:
        if declaration["repeat"]:
            text = _(
                'Publish a list named "{file}" from the repeat "{repeat}" of '
                "this form."
            ).format(file=file_name, repeat=declaration["repeat"])
        else:
            text = _('Publish a list named "{file}" from this form.').format(
                file=file_name
            )
        details = []
        if declaration["saves"]:
            details.append(
                _("Serve these columns: {columns}.").format(
                    columns=_served_columns(_, declaration["saves"])
                )
            )
        label = _label_detail(_, declaration["label"])
        if label is not None:
            details.append(label)
        if declaration["create_if"]:
            details.append(
                _(
                    "ODK Central creates an entity only when {condition}. Give "
                    "the list that condition as its filter."
                ).format(condition=declaration["create_if"])
            )
        steps.append({"text": text, "details": details, "link": "lists"})

    if declaration["updates"]:
        if not declaration["creates"] and not list_published:
            steps.append(
                {
                    "text": _(
                        'Publish a list named "{file}" from the form that '
                        "registers these cases."
                    ).format(file=file_name),
                    "details": [],
                    "link": "lists",
                }
            )
        if not linked:
            steps.append(
                {
                    "text": _(
                        'Attach "{file}", with the header of the list, as a '
                        "file of this form, then confirm its case link."
                    ).format(file=file_name),
                    "details": [],
                    "link": "links",
                }
            )
        if declaration["saves"] and not has_actions:
            details = [_("Each one must be a column or a property of the cases.")]
            if declaration["update_if"]:
                details.append(
                    _(
                        "ODK Central saves them only when {condition}. Use "
                        "that condition as the When of each action."
                    ).format(condition=declaration["update_if"])
                )
            steps.append(
                {
                    "text": _(
                        "Add an action for each value it saves to the case: "
                        "{values}."
                    ).format(values=_saved_values(_, declaration["saves"])),
                    "details": details,
                    "link": "actions",
                }
            )

    if not steps:
        return None
    return {
        "paragraphs": [
            lead,
            _(
                "FormShare keeps its answers, but it does not create or update "
                "entities. It serves cases to other forms through published "
                "lists, and changes them with actions. To set this form up:"
            ),
        ],
        "steps": steps,
    }
