"""ICU hour patterns whose literal text distinguishes them from bare numbers."""

import icu
import pytest

from icukit.detectors import DateDetector, _pattern_has_word_literal
from icukit.engine import DATE_TIME_SKELETON_FAMILY, reader_set


def _time() -> float:
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale("en"))
    calendar.clear()
    calendar.set(2026, 0, 3, 20, 7, 6)
    return calendar.getTime()


@pytest.mark.parametrize(
    ("locale", "surface", "fields"),
    [
        ("de_DE", "8 Uhr", (("H", 8),)),
        ("de_DE", "08 Uhr", (("H", 8),)),
        ("fr_FR", "8 h", (("H", 8),)),
        ("bg_BG", "08:00 ч.", (("H", 8), ("m", 0))),
        ("dsb", "zeg. 8:00", (("H", 8), ("m", 0))),
        ("eo", "08H", (("H", 8),)),
        ("zh", "8时", (("H", 8),)),
    ],
)
def test_reader_set_reads_hour_pattern_literals_whole(locale, surface, fields):
    detections = reader_set(locale).detect(surface)

    assert any(
        detection["start"] == 0
        and detection["end"] == len(surface)
        and detection["value"].fields == fields
        for detection in detections
        if hasattr(detection["value"], "fields")
    )


def test_literal_hour_keeps_the_plain_number_reading():
    detections = reader_set("de_DE").detect("8 Uhr")

    assert any(
        detection["type"] == "date:H" and detection["text"] == "8 Uhr" for detection in detections
    )
    assert any(
        detection["type"] == "number:decimal" and detection["text"] == "8"
        for detection in detections
    )


def test_locale_preference_day_period_literal_is_resolved():
    generator = icu.DateTimePatternGenerator.createInstance(icu.Locale("ee"))
    formatter = icu.SimpleDateFormat(generator.getBestPattern("j"), icu.Locale("ee"))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    surface = formatter.format(_time())

    detections = reader_set("ee").detect(surface)

    assert any(
        detection["start"] == 0
        and detection["end"] == len(surface)
        and detection["value"].fields == (("H", 20),)
        for detection in detections
        if hasattr(detection["value"], "fields")
    )


def test_every_icu_locale_hour_pattern_with_a_word_literal_is_invertible():
    """Audit fixed cycles and the locale-preference j/J/C skeletons."""
    requested = tuple(hour + rest for hour in "hHkKjJC" for rest in ("", "m", "ms"))
    instant = _time()

    for locale in sorted(icu.Locale.getAvailableLocales()):
        icu_locale = icu.Locale(locale)
        generator = icu.DateTimePatternGenerator.createInstance(icu_locale)
        by_pattern = {
            str(generator.getBestPattern(skeleton)): str(skeleton)
            for skeleton in DATE_TIME_SKELETON_FAMILY.enumerate(locale)
        }
        checked = set()
        for requested_skeleton in requested:
            pattern = str(generator.getBestPattern(requested_skeleton))
            if pattern in checked or not _pattern_has_word_literal(pattern):
                continue
            checked.add(pattern)
            skeleton = by_pattern[pattern]
            detector = DateDetector(locale, skeleton)
            formatter = icu.SimpleDateFormat(pattern, icu_locale)
            formatter.setTimeZone(icu.TimeZone.getGMT())
            surface = formatter.format(instant)

            assert any(
                detection["start"] == 0 and detection["end"] == len(surface)
                for detection in detector.detect(surface)
            ), (locale, requested_skeleton, pattern, surface)
