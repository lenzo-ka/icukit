"""Tests for flexible, recall-oriented recognizers."""

import pytest

from icukit.detectors import DateDetector, Detector, NumberDetector, detect
from icukit.recognize import FlexibleDateDetector, FlexibleNumberDetector
from icukit.resolve import resolve


@pytest.mark.parametrize("surface", ["2026", "1234"])
def test_flexible_number_gains_recall_over_strict(surface):
    strict = NumberDetector("en_US", "decimal").detect(surface)
    assert all(detection["text"] != surface for detection in strict)

    detector = FlexibleNumberDetector("en_US")
    detections = detector.detect(surface)

    assert isinstance(detector, Detector)
    assert len(detections) == 1
    assert (detections[0]["start"], detections[0]["end"]) == (0, 4)
    assert detections[0]["value"].decimal == surface


@pytest.mark.parametrize("surface, decimal", [("1,234.5", "1234.5"), ("-1,234.5", "-1234.5")])
def test_canonical_number_surfaces_still_work(surface, decimal):
    detection = FlexibleNumberDetector("en_US").detect(surface)[0]

    assert detection["value"].decimal == decimal
    assert any(c.name == "sign" for c in detection["captures"]) == surface.startswith("-")


@pytest.mark.parametrize("surface, decimal", [("1.234.567", "1234567"), ("1234,5", "1234.5")])
def test_locale_separators(surface, decimal):
    detection = FlexibleNumberDetector("de_DE").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"].decimal == decimal


def test_captures_use_source_code_point_offsets_with_astral_prefix():
    text = "📌 1,234.5!"
    detection = FlexibleNumberDetector("en_US").detect(text)[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert (detection["start"], detection["end"]) == (2, 9)
    assert captures["integer"].text == "1,234"
    assert captures["integer"].value == "1234"
    assert captures["decimal-separator"].text == "."
    assert captures["fraction"].value == "5"
    for capture in captures.values():
        assert text[capture.start : capture.end] == capture.text


def test_greedy_match_does_not_overlap_and_stops_at_non_digit():
    detections = FlexibleNumberDetector("en_US").detect("1234x")

    assert [(detection["start"], detection["end"]) for detection in detections] == [(0, 4)]
    assert detections[0]["text"] == "1234"


@pytest.mark.parametrize("surface", ["-", ".", "abc"])
def test_non_numbers_do_not_match(surface):
    assert FlexibleNumberDetector("en_US").detect(surface) == []


def test_real_text_composes_with_detect_and_resolve():
    text = "the year 2026 saw 1,234 events"
    flexible = FlexibleNumberDetector("en_US")

    detections = detect(text, [flexible])
    resolution = resolve(detections)

    assert [detection["text"] for detection in detections] == ["2026", "1,234"]
    assert [detection["text"] for detection in resolution.best] == ["2026", "1,234"]


@pytest.mark.parametrize("surface", ["1/3/26", "01/03/26"])
def test_flexible_date_gains_recall_over_strict(surface):
    assert DateDetector("en_US", "yMd").detect(surface) == []

    detector = FlexibleDateDetector("en_US")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert (detection["start"], detection["end"]) == (0, len(surface))
    assert detection["value"].fields == (("y", 26), ("M", 1), ("d", 3))
    assert detection["value"].calendar == "gregorian"
    assert detection["type"] == "date:flexible"


def test_flexible_date_accepts_four_digit_year():
    detection = FlexibleDateDetector("en_US").detect("1/3/2026")[0]

    assert detection["value"].fields == (("y", 2026), ("M", 1), ("d", 3))


def test_flexible_date_uses_locale_order_and_separator():
    detection = FlexibleDateDetector("de_DE").detect("3.1.2026")[0]

    assert detection["value"].fields == (("y", 2026), ("M", 1), ("d", 3))
    assert detection["spec"].pattern == "dd.MM.yy"


@pytest.mark.parametrize("surface", ["13/45/2026", "1/2"])
def test_flexible_date_rejects_invalid_structure_or_ranges(surface):
    assert FlexibleDateDetector("en_US").detect(surface) == []


def test_flexible_date_captures_use_code_point_offsets_and_stop_greedily():
    text = "📌 met 01/03/2026x"
    detection = FlexibleDateDetector("en_US").detect(text)[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert (detection["start"], detection["end"]) == (6, 16)
    assert detection["text"] == "01/03/2026"
    assert captures["M"].value == 1
    assert captures["d"].value == 3
    assert captures["y"].value == 2026
    for capture in captures.values():
        assert text[capture.start : capture.end] == capture.text


def test_flexible_dates_compose_with_detect_and_resolve():
    text = "met on 1/3/26 and 12/25/2026"
    detections = detect(text, [FlexibleDateDetector("en_US")])
    resolution = resolve(detections)

    assert [detection["text"] for detection in detections] == ["1/3/26", "12/25/2026"]
    assert [detection["text"] for detection in resolution.best] == [
        "1/3/26",
        "12/25/2026",
    ]
