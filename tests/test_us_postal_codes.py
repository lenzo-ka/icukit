"""The USPS state and territory codes, in the US English lexicon overlay."""

from icukit.abbreviation_recognize import AbbreviationDetector
from icukit.abbreviations import load_locale_lexicon


def _readings(locale, text):
    return {
        d["text"]: ([(e.text, e.sense, e.cue) for e in d["value"].expansions], d["value"].also)
        for d in AbbreviationDetector(locale).detect(text)
    }


def test_a_postal_code_reads_as_its_state():
    assert _readings("en_US", "Albany, NY 12207")["NY"] == (
        [("New York", "region", "address")],
        None,
    )


def test_every_state_dc_and_territory_is_listed():
    surfaces = {entry.surface for entry in load_locale_lexicon("en_US").entries}
    codes = {s for s in surfaces if len(s) == 2 and s.isalpha() and s.isupper()}
    assert {"AK", "CA", "DC", "MD", "NY", "PR", "TX", "VI", "WY"} <= codes
    assert len({"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA"} & codes) == 10


def test_a_code_that_is_also_a_word_says_so():
    assert _readings("en_US", "IN")["IN"][1] == "common-word"
    assert _readings("en_US", "OR")["OR"][1] == "common-word"


def test_a_code_the_general_lexicon_lists_keeps_both_readings():
    expansions = [text for text, _, _ in _readings("en_US", "MP")["MP"][0]]
    assert "Member of Parliament" in expansions
    assert "Northern Mariana Islands" in expansions


def test_the_codes_are_us_english_only():
    assert "NY" not in _readings("en_GB", "Albany, NY 12207")
