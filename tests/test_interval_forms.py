"""Interval forms ICU's DateIntervalFormat writes beyond CLDR's listed interval patterns.

Width-adjusted skeletons (``yMMMMd``, ``yMMMMEEEEd``), 12-hour times with their AM/PM
marker, and zoned times. Surfaces are ICU's own output: ICU writes a thin space (U+2009)
around the en dash and a narrow no-break space (U+202F) before "PM".
"""

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
