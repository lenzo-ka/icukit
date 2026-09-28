"""Ranges are read as ICU writes them, and a hyphen-minus range is a guarded reading.

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
    flexible_detectors_report,
    generated_detectors,
)
from icukit.engine import GUARDED_FAMILIES, _date_interval_skeletons
from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleDateIntervalDetector,
    FlexibleMeasureDetector,
    FlexibleNumberDetector,
    FlexibleNumberRangeDetector,
    FlexiblePercentDetector,
    FlexibleYearRangeDetector,
    _locale_digit_map,
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
    assert not {"number:range-hyphen", "measure:range-hyphen"} & names
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


def test_a_lone_numeric_field_other_than_the_year_has_no_interval_reader():
    skeletons = set(_date_interval_skeletons("en_US"))

    assert "y" in skeletons
    assert not {"d", "M", "H"} & skeletons


# ------------------------------------------------------------------------ guarded hyphen


def _years(first: int, last: int) -> DateIntervalValue:
    return DateIntervalValue(
        DateTimeValue((("y", first),), "gregorian"), DateTimeValue((("y", last),), "gregorian")
    )


@pytest.mark.parametrize(
    ("text", "first", "last"),
    [
        ("1914-1918", 1914, 1918),
        ("1893-94", 1893, 1894),
        ("1998-02", 1998, 2002),
        ("2003-4", 2003, 2004),
    ],
)
def test_a_hyphen_year_range_is_a_guarded_reading(text, first, last):
    (found,) = _whole(FlexibleYearRangeDetector("en_US"), text)

    assert found["type"] == "date-interval:y-hyphen"
    assert found["value"] == _years(first, last)
    if len(text) < 9:
        assert found["captures"][-1].form == "abbreviated"


def test_icus_separator_with_a_shortened_year_is_a_guarded_reading():
    separator = FlexibleYearRangeDetector("en_US", form="abbreviated")._written[0]
    text = f"1893{separator}94"
    (found,) = _whole(FlexibleYearRangeDetector("en_US", form="abbreviated"), text)

    assert found["type"] == "date-interval:y-abbreviated"
    assert found["value"] == _years(1893, 1894)


@pytest.mark.parametrize(
    "text", ["2024-03", "2024-03-05", "14-3-3", "555-1234", "1918-1914", "3-5"]
)
def test_a_hyphen_that_is_not_a_year_range_is_not_read_as_one(text):
    assert FlexibleYearRangeDetector("en_US").detect(text) == []


def test_a_hyphen_number_range_keeps_the_negative_reading_beside_it():
    reader = FlexibleNumberRangeDetector("en_US", form="range-hyphen")
    (found,) = _whole(reader, "1624-1713")

    assert found["type"] == "number:range-hyphen"
    assert found["value"] == NumberRangeValue(NumberValue("1624"), NumberValue("1713"))
    negatives = [d["text"] for d in FlexibleNumberDetector("en_US").detect("1624-1713")]
    assert "-1713" in negatives


@pytest.mark.parametrize(
    "text", ["ISBN 978-0-385-30414-5", "14-3-3", "on 2024-03-05", "+1-800-555-0199", "-5"]
)
def test_a_run_of_hyphen_joined_numbers_is_not_a_range(text):
    assert FlexibleNumberRangeDetector("en_US", form="range-hyphen").detect(text) == []


def test_a_hyphen_measure_range_is_a_guarded_reading():
    reader = FlexibleNumberRangeDetector(
        "en_US", [FlexibleMeasureDetector("en_US", "kilogram")], form="range-hyphen"
    )
    (found,) = _whole(reader, "10-15 kg")

    assert found["type"] == "measure:range-hyphen"
    assert found["value"] == NumberRangeValue(
        MeasureValue("10", "kilogram"), MeasureValue("15", "kilogram")
    )


def test_where_icu_writes_a_hyphen_minus_the_default_reader_reads_it():
    hyphen = _range("es_ES", 3, 5)
    if "-" not in hyphen:
        pytest.skip("ICU writes es_ES another range separator")
    report = flexible_detectors_report("es_ES", currencies=(), units=(), guarded=True)

    assert FlexibleNumberRangeDetector("es_ES", form="range-hyphen").has_marks is False
    assert "number:range-hyphen" not in report.detectors.names()
    assert any(skipped.spec == "number:range-hyphen" for skipped in report.skipped)
    assert _whole(FlexibleNumberRangeDetector("es_ES"), hyphen)[0]["type"] == "number:range"


def test_the_guarded_set_adds_the_hyphen_readers():
    gang = flexible_detectors("en_US", guarded=True)
    names = set(gang.names())

    assert {
        "number:range-hyphen",
        "measure:range-hyphen",
        "date-interval:y-hyphen",
        "date-interval:y-abbreviated",
    } <= names
    assert {"date-interval:y-hyphen", "date-interval:y-abbreviated"} <= set(
        generated_detectors("en_US", GUARDED_FAMILIES).names()
    )
    found = {(d["type"], d["text"]) for d in gang.detect("in 1914-1918")}
    assert {
        ("number:range-hyphen", "1914-1918"),
        ("date-interval:y-hyphen", "1914-1918"),
        ("number:decimal", "-1918"),
    } <= found


def test_a_shortened_year_is_written_out_in_the_digits_it_is_written_in():
    digits = _locale_digit_map("ar_EG")
    native = "".join(sorted(digits, key=digits.__getitem__))
    reader = FlexibleYearRangeDetector("ar_EG", form="abbreviated")
    if not reader.has_marks:
        pytest.skip("ICU writes ar_EG no year interval separator")
    separator = reader._written[0]
    text = f"{native[1]}{native[8]}{native[9]}{native[3]}{separator}{native[9]}{native[4]}"

    values = [found["value"] for found in _whole(reader, text)]
    assert [(v.start.fields, v.end.fields) for v in values] == [((("y", 1893),), (("y", 1894),))]
