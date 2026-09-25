"""Readings the default readers refuse on purpose are read under their own types.

A lone "one" or "first", a lowercase Roman numeral, a month or weekday name alone, and a
bare hour are refused by the readers of the existing types, which keep refusing them;
each is deposited by an opt-in reader under a type of its own, so a consumer that wants
every path (forced alignment reads "May" as a month and as a verb) includes it by type.
"""

import pytest

from icukit import DetectorSet
from icukit.detectors import DateTimeValue, NumberValue
from icukit.engine import DEFAULT_FAMILIES, GUARDED_FAMILIES, generated_detectors
from icukit.recognize import (
    FlexibleBareHourDetector,
    FlexibleLoneSpelloutDetector,
    FlexibleLowercaseRomanDetector,
    FlexibleMonthNameDetector,
    FlexibleNumberDetector,
    FlexibleSpelloutDetector,
    FlexibleTextDateDetector,
    FlexibleTimeDetector,
    FlexibleWeekdayNameDetector,
)

GUARDED_TYPES = {
    "number:spellout-lone",
    "number:spellout-lone:ordinal",
    "number:cardinal:roman-lower",
    "date:month-name",
    "date:weekday-name",
    "time:bare-hour",
}


def _read(detector, text):
    return [(d["type"], d["text"], d["value"]) for d in detector.detect(text)]


# --------------------------------------------------------------------- lone spell-out


def test_lone_spellout_reads_the_unit_words_the_spellout_reader_refuses():
    text = "one of them, twenty-one, one hundred, oneself, zero"
    assert _read(FlexibleLoneSpelloutDetector("en_US"), text) == [
        ("number:spellout-lone", "one", NumberValue("1", None)),
        ("number:spellout-lone", "zero", NumberValue("0", None)),
    ]
    # The spell-out reader still refuses both, and keeps its own readings.
    assert _read(FlexibleSpelloutDetector("en_US"), text) == [
        ("number:spellout", "twenty-one", NumberValue("21", None)),
        ("number:spellout", "one hundred", NumberValue("100", None)),
    ]


def test_lone_ordinal_reads_first_under_the_ordinal_rule_set():
    detector = FlexibleLoneSpelloutDetector("en_US", ruleset="%spellout-ordinal")
    assert detector.type == "number:spellout-lone:ordinal"
    assert _read(detector, "the first and second, twenty-first, firstly") == [
        ("number:spellout-lone:ordinal", "first", NumberValue("1", None)),
        ("number:spellout-lone:ordinal", "second", NumberValue("2", None)),
    ]
    assert (
        _read(
            FlexibleSpelloutDetector("en_US", ruleset="%spellout-ordinal"), "the first and second"
        )
        == []
    )


@pytest.mark.parametrize("ruleset", [None, "%spellout-ordinal", "%spellout-numbering-year"])
def test_lone_spellout_is_exactly_what_the_guard_withholds(ruleset):
    text = (
        "One, two, three; twenty-one first second nine hundred and five, "
        "seventh heaven, zero hour, a hundred and one dalmatians, ninety-ninth"
    )
    guarded = FlexibleSpelloutDetector("en_US", ruleset=ruleset)
    lone = FlexibleLoneSpelloutDetector("en_US", ruleset=ruleset)
    unguarded = {(d["start"], d["end"], d["value"]) for d in guarded._scan(text, guard=False)}
    kept = {(d["start"], d["end"], d["value"]) for d in guarded.detect(text)}
    refused = {(d["start"], d["end"], d["value"]) for d in lone.detect(text)}
    assert refused, "the text must exercise the guard"
    assert refused == unguarded - kept
    assert not refused & kept


# ---------------------------------------------------------------- lowercase Roman


def test_lowercase_roman_reads_under_its_own_type():
    assert _read(FlexibleLowercaseRomanDetector("en_US"), "chapter iv, xii, IV, Mix, mixer") == [
        ("number:cardinal:roman-lower", "iv", NumberValue("4", None)),
        ("number:cardinal:roman-lower", "xii", NumberValue("12", None)),
    ]
    # The default number reader still refuses them and reads the uppercase one.
    assert [
        (d["type"], d["text"]) for d in FlexibleNumberDetector("en_US").detect("iv xii IV")
    ] == [("number:cardinal:roman", "IV")]


def test_lowercase_roman_is_exactly_what_the_option_adds():
    text = "i. ii iii iv v vi mix mi cm di dim civil XII xii I v2.0 (x)"
    default = {
        (d["start"], d["end"], d["value"]) for d in FlexibleNumberDetector("en_US").detect(text)
    }
    widened = {
        (d["start"], d["end"], d["value"])
        for d in FlexibleNumberDetector("en_US", accept_lowercase_roman=True).detect(text)
    }
    lower = {
        (d["start"], d["end"], d["value"])
        for d in FlexibleLowercaseRomanDetector("en_US").detect(text)
    }
    assert lower and lower == widened - default


# ---------------------------------------------------------------- month and weekday


def test_month_name_reads_a_month_alone():
    text = "In May, Sept. and September; Mayday, may 5, 2020, 3 May 2020"
    assert _read(FlexibleMonthNameDetector("en_US"), text) == [
        ("date:month-name", "May", DateTimeValue((("M", 5),), "gregorian")),
        ("date:month-name", "Sept.", DateTimeValue((("M", 9),), "gregorian")),
        ("date:month-name", "September", DateTimeValue((("M", 9),), "gregorian")),
    ]
    # The text-date reader reads only the dates, not the names alone.
    assert [d["text"] for d in FlexibleTextDateDetector("en_US").detect(text)] == [
        "may 5, 2020",
        "3 May 2020",
    ]


def test_weekday_name_reads_a_weekday_alone_numbered_from_sunday():
    text = "Sun, Tues. and Tuesday, May 2, 2023; Sunday's and Saturday"
    assert _read(FlexibleWeekdayNameDetector("en_US"), text) == [
        ("date:weekday-name", "Sun", DateTimeValue((("E", 1),), "gregorian")),
        ("date:weekday-name", "Tues.", DateTimeValue((("E", 3),), "gregorian")),
        ("date:weekday-name", "Saturday", DateTimeValue((("E", 7),), "gregorian")),
    ]
    assert FlexibleTextDateDetector("en_US").detect("Sun and Saturday") == []


def test_names_carry_the_locales_pattern_for_their_width():
    short, wide = FlexibleMonthNameDetector("en_US").detect("Sep January")
    assert (short["captures"][0].form, short["spec"].skeleton) == ("short", "MMM")
    assert (wide["captures"][0].form, wide["spec"].skeleton) == ("wide", "MMMM")
    tuesday = FlexibleWeekdayNameDetector("en_US").detect("Tuesday")[0]
    assert (tuesday["captures"][0].form, tuesday["spec"].skeleton) == ("wide", "EEEE")


# ------------------------------------------------------------------------ bare hour


def test_bare_hour_reads_the_twelve_hour_field_where_the_locale_cycle_is_twelve():
    detector = FlexibleBareHourDetector("en_US")
    assert detector.letter == "h"
    assert _read(detector, "meet at 3, or at 12 or (11) or at 13 or at 0.") == [
        ("time:bare-hour", "3", DateTimeValue((("h", 3),), "gregorian")),
        ("time:bare-hour", "12", DateTimeValue((("h", 12),), "gregorian")),
        ("time:bare-hour", "11", DateTimeValue((("h", 11),), "gregorian")),
    ]
    assert FlexibleTimeDetector("en_US").detect("meet at 3, or at 12") == []


def test_bare_hour_reads_the_twenty_four_hour_field_where_the_cycle_is_twenty_four():
    detector = FlexibleBareHourDetector("en_GB")
    assert detector.letter == "H"
    assert _read(detector, "at 15 or 0 or 24") == [
        ("time:bare-hour", "15", DateTimeValue((("H", 15),), "gregorian")),
        ("time:bare-hour", "0", DateTimeValue((("H", 0),), "gregorian")),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "3.5",
        "3:30",
        "3pm",
        "3 pm",
        "3 in the afternoon",
        "3%",
        "-3",
        "3-4",
        "3/4",
        "3D",
        "123",
        "1,000",
        "3rd",
    ],
)
def test_bare_hour_reads_no_number_that_does_not_stand_alone(text):
    assert FlexibleBareHourDetector("en_US").detect(text) == []


# ------------------------------------------------------------------- default gang


def test_guarded_types_are_not_in_the_default_gang():
    names = set(generated_detectors("en_US").names())
    assert not names & GUARDED_TYPES
    assert "number:spellout" in names  # the gang is not empty


def test_guarded_types_are_generated_when_a_consumer_opts_in():
    names = set(generated_detectors("en_US", (*DEFAULT_FAMILIES, *GUARDED_FAMILIES)).names())
    assert GUARDED_TYPES <= names
    assert "number:spellout" in names


def test_a_consumer_includes_and_excludes_a_guarded_type_by_type():
    gang = DetectorSet(()).with_(FlexibleSpelloutDetector("en_US"))
    assert gang.detect("one day in May") == []
    widened = gang.with_(FlexibleLoneSpelloutDetector("en_US"), FlexibleMonthNameDetector("en_US"))
    assert [(d["type"], d["text"]) for d in widened.detect("one day in May")] == [
        ("number:spellout-lone", "one"),
        ("date:month-name", "May"),
    ]
    trimmed = widened.without("date:month-name")
    assert [d["type"] for d in trimmed.detect("one day in May")] == ["number:spellout-lone"]


@pytest.mark.parametrize("type_", sorted(GUARDED_TYPES))
def test_each_guarded_type_names_its_group(type_):
    gang = generated_detectors("en_US", GUARDED_FAMILIES)
    (detector,) = [d for d in gang.detectors if d.type == type_]
    assert type_.split(":")[0] == detector.group
