"""Convert offsets at the encoding-unit seam between ICU and Python.

ICU reports offsets in UTF-16 code units, while Python strings use Unicode
code-point indices. This module provides the shared mapping used where values
cross that encoding-unit seam.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import NamedTuple


class OffsetMaps(NamedTuple):
    """Cumulative offsets at every code-point boundary in a text."""

    cp_to_utf8: list[int]
    cp_to_utf16: list[int]
    utf16_to_cp: dict[int, int]


def offset_maps(text: str) -> OffsetMaps:
    """Build UTF-8, UTF-16, and code-point boundary maps in one linear pass."""
    cp_to_utf8 = [0]
    cp_to_utf16 = [0]
    utf16_to_cp = {0: 0}
    utf8_offset = 0
    utf16_offset = 0
    for cp_index, char in enumerate(text, 1):
        utf8_offset += len(char.encode("utf-8"))
        utf16_offset += 2 if ord(char) > 0xFFFF else 1
        cp_to_utf8.append(utf8_offset)
        cp_to_utf16.append(utf16_offset)
        utf16_to_cp[utf16_offset] = cp_index
    return OffsetMaps(cp_to_utf8, cp_to_utf16, utf16_to_cp)


def set_span_offsets(
    span: MutableMapping[str, object],
    start: int,
    end: int,
    maps: OffsetMaps,
) -> None:
    """Set every offset representation for a code-point range on a span."""
    span["start"] = start
    span["end"] = end
    span["codepoint_start"] = start
    span["codepoint_end"] = end
    span["utf8_start"] = maps.cp_to_utf8[start]
    span["utf8_end"] = maps.cp_to_utf8[end]
    span["utf16_start"] = maps.cp_to_utf16[start]
    span["utf16_end"] = maps.cp_to_utf16[end]


def codepoint_map(text: str) -> list[int] | None:
    """Map ICU UTF-16 offsets to Python string code-point indices.

    Args:
        text: The text whose offsets should be mapped.

    Returns:
        A UTF-16-offset-to-code-point-index map, or None when the offsets are
        already identical.
    """
    if all(ord(ch) <= 0xFFFF for ch in text):
        return None

    m = []
    for cp_index, ch in enumerate(text):
        m.append(cp_index)
        if ord(ch) > 0xFFFF:
            m.append(cp_index)
    m.append(len(text))
    return m


def to_codepoint(offmap: list[int] | None, offset: int) -> int:
    """Convert a UTF-16 offset to a Python code-point index.

    Args:
        offmap: The offset map for the text, or None for the identity mapping.
        offset: The UTF-16 code-unit offset to convert.

    Returns:
        The corresponding Python code-point index.
    """
    return offset if offmap is None else offmap[offset]


def boundary_maps(text: str) -> tuple[list[int], dict[int, int]]:
    """Build strict, bidirectional UTF-16 <-> code-point boundary maps.

    Unlike :func:`codepoint_map`, this never aliases the interior of a surrogate
    pair: an offset that falls *inside* an astral character has no code-point
    boundary and is simply absent from the reverse map. This is the map a
    detector needs to translate an ICU parse endpoint back to a code-point index
    while refusing an endpoint that lands mid-character.

    Args:
        text: The text to map.

    Returns:
        A pair ``(cp_to_u16, u16_to_cp)`` where ``cp_to_u16[i]`` is the UTF-16
        offset of code point ``i`` (for ``i`` in ``0..len(text)`` inclusive), and
        ``u16_to_cp`` maps each *genuine* UTF-16 boundary offset to its code-point
        index. Offsets interior to a surrogate pair are not keys of ``u16_to_cp``.
    """
    maps = offset_maps(text)
    return maps.cp_to_utf16, maps.utf16_to_cp


def u16_boundary_to_codepoint(u16_to_cp: dict[int, int], offset: int) -> int | None:
    """Return the code-point index for a UTF-16 boundary, or None if interior.

    Args:
        u16_to_cp: The reverse map from :func:`boundary_maps`.
        offset: A UTF-16 code-unit offset.

    Returns:
        The code-point index when ``offset`` is a genuine code-point boundary,
        otherwise ``None`` (the offset lands inside a surrogate pair).
    """
    return u16_to_cp.get(offset)
