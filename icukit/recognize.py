"""Flexible, CLDR-derived recognizers for non-canonical value surfaces.

Recognizers are the recall-oriented counterpart to the strict detectors in
:mod:`icukit.detectors`. They deposit structurally valid candidates without requiring the
surface to equal ICU's canonical formatting; the existing resolver can then select among
those candidates unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, localcontext
from functools import lru_cache
from math import gcd

import icu

from ._offsets import boundary_maps
from .breaker import break_grapheme_spans
from .detectors import (
    Capture,
    CompactFormatSpec,
    DateFormatSpec,
    DateIntervalSpec,
    DateIntervalValue,
    DateTimeValue,
    MeasureFormatSpec,
    MeasureValue,
    NumberFormatSpec,
    NumberValue,
    RelativeDateSpec,
    RelativeDateValue,
    SpelloutFormatSpec,
    ValueDetection,
    _date_fields,
    _pattern_runs,
)

__all__ = [
    "FlexibleCompactDetector",
    "FlexibleCurrencyDetector",
    "FlexibleCurrencyNameDetector",
    "FlexibleDateDetector",
    "FlexibleDateIntervalDetector",
    "FlexibleFractionDetector",
    "LetterNameDetector",
    "FlexibleMeasureDetector",
    "FlexibleNumberDetector",
    "FlexibleOrdinalDetector",
    "FlexiblePercentDetector",
    "FlexibleRelativeDateDetector",
    "FlexibleScientificDetector",
    "FlexibleSpelloutDetector",
    "FlexibleTimeDetector",
    "FlexibleTextDateDetector",
]

_SPACES = {
    " ",
    "\N{NO-BREAK SPACE}",
    "\N{THIN SPACE}",
    "\N{NARROW NO-BREAK SPACE}",
}
_SLASHES = {"/", "\N{FRACTION SLASH}"}
# Resource bound for expanded scientific decimals; larger canonical strings are not deposited.
_MAX_SCIENTIFIC_CANONICAL_DIGITS = 1000
# Defensive cross-locale bound: ICU RBNF ordinal suffixes are reliable through signed 32-bit.
_MAX_RBNF_ORDINAL_VALUE = 2_147_483_647

# CLDR identifies alphabet repertoires and character categories, but does not carry
# pronunciations for individual letters. English takes the US "zee" variant here.
_LETTER_NAMES = {
    "en": (
        "a",
        "bee",
        "cee",
        "dee",
        "e",
        "ef",
        "gee",
        "aitch",
        "i",
        "jay",
        "kay",
        "el",
        "em",
        "en",
        "o",
        "pee",
        "cue",
        "ar",
        "ess",
        "tee",
        "u",
        "vee",
        "double-u",
        "ex",
        "wye",
        "zee",
    )
}


@dataclass(frozen=True)
class _FlexibleMatch:
    end: int
    captures: tuple[Capture, ...]
    value: object
    spec: object | None = None


def _is_word_character(character: str) -> bool:
    category = icu.Char.charType(character)
    return icu.Char.isalnum(character) or category in {
        icu.UCharCategory.NON_SPACING_MARK,
        icu.UCharCategory.COMBINING_SPACING_MARK,
        icu.UCharCategory.ENCLOSING_MARK,
    }


class LetterNameDetector:
    """Recognize an isolated ASCII Latin letter as its locale's letter name.

    CLDR supplies alphabet repertoires but not the spoken names of their members, so
    supported locales use a small lexical table. Unsupported locale languages produce no
    candidates.
    """

    group = "letter"
    type = "letter:name"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._names = _LETTER_NAMES.get(icu.Locale(locale).getLanguage())

    def detect(self, text: str) -> list[ValueDetection]:
        """Return isolated letter-name candidates in source order."""
        if self._names is None:
            return []
        detections = []
        for start, letter in enumerate(text):
            folded = letter.lower()
            if not "a" <= folded <= "z":
                continue
            if start > 0 and _is_word_character(text[start - 1]):
                continue
            end = start + 1
            if end < len(text) and _is_word_character(text[end]):
                continue
            detections.append(
                ValueDetection(
                    text=letter,
                    start=start,
                    end=end,
                    type=self.type,
                    value=self._names[ord(folded) - ord("a")],
                    captures=(),
                    spec=None,
                )
            )
        return detections


def _locale_digit_map(locale: str | icu.Locale) -> dict[str, int]:
    """Map a locale's ten reflectively formatted digit glyphs to their values."""
    number_format = icu.NumberFormat.createInstance(
        locale if isinstance(locale, icu.Locale) else icu.Locale(locale)
    )
    # Format every value because a numbering system need not occupy a contiguous range.
    digits = [number_format.format(value) for value in range(10)]
    if any(len(digit) != 1 for digit in digits) or len(set(digits)) != 10:
        raise ValueError(f"locale digits must be ten distinct single code points: {digits!r}")
    return {digit: value for value, digit in enumerate(digits)}


@lru_cache(maxsize=1)
def _iso_currency_codes() -> frozenset[str]:
    """The set of currency codes ICU carries, read from its own inventory."""
    return frozenset(unit.getSubtype() for unit in icu.CurrencyUnit.getAvailable("currency"))


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
        structure = self._date_structure(self.pattern)
        self._inert = structure is None
        self._fields, self._separators = structure or ((), ())
        self._calendar = icu.Calendar.createInstance(icu_locale).getType()

        self._digits = _locale_digit_map(icu_locale)
        self._spec = DateFormatSpec(locale, "yMd", self.pattern, self._calendar)

    @staticmethod
    def _date_structure(
        pattern: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
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
            return None
        if not all(literals):
            return None
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
        if self._inert:
            return []
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


_INTERVAL_FIELDS = (
    icu.UCalendarDateFields.ERA,
    icu.UCalendarDateFields.YEAR,
    icu.UCalendarDateFields.MONTH,
    icu.UCalendarDateFields.DATE,
    icu.UCalendarDateFields.AM_PM,
    icu.UCalendarDateFields.HOUR,
    icu.UCalendarDateFields.HOUR_OF_DAY,
    icu.UCalendarDateFields.MINUTE,
    icu.UCalendarDateFields.SECOND,
)
_MODELED_DATE_LETTERS = {"y", "M", "L", "d", "H", "k", "m", "s", "E", "e", "c"}
_INTERVAL_VALUE_ORDER = ("y", "M", "d", "H", "h", "m", "s")


def _interval_pattern_parts(pattern: str) -> tuple[str, str, str] | None:
    """Split an ICU interval pattern where its first field letter repeats."""
    seen: set[str] = set()
    quoted = False
    index = 0
    last_field_end = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "'":
            if index + 1 < len(pattern) and pattern[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
            index += 1
            continue
        if quoted or not character.isascii() or not character.isalpha():
            index += 1
            continue
        end = index + 1
        while end < len(pattern) and pattern[end] == character:
            end += 1
        if character in seen:
            return pattern[:last_field_end], pattern[last_field_end:index], pattern[index:]
        seen.add(character)
        last_field_end = end
        index = end
    return None


def _continues_interval_word(text: str, cursor: int) -> bool:
    if cursor < 0 or cursor >= len(text):
        return False
    character = text[cursor]
    return _is_word_character(character) or (
        icu.Char.charType(character) == icu.UCharCategory.CONNECTOR_PUNCTUATION
    )


def _normalize_interval_surface(surface: str) -> str:
    """Fold the Unicode space variants (``_SPACES``) to a plain space and casefold.

    This normalizes only the *kind* of whitespace, never its presence: a space and no
    space stay distinct, so spacing inside a field (``Jan 1`` vs ``Jan1``) remains
    significant. The range separator's spacing is relaxed elsewhere -- the gate compares
    against a surface carrying the reflective canonical separator, whose non-space core is
    validated by :meth:`_separator_end` -- so this stays a pure whitespace-kind fold.
    """
    return "".join(" " if character in _SPACES else character for character in surface).casefold()


class FlexibleDateIntervalDetector:
    """Recognize date/time interval surfaces by inverting ICU DateIntervalFormat recipes."""

    group = "date-interval"

    def __init__(self, locale: str, skeleton: str) -> None:
        self.locale = locale
        self.skeleton = skeleton
        self.type = f"date-interval:{skeleton}"
        icu_locale = icu.Locale(locale)
        interval_info = icu.DateIntervalInfo(icu_locale)
        matchers = []
        for calendar_field in _INTERVAL_FIELDS:
            pattern = interval_info.getIntervalPattern(skeleton, calendar_field)
            parts = _interval_pattern_parts(pattern) if pattern else None
            if parts is None:
                continue
            part1, separator, part2 = parts
            letters1 = {letter for letter, _ in _pattern_runs(part1)}
            letters2 = {letter for letter, _ in _pattern_runs(part2)}
            if not letters1 <= _MODELED_DATE_LETTERS or not letters2 <= _MODELED_DATE_LETTERS:
                continue
            matchers.append(
                (
                    icu.SimpleDateFormat(part1, icu_locale),
                    separator,
                    icu.SimpleDateFormat(part2, icu_locale),
                    _date_fields(part1),
                    _date_fields(part2),
                )
            )
        self._matchers = tuple(matchers)
        self._calendar = icu.Calendar.createInstance(icu_locale).getType()
        self._spec = DateIntervalSpec(locale, skeleton)
        self._dif = icu.DateIntervalFormat.createInstance(skeleton, icu_locale)
        self._offset_maps: tuple[list[int], dict[int, int]] | None = None

    @property
    def has_patterns(self) -> bool:
        """Whether ICU exposed at least one modeled, splittable interval recipe."""
        return bool(self._matchers)

    def _parse_side(self, formatter, fields, text, start, cp_to_u16, u16_to_cp):
        calendar = icu.Calendar.createInstance(icu.Locale(self.locale))
        calendar.clear()
        position = icu.ParsePosition(cp_to_u16[start])
        formatter.parse(icu.UnicodeString(text), calendar, position)
        end_u16 = position.getIndex()
        if position.getErrorIndex() != -1 or end_u16 <= cp_to_u16[start]:
            return None
        end = u16_to_cp.get(end_u16)
        if end is None:
            return None
        try:
            values = {field.name: calendar.get(field.calendar_field) for field in fields}
        except icu.ICUError:
            return None
        return end, values

    @staticmethod
    def _separator_end(text: str, start: int, separator: str) -> int | None:
        cursor = start
        pattern_cursor = 0
        while pattern_cursor < len(separator):
            if separator[pattern_cursor] in _SPACES:
                while pattern_cursor < len(separator) and separator[pattern_cursor] in _SPACES:
                    pattern_cursor += 1
                while cursor < len(text) and text[cursor] in _SPACES:
                    cursor += 1
                continue
            literal_start = pattern_cursor
            while pattern_cursor < len(separator) and separator[pattern_cursor] not in _SPACES:
                pattern_cursor += 1
            literal = separator[literal_start:pattern_cursor]
            if not text.startswith(literal, cursor):
                return None
            cursor += len(literal)
        return cursor

    def _endpoint(self, values: dict[str, int]) -> DateTimeValue:
        ordered = tuple(
            (name, values[name] + 1 if name == "M" else values[name])
            for name in _INTERVAL_VALUE_ORDER
            if name in values
        )
        return DateTimeValue(ordered, self._calendar)

    def _calendar_from(self, values: dict[str, int]):
        calendar = icu.Calendar.createInstance(icu.Locale(self.locale))
        calendar.clear()
        fields = {field.name: field.calendar_field for field in _date_fields("yMdHhmsE")}
        for name, value in values.items():
            calendar.set(fields[name], value)
        return calendar

    def _match(self, text: str, start: int):
        if _continues_interval_word(text, start - 1):
            return None
        cp_to_u16, u16_to_cp = self._offset_maps
        matches = []
        for formatter1, separator, formatter2, fields1, fields2 in self._matchers:
            parsed1 = self._parse_side(formatter1, fields1, text, start, cp_to_u16, u16_to_cp)
            if parsed1 is None:
                continue
            end1, values1 = parsed1
            separator_end = self._separator_end(text, end1, separator)
            if separator_end is None:
                continue
            parsed2 = self._parse_side(
                formatter2, fields2, text, separator_end, cp_to_u16, u16_to_cp
            )
            if parsed2 is None:
                continue
            end2, values2 = parsed2
            if _continues_interval_word(text, end2):
                continue
            names = values1.keys() | values2.keys()
            start_values = {
                name: values1[name] if name in values1 else values2[name] for name in names
            }
            end_values = {
                name: values2[name] if name in values2 else values1[name] for name in names
            }
            try:
                start_calendar = self._calendar_from(start_values)
                end_calendar = self._calendar_from(end_values)
                reformatted = self._dif.format(
                    icu.DateInterval(start_calendar.getTime(), end_calendar.getTime())
                )
            except icu.ICUError:
                continue
            # note: The reformat guard is the correctness gate for every deposited value.
            # The two field regions are the exact surface text -- so a mis-parse whose
            # fields would render differently is rejected. Only the separator is swapped
            # for its reflective canonical form: the surface separator's non-space core was
            # already validated by _separator_end, and its spacing is the sole intentional
            # relaxation (letting "2020-2024" match canonical "2020 - 2024"). Thus a
            # deposited interval's fields always round-trip; only separator spacing is free.
            gate_surface = text[start:end1] + separator + text[separator_end:end2]
            if _normalize_interval_surface(reformatted) != _normalize_interval_surface(
                gate_surface
            ):
                continue
            captures = (
                Capture("start", start, end1, text[start:end1]),
                Capture(
                    "separator",
                    end1,
                    separator_end,
                    text[end1:separator_end],
                    form="symbol",
                ),
                Capture("end", separator_end, end2, text[separator_end:end2]),
            )
            value = DateIntervalValue(self._endpoint(start_values), self._endpoint(end_values))
            matches.append((end2, captures, value))
        return max(matches, key=lambda match: match[0], default=None)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping date-interval candidates in source order."""
        # Compute the code-point/UTF-16 offset maps once per scan; _match reuses them for
        # every candidate start rather than rebuilding them (avoids O(n^2) scanning).
        self._offset_maps = boundary_maps(text)
        try:
            return _detect_flexible(text, self.locale, self.type, self._spec, self._match)
        finally:
            self._offset_maps = None


class FlexibleTextDateDetector:
    """Recognize textual-month dates licensed by CLDR date patterns and symbols."""

    group = "date"
    type = "date:text-flexible"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        icu_locale = icu.Locale(locale)
        self._calendar = icu.Calendar.createInstance(icu_locale).getType()
        self._rbnf = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, icu_locale)
        symbols = icu.DateFormatSymbols(icu_locale)
        self._months = self._symbol_names(symbols, "month")
        self._weekdays = self._symbol_names(symbols, "weekday")
        self._digits = _locale_digit_map(icu_locale)

        structures: list[tuple[tuple[str, ...], tuple[str, ...], str]] = []
        for kind in (icu.DateFormat.kMedium, icu.DateFormat.kLong, icu.DateFormat.kFull):
            pattern = icu.DateFormat.createDateInstance(kind, icu_locale).toPattern()
            parsed = self._date_structure(pattern)
            if parsed is None:
                continue
            fields, literals = parsed
            structures.append((fields, literals, pattern))
            # A weekday can only be validated against a year, so a weekday-bearing
            # pattern gets no year-optional subset: dropping the year would deposit an
            # unchecked (and possibly contradictory) weekday reading.
            if "y" in fields and "E" not in fields:
                year = fields.index("y")
                reduced_fields = fields[:year] + fields[year + 1 :]
                # Removing the adjacent literal derives the year-optional subset from
                # the locale pattern instead of inventing punctuation or field order.
                if year == len(fields) - 1:
                    reduced_literals = literals[:-1]
                elif year == 0:
                    reduced_literals = literals[1:]
                else:
                    continue
                if {"M", "d"}.issubset(reduced_fields):
                    structures.append((reduced_fields, reduced_literals, pattern))
        language = icu_locale.getLanguage()
        for available in icu.Locale.getAvailableLocales().values():
            if available.getLanguage() != language:
                continue
            generator = icu.DateTimePatternGenerator.createInstance(available)
            for skeleton in ("dMMMMy", "dMMMy", "yMMMM", "yMMM"):
                pattern = generator.getBestPattern(skeleton)
                parsed = self._date_structure(pattern)
                if parsed is None:
                    continue
                fields, literals = parsed
                if fields in {("d", "M", "y"), ("M", "y")}:
                    structures.append((fields, literals, pattern))
        self._structures = tuple(dict.fromkeys(structures))
        pattern = self._structures[0][2] if self._structures else ""
        self._spec = DateFormatSpec(locale, "yMMMd", pattern, self._calendar)
        # note: Bare years and decades remain cardinal candidates for downstream reinterpretation.

    def _symbol_names(self, symbols: icu.DateFormatSymbols, field: str):
        found: dict[str, tuple[str, int, str]] = {}
        widths = (
            (icu.DateFormatSymbols.WIDE, "wide"),
            (icu.DateFormatSymbols.ABBREVIATED, "short"),
        )
        for context in (icu.DateFormatSymbols.FORMAT, icu.DateFormatSymbols.STANDALONE):
            for width, form in widths:
                values = (
                    symbols.getMonths(context, width)
                    if field == "month"
                    else symbols.getWeekdays(context, width)
                )
                for index, surface in enumerate(values):
                    if not surface:
                        continue
                    value = index + 1 if field == "month" else index
                    key = surface.casefold()
                    current = found.get(key)
                    if current is None or len(surface) > len(current[0]):
                        found[key] = (surface, value, form)
        return tuple(sorted(found.values(), key=lambda item: len(item[0]), reverse=True))

    @staticmethod
    def _date_structure(pattern: str):
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
            if not quoted and character in {"y", "M", "L", "d", "E"}:
                run_end = cursor + 1
                while run_end < len(pattern) and pattern[run_end] == character:
                    run_end += 1
                normalized = "M" if character == "L" else character
                if normalized == "M" and run_end - cursor < 3:
                    return None
                if fields:
                    literals.append("".join(literal))
                literal.clear()
                fields.append(normalized)
                cursor = run_end
                continue
            if not quoted and character.isalpha():
                return None
            literal.append(character)
            cursor += 1
        if set(fields) - {"y", "M", "d", "E"}:
            return None
        if not ({"y", "M", "d"}.issubset(fields) or set(fields) == {"M", "y"}):
            return None
        if "E" in fields and fields[0] != "E":
            return None
        return tuple(fields), tuple(literals)

    def _digit_run(self, text: str, start: int) -> tuple[int, int]:
        cursor = start
        value = 0
        while cursor < len(text) and text[cursor] in self._digits:
            value = value * 10 + self._digits[text[cursor]]
            cursor += 1
        return cursor, value

    def _ordinal_end(self, text: str, start: int, digit_end: int, value: int) -> int:
        rendered = self._rbnf.format(value)
        indexes = [
            index for index, char in enumerate(rendered) if char in self._digits or char.isdigit()
        ]
        if not indexes or rendered[: indexes[0]]:
            return digit_end
        suffix = rendered[indexes[-1] + 1 :]
        end = digit_end + len(suffix)
        return end if suffix and text[digit_end:end].casefold() == suffix.casefold() else digit_end

    @staticmethod
    def _name(text: str, start: int, names):
        for surface, value, form in names:
            end = start + len(surface)
            if text[start:end].casefold() == surface.casefold():
                if end == len(text) or not text[end].isalnum():
                    return end, value, form
        return None

    @staticmethod
    def _separator_end(text: str, cursor: int, literal: str) -> int | None:
        """Consume a field separator, treating only its punctuation as optional.

        The literal comes from the locale pattern, so the exact CLDR separator always
        matches. A form with the punctuation dropped is also accepted so a surface that
        omits it ("July 25 2012" for a ", " separator) still deposits a candidate. Only
        punctuation is relaxed: letters and whitespace are kept, so grammar words a
        pattern requires ("d 'de' MMMM 'de' y") stay mandatory and field order and
        spacing remain reflective.
        """
        if text.startswith(literal, cursor):
            return cursor + len(literal)
        relaxed = "".join(
            character for character in literal if character.isalnum() or character.isspace()
        )
        if relaxed != literal and text.startswith(relaxed, cursor):
            return cursor + len(relaxed)
        return None

    def _match_structure(self, text: str, start: int, structure):
        fields, literals, _pattern = structure
        month_year = set(fields) == {"M", "y"}
        if month_year and start > 0:
            previous = start - 1
            while previous >= 0 and text[previous] in _SPACES:
                previous -= 1
            if previous >= 0 and text[previous] in self._digits:
                return None
        cursor = start
        values: dict[str, int] = {}
        captures: list[Capture] = []
        for index, field in enumerate(fields):
            field_start = cursor
            if field in {"M", "E"}:
                named = self._name(text, cursor, self._months if field == "M" else self._weekdays)
                if named is None:
                    return None
                cursor, value, form = named
                name = "month" if field == "M" else "weekday"
                captures.append(
                    Capture(name, field_start, cursor, text[field_start:cursor], value, form)
                )
                values[field] = value
            else:
                digit_end, value = self._digit_run(text, cursor)
                width = digit_end - cursor
                if field == "d" and width in {1, 2} and 1 <= value <= 31:
                    following = literals[index] if index < len(literals) else ""
                    cursor = digit_end
                    if not following or not text.startswith(following, cursor):
                        cursor = self._ordinal_end(text, cursor, digit_end, value)
                elif field == "y" and width in {2, 4}:
                    cursor = digit_end
                else:
                    return None
                captures.append(
                    Capture(field, field_start, cursor, text[field_start:cursor], value, "numeric")
                )
                values[field] = value
            if index < len(literals):
                literal = literals[index]
                if not literal:
                    return None
                consumed = self._separator_end(text, cursor, literal)
                if consumed is None:
                    return None
                cursor = consumed

        if cursor < len(text) and text[cursor].isalnum():
            return None
        if month_year and cursor < len(text) and text[cursor] == ",":
            return None
        calendar = icu.Calendar.createInstance(icu.Locale(self.locale))
        calendar.setLenient(False)
        calendar.clear()
        try:
            validation_year = values.get("y", 2000)
            calendar.set(validation_year, values["M"] - 1, values.get("d", 1))
            calendar.getTime()
            if "y" in values and "E" in values:
                if calendar.get(icu.Calendar.DAY_OF_WEEK) != values["E"]:
                    return None
        except icu.ICUError:
            return None
        ordered = tuple((field, values[field]) for field in ("y", "M", "d") if field in values)
        return cursor, tuple(captures), DateTimeValue(ordered, self._calendar)

    def _match(self, text: str, start: int):
        if start > 0 and text[start - 1].isalnum():
            return None
        matches = [
            match
            for structure in self._structures
            if (match := self._match_structure(text, start, structure)) is not None
        ]
        return max(matches, key=lambda match: match[0], default=None)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping textual-date candidates in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleNumberDetector:
    """Recognize flexible decimal spellings and Roman cardinals from ICU data.

    ``accept_single_letter_roman`` defaults to true because corpora use ``I`` as the
    cardinal one. Lowercase Roman numerals are opt-in because their surfaces collide with
    unit abbreviations and common words.
    """

    group = "number"
    type = "number:decimal"

    def __init__(
        self,
        locale: str,
        *,
        accept_single_letter_roman: bool = True,
        accept_lowercase_roman: bool = False,
    ) -> None:
        self.locale = locale
        self.accept_single_letter_roman = accept_single_letter_roman
        self.accept_lowercase_roman = accept_lowercase_roman
        self._nf = icu.NumberFormat.createInstance(icu.Locale(locale))
        symbols = self._nf.getDecimalFormatSymbols()
        symbol = icu.DecimalFormatSymbols
        self._decimal = symbols.getSymbol(symbol.kDecimalSeparatorSymbol)
        self._grouping = symbols.getSymbol(symbol.kGroupingSeparatorSymbol)
        self._minus = symbols.getSymbol(symbol.kMinusSignSymbol)
        self._plus = symbols.getSymbol(symbol.kPlusSignSymbol)
        self._digits = {digit: str(value) for digit, value in _locale_digit_map(locale).items()}

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

        self._roman = icu.RuleBasedNumberFormat(
            icu.URBNFRuleSetTag.NUMBERING_SYSTEM, icu.Locale(locale)
        )
        rule_sets = tuple(
            self._roman.getRuleSetName(index)
            for index in range(self._roman.getNumberOfRuleSetNames())
        )
        self._roman_rule_sets = tuple(name for name in rule_sets if "roman" in name.casefold())
        if not accept_lowercase_roman:
            self._roman_rule_sets = tuple(
                name for name in self._roman_rule_sets if "lower" not in name.casefold()
            )
        alphabets: dict[str, frozenset[str]] = {}
        for rule_set in self._roman_rule_sets:
            alphabet = frozenset(
                character
                for value in range(1, 4000)
                for character in self._roman.format(value, rule_set)
                if _is_word_character(character)
            )
            alphabets[rule_set] = alphabet
        self._roman_alphabets = alphabets

    def _digits_ascii(self, surface: str) -> str:
        return "".join(
            self._digits[character] for character in surface if character in self._digits
        )

    def _grouping_length(self, text: str, cursor: int) -> int:
        if self._grouping in _SPACES:
            return int(cursor < len(text) and text[cursor] in _SPACES)
        return len(self._grouping) if text.startswith(self._grouping, cursor) else 0

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
        leading_decimal = text.startswith(self._decimal, cursor)
        decimal_end = cursor + len(self._decimal)
        if leading_decimal and start > 0:
            previous = text[start - 1]
            if _is_word_character(previous) or previous == self._decimal:
                return None
        if cursor >= len(text) or (
            text[cursor] not in self._digits
            and not (
                leading_decimal and decimal_end < len(text) and text[decimal_end] in self._digits
            )
        ):
            return None
        while cursor < len(text) and text[cursor] in self._digits:
            cursor += 1
        ungrouped_end = cursor
        groups = [cursor - integer_start]
        separators: list[int] = []
        while self._primary_grouping and (grouping_length := self._grouping_length(text, cursor)):
            grouping_start = cursor
            cursor += grouping_length
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
        integer_ascii = self._digits_ascii(integer_text) or "0"
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
        decimals = _detect_flexible(text, self.locale, self.type, self._spec, self._match)
        romans = _detect_flexible(
            text, self.locale, "number:cardinal:roman", self._spec, self._match_roman
        )
        return sorted((*decimals, *romans), key=lambda item: (item["start"], item["end"]))

    def _match_roman(self, text: str, start: int):
        if start > 0 and _is_word_character(text[start - 1]):
            return None
        for rule_set in self._roman_rule_sets:
            alphabet = self._roman_alphabets[rule_set]
            cursor = start
            while cursor < len(text) and text[cursor] in alphabet:
                cursor += 1
            if cursor == start or cursor - start == 1 and not self.accept_single_letter_roman:
                continue
            if cursor < len(text) and _is_word_character(text[cursor]):
                continue
            surface = text[start:cursor]
            position = icu.ParsePosition(0)
            parsed = self._roman.parse(surface, position)
            if parsed is None or position.getIndex() != len(surface):
                continue
            value = parsed.getInt64()
            if self._roman.format(value, rule_set) != surface:
                continue
            capture = Capture("integer", start, cursor, surface, str(value), "roman")
            return cursor, (capture,), NumberValue(str(value), None)
        return None


_RELATIVE_NUMERIC_UNITS = (
    "SECOND",
    "MINUTE",
    "HOUR",
    "DAY",
    "WEEK",
    "MONTH",
    "QUARTER",
    "YEAR",
)
_RELATIVE_NAMED_UNITS = ("DAY", "WEEK", "MONTH", "QUARTER", "YEAR")
_RELATIVE_DIRECTIONS = (
    ("LAST", -1),
    ("LAST_2", -2),
    ("THIS", 0),
    ("NEXT", 1),
    ("NEXT_2", 2),
)


@lru_cache(maxsize=128)
def _relative_date_vocabulary(locale: str):
    icu_locale = icu.Locale(locale)
    formatter = icu.RelativeDateTimeFormatter(icu_locale)
    number_format = icu.NumberFormat.createInstance(icu_locale)
    plural_rules = icu.PluralRules.forLocale(icu_locale)

    required_samples = {0, 1, 2, 3, 5, 11, 21, 101}
    representative_search = (*range(1001), 10_000, 100_000, 1_000_000)
    for keyword in plural_rules.getKeywords():
        representative = next(
            (value for value in representative_search if plural_rules.select(value) == keyword),
            None,
        )
        if representative is not None:
            required_samples.add(representative)

    numeric: dict[tuple[str, str], tuple[int, str, object]] = {}
    for unit_member in _RELATIVE_NUMERIC_UNITS:
        unit_enum = getattr(icu.URelativeDateTimeUnit, unit_member, None)
        if unit_enum is None:
            continue
        unit_name = unit_member.lower()
        for sign in (-1, 1):
            for magnitude in sorted(required_samples):
                if sign < 0 and magnitude == 0:
                    # ICU assigns numeric zero to the future form regardless of signed zero.
                    continue
                surface = formatter.formatNumeric(sign * magnitude, unit_enum)
                number_surface = number_format.format(magnitude)
                number_start = surface.find(number_surface)
                if number_start < 0:
                    # note: A locale/magnitude whose numeral is not embedded is silently skipped.
                    continue
                number_end = number_start + len(number_surface)
                template = (surface[:number_start], surface[number_end:])
                if not template[0] and not template[1]:
                    # A template with no marker words would reduce this lane to a bare-number
                    # matcher; no ICU relative surface is a naked numeral, so skip it.
                    continue
                numeric.setdefault(template, (sign, unit_name, unit_enum))

    named: dict[str, tuple[str, int, str, object, object]] = {}
    for unit_member in _RELATIVE_NAMED_UNITS:
        unit_enum = getattr(icu.UDateAbsoluteUnit, unit_member, None)
        if unit_enum is None:
            continue
        for direction_member, offset in _RELATIVE_DIRECTIONS:
            direction_enum = getattr(icu.UDateDirection, direction_member)
            try:
                surface = formatter.format(direction_enum, unit_enum)
            except icu.ICUError:
                continue
            if surface:
                named.setdefault(
                    surface.casefold(),
                    (surface, offset, unit_member.lower(), unit_enum, direction_enum),
                )

    now_unit = icu.UDateAbsoluteUnit.NOW
    plain = icu.UDateDirection.PLAIN
    try:
        now_surface = formatter.format(plain, now_unit)
    except icu.ICUError:
        now_surface = ""
    if now_surface:
        named.setdefault(now_surface.casefold(), (now_surface, 0, "now", now_unit, plain))

    # note: Weekday-relative offsets are out of scope for this lane.
    return tuple(
        (prefix, suffix, *details)
        for (prefix, suffix), details in sorted(
            numeric.items(), key=lambda item: (-sum(map(len, item[0])), item[0])
        )
    ), tuple(sorted(named.values(), key=lambda item: (-len(item[0]), item[0])))


class FlexibleRelativeDateDetector:
    """Recognize relative dates by inverting locale-relative ICU formatting."""

    group = "date"
    type = "date:relative"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._formatter = icu.RelativeDateTimeFormatter(icu.Locale(locale))
        self._number = FlexibleNumberDetector(locale)
        self._numeric_templates, self._named_phrases = _relative_date_vocabulary(locale)
        self._spec = RelativeDateSpec(locale)

    @property
    def reachable_units(self) -> tuple[str, ...]:
        """Unit names for which ICU exposed at least one invertible phrase."""
        numeric = {template[3] for template in self._numeric_templates}
        named = {phrase[2] for phrase in self._named_phrases}
        return tuple(sorted(numeric | named))

    @property
    def has_vocabulary(self) -> bool:
        """Whether ICU exposed any invertible relative-date phrase."""
        return bool(self._numeric_templates or self._named_phrases)

    @staticmethod
    def _continues_word(text: str, cursor: int) -> bool:
        if cursor >= len(text):
            return False
        return _is_word_character(text[cursor]) or (
            icu.Char.charType(text[cursor]) == icu.UCharCategory.CONNECTOR_PUNCTUATION
        )

    def _left_boundary(self, text: str, start: int) -> bool:
        return start <= 0 or not self._continues_word(text, start - 1)

    @staticmethod
    def _direction(offset: int) -> str:
        if offset < 0:
            return "past"
        if offset > 0:
            return "future"
        return "present"

    def _named_match(self, text: str, start: int):
        for surface, offset, unit_name, unit_enum, direction_enum in self._named_phrases:
            end = start + len(surface)
            if text[start:end].casefold() != surface.casefold():
                continue
            if self._continues_word(text, end):
                continue
            canonical = self._formatter.format(direction_enum, unit_enum)
            # note: The reformat guard is the correctness gate for every deposited value.
            if canonical.casefold() != text[start:end].casefold():
                continue
            capture = Capture("relative", start, end, text[start:end], offset, "wide")
            value = RelativeDateValue(offset, unit_name, self._direction(offset))
            return end, (capture,), value
        return None

    def _numeric_match(self, text: str, start: int):
        for prefix, suffix, sign, unit_name, unit_enum in self._numeric_templates:
            number_start = start + len(prefix)
            if text[start:number_start].casefold() != prefix.casefold():
                continue
            number = self._number._match(text, number_start)
            if number is None:
                continue
            number_end, captures, number_value = number
            if "." in number_value.decimal or number_value.decimal.startswith(("-", "+")):
                continue
            end = number_end + len(suffix)
            if text[number_end:end].casefold() != suffix.casefold():
                continue
            if self._continues_word(text, end):
                continue
            offset = sign * int(number_value.decimal)
            canonical = self._formatter.formatNumeric(offset, unit_enum)
            if canonical.casefold() != text[start:end].casefold():
                continue
            markers: list[Capture] = []
            if prefix:
                markers.append(
                    Capture(
                        "relative-marker",
                        start,
                        number_start,
                        text[start:number_start],
                        None,
                        "symbol",
                    )
                )
            if suffix:
                markers.append(
                    Capture(
                        "relative-marker", number_end, end, text[number_end:end], None, "symbol"
                    )
                )
            all_captures = tuple(
                sorted((*captures, *markers), key=lambda capture: (capture.start, capture.end))
            )
            value = RelativeDateValue(offset, unit_name, self._direction(offset))
            return end, all_captures, value
        return None

    def _match(self, text: str, start: int):
        if not self._left_boundary(text, start):
            return None
        return self._named_match(text, start) or self._numeric_match(text, start)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping relative-date candidates in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


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
        sign, digits, exponent = Decimal(value.decimal).as_tuple()
        ratio = format(Decimal((sign, digits, exponent - 2)), "f")
        if "." in ratio:
            ratio = ratio.rstrip("0").rstrip(".")
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
        sign, digits, exponent = Decimal(value.decimal).as_tuple()
        ratio = format(Decimal((sign, digits, exponent - 2)), "f")
        if "." in ratio:
            ratio = ratio.rstrip("0").rstrip(".")
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
    """Recognize a reflective currency symbol or name around a scaled flexible number."""

    group = "number"

    def __init__(self, locale: str, currency: str) -> None:
        self.locale = locale
        self.currency = currency
        self.type = f"number:currency:{currency}"
        self._number = FlexibleNumberDetector(locale)
        self._compact = (
            FlexibleCompactDetector(locale, "long"),
            FlexibleCompactDetector(locale, "short", fold_symbol_case=True),
        )
        self._currency_name = FlexibleCurrencyNameDetector(locale, currency)
        number_format = icu.NumberFormat.createCurrencyInstance(icu.Locale(locale))
        number_format.setCurrency(currency)
        symbols = number_format.getDecimalFormatSymbols()
        self._currency = symbols.getSymbol(icu.DecimalFormatSymbols.kCurrencySymbol)
        language = icu.Locale(locale).getLanguage()
        reflected_symbols = {self._currency}
        requested_locale = icu.Locale(locale).getName()
        for available in icu.Locale.getAvailableLocales().values():
            if available.getLanguage() != language:
                continue
            narrow = self._currency_affix(available, currency, icu.UNumberUnitWidth.NARROW)
            short = self._currency_affix(available, currency, icu.UNumberUnitWidth.SHORT)
            # A foreign locale's narrow symbol is locally ambiguous; only its distinct
            # short form carries enough information to import into this locale.
            if available.getName() == requested_locale or short != narrow:
                reflected_symbols.add(short)
            reflected_symbols.add(
                self._currency_affix(available, currency, icu.UNumberUnitWidth.ISO_CODE)
            )
        self._currencies = tuple(sorted(reflected_symbols, key=len, reverse=True))
        self._spec = NumberFormatSpec(locale, "currency", currency=currency)

    @staticmethod
    def _space(text: str, cursor: int) -> int:
        if cursor < len(text) and text[cursor] in _SPACES:
            return cursor + 1
        return cursor

    @staticmethod
    def _currency_affix(locale: icu.Locale, currency: str, width: int) -> str:
        formatted = str(
            icu.NumberFormatter.withLocale(locale)
            .unit(icu.CurrencyUnit(currency))
            .unitWidth(width)
            .formatInt(1)
        )
        digits = _locale_digit_map(locale)
        indexes = [index for index, character in enumerate(formatted) if character in digits]
        if not indexes:
            return ""
        prefix = formatted[: indexes[0]].strip()
        suffix = formatted[indexes[-1] + 1 :].strip()
        return prefix or suffix

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        if start > 0 and _is_word_character(text[start - 1]):
            return None
        for symbol in self._currencies:
            if not text.startswith(symbol, start):
                continue
            symbol_end = start + len(symbol)
            number_start = self._space(text, symbol_end)
            match = self._amount(text, number_start)
            if match is not None:
                end, captures, value = match
                currency = Capture("currency", start, symbol_end, symbol, self.currency, "symbol")
                return end, (currency, *captures), NumberValue(value.decimal, self.currency)

        match = self._amount(text, start)
        if match is None:
            return None
        number_end, captures, value = match
        symbol_start = self._space(text, number_end)
        for symbol in self._currencies:
            if text.startswith(symbol, symbol_start):
                end = symbol_start + len(symbol)
                currency = Capture("currency", symbol_start, end, symbol, self.currency, "symbol")
                return end, (*captures, currency), NumberValue(value.decimal, self.currency)
        if symbol_start == number_end:
            return None
        name_end = self._currency_name._currency_at(text, symbol_start, False)
        # CLDR calls USD "US dollar" in English; the corpus's region-stripped bare
        # dollar is lexical because ICU exposes no reflective region-stripping rule.
        if name_end is None and self.locale.startswith("en") and self.currency == "USD":
            for surface in ("dollars", "dollar"):
                end = symbol_start + len(surface)
                if text[symbol_start:end].casefold() == surface:
                    name_end = end
                    break
        if name_end is None:
            return None
        currency = Capture(
            "currency",
            symbol_start,
            name_end,
            text[symbol_start:name_end],
            self.currency,
            "wide",
        )
        return name_end, (*captures, currency), NumberValue(value.decimal, self.currency)

    def _amount(self, text: str, start: int):
        matches = [self._number._match(text, start)]
        matches.extend(detector._match(text, start) for detector in self._compact)
        # CLDR English short compacts carry B, but not the corpus suffix bn.
        if self.locale.startswith("en"):
            plain = self._number._match(text, start)
            if plain is not None:
                end, captures, value = plain
                for suffix, magnitude in (("bn", 9),):
                    if text[end : end + len(suffix)].casefold() == suffix:
                        scaled = Decimal(value.decimal) * Decimal(10) ** magnitude
                        compact = Capture(
                            "compact", end, end + len(suffix), suffix, magnitude, "symbol"
                        )
                        matches.append(
                            (
                                end + len(suffix),
                                (*captures, compact),
                                NumberValue(format(scaled, "f")),
                            )
                        )
        return max(
            (match for match in matches if match is not None),
            key=lambda match: match[0],
            default=None,
        )

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

    def _match(self, text: str, start: int) -> _FlexibleMatch | None:
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
            return _FlexibleMatch(
                end,
                (*captures, unit_capture),
                MeasureValue(value.decimal, self.unit),
                spec,
            )
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible measure candidates in source order."""
        return _detect_flexible(text, self.locale, self.type, None, self._match)


class FlexibleCompactDetector:
    """Recognize a flexible number with reflectively derived ICU compact affixes.

    ``fold_symbol_case`` licenses case variants of single-letter compact symbols when
    enclosing context disambiguates them. It is off by default because bare lowercase
    symbols collide with unit abbreviations.
    """

    group = "number"

    def __init__(self, locale: str, width: str, *, fold_symbol_case: bool = False) -> None:
        self.locale = locale
        self.width = width
        self.fold_symbol_case = fold_symbol_case
        self.type = f"number:compact:{width}"
        self._number = FlexibleNumberDetector(locale)
        self._spec = CompactFormatSpec(locale, width)

        styles = {
            "short": icu.UNumberCompactStyle.SHORT,
            "long": icu.UNumberCompactStyle.LONG,
        }
        if width not in styles:
            raise ValueError(f"compact width must be 'short' or 'long': {width!r}")

        formatter = icu.CompactDecimalFormat.createInstance(icu.Locale(locale), styles[width])
        digits = _locale_digit_map(locale)
        affixes: dict[tuple[str, str], int] = {}
        multipliers = ("1", "2", "3", "5", "1.1", "1.2", "1.5", "2.5")
        for power in range(16):
            for multiplier in multipliers:
                fed = Decimal(multiplier) * (Decimal(10) ** power)
                operand = int(fed) if fed == fed.to_integral_value() else float(fed)
                formatted = formatter.format(operand)
                digit_indexes = [
                    index for index, character in enumerate(formatted) if character in digits
                ]
                if not digit_indexes:
                    continue
                first_digit, last_digit = digit_indexes[0], digit_indexes[-1]
                prefix = formatted[:first_digit]
                suffix = formatted[last_digit + 1 :]
                if not prefix and not suffix:
                    continue
                displayed = formatted[first_digit : last_digit + 1]
                parsed = self._number._match(displayed, 0)
                if parsed is None or parsed[0] != len(displayed):
                    continue
                displayed_value = Decimal(parsed[2].decimal)
                if not displayed_value:
                    continue
                ratio = fed / displayed_value
                magnitude = int(ratio.log10().to_integral_value())
                if displayed_value * (Decimal(10) ** magnitude) != fed:
                    continue
                affixes.setdefault((prefix, suffix), magnitude)

        # note: A digit-less spelled compact (French "mille" for 1000) exposes no digit
        # run to anchor a number, so it is out of scope; keyed compacts ("1 million") and
        # affix-bearing surfaces are covered.
        self._affixes = affixes
        self._ordered_affixes = tuple(
            (prefix, suffix, magnitude)
            for (prefix, suffix), magnitude in sorted(
                affixes.items(), key=lambda item: (-len(item[0][1]), -len(item[0][0]))
            )
        )

    @property
    def has_affixes(self) -> bool:
        """Whether ICU exposed at least one exactly invertible compact affix."""
        return bool(self._affixes)

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

    def _left_boundary(self, text: str, start: int) -> bool:
        """Whether ``start`` begins a fresh token, not the interior of a number or word.

        Scanning starts at every grapheme, so a prefix affix ("B" in Swahili "B12") or a
        digit run could otherwise begin inside a surrounding word ("AB12") or in the tail
        of a larger number ("2M" from "1.2M"). Rejecting a start preceded by a word
        character or by the locale's decimal/grouping separator keeps matches token-aligned.
        The number parser treats every space as grouping when the separator is space-like,
        so an interior grouping space (a space sitting between digits) also bars a start,
        while a space after a word -- a normal token boundary -- does not.
        """
        if start <= 0:
            return True
        if self._continues_word(text, start - 1):
            return False
        previous = text[start - 1]
        if previous == self._number._decimal:
            return False
        grouping = self._number._grouping
        if grouping and grouping in _SPACES:
            return not (
                previous in _SPACES and start >= 2 and text[start - 2] in self._number._digits
            )
        return previous != grouping

    def _match(self, text: str, start: int):
        if not self._left_boundary(text, start):
            return None
        for prefix, suffix, magnitude in self._ordered_affixes:
            cursor = start
            captures: list[Capture] = []
            negative = False
            if prefix:
                # A prefix-affix locale (Swahili "M1.2") renders a negative value with the
                # sign before the prefix, so consume an optional leading sign here rather
                # than leaving it for the post-prefix number parse.
                for sign, is_negative in (
                    (self._number._minus, True),
                    (self._number._plus, False),
                ):
                    if sign and text.startswith(sign, cursor):
                        sign_end = cursor + len(sign)
                        captures.append(Capture("sign", cursor, sign_end, sign, None, "symbol"))
                        negative = is_negative
                        cursor = sign_end
                        break
                observed = text[cursor : cursor + len(prefix)]
                if not self._affix_equal(observed, prefix):
                    continue
                prefix_start = cursor
                cursor += len(prefix)
                captures.append(
                    Capture(
                        "compact",
                        prefix_start,
                        cursor,
                        text[prefix_start:cursor],
                        magnitude,
                        "symbol",
                    )
                )
            match = self._number._match(text, cursor)
            if match is None:
                continue
            number_end, number_captures, number = match
            # With a prefix affix the sign always precedes the prefix, so a sign on the
            # digits ("M+1.2", or the contradictory "-M+1.2") is not a compact number.
            if prefix and any(capture.name == "sign" for capture in number_captures):
                continue
            if not self._affix_equal(text[number_end : number_end + len(suffix)], suffix):
                continue
            end = number_end + len(suffix)
            if self._continues_word(text, end):
                continue

            captures.extend(number_captures)
            if suffix:
                captures.append(
                    Capture("compact", number_end, end, text[number_end:end], magnitude, "symbol")
                )
            captures.sort(key=lambda capture: (capture.start, capture.end))
            # A compact surface is a rounded display, so recover its honest nominal
            # value without inventing false precision or a range.
            sign, digits, exponent = Decimal(number.decimal).as_tuple()
            value = Decimal((sign, digits, exponent + magnitude))
            if negative:
                value = -value
            decimal = format(value, "f")
            return end, tuple(captures), NumberValue(decimal, None)
        return None

    def _affix_equal(self, observed: str, expected: str) -> bool:
        letters = sum(_is_word_character(character) for character in expected)
        if letters > 1 or self.fold_symbol_case:
            return observed.casefold() == expected.casefold()
        return observed == expected

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible compact numbers in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleScientificDetector:
    """Recognize scientific notation using locale symbols reflected from ICU."""

    group = "number"
    type = "number:scientific"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._number = FlexibleNumberDetector(locale)
        symbols = icu.NumberFormat.createInstance(icu.Locale(locale)).getDecimalFormatSymbols()
        self._exponential = symbols.getSymbol(icu.DecimalFormatSymbols.kExponentialSymbol)
        self._minus = self._number._minus
        self._plus = self._number._plus
        self._digits = self._number._digits
        self._spec = NumberFormatSpec(locale, "scientific")

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

    def _left_boundary(self, text: str, start: int) -> bool:
        if start <= 0:
            return True
        if self._continues_word(text, start - 1):
            return False
        previous = text[start - 1]
        if previous == self._number._decimal:
            return False
        grouping = self._number._grouping
        if grouping and grouping in _SPACES:
            return not (previous in _SPACES and start >= 2 and text[start - 2] in self._digits)
        return previous != grouping

    def _match(self, text: str, start: int):
        if not self._left_boundary(text, start):
            return None
        match = self._number._match(text, start)
        if match is None:
            return None
        cursor, mantissa_captures, mantissa = match
        if not text.startswith(self._exponential, cursor):
            return None
        separator_start = cursor
        cursor += len(self._exponential)
        captures = list(mantissa_captures)
        captures.append(
            Capture(
                "exponent-separator",
                separator_start,
                cursor,
                self._exponential,
                None,
                "symbol",
            )
        )
        negative = False
        for sign, is_negative in ((self._minus, True), (self._plus, False)):
            if sign and text.startswith(sign, cursor):
                sign_end = cursor + len(sign)
                captures.append(Capture("sign", cursor, sign_end, sign, None, "symbol"))
                negative = is_negative
                cursor = sign_end
                break
        exponent_start = cursor
        ascii_digits: list[str] = []
        while cursor < len(text) and text[cursor] in self._digits:
            ascii_digits.append(self._digits[text[cursor]])
            cursor += 1
        if not ascii_digits or self._continues_word(text, cursor):
            return None
        decimal_end = cursor + len(self._number._decimal)
        if text.startswith(self._number._decimal, cursor) and (
            decimal_end < len(text) and text[decimal_end] in self._digits
        ):
            return None
        grouping = self._number._grouping
        grouping_end = cursor + len(grouping)
        if (
            grouping
            and grouping not in _SPACES
            and text.startswith(grouping, cursor)
            and (grouping_end < len(text) and text[grouping_end] in self._digits)
        ):
            return None
        exponent_ascii = "".join(ascii_digits)
        captures.append(
            Capture(
                "exponent",
                exponent_start,
                cursor,
                text[exponent_start:cursor],
                exponent_ascii,
                "numeric",
            )
        )
        try:
            exponent = int(exponent_ascii) * (-1 if negative else 1)
            sign, digits, decimal_exponent = Decimal(mantissa.decimal).as_tuple()
            # Shift the exponent exactly so no significant digit is rounded away.
            adjusted_exponent = decimal_exponent + exponent
            projected = len(digits) + abs(adjusted_exponent)
            if projected > _MAX_SCIENTIFIC_CANONICAL_DIGITS:
                return None
            value = Decimal((sign, digits, adjusted_exponent))
            decimal = format(value, "f")
        except (ValueError, OverflowError):
            # An exponent too large to represent is a silent non-recognition, not a crash.
            return None
        captures.sort(key=lambda capture: (capture.start, capture.end))
        return cursor, tuple(captures), NumberValue(decimal, None)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping scientific numbers in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


def _spellout_formatter_and_ruleset(
    locale: str,
) -> tuple[icu.RuleBasedNumberFormat, str]:
    formatter = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.SPELLOUT, icu.Locale(locale))
    names = tuple(
        formatter.getRuleSetName(index) for index in range(formatter.getNumberOfRuleSetNames())
    )
    ruleset = next(
        (
            name
            for name in names
            if "cardinal" in name.casefold()
            and not any(excluded in name.casefold() for excluded in ("ordinal", "year", "verbose"))
        ),
        formatter.getDefaultRuleSetName(),
    )
    if ruleset not in names:
        raise ValueError(f"ICU exposed no usable spellout rule set for {locale!r}")
    return formatter, ruleset


class FlexibleSpelloutDetector:
    """Recognize canonical ICU spelled-out cardinals derived from locale RBNF data.

    A lone token is suppressed only when it is one of the ambiguous unit words obtained
    by formatting 0 through 9. Larger lone magnitudes and every multi-token canonical
    surface remain eligible for deposit-and-hold alongside other detector candidates.
    """

    group = "number"
    type = "number:spellout"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._rbnf, self._ruleset = _spellout_formatter_and_ruleset(locale)
        self._spec = SpelloutFormatSpec(locale, self._ruleset)
        values = (
            *range(1001),
            *(
                multiplier * 10**power
                for power in range(2, 13)
                for multiplier in (*range(1, 12), 100)
            ),
            *(multiplier * 10**power + 1 for power in range(2, 13) for multiplier in range(1, 12)),
            *(
                multiplier * 10**power + 10 ** (power - 1) + 1
                for power in range(2, 13)
                for multiplier in (1, 2)
            ),
            21,
            101,
            1234,
            2_000_000,
            999,
            999_999,
        )
        surfaces = tuple(self._rbnf.format(value, self._ruleset) for value in values)
        self._connectors = frozenset(
            character
            for surface in surfaces
            for character in surface
            if not _is_word_character(character)
        )
        tokens: set[str] = set()
        for surface in surfaces:
            token: list[str] = []
            for character in surface:
                if _is_word_character(character):
                    token.append(character)
                elif token:
                    tokens.add("".join(token).casefold())
                    token = []
            if token:
                tokens.add("".join(token).casefold())
        self._tokens = tuple(sorted(tokens, key=lambda token: (-len(token), token)))
        tokens_by_first: dict[str, list[str]] = {}
        for token in self._tokens:
            tokens_by_first.setdefault(token[0], []).append(token)
        self._tokens_by_first = {
            first: tuple(first_tokens) for first, first_tokens in tokens_by_first.items()
        }
        self._ambiguous_units = frozenset(
            self._rbnf.format(value, self._ruleset).casefold() for value in range(10)
        )
        # note: This lane is SPELLOUT cardinals only; RBNF NUMBERING_SYSTEM Roman
        # numerals are intentionally out of scope.
        # note: Reflective connector tokenization recognizes scriptio-continua/CJK and
        # soft-hyphen-free German only in ICU's exact canonical form because ICU's own
        # RBNF parser requires those forms. Sampling also cannot exhaust languages whose
        # number words inflect by grammatical context and fuse conjunctions without a
        # separator, notably Semitic construct-state/agreement systems such as Arabic and
        # Hebrew. Their agreement-inflected numerals and fused conjunction forms are
        # recognized only when a sample exposes them; other surfaces yield at most an
        # honest partial because every deposit must still satisfy
        # format(value).casefold() == surface.casefold(). This lane deliberately targets
        # connector-separated, non-agreement locales (including major European,
        # Cyrillic, and Indic locales); flexible CJK and Semitic-agreement coverage is out
        # of scope. The recognition ceiling is likewise ICU's largest parseable scale
        # word.

    @staticmethod
    def _continues_word(text: str, cursor: int) -> bool:
        if cursor >= len(text):
            return False
        character = text[cursor]
        return (
            _is_word_character(character)
            or icu.Char.charType(character) == icu.UCharCategory.CONNECTOR_PUNCTUATION
        )

    def _left_boundary(self, text: str, start: int) -> bool:
        return start <= 0 or not self._continues_word(text, start - 1)

    @staticmethod
    def _casefolded_token_end(text: str, start: int, token: str) -> int | None:
        folded = ""
        cursor = start
        while cursor < len(text) and len(folded) < len(token):
            folded += text[cursor].casefold()
            cursor += 1
        return cursor if folded == token else None

    def _token_end(self, text: str, start: int) -> int | None:
        if start >= len(text):
            return None
        first = text[start].casefold()
        if not first:
            return None
        for token in self._tokens_by_first.get(first[0], ()):
            end = self._casefolded_token_end(text, start, token)
            if end is not None:
                return end
        return None

    def _parse_integer(self, surface: str) -> tuple[int, int] | None:
        for candidate in (surface, surface.lower()):
            position = icu.ParsePosition(0)
            parsed = self._rbnf.parse(candidate, position)
            if parsed is None or position.getIndex() <= 0:
                continue
            parsed_type = parsed.getType()
            if parsed_type in (icu.Formattable.kLong, icu.Formattable.kInt64):
                return position.getIndex(), parsed.getInt64()
            if parsed_type == icu.Formattable.kDouble and float(parsed.getDouble()).is_integer():
                return position.getIndex(), parsed.getInt64()
        return None

    def _integer_value(self, surface: str) -> int | None:
        parsed = self._parse_integer(surface)
        if parsed is None or parsed[0] != len(surface):
            return None
        return parsed[1]

    def _match(self, text: str, start: int, token_end=None):
        if not self._left_boundary(text, start):
            return None
        token_end = token_end or (lambda cursor: self._token_end(text, cursor))
        cursor = start
        token_ends: list[int] = []
        expect_token = True
        while cursor < len(text) and len(token_ends) < 256:
            if expect_token:
                end = token_end(cursor)
                if end is None:
                    break
                cursor = end
                token_ends.append(cursor)
                expect_token = False
                continue
            connector_start = cursor
            while cursor < len(text) and text[cursor] in self._connectors:
                cursor += 1
            if cursor == connector_start:
                break
            expect_token = True

        if not token_ends:
            return None
        run_end = token_ends[-1]
        parsed = self._parse_integer(text[start:run_end])
        if parsed is None:
            return None
        consumed, parsed_value = parsed
        absolute_end = start + consumed
        candidates = [
            (token_index, end)
            for token_index, end in enumerate(token_ends, start=1)
            if end <= absolute_end
        ]
        for token_index, end in reversed(candidates):
            if self._continues_word(text, end):
                continue
            surface = text[start:end]
            if token_index == 1 and surface.casefold() in self._ambiguous_units:
                continue
            if end == absolute_end:
                value = parsed_value
            else:
                value = self._integer_value(surface)
                if value is None:
                    continue
            canonical = self._rbnf.format(value, self._ruleset)
            if canonical.casefold() != surface.casefold():
                continue
            capture = Capture("spellout", start, end, surface, str(value), "wide")
            return end, (capture,), NumberValue(str(value), None)
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping spelled-out cardinals in source order."""
        token_ends: dict[int, int | None] = {}

        def token_end(cursor: int) -> int | None:
            if cursor not in token_ends:
                token_ends[cursor] = self._token_end(text, cursor)
            return token_ends[cursor]

        def match(source: str, start: int):
            return self._match(source, start, token_end)

        return _detect_flexible(text, self.locale, self.type, self._spec, match)


class FlexibleCurrencyNameDetector:
    """Recognize flexible numbers adjacent to reflective spelled currency names."""

    group = "number"

    def __init__(self, locale: str, currency: str) -> None:
        self.locale = locale
        unit = icu.CurrencyUnit(currency)
        canonical = unit.getISOCurrency()
        if canonical != currency:
            raise ValueError(f"currency is not canonical: {currency!r} (canonical {canonical!r})")
        if canonical not in _iso_currency_codes():
            raise ValueError(f"not an assigned ISO currency: {canonical!r}")
        self.currency = canonical
        self.type = f"number:currency-name:{canonical}"
        self._number = FlexibleNumberDetector(locale)
        icu_locale = icu.Locale(locale)
        plural_info = icu.CurrencyPluralInfo(icu_locale)
        plural_rules = icu.PluralRules.forLocale(icu_locale)
        names: dict[str, tuple[str, bool]] = {}

        # Plural categories turn on integer, large-magnitude, and fractional operands, so
        # the search for a representative of each keyword samples all three kinds.
        samples = [
            *range(201),
            1000,
            100000,
            1000000,
            100000000,
            0.1,
            0.5,
            1.1,
            1.5,
            2.5,
            10.1,
            100.1,
            1000.1,
        ]
        keywords = list(plural_rules.getKeywords())
        for keyword in keywords:
            representative = next(
                (value for value in samples if plural_rules.select(value) == keyword), None
            )
            if representative is None:
                continue
            pattern = plural_info.getCurrencyPluralPattern(keyword)
            formatter = icu.DecimalFormat(pattern, icu.DecimalFormatSymbols(icu_locale))
            formatter.setCurrency(canonical)
            position = icu.FieldPosition(icu.UNumberFormatFields.CURRENCY_FIELD)
            rendered = formatter.format(representative, position)
            surface = rendered[position.getBeginIndex() : position.getEndIndex()]
            if surface:
                number_index = min(
                    (pattern.index(character) for character in "#0@" if character in pattern),
                    default=0,
                )
                names[surface.casefold()] = (surface, pattern.find("¤¤¤") < number_index)

        long_name = unit.getName(icu_locale, icu.UCurrNameStyle.LONG_NAME)
        orientations = {prefix for _surface, prefix in names.values()} or {False}
        for prefix in orientations:
            names.setdefault(long_name.casefold(), (long_name, prefix))
            names.setdefault(canonical.casefold(), (canonical, prefix))
        self._names = tuple(sorted(names.values(), key=lambda item: len(item[0]), reverse=True))
        self._spec = NumberFormatSpec(locale, "currency", currency=canonical)
        # note: CLDR does not reflectively expose region-stripped names or minor-unit names.

    @staticmethod
    def _space(text: str, cursor: int) -> int:
        if cursor < len(text) and text[cursor] in _SPACES:
            return cursor + 1
        return cursor

    def _currency_at(self, text: str, start: int, prefix: bool):
        for surface, is_prefix in self._names:
            if is_prefix != prefix:
                continue
            end = start + len(surface)
            if text[start:end].casefold() == surface.casefold():
                if end == len(text) or not text[end].isalnum():
                    return end
        return None

    def _match(self, text: str, start: int):
        if start > 0 and text[start - 1].isalnum():
            return None
        currency_end = self._currency_at(text, start, True)
        if currency_end is not None:
            number_start = self._space(text, currency_end)
            number = self._number._match(text, number_start)
            if number is not None:
                end, captures, value = number
                currency_capture = Capture(
                    "currency", start, currency_end, text[start:currency_end], self.currency, "wide"
                )
                return end, (currency_capture, *captures), NumberValue(value.decimal, self.currency)

        number = self._number._match(text, start)
        if number is None:
            return None
        number_end, captures, value = number
        currency_start = self._space(text, number_end)
        if currency_start == number_end:
            # A spelled name is a word; without whitespace after the number the name
            # would run into the digits ("5USD", "5euros"), a mid-token match.
            return None
        currency_end = self._currency_at(text, currency_start, False)
        if currency_end is None:
            return None
        currency_capture = Capture(
            "currency",
            currency_start,
            currency_end,
            text[currency_start:currency_end],
            self.currency,
            "wide",
        )
        return (
            currency_end,
            (*captures, currency_capture),
            NumberValue(value.decimal, self.currency),
        )

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping spelled-currency candidates in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleTimeDetector:
    """Recognize clock times using a locale's CLDR short-time structure.

    The ``time:flexible`` type marks recall candidates for hours:minutes, an optional
    ``:seconds``, and an optional day period (am/pm). All are reflective: the time
    separator, the 12- vs 24-hour convention, and whether the day period is written
    before or after the time come from the locale's short-time pattern
    (``icu.DateFormat.createTimeInstance(kShort)``), and the day-period strings come from
    ``icu.DateFormatSymbols.getAmPmStrings`` -- nothing is hard-coded per locale. A
    pattern whose am/pm field precedes the hour (``ko_KR`` ``"a h:mm"``) is read with the
    day period as a prefix; a field after the hour is read as a suffix, and a pattern
    without an am/pm field does not license one.

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
        structure = self._time_structure(self.pattern)
        self._inert = structure is None
        self._separator, self.hour12, self._period_side = structure or ("", False, None)
        self._period_prefix = self._period_side == "prefix"
        self._periods = tuple(icu.DateFormatSymbols(icu_locale).getAmPmStrings())

        self._digits = _locale_digit_map(icu_locale)
        self._spec = DateFormatSpec(locale, "Hms", self.pattern, "gregorian")

    @staticmethod
    def _time_structure(pattern: str) -> tuple[str, bool, str | None] | None:
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
            return None
        # The separator scan stops at minutes, so inspect the full pattern separately
        # to distinguish an am/pm field after the time from no am/pm field at all.
        quoted = False
        seen_hour = False
        cursor = 0
        period_side = None
        while cursor < len(pattern):
            character = pattern[cursor]
            if character == "'":
                if cursor + 1 < len(pattern) and pattern[cursor + 1] == "'":
                    cursor += 2
                    continue
                quoted = not quoted
            elif not quoted and character in hour_letters:
                seen_hour = True
            elif not quoted and character == "a":
                period_side = "suffix" if seen_hour else "prefix"
                break
            cursor += 1
        return joined, hour12, period_side

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

    def _period_precedes(self, text: str, start: int) -> bool:
        """Whether a day-period marker (with an optional space) ends just before ``start``."""
        cursor = start
        if cursor > 0 and text[cursor - 1] in _SPACES:
            cursor -= 1
        for period in self._periods:
            if period and cursor - len(period) >= 0:
                if text[cursor - len(period) : cursor].casefold() == period.casefold():
                    return True
        return False

    def _match(
        self, text: str, start: int
    ) -> tuple[int, tuple[Capture, ...], DateTimeValue] | None:
        if start > 0 and text[start - 1] in self._digits:
            return None
        cursor = start
        captures: list[Capture] = []
        period_index: int | None = None

        # A prefix locale writes the day period before the hour, so consume it here and
        # require a 12-hour reading; a bare time with no marker stays a 24-hour reading.
        if self._period_prefix:
            found = self._day_period(text, cursor)
            if found is not None:
                if start > 0 and text[start - 1].isalnum():
                    return None
                marker_end, marker_text, period_index = found
                captures.append(
                    Capture("day-period", start, marker_end, marker_text, None, "symbol")
                )
                cursor = marker_end
                if cursor < len(text) and text[cursor] in _SPACES:
                    cursor += 1
            elif self._period_precedes(text, start):
                # A bare time right after a marker is the tail of a prefixed time whose
                # hour was out of the 1-12 range; reject it as the suffix side rejects
                # "15:45 PM" rather than dropping the marker and keeping a bare reading.
                return None

        hour_start = cursor
        first = self._digit_run(text, cursor)
        hour_width = first[0] - hour_start
        if hour_width not in {1, 2}:
            return None
        cursor, raw_hour = first
        if period_index is not None and not 1 <= raw_hour <= 12:
            return None

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
        if self._period_side == "suffix":
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
        elif self._period_side is None and self._day_period(text, cursor) is not None:
            # Do not truncate a marker-bearing surface to a bare-time candidate when
            # the locale pattern does not license a day period.
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
            "H",
            hour_start,
            hour_start + hour_width,
            text[hour_start : hour_start + hour_width],
            raw_hour,
            "numeric",
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
        ordered.sort(key=lambda capture: capture.start)
        value = DateTimeValue(tuple(fields), "gregorian")
        return cursor, tuple(ordered), value

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible clock times in source order."""
        if self._inert:
            return []
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleFractionDetector:
    """Recognize signed ``N/D`` fractions and NFKC-decomposable vulgar fractions.

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
        self._digits = _locale_digit_map(locale)
        self._spec = NumberFormatSpec(locale, "decimal")
        self._nfkc = icu.Normalizer2.getNFKCInstance()
        symbols = icu.NumberFormat.createInstance(icu.Locale(locale)).getDecimalFormatSymbols()
        self._minus = symbols.getSymbol(icu.DecimalFormatSymbols.kMinusSignSymbol)
        self._plus = symbols.getSymbol(icu.DecimalFormatSymbols.kPlusSignSymbol)

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
        factors: dict[int, int] = {}
        for prime in (2, 5):
            factors[prime] = 0
            while residue % prime == 0:
                residue //= prime
                factors[prime] += 1
        if residue == 1:
            decimal_places = max(factors.values())
            with localcontext() as context:
                context.prec = len(str(abs(top))) + decimal_places + 1
                result = Decimal(top) / Decimal(bottom)
        else:
            with localcontext() as context:
                context.prec = len(str(abs(top))) + 13
                result = (Decimal(top) / Decimal(bottom)).quantize(Decimal("1.000000000000"))
        rendered = format(result, "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered

    def _vulgar_parts(self, character: str) -> tuple[int, int] | None:
        normalized = self._nfkc.normalize(character)
        pieces = normalized.split("\N{FRACTION SLASH}")
        if len(pieces) != 2 or not all(piece.isdecimal() for piece in pieces):
            return None
        return int(pieces[0]), int(pieces[1])

    def _match_vulgar(self, text: str, start: int, number_start: int, negative: bool):
        first_end = self._digit_run(text, number_start)
        whole_end = first_end
        vulgar_start = first_end
        if vulgar_start < len(text) and text[vulgar_start] in _SPACES:
            vulgar_start += 1
        parts = self._vulgar_parts(text[vulgar_start : vulgar_start + 1])
        if parts is None:
            if first_end != number_start:
                return None
            vulgar_start = number_start
            parts = self._vulgar_parts(text[vulgar_start : vulgar_start + 1])
            if parts is None:
                return None
            whole_end = number_start
        numerator, denominator = parts
        if denominator == 0:
            return None
        end = vulgar_start + 1
        captures: list[Capture] = []
        if start != number_start:
            captures.append(
                Capture("sign", start, number_start, text[start:number_start], None, "symbol")
            )
        whole = 0
        if whole_end > number_start:
            surface = text[number_start:whole_end]
            whole = int(self._ascii(surface))
            captures.append(
                Capture("whole", number_start, whole_end, surface, str(whole), "numeric")
            )
        surface = text[vulgar_start:end]
        captures.extend(
            (
                Capture("numerator", vulgar_start, end, surface, str(numerator), "numeric"),
                Capture("denominator", vulgar_start, end, surface, str(denominator), "numeric"),
            )
        )
        decimal = self._canonical(whole, numerator, denominator)
        if negative:
            decimal = "-" + decimal
        return end, tuple(captures), NumberValue(decimal, None)

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        if start > 0 and (text[start - 1] in self._digits or text[start - 1] in _SLASHES):
            return None
        number_start = start
        negative = False
        for sign, is_negative in ((self._minus, True), (self._plus, False)):
            if sign and text.startswith(sign, number_start):
                number_start += len(sign)
                negative = is_negative
                break

        vulgar = self._match_vulgar(text, start, number_start, negative)
        if vulgar is not None:
            return vulgar

        first_end = self._digit_run(text, number_start)
        if first_end == number_start:
            return None

        whole_capture: Capture | None = None
        whole_value = 0
        numerator_start, numerator_end = number_start, first_end
        cursor = first_end
        if cursor < len(text) and text[cursor] in _SPACES:
            after_space = cursor + 1
            candidate_end = self._digit_run(text, after_space)
            if (
                candidate_end > after_space
                and text[candidate_end : candidate_end + 1]
                and (text[candidate_end] in _SLASHES)
            ):
                whole_surface = text[number_start:first_end]
                whole_value = int(self._ascii(whole_surface))
                whole_capture = Capture(
                    "whole",
                    number_start,
                    first_end,
                    whole_surface,
                    self._ascii(whole_surface),
                    "numeric",
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
        if start != number_start:
            captures.append(
                Capture("sign", start, number_start, text[start:number_start], None, "symbol")
            )
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
        if negative:
            decimal = "-" + decimal
        return denominator_end, tuple(captures), NumberValue(decimal=decimal, currency=None)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible fractions in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


class FlexibleOrdinalDetector:
    """Recognize ordinal numerals (``1st``, ``第21``) using reflective CLDR affixes.

    The ``ordinal:flexible`` type marks recall candidates. Ordinal affixes are obtained
    reflectively by *forward* formatting: a candidate integer is rendered with every
    public ``icu.RuleBasedNumberFormat`` ``ORDINAL`` rule set, and the prefix and suffix
    are the non-digit parts around each rendering. No affix is hard-coded, and no fragile
    ordinal *parse* is attempted. A surface is accepted only when its affixes match a pair
    ICU generates for the parsed value, so ``21th`` is rejected while ``21st`` is not.

    Known limitation: as a defensive cross-locale constraint, RBNF ordinal formatting is
    treated as reliable only through the signed-32-bit boundary (``2^31 - 1``). Above that
    boundary it can return an incorrect suffix, and for very large integers it can raise
    an ICU or ``SystemError`` exception. Such inputs are not deposited. Future
    large-ordinal correctness awaits PyICU exposing ordinal plural rules (absent in 78.3),
    or embedding CLDR ordinal-plural data; the affix can then be derived reflectively from
    the ordinal plural category.
    """

    group = "ordinal"
    type = "ordinal:flexible"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        icu_locale = icu.Locale(locale)
        self._rbnf = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, icu_locale)
        self._rule_set_names = tuple(
            name
            for index in range(self._rbnf.getNumberOfRuleSetNames())
            if (name := self._rbnf.getRuleSetName(index)).startswith("%")
            and not name.startswith("%%")
        )
        self._digits = _locale_digit_map(icu_locale)
        self._spec = NumberFormatSpec(locale, "decimal")

    def _digit_run(self, text: str, start: int) -> tuple[int, int]:
        cursor = start
        value = 0
        while cursor < len(text) and text[cursor] in self._digits:
            value = value * 10 + self._digits[text[cursor]]
            cursor += 1
        return cursor, value

    def _affixes(self, value: int) -> set[tuple[str, str]]:
        if value > _MAX_RBNF_ORDINAL_VALUE:
            return set()

        affixes: set[tuple[str, str]] = set()
        rule_set_names: tuple[str | None, ...] = self._rule_set_names or (None,)
        for name in rule_set_names:
            try:
                rendered = (
                    self._rbnf.format(value, name) if name is not None else self._rbnf.format(value)
                )
            except (icu.ICUError, SystemError):
                return set()
            digit_indexes = [
                index
                for index, character in enumerate(rendered)
                if character in self._digits or character.isdigit()
            ]
            if digit_indexes:
                affixes.add((rendered[: digit_indexes[0]], rendered[digit_indexes[-1] + 1 :]))
        return affixes

    def _match(self, text: str, start: int) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        for digit_start in range(start, len(text)):
            if text[digit_start] not in self._digits:
                continue
            if digit_start > 0 and text[digit_start - 1] in self._digits:
                continue
            digit_end, value = self._digit_run(text, digit_start)
            if value < 1:
                continue
            matched = None
            for prefix, suffix in sorted(
                self._affixes(value), key=lambda pair: len(pair[0]) + len(pair[1]), reverse=True
            ):
                if not prefix and not suffix:
                    continue
                if text[start:digit_start].casefold() != prefix.casefold():
                    continue
                affix_end = digit_end + len(suffix)
                if text[digit_end:affix_end].casefold() == suffix.casefold():
                    matched = prefix, suffix, affix_end
                    break
            if matched is None:
                continue
            prefix, suffix, affix_end = matched
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


def _detect_flexible(
    text: str,
    locale: str,
    type_label: str,
    spec: object | None,
    match: Callable[[str, int], tuple[int, tuple[Capture, ...], object] | _FlexibleMatch | None],
) -> list[ValueDetection]:
    starts = sorted({span["start"] for span in break_grapheme_spans(text, locale)})
    detections: list[ValueDetection] = []
    cursor = 0
    for start in starts:
        if start < cursor:
            continue
        result = match(text, start)
        if result is None:
            continue
        if isinstance(result, _FlexibleMatch):
            end, captures, value = result.end, result.captures, result.value
            match_spec = result.spec if result.spec is not None else spec
        else:
            end, captures, value = result
            match_spec = spec
        detections.append(
            ValueDetection(
                text=text[start:end],
                start=start,
                end=end,
                type=type_label,
                value=value,
                captures=captures,
                spec=match_spec,
            )
        )
        cursor = end
    return detections
