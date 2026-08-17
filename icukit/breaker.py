"""
Text segmentation using ICU BreakIterator.

This module provides text segmentation capabilities for breaking text into
sentences, words, lines, or grapheme clusters using ICU's BreakIterator.

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

from typing import Iterator

import icu

from .errors import BreakerError

__all__ = [
    "Breaker",
    "break_sentences",
    "break_words",
    "break_lines",
    "break_graphemes",
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


def _offset_map(text: str) -> list[int] | None:
    """Map ICU UTF-16 offsets to Python string code-point indices.

    ICU reports break positions as UTF-16 code-unit offsets, while Python
    strings are indexed by Unicode code points. For text containing astral
    characters, each surrogate pair therefore needs an extra map slot.

    Args:
        text: The text whose offsets should be mapped.

    Returns:
        A UTF-16-offset-to-code-point-index map, or None when the offsets are
        already identical.
    """
    if all(ord(ch) <= 0xFFFF for ch in text):
        return None

    m = []
    for cp_index, ch in enumerate(text):
        m.append(cp_index)
        if ord(ch) > 0xFFFF:
            m.append(cp_index)
    m.append(len(text))
    return m


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

    def _iter_spans(self, bi, text: str) -> Iterator[tuple[int, int]]:
        us = icu.UnicodeString(text)
        bi.setText(us)
        offmap = _offset_map(text)

        def _cp(offset: int) -> int:
            return offset if offmap is None else offmap[offset]

        start = bi.first()
        for end in bi:
            yield _cp(start), _cp(end)
            start = end

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
        try:
            bi = icu.BreakIterator.createSentenceInstance(self._locale_obj)
            for start, end in self._iter_spans(bi, text):
                sentence = text[start:end]
                if skip_empty and not sentence.strip():
                    continue
                yield sentence
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break sentences: {e}") from e

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
        try:
            bi = icu.BreakIterator.createWordInstance(self._locale_obj)
            for start, end in self._iter_spans(bi, text):
                word = text[start:end]

                if skip_whitespace and word.isspace():
                    continue
                if skip_punctuation and _is_punctuation(word):
                    continue

                yield word
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break words: {e}") from e

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
        try:
            bi = icu.BreakIterator.createLineInstance(self._locale_obj)
            for start, end in self._iter_spans(bi, text):
                segment = text[start:end]
                if segment:
                    yield segment
        except icu.ICUError as e:
            raise BreakerError(f"Failed to find line breaks: {e}") from e

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
            ['é']
        """
        return list(self.iter_graphemes(text))

    def iter_graphemes(self, text: str) -> Iterator[str]:
        """Iterate over grapheme clusters.

        Args:
            text: The text to segment.

        Yields:
            Individual grapheme clusters.
        """
        try:
            bi = icu.BreakIterator.createCharacterInstance(self._locale_obj)
            for start, end in self._iter_spans(bi, text):
                grapheme = text[start:end]
                if grapheme:
                    yield grapheme
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break graphemes: {e}") from e

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
        try:
            sent_bi = icu.BreakIterator.createSentenceInstance(self._locale_obj)
            sentences = list(self._iter_spans(sent_bi, text))
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break sentences: {e}") from e

        try:
            word_bi = icu.BreakIterator.createWordInstance(self._locale_obj)
            words = list(self._iter_spans(word_bi, text))
        except icu.ICUError as e:
            raise BreakerError(f"Failed to break words: {e}") from e

        result = []
        wi = 0
        for _sentence_start, sentence_end in sentences:
            tokens = []
            while wi < len(words) and words[wi][0] < sentence_end:
                word_start, word_end = words[wi]
                wi += 1
                word = text[word_start:word_end]
                if skip_whitespace and word.isspace():
                    continue
                if skip_punctuation and _is_punctuation(word):
                    continue
                tokens.append(word)
            if tokens:
                result.append(tokens)
        return result

    def __repr__(self) -> str:
        return f"Breaker(locale='{self.locale}')"


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
