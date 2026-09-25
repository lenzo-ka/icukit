"""Every abbreviation ICU writes, with the expansions ICU gives it."""

import pytest

from icukit import ABBREVIATION_KINDS, IcuAbbreviation, icu_abbreviations


def _find(kind, surface, locale="en_US", **options):
    return [
        row for row in icu_abbreviations(locale, kinds=[kind], **options) if row.surface == surface
    ]


@pytest.mark.parametrize(
    "kind, surface, key, expansion",
    [
        ("unit", "km", "kilometer", "kilometers"),
        ("per-unit", "/km²", "per-square-kilometer", "per square kilometer"),
        ("month", "Sep", "9", "September"),
        ("month", "Sept", "9", "September"),
        ("weekday", "Thu", "5", "Thursday"),
        ("era", "BCE", "0", "Before Common Era"),
        ("time-zone", "EST", "Eastern Standard Time", "Eastern Standard Time"),
        ("currency", "USD", "USD", "US dollars"),
        ("compact", "K", "1e3", "thousand"),
        ("relative-unit", "hr.", "hour", "hours"),
        ("territory", "US", "US", "United States"),
        ("territory", "EU", "EU", "European Union"),
        ("territory", "UN", "UN", "United Nations"),
        ("territory", "UK", "GB", "United Kingdom"),
    ],
)
def test_each_kind_gives_the_surface_its_icu_expansion(kind, surface, key, expansion):
    rows = [row for row in _find(kind, surface) if row.key == key]
    assert rows and expansion in rows[0].expansions


def test_a_surface_with_several_meanings_is_listed_once_per_meaning():
    keys = {(row.kind, row.key) for kind in ABBREVIATION_KINDS for row in _find(kind, "K")}
    assert {("unit", "kelvin"), ("compact", "1e3"), ("currency", "MMK")} <= keys


def test_a_short_form_with_no_longer_one_has_no_expansion():
    assert _find("day-period", "PM")[0].expansions == ()


def test_a_currency_name_carries_no_number_code_or_symbol():
    for row in icu_abbreviations("en_US", kinds=["currency"]):
        for expansion in row.expansions:
            assert row.key not in expansion.split(), row
    names = {row.key: row.expansions for row in icu_abbreviations("en_US", kinds=["currency"])}
    assert "Afghan afghani (1927–2002)" in names["AFA"]


def test_the_choice_of_locales_governs_the_list():
    assert _find("month", "Sept", locales=()) == []


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="unknown abbreviation kinds"):
        icu_abbreviations("en_US", kinds=["stamps"])


def test_rows_are_icu_abbreviations():
    assert all(
        isinstance(row, IcuAbbreviation) for row in icu_abbreviations("en_US", kinds=["era"])
    )


def test_a_territory_carries_cldrs_variant_name_and_numeric_regions_are_not_listed():
    assert _find("territory", "CZ")[0].expansions == ("Czechia", "Czech Republic")
    surfaces = {row.surface for row in icu_abbreviations("en_US", kinds=["territory"])}
    assert "419" not in surfaces and "001" not in surfaces


def test_territory_names_come_from_the_locale():
    assert "Vereinigte Staaten" in _find("territory", "US", locale="de_DE")[0].expansions
