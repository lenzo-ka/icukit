"""Convert text boundaries between code-point, UTF-8, and UTF-16 offsets."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Iterable
from typing import Literal, TypeAlias

from ._offsets import offset_maps

__all__ = ["OffsetUnit", "TextOffsets"]

OffsetUnit: TypeAlias = Literal["codepoint", "utf8", "utf16"]
"""A text-offset coordinate system."""

_UNITS = frozenset(("codepoint", "utf8", "utf16"))


class TextOffsets:
    """Convert any number of boundaries in one text using one shared map.

    ``text`` is a read-only property. Offsets must identify boundaries between Unicode
    code points. An offset outside its coordinate system raises :class:`IndexError`; a
    UTF-8 byte offset or UTF-16 code-unit offset inside a character raises
    :class:`ValueError`.

    Python strings containing lone surrogates are supported. Their UTF-8 widths use
    Python's ``surrogatepass`` error handling, so each surrogate occupies three bytes.

    Args:
        text: The text whose boundaries will be converted.

    Raises:
        TypeError: If ``text`` is not a string.
    """

    __slots__ = ("_maps", "_text")

    def __init__(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError(f"text must be a str, not {type(text).__name__}")
        self._text = text
        self._maps = offset_maps(text)

    @property
    def text(self) -> str:
        """The mapped text. This property is read-only."""
        return self._text

    def convert(
        self,
        offsets: Iterable[int],
        *,
        source: OffsetUnit,
        target: OffsetUnit,
    ) -> tuple[int, ...]:
        """Convert boundary ``offsets`` from ``source`` to ``target``.

        The result preserves input order and duplicates. Build one :class:`TextOffsets`
        for a text and reuse it when converting more than one collection of offsets.

        Args:
            offsets: Boundary offsets to convert.
            source: Coordinate system of ``offsets``.
            target: Coordinate system of the returned offsets.

        Returns:
            The corresponding offsets in ``target`` coordinates.
        """
        if source not in _UNITS:
            raise ValueError(f"unknown source offset unit: {source!r}")
        if target not in _UNITS:
            raise ValueError(f"unknown target offset unit: {target!r}")
        return tuple(self._convert(offset, source, target) for offset in offsets)

    def _convert(self, offset: int, source: OffsetUnit, target: OffsetUnit) -> int:
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise TypeError(f"offset must be an int, not {type(offset).__name__}")
        codepoint = self._to_codepoint(offset, source)
        if target == "codepoint":
            return codepoint
        if target == "utf8":
            return self._maps.cp_to_utf8[codepoint]
        return self._maps.cp_to_utf16[codepoint]

    def _to_codepoint(self, offset: int, source: OffsetUnit) -> int:
        if source == "codepoint":
            maximum = len(self.text)
            if not 0 <= offset <= maximum:
                self._raise_out_of_range(offset, source, maximum)
            return offset
        if source == "utf8":
            maximum = self._maps.cp_to_utf8[-1]
            if not 0 <= offset <= maximum:
                self._raise_out_of_range(offset, source, maximum)
            codepoint = bisect_left(self._maps.cp_to_utf8, offset)
            if self._maps.cp_to_utf8[codepoint] != offset:
                raise ValueError(f"{source} offset {offset} is not a code-point boundary")
            return codepoint
        return self._reverse(offset, source, self._maps.utf16_to_cp, self._maps.cp_to_utf16[-1])

    @staticmethod
    def _reverse(
        offset: int,
        source: OffsetUnit,
        reverse: dict[int, int],
        maximum: int,
    ) -> int:
        if not 0 <= offset <= maximum:
            TextOffsets._raise_out_of_range(offset, source, maximum)
        try:
            return reverse[offset]
        except KeyError:
            raise ValueError(f"{source} offset {offset} is not a code-point boundary") from None

    @staticmethod
    def _raise_out_of_range(offset: int, source: OffsetUnit, maximum: int) -> None:
        raise IndexError(f"{source} offset {offset} is outside 0..{maximum}")
