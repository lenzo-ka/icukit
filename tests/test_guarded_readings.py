"""Readings the default readers refuse on purpose are read under their own types.

A lone "one" or "first", a lowercase Roman numeral, a month or weekday name alone, a bare
hour, and a date with a two- or three-digit year are refused by the readers of the
default types; each is deposited by an opt-in reader under a type of its own, so a
consumer that wants every path (forced alignment reads "May" as a month and as a verb)
includes it by type.
"""

import pytest

from icukit import DetectorSet
from icukit.detectors import DateTimeValue, NumberValue
from icukit.engine import DEFAULT_FAMILIES, GUARDED_FAMILIES, generated_detectors
from icukit.recognize import (
    FlexibleBareHourDetector,
    FlexibleDateTimeDetector,
    FlexibleLoneSpelloutDetector,
    FlexibleLowercaseRomanDetector,
    FlexibleMonthNameDetector,
    FlexibleNumberDetector,
    FlexibleShortYearDateDetector,
    FlexibleSpelloutDetector,
    FlexibleTextDateDetector,
    FlexibleTimeDetector,
    FlexibleWeekdayNameDetector,
    _detect_flexible,
)

GUARDED_TYPES = {
    "number:spellout-lone",
    "number:spellout-lone:ordinal",
    "number:cardinal:roman-lower",
    "date:month-name",
    "date:weekday-name",
    "date:short-year",
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


@pytest.mark.parametrize(
    "locale, text, hours",
    [
        ("en_US", "On May 5, 2020 we left at 3", [26]),
        ("en_US", "Jan 3 at 4", [9]),
        ("en_US", "5 March 2024 at 4", [16]),
        ("de_DE", "am 3. Mai 2020 um 3", [18]),
    ],
)
def test_bare_hour_leaves_a_day_inside_a_date_to_the_date(locale, text, hours):
    found = FlexibleBareHourDetector(locale).detect(text)
    assert [d["start"] for d in found] == hours


# ------------------------------------------------------------------------ short year


def _dated(detector, text):
    return [(d["type"], d["text"], d["value"].fields) for d in detector.detect(text)]


# The counts after a date that the text-date reader took for a two- or three-digit year.
SHORT_YEAR_REPROS = [
    (
        "5 June 200 attendees",
        [("date:text-flexible", "5 June", (("M", 6), ("d", 5)))],
        [("date:short-year", "5 June 200", (("y", 200), ("M", 6), ("d", 5)))],
    ),
    (
        "in June 200 cases",
        [],
        [("date:short-year", "June 200", (("y", 200), ("M", 6)))],
    ),
    (
        "on 5 June 20 people came",
        [
            ("date:text-flexible", "5 June", (("M", 6), ("d", 5))),
            ("date:text-flexible", "June 20", (("M", 6), ("d", 20))),
        ],
        [("date:short-year", "5 June 20", (("y", 20), ("M", 6), ("d", 5)))],
    ),
]


@pytest.mark.parametrize("text, dates, short", SHORT_YEAR_REPROS)
def test_the_text_date_reader_reads_no_two_or_three_digit_year(text, dates, short):
    assert _dated(FlexibleTextDateDetector("en_US"), text) == dates


@pytest.mark.parametrize("text, dates, short", SHORT_YEAR_REPROS)
def test_the_short_year_reader_reads_them_as_written(text, dates, short):
    assert _dated(FlexibleShortYearDateDetector("en_US"), text) == short


@pytest.mark.parametrize(
    "locale, text, surface, fields",
    [
        ("en_US", "5 June 2020 attendees", "5 June 2020", (("y", 2020), ("M", 6), ("d", 5))),
        ("en_US", "May 5, 2020", "May 5, 2020", (("y", 2020), ("M", 5), ("d", 5))),
        ("en_US", "in June 2000", "June 2000", (("y", 2000), ("M", 6))),
        ("en_GB", "Tuesday, 2 May 2023", "Tuesday, 2 May 2023", (("y", 2023), ("M", 5), ("d", 2))),
        ("de_DE", "15. Januar 2012", "15. Januar 2012", (("y", 2012), ("M", 1), ("d", 15))),
    ],
)
def test_a_four_digit_year_reads_as_before_and_not_as_a_short_year(locale, text, surface, fields):
    assert (surface, fields) in [
        (d["text"], d["value"].fields) for d in FlexibleTextDateDetector(locale).detect(text)
    ]
    assert FlexibleShortYearDateDetector(locale).detect(text) == []


def test_a_short_year_beside_an_era_stays_a_date():
    text = "5 March 44 BC"
    fields = (("G", 0), ("y", 44), ("M", 3), ("d", 5))
    assert (text, fields) in [
        (d["text"], d["value"].fields) for d in FlexibleTextDateDetector("en_US").detect(text)
    ]
    assert FlexibleShortYearDateDetector("en_US").detect(text) == []


@pytest.mark.parametrize("locale", ["en_US", "en_GB", "de_DE"])
def test_short_year_is_exactly_what_the_text_date_reader_withholds(locale):
    text = (
        "On 5 June 200 attendees came; 24 April 350 and May 5, 20; in June 200 cases, "
        "3. Mai 99 und Mai 812; 5 June 2020, June 2021, 5 March 44 BC, Tuesday, 2 May 13"
    )
    dates = FlexibleTextDateDetector(locale)
    short = FlexibleShortYearDateDetector(locale)

    def widened(text, start):
        return dates._match(text, start, year_widths=frozenset({2, 3, 4}))

    unguarded = {
        (d["start"], d["end"], d["value"])
        for d in _detect_flexible(text, locale, dates.type, None, widened)
    }
    kept = {(d["start"], d["end"], d["value"]) for d in dates.detect(text)}
    refused = {(d["start"], d["end"], d["value"]) for d in short.detect(text)}
    assert refused, "the text must exercise the year width"
    assert refused == unguarded - kept
    assert not refused & kept


def test_the_readers_built_on_the_text_date_reader_follow_it():
    # A date and time with a short year is no longer read by the date-time reader.
    assert FlexibleDateTimeDetector("en_US").detect("June 5, 99 at 3:00 PM") == []
    assert [
        d["text"] for d in FlexibleDateTimeDetector("en_US").detect("June 5, 1999 at 3:00 PM")
    ] == ["June 5, 1999 at 3:00 PM"]
    # The month-name reader reads the name the text-date reader no longer reads in a date.
    assert [d["text"] for d in FlexibleMonthNameDetector("en_US").detect("in June 200 cases")] == [
        "June"
    ]
    assert FlexibleMonthNameDetector("en_US").detect("in June 2000") == []
    # The bare-hour reader reads a number the text-date reader no longer reads as a year.
    assert [d["text"] for d in FlexibleBareHourDetector("en_GB").detect("5 June 20 people")] == [
        "20"
    ]
    assert FlexibleBareHourDetector("en_GB").detect("5 June 2020 people") == []


def test_the_short_year_value_is_the_year_as_written():
    assert _dated(FlexibleShortYearDateDetector("en_US"), "Mar 3, 07") == [
        ("date:short-year", "Mar 3, 07", (("y", 7), ("M", 3), ("d", 3)))
    ]


def _date_years(locale, text):
    gang = generated_detectors(locale, DEFAULT_FAMILIES)
    return [
        (d["type"], d["text"], dict(d["value"].fields)["y"])
        for d in gang.detect(text)
        if d["type"].startswith("date:") and "y" in dict(d["value"].fields)
    ]


@pytest.mark.parametrize(
    "locale, text",
    [
        ("en_US", "in June 200 cases"),
        ("en_US", "June 5"),
        ("en_US", "August 9"),
        ("en_US", "3/4"),
        ("en_US", "5 June 200 attendees"),
        ("de_DE", "24. April 350"),
        ("th_TH", "3 พฤษภาคม 200"),
    ],
)
def test_the_default_gang_reads_no_count_after_a_month_as_a_year(locale, text):
    assert _date_years(locale, text) == []


def test_the_default_gang_reads_four_digit_and_two_digit_pattern_years():
    # A four-digit "y" year, and the "yy" pattern's two digits, read as before.
    assert ("date:yMMMM", "June 2020", 2020) in _date_years("en_US", "June 2020")
    assert ("date:yyMd", "3/4/24", 2024) in _date_years("en_US", "3/4/24")
    assert ("date:yMMMMd", "24. April 2024", 2024) in _date_years("de_DE", "24. April 2024")
    # A Buddhist-calendar year, th_TH's default, reads in its four digits.
    thai = _date_years("th_TH", "3 พฤษภาคม 2567")
    assert ("date:yMMMMd", "3 พฤษภาคม 2567", 2567) in thai
    assert ("date:yyyyMMMM", "พฤษภาคม 2567", 2567) in thai


def test_the_default_gang_reads_the_month_year_inside_a_numeric_date():
    # With "3/4" no longer read as the year 4, "M/y" reads "4/2024" inside "3/4/2024".
    assert _date_years("en_US", "3/4/2024") == [
        ("date:yMd", "3/4/2024", 2024),
        ("date:yM", "4/2024", 2024),
    ]


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
