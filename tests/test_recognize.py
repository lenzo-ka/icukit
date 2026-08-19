"""Tests for flexible, recall-oriented recognizers."""

import pytest

from icukit.detectors import (
    DateDetector,
    Detector,
    NumberDetector,
    NumberFormatSpec,
    NumberValue,
    detect,
)
from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleDateDetector,
    FlexibleFractionDetector,
    FlexibleNumberDetector,
    FlexiblePercentDetector,
    FlexibleTimeDetector,
)
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


@pytest.mark.parametrize("surface, decimal", [("7%", "0.07"), ("7 %", "0.07"), ("7.5%", "0.075")])
def test_flexible_percent_gains_recall(surface, decimal):
    if surface == "7 %":
        assert NumberDetector("en_US", "percent").detect(surface) == []

    detector = FlexiblePercentDetector("en_US")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert detection["value"].decimal == decimal
    assert detection["value"].currency is None
    assert detection["spec"] == NumberFormatSpec("en_US", "percent")
    assert [capture.name for capture in detection["captures"]][-1] == "percent"


@pytest.mark.parametrize(
    "surface, decimal", [("$5", "5"), ("$1234", "1234"), ("$1,234.50", "1234.50")]
)
def test_flexible_currency_gains_recall(surface, decimal):
    strict = NumberDetector("en_US", "currency", "USD").detect(surface)
    if surface in {"$5", "$1234"}:
        assert all(detection["text"] != surface for detection in strict)

    detector = FlexibleCurrencyDetector("en_US", "USD")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert detection["value"] == NumberValue(decimal, "USD")
    assert detection["spec"] == NumberFormatSpec("en_US", "currency", currency="USD")
    assert detection["captures"][0].name == "currency"


@pytest.mark.parametrize("surface", ["$5", "$ 5", "$\N{NO-BREAK SPACE}5"])
def test_flexible_currency_accepts_optional_space_before_number(surface):
    detection = FlexibleCurrencyDetector("en_US", "USD").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"] == NumberValue("5", "USD")


@pytest.mark.parametrize("surface", ["5€", "5 €", "5\N{NO-BREAK SPACE}€"])
def test_flexible_currency_accepts_symbol_after_number(surface):
    detection = FlexibleCurrencyDetector("de_DE", "EUR").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"] == NumberValue("5", "EUR")
    assert detection["captures"][-1].name == "currency"


@pytest.mark.parametrize(
    "detector, surface",
    [
        (FlexiblePercentDetector("en_US"), "%"),
        (FlexiblePercentDetector("en_US"), "7"),
        (FlexibleCurrencyDetector("en_US", "USD"), "$"),
        (FlexibleCurrencyDetector("en_US", "USD"), "5"),
    ],
)
def test_flexible_money_requires_both_number_and_symbol(detector, surface):
    assert detector.detect(surface) == []


def test_flexible_money_uses_code_point_offsets_with_astral_prefix():
    text = "📌 7 % and $1,234.50"
    percent = FlexiblePercentDetector("en_US").detect(text)[0]
    currency = FlexibleCurrencyDetector("en_US", "USD").detect(text)[0]

    assert (percent["start"], percent["end"], percent["text"]) == (2, 5, "7 %")
    assert (currency["start"], currency["end"], currency["text"]) == (
        10,
        19,
        "$1,234.50",
    )
    for detection in (percent, currency):
        for capture in detection["captures"]:
            assert text[capture.start : capture.end] == capture.text


def test_flexible_money_composes_with_detect_and_resolve():
    text = "about 7% of $1,234 spent"
    detectors = [FlexiblePercentDetector("en_US"), FlexibleCurrencyDetector("en_US", "USD")]

    detections = detect(text, detectors)
    resolution = resolve(detections)

    assert [detection["text"] for detection in detections] == ["7%", "$1,234"]
    assert [detection["text"] for detection in resolution.best] == ["7%", "$1,234"]


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


@pytest.mark.parametrize(
    "surface, fields",
    [
        ("3:45", (("H", 3), ("m", 45))),
        ("15:45", (("H", 15), ("m", 45))),
        ("3:45 PM", (("H", 15), ("m", 45))),
        ("9:30am", (("H", 9), ("m", 30))),
        ("3:45:30", (("H", 3), ("m", 45), ("s", 30))),
        ("12:00 AM", (("H", 0), ("m", 0))),
        ("12:00 PM", (("H", 12), ("m", 0))),
    ],
)
def test_flexible_time_gains_recall(surface, fields):
    detector = FlexibleTimeDetector("en_US")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert (detection["start"], detection["end"]) == (0, len(surface))
    assert detection["value"].fields == fields
    assert detection["value"].calendar == "gregorian"
    assert detection["type"] == "time:flexible"


def test_flexible_time_day_period_capture_and_conversion():
    detection = FlexibleTimeDetector("en_US").detect("3:45 PM")[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert captures["H"].value == 3
    assert captures["m"].value == 45
    assert captures["day-period"].text == " PM"
    assert captures["day-period"].form == "symbol"
    assert detection["value"].fields == (("H", 15), ("m", 45))


def test_flexible_time_uses_locale_separator_and_24_hour_convention():
    detector = FlexibleTimeDetector("de_DE")

    assert detector.hour12 is False
    assert detector._separator == ":"
    detection = detector.detect("15:45")[0]
    assert detection["value"].fields == (("H", 15), ("m", 45))
    assert detection["spec"].pattern == "HH:mm"


def test_flexible_time_keeps_bare_time_when_day_period_hour_out_of_range():
    detection = FlexibleTimeDetector("en_US").detect("15:45 PM")[0]

    assert detection["text"] == "15:45"
    assert not any(c.name == "day-period" for c in detection["captures"])


@pytest.mark.parametrize("surface", [":", "3", "3:4", "3:99", "abc"])
def test_flexible_time_rejects_non_times(surface):
    assert FlexibleTimeDetector("en_US").detect(surface) == []


def test_flexible_time_captures_use_code_point_offsets_with_astral_prefix():
    text = "📌 at 9:30am!"
    detection = FlexibleTimeDetector("en_US").detect(text)[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert (detection["start"], detection["end"], detection["text"]) == (5, 11, "9:30am")
    assert captures["H"].value == 9
    assert captures["m"].value == 30
    for capture in captures.values():
        assert text[capture.start : capture.end] == capture.text


def test_flexible_time_composes_with_detect_and_resolve():
    text = "wake at 6:30am, land 15:45"
    detections = detect(text, [FlexibleTimeDetector("en_US")])
    resolution = resolve(detections)

    assert [detection["text"] for detection in detections] == ["6:30am", "15:45"]
    assert [detection["text"] for detection in resolution.best] == ["6:30am", "15:45"]


@pytest.mark.parametrize(
    "surface, decimal, names",
    [
        ("1/2", "0.5", ["numerator", "denominator"]),
        ("3/2", "1.5", ["numerator", "denominator"]),
        ("3 1/2", "3.5", ["whole", "numerator", "denominator"]),
        ("1/3", "0.333333333333", ["numerator", "denominator"]),
    ],
)
def test_flexible_fraction_gains_recall(surface, decimal, names):
    detector = FlexibleFractionDetector("en_US")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert (detection["start"], detection["end"]) == (0, len(surface))
    assert detection["value"] == NumberValue(decimal, None)
    assert detection["type"] == "fraction:flexible"
    assert [capture.name for capture in detection["captures"]] == names


def test_flexible_fraction_rejects_zero_denominator():
    assert FlexibleFractionDetector("en_US").detect("5/0") == []


@pytest.mark.parametrize("surface", ["/", "5", "1 2", "abc"])
def test_flexible_fraction_rejects_non_fractions(surface):
    assert FlexibleFractionDetector("en_US").detect(surface) == []


def test_flexible_fraction_captures_use_code_point_offsets_with_astral_prefix():
    text = "📌 ate 3 1/2 pies"
    detection = FlexibleFractionDetector("en_US").detect(text)[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert (detection["start"], detection["end"], detection["text"]) == (6, 11, "3 1/2")
    assert captures["whole"].value == "3"
    assert captures["numerator"].value == "1"
    assert captures["denominator"].value == "2"
    for capture in captures.values():
        assert text[capture.start : capture.end] == capture.text


def test_flexible_fraction_composes_with_detect_and_resolve():
    text = "add 1/2 cup then 3 1/4 more"
    detections = detect(text, [FlexibleFractionDetector("en_US")])
    resolution = resolve(detections)

    assert [detection["text"] for detection in detections] == ["1/2", "3 1/4"]
    assert [detection["text"] for detection in resolution.best] == ["1/2", "3 1/4"]
