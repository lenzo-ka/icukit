"""Day-month dates, dotted months, era years, and measures in the spellings ICU equates."""

import pytest

from icukit.recognize import (
    FlexibleMeasureDetector,
    FlexibleMixedMeasureDetector,
    FlexiblePercentDetector,
    FlexibleTextDateDetector,
    _language_era_orders,
    _language_eras,
    _language_percent_words,
    _lexicon_month_abbreviations,
    _plural_samples,
    _unit_surface_variants,
)


def _dates(text, locale="en_US"):
    return [(d["text"], d["value"].fields) for d in FlexibleTextDateDetector(locale).detect(text)]


@pytest.mark.parametrize(
    "text, surface, fields",
    [
        ("on 1 July we", "1 July", (("M", 7), ("d", 1))),
        ("1 January ", "1 January", (("M", 1), ("d", 1))),
        ("Oct 1", "Oct 1", (("M", 10), ("d", 1))),
    ],
)
def test_a_day_and_month_without_a_year_read_through_the_language(text, surface, fields):
    # en_US's own patterns put the month first; en_GB's "d MMMM" reaches en_US too.
    assert _dates(text) == [(surface, fields)]


def test_an_impossible_day_and_month_does_not_read():
    assert _dates("31 February") == []


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Oct. 2006", (("y", 2006), ("M", 10))),
        ("Jan. 1", (("M", 1), ("d", 1))),
        ("23 Oct. 2014", (("y", 2014), ("M", 10), ("d", 23))),
    ],
)
def test_an_abbreviated_month_takes_the_period_the_lexicon_gives_it(text, fields):
    assert _dates(text) == [(text, fields)]


def test_the_dotted_months_are_the_lexicons_month_entries():
    assert {"Jan.", "Oct.", "Sept."} <= _lexicon_month_abbreviations("en_US")


@pytest.mark.parametrize(
    "text, surface, fields",
    [
        ("in 500 BC it", "500 BC", (("G", 0), ("y", 500))),
        ("2000 AD", "2000 AD", (("G", 1), ("y", 2000))),
    ],
)
def test_a_year_beside_an_era_reads_with_the_era(text, surface, fields):
    assert _dates(text) == [(surface, fields)]


@pytest.mark.parametrize("text", ["BCD 500", "0 AD", "12345 BC", "abc500 BC"])
def test_no_era_year_without_a_whole_year_and_era(text):
    assert _dates(text) == []


def test_the_eras_are_cldrs():
    assert dict(_language_eras("en")) == {"BC": 0, "AD": 1}


def _measures(unit, text, locale="en_US"):
    return [
        (d["text"], d["value"].decimal, d["value"].unit)
        for d in FlexibleMeasureDetector(locale, unit).detect(text)
    ]


@pytest.mark.parametrize(
    "unit, text, value, value_unit",
    [
        ("square-kilometer", "16 km2", "16", "square-kilometer"),
        ("square-kilometer", "5 square kilometers", "5", "square-kilometer"),
        ("square-meter", "40,000 m2", "40000", "square-meter"),
        ("inch", '12"', "12", "inch"),
        ("foot", "5'", "5", "foot"),
        ("kilometer", "12 kilometers", "12", "kilometer"),
        ("square-kilometer", "1.0/km²", "1.0", "per-square-kilometer"),
        ("square-kilometer", "154.4/km2", "154.4", "per-square-kilometer"),
        ("square-kilometer", "3 per square kilometer", "3", "per-square-kilometer"),
    ],
)
def test_a_measure_reads_in_the_forms_icu_formats_and_equates(unit, text, value, value_unit):
    assert _measures(unit, text) == [(text, value, value_unit)]


def test_a_unit_surface_must_end_its_word():
    assert _measures("square-kilometer", "12 km2x") == []


def test_unit_variants_are_nfkc_and_ascii_confusables_of_marks():
    assert set(_unit_surface_variants("km²")) == {"km²", "km2"}
    assert '"' in _unit_surface_variants("″")
    assert "'" in _unit_surface_variants("′")


@pytest.mark.parametrize(
    "text, ratio", [("5 percent", "0.05"), ("2.5 percent of", "0.025"), ("5%", "0.05")]
)
def test_percent_reads_as_the_symbol_or_icus_wide_word(text, ratio):
    detections = FlexiblePercentDetector("en_US").detect(text)

    assert [d["value"].decimal for d in detections] == [ratio]


@pytest.mark.parametrize("text", ["5percent", "5 percentage"])
def test_the_percent_word_needs_a_space_and_a_word_end(text):
    assert FlexiblePercentDetector("en_US").detect(text) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Issue 3 May 5, 2020",
            [("3 May", (("M", 5), ("d", 3))), ("May 5, 2020", (("y", 2020), ("M", 5), ("d", 5)))],
        ),
        (
            "from 10 March 3 people left",
            [("10 March", (("M", 3), ("d", 10))), ("March 3", (("M", 3), ("d", 3)))],
        ),
    ],
)
def test_a_day_month_reading_does_not_take_a_later_date_away(text, expected):
    assert _dates(text) == expected


@pytest.mark.parametrize("text", ["Vancouver, BC 2010", "Photo by AD 2019", "AD 2000"])
def test_an_era_reads_only_in_the_order_cldr_writes_for_the_language(text):
    assert _dates(text) == []


def test_english_writes_the_year_before_the_era():
    assert _language_era_orders("en") == (True, False)


def test_an_era_year_is_gregorian_whatever_the_locale_calendar():
    detection = FlexibleTextDateDetector("th_TH").detect("ค.ศ. 2024")[0]

    assert detection["value"].calendar == "gregorian"
    assert detection["value"].fields == (("G", 1), ("y", 2024))


@pytest.mark.parametrize(
    "text, fields",
    [("Sept. 5", (("M", 9), ("d", 5))), ("OCT. 5", (("M", 10), ("d", 5)))],
)
def test_a_dotted_month_reads_in_any_case_and_in_the_lexicons_own_form(text, fields):
    assert _dates(text) == [(text, fields)]


def test_twelve_apostrophes_as_inches():
    assert _measures("inch", "12'' long") == [("12''", "12", "inch")]


@pytest.mark.parametrize(
    "locale, unit, text, value",
    [
        ("ru", "kilometer", "2 километра", "2"),
        ("ru", "kilometer", "1,5 километра", "1.5"),
        ("pl", "kilometer", "2 kilometry", "2"),
    ],
)
def test_a_unit_reads_in_every_plural_category_icu_gives_the_locale(locale, unit, text, value):
    assert _measures(unit, text, locale) == [(text, value, unit)]


def test_plural_samples_reach_every_category():
    assert len(_plural_samples("ru")) == 4


@pytest.mark.parametrize("locale, text", [("en_US", "5 per cent"), ("en_GB", "6 percent")])
def test_the_percent_word_is_any_the_language_writes(locale, text):
    assert [d["text"] for d in FlexiblePercentDetector(locale).detect(text)] == [text]
    assert {"percent", "per cent"} <= set(_language_percent_words("en"))


@pytest.mark.parametrize(
    "unit, text, surface, total, small",
    [
        ("foot-and-inch", "he is 5'10\" tall", "5'10\"", "70", "inch"),
        ("foot-and-inch", "5′ 10″", "5′ 10″", "70", "inch"),
        ("foot-and-inch", "5 ft, 10 in", "5 ft, 10 in", "70", "inch"),
        ("foot-and-inch", "5 feet, 10 inches", "5 feet, 10 inches", "70", "inch"),
        ("pound-and-ounce", "a 7 lb, 8 oz baby", "7 lb, 8 oz", "120", "ounce"),
    ],
)
def test_a_mixed_unit_reads_whole_as_its_smallest_component(unit, text, surface, total, small):
    detections = FlexibleMixedMeasureDetector("en_US", unit).detect(text)

    assert [(d["text"], d["value"].decimal, d["value"].unit) for d in detections] == [
        (surface, total, small)
    ]


@pytest.mark.parametrize("text", ["5'10", "5'x"])
def test_a_mixed_unit_needs_both_components(text):
    assert FlexibleMixedMeasureDetector("en_US", "foot-and-inch").detect(text) == []
