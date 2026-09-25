"""Relative dates at ICU's short and narrow styles, and relative weekdays."""

import pytest

from icukit.detectors import RelativeDateValue
from icukit.recognize import FlexibleRelativeDateDetector


def _relative(text):
    return [(d["text"], d["value"]) for d in FlexibleRelativeDateDetector("en_US").detect(text)]


@pytest.mark.parametrize(
    "text, offset, unit",
    [
        ("1 hr. ago", -1, "hour"),
        ("in 5 min.", 5, "minute"),
        ("in 2h", 2, "hour"),
        ("last mo.", -1, "month"),
        ("next Tuesday", 1, "tuesday"),
        ("next Tue.", 1, "tuesday"),
        ("last Fri.", -1, "friday"),
        ("this Friday", 0, "friday"),
    ],
)
def test_each_style_icu_writes_reads(text, offset, unit):
    direction = "past" if offset < 0 else "future" if offset > 0 else "present"
    assert _relative(text) == [(text, RelativeDateValue(offset, unit, direction))]


def test_a_named_phrase_carries_its_style_as_the_capture_form():
    forms = {
        text: [c.form for c in d["captures"] if c.name == "relative"]
        for text in ("last month", "last mo.")
        for d in FlexibleRelativeDateDetector("en_US").detect(text)
    }
    assert forms == {"last month": ["wide"], "last mo.": ["short"]}


def test_the_long_style_is_unchanged():
    assert _relative("3 days ago") == [("3 days ago", RelativeDateValue(-3, "day", "past"))]
    assert _relative("yesterday") == [("yesterday", RelativeDateValue(-1, "day", "past"))]
