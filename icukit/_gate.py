"""Sound start gates for detector scans.

A start gate is an over-approximation: it may admit starts which miss, but it must
never reject a start where the matcher reads or raises.  Gates are deliberately
small values so compiled detector sets can share their filtered start tuples.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import icu

from ._offsets import boundary_maps
from .breaker import break_grapheme_spans

__all__ = [
    "GATE_TESTS",
    "GATES_DEFAULT",
    "LaneGate",
    "StartGate",
    "candidate_starts",
    "folded_heads",
    "gate_report",
    "gates_enabled",
    "heads",
    "lane_stats",
    "reset_lane_stats",
    "ungated",
]


def _has_property(char: str, prop: int) -> bool:
    return bool(icu.Char.hasBinaryProperty(char, prop))


GATE_TESTS: Mapping[str, Callable[[str], bool]] = {
    "icu.isdigit": icu.Char.isdigit,
    "icu.not_isalpha": lambda char: not icu.Char.isalpha(char),
    "white_space": lambda char: _has_property(char, icu.UProperty.WHITE_SPACE),
    "default_ignorable": lambda char: _has_property(
        char, icu.UProperty.DEFAULT_IGNORABLE_CODE_POINT
    ),
}


@dataclass(frozen=True)
class StartGate:
    """A superset of starts where a lane can read or raise."""

    chars: frozenset[str] = frozenset()
    folded: frozenset[str] = frozenset()
    tests: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        unknown = self.tests - GATE_TESTS.keys()
        if unknown:
            raise ValueError(f"unknown start-gate tests: {sorted(unknown)!r}")

    def admits(self, char: str) -> bool:
        if char in self.chars:
            return True
        folded = char.casefold()
        if folded and folded[0] in self.folded:
            return True
        return any(GATE_TESTS[name](char) for name in self.tests)

    def __or__(self, other: StartGate | None) -> StartGate | None:
        """Union two gates; an ungated member makes the whole lane ungated."""
        if other is None:
            return None
        if not isinstance(other, StartGate):
            return NotImplemented
        return StartGate(
            self.chars | other.chars,
            self.folded | other.folded,
            self.tests | other.tests,
        )


def heads(surfaces: Iterable[str]) -> frozenset[str]:
    """Return the nonempty surfaces' first code points."""
    return frozenset(surface[0] for surface in surfaces if surface)


def folded_heads(surfaces: Iterable[str]) -> frozenset[str]:
    """Return the first code point after Python case folding each surface."""
    result = set()
    for surface in surfaces:
        folded = surface.casefold()
        if folded:
            result.add(folded[0])
    return frozenset(result)


GATES_DEFAULT = os.environ.get("ICUKIT_GATES") != "0"
GATE_AUDIT = os.environ.get("ICUKIT_GATE_AUDIT") == "1"
GATE_STATS = os.environ.get("ICUKIT_GATE_STATS") == "1" or GATE_AUDIT
_GATES_OVERRIDE: ContextVar[bool | None] = ContextVar("icukit_gates_override", default=None)


def gates_enabled() -> bool:
    """Whether gates are enabled in this context."""
    override = _GATES_OVERRIDE.get()
    return GATES_DEFAULT if override is None else override


@contextmanager
def ungated():
    """Disable start gates in this context for the duration of the block."""
    token = _GATES_OVERRIDE.set(False)
    try:
        yield
    finally:
        _GATES_OVERRIDE.reset(token)


@dataclass(frozen=True)
class _ScanPlan:
    """The L2-visible part of a compiled scan plan.

    L3 populates these maps.  They are immutable by contract: readers may inspect but
    never mutate the shared tuples or maps.
    """

    text: str
    grapheme_starts: Mapping[str, tuple[int, ...]]
    gated_starts: Mapping[StartGate, Mapping[str, tuple[int, ...]]]


_SCAN_PLAN: ContextVar[_ScanPlan | None] = ContextVar("icukit_scan_plan", default=None)


@lru_cache(maxsize=256)
def _cached_candidate_starts(text: str, locale: str, gate: StartGate) -> tuple[int, ...]:
    return tuple(start for start in _grapheme_starts(text, locale) if gate.admits(text[start]))


@lru_cache(maxsize=16)
def _grapheme_starts(text: str, locale: str) -> tuple[int, ...]:
    return tuple(sorted({span["start"] for span in break_grapheme_spans(text, locale)}))


def _candidate_starts(text: str, locale: str, gate: StartGate | None) -> tuple[int, ...]:
    """Return candidate grapheme starts, consulting a compatible scan plan when present."""
    # This check deliberately precedes both the plan and the gated cache.  An ungated
    # call can therefore never be served a tuple computed while gates were enabled.
    if not gates_enabled() or gate is None:
        return _grapheme_starts(text, locale)
    plan = _SCAN_PLAN.get()
    if plan is not None and plan.text is text:
        locale_map = plan.gated_starts.get(gate)
        if locale_map is not None and locale in locale_map:
            return locale_map[locale]
    return _cached_candidate_starts(text, locale, gate)


def candidate_starts(text: str, locale: str, gate: StartGate | None) -> tuple[int, ...]:
    """Return grapheme starts admitted by ``gate`` in the current gate context."""
    return _candidate_starts(text, locale, gate)


_COUNTER_NAMES = ("tried", "gated_out", "non_miss", "audit_probed", "audit_violations")
_STATS: dict[str, dict[str, int]] = {}
_STATS_LOCK = threading.Lock()


def _record(lane: str | None, counter: str, amount: int = 1) -> None:
    if not GATE_STATS or lane is None:
        return
    with _STATS_LOCK:
        counters = _STATS.setdefault(lane, dict.fromkeys(_COUNTER_NAMES, 0))
        counters[counter] += amount


def lane_stats() -> dict[str, dict[str, int]]:
    """Return a detached snapshot of per-lane gate counters."""
    with _STATS_LOCK:
        return {lane: dict(counters) for lane, counters in _STATS.items()}


def reset_lane_stats() -> None:
    """Clear all per-lane gate counters."""
    with _STATS_LOCK:
        _STATS.clear()


def _audit_probe(lane: str | None, probe: Callable[[], Any]) -> bool:
    """Run one pruned matcher start; return whether it read or raised."""
    _record(lane, "audit_probed")
    try:
        outcome = probe()
    except Exception:  # every matcher raise is a gate violation, but is never propagated
        _record(lane, "audit_violations")
        return True
    non_miss = bool(outcome)
    if non_miss:
        _record(lane, "audit_violations")
    return non_miss


def _canary_gate(reader: object, lane: str, gate: StartGate | None) -> StartGate | None:
    """Apply the import-time gate canary, if it names this reader and lane."""
    if gate is None:
        return None
    value = os.environ.get("ICUKIT_GATE_CANARY")
    if not value:
        return gate
    parts = value.split(":", 3)
    if len(parts) != 4:
        return gate
    reader_class, currency, named_lane, char = parts
    if (
        type(reader).__name__ != reader_class
        or str(getattr(reader, "currency", "")) != currency
        or lane != named_lane
    ):
        return gate
    folded = char.casefold()[:1]
    return StartGate(
        chars=gate.chars - {char},
        folded=gate.folded - ({folded} if folded else set()),
        tests=gate.tests,
    )


def _install_gates(
    reader: object,
    gates: Mapping[str, StartGate | None],
    reasons: Mapping[str, str] | None = None,
) -> None:
    installed = {lane: _canary_gate(reader, lane, gate) for lane, gate in gates.items()}
    reader._start_gates = installed  # type: ignore[attr-defined]
    reader._gate_reasons = dict(reasons or {})  # type: ignore[attr-defined]


class _GatedReader:
    """Internal implementation of the public :class:`GatedDetector` protocol."""

    _start_gates: Mapping[str, StartGate | None]

    def start_gates(self) -> Mapping[str, StartGate | None]:
        """Return this reader's stable lane names and sound start gates."""
        return self._start_gates

    def _lane_key(self, lane: str) -> str:
        return (
            f"{type(self).__name__}|{getattr(self, 'locale', '')}|"
            f"{getattr(self, 'type', '')}|{lane}"
        )


@dataclass(frozen=True)
class LaneGate:
    """One reader lane's gate status and derivation reason."""

    detector_key: tuple
    lane: str
    gated: bool
    reason: str


def gate_report(detectors: Iterable[object] | object) -> tuple[LaneGate, ...]:
    """Describe every declared start-scanning lane in ``detectors``."""
    from .detectors import DetectorSet, detector_key

    if isinstance(detectors, DetectorSet):
        members = detectors.detectors
    elif callable(getattr(detectors, "start_gates", None)) or callable(
        getattr(detectors, "detect", None)
    ):
        try:
            iter(detectors)
        except TypeError:
            members = (detectors,)
        else:
            members = detectors
    else:
        members = detectors
    report = []
    for detector in members:
        method = getattr(detector, "start_gates", None)
        if not callable(method):
            continue
        reasons = getattr(detector, "_gate_reasons", {})
        for lane, gate in method().items():
            reason = reasons.get(lane)
            if reason is None:
                reason = (
                    "derived from the reader tables used by this lane" if gate else "no derivation"
                )
            report.append(LaneGate(detector_key(detector), lane, gate is not None, reason))
    return tuple(report)


# Strict-lane source enumeration -------------------------------------------------


def _nonempty(values: Iterable[Any]) -> set[str]:
    return {str(value) for value in values if str(value)}


@lru_cache(maxsize=64)
def _date_symbol_strings(locale: str) -> tuple[str, ...]:
    symbols = icu.DateFormatSymbols(icu.Locale(locale))
    found: set[str] = set()
    for context in (symbols.FORMAT, symbols.STANDALONE):
        for width in (symbols.WIDE, symbols.ABBREVIATED, symbols.NARROW):
            for name in ("getMonths", "getWeekdays"):
                try:
                    found.update(_nonempty(getattr(symbols, name)(context, width)))
                except (icu.ICUError, TypeError):
                    pass
    for name in (
        "getMonths",
        "getShortMonths",
        "getWeekdays",
        "getShortWeekdays",
        "getEras",
        "getEraNames",
        "getAmPmStrings",
    ):
        try:
            found.update(_nonempty(getattr(symbols, name)()))
        except icu.ICUError:
            pass
    found.update(_date_name_resource_strings(locale))
    return tuple(sorted(found))


def _all_resource_strings(node: Any) -> set[str]:
    if node.getType() == icu.UResType.STRING:
        value = node.getString()
        return {str(value)} if value else set()
    found = set()
    for index in range(node.getSize()):
        try:
            found.update(_all_resource_strings(node.get(index)))
        except icu.ICUError:
            pass
    return found


@lru_cache(maxsize=64)
def _date_name_resource_strings(locale: str) -> tuple[str, ...]:
    """Fill PyICU's missing SHORT/context accessors from ICU resources."""
    calendar = str(icu.Calendar.createInstance(icu.Locale(locale)).getType())
    root = icu.ResourceBundle("", icu.Locale(locale)).get("calendar")
    calendars = (calendar, "gregorian") if calendar != "gregorian" else (calendar,)
    found = set()
    for calendar_name in calendars:
        try:
            calendar_node = root.getWithFallback(calendar_name)
        except icu.ICUError:
            continue
        for category in ("monthNames", "dayNames"):
            try:
                names = calendar_node.getWithFallback(category)
            except icu.ICUError:
                continue
            for context in ("format", "stand-alone"):
                for width in ("wide", "abbreviated", "narrow", "short"):
                    candidates = (
                        (context, width),
                        (context, "abbreviated"),
                        (context, "wide"),
                        ("format" if context == "stand-alone" else "stand-alone", width),
                    )
                    for candidate_context, candidate_width in dict.fromkeys(candidates):
                        try:
                            table = names.getWithFallback(candidate_context).getWithFallback(
                                candidate_width
                            )
                        except icu.ICUError:
                            continue
                        found.update(_all_resource_strings(table))
                        break
        if found:
            break
    return tuple(sorted(found))


def _resource_values(table: Any) -> set[str]:
    found = set()
    for index in range(table.getSize()):
        item = table.get(index)
        if item.getType() == icu.UResType.STRING and item.getString():
            found.add(str(item.getString()))
    return found


def _resource_descendant_strings(locale: str, keys: tuple[str, ...]) -> set[str]:
    try:
        node = icu.ResourceBundle("", icu.Locale(locale))
        for key in keys:
            node = node.getWithFallback(key)
    except icu.ICUError:
        return set()
    found = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if current.getType() == icu.UResType.STRING:
            value = current.getString()
            if value:
                found.add(str(value))
            continue
        for index in range(current.getSize()):
            try:
                stack.append(current.get(index))
            except icu.ICUError:
                pass
    return found


@lru_cache(maxsize=64)
def _day_period_strings(locale: str) -> tuple[str, ...]:
    found: set[str] = set()
    loc = icu.Locale(locale)
    calendar = str(icu.Calendar.createInstance(loc).getType())
    calendars = (calendar, "gregorian") if calendar != "gregorian" else (calendar,)
    root = icu.ResourceBundle("", loc).get("calendar")
    day_period = None
    for name in calendars:
        try:
            day_period = root.getWithFallback(name).getWithFallback("dayPeriod")
            break
        except icu.ICUError:
            pass
    if day_period is not None:
        for context in ("format", "stand-alone"):
            for width in ("wide", "abbreviated", "narrow"):
                candidates = (
                    (context, width),
                    (context, "abbreviated"),
                    (context, "wide"),
                    ("format" if context == "stand-alone" else "stand-alone", width),
                    ("format", "abbreviated"),
                    ("format", "wide"),
                )
                for candidate_context, candidate_width in dict.fromkeys(candidates):
                    try:
                        table = day_period.getWithFallback(candidate_context).getWithFallback(
                            candidate_width
                        )
                        found.update(_resource_values(table))
                        break
                    except icu.ICUError:
                        pass
    for pattern in ("B", "BBBB", "BBBBB", "b", "bbbb", "bbbbb", "a", "aaaa", "aaaaa"):
        formatter = icu.SimpleDateFormat(pattern, loc)
        formatter.setTimeZone(icu.TimeZone.getGMT())
        for hour in range(24):
            for minute in (0, 30):
                value = str(formatter.format(_calendar(locale, 2020, 0, 2, hour, minute).getTime()))
                if value:
                    found.add(value)
    return tuple(sorted(found))


def _calendar(
    locale: str, year: int, month: int, day: int, hour: int = 13, minute: int = 27
) -> Any:
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
    calendar.clear()
    calendar.set(year, month, day, hour, minute, 41)
    return calendar


@lru_cache(maxsize=64)
def _era_year_one_instants(locale: str) -> tuple[float, ...]:
    """Return one valid instant in year one of every exposed calendar era."""
    probe = _calendar(locale, 2020, 0, 2)
    found = []
    for era in range(probe.getMinimum(icu.Calendar.ERA), probe.getMaximum(icu.Calendar.ERA) + 1):
        selected = None
        for month in range(13):
            for day in range(1, 32):
                calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
                calendar.clear()
                calendar.set(icu.Calendar.ERA, era)
                calendar.set(icu.Calendar.YEAR, 1)
                calendar.set(icu.Calendar.MONTH, month)
                calendar.set(icu.Calendar.DATE, day)
                calendar.set(icu.Calendar.HOUR_OF_DAY, 13)
                try:
                    calendar.getTime()
                    if (
                        calendar.get(icu.Calendar.ERA) == era
                        and calendar.get(icu.Calendar.YEAR) == 1
                    ):
                        selected = calendar
                        break
                except icu.ICUError:
                    pass
            if selected is not None:
                break
        if selected is not None:
            found.append(selected.getTime())
    return tuple(found)


def _pattern_runs(pattern: str) -> tuple[tuple[str, int], ...]:
    runs = []
    quoted = False
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "'":
            if index + 1 < len(pattern) and pattern[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
            index += 1
            continue
        if quoted or not (char.isascii() and char.isalpha()):
            index += 1
            continue
        end = index + 1
        while end < len(pattern) and pattern[end] == char:
            end += 1
        runs.append((char, end - index))
        index = end
    return tuple(runs)


def _format_field(locale: str, letter: str, width: int, calendars: Iterable[Any]) -> set[str]:
    formatter = icu.SimpleDateFormat(letter * width, icu.Locale(locale))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    found = set()
    for calendar in calendars:
        try:
            instant = calendar.getTime() if hasattr(calendar, "getTime") else calendar
            value = str(formatter.format(instant))
        except icu.ICUError:
            continue
        if value:
            found.add(value)
    return found


def _format_pattern_field_outputs(locale: str, pattern: str, calendars: Iterable[Any]) -> set[str]:
    """Extract field spans from the full pattern, preserving numbering overrides."""
    from .detectors import _pattern_field_id

    formatter = icu.SimpleDateFormat(pattern, icu.Locale(locale))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    field_ids = {_pattern_field_id(letter) for letter, _width in _pattern_runs(pattern)}
    found = set()
    for calendar in calendars:
        instant = calendar.getTime() if hasattr(calendar, "getTime") else calendar
        for field_id in field_ids:
            position = icu.FieldPosition(field_id)
            rendered = str(formatter.format(instant, position))
            if position.getBeginIndex() == position.getEndIndex():
                continue
            _, u16_to_cp = boundary_maps(rendered)
            value = rendered[
                u16_to_cp[position.getBeginIndex()] : u16_to_cp[position.getEndIndex()]
            ]
            if value:
                found.add(value)
    return found


@lru_cache(maxsize=256)
def _formatted_field_strings(locale: str, pattern: str) -> tuple[str, ...]:
    """Enumerate every field output over P4's required domains."""
    runs = set(_pattern_runs(pattern)) | {("U", 1), ("y", 1), ("d", 1), ("M", 1)}
    found: set[str] = set()
    ordinary = [
        _calendar(locale, 2020, month, day) for month in range(12) for day in (1, 2, 15, 28)
    ]
    ordinary += [
        _calendar(locale, 2020, 0, 2, hour, minute) for hour in range(24) for minute in (0, 30)
    ]
    era_year_one = _era_year_one_instants(locale)
    full_pattern_domain = list(ordinary)
    full_pattern_domain.extend(era_year_one)
    for letter, width in runs:
        calendars = list(ordinary)
        if letter == "U":
            calendars = [_calendar(locale, year, 0, 2) for year in range(1, 61)]
        elif letter == "d":
            calendars = [_calendar(locale, 2020, 0, day) for day in range(1, 32)]
        elif letter in {"M", "L"}:
            calendars = []
            for month in range(13):
                calendar = _calendar(locale, 2020, month, 2)
                calendars.append(calendar)
                leap_field = getattr(icu.Calendar, "IS_LEAP_MONTH", None)
                if leap_field is not None:
                    leap = _calendar(locale, 2020, month, 2)
                    leap.set(leap_field, 1)
                    calendars.append(leap)
        elif letter in {"y", "Y", "u", "r"}:
            calendars = list(era_year_one)
        found.update(_format_field(locale, letter, width, calendars))
        full_pattern_domain.extend(calendars)
    found.update(_format_pattern_field_outputs(locale, pattern, full_pattern_domain))

    calendar = str(icu.Calendar.createInstance(icu.Locale(locale)).getType())
    month_patterns = _resource_descendant_strings(locale, ("calendar", calendar, "monthPatterns"))
    month_names = _resource_descendant_strings(locale, ("calendar", calendar, "monthNames"))
    for template in month_patterns:
        if "{0}" in template:
            found.update(template.replace("{0}", name) for name in month_names)
        elif template:
            found.add(template)
    for key in ("cyclicNameSets", "zodiacNames"):
        found.update(_resource_descendant_strings(locale, ("calendar", calendar, key)))
        if calendar != "gregorian":
            found.update(_resource_descendant_strings(locale, ("calendar", "gregorian", key)))
    return tuple(sorted(found))


@lru_cache(maxsize=64)
def _decimal_symbol_strings(locale: str) -> tuple[str, ...]:
    symbols = icu.DecimalFormatSymbols(icu.Locale(locale))
    return tuple(
        str(symbols.getSymbol(symbol))
        for symbol in (
            icu.DecimalFormatSymbols.kNaNSymbol,
            icu.DecimalFormatSymbols.kInfinitySymbol,
            icu.DecimalFormatSymbols.kExponentialSymbol,
        )
        if symbols.getSymbol(symbol)
    )


def _strict_gate(reader: object) -> StartGate | None:
    """Build a strict complement gate from the same ICU tables as ``reader``."""
    locale = str(reader.locale)
    strings = set(_date_symbol_strings(locale))
    strings.update(_day_period_strings(locale))
    pattern = getattr(reader, "pattern", None)
    if pattern:
        strings.update(_formatted_field_strings(locale, str(pattern)))
    strings.update(_decimal_symbol_strings(locale))
    number_format = getattr(reader, "_nf", None)
    if number_format is not None:
        for value in (-1234567.25, -1234.5, -0.0, 0, 0.5, 12, 250000):
            strings.add(str(number_format.format(value)))
        if getattr(reader, "kind", None) == "currency":
            base = icu.NumberFormatter.withLocale(icu.Locale(locale)).unit(
                icu.CurrencyUnit(reader.currency)
            )
            for sign in (icu.UNumberSignDisplay.AUTO, icu.UNumberSignDisplay.ACCOUNTING):
                formatter = base.sign(sign)
                for value in (-1234.5, -0.0, 0, 0.5, 12):
                    strings.add(str(formatter.formatDouble(value)))
    mismatches = [
        value
        for value in strings
        if value.casefold()[:1] != str(icu.UnicodeString(value).foldCase())[:1]
    ]
    alphabetic = [value for value in strings if value and icu.Char.isalpha(value[0])]
    folded = set(folded_heads(alphabetic))
    # StartGate admits input through Python casefold, but ICU's parser follows ICU's
    # newer tables.  Adding ICU's head for a mismatching source keeps both spellings.
    folded.update(str(icu.UnicodeString(value).foldCase())[:1] for value in mismatches if value)
    return StartGate(
        folded=frozenset(folded),
        tests=frozenset({"icu.not_isalpha"}),
    )
