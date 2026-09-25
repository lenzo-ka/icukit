"""Long zone names after a time, and ICU's flexible day periods."""

import json
import os
import subprocess
import sys

import icu
import pytest

import icukit.recognize as recognize
from icukit.recognize import (
    FlexibleDateTimeDetector,
    FlexibleTimeDetector,
    _day_of,
    _language_flexible_periods,
    _language_locale_names,
    _reading_days,
    _zone_parses,
    _zone_readings,
)
from icukit.resolve import _dedupe, resolve


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
# location, short specific, short generic, and GMT and UTC: ICU parses both as Etc/GMT,
# and writes "UTC" for Etc/UTC, the zone the capture names.
# Each gives the zones it is read in, one reading per zone, in order.
ZONE_FORMS = [
    ("en_US", "2:07:09 PM Eastern Standard Time", " Eastern Standard Time", ["America/New_York"]),
    ("en_US", "10:30 Eastern Time", " Eastern Time", ["America/New_York"]),
    ("en_US", "10:30 Central European Time", " Central European Time", ["Europe/Paris"]),
    ("en_US", "00:05 New York Time", " New York Time", ["America/New_York"]),
    # en_CA also parses "EST", as America/Toronto: the same metazone, so one reading.
    ("en_US", "5 p.m. EST", " EST", ["America/New_York"]),
    ("en_US", "10 PM ET", " ET", ["America/New_York"]),
    ("en_US", "10 PM PT", " PT", ["America/Los_Angeles"]),
    ("en_US", "14:00 CET", " CET", ["Europe/Paris"]),
    ("en_US", "18:30:00 GMT", " GMT", ["Etc/GMT"]),
    ("en_US", "18:00 UTC", " UTC", ["Etc/UTC"]),
    # The locale's region picks the zone of a shared name.
    ("en_CA", "10 PM ET", " ET", ["America/Toronto"]),
    # "IST" is Irish time in en_IE and India time in en_IN. en_US writes neither, so it
    # reads both from the language's other locales, in locale-name order; a locale that
    # writes one reads its own first.
    ("en_US", "10 PM IST", " IST", ["Europe/Dublin", "Asia/Kolkata"]),
    ("en_IN", "10 PM IST", " IST", ["Asia/Kolkata", "Europe/Dublin"]),
    ("en_IE", "10 PM IST", " IST", ["Europe/Dublin", "Asia/Kolkata"]),
    # Chinese locales write "CST" only for US Central time; China Standard Time has no
    # "CST" in CLDR's Chinese names, so Asia/Shanghai is not a reading.
    ("zh_CN", "10:00 CST", " CST", ["America/Chicago"]),
    ("zh_TW", "10:00 CST", " CST", ["America/Chicago"]),
]


def _zone_captures(locale, text):
    return [
        (c.text, c.value)
        for d in FlexibleTimeDetector(locale).detect(text)
        if d["text"] == text
        for c in d["captures"]
        if c.name == "time-zone"
    ]


@pytest.mark.parametrize("locale, text, zone_text, zone_ids", ZONE_FORMS)
def test_a_zone_capture_holds_the_iana_id_icu_parses_the_zone_as(locale, text, zone_text, zone_ids):
    # One reading per zone, each with one zone capture.
    assert _zone_captures(locale, text) == [(zone_text, zone_id) for zone_id in zone_ids]


def test_each_zone_reading_keeps_the_span_and_the_fields():
    readings = [d for d in FlexibleTimeDetector("en_US").detect("10 PM IST") if d["end"] == 9]
    assert [(d["start"], d["end"], d["value"].fields) for d in readings] == [
        (0, 9, (("H", 22),))
    ] * 2


def test_the_zones_of_a_name_come_from_the_languages_locales():
    # en_US parses no "IST" itself; each zone is another locale's parse.
    assert _zone_readings("IST", "en_US") == (
        ("Europe/Dublin", "en_IE"),
        ("Asia/Kolkata", "en_IN"),
    )
    assert _zone_readings("IST", "en_IN") == (
        ("Asia/Kolkata", "en_IN"),
        ("Europe/Dublin", "en_IE"),
    )


def test_a_caller_who_chooses_one_locale_gets_its_zones_alone():
    assert _zone_readings("EST", "en_US", ("en_US",)) == (("America/New_York", "en_US"),)
    detector = FlexibleTimeDetector("en_IN", locales=())
    assert [
        (c.text, c.value)
        for d in detector.detect("10 PM IST")
        for c in d["captures"]
        if c.name == "time-zone"
    ] == [(" IST", "Asia/Kolkata")]


def test_a_composed_date_time_is_read_once_per_zone():
    readings = [
        [c.value for c in d["captures"] if c.name == "time-zone"]
        for d in FlexibleDateTimeDetector("en_US").detect("Tue 10 PM IST")
        if d["text"] == "Tue 10 PM IST"
    ]
    assert readings == [["Europe/Dublin"], ["Asia/Kolkata"]]


def test_the_resolver_keeps_each_zone_reading():
    detections = FlexibleTimeDetector("en_US").detect("10 PM IST")
    zones = {
        c.value
        for detection in _dedupe(detections)
        for c in detection["captures"]
        if c.name == "time-zone"
    }
    assert zones == {"Europe/Dublin", "Asia/Kolkata"}


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
    expected = [
        [[zone_text, zone_id] for zone_id in zone_ids] for _, _, zone_text, zone_ids in ZONE_FORMS
    ]
    assert json.loads(result.stdout) == expected


def _zones_of(detections, text):
    return [
        [c.value for c in d["captures"] if c.name == "time-zone"]
        for d in detections
        if d["text"] == text
    ]


def test_a_name_icu_only_parses_leniently_is_not_a_zone():
    # en_MO's lenient parse takes the obsolete "MST" as Macau time, which ICU never writes
    # as "MST" today; only Mountain time is read.
    assert ("Asia/Macau", "en_MO") in _zone_parses("MST", "en_US")
    assert _zone_readings("MST", "en_US") == (("America/Denver", "en_US"),)
    assert _zones_of(FlexibleTimeDetector("en_US").detect("10 PM MST"), "10 PM MST") == [
        ["America/Denver"]
    ]
    text = "January 5, 2026, 10:00 PM MST"
    assert _zones_of(FlexibleDateTimeDetector("en_US").detect(text), text) == [["America/Denver"]]


@pytest.mark.parametrize(
    "text, zones",
    [
        # On July 5 Denver writes "MDT": the zone that writes "MST" that day is Phoenix,
        # of the same Mountain metazone and in en_US's region, so the ID has the offset
        # the name means (UTC-7).
        ("July 5, 2026, 10:00 PM MST", [["America/Phoenix"]]),
        # No US zone writes "CST" in July; of the Central metazone's zones that do, the
        # first by IANA ID.
        ("July 5, 2026, 10:00 PM CST", [["America/Bahia_Banderas"]]),
        ("January 5, 2026, 10:00 PM CST", [["America/Chicago"]]),
    ],
)
def test_a_dated_zone_is_the_zone_that_writes_the_name_that_day(text, zones):
    assert _zones_of(FlexibleDateTimeDetector("en_US").detect(text), text) == zones


@pytest.mark.parametrize(
    "text, zones",
    [
        # No zone writes these names on these dates, but people write them all year:
        # they are read as a bare time's, as the zone that writes them in their season.
        ("January 5, 2026, 10:00 PM EDT", [["America/New_York"]]),
        ("July 5, 2026, 10:00 PM PST", [["America/Los_Angeles"]]),
        ("December 25, 2026, 9:00 AM BST", [["Europe/London"]]),
    ],
)
def test_an_out_of_season_zone_name_is_still_read(text, zones):
    assert _zones_of(FlexibleDateTimeDetector("en_US").detect(text), text) == zones


@pytest.mark.parametrize(
    "text, zones",
    [
        # Ireland writes "IST" in summer only.
        ("July 5, 2026, 10:00 PM IST", [["Europe/Dublin"], ["Asia/Kolkata"]]),
        ("January 5, 2026, 10:00 PM IST", [["Asia/Kolkata"]]),
        # en_US also reads "1/5/2026" day first, as May 1, when Ireland writes "IST".
        ("1/5/2026, 10:00 PM IST", [["Asia/Kolkata"], ["Europe/Dublin"], ["Asia/Kolkata"]]),
    ],
)
def test_a_dated_time_reads_its_zone_on_its_date(text, zones):
    assert _zones_of(FlexibleDateTimeDetector("en_US").detect(text), text) == zones


def test_a_bare_time_reads_a_zone_written_in_either_season(monkeypatch):
    # A bare time has no date: a zone is read if ICU writes the name for it today or in
    # either season of this year, so a daylight name reads in winter too.
    winter = _day_of(2027, 1, 20)
    monkeypatch.setattr(recognize, "_today", lambda: winter)
    assert _reading_days() == (winter, _day_of(2027, 1, 15), _day_of(2027, 7, 15))
    assert _zone_readings("EDT", "en_US") == (("America/New_York", "en_US"),)
    assert [zone for zone, _ in _zone_readings("IST", "en_US")] == [
        "Europe/Dublin",
        "Asia/Kolkata",
    ]


def test_the_day_is_read_afresh_not_frozen(monkeypatch):
    monkeypatch.setattr(recognize, "_today", lambda: _day_of(2030, 3, 1))
    assert _reading_days()[0] == _day_of(2030, 3, 1)
    monkeypatch.setattr(recognize, "_today", lambda: _day_of(2031, 3, 1))
    assert _reading_days()[0] == _day_of(2031, 3, 1)
    assert _reading_days({"M": 7, "d": 5})[0] == _day_of(2031, 7, 5)
    assert _reading_days({"y": 2024, "M": 1, "d": 5}) == (_day_of(2024, 1, 5),)


def _icu_writes(zone_text, zone_id, day):
    """Whether ICU formats ``zone_id`` itself as ``zone_text`` on ``day``, in some zone
    field, in some locale of English."""
    instant = day * 86400 + 43200.0
    zone = icu.TimeZone.createTimeZone(zone_id)
    for name in _language_locale_names("en"):
        for pattern in ("z", "zzzz", "v", "vvvv", "VVVV", "X", "O", "OOOO"):
            formatter = icu.SimpleDateFormat(pattern, icu.Locale(name))
            formatter.setTimeZone(zone)
            if formatter.format(instant) == zone_text:
                return True
    return False


@pytest.mark.parametrize(
    "zone_text, date",
    [
        ("IST", (2026, 7, 5)),
        ("IST", (2026, 1, 5)),
        ("MST", (2026, 7, 5)),
        ("MST", (2026, 1, 5)),
        ("CST", (2026, 7, 5)),
        ("CST", (2026, 1, 5)),
        ("EST", (2026, 1, 5)),
        ("EDT", (2026, 7, 5)),
        ("BST", (2026, 7, 5)),
        ("CET", (2026, 1, 5)),
        ("CEST", (2026, 7, 5)),
        ("AST", (2026, 1, 5)),
        ("UTC", (2026, 7, 5)),
        ("GMT", (2026, 1, 5)),
    ],
)
def test_every_dated_zone_read_is_one_icu_writes_the_name_for_that_day(zone_text, date):
    # Every zone captured, the reader's own locale's included, is one ICU itself
    # formats with the text on the reading's date.
    year, month, day = date
    months = "January February March April May June July August September October November December"
    text = f"{months.split()[month - 1]} {day}, {year}, 10:00 PM {zone_text}"
    zones = _zones_of(FlexibleDateTimeDetector("en_US").detect(text), text)
    assert zones
    for (zone_id,) in zones:
        assert _icu_writes(zone_text, zone_id, _day_of(year, month, day)), (text, zone_id)


@pytest.mark.parametrize("text", ["10 PM IST", "10 PM MST", "10 PM CST", "18:00 UTC", "10 PM BST"])
def test_every_bare_time_zone_read_is_one_icu_writes_the_name_for_this_year(text):
    zone_text = text.split()[-1]
    zones = _zones_of(FlexibleTimeDetector("en_US").detect(text), text)
    assert zones
    for (zone_id,) in zones:
        assert any(_icu_writes(zone_text, zone_id, day) for day in _reading_days()), zone_id


@pytest.mark.parametrize(
    "locale, first, second",
    [("en_US", "Europe/Dublin", "Asia/Kolkata"), ("en_IN", "Asia/Kolkata", "Europe/Dublin")],
)
def test_a_zone_ambiguous_span_resolves_as_a_tie_broken_by_the_readers_order(locale, first, second):
    detections = FlexibleTimeDetector(locale).detect("10 PM IST")
    zoned = [d for d in detections if d["text"] == "10 PM IST"]
    assert _zones_of(zoned, "10 PM IST") == [[first], [second]]
    resolution = resolve(detections)
    assert resolution.ambiguous and resolution.margin == 0
    assert _zones_of(resolution.best, "10 PM IST") == [[first]]
    assert [_zones_of(cover, "10 PM IST") for cover in resolution.covers[:2]] == [
        [[first]],
        [[second]],
    ]
    # Deposit order, not zone name, decides: reversed, the other zone wins.
    assert _zones_of(resolve(list(reversed(zoned))).best, "10 PM IST") == [[second]]
