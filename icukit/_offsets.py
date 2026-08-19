"""Convert offsets at the encoding-unit seam between ICU and Python.

ICU reports offsets in UTF-16 code units, while Python strings use Unicode
code-point indices. This module provides the shared mapping used where values
cross that encoding-unit seam.
"""

from __future__ import annotations


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
    cp_to_u16: list[int] = []
    u16_to_cp: dict[int, int] = {}
    unit = 0
    for index, char in enumerate(text):
        cp_to_u16.append(unit)
        u16_to_cp[unit] = index
        unit += 2 if ord(char) > 0xFFFF else 1
    cp_to_u16.append(unit)
    u16_to_cp[unit] = len(text)
    return cp_to_u16, u16_to_cp


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
