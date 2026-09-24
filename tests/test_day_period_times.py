"""Clock times with a day period read ICU's forms, and an hour alone reads with one."""

import pytest

from icukit.recognize import FlexibleTimeDetector, _language_day_periods


def _times(text, locale="en_US"):
    return [
        (d["text"], d["value"].fields, [c.name for c in d["captures"]])
        for d in FlexibleTimeDetector(locale).detect(text)
    ]


@pytest.mark.parametrize(
    "text, surface, fields",
    [
        ("at 5pm", "5pm", (("H", 17),)),
        ("at 5 pm", "5 pm", (("H", 17),)),
        ("10am sharp", "10am", (("H", 10),)),
        ("12am", "12am", (("H", 0),)),
        ("12pm", "12pm", (("H", 12),)),
        ("5 p.m. today", "5 p.m.", (("H", 17),)),
        ("5:30 p.m.", "5:30 p.m.", (("H", 17), ("m", 30))),
        ("7:00pm", "7:00pm", (("H", 19), ("m", 0))),
        ("5p", "5p", (("H", 17),)),
    ],
)
def test_a_day_period_after_the_time_reads(text, surface, fields):
    assert [(s, f) for s, f, _ in _times(text)] == [(surface, fields)]


def test_an_hour_with_a_day_period_captures_the_hour_and_the_period():
    assert _times("5pm") == [("5pm", (("H", 17),), ["H", "day-period"])]


@pytest.mark.parametrize("text", ["13pm", "at 5", "5 pmol", "5 p", "5 a day"])
def test_no_time_without_a_valid_hour_and_period(text):
    assert _times(text) == []


def test_the_forms_are_icus_across_the_language():
    forms = {form.casefold() for form, _index, _narrow in _language_day_periods("en")}

    # en_US's "AM", en_CA's "a.m.", and the narrow "a".
    assert {"am", "a.m.", "a", "pm", "p.m.", "p"} <= forms


def test_only_the_narrow_forms_are_marked_narrow():
    narrow = {form for form, _index, is_narrow in _language_day_periods("en") if is_narrow}

    assert narrow == {"a", "p"}
