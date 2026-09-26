"""Unicode text normalization and character properties.

Normalize text to standard Unicode forms (NFC, NFD, NFKC, NFKD) and
query Unicode character properties like names and categories.

Key Features:
    * Normalize text to NFC, NFD, NFKC, NFKD forms
    * Get Unicode character names, name aliases and extended names
    * Look up a character by its name
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

        >>> from icukit import char_from_name, get_char_name, get_char_category
        >>>
        >>> get_char_name('α')
        'GREEK SMALL LETTER ALPHA'
        >>> get_char_name('😀')
        'GRINNING FACE'
        >>> char_from_name('GREEK SMALL LETTER ALPHA')
        'α'
        >>>
        >>> get_char_category('A')
        'Lu'  # Letter, uppercase
        >>> get_char_category('5')
        'Nd'  # Number, decimal digit
"""

from __future__ import annotations

import codecs
import re
import warnings
from typing import Any

import icu

from .errors import NormalizationError

__all__ = [
    "NFC",
    "NFD",
    "NFKC",
    "NFKD",
    "char_from_name",
    "decode_unicode_escapes",
    "encode_unicode_escapes",
    "get_block_characters",
    "get_category_characters",
    "get_char_category",
    "get_char_info",
    "get_char_name",
    "get_char_names",
    "is_normalized",
    "list_blocks",
    "list_categories",
    "normalize",
]

_SURROGATE_OFFSET = 0x10000
_HIGH_SURROGATE_BASE = 0xD800
_LOW_SURROGATE_BASE = 0xDC00
_SURROGATE_SHIFT = 10
_SURROGATE_MASK = 0x3FF


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

# ICU's name choices, by the names this module gives them. ``charFromName`` searches one
# choice at a time, so ``any`` is the sequence that together covers every name.
_CHAR_NAME_CHOICES = {
    "unicode": icu.UCharNameChoice.UNICODE_CHAR_NAME,
    "alias": icu.UCharNameChoice.CHAR_NAME_ALIAS,
    "extended": icu.UCharNameChoice.EXTENDED_CHAR_NAME,
}
_CHAR_FROM_NAME_CHOICES = {
    "any": (icu.UCharNameChoice.EXTENDED_CHAR_NAME, icu.UCharNameChoice.CHAR_NAME_ALIAS),
    **{choice: (value,) for choice, value in _CHAR_NAME_CHOICES.items()},
}

_NORMALIZERS = {
    NFC: icu.Normalizer2.getNFCInstance,
    NFD: icu.Normalizer2.getNFDInstance,
    NFKC: icu.Normalizer2.getNFKCInstance,
    NFKD: icu.Normalizer2.getNFKDInstance,
}


# Each escape sequence Python's ``unicode_escape`` codec knows, matched one at a time so
# that the characters around it -- non-ASCII text above all -- are never passed through
# the codec, which reads its input as Latin-1.
_ESCAPE_RE = re.compile(
    r"\\(?:N\{[^}]*\}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|x[0-9A-Fa-f]{2}|[0-7]{1,3}"
    r"|[\\'\"abfnrtv\n])"
    r"|U\+([0-9A-Fa-f]{4,6})"
)


def _decode_escape(match: re.Match[str]) -> str:
    if match.group(1) is not None:
        codepoint = int(match.group(1), 16)
        return chr(codepoint) if codepoint <= 0x10FFFF else match.group(0)
    try:
        # An octal escape above \377 decodes, with a DeprecationWarning of its own.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return codecs.decode(match.group(0), "unicode_escape")
    except (UnicodeDecodeError, ValueError):
        return match.group(0)


def decode_unicode_escapes(text: str) -> str:
    """Decode Unicode escape sequences in text.

    Each escape Python's ``unicode_escape`` codec knows decodes as it does there
    (``\\uXXXX``, ``\\UXXXXXXXX``, ``\\xXX`` as code point ``U+00XX``, octal,
    ``\\N{NAME}``, and ``\\n``, ``\\t``, ``\\\\`` and the other single-character
    escapes), and ``U+XXXX`` through ``U+XXXXXX`` is the character it names. Every
    other character, including non-ASCII text and an escape that does not parse, is
    left as written.
    """
    return _ESCAPE_RE.sub(_decode_escape, text)


def encode_unicode_escapes(text: str, format: str = "uplus") -> str:
    """Encode text in one of the CLI's five Unicode escape formats.

    Args:
        text: Text to encode. Escape sequences are decoded before encoding.
        format: One of ``u``, ``U``, ``x``, ``uplus``, or ``char``.

    Returns:
        Encoded text, or decoded text for the ``char`` format.

    Raises:
        ValueError: If format is not supported.
    """
    text = decode_unicode_escapes(text)
    if format == "char":
        return text
    if format == "u":
        result = []
        for char in text:
            codepoint = ord(char)
            if codepoint < _SURROGATE_OFFSET:
                result.append(f"\\u{codepoint:04X}")
            else:
                codepoint -= _SURROGATE_OFFSET
                high = _HIGH_SURROGATE_BASE + (codepoint >> _SURROGATE_SHIFT)
                low = _LOW_SURROGATE_BASE + (codepoint & _SURROGATE_MASK)
                result.append(f"\\u{high:04X}\\u{low:04X}")
        return "".join(result)
    if format == "U":
        return "".join(f"\\U{ord(char):08X}" for char in text)
    if format == "x":
        return "".join(f"\\x{byte:02X}" for byte in text.encode("utf-8"))
    if format == "uplus":
        return " ".join(f"U+{ord(char):04X}" for char in text)
    raise ValueError(f"Invalid escape format: {format}")


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


def _name_choice(choice: str, choices: dict[str, Any]) -> Any:
    try:
        return choices[choice]
    except (KeyError, TypeError):
        raise ValueError(
            f"Invalid name choice: {choice!r}. Use one of: {', '.join(choices)}."
        ) from None


def get_char_name(char: str, choice: str = "unicode") -> str:
    """Get a Unicode name of a character.

    ICU keeps three names for a code point, and ``choice`` selects one:

    * ``unicode`` -- the formal name (the Unicode ``Name`` property). Empty for a code
      point that has none: a control, a surrogate, a noncharacter, a private-use or an
      unassigned code point.
    * ``alias`` -- the formal name alias Unicode published to correct a mistaken name,
      such as ``LATIN CAPITAL LETTER GHA`` for U+01A2, whose formal name
      ``LATIN CAPITAL LETTER OI`` stays fixed by the stability policy. ICU carries only
      these corrections, not the other kinds of alias in ``NameAliases.txt`` (``BEL``,
      ``ALERT``, ``NBSP`` and the like). Empty where there is none, which is almost
      everywhere.
    * ``extended`` -- the formal name where there is one, and otherwise a label that
      names the code point by its type, such as ``<control-0007>``,
      ``<noncharacter-FFFF>`` or ``<unassigned-D7A4>``. Never empty.

    Args:
        char: A single character.
        choice: ``unicode`` (the default), ``alias``, or ``extended``.

    Returns:
        The chosen name, or an empty string where ICU has none of that kind.

    Raises:
        ValueError: If input is not a single character, or choice is not one of the
            three.

    Example:
        >>> get_char_name('A')
        'LATIN CAPITAL LETTER A'
        >>> get_char_name('α')
        'GREEK SMALL LETTER ALPHA'
        >>> get_char_name('你')
        'CJK UNIFIED IDEOGRAPH-4F60'
        >>> get_char_name('😀')
        'GRINNING FACE'
        >>> get_char_name('Ƣ', 'alias')
        'LATIN CAPITAL LETTER GHA'
        >>> get_char_name('\\x07', 'extended')
        '<control-0007>'
    """
    name_choice = _name_choice(choice, _CHAR_NAME_CHOICES)
    if len(char) != 1:
        raise ValueError("Input must be a single character")
    return icu.Char.charName(char, name_choice)


def get_char_names(char: str) -> dict[str, str]:
    """Get all three of ICU's names for a character.

    Args:
        char: A single character.

    Returns:
        Dict with the ``unicode``, ``alias`` and ``extended`` names, as
        :func:`get_char_name` returns each.

    Raises:
        ValueError: If input is not a single character.

    Example:
        >>> names = get_char_names('Ƣ')
        >>> names['unicode'], names['alias']
        ('LATIN CAPITAL LETTER OI', 'LATIN CAPITAL LETTER GHA')
    """
    return {choice: get_char_name(char, choice) for choice in _CHAR_NAME_CHOICES}


def char_from_name(name: str, choice: str = "any") -> str:
    """Look up the character a Unicode name names.

    The lookup is ICU's, exact apart from case: ICU matches names without regard to
    case, and nothing looser is added here -- no trimming, no collapsing of spaces or
    hyphens. ``choice`` selects the names searched:

    * ``unicode`` -- formal names, including the algorithmic ones such as
      ``HANGUL SYLLABLE GAG`` and ``CJK UNIFIED IDEOGRAPH-4F60``.
    * ``alias`` -- formal name aliases only, such as ``LATIN CAPITAL LETTER GHA``;
      the correction aliases alone, as :func:`get_char_name` describes.
    * ``extended`` -- formal names and the labels :func:`get_char_name` gives for
      ``extended``, such as ``<control-0007>``.
    * ``any`` (the default) -- all of the above. Unicode keeps names and aliases in
      one namespace, so no name is both one character's name and another's alias.

    Args:
        name: A character name.
        choice: ``any`` (the default), ``unicode``, ``alias``, or ``extended``.

    Returns:
        The named character.

    Raises:
        ValueError: If no character has that name among the names searched, or choice
            is not one of the four.
        TypeError: If name is not a str.

    Example:
        >>> char_from_name('GREEK SMALL LETTER ALPHA')
        'α'
        >>> char_from_name('greek small letter alpha')
        'α'
        >>> char_from_name('LATIN CAPITAL LETTER GHA')
        'Ƣ'
        >>> char_from_name('<control-0007>')
        '\\x07'
    """
    if not isinstance(name, str):
        raise TypeError(f"Character name must be a str, not {type(name).__name__}")
    name_choices = _name_choice(choice, _CHAR_FROM_NAME_CHOICES)
    try:
        encoded = name.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(f"Unknown character name: {name!r}") from None
    for name_choice in name_choices:
        try:
            return chr(icu.Char.charFromName(encoded, name_choice))
        except (icu.ICUError, ValueError):
            continue
    raise ValueError(f"Unknown character name: {name!r}")


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


def get_char_info(char: str) -> dict[str, Any]:
    """Get comprehensive information about a character.

    Args:
        char: A single character.

    Returns:
        Dict with character info: codepoint, name, category, script, etc. ``name`` is
        the formal name, ``alias`` the formal name alias (empty where there is none),
        and ``extended_name`` the extended name, which names every code point, as
        :func:`get_char_name` describes each.

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
        "name": get_char_name(char),
        "alias": get_char_name(char, "alias"),
        "extended_name": get_char_name(char, "extended"),
        "category": get_char_category(char),
        "script": icu.Script.getScript(char).getName(),
        "is_letter": icu.Char.isalpha(char),
        "is_digit": icu.Char.isdigit(char),
        "is_upper": icu.Char.isupper(char),
        "is_lower": icu.Char.islower(char),
        "is_whitespace": icu.Char.isWhitespace(char),
    }


def list_categories() -> list[dict[str, str]]:
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


def list_blocks() -> list[dict[str, Any]]:
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


def get_block_characters(block_name: str) -> list[str]:
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


def get_category_characters(category_code: str) -> list[str]:
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
