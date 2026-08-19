"""Round-trip conformance inventory for ICU-backed value detectors."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Literal

import icu

from ._offsets import boundary_maps
from .detectors import (
    Capture,
    DateDetector,
    DateFormatSpec,
    DateTimeValue,
    DetectorRefusal,
    NumberDetector,
    NumberFormatSpec,
    NumberValue,
)

Profile = Literal["ci", "full"]

CI_MATRIX = {
    "locales": [
        {"id": "en_US", "currency": "USD"},
        {"id": "de_DE", "currency": "EUR"},
        {"id": "hi_IN", "currency": "INR"},
        {"id": "th_TH", "currency": "THB"},
        {"id": "fa_IR", "currency": "IRR"},
        {"id": "ru_RU", "currency": "RUB"},
    ],
    "date_skeletons": ["yMd", "yMMMd", "yMMMEd", "Hm"],
    "numbers": {
        "decimal": ["1234567.5", "-1234567.5"],
        "percent": ["0.07"],
        "currency": ["1234.5"],
    },
    "envelopes": [
        "bare",
        "embedded",
        "astral_prefix",
        "combining_prefix",
        "adjacent",
        "rtl_embedded",
    ],
}

# This copy is intentional: it is the single seam at which the exhaustive profile grows.
FULL_MATRIX = json.loads(json.dumps(CI_MATRIX))


@dataclass(frozen=True)
class Cell:
    locale: str
    category: str
    params: str
    value: str
    envelope: str
    currency: str | None = None

    @property
    def cell_id(self) -> str:
        raw = "--".join((self.locale, self.category, self.params, self.value, self.envelope))
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
        digest = hashlib.sha256(raw.encode()).hexdigest()[:10]
        return f"{slug}-{digest}"


@dataclass(frozen=True)
class Outcome:
    reason: str
    detail: str = ""
    surface: str = ""


def matrix(profile: Profile = "ci") -> dict:
    """Return the data definition for a conformance profile."""
    if profile == "ci":
        return CI_MATRIX
    if profile == "full":
        return FULL_MATRIX
    raise ValueError("profile must be 'ci' or 'full'")


def matrix_digest(profile: Profile = "ci") -> str:
    encoded = json.dumps(matrix(profile), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def iter_cells(profile: Profile = "ci") -> list[Cell]:
    definition = matrix(profile)
    cells: list[Cell] = []
    for locale_data in definition["locales"]:
        locale = locale_data["id"]
        envelopes = [e for e in definition["envelopes"] if e != "rtl_embedded"]
        if locale == "fa_IR":
            envelopes.append("rtl_embedded")
        for skeleton in definition["date_skeletons"]:
            value = "2026-01-03T15:45:00Z"
            cells.extend(Cell(locale, "date", skeleton, value, envelope) for envelope in envelopes)
        for kind, values in definition["numbers"].items():
            for value in values:
                currency = locale_data["currency"] if kind == "currency" else None
                cells.extend(
                    Cell(locale, "number", kind, value, envelope, currency)
                    for envelope in envelopes
                )
    return cells


def _date_instant() -> float:
    calendar = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale("en_US@calendar=gregorian")
    )
    calendar.clear()
    calendar.set(2026, 0, 3, 15, 45, 0)
    return calendar.getTime()


def _wrap(surface: str, envelope: str, locale: str) -> tuple[str, int, int] | None:
    if envelope == "bare":
        text, start = surface, 0
    elif envelope == "embedded":
        text, start = f"see {surface} here", 4
    elif envelope == "astral_prefix":
        text, start = f"\U0001f4c5 {surface}", 2
    elif envelope == "combining_prefix":
        # A base+combining grapheme ("e" + U+0301) then a space, before the surface: three
        # code points but one grapheme, so it probes offset handling across a combining
        # sequence without altering the surface (a suffix mark would instead merge into the
        # surface's own trailing grapheme and leave nothing to detect).
        text, start = f"e\u0301 {surface}", 3
    elif envelope == "adjacent":
        text, start = f"{surface}x", 0
    elif envelope == "rtl_embedded":
        text, start = f"\u200f{surface}\u200f", 1
    else:
        raise ValueError(f"unknown envelope: {envelope}")
    end = start + len(surface)
    return text, start, end


def _date_setup(cell: Cell):
    detector = DateDetector(cell.locale, cell.params)
    locale = icu.Locale(cell.locale)
    pattern = icu.DateTimePatternGenerator.createInstance(locale).getBestPattern(cell.params)
    formatter = icu.SimpleDateFormat(pattern, locale)
    formatter.setTimeZone(icu.TimeZone.getGMT())
    instant = _date_instant()
    surface = formatter.format(instant)
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), locale)
    calendar.setTime(instant)
    fields = []
    field_map = {
        "y": icu.Calendar.YEAR,
        "M": icu.Calendar.MONTH,
        "d": icu.Calendar.DATE,
        "H": icu.Calendar.HOUR_OF_DAY,
        "m": icu.Calendar.MINUTE,
    }
    runs = _pattern_runs(pattern)
    letter_names = {"y": "y", "M": "M", "L": "M", "d": "d", "H": "H", "m": "m"}
    order = {"y": 0, "M": 1, "d": 2, "H": 3, "m": 4}
    present = sorted(
        {letter_names[letter] for letter, _ in runs if letter in letter_names},
        key=order.__getitem__,
    )
    for name in present:
        raw = calendar.get(field_map[name])
        fields.append((name, raw + 1 if name == "M" else raw))
    form_names = {
        "y": "y",
        "M": "M",
        "L": "M",
        "d": "d",
        "H": "H",
        "m": "m",
        "E": "weekday",
        "e": "weekday",
        "c": "weekday",
    }
    forms = []
    for letter, width in runs:
        if letter in form_names:
            form = "numeric"
            if letter in {"M", "L", "E", "e", "c"} and width >= 3:
                form = {3: "short", 4: "wide"}.get(width, "narrow")
            forms.append((form_names[letter], form))
    forms.sort(key=lambda item: {"y": 0, "M": 1, "d": 2, "weekday": 3, "H": 4, "m": 5}[item[0]])
    expected = DateTimeValue(tuple(fields), calendar.getType())
    spec = DateFormatSpec(
        cell.locale,
        cell.params,
        pattern,
        calendar.getType(),
        "GMT",
        tuple(forms),
    )
    captures = _date_captures(formatter, instant, calendar, surface, runs)
    return detector, surface, expected, spec, captures


def _date_captures(formatter, instant, calendar, surface, runs) -> tuple[Capture, ...]:
    field_data = {
        "y": ("y", icu.Calendar.YEAR, icu.DateFormat.kYearField, True),
        "M": ("M", icu.Calendar.MONTH, icu.DateFormat.kMonthField, True),
        "L": ("M", icu.Calendar.MONTH, icu.DateFormat.kMonthField, True),
        "d": ("d", icu.Calendar.DATE, icu.DateFormat.kDateField, True),
        "H": ("H", icu.Calendar.HOUR_OF_DAY, icu.DateFormat.kHourOfDay0Field, True),
        "m": ("m", icu.Calendar.MINUTE, icu.DateFormat.kMinuteField, True),
        "E": ("weekday", icu.Calendar.DAY_OF_WEEK, icu.DateFormat.kDayOfWeekField, False),
        "e": ("weekday", icu.Calendar.DAY_OF_WEEK, icu.DateFormat.kDayOfWeekField, False),
        "c": ("weekday", icu.Calendar.DAY_OF_WEEK, icu.DateFormat.kDayOfWeekField, False),
    }
    _, u16_to_cp = boundary_maps(surface)
    captures = []
    for letter, width in runs:
        if letter not in field_data:
            continue
        name, calendar_field, format_field, value_field = field_data[letter]
        position = icu.FieldPosition(format_field)
        formatter.format(instant, position)
        if position.getBeginIndex() == position.getEndIndex():
            if not value_field:
                continue
            raise ValueError(f"ICU could not locate required date field {name!r}")
        begin = u16_to_cp[position.getBeginIndex()]
        end = u16_to_cp[position.getEndIndex()]
        value = calendar.get(calendar_field)
        if name == "M":
            value += 1
        elif name == "weekday":
            value = icu.DateFormatSymbols(icu.Locale("en")).getWeekdays()[value].lower()
        form = "numeric"
        if letter in {"M", "L", "E", "e", "c"} and width >= 3:
            form = {3: "short", 4: "wide"}.get(width, "narrow")
        captures.append(Capture(name, begin, end, surface[begin:end], value, form))
    captures.sort(key=lambda capture: (capture.start, capture.end))
    return tuple(captures)


def _pattern_runs(pattern: str) -> list[tuple[str, int]]:
    runs = []
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
        if quoted or not pattern[index].isalpha():
            index += 1
            continue
        end = index + 1
        while end < len(pattern) and pattern[end] == pattern[index]:
            end += 1
        runs.append((pattern[index], end - index))
        index = end
    return runs


def _number_setup(cell: Cell):
    locale = icu.Locale(cell.locale)
    if cell.params == "currency":
        formatter = icu.NumberFormat.createCurrencyInstance(locale)
        formatter.setCurrency(cell.currency)
    elif cell.params == "percent":
        formatter = icu.NumberFormat.createPercentInstance(locale)
    else:
        formatter = icu.NumberFormat.createInstance(locale)
    detector = NumberDetector(cell.locale, cell.params, cell.currency)
    # These deliberately small matrix values are exactly or safely represented for the
    # configured formatter precision; PyICU's legacy NumberFormat rejects Decimal.
    surface = formatter.format(float(cell.value))
    grouping = None
    if formatter.isGroupingUsed():
        primary = formatter.getGroupingSize()
        secondary = formatter.getSecondaryGroupingSize()
        grouping = (secondary, primary) if secondary else (primary,)
    currency = formatter.getCurrency() if cell.params == "currency" else None
    spec = NumberFormatSpec(
        cell.locale,
        cell.params,
        currency,
        formatter.getMinimumFractionDigits(),
        formatter.getMaximumFractionDigits(),
        grouping,
    )
    expected_decimal = cell.value
    if cell.params != "percent":
        expected_decimal = _quantized_string(
            cell.value, formatter.getMinimumFractionDigits(), formatter.getMaximumFractionDigits()
        )
    captures = _number_captures(formatter, surface, cell.params, float(cell.value))
    return detector, surface, NumberValue(expected_decimal, currency), spec, captures


def _quantized_string(value: str, minimum: int, maximum: int) -> str:
    quantum = Decimal(1).scaleb(-maximum)
    rendered = format(Decimal(value).quantize(quantum, rounding=ROUND_HALF_EVEN), "f")
    if "." not in rendered:
        return rendered
    whole, fraction = rendered.split(".")
    fraction = fraction.rstrip("0")
    if len(fraction) < minimum:
        fraction += "0" * (minimum - len(fraction))
    return f"{whole}.{fraction}" if fraction else whole


def _number_captures(formatter, surface: str, kind: str, value: float) -> tuple[Capture, ...]:
    symbols = formatter.getDecimalFormatSymbols()
    symbol_type = icu.DecimalFormatSymbols
    zero = symbols.getSymbol(symbol_type.kZeroDigitSymbol)
    _, u16_to_cp = boundary_maps(surface)

    def ascii_digits(value: str) -> str:
        return "".join(
            str(offset) for character in value if 0 <= (offset := ord(character) - ord(zero)) <= 9
        )

    captures = []
    integer_end = fraction_begin = None
    for name, field in (
        ("integer", icu.NumberFormat.kIntegerField),
        ("fraction", icu.NumberFormat.kFractionField),
    ):
        position = icu.FieldPosition(field)
        formatter.format(value, position)
        if position.getEndIndex() > position.getBeginIndex():
            begin = u16_to_cp[position.getBeginIndex()]
            end = u16_to_cp[position.getEndIndex()]
            text = surface[begin:end]
            captures.append(Capture(name, begin, end, text, ascii_digits(text), "numeric"))
            if name == "integer":
                integer_end = end
            elif name == "fraction":
                fraction_begin = begin
    # The decimal separator is part of the coarse capture set (§12.2); it sits between the
    # integer and fraction fields, exactly where the detector locates it.
    if integer_end is not None and fraction_begin is not None:
        separator = symbols.getSymbol(symbol_type.kDecimalSeparatorSymbol)
        found = surface.find(separator, integer_end, fraction_begin)
        if found >= 0:
            end = found + len(separator)
            captures.append(Capture("decimal-separator", found, end, separator, None, "symbol"))
    symbol_names = []
    minus = symbols.getSymbol(symbol_type.kMinusSignSymbol)
    plus = symbols.getSymbol(symbol_type.kPlusSignSymbol)
    if minus in surface:
        symbol_names.append(("sign", minus))
    elif plus in surface:
        symbol_names.append(("sign", plus))
    if kind == "currency":
        symbol_names.append(("currency", symbols.getSymbol(symbol_type.kCurrencySymbol)))
    elif kind == "percent":
        symbol_names.append(("percent", symbols.getSymbol(symbol_type.kPercentSymbol)))
    for name, symbol in symbol_names:
        begin = surface.find(symbol)
        if begin >= 0:
            captures.append(Capture(name, begin, begin + len(symbol), symbol, None, "symbol"))
    captures.sort(key=lambda capture: (capture.start, capture.end))
    return tuple(captures)


def compare_expected(
    detection,
    text: str,
    expected_value: DateTimeValue | NumberValue,
    expected_captures: tuple[Capture, ...],
    expected_spec: DateFormatSpec | NumberFormatSpec,
    surface: str,
) -> Outcome:
    """Compare a detection with a complete independently constructed oracle record."""
    actual_value = detection["value"]
    if actual_value != expected_value:
        return Outcome(
            "value-mismatch", f"expected {expected_value!r}; got {actual_value!r}", surface
        )
    actual_captures = detection["captures"]
    actual_names = [capture.name for capture in actual_captures]
    expected_names = [capture.name for capture in expected_captures]
    if len(actual_names) != len(set(actual_names)) or set(actual_names) != set(expected_names):
        return Outcome(
            "capture-mismatch",
            f"expected capture names {expected_names!r}; got {actual_names!r}",
            surface,
        )
    expected_by_name = {capture.name: capture for capture in expected_captures}
    for actual in actual_captures:
        expected = expected_by_name[actual.name]
        if actual != expected:
            return Outcome(
                "capture-mismatch",
                f"capture {actual.name!r}: expected {expected!r}; got {actual!r}",
                surface,
            )
        if text[actual.start : actual.end] != actual.text:
            return Outcome(
                "capture-mismatch",
                f"capture {actual.name!r} text does not match its source span",
                surface,
            )
    actual_spec = detection["spec"]
    if actual_spec != expected_spec:
        return Outcome(
            "spec-mismatch",
            f"expected {expected_spec!r}; got {actual_spec!r}",
            surface,
        )
    return Outcome("recovered", surface=surface)


def classify(cell: Cell) -> Outcome:
    """Format, detect, and classify one matrix cell."""
    try:
        detector, surface, expected, expected_spec, local_captures = (
            _date_setup(cell) if cell.category == "date" else _number_setup(cell)
        )
        wrapped = _wrap(surface, cell.envelope, cell.locale)
        if wrapped is None:
            return Outcome(
                "unsupported", "envelope merges the surface's trailing grapheme", surface
            )
        text, start, end = wrapped
        expected_captures = tuple(
            replace(capture, start=capture.start + start, end=capture.end + start)
            for capture in local_captures
        )
        try:
            detections = detector.detect(text)
        except DetectorRefusal as error:
            return Outcome("refused", str(error), surface)
    except (ValueError, icu.ICUError) as error:
        return Outcome("unsupported", str(error))
    matches = [
        detection
        for detection in detections
        if (detection["start"], detection["end"]) == (start, end)
        and detection["type"] == detector.type
    ]
    if not matches:
        return Outcome("not-detected", "no matching type at the expected span", surface)
    return compare_expected(matches[0], text, expected, expected_captures, expected_spec, surface)


def _record(cell: Cell, outcome: Outcome) -> dict:
    record = {
        "cell_id": cell.cell_id,
        "locale": cell.locale,
        "category": cell.category,
        "params": f"{cell.params}:{cell.currency}" if cell.currency else cell.params,
        "value": cell.value,
        "envelope": cell.envelope,
        "surface": outcome.surface,
        "reason": outcome.reason,
    }
    if outcome.detail:
        record["detail"] = outcome.detail
    return record


def build_inventory(profile: Profile = "ci") -> dict:
    """Build the stable, JSON-compatible defect inventory for ``profile``."""
    defects = []
    unsupported = []
    for cell in iter_cells(profile):
        outcome = classify(cell)
        if outcome.reason == "unsupported":
            unsupported.append(_record(cell, outcome))
        elif outcome.reason != "recovered":
            defects.append(_record(cell, outcome))
    defects.sort(key=lambda record: record["cell_id"])
    unsupported.sort(key=lambda record: record["cell_id"])
    return {
        "icu_version": icu.ICU_VERSION,
        "unicode_version": icu.UNICODE_VERSION,
        "matrix_digest": matrix_digest(profile),
        "defects": defects,
        "unsupported_cells": unsupported,
    }


def canonical_json(value: dict) -> str:
    """Serialize an inventory in its committed canonical representation."""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
