"""Calendar system information.

Query available calendar systems (Gregorian, Buddhist, Hebrew, Islamic, etc.)
and their properties.

Key Features:
    * List all available calendar types
    * Get calendar info (type, description)
    * 17+ calendar systems supported

Calendar Types:
    * gregorian - Gregorian calendar (default Western calendar)
    * buddhist - Thai Buddhist calendar
    * chinese - Chinese lunar calendar
    * coptic - Coptic calendar (Egypt)
    * ethiopic - Ethiopian calendar
    * hebrew - Hebrew/Jewish calendar
    * indian - Indian National calendar
    * islamic - Islamic/Hijri calendar (various variants)
    * japanese - Japanese Imperial calendar
    * persian - Persian/Jalali calendar
    * roc - Republic of China (Taiwan) calendar

Example:
    List and query calendars::

        >>> from icukit import list_calendars, get_calendar_info
        >>>
        >>> # List all calendar types
        >>> cals = list_calendars()
        >>> 'hebrew' in cals
        True
        >>>
        >>> # Get info about a calendar
        >>> info = get_calendar_info('islamic')
        >>> info['type']
        'islamic'
"""

from typing import Any, Dict, List, Optional

import icu

# Calendar type descriptions (supplementary info for known types)
# PyICU doesn't expose Calendar.getKeywordValuesForLocale(), so we validate
# each type by attempting to instantiate it
_CALENDAR_DESCRIPTIONS = {
    "gregorian": "Gregorian calendar (Western standard)",
    "buddhist": "Thai Buddhist calendar",
    "chinese": "Chinese lunar calendar",
    "coptic": "Coptic calendar (Egypt)",
    "dangi": "Korean Dangi calendar",
    "ethiopic": "Ethiopian calendar",
    "ethiopic-amete-alem": "Ethiopian Amete Alem calendar",
    "hebrew": "Hebrew/Jewish calendar",
    "indian": "Indian National calendar",
    "islamic": "Islamic/Hijri calendar",
    "islamic-civil": "Islamic civil calendar",
    "islamic-rgsa": "Islamic calendar (Saudi Arabia)",
    "islamic-tbla": "Islamic tabular calendar",
    "islamic-umalqura": "Islamic Umm al-Qura calendar",
    "iso8601": "ISO 8601 calendar (Monday first, 4-day week rule)",
    "japanese": "Japanese Imperial calendar",
    "persian": "Persian/Jalali calendar",
    "roc": "Republic of China (Taiwan) calendar",
}


def _get_available_calendars() -> set:
    """Get calendar types that ICU actually supports.

    Validates each known type by attempting to create a calendar.
    Returns only types where ICU returns the same type (not a fallback).
    """
    available = set()
    for cal_type in _CALENDAR_DESCRIPTIONS:
        try:
            loc = icu.Locale(f"en@calendar={cal_type}")
            cal = icu.Calendar.createInstance(loc)
            # Only include if ICU returns the same type (not a fallback to gregorian)
            if cal.getType() == cal_type:
                available.add(cal_type)
        except icu.ICUError:
            pass
    return available


# Cache of validated calendar types (populated on first use)
_validated_calendars = None


def _get_validated_calendars() -> set:
    """Get cached set of validated calendar types."""
    global _validated_calendars
    if _validated_calendars is None:
        _validated_calendars = _get_available_calendars()
    return _validated_calendars


def list_calendars() -> List[str]:
    """List all available calendar types.

    Returns:
        List of calendar type names sorted alphabetically.

    Example:
        >>> cals = list_calendars()
        >>> 'gregorian' in cals
        True
        >>> 'hebrew' in cals
        True
    """
    return sorted(_get_validated_calendars())


def list_calendars_info() -> List[Dict[str, Any]]:
    """List all calendars with their info.

    Returns:
        List of dicts with calendar info.

    Example:
        >>> cals = list_calendars_info()
        >>> greg = next(c for c in cals if c['type'] == 'gregorian')
        >>> 'Western' in greg['description']
        True
    """
    return [get_calendar_info(cal_type) for cal_type in list_calendars()]


def get_calendar_info(cal_type: str) -> Optional[Dict[str, Any]]:
    """Get information about a calendar type.

    Args:
        cal_type: Calendar type name (e.g., 'gregorian', 'hebrew').

    Returns:
        Dict with calendar info, or None if not found.

    Example:
        >>> info = get_calendar_info('hebrew')
        >>> info['type']
        'hebrew'
    """
    cal_type = cal_type.lower()
    if cal_type not in _get_validated_calendars():
        return None

    # Get the actual ICU type
    try:
        loc = icu.Locale(f"en@calendar={cal_type}")
        cal = icu.Calendar.createInstance(loc)
        actual_type = cal.getType()
    except icu.ICUError:
        actual_type = cal_type

    return {
        "type": cal_type,
        "icu_type": actual_type,
        "description": _CALENDAR_DESCRIPTIONS.get(cal_type, ""),
    }


def is_valid_calendar(cal_type: str) -> bool:
    """Check if a calendar type is valid.

    Args:
        cal_type: Calendar type to check.

    Returns:
        True if valid, False otherwise.

    Example:
        >>> is_valid_calendar('gregorian')
        True
        >>> is_valid_calendar('invalid')
        False
    """
    return cal_type.lower() in _get_validated_calendars()
