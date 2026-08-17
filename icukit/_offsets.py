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
