"""Compiled detector gangs with one immutable scan plan per input text."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import icu

from . import cache
from ._gate import (
    _SCAN_PLAN,
    GATE_AUDIT,
    LaneGate,
    StartGate,
    _read_start_gates,
    _ScanPlan,
)
from ._offsets import boundary_maps
from ._tables import TableKey, table_key
from .detectors import (
    _ONE_BEST_PREPARED,
    Detector,
    DetectorSet,
    ValueDetection,
    _one_best_key,
    _prepare_one_best,
    _word_interior_offsets,
)
from .detectors import detect as legacy_detect
from .material import LocaleMaterial

__all__ = [
    "CompileKey",
    "CompileStats",
    "CompiledDetectorSet",
    "ReaderSpec",
    "TableKey",
    "compile_detectors",
]


@dataclass(frozen=True)
class ReaderSpec:
    """A declarative detector gang whose construction is measured by compilation."""

    locale: str
    guarded: bool = False
    flexible: bool = False
    locales: tuple[str, ...] | None = None
    currencies: tuple[str, ...] = ()
    units: tuple[str, ...] = ()
    skeletons: tuple[str, ...] | None = None
    material: tuple[LocaleMaterial, ...] = ()

    def __post_init__(self) -> None:
        if self.locales is not None:
            object.__setattr__(self, "locales", tuple(self.locales))
        object.__setattr__(self, "currencies", tuple(self.currencies))
        object.__setattr__(self, "units", tuple(self.units))
        if self.skeletons is not None:
            object.__setattr__(self, "skeletons", tuple(self.skeletons))
        object.__setattr__(self, "material", tuple(self.material))


@dataclass(frozen=True)
class CompileStats:
    """Measured reader construction/warmup and the resulting lane counts."""

    build_s: float | None
    warm_s: float
    tables_loaded: int
    tables_computed: int
    lanes_gated: int
    lanes_ungated: int
    table_store: str | None


@dataclass(frozen=True)
class CompileKey:
    """The table environment and identity of one detector gang."""

    tables: str
    locales: tuple[str, ...]
    readers: str

    def digest(self) -> str:
        """Return SHA-256 over canonical JSON of the fields."""
        payload = json.dumps(
            {"locales": self.locales, "readers": self.readers, "tables": self.tables},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest()


def _reader_children(value: object) -> Iterable[object]:
    if callable(getattr(value, "detect", None)):
        yield value
    elif isinstance(value, (tuple, list, frozenset)):
        for item in value:
            if callable(getattr(item, "detect", None)):
                yield item
    elif isinstance(value, Mapping):
        for item in value.values():
            if callable(getattr(item, "detect", None)):
                yield item


def _iter_readers(detectors: DetectorSet) -> Iterable[object]:
    pending = list(detectors.detectors)
    seen: set[int] = set()
    while pending:
        reader = pending.pop()
        if id(reader) in seen:
            continue
        seen.add(id(reader))
        yield reader
        try:
            values = vars(reader).values()
        except TypeError:
            continue
        for value in values:
            pending.extend(_reader_children(value))


def _warm(detectors: DetectorSet) -> None:
    """Force known lazy sub-readers and the zone tables they can consult."""
    from .recognize import _language_zone_abbreviations, _language_zone_names

    pending = list(detectors.detectors)
    seen: set[int] = set()
    while pending:
        reader = pending.pop()
        if id(reader) in seen:
            continue
        seen.add(id(reader))
        endpoint_readers = getattr(reader, "_endpoint_readers", None)
        if callable(endpoint_readers):
            endpoint_readers()
        bare_reader = getattr(reader, "_bare_reader", None)
        if callable(bare_reader):
            bare_reader()
        language = getattr(reader, "_language", None)
        if isinstance(language, str):
            names = getattr(reader, "locales", None)
            _language_zone_names(language, names)
            _language_zone_abbreviations(language, names)
        try:
            values = vars(reader).values()
        except TypeError:
            continue
        for value in values:
            pending.extend(_reader_children(value))


def _lane_report(detectors: DetectorSet) -> tuple[LaneGate, ...]:
    from ._gate import gate_report

    try:
        return gate_report(detectors)
    except Exception:
        # Reporting must never make detection unavailable for a third-party detector.
        return ()


def _detector_keys(detectors: DetectorSet) -> tuple[tuple, ...]:
    from .detectors import detector_key

    keys = []
    for detector in detectors.detectors:
        try:
            keys.append(detector_key(detector))
        except Exception:
            reader = type(detector)
            keys.append(
                (
                    str(getattr(detector, "type", "unknown")),
                    f"{reader.__module__}.{reader.__qualname__}",
                    None,
                    None,
                    None,
                )
            )
    return tuple(keys)


def _compile_key(detectors: DetectorSet) -> CompileKey:
    keys = _detector_keys(detectors)
    locales = tuple(sorted({key[2] for key in keys if isinstance(key[2], str)}))
    identity = repr(sorted(keys, key=repr)).encode()
    return CompileKey(
        tables=table_key().digest(),
        locales=locales,
        readers=hashlib.sha256(identity).hexdigest(),
    )


def _plan_readers(detectors: DetectorSet) -> tuple[tuple[str, ...], frozenset[StartGate | None]]:
    locales: set[str] = set()
    gates: set[StartGate | None] = set()
    for reader in _iter_readers(detectors):
        start_gates = getattr(reader, "start_gates", None)
        if callable(start_gates):
            locale = getattr(reader, "locale", None)
            if isinstance(locale, str):
                locales.add(locale)
            declared, invalid_reason = _read_start_gates(reader)
            if invalid_reason is not None:
                gates.add(None)
            else:
                assert declared is not None
                gates.update(declared.values())
    return tuple(sorted(locales)), frozenset(gates)


def _break_offsets(ustr, locale: str, u16_to_cp: Mapping[int, int], *, word: bool):
    factory = (
        icu.BreakIterator.createWordInstance if word else icu.BreakIterator.createCharacterInstance
    )
    iterator = factory(icu.Locale(locale))
    iterator.setText(ustr)
    start_u16 = iterator.first()
    spans = []
    for end_u16 in iterator:
        spans.append((u16_to_cp[start_u16], u16_to_cp[end_u16]))
        start_u16 = end_u16
    return tuple(spans)


def _scan_plan(
    text: str, locales: tuple[str, ...], gates: frozenset[StartGate | None]
) -> _ScanPlan:
    ustr = icu.UnicodeString(text)
    mutable_cp_to_u16, mutable_u16_to_cp = boundary_maps(text)
    cp_to_u16 = tuple(mutable_cp_to_u16)
    u16_to_cp = MappingProxyType(dict(mutable_u16_to_cp))
    spans: dict[str, tuple[tuple[int, int], ...]] = {}
    starts: dict[str, tuple[int, ...]] = {}
    boundaries: dict[str, frozenset[int]] = {}
    interiors: dict[str, frozenset[int]] = {}
    for locale in locales:
        locale_spans = _break_offsets(ustr, locale, u16_to_cp, word=False)
        word_spans = _break_offsets(ustr, locale, u16_to_cp, word=True)
        word_edges = frozenset((0, len(text), *(offset for span in word_spans for offset in span)))
        locale_starts = tuple(sorted({start for start, _end in locale_spans}))
        spans[locale] = locale_spans
        starts[locale] = locale_starts
        boundaries[locale] = frozenset((*locale_starts, len(text)))
        interiors[locale] = frozenset(_word_interior_offsets(text, locale, word_edges))
    frozen_starts = MappingProxyType(starts)
    gate_index = MappingProxyType(
        {
            gate: MappingProxyType(
                {
                    locale: (
                        locale_starts
                        if gate is None
                        else tuple(start for start in locale_starts if gate.admits(text[start]))
                    )
                    for locale, locale_starts in starts.items()
                }
            )
            for gate in gates
        }
    )
    return _ScanPlan(
        text=text,
        grapheme_starts=frozen_starts,
        gated_starts=gate_index,
        ustr=ustr,
        cp_to_u16=cp_to_u16,
        u16_to_cp=u16_to_cp,
        grapheme_spans=MappingProxyType(spans),
        grapheme_boundaries=MappingProxyType(boundaries),
        word_interiors=MappingProxyType(interiors),
    )


def _audit_plan(plan: _ScanPlan) -> None:
    assert str(plan.ustr) == plan.text
    assert isinstance(plan.cp_to_u16, tuple)
    assert all(isinstance(value, tuple) for value in plan.grapheme_spans.values())
    assert all(isinstance(value, frozenset) for value in plan.grapheme_boundaries.values())
    assert all(isinstance(value, frozenset) for value in plan.word_interiors.values())


@dataclass(frozen=True, eq=False, init=False)
class CompiledDetectorSet:
    """A detector gang prepared for shared per-text scanning.

    ``detectors`` is the immutable source gang. ``key`` and ``stats`` are report
    properties; implicit compilation computes them only on first access.
    """

    detectors: DetectorSet
    _build_s: float | None = field(default=None, init=False, repr=False)
    _warm_s: float = field(default=0.0, init=False, repr=False)
    _tables_loaded: int = field(default=0, init=False, repr=False)
    _tables_computed: int = field(default=0, init=False, repr=False)
    _key: CompileKey | None = field(default=None, repr=False)
    _stats: CompileStats | None = field(default=None, repr=False)
    _report: tuple[LaneGate, ...] | None = field(default=None, repr=False)
    _scan_locales: tuple[str, ...] = field(default=(), init=False, repr=False)
    _scan_gates: frozenset[StartGate | None] = field(default=frozenset(), init=False, repr=False)
    _scan_plans: dict[int, _ScanPlan] = field(default_factory=dict, init=False, repr=False)
    _kbest_plans: dict[tuple[int, tuple[int, ...], bool], object] = field(
        default_factory=dict, init=False, repr=False
    )
    _report_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __init__(self, detectors: DetectorSet) -> None:
        object.__setattr__(self, "detectors", detectors)
        object.__setattr__(self, "_build_s", None)
        object.__setattr__(self, "_warm_s", 0.0)
        object.__setattr__(self, "_tables_loaded", 0)
        object.__setattr__(self, "_tables_computed", 0)
        object.__setattr__(self, "_key", None)
        object.__setattr__(self, "_stats", None)
        object.__setattr__(self, "_report", None)
        scan_locales, scan_gates = _plan_readers(detectors)
        object.__setattr__(self, "_scan_locales", scan_locales)
        object.__setattr__(self, "_scan_gates", scan_gates)
        object.__setattr__(self, "_scan_plans", {})
        object.__setattr__(self, "_kbest_plans", {})
        object.__setattr__(self, "_report_lock", threading.Lock())

    @property
    def key(self) -> CompileKey:
        """The gang identity, computed only when reporting asks for it."""
        if self._key is None:
            with self._report_lock:
                if self._key is None:
                    object.__setattr__(self, "_key", _compile_key(self.detectors))
        return self._key

    @property
    def stats(self) -> CompileStats:
        """Compilation timings and lane counts, computed lazily on implicit compile."""
        if self._stats is None:
            report = self.gate_report()
            object.__setattr__(
                self,
                "_stats",
                CompileStats(
                    build_s=self._build_s,
                    warm_s=self._warm_s,
                    tables_loaded=self._tables_loaded,
                    tables_computed=self._tables_computed,
                    lanes_gated=sum(lane.gated for lane in report),
                    lanes_ungated=sum(not lane.gated for lane in report),
                    table_store=self.key.tables if cache.cache_info()["enabled"] else None,
                ),
            )
        return self._stats

    def gate_report(self) -> tuple[LaneGate, ...]:
        """Return one gate status row for every declared scan lane."""
        if self._report is None:
            with self._report_lock:
                if self._report is None:
                    object.__setattr__(self, "_report", _lane_report(self.detectors))
        return self._report

    def warm(self) -> CompiledDetectorSet:
        """Force lazy sub-readers and zone tables under the build phase."""
        before_loaded, before_computed = cache._table_counts()
        started = time.perf_counter()
        with cache._build_phase():
            _warm(self.detectors)
            cache.flush()
        after_loaded, after_computed = cache._table_counts()
        object.__setattr__(self, "_warm_s", self._warm_s + time.perf_counter() - started)
        object.__setattr__(
            self,
            "_tables_loaded",
            self._tables_loaded + after_loaded - before_loaded,
        )
        object.__setattr__(
            self,
            "_tables_computed",
            self._tables_computed + after_computed - before_computed,
        )
        object.__setattr__(self, "_stats", None)
        return self

    def detect(self, text: str, *, k: int | None = None) -> list[ValueDetection]:
        """Detect at ``k=None`` or ``k=1`` with one context-local immutable scan plan."""
        if not self._scan_locales:
            return legacy_detect(text, self.detectors.detectors, k=k)
        plan = self._scan_plans.get(id(text))
        if plan is None or plan.text is not text:
            try:
                plan = _scan_plan(text, self._scan_locales, self._scan_gates)
            except Exception:
                return legacy_detect(text, self.detectors.detectors, k=k)
            if len(self._scan_plans) >= 16:
                self._scan_plans.clear()
            self._scan_plans[id(text)] = plan
        token = _SCAN_PLAN.set(plan)
        # One hit means one compiled detect made its compatible plan available to the
        # detect phase. It is deliberately not counted again at every reader lookup.
        cache._record_detect_hit()
        prepared_token = None
        try:
            if k == 1:
                prepared_key = _one_best_key(text, self.detectors.detectors)
                key = (id(text), prepared_key[1], prepared_key[2])
                prepared = self._kbest_plans.get(key)
                if prepared is None or prepared[0] is not text:
                    prepared = _prepare_one_best(text, self.detectors.detectors)
                    if len(self._kbest_plans) >= 16:
                        self._kbest_plans.clear()
                    self._kbest_plans[key] = prepared
                prepared_token = _ONE_BEST_PREPARED.set(prepared)
            found = legacy_detect(text, self.detectors.detectors, k=k)
            if GATE_AUDIT:
                _audit_plan(plan)
        finally:
            if prepared_token is not None:
                _ONE_BEST_PREPARED.reset(prepared_token)
            _SCAN_PLAN.reset(token)
        return found


def _compile(
    detectors: DetectorSet | Iterable[Detector] | ReaderSpec,
    *,
    warm: bool,
    defer_report: bool,
) -> CompiledDetectorSet:
    build_s: float | None = None
    warm_s = 0.0
    before_loaded, before_computed = cache._table_counts()
    with cache._build_phase():
        if isinstance(detectors, ReaderSpec):
            from .engine import reader_set

            started = time.perf_counter()
            gang = reader_set(
                detectors.locale,
                guarded=detectors.guarded,
                flexible=detectors.flexible,
                locales=detectors.locales,
                currencies=detectors.currencies,
                units=detectors.units,
                skeletons=detectors.skeletons,
                material=detectors.material,
            )
            build_s = time.perf_counter() - started
        elif isinstance(detectors, DetectorSet):
            gang = detectors
        else:
            gang = DetectorSet(tuple(detectors))
        compiled = CompiledDetectorSet(gang)
        object.__setattr__(compiled, "_build_s", build_s)
        object.__setattr__(compiled, "_warm_s", warm_s)
        if warm:
            started = time.perf_counter()
            _warm(gang)
            cache.flush()
            object.__setattr__(compiled, "_warm_s", time.perf_counter() - started)
        else:
            cache.flush()
        cache._record_compile()
    after_loaded, after_computed = cache._table_counts()
    object.__setattr__(
        compiled,
        "_tables_loaded",
        after_loaded - before_loaded,
    )
    object.__setattr__(
        compiled,
        "_tables_computed",
        after_computed - before_computed,
    )
    if not defer_report:
        object.__setattr__(compiled, "_key", _compile_key(gang))
        object.__setattr__(compiled, "_report", _lane_report(gang))
        _ = compiled.stats
    return compiled


def compile_detectors(
    detectors: DetectorSet | Iterable[Detector] | ReaderSpec, *, warm: bool = True
) -> CompiledDetectorSet:
    """Compile a detector gang, measuring construction only for a :class:`ReaderSpec`."""
    return _compile(detectors, warm=warm, defer_report=False)


def _implicit_compile(detectors: DetectorSet) -> CompiledDetectorSet:
    return _compile(detectors, warm=False, defer_report=True)
