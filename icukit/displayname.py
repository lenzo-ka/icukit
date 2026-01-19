"""
Locale-aware display names.

Get localized names for languages, scripts, regions, currencies, and
calendar types using ICU's display name capabilities.

Example:
    >>> from icukit import get_language_name, get_region_name, get_currency_name
    >>>
    >>> get_language_name("zh", "en")
    'Chinese'
    >>> get_language_name("zh", "de")
    'Chinesisch'
    >>> get_language_name("zh", "ja")
    '中国語'
    >>>
    >>> get_region_name("JP", "en")
    'Japan'
    >>> get_region_name("JP", "ja")
    '日本'
    >>>
    >>> get_currency_name("USD", "en")
    'US Dollar'
    >>> get_currency_name("USD", "ja")
    '米ドル'
"""

import icu

from .errors import DisplayNameError

__all__ = [
    "get_language_name",
    "get_script_name",
    "get_region_name",
    "get_currency_name",
    "get_currency_symbol",
    "get_locale_name",
    "DisplayNames",
]


class DisplayNames:
    """Locale-aware display names provider.

    Provides localized names for languages, scripts, regions, and currencies.

    Example:
        >>> names = DisplayNames("de")
        >>> names.language("zh")
        'Chinesisch'
        >>> names.region("JP")
        'Japan'
        >>> names.currency("USD")
        'US-Dollar'
    """

    def __init__(self, display_locale: str = "en_US"):
        """Create a DisplayNames instance.

        Args:
            display_locale: Locale for the display names (e.g., "en", "de", "ja")
        """
        self.display_locale = display_locale
        self._icu_locale = icu.Locale(display_locale)

    def language(self, language_code: str) -> str:
        """Get the display name for a language.

        Args:
            language_code: ISO 639 language code (e.g., "en", "zh", "ar")

        Returns:
            Localized language name

        Example:
            >>> names = DisplayNames("de")
            >>> names.language("zh")
            'Chinesisch'
        """
        try:
            lang_locale = icu.Locale(language_code)
            return lang_locale.getDisplayLanguage(self._icu_locale)
        except icu.ICUError as e:
            raise DisplayNameError(f"Failed to get language name for '{language_code}': {e}") from e

    def script(self, script_code: str) -> str:
        """Get the display name for a script.

        Args:
            script_code: ISO 15924 script code (e.g., "Latn", "Cyrl", "Hans")

        Returns:
            Localized script name

        Example:
            >>> names = DisplayNames("en")
            >>> names.script("Cyrl")
            'Cyrillic'
            >>> names.script("Hans")
            'Simplified Han'
        """
        try:
            # Create a locale with just the script to get its display name
            script_locale = icu.Locale(f"und_{script_code}")
            return script_locale.getDisplayScript(self._icu_locale)
        except icu.ICUError as e:
            raise DisplayNameError(f"Failed to get script name for '{script_code}': {e}") from e

    def region(self, region_code: str) -> str:
        """Get the display name for a region/country.

        Args:
            region_code: ISO 3166-1 alpha-2 region code (e.g., "US", "JP", "DE")

        Returns:
            Localized region name

        Example:
            >>> names = DisplayNames("ja")
            >>> names.region("US")
            'アメリカ合衆国'
        """
        try:
            region_locale = icu.Locale(f"und_{region_code}")
            return region_locale.getDisplayCountry(self._icu_locale)
        except icu.ICUError as e:
            raise DisplayNameError(f"Failed to get region name for '{region_code}': {e}") from e

    def currency(self, currency_code: str) -> str:
        """Get the display name for a currency.

        Args:
            currency_code: ISO 4217 currency code (e.g., "USD", "EUR", "JPY")

        Returns:
            Localized currency name

        Example:
            >>> names = DisplayNames("de")
            >>> names.currency("USD")
            'US-Dollar'
        """
        try:
            # Create a locale with currency keyword to get display name
            curr_loc = icu.Locale(f"und@currency={currency_code.upper()}")
            display = curr_loc.getDisplayName(self._icu_locale)
            # Extract currency name from "Unknown language (Currency=US Dollar)"
            if "=" in display:
                return display.split("=", 1)[1].rstrip(")")
            return currency_code.upper()
        except icu.ICUError as e:
            raise DisplayNameError(f"Failed to get currency name for '{currency_code}': {e}") from e

    def currency_symbol(self, currency_code: str) -> str:
        """Get the currency symbol.

        Args:
            currency_code: ISO 4217 currency code (e.g., "USD", "EUR", "JPY")

        Returns:
            Currency symbol (e.g., "$", "€", "¥")

        Example:
            >>> names = DisplayNames("en_US")
            >>> names.currency_symbol("USD")
            '$'
            >>> names.currency_symbol("EUR")
            '€'
        """
        try:
            # Get symbol via DecimalFormatSymbols with locale currency variant
            locale_name = self._icu_locale.getName()
            curr_locale = icu.Locale(f"{locale_name}@currency={currency_code.upper()}")
            dfs = icu.DecimalFormatSymbols(curr_locale)
            symbol = dfs.getSymbol(dfs.kCurrencySymbol)
            return symbol if symbol else currency_code.upper()
        except icu.ICUError as e:
            raise DisplayNameError(
                f"Failed to get currency symbol for '{currency_code}': {e}"
            ) from e

    def locale(self, locale_code: str) -> str:
        """Get the display name for a locale.

        Args:
            locale_code: Locale code (e.g., "en_US", "zh_Hans_CN", "de_DE")

        Returns:
            Localized locale name

        Example:
            >>> names = DisplayNames("en")
            >>> names.locale("zh_Hans_CN")
            'Chinese (Simplified, China)'
        """
        try:
            loc = icu.Locale(locale_code)
            return loc.getDisplayName(self._icu_locale)
        except icu.ICUError as e:
            raise DisplayNameError(f"Failed to get locale name for '{locale_code}': {e}") from e

    def __repr__(self) -> str:
        return f"DisplayNames(display_locale={self.display_locale!r})"


# Convenience functions


def get_language_name(language_code: str, display_locale: str = "en_US") -> str:
    """Get the display name for a language (convenience function).

    Args:
        language_code: ISO 639 language code
        display_locale: Locale for the display name

    Returns:
        Localized language name

    Example:
        >>> get_language_name("zh", "en")
        'Chinese'
        >>> get_language_name("zh", "de")
        'Chinesisch'
    """
    return DisplayNames(display_locale).language(language_code)


def get_script_name(script_code: str, display_locale: str = "en_US") -> str:
    """Get the display name for a script (convenience function).

    Args:
        script_code: ISO 15924 script code
        display_locale: Locale for the display name

    Returns:
        Localized script name

    Example:
        >>> get_script_name("Cyrl", "en")
        'Cyrillic'
    """
    return DisplayNames(display_locale).script(script_code)


def get_region_name(region_code: str, display_locale: str = "en_US") -> str:
    """Get the display name for a region/country (convenience function).

    Args:
        region_code: ISO 3166-1 alpha-2 region code
        display_locale: Locale for the display name

    Returns:
        Localized region name

    Example:
        >>> get_region_name("JP", "en")
        'Japan'
        >>> get_region_name("JP", "ja")
        '日本'
    """
    return DisplayNames(display_locale).region(region_code)


def get_currency_name(currency_code: str, display_locale: str = "en_US") -> str:
    """Get the display name for a currency (convenience function).

    Args:
        currency_code: ISO 4217 currency code
        display_locale: Locale for the display name

    Returns:
        Localized currency name

    Example:
        >>> get_currency_name("USD", "en")
        'US Dollar'
        >>> get_currency_name("USD", "ja")
        '米ドル'
    """
    return DisplayNames(display_locale).currency(currency_code)


def get_currency_symbol(currency_code: str, display_locale: str = "en_US") -> str:
    """Get the currency symbol (convenience function).

    Args:
        currency_code: ISO 4217 currency code
        display_locale: Locale for symbol formatting

    Returns:
        Currency symbol

    Example:
        >>> get_currency_symbol("USD", "en_US")
        '$'
        >>> get_currency_symbol("EUR", "de_DE")
        '€'
    """
    return DisplayNames(display_locale).currency_symbol(currency_code)


def get_locale_name(locale_code: str, display_locale: str = "en_US") -> str:
    """Get the display name for a locale (convenience function).

    Args:
        locale_code: Locale code
        display_locale: Locale for the display name

    Returns:
        Localized locale name

    Example:
        >>> get_locale_name("zh_Hans_CN", "en")
        'Chinese (Simplified, China)'
    """
    return DisplayNames(display_locale).locale(locale_code)
