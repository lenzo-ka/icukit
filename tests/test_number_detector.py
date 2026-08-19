"""Conformance tests for the concrete ICU number detector."""

import pytest

from icukit.detectors import Detector, NumberDetector


@pytest.mark.parametrize(
    ("locale", "kind", "number", "decimal", "currency"),
    [
        ("en_US", "decimal", -1234567.5, "-1234567.5", None),
        ("de_DE", "decimal", -1234567.5, "-1234567.5", None),
        ("hi_IN", "decimal", -1234567.5, "-1234567.5", None),
        ("en_US", "percent", 0.07, "0.07", None),
        ("en_US", "currency", 1234.5, "1234.50", "USD"),
    ],
)
def test_number_detector_round_trip_matrix(locale, kind, number, decimal, currency):
    detector = NumberDetector(locale, kind)
    assert isinstance(detector, Detector)
    surface = detector._nf.format(number)
    text = f"prefix {surface} suffix"

    detections = detector.detect(text)

    assert len(detections) == 1
    detection = detections[0]
    assert (detection["start"], detection["end"]) == (7, 7 + len(surface))
    assert detection["text"] == surface
    assert detection["value"].decimal == decimal
    assert detection["value"].currency == currency


@pytest.mark.parametrize(
    ("locale", "integer_text", "separator"),
    [("en_US", "1,234,567", "."), ("de_DE", "1.234.567", ",")],
)
def test_coarse_captures_include_grouping_and_use_source_offsets(locale, integer_text, separator):
    detector = NumberDetector(locale, "decimal")
    surface = detector._nf.format(1234567.5)
    text = f"📌 {surface}!"

    detection = detector.detect(text)[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert captures["integer"].text == integer_text
    assert captures["decimal-separator"].text == separator
    for capture in captures.values():
        assert text[capture.start : capture.end] == capture.text


@pytest.mark.parametrize(
    ("kind", "surface"),
    [
        ("decimal", "1,2,3"),
        ("decimal", "12 . 5"),
        ("currency", "$ 5"),
        ("decimal", "1.2345"),
    ],
)
def test_permissive_noncanonical_number_surfaces_are_not_accepted(kind, surface):
    detections = NumberDetector("en_US", kind).detect(surface)

    assert all(detection["text"] != surface for detection in detections)


def test_number_spec_reflects_indian_grouping_sizes():
    detector = NumberDetector("hi_IN", "decimal")
    detection = detector.detect(detector._nf.format(1234567.5))[0]

    assert detection["spec"].grouping_sizes == (2, 3)


def test_number_spec_has_no_grouping_sizes_when_grouping_is_off():
    detector = NumberDetector("en_US", "decimal")
    detector._nf.setGroupingUsed(False)
    surface = detector._nf.format(1234.5)

    detection = detector.detect(surface)[0]

    assert detection["spec"].grouping_sizes is None


def test_currency_override_sets_type_value_and_spec():
    detector = NumberDetector("en_US", "currency", "EUR")
    surface = detector._nf.format(5)

    detection = detector.detect(surface)[0]

    assert detector.type == "number:currency:EUR"
    assert detection["value"].currency == "EUR"
    assert detection["spec"].currency == "EUR"
    assert next(c for c in detection["captures"] if c.name == "currency").text == "€"


def test_large_integer_surface_round_trips_without_double_rounding():
    # 2^53 + 1 is not representable as a double; routing the parsed value through
    # getDouble() would reject this exact surface and mis-detect a suffix (fugu #1).
    detector = NumberDetector("en_US", "decimal")
    surface = "9,007,199,254,740,993"
    detections = detector.detect(surface)
    assert len(detections) == 1
    assert detections[0]["text"] == surface
    assert detections[0]["value"].decimal == "9007199254740993"


def test_invalid_number_detector_arguments_are_rejected():
    with pytest.raises(ValueError, match="kind"):
        NumberDetector("en_US", "scientific")
    with pytest.raises(ValueError, match="currency"):
        NumberDetector("en_US", "decimal", "USD")
