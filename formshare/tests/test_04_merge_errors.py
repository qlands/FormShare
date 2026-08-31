"""Which merge-check results let a new version through, and which stop it.

`mergeVersions` reports what it found as a list of coded errors, and FormShare
decides from those whether the form may be merged. It used to decide by naming
the codes that refuse a merge, which meant a code it had not heard of fell
through to `form_abletomerge = 1` -- the form was published as ready to merge
and nothing was said. `ACD` is such a code today: the form changed
`allow_choice_duplicates`, which decides how every lookup table is keyed and
cannot change once the repository exists.

So the list names the codes that *allow* a merge instead, and everything else
stops it, including whatever RSTools adds next.
"""

from formshare.views.form import MERGE_ERRORS_THAT_ALLOW_A_MERGE


def test_only_three_results_let_a_merge_through():
    """A new field, a new table, and a changed description -- the last of which
    the user is asked to confirm separately."""
    assert sorted(MERGE_ERRORS_THAT_ALLOW_A_MERGE) == ["FNF", "TNF", "VNS"]


def test_every_code_rstools_can_refuse_with_stops_the_merge():
    """The codes mergeVersions emits, read out of its source on 2026-08-31.

    If RSTools grows another one, this test keeps passing and the merge keeps
    failing closed -- which is the point. It is here to say that none of the
    ones we know about were left out by accident.
    """
    refusing = ["TNS", "TWP", "FNS", "RNS", "ACD"]
    for code in refusing:
        assert code not in MERGE_ERRORS_THAT_ALLOW_A_MERGE


def test_an_unknown_code_is_not_treated_as_harmless():
    """The regression. A code from a newer RSTools must not read as 'proceed'."""
    for code in ["ZZZ", "", None, "acd", "Fnf"]:
        assert code not in MERGE_ERRORS_THAT_ALLOW_A_MERGE


def test_the_allowing_codes_are_compared_exactly():
    """Case matters: the report writes them upper case and so does the list."""
    assert "FNF" in MERGE_ERRORS_THAT_ALLOW_A_MERGE
    assert "fnf" not in MERGE_ERRORS_THAT_ALLOW_A_MERGE
