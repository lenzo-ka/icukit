"""Unicode text normalization and character properties.

Normalize text to standard Unicode forms (NFC, NFD, NFKC, NFKD) and
query Unicode character properties like names and categories.

Key Features:
    * Normalize text to NFC, NFD, NFKC, NFKD forms
    * Get Unicode character names
    * Get character categories and properties
    * Check normalization status

Normalization Forms:
    * NFC - Canonical decomposition, then canonical composition (default)
    * NFD - Canonical decomposition
    * NFKC - Compatibility decomposition, then canonical composition
    * NFKD - Compatibility decomposition

Example:
    Normalize text::

        >>> from icukit import normalize
        >>>
        >>> # Composed vs decomposed forms
        >>> text = 'café'  # may be composed or decomposed
        >>> normalize(text, 'NFC')  # composed: é is one codepoint
        'café'
        >>> normalize(text, 'NFD')  # decomposed: e + combining accent
        'café'
        >>>
        >>> # Compatibility normalization
        >>> normalize('ﬁ', 'NFKC')  # ligature to separate chars
        'fi'

    Character properties::

        >>> from icukit import get_char_name, get_char_category
        >>>
        >>> get_char_name('α')
        'GREEK SMALL LETTER ALPHA'
        >>> get_char_name('😀')
        'GRINNING FACE'
        >>>
        >>> get_char_category('A')
        'Lu'  # Letter, uppercase
        >>> get_char_category('5')
        'Nd'  # Number, decimal digit
"""

from typing import Any, Dict, List

import icu

from .errors import NormalizationError


def _get_category_short_name(cat_value: int) -> str:
    """Get category short name from ICU for a numeric charType value."""
    try:
        return icu.Char.getPropertyValueName(
            icu.UProperty.GENERAL_CATEGORY,
            cat_value,
            icu.UPropertyNameChoice.SHORT_PROPERTY_NAME,
        )
    except icu.ICUError:
        return "Cn"  # Default to Unassigned


# Normalization form constants
NFC = "NFC"
NFD = "NFD"
NFKC = "NFKC"
NFKD = "NFKD"

_NORMALIZERS = {
    NFC: icu.Normalizer2.getNFCInstance,
    NFD: icu.Normalizer2.getNFDInstance,
    NFKC: icu.Normalizer2.getNFKCInstance,
    NFKD: icu.Normalizer2.getNFKDInstance,
}


def normalize(text: str, form: str = NFC) -> str:
    """Normalize Unicode text to a standard form.

    Args:
        text: Text to normalize.
        form: Normalization form - 'NFC', 'NFD', 'NFKC', or 'NFKD'.
              Defaults to 'NFC'.

    Returns:
        Normalized text.

    Raises:
        NormalizationError: If form is invalid.

    Example:
        >>> # NFC: Canonical composition (default)
        >>> normalize('café')
        'café'
        >>>
        >>> # NFD: Canonical decomposition
        >>> len(normalize('é', 'NFC'))
        1
        >>> len(normalize('é', 'NFD'))
        2
        >>>
        >>> # NFKC/NFKD: Compatibility normalization
        >>> normalize('ﬁ', 'NFKC')  # fi ligature
        'fi'
        >>> normalize('①', 'NFKC')  # circled digit
        '1'
    """
    form = form.upper()
    if form not in _NORMALIZERS:
        raise NormalizationError(
            f"Invalid normalization form: {form}. Use NFC, NFD, NFKC, or NFKD."
        )
    normalizer = _NORMALIZERS[form]()
    return normalizer.normalize(text)


def is_normalized(text: str, form: str = NFC) -> bool:
    """Check if text is already in the specified normalization form.

    Args:
        text: Text to check.
        form: Normalization form to check against.

    Returns:
        True if text is already normalized.

    Example:
        >>> is_normalized('café', 'NFC')
        True
        >>> is_normalized('café', 'NFD')
        False  # if 'é' is composed
    """
    form = form.upper()
    if form not in _NORMALIZERS:
        raise NormalizationError(
            f"Invalid normalization form: {form}. Use NFC, NFD, NFKC, or NFKD."
        )
    normalizer = _NORMALIZERS[form]()
    return normalizer.isNormalized(text)


def get_char_name(char: str) -> str:
    """Get the Unicode name of a character.

    Args:
        char: A single character.

    Returns:
        Unicode character name.

    Raises:
        ValueError: If input is not a single character.

    Example:
        >>> get_char_name('A')
        'LATIN CAPITAL LETTER A'
        >>> get_char_name('α')
        'GREEK SMALL LETTER ALPHA'
        >>> get_char_name('你')
        'CJK UNIFIED IDEOGRAPH-4F60'
        >>> get_char_name('😀')
        'GRINNING FACE'
    """
    if len(char) != 1:
        raise ValueError("Input must be a single character")
    return icu.Char.charName(char)


def get_char_category(char: str) -> str:
    """Get the Unicode general category of a character.

    Categories are two-letter codes like 'Lu' (Letter, uppercase),
    'Ll' (Letter, lowercase), 'Nd' (Number, decimal digit), etc.

    Args:
        char: A single character.

    Returns:
        Two-letter category code.

    Raises:
        ValueError: If input is not a single character.

    Example:
        >>> get_char_category('A')
        'Lu'
        >>> get_char_category('a')
        'Ll'
        >>> get_char_category('5')
        'Nd'
        >>> get_char_category(' ')
        'Zs'
        >>> get_char_category('!')
        'Po'
    """
    if len(char) != 1:
        raise ValueError("Input must be a single character")
    # Get numeric category and convert to string code using ICU
    cat = icu.Char.charType(char)
    return _get_category_short_name(cat)


def get_char_info(char: str) -> Dict[str, Any]:
    """Get comprehensive information about a character.

    Args:
        char: A single character.

    Returns:
        Dict with character info: codepoint, name, category, script, etc.

    Raises:
        ValueError: If input is not a single character.

    Example:
        >>> info = get_char_info('α')
        >>> info['name']
        'GREEK SMALL LETTER ALPHA'
        >>> info['category']
        'Ll'
        >>> info['codepoint']
        'U+03B1'
    """
    if len(char) != 1:
        raise ValueError("Input must be a single character")

    codepoint = ord(char)
    return {
        "char": char,
        "codepoint": f"U+{codepoint:04X}",
        "decimal": codepoint,
        "name": icu.Char.charName(char),
        "category": get_char_category(char),
        "script": icu.Script.getScript(char).getName(),
        "is_letter": icu.Char.isalpha(char),
        "is_digit": icu.Char.isdigit(char),
        "is_upper": icu.Char.isupper(char),
        "is_lower": icu.Char.islower(char),
        "is_whitespace": icu.Char.isWhitespace(char),
    }


def list_categories() -> List[Dict[str, str]]:
    """List all Unicode general categories.

    Returns:
        List of dicts with category code and description.

    Example:
        >>> cats = list_categories()
        >>> next(c for c in cats if c['code'] == 'Lu')
        {'code': 'Lu', 'description': 'Letter, uppercase'}
    """
    return [
        {"code": "Lu", "description": "Letter, uppercase"},
        {"code": "Ll", "description": "Letter, lowercase"},
        {"code": "Lt", "description": "Letter, titlecase"},
        {"code": "Lm", "description": "Letter, modifier"},
        {"code": "Lo", "description": "Letter, other"},
        {"code": "Mn", "description": "Mark, nonspacing"},
        {"code": "Mc", "description": "Mark, spacing combining"},
        {"code": "Me", "description": "Mark, enclosing"},
        {"code": "Nd", "description": "Number, decimal digit"},
        {"code": "Nl", "description": "Number, letter"},
        {"code": "No", "description": "Number, other"},
        {"code": "Pc", "description": "Punctuation, connector"},
        {"code": "Pd", "description": "Punctuation, dash"},
        {"code": "Ps", "description": "Punctuation, open"},
        {"code": "Pe", "description": "Punctuation, close"},
        {"code": "Pi", "description": "Punctuation, initial quote"},
        {"code": "Pf", "description": "Punctuation, final quote"},
        {"code": "Po", "description": "Punctuation, other"},
        {"code": "Sm", "description": "Symbol, math"},
        {"code": "Sc", "description": "Symbol, currency"},
        {"code": "Sk", "description": "Symbol, modifier"},
        {"code": "So", "description": "Symbol, other"},
        {"code": "Zs", "description": "Separator, space"},
        {"code": "Zl", "description": "Separator, line"},
        {"code": "Zp", "description": "Separator, paragraph"},
        {"code": "Cc", "description": "Other, control"},
        {"code": "Cf", "description": "Other, format"},
        {"code": "Cs", "description": "Other, surrogate"},
        {"code": "Co", "description": "Other, private use"},
        {"code": "Cn", "description": "Other, not assigned"},
    ]


def list_blocks() -> List[Dict[str, Any]]:
    """List all Unicode blocks.

    Returns:
        List of dicts with block names and ranges.

    Example:
        >>> blocks = list_blocks()
        >>> basic_latin = next(b for b in blocks if b['name'] == 'Basic Latin')
        >>> basic_latin['range']
        'U+0000-U+007F'
    """
    results = []
    block_prop = icu.UProperty.BLOCK
    min_val = icu.Char.getIntPropertyMinValue(block_prop)
    max_val = icu.Char.getIntPropertyMaxValue(block_prop)

    for i in range(min_val, max_val + 1):
        try:
            name = icu.Char.getPropertyValueName(
                block_prop, i, icu.UPropertyNameChoice.LONG_PROPERTY_NAME
            )
            if not name:
                continue

            uset = icu.UnicodeSet(f"[:Block={name}:]")
            if not uset.isEmpty():
                start = uset.getRangeStart(0)
                end = uset.getRangeEnd(uset.getRangeCount() - 1)

                # Ensure start and end are integers (PyICU may return them as strings/chars)
                if isinstance(start, str):
                    start = ord(start)
                if isinstance(end, str):
                    end = ord(end)

                results.append(
                    {
                        "name": name.replace("_", " "),
                        "range": f"U+{start:04X}-U+{end:04X}",
                        "start": start,
                        "end": end,
                    }
                )
        except icu.ICUError:
            continue

    return sorted(results, key=lambda x: x["start"])


def get_block_characters(block_name: str) -> List[str]:
    """Get all characters in a specific Unicode block.

    Args:
        block_name: Name of the block (e.g., 'Basic Latin').

    Returns:
        List of characters in the block.

    Raises:
        ValueError: If block name is invalid.
    """
    try:
        # ICU often expects underscores instead of spaces in property values
        normalized_name = block_name.replace(" ", "_")
        uset = icu.UnicodeSet(f"[:Block={normalized_name}:]")
        return list(uset)
    except icu.ICUError as e:
        raise ValueError(f"Invalid Unicode block name: {block_name}") from e


def get_category_characters(category_code: str) -> List[str]:
    """Get all characters in a specific Unicode general category.

    Args:
        category_code: Two-letter category code (e.g., 'Lu', 'Nd').

    Returns:
        List of characters in the category.

    Raises:
        ValueError: If category code is invalid.
    """
    try:
        uset = icu.UnicodeSet(f"[:{category_code}:]")
        return list(uset)
    except icu.ICUError as e:
        raise ValueError(f"Invalid Unicode category code: {category_code}") from e
