"""Interval forms ICU's DateIntervalFormat writes beyond CLDR's listed interval patterns.

Width-adjusted skeletons (``yMMMMd``, ``yMMMMEEEEd``), 12-hour times with their AM/PM
marker, and zoned times. Surfaces are ICU's own output: ICU writes a thin space (U+2009)
around the en dash and a narrow no-break space (U+202F) before "PM".
"""

import os
import subprocess
import sys

import icu
import pytest

from icukit import DateIntervalValue, DateTimeValue
from icukit.recognize import FlexibleDateIntervalDetector

THIN = "\N{THIN SPACE}"
NNBSP = "\N{NARROW NO-BREAK SPACE}"
DASH = f"{THIN}\N{EN DASH}{THIN}"


def _format(locale, skeleton, start, end):
    """ICU's interval text for two Gregorian wall-clock tuples in the default zone."""
    instants = []
    for values in (start, end):
        calendar = icu.GregorianCalendar(icu.Locale(locale))
        calendar.clear()
        names = ("YEAR", "MONTH", "DATE", "HOUR_OF_DAY", "MINUTE")
        for name, value in zip(names, values, strict=False):
            calendar.set(getattr(icu.UCalendarDateFields, name), value)
        instants.append(calendar.getTime())
    formatter = icu.DateIntervalFormat.createInstance(skeleton, icu.Locale(locale))
    return str(formatter.format(icu.DateInterval(*instants)))


def _value(start, end):
    return DateIntervalValue(
        DateTimeValue(tuple(start.items()), "gregorian"),
        DateTimeValue(tuple(end.items()), "gregorian"),
    )


def _read(skeleton, surface, locale="en_US"):
    detections = FlexibleDateIntervalDetector(locale, skeleton).detect(surface)
    assert len(detections) == 1, detections
    assert detections[0]["text"] == surface
    return detections[0]


@pytest.mark.parametrize(
    "skeleton, surface, start, end",
    [
        (
            "yMMMMd",
            f"March 5{DASH}7, 2024",
            {"y": 2024, "M": 3, "d": 5},
            {"y": 2024, "M": 3, "d": 7},
        ),
        (
            "yMMMMd",
            f"March 5{DASH}April 9, 2025",
            {"y": 2025, "M": 3, "d": 5},
            {"y": 2025, "M": 4, "d": 9},
        ),
        (
            "yMMMMd",
            f"March 5, 2024{DASH}April 9, 2025",
            {"y": 2024, "M": 3, "d": 5},
            {"y": 2025, "M": 4, "d": 9},
        ),
        ("MMMMd", f"March 5{DASH}7", {"M": 3, "d": 5}, {"M": 3, "d": 7}),
        (
            "yMMMMEEEEd",
            f"Tuesday, March 5{DASH}Thursday, March 7, 2024",
            {"y": 2024, "M": 3, "d": 5},
            {"y": 2024, "M": 3, "d": 7},
        ),
        ("hm", f"2:07{DASH}4:07{NNBSP}PM", {"H": 14, "m": 7}, {"H": 16, "m": 7}),
        ("hm", f"10:07{NNBSP}AM{DASH}2:07{NNBSP}PM", {"H": 10, "m": 7}, {"H": 14, "m": 7}),
        ("hm", f"12:07{DASH}4:07{NNBSP}PM", {"H": 12, "m": 7}, {"H": 16, "m": 7}),
        ("h", f"2{DASH}4{NNBSP}PM", {"H": 14}, {"H": 16}),
        (
            "yMdhm",
            f"3/5/2024, 2:07{NNBSP}PM{DASH}3/7/2024, 2:07{NNBSP}PM",
            {"y": 2024, "M": 3, "d": 5, "H": 14, "m": 7},
            {"y": 2024, "M": 3, "d": 7, "H": 14, "m": 7},
        ),
        (
            "Hm",
            f"3/5/2024, 14:07{DASH}3/7/2024, 14:07",
            {"y": 2024, "M": 3, "d": 5, "H": 14, "m": 7},
            {"y": 2024, "M": 3, "d": 7, "H": 14, "m": 7},
        ),
    ],
)
def test_reads_interval_forms_icu_writes(skeleton, surface, start, end):
    assert _read(skeleton, surface)["value"] == _value(start, end)


@pytest.mark.parametrize(
    "skeleton, start, end",
    [
        ("yMMMMd", (2024, 2, 5), (2024, 2, 7)),
        ("yMMMMd", (2024, 2, 5), (2025, 3, 9)),
        ("MMMMd", (2024, 2, 5), (2024, 3, 14)),
        ("yMMMMEEEEd", (2024, 2, 5), (2024, 3, 14)),
        ("hm", (2024, 2, 5, 14, 7), (2024, 2, 5, 16, 7)),
        ("hm", (2024, 2, 5, 10, 7), (2024, 2, 5, 14, 7)),
        ("yMdhm", (2024, 2, 5, 14, 7), (2024, 2, 7, 14, 7)),
        ("yMMMdhm", (2024, 2, 5, 14, 7), (2024, 2, 5, 16, 7)),
    ],
)
def test_reads_what_icu_formats_here(skeleton, start, end):
    # The same forms, formatted by ICU at test time rather than copied.
    surface = _format("en_US", skeleton, start, end)
    assert _read(skeleton, surface)


def test_previously_unread_skeletons_now_have_patterns():
    for skeleton in ("yMMMMd", "MMMMd", "yMMMMEEEEd", "hm", "h", "hmv", "Hmv"):
        assert FlexibleDateIntervalDetector("en_US", skeleton).has_patterns, skeleton


@pytest.mark.parametrize(
    "skeleton, surface, zone_text, zone_id",
    [
        ("Hmv", f"14:07{DASH}16:07 ET", "ET", "America/New_York"),
        ("hmv", f"2:07{DASH}4:07{NNBSP}PM PT", "PT", "America/Los_Angeles"),
    ],
)
def test_reads_a_zoned_interval_and_captures_the_zone(skeleton, surface, zone_text, zone_id):
    detection = _read(skeleton, surface)
    assert detection["value"] == _value({"H": 14, "m": 7}, {"H": 16, "m": 7})
    zones = [capture for capture in detection["captures"] if capture.name == "time-zone"]
    assert [(zone.text, zone.value) for zone in zones] == [(zone_text, zone_id)]
    assert surface[zones[0].start : zones[0].end] == zone_text


def test_reads_a_zoned_interval_in_the_default_zone():
    surface = _format("en_US", "hmv", (2024, 2, 5, 14, 7), (2024, 2, 5, 16, 7))
    detection = _read("hmv", surface)
    assert detection["value"] == _value({"H": 14, "m": 7}, {"H": 16, "m": 7})
    assert any(capture.name == "time-zone" for capture in detection["captures"])


@pytest.mark.parametrize(
    "skeleton, surface",
    [
        # Tuesday is March 5, 2024; ICU would not write Wednesday there.
        ("yMMMMEEEEd", f"Wednesday, March 5{DASH}Thursday, March 7, 2024"),
        # The month name where en_US never writes it.
        ("yMMMMd", f"5 March{DASH}7, 2024"),
        # Not a day-period marker ICU writes.
        ("hm", f"2:07{DASH}4:07{NNBSP}XM"),
        # A 13th hour on a 12-hour clock.
        ("hm", f"2:07{DASH}13:07{NNBSP}PM"),
        # Not a zone ICU writes.
        ("hmv", f"2:07{DASH}4:07{NNBSP}PM QQ"),
    ],
)
def test_rejects_what_icu_would_not_write(skeleton, surface):
    assert FlexibleDateIntervalDetector("en_US", skeleton).detect(surface) == []


@pytest.mark.parametrize(
    "skeleton, surface",
    [
        # ICU writes these for 22:00-12:00, 23:00-13:00 and 23:30-12:30 as well, but with
        # the marker carried and no date the reading must run forward.
        ("h", f"10{DASH}12{NNBSP}PM"),
        ("h", f"11{DASH}1{NNBSP}PM"),
        ("hm", f"11:30{DASH}12:30{NNBSP}PM"),
    ],
)
def test_a_carried_marker_does_not_read_backwards(skeleton, surface):
    assert FlexibleDateIntervalDetector("en_US", skeleton).detect(surface) == []


@pytest.mark.parametrize(
    "skeleton, surface, start, end",
    [
        ("h", f"11{NNBSP}PM{DASH}1{NNBSP}AM", {"H": 23}, {"H": 1}),
        ("hm", f"11:07{NNBSP}PM{DASH}1:07{NNBSP}AM", {"H": 23, "m": 7}, {"H": 1, "m": 7}),
        ("hm", f"10:07{NNBSP}AM{DASH}12:07{NNBSP}PM", {"H": 10, "m": 7}, {"H": 12, "m": 7}),
    ],
)
def test_two_markers_read_overnight_and_across_noon(skeleton, surface, start, end):
    assert _read(skeleton, surface)["value"] == _value(start, end)


@pytest.fixture
def default_zone():
    """Set ICU's default zone for one test, restoring the process default after."""
    original = icu.TimeZone.createDefault()

    def set_zone(zone_id):
        icu.TimeZone.setDefault(icu.TimeZone.createTimeZone(zone_id))

    yield set_zone
    icu.TimeZone.setDefault(original)


@pytest.mark.parametrize(
    "skeleton, surface, zone_id, defaults",
    [
        ("hmz", f"2:07{DASH}4:07{NNBSP}PM EST", "America/New_York", ("America/Detroit", "UTC")),
        ("Hmv", f"14:07{DASH}16:07 India Time", "Asia/Kolkata", ("Asia/Calcutta", "UTC")),
    ],
)
def test_zone_capture_is_the_parsed_zone_whatever_the_default(
    default_zone, skeleton, surface, zone_id, defaults
):
    for default in defaults:
        default_zone(default)
        zones = [c for c in _read(skeleton, surface)["captures"] if c.name == "time-zone"]
        assert [zone.value for zone in zones] == [zone_id], default


@pytest.mark.parametrize(
    "skeleton, text, reading",
    [
        ("hm", f"It runs 2:07{DASH}4:07{NNBSP}PM.", f"2:07{DASH}4:07{NNBSP}PM"),
        ("hmv", f"It runs 2:07{DASH}4:07{NNBSP}PM ET.", f"2:07{DASH}4:07{NNBSP}PM ET"),
        ("yMMMMd", f"From March 5{DASH}7, 2024.", f"March 5{DASH}7, 2024"),
    ],
)
def test_reads_an_interval_at_the_end_of_a_sentence(skeleton, text, reading):
    detections = FlexibleDateIntervalDetector("en_US", skeleton).detect(text)
    assert [detection["text"] for detection in detections] == [reading]


@pytest.mark.parametrize(
    "surface, zone_text, zone_id",
    [
        (f"2:07{DASH}4:07{NNBSP}PM EDT", "EDT", "America/New_York"),
        (f"2:07{DASH}4:07{NNBSP}PM PDT", "PDT", "America/Los_Angeles"),
        (f"2:07{DASH}4:07{NNBSP}PM PST", "PST", "America/Los_Angeles"),
    ],
)
def test_reads_standard_and_daylight_names_on_a_time_only_interval(surface, zone_text, zone_id):
    detection = _read("hmz", surface)
    assert detection["value"] == _value({"H": 14, "m": 7}, {"H": 16, "m": 7})
    zones = [c for c in detection["captures"] if c.name == "time-zone"]
    assert [(zone.text, zone.value) for zone in zones] == [(zone_text, zone_id)]


def test_a_dated_interval_keeps_its_own_zone_name():
    # March 5 is before US daylight time began in 2024, and July 5 is inside it.
    detector = FlexibleDateIntervalDetector("en_US", "yMdhmz")
    assert detector.detect(f"3/5/2024, 2:07{NNBSP}PM EST{DASH}3/7/2024, 2:07{NNBSP}PM EST")
    assert detector.detect(f"7/5/2024, 2:07{NNBSP}PM EST{DASH}7/7/2024, 2:07{NNBSP}PM EST") == []


@pytest.mark.parametrize("zone_text", ["PST", "GMT-08:00", "UTC", "-0800"])
def test_zone_gate_rejects_text_the_v_field_does_not_write(zone_text):
    # SimpleDateFormat parses each of these to the end under the generic "v" field, so the
    # rejection is the reformat gate's: ICU writes "PT", "GMT-8" and "GMT" there.
    side = f"16:07 {zone_text}"
    position = icu.ParsePosition(0)
    calendar = icu.Calendar.createInstance(icu.Locale("en_US"))
    icu.SimpleDateFormat("HH:mm v", icu.Locale("en_US")).parse(
        icu.UnicodeString(side), calendar, position
    )
    assert position.getErrorIndex() == -1 and position.getIndex() == len(side)
    detector = FlexibleDateIntervalDetector("en_US", "Hmv")
    assert detector.detect(f"14:07{DASH}{side}") == []


@pytest.mark.parametrize("zone_text", ["Pacific Time", "America/Los_Angeles"])
def test_zone_names_the_v_field_does_not_parse_are_not_read(zone_text):
    detector = FlexibleDateIntervalDetector("en_US", "Hmv")
    assert detector.detect(f"14:07{DASH}16:07 {zone_text}") == []


@pytest.mark.parametrize(
    "surface, start, end",
    [
        # Inside the spring-forward gap in America/New_York.
        (
            f"3/10/2024, 02:30{DASH}02:45",
            {"y": 2024, "M": 3, "d": 10, "H": 2, "m": 30},
            {"y": 2024, "M": 3, "d": 10, "H": 2, "m": 45},
        ),
        # Inside the spring-forward gap in Europe/Berlin.
        (
            f"3/31/2024, 02:30{DASH}02:45",
            {"y": 2024, "M": 3, "d": 31, "H": 2, "m": 30},
            {"y": 2024, "M": 3, "d": 31, "H": 2, "m": 45},
        ),
        # Inside the fall-back overlap in America/New_York.
        (
            f"11/3/2024, 01:30{DASH}01:45",
            {"y": 2024, "M": 11, "d": 3, "H": 1, "m": 30},
            {"y": 2024, "M": 11, "d": 3, "H": 1, "m": 45},
        ),
    ],
)
def test_a_plain_interval_reads_the_same_in_any_default_zone(default_zone, surface, start, end):
    # A recipe with no zone field is wall-clock time in no zone: a DST gap or overlap in
    # the process default zone must not shift or drop it.
    for default in ("UTC", "America/New_York", "Europe/Berlin"):
        default_zone(default)
        assert _read("yMdHm", surface)["value"] == _value(start, end), default


@pytest.mark.parametrize("tz", ["UTC", "America/New_York", "Europe/Berlin"])
@pytest.mark.parametrize(
    "skeleton, surface",
    [("yMdHm", "3/10/2024, 02:30 – 02:45"), ("yMdhmz", "3/10/2024, 2:30 – 2:45 AM GMT")],
)
def test_an_interval_reads_under_the_process_tz(tz, skeleton, surface):
    # Gap readings with the zone taken from the process environment at startup.
    script = (
        "import sys\n"
        "from icukit.recognize import FlexibleDateIntervalDetector as F\n"
        "print([d['text'] for d in F('en_US', sys.argv[1]).detect(sys.argv[2])])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, skeleton, surface],
        env={**os.environ, "TZ": tz},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == repr([surface])


@pytest.mark.parametrize(
    "skeleton, surface, zone_text, zone_id",
    [
        # Inside the spring-forward gap in America/New_York, written in GMT.
        ("yMdhmz", f"3/10/2024, 2:30{DASH}2:45{NNBSP}AM GMT", "GMT", "Etc/GMT"),
        # ICU writes Etc/UTC as "UTC" and "GMT+0"; it parses both to Etc/GMT.
        ("yMdhmz", f"3/10/2024, 2:30{DASH}2:45{NNBSP}AM UTC", "UTC", "Etc/GMT"),
        ("Hmv", f"02:30{DASH}02:45 GMT+0", "GMT+0", "Etc/GMT"),
        # A GMT offset parses to a custom zone, which has no IANA form and keeps its ID.
        ("Hmv", f"02:30{DASH}02:45 GMT-8", "GMT-8", "GMT-08:00"),
        ("hmz", f"2:30{DASH}2:45{NNBSP}AM GMT+5:30", "GMT+5:30", "GMT+05:30"),
    ],
)
def test_a_zoned_interval_reads_the_same_in_any_default_zone(
    default_zone, skeleton, surface, zone_text, zone_id
):
    for default in ("UTC", "America/New_York", "Europe/Berlin"):
        default_zone(default)
        detection = _read(skeleton, surface)
        dated = {"y": 2024, "M": 3, "d": 10} if skeleton.startswith("y") else {}
        start, end = {**dated, "H": 2, "m": 30}, {**dated, "H": 2, "m": 45}
        assert detection["value"] == _value(start, end), default
        zones = [c for c in detection["captures"] if c.name == "time-zone"]
        assert [(zone.text, zone.value) for zone in zones] == [(zone_text, zone_id)], default


@pytest.mark.parametrize(
    "locale, surface, zone_ids",
    [
        # en_US writes no "IST"; en_IE writes it for Irish summer time and en_IN for
        # India time, so the interval is read in each, in locale-name order.
        ("en_US", f"2:07{DASH}4:07{NNBSP}PM IST", ["Europe/Dublin", "Asia/Kolkata"]),
        # A locale that writes the name reads its own zone first.
        ("en_IN", f"2:07{DASH}4:07{NNBSP}pm IST", ["Asia/Kolkata", "Europe/Dublin"]),
        # en_CA's "EST" is America/Toronto, of New York's metazone: one reading.
        ("en_US", f"2:07{DASH}4:07{NNBSP}PM EST", ["America/New_York"]),
    ],
)
def test_an_interval_is_read_once_per_zone_its_zone_text_names(
    default_zone, locale, surface, zone_ids
):
    for default in ("UTC", "Asia/Tokyo"):
        default_zone(default)
        detections = FlexibleDateIntervalDetector(locale, "hmz").detect(surface)
        assert [d["text"] for d in detections] == [surface] * len(zone_ids), default
        assert [
            [(c.text, c.value) for c in d["captures"] if c.name == "time-zone"] for d in detections
        ] == [[("IST" if "IST" in surface else "EST", zone_id)] for zone_id in zone_ids], default
        values = {d["value"] for d in detections}
        assert values == {_value({"H": 14, "m": 7}, {"H": 16, "m": 7})}


def test_each_zone_reading_is_gated_in_its_own_zone():
    # Ireland writes "IST" only in summer: a January interval is India time alone.
    detector = FlexibleDateIntervalDetector("en_US", "yMdhmz")
    january = f"1/15/2024, 2:07{NNBSP}PM IST{DASH}1/17/2024, 2:07{NNBSP}PM IST"
    july = f"7/15/2024, 2:07{NNBSP}PM IST{DASH}7/17/2024, 2:07{NNBSP}PM IST"
    zones = [
        [c.value for c in d["captures"] if c.name == "time-zone"] for d in detector.detect(january)
    ]
    assert zones == [["Asia/Kolkata", "Asia/Kolkata"]]
    zones = [
        [c.value for c in d["captures"] if c.name == "time-zone"] for d in detector.detect(july)
    ]
    assert zones == [["Europe/Dublin", "Europe/Dublin"], ["Asia/Kolkata", "Asia/Kolkata"]]
