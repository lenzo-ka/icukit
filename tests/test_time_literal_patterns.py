"""ICU hour patterns whose literal text distinguishes them from bare numbers."""

import icu
import pytest

from icukit.detectors import (
    _NUMBER_RUN_MARKS,
    _RANGE_RUN_MARKS,
    DateDetector,
    _pattern_has_word_literal,
    _pattern_runs,
    _word_interior_offsets,
)
from icukit.engine import (
    DATE_TIME_SKELETON_FAMILY,
    generated_detectors_report,
    reader_set,
)


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


@pytest.mark.parametrize(
    ("surface", "hour_pattern"), [("8 Uhr", "H 'Uhr'"), ("08 Uhr", "HH 'Uhr'")]
)
def test_literal_hour_spec_records_the_width_actually_read(surface, hour_pattern):
    detection = next(
        item for item in DateDetector("de_DE", "H").detect(surface) if item["text"] == surface
    )

    assert detection["spec"].pattern == hour_pattern
    hour = next(capture for capture in detection["captures"] if capture.name == "H")
    assert hour.text == surface.split()[0]


@pytest.mark.parametrize(
    ("locale", "surface", "fragment", "whole_time"),
    [
        ("de_DE", "08:00 Uhr", "00 Uhr", "08:00"),
        ("bg_BG", "08:00 ч.", "00 ч.", "08:00 ч."),
    ],
)
def test_literal_hour_does_not_start_inside_a_time(locale, surface, fragment, whole_time):
    detections = reader_set(locale).detect(surface)

    assert not any(
        detection["type"] == "date:H" and detection["text"] == fragment for detection in detections
    )
    assert any(
        detection["start"] == 0
        and detection["text"] == whole_time
        and detection["type"] == "date:Hm"
        and detection["value"].fields == (("H", 8), ("m", 0))
        for detection in detections
    )


@pytest.mark.parametrize(("surface", "start"), [("8 Uhr", 0), ("um 8 Uhr", 3)])
def test_literal_hour_keeps_token_aligned_readings(surface, start):
    detections = reader_set("de_DE").detect(surface)

    assert any(
        detection["type"] == "date:H"
        and detection["start"] == start
        and detection["end"] == len(surface)
        and detection["value"].fields == (("H", 8),)
        for detection in detections
    )


@pytest.mark.parametrize("separator", ["/", "-", "–", ":"])
def test_literal_hours_on_both_sides_of_punctuation_are_kept(separator):
    text = f"8 Uhr{separator}9 Uhr"
    detections = reader_set("de_DE").detect(text)

    assert [
        (detection["start"], detection["end"], detection["text"])
        for detection in detections
        if detection["type"] == "date:H"
    ] == [(0, 5, "8 Uhr"), (6, 11, "9 Uhr")]


def test_literal_hour_before_a_sentence_period_and_number_is_kept():
    text = "Es ist 8 Uhr.9 Leute kamen"

    assert any(
        detection["type"] == "date:H" and detection["start"] == 7 and detection["end"] == 12
        for detection in reader_set("de_DE").detect(text)
    )


@pytest.mark.parametrize(
    ("locale", "text", "start", "fragment"),
    [
        ("dsb", "3zeg. 8:00", 1, "zeg. 8:00"),
        ("dsb", "555-1234zeg. 8:00", 8, "zeg. 8:00"),
        ("nds", "1.2.3Kl. 8.00", 5, "Kl. 8.00"),
        ("nds", "2026-10-13Kl. 8.00", 10, "Kl. 8.00"),
        ("dsb", "1.5zeg. 8:00", 3, "zeg. 8:00"),
        ("dz", "123ཆུ་ཚོད་༠༨", 3, "ཆུ་ཚོད་༠༨"),
        ("bg", "3.5сб, 08:00 ч.", 3, "сб, 08:00 ч."),
        ("de", "5Sa., 8 Uhr morgens", 1, "Sa., 8 Uhr morgens"),
        ("bg", "5сб, 08:00 ч.5", 1, "сб, 08:00 ч."),
    ],
)
def test_literal_hour_does_not_start_inside_an_icu_word(locale, text, start, fragment):
    assert not any(
        detection["type"].startswith("date:")
        and detection["start"] == start
        and detection["text"] == fragment
        for detection in reader_set(locale).detect(text)
    )


def test_literal_hour_skips_scan_when_its_literal_is_absent(monkeypatch):
    detector = DateDetector("de_DE", "H")

    def fail_scan(*args, **kwargs):
        pytest.fail("literal-absent text reached the strict scanner")

    monkeypatch.setattr("icukit.detectors._scan", fail_scan)

    assert detector.detect("Am Morgen beginnt die Arbeit.") == []


def test_literal_hour_skips_scan_when_its_literal_is_an_ordinary_word(monkeypatch):
    detector = DateDetector("de_DE", "H")

    def fail_scan(*args, **kwargs):
        pytest.fail("literal prose without an adjacent digit reached the strict scanner")

    monkeypatch.setattr("icukit.detectors._scan", fail_scan)

    assert detector.detect("Die Uhr tickt und der Hund bellt im Haus.") == []


@pytest.mark.parametrize(
    ("locale", "surface", "expected_type"),
    [
        ("ja", "9西暦2026年", "date:Gy"),
        ("zh_Hans_CN", "9公元2026年", "date:Gy"),
        ("ii", "9ꃅꋊꊂ 2026 ꋍꆪ 3ꑍ", "date:Gy"),
    ],
)
def test_literal_date_reader_can_start_after_an_adjacent_digit(locale, surface, expected_type):
    assert any(
        detection["type"] == expected_type and detection["start"] == 1
        for detection in reader_set(locale).detect(surface)
    )


@pytest.mark.parametrize(
    ("locale", "surface", "fragment"),
    [
        ("zh", "8时30分", "8时"),
        ("dsb", "zeg. 8:00", "zeg. 8"),
        ("dz", "ཆུ་ཚོད་༡༢:༠༠", "ཆུ་ཚོད་༡༢"),
    ],
)
def test_literal_hour_does_not_end_inside_a_time(locale, surface, fragment):
    assert not any(
        detection["text"] == fragment and detection["type"] in {"date:H", "date:J"}
        for detection in reader_set(locale).detect(surface)
    )


@pytest.mark.parametrize("separator", sorted(_RANGE_RUN_MARKS))
def test_literal_hour_is_kept_as_a_complete_range_endpoint(separator):
    detections = reader_set("de_DE").detect(f"8{separator}9 Uhr")

    assert any(
        detection["type"] == "date:H" and detection["text"] == "9 Uhr" for detection in detections
    )


@pytest.mark.parametrize(
    ("pattern", "edges"),
    [
        ("HH 'Uhr'", (True, False)),
        ("'zeg'. H:mm", (False, True)),
        ("H时", (True, False)),
        ("ཆུ་ཚོད་HH", (False, True)),
    ],
)
def test_pattern_digit_boundaries_follow_quoted_and_unquoted_runs(pattern, edges):
    from icukit.detectors import _pattern_digit_boundaries

    assert _pattern_digit_boundaries(pattern) == edges


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


@pytest.mark.parametrize(("locale", "skeleton"), [("fr_CA", "Bh"), ("dsb", "Bh")])
def test_icu_unparseable_literal_day_period_detector_is_reported(locale, skeleton):
    report = generated_detectors_report(locale, (DATE_TIME_SKELETON_FAMILY,))

    skipped = next(item for item in report.skipped if item.spec == skeleton)
    assert "ICU-unparseable" in skipped.reason
    assert all(detector.skeleton != skeleton for detector in report.detectors.detectors)


def _reformat_detection(detection) -> str:
    spec = detection["spec"]
    calendar = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale(f"{spec.locale}@calendar={spec.calendar}")
    )
    calendar.clear()
    calendar_fields = {
        "H": icu.Calendar.HOUR_OF_DAY,
        "h": icu.Calendar.HOUR,
        "m": icu.Calendar.MINUTE,
        "s": icu.Calendar.SECOND,
    }
    for name, value in detection["value"].fields:
        calendar.set(calendar_fields[name], value)
    formatter = icu.SimpleDateFormat(spec.pattern, icu.Locale(spec.locale))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    return formatter.format(calendar.getTime())


@pytest.mark.slow
def test_every_admitted_literal_12_hour_surface_round_trips_at_midnight_and_noon():
    """Every admitted h/K plus day-period reader preserves the written instant."""
    instants = []
    for hour in (0, 12):
        calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale("en"))
        calendar.clear()
        calendar.set(2026, 0, 3, hour, 7, 6)
        instants.append(calendar.getTime())

    for locale in sorted(icu.Locale.getAvailableLocales()):
        report = generated_detectors_report(locale, (DATE_TIME_SKELETON_FAMILY,))
        for detector in report.detectors.detectors:
            fields = {letter for letter, _ in _pattern_runs(detector.pattern)}
            if (
                not detector._literal_words
                or not fields & {"h", "K"}
                or not fields & {"a", "b", "B"}
                or fields & {"E", "e", "c"}
            ):
                continue
            for instant in instants:
                surface = detector._df.format(instant)
                full = [
                    detection
                    for detection in detector.detect(surface)
                    if detection["start"] == 0 and detection["end"] == len(surface)
                ]
                assert full, (locale, detector.skeleton, detector.pattern, surface)
                assert all(_reformat_detection(detection) == surface for detection in full)


@pytest.mark.slow
def test_every_admitted_literal_hour_keeps_canonical_literal_boundaries():
    """Separated literal-hour surfaces survive, but ICU-word fragments do not."""
    from icukit.detectors import _pattern_literal_boundaries

    instant = _time()
    for locale in sorted(icu.Locale.getAvailableLocales()):
        report = generated_detectors_report(locale, (DATE_TIME_SKELETON_FAMILY,))
        for detector in report.detectors.detectors:
            if not detector._literal_hour:
                continue
            surface = detector._df.format(instant)
            starts_with_literal, ends_with_literal = _pattern_literal_boundaries(detector.pattern)
            glued_contexts = []
            if starts_with_literal:
                glued_contexts.append((f"7{surface}", 1, 1))
            if ends_with_literal:
                glued_contexts.append((f"{surface}7", 0, len(surface)))
            for text, start, boundary in glued_contexts:
                if boundary not in _word_interior_offsets(text, locale):
                    continue
                assert not any(
                    detection["start"] == start
                    and detection["end"] == start + len(surface)
                    and detection["text"] == surface
                    for detection in detector.detect(text)
                ), (locale, detector.skeleton, detector.pattern, surface, text)
            if not detector._guard_literal_hour_boundaries:
                continue
            for mark in _NUMBER_RUN_MARKS | {"\u202f", "~", "～", "：", "／", "．"}:
                contexts = []
                if starts_with_literal:
                    contexts.append((f"7{mark}{surface}", 2, 2))
                if ends_with_literal:
                    contexts.append((f"{surface}{mark}7", 0, len(surface)))
                for text, start, boundary in contexts:
                    found = any(
                        detection["start"] == start
                        and detection["end"] == start + len(surface)
                        and detection["text"] == surface
                        for detection in detector.detect(text)
                    )
                    expected = boundary not in _word_interior_offsets(text, locale)
                    assert found is expected, (
                        locale,
                        detector.skeleton,
                        detector.pattern,
                        surface,
                        text,
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
