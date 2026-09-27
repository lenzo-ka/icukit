"""
Unicode's formal name aliases that ICU does not carry ("BEL", "ALERT", "NBSP", "ZWJ").

Unicode gives some characters formal name aliases (``NameAliases.txt`` in the UCD), of
five types: ``correction``, ``control``, ``alternate``, ``figment`` and
``abbreviation``. ICU's name data carries the corrections alone, which
:mod:`icukit.unicode` reads from ICU; this module reads the other four types from a
snapshot of the UCD file (``data/ucd_name_aliases``), made by
``tools/ucd_name_aliases.py`` from the file of ICU's Unicode version, pinned by URL and
checksum, which the snapshot's header records.

Unicode's stability policy never changes or removes a formal name alias once
published, so under an ICU of a later Unicode the snapshot's aliases all still hold,
and only the aliases published since are missing. Under an ICU of an earlier Unicode,
the aliases of code points that ICU does not know as assigned are left out, so that
no alias names a character ICU does not have.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import icu

__all__ = [
    "ALIAS_TYPES",
    "icu_unicode_version",
    "snapshot_unicode_version",
    "ucd_name_aliases",
]

ALIAS_TYPES = ("correction", "control", "alternate", "figment", "abbreviation")
"""The types of formal name alias, in the order ``NameAliases.txt`` defines them."""

_PATH = Path(__file__).parent / "data" / "ucd_name_aliases" / "NameAliases.tsv"


def _version_key(version: str) -> tuple[int, ...]:
    parts = [int(part) for part in version.split(".") if part.isdigit()]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


@cache
def _read() -> tuple[dict[str, str], tuple[tuple[int, str, str], ...]]:
    """The snapshot's header fields and its ``(code point, alias, type)`` rows."""
    if not _PATH.is_file():
        return {}, ()
    header: dict[str, str] = {}
    rows = []
    for line in _PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            name, _tab, value = line[2:].partition("\t")
            if value:
                header[name] = value
        elif line:
            code_point, alias, kind = line.split("\t")
            rows.append((int(code_point, 16), alias, kind))
    return header, tuple(rows)


def snapshot_unicode_version() -> str:
    """The Unicode version of the snapshot's ``NameAliases.txt`` ("17.0.0"); empty
    without a snapshot."""
    return _read()[0].get("unicode-version", "")


def icu_unicode_version() -> str:
    """The Unicode version of ICU's data ("17.0")."""
    return icu.UNICODE_VERSION


@cache
def ucd_name_aliases() -> tuple[tuple[int, str, str], ...]:
    """``(code point, alias, type)`` for each alias in the snapshot, in the file's order.

    The snapshot holds every type but ``correction``, which ICU carries. Under an ICU of
    an earlier Unicode than the snapshot's, the aliases of code points ICU does not know
    as assigned are left out. Empty when the snapshot is missing.
    """
    rows = _read()[1]
    if _version_key(icu_unicode_version()) >= _version_key(snapshot_unicode_version()):
        return rows
    unassigned = icu.UCharCategory.UNASSIGNED
    return tuple(row for row in rows if icu.Char.charType(row[0]) != unassigned)
