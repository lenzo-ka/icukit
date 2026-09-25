"""The flexible reader set: every recall reader of ``icukit.recognize`` for a locale.

The assembled sets that existed before hold few of them: ``generated_detectors`` holds
the readers its ICU probes build, ``date_detectors(flexible=True)`` adds only the
text-date reader, and ``number_detectors(flexible=True)`` only the currency-name reader.
``flexible_detectors`` holds each of them, built for the parameters it chooses from ICU,
so what the flexible readers read is reachable without constructing classes.
"""

import inspect
import os
import subprocess
import sys
import time
from decimal import Decimal
from functools import cache

import icu
import pytest

import icukit.recognize as recognize
from icukit import flexible_detectors, flexible_detectors_report
from icukit.detectors import (
    DateDetector,
    DateIntervalValue,
    DateTimeValue,
    MeasureValue,
    NumberDetector,
    NumberValue,
    date_detectors,
    number_detectors,
)
from icukit.engine import _current_currencies, generated_detectors

LOCALES = ("en_US", "de_DE", "ja_JP")

GUARDED_CLASSES = {
    "FlexibleBareHourDetector",
    "FlexibleLoneSpelloutDetector",
    "FlexibleLowercaseRomanDetector",
    "FlexibleMonthNameDetector",
    "FlexibleShortYearDateDetector",
    "FlexibleWeekdayNameDetector",
}

# The units every one of the three locales reads: the world's preferences, ICU's duration
# and digital types, and the runs of CLDR's duration order.
COMMON_UNITS = {
    "barrel",
    "bit",
    "byte",
    "celsius",
    "centimeter",
    "centimeter-per-hour",
    "century",
    "cubic-centimeter",
    "cubic-meter",
    "day",
    "day-and-hour",
    "day-and-hour-and-minute",
    "day-and-hour-and-minute-and-second",
    "day-and-hour-and-minute-and-second-and-millisecond",
    "day-and-hour-and-minute-and-second-and-millisecond-and-microsecond",
    "day-and-hour-and-minute-and-second-and-millisecond-and-microsecond-and-nanosecond",
    "decade",
    "fortnight",
    "gigabit",
    "gigabyte",
    "gigawatt",
    "gram",
    "hectare",
    "hectopascal",
    "hour",
    "hour-and-minute",
    "hour-and-minute-and-second",
    "hour-and-minute-and-second-and-millisecond",
    "hour-and-minute-and-second-and-millisecond-and-microsecond",
    "hour-and-minute-and-second-and-millisecond-and-microsecond-and-nanosecond",
    "item-per-cubic-meter",
    "kilobit",
    "kilobyte",
    "kilocalorie",
    "kilogram",
    "kilogram-per-cubic-meter",
    "kilometer",
    "kilometer-per-hour",
    "kilowatt",
    "kilowatt-hour",
    "liter",
    "liter-per-100-kilometer",
    "liter-per-kilometer",
    "megabit",
    "megabyte",
    "megapascal",
    "megawatt",
    "meter",
    "microgram",
    "microsecond",
    "microsecond-and-nanosecond",
    "milligram",
    "milligram-ofglucose-per-deciliter",
    "milliliter",
    "millimeter",
    "millimeter-per-hour",
    "millisecond",
    "millisecond-and-microsecond",
    "millisecond-and-microsecond-and-nanosecond",
    "milliwatt",
    "minute",
    "minute-and-second",
    "minute-and-second-and-millisecond",
    "minute-and-second-and-millisecond-and-microsecond",
    "minute-and-second-and-millisecond-and-microsecond-and-nanosecond",
    "month",
    "month-person",
    "nanosecond",
    "night",
    "pascal",
    "petabyte",
    "quarter",
    "second",
    "second-and-millisecond",
    "second-and-millisecond-and-microsecond",
    "second-and-millisecond-and-microsecond-and-nanosecond",
    "square-centimeter",
    "square-kilometer",
    "square-meter",
    "terabit",
    "terabyte",
    "tonne",
    "watt",
    "week",
    "year",
    "year-person",
    "year-person-and-month-person",
}

EXPECTED_UNITS = {
    "en_US": COMMON_UNITS
    | {
        "acre",
        "cubic-foot",
        "cubic-inch",
        "cubic-meter-per-second",
        "cup",
        "fahrenheit",
        "fluid-ounce",
        "fluid-ounce-imperial",
        "foodcalorie",
        "foot",
        "foot-and-inch",
        "gallon",
        "gallon-imperial",
        "gigapascal",
        "horsepower",
        "inch",
        "inch-ofhg",
        "inch-per-hour",
        "kilonewton",
        "kilovolt",
        "megajoule-per-kilogram",
        "meter-and-centimeter",
        "meter-per-second",
        "mile",
        "mile-per-gallon",
        "mile-per-gallon-imperial",
        "mile-per-hour",
        "mile-scandinavian",
        "millibar",
        "millimole-per-liter",
        "millisievert",
        "nanogram",
        "ounce",
        "pint",
        "pound",
        "pound-and-ounce",
        "pound-force-per-square-inch",
        "quart",
        "square-foot",
        "square-inch",
        "square-mile",
        "stone-and-pound",
        "tablespoon",
        "teaspoon",
        "ton",
        "yard",
    },
    "de_DE": COMMON_UNITS
    | {
        "meter-and-centimeter",
        "millimole-per-liter",
    },
    "ja_JP": COMMON_UNITS
    | {
        "meter-per-second",
    },
}


def _reader_classes() -> set[str]:
    """Every public reader class of ``icukit.recognize``, read from the module."""
    return {
        name
        for name, cls in inspect.getmembers(recognize, inspect.isclass)
        if name.endswith("Detector")
        and not name.startswith("_")
        and cls.__module__ == recognize.__name__
    }


@cache
def _gang(locale: str):
    return flexible_detectors(locale)


def _classes(gang) -> set[str]:
    return {type(detector).__name__ for detector in gang.detectors}


@pytest.mark.parametrize("locale", LOCALES)
def test_the_set_holds_each_flexible_reader_and_no_guarded_one(locale):
    assert _classes(_gang(locale)) == _reader_classes() - GUARDED_CLASSES


@pytest.mark.parametrize("locale", LOCALES)
def test_the_units_are_exactly_those_chosen_for_the_locale(locale):
    units = {
        name.split(":", 1)[1]
        for name in _gang(locale).names()
        if name.startswith("measure:") and name != "measure:duration:numeric"
    }

    assert units == EXPECTED_UNITS[locale]


_RUNNING_TEXT = (
    "On Tue 2:07 PM we drove 5 km and 12.5 mi in 1 hr, 15 min, 27 sec, paid -$42.50 and "
    "($3.10), weighed 5 lb 3 oz on 3/5/2024 AD at 2:07:09 PM Eastern Standard Time; the "
    "fund rose 4.5% to $1.2 billion, €30m and ¥1,000 in 3 weeks, and 2 GB cost Rs. 500. "
)


def _detect_seconds(gang, text: str) -> float:
    start = time.perf_counter()
    gang.detect(text)
    return time.perf_counter() - start


def test_reading_costs_a_small_multiple_of_the_generated_set():
    # The currency and measure readers read the same numbers at the same starts; the
    # set shares those readings within a text, which keeps its cost near the strict
    # set's. Unshared, en_US cost about five times the strict set's on this text.
    flexible, strict = _gang("en_US"), generated_detectors("en_US")
    warm = _RUNNING_TEXT * 5
    flexible.detect(warm)
    strict.detect(warm)
    ratios = []
    for trial in range(3):
        text = f"{trial} {_RUNNING_TEXT * 10}"
        ratios.append(_detect_seconds(flexible, text) / _detect_seconds(strict, text))
    assert min(ratios) < 3, ratios


def test_the_set_is_the_same_in_any_process():
    here = flexible_detectors("ja_JP").names()
    script = "from icukit import flexible_detectors; print(flexible_detectors('ja_JP').names())"
    for seed in ("0", "1"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        assert result.stdout.strip() == repr(here)
    assert flexible_detectors("ja_JP").detect(_RUNNING_TEXT) == _gang("ja_JP").detect(_RUNNING_TEXT)


@pytest.mark.parametrize("locale", LOCALES)
def test_guarded_readers_join_on_request_and_every_type_leads_with_its_group(locale):
    report = flexible_detectors_report(locale, guarded=True)
    gang = report.detectors
    # ja_JP's textual date patterns write no short year, so it has no short-year reader,
    # and the report says so.
    absent = (
        {"FlexibleShortYearDateDetector"}
        if any(skipped.family == "short-year" for skipped in report.skipped)
        else set()
    )

    assert (locale == "ja_JP") == bool(absent)
    assert _classes(gang) == _reader_classes() - absent
    for detector in gang.detectors:
        assert detector.type.split(":")[0] == detector.group, detector.type


def _whole(gang, text: str) -> list[tuple[str, object]]:
    return [
        (found["type"], found["value"])
        for found in gang.detect(text)
        if found["start"] == 0 and found["end"] == len(text)
    ]


def test_the_set_reads_the_flexible_features_in_en_us():
    gang = _gang("en_US")
    expected = {
        "-$42.50": ("number:currency:USD", NumberValue("-42.50", "USD")),
        "($42.50)": ("number:currency:USD", NumberValue("-42.50", "USD")),
        "3/5/2024 AD": (
            "date:flexible",
            DateTimeValue((("G", 1), ("y", 2024), ("M", 3), ("d", 5)), "gregorian"),
        ),
        "1 hr, 15 min, 27 sec": (
            "measure:hour-and-minute-and-second",
            MeasureValue("4527", "second"),
        ),
        "5 ft, 10 in": ("measure:foot-and-inch", MeasureValue("70", "inch")),
        "1.234,56": ("number:decimal", NumberValue("1234.56")),
        "Tue 2:07 PM": (
            "date:datetime-flexible",
            DateTimeValue((("E", 3), ("H", 14), ("m", 7)), "gregorian"),
        ),
        "2:07:09 PM Eastern Standard Time": (
            "time:flexible",
            DateTimeValue((("H", 14), ("m", 7), ("s", 9)), "gregorian"),
        ),
        "2 in the afternoon": ("time:flexible", DateTimeValue((("H", 14),), "gregorian")),
        "3 weeks": ("measure:week", MeasureValue("3", "week")),
        "3 wk": ("measure:week", MeasureValue("3", "week")),
        "2 GB": ("measure:gigabyte", MeasureValue("2", "gigabyte")),
        "100 MB": ("measure:megabyte", MeasureValue("100", "megabyte")),
        "3/5/2024 – 3/7/2024": (
            "date-interval:yMd",
            DateIntervalValue(
                DateTimeValue((("y", 2024), ("M", 3), ("d", 5)), "gregorian"),
                DateTimeValue((("y", 2024), ("M", 3), ("d", 7)), "gregorian"),
            ),
        ),
    }
    missing = {text: want for text, want in expected.items() if want not in _whole(gang, text)}
    assert not missing


def test_the_set_reads_a_comma_decimal_and_a_euro_amount_in_de_de():
    gang = _gang("de_DE")

    assert ("number:decimal", NumberValue("1.5")) in _whole(gang, "1,5")
    assert ("number:decimal", NumberValue("1234.56")) in _whole(gang, "1.234,56")
    assert ("number:currency:EUR", NumberValue("-42.50", "EUR")) in _whole(gang, "-42,50 €")


def test_the_set_reads_an_era_date_and_a_yen_amount_in_ja_jp():
    gang = _gang("ja_JP")
    era_date = DateTimeValue((("G", 1), ("y", 2024), ("M", 3), ("d", 5)), "gregorian")

    assert ("date:flexible", era_date) in _whole(gang, "西暦2024/3/5")
    assert any(
        kind == "number:currency:JPY" and Decimal(value.decimal) == 1234
        for kind, value in _whole(gang, "￥1,234")
    )


def test_parameters_are_chosen_from_icu():
    types = set(_gang("en_US").names())

    # The locale's own currency, another en locale's (en_IN), and one en_US writes
    # with a symbol of its own (JPY, "¥").
    assert {"number:currency:USD", "number:currency:INR", "number:currency:JPY"} <= types
    # A withdrawn currency is not chosen, though de_DE writes the Mark with a symbol of
    # its own ("DM").
    de_types = set(_gang("de_DE").names())
    assert "number:currency:EUR" in de_types
    assert not {"number:currency:DEM", "number:currency:ATS"} & de_types
    # Every interval skeleton the engine's own probe accepts.
    interval_types = {name for name in types if name.startswith("date-interval:")}
    engine_intervals = {
        name for name in generated_detectors("en_US").names() if name.startswith("date-interval:")
    }
    assert interval_types == engine_intervals


def test_callers_choose_currencies_and_units():
    gang = flexible_detectors("en_US", currencies=["EUR"], units=["hertz", "pound-and-ounce"])
    types = set(gang.names())

    assert {name for name in types if name.startswith("number:currency:")} == {
        "number:currency:EUR"
    }
    assert {name for name in types if name.startswith("measure:")} == {
        "measure:hertz",
        "measure:pound-and-ounce",
        "measure:duration:numeric",
    }


def test_locales_chooses_what_the_language_wide_readers_read():
    gang = flexible_detectors("en_US", locales=["en_GB"], currencies=(), units=())
    widened = [detector for detector in gang.detectors if hasattr(detector, "locales")]

    assert widened
    for detector in widened:
        assert detector.locales == ("en_GB", "en_US"), detector.type
    with pytest.raises(ValueError):
        flexible_detectors("en_US", locales=["de_DE"])


def test_an_unbuildable_member_is_reported_not_raised():
    report = flexible_detectors_report("en_US", currencies=["ZZZ"], units=())

    assert "number:currency:ZZZ" not in report.detectors.names()
    assert {skipped.family for skipped in report.skipped if skipped.spec == "ZZZ"} == {
        "currency",
        "currency-name",
    }


def test_a_currency_counts_as_current_where_any_locale_of_a_territory_uses_it():
    current = _current_currencies()

    for name in icu.Locale.getAvailableLocales():
        if icu.Locale(name).getCountry():
            code = icu.NumberFormat.createCurrencyInstance(icu.Locale(name)).getCurrency()
            assert code in current or code == "XXX", (name, code)
    assert {"EUR", "USD", "ZAR", "NAD"} <= current
    assert not {"DEM", "FRF", "ATS"} & current
    # A known gap: ICU gives every locale of Lesotho the rand, so the loti in use beside
    # it is never chosen; a caller passes currencies=["LSL"] for it.
    assert "LSL" not in current


def test_person_durations_come_only_from_the_preferences():
    types = set(_gang("ja_JP").names())

    assert "measure:week" in types
    assert not {"measure:week-person", "measure:day-person"} & types
    # person-age's preference names these.
    assert {"measure:year-person", "measure:year-person-and-month-person"} <= types


def test_the_existing_sets_are_unchanged():
    assert date_detectors("en_US", ["yMd"], flexible=True).names() == (
        "date:yMd",
        "date:text-flexible",
    )
    assert number_detectors("en_US", currencies=["USD"], flexible=True).names() == (
        "number:decimal",
        "number:percent",
        "number:currency:USD",
        "number:currency-name:USD",
    )
    generated = generated_detectors("en_US")
    assert not {"measure", "time", "fraction", "ordinal"} & {d.group for d in generated.detectors}
    assert not any(
        isinstance(detector, (recognize.FlexibleCurrencyDetector, NumberDetector))
        for detector in generated.detectors
    )
    assert any(isinstance(detector, DateDetector) for detector in generated.detectors)
