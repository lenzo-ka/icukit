"""A weekday before a day-first date reads as the language's other locales write it."""

import pytest

from icukit.recognize import FlexibleTextDateDetector


def _dates(text):
    return [(d["text"], d["value"].fields) for d in FlexibleTextDateDetector("en_US").detect(text)]


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Thursday, 2 May 2013", (("y", 2013), ("M", 5), ("d", 2))),
        ("Saturday 3 January 1891", (("y", 1891), ("M", 1), ("d", 3))),
        ("Sat, 3 Jan 1891", (("y", 1891), ("M", 1), ("d", 3))),
    ],
)
def test_a_weekday_before_a_day_first_date_reads_whole(text, fields):
    assert _dates(text) == [(text, fields)]


def test_a_weekday_that_is_not_the_dates_is_left_out():
    # 2 May 2013 was a Thursday: the date reads, the weekday does not.
    assert _dates("Monday, 2 May 2013") == [("2 May 2013", (("y", 2013), ("M", 5), ("d", 2)))]


def test_the_choice_of_locales_governs_these_patterns():
    # The day-first forms are other locales' (en_GB, en_AU); en_US alone reads none.
    only = FlexibleTextDateDetector("en_US", locales=())
    assert only.detect("Thursday, 2 May 2013") == []
