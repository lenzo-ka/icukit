"""Curated unit data and the public flexible-reader surface inventory.

ICU and CLDR give the unit forms the measure reader inverts, and
:func:`~icukit.icu_abbreviations` lists. A few forms English writes appear in no
English locale's ICU output ("500cc", "185 lbs", "78 rpm"); this module reads a small,
hand-rolled table (``data/unit_surfaces/<language>.tsv``) mapping each to the ICU unit
it names. Only the mapping is curated: the unit, the value, and the expansions stay
ICU's. The same table names the units ICU composes from an SI prefix that are worth
building ("kilovolt"), since ICU composes any prefix onto any unit and some
compositions are false readings ("cc" is ICU's centicentury), and a few currency
surfaces the currency reader does not take from ICU ("Rs" as the Indian rupee).

The curated-table accessors remain declarative. The public inventory functions lazily
load the reader engine because their contract is the live readers' accepted surfaces,
including reader-derived punctuation and attachment rules.
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

UnitSurfaceSource: TypeAlias = Literal["icu", "curated", "punctuated"]
"""The authority from which a measure-reader surface was derived."""


@dataclass(frozen=True, slots=True)
class UnitSurface:
    """One unit surface accepted by a flexible measure reader.

    ``unit`` is the canonical ICU identifier read from ``surface``. ``source`` is
    ``"icu"`` when ICU formatting and equivalence data produced the surface,
    ``"curated"`` for a row in icukit's small supplemental table, or ``"punctuated"``
    for an English abbreviation spelling accepted by the reader. ``spaced`` says the
    reader accepts whitespace between the number and this surface. Every surface also
    works attached; detached quote and prime forms have ``spaced=False`` because they
    belong to the opt-in guarded reader when separated from the number.
    """

    surface: str
    unit: str
    source: UnitSurfaceSource
    spaced: bool


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
    # Import lazily so the declarative curated accessors remain independent at import
    # time while the public inventory follows the reader's acceptance implementation.
    from .engine import _flexible_measure_detector, _single_units

    selected = _single_units(locale, locales, units)
    rows: dict[UnitSurface, None] = {}
    for unit in selected:
        try:
            reader = _flexible_measure_detector(
                locale,
                unit,
                locales=locales,
                default_selection=units is None,
            )
        except (icu.ICUError, ValueError):
            continue
        for surface, target, source, spaced in reader._accepted_unit_surfaces():
            rows.setdefault(UnitSurface(surface, target, source, spaced))
    return tuple(sorted(rows, key=lambda row: (row.surface, row.unit, row.source, row.spaced)))


def _canonical_units(units: Iterable[str] | None) -> tuple[str, ...] | None:
    """Normalize a unit selection and enforce the public identifier contract."""
    if units is None:
        return None
    selected = tuple(units)
    for unit in selected:
        try:
            canonical = icu.MeasureUnit.forIdentifier(unit).getIdentifier()
        except (icu.ICUError, TypeError):
            canonical = None
        if canonical != unit:
            raise ValueError(f"unit is not a canonical ICU identifier: {unit!r}")
    return selected


def _selections(
    locale: str,
    locales: Iterable[str] | None,
    units: Iterable[str] | None,
) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None]:
    """Normalize selections exactly as the flexible reader gang does."""
    from .recognize import _locale_selection

    return _locale_selection(locale, locales), _canonical_units(units)


def unit_surface_inventory(
    locale: str,
    *,
    locales: Iterable[str] | None = None,
    units: Iterable[str] | None = None,
) -> tuple[UnitSurface, ...]:
    """Return the unit surfaces accepted by flexible measure readers for ``locale``.

    ``units=None`` selects exactly the CLDR-preferred, duration, digital, frequency,
    volt, micrometer, nanometer, and curated composed units selected by
    :func:`~icukit.flexible_detectors`. Passing ``units`` selects the corresponding
    single-unit readers explicitly; ``units=()`` therefore selects none. Mixed-unit
    identifiers are omitted because their component readers use these same surfaces.

    ICU-derived and curated rows come from the constructed
    :class:`~icukit.FlexibleMeasureDetector`, along with its accepted English
    punctuation variants and spacing rules. Detached quote and prime spellings that
    require whitespace are guarded and are not accepted by this inventory. Ambiguous
    spellings of units newly added to the default selection are also guarded in the
    default inventory; an explicit ``units=`` selection reports all spellings its
    directly constructed readers accept.

    Args:
        locale: ICU locale identifier for the readers.
        locales: Optional same-language locale selection, as for ``flexible_detectors``.
        units: Optional ICU unit identifiers, as for ``flexible_detectors``.

    Raises:
        ValueError: If a selected unit identifier is unknown or non-canonical. The
            message includes that identifier.
    """
    locale_selection, unit_selection = _selections(locale, locales, units)
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
    """Whether ``text`` is a unit surface in :func:`unit_surface_inventory`.

    Raises:
        ValueError: If a selected unit identifier is unknown or non-canonical. The
            message includes that identifier.
    """
    locale_selection, unit_selection = _selections(locale, locales, units)
    return text in _unit_surface_texts(locale, locale_selection, unit_selection)
