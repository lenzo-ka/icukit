"""Grouped ordinals, other locales' ordinal suffixes, and Roman numerals with a suffix."""

import pytest

from icukit.recognize import (
    FlexibleNumberDetector,
    FlexibleOrdinalDetector,
    _foreign_ordinal_suffixes,
)


def _ordinals(text, locale="en_US"):
    return [(d["text"], d["value"].decimal) for d in FlexibleOrdinalDetector(locale).detect(text)]


@pytest.mark.parametrize(
    "text, value", [("1,000th", "1000"), ("1,000,000th", "1000000"), ("12,345th", "12345")]
)
def test_a_grouped_ordinal_reads_when_icu_renders_the_same_surface(text, value):
    assert _ordinals(text) == [(text, value)]


def test_a_misgrouped_ordinal_does_not_read():
    assert _ordinals("10,00th") == []


@pytest.mark.parametrize("text", ["1º", "1ª", "2ª", "1.º"])
def test_an_ordinal_indicator_from_another_locale_reads_in_english(text):
    assert _ordinals(text) == [(text, text[0])]


@pytest.mark.parametrize("text", ["1e", "1a", "chapter 1."])
def test_a_suffix_made_of_this_locales_letters_or_punctuation_is_not_foreign(text):
    assert _ordinals(text) == []


def test_foreign_suffixes_hold_a_letter_outside_the_locales_exemplars():
    suffixes = _foreign_ordinal_suffixes("en_US")

    assert {"º", "ª", ".º"} <= suffixes
    assert not {"e", "a", "r", "."} & suffixes


@pytest.mark.parametrize("text, surface", [("Henry II's reign", "II's"), ("the III's", "III's")])
def test_a_roman_numeral_spans_its_possessive(text, surface):
    romans = [
        (d["text"], [c.name for c in d["captures"]])
        for d in FlexibleNumberDetector("en_US").detect(text)
        if d["type"] == "number:cardinal:roman"
    ]

    assert romans == [(surface, ["integer", "suffix"])]
