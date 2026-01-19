"""
Bidirectional text handling.

ICU's BiDi implementation provides the Unicode Bidirectional Algorithm (UBA)
for handling mixed left-to-right and right-to-left text.

Key Features:
    * Detect text direction (LTR, RTL, mixed)
    * Get paragraph embedding level
    * Strip invisible bidi control characters
    * List bidi control characters

Example:
    >>> from icukit import get_bidi_info, strip_bidi_controls
    >>> get_bidi_info('Hello שלום')
    {'direction': 'mixed', 'base_direction': 'ltr', 'has_rtl': True, 'has_ltr': True}
    >>> strip_bidi_controls('hello\\u200fworld')
    'helloworld'
"""

import icu

from .errors import BidiError

__all__ = [
    "get_base_direction",
    "get_bidi_info",
    "strip_bidi_controls",
    "has_bidi_controls",
    "list_bidi_controls",
    "DIRECTION_LTR",
    "DIRECTION_RTL",
    "DIRECTION_MIXED",
    "DIRECTION_NEUTRAL",
]

# Direction constants
DIRECTION_LTR = "ltr"
DIRECTION_RTL = "rtl"
DIRECTION_MIXED = "mixed"
DIRECTION_NEUTRAL = "neutral"

# Bidi control character codepoints and abbreviations
# Abbreviations are standard Unicode short names (not provided by ICU)
_BIDI_CONTROL_ABBREVS = {
    "\u200e": "LRM",
    "\u200f": "RLM",
    "\u061c": "ALM",
    "\u202a": "LRE",
    "\u202b": "RLE",
    "\u202c": "PDF",
    "\u202d": "LRO",
    "\u202e": "RLO",
    "\u2066": "LRI",
    "\u2067": "RLI",
    "\u2068": "FSI",
    "\u2069": "PDI",
}


def _get_bidi_control_name(char: str) -> str:
    """Get the Unicode name for a bidi control character from ICU."""
    name = icu.Char.charName(char)
    # Convert from "LEFT-TO-RIGHT MARK" to "Left-To-Right Mark"
    return name.title() if name else "Unknown"


def _get_bidi_controls() -> dict:
    """Build bidi controls dict with names from ICU."""
    return {
        char: (abbrev, _get_bidi_control_name(char))
        for char, abbrev in _BIDI_CONTROL_ABBREVS.items()
    }


# Bidi control characters (invisible formatting controls)
# Names retrieved from ICU, abbreviations are standard Unicode short names
_BIDI_CONTROLS = _get_bidi_controls()

_BIDI_CONTROL_CHARS = set(_BIDI_CONTROLS.keys())


def get_base_direction(text: str) -> str:
    """
    Get the base direction of text using the first strong directional character.

    Args:
        text: Text to analyze.

    Returns:
        Direction string: 'ltr', 'rtl', or 'neutral' if no strong characters.

    Example:
        >>> get_base_direction('Hello')
        'ltr'
        >>> get_base_direction('שלום')
        'rtl'
        >>> get_base_direction('123')
        'neutral'
    """
    try:
        # Handle empty text
        if not text:
            return DIRECTION_NEUTRAL
        # Bidi.getBaseDirection returns UBIDI_LTR (0), UBIDI_RTL (1), or UBIDI_NEUTRAL (3)
        direction = icu.Bidi.getBaseDirection(text)
        if direction == icu.UBiDiDirection.LTR:
            return DIRECTION_LTR
        elif direction == icu.UBiDiDirection.RTL:
            return DIRECTION_RTL
        else:  # UBIDI_NEUTRAL
            return DIRECTION_NEUTRAL
    except icu.ICUError as e:
        raise BidiError(f"Failed to get base direction: {e}") from e


def get_bidi_info(text: str) -> dict:
    """
    Get bidirectional text information.

    Args:
        text: Text to analyze.

    Returns:
        Dictionary with:
            - direction: 'ltr', 'rtl', 'mixed', or 'neutral'
            - base_direction: 'ltr', 'rtl', or 'neutral'
            - has_rtl: True if text contains RTL characters
            - has_ltr: True if text contains LTR characters
            - bidi_control_count: Number of bidi control characters

    Example:
        >>> get_bidi_info('Hello שלום')
        {'direction': 'mixed', 'base_direction': 'ltr', 'has_rtl': True, ...}
    """
    try:
        base_dir = get_base_direction(text)

        # Check for RTL and LTR characters
        has_rtl = False
        has_ltr = False
        control_count = 0

        for char in text:
            if char in _BIDI_CONTROL_CHARS:
                control_count += 1
                continue

            # Get bidi class using ICU
            bidi_class = icu.Char.charDirection(char)
            # R, AL, AN are RTL; L is LTR
            if bidi_class in (
                icu.UCharDirection.RIGHT_TO_LEFT,
                icu.UCharDirection.RIGHT_TO_LEFT_ARABIC,
                icu.UCharDirection.ARABIC_NUMBER,
            ):
                has_rtl = True
            elif bidi_class == icu.UCharDirection.LEFT_TO_RIGHT:
                has_ltr = True

        # Determine overall direction
        if has_rtl and has_ltr:
            direction = DIRECTION_MIXED
        elif has_rtl:
            direction = DIRECTION_RTL
        elif has_ltr:
            direction = DIRECTION_LTR
        else:
            direction = DIRECTION_NEUTRAL

        return {
            "direction": direction,
            "base_direction": base_dir,
            "has_rtl": has_rtl,
            "has_ltr": has_ltr,
            "bidi_control_count": control_count,
        }
    except icu.ICUError as e:
        raise BidiError(f"Failed to get bidi info: {e}") from e


def strip_bidi_controls(text: str) -> str:
    """
    Remove all bidirectional control characters from text.

    Useful for security (preventing bidi-based text spoofing attacks like
    CVE-2021-42574 "Trojan Source") and cleaning text for processing.

    Args:
        text: Text to clean.

    Returns:
        Text with bidi controls removed.

    Example:
        >>> strip_bidi_controls('hello\\u200fworld')
        'helloworld'
        >>> strip_bidi_controls('a\\u202eb\\u202cc')
        'abc'
    """
    return "".join(c for c in text if c not in _BIDI_CONTROL_CHARS)


def has_bidi_controls(text: str) -> bool:
    """
    Check if text contains any bidirectional control characters.

    Args:
        text: Text to check.

    Returns:
        True if text contains bidi controls, False otherwise.

    Example:
        >>> has_bidi_controls('hello world')
        False
        >>> has_bidi_controls('hello\\u200fworld')
        True
    """
    return any(c in _BIDI_CONTROL_CHARS for c in text)


def list_bidi_controls() -> list[dict]:
    """
    List all bidirectional control characters.

    Returns:
        List of dicts with char, codepoint, abbrev, and name.

    Example:
        >>> controls = list_bidi_controls()
        >>> controls[0]
        {'char': '\\u200e', 'codepoint': 'U+200E', 'abbrev': 'LRM', 'name': 'Left-to-Right Mark'}
    """
    result = []
    for char, (abbrev, name) in sorted(_BIDI_CONTROLS.items(), key=lambda x: ord(x[0])):
        result.append(
            {
                "char": char,
                "codepoint": f"U+{ord(char):04X}",
                "abbrev": abbrev,
                "name": name,
            }
        )
    return result
