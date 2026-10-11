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

Optional reflow substitutes selected terminators with spaces before boundary selection
and detection. The view has the same code-point length as the source: offsets,
detection ``text``, and capture ``text`` describe the original input, while values and
specs are interpretations of the substituted view. Reflow decisions add at most their
documented 1,024-code-point forward hold to the ordinary pending-segment bound.

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
from ._reflow_stream import IncrementalReflow
from .detectors import Detector, DetectorRefusal, DetectorSet, ValueDetection, _sort_key
from .reflow import ReflowMode, _validate_mode

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


def _restore_surfaces(detection: ValueDetection, source: str) -> ValueDetection:
    """Restore original source surfaces after detection on a substituted view."""
    result = dict(detection)
    result["text"] = source[detection["start"] : detection["end"]]
    result["captures"] = tuple(
        replace(capture, text=source[capture.start : capture.end])
        for capture in detection["captures"]
    )
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
    ``reflow`` selects the equal-length view used for both boundaries and detection;
    public surfaces remain slices of the original input.
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
        reflow: ReflowMode = "none",
    ) -> None:
        if (
            not isinstance(max_pending_chars, int)
            or isinstance(max_pending_chars, bool)
            or max_pending_chars <= 0
        ):
            raise ValueError("max_pending_chars must be a positive int")
        if boundary not in {"paragraph", "line", "explicit"}:
            raise ValueError("boundary must be 'paragraph', 'line', or 'explicit'")
        _validate_mode(reflow)
        detector_tuple = _detector_tuple(detectors)
        self._source = (
            detectors
            if callable(getattr(detectors, "detect", None))
            else DetectorSet(detector_tuple)
        )
        self._max_pending = max_pending_chars
        self._boundary: BoundaryMode = boundary
        self._reflow = None if reflow == "none" else IncrementalReflow(reflow)
        self._text = ""
        self._view = ""
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
        original: str | None = None,
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
        if original is not None:
            found = [_restore_surfaces(item, original) for item in found]
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
        view: str | None = None,
    ) -> tuple[list[ValueDetection], list[int], int, int, bool, int]:
        """Detect closed prefixes without mutating stream state."""
        detecting_text = text if view is None else view
        if len(detecting_text) != len(text):
            raise AssertionError("reflow view must preserve source length")
        emitted: list[ValueDetection] = []
        cuts: list[int] = []
        cursor = 0
        consumed_u16 = 0
        left_cut = self._left_cut
        detect_count = 0
        boundary_ends = _boundary_ends(detecting_text, self._boundary)
        boundary_index = 0
        while cursor < len(text):
            boundary_end = (
                boundary_ends[boundary_index] if boundary_index < len(boundary_ends) else None
            )
            if boundary_end is not None and boundary_end - cursor <= self._max_pending:
                segment = detecting_text[cursor:boundary_end]
                original = None if view is None else text[cursor:boundary_end]
                absolute_start = self._pending_from + cursor
                absolute_end = self._pending_from + boundary_end
                found = self._detect(
                    segment,
                    absolute_start,
                    self._pending_u16_from + consumed_u16,
                    original,
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
            if len(detecting_text) - cursor <= self._max_pending:
                break
            cut = self._safe_cut(detecting_text, cursor)
            cut_end = cursor + cut
            segment = detecting_text[cursor:cut_end]
            original = None if view is None else text[cursor:cut_end]
            absolute_start = self._pending_from + cursor
            absolute_end = self._pending_from + cut_end
            found = self._detect(
                segment,
                absolute_start,
                self._pending_u16_from + consumed_u16,
                original,
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
        if self._reflow is None:
            text = self._text + chunk
            view = None
            next_reflow = None
        else:
            next_reflow = self._reflow.clone()
            source_chunk, view_chunk = next_reflow.feed(chunk)
            text = self._text + source_chunk
            view = self._view + view_chunk
        detections, cuts, consumed, consumed_u16, left_cut, detect_count = self._drain(text, view)
        self._text = text[consumed:]
        if view is not None:
            self._view = view[consumed:]
            self._reflow = next_reflow
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
        if self._reflow is None:
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

        next_reflow = self._reflow.clone()
        text = self._text
        source_chunk, view_chunk = next_reflow.flush()
        text += source_chunk
        view = self._view + view_chunk
        end = self._pending_from + len(text)
        found, cuts, consumed, consumed_u16, left_cut, detect_count = self._drain(text, view)
        remaining = text[consumed:]
        remaining_view = None if view is None else view[consumed:]
        if remaining:
            tail = self._detect(
                remaining if remaining_view is None else remaining_view,
                self._pending_from + consumed,
                self._pending_u16_from + consumed_u16,
                None if remaining_view is None else remaining,
            )
            tail = self._mark_cut_edges(
                tail,
                self._pending_from + consumed,
                end,
                left_cut=left_cut,
                right_cut=True,
            )
            found.extend(tail)
            detect_count += 1
        consumed_u16 = len(text.encode("utf-16-le")) // 2
        self._window_detect_count += detect_count
        self._text = ""
        self._view = ""
        self._reflow = next_reflow
        self._pending_from = end
        self._pending_u16_from += consumed_u16
        self._left_cut = True
        return DetectionBatch(tuple(found), self._pending_from, (*cuts, end))

    def boundary(self) -> DetectionBatch:
        """Mark an explicit boundary; equivalent to :meth:`flush`."""
        return self.flush()

    def close(self) -> DetectionBatch:
        """Settle at end of input and close; repeated calls return an empty batch."""
        if self._closed:
            return DetectionBatch((), self._total)
        if self._reflow is None:
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

        next_reflow = self._reflow.clone()
        text = self._text
        source_chunk, view_chunk = next_reflow.close()
        text += source_chunk
        view = self._view + view_chunk
        end = self._pending_from + len(text)
        found, cuts, consumed, consumed_u16, left_cut, detect_count = self._drain(text, view)
        remaining = text[consumed:]
        remaining_view = None if view is None else view[consumed:]
        if remaining:
            tail = self._detect(
                remaining if remaining_view is None else remaining_view,
                self._pending_from + consumed,
                self._pending_u16_from + consumed_u16,
                None if remaining_view is None else remaining,
            )
            tail = self._mark_cut_edges(
                tail,
                self._pending_from + consumed,
                end,
                left_cut=left_cut,
                right_cut=False,
            )
            found.extend(tail)
            detect_count += 1
        consumed_u16 = len(text.encode("utf-16-le")) // 2
        self._window_detect_count += detect_count
        self._text = ""
        self._view = ""
        self._reflow = next_reflow
        self._pending_from = end
        self._pending_u16_from += consumed_u16
        self._left_cut = False
        self._closed = True
        return DetectionBatch(tuple(found), self._pending_from, tuple(cuts))

    def pending(self) -> StreamPending:
        """Return the current absolute settlement and retention positions."""
        buffered_from = self._pending_from
        has_open = bool(self._text)
        if self._reflow is not None:
            buffered_from = min(buffered_from, self._reflow.buffered_from)
            has_open = has_open or self._reflow.fed_through < self._total
        return StreamPending(
            pending_from=self._pending_from,
            decided_through=self._pending_from,
            buffered_from=buffered_from,
            total=self._total,
            open_chunk=self._pending_from if has_open else None,
        )
