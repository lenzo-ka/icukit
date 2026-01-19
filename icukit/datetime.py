"""
Locale-aware date and time formatting.

ICU's DateFormat provides sophisticated date/time formatting that adapts to
different locales and cultural conventions.

Styles:
    FULL   - Monday, January 15, 2024 at 3:45:30 PM Eastern Standard Time
    LONG   - January 15, 2024 at 3:45:30 PM EST
    MEDIUM - Jan 15, 2024, 3:45:30 PM
    SHORT  - 1/15/24, 3:45 PM

Pattern symbols:
    y - Year (yyyy=2024, yy=24)
    M - Month (M=1, MM=01, MMM=Jan, MMMM=January)
    d - Day of month (d=1, dd=01)
    E - Day of week (E=Mon, EEEE=Monday)
    h - Hour 1-12
    H - Hour 0-23
    m - Minute
    s - Second
    a - AM/PM
    z - Time zone (PST)
    Z - Time zone offset (-0800)

Example:
    >>> from icukit import DateTimeFormatter
    >>> from datetime import datetime
    >>>
    >>> fmt = DateTimeFormatter("en_US")
    >>> now = datetime.now()
    >>> print(fmt.format(now, style="SHORT"))
    1/15/24, 3:45 PM
    >>> print(fmt.format(now, pattern="EEEE, MMMM d, yyyy"))
    Monday, January 15, 2024
    >>>
    >>> fmt_de = DateTimeFormatter("de_DE")
    >>> print(fmt_de.format(now, style="LONG"))
    15. Januar 2024 um 15:45:30 MEZ
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import icu

from .errors import DateTimeError

__all__ = [
    "DateTimeFormatter",
    "format_datetime",
    "format_relative",
    "parse_datetime",
    "STYLE_FULL",
    "STYLE_LONG",
    "STYLE_MEDIUM",
    "STYLE_SHORT",
    "STYLE_NONE",
    # Symbol width constants
    "WIDTH_WIDE",
    "WIDTH_ABBREVIATED",
    # Symbol functions
    "get_month_names",
    "get_weekday_names",
    "get_era_names",
    "get_am_pm_strings",
    "get_date_symbols",
    # Duration constants
    "SECONDS_PER_MINUTE",
    "SECONDS_PER_HOUR",
    "SECONDS_PER_DAY",
    "SECONDS_PER_WEEK",
    "SECONDS_PER_MONTH",
    "SECONDS_PER_YEAR",
]

# Style constants
STYLE_FULL = "FULL"
STYLE_LONG = "LONG"
STYLE_MEDIUM = "MEDIUM"
STYLE_SHORT = "SHORT"
STYLE_NONE = "NONE"

# Time duration constants (seconds)
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800
SECONDS_PER_MONTH = 2592000  # 30 days
SECONDS_PER_YEAR = 31536000  # 365 days

_STYLE_MAP = {
    STYLE_FULL: icu.DateFormat.FULL,
    STYLE_LONG: icu.DateFormat.LONG,
    STYLE_MEDIUM: icu.DateFormat.MEDIUM,
    STYLE_SHORT: icu.DateFormat.SHORT,
    STYLE_NONE: icu.DateFormat.NONE,
}

# Common named patterns
PATTERNS = {
    "ISO_DATE": "yyyy-MM-dd",
    "ISO_TIME": "HH:mm:ss",
    "ISO_DATETIME": "yyyy-MM-dd'T'HH:mm:ss",
    "US_DATE": "MM/dd/yyyy",
    "EU_DATE": "dd/MM/yyyy",
    "LONG_DATE": "EEEE, MMMM d, yyyy",
    "TIME_12H": "h:mm a",
    "TIME_24H": "HH:mm",
}


class DateTimeFormatter:
    """Locale-aware date/time formatter.

    Provides formatting with predefined styles or custom patterns,
    relative time formatting, and date interval formatting.

    Example:
        >>> fmt = DateTimeFormatter("fr_FR")
        >>> fmt.format(datetime.now(), style="LONG")
        '15 janvier 2024 à 15:45:30 UTC−5'
        >>> fmt.format_relative(days=-1)
        'hier'
        >>>
        >>> # Different calendar systems
        >>> fmt = DateTimeFormatter("en_US", calendar="hebrew")
        >>> fmt.format(datetime(2024, 1, 15), pattern="yyyy-MM-dd")
        '5784-04-05'
    """

    def __init__(self, locale: str = "en_US", calendar: str | None = None):
        """Create a DateTimeFormatter for the given locale.

        Args:
            locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")
            calendar: Calendar system (e.g., "gregorian", "buddhist", "hebrew",
                     "islamic", "japanese", "chinese", "persian")
        """
        self.locale = locale
        self.calendar = calendar

        # Build locale with calendar keyword if specified
        if calendar:
            locale_with_cal = f"{locale}@calendar={calendar}"
        else:
            locale_with_cal = locale

        self._icu_locale = icu.Locale(locale_with_cal)
        self._formatters: dict = {}
        self._relative_formatter = None

    def format(
        self,
        dt: datetime | date | time,
        style: str | None = None,
        date_style: str | None = None,
        time_style: str | None = None,
        pattern: str | None = None,
    ) -> str:
        """Format a date/time value.

        Args:
            dt: Date/time to format
            style: Combined style (FULL, LONG, MEDIUM, SHORT) for both date and time
            date_style: Date style (overrides style for date part)
            time_style: Time style (overrides style for time part, NONE for date-only)
            pattern: Custom ICU pattern (overrides all styles)

        Returns:
            Formatted string

        Example:
            >>> fmt.format(now, style="SHORT")
            '1/15/24, 3:45 PM'
            >>> fmt.format(now, date_style="LONG", time_style="NONE")
            'January 15, 2024'
            >>> fmt.format(now, pattern="yyyy-MM-dd")
            '2024-01-15'
        """
        udate = self._to_udate(dt)

        if pattern:
            # Check for named pattern
            pattern = PATTERNS.get(pattern, pattern)
            formatter = self._get_pattern_formatter(pattern)
        else:
            if style:
                date_style = time_style = style
            date_style = date_style or STYLE_MEDIUM
            time_style = time_style or STYLE_MEDIUM
            formatter = self._get_style_formatter(date_style, time_style)

        try:
            return formatter.format(udate)
        except icu.ICUError as e:
            raise DateTimeError(f"Format failed: {e}") from e

    def format_relative(
        self,
        delta: int | timedelta | None = None,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> str:
        """Format relative time.

        Args:
            delta: Time delta (int for days, or timedelta object)
            days: Days offset (can combine with delta)
            hours: Hours offset
            minutes: Minutes offset
            seconds: Seconds offset

        Returns:
            Relative time string (e.g., "yesterday", "in 2 hours", "3 days ago")

        Example:
            >>> fmt.format_relative(days=-1)
            'yesterday'
            >>> fmt.format_relative(hours=2)
            'in 2 hours'
            >>> fmt.format_relative(timedelta(days=-7))
            '1 week ago'
        """
        # Calculate total seconds
        if isinstance(delta, int):
            total_seconds = delta * SECONDS_PER_DAY
        elif isinstance(delta, timedelta):
            total_seconds = delta.total_seconds()
        else:
            total_seconds = 0

        total_seconds += (
            days * SECONDS_PER_DAY
            + hours * SECONDS_PER_HOUR
            + minutes * SECONDS_PER_MINUTE
            + seconds
        )

        if self._relative_formatter is None:
            self._relative_formatter = icu.RelativeDateTimeFormatter(self._icu_locale)

        # Choose appropriate unit based on magnitude
        abs_seconds = abs(total_seconds)

        if abs_seconds < SECONDS_PER_MINUTE:
            value, unit = total_seconds, icu.URelativeDateTimeUnit.SECOND
        elif abs_seconds < SECONDS_PER_HOUR:
            value, unit = total_seconds / SECONDS_PER_MINUTE, icu.URelativeDateTimeUnit.MINUTE
        elif abs_seconds < SECONDS_PER_DAY:
            value, unit = total_seconds / SECONDS_PER_HOUR, icu.URelativeDateTimeUnit.HOUR
        elif abs_seconds < SECONDS_PER_WEEK:
            value, unit = total_seconds / SECONDS_PER_DAY, icu.URelativeDateTimeUnit.DAY
        elif abs_seconds < SECONDS_PER_MONTH:
            value, unit = total_seconds / SECONDS_PER_WEEK, icu.URelativeDateTimeUnit.WEEK
        elif abs_seconds < SECONDS_PER_YEAR:
            value, unit = total_seconds / SECONDS_PER_MONTH, icu.URelativeDateTimeUnit.MONTH
        else:
            value, unit = total_seconds / SECONDS_PER_YEAR, icu.URelativeDateTimeUnit.YEAR

        try:
            return self._relative_formatter.formatNumeric(value, unit)
        except icu.ICUError as e:
            raise DateTimeError(f"Relative format failed: {e}") from e

    def format_interval(
        self,
        start: datetime | date,
        end: datetime | date,
        skeleton: str = "yMMMd",
    ) -> str:
        """Format a date/time interval.

        Args:
            start: Start date/time
            end: End date/time
            skeleton: Format skeleton (e.g., "yMMMd", "MMMd", "Hm")

        Returns:
            Formatted interval (e.g., "Jan 15 – 20, 2024")

        Example:
            >>> start = date(2024, 1, 15)
            >>> end = date(2024, 1, 20)
            >>> fmt.format_interval(start, end)
            'Jan 15 – 20, 2024'
        """
        start_udate = self._to_udate(start)
        end_udate = self._to_udate(end)

        try:
            dtpg = icu.DateTimePatternGenerator.createInstance(self._icu_locale)
            pattern = dtpg.getBestPattern(skeleton)
            formatter = icu.DateIntervalFormat.createInstance(pattern, self._icu_locale)
            interval = icu.DateInterval(start_udate, end_udate)
            return formatter.format(interval)
        except icu.ICUError as e:
            raise DateTimeError(f"Interval format failed: {e}") from e

    def parse(self, text: str, pattern: str | None = None) -> datetime:
        """Parse a date/time string.

        Args:
            text: String to parse
            pattern: Expected format pattern (optional, tries common formats if not given)

        Returns:
            Parsed datetime

        Raises:
            DateTimeError: If parsing fails
        """
        if pattern:
            pattern = PATTERNS.get(pattern, pattern)
            formatter = self._get_pattern_formatter(pattern)
            try:
                udate = formatter.parse(text)
                return datetime.fromtimestamp(udate)
            except icu.ICUError as e:
                raise DateTimeError(f"Parse failed with pattern '{pattern}': {e}") from e

        # Try various styles
        for style in [STYLE_SHORT, STYLE_MEDIUM, STYLE_LONG, STYLE_FULL]:
            for time_style in [style, STYLE_NONE]:
                try:
                    formatter = self._get_style_formatter(style, time_style)
                    udate = formatter.parse(text)
                    return datetime.fromtimestamp(udate)
                except icu.ICUError:
                    continue

        raise DateTimeError(f"Could not parse '{text}' with any known format")

    def _to_udate(self, dt: datetime | date | time) -> float:
        """Convert Python datetime to ICU UDate (seconds since epoch for PyICU)."""
        if isinstance(dt, datetime):
            return dt.timestamp()
        elif isinstance(dt, date):
            return datetime.combine(dt, time()).timestamp()
        elif isinstance(dt, time):
            return datetime.combine(date.today(), dt).timestamp()
        raise TypeError(f"Expected datetime, date, or time, got {type(dt)}")

    def _get_style_formatter(self, date_style: str, time_style: str):
        """Get or create a style-based formatter."""
        key = f"style:{date_style}:{time_style}"
        if key not in self._formatters:
            ds = _STYLE_MAP.get(date_style)
            ts = _STYLE_MAP.get(time_style)
            if ds is None:
                raise DateTimeError(f"Invalid date style: {date_style}")
            if ts is None:
                raise DateTimeError(f"Invalid time style: {time_style}")
            self._formatters[key] = icu.DateFormat.createDateTimeInstance(ds, ts, self._icu_locale)
        return self._formatters[key]

    def _get_pattern_formatter(self, pattern: str):
        """Get or create a pattern-based formatter."""
        key = f"pattern:{pattern}"
        if key not in self._formatters:
            try:
                self._formatters[key] = icu.SimpleDateFormat(pattern, self._icu_locale)
            except icu.ICUError as e:
                raise DateTimeError(f"Invalid pattern '{pattern}': {e}") from e
        return self._formatters[key]

    def __repr__(self) -> str:
        if self.calendar:
            return f"DateTimeFormatter(locale={self.locale!r}, calendar={self.calendar!r})"
        return f"DateTimeFormatter(locale={self.locale!r})"


def format_datetime(
    dt: datetime | date | time,
    locale: str = "en_US",
    calendar: str | None = None,
    **kwargs,
) -> str:
    """Format a date/time value (convenience function).

    Args:
        dt: Date/time to format
        locale: Locale code
        calendar: Calendar system (e.g., "hebrew", "islamic", "buddhist")
        **kwargs: Passed to DateTimeFormatter.format()

    Returns:
        Formatted string
    """
    return DateTimeFormatter(locale, calendar=calendar).format(dt, **kwargs)


def format_relative(
    delta: int | timedelta | None = None,
    locale: str = "en_US",
    calendar: str | None = None,
    **kwargs,
) -> str:
    """Format relative time (convenience function).

    Args:
        delta: Time delta
        locale: Locale code
        calendar: Calendar system
        **kwargs: Passed to DateTimeFormatter.format_relative()

    Returns:
        Relative time string
    """
    return DateTimeFormatter(locale, calendar=calendar).format_relative(delta, **kwargs)


def parse_datetime(
    text: str,
    locale: str = "en_US",
    calendar: str | None = None,
    pattern: str | None = None,
) -> datetime:
    """Parse a date/time string (convenience function).

    Args:
        text: String to parse
        locale: Locale code
        calendar: Calendar system
        pattern: Expected format pattern

    Returns:
        Parsed datetime
    """
    return DateTimeFormatter(locale, calendar=calendar).parse(text, pattern)


# =============================================================================
# Date/Time Symbol Functions
# =============================================================================

# Width constants for symbol names (matching measure.py convention)
WIDTH_WIDE = "WIDE"
WIDTH_ABBREVIATED = "ABBREVIATED"

_WIDTH_METHODS = {
    "months": {
        WIDTH_WIDE: "getMonths",
        WIDTH_ABBREVIATED: "getShortMonths",
    },
    "weekdays": {
        WIDTH_WIDE: "getWeekdays",
        WIDTH_ABBREVIATED: "getShortWeekdays",
    },
    "eras": {
        WIDTH_WIDE: "getEraNames",
        WIDTH_ABBREVIATED: "getEras",
    },
}


def get_month_names(
    locale: str = "en_US",
    width: str = WIDTH_WIDE,
    calendar: str | None = None,
) -> list[str]:
    """Get localized month names.

    Args:
        locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
        width: Name width - WIDTH_WIDE ("January") or WIDTH_ABBREVIATED ("Jan").
        calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

    Returns:
        List of 12 month names (January-December or equivalent).

    Example:
        >>> get_month_names("en_US")
        ['January', 'February', 'March', ..., 'December']
        >>> get_month_names("de_DE", WIDTH_ABBREVIATED)
        ['Jan.', 'Feb.', 'März', ..., 'Dez.']
        >>> get_month_names("ja_JP")
        ['1月', '2月', '3月', ..., '12月']
    """
    if width not in _WIDTH_METHODS["months"]:
        raise DateTimeError(f"Invalid width: {width}. Use WIDTH_WIDE or WIDTH_ABBREVIATED.")

    locale_str = f"{locale}@calendar={calendar}" if calendar else locale
    dfs = icu.DateFormatSymbols(icu.Locale(locale_str))
    method = getattr(dfs, _WIDTH_METHODS["months"][width])
    # Filter out empty strings (ICU may return 13 elements with empty last)
    return [m for m in method() if m]


def get_weekday_names(
    locale: str = "en_US",
    width: str = WIDTH_WIDE,
    calendar: str | None = None,
) -> dict:
    """Get localized weekday names.

    Returns weekday names in standard Sunday-Saturday order, along with
    metadata about which day is the first day of the week for this locale.

    Args:
        locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
        width: Name width - WIDTH_WIDE ("Sunday") or WIDTH_ABBREVIATED ("Sun").
        calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

    Returns:
        Dict with:
            - names: List of 7 weekday names (Sunday-Saturday order)
            - first_day_index: Index of locale's first day (0=Sunday, 1=Monday, etc.)
            - first_day: Name of locale's first day of week

    Example:
        >>> get_weekday_names("en_US")
        {'names': ['Sunday', 'Monday', ...], 'first_day_index': 0, 'first_day': 'Sunday'}
        >>> get_weekday_names("de_DE")
        {'names': ['Sonntag', 'Montag', ...], 'first_day_index': 1, 'first_day': 'Montag'}
        >>> get_weekday_names("ja_JP", WIDTH_ABBREVIATED)
        {'names': ['日', '月', '火', ...], 'first_day_index': 0, 'first_day': '日'}
    """
    if width not in _WIDTH_METHODS["weekdays"]:
        raise DateTimeError(f"Invalid width: {width}. Use WIDTH_WIDE or WIDTH_ABBREVIATED.")

    locale_str = f"{locale}@calendar={calendar}" if calendar else locale
    icu_locale = icu.Locale(locale_str)
    dfs = icu.DateFormatSymbols(icu_locale)
    method = getattr(dfs, _WIDTH_METHODS["weekdays"][width])

    # ICU returns [empty, Sunday, Monday, ..., Saturday] (1-indexed)
    raw_names = list(method())
    names = raw_names[1:8] if len(raw_names) > 7 else raw_names

    # Get first day of week from calendar
    cal = icu.Calendar.createInstance(icu_locale)
    first_dow = cal.getFirstDayOfWeek()  # 1=Sunday, 2=Monday, etc.
    first_day_index = first_dow - 1  # Convert to 0-indexed

    return {
        "names": names,
        "first_day_index": first_day_index,
        "first_day": names[first_day_index] if first_day_index < len(names) else None,
    }


def get_era_names(
    locale: str = "en_US",
    width: str = WIDTH_WIDE,
    calendar: str | None = None,
) -> list[str]:
    """Get localized era names.

    Args:
        locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
        width: Name width - WIDTH_WIDE ("Before Christ") or WIDTH_ABBREVIATED ("BC").
        calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

    Returns:
        List of era names (typically 2 for Gregorian: BC/AD or equivalent).

    Example:
        >>> get_era_names("en_US")
        ['Before Christ', 'Anno Domini']
        >>> get_era_names("en_US", WIDTH_ABBREVIATED)
        ['BC', 'AD']
        >>> get_era_names("ja_JP")
        ['紀元前', '西暦']
    """
    if width not in _WIDTH_METHODS["eras"]:
        raise DateTimeError(f"Invalid width: {width}. Use WIDTH_WIDE or WIDTH_ABBREVIATED.")

    locale_str = f"{locale}@calendar={calendar}" if calendar else locale
    dfs = icu.DateFormatSymbols(icu.Locale(locale_str))
    method = getattr(dfs, _WIDTH_METHODS["eras"][width])
    return list(method())


def get_am_pm_strings(
    locale: str = "en_US",
    calendar: str | None = None,
) -> list[str]:
    """Get localized AM/PM strings.

    Args:
        locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
        calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

    Returns:
        List of 2 strings: [AM, PM] or locale equivalent.

    Example:
        >>> get_am_pm_strings("en_US")
        ['AM', 'PM']
        >>> get_am_pm_strings("ja_JP")
        ['午前', '午後']
        >>> get_am_pm_strings("zh_CN")
        ['上午', '下午']
    """
    locale_str = f"{locale}@calendar={calendar}" if calendar else locale
    dfs = icu.DateFormatSymbols(icu.Locale(locale_str))
    return list(dfs.getAmPmStrings())


def get_date_symbols(
    locale: str = "en_US",
    calendar: str | None = None,
) -> dict:
    """Get all date/time symbols for a locale.

    Returns a comprehensive dict of all localized date/time symbols including
    month names, weekday names, era names, and AM/PM strings.

    Args:
        locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
        calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

    Returns:
        Dict with all date symbols organized by category.

    Example:
        >>> symbols = get_date_symbols("fr_FR")
        >>> symbols["months"]["wide"]
        ['janvier', 'février', ..., 'décembre']
        >>> symbols["weekdays"]["abbreviated"]
        ['dim.', 'lun.', 'mar.', ...]
        >>> symbols["am_pm"]
        ['AM', 'PM']
    """
    locale_str = f"{locale}@calendar={calendar}" if calendar else locale
    icu_locale = icu.Locale(locale_str)
    dfs = icu.DateFormatSymbols(icu_locale)
    cal = icu.Calendar.createInstance(icu_locale)

    # Get weekday data
    weekdays_wide = list(dfs.getWeekdays())[1:8]
    weekdays_abbrev = list(dfs.getShortWeekdays())[1:8]
    first_dow = cal.getFirstDayOfWeek() - 1  # Convert to 0-indexed

    return {
        "locale": locale,
        "calendar": calendar or cal.getType(),
        "months": {
            "wide": [m for m in dfs.getMonths() if m],
            "abbreviated": [m for m in dfs.getShortMonths() if m],
        },
        "weekdays": {
            "wide": weekdays_wide,
            "abbreviated": weekdays_abbrev,
            "first_day_index": first_dow,
            "first_day": weekdays_wide[first_dow] if first_dow < len(weekdays_wide) else None,
        },
        "eras": {
            "wide": list(dfs.getEraNames()),
            "abbreviated": list(dfs.getEras()),
        },
        "am_pm": list(dfs.getAmPmStrings()),
    }
