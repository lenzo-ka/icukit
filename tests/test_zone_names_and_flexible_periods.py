"""Long zone names after a time, and ICU's flexible day periods."""

import pytest

from icukit.recognize import FlexibleTimeDetector, _language_flexible_periods


def _times(text):
    return [(d["text"], d["value"].fields) for d in FlexibleTimeDetector("en_US").detect(text)]


@pytest.mark.parametrize(
    "text, fields",
    [
        ("2 in the afternoon", (("H", 14),)),
        ("7 in the morning", (("H", 7),)),
        ("9 at night", (("H", 21),)),
        ("12 noon", (("H", 12),)),
        ("10:59 at night", (("H", 22), ("m", 59))),
    ],
)
def test_a_flexible_day_period_gives_the_hour_it_covers(text, fields):
    assert _times(text) == [(text, fields)]


def test_the_flexible_periods_are_icus():
    periods = dict(_language_flexible_periods("en"))
    assert 14 in periods["in the afternoon"] and 21 in periods["at night"]


def test_a_one_letter_period_is_not_read_after_a_space():
    assert _times("12 n") == []


@pytest.mark.parametrize(
    "text",
    ["2:07:09 PM Eastern Standard Time", "00:05 New York Time", "10:30 Central European Time"],
)
def test_a_long_zone_name_after_a_time_reads_with_it(text):
    assert text in [reading for reading, _fields in _times(text)]
