"""A numeral made plural reads as the written number with its suffix."""

import pytest

from icukit.detectors import NumberValue
from icukit.recognize import PluralNumeralDetector


def _plurals(text, locale="en_US"):
    return [
        (d["text"], d["value"], [c.name for c in d["captures"]])
        for d in PluralNumeralDetector(locale).detect(text)
    ]


@pytest.mark.parametrize(
    "text, surface, number, captures",
    [
        ("in the 1990s we", "1990s", "1990", ["number", "suffix"]),
        ("the 1990's", "1990's", "1990", ["number", "apostrophe", "suffix"]),
        ("back in the '90s", "'90s", "90", ["elision", "number", "suffix"]),
        ("100s of people", "100s", "100", ["number", "suffix"]),
        ("in their 20s", "20s", "20", ["number", "suffix"]),
    ],
)
def test_a_plural_numeral_reads_its_written_number(text, surface, number, captures):
    assert _plurals(text) == [(surface, NumberValue(number, None), captures)]


@pytest.mark.parametrize("text", ["1990", "1990ss", "1990sx", "abc1990s"])
def test_no_plural_reading_without_a_whole_word_suffix(text):
    assert _plurals(text) == []


def test_a_language_without_a_suffix_entry_has_no_readings():
    assert _plurals("1990s", "fr") == []
