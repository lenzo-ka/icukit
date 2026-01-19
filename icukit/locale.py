"""Locale parsing and information.

Parse, validate, and query locale identifiers (language + region + script).
Integrates with other icukit domain objects (region, script, calendar, timezone).

Key Features:
    * Parse locale strings (BCP 47 and ICU format)
    * Get display names for languages, regions, scripts
    * List available locales
    * Add likely subtags (e.g., 'zh' -> 'zh_Hans_CN')
    * Query locale components

Locale Format:
    Locales follow the pattern: language[_Script][_REGION][@keywords]

    Examples:
        * 'en' - English
        * 'en_US' - English (United States)
        * 'zh_Hans' - Chinese (Simplified)
        * 'zh_Hans_CN' - Chinese (Simplified, China)
        * 'sr_Latn_RS' - Serbian (Latin, Serbia)
        * 'en_US@calendar=hebrew' - English (US) with Hebrew calendar

Example:
    Parse and query locales::

        >>> from icukit import parse_locale, get_locale_info, list_locales
        >>>
        >>> # Parse a locale
        >>> info = parse_locale('el_GR')
        >>> info['language']
        'el'
        >>> info['region']
        'GR'
        >>>
        >>> # Get display names
        >>> info = get_locale_info('ja_JP')
        >>> info['display_name']
        'Japanese (Japan)'
        >>>
        >>> # Add likely subtags
        >>> from icukit import add_likely_subtags
        >>> add_likely_subtags('zh')
        'zh_Hans_CN'
"""

from typing import Any, Dict, List

import icu

from .alpha_index import get_bucket_labels
from .errors import LocaleError

# Measurement system mapping using ICU constants where available
# PyICU's UMeasurementSystem is incomplete (missing UK=2), so we use getattr for forward-compat
_MEASUREMENT_SYSTEMS = {
    icu.UMeasurementSystem.SI: "metric",
    icu.UMeasurementSystem.US: "US",
    getattr(icu.UMeasurementSystem, "UK", 2): "UK",
}


def _get_measurement_system_name(value: int) -> str:
    """Convert measurement system numeric value to name."""
    return _MEASUREMENT_SYSTEMS.get(value, str(value))


def list_locales() -> List[str]:
    """List all available locale identifiers.

    Returns:
        List of locale identifiers sorted alphabetically.

    Example:
        >>> locales = list_locales()
        >>> 'en_US' in locales
        True
        >>> len(locales)
        851
    """
    locs = icu.Locale.getAvailableLocales()
    return sorted(loc.getName() for loc in locs.values())


def list_languages() -> List[str]:
    """List all available language codes.

    Returns:
        List of ISO 639 language codes sorted alphabetically.

    Example:
        >>> langs = list_languages()
        >>> 'en' in langs
        True
        >>> 'el' in langs
        True
    """
    return sorted(icu.Locale.getISOLanguages())


def list_locales_info(display_locale: str = "en") -> List[Dict[str, Any]]:
    """List all locales with their info.

    Args:
        display_locale: Locale for display names.

    Returns:
        List of dicts with locale info.

    Example:
        >>> locales = list_locales_info()
        >>> el = next(l for l in locales if l['id'] == 'el_GR')
        >>> el['display_name']
        'Greek (Greece)'
    """
    return [get_locale_info(loc_id, display_locale) for loc_id in list_locales()]


def parse_locale(locale_str: str) -> Dict[str, Any]:
    """Parse a locale string into components.

    Args:
        locale_str: Locale string (e.g., 'en_US', 'zh-Hans-CN', 'sr_Latn_RS').

    Returns:
        Dict with parsed components.

    Example:
        >>> info = parse_locale('zh_Hans_CN')
        >>> info['language']
        'zh'
        >>> info['script']
        'Hans'
        >>> info['region']
        'CN'
    """
    # Try BCP 47 format first (with hyphens)
    if "-" in locale_str:
        loc = icu.Locale.forLanguageTag(locale_str)
    else:
        loc = icu.Locale(locale_str)

    return {
        "id": loc.getName() or locale_str,
        "language": loc.getLanguage() or None,
        "script": loc.getScript() or None,
        "region": loc.getCountry() or None,
        "variant": loc.getVariant() or None,
        "base_name": loc.getBaseName() or None,
    }


def get_locale_scripts(locale_str: str) -> List[str]:
    """Get the scripts used by a locale.

    Derives scripts from the locale's exemplar character set.

    Args:
        locale_str: Locale string.

    Returns:
        List of script names used by the locale.

    Example:
        >>> get_locale_scripts('ja_JP')
        ['Han', 'Hiragana', 'Katakana']
        >>> get_locale_scripts('en_US')
        ['Latin']
    """
    try:
        ld = icu.LocaleData(locale_str)
        exemplars = ld.getExemplarSet(0, 0)  # standard set
        scripts_found = set()
        for char in str(exemplars):
            if char not in "[]- ":
                try:
                    script = icu.Script.getScript(ord(char))
                    script_name = icu.Script.getName(script)
                    if script_name not in ("Common", "Inherited"):
                        scripts_found.add(script_name)
                except icu.ICUError:
                    pass
        return sorted(scripts_found)
    except icu.ICUError:
        return []


def get_locale_info(
    locale_str: str, display_locale: str = "en", extended: bool = False
) -> Dict[str, Any]:
    """Get detailed information about a locale.

    Args:
        locale_str: Locale string to get info for.
        display_locale: Locale for display names.
        extended: Include extended attributes (calendar, currency, etc.)

    Returns:
        Dict with locale info including display names and scripts.

    Example:
        >>> info = get_locale_info('ja_JP')
        >>> info['display_name']
        'Japanese (Japan)'
        >>> info['scripts']
        ['Han', 'Hiragana', 'Katakana']
        >>> info = get_locale_info('ja_JP', extended=True)
        >>> info['extended']['currency']
        'JPY'
    """
    loc = icu.Locale(locale_str) if "-" not in locale_str else icu.Locale.forLanguageTag(locale_str)
    display_loc = icu.Locale(display_locale)

    info = {
        "id": loc.getName() or locale_str,
        "language": loc.getLanguage() or None,
        "script": loc.getScript() or None,
        "region": loc.getCountry() or None,
        "variant": loc.getVariant() or None,
        "scripts": get_locale_scripts(locale_str),
        "display_name": loc.getDisplayName(display_loc) or None,
        "display_language": loc.getDisplayLanguage(display_loc) or None,
        "display_script": loc.getDisplayScript(display_loc) or None,
        "display_region": loc.getDisplayCountry(display_loc) or None,
    }

    if extended:
        info["extended"] = get_locale_extended(locale_str)

    return info


def get_locale_extended(locale_str: str) -> Dict[str, Any]:
    """Get extended locale attributes.

    Args:
        locale_str: Locale string.

    Returns:
        Dict with extended attributes (calendar, currency, RTL, index_labels, etc.)

    Example:
        >>> ext = get_locale_extended('ja_JP')
        >>> ext['currency']
        'JPY'
        >>> ext['calendar']
        'gregorian'
        >>> ext['index_labels'][:3]
        ['あ', 'か', 'さ']
    """
    loc = icu.Locale(locale_str) if "-" not in locale_str else icu.Locale.forLanguageTag(locale_str)

    ext = {}

    # Likely subtags
    expanded = loc.addLikelySubtags()
    ext["likely_script"] = expanded.getScript() or None
    ext["likely_region"] = expanded.getCountry() or None

    # RTL detection from scripts
    scripts = get_locale_scripts(locale_str)
    ext["rtl"] = _is_locale_rtl(scripts)

    # Calendar and week data
    try:
        cal = icu.Calendar.createInstance(loc)
        ext["calendar"] = cal.getType()
        # Get weekday names from ICU (index 1=Sunday through 7=Saturday)
        dfs = icu.DateFormatSymbols(icu.Locale("en_US"))
        day_names = dfs.getWeekdays()
        ext["first_day_of_week"] = day_names[cal.getFirstDayOfWeek()]
        ext["min_days_in_first_week"] = cal.getMinimalDaysInFirstWeek()
    except icu.ICUError:
        ext["calendar"] = None
        ext["first_day_of_week"] = None
        ext["min_days_in_first_week"] = None

    # Currency
    try:
        curr_fmt = icu.NumberFormat.createCurrencyInstance(loc)
        ext["currency"] = curr_fmt.getCurrency()
    except icu.ICUError:
        ext["currency"] = None

    # LocaleData attributes
    try:
        ld = icu.LocaleData(locale_str)
        ms = ld.getMeasurementSystem()
        ext["measurement_system"] = _get_measurement_system_name(ms)
        paper = ld.getPaperSize()
        ext["paper_size"] = {"height": paper[0], "width": paper[1]}
        ext["quotes"] = {"start": ld.getDelimiter(0), "end": ld.getDelimiter(1)}
        ext["alt_quotes"] = {"start": ld.getDelimiter(2), "end": ld.getDelimiter(3)}
    except icu.ICUError:
        ext["measurement_system"] = None
        ext["paper_size"] = None
        ext["quotes"] = None
        ext["alt_quotes"] = None

    # ISO codes
    ext["iso3_language"] = loc.getISO3Language() or None
    ext["iso3_country"] = loc.getISO3Country() or None
    ext["bcp47"] = loc.toLanguageTag() or None

    # Alphabetic index labels (A-Z sidebar labels)
    try:
        ext["index_labels"] = get_bucket_labels(locale_str)
    except Exception:
        ext["index_labels"] = None

    return ext


def _is_locale_rtl(scripts: List[str]) -> bool:
    """Check if locale uses RTL scripts."""
    for script_name in scripts:
        try:
            codes = icu.Script.getCode(script_name)
            if codes:
                script_obj = icu.Script(codes[0])
                if script_obj.isRightToLeft():
                    return True
        except icu.ICUError:
            pass
    return False


def add_likely_subtags(locale_str: str) -> str:
    """Add likely subtags to a locale identifier.

    Expands a minimal locale to include likely script and region.

    Args:
        locale_str: Minimal locale string (e.g., 'zh', 'sr').

    Returns:
        Expanded locale string.

    Example:
        >>> add_likely_subtags('zh')
        'zh_Hans_CN'
        >>> add_likely_subtags('sr')
        'sr_Cyrl_RS'
    """
    loc = icu.Locale(locale_str)
    expanded = loc.addLikelySubtags()
    return expanded.getName()


def minimize_subtags(locale_str: str) -> str:
    """Remove likely subtags from a locale identifier.

    Minimizes a locale to the shortest unambiguous form.

    Args:
        locale_str: Full locale string.

    Returns:
        Minimized locale string.

    Example:
        >>> minimize_subtags('zh_Hans_CN')
        'zh'
        >>> minimize_subtags('en_Latn_US')
        'en'
    """
    loc = icu.Locale(locale_str)
    minimized = loc.minimizeSubtags()
    return minimized.getName()


def canonicalize_locale(locale_str: str) -> str:
    """Canonicalize a locale identifier.

    Converts to canonical form (e.g., deprecated codes to current ones).

    Args:
        locale_str: Locale string.

    Returns:
        Canonical locale string.

    Example:
        >>> canonicalize_locale('iw')  # deprecated Hebrew code
        'he'
    """
    loc = icu.Locale.createCanonical(locale_str)
    return loc.getName()


def get_display_name(
    locale_str: str,
    display_locale: str = "en",
) -> str:
    """Get the display name for a locale.

    Args:
        locale_str: Locale to get display name for.
        display_locale: Locale for the display name.

    Returns:
        Display name string.

    Example:
        >>> get_display_name('el_GR')
        'Greek (Greece)'
        >>> get_display_name('el_GR', 'el')
        'Ελληνικά (Ελλάδα)'
    """
    loc = icu.Locale(locale_str)
    display_loc = icu.Locale(display_locale)
    return loc.getDisplayName(display_loc)


def get_language_display_name(language: str, display_locale: str = "en") -> str:
    """Get the display name for a language code.

    Args:
        language: ISO 639 language code.
        display_locale: Locale for the display name.

    Returns:
        Display name string.

    Example:
        >>> get_language_display_name('el')
        'Greek'
        >>> get_language_display_name('ja')
        'Japanese'
    """
    loc = icu.Locale(language)
    display_loc = icu.Locale(display_locale)
    return loc.getDisplayLanguage(display_loc)


def is_valid_locale(locale_str: str) -> bool:
    """Check if a locale string is valid.

    Args:
        locale_str: Locale string to validate.

    Returns:
        True if valid, False otherwise.

    Example:
        >>> is_valid_locale('en_US')
        True
        >>> is_valid_locale('xx_YY')
        False
    """
    try:
        loc = icu.Locale(locale_str)
        # Check if language is valid
        lang = loc.getLanguage()
        if lang and lang not in icu.Locale.getISOLanguages():
            return False
        # Check if country is valid
        country = loc.getCountry()
        if country and country not in icu.Locale.getISOCountries():
            return False
        return True
    except icu.ICUError:
        return False


def get_default_locale() -> str:
    """Get the system default locale.

    Returns:
        Default locale identifier.

    Example:
        >>> get_default_locale()
        'en_US'  # or whatever the system default is
    """
    return icu.Locale.getDefault().getName()


# =============================================================================
# Rich Locale Attributes
# =============================================================================


def get_locale_attributes(locale_str: str, display_locale: str = "en") -> Dict[str, Any]:
    """Get comprehensive locale attributes.

    Returns detailed information including currency, measurement system,
    quote delimiters, and more.

    Args:
        locale_str: Locale identifier.
        display_locale: Locale for display names.

    Returns:
        Dict with comprehensive locale attributes.

    Example:
        >>> attrs = get_locale_attributes('en_US')
        >>> attrs['currency']
        'USD'
        >>> attrs['measurement_system']
        'US'
        >>> attrs['quote_start']
        '"'
    """
    loc = icu.Locale(locale_str) if "-" not in locale_str else icu.Locale.forLanguageTag(locale_str)
    display_loc = icu.Locale(display_locale)

    # Basic info
    info = {
        "id": loc.getName() or locale_str,
        "language": loc.getLanguage() or None,
        "script": loc.getScript() or None,
        "region": loc.getCountry() or None,
        "display_name": loc.getDisplayName(display_loc) or None,
        "display_language": loc.getDisplayLanguage(display_loc) or None,
        "display_region": loc.getDisplayCountry(display_loc) or None,
    }

    # Currency
    try:
        curr_fmt = icu.NumberFormat.createCurrencyInstance(loc)
        info["currency"] = curr_fmt.getCurrency()
        info["currency_format_example"] = curr_fmt.format(1234.56)
    except icu.ICUError:
        info["currency"] = None
        info["currency_format_example"] = None

    # LocaleData attributes
    try:
        ld = icu.LocaleData(locale_str)

        # Measurement system
        ms = ld.getMeasurementSystem()
        info["measurement_system"] = _get_measurement_system_name(ms)

        # Paper size (height, width in mm)
        paper = ld.getPaperSize()
        info["paper_size"] = f"{paper[0]}x{paper[1]}mm"

        # Quote delimiters
        try:
            info["quote_start"] = ld.getDelimiter(0)  # ULOCDATA_QUOTATION_START
            info["quote_end"] = ld.getDelimiter(1)  # ULOCDATA_QUOTATION_END
            info["alt_quote_start"] = ld.getDelimiter(2)  # ULOCDATA_ALT_QUOTATION_START
            info["alt_quote_end"] = ld.getDelimiter(3)  # ULOCDATA_ALT_QUOTATION_END
        except (icu.ICUError, IndexError):
            info["quote_start"] = None
            info["quote_end"] = None
            info["alt_quote_start"] = None
            info["alt_quote_end"] = None
    except icu.ICUError:
        info["measurement_system"] = None
        info["paper_size"] = None
        info["quote_start"] = None
        info["quote_end"] = None

    # Number format example
    try:
        num_fmt = icu.NumberFormat.createInstance(loc)
        info["number_format_example"] = num_fmt.format(1234567.89)
    except icu.ICUError:
        info["number_format_example"] = None

    return info


# =============================================================================
# Number Formatting
# =============================================================================


def format_number(value: float, locale_str: str = "en_US") -> str:
    """Format a number according to locale conventions.

    Args:
        value: Number to format.
        locale_str: Locale for formatting.

    Returns:
        Formatted number string.

    Example:
        >>> format_number(1234567.89, 'en_US')
        '1,234,567.89'
        >>> format_number(1234567.89, 'de_DE')
        '1.234.567,89'
    """
    loc = icu.Locale(locale_str)
    fmt = icu.NumberFormat.createInstance(loc)
    return fmt.format(value)


def format_currency(value: float, locale_str: str = "en_US", currency: str = None) -> str:
    """Format a value as currency.

    Args:
        value: Amount to format.
        locale_str: Locale for formatting.
        currency: Optional currency code (e.g., 'EUR'). If None, uses locale default.

    Returns:
        Formatted currency string.

    Example:
        >>> format_currency(1234.56, 'en_US')
        '$1,234.56'
        >>> format_currency(1234.56, 'de_DE')
        '1.234,56 €'
        >>> format_currency(1234.56, 'en_US', 'EUR')
        '€1,234.56'
    """
    loc = icu.Locale(locale_str)
    fmt = icu.NumberFormat.createCurrencyInstance(loc)
    if currency:
        fmt.setCurrency(currency)
    return fmt.format(value)


def format_percent(value: float, locale_str: str = "en_US") -> str:
    """Format a value as a percentage.

    Args:
        value: Decimal value (0.15 = 15%).
        locale_str: Locale for formatting.

    Returns:
        Formatted percentage string.

    Example:
        >>> format_percent(0.15, 'en_US')
        '15%'
        >>> format_percent(0.15, 'de_DE')
        '15 %'
    """
    loc = icu.Locale(locale_str)
    fmt = icu.NumberFormat.createPercentInstance(loc)
    return fmt.format(value)


def format_scientific(value: float, locale_str: str = "en_US") -> str:
    """Format a value in scientific notation.

    Args:
        value: Number to format.
        locale_str: Locale for formatting.

    Returns:
        Formatted scientific notation string.

    Example:
        >>> format_scientific(1234567.89, 'en_US')
        '1.234568E6'
    """
    loc = icu.Locale(locale_str)
    fmt = icu.NumberFormat.createScientificInstance(loc)
    return fmt.format(value)


def format_spellout(value: int, locale_str: str = "en_US") -> str:
    """Spell out a number in words.

    Args:
        value: Integer to spell out.
        locale_str: Locale for spelling.

    Returns:
        Number spelled out in words.

    Example:
        >>> format_spellout(42, 'en_US')
        'forty-two'
        >>> format_spellout(42, 'de_DE')
        'zwei­und­vierzig'
    """
    loc = icu.Locale(locale_str)
    fmt = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.SPELLOUT, loc)
    return fmt.format(value)


def format_ordinal(value: int, locale_str: str = "en_US") -> str:
    """Format a number as an ordinal.

    Args:
        value: Integer to format.
        locale_str: Locale for formatting.

    Returns:
        Ordinal string.

    Example:
        >>> format_ordinal(1, 'en_US')
        '1st'
        >>> format_ordinal(2, 'en_US')
        '2nd'
        >>> format_ordinal(1, 'de_DE')
        '1.'
    """
    loc = icu.Locale(locale_str)
    fmt = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, loc)
    return fmt.format(value)


# Compact style constants
COMPACT_SHORT = "SHORT"
COMPACT_LONG = "LONG"

_COMPACT_STYLE_MAP = {
    COMPACT_SHORT: icu.UNumberCompactStyle.SHORT,
    COMPACT_LONG: icu.UNumberCompactStyle.LONG,
}


def format_compact(
    value: int | float,
    locale_str: str = "en_US",
    style: str = COMPACT_SHORT,
) -> str:
    """Format a number in compact form with locale-appropriate abbreviations.

    Args:
        value: Number to format.
        locale_str: Locale for formatting.
        style: COMPACT_SHORT ("1.2M") or COMPACT_LONG ("1.2 million").

    Returns:
        Compact formatted string.

    Example:
        >>> format_compact(1234567, 'en_US')
        '1.2M'
        >>> format_compact(1234567, 'de_DE')
        '1,2 Mio.'
        >>> format_compact(1234567, 'en_US', COMPACT_LONG)
        '1.2 million'
    """
    if style not in _COMPACT_STYLE_MAP:
        raise LocaleError(
            f"Invalid compact style: {style}. Valid: {list(_COMPACT_STYLE_MAP.keys())}"
        )

    loc = icu.Locale(locale_str)
    fmt = icu.CompactDecimalFormat.createInstance(loc, _COMPACT_STYLE_MAP[style])
    return fmt.format(value)


# Exemplar set type constants
EXEMPLAR_STANDARD = "standard"
EXEMPLAR_AUXILIARY = "auxiliary"
EXEMPLAR_INDEX = "index"
EXEMPLAR_PUNCTUATION = "punctuation"

_EXEMPLAR_TYPE_MAP = {
    EXEMPLAR_STANDARD: icu.ULocaleDataExemplarSetType.STANDARD,
    EXEMPLAR_AUXILIARY: icu.ULocaleDataExemplarSetType.AUXILIARY,
    EXEMPLAR_INDEX: icu.ULocaleDataExemplarSetType.INDEX,
    EXEMPLAR_PUNCTUATION: icu.ULocaleDataExemplarSetType.PUNCTUATION,
}


def get_exemplar_characters(
    locale_str: str = "en_US",
    exemplar_type: str = EXEMPLAR_STANDARD,
) -> str:
    """Get exemplar characters for a locale.

    Exemplar characters are the characters commonly used in a locale's
    writing system.

    Args:
        locale_str: Locale code (e.g., "en_US", "de_DE", "ja_JP").
        exemplar_type: Type of exemplar set:
            - "standard" - Main characters used in the locale
            - "auxiliary" - Characters for borrowed/foreign words
            - "index" - Characters for alphabetic indexes (A-Z sidebar)
            - "punctuation" - Punctuation characters

    Returns:
        String representation of the exemplar character set (ICU UnicodeSet format).

    Example:
        >>> get_exemplar_characters("de_DE")
        '[a-zßäöü]'
        >>> get_exemplar_characters("de_DE", "index")
        '[A-Z]'
        >>> get_exemplar_characters("ja_JP", "index")
        '[あかさたなはまやらわ]'
    """
    if exemplar_type not in _EXEMPLAR_TYPE_MAP:
        raise LocaleError(
            f"Invalid exemplar type: {exemplar_type}. " f"Valid: {list(_EXEMPLAR_TYPE_MAP.keys())}"
        )

    try:
        ld = icu.LocaleData(locale_str)
        exemplar_set = ld.getExemplarSet(_EXEMPLAR_TYPE_MAP[exemplar_type])
        return str(exemplar_set)
    except icu.ICUError as e:
        raise LocaleError(f"Failed to get exemplar characters for '{locale_str}': {e}") from e


def list_exemplar_types() -> List[str]:
    """List available exemplar character set types.

    Returns:
        List of exemplar type names.

    Example:
        >>> list_exemplar_types()
        ['standard', 'auxiliary', 'index', 'punctuation']
    """
    return list(_EXEMPLAR_TYPE_MAP.keys())


def get_exemplar_info(locale_str: str = "en_US") -> Dict[str, str]:
    """Get all exemplar character sets for a locale.

    Args:
        locale_str: Locale code.

    Returns:
        Dictionary mapping exemplar type to character set string.

    Example:
        >>> info = get_exemplar_info("de_DE")
        >>> info["standard"]
        '[a-zßäöü]'
        >>> info["index"]
        '[A-Z]'
    """
    try:
        ld = icu.LocaleData(locale_str)
        result = {}
        for name, icu_type in _EXEMPLAR_TYPE_MAP.items():
            try:
                result[name] = str(ld.getExemplarSet(icu_type))
            except icu.ICUError:
                result[name] = ""
        return result
    except icu.ICUError as e:
        raise LocaleError(f"Failed to get exemplar info for '{locale_str}': {e}") from e


# =============================================================================
# Number Formatting Symbols
# =============================================================================


def get_number_symbols(locale_str: str = "en_US") -> Dict[str, str]:
    """Get number formatting symbols for a locale.

    Returns the symbols used for formatting numbers, including decimal
    separator, grouping separator, percent sign, and more.

    Args:
        locale_str: Locale code (e.g., "en_US", "de_DE", "ar_SA").

    Returns:
        Dict with number formatting symbols:
            - decimal: Decimal separator ("." or ",")
            - grouping: Grouping/thousands separator ("," or "." or " ")
            - percent: Percent sign
            - per_mille: Per-mille sign (‰)
            - plus: Plus sign
            - minus: Minus sign
            - exponential: Exponential sign (E)
            - infinity: Infinity symbol (∞)
            - nan: Not-a-number symbol
            - currency: Default currency symbol for locale

    Example:
        >>> get_number_symbols("en_US")
        {'decimal': '.', 'grouping': ',', 'percent': '%', ...}
        >>> get_number_symbols("de_DE")
        {'decimal': ',', 'grouping': '.', 'percent': '%', ...}
        >>> get_number_symbols("fr_FR")
        {'decimal': ',', 'grouping': ' ', 'percent': '%', ...}
    """
    loc = icu.Locale(locale_str)
    dfs = icu.DecimalFormatSymbols(loc)

    return {
        "locale": locale_str,
        "decimal": dfs.getSymbol(dfs.kDecimalSeparatorSymbol),
        "grouping": dfs.getSymbol(dfs.kGroupingSeparatorSymbol),
        "percent": dfs.getSymbol(dfs.kPercentSymbol),
        "per_mille": dfs.getSymbol(dfs.kPerMillSymbol),
        "plus": dfs.getSymbol(dfs.kPlusSignSymbol),
        "minus": dfs.getSymbol(dfs.kMinusSignSymbol),
        "exponential": dfs.getSymbol(dfs.kExponentialSymbol),
        "infinity": dfs.getSymbol(dfs.kInfinitySymbol),
        "nan": dfs.getSymbol(dfs.kNaNSymbol),
        "currency": dfs.getSymbol(dfs.kCurrencySymbol),
    }
