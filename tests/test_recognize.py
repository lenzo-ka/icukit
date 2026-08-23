"""Tests for flexible, recall-oriented recognizers."""

import icu
import pytest

from icukit.detectors import (
    DateDetector,
    Detector,
    MeasureFormatSpec,
    MeasureValue,
    NumberDetector,
    NumberFormatSpec,
    NumberValue,
    detect,
)
from icukit.locale import COMPACT_LONG, COMPACT_SHORT, format_compact
from icukit.recognize import _SPACES as _RECOGNIZE_SPACES
from icukit.recognize import (
    FlexibleCompactDetector,
    FlexibleCurrencyDetector,
    FlexibleCurrencyNameDetector,
    FlexibleDateDetector,
    FlexibleFractionDetector,
    FlexibleMeasureDetector,
    FlexibleNumberDetector,
    FlexibleOrdinalDetector,
    FlexiblePercentDetector,
    FlexibleScientificDetector,
    FlexibleTextDateDetector,
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


@pytest.mark.parametrize(
    "locale",
    ["en_US", "ar_EG", "zh_Hans@numbers=hanidec"],
)
def test_flexible_number_uses_each_reflectively_formatted_locale_digit(locale):
    number_format = icu.NumberFormat.createInstance(icu.Locale(locale))
    digits = tuple(number_format.format(value) for value in range(10))
    detector = FlexibleNumberDetector(locale)

    assert detector._digits == {digit: str(value) for value, digit in enumerate(digits)}
    surface = "".join(digits[value] for value in (1, 2, 3))
    detection = detector.detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"] == NumberValue("123", None)


def test_hanidec_digits_are_not_assumed_to_be_contiguous_code_points():
    locale = icu.Locale("zh_Hans@numbers=hanidec")
    digits = tuple(icu.NumberFormat.createInstance(locale).format(value) for value in range(10))

    assert any(ord(digits[value]) != ord(digits[0]) + value for value in range(1, 10))
    assert FlexibleNumberDetector(locale.getName())._digits == {
        digit: str(value) for value, digit in enumerate(digits)
    }


@pytest.mark.parametrize("surface, decimal", [("1.234.567", "1234567"), ("1234,5", "1234.5")])
def test_locale_separators(surface, decimal):
    detection = FlexibleNumberDetector("de_DE").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"].decimal == decimal


@pytest.mark.parametrize("space", [" ", "\N{NO-BREAK SPACE}", "\N{NARROW NO-BREAK SPACE}"])
def test_space_grouping_separators_are_equivalent_when_licensed_by_locale(space):
    detection = FlexibleNumberDetector("fr_FR").detect(f"1{space}234,56")[0]

    assert detection["text"] == f"1{space}234,56"
    assert detection["value"].decimal == "1234.56"


def test_non_space_grouping_separator_remains_exact():
    detection = FlexibleNumberDetector("en_US").detect("1 234")[0]

    assert detection["text"] == "1"
    assert detection["value"].decimal == "1"


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


@pytest.mark.parametrize(
    "locale, surface, expected",
    [
        ("en_US", "1,2,3", "1"),
        ("en_US", "1,234", "1,234"),
        ("en_US", "1,234,567", "1,234,567"),
        ("hi_IN", "1,23,456", "1,23,456"),
    ],
)
def test_flexible_number_validates_locale_grouping(locale, surface, expected):
    detection = FlexibleNumberDetector(locale).detect(surface)[0]

    assert detection["text"] == expected


def test_flexible_percent_does_not_absorb_malformed_grouping():
    detections = FlexiblePercentDetector("en_US").detect("1,2,3%")

    assert all(detection["text"] != "1,2,3%" for detection in detections)
    assert all(detection["value"].decimal != "1.23" for detection in detections)


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


@pytest.mark.parametrize("surface", ["%5", "5%", "% 5", "5\N{NARROW NO-BREAK SPACE}%"])
def test_flexible_percent_accepts_both_reflective_symbol_orientations(surface):
    detection = FlexiblePercentDetector("tr_TR").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"] == NumberValue("0.05", None)


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


@pytest.mark.parametrize("surface, decimal", [("5 US dollars", "5"), ("1 US Dollar", "1")])
def test_flexible_currency_name_gains_recall_over_strict(surface, decimal):
    assert NumberDetector("en_US", "currency", "USD").detect(surface) == []

    detector = FlexibleCurrencyNameDetector("en_US", "USD")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert detection["text"] == surface
    assert detection["value"] == NumberValue(decimal, "USD")
    currency = next(capture for capture in detection["captures"] if capture.name == "currency")
    assert (currency.text, currency.value, currency.form) == (
        surface[len(decimal) + 1 :],
        "USD",
        "wide",
    )


def test_flexible_currency_name_is_case_insensitive_and_reflective_non_english():
    detection = FlexibleCurrencyNameDetector("de_DE", "EUR").detect("5 euro")[0]

    assert detection["text"] == "5 euro"
    assert detection["value"] == NumberValue("5", "EUR")


def test_flexible_currency_name_canonical_verifies_code():
    with pytest.raises(ValueError, match="canonical"):
        FlexibleCurrencyNameDetector("en_US", "usd")


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


def test_flexible_currency_accepts_narrow_no_break_space():
    surface = "5,00\N{NARROW NO-BREAK SPACE}€"
    detection = FlexibleCurrencyDetector("fr_FR", "EUR").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"] == NumberValue("5.00", "EUR")


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


@pytest.mark.parametrize(
    "locale, unit, surface, decimal, width",
    [
        ("en_US", "kilometer", "5 km", "5", "short"),
        ("en_US", "kilometer", "5km", "5", "narrow"),
        ("en_US", "kilogram", "3.2 kg", "3.2", "short"),
        ("en_US", "celsius", "20°C", "20", "short"),
        ("en_US", "mile-per-hour", "10 mph", "10", "short"),
        ("de_DE", "kilometer", "5 km", "5", "short"),
    ],
)
def test_flexible_measure_gains_recall(locale, unit, surface, decimal, width):
    assert all(
        detection["text"] != surface
        for detection in NumberDetector(locale, "decimal").detect(surface)
    )

    detector = FlexibleMeasureDetector(locale, unit)
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert detection["text"] == surface
    assert detection["type"] == f"measure:{unit}"
    assert detection["value"] == MeasureValue(decimal, unit)
    assert detection["spec"] == MeasureFormatSpec(locale, unit, width)
    assert detection["captures"][-1].name == "unit"
    assert detection["captures"][-1].value == unit
    assert detection["captures"][-1].form == "symbol"


@pytest.mark.parametrize("surface", ["5", "5 parsecs"])
def test_flexible_measure_requires_requested_unit(surface):
    assert FlexibleMeasureDetector("en_US", "kilometer").detect(surface) == []


@pytest.mark.parametrize(
    "unit, surface",
    [
        ("meter", "5mph"),
        ("meter", "5ms"),
        ("kilogram", "5kgfoo"),
        ("celsius", "20°Celsius"),
    ],
)
def test_flexible_measure_rejects_unit_prefix_of_word(unit, surface):
    assert FlexibleMeasureDetector("en_US", unit).detect(surface) == []


@pytest.mark.parametrize("text", ["5m, then", "5 m traveled"])
def test_flexible_measure_allows_boundary_after_unit(text):
    detection = FlexibleMeasureDetector("en_US", "meter").detect(text)[0]

    assert detection["text"] in {"5m", "5 m"}


def test_flexible_measure_skips_undecomposable_width():
    locale = icu.Locale("ar_EG")
    unit = icu.MeasureUnit.forIdentifier("meter")
    number_surface = icu.NumberFormat.createInstance(locale).format(1)
    short_surface = icu.MeasureFormat(locale, icu.UMeasureFormatWidth.SHORT).formatMeasure(
        icu.Measure(1, unit)
    )
    surface = icu.MeasureFormat(locale, icu.UMeasureFormatWidth.NARROW).formatMeasure(
        icu.Measure(1, unit)
    )
    assert number_surface not in short_surface

    detection = FlexibleMeasureDetector("ar_EG", "meter").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["spec"] == MeasureFormatSpec("ar_EG", "meter", "narrow")


def test_flexible_measure_refuses_icu_normalized_identifier():
    canonical = next(
        unit.getIdentifier()
        for unit_type in icu.MeasureUnit.getAvailableTypes()
        for unit in icu.MeasureUnit.getAvailable(unit_type)
        if "-per-square-" in unit.getIdentifier()
    )
    numerator, denominator = canonical.split("-per-square-", 1)
    noncanonical = f"{numerator}-per-{denominator}-per-{denominator}"
    assert icu.MeasureUnit.forIdentifier(noncanonical).getIdentifier() == canonical

    with pytest.raises(ValueError, match="not a canonical ICU identifier"):
        FlexibleMeasureDetector("en_US", noncanonical)


def test_flexible_measure_capture_offsets_with_astral_prefix():
    source = "📌 20°C"
    detection = FlexibleMeasureDetector("en_US", "celsius").detect(source)[0]
    unit = detection["captures"][-1]

    assert (unit.start, unit.end, unit.text) == (4, 6, "°C")
    assert all(
        source[capture.start : capture.end] == capture.text for capture in detection["captures"]
    )


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


@pytest.mark.parametrize(
    "surface, fields",
    [
        ("July 25th, 2012", (("y", 2012), ("M", 7), ("d", 25))),
        ("Wednesday, July 25, 2012", (("y", 2012), ("M", 7), ("d", 25))),
        ("January 15", (("M", 1), ("d", 15))),
    ],
)
def test_flexible_text_date_gains_recall_over_numeric(surface, fields):
    assert FlexibleDateDetector("en_US").detect(surface) == []

    detector = FlexibleTextDateDetector("en_US")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert detection["text"] == surface
    assert detection["value"].fields == fields
    assert detection["value"].calendar == "gregorian"
    month = next(capture for capture in detection["captures"] if capture.name == "month")
    assert (month.value, month.form) == (fields[-2][1], "wide")


def test_flexible_text_date_captures_short_names_and_is_case_insensitive():
    detection = FlexibleTextDateDetector("en_US").detect("wednesday, jul 25, 2012")[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert captures["weekday"].form == "wide"
    assert captures["month"].form == "short"
    assert captures["month"].value == 7
    assert captures["d"].form == captures["y"].form == "numeric"


def test_flexible_text_date_is_reflective_for_non_english_locale():
    detection = FlexibleTextDateDetector("de_DE").detect("15. Januar 2012")[0]

    assert detection["value"].fields == (("y", 2012), ("M", 1), ("d", 15))
    assert next(c for c in detection["captures"] if c.name == "month").form == "wide"


@pytest.mark.parametrize("surface", ["February 30, 2012", "April 31, 2012"])
def test_flexible_text_date_rejects_impossible_dates(surface):
    assert FlexibleTextDateDetector("en_US").detect(surface) == []


@pytest.mark.parametrize(
    "surface, fields",
    [
        ("July 25 2012", (("y", 2012), ("M", 7), ("d", 25))),
        ("july 25th 2012", (("y", 2012), ("M", 7), ("d", 25))),
        ("Jan 15 2020", (("y", 2020), ("M", 1), ("d", 15))),
    ],
)
def test_flexible_text_date_treats_separator_punctuation_as_optional(surface, fields):
    """A surface that drops the CLDR comma still deposits the full-span candidate."""
    detection = FlexibleTextDateDetector("en_US").detect(surface)[0]

    assert (detection["start"], detection["end"]) == (0, len(surface))
    assert detection["value"].fields == fields


@pytest.mark.parametrize("surface", ["hello july world", "march on washington 2020", "May I go"])
def test_flexible_text_date_requires_a_real_day_and_boundary(surface):
    """Relaxed separators do not turn a bare month name into a false date."""
    assert FlexibleTextDateDetector("en_US").detect(surface) == []


def test_flexible_currency_name_reads_a_non_home_currency_reflectively():
    """setCurrency drives the spelled name for a currency other than the locale's own."""
    detection = FlexibleCurrencyNameDetector("en_US", "EUR").detect("5 euros")[0]

    assert detection["text"] == "5 euros"
    assert detection["value"] == NumberValue("5", "EUR")
    assert FlexibleCurrencyNameDetector("en_US", "EUR").detect("5 EUR")[0]["value"] == NumberValue(
        "5", "EUR"
    )


def test_flexible_text_date_keeps_pattern_grammar_words_mandatory():
    """Relaxing punctuation must not drop a locale's required grammar word."""
    detector = FlexibleTextDateDetector("pt_BR")

    assert detector.detect("25 julho 2012") == []
    assert detector.detect("25 de julho de 2012")[0]["text"] == "25 de julho de 2012"


@pytest.mark.parametrize("surface", ["5USD", "5euros", "5US dollars"])
def test_flexible_currency_name_requires_a_boundary_before_the_name(surface):
    """A spelled name glued to the digits is a mid-token match and is refused."""
    assert FlexibleCurrencyNameDetector("en_US", "USD").detect(surface) == []
    assert FlexibleCurrencyNameDetector("fr_FR", "EUR").detect(surface) == []


def test_flexible_text_date_does_not_truncate_a_contradictory_weekday():
    """A wrong weekday yields no weekday-date candidate, not a truncated one."""
    detections = FlexibleTextDateDetector("en_US").detect("Tuesday July 25 2012")

    assert [detection["text"] for detection in detections] == ["July 25 2012"]
    assert all(
        capture.name != "weekday" for detection in detections for capture in detection["captures"]
    )


def test_flexible_currency_name_rejects_an_unassigned_code():
    """A three-letter string outside ICU's currency inventory is refused."""
    with pytest.raises(ValueError, match="not an assigned ISO currency"):
        FlexibleCurrencyNameDetector("en_US", "ZZZ")


def test_flexible_currency_name_accepts_an_assigned_code_without_a_display_name():
    """Inventory membership, not a localized name, decides a code is a currency."""
    # ARY is an assigned ISO 4217 code whose English long name falls back to the code.
    detector = FlexibleCurrencyNameDetector("en_US", "ARY")

    assert detector.currency == "ARY"


def test_flexible_date_accepts_four_digit_year():
    detection = FlexibleDateDetector("en_US").detect("1/3/2026")[0]

    assert detection["value"].fields == (("y", 2026), ("M", 1), ("d", 3))


@pytest.mark.parametrize("surface", ["2/30/2026", "4/31/26", "2/29/2025"])
def test_flexible_date_rejects_impossible_gregorian_dates(surface):
    assert FlexibleDateDetector("en_US").detect(surface) == []


def test_flexible_date_uses_locale_default_calendar():
    detection = FlexibleDateDetector("th_TH").detect("19/8/69")[0]

    assert detection["value"].fields == (("y", 69), ("M", 8), ("d", 19))
    assert detection["value"].calendar == "buddhist"
    assert detection["spec"].calendar == "buddhist"


def test_flexible_date_uses_locale_order_and_separator():
    detection = FlexibleDateDetector("de_DE").detect("3.1.2026")[0]

    assert detection["value"].fields == (("y", 2026), ("M", 1), ("d", 3))
    assert detection["spec"].pattern == "dd.MM.yy"


def test_flexible_date_or_time_is_inert_for_an_unsupported_locale_pattern(monkeypatch):
    """Real ICU data is preferred; this build's inventory may all be modelable."""
    detector = None
    for locale in icu.Locale.getAvailableLocales().values():
        locale_name = locale.getName()
        date_pattern = icu.DateFormat.createDateInstance(icu.DateFormat.kShort, locale).toPattern()
        if FlexibleDateDetector._date_structure(date_pattern) is None:
            detector = FlexibleDateDetector(locale_name)
            break
        time_pattern = icu.DateFormat.createTimeInstance(icu.DateFormat.kShort, locale).toPattern()
        if FlexibleTimeDetector._time_structure(time_pattern) is None:
            detector = FlexibleTimeDetector(locale_name)
            break

    if detector is None:
        # The installed ICU inventory contains only patterns these parsers model.
        # Drive the same real unsupported-parser result through the constructor.
        unsupported = FlexibleTimeDetector._time_structure("m")
        assert unsupported is None
        monkeypatch.setattr(
            FlexibleTimeDetector, "_time_structure", staticmethod(lambda pattern: unsupported)
        )
        detector = FlexibleTimeDetector("en_US")

    assert detector.detect("1/3/2026 3:45 PM") == []


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


@pytest.mark.parametrize(
    "surface, fields",
    [
        ("오후 9:30", (("H", 21), ("m", 30))),
        ("오전 9:30", (("H", 9), ("m", 30))),
        ("오후 12:00", (("H", 12), ("m", 0))),
        ("오전 12:00", (("H", 0), ("m", 0))),
        ("9:30", (("H", 9), ("m", 30))),
    ],
)
def test_flexible_time_reads_a_prefix_day_period(surface, fields):
    """A locale whose am/pm precedes the hour (ko_KR "a h:mm") reads it as a prefix."""
    detector = FlexibleTimeDetector("ko_KR")

    assert detector._period_prefix is True
    detection = detector.detect(surface)[0]
    assert (detection["start"], detection["end"]) == (0, len(surface))
    assert detection["value"].fields == fields


def test_flexible_time_prefix_day_period_capture_precedes_the_hour():
    """The prefix marker is captured, in source order, before the hour."""
    detection = FlexibleTimeDetector("ko_KR").detect("오후 9:30")[0]
    names = [capture.name for capture in detection["captures"]]

    assert names == ["day-period", "H", "m"]
    period = next(capture for capture in detection["captures"] if capture.name == "day-period")
    assert period.text == "오후"
    assert period.start == 0


@pytest.mark.parametrize("surface", ["오후 0:30", "오후 13:30", "오전 0:30"])
def test_flexible_time_rejects_a_prefix_marker_with_an_out_of_range_hour(surface):
    """A prefix marker blocks a bare fallback, as a suffix marker rejects "15:45 PM"."""
    assert FlexibleTimeDetector("ko_KR").detect(surface) == []


@pytest.mark.parametrize("surface", ["x오후 9:30", "가오후 9:30"])
def test_flexible_time_prefix_marker_does_not_start_mid_word(surface):
    """A day-period marker inside an alphanumeric token is not a match."""
    assert FlexibleTimeDetector("ko_KR").detect(surface) == []


def test_flexible_time_uses_locale_separator_and_24_hour_convention():
    detector = FlexibleTimeDetector("de_DE")

    assert detector.hour12 is False
    assert detector._separator == ":"
    detection = detector.detect("15:45")[0]
    assert detection["value"].fields == (("H", 15), ("m", 45))
    assert detection["spec"].pattern == "HH:mm"


@pytest.mark.parametrize(
    "locale, side",
    [("en_US", "suffix"), ("ko_KR", "prefix"), ("de_DE", None)],
)
def test_flexible_time_reports_pattern_day_period_side(locale, side):
    assert FlexibleTimeDetector(locale)._period_side == side


def test_flexible_time_does_not_read_a_day_period_absent_from_pattern():
    assert FlexibleTimeDetector("de_DE").detect("3:45 PM") == []


@pytest.mark.parametrize("surface", ["12:30:99", "12:30:4", "15:45 PM"])
def test_flexible_time_rejects_malformed_continuations(surface):
    assert FlexibleTimeDetector("en_US").detect(surface) == []


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


def test_flexible_fraction_rejects_chained_fraction():
    assert FlexibleFractionDetector("en_US").detect("1/2/3") == []


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


@pytest.mark.parametrize(
    "surface, decimal",
    [("1st", "1"), ("2nd", "2"), ("3rd", "3"), ("4th", "4"), ("21st", "21"), ("101st", "101")],
)
def test_flexible_ordinal_gains_recall(surface, decimal):
    detector = FlexibleOrdinalDetector("en_US")
    detection = detector.detect(surface)[0]

    assert isinstance(detector, Detector)
    assert (detection["start"], detection["end"]) == (0, len(surface))
    assert detection["value"] == NumberValue(decimal, None)
    assert detection["type"] == "ordinal:flexible"
    assert [capture.name for capture in detection["captures"]] == ["integer", "ordinal-affix"]


def test_flexible_ordinal_rejects_wrong_affix_reflectively():
    assert FlexibleOrdinalDetector("en_US").detect("21th") == []
    assert FlexibleOrdinalDetector("en_US").detect("2th") == []


@pytest.mark.parametrize("surface", ["1er", "1re"])
def test_flexible_ordinal_accepts_gender_variants_reflectively(surface):
    detection = FlexibleOrdinalDetector("fr_FR").detect(surface)[0]

    assert detection["value"] == NumberValue("1", None)


def test_flexible_ordinal_affixes_include_gender_variants_reflectively():
    affixes = FlexibleOrdinalDetector("fr_FR")._affixes(1)

    assert ("", "er") in affixes
    assert ("", "re") in affixes


@pytest.mark.parametrize("locale, surface", [("ja_JP", "第1"), ("zh_CN", "第21")])
def test_flexible_ordinal_accepts_reflective_prefix(locale, surface):
    detection = FlexibleOrdinalDetector(locale).detect(surface)[0]

    assert detection["text"] == surface
    assert [capture.name for capture in detection["captures"]] == [
        "ordinal-affix",
        "integer",
    ]


@pytest.mark.parametrize("surface", ["1", "st", "abc"])
def test_flexible_ordinal_rejects_bare_number_or_affix(surface):
    assert FlexibleOrdinalDetector("en_US").detect(surface) == []


def test_flexible_ordinal_captures_use_code_point_offsets_with_astral_prefix():
    text = "📌 the 21st day"
    detection = FlexibleOrdinalDetector("en_US").detect(text)[0]
    captures = {capture.name: capture for capture in detection["captures"]}

    assert (detection["start"], detection["end"], detection["text"]) == (6, 10, "21st")
    assert captures["integer"].value == "21"
    assert captures["ordinal-affix"].form == "symbol"
    for capture in captures.values():
        assert text[capture.start : capture.end] == capture.text


def test_flexible_ordinal_composes_with_detect_and_resolve():
    text = "finished 1st and 22nd overall"
    detections = detect(text, [FlexibleOrdinalDetector("en_US")])
    resolution = resolve(detections)

    assert [detection["text"] for detection in detections] == ["1st", "22nd"]
    assert [detection["text"] for detection in resolution.best] == ["1st", "22nd"]


@pytest.mark.parametrize(
    "surface,width,decimal,style",
    [
        ("1.2M", "short", "1200000", COMPACT_SHORT),
        ("3K", "short", "3000", COMPACT_SHORT),
        ("1.2 million", "long", "1200000", COMPACT_LONG),
    ],
)
def test_flexible_compact_gains_recall(surface, width, decimal, style):
    plain = [
        *NumberDetector("en_US", "decimal").detect(surface),
        *FlexibleNumberDetector("en_US").detect(surface),
    ]
    assert not any(
        detection["text"] == surface and detection["value"].decimal == decimal
        for detection in plain
    )

    detector = FlexibleCompactDetector("en_US", width)
    detections = detector.detect(surface)

    assert isinstance(detector, Detector)
    assert len(detections) == 1
    assert detections[0]["text"] == surface
    assert detections[0]["value"] == NumberValue(decimal, None)
    assert format_compact(int(decimal), "en_US", style) == surface


def test_flexible_compact_long_is_reflective_in_a_non_english_locale():
    locale = "de_DE"
    value = 1_200_000
    formatter = icu.CompactDecimalFormat.createInstance(
        icu.Locale(locale), icu.UNumberCompactStyle.LONG
    )
    surface = formatter.format(value)
    digits = set(
        icu.NumberFormat.createInstance(icu.Locale(locale)).format(number) for number in range(10)
    )
    word = "".join(character for character in surface if character not in digits).strip()

    assert word
    detection = FlexibleCompactDetector(locale, "long").detect(surface)[0]
    assert detection["text"] == surface
    assert detection["value"] == NumberValue(str(value), None)


@pytest.mark.parametrize("surface", ["1.2Million", "3Km"])
def test_flexible_compact_rejects_a_suffix_inside_a_word(surface):
    detections = FlexibleCompactDetector("en_US", "short").detect(surface)

    assert not any(detection["value"].decimal in {"1200000", "3000"} for detection in detections)


def test_flexible_compact_derivation_and_detection_are_deterministic():
    first = FlexibleCompactDetector("en_US", "short")
    second = FlexibleCompactDetector("en_US", "short")

    assert first._affixes == second._affixes
    assert first.detect("1.2M then 3K") == first.detect("1.2M then 3K")


def test_flexible_compact_holds_the_bare_number_candidate_separately():
    compact = FlexibleCompactDetector("en_US", "short").detect("1.2M")
    decimal = FlexibleNumberDetector("en_US").detect("1.2M")

    assert compact[0]["value"] == NumberValue("1200000", None)
    assert decimal[0]["text"] == "1.2"
    assert decimal[0]["value"] == NumberValue("1.2", None)


@pytest.mark.parametrize(
    "surface,decimal",
    [
        ("1.2345E4", "12345"),
        ("1E-3", "0.001"),
        ("6.022E23", "602200000000000000000000"),
        ("-1.2345E4", "-12345"),
    ],
)
def test_flexible_scientific_gains_recall(surface, decimal):
    detection = FlexibleScientificDetector("en_US").detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"] == NumberValue(decimal, None)


def test_flexible_scientific_round_trips_and_holds_the_mantissa_separately():
    surface = "1.2345E4"
    scientific = FlexibleScientificDetector("en_US").detect(surface)[0]
    decimal = FlexibleNumberDetector("en_US").detect(surface)[0]

    assert scientific["value"] == NumberValue("12345", None)
    assert decimal["text"] == "1.2345"
    assert decimal["value"] == NumberValue("1.2345", None)
    assert icu.NumberFormat.createScientificInstance(icu.Locale("en_US")).format(12345.0) == surface


def test_flexible_scientific_preserves_a_long_mantissa_exactly():
    detection = FlexibleScientificDetector("en_US").detect("1.2345678901234567890123456789E1")[0]

    assert detection["value"] == NumberValue("12.345678901234567890123456789", None)


def test_flexible_scientific_accepts_a_large_reasonable_exponent():
    detection = FlexibleScientificDetector("en_US").detect("1E100")[0]

    assert detection["value"] == NumberValue("1" + "0" * 100, None)


@pytest.mark.parametrize("surface", ["1E1000000", "1E100000000000"])
def test_flexible_scientific_silently_rejects_an_oversized_expansion(surface):
    assert FlexibleScientificDetector("en_US").detect(surface) == []


@pytest.mark.parametrize("width", [4000, 4301])
def test_flexible_scientific_silently_rejects_an_unrepresentable_exponent(width):
    assert FlexibleScientificDetector("en_US").detect("1E" + "9" * width) == []


def test_flexible_scientific_reflects_a_non_english_exponent_symbol():
    locale = "sv_SE"
    surface = icu.NumberFormat.createScientificInstance(icu.Locale(locale)).format(12345.0)

    detection = FlexibleScientificDetector(locale).detect(surface)[0]

    assert detection["text"] == surface
    assert detection["value"] == NumberValue("12345", None)


@pytest.mark.parametrize("surface", ["x1E4y", "0xE", "1E", "1E4.5", "1E4,000"])
def test_flexible_scientific_requires_complete_token_boundaries(surface):
    assert FlexibleScientificDetector("en_US").detect(surface) == []


def test_flexible_scientific_is_deterministic():
    first = FlexibleScientificDetector("en_US")
    second = FlexibleScientificDetector("en_US")

    assert first.detect("1.2345E4 then 1E-3") == second.detect("1.2345E4 then 1E-3")


def test_flexible_compact_requires_a_left_token_boundary():
    # A suffix affix must not begin inside a preceding word or in a larger number's tail.
    en = FlexibleCompactDetector("en_US", "short")
    assert en.detect("x1.2M") == []
    assert en.detect("a3K") == []

    # A prefix affix ("B" in Swahili "B12") must not begin inside a word either.
    sw = FlexibleCompactDetector("sw_KE", "short")
    assert sw.detect("AB12") == []
    assert sw.detect("xM1.2") == []


def test_flexible_compact_recovers_a_signed_prefix_affix():
    # Confirm the prefix form and its sign placement reflectively from ICU, then invert.
    formatter = icu.CompactDecimalFormat.createInstance(
        icu.Locale("sw_KE"), icu.UNumberCompactStyle.SHORT
    )
    positive_surface = formatter.format(1_200_000)
    negative_surface = formatter.format(-1_200_000)
    if positive_surface[0].isdigit():
        pytest.skip("locale no longer uses a prefix compact affix")

    sw = FlexibleCompactDetector("sw_KE", "short")

    positive = sw.detect(positive_surface)[0]
    assert positive["text"] == positive_surface
    assert positive["value"] == NumberValue("1200000", None)

    negative = sw.detect(negative_surface)[0]
    assert negative["text"] == negative_surface
    assert negative["value"] == NumberValue("-1200000", None)


def test_flexible_compact_boundary_respects_space_grouping():
    # In a space-grouping locale the parser treats any space as a group separator, so a
    # match must not begin at an interior digit group ("2 M" out of "1 2 M"), while a
    # number after a word (a real boundary) still matches.
    detector = FlexibleCompactDetector("fr_FR", "short")
    grouping = detector._number._grouping
    if grouping not in _RECOGNIZE_SPACES:
        pytest.skip("fr_FR no longer uses a space grouping separator")
    million = icu.CompactDecimalFormat.createInstance(
        icu.Locale("fr_FR"), icu.UNumberCompactStyle.SHORT
    ).format(1_200_000)

    for space in _RECOGNIZE_SPACES:
        interior = f"1{space}2{space}M"
        assert all(d["value"].decimal != "2000000" for d in detector.detect(interior))
    assert detector.detect(f"budget {million}")[0]["value"] == NumberValue("1200000", None)


@pytest.mark.parametrize("surface", ["-M+1.2", "+M-1.2", "+M+1.2", "-M-1.2", "M-1.2", "M+1.2"])
def test_flexible_compact_rejects_contradictory_double_signs(surface):
    detector = FlexibleCompactDetector("sw_KE", "short")
    if detector.detect("M1.2")[0]["text"] != "M1.2":
        pytest.skip("locale no longer uses a prefix compact affix")

    assert detector.detect(surface) == []
