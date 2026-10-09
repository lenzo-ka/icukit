"""Bounded, incremental detection over text supplied in arbitrary chunks.

Streaming never changes the whole-text :meth:`DetectorSet.detect` path.  It keeps a
bounded suffix, re-runs the selected readers on that suffix, and publishes only starts
whose declared right extent has closed.  Reader extents are deliberately data carried
by each reader: they describe ICU and material that the reader already owns, rather
than a locale table duplicated by the stream.

The behavior-schema names for the three constructor options are
``detection.stream.max_pending_chars``, ``detection.stream.reader_cap_chars``, and
``detection.stream.detect_stride_chars``.  Their defaults are respectively 4096, each
reader's declared cap (4096 for stock unbounded readers), and 32 code points.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Protocol, TypedDict, runtime_checkable

import icu

from .detectors import Detector, DetectorRefusal, DetectorSet, ValueDetection, _sort_key

DEFAULT_MAX_PENDING_CHARS: int = 4096
DEFAULT_READER_CAP_CHARS: int = 4096
DEFAULT_DETECT_STRIDE_CHARS: int = 32

_RIGHT_PEEK = 2
_NUMBER_LEFT_CHARS = r"[\p{Nd}\p{Sm}\p{Cf}]"
_NUMERIC_JOIN_CHARS = r"[\p{N}\p{S}\p{Cf}]"

_WB = icu.UProperty.WORD_BREAK
_GCB = icu.UProperty.GRAPHEME_CLUSTER_BREAK
_WB_LEFT = {
    icu.Char.getPropertyValueEnum(_WB, name)
    for name in ("Other", "CR", "LF", "Newline", "WSegSpace")
}
_WB_RIGHT_EXCLUDED = {
    icu.Char.getPropertyValueEnum(_WB, name) for name in ("Extend", "Format", "ZWJ")
}
_GCB_LEFT_EXCLUDED = {icu.Char.getPropertyValueEnum(_GCB, "Prepend")}
_GCB_RIGHT_EXCLUDED = {
    icu.Char.getPropertyValueEnum(_GCB, name) for name in ("Extend", "ZWJ", "SpacingMark")
}
_WB_WSEGSPACE = icu.Char.getPropertyValueEnum(_WB, "WSegSpace")
_DICT = icu.UnicodeSet(r"[\p{Line_Break=SA}\p{Ideographic}\p{Hiragana}\p{Katakana}]")
_PUNCTUATION = icu.UnicodeSet(r"[\p{P}]")
_LETTERS_MARKS = icu.UnicodeSet(r"[\p{L}\p{M}]")
_REFUSAL_MESSAGES = {
    "reversed-endpoint": "parse ended before its start",
    "out-of-range-endpoint": "parse ended beyond the end of the text",
    "surrogate-interior-endpoint": "parse ended inside a surrogate pair",
    "mid-grapheme-endpoint": "parse ended inside a grapheme cluster",
}


def _set_union(first: str, second: str) -> str:
    if not first:
        return second
    if not second:
        return first
    result = icu.UnicodeSet(first)
    result.addAll(icu.UnicodeSet(second))
    return result.toPattern()


@dataclass(frozen=True)
class Extent:
    """A reader's maximum right and left context, measured in stream chunks.

    ``chunks=None`` denotes a reader closed by the declared ``joins``/``join_chars``
    condition and therefore requires a positive ``cap_chars``.  ``left_chunks=None``
    analogously walks left while the left join condition holds.  ``source`` records
    how the reader derived the declaration from its own ICU objects or material.
    """

    chunks: int | None
    joins: frozenset[str] | None = frozenset()
    join_chars: str = ""
    cap_chars: int | None = None
    left_chunks: int | None = 0
    left_joins: frozenset[str] | None = frozenset()
    left_join_chars: str = ""
    source: str = ""

    def union(self, other: Extent) -> Extent:
        """Return the conservative extent accepting either declaration."""
        chunks = (
            None if self.chunks is None or other.chunks is None else max(self.chunks, other.chunks)
        )
        left_chunks = (
            None
            if self.left_chunks is None or other.left_chunks is None
            else max(self.left_chunks, other.left_chunks)
        )
        joins = None if self.joins is None or other.joins is None else self.joins | other.joins
        left_joins = (
            None
            if self.left_joins is None or other.left_joins is None
            else self.left_joins | other.left_joins
        )
        caps = [value for value in (self.cap_chars, other.cap_chars) if value is not None]
        cap = min(caps) if chunks is None and caps else None
        return Extent(
            chunks,
            joins,
            _set_union(self.join_chars, other.join_chars),
            cap,
            left_chunks,
            left_joins,
            _set_union(self.left_join_chars, other.left_join_chars),
            "; ".join(part for part in (self.source, other.source) if part),
        )

    def then(self, other: Extent) -> Extent:
        """Return a composite extent whose right side follows ``self`` with ``other``."""
        chunks = None if self.chunks is None or other.chunks is None else self.chunks + other.chunks
        joins = None if self.joins is None or other.joins is None else self.joins | other.joins
        caps = [value for value in (self.cap_chars, other.cap_chars) if value is not None]
        cap = min(caps) if chunks is None and caps else None
        return Extent(
            chunks,
            joins,
            _set_union(self.join_chars, other.join_chars),
            cap,
            self.left_chunks,
            self.left_joins,
            self.left_join_chars,
            "; then ".join(part for part in (self.source, other.source) if part),
        )


@runtime_checkable
class StreamableDetector(Detector, Protocol):
    """A detector with a sound static declaration of both context directions."""

    def extent(self) -> Extent: ...


@dataclass(frozen=True)
class ReaderExtent:
    """One detector's declared extent and effective configurable cap."""

    reader: str
    type: str
    locale: str | None
    extent: Extent
    cap_chars: int | None


@dataclass(frozen=True)
class DetectionBatch:
    """Detections settled by one call and the stream frontier after that call."""

    detections: tuple[ValueDetection, ...]
    pending_from: int
    cuts: tuple[int, ...] = ()
    reader_cuts: tuple[tuple[str, int], ...] = ()


class StreamPending(TypedDict):
    """A snapshot of retained and undecided stream state."""

    pending_from: int
    decided_through: int
    buffered_from: int
    total: int
    open_chunk: int | None


def _detector_tuple(
    detectors: DetectorSet | object | Iterable[Detector],
) -> tuple[Detector, ...]:
    if isinstance(detectors, DetectorSet):
        return detectors.detectors
    owned = getattr(detectors, "detectors", None)
    if isinstance(owned, DetectorSet):
        return owned.detectors
    return tuple(detectors)  # type: ignore[arg-type]


def _valid_extent(extent: object) -> bool:
    if not isinstance(extent, Extent):
        return False
    right = extent.chunks is not None or (
        extent.joins is not None
        and isinstance(extent.cap_chars, int)
        and not isinstance(extent.cap_chars, bool)
        and extent.cap_chars > 0
    )
    left = extent.left_chunks is not None or extent.left_joins is not None
    return right and left


def _validate_cap_mapping(reader_cap_chars: Mapping[str, int] | None) -> dict[str, int]:
    if reader_cap_chars is None:
        return {}
    if not isinstance(reader_cap_chars, Mapping) or any(
        not isinstance(key, str)
        or not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        for key, value in reader_cap_chars.items()
    ):
        raise ValueError("reader_cap_chars must map detector types to positive ints")
    return dict(reader_cap_chars)


def extent_report(
    detectors: DetectorSet | object | Iterable[Detector],
    *,
    reader_cap_chars: Mapping[str, int] | None = None,
) -> tuple[ReaderExtent, ...]:
    """Return every reader's declaration, refusing an unstreamable member.

    ``reader_cap_chars`` is keyed by detection type, matching the future behavior
    schema field ``detection.stream.reader_cap_chars``.
    """
    caps = _validate_cap_mapping(reader_cap_chars)
    rows = []
    for detector in _detector_tuple(detectors):
        declaration = getattr(detector, "extent", None)
        extent = declaration() if callable(declaration) else None
        if not _valid_extent(extent):
            raise ValueError(
                f"detector {detector.type!r} ({type(detector).__name__}) declares no "
                "streamable extent; define extent() -> Extent with a closing condition "
                "and cap_chars on each unbounded side"
            )
        assert isinstance(extent, Extent)
        cap = caps.get(detector.type, extent.cap_chars)
        rows.append(
            ReaderExtent(
                type(detector).__name__,
                detector.type,
                getattr(detector, "locale", None),
                extent,
                cap,
            )
        )
    return tuple(rows)


@lru_cache(maxsize=256)
def _aggregate_extent(extents: tuple[Extent, ...]) -> Extent:
    extent = Extent(0, source="empty detector set")
    for declared in extents:
        extent = extent.union(declared)
    return extent


def _seams(text: str, *, origin: int = 0) -> tuple[int, ...]:
    """Return settlement seams, excluding CR|LF and unstable Unicode interiors."""
    found = []
    for position in range(1, len(text)):
        left = text[position - 1]
        right = text[position]
        left_wb = icu.Char.getIntPropertyValue(left, _WB)
        right_wb = icu.Char.getIntPropertyValue(right, _WB)
        left_gcb = icu.Char.getIntPropertyValue(left, _GCB)
        right_gcb = icu.Char.getIntPropertyValue(right, _GCB)
        if (
            left_wb in _WB_LEFT
            and left not in _DICT
            and left_gcb not in _GCB_LEFT_EXCLUDED
            and right_wb not in _WB_RIGHT_EXCLUDED
            and right_gcb not in _GCB_RIGHT_EXCLUDED
            and not (left_wb == right_wb == _WB_WSEGSPACE)
            and not (left == "\r" and right == "\n")
        ):
            found.append(origin + position)
    return tuple(found)


@lru_cache(maxsize=8192)
def _words(text: str) -> tuple[str, ...]:
    """Return contiguous letter-and-mark runs.

    Numeric readers commonly attach a localized suffix to digits without a word
    boundary (``500e.``).  The suffix is the reader-owned join; the digits are covered
    by ``join_chars``.  Contiguous runs, rather than ICU word segments, are intentional:
    dictionary segmentation is not prefix-stable (a partial Japanese unit can be one
    word before ICU later splits its completed form).  The same rule derives the join
    vocabulary and checks live prefixes, while preserving marks in names such as
    ``Bɔ̀ŋ``.
    """
    result = []
    run = []
    for character in text:
        if character in _LETTERS_MARKS:
            run.append(character)
        elif run:
            result.append("".join(run).casefold())
            run = []
    if run:
        result.append("".join(run).casefold())
    return tuple(result)


@lru_cache(maxsize=8192)
def _joinable(
    text: str, joins: frozenset[str] | None, join_chars: str, *, prefix: bool = False
) -> bool:
    words = _words(text)
    if joins is not None and any(
        word not in joins
        and (not prefix or not any(candidate.startswith(word) for candidate in joins))
        for word in words
    ):
        return False
    allowed = icu.UnicodeSet(join_chars) if join_chars else None
    for character in text:
        if icu.Char.isUWhiteSpace(character) or character in _PUNCTUATION:
            continue
        if character in _LETTERS_MARKS:
            continue
        if allowed is None or character not in allowed:
            return False
    return True


@lru_cache(maxsize=8192)
def _gate_admits_chunk(gate: object, chunk: str) -> bool:
    """Return whether a shared start gate admits any start in one seam chunk."""
    return gate is None or any(gate.admits(character) for character in chunk)  # type: ignore[attr-defined]


def _shift_detection(detection: ValueDetection, offset: int) -> ValueDetection:
    if offset == 0:
        return detection
    shifted = dict(detection)
    shifted["start"] = detection["start"] + offset
    shifted["end"] = detection["end"] + offset
    shifted["captures"] = tuple(
        replace(capture, start=capture.start + offset, end=capture.end + offset)
        for capture in detection["captures"]
    )
    return shifted  # type: ignore[return-value]


def _truncated(detection: ValueDetection) -> ValueDetection:
    result = dict(detection)
    result["truncated"] = True
    return result  # type: ignore[return-value]


def _deduplicate(detections: Iterable[ValueDetection]) -> list[ValueDetection]:
    result = []
    seen = set()
    for detection in sorted(detections, key=_sort_key):
        key = repr(detection)
        if key not in seen:
            seen.add(key)
            result.append(detection)
    return result


def _grapheme_boundaries(text: str, origin: int) -> tuple[int, ...]:
    iterator = icu.BreakIterator.createCharacterInstance(icu.Locale.getRoot())
    iterator.setText(text)
    from ._offsets import boundary_maps

    _cp_to_u16, u16_to_cp = boundary_maps(text)
    return tuple(origin + u16_to_cp[end] for end in iterator)


class DetectionStream:
    """Incrementally detect text with bounded retention and absolute offsets.

    The stream cap bounds overlap chains, open Unicode chunks, and left walks that no
    individual reader owns.  Unbounded readers also retain their declared, independently
    configurable caps.  ``feed`` performs at most one ordinary detection window when the
    frontier has advanced by ``detect_stride_chars``; a cut, ``flush``, or ``close``
    always performs the required final window.
    """

    def __init__(
        self,
        detectors: DetectorSet | object | Iterable[Detector],
        /,
        *,
        max_pending_chars: int = DEFAULT_MAX_PENDING_CHARS,
        reader_cap_chars: Mapping[str, int] | None = None,
        detect_stride_chars: int = DEFAULT_DETECT_STRIDE_CHARS,
    ) -> None:
        for name, value in (
            ("max_pending_chars", max_pending_chars),
            ("detect_stride_chars", detect_stride_chars),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive int")
        self._detectors = _detector_tuple(detectors)
        self._source = (
            detectors
            if callable(getattr(detectors, "_detect_window", None))
            else DetectorSet(self._detectors)
        )
        self._cap_overrides = _validate_cap_mapping(reader_cap_chars)
        self._report = extent_report(self._detectors, reader_cap_chars=self._cap_overrides)
        self._reader_gates = tuple(self._start_gate(detector) for detector in self._detectors)
        grouped: dict[tuple[object, bool], list[Extent]] = {}
        for row, gate in zip(self._report, self._reader_gates, strict=True):
            grouped.setdefault((gate, row.extent.chunks is None), []).append(row.extent)
        self._gate_extents = tuple(
            (gate, unbounded, _aggregate_extent(tuple(extents)))
            for (gate, unbounded), extents in grouped.items()
        )
        self._extent = _aggregate_extent(tuple(row.extent for row in self._report))
        self._max_pending = max_pending_chars
        self._stride = detect_stride_chars
        self._text = ""
        self._total = 0
        self._buffered_from = 0
        self._buffered_u16_from = 0
        self._pending_from = 0
        self._cap_pending_from = 0
        self._left_checked_through = 0
        self._decided_through = 0
        self._last_detect_total = 0
        self._closed = False
        self._reader_origins: dict[str, int] = {}
        self._reader_checked_starts: dict[str, int] = {}
        self._window_detect_count = 0

    @staticmethod
    def _start_gate(detector: Detector):
        declaration = getattr(detector, "start_gates", None)
        if not callable(declaration):
            return None
        gates = tuple(declaration().values())
        if not gates or any(gate is None for gate in gates):
            return None
        combined = gates[0]
        for gate in gates[1:]:
            combined = combined | gate
        return combined

    @property
    def window_detect_count(self) -> int:
        """Number of detection windows run, for benchmark accounting."""
        return self._window_detect_count

    def _detect_raw(
        self,
        text: str,
        only: tuple[Detector, ...] | None = None,
        *,
        offset: int = 0,
        u16_offset: int = 0,
    ):
        self._window_detect_count += 1
        try:
            compiled_window = getattr(self._source, "_detect_window", None)
            if callable(compiled_window):
                return compiled_window(text, only=only)
            selected = self._detectors if only is None else only
            from .detectors import detect

            return detect(text, selected)
        except DetectorRefusal as error:
            if not offset and not u16_offset:
                raise
            endpoint_offset = offset if error.reason == "mid-grapheme-endpoint" else u16_offset
            endpoint = None if error.endpoint is None else error.endpoint + endpoint_offset
            raise DetectorRefusal(
                error.type,
                error.start + offset,
                endpoint,
                error.reason,
                _REFUSAL_MESSAGES[error.reason],
            ) from None

    def _slice(self, start: int, end: int) -> str:
        return self._text[start - self._buffered_from : end - self._buffered_from]

    def _u16_offset(self, position: int) -> int:
        prefix = self._slice(self._buffered_from, position)
        return self._buffered_u16_from + len(prefix.encode("utf-16-le")) // 2

    def _drop_before(self, offset: int) -> None:
        if offset <= self._buffered_from:
            return
        discarded = self._text[: offset - self._buffered_from]
        self._text = self._text[offset - self._buffered_from :]
        self._buffered_u16_from += len(discarded.encode("utf-16-le")) // 2
        self._buffered_from = offset

    def _window_detections(self, end: int | None = None) -> list[ValueDetection]:
        if end is None:
            end = self._total
        begin = self._buffered_from
        local = self._slice(begin, end)
        cut_types = set(self._reader_origins)
        ordinary = tuple(detector for detector in self._detectors if detector.type not in cut_types)
        found = [
            _shift_detection(item, begin)
            for item in self._detect_raw(
                local,
                only=ordinary,
                offset=begin,
                u16_offset=self._u16_offset(begin),
            )
        ]
        for detector_type, reader_origin in self._reader_origins.items():
            if reader_origin >= end:
                continue
            selected = tuple(d for d in self._detectors if d.type == detector_type)
            segment = self._slice(reader_origin, end)
            found.extend(
                _shift_detection(item, reader_origin)
                for item in self._detect_raw(
                    segment,
                    only=selected,
                    offset=reader_origin,
                    u16_offset=self._u16_offset(reader_origin),
                )
            )
        return _deduplicate(found)

    def _chunk_frontier(self, end: int | None = None, *, pending_from: int | None = None) -> int:
        if end is None:
            end = self._total
        if pending_from is None:
            pending_from = self._pending_from
        origin = self._buffered_from
        local = self._slice(origin, end)
        seams = _seams(local, origin=origin)
        starts = (origin, *seams)
        ends = (*seams, end)
        frontier = pending_from
        for index, start in enumerate(starts):
            if start < pending_from:
                continue
            if index >= len(seams):
                break
            if not self._start_is_decided(index, start, end, seams, starts, ends):
                break
            # ``frontier`` is the first possible start not yet proved closed, not the
            # farthest reach of a reader at an earlier start.  Jumping to that far
            # reach skips competitors that can begin in an intervening chunk.
            frontier = seams[index]
        return max(pending_from, frontier)

    def _start_is_decided(self, index, start, end, seams, starts, ends) -> bool:
        """Whether every reader that can own ``start`` has closed by ``end``."""
        chunk = self._slice(start, ends[index])
        bounded = []
        unbounded = []
        if not self._reader_origins:
            # Hundreds of locale readers share a few dozen immutable start gates.
            # Aggregate those equal-gate extents once per stream, then test each gate
            # once per seam instead of once per reader and character.
            for gate, is_unbounded, extent in self._gate_extents:
                if _gate_admits_chunk(gate, chunk):
                    (unbounded if is_unbounded else bounded).append(extent)
        else:
            # A reader-specific cap changes the origin of only that detection type,
            # so retain the individual path while any such origin is active.
            for row, gate in zip(self._report, self._reader_gates, strict=True):
                reader_origin = self._reader_origins.get(row.type)
                if reader_origin is not None and start < reader_origin:
                    continue
                if not _gate_admits_chunk(gate, chunk):
                    continue
                target = unbounded if row.extent.chunks is None else bounded
                target.append(row.extent)
        for extents in (bounded, unbounded):
            if extents and not self._extent_is_closed(
                index,
                end,
                seams,
                starts,
                ends,
                _aggregate_extent(tuple(extents)),
            ):
                return False
        return True

    def _extent_is_closed(self, index, end, seams, starts, ends, extent) -> bool:
        limit = None if extent.chunks is None else index + max(extent.chunks, 1)
        cursor = index + 1
        while (
            cursor < len(starts)
            and (limit is None or cursor < limit)
            and _joinable(
                self._slice(starts[cursor], ends[cursor]),
                extent.joins,
                extent.join_chars,
                prefix=cursor >= len(seams),
            )
        ):
            if cursor >= len(seams):
                cursor = len(starts)
                break
            cursor += 1
        if limit is not None and cursor >= limit:
            if limit >= len(starts):
                return False
            close = starts[limit]
        elif cursor >= len(starts):
            return False
        else:
            close = starts[cursor]
        return end >= close + _RIGHT_PEEK

    def _settlement_candidate(
        self, end: int, pending_from: int
    ) -> tuple[list[ValueDetection], int, int]:
        frontier = self._chunk_frontier(end, pending_from=pending_from)
        if frontier <= pending_from:
            return [], pending_from, frontier
        found = self._window_detections(end=end)
        seams = [
            seam
            for seam in _seams(self._slice(self._buffered_from, end), origin=self._buffered_from)
            if pending_from < seam <= frontier
        ]
        new_pending = pending_from
        for seam in seams:
            if not any(item["start"] < seam < item["end"] for item in found):
                new_pending = seam
        return found, new_pending, frontier

    def _settle(self, *, force: bool = False, end: int | None = None) -> list[ValueDetection]:
        if end is None:
            end = self._total
        frontier = self._chunk_frontier(end)
        self._decided_through = frontier
        if not force and end - self._last_detect_total < self._stride:
            return []
        if frontier <= self._pending_from:
            self._last_detect_total = end
            return []
        old_pending = self._pending_from
        try:
            found, new_pending, _frontier = self._settlement_candidate(end, old_pending)
        except DetectorRefusal:
            # A feed boundary is not an input boundary. ICU can reject an otherwise
            # valid parse while the prefix ends inside the grapheme that completes it
            # (notably Sinhala date fields). Keep the window unsettled and retry after
            # more text; flush() still runs the final window and therefore preserves a
            # refusal from the complete segment.
            self._last_detect_total = end
            return []
        keep_from = self._left_window(new_pending, end=end)
        if new_pending - keep_from > self._max_pending:
            self._last_detect_total = end
            return []
        decided = [item for item in found if old_pending <= item["start"] < new_pending]
        self._pending_from = new_pending
        self._last_detect_total = end
        self._trim(end=end)
        return decided

    def _cut_position(self, start: int, cap: int, *, end: int | None = None) -> int:
        if end is None:
            end = self._total
        limit = min(end, start + cap)
        seams = [
            value
            for value in _seams(
                self._slice(self._buffered_from, min(end, limit + 1)),
                origin=self._buffered_from,
            )
            if start < value <= limit
        ]
        if seams:
            return seams[-1]
        local = self._slice(start, min(end, limit + 1))
        words = icu.BreakIterator.createWordInstance(icu.Locale.getRoot())
        words.setText(local)
        from ._offsets import boundary_maps

        _cp_to_u16, u16_to_cp = boundary_maps(local)
        word_edges = [
            start + u16_to_cp[end] for end in words if start < start + u16_to_cp[end] <= limit
        ]
        if word_edges:
            return word_edges[-1]
        graphemes = [edge for edge in _grapheme_boundaries(local, start) if start < edge <= limit]
        return graphemes[-1] if graphemes else limit

    def _reader_open_at_cap(self, start: int, extent: Extent, cap: int, *, end: int) -> bool:
        """Whether the earliest reader chunk still reaches its cap under its joins."""
        limit = start + cap
        inspected_end = min(end, limit + 1)
        seams = tuple(
            seam
            for seam in _seams(self._slice(start, inspected_end), origin=start)
            if seam <= limit
        )
        if not seams:
            return True
        return self._reader_continuation_open(start, inspected_end, limit, seams, extent)

    def _reader_continuation_open(self, start, inspected_end, limit, seams, extent):
        edges = (start, *seams, inspected_end)
        for index in range(1, len(edges) - 1):
            chunk_start = edges[index]
            if chunk_start >= limit:
                return True
            chunk_end = edges[index + 1]
            complete = index + 1 < len(edges) - 1 or inspected_end > limit
            if not _joinable(
                self._slice(chunk_start, chunk_end),
                extent.joins,
                extent.join_chars,
                prefix=not complete,
            ):
                return False
        return True

    def _reader_rows(self) -> dict[str, tuple[Detector, ReaderExtent]]:
        by_type: dict[str, tuple[Detector, ReaderExtent]] = {}
        for detector, row in zip(self._detectors, self._report, strict=True):
            if row.extent.chunks is None:
                by_type.setdefault(detector.type, (detector, row))
        return by_type

    def _reader_start(self, detector_type: str) -> int:
        return max(self._pending_from, self._reader_origins.get(detector_type, self._pending_from))

    def _reader_cuts_at(
        self, end: int, detector_types: Iterable[str]
    ) -> tuple[list[ValueDetection], list[tuple[str, int]]]:
        emitted: list[ValueDetection] = []
        cuts: list[tuple[str, int]] = []
        by_type = self._reader_rows()
        for detector_type in detector_types:
            _detector, row = by_type[detector_type]
            cap = self._cap_overrides.get(detector_type, row.cap_chars)
            if cap is None:
                continue
            start = self._reader_start(detector_type)
            if end < start + cap + 1:
                continue
            if self._reader_open_at_cap(start, row.extent, cap, end=end):
                cut = self._cut_position(start, cap, end=end)
                selected = tuple(d for d in self._detectors if d.type == detector_type)
                prefix = self._slice(start, cut)
                emitted.extend(
                    _truncated(_shift_detection(item, start))
                    for item in self._detect_raw(
                        prefix,
                        only=selected,
                        offset=start,
                        u16_offset=self._u16_offset(start),
                    )
                    if item["start"] < cut - start
                )
                cuts.append((detector_type, cut))
                self._reader_origins[detector_type] = cut
                self._reader_checked_starts.pop(detector_type, None)
            else:
                self._reader_checked_starts[detector_type] = start
        return _deduplicate(emitted), cuts

    def _stream_cut_at(
        self, end: int, *, start: int, decided_through: int
    ) -> tuple[list[ValueDetection], int]:
        actual_pending = self._pending_from
        cut = self._cut_position(start, self._max_pending, end=end)
        if not start < cut <= start + self._max_pending:
            raise RuntimeError("stream cap cut is outside its pending interval")
        if cut < actual_pending:
            raise RuntimeError("stream cap cut fell behind the settlement frontier")
        found = self._window_detections(end=end)
        emitted = [
            item for item in found if actual_pending <= item["start"] < min(decided_through, cut)
        ]
        prefix = self._window_detections(end=cut)
        emitted.extend(
            _truncated(item)
            for item in prefix
            if max(actual_pending, decided_through) <= item["start"] < cut
        )
        self._pending_from = cut
        self._cap_pending_from = cut
        self._left_checked_through = cut
        self._decided_through = cut
        self._drop_before(cut)
        for detector_type in self._reader_origins:
            self._reader_origins[detector_type] = max(cut, self._reader_origins[detector_type])
        return _deduplicate(emitted), cut

    def _left_cap_threshold(self) -> int | None:
        """Return the first prefix whose frontier passes the current left-walk bound."""
        start = self._cap_pending_from
        if start >= self._total:
            return None
        left_from = self._left_window(start, end=self._total)
        limit = left_from + self._max_pending
        checked = max(self._left_checked_through, start)

        def passes(end: int) -> bool:
            return self._chunk_frontier(end, pending_from=start) > limit

        if checked >= self._total or not passes(self._total):
            return None
        low = checked + 1
        high = self._total
        while low < high:
            middle = (low + high) // 2
            if passes(middle):
                high = middle
            else:
                low = middle + 1
        return low

    def _safe_pending_at(
        self,
        found: Iterable[ValueDetection],
        *,
        end: int,
        start: int,
        frontier: int,
        limit: int,
    ) -> int:
        safe = start
        for seam in _seams(self._slice(self._buffered_from, end), origin=self._buffered_from):
            if seam > min(frontier, limit):
                break
            if start < seam and not any(item["start"] < seam < item["end"] for item in found):
                safe = seam
        return safe

    def _cap_events(
        self,
    ) -> tuple[list[ValueDetection], list[int], list[tuple[str, int]]]:
        """Evaluate cap decisions at their text-fixed prefix thresholds."""
        emitted: list[ValueDetection] = []
        cuts: list[int] = []
        reader_cuts: list[tuple[str, int]] = []
        by_type = self._reader_rows()
        cap_distances = [self._max_pending]
        cap_distances.extend(
            cap
            for _detector_type, (_detector, row) in by_type.items()
            if (cap := self._cap_overrides.get(row.type, row.cap_chars)) is not None
        )
        if (
            self._cap_pending_from == self._buffered_from
            and self._total <= self._cap_pending_from + min(cap_distances)
        ):
            return emitted, cuts, reader_cuts
        while True:
            stream_threshold = self._cap_pending_from + self._max_pending + 1
            left_threshold = self._left_cap_threshold()
            reader_thresholds: dict[str, int] = {}
            for detector_type, (_detector, row) in by_type.items():
                cap = self._cap_overrides.get(detector_type, row.cap_chars)
                if cap is None:
                    continue
                start = self._reader_start(detector_type)
                if self._reader_checked_starts.get(detector_type) == start:
                    continue
                reader_thresholds[detector_type] = start + cap + 1
            thresholds = [stream_threshold, *reader_thresholds.values()]
            if left_threshold is not None:
                thresholds.append(left_threshold)
            threshold = min(thresholds)
            if threshold > self._total:
                break
            due_readers = [
                detector_type
                for detector_type, reader_threshold in reader_thresholds.items()
                if reader_threshold == threshold
            ]
            if due_readers:
                reader_emitted, new_reader_cuts = self._reader_cuts_at(threshold, due_readers)
                emitted.extend(reader_emitted)
                reader_cuts.extend(new_reader_cuts)
            cap_due = threshold == stream_threshold or threshold == left_threshold
            if not cap_due:
                emitted.extend(self._settle(end=threshold))
                continue
            cap_pending = self._cap_pending_from
            found, cap_new_pending, cap_frontier = self._settlement_candidate(
                threshold, cap_pending
            )
            self._decided_through = cap_frontier
            keep_from = self._left_window(cap_new_pending, end=threshold)
            left_limit = self._left_window(cap_pending, end=threshold) + self._max_pending
            safe_pending = self._safe_pending_at(
                found,
                end=threshold,
                start=cap_pending,
                frontier=cap_frontier,
                limit=left_limit,
            )
            if cap_new_pending > cap_pending and cap_new_pending - keep_from <= self._max_pending:
                self._cap_pending_from = cap_new_pending
                self._left_checked_through = threshold
                emitted.extend(self._settle(force=True, end=threshold))
            elif safe_pending > cap_pending:
                self._cap_pending_from = safe_pending
                self._left_checked_through = threshold
            elif cap_new_pending == cap_pending and threshold == left_threshold:
                self._left_checked_through = threshold
            else:
                cut_emitted, cut = self._stream_cut_at(
                    threshold,
                    start=cap_pending,
                    decided_through=cap_new_pending,
                )
                emitted.extend(cut_emitted)
                cuts.append(cut)
        return _deduplicate(emitted), cuts, reader_cuts

    def _left_window(self, position: int, *, end: int | None = None) -> int:
        if end is None:
            end = self._total
        seams = _seams(self._slice(self._buffered_from, end), origin=self._buffered_from)
        edges = (self._buffered_from, *seams, end)
        cursor = max(index for index, edge in enumerate(edges) if edge <= position)
        crossed = 0
        while cursor > 0 and (
            self._extent.left_chunks is None or crossed < self._extent.left_chunks
        ):
            start, end = edges[cursor - 1], edges[cursor]
            if not _joinable(
                self._slice(start, end),
                self._extent.left_joins,
                self._extent.left_join_chars,
            ):
                break
            cursor -= 1
            crossed += 1
        start = edges[cursor]
        index = start - 1
        while index >= self._buffered_from and icu.Char.isUWhiteSpace(
            self._slice(index, index + 1)
        ):
            index -= 1
        return max(self._buffered_from, index - 1)

    def _trim(self, *, end: int | None = None) -> None:
        keep_from = self._left_window(self._pending_from, end=end)
        if self._reader_origins:
            keep_from = min(keep_from, *self._reader_origins.values())
        if keep_from > self._cap_pending_from:
            self._cap_pending_from = keep_from
            self._left_checked_through = max(self._left_checked_through, keep_from)
        self._drop_before(keep_from)

    def feed(self, chunk: str, /) -> DetectionBatch:
        """Append ``chunk`` and return every detection newly settled by this call."""
        if self._closed:
            raise RuntimeError("detection stream is closed")
        if not isinstance(chunk, str):
            raise TypeError("chunk must be str")
        self._text += chunk
        self._total += len(chunk)
        cap_detections, cuts, reader_cuts = self._cap_events()
        detections = [*cap_detections, *self._settle()]
        return DetectionBatch(
            tuple(_deduplicate(detections)),
            self._pending_from,
            tuple(sorted(set(cuts))),
            tuple(sorted(reader_cuts, key=lambda item: (item[1], item[0]))),
        )

    def flush(self) -> DetectionBatch:
        """End the current segment without marking or recording a safety cut."""
        if self._closed:
            raise RuntimeError("detection stream is closed")
        found = [
            item
            for item in self._window_detections()
            if self._pending_from <= item["start"] < self._total
        ]
        self._pending_from = self._total
        self._cap_pending_from = self._total
        self._left_checked_through = self._total
        self._decided_through = self._total
        self._drop_before(self._total)
        self._reader_origins.clear()
        self._last_detect_total = self._total
        return DetectionBatch(tuple(found), self._pending_from)

    def close(self) -> DetectionBatch:
        """Flush once and close; repeated calls return an empty final batch."""
        if self._closed:
            return DetectionBatch((), self._total)
        batch = self.flush()
        self._closed = True
        return batch

    def pending(self) -> StreamPending:
        """Return the current absolute settlement and retention positions."""
        seams = _seams(self._text, origin=self._buffered_from)
        open_chunk = next((value for value in reversed(seams) if value >= self._pending_from), None)
        if open_chunk is None and self._pending_from < self._total:
            open_chunk = self._pending_from
        return StreamPending(
            pending_from=self._pending_from,
            decided_through=self._decided_through,
            buffered_from=self._buffered_from,
            total=self._total,
            open_chunk=open_chunk,
        )


def _extent_violations(
    text: str,
    detections: Iterable[ValueDetection],
    detectors: DetectorSet | object | Iterable[Detector],
) -> tuple[str, ...]:
    """Return right-span and left-window witnesses against reader declarations.

    This private audit intentionally reports compact, stable strings: the identity
    harness needs a non-empty witness, while public callers should use
    :func:`extent_report` for structured declarations.
    """
    del detections  # Each reader is rerun so same-type readers remain distinguishable.
    violations = []
    seams = _seams(text)
    edges = (0, *seams, len(text))
    for detector in _detector_tuple(detectors):
        declaration = getattr(detector, "extent", None)
        extent = declaration() if callable(declaration) else None
        if not _valid_extent(extent):
            violations.append(f"{detector.type}: unstreamable extent")
            continue
        assert isinstance(extent, Extent)
        for detection in detector.detect(text):
            start_chunk = max(
                index for index, edge in enumerate(edges[:-1]) if edge <= detection["start"]
            )
            end_chunk = max(
                index for index, edge in enumerate(edges[:-1]) if edge < detection["end"]
            )
            span_chunks = end_chunk - start_chunk + 1
            if extent.chunks is not None and span_chunks > extent.chunks:
                violations.append(
                    f"{detector.type}: right {span_chunks}>{extent.chunks} at {detection['start']}"
                )
            elif extent.chunks is None:
                for index in range(start_chunk + 1, end_chunk + 1):
                    # The last seam chunk can continue with unrelated text after this
                    # reader's endpoint (``-42.50ユーロ`` for the decimal reader). That
                    # suffix is what closes the extent; it is not context the detection
                    # consumes. Audit the accepted prefix, as live settlement does before
                    # the closing suffix arrives.
                    chunk_end = min(edges[index + 1], detection["end"])
                    if not _joinable(
                        text[edges[index] : chunk_end],
                        extent.joins,
                        extent.join_chars,
                        prefix=index == end_chunk,
                    ):
                        violations.append(
                            f"{detector.type}: right join at {edges[index]} for "
                            f"{detection['start']}"
                        )
                        break

            cut = edges[start_chunk]
            cursor = start_chunk
            crossed = 0
            while cursor > 0 and (extent.left_chunks is None or crossed < extent.left_chunks):
                if not _joinable(
                    text[edges[cursor - 1] : edges[cursor]],
                    extent.left_joins,
                    extent.left_join_chars,
                ):
                    break
                cursor -= 1
                crossed += 1
            window_start = edges[cursor]
            index = window_start - 1
            while index >= 0 and icu.Char.isUWhiteSpace(text[index]):
                index -= 1
            window_start = max(0, index - 1)
            shifted = [
                _shift_detection(item, window_start)
                for item in detector.detect(text[window_start:])
                if item["start"] + window_start >= cut
            ]
            if detection not in shifted:
                violations.append(f"{detector.type}: left context at {detection['start']}")
    return tuple(violations)


def _stock_bounded_extent(
    reader: object,
    chunks: int,
    *,
    numeric_left: bool = False,
    source: str,
) -> Extent:
    """Build a conservative bounded stock declaration from one reader's own state."""
    locale = getattr(reader, "locale", None)
    qualified = source
    if locale and str(locale) not in source:
        qualified = f"{source} {locale}"
    return Extent(
        chunks,
        source=qualified,
        left_chunks=None if numeric_left else 0,
        left_join_chars=_NUMBER_LEFT_CHARS if numeric_left else "",
    )


def _stock_unbounded_extent(
    reader: object,
    joins: Iterable[str] = (),
    *,
    join_chars: str = _NUMERIC_JOIN_CHARS,
    surfaces: Iterable[str] = (),
    numeric_left: bool = False,
    source: str,
) -> Extent:
    """Build a capped closing declaration from reader-owned vocabulary and symbols."""
    locale = getattr(reader, "locale", None)
    qualified = source
    if locale and str(locale) not in source:
        qualified = f"{source} {locale}"
    allowed = icu.UnicodeSet(join_chars)
    for surface in (*_owned_strings(vars(reader)), *surfaces):
        for character in surface:
            if (
                not icu.Char.isUWhiteSpace(character)
                and character not in _PUNCTUATION
                and character not in _LETTERS_MARKS
            ):
                allowed.add(character)
    return Extent(
        None,
        frozenset(word.casefold() for word in joins if word),
        allowed.toPattern(),
        DEFAULT_READER_CAP_CHARS,
        None if numeric_left else 0,
        frozenset(),
        _NUMBER_LEFT_CHARS if numeric_left else "",
        qualified,
    )


def _reader_words(reader: object) -> frozenset[str]:
    """Collect word tokens from the ICU-derived tables already owned by ``reader``."""
    words: set[str] = set()
    pending = list(vars(reader).values())
    seen: set[int] = set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if isinstance(value, str):
            words.update(_words(value))
        elif isinstance(value, Mapping):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (tuple, list, set, frozenset)):
            pending.extend(value)
        elif isinstance(value, Detector):
            pending.extend(vars(value).values())
    return frozenset(words)


def _sample_chunk_count(samples: Iterable[str]) -> int:
    """Return the maximum seam chunk count in non-empty formatter exemplars."""
    counts = [len(_seams(sample)) + 1 for sample in samples if sample]
    return max(counts, default=1)


def _owned_strings(value: object, seen: set[int] | None = None) -> tuple[str, ...]:
    """Harvest strings from one reader's Python-owned ICU-derived tables."""
    if seen is None:
        seen = set()
    if id(value) in seen:
        return ()
    seen.add(id(value))
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values = (*value.keys(), *value.values())
    elif isinstance(value, (tuple, list, set, frozenset)):
        values = tuple(value)
    elif isinstance(value, Detector):
        values = tuple(vars(value).values())
    else:
        return ()
    return tuple(string for child in values for string in _owned_strings(child, seen))


def _longest_surface(values: object, fallback: str) -> str:
    surfaces = _owned_strings(values)
    return max(
        surfaces,
        key=lambda value: (_sample_chunk_count((value,)), len(value)),
        default=fallback,
    )


def _date_structure_samples(reader: object) -> tuple[str, ...]:
    field_values = {
        "M": _longest_surface(getattr(reader, "_months", ()), "12"),
        "L": _longest_surface(getattr(reader, "_months", ()), "12"),
        "E": _longest_surface(getattr(reader, "_weekdays", ()), "Wednesday"),
        "e": _longest_surface(getattr(reader, "_weekdays", ()), "Wednesday"),
        "c": _longest_surface(getattr(reader, "_weekdays", ()), "Wednesday"),
        "G": _longest_surface(getattr(reader, "_eras", ()), "AD"),
        "Q": _longest_surface(getattr(reader, "_quarters", ()), "4"),
        "q": _longest_surface(getattr(reader, "_quarters", ()), "4"),
        "y": "99999",
        "Y": "99999",
        "d": "28",
        "D": "365",
    }
    samples = []
    for attribute in ("_structures", "_day_month_structures"):
        for structure in getattr(reader, attribute, ()):
            if not isinstance(structure, tuple) or len(structure) < 2:
                continue
            fields, separators = structure[:2]
            if not isinstance(fields, tuple) or not isinstance(separators, tuple):
                continue
            parts = []
            for index, field in enumerate(fields):
                parts.append(field_values.get(str(field), "23"))
                if index < len(separators):
                    parts.append(str(separators[index]))
            samples.append("".join(parts))
    for structure in getattr(reader, "_era_structures", ()):
        if not isinstance(structure, tuple) or len(structure) < 5:
            continue
        fields, separators, era_first, literal, _pattern = structure[:5]
        if not isinstance(fields, tuple) or not isinstance(separators, tuple):
            continue
        date_parts = []
        for index, field in enumerate(fields):
            date_parts.append(field_values.get(str(field), "23"))
            if index < len(separators):
                date_parts.append(str(separators[index]))
        date = "".join(date_parts)
        for era in getattr(reader, "_eras", ()):
            if not era or not isinstance(era[0], str):
                continue
            samples.append(f"{era[0]}{literal}{date}" if era_first else f"{date}{literal}{era[0]}")
    # FlexibleTextDateDetector has an independent era/year lane even when CLDR gives
    # it no textual month-date structures.  Its matcher requires exactly one space
    # and accepts one through four locale digits beside every reader-owned era form.
    eras = getattr(reader, "_eras", ())
    era_first = getattr(reader, "_era_first", None)
    digits = getattr(reader, "_digits", {})
    if eras and isinstance(era_first, bool) and isinstance(digits, Mapping):
        inverse = {value: character for character, value in digits.items()}
        year = "".join(inverse.get(value, str(value)) for value in (9, 9, 9, 9))
        for era in eras:
            if not era or not isinstance(era[0], str):
                continue
            samples.append(f"{era[0]} {year}" if era_first else f"{year} {era[0]}")
    return tuple(samples)


@lru_cache(maxsize=256)
def _calendar_symbol_surfaces(locale: str) -> tuple[str, ...]:
    """Return the complete ICU name tables used by canonical calendar patterns."""
    symbols = icu.DateFormatSymbols(icu.Locale(locale))
    surfaces = [*symbols.getEras(), *symbols.getEraNames(), *symbols.getAmPmStrings()]
    # Date/time pattern fields choose one of these context/width tables. Reading the
    # tables themselves is exhaustive for the grammar; unlike formatting sample dates,
    # it does not guess a maximum from a finite selection of calendar values.
    for context in (symbols.FORMAT, symbols.STANDALONE):
        for width in (symbols.WIDE, symbols.ABBREVIATED, symbols.NARROW):
            surfaces.extend(symbols.getMonths(context, width))
            surfaces.extend(symbols.getWeekdays(context, width))
    return tuple(dict.fromkeys(str(surface) for surface in surfaces if surface))


@lru_cache(maxsize=256)
def _calendar_vocabulary_instants(locale: str) -> tuple[object, ...]:
    """Enumerate the finite calendar fields that can change formatted word tokens."""
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
    found = []

    def add(year: int, month: int, day: int, hour: int = 13, era: int | None = None) -> None:
        calendar.clear()
        if era is not None:
            calendar.set(icu.UCalendarDateFields.ERA, era)
        calendar.set(year, month, day, hour, 5, 7)
        found.append(calendar.getTime())

    # Month/quarter, weekday, day-period, and era are the only finite fields that can
    # change word vocabulary. Years/days/times themselves are numeric and are handled by
    # join_chars. This enumeration is used only for the closing vocabulary, never to fit
    # a seam-count bound.
    for month in range(12):
        add(2024, month, 15)
    for day in range(1, 8):
        add(2024, 0, day)
    for hour in range(24):
        add(2024, 0, 2, hour)
    for era in range(calendar.getMaximum(icu.UCalendarDateFields.ERA) + 1):
        add(44, 2, 15, era=era)
    return tuple(found)


def _calendar_closing_surfaces(reader: object) -> tuple[str, ...]:
    """Return complete symbol and formatter word surfaces for an unbounded reader."""
    locale = getattr(reader, "locale", "")
    surfaces = list(_calendar_symbol_surfaces(locale))
    formatters = []
    formatter = getattr(reader, "_df", None)
    if formatter is not None:
        formatters.append(formatter)
    for matcher in getattr(reader, "_matchers", ()):
        if len(matcher) >= 3:
            formatters.extend((matcher[0], matcher[2]))
    for owned in formatters:
        surfaces.extend(
            str(owned.format(instant)) for instant in _calendar_vocabulary_instants(locale)
        )
    return tuple(dict.fromkeys(surface for surface in surfaces if surface))


def _temporal_zone_surfaces(reader: object) -> tuple[str, ...]:
    """Return every language-level zone surface a temporal reader can consume."""
    if type(reader).__name__ not in {
        "FlexibleDateIntervalDetector",
        "FlexibleTimeDetector",
        "FlexibleBareHourDetector",
        "FlexibleDateTimeDetector",
    }:
        return ()
    locale = getattr(reader, "locale", "")
    if not locale:
        return ()
    from .recognize import _language_zone_abbreviations, _language_zone_names

    language = icu.Locale(locale).getLanguage()
    locales = getattr(reader, "locales", None)
    forms = (
        *_language_zone_names(language, locales),
        *_language_zone_abbreviations(language, locales),
    )
    return tuple(forms)


def _temporal_samples(reader: object) -> tuple[str, ...]:
    """Build exhaustive surfaces for the remaining statically bounded readers."""
    name = type(reader).__name__
    if name in {
        "FlexibleDateDetector",
        "FlexibleTextDateDetector",
        "FlexibleShortYearDateDetector",
    }:
        return _date_structure_samples(reader)
    if name in {"FlexibleMonthNameDetector", "FlexibleWeekdayNameDetector"}:
        return tuple(
            item[0] for item in getattr(reader, "_names", ()) if item and isinstance(item[0], str)
        )
    return _owned_strings(vars(reader))


def _ordinal_affix_words(reader: object) -> frozenset[str]:
    """Return the RBNF affix vocabulary the ordinal reader probes and accepts."""
    affixes = getattr(reader, "_affixes", None)
    if not callable(affixes):
        return frozenset()
    values = (*range(1, 121), 1000, 1001, 10000, 100000)
    surfaces = (
        surface for value in values for pair in affixes(value) for surface in pair if surface
    )
    return frozenset(word for surface in surfaces for word in _words(surface))


def _extent_for_reader(reader: object) -> Extent:
    """Return a reader-local cached declaration derived by the helper below."""
    cached = getattr(reader, "_stream_extent", None)
    if isinstance(cached, Extent):
        return cached
    extent = _derive_extent_for_reader(reader)
    try:
        object.__setattr__(reader, "_stream_extent", extent)
    except (AttributeError, TypeError):
        pass
    return extent


def _derive_extent_for_reader(reader: object) -> Extent:
    """Derive the stock policy for a reader from its own ICU/material state.

    The class split mirrors the adjudicated table.  Locale-sensitive content is never
    typed here: word joins come from the instantiated reader's formatter-derived tables,
    lexicon, rule text, symbols, or unit surfaces.
    """
    name = type(reader).__name__
    words = _reader_words(reader)
    numeric_left = name not in {
        "AbbreviationDetector",
        "AlphanumericRunsDetector",
        "LetterNameDetector",
        "SingleLetterWordDetector",
        "FlexibleMonthNameDetector",
        "FlexibleWeekdayNameDetector",
        "FlexibleSpelloutDetector",
        "MaterialSpelloutDetector",
        "FlexibleLoneSpelloutDetector",
        "MaterialLoneSpelloutDetector",
    }
    one_chunk = {
        "LetterNameDetector",
        "AlphanumericRunsDetector",
        "PluralNumeralDetector",
        "SingleLetterWordDetector",
        "FlexibleLowercaseRomanDetector",
    }
    unbounded = {
        "FlexibleNumberDetector",
        "FlexibleSpelloutDetector",
        "MaterialSpelloutDetector",
        "FlexibleLoneSpelloutDetector",
        "MaterialLoneSpelloutDetector",
        "FlexibleCompactDetector",
        "FlexibleScientificDetector",
        "FlexibleCurrencyDetector",
        "FlexibleCurrencyNameDetector",
        "FlexiblePercentDetector",
        "FlexibleMeasureDetector",
        "FlexibleMixedMeasureDetector",
        "FlexibleNumericDurationDetector",
        "FlexibleFractionDetector",
        "FlexibleOrdinalDetector",
        "FlexibleNumberRangeDetector",
    }
    # These grammars have no sound fixed seam count: strict numbers admit arbitrary
    # digit/group runs; relative dates embed that number grammar; intervals compose two
    # independent sides; and time/date-time readers may append any accepted zone form.
    # DateDetector delegates to ICU parsing, whose accepted canonical field widths are
    # not bounded by a finite set of formatted calendar probes. They therefore use a
    # reader-data closing condition and the configurable reader cap.
    grammar_unbounded = {
        "FlexibleDateIntervalDetector",
        "FlexibleRelativeDateDetector",
        "FlexibleTimeDetector",
        "FlexibleBareHourDetector",
        "FlexibleDateTimeDetector",
    }
    if name == "NumberDetector":
        symbols = reader._nf.getDecimalFormatSymbols()
        exponent = symbols.getSymbol(icu.DecimalFormatSymbols.kExponentialSymbol)
        number_surfaces = (
            reader._decimal,
            reader._grouping,
            reader._zero,
            reader._minus,
            reader._plus,
            reader._currency_symbol,
            reader._percent,
            exponent,
        )
        return _stock_unbounded_extent(
            reader,
            frozenset(word for surface in number_surfaces for word in _words(surface)),
            surfaces=number_surfaces,
            numeric_left=True,
            source=(
                f"NumberDetector grammar with ICU DecimalFormatSymbols {reader.locale}; "
                "closes at the first non-number/symbol chunk"
            ),
        )
    if name == "DateDetector":
        surfaces = _calendar_closing_surfaces(reader)
        return _stock_unbounded_extent(
            reader,
            words | frozenset(word for surface in surfaces for word in _words(surface)),
            surfaces=surfaces,
            numeric_left=True,
            source=(
                f"ICU SimpleDateFormat pattern and complete DateFormatSymbols {reader.locale}; "
                "closes outside the pattern vocabulary"
            ),
        )
    if name == "AbbreviationDetector":
        surfaces = tuple(getattr(reader, "_surfaces", ()))
        return Extent(
            _sample_chunk_count(surfaces),
            frozenset(word for surface in surfaces for word in _words(surface)),
            source=f"compiled abbreviation lexicon {getattr(reader, 'locale', '')}",
        )
    if name in one_chunk:
        return _stock_bounded_extent(
            reader,
            1,
            numeric_left=name == "PluralNumeralDetector",
            source="single ICU word",
        )
    if name in unbounded:
        if name == "FlexibleOrdinalDetector":
            # The reader derives its maximum prefix and all ordinal plural categories
            # from this same RBNF probe set. Reuse that accepted pattern vocabulary for
            # streaming instead of inferring suffixes from observed corpus rows.
            words |= _ordinal_affix_words(reader)
        return _stock_unbounded_extent(
            reader,
            words,
            join_chars=_NUMERIC_JOIN_CHARS,
            numeric_left=numeric_left,
            source="reader-owned ICU symbols, rule text, and material surfaces",
        )
    if name in grammar_unbounded:
        calendar_surfaces = _calendar_closing_surfaces(reader)
        zone_surfaces = _temporal_zone_surfaces(reader)
        surfaces = (*calendar_surfaces, *zone_surfaces)
        return _stock_unbounded_extent(
            reader,
            words | frozenset(word for surface in surfaces for word in _words(surface)),
            surfaces=surfaces,
            numeric_left=numeric_left,
            source=(
                "reader grammar plus complete ICU calendar and reader-owned zone vocabulary; "
                "closes at the first chunk outside that vocabulary"
            ),
        )
    # The remaining date/name readers have fixed field sequences, fixed numeric widths,
    # and finite reader-owned name tables. Selecting each field's maximum seam count is
    # compositional: fields are independent and literal separators are fixed, so the sum
    # bounds every spelling accepted by the matcher rather than a sampled corpus.
    samples = _temporal_samples(reader)
    if name in {"FlexibleMonthNameDetector", "FlexibleWeekdayNameDetector"}:
        # These readers suppress names that overlap their child text-date reader, so
        # their left declaration must include the child's numeric context as well.
        numeric_left = True
    return Extent(
        _sample_chunk_count(samples),
        words
        | frozenset(word for sample in samples for word in _words(sample))
        | frozenset(
            word for surface in _temporal_zone_surfaces(reader) for word in _words(surface)
        ),
        _NUMERIC_JOIN_CHARS,
        left_chunks=None if numeric_left else 0,
        left_join_chars=_NUMBER_LEFT_CHARS if numeric_left else "",
        source=(
            f"reader-owned ICU formatter/name exemplars {getattr(reader, 'locale', '')}: "
            f"{len(samples)} surfaces"
        ),
    )
