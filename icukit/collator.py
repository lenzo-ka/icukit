"""
Locale-aware string collation and sorting.

ICU's Collator provides Unicode-compliant string comparison that respects
language-specific sorting rules.

Example:
    >>> from icukit import sort_strings
    >>> sort_strings(["café", "cafe", "CAFÉ"], "en_US")
    ['cafe', 'café', 'CAFÉ']
    >>> sort_strings(["Öl", "Ol", "öl"], "de_DE")
    ['Ol', 'Öl', 'öl']
"""

import icu

from .errors import CollatorError

__all__ = [
    "sort_strings",
    "compare_strings",
    "get_sort_key",
    "list_collation_types",
    "get_collator_info",
    "STRENGTH_PRIMARY",
    "STRENGTH_SECONDARY",
    "STRENGTH_TERTIARY",
    "STRENGTH_QUATERNARY",
    "STRENGTH_IDENTICAL",
]

# Collation strength levels
STRENGTH_PRIMARY = "primary"  # Base letters only (a=A=á)
STRENGTH_SECONDARY = "secondary"  # Base + accents (a=A, a≠á)
STRENGTH_TERTIARY = "tertiary"  # Base + accents + case (default)
STRENGTH_QUATERNARY = "quaternary"  # Tertiary + punctuation
STRENGTH_IDENTICAL = "identical"  # Bit-for-bit

_STRENGTH_MAP = {
    STRENGTH_PRIMARY: icu.Collator.PRIMARY,
    STRENGTH_SECONDARY: icu.Collator.SECONDARY,
    STRENGTH_TERTIARY: icu.Collator.TERTIARY,
    STRENGTH_QUATERNARY: icu.Collator.QUATERNARY,
    STRENGTH_IDENTICAL: icu.Collator.IDENTICAL,
}

_STRENGTH_REVERSE = {v: k for k, v in _STRENGTH_MAP.items()}


def _get_collator(locale: str, strength: str | None = None) -> icu.Collator:
    """Create a collator instance for the given locale."""
    try:
        loc = icu.Locale(locale)
        collator = icu.Collator.createInstance(loc)
        if strength:
            if strength not in _STRENGTH_MAP:
                raise CollatorError(
                    f"Invalid strength: {strength}. " f"Valid: {list(_STRENGTH_MAP.keys())}"
                )
            collator.setStrength(_STRENGTH_MAP[strength])
        return collator
    except icu.ICUError as e:
        raise CollatorError(f"Failed to create collator for {locale}: {e}") from e


def sort_strings(
    items: list[str],
    locale: str = "en_US",
    *,
    reverse: bool = False,
    strength: str | None = None,
    case_first: str | None = None,
) -> list[str]:
    """
    Sort strings using locale-aware collation.

    Args:
        items: List of strings to sort.
        locale: Locale for sorting rules (default: en_US).
        reverse: Sort in descending order.
        strength: Collation strength (primary, secondary, tertiary, quaternary, identical).
        case_first: "upper" or "lower" to control case ordering.

    Returns:
        Sorted list of strings.

    Example:
        >>> sort_strings(["café", "cafe", "Cafe"], "en_US")
        ['cafe', 'Cafe', 'café']
        >>> sort_strings(["ö", "o", "p"], "de_DE")
        ['o', 'ö', 'p']
        >>> sort_strings(["ö", "o", "p"], "sv_SE")
        ['o', 'p', 'ö']
    """
    collator = _get_collator(locale, strength)

    if case_first == "upper":
        collator.setAttribute(icu.UCollAttribute.CASE_FIRST, icu.UCollAttributeValue.UPPER_FIRST)
    elif case_first == "lower":
        collator.setAttribute(icu.UCollAttribute.CASE_FIRST, icu.UCollAttributeValue.LOWER_FIRST)

    return sorted(items, key=collator.getSortKey, reverse=reverse)


def compare_strings(
    a: str,
    b: str,
    locale: str = "en_US",
    *,
    strength: str | None = None,
) -> int:
    """
    Compare two strings using locale-aware collation.

    Args:
        a: First string.
        b: Second string.
        locale: Locale for comparison rules.
        strength: Collation strength.

    Returns:
        -1 if a < b, 0 if a == b, 1 if a > b.

    Example:
        >>> compare_strings("cafe", "café", "en_US")
        -1
        >>> compare_strings("cafe", "café", "en_US", strength="primary")
        0
    """
    collator = _get_collator(locale, strength)
    return collator.compare(a, b)


def get_sort_key(text: str, locale: str = "en_US", *, strength: str | None = None) -> bytes:
    """
    Get a binary sort key for external sorting.

    Sort keys can be compared using standard byte comparison, useful for
    database indexing or when sorting needs to be done outside Python.

    Args:
        text: String to get sort key for.
        locale: Locale for collation rules.
        strength: Collation strength.

    Returns:
        Binary sort key.

    Example:
        >>> key_a = get_sort_key("apple", "en_US")
        >>> key_b = get_sort_key("banana", "en_US")
        >>> key_a < key_b
        True
    """
    collator = _get_collator(locale, strength)
    return collator.getSortKey(text)


def list_collation_types() -> list[str]:
    """
    List available collation types.

    Returns:
        List of collation type names (e.g., standard, phonebook, emoji).

    Example:
        >>> types = list_collation_types()
        >>> "phonebook" in types
        True
    """
    try:
        return list(icu.Collator.getKeywordValues("collation"))
    except icu.ICUError:
        return []


def get_collator_info(locale: str, *, include_extended: bool = False) -> dict:
    """
    Get information about a collator for a locale.

    Args:
        locale: Locale identifier.
        include_extended: Include additional details in extended dict.

    Returns:
        Dictionary with collator properties.

    Example:
        >>> info = get_collator_info("de_DE")
        >>> info["locale"]
        'de_DE'
    """
    collator = _get_collator(locale)
    loc = collator.getLocale(icu.ULocDataLocaleType.VALID_LOCALE)

    info = {
        "locale": locale,
        "actual_locale": str(loc),
        "strength": _STRENGTH_REVERSE.get(collator.getStrength(), "unknown"),
    }

    if include_extended:
        rules = collator.getRules()
        info["extended"] = {
            "has_tailoring": bool(rules),
            "rules_length": len(rules) if rules else 0,
        }

    return info
