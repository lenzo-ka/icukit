"""Three-digit years, and the lexicon's weekday abbreviations."""

import pytest

from icukit.recognize import FlexibleTextDateDetector


def _dates(text):
    return [(d["text"], d["value"].fields) for d in FlexibleTextDateDetector("en_US").detect(text)]


def test_a_three_digit_year_reads_as_icu_writes_it():
    assert _dates("24 April 350") == [("24 April 350", (("y", 350), ("M", 4), ("d", 24)))]


def test_a_one_digit_year_is_not_read():
    # "3 May 2 people": a one-digit number after a date is not taken as its year.
    assert [text for text, _fields in _dates("3 May 2 people")] == ["3 May", "May 2"]


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Sun. 29 September 1912", (("y", 1912), ("M", 9), ("d", 29))),
        ("Tues. 3 May 2011", (("y", 2011), ("M", 5), ("d", 3))),
        ("Thurs., 2 May 2013", (("y", 2013), ("M", 5), ("d", 2))),
    ],
)
def test_a_lexicon_weekday_abbreviation_reads_before_a_date(text, fields):
    assert _dates(text) == [(text, fields)]


def test_the_weekday_is_still_checked_against_the_date():
    # 30 September 1912 was a Monday.
    assert _dates("Sun. 30 September 1912") == [
        ("30 September 1912", (("y", 1912), ("M", 9), ("d", 30)))
    ]
