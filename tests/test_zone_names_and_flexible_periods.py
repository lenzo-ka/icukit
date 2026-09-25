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
    "text, fields, zone",
    [
        (
            "2:07:09 PM Eastern Standard Time",
            (("H", 14), ("m", 7), ("s", 9)),
            "Eastern Standard Time",
        ),
        ("00:05 New York Time", (("H", 0), ("m", 5)), "New York Time"),
        ("10:30 Central European Time", (("H", 10), ("m", 30)), "Central European Time"),
    ],
)
def test_a_long_zone_name_after_a_time_reads_with_it(text, fields, zone):
    # The time detector's zone capture carries the name ICU writes, not a zone ID: a
    # metazone name ("Central European Time") stands for many IANA zones.
    readings = FlexibleTimeDetector("en_US").detect(text)
    whole = [detection for detection in readings if detection["text"] == text]
    assert len(whole) == 1, readings
    assert whole[0]["value"].fields == fields
    zones = [capture for capture in whole[0]["captures"] if capture.name == "time-zone"]
    begin = len(text) - len(zone) - 1
    assert [(c.start, c.end, c.text, c.value) for c in zones] == [
        (begin, len(text), f" {zone}", zone)
    ]
