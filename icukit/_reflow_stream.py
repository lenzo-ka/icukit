"""Bounded incremental production of an equal-length reflow view."""

from __future__ import annotations

from bisect import bisect_right
from copy import copy

from .reflow import (
    _HORIZONTAL_SPACE,
    _REFLOW_HOLD_CHARS,
    ReflowMode,
    _auto_uses_lines,
    _lines,
    _substitute,
    _trim_horizontal,
)


class IncrementalReflow:
    """Emit source and substituted prefixes once their reflow decisions settle."""

    def __init__(self, mode: ReflowMode) -> None:
        self.mode = mode
        self._text = ""
        self._base_offset = 0
        self._total_length = 0
        self._segment_start = 0
        self._fed = 0
        self._closed = False
        self._block_starts = [0]
        self._block_scan = 0
        self._last_terminator_end: int | None = None
        self._only_horizontal_after_terminator = False
        self._leading_auto_start = 0
        self._leading_auto_mode: ReflowMode | None = None

    @property
    def buffered_from(self) -> int:
        """Absolute start of source retained for bounded reflow context."""
        return self._base_offset

    @property
    def fed_through(self) -> int:
        """Absolute end of the source already emitted in substituted form."""
        return self._fed

    def clone(self) -> IncrementalReflow:
        """Return an independent cheap copy for transactional stream updates."""
        result = copy(self)
        result._block_starts = self._block_starts.copy()
        return result

    def _char(self, position: int) -> str:
        return self._text[position - self._base_offset]

    def _slice(self, start: int, end: int) -> str:
        return self._text[start - self._base_offset : end - self._base_offset]

    def _scan_blocks(self) -> None:
        """Record auto-mode block starts while scanning each source code point once."""
        index = self._block_scan
        while index < self._total_length:
            char = self._char(index)
            if char == "\n" and index > self._base_offset and self._char(index - 1) == "\r":
                if self._last_terminator_end == index:
                    self._last_terminator_end = index + 1
                    if self._block_starts[-1] == index:
                        self._block_starts[-1] = index + 1
                index += 1
                continue
            if char == "\u2029":
                if self._block_starts[-1] == index:
                    self._block_starts[-1] = index + 1
                else:
                    self._block_starts.append(index + 1)
                self._last_terminator_end = index + 1
                self._only_horizontal_after_terminator = True
            elif char in {"\n", "\r", "\x85", "\u2028"}:
                if self._last_terminator_end is not None and self._only_horizontal_after_terminator:
                    if self._block_starts[-1] == self._last_terminator_end:
                        self._block_starts[-1] = index + 1
                    else:
                        self._block_starts.append(index + 1)
                self._last_terminator_end = index + 1
                self._only_horizontal_after_terminator = True
            elif self._last_terminator_end is not None and not _HORIZONTAL_SPACE.contains(char):
                self._only_horizontal_after_terminator = False
            index += 1
        self._block_scan = index

    def _line_context_start(self, position: int) -> int:
        start = max(
            self._base_offset,
            self._segment_start,
            position - 2 * _REFLOW_HOLD_CHARS,
        )
        if (
            start > self._base_offset
            and start < self._total_length
            and self._char(start - 1) == "\r"
            and self._char(start) == "\n"
        ):
            start -= 1
        return start

    def _auto_mode(self, block_start: int, next_block: int | None) -> ReflowMode:
        if block_start == self._leading_auto_start and self._leading_auto_mode is not None:
            return self._leading_auto_mode
        block_end = self._total_length if next_block is None else next_block
        sample_end = min(block_end, block_start + _REFLOW_HOLD_CHARS)
        if block_start < self._base_offset:
            raise AssertionError("auto block sample was discarded before it was classified")
        sample = self._slice(block_start, sample_end)
        lines = _lines(sample)
        for index, line in enumerate(lines[:-1]):
            following = lines[index + 1]
            if not _trim_horizontal(sample[following.start : following.content_end]):
                sample = sample[: line.terminator_end]
                break
        return "lines" if _auto_uses_lines(sample) else "none"

    def _substituted_chunk(self, end: int) -> str:
        """Transform only context whose decisions can affect the next frozen slice."""
        context_start = self._line_context_start(self._fed)
        if self.mode != "auto":
            transformed = _substitute(self._slice(context_start, self._total_length), self.mode)
            return transformed[self._fed - context_start : end - context_start]

        block_index = bisect_right(self._block_starts, self._fed) - 1
        cursor = self._fed
        result: list[str] = []
        while cursor < end:
            block_start = max(self._segment_start, self._block_starts[block_index])
            next_block = (
                self._block_starts[block_index + 1]
                if block_index + 1 < len(self._block_starts)
                else None
            )
            block_end = self._total_length if next_block is None else next_block
            transform_start = context_start if cursor == self._fed else block_start
            transformed = _substitute(
                self._slice(transform_start, block_end),
                self._auto_mode(block_start, next_block),
            )
            slice_end = min(end, block_end)
            result.append(transformed[cursor - transform_start : slice_end - transform_start])
            cursor = slice_end
            block_index += 1
        return "".join(result)

    def _separator_start(self, end: int) -> int:
        """Keep CRLF and blank-line separators on one side of the frontier."""
        if (
            self._base_offset < end < self._total_length
            and self._char(end - 1) == "\r"
            and self._char(end) == "\n"
        ):
            return end - 1
        ruled = {"\n", "\r", "\x85", "\u2028"}

        def separator_char(char: str) -> bool:
            return char in ruled or _HORIZONTAL_SPACE.contains(char)

        left = end
        while left > self._base_offset and separator_char(self._char(left - 1)):
            left -= 1
        right = end
        while right < self._total_length and separator_char(self._char(right)):
            right += 1
        events = 0
        first: int | None = None
        last_end: int | None = None
        index = left
        while index < right:
            char = self._char(index)
            if char in ruled:
                if first is None:
                    first = index
                events += 1
                last_end = index + 1
                if char == "\r" and index + 1 < right and self._char(index + 1) == "\n":
                    index += 1
                    last_end = index + 1
            index += 1
        if events >= 2 and first is not None and last_end is not None and end <= last_end:
            return first
        return end

    def _settled_end(self) -> int:
        end = max(self._fed, self._total_length - _REFLOW_HOLD_CHARS)
        return max(self._fed, self._separator_start(end))

    def _compact(self) -> None:
        retain = self._line_context_start(self._fed)
        if retain <= self._base_offset:
            return
        block_index = bisect_right(self._block_starts, retain) - 1
        block_start = self._block_starts[block_index]
        next_block = (
            self._block_starts[block_index + 1]
            if block_index + 1 < len(self._block_starts)
            else None
        )
        if self.mode == "auto" and block_start < retain:
            self._leading_auto_start = block_start
            self._leading_auto_mode = self._auto_mode(block_start, next_block)
        else:
            self._leading_auto_start = block_start
            self._leading_auto_mode = None
        self._text = self._slice(retain, self._total_length)
        self._base_offset = retain
        keep_block = max(0, bisect_right(self._block_starts, retain) - 1)
        self._block_starts = self._block_starts[keep_block:]

    def _emit_through(self, end: int) -> tuple[str, str]:
        if end <= self._fed:
            return "", ""
        source = self._slice(self._fed, end)
        transformed = self._substituted_chunk(end)
        self._fed = end
        self._compact()
        return source, transformed

    def feed(self, chunk: str, /) -> tuple[str, str]:
        """Append source and return the newly settled source and reflow views."""
        if self._closed:
            raise RuntimeError("incremental reflow is closed")
        if not isinstance(chunk, str):
            raise TypeError("chunk must be str")
        self._text += chunk
        self._total_length += len(chunk)
        self._scan_blocks()
        return self._emit_through(self._settled_end())

    def flush(self) -> tuple[str, str]:
        """Resolve through the current end and begin a new logical segment."""
        if self._closed:
            return "", ""
        result = self._emit_through(self._total_length)
        self._base_offset = self._total_length
        self._text = ""
        self._segment_start = self._total_length
        self._fed = self._total_length
        self._block_starts = [self._total_length]
        self._block_scan = self._total_length
        self._last_terminator_end = None
        self._only_horizontal_after_terminator = False
        self._leading_auto_start = self._total_length
        self._leading_auto_mode = None
        return result

    def close(self) -> tuple[str, str]:
        """Resolve through the final end and reject later input."""
        if self._closed:
            return "", ""
        result = self._emit_through(self._total_length)
        self._closed = True
        return result
