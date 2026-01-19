"""Utilities for handling locale and multi-value parsing."""

import re
from typing import List, Optional

import icu

from ..script import _MAX_SCRIPT_CODE


def _get_major_scripts() -> List[str]:
    """Get major scripts from ICU based on RECOMMENDED usage."""
    major = []
    for i in range(_MAX_SCRIPT_CODE):
        try:
            script = icu.Script(i)
            name = script.getName()
            if name and name != "Unknown":
                # RECOMMENDED usage (5) indicates actively used scripts
                if script.getUsage() == icu.UScriptUsage.RECOMMENDED:
                    major.append(name)
        except (ValueError, icu.ICUError):
            break
    return sorted(major)


# Major scripts derived from ICU's RECOMMENDED usage classification
MAJOR_SCRIPTS = _get_major_scripts()


def parse_multi_value(
    value: str,
    value_type: str = "locale",
    available_values: Optional[List[str]] = None,
) -> List[str]:
    """Parse a multi-value argument supporting comma-separated values and regex patterns.

    Args:
        value: The input value (comma-separated list or regex pattern)
        value_type: Type of value ('locale', 'script', 'transliterator', etc.)
        available_values: List of available values to match against

    Returns:
        List of matching values
    """
    if not value:
        return []

    value = value.strip()

    # Handle special keywords
    if value == "major":
        if value_type == "script":
            return MAJOR_SCRIPTS.copy()
        return []

    if value == "any":
        return available_values.copy() if available_values else []

    # Check if value contains regex special characters
    regex_chars = ["*", ".", "[", "]", "(", ")", "\\", "^", "$", "+", "?", "{", "}", "|"]
    is_pattern = any(char in value for char in regex_chars)

    if is_pattern and available_values:
        # Convert comma to pipe for regex OR operation
        pattern = value.replace(",", "|")
        try:
            regex = re.compile(f"^({pattern})$", re.IGNORECASE)
            return [item for item in available_values if regex.match(item)]
        except re.error:
            pass

    # Simple comma-separated values
    values = [v.strip() for v in value.split(",")]

    if available_values:
        lower_to_original = {val.lower(): val for val in available_values}
        result = []
        for v in values:
            v_lower = v.lower()
            if v_lower in lower_to_original:
                original = lower_to_original[v_lower]
                if original not in result:
                    result.append(original)
        return result

    return [v for v in values if v]
