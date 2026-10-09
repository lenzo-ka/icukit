"""Bounded detection over boundary-delimited text supplied in arbitrary chunks.

The default paragraph mode holds an open paragraph and runs the gang's ordinary
whole-text :meth:`~icukit.detectors.DetectorSet.detect` exactly once when that
paragraph closes. Stock readers do not cross paragraph boundaries, so no-cut output
is identical to whole-text detection with only absolute-offset shifts. Line mode is a
lower-latency option; a wrapped number range may cross one line break, so line mode is
not guaranteed to preserve whole-text identity. Explicit mode settles only at
:meth:`DetectionStream.flush`, :meth:`DetectionStream.boundary`, or close.

An open segment is length-bounded by ``max_pending_chars`` (4096 by default). When no
configured boundary closes it in time, the stream detects and cuts a prefix at the
last available whitespace boundary, then a grapheme boundary, with a code-point cut
only when one overlong grapheme leaves no positive grapheme boundary within the hard
cap. Such cuts are deterministic functions of the text, and detections ending at a
cut are marked ``truncated``.
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

    ``cuts`` contains safety-cut offsets. ``reader_cuts`` remains in the result shape
    for compatibility; boundary segmentation has no per-reader cuts, so it is empty.
    """

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
    for detection in sorted(detections, key=_sort_key):
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
        self._closed = False
        self._window_detect_count = 0

    @property
    def window_detect_count(self) -> int:
        """Number of settled segments passed once to whole-text detection."""
        return self._window_detect_count

    def _detect(self, text: str) -> list[ValueDetection]:
        self._window_detect_count += 1
        try:
            found = self._source.detect(text)  # type: ignore[union-attr]
        except DetectorRefusal as error:
            endpoint_offset = (
                self._pending_from
                if error.reason == "mid-grapheme-endpoint"
                else self._pending_u16_from
            )
            endpoint = None if error.endpoint is None else error.endpoint + endpoint_offset
            raise DetectorRefusal(
                error.type,
                error.start + self._pending_from,
                endpoint,
                error.reason,
                _REFUSAL_MESSAGES[error.reason],
            ) from None
        return [_shift_detection(item, self._pending_from) for item in found]

    def _drop(self, end: int) -> None:
        discarded = self._text[:end]
        self._text = self._text[end:]
        self._pending_from += len(discarded)
        self._pending_u16_from += len(discarded.encode("utf-16-le")) // 2

    def _settle(self, end: int, *, cut: bool) -> list[ValueDetection]:
        found = self._detect(self._text[:end])
        if cut:
            absolute_end = self._pending_from + end
            found = [_truncated(item) if item["end"] == absolute_end else item for item in found]
        self._drop(end)
        return found

    def _safe_cut(self) -> int:
        """Choose a deterministic positive cut no later than the hard cap."""
        limit = self._max_pending
        probe = self._text[: limit + 1]
        graphemes = tuple(edge for edge in _grapheme_boundaries(probe) if 0 < edge <= limit)
        whitespace = tuple(
            edge
            for edge in graphemes
            if probe[edge - 1].isspace() and (edge == len(probe) or not probe[edge].isspace())
        )
        if whitespace:
            return whitespace[-1]
        if graphemes:
            return graphemes[-1]
        # A single grapheme can be arbitrarily long. The mandatory length bound wins
        # only in that pathological case; Python indices are code-point boundaries.
        return limit

    def _drain(self) -> tuple[list[ValueDetection], list[int]]:
        emitted: list[ValueDetection] = []
        cuts: list[int] = []
        while self._text:
            ends = _boundary_ends(self._text, self._boundary)
            boundary_end = ends[0] if ends else None
            if boundary_end is not None and boundary_end <= self._max_pending:
                emitted.extend(self._settle(boundary_end, cut=False))
                continue
            if len(self._text) <= self._max_pending:
                break
            cut = self._safe_cut()
            emitted.extend(self._settle(cut, cut=True))
            cuts.append(self._pending_from)
        return _deduplicate(emitted), cuts

    def feed(self, chunk: str, /) -> DetectionBatch:
        """Append ``chunk`` and return detections from newly closed segments."""
        if self._closed:
            raise RuntimeError("detection stream is closed")
        if not isinstance(chunk, str):
            raise TypeError("chunk must be str")
        self._text += chunk
        self._total += len(chunk)
        detections, cuts = self._drain()
        return DetectionBatch(tuple(detections), self._pending_from, tuple(cuts))

    def flush(self) -> DetectionBatch:
        """Settle the open segment without marking or recording a safety cut."""
        if self._closed:
            raise RuntimeError("detection stream is closed")
        found = self._detect(self._text) if self._text else []
        self._drop(len(self._text))
        return DetectionBatch(tuple(found), self._pending_from)

    def boundary(self) -> DetectionBatch:
        """Mark an explicit boundary; equivalent to :meth:`flush`."""
        return self.flush()

    def close(self) -> DetectionBatch:
        """Flush once and close; repeated calls return an empty final batch."""
        if self._closed:
            return DetectionBatch((), self._total)
        batch = self.flush()
        self._closed = True
        return batch

    def pending(self) -> StreamPending:
        """Return the current absolute settlement and retention positions."""
        return StreamPending(
            pending_from=self._pending_from,
            decided_through=self._pending_from,
            buffered_from=self._pending_from,
            total=self._total,
            open_chunk=self._pending_from if self._text else None,
        )
