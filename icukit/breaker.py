"""
Text segmentation using ICU BreakIterator.

This module provides text segmentation capabilities for breaking text into
sentences, words, lines, or grapheme clusters using ICU's BreakIterator.
Structured span offsets are Python code-point indices into the source text.

Key Features:
    * Locale-aware sentence segmentation
    * Word tokenization with optional punctuation filtering
    * Line break detection
    * Grapheme cluster iteration (user-perceived characters)
    * Memory-efficient iteration over large texts

Example:
    >>> from icukit import break_sentences, break_words
    >>> break_sentences('Hello world. How are you?', 'en')
    ['Hello world. ', 'How are you?']
    >>> break_words('Hello, world!', 'en', skip_punctuation=True)
    ['Hello', 'world']
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import NotRequired, TypedDict

import icu

from ._offsets import codepoint_map, to_codepoint
from .errors import BreakerError

__all__ = [
    "Breaker",
    "BreakSpan",
    "RuleBreaker",
    "default_rules",
    "break_sentences",
    "break_words",
    "break_lines",
    "break_graphemes",
    "break_word_spans",
    "break_sentence_spans",
    "break_line_spans",
    "break_grapheme_spans",
    "BREAK_SENTENCE",
    "BREAK_WORD",
    "BREAK_LINE",
    "BREAK_CHARACTER",
]

# Break type constants
BREAK_SENTENCE = "sentence"
BREAK_WORD = "word"
BREAK_LINE = "line"
BREAK_CHARACTER = "character"


class BreakSpan(TypedDict):
    """A segment with code-point offsets into its source text.

    ``break_type``, present only for line spans, describes the break at the
    span's end boundary.
    """

    text: str
    start: int
    end: int
    types: list[str]
    statuses: list[int]
    break_type: NotRequired[str]


def _make_span(
    text: str,
    start: int,
    end: int,
    types: list[str],
    statuses: list[int],
    break_type: str | None = None,
) -> BreakSpan:
    """Build a span; offsets are Python code-point indices."""
    span: BreakSpan = {
        "text": text[start:end],
        "start": start,
        "end": end,
        "types": types,
        "statuses": statuses,
    }
    if break_type is not None:
        span["break_type"] = break_type
    return span


def _iter_spans(bi, text: str) -> Iterator[tuple[int, int, list[int]]]:
    """Yield code-point boundaries and statuses from an ICU iterator."""
    us = icu.UnicodeString(text)
    bi.setText(us)
    offmap = codepoint_map(text)

    start = bi.first()
    for end in bi:
        statuses = list(bi.getRuleStatusVec())
        yield (
            to_codepoint(offmap, start),
            to_codepoint(offmap, end),
            statuses,
        )
        start = end


def _word_types(segment: str, statuses: list[int]) -> list[str]:
    types = []
    for status in statuses:
        word_type = None
        if 100 <= status <= 199:
            word_type = "number"
        elif 200 <= status <= 299:
            word_type = "letter"
        elif 300 <= status <= 399:
            word_type = "kana"
        elif 400 <= status <= 499:
            word_type = "ideo"
        if word_type is not None and word_type not in types:
            types.append(word_type)

    if statuses and all(0 <= status <= 99 for status in statuses):
        if segment.isspace():
            types.append("whitespace")
        elif _is_punctuation(segment):
            types.append("punctuation")
        else:
            types.append("other")
    return types


def _skip_word(span: BreakSpan, skip_whitespace: bool, skip_punctuation: bool) -> bool:
    return (skip_whitespace and "whitespace" in span["types"]) or (
        skip_punctuation and "punctuation" in span["types"]
    )


class Breaker:
    """Text segmentation using ICU BreakIterator.

    A versatile text segmentation tool that can break text into sentences,
    words, lines, or grapheme clusters based on locale-specific rules.

    Example:
        >>> breaker = Breaker('en')
        >>> list(breaker.iter_sentences('Hello. World.'))
        ['Hello. ', 'World.']
        >>> breaker.break_words('Hello, world!', skip_punctuation=True)
        ['Hello', 'world']
    """

    def __init__(self, locale: str = "en_US"):
        """Initialize a Breaker instance.

        Args:
            locale: Locale code for language-specific rules (e.g., 'en', 'en_US', 'ja').

        Raises:
            BreakerError: If the locale is invalid.
        """
        self.locale = locale
        try:
            self._locale_obj = icu.Locale(locale)
        except icu.ICUError as e:
            raise BreakerError(f"Invalid locale '{locale}': {e}") from e

    def iter_word_spans(self, text: str) -> Iterator[BreakSpan]:
        """Yield every word segment with code-point offsets and ICU status."""
        try:
            bi = icu.BreakIterator.createWordInstance(self._locale_obj)
            for start, end, statuses in _iter_spans(bi, text):
                if start != end:
                    yield _make_span(
                        text, start, end, _word_types(text[start:end], statuses), statuses
                    )
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break words: {e}") from e

    def break_word_spans(self, text: str) -> list[BreakSpan]:
        """Return every word segment as a structured span."""
        return list(self.iter_word_spans(text))

    def iter_sentence_spans(self, text: str) -> Iterator[BreakSpan]:
        """Yield every sentence segment with code-point offsets."""
        try:
            bi = icu.BreakIterator.createSentenceInstance(self._locale_obj)
            for start, end, _statuses in _iter_spans(bi, text):
                if start != end:
                    yield _make_span(text, start, end, [], [])
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break sentences: {e}") from e

    def break_sentence_spans(self, text: str) -> list[BreakSpan]:
        """Return every sentence segment as a structured span."""
        return list(self.iter_sentence_spans(text))

    def iter_line_spans(self, text: str) -> Iterator[BreakSpan]:
        """Yield line segments; break type describes each end boundary."""
        try:
            bi = icu.BreakIterator.createLineInstance(self._locale_obj)
            for start, end, statuses in _iter_spans(bi, text):
                if start != end:
                    break_type = (
                        "mandatory"
                        if any(100 <= status <= 199 for status in statuses)
                        else "optional"
                    )
                    yield _make_span(text, start, end, [], statuses, break_type)
        except icu.ICUError as e:
            raise BreakerError(f"Failed to find line breaks: {e}") from e

    def break_line_spans(self, text: str) -> list[BreakSpan]:
        """Return every line-break segment as a structured span."""
        return list(self.iter_line_spans(text))

    def iter_grapheme_spans(self, text: str) -> Iterator[BreakSpan]:
        """Yield every grapheme cluster with code-point offsets."""
        try:
            bi = icu.BreakIterator.createCharacterInstance(self._locale_obj)
            for start, end, _statuses in _iter_spans(bi, text):
                if start != end:
                    yield _make_span(text, start, end, [], [])
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break graphemes: {e}") from e

    def break_grapheme_spans(self, text: str) -> list[BreakSpan]:
        """Return every grapheme cluster as a structured span."""
        return list(self.iter_grapheme_spans(text))

    def break_sentences(self, text: str, skip_empty: bool = True) -> list[str]:
        """Break text into sentences.

        Args:
            text: The text to segment.
            skip_empty: If True, empty sentences are excluded.

        Returns:
            List of sentence strings.

        Example:
            >>> breaker = Breaker('en')
            >>> breaker.break_sentences('Hello world. How are you?')
            ['Hello world. ', 'How are you?']
        """
        return list(self.iter_sentences(text, skip_empty))

    def iter_sentences(self, text: str, skip_empty: bool = True) -> Iterator[str]:
        """Iterate over sentences in text.

        Memory-efficient sentence iteration.

        Args:
            text: The text to segment.
            skip_empty: If True, skip empty sentences.

        Yields:
            Individual sentence strings.
        """
        for span in self.iter_sentence_spans(text):
            if skip_empty and not span["text"].strip():
                continue
            yield span["text"]

    def break_words(
        self,
        text: str,
        skip_whitespace: bool = True,
        skip_punctuation: bool = False,
    ) -> list[str]:
        """Break text into words.

        Args:
            text: The text to tokenize.
            skip_whitespace: If True, whitespace tokens are excluded (default True).
            skip_punctuation: If True, punctuation tokens are excluded.

        Returns:
            List of word/token strings.

        Example:
            >>> breaker = Breaker('en')
            >>> breaker.break_words('Hello, world!')
            ['Hello', ',', 'world', '!']
            >>> breaker.break_words('Hello, world!', skip_punctuation=True)
            ['Hello', 'world']
        """
        return list(self.iter_words(text, skip_whitespace, skip_punctuation))

    def iter_words(
        self,
        text: str,
        skip_whitespace: bool = True,
        skip_punctuation: bool = False,
    ) -> Iterator[str]:
        """Iterate over words in text.

        Args:
            text: The text to tokenize.
            skip_whitespace: If True, skip whitespace tokens.
            skip_punctuation: If True, skip punctuation tokens.

        Yields:
            Individual word/token strings.
        """
        for span in self.iter_word_spans(text):
            if not _skip_word(span, skip_whitespace, skip_punctuation):
                yield span["text"]

    def break_lines(self, text: str) -> list[str]:
        """Find line break opportunities in text.

        Returns segments where line breaks can occur (for text wrapping).

        Args:
            text: The text to analyze.

        Returns:
            List of segments at line break boundaries.
        """
        return list(self.iter_lines(text))

    def iter_lines(self, text: str) -> Iterator[str]:
        """Iterate over line break segments.

        Args:
            text: The text to analyze.

        Yields:
            Segments at line break boundaries.
        """
        for span in self.iter_line_spans(text):
            yield span["text"]

    def break_graphemes(self, text: str) -> list[str]:
        """Break text into grapheme clusters (user-perceived characters).

        Useful for correctly handling emoji, combining characters, etc.

        Args:
            text: The text to segment.

        Returns:
            List of grapheme clusters.

        Example:
            >>> breaker = Breaker('en')
            >>> breaker.break_graphemes('e\\u0301')  # e + combining accent
            ['é']
        """
        return list(self.iter_graphemes(text))

    def iter_graphemes(self, text: str) -> Iterator[str]:
        """Iterate over grapheme clusters.

        Args:
            text: The text to segment.

        Yields:
            Individual grapheme clusters.
        """
        for span in self.iter_grapheme_spans(text):
            yield span["text"]

    def tokenize_sentences(
        self,
        text: str,
        skip_whitespace: bool = True,
        skip_punctuation: bool = False,
    ) -> list[list[str]]:
        """Break text into sentences, then tokenize each sentence.

        Args:
            text: The text to process.
            skip_whitespace: If True, skip whitespace tokens.
            skip_punctuation: If True, skip punctuation tokens.

        Returns:
            List of sentences, where each sentence is a list of tokens.

        Example:
            >>> breaker = Breaker('en')
            >>> breaker.tokenize_sentences('Hello world. How are you?')
            [['Hello', 'world', '.'], ['How', 'are', 'you', '?']]
        """
        sentences = self.break_sentence_spans(text)
        words = self.break_word_spans(text)

        result = []
        wi = 0
        for sentence in sentences:
            tokens = []
            while wi < len(words) and words[wi]["start"] < sentence["end"]:
                word = words[wi]
                wi += 1
                if _skip_word(word, skip_whitespace, skip_punctuation):
                    continue
                tokens.append(word["text"])
            if tokens:
                result.append(tokens)
        return result

    def __repr__(self) -> str:
        return f"Breaker(locale='{self.locale}')"


def default_rules(kind: str = "word", locale: str = "en_US") -> str:
    """Return the standard ICU rules to use as a tailoring base.

    This is the base rule set to extend with custom exception rules.

    Args:
        kind: Iterator kind: ``word``, ``sentence``, ``line``, or ``grapheme``.
        locale: Locale code for the standard rule set.

    Returns:
        The ICU rule source for the requested standard iterator.

    Raises:
        BreakerError: If the kind is unsupported or ICU cannot load the rules.
    """
    factories = {
        "word": icu.BreakIterator.createWordInstance,
        "sentence": icu.BreakIterator.createSentenceInstance,
        "line": icu.BreakIterator.createLineInstance,
        "grapheme": icu.BreakIterator.createCharacterInstance,
    }
    try:
        factory = factories[kind]
    except KeyError as e:
        raise BreakerError(f"Invalid break kind '{kind}'") from e

    try:
        return factory(icu.Locale(locale)).getRules()
    except icu.ICUError as e:
        raise BreakerError(f"Failed to load {kind} rules: {e}") from e


class RuleBreaker:
    """Text segmentation using a custom ICU RBBI rule set."""

    def __init__(self, rules: str, status_types: dict[int, str] | None = None):
        """Compile a custom rule set once for subsequent segmentation.

        Args:
            rules: ICU RuleBasedBreakIterator rule source.
            status_types: Optional mapping from numeric rule statuses to type names.

        Raises:
            BreakerError: If ICU cannot compile the rules.
        """
        self.rules = rules
        self.status_types = dict(status_types or {})
        try:
            self._bi = icu.RuleBasedBreakIterator(rules)
        except icu.ICUError as e:
            raise BreakerError(f"Invalid break rules: {e}") from e

    def _types(self, statuses: list[int]) -> list[str]:
        types = []
        for status in statuses:
            span_type = self.status_types.get(status)
            if span_type is None:
                if 100 <= status < 200:
                    span_type = "number"
                elif 200 <= status < 300:
                    span_type = "letter"
                elif 300 <= status < 400:
                    span_type = "kana"
                elif 400 <= status < 500:
                    span_type = "ideo"
            if span_type is not None and span_type not in types:
                types.append(span_type)
        return types

    def iter_spans(self, text: str) -> Iterator[BreakSpan]:
        """Yield every custom-rule segment with offsets and raw statuses."""
        for start, end, statuses in _iter_spans(self._bi, text):
            if start != end:
                yield _make_span(text, start, end, self._types(statuses), statuses)

    def spans(self, text: str) -> list[BreakSpan]:
        """Return every custom-rule segment as a structured span."""
        return list(self.iter_spans(text))

    def tokens(self, text: str) -> list[str]:
        """Return every custom-rule segment as text."""
        return [span["text"] for span in self.spans(text)]


def _is_punctuation(token: str) -> bool:
    """Check if token is entirely punctuation."""
    if not token:
        return False
    return all(icu.Char.ispunct(char) for char in token)


def break_sentences(
    text: str,
    locale: str = "en_US",
    skip_empty: bool = True,
) -> list[str]:
    """Break text into sentences.

    Convenience function that creates a Breaker for one-off use.

    Args:
        text: The text to segment.
        locale: Locale code for language-specific rules.
        skip_empty: If True, empty sentences are excluded.

    Returns:
        List of sentence strings.

    Example:
        >>> break_sentences('Hello. World.', 'en')
        ['Hello. ', 'World.']
    """
    return Breaker(locale).break_sentences(text, skip_empty)


def break_words(
    text: str,
    locale: str = "en_US",
    skip_whitespace: bool = True,
    skip_punctuation: bool = False,
) -> list[str]:
    """Break text into words.

    Convenience function that creates a Breaker for one-off use.

    Args:
        text: The text to tokenize.
        locale: Locale code for language-specific rules.
        skip_whitespace: If True, whitespace tokens are excluded.
        skip_punctuation: If True, punctuation tokens are excluded.

    Returns:
        List of word/token strings.

    Example:
        >>> break_words('Hello, world!', 'en', skip_punctuation=True)
        ['Hello', 'world']
    """
    return Breaker(locale).break_words(text, skip_whitespace, skip_punctuation)


def break_lines(text: str, locale: str = "en_US") -> list[str]:
    """Find line break opportunities in text.

    Args:
        text: The text to analyze.
        locale: Locale code for language-specific rules.

    Returns:
        List of segments at line break boundaries.
    """
    return Breaker(locale).break_lines(text)


def break_graphemes(text: str, locale: str = "en_US") -> list[str]:
    """Break text into grapheme clusters.

    Args:
        text: The text to segment.
        locale: Locale code for language-specific rules.

    Returns:
        List of grapheme clusters.

    Example:
        >>> break_graphemes('👨‍👩‍👧‍👦')  # Family emoji
        ['👨\u200d👩\u200d👧\u200d👦']
    """
    return Breaker(locale).break_graphemes(text)


def break_word_spans(text: str, locale: str = "en_US") -> list[BreakSpan]:
    """Return every word segment with code-point offsets and ICU status."""
    return Breaker(locale).break_word_spans(text)


def break_sentence_spans(text: str, locale: str = "en_US") -> list[BreakSpan]:
    """Return every sentence segment with code-point offsets."""
    return Breaker(locale).break_sentence_spans(text)


def break_line_spans(text: str, locale: str = "en_US") -> list[BreakSpan]:
    """Return line segments whose break type describes their end boundary."""
    return Breaker(locale).break_line_spans(text)


def break_grapheme_spans(text: str, locale: str = "en_US") -> list[BreakSpan]:
    """Return every grapheme cluster with code-point offsets."""
    return Breaker(locale).break_grapheme_spans(text)
