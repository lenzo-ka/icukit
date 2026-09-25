"""The lexicon's curated acronyms: read with their written long forms, never a break."""

import pytest

from icukit import icu_abbreviations
from icukit.abbreviation_breaker import AbbreviationSentenceBreaker
from icukit.abbreviation_recognize import AbbreviationDetector
from icukit.abbreviations import load_lexicon


@pytest.mark.parametrize(
    "surface, expansion",
    [
        ("FBI", "Federal Bureau of Investigation"),
        ("NASA", "National Aeronautics and Space Administration"),
        ("CEO", "chief executive officer"),
        ("PDF", "Portable Document Format"),
    ],
)
def test_an_acronym_reads_with_its_written_long_form(surface, expansion):
    found = AbbreviationDetector("en_US").detect(f"The {surface} said so.")
    assert [(d["text"], d["value"].expansions[0].text) for d in found] == [(surface, expansion)]


def test_an_ambiguous_acronym_keeps_every_long_form():
    (found,) = AbbreviationDetector("en").detect("a CD")
    assert [e.text for e in found["value"].expansions] == [
        "compact disc",
        "certificate of deposit",
    ]


def test_a_sentence_ending_in_an_acronym_still_breaks():
    assert len(AbbreviationSentenceBreaker("en").spans("Save it as a PDF. Then send it.")) == 2


def test_no_curated_reading_repeats_one_icu_gives():
    # "TV" is Tuvalu's code and television's acronym: two readings, one from each
    # source. What the lexicon adds must not be what ICU already says.
    icu = {}
    for row in icu_abbreviations("en_US"):
        icu.setdefault(row.surface, set()).update(row.expansions)
    acronyms = [
        e for e in load_lexicon("en").entries if e.surface.isalpha() and e.surface.isupper()
    ]
    assert len(acronyms) > 40
    for entry in acronyms:
        curated = {expansion.value for expansion in entry.expansions}
        assert not curated & icu.get(entry.surface, set()), entry.surface
