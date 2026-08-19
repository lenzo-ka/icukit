"""D1 detectors: invert ICU formatters to find typed values in running text.

A *detector* here wraps the invertible class -- the value kinds where an ICU parser
inverts the formatter (dates, times, datetimes, decimal numbers, currency, percent).
Each accepted match is a :class:`ValueDetection` that carries the full generative
structure of the parse::

    surface  <->  (spec, value, captures)

governed by the invariant ``reformat(spec, value) == surface`` -- which is also the
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

from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass
from typing import Literal, Protocol, runtime_checkable

import icu

from ._offsets import boundary_maps, u16_boundary_to_codepoint
from .breaker import break_grapheme_spans
from .detect import Detection

__all__ = [
    "Capture",
    "DateFormatSpec",
    "DateTimeValue",
    "Detector",
    "DetectorRefusal",
    "DetectorSet",
    "NumberFormatSpec",
    "NumberValue",
    "ValueDetection",
    "detect",
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
class NumberValue:
    """A numeric value recovered as a canonical decimal string.

    ``decimal`` is derived from the accepted surface (locale digits and separators
    normalized to ASCII), never from a binary ``float``. For a percent it is the ratio
    (``"7%"`` -> ``"0.07"``); for a currency, ``currency`` carries the ISO 4217 code.
    """

    decimal: str
    currency: str | None = None


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
class NumberFormatSpec:
    """The generative recipe for a numeric detection.

    ``grouping_sizes`` are Known from the formatter (e.g. ``(3,)`` for en_US,
    ``(2, 3)`` for hi_IN Indian grouping), not read off one value; ``None`` when the
    formatter groups by no fixed size. ``min_fraction``/``max_fraction`` are the
    formatter's configured fraction-digit bounds.
    """

    locale: str
    kind: Literal["decimal", "currency", "percent"]
    currency: str | None = None
    min_fraction: int | None = None
    max_fraction: int | None = None
    grouping_sizes: tuple[int, ...] | None = None


# --------------------------------------------------------------------------- detection


class ValueDetection(Detection):
    """A D1 detection: a :class:`~icukit.detect.Detection` plus its generative structure.

    Inherits ``text``/``start``/``end``/``type`` (code-point offsets) and adds ``value``,
    ``captures``, and ``spec`` (see the module docstring). The invariant
    ``reformat(spec, value) == surface`` holds for every accepted detection.
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
    """A runnable D1 detector.

    ``type`` is the stable label carried on its detections (``date:yMMMd``,
    ``number:currency:USD``); ``group`` is its coarse family (``date``, ``number``) and
    equals the ``type`` prefix. ``detect`` scans the whole text and returns its
    detections in source order -- unanchored, partial, tolerant of finding nothing.
    """

    type: str
    group: str

    def detect(self, text: str) -> list[ValueDetection]: ...


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
        tuple[object, tuple[Capture, ...], object],
    ]


def _contains_float(obj: object) -> bool:
    """True if a ``float`` lurks anywhere in a value/spec record (recursively).

    §12.1: a detection's value is surface-derived, never a binary ``float`` (ICU's
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


def _scan(text: str, locale: str, type_label: str, inv: _Inverter) -> list[ValueDetection]:
    """Windowed detection with reformat-equality acceptance and greedy longest-match.

    Scans grapheme-cluster starts left to right. A miss or no forward progress simply
    continues (never a refusal). A successful parse whose endpoint is reversed,
    surrogate-interior, or mid-grapheme is a :class:`DetectorRefusal`. An accepted span
    must reproduce the formatter's canonical output exactly (rejecting ICU's permissive
    coercions). After a match ``[s, e)`` the scan resumes at ``e`` so one detector never
    self-overlaps.
    """
    us = icu.UnicodeString(text)
    cp_to_u16, u16_to_cp = boundary_maps(text)
    gspans = break_grapheme_spans(text, locale)
    starts = sorted({g["start"] for g in gspans})
    boundaries = {g["start"] for g in gspans} | {g["end"] for g in gspans} | {0, len(text)}

    out: list[ValueDetection] = []
    cursor = 0
    for start_cp in starts:
        if start_cp < cursor:
            continue  # greedy: inside a prior match
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
        surface = text[start_cp:end_cp]
        if inv.reformat(parsed) != surface:
            continue  # permissive coercion -> not accepted (not fatal)
        value, captures, spec = inv.build(parsed, surface, start_cp, cp_to_u16, u16_to_cp)
        if _contains_float(value) or _contains_float(spec) or _contains_float(captures):
            raise ValueError(
                f"{type_label}: build() produced a float in a record (§12.1: values are "
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
    Detections from different detectors may overlap -- H3 deposits them; resolving
    overlap is H4.

    Each detector runs its own scan here (multi-pass), so a gang trivially equals the
    merge of its members. The single-pass variant §12.5 describes -- one shared scan
    with per-member resume cursors and a freshly cleared calendar per (member, start)
    attempt -- is a deferred efficiency optimization, not yet built; its equivalence
    to this merge is the invariant that variant must preserve.
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
    """

    detectors: tuple[Detector, ...]

    def detect(self, text: str) -> list[ValueDetection]:
        return detect(text, self.detectors)

    def names(self) -> tuple[str, ...]:
        return tuple(d.type for d in self.detectors)

    def with_(self, *more: Detector) -> DetectorSet:
        """Return a new gang with ``more`` detectors added (deduplicated by type)."""
        seen = {d.type: d for d in self.detectors}
        for d in more:
            seen[d.type] = d
        return DetectorSet(tuple(seen.values()))

    def without(self, *types: str) -> DetectorSet:
        """Return a new gang with the named detector types removed."""
        drop = set(types)
        return DetectorSet(tuple(d for d in self.detectors if d.type not in drop))
