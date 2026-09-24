"""A time ending in, or split by, CLDR's hour symbol, and a fraction made plural."""

import pytest

from icukit.recognize import FlexibleFractionDetector, FlexibleTimeDetector, _hour_unit_forms


def _times(text, locale):
    return [
        (d["text"], d["value"].fields, [c.name for c in d["captures"]])
        for d in FlexibleTimeDetector(locale).detect(text)
    ]


@pytest.mark.parametrize(
    "locale, text, surface, captures",
    [
        ("de_DE", "um 10:30h", "10:30h", ["H", "m", "hour-unit"]),
        ("de_DE", "um 10:30 Std. heute", "10:30 Std.", ["H", "m", "hour-unit"]),
        ("es", "a las 10:30h", "10:30h", ["H", "m", "hour-unit"]),
        ("fr_FR", "à 10h30 ce soir", "10h30", ["H", "hour-unit", "m"]),
    ],
)
def test_a_time_reads_with_cldrs_hour_symbol(locale, text, surface, captures):
    assert (surface, (("H", 10), ("m", 30)), captures) in _times(text, locale)


@pytest.mark.parametrize("locale, text", [("de_DE", "10:30hx"), ("fr_FR", "10h3")])
def test_the_hour_symbol_must_end_the_word_or_precede_two_minute_digits(locale, text):
    assert _times(text, locale) == []


def test_a_trailing_hour_unit_keeps_the_plain_time_too():
    assert [(s, f) for s, f, _c in _times("10:30 hr later", "en_US")] == [
        ("10:30", (("H", 10), ("m", 30))),
        ("10:30 hr", (("H", 10), ("m", 30))),
    ]


def test_hour_forms_come_from_cldr_measure_formats():
    assert ("h", True) in _hour_unit_forms("fr_FR")
    assert ("Std.", False) in _hour_unit_forms("de_DE")


@pytest.mark.parametrize(
    "text, captures",
    [
        ("3/4s", ["numerator", "denominator", "suffix"]),
        ("3/4's", ["numerator", "denominator", "apostrophe", "suffix"]),
    ],
)
def test_a_fraction_made_plural_spans_its_suffix(text, captures):
    detections = FlexibleFractionDetector("en_US").detect(text)

    assert [
        (d["text"], d["value"].decimal, [c.name for c in d["captures"]]) for d in detections
    ] == [(text, "0.75", captures)]
