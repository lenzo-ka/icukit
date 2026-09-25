"""Flexible, CLDR-derived recognizers for non-canonical value surfaces.

Recognizers are the recall-oriented counterpart to the strict detectors in
:mod:`icukit.detectors`. They deposit structurally valid candidates without requiring the
surface to equal ICU's canonical formatting; the existing resolver can then select among
those candidates unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from functools import cache, lru_cache
from itertools import chain, product
from math import gcd

import icu

from ._offsets import boundary_maps
from .breaker import break_grapheme_spans
from .detectors import (
    _EXTENDING_CATEGORIES,
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
    UnitValue,
    ValueDetection,
    _date_fields,
    _DateField,
    _is_pattern_letter,
    _pattern_runs,
    _word_edges,
    _word_interior_offsets,
)
from .unit_surfaces import curated_currency_surfaces, curated_unit_surfaces

__all__ = [
    "AlphanumericRunsDetector",
    "FlexibleMixedMeasureDetector",
    "AlphanumericRunsValue",
    "PluralNumeralDetector",
    "FlexibleCompactDetector",
    "FlexibleCurrencyDetector",
    "FlexibleCurrencyNameDetector",
    "FlexibleDateDetector",
    "FlexibleDateIntervalDetector",
    "FlexibleFractionDetector",
    "FlexibleMeasureDetector",
    "FlexibleNumberDetector",
    "FlexibleOrdinalDetector",
    "FlexiblePercentDetector",
    "FlexibleRelativeDateDetector",
    "FlexibleScientificDetector",
    "FlexibleSpelloutDetector",
    "FlexibleTimeDetector",
    "FlexibleTextDateDetector",
    "LetterNameDetector",
    "SingleLetterWordDetector",
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
# pronunciations for individual letters. The sole English regional divergence, Z, is
# resolved separately because CLDR carries neither "zee" nor "zed".
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
# CLDR has no locale word lists. Keep these case-sensitive lexical entries small.
_SINGLE_LETTER_WORDS = {"en": frozenset({"I", "a", "A", "O"})}


def _is_apostrophe(character: str) -> bool:
    """A quotation mark that Unicode word breaking treats as joining a word.

    Word_Break Single_Quote (U+0027) and MidNumLet among the quotation marks (U+2019,
    U+2018) join "C's" into one word; the double quote and guillemets do not, and "."
    is MidNumLet but no quotation mark.
    """
    if not character or not icu.Char.hasBinaryProperty(character, icu.UProperty.QUOTATION_MARK):
        return False
    value = icu.Char.getIntPropertyValue(character, icu.UProperty.WORD_BREAK)
    return value in {icu.UWordBreakValues.SINGLE_QUOTE, icu.UWordBreakValues.MIDNUMLET}


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


def _continues_letter_token(text: str, index: int, direction: int) -> bool:
    """Whether the character at ``index`` joins a neighboring letter token."""
    character = text[index]
    if _is_word_character(character):
        return True
    if icu.Char.charType(character) == icu.UCharCategory.CONNECTOR_PUNCTUATION:
        return True
    if not icu.Char.hasBinaryProperty(character, icu.UProperty.QUOTATION_MARK):
        return False
    beyond = index + direction
    return 0 <= beyond < len(text) and _is_word_character(text[beyond])


def _is_isolated_letter(text: str, start: int) -> bool:
    # The shared word helper stays unchanged because widening it would alter existing
    # detector boundaries. Letter readings additionally exclude identifiers and contractions.
    return not (
        start > 0
        and _continues_letter_token(text, start - 1, -1)
        or start + 1 < len(text)
        and _continues_letter_token(text, start + 1, 1)
    )


def _ends_letter_token(text: str, end: int) -> bool:
    return end == len(text) or not _continues_letter_token(text, end, 1)


def _letter_suffix_end(text: str, start: int) -> int | None:
    """The end of a letter's plural or possessive suffix: "C's", "p's", or "Cs".

    The suffix is "s" after an apostrophe (see :func:`_is_apostrophe`), or a bare "s"
    after a capital. "As" and "Is" are words as well, but both readings are kept as
    candidates for the prior to rank rather than excluded by a word list, which CLDR
    does not carry. Anything else that continues the token, such as the "m" of "I'm",
    is no suffix.
    """
    after = start + 1
    if (
        _is_apostrophe(text[after : after + 1])
        and text[after + 1 : after + 2] == "s"
        and _ends_letter_token(text, after + 2)
    ):
        return after + 2
    if (
        text[start].isupper()
        and text[after : after + 1] == "s"
        and _ends_letter_token(text, after + 1)
    ):
        return after + 1
    return None


class LetterNameDetector:
    """Recognize an isolated ASCII Latin letter as its locale's letter name.

    CLDR supplies alphabet repertoires but not the spoken names of their members, so
    supported locales use a small lexical table. Unsupported locale languages produce no
    candidates.

    A letter may carry a plural or possessive suffix ("C's", "Cs"): the detection then
    spans the whole token, with the letter in the ``letter`` capture and the rest in a
    ``suffix`` capture.
    """

    group = "letter"
    type = "letter:name"

    # A capture means both "I have structure to report" and "do not eliminate me" in
    # resolver geometry. New competing reading types need to account for both meanings.

    def __init__(self, locale: str) -> None:
        self.locale = locale
        icu_locale = icu.Locale(locale)
        self._names = _LETTER_NAMES.get(icu_locale.getLanguage())
        self._z_name = "zed" if icu_locale.getCountry() not in {"", "US"} else "zee"

    def detect(self, text: str) -> list[ValueDetection]:
        """Return isolated letter-name candidates in source order."""
        if self._names is None:
            return []
        detections = []
        for start, letter in enumerate(text):
            if not ("A" <= letter <= "Z" or "a" <= letter <= "z"):
                continue
            if start > 0 and _continues_letter_token(text, start - 1, -1):
                continue
            if _ends_letter_token(text, start + 1):
                end = start + 1
            else:
                end = _letter_suffix_end(text, start)
                if end is None:
                    continue
            folded = letter.lower()
            value = self._z_name if folded == "z" else self._names[ord(folded) - ord("a")]
            captures = [Capture("letter", start, start + 1, letter, letter)]
            if end > start + 1:
                captures.append(Capture("suffix", start + 1, end, text[start + 1 : end]))
            detections.append(
                ValueDetection(
                    text=text[start:end],
                    start=start,
                    end=end,
                    type=self.type,
                    value=value,
                    captures=tuple(captures),
                    spec=None,
                )
            )
        return detections


@dataclass(frozen=True)
class AlphanumericRunsValue:
    """A token read as its runs: ``(("digits", "3"), ("letters", "D"))`` for "3D"."""

    runs: tuple[tuple[str, str], ...]


def _run_kind(character: str) -> str:
    if icu.Char.isdigit(character):
        return "digits"
    if icu.Char.isalpha(character):
        return "letters"
    return "separator"


class AlphanumericRunsDetector:
    """Read a word that mixes letters and digits as its runs.

    "3D" is digits "3" then letters "D", "5pm" is "5" then "pm", and "2Q22" is "2", "Q",
    "22": the path a speaker takes when a token has no reading of its own ("three d",
    "five p m"). It spans one ICU word with at least one digit and one letter, and it is
    an alternative beside any other reading of the word, never a replacement for one.
    Each run is a ``digits``, ``letters``, or ``separator`` capture in source order; a
    combining mark or format character stays in the run it extends. A word whose letters
    are in a script ICU breaks between letters (Thai, Lao, Khmer, Myanmar) has no runs
    reading, since ICU's dictionary segmentation does not separate its digits into a
    word of their own.
    """

    group = "alnum"
    type = "alnum:runs"

    def __init__(self, locale: str) -> None:
        self.locale = locale

    def detect(self, text: str) -> list[ValueDetection]:
        """Return one runs reading per mixed letter-and-digit word, in source order."""
        edges = sorted(_word_edges(text, self.locale))
        detections = []
        for start, end in zip(edges, edges[1:], strict=False):
            word = text[start:end]
            letters = [character for character in word if icu.Char.isalpha(character)]
            if not letters or not any(icu.Char.isdigit(character) for character in word):
                continue
            if any(icu.Script.getScript(letter).breaksBetweenLetters() for letter in letters):
                continue
            runs: list[list] = []
            for offset, character in enumerate(word, start):
                extends = icu.Char.charType(character) in _EXTENDING_CATEGORIES
                kind = runs[-1][0] if extends and runs else _run_kind(character)
                if runs and runs[-1][0] == kind:
                    runs[-1][2] = offset + 1
                else:
                    runs.append([kind, offset, offset + 1])
            captures = tuple(
                Capture(kind, run_start, run_end, text[run_start:run_end], text[run_start:run_end])
                for kind, run_start, run_end in runs
            )
            value = AlphanumericRunsValue(tuple((c.name, c.text) for c in captures))
            detections.append(
                ValueDetection(
                    text=word,
                    start=start,
                    end=end,
                    type=self.type,
                    value=value,
                    captures=captures,
                    spec=None,
                )
            )
        return detections


# Hand-rolled, as CLDR carries no plural or decade form of a numeral: the letters a
# language writes after a numeral to make it plural ("1990s", "the 20s"), keyed by
# language. The apostrophe variant ("1990's", "'90s") is read by _is_apostrophe.
_PLURAL_NUMERAL_SUFFIXES = {"en": ("s",)}


def _plural_suffix(text: str, cursor: int, locale: str) -> tuple[int, tuple[Capture, ...]] | None:
    """A plural suffix at ``cursor`` ("s" or "'s" in English) that ends its word."""
    suffixes = _PLURAL_NUMERAL_SUFFIXES.get(icu.Locale(locale).getLanguage(), ())
    captures = []
    if _is_apostrophe(text[cursor : cursor + 1]):
        captures.append(Capture("apostrophe", cursor, cursor + 1, text[cursor]))
        cursor += 1
    for suffix in suffixes:
        end = cursor + len(suffix)
        if text.startswith(suffix, cursor) and _ends_letter_token(text, end):
            return end, (*captures, Capture("suffix", cursor, end, suffix))
    return None


class PluralNumeralDetector:
    """Recognize a numeral made plural: "1990s", "1990's", "'90s", "100s", "the 20s".

    The value is the written number (``1990``, and ``90`` for "'90s", whose century is
    elided), never a guessed decade or century: whether "1900s" is a decade or a century,
    and whether "100s" is "hundreds" or "one hundreds", is for verbalization to offer.
    Captures: ``number``, the ``suffix``, an ``apostrophe`` before the suffix if written,
    and an ``elision`` apostrophe before the number if written. Digits are read by ICU's
    digit values, so a locale's native digits count; the suffix letters are a small
    per-language table, since CLDR has none, and a language without an entry has no
    readings.
    """

    group = "number"
    type = "number:plural"

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._suffixes = _PLURAL_NUMERAL_SUFFIXES.get(icu.Locale(locale).getLanguage(), ())

    def detect(self, text: str) -> list[ValueDetection]:
        """Return plural-numeral readings in source order."""
        if not self._suffixes:
            return []
        edges = _word_edges(text, self.locale)
        detections = []
        for start in sorted(edges):
            if start >= len(text) or not icu.Char.isdigit(text[start]):
                continue
            found = self._match(text, start, edges)
            if found is not None:
                detections.append(found)
        return detections

    def _match(self, text: str, start: int, edges: frozenset[int]) -> ValueDetection | None:
        cursor = start
        while cursor < len(text) and icu.Char.isdigit(text[cursor]):
            cursor += 1
        number_end = cursor
        captures = []
        begin = start
        if (
            start > 0
            and _is_apostrophe(text[start - 1])
            and (start - 1 == 0 or not text[start - 2].isalnum())
        ):
            begin = start - 1
            captures.append(Capture("elision", begin, start, text[begin:start]))
        digits = "".join(str(icu.Char.digit(character, 10)) for character in text[start:number_end])
        captures.append(Capture("number", start, number_end, text[start:number_end], int(digits)))
        if cursor < len(text) and _is_apostrophe(text[cursor]):
            captures.append(Capture("apostrophe", cursor, cursor + 1, text[cursor]))
            cursor += 1
        for suffix in self._suffixes:
            if text.startswith(suffix, cursor) and cursor + len(suffix) in edges:
                end = cursor + len(suffix)
                captures.append(Capture("suffix", cursor, end, suffix))
                return ValueDetection(
                    text=text[begin:end],
                    start=begin,
                    end=end,
                    type=self.type,
                    value=NumberValue(str(int(digits)), None),
                    captures=tuple(captures),
                    spec=None,
                )
        return None


class SingleLetterWordDetector:
    """Recognize an isolated letter that is a word in its locale.

    CLDR does not supply word lists, so supported locales use a small case-sensitive
    lexical set. Unsupported locale languages produce no candidates.
    """

    group = "word"
    type = "word:single-letter"

    # A capture means both "I have structure to report" and "do not eliminate me" in
    # resolver geometry. New competing reading types need to account for both meanings.

    def __init__(self, locale: str) -> None:
        self.locale = locale
        self._words = _SINGLE_LETTER_WORDS.get(icu.Locale(locale).getLanguage(), frozenset())

    def detect(self, text: str) -> list[ValueDetection]:
        """Return isolated one-letter word candidates in source order."""
        detections = []
        for start, letter in enumerate(text):
            if letter not in self._words:
                continue
            end = start + 1
            if not _is_isolated_letter(text, start):
                continue
            detections.append(
                ValueDetection(
                    text=letter,
                    start=start,
                    end=end,
                    type=self.type,
                    value=letter,
                    captures=(Capture("letter", start, end, letter, letter),),
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


@cache
def _language_locale_names(language: str, names: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """The ICU locale names a widened reader reads for ``language``, in name order.

    Every available locale of the language by default; only ``names`` when a caller chose
    them (see :func:`_locale_selection`).
    """
    if names is not None:
        return tuple(sorted(names))
    return tuple(
        name
        for name in sorted(icu.Locale.getAvailableLocales())
        if icu.Locale(name).getLanguage() == language
    )


def _locale_selection(locale: str, locales: Iterable[str] | None) -> tuple[str, ...] | None:
    """The canonical names a detector for ``locale`` reads, from a caller's ``locales``.

    ``None`` keeps the default, every ICU locale of the language. Otherwise the chosen
    locales, which must share ``locale``'s language, together with ``locale`` itself.
    """
    if locales is None:
        return None
    base = icu.Locale(locale)
    chosen = {base.getName()}
    for name in [locales] if isinstance(locales, str) else locales:
        other = icu.Locale(name)
        if other.getLanguage() != base.getLanguage():
            raise ValueError(f"locale {name!r} is not a locale of {locale!r}'s language")
        chosen.add(other.getName())
    return tuple(sorted(chosen))


@cache
def _language_locales(locale: str, names: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """``locale`` first, then the other locales of its language a detector reads.

    Text in a language may be written in any of its locales' conventions: en_US text
    quotes "5 kilometres" as en_GB formats it, and "250 000" as en_ZA does.
    """
    base = icu.Locale(locale).getName()
    language = icu.Locale(locale).getLanguage()
    return (locale, *(name for name in _language_locale_names(language, names) if name != base))


@cache
def _language_date_structures(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...]:
    """The numeric short-date structures CLDR gives the locales of ``language``.

    Each is ``(fields, separators, pattern)`` as :class:`FlexibleDateDetector` reads a
    pattern, in locale order, without duplicates.
    """
    structures = {}
    for name in _language_locale_names(language, names):
        locale = icu.Locale(name)
        pattern = icu.DateFormat.createDateInstance(icu.DateFormat.kShort, locale).toPattern()
        structure = FlexibleDateDetector._date_structure(pattern)
        if structure is not None and structure not in structures:
            structures[structure] = pattern
    return tuple(
        (fields, separators, pattern) for (fields, separators), pattern in structures.items()
    )


@cache
def _language_era_date_structures(language: str, names: tuple[str, ...] | None = None):
    """CLDR's ``GyMd`` patterns for the locales of ``language``, read around their era.

    Each is ``(fields, separators, pattern, era_first, era_literal)``: the numeric date
    as :class:`FlexibleDateDetector` reads a short-date pattern, and where the era
    stands ("M/d/y G" after, with " "; ja's "Gy/M/d" before, with nothing).
    """
    structures = {}
    for name in _language_locale_names(language, names):
        generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(name))
        pattern = generator.getBestPattern("GyMd")
        found = _era_date_structure(pattern)
        if found is not None:
            structures.setdefault(found, pattern)
    return tuple((*structure, pattern) for structure, pattern in structures.items())


def _era_date_structure(pattern: str):
    """``pattern``'s numeric date and its era's place: ``(fields, separators, era_first,
    era_literal)``, or ``None`` where the era is not at one end."""
    stripped = pattern.rstrip("G")
    if stripped != pattern and "G" not in stripped:
        core = stripped.rstrip(" \u00a0\u202f,")
        era_first, literal = False, stripped[len(core) :]
    else:
        stripped = pattern.lstrip("G")
        if stripped == pattern or "G" in stripped:
            return None
        core = stripped.lstrip(" \u00a0\u202f,")
        era_first, literal = True, stripped[: len(stripped) - len(core)]
    structure = FlexibleDateDetector._date_structure(core)
    if structure is None or "'" in literal:
        return None
    return (*structure, era_first, literal)


class FlexibleDateDetector:
    """Recognize flexible numeric dates using CLDR short-date structures.

    The stable ``date:flexible`` type distinguishes recall candidates from strict,
    skeleton-specific date detections. Two-digit years retain their observed value;
    this detector deposits one maximal candidate rather than expanding a century.

    Every numeric short-date structure CLDR gives a locale of the same language is
    read, the locale's own included, and each distinct valid date is deposited: en_US
    reads "03/05/2013" both month first (its own pattern) and day first (en_GB's), and
    reads "31.12.2012" through en_CH's dotted pattern. Each reading's spec names the
    pattern it came from. A year written first must have four digits, since a leading
    two-digit year cannot be told from a day ("10-12-14").

    A date with its era reads as CLDR's ``GyMd`` patterns write it ("3/5/2024 AD",
    "15/03/44 BC"), the era's names the language's (see ``_language_eras``); the value
    leads with ``("G", era)``.
    """

    group = "date"
    type = "date:flexible"

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        icu_locale = icu.Locale(locale)
        date_format = icu.DateFormat.createDateInstance(icu.DateFormat.kShort, icu_locale)
        self.pattern = date_format.toPattern()
        structure = self._date_structure(self.pattern)
        self._inert = structure is None
        self._fields, self._separators = structure or ((), ())
        self._calendar = icu.Calendar.createInstance(icu_locale).getType()
        self._structures = tuple(
            dict.fromkeys(
                ((self._fields, self._separators, self.pattern),) * (structure is not None)
                + _language_date_structures(icu_locale.getLanguage(), self.locales)
            )
        )

        self._digits = _locale_digit_map(icu_locale)
        self._spec = DateFormatSpec(locale, "yMd", self.pattern, self._calendar)
        language = icu_locale.getLanguage()
        self._era_structures = _language_era_date_structures(language, self.locales)
        self._eras = _language_eras(language, self.locales)

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

    def _structure_matcher(self, fields, separators, pattern):
        spec = DateFormatSpec(self.locale, "yMd", pattern, self._calendar)

        def match(text: str, start: int) -> _FlexibleMatch | None:
            found = self._match_structure(text, start, fields, separators)
            if found is None:
                return None
            end, captures, value = found
            return _FlexibleMatch(end, captures, value, spec)

        return match

    def _match_structure(
        self,
        text: str,
        start: int,
        fields: tuple[str, ...],
        separators: tuple[str, ...],
        checked: bool = True,
    ) -> tuple[int, tuple[Capture, ...], DateTimeValue] | None:
        """The date at ``start``; ``checked`` confirms it exists (the era reader checks
        it in its era instead)."""
        cursor = start
        values: dict[str, int] = {}
        captures: list[Capture] = []
        for index, field in enumerate(fields):
            field_start = cursor
            cursor, surface, value = self._digit_run(text, cursor)
            width = cursor - field_start
            year_widths = {4} if index == 0 else {2, 4}
            valid_width = width in (year_widths if field == "y" else {1, 2})
            valid_range = field == "y" or field == "M" and 1 <= value <= 12
            valid_range = valid_range or field == "d" and 1 <= value <= 31
            if not valid_width or not valid_range:
                return None
            values[field] = value
            captures.append(Capture(field, field_start, cursor, surface, value, "numeric"))
            if index < len(separators):
                separator = separators[index]
                if not text.startswith(separator, cursor):
                    return None
                cursor += len(separator)

        if checked:
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

    def _era_at(
        self, text: str, cursor: int, before_digits: bool = False
    ) -> tuple[int, int, str] | None:
        """The era at ``cursor``, ending a word, or touching a digit where the pattern
        writes the era straight before the year (``before_digits``)."""
        for form, index, width in self._eras:
            end = cursor + len(form)
            if text[cursor:end] != form:
                continue
            if end == len(text) or not text[end].isalnum():
                return end, index, width
            if before_digits and text[end] in self._digits:
                return end, index, width
        return None

    def _era_matcher(self, fields, separators, era_first, literal, pattern):
        spec = DateFormatSpec(self.locale, "GyMd", pattern, self._calendar)

        def match(text: str, start: int) -> _FlexibleMatch | None:
            if era_first:
                found = self._era_at(text, start, before_digits=not literal)
                if found is None or not text.startswith(literal, found[0]):
                    return None
                era_start, (era_end, era, width) = start, found
                date = self._match_structure(
                    text, era_end + len(literal), fields, separators, checked=False
                )
                if date is None:
                    return None
                end, captures, value = date
            else:
                date = self._match_structure(text, start, fields, separators, checked=False)
                if date is None or not text.startswith(literal, date[0]):
                    return None
                end, captures, value = date
                era_start = end + len(literal)
                found = self._era_at(text, era_start)
                if found is None:
                    return None
                end, era, width = found
                era_end = end
            if not self._valid_in_era(value, era):
                return None
            era_capture = Capture("era", era_start, era_end, text[era_start:era_end], era, width)
            joined = (era_capture, *captures) if era_first else (*captures, era_capture)
            dated = DateTimeValue((("G", era), *value.fields), value.calendar)
            return _FlexibleMatch(end, joined, dated, spec)

        return match

    def _valid_in_era(self, value: DateTimeValue, era: int) -> bool:
        """Whether the date exists in the era (a leap day in 44 BC, say)."""
        fields = dict(value.fields)
        calendar = icu.Calendar.createInstance(icu.Locale(self.locale))
        calendar.setLenient(False)
        calendar.clear()
        try:
            calendar.set(icu.UCalendarDateFields.ERA, era)
            calendar.set(icu.UCalendarDateFields.YEAR, fields["y"])
            calendar.set(icu.UCalendarDateFields.MONTH, fields["M"] - 1)
            calendar.set(icu.UCalendarDateFields.DATE, fields["d"])
            calendar.getTime()
        except icu.ICUError:
            return False
        return True

    def detect(self, text: str) -> list[ValueDetection]:
        """Return every structure's flexible numeric dates, distinct, in source order.

        A date with its era is its own reading, beside the date without it.
        """
        if self._inert:
            return []
        found: dict[tuple[int, int, object], ValueDetection] = {}
        matchers = [
            self._structure_matcher(fields, separators, pattern)
            for fields, separators, pattern in self._structures
        ] + [self._era_matcher(*structure) for structure in self._era_structures]
        for matcher in matchers:
            for detection in _detect_flexible(text, self.locale, self.type, self._spec, matcher):
                key = (detection["start"], detection["end"], detection["value"])
                found.setdefault(key, detection)
        return sorted(found.values(), key=lambda d: (d["start"], d["end"]))


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
# CLDR pattern grammar, not locale data: the zone letters, whose text SimpleDateFormat
# parses and writes ("ET", "GMT-5", "Eastern Time").
_ZONE_LETTERS = frozenset("zZOvVXx")
# The interval reader also models the 12-hour clock with its AM/PM marker ("h", "K", "a")
# and one time zone; a day period ("B", "b") and the rest stay unmodeled.
_MODELED_INTERVAL_LETTERS = frozenset(_MODELED_DATE_LETTERS | {"h", "K", "a"} | _ZONE_LETTERS)
_INTERVAL_VALUE_ORDER = ("y", "M", "d", "H", "h", "m", "s")
# hand-rolled: ICU publishes no sample intervals, so these are chosen here -- two start
# instants and, per greatest-difference field, an end that differs at that field and at
# every smaller one. The values are distinctive (1- vs 2-digit month, day and hour, a
# morning start) so that each field's width shows; ICU renders every one of them, and a
# recovered pattern must reproduce ICU's output for both samples or it is dropped.
_INTERVAL_SAMPLE_STARTS = ((2024, 2, 5, 10, 7, 9), (2031, 10, 23, 1, 52, 8))
_INTERVAL_SAMPLE_ENDS = {
    icu.UCalendarDateFields.YEAR: ((2025, 3, 9, 15, 38, 21), (2032, 11, 28, 13, 54, 31)),
    icu.UCalendarDateFields.MONTH: ((2024, 3, 9, 15, 38, 21), (2031, 11, 28, 13, 54, 31)),
    icu.UCalendarDateFields.DATE: ((2024, 2, 7, 15, 38, 21), (2031, 10, 28, 13, 54, 31)),
    icu.UCalendarDateFields.AM_PM: ((2024, 2, 5, 15, 38, 21), (2031, 10, 23, 13, 54, 31)),
    icu.UCalendarDateFields.HOUR: ((2024, 2, 5, 11, 38, 21), (2031, 10, 23, 6, 54, 31)),
    icu.UCalendarDateFields.MINUTE: ((2024, 2, 5, 10, 38, 21), (2031, 10, 23, 1, 54, 31)),
    icu.UCalendarDateFields.SECOND: ((2024, 2, 5, 10, 7, 21), (2031, 10, 23, 1, 52, 31)),
}


def _interval_fields(pattern: str) -> tuple[_DateField, ...]:
    """The date fields of one interval side, plus its AM/PM marker when it has one."""
    fields = list(_date_fields(pattern))
    for letter, width in _pattern_runs(pattern):
        if letter == "a":
            field_id = _letter_field_id(letter)
            fields.append(
                _DateField(letter, width, "ampm", icu.Calendar.AM_PM, field_id, "symbol", False)
            )
    return tuple(fields)


@cache
def _pattern_chars() -> str:
    """ICU's date pattern letters, indexed by ``UDateFormatField`` (``G`` is 0, ``y`` 1)."""
    return str(icu.DateFormatSymbols(icu.Locale.getRoot()).getLocalPatternChars())


def _letter_field_id(letter: str) -> int:
    """ICU's ``UDateFormatField`` id for pattern ``letter``, or -1 for a non-field letter."""
    return _pattern_chars().find(letter)


def _leads_with_digit_field(pattern: str) -> bool:
    """Whether ``pattern`` opens with a field ICU always writes in digits.

    CLDR pattern grammar: a day, hour, minute, second, or numeric month (``M``/``MM``)
    renders as decimal digits in any numbering system. A year is left out, since a
    calendar may write one in words (the Japanese first year, "元年").
    """
    if not pattern or not _is_pattern_letter(pattern[0]):
        return False
    letter, width = _pattern_runs(pattern)[0]
    return letter in {"d", "H", "h", "K", "k", "m", "s"} or letter in {"M", "L"} and width <= 2


_INTERVAL_DATING_FIELDS = {
    "y": icu.UCalendarDateFields.YEAR,
    "M": icu.UCalendarDateFields.MONTH,
    "d": icu.UCalendarDateFields.DATE,
}


def _interval_datings(pattern: str) -> tuple[dict[str, int], ...]:
    """The dates a zoned interval's sides are parsed and gated on.

    An interval that shows no year falls on 1970, where a zone writes only its winter
    name, and a parsed daylight name ("EDT") shifts the clock an hour. hand-rolled: such an
    interval is also tried on a mid-January and a mid-July day of a recent year, to meet
    either hemisphere's standard and daylight names; the dating whose zone name ICU
    writes back is the one that reads. A shown month and day are kept (only the year is
    supplied). The dating never enters the value.
    """
    letters = {letter for letter, _ in _pattern_runs(pattern)}
    if "y" in letters:
        return ({},)
    if letters & {"M", "L", "d"}:
        return ({}, {"y": 2024})
    return ({}, *({"y": 2024, "M": month, "d": 15} for month in (0, 6)))


def _iana_zone_id(zone_id: str) -> str:
    """ICU's IANA form of a zone ID ("Asia/Calcutta" -> "Asia/Kolkata").

    A custom offset zone ("GMT-08:00") has no IANA form and keeps its own ID.
    """
    try:
        return str(icu.TimeZone.getIanaID(zone_id)) or zone_id
    except icu.ICUError:
        return zone_id


# The zone fields ICU writes a zone name with (UTS #35): long and short specific
# ("Eastern Standard Time", "EST"), long and short generic ("Eastern Time", "ET"), the
# generic location ("New York Time"), and ISO 8601 ("Z").
_ZONE_NAME_PATTERNS = ("zzzz", "z", "vvvv", "v", "VVVV", "X")


_SECONDS_PER_DAY = 86400


def _today() -> int:
    """Today's day number (days since 1970-01-01), read from the clock on every call."""
    return int(icu.Calendar.getNow() // _SECONDS_PER_DAY)


def _day_of(year: int, month: int, day: int) -> int:
    """The day number of a Gregorian date (``month`` 1-12)."""
    calendar = icu.GregorianCalendar(icu.TimeZone.getGMT(), icu.Locale.getRoot())
    calendar.clear()
    calendar.set(year, month - 1, day)
    return int(calendar.getTime() // _SECONDS_PER_DAY)


def _reading_days(fields: dict[str, int] | None = None) -> tuple[int, ...]:
    """The days a reading's zone text is read on, the first the one its zone is taken on.

    A reading with a month is read on its date, in its year or else this one ("Jul 5":
    July 5 of this year; a month with no day, its 15th). A reading with no date (a bare
    time) is read today, and written for the zone on today, mid-January or mid-July of
    this year: a daylight name ("EDT", "IST" for Irish summer time) names its zone in
    its season, whatever today is.
    """
    today = _today()
    calendar = icu.GregorianCalendar(icu.TimeZone.getGMT(), icu.Locale.getRoot())
    calendar.setTime(float(today * _SECONDS_PER_DAY))
    year = calendar.get(icu.UCalendarDateFields.YEAR)
    if fields and "M" in fields:
        return (_day_of(fields.get("y", year), fields["M"], fields.get("d", 15)),)
    return (today, _day_of(year, 1, 15), _day_of(year, 7, 15))


@cache
def _zone_metazone(zone_id: str, day: int) -> str:
    """The metazone ICU maps ``zone_id`` to on ``day``, or ``zone_id`` if it maps none.

    A metazone is a zone name CLDR shares among regions: America_Eastern is "Eastern
    Time" for America/New_York, America/Toronto and America/Nassau alike, and ICU parses
    such a name to the metazone's zone for the locale's region. Zones of one metazone
    are one zone read in different regions; zones of different metazones (Irish time
    and India time, both "IST") are different zones. The mapping is ICU's
    (``TimeZoneNames.getMetaZoneID``), which changes over time, so it is taken on the
    reading's day (see :func:`_reading_days`). A custom offset zone ("GMT-08:00") has
    no metazone and stands for itself.
    """
    names = icu.TimeZoneNames.createInstance(icu.Locale.getRoot())
    instant = day * _SECONDS_PER_DAY + _SECONDS_PER_DAY / 2
    return names.getMetaZoneID(zone_id, instant) or zone_id


@cache
def _zone_parses(
    zone_text: str, locale: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, str], ...]:
    """Each zone ICU parses ``zone_text`` as, in the locales of the language: ``(ID, locale)``.

    ``SimpleDateFormat`` parses the whole text with each zone field in turn, on a GMT
    calendar whose zone the parse sets, in ``locale`` and then in each other locale of
    its language (see :func:`_language_locales`); the locale is the first that parsed
    the text as that zone. Each ID is canonicalized as :func:`_iana_zone_id` does ("IST"
    in en_IN parses as Asia/Calcutta, read as Asia/Kolkata). A lenient parse also takes
    names ICU no longer writes (en_MO parses "MST" as Asia/Macau), which
    :func:`_zone_writes` weeds out.
    """
    source = icu.UnicodeString(zone_text)
    found: dict[str, str] = {}
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        for pattern in _ZONE_NAME_PATTERNS:
            calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu_locale)
            calendar.clear()
            position = icu.ParsePosition(0)
            icu.SimpleDateFormat(pattern, icu_locale).parse(source, calendar, position)
            if position.getErrorIndex() == -1 and position.getIndex() == len(source):
                found.setdefault(_iana_zone_id(str(calendar.getTimeZone().getID())), name)
                break
    return tuple(found.items())


@cache
def _metazone_zones(metazone: str, day: int) -> tuple[str, ...]:
    """The zones ICU maps to ``metazone`` on ``day`` (none for a zone standing for itself)."""
    names = icu.TimeZoneNames.createInstance(icu.Locale.getRoot())
    instant = day * _SECONDS_PER_DAY + _SECONDS_PER_DAY / 2
    return tuple(
        str(zone_id)
        for zone_id in icu.TimeZone.createEnumeration()
        if names.getMetaZoneID(str(zone_id), instant) == metazone
    )


def _plain_spaces(text: str) -> str:
    return "".join(" " if character in _SPACES else character for character in text)


@cache
def _zone_writes(
    zone_text: str, zone_id: str, locale: str, names: tuple[str, ...] | None, day: int
) -> bool:
    """Whether ICU writes ``zone_text`` for ``zone_id`` on ``day`` in a locale of the language.

    In any zone field (see ``_ZONE_NAME_PATTERNS``), ``locale`` first, for the zone, a
    zone ICU keeps with the same offset and rules (see :func:`_same_rule_zone_ids`: ICU
    writes "UTC" for Etc/UTC, which "UTC" parses as Etc/GMT), or a zone of its metazone
    that day (ICU parses "MST" as America/Denver, whose July name is "MDT", while
    America/Phoenix, of the same Mountain metazone, writes "MST" all year). Spaces
    compare as spaces, as CLDR's no-break spaces are typed as ordinary ones.
    """
    wanted = _plain_spaces(zone_text)
    instant = day * _SECONDS_PER_DAY + _SECONDS_PER_DAY / 2
    others = dict.fromkeys(
        (*_same_rule_zone_ids(zone_id), *_metazone_zones(_zone_metazone(zone_id, day), day))
    )
    others.pop(zone_id, None)
    zones = [icu.TimeZone.createTimeZone(zone_id)]
    zones += [icu.TimeZone.createTimeZone(other) for other in others]
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        for pattern in _ZONE_NAME_PATTERNS:
            formatter = icu.SimpleDateFormat(pattern, icu_locale)
            for zone in zones:
                formatter.setTimeZone(zone)
                if _plain_spaces(str(formatter.format(instant))) == wanted:
                    return True
    return False


def _zone_readings(
    zone_text: str,
    locale: str,
    names: tuple[str, ...] | None = None,
    days: tuple[int, ...] | None = None,
) -> tuple[tuple[str, str], ...]:
    """Each zone ``zone_text`` names, one per metazone: ``(IANA ID, locale)``.

    The zones ICU parses the text as in the locales of the language (see
    :func:`_zone_parses`), each kept only where ICU writes the text for it on one of
    ``days`` (see :func:`_zone_writes`; by default a bare time's, see
    :func:`_reading_days`), and grouped by metazone on the first day (see
    :func:`_zone_metazone`). The locale's region picks the zone of a shared name
    ("Eastern Time" is America/New_York in en_US, America/Toronto in en_CA). A name
    that different metazones share gives each: en_US reads "IST" as en_IE's
    Europe/Dublin and en_IN's Asia/Kolkata. ``locale``'s own zone comes first, then the
    others in locale-name order. The process default zone plays no part.
    """
    return _zone_readings_on(zone_text, locale, names, days or _reading_days())


@cache
def _zone_readings_on(
    zone_text: str, locale: str, names: tuple[str, ...] | None, days: tuple[int, ...]
) -> tuple[tuple[str, str], ...]:
    found: dict[str, tuple[str, str]] = {}
    for zone_id, name in _zone_parses(zone_text, locale, names):
        if not any(_zone_writes(zone_text, zone_id, name, names, day) for day in days):
            continue
        found.setdefault(_zone_metazone(zone_id, days[0]), (zone_id, name))
    return tuple(found.values())


def _zone_key(captures: Iterable[Capture]) -> tuple[object, ...]:
    """The zones a reading's ``time-zone`` captures name, which tell its readings apart."""
    return tuple(capture.value for capture in captures if capture.name == "time-zone")


@cache
def _interval_side_formatter(pattern: str, locale: str):
    """ICU's formatter for one side of an interval pattern, in ``locale``."""
    return icu.SimpleDateFormat(pattern, icu.Locale(locale))


@cache
def _same_rule_zone_ids(zone_id: str) -> tuple[str, ...]:
    """The zones ICU keeps with the same offset and rules as ``zone_id``, other than it.

    ICU parses some zone text to a zone that writes other text: "UTC" and "GMT+0", which
    ICU writes for Etc/UTC, parse to Etc/GMT, which writes "GMT". A zone with the same
    offset and rules gives every endpoint the same instant, so ICU writing the surface
    for any of them is ICU writing it for the zone the text was parsed as.
    """
    zone = icu.TimeZone.createTimeZone(zone_id)
    return tuple(
        other_id
        for other_id in (str(other) for other in icu.TimeZone.createEnumeration())
        if other_id != zone_id
        and (other := icu.TimeZone.createTimeZone(other_id)).getRawOffset() == zone.getRawOffset()
        and other.hasSameRules(zone)
    )


def _zone_run(pattern: str) -> tuple[str, int] | None:
    """The pattern's zone field as ``(letter, width)``, or ``None`` when it has none."""
    runs = _pattern_runs(pattern)
    return next(((letter, width) for letter, width in runs if letter in _ZONE_LETTERS), None)


def _letters_for_field(field_id: int) -> tuple[str, ...]:
    """The pattern letter whose ICU field id is ``field_id``, or none for an unknown id."""
    chars = _pattern_chars()
    return (chars[field_id],) if 0 <= field_id < len(chars) else ()


def _gregorian_instant(values: tuple[int, int, int, int, int, int]) -> float:
    """The instant of a Gregorian wall-clock sample in the default time zone.

    ICU's interval and date formatters write in the default zone, so the sample is read
    in that zone too; each formatter renders the instant in the locale's own calendar.
    """
    calendar = icu.GregorianCalendar(icu.Locale.getRoot())
    calendar.clear()
    names = ("YEAR", "MONTH", "DATE", "HOUR_OF_DAY", "MINUTE", "SECOND")
    for name, value in zip(names, values, strict=True):
        calendar.set(getattr(icu.UCalendarDateFields, name), value)
    return calendar.getTime()


def _interval_layout(formatted) -> tuple[str, list[tuple[int, int]], list[tuple[int, int, int]]]:
    """Read ICU's own structure off a formatted interval, in code-point offsets.

    Returns the text, the spans of the two endpoints (ICU's ``DATE_INTERVAL_SPAN``
    fields, in order), and every date field as ``(start, limit, field id)``.
    """
    text = str(formatted)
    _, u16_to_cp = boundary_maps(text)
    spans: dict[int, tuple[int, int]] = {}
    fields: list[tuple[int, int, int]] = []
    position = icu.ConstrainedFieldPosition()
    while formatted.nextPosition(position):
        start = u16_to_cp[position.getStart()]
        limit = u16_to_cp[position.getLimit()]
        category = position.getCategory()
        if category == icu.UFieldCategory.DATE_INTERVAL_SPAN:
            spans[position.getField()] = (start, limit)
        elif category == icu.UFieldCategory.DATE:
            fields.append((start, limit, position.getField()))
    return text, [spans[index] for index in sorted(spans)], sorted(fields)


def _quoted_literal(text: str) -> str:
    """``text`` as pattern literal text, quoted when it holds a letter or an apostrophe."""
    if any(character == "'" or _is_pattern_letter(character) for character in text):
        return "'" + text.replace("'", "''") + "'"
    return text


@cache
def _recovered_interval_parts(
    locale: str, skeleton: str, calendar_field: int
) -> tuple[str, str, str] | None:
    """Recover the interval pattern ICU uses for ``skeleton`` from ICU's own output.

    ``DateIntervalInfo.getIntervalPattern`` answers only for skeletons CLDR lists; for the
    rest (``yMMMMd``, ``MMMMd``, ``yMMMMEEEEd``, and time skeletons whose dates differ)
    ``DateIntervalFormat`` derives the pattern itself, by adjusting field widths or by
    falling back to a full date and time on each side. This formats sample intervals that
    differ at ``calendar_field`` with ``formatToValue``, whose field positions say which
    text is which date field and which endpoint's span it lies in, and names each field's
    pattern letter and width as the one ``SimpleDateFormat`` renders to that exact text in
    both samples -- trying the skeleton's best pattern first. The result is the
    ``(part1, separator, part2)`` split :func:`_interval_pattern_parts` gives, and it
    stands only if it reproduces ICU's output for every sample.
    """
    ends = _INTERVAL_SAMPLE_ENDS.get(calendar_field)
    if ends is None:
        return None
    icu_locale = icu.Locale(locale)
    dif = icu.DateIntervalFormat.createInstance(skeleton, icu_locale)
    samples = []
    for start_values, end_values in zip(_INTERVAL_SAMPLE_STARTS, ends, strict=True):
        start, end = _gregorian_instant(start_values), _gregorian_instant(end_values)
        text, spans, fields = _interval_layout(dif.formatToValue(icu.DateInterval(start, end)))
        if len(spans) != 2:
            return None  # ICU collapsed the interval to one date at this granularity
        samples.append((start, end, text, spans, fields))
    if len({tuple(field_id for *_, field_id in sample[4]) for sample in samples}) != 1:
        return None

    try:
        best = str(icu.DateTimePatternGenerator.createInstance(icu_locale).getBestPattern(skeleton))
    except icu.ICUError:
        best = ""
    preferred = _pattern_runs(best)

    def letter_run(field_index: int) -> str | None:
        field_id = samples[0][4][field_index][2]
        letters = _letters_for_field(field_id)
        candidates = [(letter, width) for letter, width in preferred if letter in letters]
        candidates += [(letter, width) for letter in letters for width in range(1, 6)]
        for letter, width in candidates:
            formatter = icu.SimpleDateFormat(letter * width, icu_locale)
            for start, end, text, spans, fields in samples:
                field_start, field_limit, _ = fields[field_index]
                instant = start if field_start < spans[1][0] else end
                if str(formatter.format(instant)) != text[field_start:field_limit]:
                    break
            else:
                return letter * width
        return None

    text, spans, fields = samples[0][2:]
    split1, split2 = spans[0][1], spans[1][0]
    # Each side is text[0:split1] and text[split2:]; the separator between holds no field.
    if any(start < split2 and limit > split1 for start, limit, _ in fields):
        return None
    runs = []
    for index in range(len(fields)):
        run = letter_run(index)
        if run is None:
            return None
        runs.append(run)

    def side_pattern(region_start: int, region_end: int) -> str:
        pieces = []
        cursor = region_start
        for (start, limit, _), run in zip(fields, runs, strict=True):
            if region_start <= start and limit <= region_end:
                pieces.append(_quoted_literal(text[cursor:start]))
                pieces.append(run)
                cursor = limit
        pieces.append(_quoted_literal(text[cursor:region_end]))
        return "".join(pieces)

    part1 = side_pattern(0, split1)
    separator = text[split1:split2]
    part2 = side_pattern(split2, len(text))

    formatter1 = icu.SimpleDateFormat(part1, icu_locale)
    formatter2 = icu.SimpleDateFormat(part2, icu_locale)
    for start, end, text, _spans, _fields in samples:
        rendered = str(formatter1.format(start)) + separator + str(formatter2.format(end))
        if rendered != text:
            return None
    return part1, separator, part2


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
    """Recognize date/time interval surfaces by inverting ICU DateIntervalFormat recipes.

    Each greatest-difference field's recipe is CLDR's interval pattern when
    ``DateIntervalInfo`` has one, else the pattern recovered from ``DateIntervalFormat``'s
    own output (see :func:`_recovered_interval_parts`). A 12-hour side's AM/PM marker is
    parsed into the value, which keeps 24-hour ``H``; a time zone's text is parsed, gated
    against ICU's rendering of that zone, and captured as ``time-zone``: the text as
    written, the value the parsed zone's IANA ID ("ET" -> "America/New_York"; a GMT
    offset, which has none, keeps ICU's custom ID, "GMT-08:00"). Zone text another
    locale of the language writes, or that names different zones in its locales, is
    read once per zone, each gated in its own zone (see :meth:`_read`).
    """

    group = "date-interval"

    def __init__(self, locale: str, skeleton: str) -> None:
        self.locale = locale
        self.skeleton = skeleton
        self.type = f"date-interval:{skeleton}"
        icu_locale = icu.Locale(locale)
        interval_info = icu.DateIntervalInfo(icu_locale)
        matchers = []
        seen: set[tuple[str, str, str]] = set()
        for calendar_field in _INTERVAL_FIELDS:
            pattern = interval_info.getIntervalPattern(skeleton, calendar_field)
            if pattern:
                parts = _interval_pattern_parts(pattern)
            else:
                parts = _recovered_interval_parts(locale, skeleton, calendar_field)
            if parts is None or parts in seen:
                continue
            seen.add(parts)
            part1, separator, part2 = parts
            letters1 = {letter for letter, _ in _pattern_runs(part1)}
            letters2 = {letter for letter, _ in _pattern_runs(part2)}
            if not (letters1 | letters2) <= _MODELED_INTERVAL_LETTERS:
                continue
            zones = {run for run in (_zone_run(part1), _zone_run(part2)) if run is not None}
            if len(zones) > 1:
                continue  # one interval is written in one zone, with one zone field
            matchers.append(
                (
                    icu.SimpleDateFormat(part1, icu_locale),
                    separator,
                    icu.SimpleDateFormat(part2, icu_locale),
                    _interval_fields(part1),
                    _interval_fields(part2),
                    (part1, part2),
                    next(iter(zones), None),
                    (_zone_run(part1) is not None, _zone_run(part2) is not None),
                    _leads_with_digit_field(part1),
                    _interval_datings(part1 + part2) if zones else ({},),
                )
            )
        self._matchers = tuple(matchers)
        self._calendar = icu.Calendar.createInstance(icu_locale).getType()
        self._spec = DateIntervalSpec(locale, skeleton)
        self._dif = icu.DateIntervalFormat.createInstance(skeleton, icu_locale)

    @property
    def has_patterns(self) -> bool:
        """Whether ICU yielded at least one modeled, splittable interval recipe."""
        return bool(self._matchers)

    def _parse_position(self, formatter, text, start, cp_to_u16, dating):
        # The side is parsed on a GMT calendar, never in the process default zone: GMT
        # has no DST gap or overlap, so a side with no zone text keeps the wall time it
        # writes ("02:30" on a spring-forward date in America/New_York would be moved to
        # 03:30 there). A side with zone text is read in the zone the text names, since
        # SimpleDateFormat sets the calendar's zone from the zone text it parses.
        calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(self.locale))
        calendar.clear()
        for name, value in dating.items():
            calendar.set(_INTERVAL_DATING_FIELDS[name], value)
        position = icu.ParsePosition(cp_to_u16[start])
        formatter.parse(icu.UnicodeString(text), calendar, position)
        return position, calendar

    def _parse_side(self, formatter, fields, has_zone, text, start, cp_to_u16, u16_to_cp, dating):
        position, calendar = self._parse_position(formatter, text, start, cp_to_u16, dating)
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
        zone = calendar.getTimeZone() if has_zone else None
        return end, values, zone

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

    @staticmethod
    def _twenty_four_hour(values: dict[str, int]) -> dict[str, int]:
        """Resolve a 12-hour ``h`` (ICU's 0-11 ``HOUR``) and its AM/PM to 24-hour ``H``."""
        values = dict(values)
        ampm = values.pop("ampm", None)
        if ampm is not None and "h" in values:
            values["H"] = values.pop("h") + 12 * ampm
        return values

    def _endpoint(self, values: dict[str, int]) -> DateTimeValue:
        ordered = tuple(
            (name, values[name] + 1 if name == "M" else values[name])
            for name in _INTERVAL_VALUE_ORDER
            if name in values
        )
        return DateTimeValue(ordered, self._calendar)

    def _calendar_from(self, values: dict[str, int], zone=None):
        icu_locale = icu.Locale(self.locale)
        if zone is None:
            calendar = icu.Calendar.createInstance(icu_locale)
        else:
            calendar = icu.Calendar.createInstance(zone, icu_locale)
        calendar.clear()
        fields = {field.name: field.calendar_field for field in _date_fields("yMdHhmsE")}
        for name, value in values.items():
            calendar.set(fields[name], value)
        return calendar

    def _zone_capture(self, side_pattern, zone_run, zone, values, text, start, end, zone_id, name):
        """The ``time-zone`` capture within one side, located by ICU's field position.

        The side is rendered in the reader's locale, with the zone field in ``name``'s
        text for the zone (see :meth:`_in_zone_names_of`).
        """
        icu_locale = icu.Locale(self.locale)
        formatter = icu.SimpleDateFormat(side_pattern, icu_locale)
        formatter.setTimeZone(zone)
        position = icu.FieldPosition(_letter_field_id(zone_run[0]))
        instant = self._calendar_from(values, zone).getTime()
        rendered = str(formatter.format(instant, position))
        _, u16_to_cp = boundary_maps(rendered)
        zone_begin = u16_to_cp[position.getBeginIndex()]
        zone_limit = u16_to_cp[position.getEndIndex()]
        if name != self.locale:
            written = self._zone_formatter(zone_run, zone, name).format(instant)
            rendered = rendered[:zone_begin] + written + rendered[zone_limit:]
            zone_limit = zone_begin + len(written)
        surface = text[start:end]
        if len(rendered) != len(surface) or _normalize_interval_surface(
            rendered
        ) != _normalize_interval_surface(surface):
            return None
        zone_start = start + zone_begin
        zone_end = start + zone_limit
        if zone_end <= zone_start:
            return None
        return Capture("time-zone", zone_start, zone_end, text[zone_start:zone_end], zone_id)

    @staticmethod
    def _zone_formatter(zone_run, zone, name):
        """ICU's formatter for the zone field alone, in locale ``name`` and ``zone``."""
        formatter = icu.SimpleDateFormat(zone_run[0] * zone_run[1], icu.Locale(name))
        formatter.setTimeZone(zone)
        return formatter

    def _in_zone_names_of(self, rendered, zone_run, zone, calendars, name):
        """``rendered`` with the zone's text in ``name``, another locale of the language.

        The interval is ICU's rendering in the reader's own locale; only the zone field
        is written as ICU writes the zone in ``name`` ("IST", en_IN's name for India
        time, where en_US writes "GMT+5:30"). Each endpoint's zone text is replaced, as
        a zone may write a standard name at one end and a daylight name at the other.
        """
        if name == self.locale:
            return rendered
        own = self._zone_formatter(zone_run, zone, self.locale)
        other = self._zone_formatter(zone_run, zone, name)
        for calendar in calendars:
            instant = calendar.getTime()
            rendered = rendered.replace(str(own.format(instant)), str(other.format(instant)))
        return rendered

    @staticmethod
    def _gated_end(
        reformatted: str,
        text: str,
        start: int,
        end1: int,
        separator: str,
        separator_end: int,
        end2: int,
    ) -> int | None:
        """Where the reading ends if ICU's rendering matches the surface, else ``None``.

        Lenient ``SimpleDateFormat.parse`` may take trailing punctuation into the last
        field ("4:07 PM." at a sentence end); ICU's rendering says where the field ends,
        so a surface that is the rendering plus only punctuation ends there.
        """
        rendered = _normalize_interval_surface(reformatted)
        surface = text[start:end1] + separator + text[separator_end:end2]
        gate_surface = _normalize_interval_surface(surface)
        if rendered == gate_surface:
            return end2
        if len(gate_surface) != len(surface) or not gate_surface.startswith(rendered):
            return None
        trimmed = end2 - (len(gate_surface) - len(rendered))
        tail = text[trimmed:end2]
        if trimmed <= separator_end or any(_is_word_character(ch) or ch.isalnum() for ch in tail):
            return None
        return trimmed

    @staticmethod
    def _carried_marker_runs_backwards(values1, values2, start_values, end_values) -> bool:
        """Whether an AM/PM carried to the unmarked side puts the end before the start.

        ICU writes one marker when both times share it ("2:07 - 4:07 PM"), but it writes a
        backwards interval the same way: "10 - 12 PM" is also ICU's text for 22:00 to
        12:00. With no date to order the endpoints, the carried reading must run forward.
        A reading with a marker on each side ("11 PM - 1 AM") is ICU's overnight form.
        """
        if ("ampm" in values1) == ("ampm" in values2):
            return False
        if {"y", "M", "d"} & (values1.keys() | values2.keys()):
            return False

        def clock(values):
            return tuple(values.get(name, 0) for name in ("H", "m", "s"))

        return clock(end_values) < clock(start_values)

    def _read(self, matcher, dating, text, start, cp_to_u16, u16_to_cp):
        """One matcher's readings at ``start``, sides parsed on ``dating``, one per zone.

        Zone text that names different zones in the locales of the language gives one
        reading per zone (see :func:`_zone_readings`), each parsed and gated in its own
        zone with the zone written as the locale that names it writes it: en_US "2:07 -
        4:07 PM IST" is read in Europe/Dublin and in Asia/Kolkata. Each reading is
        ``(end, captures, value, zone key, rank)``, the key the zone's metazone on the
        reading's date and the rank ordering the reader's own locale's zone first.
        """
        own = self._read_as(matcher, self.locale, dating, text, start, cp_to_u16, u16_to_cp)
        if matcher[6] is None:
            return [(*own[:3], None, 0)] if own is not None else []
        if own is not None:
            zone_text = next(
                (capture.text for capture in own[1] if capture.name == "time-zone"), None
            )
        else:
            zone_text = self._unread_zone_text(matcher, dating, text, start, cp_to_u16, u16_to_cp)
        if not zone_text:
            return [(*own[:3], None, 0)] if own is not None else []
        attempts = [(own, self.locale)]
        for _zone_id, name in _zone_parses(zone_text, self.locale):
            if name != self.locale:
                attempts.append(
                    (
                        self._read_as(matcher, name, dating, text, start, cp_to_u16, u16_to_cp),
                        name,
                    )
                )
        readings = []
        seen: set[str] = set()
        for rank, (reading, name) in enumerate(attempts):
            if reading is None or reading[3] is None:
                continue
            end, captures, value, zone_id = reading
            written = next(c.text for c in captures if c.name == "time-zone")
            days = _reading_days(dict(value.start.fields))
            # Kept only where ICU writes the zone text for the zone on the reading's
            # date, in some locale of the language: a lenient parse also takes names ICU
            # no longer writes ("MST" as Asia/Macau), and a date-less side is parsed on
            # a stand-in dating.
            if not any(_zone_writes(written, zone_id, name, None, day) for day in days):
                continue
            metazone = _zone_metazone(zone_id, days[0])
            if metazone not in seen:
                seen.add(metazone)
                readings.append((end, captures, value, metazone, rank))
        return readings

    def _unread_zone_text(self, matcher, dating, text, start, cp_to_u16, u16_to_cp):
        """The zone name where the reader's own locale stopped parsing a zoned side.

        ICU's parse stops at zone text its locale does not write ("IST" in en_US); a
        name another locale of the language writes there is read by that locale.
        """
        formatter1, separator, formatter2 = matcher[0], matcher[1], matcher[2]
        has_zone1, has_zone2 = matcher[7]
        position, _ = self._parse_position(formatter1, text, start, cp_to_u16, dating)
        has_zone = has_zone1
        if position.getErrorIndex() == -1:
            end1 = u16_to_cp.get(position.getIndex())
            if end1 is None or end1 <= start:
                return None
            separator_end = self._separator_end(text, end1, separator)
            if separator_end is None:
                return None
            position, _ = self._parse_position(formatter2, text, separator_end, cp_to_u16, dating)
            has_zone = has_zone2
        error = u16_to_cp.get(position.getErrorIndex())
        if not has_zone or error is None:
            return None
        return _zone_form_at(text, error, icu.Locale(self.locale).getLanguage())

    def _read_as(self, matcher, name, dating, text, start, cp_to_u16, u16_to_cp):
        """One matcher's reading at ``start``, its zone text read as locale ``name`` does.

        ``name`` is the reader's own locale, or another of its language whose zone name
        the text writes; the sides' other fields are the reader's own pattern's either
        way. Returns ``(end, captures, value, zone ID)``, the ID ``None`` with no zone.
        """
        formatter1, separator, formatter2, fields1, fields2, patterns, zone_run = matcher[:7]
        has_zone1, has_zone2 = matcher[7]
        if name != self.locale:
            formatter1 = _interval_side_formatter(patterns[0], name)
            formatter2 = _interval_side_formatter(patterns[1], name)
        parsed1 = self._parse_side(
            formatter1, fields1, has_zone1, text, start, cp_to_u16, u16_to_cp, dating
        )
        if parsed1 is None:
            return None
        end1, values1, zone1 = parsed1
        separator_end = self._separator_end(text, end1, separator)
        if separator_end is None:
            return None
        # A side that shows no date is parsed on the date the other shows: a daylight
        # name ("IST", Irish summer time) is read on the day it names ("Jul 5, 2:07 -
        # 4:07 PM IST"), not on the stand-in dating's January.
        shown = {name: values1[name] for name in _INTERVAL_DATING_FIELDS if name in values1}
        parsed2 = self._parse_side(
            formatter2,
            fields2,
            has_zone2,
            text,
            separator_end,
            cp_to_u16,
            u16_to_cp,
            {**dating, **shown},
        )
        if parsed2 is None:
            return None
        end2, values2, zone2 = parsed2
        if _continues_interval_word(text, end2):
            return None
        if zone1 is not None and zone2 is not None and zone1.getID() != zone2.getID():
            return None  # ICU writes both endpoints in one zone
        zone = zone2 if zone2 is not None else zone1
        names = values1.keys() | values2.keys()
        start_values = self._twenty_four_hour(
            {name: values1[name] if name in values1 else values2[name] for name in names}
        )
        end_values = self._twenty_four_hour(
            {name: values2[name] if name in values2 else values1[name] for name in names}
        )
        if self._carried_marker_runs_backwards(values1, values2, start_values, end_values):
            return None
        # The gate renders the endpoints on the dating the sides were parsed on.
        dated_start = {**dating, **start_values}
        dated_end = {**dating, **end_values}
        # The gate renders in the zone the text names (or one ICU keeps with the same
        # offset and rules; see _same_rule_zone_ids), or in GMT when it names none, and
        # never in the process default zone. DateIntervalFormat's calendar-taking
        # formatToValue writes each endpoint in its calendar's zone (PyICU exposes no
        # setTimeZone), wall-clock fields and zone text alike.
        if zone is None:
            render_zones = iter((icu.TimeZone.getGMT(),))
        else:
            others = _same_rule_zone_ids(str(zone.getID()))
            render_zones = chain((zone,), map(icu.TimeZone.createTimeZone, others))
        # note: The reformat guard is the correctness gate for every deposited value.
        # The two field regions are the exact surface text -- so a mis-parse whose
        # fields would render differently is rejected. Only the separator is swapped
        # for its reflective canonical form: the surface separator's non-space core was
        # already validated by _separator_end, and its spacing is the sole intentional
        # relaxation (letting "2020-2024" match canonical "2020 - 2024"). Thus a
        # deposited interval's fields always round-trip; only separator spacing is free.
        # AM/PM is resolved into 24-hour H before the reformat, so a wrong marker renders
        # differently and fails here; a zone is gated on ICU's text for the parsed zone.
        gated = None
        for render_zone in render_zones:
            try:
                start_calendar = self._calendar_from(dated_start, render_zone)
                end_calendar = self._calendar_from(dated_end, render_zone)
                reformatted = str(self._dif.formatToValue(start_calendar, end_calendar))
            except icu.ICUError:
                continue
            if zone is not None:
                reformatted = self._in_zone_names_of(
                    reformatted, zone_run, render_zone, (start_calendar, end_calendar), name
                )
            end = self._gated_end(reformatted, text, start, end1, separator, separator_end, end2)
            if end is not None:
                gated = end, render_zone
                break
        if gated is None:
            return None
        end2, render_zone = gated
        captures = [
            Capture("start", start, end1, text[start:end1]),
            Capture("separator", end1, separator_end, text[end1:separator_end], form="symbol"),
            Capture("end", separator_end, end2, text[separator_end:end2]),
        ]
        zone_id = None
        if zone is not None:
            # The capture names the zone the text was parsed as, in its IANA form,
            # whatever the process default zone is.
            zone_id = _iana_zone_id(zone.getID())
            sides = (
                (has_zone1, patterns[0], dated_start, start, end1),
                (has_zone2, patterns[1], dated_end, separator_end, end2),
            )
            for has_zone, pattern, values, side_start, side_end in sides:
                if not has_zone:
                    continue
                zone_capture = self._zone_capture(
                    pattern,
                    zone_run,
                    render_zone,
                    values,
                    text,
                    side_start,
                    side_end,
                    zone_id,
                    name,
                )
                if zone_capture is not None:
                    captures.append(zone_capture)
        value = DateIntervalValue(self._endpoint(start_values), self._endpoint(end_values))
        return end2, tuple(captures), value, zone_id

    def _match(
        self,
        text: str,
        start: int,
        offset_maps: tuple[list[int], dict[int, int]] | None = None,
    ):
        if _continues_interval_word(text, start - 1):
            return []
        cp_to_u16, u16_to_cp = offset_maps if offset_maps is not None else boundary_maps(text)
        # One reading per zone: every dating is tried for a zoned matcher, since a zone
        # may write its name on one dating only (Irish time is "IST" in summer).
        readings: dict[tuple, tuple] = {}
        leads_with_digit = icu.Char.isdigit(text[start]) if start < len(text) else False
        for matcher in self._matchers:
            if matcher[8] and not leads_with_digit:
                continue  # ICU writes this side's first field in digits
            for dating in matcher[9]:
                found = self._read(matcher, dating, text, start, cp_to_u16, u16_to_cp)
                for end, captures, value, zone_key, rank in found:
                    readings.setdefault((end, value, zone_key), (rank, end, captures, value))
                if found and matcher[6] is None:
                    break
        if not readings:
            return []
        longest = max(end for _, end, _, _ in readings.values())
        return [
            _FlexibleMatch(end, captures, value, self._spec)
            for _, end, captures, value in sorted(
                (reading for reading in readings.values() if reading[1] == longest),
                key=lambda reading: reading[0],
            )
        ]

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping date-interval candidates in source order.

        A span whose zone text names several zones is read once per zone, the reader's
        own locale's zone first.
        """
        # Compute the code-point/UTF-16 offset maps once per scan and pass them to every
        # candidate start (avoids O(n^2) scanning). They are bound to this call, never
        # stored on the detector, so one detector can serve concurrent or nested calls.
        offset_maps = boundary_maps(text)

        def match(source: str, start: int):
            return self._match(source, start, offset_maps)

        return _detect_flexible_alternatives(text, self.locale, self.type, match)


@cache
def _language_eras(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, int, str], ...]:
    """CLDR's era names for the locales of ``language``: ``(name, era index, width)``.

    The abbreviated names ("BC" 0, "AD" 1), and from CLDR's Gregorian era table the
    variants and wide names ICU also formats: "BCE"/"CE", "Before Christ"/"Anno
    Domini", "Before Common Era"/"Common Era". Longest first; the case is CLDR's.
    """
    eras: dict[str, tuple[int, str]] = {}
    for name in _language_locale_names(language, names):
        locale = icu.Locale(name)
        for index, form in enumerate(icu.DateFormatSymbols(locale).getEras()):
            if form:
                eras.setdefault(form, (index, "short"))
        try:
            table = (
                icu.ResourceBundle("", locale)
                .getWithFallback("calendar")
                .getWithFallback("gregorian")
                .getWithFallback("eras")
            )
        except icu.ICUError:
            continue
        for key, width in (
            ("abbreviated%variant", "short"),
            ("wide", "wide"),
            ("wide%variant", "wide"),
        ):
            try:
                forms = table.getWithFallback(key)
            except icu.ICUError:
                continue
            for index in range(forms.getSize()):
                form = forms.get(index).getString()
                if form:
                    eras.setdefault(form, (index, width))
    return tuple(
        (form, index, width)
        for form, (index, width) in sorted(eras.items(), key=lambda item: -len(item[0]))
    )


@cache
def _lexicon_month_expansions(locale: str) -> tuple[tuple[str, str], ...]:
    """Dotted month abbreviations in the locale's lexicon, with the month each expands to."""
    from .abbreviation_compile import compile_lexicon

    compiled = compile_lexicon(locale)
    if compiled is None:
        return ()
    return tuple(
        (entry.surface, expansion.value)
        for entry in compiled.lexicon.entries
        if entry.surface.endswith(".")
        for expansion in entry.expansions
        if expansion.sense == "month"
    )


@cache
def _language_era_orders(language: str, names: tuple[str, ...] | None = None) -> tuple[bool, bool]:
    """Whether the language's CLDR ``yG`` patterns put the year first, the era first."""
    year_first = era_first = False
    for name in _language_locale_names(language, names):
        locale = icu.Locale(name)
        pattern = icu.DateTimePatternGenerator.createInstance(locale).getBestPattern("yG")
        year_at, era_at = pattern.find("y"), pattern.find("G")
        if year_at < 0 or era_at < 0:
            continue
        year_first |= year_at < era_at
        era_first |= era_at < year_at
    return year_first, era_first


@cache
def _lexicon_month_abbreviations(locale: str) -> frozenset[str]:
    """Month abbreviations with a period that the locale's abbreviation lexicon lists.

    CLDR's abbreviated month names carry no period in English ("Oct"), but English
    writes one ("Oct."), and icukit's abbreviation lexicon records it with the month
    sense. An empty set where the locale has no lexicon.
    """
    return _lexicon_dotted(locale, "month")


@cache
def _lexicon_dotted(locale: str, sense: str) -> frozenset[str]:
    """The locale lexicon's abbreviations with a period for ``sense`` ("Oct.", "Sun.")."""
    from .abbreviation_compile import compile_lexicon

    compiled = compile_lexicon(locale)
    if compiled is None:
        return frozenset()
    return frozenset(
        entry.surface
        for entry in compiled.lexicon.entries
        if entry.surface.endswith(".")
        and any(expansion.sense == sense for expansion in entry.expansions)
    )


@cache
def _lexicon_expansions(locale: str, sense: str) -> tuple[tuple[str, str], ...]:
    """The locale lexicon's dotted abbreviations for ``sense``, with what each expands to."""
    from .abbreviation_compile import compile_lexicon

    compiled = compile_lexicon(locale)
    if compiled is None:
        return ()
    return tuple(
        (entry.surface, expansion.value)
        for entry in compiled.lexicon.entries
        if entry.surface.endswith(".")
        for expansion in entry.expansions
        if expansion.sense == sense
    )


# The widths of a year the text-date reader reads, and those only the short-year reader
# reads (see the comment in FlexibleTextDateDetector._match_structure).
_YEAR_WIDTHS = frozenset({4})
_SHORT_YEAR_WIDTHS = frozenset({2, 3})


class FlexibleTextDateDetector:
    """Recognize textual-month dates licensed by CLDR date patterns and symbols.

    The structures are the locale's own medium, long, and full patterns (with their
    year-optional subsets), plus the day-month-year, month-year, day-month, and
    weekday-day-month-year patterns CLDR gives every locale of the same language, so
    en_US reads en_GB's "1 July", "23 October 2014", and "Thursday, 2 May 2013". An
    abbreviated month may carry a period where the locale's abbreviation lexicon lists
    the month that way ("Oct. 2006", "Jan. 1").

    A year in a date is read in four digits. A two- or three-digit one is read only
    beside an era ("5 March 44 BC"), since without one it cannot be told from a count
    after a date ("5 June 200 attendees"); those dates are read under their own type by
    :class:`FlexibleShortYearDateDetector`.

    A year beside an era abbreviation CLDR gives the language ("500 BC") is read as a
    year with its era, in the order the language's CLDR ``yG`` pattern writes them (year
    first in English, so "Vancouver, BC 2010" is not 2010 BC). The era names are
    Gregorian, so the value is a Gregorian year: ``G`` (0 before the epoch, 1 after, as
    ICU numbers them) and ``y``, with ``era`` and ``y`` captures.
    """

    group = "date"
    type = "date:text-flexible"

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        icu_locale = icu.Locale(locale)
        self._calendar = icu.Calendar.createInstance(icu_locale).getType()
        self._rbnf = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, icu_locale)
        self._months = self._language_symbol_names(icu_locale, "month")
        self._quarters = self._quarter_names(icu_locale)
        self._weekdays = self._language_symbol_names(icu_locale, "weekday")
        self._dotted_months = _lexicon_month_abbreviations(locale)
        self._dotted = frozenset(surface.casefold() for surface in self._dotted_months)
        # Weekdays take the lexicon's period ("Sun.") and its forms CLDR does not name
        # ("Tues.", "Thurs."), as months do.
        self._dotted_weekdays = frozenset(
            surface.casefold() for surface in _lexicon_dotted(locale, "weekday")
        )
        weekday_values = {surface.casefold(): value for surface, value, _form in self._weekdays}
        extra_weekdays = [
            (surface, weekday_values[expansion.casefold()], "short")
            for surface, expansion in _lexicon_expansions(locale, "weekday")
            if expansion.casefold() in weekday_values
            and surface[:-1].casefold() not in weekday_values
        ]
        if extra_weekdays:
            self._weekdays = tuple(
                sorted(
                    (*self._weekdays, *extra_weekdays), key=lambda item: len(item[0]), reverse=True
                )
            )
        # A lexicon month form CLDR does not name ("Sept." beside CLDR's "Sep") is read as
        # the month its expansion names.
        month_values = {surface.casefold(): value for surface, value, _form in self._months}
        extra = []
        for surface, expansion in _lexicon_month_expansions(locale):
            value = month_values.get(expansion.casefold())
            if value is not None and surface[:-1].casefold() not in month_values:
                extra.append((surface, value, "short"))
        if extra:
            self._months = tuple(
                sorted((*self._months, *extra), key=lambda item: len(item[0]), reverse=True)
            )
        self._eras = _language_eras(icu_locale.getLanguage(), self.locales)
        self._year_first, self._era_first = _language_era_orders(
            icu_locale.getLanguage(), self.locales
        )
        self._era_spec = DateFormatSpec(locale, "yG", "y G", "gregorian")
        self._era_specs = {
            "short": self._era_spec,
            "wide": DateFormatSpec(locale, "yGGGG", "y GGGG", "gregorian"),
        }
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
        day_month: list[tuple[tuple[str, ...], tuple[str, ...], str]] = []
        for available in map(icu.Locale, _language_locale_names(language, self.locales)):
            generator = icu.DateTimePatternGenerator.createInstance(available)
            # A weekday reads only with its year, which checks it ("Thursday, 2 May 2013",
            # en_GB; "Saturday 3 January 1891", en_AU and en_IE).
            for skeleton in (
                "dMMMMy",
                "dMMMy",
                "yMMMM",
                "yMMM",
                "yMMMMEEEEd",
                "yMMMEd",
                "yMMMdG",
                "yMMMMdG",
                "GyMMM",
                "GyMMMEd",
                "yQQQ",
                "yQQQQ",
            ):
                pattern = generator.getBestPattern(skeleton)
                parsed = self._date_structure(pattern)
                if parsed is None:
                    continue
                fields, literals = parsed
                if fields in {
                    ("d", "M", "y"),
                    ("M", "y"),
                    ("E", "d", "M", "y"),
                    ("E", "M", "d", "y"),
                    ("M", "d", "y", "G"),
                    ("d", "M", "y", "G"),
                    ("M", "y", "G"),
                    ("E", "M", "d", "y", "G"),
                    ("E", "d", "M", "y", "G"),
                    ("Q", "y"),
                }:
                    structures.append((fields, literals, pattern))
            for skeleton in ("dMMMM", "dMMM"):
                pattern = generator.getBestPattern(skeleton)
                parsed = self._date_structure(pattern)
                if parsed is None:
                    continue
                fields, literals = parsed
                if fields in {("d", "M"), ("M", "d")}:
                    day_month.append((fields, literals, pattern))
        self._structures = tuple(dict.fromkeys(structures))
        # Scanned as their own pass: sharing a start with the patterns above would let
        # "3 May" take the start from "May 5, 2020" in "Issue 3 May 5, 2020".
        self._day_month_structures = tuple(
            structure for structure in dict.fromkeys(day_month) if structure not in structures
        )
        pattern = self._structures[0][2] if self._structures else ""
        self._spec = DateFormatSpec(locale, "yMMMd", pattern, self._calendar)
        # note: Bare years and decades remain cardinal candidates for downstream reinterpretation.

    def _quarter_names(self, icu_locale: icu.Locale):
        """The quarter names ICU writes in the language ("Q1", "1st quarter"), longest first.

        From ICU's own QQQ and QQQQ formatting of a date in each quarter, in every locale
        of the language.
        """
        found: dict[str, tuple[str, int, str]] = {}
        calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu_locale)
        for name in _language_locales(icu_locale.getName(), self.locales):
            for field, form in (("QQQQ", "wide"), ("QQQ", "short")):
                formatter = icu.SimpleDateFormat(field, icu.Locale(name))
                formatter.setTimeZone(icu.TimeZone.getGMT())
                for quarter in range(4):
                    calendar.clear()
                    calendar.set(2026, quarter * 3, 15)
                    surface = formatter.format(calendar.getTime())
                    if surface:
                        found.setdefault(surface.casefold(), (surface, quarter + 1, form))
        return tuple(sorted(found.values(), key=lambda item: len(item[0]), reverse=True))

    def _language_symbol_names(self, icu_locale: icu.Locale, field: str):
        """The month or weekday names of the locale, then of its language's other locales.

        So en_US reads en_GB's "Sept". ``DateFormatSymbols`` gives every locale its
        Gregorian names (fa_IR's first month is January, whatever its calendar), so the
        names merged are the same calendar's.
        """
        found = {
            surface.casefold(): (surface, value, form)
            for surface, value, form in self._symbol_names(icu.DateFormatSymbols(icu_locale), field)
        }
        own = icu_locale.getName()
        for name in _language_locale_names(icu_locale.getLanguage(), self.locales):
            if name == own:
                continue
            symbols = icu.DateFormatSymbols(icu.Locale(name))
            for surface, value, form in self._symbol_names(symbols, field):
                found.setdefault(surface.casefold(), (surface, value, form))
        return tuple(sorted(found.values(), key=lambda item: len(item[0]), reverse=True))

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
            if not quoted and character in {"y", "M", "L", "d", "E", "G", "Q", "q"}:
                run_end = cursor + 1
                while run_end < len(pattern) and pattern[run_end] == character:
                    run_end += 1
                normalized = {"L": "M", "q": "Q"}.get(character, character)
                if normalized == "Q" and run_end - cursor < 3:
                    return None
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
        if set(fields) - {"y", "M", "d", "E", "G", "Q"}:
            return None
        date = set(fields) - {"E", "G"}
        if not ({"y", "M", "d"}.issubset(date) or date in ({"M", "y"}, {"M", "d"}, {"Q", "y"})):
            return None
        if "G" in fields and "y" not in fields:
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

    def _match_structure(self, text: str, start: int, structure, year_widths=_YEAR_WIDTHS):
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
            if field == "G":
                found = self._era_at(text, cursor)
                if found is None:
                    return None
                era_end, era, width = found
                captures.append(
                    Capture("era", field_start, era_end, text[field_start:era_end], era, width)
                )
                values["G"] = era
                cursor = era_end
            elif field in {"M", "E", "Q"}:
                table = {"M": self._months, "E": self._weekdays, "Q": self._quarters}[field]
                named = self._name(text, cursor, table)
                if named is None:
                    return None
                cursor, value, form = named
                if field == "M" and text[field_start : cursor + 1].casefold() in self._dotted:
                    cursor += 1
                elif (
                    field == "E"
                    and text[field_start : cursor + 1].casefold() in self._dotted_weekdays
                ):
                    cursor += 1
                name = {"M": "month", "E": "weekday", "Q": "quarter"}[field]
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
                # ICU's "y" writes a year in as many digits as it has ("24 April 350"),
                # but nothing in the patterns tells a short year from a count after a
                # date ("5 June 200 attendees", "on 5 June 20 people came"), so the
                # widths read are a hand-rolled limit: four by default, two and three
                # also for FlexibleShortYearDateDetector, and never one ("3 May 2"). An
                # era beside the year marks it a year, so there two and three are read
                # too ("5 March 44 BC"), as the era pass reads "44 BC".
                elif field == "y" and (
                    width in year_widths or ("G" in fields and width in _SHORT_YEAR_WIDTHS)
                ):
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
            calendar.set(validation_year, values.get("M", 1) - 1, values.get("d", 1))
            calendar.getTime()
            if "y" in values and "E" in values:
                if calendar.get(icu.Calendar.DAY_OF_WEEK) != values["E"]:
                    return None
        except icu.ICUError:
            return None
        ordered = tuple(
            (field, values[field]) for field in ("G", "y", "Q", "M", "d") if field in values
        )
        return cursor, tuple(captures), DateTimeValue(ordered, self._calendar)

    def _match(self, text: str, start: int, structures=None, year_widths=_YEAR_WIDTHS):
        if start > 0 and text[start - 1].isalnum():
            return None
        matches = [
            match
            for structure in (self._structures if structures is None else structures)
            if (match := self._match_structure(text, start, structure, year_widths)) is not None
        ]
        return max(matches, key=lambda match: match[0], default=None)

    def _match_day_month(self, text: str, start: int):
        return self._match(text, start, self._day_month_structures)

    def _era_at(self, text: str, cursor: int) -> tuple[int, int, str] | None:
        for form, index, width in self._eras:
            end = cursor + len(form)
            if text[cursor:end] == form and (end == len(text) or not text[end].isalnum()):
                return end, index, width
        return None

    def _match_era(self, text: str, start: int):
        """A year and an era abbreviation, in the order CLDR's ``yG`` pattern writes."""
        if start > 0 and text[start - 1].isalnum():
            return None
        era_first = self._era_at(text, start) if self._era_first else None
        if era_first is not None:
            era_end, era, width = era_first
            if not (era_end < len(text) and text[era_end] in _SPACES):
                return None
            year_start = era_end + 1
            year_end, year = self._digit_run(text, year_start)
            if not 1 <= year_end - year_start <= 4 or year < 1:
                return None
            if year_end < len(text) and text[year_end].isalnum():
                return None
            captures = (
                Capture("era", start, era_end, text[start:era_end], era, width),
                Capture("y", year_start, year_end, text[year_start:year_end], year, "numeric"),
            )
            value = DateTimeValue((("G", era), ("y", year)), "gregorian")
            return _FlexibleMatch(year_end, captures, value, self._era_specs[width])
        if not self._year_first:
            return None
        year_end, year = self._digit_run(text, start)
        if not 1 <= year_end - start <= 4 or year < 1:
            return None
        if not (year_end < len(text) and text[year_end] in _SPACES):
            return None
        found = self._era_at(text, year_end + 1)
        if found is None:
            return None
        end, era, width = found
        captures = (
            Capture("y", start, year_end, text[start:year_end], year, "numeric"),
            Capture("era", year_end + 1, end, text[year_end + 1 : end], era, width),
        )
        value = DateTimeValue((("G", era), ("y", year)), "gregorian")
        return _FlexibleMatch(end, captures, value, self._era_specs[width])

    def detect(self, text: str) -> list[ValueDetection]:
        """Return textual-date, day-month, and era-year candidates in source order.

        Each kind is its own pass, so their readings may overlap ("5 May 2000 AD" gives
        the date and "2000 AD"); none takes a start from another.
        """
        dates = _detect_flexible(text, self.locale, self.type, self._spec, self._match)
        day_month = _detect_flexible(
            text, self.locale, self.type, self._spec, self._match_day_month
        )
        eras = _detect_flexible(text, self.locale, self.type, self._era_spec, self._match_era)
        # A day-month reading inside a fuller date adds nothing ("July 25" in "July 25,
        # 2012"); one that only overlaps a date is a different path and stays.
        extra = [
            d
            for d in day_month
            if not any(e["start"] <= d["start"] and d["end"] <= e["end"] for e in dates)
        ]
        return sorted((*dates, *extra, *eras), key=lambda item: (item["start"], item["end"]))


class FlexibleShortYearDateDetector(FlexibleTextDateDetector):
    """Recognize the textual dates with a two- or three-digit year the text-date reader refuses.

    :class:`FlexibleTextDateDetector` reads a year in a date without an era only in four
    digits, since a shorter one cannot be told from a count after a date ("5 June 200
    attendees", "in June 200 cases"). This reader deposits exactly those refused
    readings: the dates that reader's patterns read with two- and three-digit years
    allowed as well, less those it reads without them, which are the dates with no era
    whose year has two or three digits ("24 April 350", "on 5 June 20 people came"). The
    type is ``date:short-year`` and the value the text-date reader's
    :class:`DateTimeValue`, with the year as written: ``("y", 20)`` is the year 20, not
    2020, and "Mar 3, 07" is ``("y", 7)``: the value is the digits' value, never widened
    to a century, since the patterns read here write ``y``, not ``yy``.
    """

    type = "date:short-year"

    @property
    def has_year_patterns(self) -> bool:
        """Whether the locale's textual date patterns write a year at all."""
        return any("y" in fields for fields, _literals, _pattern in self._structures)

    def _match_short(self, text: str, start: int):
        return self._match(text, start, year_widths=_YEAR_WIDTHS | _SHORT_YEAR_WIDTHS)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return the dates with a two- or three-digit year, in source order."""
        return [
            date
            for date in _detect_flexible(
                text, self.locale, self.type, self._spec, self._match_short
            )
            if _short_year_without_era(date["captures"])
        ]


def _short_year_without_era(captures) -> bool:
    """Whether a text date's year has two or three digits and no era beside it."""
    names = {capture.name for capture in captures}
    return "era" not in names and any(
        capture.name == "y" and len(capture.text) in _SHORT_YEAR_WIDTHS for capture in captures
    )


class _FlexibleDateNameDetector:
    """A month or weekday name alone, where the text-date reader reads no date.

    The names, their widths, and the lexicon's dotted and extra forms ("Sept.",
    "Tues.") are exactly the ones :class:`FlexibleTextDateDetector` reads inside a date,
    for the same locales of the language, matched as it matches them (in any case, not
    followed by a letter or digit). A name inside one of that reader's dates is left to
    the date, so this reader deposits only the names it refuses to read alone.
    """

    group = "date"
    type: str
    _field: str
    _capture: str
    _skeletons: dict[str, str]

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        self._dates = FlexibleTextDateDetector(locale, locales=locales)
        if self._field == "M":
            self._names, self._dotted = self._dates._months, self._dates._dotted
        else:
            self._names, self._dotted = self._dates._weekdays, self._dates._dotted_weekdays
        generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(locale))
        self._specs = {
            form: DateFormatSpec(locale, skeleton, generator.getBestPattern(skeleton), "gregorian")
            for form, skeleton in self._skeletons.items()
        }

    @property
    def has_names(self) -> bool:
        """Whether ICU gives the locale's language any such names."""
        return bool(self._names)

    def _match(self, text: str, start: int) -> _FlexibleMatch | None:
        if start > 0 and text[start - 1].isalnum():
            return None
        named = FlexibleTextDateDetector._name(text, start, self._names)
        if named is None:
            return None
        end, value, form = named
        if text[start : end + 1].casefold() in self._dotted:
            end += 1
        capture = Capture(self._capture, start, end, text[start:end], value, form)
        # DateFormatSymbols gives every locale its Gregorian names (see
        # FlexibleTextDateDetector._language_symbol_names), so the value is Gregorian.
        value_record = DateTimeValue(((self._field, value),), "gregorian")
        return _FlexibleMatch(end, (capture,), value_record, self._specs[form])

    def detect(self, text: str) -> list[ValueDetection]:
        """Return the names read alone, in source order, outside the text-date readings."""
        found = _detect_flexible(text, self.locale, self.type, None, self._match)
        if not found:
            return []
        dates = self._dates.detect(text)
        return [
            name
            for name in found
            if not any(
                date["start"] < name["end"] and name["start"] < date["end"] for date in dates
            )
        ]


class FlexibleMonthNameDetector(_FlexibleDateNameDetector):
    """Recognize a month name alone ("May", "Sept."), which the date readers refuse.

    The type is ``date:month-name`` and the value ``DateTimeValue((("M", month),),
    "gregorian")``, with the month numbered from 1 as ICU's ``M`` field does; the spec
    is the locale's ``MMMM`` or ``MMM`` pattern, by the name's width. See
    :class:`_FlexibleDateNameDetector` for which names are read.
    """

    type = "date:month-name"
    _field = "M"
    _capture = "month"
    _skeletons = {"wide": "MMMM", "short": "MMM"}


class FlexibleWeekdayNameDetector(_FlexibleDateNameDetector):
    """Recognize a weekday name alone ("Tuesday", "Sun"), which the date readers refuse.

    The type is ``date:weekday-name`` and the value ``DateTimeValue((("E", weekday),),
    "gregorian")``, with the weekday numbered as ICU's calendar numbers it (Sunday 1);
    the spec is the locale's ``EEEE`` or ``EEE`` pattern, by the name's width. See
    :class:`_FlexibleDateNameDetector` for which names are read.
    """

    type = "date:weekday-name"
    _field = "E"
    _capture = "weekday"
    _skeletons = {"wide": "EEEE", "short": "EEE"}


@cache
def _language_groupings(
    locale: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, int, int, NumberFormatSpec], ...]:
    """The groupings the other locales of the language write, beside ``locale``'s own.

    Each is ``(separator, primary, secondary, spec)``. Any space separates groups where
    any space does (``FlexibleNumberDetector._grouping_length``), so the spaces are one
    grouping; a grouping whose separator is ``locale``'s decimal separator is left out.
    """
    own = icu.NumberFormat.createInstance(icu.Locale(locale))
    symbol = icu.DecimalFormatSymbols
    decimal = own.getDecimalFormatSymbols().getSymbol(symbol.kDecimalSeparatorSymbol)

    def key(number_format) -> tuple[str, int, int] | None:
        if not number_format.isGroupingUsed():
            return None
        separator = number_format.getDecimalFormatSymbols().getSymbol(
            symbol.kGroupingSeparatorSymbol
        )
        primary = number_format.getGroupingSize()
        secondary = number_format.getSecondaryGroupingSize() or primary
        return (" " if separator in _SPACES else separator, primary, secondary)

    seen = {key(own)}
    groupings = []
    for name in _language_locales(locale, names)[1:]:
        number_format = icu.NumberFormat.createInstance(icu.Locale(name))
        style = key(number_format)
        if style is None or style in seen:
            continue
        separator = number_format.getDecimalFormatSymbols().getSymbol(
            symbol.kGroupingSeparatorSymbol
        )
        if separator == decimal or (separator in _SPACES and decimal in _SPACES):
            continue
        seen.add(style)
        secondary = number_format.getSecondaryGroupingSize()
        primary = number_format.getGroupingSize()
        sizes = (secondary, primary) if secondary else (primary,)
        spec = NumberFormatSpec(name, "decimal", grouping_sizes=sizes)
        groupings.append((separator, primary, secondary or primary, spec))
    return tuple(groupings)


@cache
def _language_decimal_styles(
    locale: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, str, int, int, NumberFormatSpec], ...]:
    """The other locales' number styles whose decimal separator is not ``locale``'s.

    Each is ``(grouping separator, decimal separator, primary, secondary, spec)``: in
    English, en_DE's "1.234,56" and en_ZA's "1 234,56". Any space is one grouping.
    """
    symbol = icu.DecimalFormatSymbols
    own = icu.NumberFormat.createInstance(icu.Locale(locale)).getDecimalFormatSymbols()
    own_decimal = own.getSymbol(symbol.kDecimalSeparatorSymbol)
    styles: dict[tuple[str, str, int, int], tuple[str, str, int, int, NumberFormatSpec]] = {}
    for name in _language_locales(locale, names)[1:]:
        number_format = icu.NumberFormat.createInstance(icu.Locale(name))
        symbols = number_format.getDecimalFormatSymbols()
        decimal = symbols.getSymbol(symbol.kDecimalSeparatorSymbol)
        if decimal == own_decimal:
            continue
        grouping = symbols.getSymbol(symbol.kGroupingSeparatorSymbol)
        primary = number_format.getGroupingSize() if number_format.isGroupingUsed() else 0
        secondary = number_format.getSecondaryGroupingSize() or primary
        key = (" " if grouping in _SPACES else grouping, decimal, primary, secondary)
        if key in styles:
            continue
        sizes = (secondary, primary) if secondary and secondary != primary else (primary,)
        spec = NumberFormatSpec(name, "decimal", grouping_sizes=sizes if primary else None)
        styles[key] = (grouping, decimal, primary, secondary, spec)
    return tuple(styles.values())


class FlexibleNumberDetector:
    """Recognize flexible decimal spellings and Roman cardinals from ICU data.

    Beside the locale's own grouping, a number reads in each other grouping ICU gives a
    locale of the language ("250 000" as en_ZA formats it, "1'234'567" as en_CH,
    "12,34,567" as en_IN), as an extra reading: "12 100" still reads "12" and "100",
    and also 12100. A grouping whose separator is the locale's decimal separator is not
    read that way, since it would reread every decimal number; instead the language's
    other decimal styles (en_DE's "1.234,56", en_ZA's "1 234,56") are read only where the
    locale's own styles do not already read the text: "1,5" reads 1.5 and "1.234,56"
    1234.56, while "1,234" stays 1234 alone.

    ``accept_single_letter_roman`` defaults to true because corpora use ``I`` as the
    cardinal one. Lowercase Roman numerals are opt-in because their surfaces collide with
    unit abbreviations and common words; :class:`FlexibleLowercaseRomanDetector` reads
    them as their own type, ``number:cardinal:roman-lower``.
    """

    group = "number"
    type = "number:decimal"

    def __init__(
        self,
        locale: str,
        *,
        accept_single_letter_roman: bool = True,
        accept_lowercase_roman: bool = False,
        locales: Iterable[str] | None = None,
    ) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
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
        self._other_groupings = _language_groupings(locale, self.locales)
        self._decimal_styles = _language_decimal_styles(locale, self.locales)

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

    def _grouping_length(self, text: str, cursor: int, separator: str | None = None) -> int:
        separator = self._grouping if separator is None else separator
        if separator in _SPACES:
            return int(cursor < len(text) and text[cursor] in _SPACES)
        return len(separator) if text.startswith(separator, cursor) else 0

    def _match(
        self,
        text: str,
        start: int,
        grouping: tuple[str, int, int] | None = None,
        decimal: str | None = None,
    ) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        separator, primary_grouping, secondary_grouping = grouping or (
            self._grouping,
            self._primary_grouping,
            self._secondary_grouping,
        )
        decimal = self._decimal if decimal is None else decimal
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
        leading_decimal = text.startswith(decimal, cursor)
        decimal_end = cursor + len(decimal)
        if leading_decimal and start > 0:
            previous = text[start - 1]
            if _is_word_character(previous) or previous == decimal:
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
        while primary_grouping and (
            grouping_length := self._grouping_length(text, cursor, separator)
        ):
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
            valid = groups[-1] == primary_grouping
            valid = valid and all(size == secondary_grouping for size in groups[1:-1])
            valid = valid and 1 <= groups[0] <= secondary_grouping
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
        separator_end = cursor + len(decimal)
        if (
            text.startswith(decimal, cursor)
            and separator_end < len(text)
            and text[separator_end] in self._digits
        ):
            captures.append(
                Capture(
                    "decimal-separator",
                    cursor,
                    separator_end,
                    decimal,
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

    def _match_other_groupings(self, text: str, start: int) -> list[_FlexibleMatch]:
        """Each reading at ``start`` in another grouping of the language that groups."""
        found = []
        for separator, primary, secondary, spec in self._other_groupings:
            match = self._match(text, start, (separator, primary, secondary))
            if match is None:
                continue
            end, captures, value = match
            integer = next(capture for capture in captures if capture.name == "integer")
            if not integer.text.isdigit():
                found.append(_FlexibleMatch(end, captures, value, spec))
        return found

    def _match_decimal_styles(self, text: str, start: int) -> list[_FlexibleMatch]:
        """Each reading at ``start`` in another decimal style of the language."""
        found = []
        for grouping, decimal, primary, secondary, spec in self._decimal_styles:
            match = self._match(text, start, (grouping, primary, secondary), decimal)
            if match is not None:
                end, captures, value = match
                found.append(_FlexibleMatch(end, captures, value, spec))
        return found

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible decimal candidates in source order."""
        decimals = _detect_flexible(text, self.locale, self.type, self._spec, self._match)
        if self._other_groupings:
            spans = {(item["start"], item["end"]) for item in decimals}
            decimals.extend(
                item
                for item in _detect_flexible_alternatives(
                    text, self.locale, self.type, self._match_other_groupings
                )
                if (item["start"], item["end"]) not in spans
            )
        if self._decimal_styles:
            # Only where the locale's own styles do not already read the text (kal's
            # ruling of 2026-09-24): "1,234" stays 1234 alone in en_US, while "1 234,56"
            # reads 1234.56 though en_US reads a fragment "1" of it.
            own = [(item["start"], item["end"]) for item in decimals]
            decimals.extend(
                item
                for item in _detect_flexible_alternatives(
                    text, self.locale, self.type, self._match_decimal_styles
                )
                if not any(s <= item["start"] and item["end"] <= e for s, e in own)
            )
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
            if cursor - start == 1 and not _is_isolated_letter(text, start):
                continue
            if cursor < len(text) and _is_word_character(text[cursor]):
                continue
            surface = text[start:cursor]
            # "II's" is one word, so a Roman reading spans a possessive or plural suffix
            # written after an apostrophe, from the language's plural table (see
            # _plural_suffix); a language without an entry reads no suffix.
            position = icu.ParsePosition(0)
            parsed = self._roman.parse(surface, position)
            if parsed is None or position.getIndex() != len(surface):
                continue
            value = parsed.getInt64()
            if self._roman.format(value, rule_set) != surface:
                continue
            captures = [Capture("integer", start, cursor, surface, str(value), "roman")]
            end = cursor
            plural = (
                _plural_suffix(text, cursor, self.locale)
                if _is_apostrophe(text[cursor : cursor + 1])
                else None
            )
            if plural is not None:
                end, suffix_captures = plural
                captures.extend(suffix_captures)
            return end, tuple(captures), NumberValue(str(value), None)
        return None


class FlexibleLowercaseRomanDetector:
    """Recognize lowercase Roman cardinals ("iv", "xii") as their own type.

    :class:`FlexibleNumberDetector` refuses these by default, since the surfaces collide
    with unit abbreviations and words ("mix", "mi", "cm", "di"), and its
    ``accept_lowercase_roman`` option deposits them under the same
    ``number:cardinal:roman`` type as the uppercase ones. This reader deposits exactly the
    readings that option adds, under ``number:cardinal:roman-lower`` (after ICU's
    ``%roman-lower`` rule set), so a consumer includes or excludes them by type. The value
    is a :class:`NumberValue` of the integer, as for uppercase Roman numerals; the rule
    sets and their alphabets are ICU's (``URBNFRuleSetTag.NUMBERING_SYSTEM``).
    """

    group = "number"
    type = "number:cardinal:roman-lower"

    def __init__(self, locale: str, *, accept_single_letter_roman: bool = True) -> None:
        self.locale = locale
        self.accept_single_letter_roman = accept_single_letter_roman
        self._number = FlexibleNumberDetector(
            locale,
            accept_single_letter_roman=accept_single_letter_roman,
            accept_lowercase_roman=True,
        )
        # Only the rule sets the default reader leaves out, so every reading here is one
        # it refuses; the uppercase ones stay number:cardinal:roman's.
        self._number._roman_rule_sets = tuple(
            name for name in self._number._roman_rule_sets if "lower" in name.casefold()
        )

    @property
    def has_rule_sets(self) -> bool:
        """Whether ICU gives the locale a lowercase Roman rule set."""
        return bool(self._number._roman_rule_sets)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return lowercase Roman cardinals in source order."""
        return _detect_flexible(
            text, self.locale, self.type, self._number._spec, self._number._match_roman
        )


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
# ICU names a weekday relative to now too ("next Tuesday", "last Fri."): LAST, THIS,
# and NEXT only, since ICU writes no "the Tuesday after next".
_RELATIVE_WEEKDAYS = (
    "SUNDAY",
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
)
_RELATIVE_STYLES = (("LONG", "wide"), ("SHORT", "short"), ("NARROW", "narrow"))


def _relative_formatter(icu_locale, style: str):
    """ICU's relative-date formatter for the locale at a style (LONG, SHORT, NARROW)."""
    return icu.RelativeDateTimeFormatter(
        icu_locale,
        icu.NumberFormat.createInstance(icu_locale),
        getattr(icu.UDateRelativeDateTimeFormatterStyle, style),
        icu.UDisplayContext.CAPITALIZATION_NONE,
    )


_RELATIVE_DIRECTIONS = (
    ("LAST", -1),
    ("LAST_2", -2),
    ("THIS", 0),
    ("NEXT", 1),
    ("NEXT_2", 2),
)


@lru_cache(maxsize=128)
def _relative_date_vocabulary(locale: str):
    """The numeric templates and named phrases ICU writes at its long, short and narrow styles.

    Each entry ends with its style, whose formatter checks a reading ("in 2 hr.", "last
    mo.", "next Tue."); the first style that writes a surface keeps it.
    """
    icu_locale = icu.Locale(locale)
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

    numeric: dict[tuple[str, str], tuple[int, str, object, str]] = {}
    named: dict[str, tuple[str, int, str, object, object, str]] = {}
    for style, _form in _RELATIVE_STYLES:
        formatter = _relative_formatter(icu_locale, style)
        for unit_member in _RELATIVE_NUMERIC_UNITS:
            unit_enum = getattr(icu.URelativeDateTimeUnit, unit_member, None)
            if unit_enum is None:
                continue
            unit_name = unit_member.lower()
            for sign in (-1, 1):
                for magnitude in sorted(required_samples):
                    if sign < 0 and magnitude == 0:
                        # ICU assigns numeric zero to the future form regardless of sign.
                        continue
                    surface = formatter.formatNumeric(sign * magnitude, unit_enum)
                    number_surface = number_format.format(magnitude)
                    number_start = surface.find(number_surface)
                    if number_start < 0:
                        # note: A locale/magnitude whose numeral is not embedded is skipped.
                        continue
                    number_end = number_start + len(number_surface)
                    template = (surface[:number_start], surface[number_end:])
                    if not template[0] and not template[1]:
                        # A template with no marker words would reduce this lane to a
                        # bare-number matcher; no ICU relative surface is a naked numeral.
                        continue
                    numeric.setdefault(template, (sign, unit_name, unit_enum, style))

        named_units = [
            (member, offsets)
            for member in _RELATIVE_NAMED_UNITS
            for offsets in [_RELATIVE_DIRECTIONS]
        ] + [(member, (("LAST", -1), ("THIS", 0), ("NEXT", 1))) for member in _RELATIVE_WEEKDAYS]
        for unit_member, directions in named_units:
            unit_enum = getattr(icu.UDateAbsoluteUnit, unit_member, None)
            if unit_enum is None:
                continue
            for direction_member, offset in directions:
                direction_enum = getattr(icu.UDateDirection, direction_member)
                try:
                    surface = formatter.format(direction_enum, unit_enum)
                except icu.ICUError:
                    continue
                if surface:
                    named.setdefault(
                        surface.casefold(),
                        (surface, offset, unit_member.lower(), unit_enum, direction_enum, style),
                    )

        now_unit = icu.UDateAbsoluteUnit.NOW
        plain = icu.UDateDirection.PLAIN
        try:
            now_surface = formatter.format(plain, now_unit)
        except icu.ICUError:
            now_surface = ""
        if now_surface:
            named.setdefault(
                now_surface.casefold(), (now_surface, 0, "now", now_unit, plain, style)
            )

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
        self._formatters = {
            style: _relative_formatter(icu.Locale(locale), style) for style, _ in _RELATIVE_STYLES
        }
        self._forms = dict(_RELATIVE_STYLES)
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
        for surface, offset, unit_name, unit_enum, direction_enum, style in self._named_phrases:
            end = start + len(surface)
            if text[start:end].casefold() != surface.casefold():
                continue
            if self._continues_word(text, end):
                continue
            canonical = self._formatters[style].format(direction_enum, unit_enum)
            # note: The reformat guard is the correctness gate for every deposited value.
            if canonical.casefold() != text[start:end].casefold():
                continue
            form = self._forms[style]
            capture = Capture("relative", start, end, text[start:end], offset, form)
            value = RelativeDateValue(offset, unit_name, self._direction(offset))
            return end, (capture,), value
        return None

    def _numeric_match(self, text: str, start: int):
        for prefix, suffix, sign, unit_name, unit_enum, style in self._numeric_templates:
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
            canonical = self._formatters[style].formatNumeric(offset, unit_enum)
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


@cache
def _language_percent_words(language: str, names: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """The percent unit's wide names across the locales of ``language``, longest first.

    English gives "percent" (en_US) and "per cent" (en_GB and others).
    """
    words: set[str] = set()
    for name in _language_locale_names(language, names):
        locale = icu.Locale(name)
        wide = icu.MeasureFormat(locale, icu.UMeasureFormatWidth.WIDE)
        number_format = icu.NumberFormat.createInstance(locale)
        for amount in _plural_samples(name):
            number_surface = number_format.format(amount)
            formatted = wide.formatMeasures(
                [icu.Measure(icu.Formattable(amount), icu.MeasureUnit.forIdentifier("percent"))]
            )
            if formatted.startswith(number_surface):
                word = formatted[len(number_surface) :].strip()
                if word and not any(character.isdigit() for character in word):
                    words.add(word)
    return tuple(sorted(words, key=len, reverse=True))


class FlexiblePercentDetector:
    """Recognize flexible numbers adjacent to the locale's percent symbol.

    The percent may also be written as a wide name ICU gives the percent unit in any
    locale of the language ("5 percent", "5 per cent"), after the number.
    """

    group = "number"
    type = "number:percent"

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
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
        self._words = tuple(
            word
            for word in _language_percent_words(icu.Locale(locale).getLanguage(), self.locales)
            if word != self._percent
        )

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
        spaced = self._space(text, cursor)
        if text.startswith(self._percent, spaced):
            cursor = spaced
            end = cursor + len(self._percent)
            percent = Capture("percent", cursor, end, self._percent, None, "symbol")
        else:
            word = next(
                (
                    word
                    for word in self._words
                    if spaced > cursor
                    and text[spaced : spaced + len(word)].casefold() == word.casefold()
                    and not (spaced + len(word) < len(text) and text[spaced + len(word)].isalnum())
                ),
                None,
            )
            if word is None:
                return None
            cursor = spaced
            end = cursor + len(word)
            percent = Capture("percent", cursor, end, text[cursor:end], None, "wide")
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


@cache
def _negative_currency_wraps(
    locale: str, currency: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, str], ...]:
    """What ICU writes around a currency amount to make it negative, in the language.

    Each is ``(before, after)``: the negative form with the positive one taken out, at
    ICU's standard and accounting sign displays: en_US "-$42.50" gives ``("-", "")`` and
    "($42.50)" ``("(", ")")``. A sign ICU writes inside, after the symbol ("US$-42.50"),
    is the number's own and needs none.
    """
    wraps: dict[tuple[str, str], None] = {}
    signs = (icu.UNumberSignDisplay.AUTO, icu.UNumberSignDisplay.ACCOUNTING)
    for name in _language_locales(locale, names):
        base = icu.NumberFormatter.withLocale(icu.Locale(name)).unit(icu.CurrencyUnit(currency))
        for sign in signs:
            formatter = base.sign(sign)
            positive = str(formatter.formatDouble(42.5))
            negative = str(formatter.formatDouble(-42.5))
            index = negative.find(positive)
            if index >= 0 and negative != positive:
                wraps.setdefault((negative[:index], negative[index + len(positive) :]))
    return tuple(wraps)


class FlexibleCurrencyDetector:
    """Recognize a reflective currency symbol or name around a scaled flexible number."""

    group = "number"

    def __init__(self, locale: str, currency: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
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
        for available in map(icu.Locale, _language_locale_names(language, self.locales)):
            narrow = self._currency_affix(available, currency, icu.UNumberUnitWidth.NARROW)
            short = self._currency_affix(available, currency, icu.UNumberUnitWidth.SHORT)
            # A foreign locale's narrow symbol is locally ambiguous; only its distinct
            # short form carries enough information to import into this locale.
            if available.getName() == requested_locale or short != narrow:
                reflected_symbols.add(short)
            reflected_symbols.add(
                self._currency_affix(available, currency, icu.UNumberUnitWidth.ISO_CODE)
            )
        # The language's curated surfaces for this currency ("Rs" for INR; see
        # icukit.unit_surfaces).
        reflected_symbols.update(
            surface for surface, code in curated_currency_surfaces(language) if code == currency
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

    def _match_signed(self, text: str, start: int):
        """An amount ICU's negative forms wrap ("-$42.50", "($42.50)"), else a plain one."""
        for before, after in _negative_currency_wraps(self.locale, self.currency, self.locales):
            if not before or not text.startswith(before, start):
                continue
            inner = self._match(text, start + len(before))
            if inner is None:
                continue
            end, captures, value = inner
            if not text.startswith(after, end) or value.decimal.startswith("-"):
                continue
            wrap = [Capture("sign", start, start + len(before), before, None, "symbol")]
            if after:
                wrap.append(Capture("sign", end, end + len(after), after, None, "symbol"))
            ordered = tuple(sorted((*captures, *wrap), key=lambda c: (c.start, c.end)))
            return end + len(after), ordered, NumberValue("-" + value.decimal, self.currency)
        return self._match(text, start)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible currency candidates in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match_signed)


@cache
def _ascii_confusables(mark: str) -> tuple[str, ...]:
    """ASCII punctuation ICU's confusable data maps to the same skeleton as ``mark``.

    The double prime "″" CLDR writes for inches is confusable with a straight double
    quote, and the prime "′" for feet with an apostrophe or a backtick; text usually
    writes the ASCII forms.
    """
    checker = icu.SpoofChecker()
    skeleton = checker.getSkeleton(0, mark)
    return tuple(
        candidate
        for candidate in map(chr, range(33, 127))
        if not candidate.isalnum()
        and candidate != mark
        and checker.getSkeleton(0, candidate) == skeleton
    )


@cache
def _plural_samples(locale: str) -> tuple[int | float, ...]:
    """One amount for each plural category ICU's rules give the locale.

    ICU chooses the category (``PluralRules.select``); the amounts scanned are the
    integers 0 to 200 and one decimal (1.5), enough to reach every category CLDR
    defines ("2 километра" is Russian's few, "5 километров" its many).
    """
    rules = icu.PluralRules.forLocale(icu.Locale(locale))
    samples: dict[str, int | float] = {}
    for amount in (*range(0, 201), 1.5):
        samples.setdefault(rules.select(amount), amount)
    return tuple(samples.values())


def _unit_surface_variants(surface: str) -> tuple[str, ...]:
    """A unit surface and the spellings ICU equates with it.

    Its NFKC form ("km²" is "km2") and, for each mark in it, the ASCII confusables of
    that mark ("12″" is written 12"). Letters and digits are never swapped for
    confusables, so no letter reads as a digit.
    """
    variants: set[str] = set()
    for base in {surface, icu.Normalizer2.getNFKCInstance().normalize(surface)}:
        choices = [
            (character,)
            if character.isalnum() or character.isspace()
            else (character, *_ascii_confusables(character))
            for character in base
        ]
        variants.update("".join(combination) for combination in product(*choices))
    return tuple(sorted(variants, key=len, reverse=True))


@cache
def _measure_surfaces(
    locale: str, unit: str, per_valid: bool, names: tuple[str, ...] | None = None
) -> tuple[list[tuple[str, str, bool, str]], list[tuple[str, str, bool, str]]]:
    """The unit and per-unit surfaces ICU formats for ``unit`` in the locale's language.

    Each is ``(surface, width, spaced, unit)``, the detector's own locale first so its
    width names win a tie; see :class:`FlexibleMeasureDetector`.
    """
    measure_unit = icu.MeasureUnit.forIdentifier(unit)
    per_unit = f"per-{unit}"
    surfaces: dict[tuple[str, str, bool, str], None] = {}
    rates: dict[tuple[str, str, bool, str], None] = {}
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        number_format = icu.NumberFormat.createInstance(icu_locale)
        base = icu.NumberFormatter.withLocale(icu_locale)
        for width, width_name in (
            (icu.UNumberUnitWidth.SHORT, "short"),
            (icu.UNumberUnitWidth.NARROW, "narrow"),
            (icu.UNumberUnitWidth.FULL_NAME, "wide"),
        ):
            # NumberFormatter, not MeasureFormat: it also formats a unit ICU composes from
            # an SI prefix or a product ("kilovolt", "kilonewton"), as CLDR writes it.
            formatter = base.unit(measure_unit).unitWidth(width)
            carrier = base.unit(icu.MeasureUnit.createMeter()).unitWidth(width)
            for amount in _plural_samples(name):
                number_surface = number_format.format(amount)
                formatted = str(formatter.formatDouble(amount))
                number_start = formatted.find(number_surface)
                if number_start < 0:
                    continue
                number_end = number_start + len(number_surface)
                prefix = formatted[:number_start].strip()
                raw_suffix = formatted[number_end:]
                suffix = raw_suffix.strip()
                if prefix or not suffix:
                    continue
                spaced = raw_suffix != raw_suffix.lstrip()
                for variant in _unit_surface_variants(suffix):
                    surfaces.setdefault((variant, width_name, spaced, unit))
                if not per_valid:
                    continue
                # CLDR's per pattern: the rate "12 m/km²" is the plain "12 m" followed by
                # the per form "/km²", which follows a bare number the same way. The
                # numerator unit is only a carrier for the pattern (meter is a unit every
                # locale formats); the reading has none, as in "1.0/km²".
                plain = str(carrier.formatDouble(amount))
                try:
                    rate = str(carrier.perUnit(measure_unit).formatDouble(amount))
                except icu.ICUError:
                    # ICU formats no per form for some composed units ("/kV").
                    continue
                if rate.startswith(plain) and len(rate) > len(plain):
                    tail = rate[len(plain) :]
                    for variant in _unit_surface_variants(tail.strip()):
                        rates.setdefault((variant, width_name, tail != tail.lstrip(), per_unit))
    # The language's curated surfaces ICU does not write ("500cc", "185 lbs"; see
    # icukit.unit_surfaces): the unit and its value stay ICU's.
    for surface, target in curated_unit_surfaces(icu.Locale(locale).getLanguage()):
        if target == unit:
            for variant in _unit_surface_variants(surface):
                surfaces.setdefault((variant, "curated", True, unit))
        elif per_valid and target == per_unit:
            for variant in _unit_surface_variants(surface):
                rates.setdefault((variant, "curated", True, per_unit))
    return list(surfaces), list(rates)


class FlexibleMeasureDetector:
    """Recognize a flexible number followed by a reflectively derived ICU unit surface.

    The surfaces are the unit's short, narrow, and wide forms as ICU formats them
    ("5 km", "5km", "5 kilometers"), in every locale of the language (en_GB's "5
    kilometres" reads in en_US text; see :func:`_language_locales`), for an amount in
    each of that locale's plural categories (see :func:`_plural_samples`), each also in
    the spellings ICU equates with it (see :func:`_unit_surface_variants`: "km2", 12").
    A rate ("1.0/km²", "3 per square kilometer") is read through CLDR's per-unit
    pattern, with the value's unit ``per-<unit>``; a symbol-only per form follows the
    number directly. A per form written without an amount ("/s", "per second") reads as
    a :class:`~icukit.detectors.UnitValue` of the rate's unit, where no digit is
    written right before it.
    """

    group = "measure"

    def __init__(self, locale: str, unit: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        self.unit = unit
        self.type = f"measure:{unit}"
        self._number = FlexibleNumberDetector(locale)

        measure_unit = icu.MeasureUnit.forIdentifier(unit)
        if measure_unit.getIdentifier() != unit:
            raise ValueError(f"unit is not a canonical ICU identifier: {unit!r}")

        per_unit = f"per-{unit}"
        try:
            per_valid = icu.MeasureUnit.forIdentifier(per_unit).getIdentifier() == per_unit
        except icu.ICUError:
            per_valid = False
        surfaces, rates = _measure_surfaces(locale, unit, per_valid, self.locales)
        if not surfaces:
            raise ValueError(f"ICU exposes no supported suffix surface for unit: {unit!r}")
        self._units = tuple(sorted(surfaces + rates, key=lambda item: len(item[0]), reverse=True))
        # Longest first, those written as the text is (spaced or attached) ahead.
        self._ordered_units = {
            has_space: tuple(sorted(self._units, key=lambda item: item[2] != has_space))
            for has_space in (False, True)
        }

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
        # A superscript digit continues a unit symbol ("km²" is not "km").
        return icu.Char.isalnum(character) or category in {
            icu.UCharCategory.NON_SPACING_MARK,
            icu.UCharCategory.COMBINING_SPACING_MARK,
            icu.UCharCategory.ENCLOSING_MARK,
            icu.UCharCategory.CONNECTOR_PUNCTUATION,
            icu.UCharCategory.OTHER_NUMBER,
        }

    def _match(
        self, text: str, start: int, digit_may_follow: bool = False
    ) -> _FlexibleMatch | None:
        match = self._number._match(text, start)
        if match is None:
            return None
        number_end, captures, value = match
        unit_start = self._space(text, number_end)
        has_space = unit_start != number_end
        for surface, width, _expects_space, unit in self._ordered_units[has_space]:
            # A rate's per form ("/km²") follows the number directly, not after a space.
            cursor = number_end if unit != self.unit and not surface[:1].isalnum() else unit_start
            if not text.startswith(surface, cursor):
                continue
            end = cursor + len(surface)
            # A mixed unit's first component may run straight into the next number
            # ("5'10\""): a mark ends the unit even with a digit after it.
            open_mark = (
                digit_may_follow and not surface[-1:].isalnum() and text[end : end + 1].isdigit()
            )
            if self._continues_word(text, end) and not open_mark:
                continue
            unit_capture = Capture("unit", cursor, end, surface, unit, "symbol")
            spec = MeasureFormatSpec(self.locale, unit, width)
            return _FlexibleMatch(
                end,
                (*captures, unit_capture),
                MeasureValue(value.decimal, unit),
                spec,
            )
        return None

    def _match_per_form(self, text: str, start: int) -> _FlexibleMatch | None:
        """A rate's per form at ``start`` with no amount before it: "/s", "per second"."""
        if start and (text[start - 1] in self._number._digits or text[start - 1].isdigit()):
            return None
        for surface, width, _expects_space, unit in self._units:
            if unit == self.unit or not text.startswith(surface, start):
                continue
            end = start + len(surface)
            if self._continues_word(text, end):
                continue
            unit_capture = Capture("unit", start, end, surface, unit, "symbol")
            spec = MeasureFormatSpec(self.locale, unit, width)
            return _FlexibleMatch(end, (unit_capture,), UnitValue(unit), spec)
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return flexible measure candidates in source order, a bare per form beside them."""
        measures = _detect_flexible(text, self.locale, self.type, None, self._match)
        # A per form inside a rate with its amount ("5 per square kilometre") is that
        # rate's, not a bare one.
        rates = [
            item
            for item in _detect_flexible(text, self.locale, self.type, None, self._match_per_form)
            if not any(m["start"] <= item["start"] and item["end"] <= m["end"] for m in measures)
        ]
        return sorted((*measures, *rates), key=lambda item: (item["start"], item["end"]))


class FlexibleMixedMeasureDetector:
    """Recognize a mixed-unit measure, such as feet and inches: "5'10\"", "5 ft, 10 in".

    ``unit`` is an ICU mixed-unit identifier of two or more components (``foot-and-inch``,
    ``pound-and-ounce``, ``hour-and-minute-and-second``). Everything is read from ICU:
    each component's surfaces as :class:`FlexibleMeasureDetector` reads a single unit,
    and, for each adjacent pair (itself an ICU mixed unit), the joiner from ICU's own
    formatting of the pair at each width ("5′ 10″", "5 ft, 10 in"), optional where the
    joiner is only a space, and the factor between the two (1.5 feet formats as 1 foot
    6 inches). The value is the whole quantity in the smallest component, which is exact
    ("5'10\"" is 70 inches; "1 hr, 15 min, 27 sec" is 4527 seconds).
    """

    group = "measure"

    def __init__(self, locale: str, unit: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        self.unit = unit
        self.type = f"measure:{unit}"
        parts = unit.split("-and-")
        if len(parts) < 2:
            raise ValueError(f"expected a mixed unit identifier of two or more parts: {unit!r}")
        self._number = FlexibleNumberDetector(locale)
        self._components = tuple(
            FlexibleMeasureDetector(locale, part, locales=self.locales) for part in parts
        )
        icu_locale = icu.Locale(locale)
        self._factors: list[int] = []
        self._joiners: list[tuple[str, ...]] = []
        for index in range(len(parts) - 1):
            pair = icu.MeasureUnit.forIdentifier(f"{parts[index]}-and-{parts[index + 1]}")
            joiners: set[str] = set()
            factor = None
            for width in (
                icu.UNumberUnitWidth.NARROW,
                icu.UNumberUnitWidth.SHORT,
                icu.UNumberUnitWidth.FULL_NAME,
            ):
                formatter = icu.NumberFormatter.withLocale(icu_locale).unit(pair).unitWidth(width)
                rendered = str(formatter.formatDouble(1.5))
                numbers = [(i, i + len(match)) for i, match in _digit_spans(rendered)]
                if len(numbers) != 2:
                    continue
                factor = int(rendered[numbers[1][0] : numbers[1][1]]) * 2
                between = rendered[numbers[0][1] : numbers[1][0]]
                for surface, *_rest in self._components[index]._units:
                    if between.startswith(surface) or between.lstrip().startswith(surface):
                        joiners.add(between.lstrip()[len(surface) :])
                        break
            if factor is None or not joiners:
                raise ValueError(f"ICU formats no two-number surface for mixed unit: {unit!r}")
            self._factors.append(factor)
            self._joiners.append(
                tuple(sorted({*joiners, *(j.strip() for j in joiners)}, key=len, reverse=True))
            )
        self._spec = MeasureFormatSpec(locale, unit, "mixed")
        self._small_unit = parts[-1]

    def _match(self, text: str, start: int) -> _FlexibleMatch | None:
        first = self._components[0]._match(text, start, digit_may_follow=True)
        if first is None or first.value.unit != self._components[0].unit:
            return None
        return self._continue(text, first, 1, Decimal(first.value.decimal), first.captures)

    def _continue(self, text, previous, index, total, captures) -> _FlexibleMatch | None:
        """The components from ``index`` on, each after a joiner ICU writes."""
        if index == len(self._components):
            value = MeasureValue(format(total, "f"), self._small_unit)
            return _FlexibleMatch(previous.end, captures, value, self._spec)
        component = self._components[index]
        last = index == len(self._components) - 1
        for joiner in self._joiners[index - 1]:
            if not text.startswith(joiner, previous.end):
                continue
            match = component._match(text, previous.end + len(joiner), digit_may_follow=not last)
            if match is None or match.value.unit != component.unit:
                continue
            carried = total * self._factors[index - 1] + Decimal(match.value.decimal)
            found = self._continue(text, match, index + 1, carried, (*captures, *match.captures))
            if found is not None:
                return found
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping mixed-unit measures in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


# CLDR's numeric duration patterns (durationUnits) and the ICU mixed unit each writes.
_NUMERIC_DURATION_UNITS = {
    "hms": ("hour-and-minute-and-second", "second"),
    "hm": ("hour-and-minute", "minute"),
    "ms": ("minute-and-second", "second"),
}
_DURATION_FACTORS = {"h": 3600, "m": 60, "s": 1}


@cache
def _numeric_duration_patterns(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, tuple[str, ...], tuple[int, ...], tuple[str, ...], str], ...]:
    """CLDR's numeric duration patterns across the locales of ``language``.

    Each is ``(key, fields, widths, separators, decimal)``: "m:ss" is ``("ms", ("m",
    "s"), (1, 2), (":",), ".")``, the decimal being the locale's, since ICU writes a
    fraction of the last field with it ("1:47.22"). Read from ICU's unit data
    (``durationUnits``), without duplicates.
    """
    patterns: dict[tuple, None] = {}
    for name in _language_locale_names(language, names):
        locale = icu.Locale(name)
        try:
            table = icu.ResourceBundle("ICUDATA-unit", locale).get("durationUnits")
        except icu.ICUError:
            continue
        decimal = (
            icu.NumberFormat.createInstance(locale)
            .getDecimalFormatSymbols()
            .getSymbol(icu.DecimalFormatSymbols.kDecimalSeparatorSymbol)
        )
        for index in range(table.getSize()):
            entry = table.get(index)
            key = entry.getKey()
            if key not in _NUMERIC_DURATION_UNITS:
                continue
            fields: list[str] = []
            widths: list[int] = []
            separators: list[str] = []
            literal = ""
            for character in entry.getString():
                if character in _DURATION_FACTORS:
                    if fields and fields[-1] == character and not literal:
                        widths[-1] += 1
                        continue
                    if fields:
                        separators.append(literal)
                    fields.append(character)
                    widths.append(1)
                    literal = ""
                else:
                    literal += character
            if len(fields) >= 2 and len(separators) == len(fields) - 1 and all(separators):
                patterns.setdefault((key, tuple(fields), tuple(widths), tuple(separators), decimal))
    return tuple(patterns)


class FlexibleNumericDurationDetector:
    """Recognize a numeric duration as CLDR writes one: "1:47.22", "2:03:04", "2:30".

    The patterns are CLDR's numeric duration units (``m:ss``, ``h:mm:ss``, ``h:mm``) in
    the locales of the language (see :func:`_numeric_duration_patterns`), so Danish
    also reads "1.47". The first field takes any number of digits and the rest exactly
    the pattern's, each below 60; the last field may carry a fraction written with the
    locale's decimal separator, as ICU formats one. The value is the whole duration in
    the smallest field, as for a mixed unit ("1:47.22" is 107.22 seconds), with the
    fields captured by their pattern letters. Where two patterns read the same text
    ("2:30" as two hours thirty and as two minutes thirty), both readings are kept.
    """

    group = "measure"
    type = "measure:duration:numeric"

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        self._digits = {digit: str(value) for digit, value in _locale_digit_map(locale).items()}
        self._patterns = _numeric_duration_patterns(icu.Locale(locale).getLanguage(), self.locales)

    def _digit_run(self, text: str, cursor: int) -> int:
        end = cursor
        while end < len(text) and text[end] in self._digits:
            end += 1
        return end

    def _read(self, text: str, start: int, pattern) -> _FlexibleMatch | None:
        key, fields, widths, separators, decimal = pattern
        cursor = start
        captures: list[Capture] = []
        values: list[int] = []
        for index, (field, width) in enumerate(zip(fields, widths, strict=True)):
            if index:
                separator = separators[index - 1]
                if not text.startswith(separator, cursor):
                    return None
                cursor += len(separator)
            end = self._digit_run(text, cursor)
            length = end - cursor
            if length == 0 or (index and length != width):
                return None
            digits = "".join(self._digits[character] for character in text[cursor:end])
            value = int(digits)
            if index and value >= 60:
                return None
            captures.append(Capture(field, cursor, end, text[cursor:end], value, "numeric"))
            values.append(value)
            cursor = end
        fraction = ""
        after = cursor + len(decimal)
        if text.startswith(decimal, cursor) and after < len(text) and text[after] in self._digits:
            end = self._digit_run(text, after)
            fraction = "".join(self._digits[character] for character in text[after:end])
            captures.append(Capture("decimal-separator", cursor, after, decimal, None, "symbol"))
            captures.append(Capture("fraction", after, end, text[after:end], fraction, "numeric"))
            cursor = end
        # A duration does not run on into more digits or another field.
        if cursor < len(text) and text[cursor] in self._digits:
            return None
        for separator in (*separators, decimal):
            follow = cursor + len(separator)
            if text.startswith(separator, cursor) and text[follow : follow + 1] in self._digits:
                return None
        smallest = _DURATION_FACTORS[fields[-1]]
        total = Decimal(
            sum(
                value * _DURATION_FACTORS[field]
                for field, value in zip(fields, values, strict=True)
            )
        )
        total = total / smallest + (Decimal(f"0.{fraction}") if fraction else 0)
        unit, small_unit = _NUMERIC_DURATION_UNITS[key]
        return _FlexibleMatch(
            cursor,
            tuple(captures),
            MeasureValue(format(total, "f"), small_unit),
            MeasureFormatSpec(self.locale, unit, "numeric"),
        )

    def _match(self, text: str, start: int) -> list[_FlexibleMatch]:
        if start and (text[start - 1] in self._digits or text[start - 1] in {":", "."}):
            return []
        found = []
        for pattern in self._patterns:
            match = self._read(text, start, pattern)
            if match is not None:
                found.append(match)
        return found

    def detect(self, text: str) -> list[ValueDetection]:
        """Return numeric durations in source order, every pattern's reading at a start."""
        return _detect_flexible_alternatives(text, self.locale, self.type, self._match)


def _digit_spans(text: str):
    cursor = 0
    while cursor < len(text):
        if text[cursor].isdigit():
            end = cursor
            while end < len(text) and text[end].isdigit():
                end += 1
            yield cursor, text[cursor:end]
            cursor = end
        else:
            cursor += 1


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


def _spellout_rulesets(locale: str) -> tuple[str, ...]:
    """The locale's public RBNF spell-out rule sets a reader inverts.

    The cardinal, ordinal, and year ones, plain and verbose ("%spellout-ordinal",
    "%spellout-numbering-year", "%spellout-cardinal-verbose"); the plain "numbering"
    sets write what the cardinal ones do.
    """
    formatter = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.SPELLOUT, icu.Locale(locale))
    names = tuple(
        formatter.getRuleSetName(index) for index in range(formatter.getNumberOfRuleSetNames())
    )
    return tuple(
        name
        for name in names
        if any(kind in name.casefold() for kind in ("cardinal", "ordinal", "year"))
    )


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
    """Recognize canonical ICU spelled-out numbers derived from locale RBNF data.

    The cardinal rule set by default; ``ruleset`` chooses another the locale has (see
    :func:`_spellout_rulesets`): "%spellout-ordinal" ("twenty-first"),
    "%spellout-numbering-year" ("nineteen ninety-nine"), "%spellout-cardinal-verbose"
    ("one hundred and one"). The type is ``number:spellout`` for the default and
    ``number:spellout:<rule set>`` otherwise ("number:spellout:ordinal").

    A lone token is suppressed only when it is one of the ambiguous unit words obtained
    by formatting 0 through 9 ("one", "first"). Larger lone magnitudes and every
    multi-token canonical surface remain eligible for deposit-and-hold alongside other
    detector candidates.
    """

    group = "number"
    type = "number:spellout"

    def __init__(self, locale: str, *, ruleset: str | None = None) -> None:
        self.locale = locale
        self._rbnf, self._ruleset = _spellout_formatter_and_ruleset(locale)
        if ruleset is not None and ruleset != self._ruleset:
            if ruleset not in _spellout_rulesets(locale):
                raise ValueError(f"no spellout rule set {ruleset!r} in {locale!r}")
            self._ruleset = ruleset
            self.type = "number:spellout:" + ruleset.lstrip("%").removeprefix("spellout-")
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

    def _match(self, text: str, start: int, token_end=None, guard: bool = True):
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
            if guard and token_index == 1 and surface.casefold() in self._ambiguous_units:
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
        return self._scan(text, guard=True)

    def _scan(self, text: str, *, guard: bool) -> list[ValueDetection]:
        """The greedy scan, with or without the guard on a lone ambiguous unit word."""
        token_ends: dict[int, int | None] = {}

        def token_end(cursor: int) -> int | None:
            if cursor not in token_ends:
                token_ends[cursor] = self._token_end(text, cursor)
            return token_ends[cursor]

        def match(source: str, start: int):
            return self._match(source, start, token_end, guard)

        return _detect_flexible(text, self.locale, self.type, self._spec, match)


class FlexibleLoneSpelloutDetector(FlexibleSpelloutDetector):
    """Recognize the lone spelled-out unit words the spell-out reader refuses.

    :class:`FlexibleSpelloutDetector` does not read a lone token that is one of the
    locale's words for 0 through 9 in its rule set ("one", "first"), since most are not
    numbers in running text. This reader deposits exactly those refused readings: the
    readings the spell-out reader makes with its guard lifted, less those it makes with
    it, which are the lone unit words (the multi-token readings do not change, since the
    guard only ever withholds a one-token reading). The type is
    ``number:spellout-lone`` for the cardinal rule set and
    ``number:spellout-lone:<rule set>`` otherwise ("number:spellout-lone:ordinal" reads
    "first" as 1), and the value is the spell-out reader's :class:`NumberValue`.
    """

    type = "number:spellout-lone"

    def __init__(self, locale: str, *, ruleset: str | None = None) -> None:
        super().__init__(locale, ruleset=ruleset)
        # The parent names a non-default rule set's type on the instance.
        chosen = self.__dict__.get("type", FlexibleSpelloutDetector.type)
        self.type = FlexibleLoneSpelloutDetector.type + chosen.removeprefix(
            FlexibleSpelloutDetector.type
        )

    def detect(self, text: str) -> list[ValueDetection]:
        """Return the lone unit words the spell-out reader refuses, in source order."""
        return [
            detection
            for detection in self._scan(text, guard=False)
            if detection["text"].casefold() in self._ambiguous_units
            and not any(character in self._connectors for character in detection["text"])
        ]


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


@cache
def _language_day_periods(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, int, bool], ...]:
    """Every CLDR day-period form of ``language``, as ``(form, index, narrow)``.

    ICU formats the am (index 0) and pm (1) day period at each width, from the
    abbreviated (``a``) and wide (``aaaa``) to the narrow (``aaaaa``) field, for every
    available locale of the language: regional forms are part of the language's
    writing, so en_US reads en_CA's "a.m." and the narrow "a"/"p". ``narrow`` marks a
    one-letter form. Longest first, so a dotted form wins over a shorter one sharing
    its start; case-folded duplicates keep their first reading.
    """
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale("en_US"))
    instants = []
    for hour in (1, 13):
        calendar.clear()
        calendar.set(2026, 0, 3, hour, 0, 0)
        instants.append(calendar.getTime())
    seen: dict[str, tuple[str, int, bool]] = {}
    for name in _language_locale_names(language, names):
        locale = icu.Locale(name)
        for field in ("a", "aaaa", "aaaaa"):
            formatter = icu.SimpleDateFormat(field, locale)
            formatter.setTimeZone(icu.TimeZone.getGMT())
            for index, instant in enumerate(instants):
                form = formatter.format(instant)
                if form:
                    seen.setdefault(form.casefold(), (form, index, len(form) == 1))
    return tuple(sorted(seen.values(), key=lambda form: -len(form[0])))


def _match_period(text: str, cursor: int, period: str, *, exact: bool = False) -> int | None:
    """Match a day-period form at ``cursor``, case-insensitively unless ``exact``.

    A space inside the form (Spanish "a.\u202fm.") matches any space character, since
    CLDR's no-break spaces are typed as ordinary ones.
    """
    for offset, expected in enumerate(period):
        index = cursor + offset
        if index >= len(text):
            return None
        actual = text[index]
        if expected in _SPACES:
            if actual not in _SPACES:
                return None
        elif actual != expected if exact else actual.casefold() != expected.casefold():
            return None
    return cursor + len(period)


@cache
def _hour_unit_forms(locale: str) -> tuple[tuple[str, bool], ...]:
    """CLDR's short and narrow symbols for an hour, as ``(symbol, attached)``.

    ICU formats one ten-hour measure at each width ("10h", "10\u202fh", "10 Std.")
    and the symbol is what surrounds the number; ``attached`` is true where CLDR writes
    it against the digits. Longest first.
    """
    forms: dict[str, tuple[str, bool]] = {}
    for width in (icu.UMeasureFormatWidth.SHORT, icu.UMeasureFormatWidth.NARROW):
        rendered = icu.MeasureFormat(icu.Locale(locale), width).formatMeasures(
            [icu.Measure(icu.Formattable(10), icu.MeasureUnit.createHour())]
        )
        if not rendered.startswith("10"):
            continue
        rest = rendered[2:]
        symbol = rest.lstrip("".join(_SPACES))
        if symbol:
            # Attached if any width writes it attached (fr: "10 h" short, "10h" narrow).
            _known, attached = forms.get(symbol.casefold(), (symbol, False))
            forms[symbol.casefold()] = (symbol, attached or rest == symbol)
    return tuple(sorted(forms.values(), key=lambda form: -len(form[0])))


@cache
def _language_time_separators(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[str, ...]:
    """The hour-minute separators CLDR's short-time patterns use across ``language``.

    English locales write ":" and, in en_FI, en_DK and others, "." ("H.mm"), so an
    English text is read with either.
    """
    separators: dict[str, None] = {}
    for name in _language_locale_names(language, names):
        locale = icu.Locale(name)
        pattern = icu.DateFormat.createTimeInstance(icu.DateFormat.kShort, locale).toPattern()
        structure = FlexibleTimeDetector._time_structure(pattern)
        if structure is not None:
            separators.setdefault(structure[0], None)
    return tuple(separators)


@cache
def _language_zone_abbreviations(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[str, ...]:
    """Time-zone abbreviations ICU writes for the locales of ``language``, longest first.

    Each zone's short and short-generic display names, standard and daylight ("EST",
    "EDT", "ET", "UTC", "CET"). Keeping only all-capital letter runs of two to five is
    hand-rolled: it drops the offset forms ("GMT+1") and full names ICU returns when a
    locale has no abbreviation, which are not what a clock time is followed by.
    """
    styles = (icu.TimeZone.SHORT, icu.TimeZone.SHORT_GENERIC)
    forms: set[str] = set()
    locales = [icu.Locale(name) for name in _language_locale_names(language, names)]
    for zone_id in icu.TimeZone.createEnumeration():
        zone = icu.TimeZone.createTimeZone(zone_id)
        for locale in locales:
            for style in styles:
                for daylight in (False, True):
                    try:
                        form = zone.getDisplayName(daylight, style, locale)
                    except icu.ICUError:
                        continue
                    if 2 <= len(form) <= 5 and form.isalpha() and form.isupper():
                        forms.add(form)
    return tuple(sorted(forms, key=lambda form: (-len(form), form)))


@cache
def _iso_utc_designator() -> str:
    """What ICU's ISO 8601 zone pattern ``X`` writes for UTC: "Z"."""
    formatter = icu.SimpleDateFormat("X", icu.Locale("en_US"))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    return formatter.format(0.0)


@cache
def _language_zone_names(language: str, names: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """The long zone names ICU writes for the locales of ``language``, longest first.

    Each zone's long and long generic names, standard and daylight ("Eastern Standard
    Time", "Eastern Time"), and its generic location name, ICU's ``VVVV`` ("New York
    Time"). Offset forms ("GMT-05:00") are left out: they are not names.
    """
    forms: set[str] = set()
    locales = [icu.Locale(name) for name in _language_locale_names(language, names)]
    styles = (icu.TimeZone.LONG, icu.TimeZone.LONG_GENERIC)
    location = {
        name: icu.SimpleDateFormat("VVVV", icu.Locale(name))
        for name in _language_locale_names(language, names)
    }
    for zone_id in icu.TimeZone.createEnumeration():
        zone = icu.TimeZone.createTimeZone(zone_id)
        for icu_locale in locales:
            for style in styles:
                for daylight in (False, True):
                    try:
                        forms.add(zone.getDisplayName(daylight, style, icu_locale))
                    except icu.ICUError:
                        continue
        for formatter in location.values():
            formatter.setTimeZone(zone)
            forms.add(formatter.format(0.0))
    return tuple(
        sorted(
            (form for form in forms if " " in form and not any(c.isdigit() for c in form)),
            key=lambda form: (-len(form), form),
        )
    )


@cache
def _zone_forms_by_initial(
    language: str, names: tuple[str, ...] | None = None
) -> dict[str, tuple[tuple[str, bool], ...]]:
    """The zone names and abbreviations of ``language`` by first letter, longest first.

    Each is ``(form, is_name)``: a long name matches any space where it has one (see
    :func:`_match_period`), an abbreviation exactly.
    """
    forms: dict[str, list[tuple[str, bool]]] = {}
    for form in _language_zone_names(language, names):
        forms.setdefault(form[0], []).append((form, True))
    for form in _language_zone_abbreviations(language, names):
        forms.setdefault(form[0], []).append((form, False))
    return {initial: tuple(entries) for initial, entries in forms.items()}


def _zone_form_at(
    text: str, cursor: int, language: str, names: tuple[str, ...] | None = None
) -> str | None:
    """The zone name or abbreviation ICU writes for ``language`` at ``cursor``, if any.

    Long names first, as :func:`_language_zone_names` orders them, then abbreviations;
    the form must end its letter token ("ET", not "ETC").
    """
    if cursor >= len(text):
        return None
    for form, is_name in _zone_forms_by_initial(language, names).get(text[cursor], ()):
        if is_name:
            end = _match_period(text, cursor, form, exact=True)
        else:
            end = cursor + len(form) if text[cursor : cursor + len(form)] == form else None
        if end is not None and _ends_letter_token(text, end):
            return form
    return None


@cache
def _language_flexible_periods(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[str, frozenset[int]], ...]:
    """The flexible day periods ICU's ``B`` writes, each with the hours it covers.

    English: "in the morning" (6-11), "noon" (12), "in the afternoon" (12-17), "in the
    evening" (18-20), "at night" (21-5), "midnight" (0). Longest first.
    """
    hours: dict[str, set[int]] = {}
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale("en_US"))
    for name in _language_locale_names(language, names):
        for field in ("B", "BBBB", "BBBBB"):
            formatter = icu.SimpleDateFormat(field, icu.Locale(name))
            formatter.setTimeZone(icu.TimeZone.getGMT())
            for hour in range(24):
                for minute in (0, 30):
                    calendar.clear()
                    calendar.set(2026, 0, 3, hour, minute, 0)
                    form = formatter.format(calendar.getTime())
                    if form and any(character.isalpha() for character in form):
                        hours.setdefault(form, set()).add(hour)
    return tuple(
        (form, frozenset(covered))
        for form, covered in sorted(hours.items(), key=lambda item: -len(item[0]))
    )


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
    seconds are exactly two digits in 0-59. An hour with no minutes reads only with a
    day period after it ("5pm", "10 a.m."), where the locale writes the period after
    the time, and its value then carries ``H`` alone.

    The day-period forms are ICU's, at every width, for every CLDR locale of the same
    language (see :func:`_language_day_periods`), so en_US also reads en_CA's "a.m.".
    Likewise the hour-minute separator may be any the language's CLDR patterns use
    ("7.30pm"; see :func:`_language_time_separators`), and a time may be followed by a
    time-zone abbreviation ICU writes for the language ("10 PM ET", "18:00 UTC"; see
    :func:`_language_zone_abbreviations`), or by ICU's ISO 8601 "Z" written against it
    ("12:00:00Z"), captured as ``time-zone``. The capture's text is the zone as written;
    its value is the IANA ID of the zone ICU parses it as (see :func:`_zone_readings`):
    "Eastern Standard Time", "New York Time", "EST" and "ET" are all
    "America/New_York" in en_US, and "UTC", "GMT" and "Z" are "Etc/GMT". A name that
    names several zones in the locales of the language gives one reading per zone:
    "IST" is Europe/Dublin (en_IE) and Asia/Kolkata (en_IN).

    A time may end in the locale's hour symbol ("10:30h", "10:30 Std."), and the symbol
    CLDR writes attached may stand between hour and minutes ("10h30"); both forms come
    from :func:`_hour_unit_forms`. Composing a clock time with a unit symbol this way
    is hand-rolled, as CLDR has no pattern for it; the symbol is captured as
    ``hour-unit``.
    """

    group = "time"
    type = "time:flexible"

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        icu_locale = icu.Locale(locale)
        time_format = icu.DateFormat.createTimeInstance(icu.DateFormat.kShort, icu_locale)
        self.pattern = time_format.toPattern()
        structure = self._time_structure(self.pattern)
        self._inert = structure is None
        self._separator, self.hour12, self._period_side = structure or ("", False, None)
        self._period_prefix = self._period_side == "prefix"
        self._periods = _language_day_periods(icu_locale.getLanguage(), self.locales)
        self._flexible_periods = _language_flexible_periods(icu_locale.getLanguage(), self.locales)
        self._hour_units = _hour_unit_forms(locale)
        self._separators = tuple(
            dict.fromkeys(
                ((self._separator,) if self._separator else ())
                + _language_time_separators(icu_locale.getLanguage(), self.locales)
            )
        )
        self._language = icu_locale.getLanguage()

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
        spaced = cursor < len(text) and text[cursor] in _SPACES
        if spaced:
            cursor += 1
        for period, index, narrow in self._periods:
            # Hand-rolled, as CLDR says nothing about spacing: a one-letter narrow form
            # is read only attached to the time ("5p"), since a spaced "5 a" is far more
            # often the article than the morning.
            if narrow and spaced:
                continue
            # A narrow form matches only in the case CLDR writes it ("5p", not "5A"
            # amperes or "Form 1A"); longer forms match in any case.
            end = _match_period(text, cursor, period, exact=narrow)
            if end is not None:
                return end, text[marker_start:end], index
        return None

    def _flexible_period(self, text: str, cursor: int, raw_hour: int):
        """A flexible day period after one space, with the 24-hour hour it makes.

        "2 in the afternoon" is 14:00: of 2 and 14, the hour the period covers.
        """
        if not (1 <= raw_hour <= 12 and cursor < len(text) and text[cursor] in _SPACES):
            return None
        for form, covered in self._flexible_periods:
            # As for "a"/"p", a one-letter narrow form is not read after a space ("12 n"),
            # a hand-rolled rule.
            if len(form) == 1:
                continue
            end = _match_period(text, cursor + 1, form)
            if end is None or (end < len(text) and text[end].isalnum()):
                continue
            candidates = [h for h in (raw_hour % 12, raw_hour % 12 + 12) if h in covered]
            if candidates:
                return end, text[cursor:end], candidates[0]
        return None

    def _period_precedes(self, text: str, start: int) -> bool:
        """Whether a day-period marker (with an optional space) ends just before ``start``."""
        cursor = start
        if cursor > 0 and text[cursor - 1] in _SPACES:
            cursor -= 1
        for period, _index, _narrow in self._periods:
            if cursor - len(period) >= 0:
                if text[cursor - len(period) : cursor].casefold() == period.casefold():
                    return True
        return False

    def _match(
        self, text: str, start: int, read_units: bool = False
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

        separator = next((sep for sep in self._separators if text.startswith(sep, cursor)), "")
        if not separator:
            separator = next(
                (
                    symbol
                    for symbol, attached in self._hour_units
                    if attached
                    and text[cursor : cursor + len(symbol)].casefold() == symbol.casefold()
                    and self._field(text, cursor + len(symbol), 2) is not None
                ),
                "",
            )
            if not separator:
                return self._hour_with_period(
                    text, hour_start, hour_width, raw_hour, captures, read_units
                )
            captures.append(
                Capture(
                    "hour-unit",
                    cursor,
                    cursor + len(separator),
                    text[cursor : cursor + len(separator)],
                )
            )
        minute = self._field(text, cursor + len(separator), 2)
        if minute is None or not 0 <= minute[1] <= 59:
            return None
        minute_end, minute_value = minute

        second_value: int | None = None
        second_end = minute_end
        clock = separator in self._separators
        if clock and text.startswith(separator, minute_end):
            second = self._field(text, minute_end + len(separator), 2)
            if second is not None and 0 <= second[1] <= 59:
                second_end, second_value = second
            elif self._digit_run(text, minute_end + len(separator))[0] > (
                minute_end + len(separator)
            ):
                return None

        cursor = second_end
        if not self._period_prefix:
            # A 24-hour locale's language still writes a day period after the time
            # (en_GB "5:30 p.m."), so every locale that does not put it first reads one.
            if 1 <= raw_hour <= 12:
                found = self._day_period(text, cursor)
                if found is not None:
                    marker_end, marker_text, period_index = found
                    captures.append(
                        Capture("day-period", cursor, marker_end, marker_text, None, "symbol")
                    )
                    cursor = marker_end
                else:
                    flexible = self._flexible_period(text, cursor, raw_hour)
                    if flexible is not None:
                        marker_end, marker_text, flexible_hour = flexible
                        captures.append(
                            Capture("day-period", cursor, marker_end, marker_text, None, "flexible")
                        )
                        cursor = marker_end
                        raw_hour = flexible_hour
                        period_index = -1
            elif self._day_period(text, cursor) is not None:
                return None

        if read_units and period_index is None and clock:
            unit = self._hour_unit(text, cursor)
            if unit is not None:
                captures.append(unit)
                cursor = unit.end
        if read_units:
            zone = self._time_zone(text, cursor)
            if zone is not None:
                captures.append(zone)
                cursor = zone.end

        next_separator = separator if clock else self._separator
        continuation = cursor + len(next_separator)
        if text.startswith(next_separator, cursor) and self._digit_run(text, continuation)[0] > (
            continuation
        ):
            return None

        if period_index is None or period_index == -1:
            # -1: a flexible day period already gave the 24-hour hour.
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

    def _hour_unit(self, text: str, cursor: int) -> Capture | None:
        """The locale's hour symbol after a time, attached or after one space."""
        begin = cursor
        if cursor < len(text) and text[cursor] in _SPACES:
            cursor += 1
        for symbol, _attached in self._hour_units:
            end = cursor + len(symbol)
            if text[cursor:end].casefold() == symbol.casefold() and _ends_letter_token(text, end):
                return Capture("hour-unit", begin, end, text[begin:end])
        return None

    def _time_zone(self, text: str, cursor: int) -> Capture | None:
        """A time-zone abbreviation after a time, after one space ("10 PM ET").

        Or ICU's ISO 8601 zero-offset designator written against the time, as its ``X``
        pattern writes UTC ("12:00:00Z"; see :func:`_iso_utc_designator`).
        """
        designator = _iso_utc_designator()
        end = cursor + len(designator)
        if text[cursor:end] == designator and _ends_letter_token(text, end):
            return Capture("time-zone", cursor, end, designator, self._zone_ids(designator))
        if not (cursor < len(text) and text[cursor] in _SPACES):
            return None
        begin, cursor = cursor, cursor + 1
        form = _zone_form_at(text, cursor, self._language, self.locales)
        if form is None:
            return None
        end = cursor + len(form)
        return Capture("time-zone", begin, end, text[begin:end], self._zone_ids(form))

    def _zone_ids(self, form: str, days: tuple[int, ...] | None = None) -> tuple[str, ...]:
        """The IANA IDs of the zones a zone form names (see :func:`_zone_readings`).

        On ``days``, by default a bare time's (see :func:`_reading_days`). The capture
        holds them all until :meth:`detect` gives each its own reading.
        """
        readings = _zone_readings(form, self.locale, self.locales, days)
        return tuple(zone_id for zone_id, _ in readings)

    def on_date(self, text: str, time: ValueDetection, fields) -> list[ValueDetection]:
        """``time``'s readings once it is known to fall on the date ``fields`` give.

        A zone is read as ICU writes it that day: "10:00 PM IST" is Irish summer time on
        July 5 but not on January 5. ``fields`` are a date's ``(letter, value)`` pairs.
        """
        zone = next((c for c in time["captures"] if c.name == "time-zone"), None)
        if zone is None:
            return [time]
        written = zone.text[1:] if zone.text[:1] in _SPACES else zone.text
        form = _zone_form_at(text, zone.end - len(written), self._language, self.locales)
        days = _reading_days(dict(fields))
        zone_ids = self._zone_ids(form or written, days)
        dated = replace(zone, value=zone_ids)
        return self._one_reading_per_zone(
            ValueDetection(
                **{
                    **time,
                    "captures": tuple(
                        dated if capture is zone else capture for capture in time["captures"]
                    ),
                }
            )
        )[: len(zone_ids)]

    @staticmethod
    def _one_reading_per_zone(detection: ValueDetection) -> list[ValueDetection]:
        """``detection`` once per zone its zone capture names, in the capture's order."""
        zone = next((c for c in detection["captures"] if c.name == "time-zone"), None)
        if zone is None:
            return [detection]
        return [
            ValueDetection(
                **{
                    **detection,
                    "captures": tuple(
                        replace(capture, value=zone_id) if capture is zone else capture
                        for capture in detection["captures"]
                    ),
                }
            )
            for zone_id in zone.value or (None,)
        ]

    def _hour_with_period(
        self,
        text: str,
        hour_start: int,
        hour_width: int,
        raw_hour: int,
        captures: list[Capture],
        read_units: bool = False,
    ) -> tuple[int, tuple[Capture, ...], DateTimeValue] | None:
        """An hour with no minutes, read only with a day period after it ("5pm")."""
        if self._period_prefix or captures or not 1 <= raw_hour <= 12:
            return None
        cursor = hour_start + hour_width
        found = self._day_period(text, cursor)
        if found is None:
            flexible = self._flexible_period(text, cursor, raw_hour)
            if flexible is None:
                return None
            marker_end, marker_text, hour24 = flexible
            ordered = [
                Capture("H", hour_start, cursor, text[hour_start:cursor], raw_hour, "numeric"),
                Capture("day-period", cursor, marker_end, marker_text, None, "flexible"),
            ]
            return marker_end, tuple(ordered), DateTimeValue((("H", hour24),), "gregorian")
        marker_end, marker_text, period_index = found
        hour24 = (0 if raw_hour == 12 else raw_hour) + (12 if period_index == 1 else 0)
        ordered = [
            Capture("H", hour_start, cursor, text[hour_start:cursor], raw_hour, "numeric"),
            Capture("day-period", cursor, marker_end, marker_text, None, "symbol"),
        ]
        end = marker_end
        zone = self._time_zone(text, end) if read_units else None
        if zone is not None:
            ordered.append(zone)
            end = zone.end
        return end, tuple(ordered), DateTimeValue((("H", hour24),), "gregorian")

    def detect(self, text: str) -> list[ValueDetection]:
        """Return flexible clock times in source order.

        A time followed by an hour symbol or a time-zone abbreviation is read both with and
        without it ("10:30" and "10:30 hr"; "10 PM" and "10 PM ET"), so neither span
        replaces the other. A zone name that names several zones is read once per zone
        ("10 PM IST": Europe/Dublin and Asia/Kolkata), the locale's own zone first.
        """
        if self._inert:
            return []
        # Whether to read a trailing unit is an argument of each pass, not detector state,
        # so one detector can serve concurrent or nested calls.
        plain = _detect_flexible(text, self.locale, self.type, self._spec, self._match)

        def match_with_units(source: str, start: int):
            return self._match(source, start, read_units=True)

        with_units = [
            reading
            for detection in _detect_flexible(
                text, self.locale, self.type, self._spec, match_with_units
            )
            for reading in self._one_reading_per_zone(detection)
        ]
        spans = {(d["start"], d["end"]) for d in plain}
        merged = plain + [d for d in with_units if (d["start"], d["end"]) not in spans]
        return sorted(merged, key=lambda d: (d["start"], d["end"]))


# ICU's hour-field letters and the clock hours each writes (UTS #35, the date field
# symbol table): h 1-12, H 0-23, K 0-11, k 1-24. The ranges are the standard's, which
# PyICU exposes no accessor for, so they are listed here.
_HOUR_CYCLE_RANGES = {"h": (1, 12), "H": (0, 23), "K": (0, 11), "k": (1, 24)}


def _hour_cycle_letter(pattern: str) -> str | None:
    """The first unquoted hour-field letter of a date pattern, or ``None``."""
    quoted = False
    for character in pattern:
        if character == "'":
            quoted = not quoted
        elif not quoted and character in _HOUR_CYCLE_RANGES:
            return character
    return None


class FlexibleBareHourDetector:
    """Recognize a lone number as a clock hour ("at 3"), which the time reader refuses.

    :class:`FlexibleTimeDetector` reads an hour without minutes only with a day period
    after it ("3pm"), never a number alone. This reader deposits the lone number as an
    hour of the locale's own hour cycle: the hour field of ICU's best pattern for the
    ``j`` skeleton (the locale's preferred cycle; en_US "h a", en_GB "HH") says which
    field and so which range. The type is ``time:bare-hour`` and the value
    ``DateTimeValue(((letter, hour),), "gregorian")`` with that field's letter: ``("h",
    3)`` in a 12-hour locale, where the number does not say morning or afternoon, and
    ``("H", 15)`` in a 24-hour one. Only an hour the field can write is read (1-12 for
    ``h``, 0-23 for ``H``), in one or two of the locale's digits.

    The number must stand alone, a hand-rolled rule because CLDR has no pattern for a
    number in running text: before it, the start of the text, a space, or opening
    punctuation ("at 3", "(3)"); after it, the end, a space, or closing punctuation not
    followed by a letter or digit ("at 3.", "at 3, then"). So a decimal ("3.5"), a
    ratio or time ("3:30", "3/4"), a range ("3-4"), a percentage ("3%"; the locale's
    percent and per-mille signs), a signed number ("-3"; its minus and plus signs), and
    a number in a word ("3D") are not read. A number inside one of the time reader's
    readings ("3 pm", "3 in the afternoon") is left to it, and one inside a text or
    numeric date's reading ("May 5, 2020", "Jan 3", "5 March 2024") to the date, so this
    reader deposits only the numbers those readers leave.
    """

    group = "time"
    type = "time:bare-hour"

    _OPENING = frozenset(
        {icu.UCharCategory.START_PUNCTUATION, icu.UCharCategory.INITIAL_PUNCTUATION}
    )
    _CLOSING = frozenset(
        {
            icu.UCharCategory.END_PUNCTUATION,
            icu.UCharCategory.FINAL_PUNCTUATION,
            icu.UCharCategory.OTHER_PUNCTUATION,
        }
    )

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        icu_locale = icu.Locale(locale)
        generator = icu.DateTimePatternGenerator.createInstance(icu_locale)
        self.pattern = generator.getBestPattern("j")
        self.letter = _hour_cycle_letter(self.pattern)
        self._range = _HOUR_CYCLE_RANGES.get(self.letter or "", (1, 0))
        self._digits = _locale_digit_map(icu_locale)
        symbols = icu.DecimalFormatSymbols(icu_locale)
        symbol = icu.DecimalFormatSymbols
        self._signs = frozenset(
            symbols.getSymbol(kind)
            for kind in (
                symbol.kMinusSignSymbol,
                symbol.kPlusSignSymbol,
                symbol.kPercentSymbol,
                symbol.kPerMillSymbol,
            )
        )
        self._time = FlexibleTimeDetector(locale, locales=locales)
        self._text_dates = FlexibleTextDateDetector(locale, locales=locales)
        self._numeric_dates = FlexibleDateDetector(locale, locales=locales)
        self._spec = DateFormatSpec(locale, "j", self.pattern, "gregorian")

    def _opens(self, character: str) -> bool:
        return character.isspace() or (
            character not in self._signs and icu.Char.charType(character) in self._OPENING
        )

    def _closes(self, text: str, end: int) -> bool:
        character = text[end]
        if character.isspace():
            return True
        if character in self._signs or icu.Char.charType(character) not in self._CLOSING:
            return False
        after = text[end + 1 : end + 2]
        return not after or not (_is_word_character(after) or after in self._digits)

    def _match(self, text: str, start: int):
        if self.letter is None or text[start] not in self._digits:
            return None
        if start > 0 and not self._opens(text[start - 1]):
            return None
        end = start
        hour = 0
        while end < len(text) and text[end] in self._digits:
            hour = hour * 10 + self._digits[text[end]]
            end += 1
        low, high = self._range
        if end - start > 2 or not low <= hour <= high:
            return None
        if end < len(text) and not self._closes(text, end):
            return None
        capture = Capture(self.letter, start, end, text[start:end], hour, "numeric")
        return end, (capture,), DateTimeValue(((self.letter, hour),), "gregorian")

    def detect(self, text: str) -> list[ValueDetection]:
        """Return lone clock hours in source order, outside the time and date readings."""
        found = _detect_flexible(text, self.locale, self.type, self._spec, self._match)
        if not found:
            return []
        taken = [
            *self._time.detect(text),
            *self._text_dates.detect(text),
            *self._numeric_dates.detect(text),
        ]
        return [
            hour
            for hour in found
            if not any(
                other["start"] < hour["end"] and hour["start"] < other["end"] for other in taken
            )
        ]


@cache
def _language_datetime_glue(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[tuple[bool, str, str], ...]:
    """How CLDR joins a date and a time in the locales of ``language``.

    Each is ``(date_first, literal, pattern)`` from the ``{1}``/``{0}`` date-time
    pattern ICU gives each style: English ``"{1}, {0}"`` and ``"{1} 'at' {0}"``, so
    ``(True, ", ", "{1}, {0}")`` and ``(True, " at ", "{1} 'at' {0}")``. Longest first.
    """
    glue: dict[tuple[bool, str], str] = {}
    styles = (
        icu.DateFormat.kFull,
        icu.DateFormat.kLong,
        icu.DateFormat.kMedium,
        icu.DateFormat.kShort,
    )
    for name in _language_locale_names(language, names):
        generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(name))
        for style in styles:
            try:
                pattern = generator.getDateTimeFormat(style)
            except (icu.ICUError, TypeError):
                pattern = generator.getDateTimeFormat()
            date_at, time_at = pattern.find("{1}"), pattern.find("{0}")
            if date_at < 0 or time_at < 0:
                continue
            first, second = sorted((date_at, time_at))
            literal = pattern[first + 3 : second].replace("'", "")
            if literal.strip() or literal:
                glue.setdefault((date_at < time_at, literal), pattern)
    return tuple(
        (date_first, literal, pattern)
        for (date_first, literal), pattern in sorted(
            glue.items(), key=lambda item: -len(item[0][1])
        )
    )


@cache
def _language_weekday_time_glue(
    language: str, names: tuple[str, ...] | None = None
) -> tuple[str, ...]:
    """What CLDR writes between a weekday and a time, in the locales of ``language``.

    From the best patterns of the weekday-and-time skeletons ("Ehm" is "EEE h:mm a" in
    English, so " "): the literal after the weekday field and before the hour.
    """
    glue: dict[str, None] = {}
    skeletons = ("Eh", "Ehm", "Ehms", "EHm", "EHms", "EBh", "EBhm", "EEEEhm", "EEEEHm")
    for name in _language_locale_names(language, names):
        generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(name))
        for skeleton in skeletons:
            pattern = generator.getBestPattern(skeleton)
            weekday_end = pattern.rfind("E") + 1
            hours = [pattern.find(letter, weekday_end) for letter in "hHkK"]
            hours = [index for index in hours if index >= 0]
            if not weekday_end or not hours or pattern.find("E") < 0:
                continue
            literal = pattern[weekday_end : min(hours)].replace("'", "")
            if literal:
                glue.setdefault(literal)
    return tuple(sorted(glue, key=len, reverse=True))


class FlexibleDateTimeDetector:
    """Recognize a date and a time joined as CLDR's date-time patterns join them.

    CLDR joins a date and a time with a pattern per style ("{1}, {0}", "{1} 'at' {0}"
    in English; see :func:`_language_datetime_glue`), which this reader inverts over
    the readings of :class:`FlexibleTextDateDetector`, :class:`FlexibleDateDetector`,
    and :class:`FlexibleTimeDetector`: "Mar 5, 2024, 2:07 PM", "July 4, 1999 at 12:05:00
    AM EDT", "3/5/24, 14:07". A space in the glue matches any space. The value holds the
    date's fields and then the time's; the spec's pattern is the glue with the date's
    pattern for ``{1}`` and the time's for ``{0}``.

    A weekday alone before a time reads too, as CLDR's weekday-and-time patterns write it
    ("Tue 2:07 PM", "Thu 10 at night"; see :func:`_language_weekday_time_glue`), with
    the weekday's names those of :class:`FlexibleTextDateDetector`; its value is
    ``("E", weekday)`` (ICU's number, Sunday 1) and then the time's fields.
    """

    group = "date"
    type = "date:datetime-flexible"

    def __init__(self, locale: str, *, locales: Iterable[str] | None = None) -> None:
        self.locale = locale
        self.locales = _locale_selection(locale, locales)
        self._dates = (
            FlexibleTextDateDetector(locale, locales=locales),
            FlexibleDateDetector(locale, locales=locales),
        )
        self._time = FlexibleTimeDetector(locale, locales=locales)
        self._glue = _language_datetime_glue(icu.Locale(locale).getLanguage(), self.locales)
        self._weekday_glue = _language_weekday_time_glue(
            icu.Locale(locale).getLanguage(), self.locales
        )

    @staticmethod
    def _glue_matches(between: str, literal: str) -> bool:
        if len(between) != len(literal):
            return False
        return all(
            (written in _SPACES and expected in _SPACES) or written == expected
            for written, expected in zip(between, literal, strict=True)
        )

    def detect(self, text: str) -> list[ValueDetection]:
        """Return each date and time CLDR's glue joins, in source order."""
        dates = [d for detector in self._dates for d in detector.detect(text)]
        times = self._time.detect(text)
        found: dict[tuple[int, int, object], ValueDetection] = {}
        # A time's zones are read again on the date it is joined to, since the time
        # reader's are a bare time's: one reading of each span stands for its zones.
        by_span: dict[tuple, ValueDetection] = {}
        for time in times:
            by_span.setdefault((time["start"], time["end"], time["value"]), time)
        spans = list(by_span.values())
        for date in dates:
            for span in spans:
                for date_first, literal, pattern in self._glue:
                    first, second = (date, span) if date_first else (span, date)
                    if not self._glue_matches(text[first["end"] : second["start"]], literal):
                        continue
                    for time in self._time.on_date(text, span, date["value"].fields):
                        first, second = (date, time) if date_first else (time, date)
                        self._compose(text, date, time, first, second, pattern, found)
        for time in times:
            found.update(
                (key, detection) for key, detection in self._weekday_times(text, time).items()
            )
        return sorted(found.values(), key=lambda item: (item["start"], item["end"]))

    def _compose(self, text, date, time, first, second, pattern, found) -> None:
        """Deposit ``date`` and ``time`` joined by CLDR's ``pattern`` into ``found``."""
        fields = date["value"].fields + time["value"].fields
        value = DateTimeValue(fields, date["value"].calendar)
        glue = Capture(
            "datetime-glue",
            first["end"],
            second["start"],
            text[first["end"] : second["start"]],
            None,
            "symbol",
        )
        captures = tuple(
            sorted(
                (*first["captures"], glue, *second["captures"]),
                key=lambda capture: (capture.start, capture.end),
            )
        )
        date_pattern = getattr(date["spec"], "pattern", "")
        time_pattern = getattr(time["spec"], "pattern", "")
        spec = DateFormatSpec(
            self.locale,
            "datetime",
            pattern.replace("{1}", date_pattern).replace("{0}", time_pattern),
            date["value"].calendar,
        )
        # A time read in two zones gives two readings.
        key = (first["start"], second["end"], value, _zone_key(time["captures"]))
        found.setdefault(
            key,
            ValueDetection(
                text=text[first["start"] : second["end"]],
                start=first["start"],
                end=second["end"],
                type=self.type,
                value=value,
                captures=captures,
                spec=spec,
            ),
        )

    def _weekday_times(self, text: str, time: ValueDetection) -> dict:
        """A weekday and CLDR's glue right before ``time`` ("Tue 2:07 PM")."""
        found = {}
        names = self._dates[0]
        for literal in self._weekday_glue:
            glue_start = time["start"] - len(literal)
            if glue_start <= 0 or not self._glue_matches(text[glue_start : time["start"]], literal):
                continue
            for surface, weekday, form in names._weekdays:
                for written in (surface, surface + "."):
                    start = glue_start - len(written)
                    if start < 0 or text[start:glue_start].casefold() != written.casefold():
                        continue
                    if written.endswith(".") and written.casefold() not in names._dotted_weekdays:
                        continue
                    if start > 0 and _is_word_character(text[start - 1]):
                        continue
                    value = DateTimeValue((("E", weekday), *time["value"].fields), "gregorian")
                    captures = (
                        Capture(
                            "weekday", start, glue_start, text[start:glue_start], weekday, form
                        ),
                        Capture(
                            "datetime-glue", glue_start, time["start"], literal, None, "symbol"
                        ),
                        *time["captures"],
                    )
                    time_pattern = getattr(time["spec"], "pattern", "")
                    spec = DateFormatSpec(
                        self.locale, "weekday-time", f"EEE{literal}{time_pattern}", "gregorian"
                    )
                    found.setdefault(
                        (start, time["end"], value, _zone_key(time["captures"])),
                        ValueDetection(
                            text=text[start : time["end"]],
                            start=start,
                            end=time["end"],
                            type=self.type,
                            value=value,
                            captures=captures,
                            spec=spec,
                        ),
                    )
        return found


class FlexibleFractionDetector:
    """Recognize signed ``N/D`` fractions and NFKC-decomposable vulgar fractions.

    The ``fraction:flexible`` type marks recall candidates. Locale digits are reflective;
    the fraction slash is the mathematical solidus (``/`` or U+2044), not locale data.
    A fraction made plural ("3/4s") spans its suffix, with ``suffix`` (and
    ``apostrophe``) captures, as :class:`PluralNumeralDetector` reads a numeral.
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
        end = denominator_end
        plural = _plural_suffix(text, end, self.locale)
        if plural is not None:
            end, suffix_captures = plural
            captures.extend(suffix_captures)
        return end, tuple(captures), NumberValue(decimal=decimal, currency=None)

    def detect(self, text: str) -> list[ValueDetection]:
        """Return greedy, non-overlapping flexible fractions in source order."""
        return _detect_flexible(text, self.locale, self.type, self._spec, self._match)


@cache
def _foreign_ordinal_suffixes(locale: str) -> frozenset[str]:
    """Ordinal suffixes ICU writes in other locales that ``locale`` can read unambiguously.

    Every locale's RBNF digit-ordinal rule sets are rendered for small values, and a
    suffix is kept when it holds a letter and none of its letters is in ``locale``'s
    CLDR exemplar letters (standard or auxiliary): Italian and Portuguese "º" and "ª",
    Spanish ".º", but not French "e" or Catalan "a", which an English text writes as
    letters of its own. A suffix of punctuation alone (German "1.") is not kept, nor one
    holding a space.

    Hand-rolled choices, since CLDR does not enumerate the suffixes directly: only the
    ``%digits-ordinal`` rule sets are read (the others spell the number out), and the
    values 1, 2, 3, 4, 11 and 21 are rendered, which reach every ordinal plural category
    CLDR's rules distinguish for these rule sets (one, two, few, other, and the teens and
    twenties exceptions).
    """
    data = icu.LocaleData(locale)
    own = [
        data.getExemplarSet(0, kind)
        for kind in (
            icu.ULocaleDataExemplarSetType.ES_STANDARD,
            icu.ULocaleDataExemplarSetType.ES_AUXILIARY,
        )
    ]
    suffixes: set[str] = set()
    languages = {icu.Locale(name).getLanguage() for name in icu.Locale.getAvailableLocales()}
    for language in sorted(languages):
        try:
            rbnf = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, icu.Locale(language))
        except icu.ICUError:
            continue
        for index in range(rbnf.getNumberOfRuleSetNames()):
            name = rbnf.getRuleSetName(index)
            if "digits" not in name or name.startswith("%%"):
                continue
            for value in (1, 2, 3, 4, 11, 21):
                rendered = rbnf.format(value, name)
                digits = [i for i, character in enumerate(rendered) if character.isdigit()]
                if not digits or digits[0] != 0:
                    continue
                suffix = rendered[digits[-1] + 1 :]
                letters = [character for character in suffix if icu.Char.isalpha(character)]
                if any(character in _SPACES or character.isspace() for character in suffix):
                    continue
                if letters and not any(
                    exemplars.contains(letter.lower()) for letter in letters for exemplars in own
                ):
                    suffixes.add(suffix)
    return frozenset(suffixes)


@cache
def _punctuation_ordinal_markers() -> frozenset[str]:
    """Ordinal markers made only of punctuation that ICU writes in some locale.

    German, Danish, and others write an ordinal as a number and a period ("1."), which
    their RBNF digit-ordinal rule sets render; a Roman numeral written that way ("V.",
    "Heinrich V.") is read as an ordinal through these markers.
    """
    markers: set[str] = set()
    languages = {icu.Locale(name).getLanguage() for name in icu.Locale.getAvailableLocales()}
    for language in sorted(languages):
        try:
            rbnf = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, icu.Locale(language))
        except icu.ICUError:
            continue
        for index in range(rbnf.getNumberOfRuleSetNames()):
            name = rbnf.getRuleSetName(index)
            if "digits" not in name or name.startswith("%%"):
                continue
            rendered = rbnf.format(1, name)
            if rendered[:1].isdigit():
                suffix = rendered.lstrip("0123456789")
                if suffix and not any(
                    character.isalnum() or character.isspace() for character in suffix
                ):
                    markers.add(suffix)
    return frozenset(markers)


class FlexibleOrdinalDetector:
    """Recognize ordinal numerals (``1st``, ``第21``) using reflective CLDR affixes.

    The ``ordinal:flexible`` type marks recall candidates. Ordinal affixes are obtained
    reflectively by *forward* formatting: a candidate integer is rendered with every
    public ``icu.RuleBasedNumberFormat`` ``ORDINAL`` rule set, and the prefix and suffix
    are the non-digit parts around each rendering. No affix is hard-coded, and no fragile
    ordinal *parse* is attempted. A surface is accepted only when its affixes match a pair
    ICU generates for the parsed value, so ``21th`` is rejected while ``21st`` is not.

    A grouped integer ("1,000th") is accepted when ICU renders the same surface for its
    value. An ordinal suffix ICU writes in another locale is also read when it cannot be
    mistaken for this locale's letters ("1º" in English text; see
    :func:`_foreign_ordinal_suffixes`).

    An uppercase Roman numeral is read as an ordinal when it carries this locale's own
    ordinal suffix for its value ("Ist", "IInd", "XIVth") or a punctuation-only ordinal
    marker ICU writes in some locale ("V.", "X."; see
    :func:`_punctuation_ordinal_markers`). The integer capture's form is ``roman``.

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
        self._roman = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.NUMBERING_SYSTEM, icu_locale)
        self._roman_rule_set = next(
            (
                name
                for index in range(self._roman.getNumberOfRuleSetNames())
                if "roman-upper" in (name := self._roman.getRuleSetName(index))
            ),
            None,
        )
        self._roman_letters = frozenset(
            character
            for value in (1, 5, 10, 50, 100, 500, 1000)
            for character in (
                self._roman.format(value, self._roman_rule_set) if self._roman_rule_set else ""
            )
        )
        self._digits = _locale_digit_map(icu_locale)
        self._grouping = icu.DecimalFormatSymbols(icu_locale).getSymbol(
            icu.DecimalFormatSymbols.kGroupingSeparatorSymbol
        )
        self._foreign_suffixes = tuple(
            sorted(_foreign_ordinal_suffixes(locale), key=len, reverse=True)
        )
        # The longest prefix ICU writes before an ordinal's digits ("第" in Chinese), over
        # a sample reaching every ordinal plural category and the first grouped values;
        # the digit search from a start never looks further than this.
        self._max_prefix = max(
            (
                len(prefix)
                for value in (*range(1, 121), 1000, 1001, 10000, 100000)
                for prefix, _suffix in self._affixes(value)
            ),
            default=0,
        )
        self._spec = NumberFormatSpec(locale, "decimal")

    def _digit_run(self, text: str, start: int) -> tuple[int, int]:
        cursor = start
        value = 0
        while cursor < len(text) and text[cursor] in self._digits:
            value = value * 10 + self._digits[text[cursor]]
            cursor += 1
        return cursor, value

    def _grouped_run(self, text: str, start: int) -> tuple[int, int]:
        """A digit run that may hold the locale's grouping separator between digits."""
        cursor = start
        value = 0
        while cursor < len(text):
            if text[cursor] in self._digits:
                value = value * 10 + self._digits[text[cursor]]
                cursor += 1
                continue
            after = cursor + len(self._grouping)
            if (
                self._grouping
                and cursor > start
                and text.startswith(self._grouping, cursor)
                and after < len(text)
                and text[after] in self._digits
            ):
                cursor = after
                continue
            break
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
        # An ordinal's digits start within its longest prefix of ``start``; scanning further
        # made every start walk the rest of the text (quadratic in its length).
        for digit_start in range(start, min(len(text), start + self._max_prefix + 1)):
            if text[digit_start] not in self._digits:
                continue
            if digit_start > 0 and text[digit_start - 1] in self._digits:
                continue
            digit_end, value = self._digit_run(text, digit_start)
            grouped_end, grouped_value = self._grouped_run(text, digit_start)
            if grouped_end > digit_end and digit_start == start:
                found = self._grouped(text, start, grouped_end, grouped_value)
                if found is not None:
                    return found
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
            if matched is None and digit_start == start:
                foreign = self._foreign(text, start, digit_end, value)
                if foreign is not None:
                    return foreign
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

    def _captures(
        self, text: str, start: int, digit_start: int, digit_end: int, end: int, value: int
    ) -> tuple[Capture, ...]:
        captures = []
        if digit_start > start:
            captures.append(
                Capture(
                    "ordinal-affix", start, digit_start, text[start:digit_start], None, "symbol"
                )
            )
        captures.append(
            Capture(
                "integer",
                digit_start,
                digit_end,
                text[digit_start:digit_end],
                str(value),
                "numeric",
            )
        )
        if end > digit_end:
            captures.append(
                Capture("ordinal-affix", digit_end, end, text[digit_end:end], None, "symbol")
            )
        return tuple(captures)

    def _foreign(
        self, text: str, start: int, digit_end: int, value: int
    ) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        """Another locale's ordinal suffix, tried after this locale's own affixes."""
        for suffix in self._foreign_suffixes:
            end = digit_end + len(suffix)
            if text[digit_end:end].casefold() == suffix.casefold() and _ends_letter_token(
                text, end
            ):
                captures = self._captures(text, start, start, digit_end, end, value)
                return end, captures, NumberValue(str(value), None)
        return None

    def _grouped(
        self, text: str, start: int, grouped_end: int, value: int
    ) -> tuple[int, tuple[Capture, ...], NumberValue] | None:
        """A grouped ordinal, accepted only when ICU renders exactly this surface."""
        if value < 1 or value > _MAX_RBNF_ORDINAL_VALUE:
            return None
        for name in self._rule_set_names or (None,):
            try:
                rendered = self._rbnf.format(value, name) if name else self._rbnf.format(value)
            except (icu.ICUError, SystemError):
                return None
            end = start + len(rendered)
            if end > grouped_end and text[start:end].casefold() == rendered.casefold():
                captures = self._captures(text, start, start, grouped_end, end, value)
                return end, captures, NumberValue(str(value), None)
        return None

    def _match_roman(self, text: str, start: int):
        """A Roman numeral with an ordinal suffix or marker ("XIVth", "V.")."""
        if self._roman_rule_set is None or (start > 0 and _is_word_character(text[start - 1])):
            return None
        cursor = start
        while cursor < len(text) and text[cursor] in self._roman_letters:
            cursor += 1
        if cursor == start:
            return None
        surface = text[start:cursor]
        position = icu.ParsePosition(0)
        parsed = self._roman.parse(surface, position)
        if parsed is None or position.getIndex() != len(surface):
            return None
        value = parsed.getInt64()
        if value < 1 or self._roman.format(value, self._roman_rule_set) != surface:
            return None
        suffixes = [suffix for prefix, suffix in self._affixes(value) if not prefix and suffix]
        suffixes += sorted(_punctuation_ordinal_markers())
        for suffix in sorted(set(suffixes), key=len, reverse=True):
            end = cursor + len(suffix)
            if text[cursor:end].casefold() != suffix.casefold():
                continue
            if end < len(text) and _is_word_character(text[end]):
                continue
            captures = (
                Capture("integer", start, cursor, surface, str(value), "roman"),
                Capture("ordinal-affix", cursor, end, text[cursor:end], None, "symbol"),
            )
            return end, captures, NumberValue(str(value), None)
        return None

    def detect(self, text: str) -> list[ValueDetection]:
        """Return flexible ordinals in source order: digit ordinals, then Roman ones."""
        digits = _detect_flexible(text, self.locale, self.type, self._spec, self._match)
        romans = _detect_flexible(text, self.locale, self.type, self._spec, self._match_roman)
        return sorted((*digits, *romans), key=lambda item: (item["start"], item["end"]))


def _detect_flexible_alternatives(
    text: str,
    locale: str,
    type_label: str,
    match: Callable[[str, int], list[_FlexibleMatch]],
) -> list[ValueDetection]:
    """Like :func:`_detect_flexible`, but keep every distinct reading at a start.

    One pass over the text, however many alternative matchers ``match`` compiles; the
    scan resumes after the longest reading at a start.
    """
    starts = sorted({span["start"] for span in break_grapheme_spans(text, locale)})
    interior = _word_interior_offsets(text, locale)
    detections: list[ValueDetection] = []
    cursor = 0
    for start in starts:
        if start < cursor or start in interior:
            continue
        ends: set[int] = set()
        kept: set[tuple[int, object, tuple[object, ...]]] = set()
        for result in match(text, start):
            # Readings of one value in different zones stay distinct.
            key = (result.end, result.value, _zone_key(result.captures))
            if result.end in interior or key in kept:
                continue
            kept.add(key)
            ends.add(result.end)
            detections.append(
                ValueDetection(
                    text=text[start : result.end],
                    start=start,
                    end=result.end,
                    type=type_label,
                    value=result.value,
                    captures=result.captures,
                    spec=result.spec,
                )
            )
        if ends:
            cursor = max(ends)
    return detections


def _detect_flexible(
    text: str,
    locale: str,
    type_label: str,
    spec: object | None,
    match: Callable[[str, int], tuple[int, tuple[Capture, ...], object] | _FlexibleMatch | None],
) -> list[ValueDetection]:
    starts = sorted({span["start"] for span in break_grapheme_spans(text, locale)})
    interior = _word_interior_offsets(text, locale)
    detections: list[ValueDetection] = []
    cursor = 0
    for start in starts:
        if start < cursor or start in interior:
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
        if end in interior:
            continue
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
