"""Long zone names after a time, and ICU's flexible day periods."""

import json
import os
import subprocess
import sys

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
    "text, fields, zone, zone_id",
    [
        (
            "2:07:09 PM Eastern Standard Time",
            (("H", 14), ("m", 7), ("s", 9)),
            "Eastern Standard Time",
            "America/New_York",
        ),
        ("00:05 New York Time", (("H", 0), ("m", 5)), "New York Time", "America/New_York"),
        (
            "10:30 Central European Time",
            (("H", 10), ("m", 30)),
            "Central European Time",
            "Europe/Paris",
        ),
    ],
)
def test_a_long_zone_name_after_a_time_reads_with_it(text, fields, zone, zone_id):
    # The capture's text is the name as written; its value is the IANA ID of the zone
    # ICU parses the name as, as the interval reader's is.
    readings = FlexibleTimeDetector("en_US").detect(text)
    whole = [detection for detection in readings if detection["text"] == text]
    assert len(whole) == 1, readings
    assert whole[0]["value"].fields == fields
    zones = [capture for capture in whole[0]["captures"] if capture.name == "time-zone"]
    begin = len(text) - len(zone) - 1
    assert [(c.start, c.end, c.text, c.value) for c in zones] == [
        (begin, len(text), f" {zone}", zone_id)
    ]


# One of each zone form a time is read with: long specific, long generic, generic
# location, short specific, short generic, and GMT and UTC, which ICU parses as Etc/GMT.
ZONE_FORMS = [
    ("en_US", "2:07:09 PM Eastern Standard Time", " Eastern Standard Time", "America/New_York"),
    ("en_US", "10:30 Eastern Time", " Eastern Time", "America/New_York"),
    ("en_US", "10:30 Central European Time", " Central European Time", "Europe/Paris"),
    ("en_US", "00:05 New York Time", " New York Time", "America/New_York"),
    ("en_US", "5 p.m. EST", " EST", "America/New_York"),
    ("en_US", "10 PM ET", " ET", "America/New_York"),
    ("en_US", "10 PM PT", " PT", "America/Los_Angeles"),
    ("en_US", "14:00 CET", " CET", "Europe/Paris"),
    ("en_US", "18:30:00 GMT", " GMT", "Etc/GMT"),
    ("en_US", "18:00 UTC", " UTC", "Etc/GMT"),
    # The locale's region picks the zone of a shared name.
    ("en_CA", "10 PM ET", " ET", "America/Toronto"),
]


def _zone_captures(locale, text):
    return [
        (c.text, c.value)
        for d in FlexibleTimeDetector(locale).detect(text)
        if d["text"] == text
        for c in d["captures"]
        if c.name == "time-zone"
    ]


@pytest.mark.parametrize("locale, text, zone_text, zone_id", ZONE_FORMS)
def test_a_zone_capture_holds_the_iana_id_icu_parses_the_zone_as(locale, text, zone_text, zone_id):
    assert _zone_captures(locale, text) == [(zone_text, zone_id)]


@pytest.mark.parametrize("tz", ["America/Los_Angeles", "Asia/Kolkata"])
def test_a_zone_capture_is_the_same_under_any_process_tz(tz):
    script = (
        "import json, sys\n"
        "from icukit.recognize import FlexibleTimeDetector as F\n"
        "out = []\n"
        "for locale, text in json.loads(sys.argv[1]):\n"
        "    out.append([(c.text, c.value) for d in F(locale).detect(text)\n"
        "                if d['text'] == text for c in d['captures'] if c.name == 'time-zone'])\n"
        "print(json.dumps(out))\n"
    )
    forms = [(locale, text) for locale, text, _, _ in ZONE_FORMS]
    result = subprocess.run(
        [sys.executable, "-c", script, json.dumps(forms)],
        env={**os.environ, "TZ": tz},
        capture_output=True,
        text=True,
        check=True,
    )
    expected = [[[zone_text, zone_id]] for _, _, zone_text, zone_id in ZONE_FORMS]
    assert json.loads(result.stdout) == expected
