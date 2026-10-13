"""The public unit inventory is the flexible readers' own surface table."""

import pytest

from icukit import UnitSurface, is_unit_surface, unit_surface_inventory
from icukit.recognize import FlexibleMeasureDetector


@pytest.mark.parametrize(
    "locale, units",
    [
        ("en_US", ("meter", "pound", "square-kilometer", "year")),
        ("fr_FR", ("meter", "liter", "year")),
        ("ja_JP", ("meter", "liter", "year")),
    ],
)
def test_inventory_and_reader_tables_are_exactly_equal(locale, units):
    expected = {
        UnitSurface(surface, target, "curated" if width == "curated" else "icu")
        for unit in units
        for surface, width, _spaced, target in FlexibleMeasureDetector(locale, unit)._units
    }

    assert set(unit_surface_inventory(locale, units=units)) == expected


def test_inventory_marks_icu_and_curated_sources():
    rows = set(unit_surface_inventory("en_US", units=("cubic-centimeter", "meter")))

    assert UnitSurface("cc", "cubic-centimeter", "curated") in rows
    assert UnitSurface("m", "meter", "icu") in rows


def test_predicate_uses_the_selected_reader_inventory():
    assert is_unit_surface("km", "en_US", units=("kilometer",))
    assert not is_unit_surface("km", "en_US", units=("meter",))


def test_mixed_identifiers_are_omitted_because_components_own_the_surfaces():
    assert unit_surface_inventory("en_US", units=("foot-and-inch",)) == ()


def test_inventory_is_exported_from_package_root():
    from icukit import UnitSurfaceSource

    source: UnitSurfaceSource = "icu"
    assert source == "icu"
