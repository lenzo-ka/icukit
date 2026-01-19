"""
Locale-aware plural rules.

ICU's PluralRules determines which plural category (one, two, few, many, other)
a number falls into for a given locale.

Plural Categories:
    zero  - For 0 in some languages (Arabic)
    one   - Singular form (1 in English, but more complex in other languages)
    two   - Dual form (Arabic, Hebrew, Slovenian)
    few   - Paucal form (2-4 in Slavic languages)
    many  - "Many" category (5+ in Slavic, 11-99 in Maltese)
    other - General plural (default fallback)

Example:
    >>> from icukit import get_plural_category, list_plural_categories
    >>>
    >>> get_plural_category(1, "en")
    'one'
    >>> get_plural_category(2, "en")
    'other'
    >>> get_plural_category(1, "ru")
    'one'
    >>> get_plural_category(2, "ru")
    'few'
    >>> get_plural_category(5, "ru")
    'many'
    >>>
    >>> list_plural_categories("ar")
    ['zero', 'one', 'two', 'few', 'many', 'other']
"""

from __future__ import annotations

import icu

from .errors import PluralError

__all__ = [
    "get_plural_category",
    "get_ordinal_category",
    "list_plural_categories",
    "list_ordinal_categories",
    "get_plural_rules_info",
    "CATEGORY_ZERO",
    "CATEGORY_ONE",
    "CATEGORY_TWO",
    "CATEGORY_FEW",
    "CATEGORY_MANY",
    "CATEGORY_OTHER",
    "TYPE_CARDINAL",
    "TYPE_ORDINAL",
]

# Category constants
CATEGORY_ZERO = "zero"
CATEGORY_ONE = "one"
CATEGORY_TWO = "two"
CATEGORY_FEW = "few"
CATEGORY_MANY = "many"
CATEGORY_OTHER = "other"

# All possible categories in precedence order
ALL_CATEGORIES = [
    CATEGORY_ZERO,
    CATEGORY_ONE,
    CATEGORY_TWO,
    CATEGORY_FEW,
    CATEGORY_MANY,
    CATEGORY_OTHER,
]

# Type constants
TYPE_CARDINAL = "cardinal"
TYPE_ORDINAL = "ordinal"


def _get_rules(locale: str, plural_type: str = TYPE_CARDINAL) -> icu.PluralRules:
    """Get PluralRules for locale and type."""
    try:
        loc = icu.Locale(locale)
        # UPluralType may not exist in all PyICU versions
        if hasattr(icu, "UPluralType"):
            if plural_type == TYPE_ORDINAL:
                return icu.PluralRules.forLocale(loc, icu.UPluralType.ORDINAL)
            return icu.PluralRules.forLocale(loc, icu.UPluralType.CARDINAL)
        # Fallback for older PyICU without UPluralType
        if plural_type == TYPE_ORDINAL:
            raise PluralError("Ordinal rules not supported in this PyICU version")
        return icu.PluralRules.forLocale(loc)
    except icu.ICUError as e:
        raise PluralError(f"Failed to get plural rules for '{locale}': {e}") from e


def get_plural_category(
    number: int | float,
    locale: str = "en_US",
) -> str:
    """Get the plural category for a number.

    Args:
        number: The number to categorize
        locale: Locale code (e.g., "en_US", "ru", "ar")

    Returns:
        Plural category: "zero", "one", "two", "few", "many", or "other"

    Example:
        >>> get_plural_category(1, "en")
        'one'
        >>> get_plural_category(2, "en")
        'other'
        >>> get_plural_category(2, "ru")
        'few'
        >>> get_plural_category(5, "ru")
        'many'
    """
    rules = _get_rules(locale, TYPE_CARDINAL)
    try:
        return rules.select(float(number))
    except icu.ICUError as e:
        raise PluralError(f"Failed to select plural category: {e}") from e


def get_ordinal_category(
    number: int | float,
    locale: str = "en_US",
) -> str:
    """Get the ordinal category for a number.

    Ordinal categories are used for "1st", "2nd", "3rd", etc.

    Args:
        number: The number to categorize
        locale: Locale code

    Returns:
        Ordinal category: "zero", "one", "two", "few", "many", or "other"

    Example:
        >>> get_ordinal_category(1, "en")
        'one'
        >>> get_ordinal_category(2, "en")
        'two'
        >>> get_ordinal_category(3, "en")
        'few'
        >>> get_ordinal_category(4, "en")
        'other'
    """
    rules = _get_rules(locale, TYPE_ORDINAL)
    try:
        return rules.select(float(number))
    except icu.ICUError as e:
        raise PluralError(f"Failed to select ordinal category: {e}") from e


def list_plural_categories(locale: str = "en_US") -> list[str]:
    """List the plural categories used by a locale.

    Args:
        locale: Locale code

    Returns:
        List of category names used by this locale (subset of
        ["zero", "one", "two", "few", "many", "other"])

    Example:
        >>> list_plural_categories("en")
        ['one', 'other']
        >>> list_plural_categories("ru")
        ['one', 'few', 'many', 'other']
        >>> list_plural_categories("ar")
        ['zero', 'one', 'two', 'few', 'many', 'other']
    """
    rules = _get_rules(locale, TYPE_CARDINAL)
    try:
        keywords = list(rules.getKeywords())
        # Return in standard order
        return [cat for cat in ALL_CATEGORIES if cat in keywords]
    except icu.ICUError as e:
        raise PluralError(f"Failed to get plural categories: {e}") from e


def list_ordinal_categories(locale: str = "en_US") -> list[str]:
    """List the ordinal categories used by a locale.

    Args:
        locale: Locale code

    Returns:
        List of ordinal category names used by this locale

    Example:
        >>> list_ordinal_categories("en")
        ['one', 'two', 'few', 'other']
    """
    rules = _get_rules(locale, TYPE_ORDINAL)
    try:
        keywords = list(rules.getKeywords())
        return [cat for cat in ALL_CATEGORIES if cat in keywords]
    except icu.ICUError as e:
        raise PluralError(f"Failed to get ordinal categories: {e}") from e


def get_plural_rules_info(locale: str = "en_US") -> dict:
    """Get detailed plural rules information for a locale.

    Args:
        locale: Locale code

    Returns:
        Dictionary with:
            - locale: The locale code
            - cardinal_categories: List of cardinal plural categories
            - ordinal_categories: List of ordinal plural categories
            - examples: Sample numbers for each cardinal category

    Example:
        >>> info = get_plural_rules_info("ru")
        >>> info["cardinal_categories"]
        ['one', 'few', 'many', 'other']
    """
    cardinal_cats = list_plural_categories(locale)
    ordinal_cats = list_ordinal_categories(locale)

    # Generate examples for each cardinal category
    examples = {}
    test_numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 21, 22, 25, 100, 101, 102]

    for cat in cardinal_cats:
        examples[cat] = []

    for n in test_numbers:
        cat = get_plural_category(n, locale)
        if cat in examples and len(examples[cat]) < 5:
            examples[cat].append(n)

    return {
        "locale": locale,
        "cardinal_categories": cardinal_cats,
        "ordinal_categories": ordinal_cats,
        "examples": examples,
    }
