"""
Curated unit surfaces: the unit forms a language writes that ICU does not.

ICU and CLDR give the unit forms the measure reader inverts, and
:func:`~icukit.icu_abbreviations` lists. A few forms English writes appear in no
English locale's ICU output ("500cc", "185 lbs", "78 rpm"); this module reads a small,
hand-rolled table (``data/unit_surfaces/<language>.tsv``) mapping each to the ICU unit
it names. Only the mapping is curated: the unit, the value, and the expansions stay
ICU's. The same table names the units ICU composes from an SI prefix that are worth
building ("kilovolt"), since ICU composes any prefix onto any unit and some
compositions are false readings ("cc" is ICU's centicentury), and a few currency
surfaces the currency reader does not take from ICU ("Rs" as the Indian rupee).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal, TypeAlias

import icu

__all__ = [
    "UnitSurface",
    "UnitSurfaceSource",
    "curated_composed_units",
    "curated_currency_surfaces",
    "curated_unit_surfaces",
    "is_unit_surface",
    "unit_surface_inventory",
]

_DATA_DIR = Path(__file__).parent / "data" / "unit_surfaces"

UnitSurfaceSource: TypeAlias = Literal["icu", "curated"]
"""The authority from which a measure-reader surface was derived."""


@dataclass(frozen=True, slots=True)
class UnitSurface:
    """One unit surface accepted by a flexible measure reader.

    ``unit`` is the canonical ICU identifier read from ``surface``. ``source`` is
    ``"icu"`` when ICU formatting and equivalence data produced the surface, or
    ``"curated"`` for a row in icukit's small supplemental table.
    """

    surface: str
    unit: str
    source: UnitSurfaceSource


@cache
def _rows(language: str) -> tuple[tuple[str, str, str], ...]:
    path = _DATA_DIR / f"{language}.tsv"
    if not path.is_file():
        return ()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        kind, surface, unit, *_note = line.split("\t")
        if kind == "currency":
            if unit not in _currency_codes():
                raise ValueError(f"{path.name}: not an ICU currency code: {unit!r}")
        else:
            target = unit.removeprefix("per-")
            if icu.MeasureUnit.forIdentifier(target).getIdentifier() != target:
                raise ValueError(f"{path.name}: not a canonical ICU unit: {unit!r}")
        rows.append((kind, surface, unit))
    return tuple(rows)


def curated_unit_surfaces(language: str) -> tuple[tuple[str, str], ...]:
    """``(surface, ICU unit)`` for the curated unit surfaces of ``language``.

    A rate's per form maps to ``per-<unit>`` ("per km²": ``per-square-kilometer``).
    Empty for a language with no table.
    """
    return tuple((surface, unit) for kind, surface, unit in _rows(language) if kind == "surface")


@cache
def _currency_codes() -> frozenset[str]:
    return frozenset(unit.getSubtype() for unit in icu.CurrencyUnit.getAvailable("currency"))


def curated_currency_surfaces(language: str) -> tuple[tuple[str, str], ...]:
    """``(surface, ISO 4217 code)`` for the curated currency surfaces of ``language``.

    English: "Rs" and "Rs." as the Indian rupee (what English text means by them), and
    "Rs" as the five rupees ICU itself writes it for (Pakistani, Mauritian, Seychellois,
    Sri Lankan, Nepalese).
    """
    return tuple((surface, code) for kind, surface, code in _rows(language) if kind == "currency")


def curated_composed_units(language: str) -> tuple[str, ...]:
    """The ICU units composed from an SI prefix that ``language``'s table chooses."""
    return tuple(unit for kind, _surface, unit in _rows(language) if kind == "compose")


@cache
def _unit_surface_inventory(
    locale: str,
    locales: tuple[str, ...] | None,
    units: tuple[str, ...] | None,
) -> tuple[UnitSurface, ...]:
    # Import lazily to keep the declarative curated table independent of the reader
    # engine while making the reader's own surface table the sole implementation.
    from .engine import _single_units
    from .recognize import _locale_selection, _measure_surfaces

    selection = _locale_selection(locale, locales)
    selected = _single_units(locale, selection, units)
    rows: dict[UnitSurface, None] = {}
    for unit in selected:
        measure_unit = icu.MeasureUnit.forIdentifier(unit)
        if measure_unit.getIdentifier() != unit:
            raise ValueError(f"unit is not a canonical ICU identifier: {unit!r}")
        per_unit = f"per-{unit}"
        try:
            per_valid = icu.MeasureUnit.forIdentifier(per_unit).getIdentifier() == per_unit
        except icu.ICUError:
            per_valid = False
        surfaces, rates = _measure_surfaces(locale, unit, per_valid, selection)
        for surface, width, _spaced, target in (*surfaces, *rates):
            source: UnitSurfaceSource = "curated" if width == "curated" else "icu"
            rows.setdefault(UnitSurface(surface, target, source))
    return tuple(sorted(rows, key=lambda row: (row.surface, row.unit, row.source)))


def unit_surface_inventory(
    locale: str,
    *,
    locales: Iterable[str] | None = None,
    units: Iterable[str] | None = None,
) -> tuple[UnitSurface, ...]:
    """Return the unit surfaces accepted by flexible measure readers for ``locale``.

    The default ``units`` are exactly the CLDR-preferred, duration, digital, and
    curated composed units selected by :func:`~icukit.flexible_detectors`. Passing
    ``units`` selects the corresponding single-unit readers explicitly. Mixed-unit
    identifiers are omitted because their component readers use these same surfaces.

    ICU-derived and curated rows pass through the same cached surface table used to
    construct :class:`~icukit.FlexibleMeasureDetector`; this function does not maintain
    a parallel spelling list.

    Args:
        locale: ICU locale identifier for the readers.
        locales: Optional same-language locale selection, as for ``flexible_detectors``.
        units: Optional ICU unit identifiers, as for ``flexible_detectors``.
    """
    locale_selection = None if locales is None else tuple(locales)
    unit_selection = None if units is None else tuple(units)
    return _unit_surface_inventory(locale, locale_selection, unit_selection)


@cache
def _unit_surface_texts(
    locale: str,
    locales: tuple[str, ...] | None,
    units: tuple[str, ...] | None,
) -> frozenset[str]:
    return frozenset(row.surface for row in _unit_surface_inventory(locale, locales, units))


def is_unit_surface(
    text: str,
    locale: str,
    *,
    locales: Iterable[str] | None = None,
    units: Iterable[str] | None = None,
) -> bool:
    """Whether ``text`` is a unit surface in :func:`unit_surface_inventory`."""
    locale_selection = None if locales is None else tuple(locales)
    unit_selection = None if units is None else tuple(units)
    return text in _unit_surface_texts(locale, locale_selection, unit_selection)
