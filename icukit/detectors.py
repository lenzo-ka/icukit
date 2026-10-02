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
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from dataclasses import field as dataclass_field
from decimal import Decimal
from threading import Lock
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

import icu

if TYPE_CHECKING:
    from .compiled import CompiledDetectorSet

from ._gate import (
    GATE_AUDIT,
    GATE_STATS,
    StartGate,
    _audit_probe,
    _candidate_starts_from_plan,
    _GatedReader,
    _grapheme_starts,
    _install_gates,
    _record,
    _scan_plan_for,
    _ScanPlan,
    _strict_gate,
    gates_enabled,
)
from ._offsets import boundary_maps, u16_boundary_to_codepoint
from .breaker import break_word_spans
from .detect import Detection

__all__ = [
    "ApproximateValue",
    "Capture",
    "CompactFormatSpec",
    "DateFormatSpec",
    "DateIntervalSpec",
    "DateIntervalValue",
    "DateDetector",
    "DateTimeValue",
    "Detector",
    "GatedDetector",
    "DetectorRefusal",
    "DetectorSet",
    "MeasureFormatSpec",
    "MeasureValue",
    "UnitValue",
    "NumberFormatSpec",
    "NumberDetector",
    "NumberRangeSpec",
    "NumberRangeValue",
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


@dataclass(frozen=True)
class NumberRangeValue:
    """A recovered (start, end) range of two amounts, as ICU's NumberRangeFormatter writes.

    Each endpoint is a :class:`NumberValue` (a number, a percent's ratio, or a currency
    amount) or a :class:`MeasureValue`. A side written without its unit ("$3–5",
    "10–15 kg", where ICU collapses the unit onto one side) carries the unit the other
    side writes, so both endpoints are whole amounts.
    """

    start: NumberValue | MeasureValue
    end: NumberValue | MeasureValue


@dataclass(frozen=True)
class ApproximateValue:
    """An amount written with an approximately sign ICU writes ("~3", "≈3", "約3")."""

    value: NumberValue | MeasureValue


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
class MaterialSpelloutFormatSpec(SpelloutFormatSpec):
    """A user-material spell-out recipe, identified by its content digest."""

    material_digest: str


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


@dataclass(frozen=True)
class NumberRangeSpec:
    """The locale and form of a number-range or approximately candidate.

    ``form`` is ``"range"`` (a separator ICU's ``NumberRangeFormatter`` writes) or
    ``"approximately"``. ``collapse`` is ``"unit"`` when one side's unit is shared with
    the other ("$3–5"), else ``"none"``; ``mark`` is the separator or the approximately
    sign as written, without the spaces around it.
    """

    locale: str
    form: str
    collapse: str
    mark: str


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


@runtime_checkable
class GatedDetector(Detector, Protocol):
    """A detector which declares a sound gate for each start-scanning lane."""

    def start_gates(self) -> Mapping[str, StartGate | None]: ...


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
    if letter == "G":
        # CLDR pattern grammar: one to three G write the abbreviated era, four the
        # wide, five the narrow.
        return {4: "wide", 5: "narrow"}.get(width, "short")
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


def _widen_years(pattern: str) -> str:
    """``pattern`` with each unquoted one-letter ``y`` widened to ``yyy``.

    CLDR pattern grammar, not locale data: ICU applies its two-digit-year window to a
    year field of one or two letters. ``yy`` is left alone, since it always writes two
    digits and the window is the only reading of them.
    """
    out: list[str] = []
    quoted = False
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "'":
            quoted = not quoted
            out.append(char)
            index += 1
            continue
        if quoted or char != "y":
            out.append(char)
            index += 1
            continue
        end = index
        while end < len(pattern) and pattern[end] == "y":
            end += 1
        out.append("yyy" if end - index == 1 else pattern[index:end])
        index = end
    return "".join(out)


def _date_fields(pattern: str) -> tuple[_DateField, ...]:
    # This is CLDR pattern grammar, not locale data. Calendar values and displayed names
    # are obtained from the formatter/calendar at runtime.
    mapping = {
        "G": ("G", icu.Calendar.ERA, icu.DateFormat.kEraField, True),
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
    order = {"G": -1, "y": 0, "M": 1, "d": 2, "weekday": 3, "H": 4, "h": 4, "m": 5, "s": 6}
    return tuple(sorted(found, key=lambda field: order[field.name]))


class DateDetector(_GatedReader):
    """Detect canonical ICU date surfaces for ``locale`` and ``skeleton``.

    The public ``tz`` parameter is deliberately restricted to ``"GMT"``: the current
    date specification fixes GMT so date-only parsing cannot acquire host-zone behavior.

    A year from a ``y`` field is read only in four or more digits when this locale's
    calendar writes its current year that way; a shorter one cannot be told from a
    count after a month ("June 200", "August 9", "3/4"). Calendars whose current era
    naturally has a short year, such as Japanese and ROC calendars, keep that canonical
    short year. A ``yy`` field keeps its two digits.

    An era field (``G``, any width) is read where the pattern writes it, in the locale's
    own calendar (the Buddhist era in ``th``, the Persian in ``fa``), as ICU formats it;
    it is captured as ``era`` and valued ``("G", era)``, ICU's era index, beside the year
    of that era ("Mar 15, 2024 BC" is ``(("G", 0), ("y", 2024), ...)``). The year
    beside an era keeps the four-digit floor only when ICU writes the current year of
    that locale's calendar in four or more digits: a short number before a short era is
    as often a count before a unit or a clock ("100 م" is 100 meters in Arabic, "5 م"
    five PM, "7 AD units").

    ``short_years=True`` builds the guarded reader of exactly the readings that floor
    refuses: a pattern with an era, read with a year of one to three digits ("Mar 15,
    44 BC" is ``(("G", 0), ("y", 44), ...)``, the year as written, never widened to a
    century). Its type is ``date:short-year:<skeleton>``, beside the text-date reader's
    ``date:short-year``, and a pattern without an era refuses it.
    """

    group = "date"

    def __init__(
        self, locale: str, skeleton: str, tz: str = "GMT", *, short_years: bool = False
    ) -> None:
        if tz != "GMT":
            raise ValueError("DateDetector currently requires tz='GMT'")
        self.locale = locale
        self.skeleton = skeleton
        self.tz = tz
        self.short_years = short_years
        self.type = f"date:short-year:{skeleton}" if short_years else f"date:{skeleton}"
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
        # 24-hour clock (H/k), dates, and the era (G) are fully modeled; the 12-hour
        # clock needs a day-period field whose value modeling is deferred, and
        # quarter/week/time-zone fields are out of scope. A day-period letter (a/b/B) is
        # exactly what makes "3:45 PM" non-invertible from bare (h, m).
        _modeled = {"G", "y", "M", "L", "d", "H", "k", "m", "s", "E", "e", "c"}
        _letters = {letter for letter, _ in _pattern_runs(self.pattern)}
        _unmodeled = sorted(_letters - _modeled)
        if _unmodeled:
            raise ValueError(
                f"DateDetector cannot invert pattern field(s) {_unmodeled} in {self.pattern!r} "
                f"(skeleton {skeleton!r}); 12-hour/day-period, quarter, week, and time-zone "
                f"fields are not supported"
            )
        self._has_era = "G" in _letters
        current = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
        year_position = icu.FieldPosition(icu.DateFormat.kYearField)
        current_surface = self._df.format(current.getTime(), year_position)
        _, current_u16_to_cp = boundary_maps(current_surface)
        current_year = current_surface[
            current_u16_to_cp[year_position.getBeginIndex()] : current_u16_to_cp[
                year_position.getEndIndex()
            ]
        ]
        self._year_floor = sum(icu.Char.isdigit(char) for char in current_year) >= 4
        if short_years and not (
            self._year_floor
            and self._has_era
            and any(f.letter == "y" and f.width != 2 for f in self._fields)
        ):
            raise ValueError(
                f"DateDetector reads a guarded short year only where ICU writes the "
                f"calendar's current 'y' year in at least four digits beside an era, and "
                f"{self.pattern!r} (skeleton {skeleton!r}) has no such field"
            )
        # ICU parses two digits in a one-letter year field into the century around
        # today ("44 BC" as 2044 BC), which is right where the year alone must be a
        # recent one, and wrong where an era dates it. A pattern with an era parses
        # through the same pattern with each "y" widened to "yyy", which ICU reads at
        # face value; the surface is still checked against the pattern itself. That
        # parser is also strict: a lenient one lets the era go missing, and then reads
        # on from a bare number through whatever follows it (ta's "G y-MM-dd, EEE"
        # takes "1,234.56 ச" as year 1 and a weekday), ending inside a grapheme, which
        # the scan must refuse. ICU writes every date it formats in a form it parses
        # strictly, so no canonical surface is lost.
        self._parser = self._df
        if self._has_era:
            self._parser = icu.SimpleDateFormat(_widen_years(self.pattern), icu.Locale(locale))
            self._parser.setTimeZone(icu.TimeZone.getGMT())
            self._parser.setLenient(False)
        # A weekday with no year ("Tue, 3/5") names a date in some year the text does not
        # give; ICU resolves a year-less parse in 1970, where 5 March is a Thursday.
        self._yearless_weekday = bool(_letters & {"E", "e", "c"}) and "y" not in _letters
        self._inv = _Inverter(self._parse, self._reformat, self._build)
        _install_gates(self, {"scan": _strict_gate(self)})

    def _parse(self, text: icu.UnicodeString, start_u16: int) -> tuple[int, object] | None:
        calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(self.locale))
        calendar.clear()
        if self._yearless_weekday:
            # A leap year, so "Sat, 2/29" keeps its day rather than rolling to 1 March.
            calendar.set(icu.Calendar.YEAR, 1972)
        position = icu.ParsePosition(start_u16)
        self._parser.parse(text, calendar, position)
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
            if (
                field.letter == "y"
                and field.width != 2
                and self._year_floor
                and (end_cp - begin_cp < 4) != (self.short_years)
            ):
                # ICU's "y" writes a year in as many digits as it has: four for every
                # year from 1000 on, and one to three below it ("June 200", "3/4"). The
                # reformat check cannot tell those from a count after a month ("in June
                # 200 cases", "August 9"), so a year under four digits is not read here,
                # a hand-rolled limit. It applies only where this formatter writes its
                # calendar's current year in four or more digits; calendars with a
                # naturally short current era year keep ICU's canonical output. "yy"
                # keeps its two digits, which ICU writes for every year. A short era can
                # follow a count or a clock as readily ("100 م" meters, "5 م" PM, "7 AD
                # units"), so the guarded reader gets exactly the short years refused by
                # an active floor, beside an era, and nothing else.
                return None
            captures.append(
                Capture(
                    "era" if field.name == "G" else field.name,
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
        return _scan(
            text,
            self.locale,
            self.type,
            self._inv,
            gate=self._start_gates["scan"],
            stats_key=self._lane_key("scan"),
        )


# --------------------------------------------------------------------------- numbers


class NumberDetector(_GatedReader):
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
        _install_gates(self, {"scan": _strict_gate(self)})

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
        return _scan(
            text,
            self.locale,
            self.type,
            self._inv,
            gate=self._start_gates["scan"],
            stats_key=self._lane_key("scan"),
        )


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
def _word_interior_offsets(
    text: str, locale: str, edges: frozenset[int] | None = None
) -> frozenset[int]:
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
    edges = sorted(_word_edges(text, locale) if edges is None else edges)
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


@dataclass(frozen=True)
class _ScanContext:
    ustr: object
    cp_to_u16: tuple[int, ...] | list[int]
    u16_to_cp: Mapping[int, int]
    boundaries: frozenset[int]
    interior: frozenset[int]


def _scan_context_from_plan(text: str, locale: str, plan: _ScanPlan | None) -> _ScanContext:
    if (
        plan is not None
        and plan.ustr is not None
        and locale in plan.grapheme_boundaries
        and locale in plan.word_interiors
    ):
        return _ScanContext(
            plan.ustr,
            plan.cp_to_u16,
            plan.u16_to_cp,
            plan.grapheme_boundaries[locale],
            plan.word_interiors[locale],
        )
    ustr = icu.UnicodeString(text)
    cp_to_u16, u16_to_cp = boundary_maps(text)
    boundaries = frozenset((*_grapheme_starts(text, locale), len(text)))
    return _ScanContext(
        ustr,
        cp_to_u16,
        u16_to_cp,
        boundaries,
        _word_interior_offsets(text, locale),
    )


def _scan_context(text: str, locale: str, gate: StartGate | None = None) -> _ScanContext:
    return _scan_context_from_plan(text, locale, _scan_plan_for(text, locale, gate))


def _scan_step(
    text: str,
    start_cp: int,
    locale: str,
    type_label: str,
    inv: _Inverter,
    ctx: _ScanContext,
) -> ValueDetection | None:
    """Run the strict matcher at one start, preserving every existing refusal."""
    del locale  # the context already embodies the locale's grapheme and word rules
    if start_cp in ctx.interior:
        return None
    result = inv.parse(ctx.ustr, ctx.cp_to_u16[start_cp])
    if result is None:
        return None
    end_u16, parsed = result
    if end_u16 < ctx.cp_to_u16[start_cp]:
        raise DetectorRefusal(
            type_label, start_cp, end_u16, "reversed-endpoint", "parse ended before its start"
        )
    if end_u16 == ctx.cp_to_u16[start_cp]:
        return None
    if end_u16 > ctx.cp_to_u16[-1]:
        raise DetectorRefusal(
            type_label,
            start_cp,
            end_u16,
            "out-of-range-endpoint",
            "parse ended beyond the end of the text",
        )
    end_cp = u16_boundary_to_codepoint(ctx.u16_to_cp, end_u16)
    if end_cp is None:
        raise DetectorRefusal(
            type_label,
            start_cp,
            end_u16,
            "surrogate-interior-endpoint",
            "parse ended inside a surrogate pair",
        )
    if end_cp not in ctx.boundaries:
        raise DetectorRefusal(
            type_label,
            start_cp,
            end_cp,
            "mid-grapheme-endpoint",
            "parse ended inside a grapheme cluster",
        )
    if end_cp in ctx.interior:
        return None
    surface = text[start_cp:end_cp]
    try:
        reformatted = inv.reformat(parsed)
    except icu.ICUError:
        return None
    if reformatted != surface:
        return None
    built = inv.build(parsed, surface, start_cp, ctx.cp_to_u16, ctx.u16_to_cp)
    if built is None:
        return None
    value, captures, spec = built
    if _contains_float(value) or _contains_float(spec) or _contains_float(captures):
        raise ValueError(
            f"{type_label}: build() produced a float in a record (values are "
            f"surface-derived, never a float) at [{start_cp}, {end_cp})"
        )
    return ValueDetection(
        text=surface,
        start=start_cp,
        end=end_cp,
        type=type_label,
        value=value,
        captures=captures,
        spec=spec,
    )


def _scan_outcome(
    text: str,
    start_cp: int,
    locale: str,
    type_label: str,
    inv: _Inverter,
) -> Literal["miss", "reading", "raise"]:
    """Classify the strict matcher outcome at one start for gate falsifiers."""
    try:
        result = _scan_step(text, start_cp, locale, type_label, inv, _scan_context(text, locale))
    except Exception:
        return "raise"
    return "reading" if result is not None else "miss"


def _scan(
    text: str,
    locale: str,
    type_label: str,
    inv: _Inverter,
    *,
    gate: StartGate | None = None,
    stats_key: str | None = None,
) -> list[ValueDetection]:
    """Windowed detection with reformat-equality acceptance and greedy longest-match.

    Scans grapheme-cluster starts left to right. A miss or no forward progress simply
    continues (never a refusal). A successful parse whose endpoint is reversed,
    surrogate-interior, or mid-grapheme is a :class:`DetectorRefusal`. An accepted span
    must reproduce the formatter's canonical output exactly (rejecting ICU's permissive
    coercions), and may neither start nor end inside a word between two alphanumerics
    (see :func:`_word_interior_offsets`). After a match ``[s, e)`` the scan resumes at
    ``e`` so one detector never self-overlaps.
    """
    plan = _scan_plan_for(text, locale, gate)
    ctx = _scan_context_from_plan(text, locale, plan)
    inspect_gate = GATE_STATS and gates_enabled() and gate is not None
    starts = (
        plan.grapheme_starts[locale]
        if inspect_gate and plan is not None
        else _grapheme_starts(text, locale)
        if inspect_gate
        else _candidate_starts_from_plan(text, locale, gate, plan)
    )
    out: list[ValueDetection] = []
    cursor = 0
    for start_cp in starts:
        if start_cp < cursor:
            continue  # greedy: inside a prior match
        if start_cp in ctx.interior:
            continue  # a fragment of a longer token
        if inspect_gate and not gate.admits(text[start_cp]):
            _record(stats_key, "gated_out")
            if GATE_AUDIT:
                _audit_probe(
                    stats_key,
                    lambda start=start_cp: _scan_step(text, start, locale, type_label, inv, ctx),
                )
            continue
        if GATE_STATS:
            _record(stats_key, "tried")
        try:
            detection = _scan_step(text, start_cp, locale, type_label, inv, ctx)
        except Exception:
            if GATE_STATS:
                _record(stats_key, "non_miss")
            raise
        if detection is None:
            continue
        if GATE_STATS:
            _record(stats_key, "non_miss")
        out.append(detection)
        cursor = detection["end"]
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

    A member is identified by its type, its reader class, its locale, the locales it
    reads, and any user-material content digest (see :func:`detector_key`), so an en_US
    and an en_GB detector of one type share a gang, as do a strict and a flexible reader
    of one type, while same-type readers from different materials coexist.
    """

    detectors: tuple[Detector, ...]
    _compiled: object | None = dataclass_field(
        default=None, init=False, repr=False, compare=False, hash=False
    )
    _compiled_reuse_recorded: bool = dataclass_field(
        default=False, init=False, repr=False, compare=False, hash=False
    )
    _compile_lock: Lock = dataclass_field(
        default_factory=Lock, init=False, repr=False, compare=False, hash=False
    )

    def detect(self, text: str) -> list[ValueDetection]:
        from .cache import cache_enabled

        if not cache_enabled():
            return detect(text, self.detectors)
        compiled = self._compiled
        if compiled is None:
            try:
                with self._compile_lock:
                    compiled = self._compiled
                    if compiled is None:
                        from .compiled import _implicit_compile

                        compiled = _implicit_compile(self)
                        object.__setattr__(self, "_compiled", compiled)
            except Exception:
                return detect(text, self.detectors)
        elif not self._compiled_reuse_recorded:
            from .cache import _record_compiled_reuse

            _record_compiled_reuse()
            object.__setattr__(self, "_compiled_reuse_recorded", True)
        return compiled.detect(text)  # type: ignore[union-attr]

    def compile(self, *, warm: bool = True) -> CompiledDetectorSet:
        """Compile this gang explicitly, optionally forcing lazy reader state."""
        from .compiled import compile_detectors

        return compile_detectors(self, warm=warm)

    def __getstate__(self):
        """Omit process-local compiled state and its lock from pickles and copies."""
        state = object.__getstate__(self)

        def without_compiled(attributes):
            if attributes is None:
                return None
            attributes = dict(attributes)
            attributes.pop("_compiled", None)
            attributes.pop("_compiled_reuse_recorded", None)
            attributes.pop("_compile_lock", None)
            return attributes

        if isinstance(state, tuple):
            attributes, slots = state
            return without_compiled(attributes), without_compiled(slots)
        return without_compiled(state)

    def __setstate__(self, state) -> None:
        if isinstance(state, tuple):
            attributes, slots = state
        else:
            attributes, slots = state, None
        if attributes is not None:
            vars(self).update(attributes)
        if slots is not None:
            for name, value in slots.items():
                object.__setattr__(self, name, value)
        object.__setattr__(self, "_compiled", None)
        object.__setattr__(self, "_compiled_reuse_recorded", False)
        object.__setattr__(self, "_compile_lock", Lock())

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


def detector_key(
    detector: Detector,
) -> tuple[str, str, str | None, tuple[str, ...] | None, str | None]:
    """A detector's identity: type, class, locale, read locales, and material digest.

    The locales are the ones the reader actually reads: a reader with no choice of
    locales reads its own locale alone, and a language-wide reader left at its default
    (``locales=None``) reads every ICU locale of the language, spelled out. So two
    readers share a key only when they are the same kind of reader reading the same
    locales -- a strict currency reader and a flexible one of the same type and locale
    are two members, not one replacing the other -- while a reader built twice, or once
    with ``locales=None`` and once with every locale named, is one member. The digest is
    ``None`` for ICU and curated readers; material readers carry their content digest so
    same-type readers from distinct materials coexist.
    """
    reader = type(detector)
    return (
        detector.type,
        f"{reader.__module__}.{reader.__qualname__}",
        getattr(detector, "locale", None),
        _read_locales(detector),
        getattr(detector, "material_digest", None),
    )


def _read_locales(detector: Detector) -> tuple[str, ...] | None:
    locale = getattr(detector, "locale", None)
    if locale is None:
        return None
    if not hasattr(detector, "locales"):
        return _own_locale(locale)
    chosen = detector.locales
    if chosen is None:
        return _every_locale_of_language(locale)
    if isinstance(chosen, str):
        chosen = (chosen,)
    # Named the way the default resolution names them (ICU's getName), so "en-GB" and
    # "en_gb" key as the "en_GB" that locales=None reads.
    return tuple(sorted({icu.Locale(str(name)).getName() for name in chosen}))


@functools.cache
def _own_locale(locale: str) -> tuple[str, ...]:
    return (icu.Locale(locale).getName(),)


@functools.cache
def _every_locale_of_language(locale: str) -> tuple[str, ...]:
    from .recognize import _language_locale_names

    base = icu.Locale(locale)
    return tuple(sorted({base.getName(), *_language_locale_names(base.getLanguage())}))


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
