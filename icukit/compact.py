"""
Compact number formatting.

Format large numbers in abbreviated form with locale-appropriate suffixes.

This module provides a standalone interface to compact number formatting.
The core function `format_compact` is defined in `locale.py` alongside
other number formatting functions.

Styles:
    SHORT - "1.2M", "3.5K", "1,2 Mrd." (German)
    LONG  - "1.2 million", "3.5 thousand"

Example:
    >>> from icukit import format_compact
    >>>
    >>> format_compact(1234567)
    '1.2M'
    >>> format_compact(1234567, locale="de_DE")
    '1,2 Mio.'
    >>> format_compact(1234567, style="LONG")
    '1.2 million'
    >>>
    >>> format_compact(3500)
    '3.5K'
    >>> format_compact(3500, locale="ja_JP")
    '3500'  # Japanese uses 万 (10000) not K (1000)
"""

# Import from locale.py where the core function lives
from .locale import COMPACT_LONG, COMPACT_SHORT, format_compact

# Re-export with convenience names
STYLE_SHORT = COMPACT_SHORT
STYLE_LONG = COMPACT_LONG

__all__ = [
    "CompactFormatter",
    "format_compact",
    "STYLE_SHORT",
    "STYLE_LONG",
    "COMPACT_SHORT",
    "COMPACT_LONG",
]


class CompactFormatter:
    """Locale-aware compact number formatter.

    Formats large numbers with locale-appropriate abbreviations.

    Example:
        >>> fmt = CompactFormatter("en_US")
        >>> fmt.format(1234567)
        '1.2M'
        >>> fmt.format(1234567, style="LONG")
        '1.2 million'
    """

    def __init__(self, locale: str = "en_US", style: str = STYLE_SHORT):
        """Create a CompactFormatter.

        Args:
            locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")
            style: Default style (SHORT or LONG)
        """
        self.locale = locale
        self.style = style

    def format(self, number: int | float, style: str | None = None) -> str:
        """Format a number in compact form.

        Args:
            number: Number to format
            style: Style override (SHORT or LONG)

        Returns:
            Formatted string (e.g., "1.2M", "1.2 million")

        Example:
            >>> fmt.format(1234567)
            '1.2M'
            >>> fmt.format(1234567, style="LONG")
            '1.2 million'
        """
        return format_compact(number, self.locale, style or self.style)

    def __repr__(self) -> str:
        return f"CompactFormatter(locale={self.locale!r}, style={self.style!r})"
