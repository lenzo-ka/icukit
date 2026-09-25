"""
Curated unit surfaces: the unit forms a language writes that ICU does not.

ICU and CLDR give the unit forms the measure reader inverts, and
:func:`~icukit.icu_abbreviations` lists. A few forms English writes appear in no
English locale's ICU output ("500cc", "185 lbs", "78 rpm"); this module reads a small,
hand-rolled table (``data/unit_surfaces/<language>.tsv``) mapping each to the ICU unit
it names. Only the mapping is curated: the unit, the value, and the expansions stay
ICU's. The same table names the units ICU composes from an SI prefix that are worth
building ("kilovolt"), since ICU composes any prefix onto any unit and some
compositions are false readings ("cc" is ICU's centicentury).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import icu

__all__ = ["curated_composed_units", "curated_unit_surfaces"]

_DATA_DIR = Path(__file__).parent / "data" / "unit_surfaces"


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


def curated_composed_units(language: str) -> tuple[str, ...]:
    """The ICU units composed from an SI prefix that ``language``'s table chooses."""
    return tuple(unit for kind, _surface, unit in _rows(language) if kind == "compose")
