"""A rate's per form written without an amount reads as the rate's unit alone."""

import pytest

from icukit import UnitValue
from icukit.detectors import MeasureValue
from icukit.recognize import FlexibleMeasureDetector


def _readings(unit, text):
    return [(d["text"], d["value"]) for d in FlexibleMeasureDetector("en_US", unit).detect(text)]


@pytest.mark.parametrize(
    "unit, text, surface, rate",
    [
        ("second", "/s", "/s", "per-second"),
        ("second", "per second", "per second", "per-second"),
        ("square-kilometer", "/km²", "/km²", "per-square-kilometer"),
        ("square-kilometer", "/km2", "/km2", "per-square-kilometer"),
        ("minute", "120 beats/min", "/min", "per-minute"),
        ("gram", "/g", "/g", "per-gram"),
    ],
)
def test_a_per_form_without_an_amount_reads_as_its_unit(unit, text, surface, rate):
    assert _readings(unit, text) == [(surface, UnitValue(rate))]


def test_a_per_form_after_its_amount_stays_the_rate():
    assert _readings("second", "1.0/s") == [("1.0/s", MeasureValue("1.0", "per-second"))]
    assert _readings("square-kilometer", "5 per square kilometre") == [
        ("5 per square kilometre", MeasureValue("5", "per-square-kilometer"))
    ]


@pytest.mark.parametrize("text", ["/sec", "/s2", "s"])
def test_what_icu_does_not_write_as_a_per_form_is_not_read(text):
    assert _readings("second", text) == []
