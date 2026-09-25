"""A mixed unit of three components, read whole in its smallest one."""

import pytest

from icukit.detectors import MeasureValue
from icukit.recognize import FlexibleMixedMeasureDetector


def _mixed(unit, text):
    return [
        (d["text"], d["value"]) for d in FlexibleMixedMeasureDetector("en_US", unit).detect(text)
    ]


@pytest.mark.parametrize(
    "text", ["1 hr, 15 min, 27 sec", "1h 15m 27s", "1 hour, 15 minutes, 27 seconds"]
)
def test_three_components_read_whole_in_seconds(text):
    assert _mixed("hour-and-minute-and-second", text) == [(text, MeasureValue("4527", "second"))]


def test_every_component_is_needed():
    assert _mixed("hour-and-minute-and-second", "1 hr, 15 min") == []


def test_two_components_read_as_before():
    assert _mixed("foot-and-inch", "5 ft, 10 in") == [("5 ft, 10 in", MeasureValue("70", "inch"))]
