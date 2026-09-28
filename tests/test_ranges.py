"""Ranges are read as ICU writes them, and a hyphen-minus only where ICU writes one.

Every surface a default reader is held to here is ICU's own: a range formatted by
``NumberRangeFormatter`` or a year interval by ``DateIntervalFormat``, in the ICU the
suite runs on.
"""

from decimal import Decimal

import icu
import pytest

from icukit import (
    ApproximateValue,
    DateIntervalValue,
    DateTimeValue,
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


def _whole(detector, text: str):
    return [
        found for found in detector.detect(text) if (found["start"], found["end"]) == (0, len(text))
    ]


def _amounts(value) -> tuple[Decimal, Decimal]:
    return Decimal(value.start.decimal), Decimal(value.end.decimal)


def _numbers(locale: str) -> list:
    return [FlexibleNumberDetector(locale), FlexiblePercentDetector(locale)]


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize(("low", "high"), [(3, 5), (1000, 2000), (-3, -1)])
def test_a_plain_range_reads_as_icu_writes_it(locale, low, high):
    text = _range(locale, low, high)
    minus = icu.NumberFormatter.withLocale(icu.Locale(locale)).formatInt(-1)[:-1]
    if low < 0 and text.count(minus) < 2:
        # ICU writes the shared sign once ("-3–1" for -3 to -1), which reads as -3 to 1.
        pytest.skip(f"ICU writes {locale} one minus sign for both ends: {text!r}")
    (found,) = _whole(FlexibleNumberRangeDetector(locale), text)

    assert found["type"] == "number:range"
    assert found["value"] == NumberRangeValue(NumberValue(str(low)), NumberValue(str(high)))
    assert [capture.name for capture in found["captures"]] == ["start", "separator", "end"]


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
    return detection["type"].startswith("date-interval") or detection["type"].endswith(":range")


@pytest.mark.parametrize(
    "gang",
    [
        lambda: generated_detectors("en_US"),
        lambda: generated_detectors("en_US", (*DEFAULT_FAMILIES, *GUARDED_FAMILIES)),
        lambda: flexible_detectors("en_US", guarded=True),
    ],
    ids=["default", "guarded", "flexible-guarded"],
)
def test_a_hyphen_minus_is_no_range_where_icu_writes_another_separator(gang):
    found = gang().detect("in 1914-1918, 10-15 kg, 1893-94, 1893–94")

    ranges = {(d["type"], d["text"]) for d in found if _is_range(d)}
    # ICU writes "1893–94" as a range of numbers, falling; never as years.
    assert ranges <= {("number:range", "1893–94")}


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
