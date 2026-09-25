"""A weekday before a time, and eras on month-year and weekday dates."""

import pytest

from icukit.recognize import (
    FlexibleDateTimeDetector,
    FlexibleTextDateDetector,
    _language_weekday_time_glue,
)


def _readings(detector, text):
    return [(d["text"], d["value"].fields) for d in detector.detect(text)]


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Tue 2:07 PM", (("E", 3), ("H", 14), ("m", 7))),
        ("Thu 10 at night", (("E", 5), ("H", 22))),
        ("Tuesday 14:07", (("E", 3), ("H", 14), ("m", 7))),
        ("Tue. 2:07 PM", (("E", 3), ("H", 14), ("m", 7))),
    ],
)
def test_a_weekday_before_a_time_reads_whole(text, fields):
    assert _readings(FlexibleDateTimeDetector("en_US"), text) == [(text, fields)]


def test_the_glue_is_cldrs():
    assert " " in _language_weekday_time_glue("en")


def test_a_time_alone_is_not_a_weekday_time():
    assert _readings(FlexibleDateTimeDetector("en_US"), "see 2:07 PM") == []


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Jul 1999 AD", (("G", 1), ("y", 1999), ("M", 7))),
        ("Sun, Jul 4, 1999 AD", (("G", 1), ("y", 1999), ("M", 7), ("d", 4))),
    ],
)
def test_an_era_on_a_month_year_or_weekday_date_reads_with_it(text, fields):
    assert (text, fields) in _readings(FlexibleTextDateDetector("en_US"), text)
