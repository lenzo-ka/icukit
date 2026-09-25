"""Forms other locales of the language write, the caller's choice of them, and gangs."""

import pytest

from icukit import DetectorSet, date_detectors, detector_key
from icukit.detectors import NumberDetector
from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleDateDetector,
    FlexibleMeasureDetector,
    FlexibleMixedMeasureDetector,
    FlexibleNumberDetector,
    FlexibleNumericDurationDetector,
    FlexiblePercentDetector,
    FlexibleTextDateDetector,
    FlexibleTimeDetector,
    _language_locale_names,
    _numeric_duration_patterns,
)


def default_locales(language):
    return _language_locale_names(language)


def _texts(detector, text):
    return [d["text"] for d in detector.detect(text)]


def _numbers(detector, text):
    return [(d["text"], d["value"].decimal) for d in detector.detect(text)]


@pytest.mark.parametrize(
    "unit, text",
    [
        ("kilometer", "12 kilometres"),
        ("liter", "2 litres"),
        ("square-kilometer", "5 square kilometres"),
    ],
)
def test_a_unit_reads_in_the_spelling_of_any_locale_of_the_language(unit, text):
    assert _texts(FlexibleMeasureDetector("en_US", unit), text) == [text]


def test_a_rate_reads_in_another_locales_spelling():
    detections = FlexibleMeasureDetector("en_US", "square-kilometer").detect(
        "5 per square kilometre"
    )
    assert [(d["text"], d["value"].unit) for d in detections] == [
        ("5 per square kilometre", "per-square-kilometer")
    ]


@pytest.mark.parametrize(
    "text, reading",
    [
        ("250 000 people", ("250 000", "250000")),
        ("250\N{NARROW NO-BREAK SPACE}000", ("250\N{NARROW NO-BREAK SPACE}000", "250000")),
        ("1'234'567", ("1'234'567", "1234567")),
        ("12,34,567", ("12,34,567", "1234567")),
    ],
)
def test_a_number_reads_in_another_locales_grouping(text, reading):
    assert reading in _numbers(FlexibleNumberDetector("en_US"), text)


def test_a_grouped_reading_is_added_beside_the_separate_numbers():
    assert _numbers(FlexibleNumberDetector("en_US"), "12 100") == [
        ("12", "12"),
        ("12 100", "12100"),
        ("100", "100"),
    ]


def test_a_grouping_that_writes_the_decimal_separator_gives_no_rival_reading():
    # en_DE groups with ".", en_US's decimal separator; es_419 groups with ",", Spanish's.
    # Text the locale reads keeps that reading alone: "1.234" is not also 1234.
    assert _numbers(FlexibleNumberDetector("en_US"), "1.234") == [("1.234", "1.234")]
    assert _numbers(FlexibleNumberDetector("es"), "1,5") == [("1,5", "1.5")]


@pytest.mark.parametrize(
    "build, text",
    [
        (
            lambda locales: FlexibleMeasureDetector("en_US", "kilometer", locales=locales),
            "12 kilometres",
        ),
        (
            lambda locales: FlexibleMixedMeasureDetector(
                "en_US", "meter-and-centimeter", locales=locales
            ),
            "1 metre, 50 centimetres",
        ),
        (lambda locales: FlexiblePercentDetector("en_US", locales=locales), "5 per cent"),
        (lambda locales: FlexibleTimeDetector("en_US", locales=locales), "7.30pm"),
        (lambda locales: FlexibleDateDetector("en_US", locales=locales), "2020-12-31"),
    ],
)
def test_a_caller_chooses_the_locales_a_detector_reads(build, text):
    # Each form is another locale's: read by default, not when en_US alone is chosen.
    assert _texts(build(None), text) == [text]
    assert _texts(build(()), text) == []


def test_the_choice_narrows_and_widens_the_forms_read():
    assert _texts(FlexibleMeasureDetector("en_US", "kilometer", locales=()), "12 kilometres") == []
    assert _texts(
        FlexibleMeasureDetector("en_US", "kilometer", locales=["en_GB"]), "12 kilometres"
    ) == ["12 kilometres"]
    only = FlexibleNumberDetector("en_US", locales=())
    assert ("12,34,567", "1234567") not in _numbers(only, "12,34,567")
    indian = FlexibleNumberDetector("en_US", locales=["en_IN"])
    assert ("12,34,567", "1234567") in _numbers(indian, "12,34,567")
    assert _texts(FlexiblePercentDetector("en_US", locales=()), "5 per cent") == []
    assert _texts(FlexibleTimeDetector("en_US", locales=()), "7.30pm") == []


def test_the_chosen_locales_are_canonical_and_include_the_detectors_own():
    assert FlexibleMeasureDetector("en_US", "meter", locales=["en-GB"]).locales == (
        "en_GB",
        "en_US",
    )
    assert FlexibleMeasureDetector("en_US", "meter").locales is None


def test_a_locale_of_another_language_is_refused():
    with pytest.raises(ValueError, match="not a locale of"):
        FlexibleMeasureDetector("en_US", "kilometer", locales=["fr"])


def test_detectors_of_one_type_for_two_locales_share_a_gang():
    us = FlexibleMeasureDetector("en_US", "kilometer")
    gb = FlexibleMeasureDetector("en_GB", "kilometer")
    gang = DetectorSet(()).with_(us, gb)

    assert gang.detectors == (us, gb)
    assert gang.names() == ("measure:kilometer", "measure:kilometer")
    assert gang.without("measure:kilometer").detectors == ()
    assert gang.without("measure:kilometer", locale="en_GB").detectors == (us,)


def test_a_detector_with_the_same_key_replaces_a_member_in_place():
    first = FlexibleMeasureDetector("en_US", "kilometer")
    second = FlexibleMeasureDetector("en_US", "kilometer")
    narrowed = FlexibleMeasureDetector("en_US", "kilometer", locales=())
    gang = DetectorSet(()).with_(first).with_(second)

    assert gang.detectors == (second,)
    assert detector_key(first)[:3] == (
        "measure:kilometer",
        "icukit.recognize.FlexibleMeasureDetector",
        "en_US",
    )
    assert DetectorSet(()).with_(first, narrowed).detectors == (first, narrowed)


def test_a_default_selection_is_keyed_by_the_locales_it_reads():
    default = FlexibleMeasureDetector("en_US", "kilometer")
    every = FlexibleMeasureDetector("en_US", "kilometer", locales=default_locales("en"))

    assert "en_GB" in detector_key(default)[3]
    assert detector_key(default) == detector_key(every)
    assert DetectorSet(()).with_(default, every).detectors == (every,)


@pytest.mark.parametrize("locales", [None, ()])
def test_a_strict_and_a_flexible_reader_of_one_type_are_two_members(locales):
    strict = NumberDetector("en_US", "currency", "USD")
    flexible = FlexibleCurrencyDetector("en_US", "USD", locales=locales)

    assert DetectorSet(()).with_(strict).with_(flexible).detectors == (strict, flexible)
    assert DetectorSet(()).with_(flexible).with_(strict).detectors == (flexible, strict)
    both = DetectorSet(()).with_(strict, flexible)
    found = {(d["type"], d["text"]) for d in both.detect("Paid ($12.50) and -$5.")}
    assert {
        ("number:currency:USD", "($12.50)"),
        ("number:currency:USD", "$12.50"),
        ("number:currency:USD", "-$5"),
    } <= found


def test_date_detectors_pass_the_choice_to_the_flexible_reader():
    gang = date_detectors("en_US", ["yMd"], flexible=True, locales=["en_GB"])
    readers = [d for d in gang.detectors if isinstance(d, FlexibleTextDateDetector)]

    assert [reader.locales for reader in readers] == [("en_GB", "en_US")]


def _durations(text, locale="en_US"):
    return [
        (d["text"], d["value"].decimal, d["value"].unit, d["spec"].unit)
        for d in FlexibleNumericDurationDetector(locale).detect(text)
    ]


def test_a_race_time_reads_as_cldr_writes_minutes_and_seconds():
    assert ("1:47.22", "107.22", "second", "minute-and-second") in _durations("won in 1:47.22")


def test_hours_minutes_and_seconds_read_whole():
    assert _durations("marathon 2:03:04") == [
        ("2:03:04", "7384", "second", "hour-and-minute-and-second")
    ]


def test_each_pattern_that_reads_the_text_is_kept():
    assert _durations("2:30") == [
        ("2:30", "150", "minute", "hour-and-minute"),
        ("2:30", "150", "second", "minute-and-second"),
    ]


@pytest.mark.parametrize("text", ["10:75", "12:34:56:78", "v1:47", "3.14", "1:4"])
def test_what_no_duration_pattern_writes_is_not_read(text):
    assert _durations(text) == []


def test_the_fields_are_captured_by_their_pattern_letters():
    detection = FlexibleNumericDurationDetector("en_US").detect("2:03:04.5")[0]

    assert [(c.name, c.text) for c in detection["captures"]] == [
        ("h", "2"),
        ("m", "03"),
        ("s", "04"),
        ("decimal-separator", "."),
        ("fraction", "5"),
    ]


def test_the_patterns_are_cldrs_including_their_separators():
    assert ("ms", ("m", "s"), (1, 2), (".",), ",") in _numeric_duration_patterns("da")
    assert ("1.47,5", "107.5", "second", "minute-and-second") in _durations("1.47,5", "da")
