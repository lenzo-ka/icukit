"""Conformance tests for the concrete ICU date detector."""

import icu
import pytest

from icukit.detectors import DateDetector, Detector

LOCALES_AND_SKELETONS = [
    (locale, skeleton)
    for locale in ("en_US", "th_TH", "fa_IR")
    for skeleton in ("yMd", "yMMMd", "yMMMEd")
]


def _instant() -> float:
    calendar = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale("en_US@calendar=gregorian")
    )
    calendar.clear()
    calendar.set(2026, 0, 3)
    return calendar.getTime()


def _formatter(locale: str, pattern: str) -> icu.SimpleDateFormat:
    formatter = icu.SimpleDateFormat(pattern, icu.Locale(locale))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    return formatter


def _rebuild(detection) -> str:
    spec = detection["spec"]
    calendar = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale(f"{spec.locale}@calendar={spec.calendar}")
    )
    calendar.clear()
    calendar_fields = {
        "y": icu.Calendar.YEAR,
        "M": icu.Calendar.MONTH,
        "d": icu.Calendar.DATE,
        "H": icu.Calendar.HOUR_OF_DAY,
        "h": icu.Calendar.HOUR,
        "m": icu.Calendar.MINUTE,
        "s": icu.Calendar.SECOND,
    }
    for name, value in detection["value"].fields:
        calendar.set(calendar_fields[name], value - 1 if name == "M" else value)
    return _formatter(spec.locale, spec.pattern).format(calendar.getTime())


@pytest.mark.parametrize(("locale", "skeleton"), LOCALES_AND_SKELETONS)
def test_date_detector_round_trip_matrix(locale, skeleton):
    detector = DateDetector(locale, skeleton)
    assert isinstance(detector, Detector)
    surface = detector._df.format(_instant())
    text = f"prefix {surface} suffix"

    detections = detector.detect(text)

    assert len(detections) == 1
    detection = detections[0]
    assert (detection["start"], detection["end"]) == (7, 7 + len(surface))
    assert detection["text"] == surface
    observed = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
    assert detection["value"].calendar == observed.getType()
    assert tuple(name for name, _ in detection["value"].fields) == ("y", "M", "d")
    assert _rebuild(detection) == surface

    fields = dict(detection["value"].fields)
    if locale == "th_TH":
        assert fields["y"] == 2569
    if locale == "fa_IR":
        assert fields["y"] == 1404


@pytest.mark.parametrize(("locale", "year_text"), [("th_TH", "2569"), ("fa_IR", "۱۴۰۴")])
def test_year_capture_uses_observed_calendar_digits_and_source_offsets(locale, year_text):
    detector = DateDetector(locale, "yMMMd")
    surface = detector._df.format(_instant())
    text = f"📅 {surface}!"

    detection = detector.detect(text)[0]
    capture = next(item for item in detection["captures"] if item.name == "y")

    assert capture.text == year_text
    assert text[capture.start : capture.end] == year_text
    assert capture.value == dict(detection["value"].fields)["y"]


@pytest.mark.parametrize("surface", ["1/3/26", "01/03/2026", "1 /3/2026"])
def test_permissive_noncanonical_date_surfaces_are_rejected(surface):
    assert DateDetector("en_US", "yMd").detect(surface) == []


def test_date_detector_rejects_non_gmt_timezone():
    with pytest.raises(ValueError, match="GMT"):
        DateDetector("en_US", "yMd", tz="America/New_York")


def test_date_detector_refuses_uninvertible_day_period_skeleton():
    # en_US "hm" best pattern is 12-hour "h:mm a"; bare (h, m) cannot reproduce AM vs PM,
    # so the detector refuses the skeleton rather than emit a non-invertible value (fugu #2).
    with pytest.raises(ValueError, match="invert"):
        DateDetector("en_US", "hm")


def test_standalone_weekday_pattern_detects_without_empty_capture():
    # ru_RU "yMdE" best pattern uses a standalone weekday ('ccc') that ICU's FieldPosition
    # cannot locate on this build; the detector omits that capture instead of emitting a
    # zero-length one, and still detects the date (fugu #3).
    detector = DateDetector("ru_RU", "yMdE")
    surface = detector._df.format(_instant())

    detections = detector.detect(surface)

    assert len(detections) == 1
    captures = detections[0]["captures"]
    assert all(capture.end > capture.start for capture in captures)
    assert {capture.name for capture in captures} == {"y", "M", "d"}
    assert tuple(name for name, _ in detections[0]["value"].fields) == ("y", "M", "d")
