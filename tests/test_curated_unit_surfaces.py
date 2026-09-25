"""Curated unit surfaces: forms ICU does not write, mapped to ICU units."""

import pytest

from icukit import UnitValue, icu_abbreviations
from icukit.detectors import MeasureValue
from icukit.recognize import FlexibleMeasureDetector
from icukit.unit_surfaces import curated_composed_units, curated_unit_surfaces


def _readings(unit, text):
    return [(d["text"], d["value"]) for d in FlexibleMeasureDetector("en_US", unit).detect(text)]


@pytest.mark.parametrize(
    "unit, text, value",
    [
        ("cubic-centimeter", "500cc", MeasureValue("500", "cubic-centimeter")),
        ("cubic-centimeter", "250 cc", MeasureValue("250", "cubic-centimeter")),
        ("pound", "185 lbs", MeasureValue("185", "pound")),
        ("revolution-per-minute", "78 rpm", MeasureValue("78", "revolution-per-minute")),
        ("kilobyte", "83 KB", MeasureValue("83", "kilobyte")),
        ("square-kilometer", "3 sq km", MeasureValue("3", "square-kilometer")),
        ("square-kilometer", "5 per km²", MeasureValue("5", "per-square-kilometer")),
        ("year", "12/year", MeasureValue("12", "per-year")),
        ("year", "/year", UnitValue("per-year")),
    ],
)
def test_a_curated_surface_reads_as_its_icu_unit(unit, text, value):
    assert _readings(unit, text) == [(text, value)]


def test_no_curated_surface_is_one_icu_already_writes():
    # A surface ICU writes in any English locale is ICU's, not a curation.
    icu_rows = {
        (row.surface, row.key)
        for row in icu_abbreviations("en_US", kinds=["unit", "per-unit"])
        if row.source == "icu"
    }
    assert not set(curated_unit_surfaces("en")) & icu_rows


def test_curated_rows_carry_icus_expansions():
    rows = {
        row.surface: row
        for row in icu_abbreviations("en_US", kinds=["unit", "per-unit"])
        if row.source == "curated"
    }
    assert rows["cc"].expansions[0] == "cubic centimeters"
    assert "revolutions per minute" in rows["rpm"].expansions
    assert rows["/year"].expansions == ("per year",)


def test_the_composed_units_chosen_are_ones_icu_formats():
    for unit in curated_composed_units("en"):
        FlexibleMeasureDetector("en_US", unit)  # raises if ICU cannot format it
    assert "kilovolt" in curated_composed_units("en")


def test_a_language_without_a_table_has_no_curation():
    assert curated_unit_surfaces("xx") == () and curated_composed_units("xx") == ()
