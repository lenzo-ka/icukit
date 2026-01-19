"""
Locale-aware parsing of numbers, currencies, and percentages.

ICU's NumberFormat can parse locale-formatted strings back to numeric values,
handling locale-specific conventions like decimal separators, grouping
separators, and currency symbols.

Example:
    >>> from icukit import parse_number, parse_currency, parse_percent
    >>>
    >>> parse_number("1,234.56", "en_US")
    1234.56
    >>> parse_number("1.234,56", "de_DE")
    1234.56
    >>>
    >>> parse_currency("$1,234.56", "en_US")
    {'value': 1234.56, 'currency': 'USD'}
    >>> parse_currency("€1.234,56", "de_DE")
    {'value': 1234.56, 'currency': 'EUR'}
    >>>
    >>> parse_percent("50%", "en_US")
    0.5
"""

import icu

from .errors import ParseError

__all__ = [
    "parse_number",
    "parse_currency",
    "parse_percent",
    "NumberParser",
]


class NumberParser:
    """Locale-aware number parser.

    Parses numbers, currencies, and percentages according to locale conventions.

    Example:
        >>> parser = NumberParser("de_DE")
        >>> parser.parse_number("1.234,56")
        1234.56
        >>> parser.parse_currency("€1.234,56")
        {'value': 1234.56, 'currency': 'EUR'}
    """

    def __init__(self, locale: str = "en_US"):
        """Create a NumberParser for the given locale.

        Args:
            locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")
        """
        self.locale = locale
        self._icu_locale = icu.Locale(locale)
        self._number_formatter = None
        self._currency_formatter = None
        self._percent_formatter = None

    def parse_number(self, text: str, lenient: bool = True) -> float:
        """Parse a locale-formatted number string.

        Args:
            text: Number string to parse (e.g., "1,234.56" or "1.234,56")
            lenient: If True, be lenient with formatting variations

        Returns:
            Parsed numeric value

        Raises:
            ParseError: If parsing fails

        Example:
            >>> parser = NumberParser("en_US")
            >>> parser.parse_number("1,234.56")
            1234.56
            >>> parser = NumberParser("de_DE")
            >>> parser.parse_number("1.234,56")
            1234.56
        """
        if self._number_formatter is None:
            self._number_formatter = icu.NumberFormat.createInstance(self._icu_locale)
            if lenient:
                self._number_formatter.setLenient(True)

        try:
            result = self._number_formatter.parse(text.strip())
            return result.getDouble()
        except icu.ICUError as e:
            raise ParseError(f"Failed to parse number '{text}': {e}") from e

    def parse_currency(self, text: str, lenient: bool = True) -> dict:
        """Parse a locale-formatted currency string.

        Args:
            text: Currency string to parse (e.g., "$1,234.56" or "€1.234,56")
            lenient: If True, be lenient with formatting variations

        Returns:
            Dictionary with 'value' (float) and 'currency' (ISO code)

        Raises:
            ParseError: If parsing fails

        Example:
            >>> parser = NumberParser("en_US")
            >>> parser.parse_currency("$1,234.56")
            {'value': 1234.56, 'currency': 'USD'}
        """
        if self._currency_formatter is None:
            self._currency_formatter = icu.NumberFormat.createCurrencyInstance(self._icu_locale)
            if lenient:
                self._currency_formatter.setLenient(True)

        try:
            result = self._currency_formatter.parse(text.strip())
            currency = self._currency_formatter.getCurrency()
            return {
                "value": result.getDouble(),
                "currency": currency if currency else None,
            }
        except icu.ICUError as e:
            raise ParseError(f"Failed to parse currency '{text}': {e}") from e

    def parse_percent(self, text: str, lenient: bool = True) -> float:
        """Parse a locale-formatted percentage string.

        Args:
            text: Percentage string to parse (e.g., "50%" or "50 %")
            lenient: If True, be lenient with formatting variations

        Returns:
            Parsed value as decimal (50% → 0.5)

        Raises:
            ParseError: If parsing fails

        Example:
            >>> parser = NumberParser("en_US")
            >>> parser.parse_percent("50%")
            0.5
            >>> parser.parse_percent("125%")
            1.25
        """
        if self._percent_formatter is None:
            self._percent_formatter = icu.NumberFormat.createPercentInstance(self._icu_locale)
            if lenient:
                self._percent_formatter.setLenient(True)

        try:
            result = self._percent_formatter.parse(text.strip())
            return result.getDouble()
        except icu.ICUError as e:
            raise ParseError(f"Failed to parse percent '{text}': {e}") from e

    def __repr__(self) -> str:
        return f"NumberParser(locale={self.locale!r})"


def parse_number(text: str, locale: str = "en_US", lenient: bool = True) -> float:
    """Parse a locale-formatted number string (convenience function).

    Args:
        text: Number string to parse
        locale: Locale code
        lenient: If True, be lenient with formatting variations

    Returns:
        Parsed numeric value

    Example:
        >>> parse_number("1,234.56", "en_US")
        1234.56
        >>> parse_number("1.234,56", "de_DE")
        1234.56
    """
    return NumberParser(locale).parse_number(text, lenient)


def parse_currency(text: str, locale: str = "en_US", lenient: bool = True) -> dict:
    """Parse a locale-formatted currency string (convenience function).

    Args:
        text: Currency string to parse
        locale: Locale code
        lenient: If True, be lenient with formatting variations

    Returns:
        Dictionary with 'value' and 'currency'

    Example:
        >>> parse_currency("$1,234.56", "en_US")
        {'value': 1234.56, 'currency': 'USD'}
        >>> parse_currency("€1.234,56", "de_DE")
        {'value': 1234.56, 'currency': 'EUR'}
    """
    return NumberParser(locale).parse_currency(text, lenient)


def parse_percent(text: str, locale: str = "en_US", lenient: bool = True) -> float:
    """Parse a locale-formatted percentage string (convenience function).

    Args:
        text: Percentage string to parse
        locale: Locale code
        lenient: If True, be lenient with formatting variations

    Returns:
        Parsed value as decimal (50% → 0.5)

    Example:
        >>> parse_percent("50%", "en_US")
        0.5
    """
    return NumberParser(locale).parse_percent(text, lenient)
