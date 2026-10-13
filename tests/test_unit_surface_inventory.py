"""The public unit inventory matches live flexible-reader acceptance."""

from itertools import chain

import pytest

from icukit import UnitSurface, flexible_detectors, is_unit_surface, unit_surface_inventory
from icukit.detectors import DetectorSet
from icukit.recognize import FlexibleMeasureDetector


def _measure_gang(locale, *, locales=None, units=None):
    gang = flexible_detectors(locale, locales=locales, currencies=(), units=units)
    readers = tuple(reader for reader in gang.detectors if type(reader) is FlexibleMeasureDetector)
    return DetectorSet(readers)


def _reader_candidates(gang):
    """Surfaces derived from each reader's own ICU, curated, and punctuation sources."""
    candidates = set()
    for reader in gang.detectors:
        base = reader._units
        internal = set(chain.from_iterable(reader._ordered_period_units.values()))
        for surface, width, _expects_space, target in base:
            candidates.add((surface, target))
            if (surface, width, target) in reader._periodizable_units:
                candidates.add((f"{surface}.", target))
        for surface, _width, _expects_space, target in internal:
            candidates.add((surface, target))
            candidates.add((f"{surface}.", target))
    return candidates


def _batch_readings(gang, contexts):
    separator = "\n—\n"
    text = separator.join(contexts)
    starts = {}
    cursor = 0
    for context in contexts:
        starts[cursor] = context
        cursor += len(context) + len(separator)
    found = set()
    for reading in gang.detect(text):
        context = starts.get(reading["start"])
        if context is None or reading["end"] != reading["start"] + len(context):
            continue
        unit = next((capture for capture in reading["captures"] if capture.name == "unit"), None)
        if unit is not None:
            found.add((context, unit.text, unit.value))
    return found


@pytest.mark.parametrize(
    "locale, locales, units",
    [
        ("en_US", None, None),
        ("en_US", "en_GB", ("foot", "square-foot", "kilogram")),
        ("fr_FR", (), ("meter", "liter", "year")),
        ("ja_JP", (), ("meter", "liter", "year")),
    ],
)
def test_inventory_and_live_reader_acceptance_are_exactly_equal(locale, locales, units):
    inventory = unit_surface_inventory(locale, locales=locales, units=units)
    gang = _measure_gang(locale, locales=locales, units=units)

    preferred_contexts = {f"5{' ' if row.spaced else ''}{row.surface}" for row in inventory}
    preferred_readings = _batch_readings(gang, sorted(preferred_contexts))
    for row in inventory:
        context = f"5{' ' if row.spaced else ''}{row.surface}"
        assert (context, row.surface, row.unit) in preferred_readings

    candidate_contexts = {
        f"5{separator}{surface}"
        for surface, _target in _reader_candidates(gang)
        for separator in ("", " ")
    }
    actual = _batch_readings(gang, sorted(candidate_contexts))
    for context, surface, target in actual:
        matching = [row for row in inventory if (row.surface, row.unit) == (surface, target)]
        assert matching
        assert not context.startswith("5 ") or any(row.spaced for row in matching)


def test_inventory_marks_icu_curated_and_punctuated_sources():
    rows = set(
        unit_surface_inventory("en_US", units=("cubic-centimeter", "foot", "meter", "square-foot"))
    )

    assert UnitSurface("cc", "cubic-centimeter", "curated", True) in rows
    assert UnitSurface("m", "meter", "icu", True) in rows
    assert UnitSurface("ft.", "foot", "punctuated", True) in rows
    assert UnitSurface("sq. ft.", "square-foot", "punctuated", True) in rows


def test_predicate_uses_the_selected_reader_inventory():
    assert is_unit_surface("km", "en_US", units=("kilometer",))
    assert not is_unit_surface("km", "en_US", units=("meter",))


def test_bare_locale_string_is_normalized_like_flexible_detectors():
    bare = unit_surface_inventory("en_US", locales="en_GB", units=("meter",))
    sequence = unit_surface_inventory("en_US", locales=("en_GB",), units=("meter",))

    assert bare == sequence
    assert is_unit_surface("metres", "en_US", locales="en_GB", units=("meter",))


@pytest.mark.parametrize("unit", ["bogus", "meters", "meter-per-second-per-second"])
@pytest.mark.parametrize("function", [unit_surface_inventory, is_unit_surface])
def test_invalid_unit_selection_raises_value_error_with_identifier(unit, function):
    args = ("m", "en_US") if function is is_unit_surface else ("en_US",)
    with pytest.raises(ValueError, match=repr(unit)):
        function(*args, units=(unit,))


def test_empty_and_default_unit_selections_are_distinct():
    assert unit_surface_inventory("en_US", units=()) == ()
    assert unit_surface_inventory("en_US")


def test_mixed_identifiers_are_omitted_because_components_own_the_surfaces():
    assert unit_surface_inventory("en_US", units=("foot-and-inch",)) == ()


def test_detached_quote_and_prime_surfaces_are_marked_attached_only():
    rows = unit_surface_inventory("en_US", locales=(), units=("foot", "inch"))
    marks = [row for row in rows if row.surface in {'"', "'", "″", "′"}]

    assert marks
    assert all(not row.spaced for row in marks)
