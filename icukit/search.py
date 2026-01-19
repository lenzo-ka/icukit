"""
Locale-aware text search using ICU's StringSearch.

ICU's StringSearch provides collation-based searching that respects
language-specific rules, allowing matches like "café" to match "cafe"
when using accent-insensitive comparison.

Example:
    >>> from icukit import search_all, search_first
    >>> search_all("cafe", "Visit the café. The CAFE is open.", "fr_FR", strength="primary")
    [{'start': 10, 'end': 14, 'text': 'café'}, {'start': 20, 'end': 24, 'text': 'CAFE'}]
    >>> search_first("cafe", "The café is here", strength="primary")
    {'start': 4, 'end': 8, 'text': 'café'}
"""

from __future__ import annotations

from typing import Any

import icu

from .errors import SearchError

__all__ = [
    "search_all",
    "search_first",
    "search_count",
    "search_replace",
    "StringSearcher",
    "STRENGTH_PRIMARY",
    "STRENGTH_SECONDARY",
    "STRENGTH_TERTIARY",
    "STRENGTH_QUATERNARY",
    "STRENGTH_IDENTICAL",
]

# Search strength levels (reuse collator terminology)
STRENGTH_PRIMARY = "primary"  # Base letters only (a=A=á=Á)
STRENGTH_SECONDARY = "secondary"  # Base + accents (a=A, á=Á, but a≠á)
STRENGTH_TERTIARY = "tertiary"  # Base + accents + case (default)
STRENGTH_QUATERNARY = "quaternary"  # + punctuation/whitespace
STRENGTH_IDENTICAL = "identical"  # Exact match

_STRENGTH_MAP = {
    STRENGTH_PRIMARY: icu.Collator.PRIMARY,
    STRENGTH_SECONDARY: icu.Collator.SECONDARY,
    STRENGTH_TERTIARY: icu.Collator.TERTIARY,
    STRENGTH_QUATERNARY: icu.Collator.QUATERNARY,
    STRENGTH_IDENTICAL: icu.Collator.IDENTICAL,
}


def _create_searcher(
    pattern: str,
    text: str,
    locale: str = "en_US",
    strength: str | None = None,
) -> icu.StringSearch:
    """Create a StringSearch instance."""
    try:
        loc = icu.Locale(locale)
        collator = icu.Collator.createInstance(loc)

        if strength:
            if strength not in _STRENGTH_MAP:
                raise SearchError(
                    f"Invalid strength: {strength}. Valid: {list(_STRENGTH_MAP.keys())}"
                )
            collator.setStrength(_STRENGTH_MAP[strength])

        return icu.StringSearch(pattern, text, collator)
    except icu.ICUError as e:
        raise SearchError(f"Failed to create searcher: {e}") from e


def _collect_matches(searcher: icu.StringSearch) -> list[dict[str, Any]]:
    """Collect all matches from a StringSearch."""
    matches = []
    pos = searcher.first()
    while pos != icu.StringSearch.DONE:
        length = searcher.getMatchedLength()
        matched = searcher.getMatchedText()
        matches.append({"start": pos, "end": pos + length, "text": matched})
        pos = searcher.nextMatch()
    return matches


def search_all(
    pattern: str,
    text: str,
    locale: str = "en_US",
    *,
    strength: str | None = None,
) -> list[dict[str, Any]]:
    """
    Find all occurrences of pattern in text using locale-aware matching.

    Args:
        pattern: The string to search for.
        text: The text to search in.
        locale: Locale for collation rules (default: en_US).
        strength: Collation strength:
            - "primary" - Base letters only (café=cafe=CAFE)
            - "secondary" - Base + accents (cafe=CAFE, but café≠cafe)
            - "tertiary" - Base + accents + case (default, exact match)
            - "quaternary" - Tertiary + punctuation differences
            - "identical" - Bit-for-bit identical

    Returns:
        List of match dicts with 'start', 'end', and 'text' keys.

    Example:
        >>> search_all("cafe", "The café and CAFE", "en_US", strength="primary")
        [{'start': 4, 'end': 8, 'text': 'café'}, {'start': 13, 'end': 17, 'text': 'CAFE'}]
    """
    if not pattern:
        return []
    if not text:
        return []

    try:
        searcher = _create_searcher(pattern, text, locale, strength)
        return _collect_matches(searcher)
    except icu.ICUError as e:
        raise SearchError(f"Search failed: {e}") from e


def search_first(
    pattern: str,
    text: str,
    locale: str = "en_US",
    *,
    strength: str | None = None,
) -> dict[str, Any] | None:
    """
    Find the first occurrence of pattern in text.

    Args:
        pattern: The string to search for.
        text: The text to search in.
        locale: Locale for collation rules (default: en_US).
        strength: Collation strength (see search_all).

    Returns:
        Match dict with 'start', 'end', 'text', or None if not found.

    Example:
        >>> search_first("café", "Visit the cafe today", strength="primary")
        {'start': 10, 'end': 14, 'text': 'cafe'}
    """
    if not pattern or not text:
        return None

    try:
        searcher = _create_searcher(pattern, text, locale, strength)
        pos = searcher.first()
        if pos == icu.StringSearch.DONE:
            return None
        return {
            "start": pos,
            "end": pos + searcher.getMatchedLength(),
            "text": searcher.getMatchedText(),
        }
    except icu.ICUError as e:
        raise SearchError(f"Search failed: {e}") from e


def search_count(
    pattern: str,
    text: str,
    locale: str = "en_US",
    *,
    strength: str | None = None,
) -> int:
    """
    Count occurrences of pattern in text.

    Args:
        pattern: The string to search for.
        text: The text to search in.
        locale: Locale for collation rules (default: en_US).
        strength: Collation strength (see search_all).

    Returns:
        Number of matches found.

    Example:
        >>> search_count("cafe", "café, Cafe, CAFE", strength="primary")
        3
    """
    if not pattern or not text:
        return 0

    try:
        searcher = _create_searcher(pattern, text, locale, strength)
        count = 0
        pos = searcher.first()
        while pos != icu.StringSearch.DONE:
            count += 1
            pos = searcher.nextMatch()
        return count
    except icu.ICUError as e:
        raise SearchError(f"Search failed: {e}") from e


def search_replace(
    pattern: str,
    text: str,
    replacement: str,
    locale: str = "en_US",
    *,
    strength: str | None = None,
    count: int = 0,
) -> str:
    """
    Replace occurrences of pattern in text using locale-aware matching.

    Args:
        pattern: The string to search for.
        text: The text to search in.
        replacement: The replacement string.
        locale: Locale for collation rules (default: en_US).
        strength: Collation strength (see search_all).
        count: Maximum replacements (0 = unlimited).

    Returns:
        Text with replacements made.

    Example:
        >>> search_replace("cafe", "Visit the café", "tea", strength="primary")
        'Visit the tea'
    """
    if not pattern or not text:
        return text

    try:
        matches = search_all(pattern, text, locale, strength=strength)
        if not matches:
            return text

        if count > 0:
            matches = matches[:count]

        # Replace from end to preserve positions
        result = text
        for match in reversed(matches):
            result = result[: match["start"]] + replacement + result[match["end"] :]
        return result
    except icu.ICUError as e:
        raise SearchError(f"Replace failed: {e}") from e


class StringSearcher:
    """
    Reusable locale-aware string searcher.

    Useful when searching the same pattern across multiple texts,
    or when you need more control over the search process.

    Example:
        >>> searcher = StringSearcher("café", "en_US", strength="primary")
        >>> searcher.find_all("I love cafe and CAFÉ")
        [{'start': 7, 'end': 11, 'text': 'cafe'}, {'start': 16, 'end': 20, 'text': 'CAFÉ'}]
        >>> searcher.contains("No coffee here")
        False
    """

    def __init__(
        self,
        pattern: str,
        locale: str = "en_US",
        *,
        strength: str | None = None,
    ):
        """
        Create a reusable searcher for the given pattern.

        Args:
            pattern: The string to search for.
            locale: Locale for collation rules.
            strength: Collation strength.
        """
        self.pattern = pattern
        self.locale = locale
        self.strength = strength

        try:
            loc = icu.Locale(locale)
            self._collator = icu.Collator.createInstance(loc)
            if strength:
                if strength not in _STRENGTH_MAP:
                    raise SearchError(
                        f"Invalid strength: {strength}. Valid: {list(_STRENGTH_MAP.keys())}"
                    )
                self._collator.setStrength(_STRENGTH_MAP[strength])
        except icu.ICUError as e:
            raise SearchError(f"Failed to create searcher: {e}") from e

    def find_all(self, text: str) -> list[dict[str, Any]]:
        """Find all matches of the pattern in text."""
        if not self.pattern or not text:
            return []
        try:
            searcher = icu.StringSearch(self.pattern, text, self._collator)
            return _collect_matches(searcher)
        except icu.ICUError as e:
            raise SearchError(f"Search failed: {e}") from e

    def find_first(self, text: str) -> dict[str, Any] | None:
        """Find the first match of the pattern in text."""
        if not self.pattern or not text:
            return None
        try:
            searcher = icu.StringSearch(self.pattern, text, self._collator)
            pos = searcher.first()
            if pos == icu.StringSearch.DONE:
                return None
            return {
                "start": pos,
                "end": pos + searcher.getMatchedLength(),
                "text": searcher.getMatchedText(),
            }
        except icu.ICUError as e:
            raise SearchError(f"Search failed: {e}") from e

    def count(self, text: str) -> int:
        """Count matches of the pattern in text."""
        return len(self.find_all(text))

    def contains(self, text: str) -> bool:
        """Check if the pattern exists in text."""
        return self.find_first(text) is not None

    def replace(self, text: str, replacement: str, count: int = 0) -> str:
        """Replace matches with replacement string."""
        return search_replace(
            self.pattern,
            text,
            replacement,
            self.locale,
            strength=self.strength,
            count=count,
        )

    def __repr__(self) -> str:
        strength_str = f", strength={self.strength!r}" if self.strength else ""
        return f"StringSearcher({self.pattern!r}, {self.locale!r}{strength_str})"
