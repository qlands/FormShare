"""Option values a repository keeps exactly as written.

The value of a choice, and the value of a lookup data column a choice_filter
compares with, are data: the repository stores them as the form has them and
never changes them, so that an answer read back out of the repository names
an option the form has. Anything MySQL could not store as written is
therefore a fault of the form, reported before a repository exists.

RSTools applies the rule at build: jxformtomysql exits 37 and, with -o m,
writes an XMLInvalidOptionValues report. FormShare applies the same rule --
these functions -- where it writes codes into a lookup itself, when a CSV or
a GeoJSON attachment is replaced, and turns the report into what the owner
reads. docs/formshare_case_management/rstools.md, 8.9.
"""

import re

# The names RSTools puts in the "problems" attribute, each with what it means
# to the person who has to fix the form.
PROBLEMS = [
    ("single_quote", "a single quote"),
    ("double_quote", "a double quote"),
    ("semicolon", "a semicolon"),
    ("backslash", "a backslash"),
    ("line_break", "a line break"),
    ("tab", "a tab"),
    ("white_space", "white space at its ends or doubled"),
    ("not_stored_as_written", "a character the repository cannot keep as written"),
]

RULE = (
    "An option's value is kept exactly as the form has it, so it cannot contain "
    "quotes, semicolons, backslashes, tabs, line breaks, or spaces at its ends "
    "or doubled."
)


def option_value_problems(value):
    """The problems of one value, by RSTools' names; empty when it is fine.

    A single space inside a value is fine, as are dots, dashes, underscores,
    backticks, bars, digits and any letter of any script.
    """
    if not isinstance(value, str):
        return []
    problems = []
    if "'" in value:
        problems.append("single_quote")
    if '"' in value:
        problems.append("double_quote")
    if ";" in value:
        problems.append("semicolon")
    if "\\" in value:
        problems.append("backslash")
    if "\n" in value or "\r" in value:
        problems.append("line_break")
    if "\t" in value:
        problems.append("tab")
    if re.search(r"^\s|\s$|\s\s", value):
        problems.append("white_space")
    return problems


def describe_problems(problems, translate):
    """ "a semicolon, a single quote" for a list or a comma-separated string."""
    _ = translate
    if isinstance(problems, str):
        problems = [p.strip() for p in problems.split(",") if p.strip()]
    names = dict(PROBLEMS)
    return ", ".join(_(names.get(p, p)) for p in problems)


def option_value_message(translate, file_name, code, problems, column=None, value=None):
    """The refusal of a replaced file, in the same words as exit 37."""
    _ = translate
    if column:
        where = _('Option "{}" of {}, column {} = "{}": {}.').format(
            code, file_name, column, value, describe_problems(problems, _)
        )
    else:
        where = _('Option "{}" of {}: {}.').format(
            code, file_name, describe_problems(problems, _)
        )
    return (
        _("The file has options whose value cannot be stored as it is written. ")
        + _(RULE)
        + " "
        + where
    )


def invalid_option_values_heading(translate):
    _ = translate
    return _(
        "The ODK you just submitted has options whose value cannot be stored "
        "as it is written. "
    ) + _(RULE)


def describe_invalid_option_values(root, translate):
    """The lines of an XMLInvalidOptionValues report, one per invalidOption,
    and a last line for what the report did not list (it lists at most 50)."""
    _ = translate
    lines = []
    report = (
        root
        if root.tag == "XMLInvalidOptionValues"
        else root.find(".//XMLInvalidOptionValues")
    )
    if report is None:
        return lines
    for an_option in report.findall(".//invalidOption"):
        list_name = an_option.get("listName", "")
        source = an_option.get("source", "")
        if source:
            list_name = _("{} (file {})").format(list_name, source)
        variables = an_option.get("variables", "")
        problems = describe_problems(an_option.get("problems", ""), _)
        column = an_option.get("column", "")
        if column:
            lines.append(
                _('Option "{}" of list {} (used by {}), column {} = "{}": {}.').format(
                    an_option.get("option", ""),
                    list_name,
                    variables,
                    column,
                    an_option.get("value", ""),
                    problems,
                )
            )
        else:
            lines.append(
                _('Option "{}" of list {} (used by {}): {}.').format(
                    an_option.get("option", ""), list_name, variables, problems
                )
            )
    try:
        total = int(report.get("total", "0"))
    except ValueError:
        total = 0
    if total > len(lines):
        lines.append(_("... and {} more.").format(total - len(lines)))
    return lines
