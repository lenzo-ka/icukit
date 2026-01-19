"""
Confusable and homoglyph detection using ICU's SpoofChecker.

ICU's SpoofChecker detects visually confusable strings that could be used
in phishing or spoofing attacks (e.g., Cyrillic "а" vs Latin "a").

Example:
    >>> from icukit import are_confusable, get_skeleton
    >>> are_confusable("paypal", "pаypal")  # Cyrillic 'а'
    True
    >>> get_skeleton("pаypal")
    'paypal'
"""

from typing import Any

import icu

from .errors import SpoofError

__all__ = [
    "are_confusable",
    "check_string",
    "get_skeleton",
    "get_confusable_info",
    "SpoofChecker",
    "CONFUSABLE_NONE",
    "CONFUSABLE_SINGLE_SCRIPT",
    "CONFUSABLE_MIXED_SCRIPT",
    "CONFUSABLE_WHOLE_SCRIPT",
]

# Confusable result flags (bitmask values from ICU)
CONFUSABLE_NONE = 0
CONFUSABLE_SINGLE_SCRIPT = icu.USpoofChecks.SINGLE_SCRIPT_CONFUSABLE
CONFUSABLE_MIXED_SCRIPT = icu.USpoofChecks.MIXED_SCRIPT_CONFUSABLE
CONFUSABLE_WHOLE_SCRIPT = icu.USpoofChecks.WHOLE_SCRIPT_CONFUSABLE

# Check result flags
_CHECK_SINGLE_SCRIPT_CONFUSABLE = icu.USpoofChecks.SINGLE_SCRIPT_CONFUSABLE
_CHECK_MIXED_SCRIPT_CONFUSABLE = icu.USpoofChecks.MIXED_SCRIPT_CONFUSABLE
_CHECK_WHOLE_SCRIPT_CONFUSABLE = icu.USpoofChecks.WHOLE_SCRIPT_CONFUSABLE
_CHECK_ANY_CASE = icu.USpoofChecks.ANY_CASE
_CHECK_RESTRICTION_LEVEL = icu.USpoofChecks.RESTRICTION_LEVEL
_CHECK_INVISIBLE = icu.USpoofChecks.INVISIBLE
_CHECK_CHAR_LIMIT = icu.USpoofChecks.CHAR_LIMIT
_CHECK_MIXED_NUMBERS = icu.USpoofChecks.MIXED_NUMBERS
_CHECK_HIDDEN_OVERLAY = 256  # Not in USpoofChecks? checking...


def are_confusable(string1: str, string2: str) -> bool:
    """
    Check if two strings are visually confusable.

    Two strings are confusable if they could be mistaken for each other,
    such as when one uses lookalike characters from different scripts.

    Args:
        string1: First string to compare.
        string2: Second string to compare.

    Returns:
        True if the strings are confusable, False otherwise.

    Example:
        >>> are_confusable("paypal", "pаypal")  # Second has Cyrillic 'а'
        True
        >>> are_confusable("hello", "world")
        False
    """
    try:
        checker = icu.SpoofChecker()
        result = checker.areConfusable(string1, string2)
        return result != CONFUSABLE_NONE
    except icu.ICUError as e:
        raise SpoofError(f"Failed to check confusability: {e}") from e


def get_confusable_type(string1: str, string2: str) -> int:
    """
    Get the type of confusability between two strings.

    Args:
        string1: First string to compare.
        string2: Second string to compare.

    Returns:
        Bitmask indicating confusability type:
        - CONFUSABLE_NONE (0): Not confusable
        - CONFUSABLE_SINGLE_SCRIPT (1): Confusable within same script
        - CONFUSABLE_MIXED_SCRIPT (2): Confusable across scripts
        - CONFUSABLE_WHOLE_SCRIPT (4): Entire string looks like different script

    Example:
        >>> get_confusable_type("paypal", "pаypal")
        2  # CONFUSABLE_MIXED_SCRIPT
    """
    try:
        checker = icu.SpoofChecker()
        return checker.areConfusable(string1, string2)
    except icu.ICUError as e:
        raise SpoofError(f"Failed to check confusability: {e}") from e


def get_skeleton(text: str) -> str:
    """
    Get the skeleton form of a string for confusability comparison.

    The skeleton is a normalized form where visually similar characters
    are mapped to a common representation. Two strings with the same
    skeleton are confusable.

    Args:
        text: String to get skeleton for.

    Returns:
        Skeleton string.

    Example:
        >>> get_skeleton("pаypal")  # Cyrillic 'а'
        'paypal'
        >>> get_skeleton("paypal")
        'paypal'
    """
    try:
        checker = icu.SpoofChecker()
        # PyICU getSkeleton takes (type, string) where type is usually 0
        return checker.getSkeleton(0, text)
    except icu.ICUError as e:
        raise SpoofError(f"Failed to get skeleton: {e}") from e


def check_string(text: str) -> dict[str, Any]:
    """
    Check a string for potential spoofing issues.

    Analyzes the string for mixed scripts, invisible characters,
    and other potential security issues.

    Args:
        text: String to check.

    Returns:
        Dict with check results:
        - 'flags': Raw check result flags
        - 'is_suspicious': True if any issues detected
        - 'mixed_script': Contains mixed scripts
        - 'restriction_level': Restriction level issue
        - 'invisible': Contains invisible characters
        - 'mixed_numbers': Contains mixed number systems

    Example:
        >>> result = check_string("pаypal")  # Cyrillic 'а'
        >>> result['is_suspicious']
        True
        >>> result['mixed_script']
        True
    """
    try:
        checker = icu.SpoofChecker()
        flags = checker.check(text)

        return {
            "flags": flags,
            "is_suspicious": flags != 0,
            "mixed_script": bool(flags & _CHECK_MIXED_SCRIPT_CONFUSABLE),
            "whole_script": bool(flags & _CHECK_WHOLE_SCRIPT_CONFUSABLE),
            "restriction_level": bool(flags & _CHECK_RESTRICTION_LEVEL),
            "invisible": bool(flags & _CHECK_INVISIBLE),
            "mixed_numbers": bool(flags & _CHECK_MIXED_NUMBERS),
        }
    except icu.ICUError as e:
        raise SpoofError(f"Failed to check string: {e}") from e


def get_confusable_info(string1: str, string2: str) -> dict[str, Any]:
    """
    Get detailed confusability information between two strings.

    Args:
        string1: First string to compare.
        string2: Second string to compare.

    Returns:
        Dict with confusability details:
        - 'confusable': Whether strings are confusable
        - 'type': Confusability type flags
        - 'type_names': List of type names
        - 'skeleton1': Skeleton of first string
        - 'skeleton2': Skeleton of second string
        - 'same_skeleton': Whether skeletons match

    Example:
        >>> info = get_confusable_info("paypal", "pаypal")
        >>> info['confusable']
        True
        >>> info['type_names']
        ['mixed_script']
    """
    try:
        checker = icu.SpoofChecker()
        conf_type = checker.areConfusable(string1, string2)
        skel1 = checker.getSkeleton(0, string1)
        skel2 = checker.getSkeleton(0, string2)

        type_names = []
        if conf_type & CONFUSABLE_SINGLE_SCRIPT:
            type_names.append("single_script")
        if conf_type & CONFUSABLE_MIXED_SCRIPT:
            type_names.append("mixed_script")
        if conf_type & CONFUSABLE_WHOLE_SCRIPT:
            type_names.append("whole_script")

        return {
            "confusable": conf_type != CONFUSABLE_NONE,
            "type": conf_type,
            "type_names": type_names,
            "skeleton1": skel1,
            "skeleton2": skel2,
            "same_skeleton": skel1 == skel2,
        }
    except icu.ICUError as e:
        raise SpoofError(f"Failed to get confusable info: {e}") from e


class SpoofChecker:
    """
    Reusable spoof checker for multiple operations.

    Example:
        >>> checker = SpoofChecker()
        >>> checker.are_confusable("paypal", "pаypal")
        True
        >>> checker.get_skeleton("pаypal")
        'paypal'
    """

    def __init__(self):
        """Create a new SpoofChecker."""
        try:
            self._checker = icu.SpoofChecker()
        except icu.ICUError as e:
            raise SpoofError(f"Failed to create SpoofChecker: {e}") from e

    def are_confusable(self, string1: str, string2: str) -> bool:
        """Check if two strings are confusable."""
        try:
            return self._checker.areConfusable(string1, string2) != CONFUSABLE_NONE
        except icu.ICUError as e:
            raise SpoofError(f"Failed to check confusability: {e}") from e

    def get_confusable_type(self, string1: str, string2: str) -> int:
        """Get confusability type between two strings."""
        try:
            return self._checker.areConfusable(string1, string2)
        except icu.ICUError as e:
            raise SpoofError(f"Failed to check confusability: {e}") from e

    def get_skeleton(self, text: str) -> str:
        """Get skeleton form of a string."""
        try:
            return self._checker.getSkeleton(0, text)
        except icu.ICUError as e:
            raise SpoofError(f"Failed to get skeleton: {e}") from e

    def check(self, text: str) -> dict[str, Any]:
        """Check string for spoofing issues."""
        try:
            flags = self._checker.check(text)
            return {
                "flags": flags,
                "is_suspicious": flags != 0,
                "mixed_script": bool(flags & _CHECK_MIXED_SCRIPT_CONFUSABLE),
                "whole_script": bool(flags & _CHECK_WHOLE_SCRIPT_CONFUSABLE),
                "restriction_level": bool(flags & _CHECK_RESTRICTION_LEVEL),
                "invisible": bool(flags & _CHECK_INVISIBLE),
                "mixed_numbers": bool(flags & _CHECK_MIXED_NUMBERS),
            }
        except icu.ICUError as e:
            raise SpoofError(f"Failed to check string: {e}") from e

    def __repr__(self) -> str:
        return "SpoofChecker()"
