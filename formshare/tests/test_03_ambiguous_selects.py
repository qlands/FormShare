"""How FormShare reports a select whose options cannot be told apart.

Exit code 9 covers two reports from JXFormToMySQL. The older one is a list
whose options repeat in a form that did not declare allow_choice_duplicates,
and "duplicated" is the right word for it. The newer one, added with schema
3.0, is a repeat the schema cannot resolve, and it carries a reason: a
repeated option code is legal now where a choice_filter tells the repeats
apart, so "duplicated" is no longer the diagnosis. One of the four reasons -
nocolumn - has no repeated option at all, and read as a list of duplicates it
comes out empty.

The XML in here is the tool's own output, captured from jxformtomysql at
main_3.0 e3d0812 against the workbooks in the fixtures listed on each one.
"""

from lxml import etree

from formshare.processes.odk.api import (
    ambiguous_selects_heading,
    describe_ambiguous_selects,
)


def translate(message):
    """Stand in for request.translate, which returns the msgid untranslated."""
    return message


def parse(body):
    return etree.fromstring(body.encode("utf-8"))


# duplicated_choices_no_filter.xlsx - a repeated code with no choice_filter
NO_FILTER = """<XMLResult>
 <XMLAmbiguousSelects>
  <ambiguousItem lookupTable="lkpvillages" reason="nofilter" variableName="village">
   <duplicatedItem duplicatedValue="v001" variableName="village"/>
  </ambiguousItem>
 </XMLAmbiguousSelects>
</XMLResult>"""

# a choice_filter naming a column both repeats agree on
WEAK_FILTER = """<XMLResult>
 <XMLAmbiguousSelects>
  <ambiguousItem lookupTable="lkpvillages" reason="weakfilter" variableName="village">
   <duplicatedItem duplicatedValue="v001" variableName="village"/>
  </ambiguousItem>
 </XMLAmbiguousSelects>
</XMLResult>"""

# duplicated_choices_multiselect.xlsx - a select_multiple over a repeating list
MULTISELECT = """<XMLResult>
 <XMLAmbiguousSelects>
  <ambiguousItem lookupTable="lkpvillages" reason="multiselect" variableName="visited">
   <duplicatedItem duplicatedValue="v001" variableName="visited"/>
  </ambiguousItem>
 </XMLAmbiguousSelects>
</XMLResult>"""

# a choice_filter naming a column the list does not have. No duplicatedItem:
# nothing is repeated, the filter simply cannot be built.
NO_COLUMN = """<XMLResult>
 <XMLAmbiguousSelects>
  <ambiguousItem lookupTable="lkpvillage" missingColumn="sub_location"
                 reason="nocolumn" variableName="village"/>
 </XMLAmbiguousSelects>
</XMLResult>"""

# The older report, which exit 9 still uses for a form that did not declare
# allow_choice_duplicates.
DUPLICATED = """<XMLResult>
 <XMLDuplicatedSelects>
  <duplicatedItem duplicatedValue="1" variableName="yesno"/>
  <duplicatedItem duplicatedValue="2" variableName="yesno"/>
 </XMLDuplicatedSelects>
</XMLResult>"""


def test_a_filter_naming_a_missing_column_is_reported():
    """The reason with no repeated option in it. Read as a list of duplicates
    this produces nothing at all, which is what it used to do."""
    messages = describe_ambiguous_selects(parse(NO_COLUMN), translate)
    assert len(messages) == 1
    assert "sub_location" in messages[0]
    assert "village" in messages[0]
    assert "duplicated" not in messages[0].lower()


def test_a_repeat_with_no_filter_is_reported():
    messages = describe_ambiguous_selects(parse(NO_FILTER), translate)
    assert len(messages) == 1
    assert "v001" in messages[0]
    assert "village" in messages[0]
    assert "no choice_filter" in messages[0]


def test_a_filter_that_does_not_separate_is_reported():
    messages = describe_ambiguous_selects(parse(WEAK_FILTER), translate)
    assert len(messages) == 1
    assert "v001" in messages[0]
    assert "does not tell them apart" in messages[0]


def test_a_multiple_select_over_a_repeating_list_is_reported():
    """Its junction table stores the code alone, so no filter can resolve it."""
    messages = describe_ambiguous_selects(parse(MULTISELECT), translate)
    assert len(messages) == 1
    assert "visited" in messages[0]
    assert "multiple select" in messages[0]


def test_each_reason_says_something_different():
    """A reader has to be able to tell which of the four they hit."""
    said = {
        name: describe_ambiguous_selects(parse(body), translate)[0]
        for name, body in [
            ("nofilter", NO_FILTER),
            ("weakfilter", WEAK_FILTER),
            ("multiselect", MULTISELECT),
            ("nocolumn", NO_COLUMN),
        ]
    }
    assert len(set(said.values())) == 4


def test_an_unknown_reason_still_says_something():
    """A reason this version has not heard of must not come out blank."""
    body = NO_FILTER.replace('reason="nofilter"', 'reason="something_new"')
    messages = describe_ambiguous_selects(parse(body), translate)
    assert len(messages) == 1
    assert "v001" in messages[0]
    assert "village" in messages[0]


def test_the_older_duplicated_report_is_unchanged():
    """A form that did not declare allow_choice_duplicates still gets the
    wording it always got - there, the options really are duplicated."""
    messages = describe_ambiguous_selects(parse(DUPLICATED), translate)
    assert messages == [
        "Option 1 in variable yesno",
        "Option 2 in variable yesno",
    ]
    assert (
        ambiguous_selects_heading(parse(DUPLICATED), translate)
        == "The following options are duplicated in the ODK you just submitted:"
    )


def test_the_heading_matches_the_report():
    """The two reports need different headings: one is about duplicates and
    the other is not."""
    ambiguous = ambiguous_selects_heading(parse(NO_COLUMN), translate)
    duplicated = ambiguous_selects_heading(parse(DUPLICATED), translate)
    assert ambiguous != duplicated
    assert "duplicated" not in ambiguous.lower()


def test_every_question_is_reported_not_only_the_first():
    body = """<XMLResult>
     <XMLAmbiguousSelects>
      <ambiguousItem lookupTable="lkpvillages" reason="nofilter" variableName="village">
       <duplicatedItem duplicatedValue="v001" variableName="village"/>
      </ambiguousItem>
      <ambiguousItem lookupTable="lkpwards" missingColumn="ward" reason="nocolumn"
                     variableName="ward"/>
     </XMLAmbiguousSelects>
    </XMLResult>"""
    messages = describe_ambiguous_selects(parse(body), translate)
    assert len(messages) == 2
    assert "village" in messages[0]
    assert "ward" in messages[1]


def test_several_repeated_options_are_all_named():
    body = NO_FILTER.replace(
        '<duplicatedItem duplicatedValue="v001" variableName="village"/>',
        '<duplicatedItem duplicatedValue="v001" variableName="village"/>'
        '<duplicatedItem duplicatedValue="v002" variableName="village"/>',
    )
    messages = describe_ambiguous_selects(parse(body), translate)
    assert len(messages) == 1
    assert "v001" in messages[0]
    assert "v002" in messages[0]


def test_a_report_with_neither_shape_is_empty():
    """Not a crash, and not a heading with nothing under it."""
    assert describe_ambiguous_selects(parse("<XMLResult/>"), translate) == []


# ---------------------------------------------------------------------------
# Exit 37: an option value the repository cannot keep as written (rstools.md 8.9)
# ---------------------------------------------------------------------------

from formshare.processes.option_values import (  # noqa: E402
    option_value_problems,
    describe_invalid_option_values,
    invalid_option_values_heading,
)

INVALID_OPTION_VALUES = """<XMLInvalidOptionValues total="5">
 <invalidOption listName="zones"  variables="zone"  option="nor'th" column=""     value="nor'th" problems="single_quote" source=""/>
 <invalidOption listName="places" variables="place" option="p001"   column="from" value="nor'th" problems="single_quote" source="places.csv"/>
 <invalidOption listName="places" variables="place" option="a;b"    column=""     value="a;b"    problems="semicolon,white_space" source=""/>
</XMLInvalidOptionValues>"""


def test_the_rule_names_every_problem_by_rstools_name():
    assert option_value_problems("v001") == []
    assert option_value_problems("far away") == []
    assert option_value_problems(12) == []
    assert option_value_problems("nor'th") == ["single_quote"]
    assert option_value_problems('say "hi"') == ["double_quote"]
    assert option_value_problems("a;b") == ["semicolon"]
    assert option_value_problems("C:\\temp") == ["backslash"]
    assert option_value_problems("two\nlines") == ["line_break"]
    assert option_value_problems("a\tb") == ["tab"]
    assert option_value_problems(" v001") == ["white_space"]
    assert option_value_problems("v001 ") == ["white_space"]
    assert option_value_problems("v  001") == ["white_space"]
    assert option_value_problems("a;'b' ") == [
        "single_quote",
        "semicolon",
        "white_space",
    ]


def test_the_report_is_read_line_by_line_with_what_it_did_not_list():
    root = etree.fromstring(INVALID_OPTION_VALUES)
    lines = describe_invalid_option_values(root, lambda s: s)
    assert lines == [
        'Option "nor\'th" of list zones (used by zone): a single quote.',
        'Option "p001" of list places (file places.csv) (used by place), '
        'column from = "nor\'th": a single quote.',
        'Option "a;b" of list places (used by place): a semicolon, '
        "white space at its ends or doubled.",
        "... and 2 more.",
    ]
    assert "cannot be stored as it is written" in invalid_option_values_heading(
        lambda s: s
    )
