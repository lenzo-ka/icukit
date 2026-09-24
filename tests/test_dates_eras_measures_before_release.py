"""Day-month dates, dotted months, era years, and measures in the spellings ICU equates."""

import pytest

from icukit.recognize import (
    FlexibleMeasureDetector,
    FlexiblePercentDetector,
    FlexibleTextDateDetector,
    _language_eras,
    _lexicon_month_abbreviations,
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
        ("AD 2000", "AD 2000", (("G", 1), ("y", 2000))),
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
