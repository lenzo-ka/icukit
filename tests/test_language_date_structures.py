"""A flexible date reads its own pattern first, then the other patterns of its language."""

import pytest

from icukit.recognize import FlexibleDateDetector, _language_date_structures


def _dates(text, locale="en_US"):
    return [
        (d["text"], d["value"].fields, d["spec"].pattern)
        for d in FlexibleDateDetector(locale).detect(text)
    ]


def test_an_ambiguous_date_keeps_every_valid_reading():
    assert _dates("03/05/2013") == [
        ("03/05/2013", (("y", 2013), ("M", 3), ("d", 5)), "M/d/yy"),
        ("03/05/2013", (("y", 2013), ("M", 5), ("d", 3)), "dd/MM/y"),
    ]


@pytest.mark.parametrize("text", ["10-12-14", "12-10-15"])
def test_a_year_written_first_needs_four_digits(text):
    assert all(pattern != "y-MM-dd" for _surface, _value, pattern in _dates(text))


@pytest.mark.parametrize(
    "text, fields",
    [
        ("31.12.2012", (("y", 2012), ("M", 12), ("d", 31))),
        ("1.1.2013", (("y", 2013), ("M", 1), ("d", 1))),
        ("31/12/2012", (("y", 2012), ("M", 12), ("d", 31))),
        ("2011-11-11", (("y", 2011), ("M", 11), ("d", 11))),
    ],
)
def test_a_date_the_own_pattern_cannot_read_reads_through_the_language(text, fields):
    assert [(surface, value) for surface, value, _ in _dates(text)] == [(text, fields)]


def test_an_impossible_date_reads_through_no_pattern():
    assert _dates("13/13/2013") == []


def test_the_structures_are_cldrs_short_date_patterns_for_the_language():
    patterns = {pattern for _fields, _separators, pattern in _language_date_structures("en")}

    assert {"M/d/yy", "dd/MM/y", "dd.MM.y", "y-MM-dd"} <= patterns
