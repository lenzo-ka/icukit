"""Flexible, CLDR-derived recognizers for non-canonical value surfaces.

Recognizers are the recall-oriented counterpart to the strict detectors in
:mod:`icukit.detectors`. They deposit structurally valid candidates without requiring the
surface to equal ICU's canonical formatting; the existing resolver can then select among
those candidates unchanged.
"""

from __future__ import annotations

import icu

from .breaker import break_grapheme_spans
from .detectors import (
    Capture,
    DateFormatSpec,
    DateTimeValue,
    NumberFormatSpec,
    NumberValue,
    ValueDetection,
)

__all__ = ["FlexibleDateDetector", "FlexibleNumberDetector"]


class FlexibleDateDetector:
    """Recognize flexible numeric dates using a locale's CLDR short-date structure.

    The stable ``date:flexible`` type distinguishes recall candidates from strict,
    skeleton-specific date detections. Two-digit years retain their observed value;
    this detector deposits one maximal candidate rather than expanding a century.
    """

    group = "date"
    type = "date:flexible"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        icu_locale = icu.Locale(locale)
        date_format = icu.DateFormat.createDateInstance(icu.DateFormat.kShort, icu_locale)
        self.pattern = date_format.toPattern()
        self._fields, self._separators = self._date_structure(self.pattern)

        number_format = icu.NumberFormat.createInstance(icu_locale)
        symbols = number_format.getDecimalFormatSymbols()
        zero = symbols.getSymbol(icu.DecimalFormatSymbols.kZeroDigitSymbol)
        self._digits = {chr(ord(zero) + offset): offset for offset in range(10)}
        self._spec = DateFormatSpec(locale, "yMd", self.pattern, "gregorian")

    @staticmethod
    def _date_structure(pattern: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        fields: list[str] = []
        literals: list[str] = []
        literal: list[str] = []
        quoted = False
        cursor = 0
        while cursor < len(pattern):
            character = pattern[cursor]
            if character == "'":
                if cursor + 1 < len(pattern) and pattern[cursor + 1] == "'":
                    literal.append("'")
                    cursor += 2
                    continue
                quoted = not quoted
                cursor += 1
                continue
            if not quoted and character in {"y", "M", "L", "d"}:
                if fields:
                    literals.append("".join(literal))
                literal.clear()
                field = "M" if character == "L" else character
                fields.append(field)
                cursor += 1
                while cursor < len(pattern) and pattern[cursor] == character:
                    cursor += 1
                continue
            literal.append(character)
            cursor += 1

        if len(fields) != 3 or set(fields) != {"y", "M", "d"} or len(literals) != 2:
            raise ValueError(f"unsupported short date pattern: {pattern!r}")
        if not all(literals):
            raise ValueError(f"short date pattern has an empty separator: {pattern!r}")
        return tuple(fields), tuple(literals)

    def _digit_run(self, text: str, start: int) -> tuple[int, str, int]:
        cursor = start
        value = 0
        while cursor < len(text) and text[cursor] in self._digits:
            value = value * 10 + self._digits[text[cursor]]
            cursor += 1
        return cursor, text[start:cursor], value

    def _match(
        self, text: str, start: int
    ) -> tuple[int, tuple[Capture, ...], DateTimeValue] | None:
        cursor = start
        values: dict[str, int] = {}
        captures: list[Capture] = []
        for index, field in enumerate(self._fields):
            field_start = cursor
            cursor, surface, value = self._digit_run(text, cursor)
            width = cursor - field_start
            valid_width = width in ({2, 4} if field == "y" else {1, 2})
            valid_range = field == "y" or field == "M" and 1 <= value <= 12
            valid_range = valid_range or field == "d" and 1 <= value <= 31
            if not valid_width or not valid_range:
                return None
            values[field] = value
            captures.append(Capture(field, field_start, cursor, surface, value, "numeric"))
            if index < len(self._separators):
                separator = self._separators[index]
                if not text.startswith(separator, cursor):
                    return None
                cursor += len(separator)

        ordered = tuple((field, values[field]) for field in ("y", "M", "d"))
        return cursor, tuple(captures), DateTimeValue(ordered, "gregorian")

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible numeric dates in source order."""
        starts = sorted({span["start"] for span in break_grapheme_spans(text, self.locale)})
        detections: list[ValueDetection] = []
        cursor = 0
        for start in starts:
            if start < cursor:
                continue
            match = self._match(text, start)
            if match is None:
                continue
            end, captures, value = match
            detections.append(
                ValueDetection(
                    text=text[start:end],
                    start=start,
                    end=end,
                    type=self.type,
                    value=value,
                    captures=captures,
                    spec=self._spec,
                )
            )
            cursor = end
        return detections


class FlexibleNumberDetector:
    """Recognize flexible decimal-number spellings using locale symbols from CLDR."""

    group = "number"
    type = "number:decimal"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._nf = icu.NumberFormat.createInstance(icu.Locale(locale))
        symbols = self._nf.getDecimalFormatSymbols()
        symbol = icu.DecimalFormatSymbols
        self._decimal = symbols.getSymbol(symbol.kDecimalSeparatorSymbol)
        self._grouping = symbols.getSymbol(symbol.kGroupingSeparatorSymbol)
        self._zero = symbols.getSymbol(symbol.kZeroDigitSymbol)
        self._minus = symbols.getSymbol(symbol.kMinusSignSymbol)
        self._plus = symbols.getSymbol(symbol.kPlusSignSymbol)
        zero = ord(self._zero)
        self._digits = {chr(zero + offset): str(offset) for offset in range(10)}

        grouping_sizes = None
        if self._nf.isGroupingUsed():
            primary = self._nf.getGroupingSize()
            secondary = self._nf.getSecondaryGroupingSize()
            grouping_sizes = (secondary, primary) if secondary else (primary,)
        self._spec = NumberFormatSpec(locale, "decimal", grouping_sizes=grouping_sizes)

    def _digits_ascii(self, surface: str) -> str:
        return "".join(
            self._digits[character] for character in surface if character in self._digits
        )

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        cursor = start
        captures: list[Capture] = []
        negative = False

        if text.startswith(self._minus, cursor) or text.startswith(self._plus, cursor):
            sign = self._minus if text.startswith(self._minus, cursor) else self._plus
            sign_end = cursor + len(sign)
            captures.append(Capture("sign", cursor, sign_end, sign, None, "symbol"))
            negative = sign == self._minus
            cursor = sign_end

        integer_start = cursor
        if cursor >= len(text) or text[cursor] not in self._digits:
            return None
        cursor += 1
        while cursor < len(text):
            if text[cursor] in self._digits:
                cursor += 1
                continue
            grouping_end = cursor + len(self._grouping)
            if (
                text.startswith(self._grouping, cursor)
                and grouping_end < len(text)
                and text[grouping_end] in self._digits
            ):
                cursor = grouping_end + 1
                continue
            break

        integer_end = cursor
        integer_text = text[integer_start:integer_end]
        integer_ascii = self._digits_ascii(integer_text)
        captures.append(
            Capture(
                "integer",
                integer_start,
                integer_end,
                integer_text,
                integer_ascii,
                "numeric",
            )
        )

        fraction_ascii = ""
        separator_end = cursor + len(self._decimal)
        if (
            text.startswith(self._decimal, cursor)
            and separator_end < len(text)
            and text[separator_end] in self._digits
        ):
            captures.append(
                Capture(
                    "decimal-separator",
                    cursor,
                    separator_end,
                    self._decimal,
                    None,
                    "symbol",
                )
            )
            fraction_start = separator_end
            cursor = fraction_start + 1
            while cursor < len(text) and text[cursor] in self._digits:
                cursor += 1
            fraction_text = text[fraction_start:cursor]
            fraction_ascii = self._digits_ascii(fraction_text)
            captures.append(
                Capture(
                    "fraction",
                    fraction_start,
                    cursor,
                    fraction_text,
                    fraction_ascii,
                    "numeric",
                )
            )

        decimal = ("-" if negative else "") + integer_ascii
        if fraction_ascii:
            decimal += "." + fraction_ascii
        captures.sort(key=lambda capture: (capture.start, capture.end))
        return cursor, tuple(captures), NumberValue(decimal=decimal, currency=None)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible decimal candidates in source order."""
        starts = sorted({span["start"] for span in break_grapheme_spans(text, self.locale)})
        detections: list[ValueDetection] = []
        cursor = 0
        for start in starts:
            if start < cursor:
                continue
            match = self._match(text, start)
            if match is None:
                continue
            end, captures, value = match
            detections.append(
                ValueDetection(
                    text=text[start:end],
                    start=start,
                    end=end,
                    type=self.type,
                    value=value,
                    captures=captures,
                    spec=self._spec,
                )
            )
            cursor = end
        return detections
