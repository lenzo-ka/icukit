"""Spelled-out ordinals, years, and verbose cardinals, from the locale's RBNF rule sets."""

import pytest

from icukit.engine import generated_detectors
from icukit.recognize import FlexibleSpelloutDetector, _spellout_rulesets


def _spelled(ruleset, text):
    detector = FlexibleSpelloutDetector("en_US", ruleset=ruleset)
    return [(d["text"], d["value"].decimal) for d in detector.detect(text)]


@pytest.mark.parametrize(
    "ruleset, text, reading",
    [
        ("%spellout-ordinal", "the twenty-first time", ("twenty-first", "21")),
        ("%spellout-ordinal", "one hundred first", ("one hundred first", "101")),
        ("%spellout-numbering-year", "in nineteen ninety-nine", ("nineteen ninety-nine", "1999")),
        ("%spellout-cardinal-verbose", "one hundred and one", ("one hundred and one", "101")),
    ],
)
def test_each_rule_set_reads_what_icu_writes_with_it(ruleset, text, reading):
    assert _spelled(ruleset, text) == [reading]


def test_a_lone_first_is_not_read_like_a_lone_one():
    assert _spelled("%spellout-ordinal", "first") == []


def test_each_rule_set_has_its_own_type():
    assert FlexibleSpelloutDetector("en_US").type == "number:spellout"
    ordinal = FlexibleSpelloutDetector("en_US", ruleset="%spellout-ordinal")
    assert ordinal.type == "number:spellout:ordinal"


def test_the_engine_generates_a_reader_per_rule_set():
    types = {d.type for d in generated_detectors("en_US").detectors if "spellout" in d.type}
    assert {"number:spellout", "number:spellout:ordinal", "number:spellout:numbering-year"} <= types
    assert "%spellout-ordinal" in _spellout_rulesets("en_US")


def test_an_unknown_rule_set_is_refused():
    with pytest.raises(ValueError, match="no spellout rule set"):
        FlexibleSpelloutDetector("en_US", ruleset="%spellout-roman")
