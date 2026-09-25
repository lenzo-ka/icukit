"""A weekday date with no year names a day that falls on that weekday in some year."""

import pytest

from icukit.detectors import DateDetector

WEEKDAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


def _fields(skeleton, text):
    return [(d["text"], d["value"].fields) for d in DateDetector("en_US", skeleton).detect(text)]


@pytest.mark.parametrize("weekday", WEEKDAYS)
def test_every_weekday_reads_on_a_yearless_date(weekday):
    # Before, only 1970's weekday read: "Thu, 3/5" did, "Tue, 3/5" did not.
    text = f"{weekday}, 3/5"
    assert _fields("MEd", text) == [(text, (("M", 3), ("d", 5)))]


@pytest.mark.parametrize("weekday", WEEKDAYS)
def test_a_leap_day_reads_on_every_weekday(weekday):
    text = f"{weekday}, 2/29"
    assert _fields("MEd", text) == [(text, (("M", 2), ("d", 29)))]


def test_a_textual_month_reads_with_any_weekday():
    assert _fields("MMMEd", "Tue, Mar 5") == [("Tue, Mar 5", (("M", 3), ("d", 5)))]


@pytest.mark.parametrize("text", ["Xyz, 3/5", "Tue, 13/5", "Tue, 2/30"])
def test_what_no_year_can_write_is_not_read(text):
    assert _fields("MEd", text) == []


def test_a_date_with_a_year_still_needs_its_own_weekday():
    assert _fields("yMEd", "Tue, 3/5/2024") == [
        ("Tue, 3/5/2024", (("y", 2024), ("M", 3), ("d", 5)))
    ]
    assert _fields("yMEd", "Thu, 3/5/2024") == []
