"""
Locale-aware list formatting.

ICU's ListFormatter formats lists of items with appropriate conjunctions
and separators for each locale.

Key Features:
    * Locale-aware conjunctions ("and", "oder", "と", etc.)
    * Multiple styles: and, or, unit
    * Handles two-item special case
    * Oxford comma where appropriate

Example:
    >>> from icukit import format_list
    >>> format_list(['apples', 'oranges', 'bananas'], 'en')
    'apples, oranges, and bananas'
    >>> format_list(['Äpfel', 'Orangen', 'Bananen'], 'de')
    'Äpfel, Orangen und Bananen'
"""

import icu

from .errors import ListFormatError

__all__ = [
    "format_list",
    "ListFormatter",
    "STYLE_AND",
    "STYLE_OR",
    "STYLE_UNIT",
]

# List format styles
STYLE_AND = "and"  # "a, b, and c"
STYLE_OR = "or"  # "a, b, or c"
STYLE_UNIT = "unit"  # "a, b, c" (no conjunction)

_STYLE_MAP = {
    STYLE_AND: icu.UListFormatterType.AND,
    STYLE_OR: icu.UListFormatterType.OR,
    STYLE_UNIT: icu.UListFormatterType.UNITS,
}


class ListFormatter:
    """Locale-aware list formatter.

    Formats lists of items with appropriate conjunctions and separators.

    Example:
        >>> lf = ListFormatter('en', style='and')
        >>> lf.format(['apples', 'oranges', 'bananas'])
        'apples, oranges, and bananas'
    """

    def __init__(self, locale: str = "en_US", style: str = STYLE_AND):
        """Initialize a ListFormatter.

        Args:
            locale: Locale for formatting rules.
            style: List style - 'and', 'or', or 'unit'.

        Raises:
            ListFormatError: If locale or style is invalid.
        """
        self.locale = locale
        self.style = style

        if style not in _STYLE_MAP:
            raise ListFormatError(f"Invalid style '{style}'. Valid: {list(_STYLE_MAP.keys())}")

        try:
            loc = icu.Locale(locale)
            self._formatter = icu.ListFormatter.createInstance(
                loc, _STYLE_MAP[style], icu.UListFormatterWidth.WIDE
            )
        except icu.ICUError as e:
            raise ListFormatError(f"Failed to create list formatter: {e}") from e

    def format(self, items: list[str]) -> str:
        """Format a list of items.

        Args:
            items: List of strings to format.

        Returns:
            Formatted string with locale-appropriate conjunctions.

        Example:
            >>> lf = ListFormatter('en')
            >>> lf.format(['a', 'b', 'c'])
            'a, b, and c'
        """
        if not items:
            return ""
        if len(items) == 1:
            return items[0]

        try:
            return self._formatter.format(items)
        except icu.ICUError as e:
            raise ListFormatError(f"Failed to format list: {e}") from e

    def __repr__(self) -> str:
        return f"ListFormatter(locale={self.locale!r}, style={self.style!r})"


def format_list(
    items: list[str],
    locale: str = "en_US",
    style: str = STYLE_AND,
) -> str:
    """Format a list of items with locale-appropriate conjunctions.

    Args:
        items: List of strings to format.
        locale: Locale for formatting rules.
        style: List style - 'and', 'or', or 'unit'.

    Returns:
        Formatted string.

    Example:
        >>> format_list(['apples', 'oranges', 'bananas'], 'en')
        'apples, oranges, and bananas'

        >>> format_list(['apples', 'oranges', 'bananas'], 'en', style='or')
        'apples, oranges, or bananas'

        >>> format_list(['Äpfel', 'Orangen'], 'de')
        'Äpfel und Orangen'
    """
    return ListFormatter(locale, style).format(items)
