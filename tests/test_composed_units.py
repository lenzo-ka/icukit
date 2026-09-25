"""A unit ICU composes (SI prefix) reads as ICU formats it; a superscript ends no unit."""

import pytest

from icukit.recognize import FlexibleMeasureDetector


def _measures(unit, text):
    return [
        (d["text"], d["value"].decimal, d["value"].unit)
        for d in FlexibleMeasureDetector("en_US", unit).detect(text)
    ]


@pytest.mark.parametrize(
    "unit, text",
    [("kilovolt", "25 kV"), ("kilovolt", "25 kilovolts"), ("kilonewton", "3 kN")],
)
def test_a_composed_unit_reads_as_icu_formats_it(unit, text):
    amount = text.split()[0]
    assert _measures(unit, text) == [(text, amount, unit)]


@pytest.mark.parametrize("text", ["5 km²", "5/km²", "5 km³"])
def test_a_superscript_digit_continues_the_unit_symbol(text):
    # "km²" is square kilometers, not kilometers followed by a mark.
    assert _measures("kilometer", text) == []


def test_the_unit_with_the_superscript_still_reads():
    assert _measures("square-kilometer", "5 km²") == [("5 km²", "5", "square-kilometer")]
