"""Timezone information and utilities.

Query timezone data including offsets, DST rules, and display names.

Key Features:
    * List all available timezones (637+)
    * Get timezone info (offset, DST, display name)
    * Query equivalent timezone IDs
    * Get current offset for a timezone

Example:
    List and query timezones::

        >>> from icukit import list_timezones, get_timezone_info
        >>>
        >>> # List all timezones
        >>> tzs = list_timezones()
        >>> len(tzs)
        637
        >>>
        >>> # Get info about a timezone
        >>> info = get_timezone_info('America/New_York')
        >>> info['offset_hours']
        -5.0
        >>> info['uses_dst']
        True
"""

from typing import Any, Dict, List, Optional

import icu

from .errors import TimezoneError


def list_timezones(country: Optional[str] = None) -> List[str]:
    """List all available timezone IDs.

    Args:
        country: Optional ISO 3166 country code to filter by (e.g., 'US', 'DE').

    Returns:
        List of timezone IDs sorted alphabetically.

    Example:
        >>> tzs = list_timezones()
        >>> 'America/New_York' in tzs
        True
        >>> us_tzs = list_timezones('US')
        >>> 'America/New_York' in us_tzs
        True
    """
    if country:
        tz_enum = icu.TimeZone.createEnumeration(country.upper())
    else:
        tz_enum = icu.TimeZone.createEnumeration()
    return sorted(list(tz_enum))


def list_timezones_info(country: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all timezones with their info.

    Args:
        country: Optional country code to filter by.

    Returns:
        List of dicts with timezone info.

    Example:
        >>> tzs = list_timezones_info()
        >>> nyc = next(t for t in tzs if t['id'] == 'America/New_York')
        >>> nyc['uses_dst']
        True
    """
    ids = list_timezones(country)
    return [get_timezone_info(tz_id) for tz_id in ids]


def get_timezone_info(tz_id: str, extended: bool = False) -> Optional[Dict[str, Any]]:
    """Get information about a timezone.

    Args:
        tz_id: Timezone ID (e.g., 'America/New_York', 'Europe/London').
        extended: Include extended attributes (region, windows_id, equivalent_ids).

    Returns:
        Dict with timezone info, or None if not found.

    Example:
        >>> info = get_timezone_info('America/New_York')
        >>> info['id']
        'America/New_York'
        >>> info['display_name']
        'Eastern Standard Time'
        >>> info = get_timezone_info('America/New_York', extended=True)
        >>> info['extended']['region']
        'US'
    """
    tz = icu.TimeZone.createTimeZone(tz_id)

    # Check if timezone was found (ICU returns GMT or Etc/Unknown for unknown)
    actual_id = tz.getID()
    if (
        actual_id != tz_id
        and actual_id in ("GMT", "Etc/Unknown")
        and tz_id not in ("GMT", "Etc/Unknown")
    ):
        return None

    raw_offset_ms = tz.getRawOffset()
    offset_hours = raw_offset_ms / 3600000

    info = {
        "id": actual_id,
        "display_name": tz.getDisplayName(),
        "offset_hours": offset_hours,
        "offset_formatted": _format_offset(offset_hours),
        "uses_dst": tz.useDaylightTime(),
        "dst_savings_hours": tz.getDSTSavings() / 3600000 if tz.useDaylightTime() else 0,
    }

    if extended:
        # Get region
        try:
            region = icu.TimeZone.getRegion(tz_id)
        except icu.ICUError:
            region = None

        # Get Windows ID
        try:
            windows_id = icu.TimeZone.getWindowsID(tz_id)
        except icu.ICUError:
            windows_id = None

        # Get equivalent IDs
        equiv_ids = get_equivalent_timezones(tz_id)

        info["extended"] = {
            "region": region or None,
            "windows_id": windows_id or None,
            "equivalent_ids": equiv_ids if len(equiv_ids) > 1 else None,
        }

    return info


def get_equivalent_timezones(tz_id: str) -> List[str]:
    """Get equivalent timezone IDs for a timezone.

    Args:
        tz_id: Timezone ID.

    Returns:
        List of equivalent timezone IDs.

    Example:
        >>> equivs = get_equivalent_timezones('America/New_York')
        >>> 'US/Eastern' in equivs
        True
    """
    count = icu.TimeZone.countEquivalentIDs(tz_id)
    return [icu.TimeZone.getEquivalentID(tz_id, i) for i in range(count)]


def get_timezone_offset(tz_id: str) -> float:
    """Get the current UTC offset for a timezone in hours.

    Args:
        tz_id: Timezone ID.

    Returns:
        Offset in hours (negative for west of UTC).

    Raises:
        TimezoneError: If timezone is not found.

    Example:
        >>> get_timezone_offset('America/New_York')
        -5.0  # or -4.0 during DST
    """
    info = get_timezone_info(tz_id)
    if info is None:
        raise TimezoneError(f"Unknown timezone: {tz_id}")
    return info["offset_hours"]


def _format_offset(hours: float) -> str:
    """Format offset hours as UTC+/-HH:MM string."""
    sign = "+" if hours >= 0 else "-"
    abs_hours = abs(hours)
    h = int(abs_hours)
    m = int((abs_hours - h) * 60)
    if m:
        return f"UTC{sign}{h:02d}:{m:02d}"
    return f"UTC{sign}{h:d}"
