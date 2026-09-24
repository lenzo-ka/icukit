"""Time zones after a time, the language's time separators, and Roman ordinals."""

import pytest

from icukit.recognize import (
    FlexibleOrdinalDetector,
    FlexibleTimeDetector,
    _language_time_separators,
    _language_zone_abbreviations,
    _punctuation_ordinal_markers,
)


def _times(text, locale="en_US"):
    return [(d["text"], d["value"].fields) for d in FlexibleTimeDetector(locale).detect(text)]


@pytest.mark.parametrize(
    "text, plain, zoned, fields",
    [
        ("10 PM ET", "10 PM", "10 PM ET", (("H", 22),)),
        ("18:00 UTC", "18:00", "18:00 UTC", (("H", 18), ("m", 0))),
        ("5 p.m. EST", "5 p.m.", "5 p.m. EST", (("H", 17),)),
        ("2:00 p.m. EDT", "2:00 p.m.", "2:00 p.m. EDT", (("H", 14), ("m", 0))),
        ("14:00 CET", "14:00", "14:00 CET", (("H", 14), ("m", 0))),
        ("18:30:00 GMT", "18:30:00", "18:30:00 GMT", (("H", 18), ("m", 30), ("s", 0))),
    ],
)
def test_a_zone_after_a_time_is_read_beside_the_plain_time(text, plain, zoned, fields):
    assert _times(text) == [(plain, fields), (zoned, fields)]


def test_the_zone_is_its_own_capture():
    detection = FlexibleTimeDetector("en_US").detect("10 PM ET")[-1]
    zone = [c for c in detection["captures"] if c.name == "time-zone"]

    assert [(c.text, c.value) for c in zone] == [(" ET", "ET")]


@pytest.mark.parametrize("text", ["10:30 ETC", "10:30 et"])
def test_only_an_icu_zone_abbreviation_in_its_case_is_a_zone(text):
    assert [surface for surface, _ in _times(text)] == ["10:30"]


def test_zone_abbreviations_come_from_icu_display_names():
    assert {"ET", "EST", "EDT", "UTC", "GMT", "CET", "PT", "BST"} <= set(
        _language_zone_abbreviations("en")
    )
    assert not any("+" in form or len(form) > 5 for form in _language_zone_abbreviations("en"))


@pytest.mark.parametrize(
    "text, fields",
    [
        ("7.30pm", (("H", 19), ("m", 30))),
        ("1.00am", (("H", 1), ("m", 0))),
        ("8.00 PM", (("H", 20), ("m", 0))),
        ("01.11", (("H", 1), ("m", 11))),
    ],
)
def test_a_time_reads_with_any_separator_its_language_writes(text, fields):
    assert _times(text) == [(text, fields)]


def test_the_separators_are_cldrs_for_the_language():
    assert {":", "."} <= set(_language_time_separators("en"))


def _ordinals(text, locale="en_US"):
    return [
        (d["text"], d["value"].decimal, [(c.name, c.form) for c in d["captures"]])
        for d in FlexibleOrdinalDetector(locale).detect(text)
    ]


@pytest.mark.parametrize(
    "text, surface, value",
    [
        ("Henry V. was", "V.", "5"),
        ("Pius X.", "X.", "10"),
        ("Ist", "Ist", "1"),
        ("IInd", "IInd", "2"),
        ("XIVth", "XIVth", "14"),
        ("XXVth", "XXVth", "25"),
        ("Cth", "Cth", "100"),
    ],
)
def test_a_roman_numeral_with_an_ordinal_suffix_or_marker_is_an_ordinal(text, surface, value):
    assert _ordinals(text) == [
        (surface, value, [("integer", "roman"), ("ordinal-affix", "symbol")])
    ]


@pytest.mark.parametrize("text", ["IIst", "V", "iv.", "VX.", "XIVthx"])
def test_no_roman_ordinal_without_the_right_suffix_or_a_valid_numeral(text):
    assert _ordinals(text) == []


def test_the_punctuation_ordinal_marker_is_icus():
    assert "." in _punctuation_ordinal_markers()
