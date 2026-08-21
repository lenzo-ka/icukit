"""Flexible, CLDR-derived recognizers for non-canonical value surfaces.

Recognizers are the recall-oriented counterpart to the strict detectors in
:mod:`icukit.detectors`. They deposit structurally valid candidates without requiring the
surface to equal ICU's canonical formatting; the existing resolver can then select among
those candidates unchanged.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from math import gcd

import icu

from .breaker import break_grapheme_spans
from .detectors import (
    Capture,
    DateFormatSpec,
    DateTimeValue,
    MeasureFormatSpec,
    MeasureValue,
    NumberFormatSpec,
    NumberValue,
    ValueDetection,
)

__all__ = [
    "FlexibleCurrencyDetector",
    "FlexibleDateDetector",
    "FlexibleFractionDetector",
    "FlexibleMeasureDetector",
    "FlexibleNumberDetector",
    "FlexibleOrdinalDetector",
    "FlexiblePercentDetector",
    "FlexibleTimeDetector",
]

_SPACES = {" ", "\N{NO-BREAK SPACE}", "\N{NARROW NO-BREAK SPACE}"}
_SLASHES = {"/", "\N{FRACTION SLASH}"}


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
        self._calendar = icu.Calendar.createInstance(icu_locale).getType()

        number_format = icu.NumberFormat.createInstance(icu_locale)
        symbols = number_format.getDecimalFormatSymbols()
        zero = symbols.getSymbol(icu.DecimalFormatSymbols.kZeroDigitSymbol)
        self._digits = {chr(ord(zero) + offset): offset for offset in range(10)}
        self._spec = DateFormatSpec(locale, "yMd", self.pattern, self._calendar)

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

        calendar = icu.Calendar.createInstance(icu.Locale(self.locale))
        calendar.setLenient(False)
        calendar.clear()
        try:
            calendar.set(values["y"], values["M"] - 1, values["d"])
            calendar.getTime()
        except icu.ICUError:
            return None

        ordered = tuple((field, values[field]) for field in ("y", "M", "d"))
        return cursor, tuple(captures), DateTimeValue(ordered, self._calendar)

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
        self._primary_grouping = 0
        self._secondary_grouping = 0
        if self._nf.isGroupingUsed():
            primary = self._nf.getGroupingSize()
            secondary = self._nf.getSecondaryGroupingSize()
            self._primary_grouping = primary
            self._secondary_grouping = secondary or primary
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
        while cursor < len(text) and text[cursor] in self._digits:
            cursor += 1
        ungrouped_end = cursor
        groups = [cursor - integer_start]
        separators: list[int] = []
        while self._primary_grouping and text.startswith(self._grouping, cursor):
            grouping_start = cursor
            cursor += len(self._grouping)
            group_start = cursor
            while cursor < len(text) and text[cursor] in self._digits:
                cursor += 1
            if cursor == group_start:
                cursor = grouping_start
                break
            separators.append(grouping_start)
            groups.append(cursor - group_start)

        if separators:
            valid = groups[-1] == self._primary_grouping
            valid = valid and all(size == self._secondary_grouping for size in groups[1:-1])
            valid = valid and 1 <= groups[0] <= self._secondary_grouping
            if not valid:
                cursor = ungrouped_end

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


class FlexiblePercentDetector:
    """Recognize flexible numbers adjacent to the locale's percent symbol."""

    group = "number"
    type = "number:percent"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._number = FlexibleNumberDetector(locale)
        number_format = icu.NumberFormat.createPercentInstance(icu.Locale(locale))
        symbols = number_format.getDecimalFormatSymbols()
        self._percent = symbols.getSymbol(icu.DecimalFormatSymbols.kPercentSymbol)
        pattern = number_format.toPattern()
        number_index = min(
            (pattern.index(character) for character in "#0@" if character in pattern),
            default=0,
        )
        self._prefix_first = pattern.find("%") < number_index
        self._spec = NumberFormatSpec(locale, "percent")

    @staticmethod
    def _space(text: str, cursor: int) -> int:
        if cursor < len(text) and text[cursor] in _SPACES:
            return cursor + 1
        return cursor

    def _suffix_match(
        self, text: str, start: int
    ) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        match = self._number._match(text, start)
        if match is None:
            return None
        cursor, captures, value = match
        cursor = self._space(text, cursor)
        if not text.startswith(self._percent, cursor):
            return None
        end = cursor + len(self._percent)
        percent = Capture("percent", cursor, end, self._percent, None, "symbol")
        ratio = str(Decimal(value.decimal) / 100)
        all_captures = tuple(sorted((*captures, percent), key=lambda capture: capture.start))
        return end, all_captures, NumberValue(ratio)

    def _prefix_match(
        self, text: str, start: int
    ) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        if not text.startswith(self._percent, start):
            return None
        symbol_end = start + len(self._percent)
        match = self._number._match(text, self._space(text, symbol_end))
        if match is None:
            return None
        end, captures, value = match
        percent = Capture("percent", start, symbol_end, self._percent, None, "symbol")
        ratio = str(Decimal(value.decimal) / 100)
        return end, (percent, *captures), NumberValue(ratio)

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        matchers = (
            (self._prefix_match, self._suffix_match)
            if self._prefix_first
            else (self._suffix_match, self._prefix_match)
        )
        for matcher in matchers:
            match = matcher(text, start)
            if match is not None:
                return match
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible percent candidates in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleCurrencyDetector:
    """Recognize a locale currency symbol before or after a flexible number."""

    group = "number"

    def __init__(self, locale: str, currency: str) -> None:
        self.locale = locale
        self.currency = currency
        self.type = f"number:currency:{currency}"
        self._number = FlexibleNumberDetector(locale)
        number_format = icu.NumberFormat.createCurrencyInstance(icu.Locale(locale))
        number_format.setCurrency(currency)
        symbols = number_format.getDecimalFormatSymbols()
        self._currency = symbols.getSymbol(icu.DecimalFormatSymbols.kCurrencySymbol)
        self._spec = NumberFormatSpec(locale, "currency", currency=currency)

    @staticmethod
    def _space(text: str, cursor: int) -> int:
        if cursor < len(text) and text[cursor] in _SPACES:
            return cursor + 1
        return cursor

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        if text.startswith(self._currency, start):
            symbol_end = start + len(self._currency)
            number_start = self._space(text, symbol_end)
            match = self._number._match(text, number_start)
            if match is not None:
                end, captures, value = match
                currency = Capture("currency", start, symbol_end, self._currency, None, "symbol")
                return end, (currency, *captures), NumberValue(value.decimal, self.currency)

        match = self._number._match(text, start)
        if match is None:
            return None
        number_end, captures, value = match
        symbol_start = self._space(text, number_end)
        if not text.startswith(self._currency, symbol_start):
            return None
        end = symbol_start + len(self._currency)
        currency = Capture("currency", symbol_start, end, self._currency, None, "symbol")
        return end, (*captures, currency), NumberValue(value.decimal, self.currency)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible currency candidates in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleMeasureDetector:
    """Recognize a flexible number followed by a reflectively derived ICU unit surface."""

    group = "measure"

    def __init__(self, locale: str, unit: str) -> None:
        self.locale = locale
        self.unit = unit
        self.type = f"measure:{unit}"
        self._number = FlexibleNumberDetector(locale)

        measure_unit = icu.MeasureUnit.forIdentifier(unit)
        if measure_unit.getIdentifier() != unit:
            raise ValueError(f"unit is not a canonical ICU identifier: {unit!r}")

        icu_locale = icu.Locale(locale)
        number_surface = icu.NumberFormat.createInstance(icu_locale).format(1)
        surfaces: list[tuple[str, str, bool]] = []
        for width, width_name in (
            (icu.UMeasureFormatWidth.SHORT, "short"),
            (icu.UMeasureFormatWidth.NARROW, "narrow"),
        ):
            formatter = icu.MeasureFormat(icu_locale, width)
            formatted = formatter.formatMeasure(icu.Measure(1, measure_unit))
            number_start = formatted.find(number_surface)
            if number_start < 0:
                continue
            number_end = number_start + len(number_surface)
            prefix = formatted[:number_start].strip()
            raw_suffix = formatted[number_end:]
            suffix = raw_suffix.strip()
            if prefix or not suffix:
                continue
            candidate = (suffix, width_name, raw_suffix != raw_suffix.lstrip())
            if candidate not in surfaces:
                surfaces.append(candidate)
        if not surfaces:
            raise ValueError(f"ICU exposes no supported suffix surface for unit: {unit!r}")
        self._units = tuple(surfaces)

    @staticmethod
    def _space(text: str, cursor: int) -> int:
        if cursor < len(text) and text[cursor] in _SPACES:
            return cursor + 1
        return cursor

    @staticmethod
    def _continues_word(text: str, cursor: int) -> bool:
        if cursor >= len(text):
            return False
        character = text[cursor]
        category = icu.Char.charType(character)
        return icu.Char.isalnum(character) or category in {
            icu.UCharCategory.NON_SPACING_MARK,
            icu.UCharCategory.COMBINING_SPACING_MARK,
            icu.UCharCategory.ENCLOSING_MARK,
            icu.UCharCategory.CONNECTOR_PUNCTUATION,
        }

    def _match(self, text: str, start: int):
        match = self._number._match(text, start)
        if match is None:
            return None
        number_end, captures, value = match
        unit_start = self._space(text, number_end)
        has_space = unit_start != number_end
        ordered_units = sorted(self._units, key=lambda item: item[2] != has_space)
        for surface, width, _expects_space in ordered_units:
            if not text.startswith(surface, unit_start):
                continue
            end = unit_start + len(surface)
            if self._continues_word(text, end):
                continue
            unit_capture = Capture("unit", unit_start, end, surface, self.unit, "symbol")
            spec = MeasureFormatSpec(self.locale, self.unit, width)
            return end, (*captures, unit_capture), MeasureValue(value.decimal, self.unit), spec
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible measure candidates in source order."""
        starts = sorted({span["start"] for span in break_grapheme_spans(text, self.locale)})
        detections: list[ValueDetection] = []
        cursor = 0
        for start in starts:
            if start < cursor:
                continue
            result = self._match(text, start)
            if result is None:
                continue
            end, captures, value, spec = result
            detections.append(
                ValueDetection(
                    text=text[start:end],
                    start=start,
                    end=end,
                    type=self.type,
                    value=value,
                    captures=captures,
                    spec=spec,
                )
            )
            cursor = end
        return detections


class FlexibleTimeDetector:
    """Recognize clock times using a locale's CLDR short-time structure.

    The ``time:flexible`` type marks recall candidates for hours:minutes, an optional
    ``:seconds``, and an optional day period (am/pm). Both are reflective: the time
    separator and 12- vs 24-hour convention come from the locale's short-time pattern
    (``icu.DateFormat.createTimeInstance(kShort)``), and the day-period strings come from
    ``icu.DateFormatSymbols.getAmPmStrings`` -- nothing is hard-coded per locale.

    A bare hour is read directly as a 24-hour ``H`` (so ``15:45`` is recognized in a
    12-hour locale); a day period is only consumed when the hour reads 1-12, and the
    reading is then converted to 24-hour ``H`` (12 AM -> 0, 12 PM -> 12). Minutes and
    seconds are exactly two digits in 0-59.
    """

    group = "time"
    type = "time:flexible"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        icu_locale = icu.Locale(locale)
        time_format = icu.DateFormat.createTimeInstance(icu.DateFormat.kShort, icu_locale)
        self.pattern = time_format.toPattern()
        self._separator, self.hour12 = self._time_structure(self.pattern)
        self._periods = tuple(icu.DateFormatSymbols(icu_locale).getAmPmStrings())

        number_format = icu.NumberFormat.createInstance(icu_locale)
        symbols = number_format.getDecimalFormatSymbols()
        zero = symbols.getSymbol(icu.DecimalFormatSymbols.kZeroDigitSymbol)
        self._digits = {chr(ord(zero) + offset): offset for offset in range(10)}
        self._spec = DateFormatSpec(locale, "Hms", self.pattern, "gregorian")

    @staticmethod
    def _time_structure(pattern: str) -> tuple[str, bool]:
        hour_letters = {"h", "H", "k", "K"}
        separator: list[str] = []
        hour12 = False
        seen_hour = False
        found = False
        quoted = False
        cursor = 0
        while cursor < len(pattern):
            character = pattern[cursor]
            if character == "'":
                if cursor + 1 < len(pattern) and pattern[cursor + 1] == "'":
                    if seen_hour:
                        separator.append("'")
                    cursor += 2
                    continue
                quoted = not quoted
                cursor += 1
                continue
            if not quoted and character in hour_letters:
                hour12 = character in {"h", "K"}
                seen_hour = True
                separator.clear()
                cursor += 1
                while cursor < len(pattern) and pattern[cursor] == character:
                    cursor += 1
                continue
            if not quoted and character == "m" and seen_hour:
                found = True
                break
            if seen_hour:
                separator.append(character)
            cursor += 1
        joined = "".join(separator)
        if not found or not joined:
            raise ValueError(f"unsupported short time pattern: {pattern!r}")
        return joined, hour12

    def _digit_run(self, text: str, start: int) -> tuple[int, int]:
        cursor = start
        value = 0
        while cursor < len(text) and text[cursor] in self._digits:
            value = value * 10 + self._digits[text[cursor]]
            cursor += 1
        return cursor, value

    def _field(self, text: str, start: int, width: int) -> tuple[int, int] | None:
        cursor, value = self._digit_run(text, start)
        if cursor - start != width:
            return None
        return cursor, value

    def _day_period(self, text: str, cursor: int) -> tuple[int, str, int] | None:
        marker_start = cursor
        if cursor < len(text) and text[cursor] in _SPACES:
            cursor += 1
        for index, period in enumerate(self._periods):
            if period and text[cursor : cursor + len(period)].casefold() == period.casefold():
                return cursor + len(period), text[marker_start : cursor + len(period)], index
        return None

    def _match(
        self, text: str, start: int
    ) -> tuple[int, tuple[Capture, ...], DateTimeValue] | None:
        if start > 0 and text[start - 1] in self._digits:
            return None
        first = self._digit_run(text, start)
        hour_width = first[0] - start
        if hour_width not in {1, 2}:
            return None
        cursor, raw_hour = first
        captures: list[Capture] = []

        if not text.startswith(self._separator, cursor):
            return None
        minute = self._field(text, cursor + len(self._separator), 2)
        if minute is None or not 0 <= minute[1] <= 59:
            return None
        minute_end, minute_value = minute

        second_value: int | None = None
        second_end = minute_end
        if text.startswith(self._separator, minute_end):
            second = self._field(text, minute_end + len(self._separator), 2)
            if second is not None and 0 <= second[1] <= 59:
                second_end, second_value = second
            elif self._digit_run(text, minute_end + len(self._separator))[0] > (
                minute_end + len(self._separator)
            ):
                return None

        cursor = second_end
        period_index: int | None = None
        if 1 <= raw_hour <= 12:
            found = self._day_period(text, cursor)
            if found is not None:
                marker_end, marker_text, period_index = found
                captures.append(
                    Capture("day-period", cursor, marker_end, marker_text, None, "symbol")
                )
                cursor = marker_end
        elif self._day_period(text, cursor) is not None:
            return None

        continuation = cursor + len(self._separator)
        if text.startswith(self._separator, cursor) and self._digit_run(text, continuation)[0] > (
            continuation
        ):
            return None

        if period_index is None:
            if not 0 <= raw_hour <= 23:
                return None
            hour24 = raw_hour
        else:
            hour24 = (0 if raw_hour == 12 else raw_hour) + (12 if period_index == 1 else 0)

        fields: list[tuple[str, int]] = [("H", hour24), ("m", minute_value)]
        hour_capture = Capture(
            "H", start, start + hour_width, text[start : start + hour_width], raw_hour, "numeric"
        )
        minute_capture = Capture(
            "m",
            minute_end - 2,
            minute_end,
            text[minute_end - 2 : minute_end],
            minute_value,
            "numeric",
        )
        ordered = [hour_capture, minute_capture]
        if second_value is not None:
            fields.append(("s", second_value))
            ordered.append(
                Capture(
                    "s",
                    second_end - 2,
                    second_end,
                    text[second_end - 2 : second_end],
                    second_value,
                    "numeric",
                )
            )
        ordered.extend(captures)
        value = DateTimeValue(tuple(fields), "gregorian")
        return cursor, tuple(ordered), value

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible clock times in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleFractionDetector:
    """Recognize ``N/D`` fractions, optionally with a leading whole part ``W N/D``.

    The ``fraction:flexible`` type marks recall candidates. Locale digits are reflective;
    the fraction slash is the mathematical solidus (``/`` or U+2044), not locale data.
    The value is a :class:`NumberValue` whose ``decimal`` is computed with ``Decimal``:
    a terminating fraction is exact (``1/2`` -> ``"0.5"``, ``3 1/2`` -> ``"3.5"``); a
    non-terminating one is quantized to twelve fractional digits (``1/3`` ->
    ``"0.333333333333"``). A zero denominator is rejected.
    """

    group = "fraction"
    type = "fraction:flexible"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        number_format = icu.NumberFormat.createInstance(icu.Locale(locale))
        symbols = number_format.getDecimalFormatSymbols()
        zero = symbols.getSymbol(icu.DecimalFormatSymbols.kZeroDigitSymbol)
        self._zero = ord(zero)
        self._digits = {chr(self._zero + offset): offset for offset in range(10)}
        self._spec = NumberFormatSpec(locale, "decimal")

    def _digit_run(self, text: str, start: int) -> int:
        cursor = start
        while cursor < len(text) and text[cursor] in self._digits:
            cursor += 1
        return cursor

    def _ascii(self, surface: str) -> str:
        return "".join(str(self._digits[character]) for character in surface)

    @staticmethod
    def _canonical(whole: int, numerator: int, denominator: int) -> str:
        top = whole * denominator + numerator
        divisor = gcd(top, denominator)
        top //= divisor
        bottom = denominator // divisor
        residue = bottom
        for prime in (2, 5):
            while residue % prime == 0:
                residue //= prime
        if residue == 1:
            result = Decimal(top) / Decimal(bottom)
        else:
            with localcontext() as context:
                context.prec = 40
                result = (Decimal(top) / Decimal(bottom)).quantize(Decimal("1.000000000000"))
        rendered = format(result, "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        if start > 0 and (text[start - 1] in self._digits or text[start - 1] in _SLASHES):
            return None
        first_end = self._digit_run(text, start)
        if first_end == start:
            return None

        whole_capture: Capture | None = None
        whole_value = 0
        numerator_start, numerator_end = start, first_end
        cursor = first_end
        if cursor < len(text) and text[cursor] in _SPACES:
            after_space = cursor + 1
            candidate_end = self._digit_run(text, after_space)
            if (
                candidate_end > after_space
                and text[candidate_end : candidate_end + 1]
                and (text[candidate_end] in _SLASHES)
            ):
                whole_surface = text[start:first_end]
                whole_value = int(self._ascii(whole_surface))
                whole_capture = Capture(
                    "whole", start, first_end, whole_surface, self._ascii(whole_surface), "numeric"
                )
                numerator_start, numerator_end = after_space, candidate_end
                cursor = candidate_end

        if cursor >= len(text) or text[cursor] not in _SLASHES:
            return None
        cursor += 1
        denominator_start = cursor
        denominator_end = self._digit_run(text, cursor)
        if denominator_end == denominator_start:
            return None
        chained_start = denominator_end + 1
        if (
            denominator_end < len(text)
            and text[denominator_end] in _SLASHES
            and self._digit_run(text, chained_start) > chained_start
        ):
            return None

        numerator_surface = text[numerator_start:numerator_end]
        denominator_surface = text[denominator_start:denominator_end]
        numerator = int(self._ascii(numerator_surface))
        denominator = int(self._ascii(denominator_surface))
        if denominator == 0:
            return None

        captures: list[Capture] = []
        if whole_capture is not None:
            captures.append(whole_capture)
        captures.append(
            Capture(
                "numerator",
                numerator_start,
                numerator_end,
                numerator_surface,
                self._ascii(numerator_surface),
                "numeric",
            )
        )
        captures.append(
            Capture(
                "denominator",
                denominator_start,
                denominator_end,
                denominator_surface,
                self._ascii(denominator_surface),
                "numeric",
            )
        )
        decimal = self._canonical(whole_value, numerator, denominator)
        return denominator_end, tuple(captures), NumberValue(decimal=decimal, currency=None)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible fractions in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleOrdinalDetector:
    """Recognize ordinal numerals (``1st``, ``第21``) using reflective CLDR affixes.

    The ``ordinal:flexible`` type marks recall candidates. The ordinal affix is obtained
    reflectively by *forward* formatting: a candidate integer is rendered with
    ``icu.RuleBasedNumberFormat`` on the ``ORDINAL`` rule set, and the prefix and suffix
    are the non-digit parts around that rendering. No affix is hard-coded, and no fragile
    ordinal *parse* is attempted. A surface is accepted only when its affixes match those
    ICU generates for the parsed value, so ``21th`` is rejected while ``21st`` is not.
    """

    group = "ordinal"
    type = "ordinal:flexible"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        icu_locale = icu.Locale(locale)
        self._rbnf = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, icu_locale)
        number_format = icu.NumberFormat.createInstance(icu_locale)
        symbols = number_format.getDecimalFormatSymbols()
        zero = symbols.getSymbol(icu.DecimalFormatSymbols.kZeroDigitSymbol)
        self._digits = {chr(ord(zero) + offset): offset for offset in range(10)}
        self._spec = NumberFormatSpec(locale, "decimal")

    def _digit_run(self, text: str, start: int) -> tuple[int, int]:
        cursor = start
        value = 0
        while cursor < len(text) and text[cursor] in self._digits:
            value = value * 10 + self._digits[text[cursor]]
            cursor += 1
        return cursor, value

    def _affixes(self, value: int) -> tuple[str, str]:
        rendered = self._rbnf.format(value)
        digit_indexes = [
            index
            for index, character in enumerate(rendered)
            if character in self._digits or character.isdigit()
        ]
        if not digit_indexes:
            return rendered, ""
        return rendered[: digit_indexes[0]], rendered[digit_indexes[-1] + 1 :]

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        for digit_start in range(start, len(text)):
            if text[digit_start] not in self._digits:
                continue
            digit_end, value = self._digit_run(text, digit_start)
            if value < 1:
                continue
            prefix, suffix = self._affixes(value)
            if not prefix and not suffix:
                continue
            if text[start:digit_start].casefold() != prefix.casefold():
                continue
            affix_end = digit_end + len(suffix)
            if text[digit_end:affix_end].casefold() != suffix.casefold():
                continue
            integer_surface = text[digit_start:digit_end]
            captures: list[Capture] = []
            if prefix:
                captures.append(
                    Capture(
                        "ordinal-affix",
                        start,
                        digit_start,
                        text[start:digit_start],
                        None,
                        "symbol",
                    )
                )
            captures.append(
                Capture("integer", digit_start, digit_end, integer_surface, str(value), "numeric")
            )
            if suffix:
                captures.append(
                    Capture(
                        "ordinal-affix",
                        digit_end,
                        affix_end,
                        text[digit_end:affix_end],
                        None,
                        "symbol",
                    )
                )
            return affix_end, tuple(captures), NumberValue(decimal=str(value), currency=None)
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible ordinals in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


def _detect_flexible(text, locale, type_label, spec, match):
    starts = sorted({span["start"] for span in break_grapheme_spans(text, locale)})
    detections: list[ValueDetection] = []
    cursor = 0
    for start in starts:
        if start < cursor:
            continue
        result = match(text, start)
        if result is None:
            continue
        end, captures, value = result
        detections.append(
            ValueDetection(
                text=text[start:end],
                start=start,
                end=end,
                type=type_label,
                value=value,
                captures=captures,
                spec=spec,
            )
        )
        cursor = end
    return detections
