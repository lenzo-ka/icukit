"""Document reflow heuristics for plain text and sentence segmentation.

Reflow is an ICUKit policy rather than an ICU text form.  The modes below are
therefore intentionally small, named heuristics.  Unicode properties used by
the heuristics come from ICU; the numeric thresholds and protected shapes are
part of the documented policy.

``reflow`` changes only selected line terminators to U+0020 and always returns
exactly as many code points as it receives. Sentence breaking uses that
equal-length view internally while retaining original text and offsets.

The ruled terminators are LF, CR, CRLF, NEL, and U+2028. U+2029, VT, and FF
are never rewritten. Every decision keeps its terminator unless the necessary
context appears within 1,024 code points. ``lines`` joins a lone terminator
except before a list marker, beside an all-capital heading of at most 80 code
points, before indentation of two horizontal spaces or one tab, after a line
shorter than 40 code points, or inside a run of at least three capital-started
nonblank lines no longer than 60 code points. ``paragraphs`` also joins a blank
separator when the preceding block is unterminated and the following block
begins with neither a capital, list marker, nor heading. ``auto`` samples at
most the first eight complete lines and 1,024 code points of each blank-line
block. It selects ``lines`` when there are at least three sampled lines, at
least 70 percent of non-final widths fall between 75 percent of the sample
width and that width, and at least 50 percent lack ICU sentence-terminal
punctuation.

The protection rules are deliberately narrow. They do not recognize
title-case headings, two-line or lowercase verse, CJK verse without cased
letters, arrow bullets, code, or legal formatting. Capital-started verse longer
than 60 code points is also outside the measured rule. These shapes need an
explicit protected span when retaining their line endings matters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import icu

__all__ = ["ReflowMode", "reflow"]

ReflowMode = Literal["none", "lines", "paragraphs", "auto"]

_REFLOW_HOLD_CHARS = 1024
_HEADING_MAX_CHARS = 80
_SHORT_LINE_CHARS = 40
_VERSE_MIN_CAPITAL_RUN = 3
_VERSE_MAX_LINE_CHARS = 60
_AUTO_LOOKAHEAD_LINES = 8
_AUTO_LOOKAHEAD_CHARS = 1024
_AUTO_MIN_LINES = 3
_AUTO_WIDTH_SHARE = 0.70
_AUTO_WIDTH_BAND = 0.75
_AUTO_UNTERMINATED_SHARE = 0.50

# Reflow terminators are a ruled policy: LF, CR, CRLF, NEL, and U+2028.
# U+2029 is a line boundary but is never rewritten; VT and FF are ordinary
# content here.  Horizontal whitespace and every character-property test come
# from ICU rather than a local character table.
_REFLOW_TERMINATORS = frozenset({"\n", "\r", "\x85", "\u2028"})
_PARAGRAPH_SEPARATOR = "\u2029"
_HORIZONTAL_SPACE = icu.UnicodeSet(
    r"[\p{White_Space}-[\u000A\u000B\u000C\u000D\u0085\u2028\u2029]]"
)
_WHITE_SPACE = icu.UnicodeSet(r"[\p{White_Space}]")
_CASED = icu.UnicodeSet(r"[\p{Cased}]")
_UPPER_OR_TITLE = icu.UnicodeSet(r"[\p{Lu}\p{Lt}]")
_DASH = icu.UnicodeSet(r"[\p{Pd}]")
_LETTER = icu.UnicodeSet(r"[\p{L}]")
_DIGIT = icu.UnicodeSet(r"[\p{Nd}]")
_WORD = icu.UnicodeSet(r"[\p{Alphabetic}\p{M}\p{Nd}\p{Pc}\p{Join_Control}]")
_LEADING_QUOTE_OR_BRACKET = icu.UnicodeSet(r"[\p{Pi}\p{Ps}]")
_SENTENCE_TERMINAL = icu.UnicodeSet(r"[\p{Sentence_Break=STerm}\p{Sentence_Break=ATerm}]")
_SENTENCE_CLOSE = icu.UnicodeSet(r"[\p{Sentence_Break=Close}]")
for _unicode_set in (
    _HORIZONTAL_SPACE,
    _WHITE_SPACE,
    _CASED,
    _UPPER_OR_TITLE,
    _DASH,
    _LETTER,
    _DIGIT,
    _WORD,
    _LEADING_QUOTE_OR_BRACKET,
    _SENTENCE_TERMINAL,
    _SENTENCE_CLOSE,
):
    _unicode_set.freeze()


@dataclass(frozen=True)
class _Line:
    start: int
    content_end: int
    terminator_end: int
    terminator: str


def _validate_mode(mode: ReflowMode) -> None:
    if mode not in {"none", "lines", "paragraphs", "auto"}:
        raise ValueError("reflow must be one of 'none', 'lines', 'paragraphs', 'auto'")


def _lines(text: str) -> list[_Line]:
    """Split at ruled terminators and U+2029, keeping CRLF together."""
    result: list[_Line] = []
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char not in _REFLOW_TERMINATORS and char != _PARAGRAPH_SEPARATOR:
            index += 1
            continue
        end = index + 1
        if char == "\r" and end < len(text) and text[end] == "\n":
            end += 1
        result.append(_Line(start, index, end, text[index:end]))
        start = end
        index = end
    result.append(_Line(start, len(text), len(text), ""))
    return result


def _is_reflowable_terminator(terminator: str) -> bool:
    return bool(terminator) and all(char in _REFLOW_TERMINATORS for char in terminator)


def _trim_horizontal(text: str) -> str:
    start = 0
    end = len(text)
    while start < end and _HORIZONTAL_SPACE.contains(text[start]):
        start += 1
    while end > start and _HORIZONTAL_SPACE.contains(text[end - 1]):
        end -= 1
    return text[start:end]


def _leading_content(text: str) -> tuple[int, str] | None:
    """Return the first content character after ICU spaces, quotes, and brackets."""
    for index, char in enumerate(text):
        if _HORIZONTAL_SPACE.contains(char) or _LEADING_QUOTE_OR_BRACKET.contains(char):
            continue
        return index, char
    return None


def _starts_capital(text: str) -> bool:
    leading = _leading_content(text)
    return leading is not None and _UPPER_OR_TITLE.contains(leading[1])


def _is_heading(text: str) -> bool:
    stripped = _trim_horizontal(text)
    if not stripped or len(stripped) > _HEADING_MAX_CHARS:
        return False
    cased = [char for char in stripped if _CASED.contains(char)]
    return bool(cased) and all(_UPPER_OR_TITLE.contains(char) for char in cased)


def _starts_list_marker(text: str) -> bool:
    """Recognize the documented ICU-property-based list-marker shapes."""
    index = 0
    while index < len(text) and _HORIZONTAL_SPACE.contains(text[index]):
        index += 1
    if index >= len(text):
        return False
    char = text[index]
    if _DASH.contains(char) or char in "•◦‣⁃▪*+":
        return index + 1 < len(text) and _HORIZONTAL_SPACE.contains(text[index + 1])
    if char == "(":
        index += 1
        start = index
        while index < len(text) and _WORD.contains(text[index]):
            index += 1
        return (
            index > start
            and index + 1 < len(text)
            and text[index] == ")"
            and _HORIZONTAL_SPACE.contains(text[index + 1])
        )
    if _DIGIT.contains(char):
        while index < len(text) and _DIGIT.contains(text[index]):
            index += 1
    elif _LETTER.contains(char):
        index += 1
    else:
        return False
    return (
        index + 1 < len(text)
        and text[index] in ".)"
        and _HORIZONTAL_SPACE.contains(text[index + 1])
    )


def _is_indented(text: str) -> bool:
    if text.startswith("\t"):
        return True
    count = 0
    for char in text:
        if not _HORIZONTAL_SPACE.contains(char):
            break
        count += 1
    return count >= 2


def _capital_run(lines: list[_Line], text: str, boundary: int) -> int:
    """Count a measured verse-like capital-started run containing a boundary."""
    boundary_offset = lines[boundary].content_end

    def eligible(index: int) -> bool:
        line = lines[index]
        line_text = text[line.start : line.content_end]
        leading = _leading_content(line_text)
        return (
            bool(_trim_horizontal(line_text))
            and len(_trim_horizontal(line_text)) <= _VERSE_MAX_LINE_CHARS
            and leading is not None
            and abs(line.start + leading[0] - boundary_offset) <= _REFLOW_HOLD_CHARS
            and _UPPER_OR_TITLE.contains(leading[1])
        )

    if not eligible(boundary) or not eligible(boundary + 1):
        return 0
    start = boundary
    while start > 0:
        previous = lines[start - 1]
        if not _is_reflowable_terminator(previous.terminator) or not eligible(start - 1):
            break
        start -= 1
    end = boundary + 1
    while end + 1 < len(lines):
        current = lines[end]
        if not _is_reflowable_terminator(current.terminator) or not eligible(end + 1):
            break
        end += 1
    return end - start + 1


def _line_replacements(text: str, lines: list[_Line]) -> set[int]:
    replacements: set[int] = set()
    for index, previous in enumerate(lines[:-1]):
        if not _is_reflowable_terminator(previous.terminator):
            continue
        following = lines[index + 1]
        previous_text = text[previous.start : previous.content_end]
        following_text = text[following.start : following.content_end]
        left = _trim_horizontal(previous_text)
        right = _trim_horizontal(following_text)
        if not left or not right:
            continue
        # Every decision is local to at most 1,024 code points on either side.
        # If either adjacent line does not expose content inside that bound, the
        # line terminator remains a break.
        if previous.content_end - previous.start > _REFLOW_HOLD_CHARS:
            if not _trim_horizontal(previous_text[-_REFLOW_HOLD_CHARS:]):
                continue
        if following.content_end - following.start > _REFLOW_HOLD_CHARS:
            if not _trim_horizontal(following_text[:_REFLOW_HOLD_CHARS]):
                continue
        protected = (
            _starts_list_marker(following_text)
            or _is_heading(previous_text)
            or _is_heading(following_text)
            or _is_indented(following_text)
            or len(left) < _SHORT_LINE_CHARS
            or _capital_run(lines, text, index) >= _VERSE_MIN_CAPITAL_RUN
        )
        if not protected:
            replacements.update(range(previous.content_end, previous.terminator_end))
    return replacements


def _last_sentence_character(text: str) -> str | None:
    index = len(text) - 1
    while index >= 0 and _WHITE_SPACE.contains(text[index]):
        index -= 1
    while index >= 0 and _SENTENCE_CLOSE.contains(text[index]):
        index -= 1
        while index >= 0 and _WHITE_SPACE.contains(text[index]):
            index -= 1
    return text[index] if index >= 0 else None


def _paragraph_replacements(text: str, lines: list[_Line]) -> set[int]:
    """Return blank-separator terminators joined by the paragraphs policy."""
    replacements: set[int] = set()
    index = 0
    while index + 2 < len(lines):
        previous = lines[index]
        if not _trim_horizontal(text[previous.start : previous.content_end]):
            index += 1
            continue
        blank_end = index + 1
        while blank_end < len(lines) - 1 and not _trim_horizontal(
            text[lines[blank_end].start : lines[blank_end].content_end]
        ):
            blank_end += 1
        if blank_end == index + 1:
            index += 1
            continue
        following = lines[blank_end]
        separator_start = previous.content_end
        separator_end = following.start
        separator = text[separator_start:separator_end]
        if (
            len(separator) > _REFLOW_HOLD_CHARS
            or _PARAGRAPH_SEPARATOR in separator
            or any(
                char not in _REFLOW_TERMINATORS and not _HORIZONTAL_SPACE.contains(char)
                for char in separator
            )
        ):
            index = blank_end
            continue
        previous_context = text[
            max(previous.start, separator_start - _REFLOW_HOLD_CHARS) : separator_start
        ]
        following_text = text[
            following.start : min(following.content_end, following.start + _REFLOW_HOLD_CHARS)
        ]
        previous_char = _last_sentence_character(previous_context)
        if (
            previous_char is not None
            and _trim_horizontal(following_text)
            and not _SENTENCE_TERMINAL.contains(previous_char)
            and not _starts_capital(following_text)
            and not _starts_list_marker(following_text)
            and not _is_heading(following_text)
        ):
            replacements.update(
                position
                for position in range(separator_start, separator_end)
                if text[position] in _REFLOW_TERMINATORS
            )
        index = blank_end
    return replacements


def _has_terminal_punctuation(text: str) -> bool:
    char = _last_sentence_character(text)
    return char is not None and _SENTENCE_TERMINAL.contains(char)


def _auto_uses_lines(block: str) -> bool:
    """Apply the documented bounded hard-wrap sample to one blank-line block."""
    lines = _lines(block)
    complete = [line for line in lines if line.terminator]
    sample: list[_Line] = []
    for line in complete[:_AUTO_LOOKAHEAD_LINES]:
        if line.terminator_end > _AUTO_LOOKAHEAD_CHARS:
            break
        sample.append(line)
    if len(sample) < _AUTO_MIN_LINES:
        return False
    nonfinal = sample[:-1]
    if not nonfinal:
        return False
    widths = [len(_trim_horizontal(block[line.start : line.content_end])) for line in nonfinal]
    width = max(widths, default=0)
    if width == 0:
        return False
    near_width = sum(item >= _AUTO_WIDTH_BAND * width for item in widths) / len(widths)
    unterminated = sum(
        not _has_terminal_punctuation(block[line.start : line.content_end]) for line in nonfinal
    ) / len(nonfinal)
    return near_width >= _AUTO_WIDTH_SHARE and unterminated >= _AUTO_UNTERMINATED_SHARE


def _auto_replacements(text: str, lines: list[_Line]) -> set[int]:
    replacements: set[int] = set()
    block_start = 0
    index = 0
    while index < len(lines) - 1:
        line = lines[index]
        next_line = lines[index + 1]
        blank = not _trim_horizontal(text[next_line.start : next_line.content_end])
        paragraph = line.terminator == _PARAGRAPH_SEPARATOR
        if not blank and not paragraph:
            index += 1
            continue
        block_end = line.terminator_end
        block = text[block_start:block_end]
        if _auto_uses_lines(block):
            block_lines = _lines(block)
            replacements.update(
                block_start + position for position in _line_replacements(block, block_lines)
            )
        if paragraph:
            block_start = line.terminator_end
            index += 1
        else:
            blank_end = index + 1
            while blank_end < len(lines) - 1 and not _trim_horizontal(
                text[lines[blank_end].start : lines[blank_end].content_end]
            ):
                blank_end += 1
            block_start = lines[blank_end].start
            index = blank_end
    block = text[block_start:]
    if _auto_uses_lines(block):
        replacements.update(
            block_start + position for position in _line_replacements(block, _lines(block))
        )
    return replacements


def _substitute(text: str, mode: ReflowMode) -> str:
    """Return an equal-length sentence-breaking view of ``text``.

    The heuristic reads at most ``_REFLOW_HOLD_CHARS`` beyond a candidate.  If
    enough context is not available inside that bound, the terminator is kept.
    """
    _validate_mode(mode)
    if mode == "none" or not text:
        return text
    lines = _lines(text)
    if mode == "auto":
        replacements = _auto_replacements(text, lines)
    else:
        replacements = _line_replacements(text, lines)
        if mode == "paragraphs":
            replacements.update(_paragraph_replacements(text, lines))
    if not replacements:
        return text
    return "".join(" " if index in replacements else char for index, char in enumerate(text))


def reflow(text: str, mode: ReflowMode = "lines") -> str:
    """Reflow plain text while preserving its code-point length.

    ``none`` returns its input unchanged. ``lines`` joins eligible single line
    endings, ``paragraphs`` may also join eligible blank-line separators, and
    ``auto`` applies ``lines`` only to blocks whose bounded sample resembles
    hard-wrapped prose. Protected headings, lists, indentation, short lines,
    and measured verse-like capital-started runs remain broken. The heuristic
    intentionally does not infer title-case headings, two-line or lowercase
    verse, CJK verse, arrow bullets, code, or legal formatting.

    The result has ``len(result) == len(text)``. Collapsing selected whitespace
    was measured on two reference books and did not improve the whole
    no-offsets sentence-breaking path by the required 10 percent.
    """
    return _substitute(text, mode)
