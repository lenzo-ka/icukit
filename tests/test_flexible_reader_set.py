"""The flexible reader set: every recall reader of ``icukit.recognize`` for a locale.

The assembled sets that existed before hold few of them: ``generated_detectors`` holds
the readers its ICU probes build, ``date_detectors(flexible=True)`` adds only the
text-date reader, and ``number_detectors(flexible=True)`` only the currency-name reader.
``flexible_detectors`` holds each of them, built for the parameters it chooses from ICU,
so what the flexible readers read is reachable without constructing classes.
"""

import inspect
import time
from decimal import Decimal
from functools import cache

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
from icukit.engine import generated_detectors

LOCALES = ("en_US", "de_DE", "ja_JP")

GUARDED_CLASSES = {
    "FlexibleBareHourDetector",
    "FlexibleLoneSpelloutDetector",
    "FlexibleLowercaseRomanDetector",
    "FlexibleMonthNameDetector",
    "FlexibleWeekdayNameDetector",
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
def _gang(locale: str, guarded: bool = False):
    return flexible_detectors(locale, guarded=guarded)


def _classes(gang) -> set[str]:
    return {type(detector).__name__ for detector in gang.detectors}


@pytest.mark.parametrize("locale", LOCALES)
def test_the_set_holds_each_flexible_reader_and_no_guarded_one(locale):
    start = time.perf_counter()
    gang = flexible_detectors(locale)
    elapsed = time.perf_counter() - start

    assert _classes(gang) == _reader_classes() - GUARDED_CLASSES
    # A guard against a blowup (the full currency inventory in a language of many
    # locales), not a benchmark: en_US, the costliest, builds in seconds.
    assert elapsed < 120


@pytest.mark.parametrize("locale", LOCALES)
def test_guarded_readers_join_on_request_and_every_type_leads_with_its_group(locale):
    gang = _gang(locale, guarded=True)

    assert _classes(gang) == _reader_classes()
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
    # CLDR's preferred units for US and world usages, its mixed person-height unit, and a
    # run of its duration order.
    assert {"measure:mile", "measure:kilometer", "measure:foot-and-inch"} <= types
    assert "measure:hour-and-minute-and-second" in types
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
