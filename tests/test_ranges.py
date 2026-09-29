"""Ranges are read as ICU writes them, and a hyphen-minus only where ICU writes one.

Every surface a default reader is held to here is ICU's own: a range formatted by
``NumberRangeFormatter`` or a year interval by ``DateIntervalFormat``, in the ICU the
suite runs on.
"""

from dataclasses import replace
from decimal import Decimal

import icu
import pytest

from icukit import (
    ApproximateValue,
    DateIntervalValue,
    DateTimeValue,
    DetectorSet,
    MeasureValue,
    NumberRangeValue,
    NumberValue,
    detection_to_dict,
    flexible_detectors,
    generated_detectors,
    number_detectors,
    range_detectors,
)
from icukit.engine import DEFAULT_FAMILIES, GUARDED_FAMILIES, _date_interval_skeletons
from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleDateIntervalDetector,
    FlexibleMeasureDetector,
    FlexibleNumberDetector,
    FlexibleNumberRangeDetector,
    FlexiblePercentDetector,
)

LOCALES = ("en_US", "de_DE", "fr_FR", "ja_JP", "es_ES", "zh_CN", "ru_RU", "hi_IN", "ar_EG")
COLLAPSES = ("AUTO", "UNIT", "ALL", "NONE")


def _range(locale: str, low: int, high: int, unit=None, collapse: str = "AUTO") -> str:
    formatter = icu.NumberRangeFormatter.withLocale(icu.Locale(locale))
    if unit is not None:
        formatter = formatter.numberFormatterBoth(icu.NumberFormatter.with_().unit(unit))
    formatter = formatter.collapse(getattr(icu.UNumberRangeCollapse, collapse))
    return formatter.formatIntRange(low, high)


def _range_with_endpoint_spans(locale: str, low: int, high: int):
    formatted = icu.NumberRangeFormatter.withLocale(icu.Locale(locale)).formatIntRangeToValue(
        low, high
    )
    positions = {}
    position = icu.ConstrainedFieldPosition()
    position.constrainCategory(icu.UFieldCategory.NUMBER_RANGE_SPAN)
    while formatted.nextPosition(position):
        positions[position.getField()] = (position.getStart(), position.getLimit())
    return str(formatted), positions


def _whole(detector, text: str):
    return [
        found for found in detector.detect(text) if (found["start"], found["end"]) == (0, len(text))
    ]


def _fixed_range(locale: str, low: float, high: float, unit=None, collapse: str = "AUTO") -> str:
    number = icu.NumberFormatter.with_().precision(icu.Precision.fixedFraction(2))
    if unit is not None:
        number = number.unit(unit)
    formatter = (
        icu.NumberRangeFormatter.withLocale(icu.Locale(locale))
        .numberFormatterBoth(number)
        .collapse(getattr(icu.UNumberRangeCollapse, collapse))
    )
    return str(formatter.formatDoubleRange(low, high))


def _assert_capture_offsets(text, detection):
    assert all(
        text[capture.start : capture.end] == capture.text for capture in detection["captures"]
    )
    # An endpoint's own capture lies within that endpoint.
    owners = {capture.name: capture for capture in detection["captures"] if "." not in capture.name}
    for capture in detection["captures"]:
        if "." in capture.name:
            owner = owners[capture.name.split(".", 1)[0]]
            assert owner.start <= capture.start <= capture.end <= owner.end


def _amounts(value) -> tuple[Decimal, Decimal]:
    return Decimal(value.start.decimal), Decimal(value.end.decimal)


def _assert_decimal_matches_double(actual: Decimal, expected: float) -> None:
    expected_decimal = Decimal(str(expected))
    assert actual == expected_decimal
    if expected_decimal.is_zero():
        assert actual.is_signed() == expected_decimal.is_signed()


def _numbers(locale: str) -> list:
    return [FlexibleNumberDetector(locale), FlexiblePercentDetector(locale)]


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize(("low", "high"), [(3, 5), (1000, 2000), (-3, -1)])
def test_a_plain_range_reads_as_icu_writes_it(locale, low, high):
    text = _range(locale, low, high)
    (found,) = _whole(FlexibleNumberRangeDetector(locale), text)

    assert found["type"] == "number:range"
    assert found["value"] == NumberRangeValue(NumberValue(str(low)), NumberValue(str(high)))
    names = [capture.name for capture in found["captures"]]
    assert names[0] == "start"
    assert names.index("separator") > 0
    assert names[names.index("separator") + 1] == "end"
    assert all(
        name == "start" or name.startswith("start.") for name in names[: names.index("separator")]
    )
    assert all(
        name == "end" or name.startswith("end.") for name in names[names.index("separator") + 1 :]
    )
    assert "start.integer" in names and "end.integer" in names
    _assert_capture_offsets(text, found)


@pytest.mark.parametrize(
    ("text", "reader", "names"),
    [
        (
            "79.20%–80.00%",
            FlexibleNumberRangeDetector("en_US"),
            [
                "start",
                "start.integer",
                "start.decimal-separator",
                "start.fraction",
                "start.percent",
                "separator",
                "end",
                "end.integer",
                "end.decimal-separator",
                "end.fraction",
                "end.percent",
            ],
        ),
        (
            _fixed_range("en_US", 1, 2),
            FlexibleNumberRangeDetector("en_US"),
            [
                "start",
                "start.integer",
                "start.decimal-separator",
                "start.fraction",
                "separator",
                "end",
                "end.integer",
                "end.decimal-separator",
                "end.fraction",
            ],
        ),
    ],
)
def test_a_range_carries_each_endpoints_own_captures(text, reader, names):
    # The no-space, repeated-percent spelling is accepted by the flexible reader; this
    # ICU writes its equivalent with spaces, so that named regression surface is the one
    # unavoidable hand-written range here. The decimal case is ICU-formatted.
    (found,) = _whole(reader, text)

    assert [capture.name for capture in found["captures"]] == names
    _assert_capture_offsets(text, found)


def test_an_approximately_reading_carries_its_values_own_captures():
    formatter = (
        icu.NumberRangeFormatter.withLocale(icu.Locale("en_US"))
        .numberFormatterBoth(icu.NumberFormatter.with_().precision(icu.Precision.fixedFraction(2)))
        .identityFallback(icu.UNumberRangeIdentityFallback.APPROXIMATELY)
    )
    text = str(formatter.formatDoubleRange(3.5, 3.5))
    (found,) = _whole(FlexibleNumberRangeDetector("en_US", form="approximately"), text)

    assert [capture.name for capture in found["captures"]] == [
        "approximately",
        "value",
        "value.integer",
        "value.decimal-separator",
        "value.fraction",
    ]
    _assert_capture_offsets(text, found)


def test_currency_and_measure_ranges_keep_only_each_written_sides_captures():
    currency_text = _fixed_range("en_US", 3, 5, icu.CurrencyUnit("USD"), "NONE")
    currency_reader = FlexibleNumberRangeDetector(
        "en_US", [*_numbers("en_US"), FlexibleCurrencyDetector("en_US", "USD")]
    )
    measure_text = _fixed_range("en_US", 10, 15, icu.MeasureUnit.forIdentifier("kilogram"), "UNIT")
    measure_reader = FlexibleNumberRangeDetector(
        "en_US", [FlexibleMeasureDetector("en_US", "kilogram")]
    )

    (currency,) = _whole(currency_reader, currency_text)
    (measure,) = _whole(measure_reader, measure_text)
    assert [capture.name for capture in currency["captures"]] == [
        "start",
        "start.currency",
        "start.integer",
        "start.decimal-separator",
        "start.fraction",
        "separator",
        "end",
        "end.currency",
        "end.integer",
        "end.decimal-separator",
        "end.fraction",
    ]
    measure_names = [capture.name for capture in measure["captures"]]
    assert measure_names == [
        "start",
        "start.integer",
        "start.decimal-separator",
        "start.fraction",
        "separator",
        "end",
        "end.integer",
        "end.decimal-separator",
        "end.fraction",
        "end.unit",
    ]
    assert "start.unit" not in measure_names
    _assert_capture_offsets(currency_text, currency)
    _assert_capture_offsets(measure_text, measure)


def test_an_extended_unicode_minus_is_a_start_sign_capture():
    # ICU en_US writes a hyphen-minus for negatives, while this existing flexible path
    # specifically accepts U+2212 before a range, so its regression spelling is manual.
    text = "\N{MINUS SIGN}3–5"
    (found,) = _whole(FlexibleNumberRangeDetector("en_US"), text)

    assert [capture.name for capture in found["captures"]] == [
        "start",
        "start.sign",
        "start.integer",
        "separator",
        "end",
        "end.integer",
    ]
    assert found["captures"][1].form == "symbol"
    _assert_capture_offsets(text, found)


@pytest.mark.parametrize("locale", ["en_US", "ar_EG", "fa_IR"])
@pytest.mark.parametrize(("low", "high"), [(3.25, 5.5), (-3, 5), (-3, -1)])
def test_each_endpoint_capture_is_the_endpoint_readers_own(locale, low, high):
    text = str(icu.NumberRangeFormatter.withLocale(icu.Locale(locale)).formatDoubleRange(low, high))
    (found,) = _whole(FlexibleNumberRangeDetector(locale), text)

    captures = {capture.name: capture for capture in found["captures"]}
    assert ("start.sign" in captures) == (low < 0)
    for side in ("start", "end"):
        whole = captures[side]
        (alone,) = [
            detection
            for detection in FlexibleNumberDetector(locale).detect(whole.text)
            if (detection["start"], detection["end"]) == (0, len(whole.text))
        ]
        own = [
            replace(
                capture,
                name=f"{side}.{capture.name}",
                start=whole.start + capture.start,
                end=whole.start + capture.end,
            )
            for capture in alone["captures"]
        ]
        prefixed = [c for c in found["captures"] if c.name.startswith(f"{side}.")]
        assert prefixed == own


def test_a_unit_written_first_once_is_captured_only_on_the_start():
    text = _fixed_range("en_US", 3, 5, icu.CurrencyUnit("USD"), "UNIT")
    reader = FlexibleNumberRangeDetector(
        "en_US", [*_numbers("en_US"), FlexibleCurrencyDetector("en_US", "USD")]
    )
    (found,) = _whole(reader, text)

    captures = {capture.name: capture for capture in found["captures"]}
    assert found["spec"].collapse == "unit"
    assert "end.currency" not in captures
    assert captures["start.currency"].start == 0
    assert captures["start.integer"].start == captures["start.currency"].end
    assert captures["end.integer"].start == captures["end"].start
    _assert_capture_offsets(text, found)


def test_an_adlam_range_after_an_astral_prefix_has_code_point_capture_offsets():
    locale = "ff_Adlm_GN"
    surface = _fixed_range(locale, 1, 2)
    text = "𞤀 " + surface
    (found,) = FlexibleNumberRangeDetector(locale).detect(text)

    assert (found["start"], found["end"]) == (2, len(text))
    assert [capture.name for capture in found["captures"]] == [
        "start",
        "start.integer",
        "start.decimal-separator",
        "start.fraction",
        "separator",
        "end",
        "end.integer",
        "end.decimal-separator",
        "end.fraction",
    ]
    _assert_capture_offsets(text, found)


def test_icus_shared_and_independent_negative_sign_shapes_keep_their_values():
    locale = "ar_EG"
    shared = _range(locale, -3, -1)
    independent = _range(locale, -3, 1)
    if shared == independent:
        pytest.skip("this ICU does not distinguish shared and independent sign scope")
    reader = FlexibleNumberRangeDetector(locale)

    assert _whole(reader, shared)[0]["value"] == NumberRangeValue(
        NumberValue("-3"), NumberValue("-1")
    )
    assert _whole(reader, independent)[0]["value"] == NumberRangeValue(
        NumberValue("-3"), NumberValue("1")
    )


@pytest.mark.parametrize("locale", ("ar_EG", "en_US"))
@pytest.mark.parametrize(("start", "end"), [(-0.0, -1.0), (-0.5, -1.0)])
def test_a_negative_range_starting_below_or_at_zero_keeps_icus_endpoint_signs(locale, start, end):
    text = icu.NumberRangeFormatter.withLocale(icu.Locale(locale)).formatDoubleRange(start, end)
    (found,) = _whole(FlexibleNumberRangeDetector(locale), text)
    actual_start, actual_end = _amounts(found["value"])

    _assert_decimal_matches_double(actual_start, start)
    _assert_decimal_matches_double(actual_end, end)


@pytest.mark.parametrize("locale", ("ar_EG", "en_US"))
@pytest.mark.parametrize(("start", "end"), [(-1.0, -0.0), (-3.0, 0.0)])
def test_a_range_ending_at_zero_keeps_icus_endpoint_signs(locale, start, end):
    text = icu.NumberRangeFormatter.withLocale(icu.Locale(locale)).formatDoubleRange(start, end)
    (found,) = _whole(FlexibleNumberRangeDetector(locale), text)
    actual_start, actual_end = _amounts(found["value"])

    _assert_decimal_matches_double(actual_start, start)
    _assert_decimal_matches_double(actual_end, end)


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("collapse", COLLAPSES)
def test_a_currency_range_reads_whole_however_icu_collapses_it(locale, collapse):
    text = _range(locale, 3, 5, icu.CurrencyUnit("USD"), collapse)
    currency = FlexibleCurrencyDetector(locale, "USD")
    single = icu.NumberFormatter.withLocale(icu.Locale(locale)).unit(icu.CurrencyUnit("USD"))
    amount = single.formatDouble(5.0)
    if not _whole(currency, amount):
        # A range is read as its sides are; the currency reader does not read ICU's own
        # amount whole here.
        pytest.skip(f"the currency reader does not read {amount!r} whole")
    reader = FlexibleNumberRangeDetector(locale, [*_numbers(locale), currency])
    values = [found["value"] for found in _whole(reader, text)]

    assert any(
        _amounts(value) == (3, 5) and value.start.currency == value.end.currency == "USD"
        for value in values
    ), (text, values)


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("collapse", COLLAPSES)
def test_a_measure_range_reads_whole_however_icu_collapses_it(locale, collapse):
    text = _range(locale, 10, 15, icu.MeasureUnit.forIdentifier("kilogram"), collapse)
    reader = FlexibleNumberRangeDetector(locale, [FlexibleMeasureDetector(locale, "kilogram")])
    (found,) = _whole(reader, text)

    assert found["type"] == "measure:range"
    assert found["value"] == NumberRangeValue(
        MeasureValue("10", "kilogram"), MeasureValue("15", "kilogram")
    )


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("collapse", COLLAPSES)
def test_a_percent_range_reads_as_ratios(locale, collapse):
    text = _range(locale, 10, 15, icu.MeasureUnit.forIdentifier("percent"), collapse)
    values = [found["value"] for found in _whole(FlexibleNumberRangeDetector(locale), text)]

    assert NumberRangeValue(NumberValue("0.1"), NumberValue("0.15")) in values, (text, values)


def test_a_collapsed_unit_stays_on_the_side_icu_writes_it():
    reader = FlexibleNumberRangeDetector(
        "en_US", [*_numbers("en_US"), FlexibleCurrencyDetector("en_US", "USD")]
    )
    measures = FlexibleNumberRangeDetector("en_US", [FlexibleMeasureDetector("en_US", "kilogram")])

    assert _whole(reader, "$3–5")[0]["value"] == NumberRangeValue(
        NumberValue("3", "USD"), NumberValue("5", "USD")
    )
    # A prefix symbol is not left to the second side, nor a suffix unit to the first.
    assert _whole(reader, "3–$5") == []
    assert _whole(measures, "10 kg–15") == []


@pytest.mark.parametrize("locale", LOCALES)
def test_the_approximately_form_reads_where_icu_writes_one(locale):
    text = (
        icu.NumberRangeFormatter.withLocale(icu.Locale(locale))
        .identityFallback(icu.UNumberRangeIdentityFallback.APPROXIMATELY)
        .formatIntRange(3, 3)
    )
    reader = FlexibleNumberRangeDetector(locale, form="approximately")
    if not reader.has_marks:
        pytest.skip(f"ICU writes {locale} no approximately sign apart from its minus sign")
    (found,) = _whole(reader, text)

    assert found["type"] == "number:approximately"
    assert found["value"] == ApproximateValue(NumberValue("3"))


def test_a_range_serializes_with_its_endpoints():
    (found,) = _whole(FlexibleNumberRangeDetector("en_US"), "3–5")
    value = detection_to_dict(found)["value"]

    assert value["kind"] == "number_range"
    assert (value["start"]["decimal"], value["end"]["decimal"]) == ("3", "5")


def test_the_default_set_reads_icus_ranges_and_keeps_the_endpoints():
    gang = flexible_detectors("en_US")
    names = set(gang.names())

    assert {"number:range", "measure:range", "number:approximately"} <= names
    found = {(d["type"], d["text"]) for d in gang.detect("10–15 kg")}
    # Each endpoint's own reading is kept beside the range.
    assert {("measure:range", "10–15 kg"), ("number:decimal", "10")} <= found
    assert ("measure:kilogram", "15 kg") in found


# ------------------------------------------------------------------------ year intervals


@pytest.mark.parametrize("locale", LOCALES)
def test_a_year_interval_reads_as_icu_writes_it(locale):
    icu_locale = icu.Locale(locale)
    calendar = icu.Calendar.createInstance(icu_locale)
    calendar.clear()
    calendar.set(icu.UCalendarDateFields.YEAR, 1624)
    start = calendar.getTime()
    calendar.set(icu.UCalendarDateFields.YEAR, 1713)
    text = icu.DateIntervalFormat.createInstance("y", icu_locale).format(
        icu.DateInterval(start, calendar.getTime())
    )

    assert "y" in _date_interval_skeletons(locale)
    (found,) = _whole(FlexibleDateIntervalDetector(locale, "y"), text)
    assert found["type"] == "date-interval:y"
    kind = calendar.getType()
    assert found["value"] == DateIntervalValue(
        DateTimeValue((("y", 1624),), kind), DateTimeValue((("y", 1713),), kind)
    )


def test_the_default_set_reads_ranges_in_icus_own_form():
    gang = generated_detectors("en_US")
    names = set(gang.names())

    assert {"number:range", "number:approximately", "date-interval:y"} <= names
    # The generated set reads no currency or measure, so no range of one.
    assert "measure:range" not in names
    found = {(d["type"], d["text"]) for d in gang.detect("in 1914–1918, 3–5 kg, $3–5, ~3")}
    assert {
        ("date-interval:y", "1914–1918"),
        ("number:range", "1914–1918"),
        ("number:range", "3–5"),
        ("number:approximately", "~3"),
    } <= found
    assert not {text for _, text in found} & {"3–5 kg", "$3–5"}
    # A year under four digits is the guarded short-year reading, not a default one.
    assert not any(t.startswith("date-interval") for t, text in found if text == "3–5")


def test_a_ranges_endpoints_follow_the_reader_set():
    gang = generated_detectors("en_US").with_(
        *number_detectors("en_US", currencies=["USD"]).detectors,
        FlexibleMeasureDetector("en_US", "kilogram"),
    )
    gang = gang.with_(*range_detectors("en_US", gang).detectors)
    found = {(d["type"], d["text"]) for d in gang.detect("3–5 kg, $3.00 – $5.00, 3–5")}

    assert {
        ("measure:range", "3–5 kg"),
        ("number:range", "$3.00 – $5.00"),
        ("number:range", "3–5"),
    } <= found
    assert [d.type for d in gang.detectors].count("number:range") == 1


def test_a_currency_only_sets_ranges_do_not_invent_plain_number_endpoints():
    currency = FlexibleCurrencyDetector("en_US", "USD")
    currency_only = DetectorSet([currency])
    currency_only = currency_only.with_(*range_detectors("en_US", currency_only).detectors)
    plain = _range("en_US", 3, 5)
    approximate = (
        icu.NumberRangeFormatter.withLocale(icu.Locale("en_US"))
        .identityFallback(icu.UNumberRangeIdentityFallback.APPROXIMATELY)
        .formatIntRange(3, 3)
    )
    currency_text = _range("en_US", 3, 5, icu.CurrencyUnit("USD"), "ALL")

    assert _whole(currency_only, plain) == []
    assert _whole(currency_only, approximate) == []
    assert any(
        found["value"].start.currency == found["value"].end.currency == "USD"
        for found in _whole(currency_only, currency_text)
    )

    numbers = DetectorSet([FlexibleNumberDetector("en_US")])
    numbers = numbers.with_(*range_detectors("en_US", numbers).detectors)
    assert _whole(numbers, plain)
    assert _whole(numbers, approximate)


def test_a_range_reader_builds_its_endpoints_on_its_first_read():
    built = []

    def endpoints():
        built.append(True)
        return [FlexibleMeasureDetector("en_US", "kilogram")]

    reader = FlexibleNumberRangeDetector("en_US", endpoints, group="measure")
    assert reader.type == "measure:range" and not built
    assert reader.detect("no range here") == [] and not built
    assert [d["text"] for d in reader.detect("3–5 kg")] == ["3–5 kg"] and built == [True]


def test_a_run_of_numbers_is_rejected_before_any_side_is_read():
    reader = FlexibleNumberRangeDetector("en_US")
    reader._read_sides = None  # a side read would fail

    assert reader.detect("1–2–3–4–5–6–7–8–9 " * 100) == []


@pytest.mark.parametrize("locale", LOCALES)
def test_a_spaced_chain_using_icus_separator_is_not_a_range(locale):
    text, positions = _range_with_endpoint_spans(locale, -3, -1)
    if set(positions) != {0, 1}:
        pytest.skip("ICU reports no two endpoint spans for the formatted range")
    separator = text[positions[0][1] : positions[1][0]]
    if not any(character.isspace() for character in separator):
        pytest.skip(f"ICU writes {locale} no spaced range separator")
    number = icu.NumberFormatter.withLocale(icu.Locale(locale))
    chain = separator.join(str(number.formatInt(value)) for value in (1, 2, 3))
    negative_chain = separator.join(str(number.formatInt(value)) for value in (-5, -3, -1))
    reader = FlexibleNumberRangeDetector(locale)

    assert _whole(reader, text)
    assert reader.detect(chain) == []
    assert reader.detect(negative_chain) == []


def test_a_spaced_chain_with_negative_endpoints_is_not_two_ranges():
    assert FlexibleNumberRangeDetector("en_US").detect("-5 – -3 – -1") == []


def test_a_spaced_chain_with_a_negative_middle_endpoint_is_not_two_ranges():
    assert FlexibleNumberRangeDetector("en_US").detect("1 – -2 – 3") == []


def test_an_unspaced_chain_with_negative_endpoints_is_not_a_range():
    assert FlexibleNumberRangeDetector("en_US").detect("-3–-1–-5") == []


def test_a_spaced_prose_join_does_not_hide_an_unspaced_icu_range():
    range_text, positions = _range_with_endpoint_spans("en_US", 3, 5)
    if set(positions) != {0, 1}:
        pytest.skip("ICU reports no two endpoint spans for the formatted range")
    separator = range_text[positions[0][1] : positions[1][0]]
    if any(character.isspace() for character in separator):
        pytest.skip("ICU writes en_US no unspaced range separator")
    prose_separator = " - "
    if prose_separator == separator:
        pytest.skip("the prose separator is not distinct from ICU's range separator")
    prefix = str(icu.NumberFormatter.withLocale(icu.Locale("en_US")).formatInt(7))
    text = f"{prefix}{prose_separator}{range_text}"

    assert [found["text"] for found in FlexibleNumberRangeDetector("en_US").detect(text)] == [
        range_text
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("page 7 – 3–5", "3–5"), ("in 2019 - 10–15 kg", "10–15"), ("1–2 – 3", "1–2")],
)
def test_a_spaced_prose_join_does_not_hide_named_en_us_ranges(text, expected):
    assert [found["text"] for found in FlexibleNumberRangeDetector("en_US").detect(text)] == [
        expected
    ]


def test_a_year_range_rises_and_is_not_one_pair_of_a_run():
    reader = FlexibleDateIntervalDetector("en_US", "y")

    assert [d["text"] for d in reader.detect("1914–1918–1945; 1918–1914; 1939–1945")] == [
        "1939–1945"
    ]


def test_a_unicode_minus_sign_before_a_range_keeps_its_sign():
    (found,) = _whole(FlexibleNumberRangeDetector("en_US"), "\N{MINUS SIGN}3–5")

    assert found["value"] == NumberRangeValue(NumberValue("-3"), NumberValue("5"))


def test_a_short_year_interval_is_a_guarded_reading():
    guarded = generated_detectors("en_US", (*DEFAULT_FAMILIES, *GUARDED_FAMILIES))
    found = {(d["type"], d["text"]) for d in guarded.detect("in 44–45")}

    assert ("date-interval:short-year:y", "44–45") in found
    assert ("date-interval:y", "44–45") not in found
    short = FlexibleDateIntervalDetector("en_US", "y", short_years=True)
    assert [d["value"] for d in _whole(short, "44–45")] == [
        DateIntervalValue(
            DateTimeValue((("y", 44),), "gregorian"), DateTimeValue((("y", 45),), "gregorian")
        )
    ]
    assert _whole(short, "1914–1918") == []


def test_a_lone_numeric_field_other_than_the_year_has_no_interval_reader():
    skeletons = set(_date_interval_skeletons("en_US"))

    assert "y" in skeletons
    assert not {"d", "M", "H"} & skeletons


# ------------------------------------------------------------------------ hyphen-minus


def _is_range(detection) -> bool:
    kind = detection["type"]
    return kind.startswith("date-interval") or ":range" in kind or "hyphen" in kind


HYPHEN_GANGS = {
    "default": lambda: generated_detectors("en_US"),
    "guarded": lambda: generated_detectors("en_US", (*DEFAULT_FAMILIES, *GUARDED_FAMILIES)),
    "flexible-guarded": lambda: flexible_detectors("en_US", guarded=True),
}


@pytest.mark.parametrize(
    "gang_id",
    HYPHEN_GANGS,
)
def test_a_hyphen_minus_is_no_range_where_icu_writes_another_separator(gang_id):
    found = HYPHEN_GANGS[gang_id]().detect("in 1914-1918, 10-15 kg, 1893-94, 1893–94")

    ranges = {(d["type"], d["text"]) for d in found if _is_range(d)}
    # ICU writes "1893–94" as a range of numbers, falling; never as years.
    assert ranges <= {("number:range", "1893–94")}


def test_a_hyphenated_single_date_is_not_classified_as_a_range():
    text = "2008-09-30"
    detections = {gang_id: gang().detect(text) for gang_id, gang in HYPHEN_GANGS.items()}

    assert all(not any(_is_range(found) for found in result) for result in detections.values())
    # The named flexible-guarded gang makes this a live single-date control: it reads
    # the entire hyphenated surface as one date, while no gang mistakes it for a range.
    dates = [
        found
        for found in detections["flexible-guarded"]
        if found["type"] == "date:flexible" and (found["start"], found["end"]) == (0, len(text))
    ]
    assert len(dates) == 1
    found = dates[0]
    assert not isinstance(found["value"], DateIntervalValue)
    assert dict(found["value"].fields) == {"y": 2008, "M": 9, "d": 30}


def test_where_icu_writes_a_hyphen_minus_the_default_reader_reads_it():
    hyphen = _range("es_ES", 3, 5)
    if "-" not in hyphen:
        pytest.skip("ICU writes es_ES another range separator")
    found = {(d["type"], d["text"]) for d in generated_detectors("es_ES").detect(hyphen)}

    assert ("number:range", hyphen) in found
    # The endpoint's own reading is not touched: "-5" still reads as a negative number.
    assert "-5" in [d["text"] for d in FlexibleNumberDetector("es_ES").detect(hyphen)]


@pytest.mark.parametrize(
    "text", ["ISBN 978-0-385-30414-5", "14-3-3", "el 2024-03-05", "+1-800-555-0199", "-5"]
)
def test_a_run_of_hyphen_joined_numbers_is_not_a_range(text):
    reader = FlexibleNumberRangeDetector("es_ES")
    if "-" not in reader._marks:
        pytest.skip("ICU writes es_ES another range separator")
    assert reader.detect(text) == []
