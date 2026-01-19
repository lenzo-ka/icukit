"""
Locale-aware duration formatting.

Format time durations (e.g., "2 hours, 30 minutes") with proper locale
conventions using ICU's MeasureFormat.

Width Styles:
    WIDE   - "2 hours, 30 minutes, 15 seconds"
    SHORT  - "2 hr, 30 min, 15 sec"
    NARROW - "2h 30m 15s"

Example:
    >>> from icukit import format_duration, DurationFormatter
    >>>
    >>> format_duration(3661)  # seconds
    '1 hour, 1 minute, 1 second'
    >>>
    >>> format_duration(3661, locale="de_DE")
    '1 Stunde, 1 Minute und 1 Sekunde'
    >>>
    >>> format_duration(3661, width="SHORT")
    '1 hr, 1 min, 1 sec'
    >>>
    >>> fmt = DurationFormatter("ja_JP", width="NARROW")
    >>> fmt.format(hours=2, minutes=30)
    '2時間30分'
"""

import re

import icu

from .errors import DurationError

__all__ = [
    "DurationFormatter",
    "format_duration",
    "parse_iso_duration",
    "WIDTH_WIDE",
    "WIDTH_SHORT",
    "WIDTH_NARROW",
]

# Width constants
WIDTH_WIDE = "WIDE"
WIDTH_SHORT = "SHORT"
WIDTH_NARROW = "NARROW"

_WIDTH_MAP = {
    WIDTH_WIDE: icu.UMeasureFormatWidth.WIDE,
    WIDTH_SHORT: icu.UMeasureFormatWidth.SHORT,
    WIDTH_NARROW: icu.UMeasureFormatWidth.NARROW,
}

# Duration unit names for MeasureUnit
_DURATION_UNITS = {
    "year": "year",
    "month": "month",
    "week": "week",
    "day": "day",
    "hour": "hour",
    "minute": "minute",
    "second": "second",
    "millisecond": "millisecond",
}


def parse_iso_duration(iso_string: str) -> dict:
    """Parse an ISO 8601 duration string.

    Args:
        iso_string: ISO 8601 duration (e.g., "P2DT3H30M", "PT1H30M")

    Returns:
        Dictionary with duration components (years, months, days, hours, minutes, seconds)

    Raises:
        DurationError: If parsing fails

    Example:
        >>> parse_iso_duration("P2DT3H30M")
        {'years': 0, 'months': 0, 'weeks': 0, 'days': 2, 'hours': 3, 'minutes': 30, 'seconds': 0}
        >>> parse_iso_duration("PT1H30M15S")
        {'years': 0, 'months': 0, 'weeks': 0, 'days': 0, 'hours': 1, 'minutes': 30, 'seconds': 15}
    """
    result = {
        "years": 0,
        "months": 0,
        "weeks": 0,
        "days": 0,
        "hours": 0,
        "minutes": 0,
        "seconds": 0,
    }

    s = iso_string.strip().upper()
    if not s.startswith("P"):
        raise DurationError(f"Invalid ISO 8601 duration: must start with 'P': {iso_string}")

    s = s[1:]  # Remove P

    # Split into date and time parts
    if "T" in s:
        date_part, time_part = s.split("T", 1)
    else:
        date_part, time_part = s, ""

    # Parse date part (Y, M, W, D)
    date_pattern = re.compile(r"(\d+(?:\.\d+)?)(Y|M|W|D)")
    for match in date_pattern.finditer(date_part):
        value = float(match.group(1))
        unit = match.group(2)
        if unit == "Y":
            result["years"] = value
        elif unit == "M":
            result["months"] = value
        elif unit == "W":
            result["weeks"] = value
        elif unit == "D":
            result["days"] = value

    # Parse time part (H, M, S)
    time_pattern = re.compile(r"(\d+(?:\.\d+)?)(H|M|S)")
    for match in time_pattern.finditer(time_part):
        value = float(match.group(1))
        unit = match.group(2)
        if unit == "H":
            result["hours"] = value
        elif unit == "M":
            result["minutes"] = value
        elif unit == "S":
            result["seconds"] = value

    return result


class DurationFormatter:
    """Locale-aware duration formatter.

    Formats time durations with proper locale conventions.

    Example:
        >>> fmt = DurationFormatter("en_US")
        >>> fmt.format(hours=2, minutes=30)
        '2 hours, 30 minutes'
        >>> fmt.format(seconds=3661)
        '1 hour, 1 minute, 1 second'
    """

    def __init__(self, locale: str = "en_US", width: str = WIDTH_WIDE):
        """Create a DurationFormatter.

        Args:
            locale: Locale code (e.g., "en_US", "de_DE")
            width: Width style (WIDE, SHORT, NARROW)
        """
        self.locale = locale
        self.width = width

        if width not in _WIDTH_MAP:
            raise DurationError(f"Invalid width: {width}. Valid: {list(_WIDTH_MAP.keys())}")

        self._icu_locale = icu.Locale(locale)
        self._formatter = icu.MeasureFormat(self._icu_locale, _WIDTH_MAP[width])

    def format(
        self,
        seconds: float | None = None,
        minutes: float = 0,
        hours: float = 0,
        days: float = 0,
        weeks: float = 0,
        months: float = 0,
        years: float = 0,
    ) -> str:
        """Format a duration.

        Args:
            seconds: Total seconds (will be decomposed if other args are 0),
                    or just the seconds component if other args are provided
            minutes: Minutes component
            hours: Hours component
            days: Days component
            weeks: Weeks component
            months: Months component
            years: Years component

        Returns:
            Formatted duration string

        Example:
            >>> fmt.format(seconds=3661)
            '1 hour, 1 minute, 1 second'
            >>> fmt.format(hours=2, minutes=30)
            '2 hours, 30 minutes'
        """
        # If only seconds provided, decompose into components
        if (
            seconds is not None
            and minutes == 0
            and hours == 0
            and days == 0
            and weeks == 0
            and months == 0
            and years == 0
        ):
            years, seconds = divmod(seconds, 31536000)  # 365 days
            months, seconds = divmod(seconds, 2592000)  # 30 days
            weeks, seconds = divmod(seconds, 604800)  # 7 days
            days, seconds = divmod(seconds, 86400)
            hours, seconds = divmod(seconds, 3600)
            minutes, seconds = divmod(seconds, 60)

        # Build list of measures
        measures = []
        components = [
            (years, "year"),
            (months, "month"),
            (weeks, "week"),
            (days, "day"),
            (hours, "hour"),
            (minutes, "minute"),
            (seconds or 0, "second"),
        ]

        for value, unit in components:
            if value and value != 0:
                try:
                    measure = icu.Measure(float(value), icu.MeasureUnit.forIdentifier(unit))
                    measures.append(measure)
                except icu.ICUError as e:
                    raise DurationError(f"Failed to create measure for {value} {unit}: {e}") from e

        if not measures:
            # No duration, return "0 seconds"
            try:
                measure = icu.Measure(0.0, icu.MeasureUnit.forIdentifier("second"))
                return self._formatter.formatMeasure(measure)
            except icu.ICUError as e:
                raise DurationError(f"Failed to format zero duration: {e}") from e

        # Format the measures individually and join
        # (formatMeasures doesn't work in some PyICU versions)
        try:
            parts = [self._formatter.formatMeasure(m) for m in measures]
            return " ".join(parts)
        except icu.ICUError as e:
            raise DurationError(f"Failed to format duration: {e}") from e

    def format_iso(self, iso_string: str) -> str:
        """Format an ISO 8601 duration string.

        Args:
            iso_string: ISO 8601 duration (e.g., "P2DT3H30M")

        Returns:
            Formatted duration string

        Example:
            >>> fmt.format_iso("P2DT3H30M")
            '2 days, 3 hours, 30 minutes'
        """
        components = parse_iso_duration(iso_string)
        return self.format(**components)

    def __repr__(self) -> str:
        return f"DurationFormatter(locale={self.locale!r}, width={self.width!r})"


def format_duration(
    seconds: float | None = None,
    locale: str = "en_US",
    width: str = WIDTH_WIDE,
    **kwargs,
) -> str:
    """Format a duration (convenience function).

    Args:
        seconds: Total seconds (or provide individual components via kwargs)
        locale: Locale code
        width: Width style (WIDE, SHORT, NARROW)
        **kwargs: Individual components (minutes, hours, days, weeks, months, years)

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(3661)
        '1 hour, 1 minute, 1 second'
        >>> format_duration(3661, locale="de_DE")
        '1 Stunde, 1 Minute und 1 Sekunde'
        >>> format_duration(hours=2, minutes=30)
        '2 hours, 30 minutes'
    """
    return DurationFormatter(locale, width).format(seconds=seconds, **kwargs)
