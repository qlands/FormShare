"""Messages added since the catalogs were last exported from POEditor stay
translated (2026-11-23).

The catalogs under formshare/locale are exported from POEditor. The project
logo's label, help and refusals (2026-10-14) were never in them, so every
language showed them in English. The names of FormShare Collect changed on
2026-11-21; the list deletion's dialog, the refusals of a property or an
action in use, and the labels of a case's parent came on 2026-11-23. Each
one must keep a translation in every language: an export from POEditor that
lacks them fails here, which is the reminder to add them there.
"""

import os

import pytest
from babel.messages.pofile import read_po

LOCALE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale")
LANGUAGES = ["es", "fr", "pt", "uk"]
MESSAGES = [
    "Logo",
    "Remove the logo",
    "Shown on the main menu of FormShare Collect, at most 64 points tall. A PNG with a transparent background, about four times as wide as it is tall, such as 1200 × 300 px: from square to 6:1, at least 192 px tall and at most 200 KB. A wider image is scaled down to 1600 px. Check that it reads on both backgrounds.",
    "It stays checked while these lists serve each assistant their own cases, since public submissions name no assistant:",
    "Set them to serve every case first.",
    "The logo file is larger than 10 MB.",
    "The logo is not an image FormShare can read. Upload a PNG.",
    "The logo must be a PNG (a WebP is converted). This file is a {}.",
    "The logo cannot be animated.",
    "The logo is {} × {} px: taller than it is wide. It must be from square (1:1) to six times as wide as it is tall, such as 1200 × 300 px.",
    "The logo is {} × {} px: more than six times as wide as it is tall. It must be from square (1:1) to 6:1, such as 1200 × 300 px.",
    "The logo is {} px tall. It must be at least {} px tall to stay sharp on a phone.",
    "The logo is {} KB as a PNG. It must be at most 200 KB: fewer colours or a smaller canvas make it lighter.",
    "No form uses this list.",
    "Use this QR to configure FormShare Collect",
    "Use this QR Code to configure FormShare Collect",
    "You will use this in FormShare Collect to identify your project.",
    "You will use this in FormShare Collect to identify your project. Only the first Emoji will be used.",
    "FormShare Collect XML data files",
    "Import FormShare Collect XML data",
    "FormShare can import FormShare Collect XML files. However, the files must be inside a zip. The following image shows how to zip the files.",
    "No such form",
    "No such action",
    "The action was not removed, because the form's other actions cannot be put together without it: {}",
    "The action was not moved, because the form's actions cannot be put together in that order: {}",
    'The filter "{}" of the published list "{}", given to assistants, reads this property. Change the filter first.',
    'Action {} of the form "{}" uses this property ({}). Change or remove the action first.',
    "no description",
    "the case's parent",
    "deactivate the case",
    "reactivate the case",
    "deactivate the case's parent",
    "reactivate the case's parent",
]


def _catalog(language):
    path = os.path.join(LOCALE, language, "LC_MESSAGES", "formshare.po")
    with open(path, "rb") as a_file:
        return read_po(a_file, locale=language)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_message_has_a_translation(language):
    catalog = _catalog(language)
    untranslated = [
        message
        for message in MESSAGES
        if catalog.get(message) is None or not catalog.get(message).string
    ]
    assert untranslated == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_translation_keeps_the_placeholders(language):
    catalog = _catalog(language)
    for message in MESSAGES:
        assert catalog.get(message).string.count("{}") == message.count("{}"), message


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_app_keeps_its_name(language):
    catalog = _catalog(language)
    for message in MESSAGES:
        if "FormShare Collect" in message:
            assert "FormShare Collect" in catalog.get(message).string, message
