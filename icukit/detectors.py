"""Detectors: find typed values in running text by inverting ICU's formatting.

This module holds what every reader shares -- the value and spec records, the
:class:`ValueDetection` shape, the :class:`Detector` protocol, and the
:class:`DetectorSet` gang -- and the strict readers, :class:`DateDetector` and
:class:`NumberDetector`, where an ICU parser inverts the formatter (dates, times,
datetimes, decimal numbers, currency, percent). The flexible readers, which read the
forms text writes beyond ICU's own, are in :mod:`icukit.recognize`; the assembled sets
are :func:`~icukit.engine.generated_detectors` (a reader for each canonical ICU form)
and :func:`~icukit.engine.flexible_detectors`.

Each accepted match is a :class:`ValueDetection` that carries the structure of the
parse::

    surface  <->  (spec, value, captures)

For the strict readers the invariant ``reformat(spec, value) == surface`` is also the
acceptance test, so a permissive ICU spelling that would not reproduce its own surface
is rejected rather than accepted.

* ``value`` -- an immutable semantic record (:class:`DateTimeValue` / :class:`NumberValue`).
  Numeric values are canonical decimal *strings* derived from the accepted surface, never a
  binary ``float`` (this PyICU's ``Formattable`` has no decimal accessor, so a float would
  otherwise be smuggled in).
* ``captures`` -- the named sub-parts of the match (:class:`Capture`): year/month/day of a
  date, sign/integer/fraction of a number, each with its own source span, resolved value,
  and form (short/wide/numeric/symbol). They reveal *how* the surface decomposes.
* ``spec`` -- the generative recipe (:class:`DateFormatSpec` / :class:`NumberFormatSpec`):
  the parameters sufficient to reproduce the surface. Calendars are *observed*, not assumed
  Gregorian, so a Buddhist or Persian locale round-trips correctly.

Detectors run individually (``detector.detect(text)``) or ganged in an immutable
:class:`DetectorSet`; a gang's result equals the merge of running its members alone.
Everything here is pure icukit over code-point offsets -- no tiergraph.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterable
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

import icu

from ._offsets import boundary_maps, u16_boundary_to_codepoint
from .breaker import break_grapheme_spans, break_word_spans
from .detect import Detection

__all__ = [
    "Capture",
    "CompactFormatSpec",
    "DateFormatSpec",
    "DateIntervalSpec",
    "DateIntervalValue",
    "DateDetector",
    "DateTimeValue",
    "Detector",
    "DetectorRefusal",
    "DetectorSet",
    "MeasureFormatSpec",
    "MeasureValue",
    "UnitValue",
    "NumberFormatSpec",
    "NumberDetector",
    "NumberValue",
    "RelativeDateSpec",
    "RelativeDateValue",
    "SpelloutFormatSpec",
    "ValueDetection",
    "abbreviation_detectors",
    "all_detectors",
    "date_detectors",
    "detect",
    "detector_key",
    "number_detectors",
]

# Closed vocabulary of refusal reasons (an ostensibly-successful parse with an
# unrepresentable endpoint -- distinct from an ordinary parse miss, which is silent).
RefusalReason = Literal[
    "reversed-endpoint",
    "out-of-range-endpoint",
    "surrogate-interior-endpoint",
    "mid-grapheme-endpoint",
    "inconsistent-surface",
]


# --------------------------------------------------------------------------- values


@dataclass(frozen=True)
class DateTimeValue:
    """Civil date/time fields recovered from a temporal parse.

    ``fields`` holds only the fields the pattern actually pins, as ``(name, value)``
    pairs in canonical order (e.g. ``(("y", 2569), ("M", 1), ("d", 3))``). ``calendar``
    is the *observed* calendar of those fields -- ``"buddhist"`` for ``th_TH`` etc. -- so
    the year is the value displayed in that calendar, matching the surface. A moment is
    *derivable* from these fields plus the spec's calendar and time zone when a caller
    needs one; it is never stored, so the record never implies a time the surface did
    not show.
    """

    fields: tuple[tuple[str, int], ...]
    calendar: str


@dataclass(frozen=True)
class DateIntervalValue:
    """A recovered (start, end) civil date/time interval.

    Each endpoint is a :class:`DateTimeValue` holding only the fields the interval pins
    (shared higher-order fields inherited on both ends), with 1-based months and the
    observed calendar.
    """

    start: DateTimeValue
    end: DateTimeValue


@dataclass(frozen=True)
class NumberValue:
    """A numeric value recovered as a canonical decimal string.

    ``decimal`` is derived from the accepted surface (locale digits and separators
    normalized to ASCII), never from a binary ``float``. For a percent it is the ratio
    (``"7%"`` -> ``"0.07"``); for a currency, ``currency`` carries the ISO 4217 code.
    """

    decimal: str
    currency: str | None = None


@dataclass(frozen=True)
class MeasureValue:
    """A numeric value paired with its canonical ICU unit identifier."""

    decimal: str
    unit: str


@dataclass(frozen=True)
class UnitValue:
    """A unit written without an amount, such as a rate's per form ("/s").

    ``unit`` is the canonical ICU identifier (``per-second``). There is no amount, so
    none is recorded.
    """

    unit: str


@dataclass(frozen=True)
class RelativeDateValue:
    """A signed relative offset in one duration unit."""

    offset: int
    unit: str
    direction: str


# --------------------------------------------------------------------------- captures


@dataclass(frozen=True)
class Capture:
    """One named sub-part of a match, revealing the parse structure.

    ``start``/``end`` are code-point offsets into the *source* text (half-open), so
    ``text[start:end]`` is this part's surface. ``value`` is the resolved value --
    numeric (``day`` -> ``3``) or an enumerated member (``weekday`` -> ``"wednesday"``,
    ``month`` -> ``1``). ``form`` is how the surface encodes it: ``"numeric"``,
    ``"short"``, ``"wide"``, ``"narrow"``, or ``"symbol"``.
    """

    name: str
    start: int
    end: int
    text: str
    value: object | None = None
    form: str | None = None


# --------------------------------------------------------------------------- specs


@dataclass(frozen=True)
class DateFormatSpec:
    """The generative recipe for a temporal detection.

    ``skeleton`` is the caller's canonical skeleton; ``pattern`` is the locale best
    pattern actually used; ``calendar`` is observed from the constructed formatter, not
    assumed. ``field_forms`` records each present field's form (``("month", "short")``).
    """

    locale: str
    skeleton: str
    pattern: str
    calendar: str
    tz: str = "GMT"
    field_forms: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class DateIntervalSpec:
    """Generative recipe for a date-interval detection.

    ``locale`` and ``skeleton`` select the ICU :class:`DateIntervalFormat` that
    reproduces the surface.
    """

    locale: str
    skeleton: str


@dataclass(frozen=True)
class NumberFormatSpec:
    """The generative recipe for a numeric detection.

    ``grouping_sizes`` are Known from the formatter (e.g. ``(3,)`` for en_US,
    ``(2, 3)`` for hi_IN Indian grouping), not read off one value; ``None`` when the
    formatter groups by no fixed size. ``min_fraction``/``max_fraction`` are the
    formatter's configured fraction-digit bounds.
    """

    locale: str
    kind: Literal["decimal", "currency", "percent", "scientific"]
    currency: str | None = None
    min_fraction: int | None = None
    max_fraction: int | None = None
    grouping_sizes: tuple[int, ...] | None = None


@dataclass(frozen=True)
class CompactFormatSpec:
    """The locale and width used for a compact-number candidate."""

    locale: str
    width: str


@dataclass(frozen=True)
class SpelloutFormatSpec:
    """The locale and ICU rule set used for a spelled-out cardinal candidate."""

    locale: str
    ruleset: str


@dataclass(frozen=True)
class MeasureFormatSpec:
    """The locale, canonical ICU unit, and width used for a measure candidate."""

    locale: str
    unit: str
    width: str


@dataclass(frozen=True)
class RelativeDateSpec:
    """The locale used to generate a relative-date phrase."""

    locale: str


# --------------------------------------------------------------------------- detection


class ValueDetection(Detection):
    """A typed detection with formatter structure or recall annotations.

    Inherits ``text``/``start``/``end``/``type`` (code-point offsets) and adds ``value``,
    ``captures``, and ``spec`` (see the module docstring). For the strict,
    formatter-inverting detector family, ``reformat(spec, value) == text`` holds for every
    accepted detection. Recall recognizers such as ``Flexible*`` and abbreviations instead
    deposit structurally valid candidates with an explicit surface or annotation model.
    Abbreviation surfaces round-trip by identity; their expansions are annotations, never
    reformats.
    """

    value: object
    captures: tuple[Capture, ...]
    spec: object


# --------------------------------------------------------------------------- refusal


class DetectorRefusal(Exception):
    """An ostensibly-successful ICU parse produced an unrepresentable endpoint.

    This is *not* a parse miss (a miss is silent and returns no candidate). It signals a
    reversed, surrogate-interior, or mid-grapheme endpoint -- an invariant violation the
    detector refuses to represent rather than emit wrongly. It carries a stable
    ``reason`` from :data:`RefusalReason` and the offsets involved.
    """

    def __init__(
        self,
        type: str,
        start: int,
        endpoint: int | None,
        reason: RefusalReason,
        message: str,
    ) -> None:
        self.type = type
        self.start = start
        self.endpoint = endpoint
        self.reason = reason
        super().__init__(f"{reason}: {message} (type={type!r}, start={start}, end={endpoint})")


# --------------------------------------------------------------------------- protocol


@runtime_checkable
class Detector(Protocol):
    """A runnable detector.

    ``type`` is the stable label carried on its detections (``date:yMMMd``,
    ``number:currency:USD``); ``group`` is its coarse family (``date``, ``number``) and
    equals the ``type`` prefix. ``detect`` scans the whole text and returns its
    detections in source order -- unanchored, partial, tolerant of finding nothing.
    """

    type: str
    group: str

    def detect(self, text: str) -> list[ValueDetection]: ...


# --------------------------------------------------------------------------- dates


@dataclass(frozen=True)
class _DateField:
    letter: str
    width: int
    name: str
    calendar_field: int
    format_field: int
    form: str
    value_field: bool = True


def _is_pattern_letter(char: str) -> bool:
    """A CLDR date pattern letter is an ASCII letter; everything else is literal text.

    Localized patterns interleave field letters with locale literal text (e.g. Japanese
    ``y年M月d日``); that literal text is often alphabetic under Unicode, so classifying it
    by ``str.isalpha`` would mistake it for unmodeled fields and reject an otherwise
    invertible skeleton. CLDR pattern letters are drawn only from ``A-Za-z``.
    """
    return char.isascii() and char.isalpha()


def _pattern_runs(pattern: str) -> list[tuple[str, int]]:
    """Return unquoted CLDR pattern-letter runs."""
    runs: list[tuple[str, int]] = []
    quoted = False
    index = 0
    while index < len(pattern):
        if pattern[index] == "'":
            if index + 1 < len(pattern) and pattern[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
            index += 1
            continue
        if quoted or not _is_pattern_letter(pattern[index]):
            index += 1
            continue
        letter = pattern[index]
        end = index + 1
        while end < len(pattern) and pattern[end] == letter:
            end += 1
        runs.append((letter, end - index))
        index = end
    return runs


def _date_form(letter: str, width: int) -> str:
    if letter in {"M", "L", "E", "e", "c"} and width >= 3:
        return {3: "short", 4: "wide"}.get(width, "narrow")
    return "numeric"


@functools.cache
def _pattern_field_id(letter: str) -> int:
    """ICU FieldPosition field id carrying the span for CLDR pattern `letter`.

    ICU gives the format vs standalone variants of month ('M' vs 'L') and weekday
    ('E'/'e' vs 'c') distinct field ids, and this PyICU build exposes named constants
    only for the format variants. Rather than hard-code the standalone enum values,
    discover the id reflectively: format a probe instant with a pattern built from
    `letter` alone and return the one field id whose reported span is non-empty.
    """
    probe = icu.SimpleDateFormat(letter * 3, icu.Locale("en"))
    calendar = icu.GregorianCalendar(icu.Locale("en"))
    calendar.set(2020, 0, 15)  # 15 Jan 2020 (a Wednesday): every month/weekday span non-empty
    instant = calendar.getTime()
    for field_id in range(64):  # generous upper bound on ICU's UDateFormatField enum
        position = icu.FieldPosition(field_id)
        probe.format(instant, position)
        if position.getBeginIndex() != position.getEndIndex():
            return field_id
    return -1


def _date_fields(pattern: str) -> tuple[_DateField, ...]:
    # This is CLDR pattern grammar, not locale data. Calendar values and displayed names
    # are obtained from the formatter/calendar at runtime.
    mapping = {
        "y": ("y", icu.Calendar.YEAR, icu.DateFormat.kYearField, True),
        "M": ("M", icu.Calendar.MONTH, icu.DateFormat.kMonthField, True),
        "L": ("M", icu.Calendar.MONTH, icu.DateFormat.kMonthField, True),
        "d": ("d", icu.Calendar.DATE, icu.DateFormat.kDateField, True),
        "H": ("H", icu.Calendar.HOUR_OF_DAY, icu.DateFormat.kHourOfDay0Field, True),
        "h": ("h", icu.Calendar.HOUR, icu.DateFormat.kHour1Field, True),
        "K": ("h", icu.Calendar.HOUR, icu.DateFormat.kHour0Field, True),
        "k": ("H", icu.Calendar.HOUR_OF_DAY, icu.DateFormat.kHourOfDay1Field, True),
        "m": ("m", icu.Calendar.MINUTE, icu.DateFormat.kMinuteField, True),
        "s": ("s", icu.Calendar.SECOND, icu.DateFormat.kSecondField, True),
        "E": ("weekday", icu.Calendar.DAY_OF_WEEK, icu.DateFormat.kDayOfWeekField, False),
        "e": ("weekday", icu.Calendar.DAY_OF_WEEK, icu.DateFormat.kDayOfWeekField, False),
        "c": ("weekday", icu.Calendar.DAY_OF_WEEK, icu.DateFormat.kDayOfWeekField, False),
    }
    found: list[_DateField] = []
    for letter, width in _pattern_runs(pattern):
        if letter not in mapping:
            continue
        name, calendar_field, _format_field, value_field = mapping[letter]
        found.append(
            _DateField(
                letter,
                width,
                name,
                calendar_field,
                _pattern_field_id(letter),
                _date_form(letter, width),
                value_field,
            )
        )
    order = {"y": 0, "M": 1, "d": 2, "weekday": 3, "H": 4, "h": 4, "m": 5, "s": 6}
    return tuple(sorted(found, key=lambda field: order[field.name]))


class DateDetector:
    """Detect canonical ICU date surfaces for ``locale`` and ``skeleton``.

    The public ``tz`` parameter is deliberately restricted to ``"GMT"``: the current
    date specification fixes GMT so date-only parsing cannot acquire host-zone behavior.

    A year from a ``y`` field is read only in four or more digits, as ICU writes every
    year from 1000 on; a shorter one cannot be told from a count after a month ("June
    200", "August 9", "3/4"). A ``yy`` field keeps its two digits.
    """

    group = "date"

    def __init__(self, locale: str, skeleton: str, tz: str = "GMT") -> None:
        if tz != "GMT":
            raise ValueError("DateDetector currently requires tz='GMT'")
        self.locale = locale
        self.skeleton = skeleton
        self.tz = tz
        self.type = f"date:{skeleton}"
        generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(locale))
        self.pattern = generator.getBestPattern(skeleton)
        # A skeleton this locale's generator cannot express yields an empty pattern,
        # which carries no field for the check below to find unsupported. Left alone it
        # builds a detector that matches nothing on every input and never says why, so
        # "I cannot detect this skeleton" reaches the caller as "there are no dates
        # here". Refuse it instead, naming the skeleton.
        if not self.pattern:
            raise ValueError(
                f"DateDetector cannot detect skeleton {skeleton!r} in locale "
                f"{locale!r}: the locale's pattern generator produces no pattern "
                f"for it, so no date could ever be recognized"
            )
        self._df = icu.SimpleDateFormat(self.pattern, icu.Locale(locale))
        self._df.setTimeZone(icu.TimeZone.getGMT())
        self._fields = _date_fields(self.pattern)
        # Refuse a skeleton whose best pattern carries a field this detector cannot make
        # invertible, rather than emit a value that cannot reproduce the surface. The
        # 24-hour clock (H/k) and dates are fully modeled; the 12-hour clock needs a
        # day-period field whose value modeling is deferred, and era/quarter/week/
        # time-zone fields are out of scope. A day-period letter (a/b/B) is exactly what
        # makes "3:45 PM" non-invertible from bare (h, m).
        _modeled = {"y", "M", "L", "d", "H", "k", "m", "s", "E", "e", "c"}
        _letters = {letter for letter, _ in _pattern_runs(self.pattern)}
        _unmodeled = sorted(_letters - _modeled)
        if _unmodeled:
            raise ValueError(
                f"DateDetector cannot invert pattern field(s) {_unmodeled} in {self.pattern!r} "
                f"(skeleton {skeleton!r}); 12-hour/day-period, era, quarter, week, and time-zone "
                f"fields are not supported"
            )
        # A weekday with no year ("Tue, 3/5") names a date in some year the text does not
        # give; ICU resolves a year-less parse in 1970, where 5 March is a Thursday.
        self._yearless_weekday = bool(_letters & {"E", "e", "c"}) and "y" not in _letters
        self._inv = _Inverter(self._parse, self._reformat, self._build)

    def _parse(self, text: icu.UnicodeString, start_u16: int) -> tuple[int, object] | None:
        calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(self.locale))
        calendar.clear()
        if self._yearless_weekday:
            # A leap year, so "Sat, 2/29" keeps its day rather than rolling to 1 March.
            calendar.set(icu.Calendar.YEAR, 1972)
        position = icu.ParsePosition(start_u16)
        self._df.parse(text, calendar, position)
        if position.getErrorIndex() != -1 or position.getIndex() <= start_u16:
            return None
        end = position.getIndex()
        if self._yearless_weekday:
            calendar = self._weekday_year(calendar, str(text[start_u16:end]))
        return end, calendar

    def _weekday_year(self, calendar: object, surface: str) -> object:
        """The parse placed in a year where its day falls on the weekday the text names.

        The weekdays repeat every 28 years, so one of 1970 to 1997 reproduces the surface
        if any year does; the year is not a value field, since the pattern shows none.
        Where none does, the parse stands and fails the reformat check as before.
        """
        if self._df.format(calendar.getTime()) == surface:
            return calendar
        fields = (
            icu.Calendar.MONTH,
            icu.Calendar.DATE,
            icu.Calendar.HOUR_OF_DAY,
            icu.Calendar.MINUTE,
            icu.Calendar.SECOND,
        )
        month, day, hour, minute, second = (calendar.get(field) for field in fields)
        for year in range(1970, 1998):
            candidate = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(self.locale))
            candidate.clear()
            candidate.set(year, month, day, hour, minute, second)
            if candidate.get(icu.Calendar.DATE) != day:
                continue
            if self._df.format(candidate.getTime()) == surface:
                return candidate
        return calendar

    def _reformat(self, parsed: object) -> str:
        calendar = parsed
        return self._df.format(calendar.getTime())

    def _field_value(self, calendar: object, field: _DateField) -> object:
        value = calendar.get(field.calendar_field)
        if field.name == "M":
            return value + 1
        if field.name == "weekday":
            symbols = icu.DateFormatSymbols(icu.Locale("en"))
            return symbols.getWeekdays()[value].lower()
        if field.letter == "h" and value == 0:
            return 12
        if field.letter == "k" and value == 0:
            return 24
        return value

    def _build(
        self,
        parsed: object,
        surface: str,
        start_cp: int,
        cp_to_u16: list[int],
        u16_to_cp: dict[int, int],
    ) -> tuple[object, tuple[Capture, ...], object] | None:
        calendar = parsed
        values: list[tuple[str, int]] = []
        captures: list[Capture] = []
        forms: list[tuple[str, str]] = []
        start_u16 = cp_to_u16[start_cp]
        for field in self._fields:
            value = self._field_value(calendar, field)
            if field.value_field:
                values.append((field.name, value))
            forms.append((field.name, field.form))
            position = icu.FieldPosition(field.format_field)
            self._df.format(calendar.getTime(), position)
            if position.getBeginIndex() == position.getEndIndex():
                # A value field must be locatable; otherwise skip this candidate. A
                # display-only field (weekday) is derivable from the date via the pattern,
                # so omit its capture rather than emit a zero-length one.
                if field.value_field:
                    return None
                continue
            begin_u16 = start_u16 + position.getBeginIndex()
            end_u16 = start_u16 + position.getEndIndex()
            begin_cp = u16_to_cp[begin_u16]
            end_cp = u16_to_cp[end_u16]
            if field.letter == "y" and field.width != 2 and end_cp - begin_cp < 4:
                # ICU's "y" writes a year in as many digits as it has: four for every
                # year from 1000 on, and one to three below it ("June 200", "3/4"). The
                # reformat check cannot tell those from a count after a month ("in June
                # 200 cases", "August 9"), so a year under four digits is not read here,
                # a hand-rolled limit; "yy" keeps its two digits, which ICU writes for
                # every year. An era would mark a short year a year, but this detector
                # refuses a pattern with an era field (see __init__), so none reaches here.
                return None
            captures.append(
                Capture(
                    field.name,
                    begin_cp,
                    end_cp,
                    surface[begin_cp - start_cp : end_cp - start_cp],
                    value,
                    field.form,
                )
            )
        calendar_type = calendar.getType()
        value = DateTimeValue(tuple(values), calendar_type)
        spec = DateFormatSpec(
            self.locale,
            self.skeleton,
            self.pattern,
            calendar_type,
            self.tz,
            tuple(forms),
        )
        return value, tuple(captures), spec

    def detect(self, text: str) -> list[ValueDetection]:
        return _scan(text, self.locale, self.type, self._inv)


# --------------------------------------------------------------------------- numbers


class NumberDetector:
    """Detect canonical ICU decimal, currency, or percent surfaces."""

    group = "number"

    def __init__(
        self,
        locale: str,
        kind: Literal["decimal", "currency", "percent"],
        currency: str | None = None,
    ) -> None:
        if kind not in {"decimal", "currency", "percent"}:
            raise ValueError("kind must be 'decimal', 'currency', or 'percent'")
        if currency is not None and kind != "currency":
            raise ValueError("currency is only valid for kind='currency'")

        self.locale = locale
        self.kind = kind
        icu_locale = icu.Locale(locale)
        if kind == "currency":
            self._nf = icu.NumberFormat.createCurrencyInstance(icu_locale)
            if currency is not None:
                self._nf.setCurrency(currency)
            self.currency = self._nf.getCurrency()
            self.type = f"number:currency:{self.currency}"
        elif kind == "percent":
            self._nf = icu.NumberFormat.createPercentInstance(icu_locale)
            self.currency = None
            self.type = "number:percent"
        else:
            self._nf = icu.NumberFormat.createInstance(icu_locale)
            self.currency = None
            self.type = "number:decimal"

        symbols = self._nf.getDecimalFormatSymbols()
        symbol = icu.DecimalFormatSymbols
        self._decimal = symbols.getSymbol(symbol.kDecimalSeparatorSymbol)
        self._grouping = symbols.getSymbol(symbol.kGroupingSeparatorSymbol)
        self._zero = symbols.getSymbol(symbol.kZeroDigitSymbol)
        self._minus = symbols.getSymbol(symbol.kMinusSignSymbol)
        self._plus = symbols.getSymbol(symbol.kPlusSignSymbol)
        self._currency_symbol = symbols.getSymbol(symbol.kCurrencySymbol)
        self._percent = symbols.getSymbol(symbol.kPercentSymbol)
        self._inv = _Inverter(self._parse, self._reformat, self._build)

    def _parse(self, text: icu.UnicodeString, start_u16: int) -> tuple[int, object] | None:
        position = icu.ParsePosition(start_u16)
        parsed = self._nf.parse(text, position)
        if position.getErrorIndex() != -1 or position.getIndex() <= start_u16:
            return None
        return position.getIndex(), parsed

    def _reformat(self, parsed: object) -> str:
        # Format the parsed Formattable directly, not its getDouble(): a double loses
        # precision above 2^53, which would reject an exact large-integer surface and
        # then mis-detect a suffix. The Formattable keeps the int64 the parse recovered.
        return self._nf.format(parsed)

    def _ascii_digits(self, text: str) -> str:
        zero = ord(self._zero)
        converted: list[str] = []
        for character in text:
            offset = ord(character) - zero
            if 0 <= offset <= 9:
                converted.append(str(offset))
        return "".join(converted)

    def _capture(
        self,
        name: str,
        begin: int,
        end: int,
        surface: str,
        start_cp: int,
        start_u16: int,
        u16_to_cp: dict[int, int],
        value: object | None,
        form: str,
    ) -> Capture:
        begin_cp = u16_to_cp[start_u16 + begin]
        end_cp = u16_to_cp[start_u16 + end]
        return Capture(
            name,
            begin_cp,
            end_cp,
            surface[begin_cp - start_cp : end_cp - start_cp],
            value,
            form,
        )

    def _symbol_capture(
        self,
        name: str,
        symbol: str,
        surface: str,
        start_cp: int,
        start_u16: int,
        u16_to_cp: dict[int, int],
    ) -> Capture | None:
        begin_cp = surface.find(symbol)
        if begin_cp < 0:
            return None
        local_cp_to_u16, _ = boundary_maps(surface)
        return self._capture(
            name,
            local_cp_to_u16[begin_cp],
            local_cp_to_u16[begin_cp + len(symbol)],
            surface,
            start_cp,
            start_u16,
            u16_to_cp,
            None,
            "symbol",
        )

    def _build(
        self,
        parsed: object,
        surface: str,
        start_cp: int,
        cp_to_u16: list[int],
        u16_to_cp: dict[int, int],
    ) -> tuple[object, tuple[Capture, ...], object]:
        start_u16 = cp_to_u16[start_cp]
        integer_position = icu.FieldPosition(icu.NumberFormat.kIntegerField)
        self._nf.format(parsed, integer_position)
        fraction_position = icu.FieldPosition(icu.NumberFormat.kFractionField)
        self._nf.format(parsed, fraction_position)

        local_cp_to_u16, local_u16_to_cp = boundary_maps(surface)
        integer_begin = local_u16_to_cp[integer_position.getBeginIndex()]
        integer_end = local_u16_to_cp[integer_position.getEndIndex()]
        integer_text = surface[integer_begin:integer_end]
        integer_ascii = self._ascii_digits(integer_text)
        captures = [
            self._capture(
                "integer",
                integer_position.getBeginIndex(),
                integer_position.getEndIndex(),
                surface,
                start_cp,
                start_u16,
                u16_to_cp,
                integer_ascii,
                "numeric",
            )
        ]

        fraction_ascii = ""
        if fraction_position.getEndIndex() > fraction_position.getBeginIndex():
            fraction_begin = local_u16_to_cp[fraction_position.getBeginIndex()]
            fraction_end = local_u16_to_cp[fraction_position.getEndIndex()]
            fraction_ascii = self._ascii_digits(surface[fraction_begin:fraction_end])
            captures.append(
                self._capture(
                    "fraction",
                    fraction_position.getBeginIndex(),
                    fraction_position.getEndIndex(),
                    surface,
                    start_cp,
                    start_u16,
                    u16_to_cp,
                    fraction_ascii,
                    "numeric",
                )
            )
            separator_start = surface.find(self._decimal, integer_end, fraction_begin)
            if separator_start >= 0:
                separator_u16 = local_cp_to_u16[separator_start]
                captures.append(
                    self._capture(
                        "decimal-separator",
                        separator_u16,
                        local_cp_to_u16[separator_start + len(self._decimal)],
                        surface,
                        start_cp,
                        start_u16,
                        u16_to_cp,
                        None,
                        "symbol",
                    )
                )

        sign = (
            self._minus if self._minus in surface else self._plus if self._plus in surface else None
        )
        if sign is not None:
            capture = self._symbol_capture("sign", sign, surface, start_cp, start_u16, u16_to_cp)
            if capture is not None:
                captures.append(capture)
        if self.kind == "currency":
            capture = self._symbol_capture(
                "currency", self._currency_symbol, surface, start_cp, start_u16, u16_to_cp
            )
            if capture is not None:
                captures.append(capture)
        if self.kind == "percent":
            capture = self._symbol_capture(
                "percent", self._percent, surface, start_cp, start_u16, u16_to_cp
            )
            if capture is not None:
                captures.append(capture)

        normalized = ("-" if sign == self._minus else "") + integer_ascii
        if fraction_ascii:
            normalized += "." + fraction_ascii
        if self.kind == "percent":
            normalized = str(Decimal(normalized) / 100)
        value = NumberValue(normalized, self.currency)

        grouping_sizes = None
        if self._nf.isGroupingUsed():
            primary = self._nf.getGroupingSize()
            secondary = self._nf.getSecondaryGroupingSize()
            # Left-to-right semantic order: secondary groups, then the rightmost primary.
            grouping_sizes = (secondary, primary) if secondary else (primary,)
        spec = NumberFormatSpec(
            self.locale,
            self.kind,
            self.currency,
            self._nf.getMinimumFractionDigits(),
            self._nf.getMaximumFractionDigits(),
            grouping_sizes,
        )
        captures.sort(key=lambda capture: (capture.start, capture.end))
        return value, tuple(captures), spec

    def detect(self, text: str) -> list[ValueDetection]:
        return _scan(text, self.locale, self.type, self._inv)


# --------------------------------------------------------------------------- scanner

# The scanner is generic over kind. A detector supplies an _Inverter bound to its
# ICU formatter; the scanner owns position walking, offset maps, endpoint validation,
# reformat-equality acceptance, and greedy longest-match resume.


@dataclass(frozen=True)
class _Inverter:
    """What the windowed scanner needs from a concrete detector.

    ``parse`` attempts an ICU parse anchored at a UTF-16 offset and returns
    ``(end_u16, parsed)`` for a clean success (no error index) or ``None`` for an
    ordinary miss (exception / error index). ``end_u16`` may be ``<= start`` -- the
    scanner classifies reversed / no-progress. ``reformat`` renders ``parsed`` back to
    its canonical surface. ``build`` produces ``(value, captures, spec)`` from the
    accepted surface (value is surface-derived, never a float).
    """

    parse: Callable[[icu.UnicodeString, int], tuple[int, object] | None]
    reformat: Callable[[object], str]
    build: Callable[
        [object, str, int, list[int], dict[int, int]],
        tuple[object, tuple[Capture, ...], object] | None,
    ]


def _contains_float(obj: object) -> bool:
    """True if a ``float`` lurks anywhere in a value/spec record (recursively).

    A detection's value is surface-derived, never a binary ``float`` (ICU's
    ``Formattable`` has no decimal accessor, so ``7%`` would arrive as ``0.07``). This
    guards the acceptance seam so a mis-built detector cannot smuggle a float into a
    record before it is hashed or emitted. ``bool`` is an ``int`` subclass and is fine.
    """
    if isinstance(obj, bool):
        return False
    if isinstance(obj, float):
        return True
    if is_dataclass(obj) and not isinstance(obj, type):
        return any(_contains_float(getattr(obj, f.name)) for f in fields(obj))
    if isinstance(obj, (tuple, list)):
        return any(_contains_float(item) for item in obj)
    return False


@functools.lru_cache(maxsize=16)
def _word_edges(text: str, locale: str) -> frozenset[int]:
    """ICU word-break offsets of ``text``, cached so a gang segments a text once."""
    edges = {0, len(text)}
    for span in break_word_spans(text, locale):
        edges.add(span["start"])
        edges.add(span["end"])
    return frozenset(edges)


_EXTENDING_CATEGORIES = frozenset(
    {
        icu.UCharCategory.NON_SPACING_MARK,
        icu.UCharCategory.COMBINING_SPACING_MARK,
        icu.UCharCategory.ENCLOSING_MARK,
        icu.UCharCategory.FORMAT_CHAR,
    }
)


def _base_before(text: str, offset: int) -> str | None:
    """The character before ``offset``, looking past marks and format characters."""
    index = offset - 1
    while index >= 0 and icu.Char.charType(text[index]) in _EXTENDING_CATEGORIES:
        index -= 1
    return text[index] if index >= 0 else None


def _is_script_seam(left: str | None, right: str) -> bool:
    """A digit against a letter of a script written without spaces between words.

    ICU's dictionary segmentation of Thai, Lao, Khmer, or Myanmar can leave a digit and
    its neighboring letters in one "word" ("ราคา100บาท"), although the digits are a
    token of their own; ICU marks those scripts as breaking between letters.
    """
    if left is None:
        return False
    for digit, letter in ((left, right), (right, left)):
        if (
            icu.Char.isdigit(digit)
            and icu.Char.isalpha(letter)
            and icu.Script.getScript(letter).breaksBetweenLetters()
        ):
            return True
    return False


_EXTEND_NUM_LET = icu.Char.getPropertyValueEnum(icu.UProperty.WORD_BREAK, "ExtendNumLet")


def _is_word_joiner(character: str) -> bool:
    """A connector ICU's word rules join into a word: "_" and its kin, not a space.

    Word_Break=ExtendNumLet without the spaces it also holds (the narrow no-break space
    French writes in "5\u202f%" stays a gap), so "_2788" and "2788_" are one word.
    """
    return icu.Char.getIntPropertyValue(
        character, icu.UProperty.WORD_BREAK
    ) == _EXTEND_NUM_LET and not icu.Char.isUWhiteSpace(character)


@functools.lru_cache(maxsize=16)
def _word_interior_offsets(text: str, locale: str) -> frozenset[int]:
    """Offsets inside one word with word characters on both sides of them in that word.

    A reading may not start or end at one of these: "788" inside "2788" or "ab2,788",
    "29" inside "29th", and "123" inside "asdf123" are fragments of a longer token, not
    readings of it. The word is ICU's, so "3" in "我有3个" is its own token, and a mark
    or format character is part of the word it extends. A word character is an
    alphanumeric or a connector ICU joins into words (:func:`_is_word_joiner`), so
    "2788" in "_2788" or "2788_" is a fragment of an identifier; markup such as
    emphasis is taken out before text reaches recognition. A digit against a letter of
    a script that ICU breaks between letters is a seam, not an interior ("100" in
    "ราคา100บาท").
    """
    edges = sorted(_word_edges(text, locale))
    interior: set[int] = set()
    for word_start, word_end in zip(edges, edges[1:], strict=False):
        alnum = [
            i
            for i in range(word_start, word_end)
            if icu.Char.isalnum(text[i]) or _is_word_joiner(text[i])
        ]
        if len(alnum) < 2:
            continue
        for offset in range(alnum[0] + 1, alnum[-1] + 1):
            if not _is_script_seam(_base_before(text, offset), text[offset]):
                interior.add(offset)
    return frozenset(interior)


def _scan(text: str, locale: str, type_label: str, inv: _Inverter) -> list[ValueDetection]:
    """Windowed detection with reformat-equality acceptance and greedy longest-match.

    Scans grapheme-cluster starts left to right. A miss or no forward progress simply
    continues (never a refusal). A successful parse whose endpoint is reversed,
    surrogate-interior, or mid-grapheme is a :class:`DetectorRefusal`. An accepted span
    must reproduce the formatter's canonical output exactly (rejecting ICU's permissive
    coercions), and may neither start nor end inside a word between two alphanumerics
    (see :func:`_word_interior_offsets`). After a match ``[s, e)`` the scan resumes at
    ``e`` so one detector never self-overlaps.
    """
    us = icu.UnicodeString(text)
    cp_to_u16, u16_to_cp = boundary_maps(text)
    gspans = break_grapheme_spans(text, locale)
    starts = sorted({g["start"] for g in gspans})
    boundaries = {g["start"] for g in gspans} | {g["end"] for g in gspans} | {0, len(text)}
    interior = _word_interior_offsets(text, locale)

    out: list[ValueDetection] = []
    cursor = 0
    for start_cp in starts:
        if start_cp < cursor:
            continue  # greedy: inside a prior match
        if start_cp in interior:
            continue  # a fragment of a longer token
        result = inv.parse(us, cp_to_u16[start_cp])
        if result is None:
            continue  # ordinary miss
        end_u16, parsed = result
        if end_u16 < cp_to_u16[start_cp]:
            raise DetectorRefusal(
                type_label, start_cp, end_u16, "reversed-endpoint", "parse ended before its start"
            )
        if end_u16 == cp_to_u16[start_cp]:
            continue  # no forward progress -> miss
        if end_u16 > cp_to_u16[-1]:
            raise DetectorRefusal(
                type_label,
                start_cp,
                end_u16,
                "out-of-range-endpoint",
                "parse ended beyond the end of the text",
            )
        end_cp = u16_boundary_to_codepoint(u16_to_cp, end_u16)
        if end_cp is None:
            raise DetectorRefusal(
                type_label,
                start_cp,
                end_u16,
                "surrogate-interior-endpoint",
                "parse ended inside a surrogate pair",
            )
        if end_cp not in boundaries:
            raise DetectorRefusal(
                type_label,
                start_cp,
                end_cp,
                "mid-grapheme-endpoint",
                "parse ended inside a grapheme cluster",
            )
        if end_cp in interior:
            continue  # a fragment of a longer token
        surface = text[start_cp:end_cp]
        try:
            reformatted = inv.reformat(parsed)
        except icu.ICUError:
            # ICU accepted a parse it cannot reformat (an out-of-range field
            # combination whose getTime() is illegal). Not a match, not fatal.
            continue
        if reformatted != surface:
            continue  # permissive coercion -> not accepted (not fatal)
        built = inv.build(parsed, surface, start_cp, cp_to_u16, u16_to_cp)
        if built is None:
            continue
        value, captures, spec = built
        if _contains_float(value) or _contains_float(spec) or _contains_float(captures):
            raise ValueError(
                f"{type_label}: build() produced a float in a record (values are "
                f"surface-derived, never a float) at [{start_cp}, {end_cp})"
            )
        out.append(
            ValueDetection(
                text=surface,
                start=start_cp,
                end=end_cp,
                type=type_label,
                value=value,
                captures=captures,
                spec=spec,
            )
        )
        cursor = end_cp
    return out


# --------------------------------------------------------------------------- orchestration


def _value_key(value: object) -> str:
    """A stable, total sort key for a semantic value record."""
    if isinstance(value, DateTimeValue):
        return f"dt:{value.calendar}:{value.fields!r}"
    if isinstance(value, NumberValue):
        return f"num:{value.currency}:{value.decimal}"
    return f"other:{value!r}"


def _sort_key(det: ValueDetection) -> tuple[int, int, str, str]:
    # start ascending, longer extent first, then type, then value key -- fully deterministic.
    return (det["start"], -(det["end"] - det["start"]), det["type"], _value_key(det["value"]))


def detect(text: str, detectors: list[Detector] | tuple[Detector, ...]) -> list[ValueDetection]:
    """Run every detector over ``text`` and return the merged detections.

    Detections are returned in a fully deterministic order (start ascending, longer
    extent first, then type, then value key) independent of ``detectors`` order.
    Detections from different detectors may overlap: recognition keeps every
    candidate, and choosing among overlapping readings is left to the consumer.

    Each detector runs its own scan, so a gang's result equals the merge of running its
    members alone. A single shared scan would be faster; any such scan must give this
    same merge.
    """
    found: list[ValueDetection] = []
    for det in detectors:
        found.extend(det.detect(text))
    found.sort(key=_sort_key)
    return found


@dataclass(frozen=True)
class DetectorSet:
    """An immutable gang of detectors that runs its members together.

    ``detect`` returns exactly the merge of running each member individually (the same
    result :func:`detect` would give). A gang is a value -- there is no mutable global
    registry; selection and grouping are expressed by composing gangs with
    :meth:`with_` / :meth:`without`.

    A member is identified by its type, its locale, and the locales it reads (see
    :func:`detector_key`), so an en_US and an en_GB detector of one type share a gang.
    """

    detectors: tuple[Detector, ...]

    def detect(self, text: str) -> list[ValueDetection]:
        return detect(text, self.detectors)

    def names(self) -> tuple[str, ...]:
        """The members' types, in order; a type repeats once per locale it is built for."""
        return tuple(d.type for d in self.detectors)

    def with_(self, *more: Detector) -> DetectorSet:
        """Return a new gang with ``more`` detectors added.

        A detector with the same key as a member (:func:`detector_key`) replaces it in
        place.
        """
        seen = {detector_key(d): d for d in self.detectors}
        for d in more:
            seen[detector_key(d)] = d
        return DetectorSet(tuple(seen.values()))

    def without(self, *types: str, locale: str | None = None) -> DetectorSet:
        """Return a new gang with the named detector types removed.

        Every locale's member of a type is removed, or only ``locale``'s when given.
        """
        drop = set(types)
        return DetectorSet(
            tuple(
                d
                for d in self.detectors
                if d.type not in drop
                or (locale is not None and getattr(d, "locale", None) != locale)
            )
        )


def detector_key(detector: Detector) -> tuple[str, str | None, tuple[str, ...] | None]:
    """A detector's identity in a gang: its type, locale, and chosen locales.

    ``locale`` and ``locales`` are read where a detector has them; a detector without a
    locale is identified by its type alone.
    """
    return (
        detector.type,
        getattr(detector, "locale", None),
        getattr(detector, "locales", None),
    )


# --------------------------------------------------------------------------- groups

# Pure constructors that assemble a common family of detectors into a gang. A group is
# just a DetectorSet -- compose or trim it with .with_/.without like any other.


def date_detectors(
    locale: str,
    skeletons: Iterable[str],
    *,
    flexible: bool = False,
    locales: Iterable[str] | None = None,
) -> DetectorSet:
    """A gang of date detectors for ``locale``, one per skeleton.

    ``skeletons`` are ICU date-time skeletons (``"yMd"``, ``"yMMMd"``); each becomes a
    :class:`DateDetector`. Members are deduplicated by type, so a repeated skeleton is
    harmless. A skeleton whose pattern carries an uninvertible field raises (see
    :class:`DateDetector`). When ``flexible`` is true, the gang additionally contains
    only a :class:`~icukit.recognize.FlexibleTextDateDetector`; it does not add the
    flexible numeric-date or other flexible date recognizers. ``locales`` chooses the
    other locales of the language that reader reads (every one by default).
    """
    members: list[Detector] = [DateDetector(locale, skeleton) for skeleton in skeletons]
    if flexible:
        from .recognize import FlexibleTextDateDetector

        members.append(FlexibleTextDateDetector(locale, locales=locales))
    return DetectorSet(()).with_(*members)


def number_detectors(
    locale: str,
    *,
    decimal: bool = True,
    percent: bool = True,
    currencies: Iterable[str] = (),
    flexible: bool = False,
) -> DetectorSet:
    """A gang of number detectors for ``locale``.

    ``decimal`` and ``percent`` add the plain decimal and percent detectors; each ISO code
    in ``currencies`` adds a currency detector (type ``number:currency:<ISO>``).
    When ``flexible`` is true, the gang additionally contains only a
    :class:`~icukit.recognize.FlexibleCurrencyNameDetector` for each requested currency;
    it does not add flexible decimal, percent, symbol-currency, compact, scientific,
    spellout, fraction, or ordinal recognizers.
    """
    members: list[Detector] = []
    if decimal:
        members.append(NumberDetector(locale, "decimal"))
    if percent:
        members.append(NumberDetector(locale, "percent"))
    members.extend(NumberDetector(locale, "currency", code) for code in currencies)
    if flexible:
        from .recognize import FlexibleCurrencyNameDetector

        members.extend(FlexibleCurrencyNameDetector(locale, code) for code in currencies)
    return DetectorSet(()).with_(*members)


def abbreviation_detectors(locale: str = "en") -> DetectorSet:
    """The lexicon-backed abbreviation detector, or an empty gang when unavailable."""
    from .abbreviation_recognize import abbreviation_detectors as build

    return build(locale)


def all_detectors(
    locale: str,
    skeletons: Iterable[str],
    *,
    currencies: Iterable[str] = (),
    flexible: bool = False,
    abbreviations: bool = False,
    locales: Iterable[str] | None = None,
) -> DetectorSet:
    """Date detectors for ``skeletons`` plus the decimal, percent, and currency detectors.

    A convenience composition of :func:`date_detectors` and :func:`number_detectors` for
    ``locale`` into one gang.
    """
    numbers = number_detectors(locale, currencies=currencies, flexible=flexible)
    gang = date_detectors(locale, skeletons, flexible=flexible, locales=locales).with_(
        *numbers.detectors
    )
    if abbreviations:
        gang = gang.with_(*abbreviation_detectors(locale).detectors)
    return gang
