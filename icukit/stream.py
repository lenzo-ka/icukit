"""Bounded detection over boundary-delimited text supplied in arbitrary chunks.

The default paragraph mode holds an open paragraph and runs the gang's ordinary
whole-text :meth:`~icukit.detectors.DetectorSet.detect` exactly once when that
paragraph closes. Stock readers do not cross paragraph boundaries, so no-cut output
is identical to whole-text detection with only absolute-offset shifts. A third-party
reader has that guarantee only when its detections are context-independent across the
selected boundary grammar: adding text beyond a boundary cannot create, remove, or
change a detection on the other side. Line mode is a lower-latency option; a wrapped
number range may cross one line break, so line mode is not guaranteed to preserve
whole-text identity. Explicit mode settles only at :meth:`DetectionStream.flush`,
:meth:`DetectionStream.boundary`, or close.

An open segment is length-bounded by ``max_pending_chars`` (4096 by default). When no
configured boundary closes it in time, the stream examines the fixed cap-length
prefix and cuts at its last grapheme edge immediately following whitespace, then at
its last grapheme edge, with a code-point cut only when one overlong grapheme leaves
no positive grapheme boundary within the hard cap. Such cuts are deterministic
functions of the text. Caller-imposed :meth:`DetectionStream.flush` boundaries are
also cuts. Detections starting or ending at any cut are marked ``truncated``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Literal, TypedDict

import icu

from ._offsets import boundary_maps
from .detectors import Detector, DetectorRefusal, DetectorSet, ValueDetection, _sort_key

DEFAULT_MAX_PENDING_CHARS: int = 4096
BoundaryMode = Literal["paragraph", "line", "explicit"]

_PARAGRAPH_BOUNDARY = re.compile(r"(?:\r\n|\n)[ \t]*(?:\r\n|\n)|\u2029")
_LINE_BOUNDARY = re.compile(r"\r\n|[\r\n\u2028\u2029]")
_REFUSAL_MESSAGES = {
    "reversed-endpoint": "parse ended before its start",
    "out-of-range-endpoint": "parse ended beyond the end of the text",
    "surrogate-interior-endpoint": "parse ended inside a surrogate pair",
    "mid-grapheme-endpoint": "parse ended inside a grapheme cluster",
}


@dataclass(frozen=True)
class DetectionBatch:
    """Detections settled by one call and the absolute open-segment start.

    ``cuts`` contains cap and caller-imposed boundary offsets.
    """

    detections: tuple[ValueDetection, ...]
    pending_from: int
    cuts: tuple[int, ...] = ()


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


def _shift_detection(detection: ValueDetection, offset: int) -> ValueDetection:
    """Shift one detection and its captures by an absolute code-point offset."""
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
    for detection in detections:
        key = repr(detection)
        if key not in seen:
            seen.add(key)
            result.append(detection)
    return result


def _grapheme_boundaries(text: str) -> tuple[int, ...]:
    iterator = icu.BreakIterator.createCharacterInstance(icu.Locale.getRoot())
    iterator.setText(text)
    _cp_to_u16, u16_to_cp = boundary_maps(text)
    return tuple(u16_to_cp[end] for end in iterator)


def _boundary_ends(text: str, mode: BoundaryMode, *, final: bool = False) -> tuple[int, ...]:
    """Return configured boundary ends in ``text``.

    A final CR is held in line mode until the next feed says whether it begins CRLF.
    ``final=True`` is used only by the premise helper, where the input is complete.
    """
    if mode == "explicit":
        return ()
    pattern = _PARAGRAPH_BOUNDARY if mode == "paragraph" else _LINE_BOUNDARY
    ends = []
    for match in pattern.finditer(text):
        if mode == "line" and not final and match.group() == "\r" and match.end() == len(text):
            continue
        ends.append(match.end())
    return tuple(ends)


def _boundary_violations(
    text: str,
    detections: Iterable[ValueDetection],
    mode: BoundaryMode = "paragraph",
) -> tuple[str, ...]:
    """Return compact witnesses for detections crossing configured boundaries."""
    ends = _boundary_ends(text, mode, final=True)
    return tuple(
        f"{item['type']}:{item['start']}:{item['end']}@{boundary}"
        for item in detections
        for boundary in ends
        if item["start"] < boundary < item["end"]
    )


class DetectionStream:
    """Incrementally detect closed segments with bounded retention and absolute offsets.

    ``boundary`` selects ``"paragraph"`` (the identity-preserving default for stock
    readers), ``"line"`` (lower latency without an identity guarantee), or
    ``"explicit"`` (only :meth:`flush`, :meth:`boundary`, and :meth:`close` settle).
    The chunk passed to :meth:`feed` is appended before boundaries and cap cuts are
    drained, so it can transiently exceed the configured cap during that call.
    """

    def __init__(
        self,
        detectors: DetectorSet | object | Iterable[Detector],
        /,
        *,
        max_pending_chars: int = DEFAULT_MAX_PENDING_CHARS,
        boundary: BoundaryMode = "paragraph",
    ) -> None:
        if (
            not isinstance(max_pending_chars, int)
            or isinstance(max_pending_chars, bool)
            or max_pending_chars <= 0
        ):
            raise ValueError("max_pending_chars must be a positive int")
        if boundary not in {"paragraph", "line", "explicit"}:
            raise ValueError("boundary must be 'paragraph', 'line', or 'explicit'")
        detector_tuple = _detector_tuple(detectors)
        self._source = (
            detectors
            if callable(getattr(detectors, "detect", None))
            else DetectorSet(detector_tuple)
        )
        self._max_pending = max_pending_chars
        self._boundary: BoundaryMode = boundary
        self._text = ""
        self._total = 0
        self._pending_from = 0
        self._pending_u16_from = 0
        self._left_cut = False
        self._closed = False
        self._window_detect_count = 0

    @property
    def window_detect_count(self) -> int:
        """Number of settled segments passed once to whole-text detection."""
        return self._window_detect_count

    def _detect(
        self,
        text: str,
        pending_from: int,
        pending_u16_from: int,
    ) -> list[ValueDetection]:
        try:
            found = self._source.detect(text)  # type: ignore[union-attr]
        except DetectorRefusal as error:
            endpoint_offset = (
                pending_from if error.reason == "mid-grapheme-endpoint" else pending_u16_from
            )
            endpoint = None if error.endpoint is None else error.endpoint + endpoint_offset
            raise DetectorRefusal(
                error.type,
                error.start + pending_from,
                endpoint,
                error.reason,
                _REFUSAL_MESSAGES[error.reason],
            ) from None
        shifted = [_shift_detection(item, pending_from) for item in found]
        shifted.sort(key=_sort_key)
        return shifted

    @staticmethod
    def _mark_cut_edges(
        found: list[ValueDetection],
        start: int,
        end: int,
        *,
        left_cut: bool,
        right_cut: bool,
    ) -> list[ValueDetection]:
        if not left_cut and not right_cut:
            return found
        return [
            _truncated(item)
            if (left_cut and item["start"] == start) or (right_cut and item["end"] == end)
            else item
            for item in found
        ]

    def _safe_cut(self, text: str, start: int) -> int:
        """Choose a deterministic positive cut no later than the hard cap."""
        limit = self._max_pending
        probe = text[start : start + limit]
        graphemes = tuple(edge for edge in _grapheme_boundaries(probe) if edge > 0)
        whitespace = tuple(edge for edge in graphemes if probe[edge - 1].isspace())
        if whitespace:
            return whitespace[-1]
        if graphemes:
            return graphemes[-1]
        # A single grapheme can be arbitrarily long. The mandatory length bound wins
        # only in that pathological case; Python indices are code-point boundaries.
        return limit

    def _drain(
        self,
        text: str,
    ) -> tuple[list[ValueDetection], list[int], int, int, bool, int]:
        """Detect closed prefixes without mutating stream state."""
        emitted: list[ValueDetection] = []
        cuts: list[int] = []
        cursor = 0
        consumed_u16 = 0
        left_cut = self._left_cut
        detect_count = 0
        boundary_ends = _boundary_ends(text, self._boundary)
        boundary_index = 0
        while cursor < len(text):
            boundary_end = (
                boundary_ends[boundary_index] if boundary_index < len(boundary_ends) else None
            )
            if boundary_end is not None and boundary_end - cursor <= self._max_pending:
                segment = text[cursor:boundary_end]
                absolute_start = self._pending_from + cursor
                absolute_end = self._pending_from + boundary_end
                found = self._detect(
                    segment,
                    absolute_start,
                    self._pending_u16_from + consumed_u16,
                )
                detect_count += 1
                emitted.extend(
                    self._mark_cut_edges(
                        found,
                        absolute_start,
                        absolute_end,
                        left_cut=left_cut,
                        right_cut=False,
                    )
                )
                consumed_u16 += len(segment.encode("utf-16-le")) // 2
                cursor = boundary_end
                boundary_index += 1
                left_cut = False
                continue
            if len(text) - cursor <= self._max_pending:
                break
            cut = self._safe_cut(text, cursor)
            cut_end = cursor + cut
            segment = text[cursor:cut_end]
            absolute_start = self._pending_from + cursor
            absolute_end = self._pending_from + cut_end
            found = self._detect(
                segment,
                absolute_start,
                self._pending_u16_from + consumed_u16,
            )
            detect_count += 1
            emitted.extend(
                self._mark_cut_edges(
                    found,
                    absolute_start,
                    absolute_end,
                    left_cut=left_cut,
                    right_cut=True,
                )
            )
            consumed_u16 += len(segment.encode("utf-16-le")) // 2
            cursor = cut_end
            cuts.append(absolute_end)
            left_cut = True
        return _deduplicate(emitted), cuts, cursor, consumed_u16, left_cut, detect_count

    def feed(self, chunk: str, /) -> DetectionBatch:
        """Append ``chunk`` and return detections from newly closed segments."""
        if self._closed:
            raise RuntimeError("detection stream is closed")
        if not isinstance(chunk, str):
            raise TypeError("chunk must be str")
        text = self._text + chunk
        detections, cuts, consumed, consumed_u16, left_cut, detect_count = self._drain(text)
        self._text = text[consumed:]
        self._total += len(chunk)
        self._pending_from += consumed
        self._pending_u16_from += consumed_u16
        self._left_cut = left_cut
        self._window_detect_count += detect_count
        return DetectionBatch(tuple(detections), self._pending_from, tuple(cuts))

    def flush(self) -> DetectionBatch:
        """Settle at a caller-imposed cut and mark detections touching either side."""
        if self._closed:
            raise RuntimeError("detection stream is closed")
        end = self._pending_from + len(self._text)
        if self._text:
            found = self._detect(self._text, self._pending_from, self._pending_u16_from)
            found = self._mark_cut_edges(
                found,
                self._pending_from,
                end,
                left_cut=self._left_cut,
                right_cut=True,
            )
            consumed_u16 = len(self._text.encode("utf-16-le")) // 2
            self._window_detect_count += 1
        else:
            found = []
            consumed_u16 = 0
        self._text = ""
        self._pending_from = end
        self._pending_u16_from += consumed_u16
        self._left_cut = True
        return DetectionBatch(tuple(found), self._pending_from, (end,))

    def boundary(self) -> DetectionBatch:
        """Mark an explicit boundary; equivalent to :meth:`flush`."""
        return self.flush()

    def close(self) -> DetectionBatch:
        """Settle at end of input and close; repeated calls return an empty batch."""
        if self._closed:
            return DetectionBatch((), self._total)
        end = self._pending_from + len(self._text)
        if self._text:
            found = self._detect(self._text, self._pending_from, self._pending_u16_from)
            found = self._mark_cut_edges(
                found,
                self._pending_from,
                end,
                left_cut=self._left_cut,
                right_cut=False,
            )
            consumed_u16 = len(self._text.encode("utf-16-le")) // 2
            self._window_detect_count += 1
        else:
            found = []
            consumed_u16 = 0
        self._text = ""
        self._pending_from = end
        self._pending_u16_from += consumed_u16
        self._left_cut = False
        self._closed = True
        return DetectionBatch(tuple(found), self._pending_from)

    def pending(self) -> StreamPending:
        """Return the current absolute settlement and retention positions."""
        return StreamPending(
            pending_from=self._pending_from,
            decided_through=self._pending_from,
            buffered_from=self._pending_from,
            total=self._total,
            open_chunk=self._pending_from if self._text else None,
        )
