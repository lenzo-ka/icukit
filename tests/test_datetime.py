"""Tests for the datetime module."""

import subprocess
import sys
from datetime import date, datetime, timedelta

from icukit import (
    STYLE_LONG,
    STYLE_MEDIUM,
    STYLE_NONE,
    STYLE_SHORT,
    WIDTH_ABBREVIATED,
    WIDTH_WIDE,
    DateTimeFormatter,
    format_datetime,
    format_relative,
    get_am_pm_strings,
    get_date_symbols,
    get_era_names,
    get_month_names,
    get_weekday_names,
    parse_datetime,
)


def run_cli(*args, input_text=None):
    """Run icukit CLI and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "icukit.cli"] + list(args)
    result = subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


class TestDateTimeFormatter:
    """Tests for DateTimeFormatter class."""

    def test_init(self):
        """Test initialization."""
        fmt = DateTimeFormatter("en_US")
        assert fmt.locale == "en_US"

    def test_format_with_style(self):
        """Test formatting with predefined styles."""
        fmt = DateTimeFormatter("en_US")
        dt = datetime(2024, 1, 15, 14, 30, 0)

        # Just verify we get non-empty strings
        result = fmt.format(dt, style=STYLE_SHORT)
        assert result
        assert "2024" in result or "24" in result

        result = fmt.format(dt, style=STYLE_MEDIUM)
        assert result

    def test_format_with_pattern(self):
        """Test formatting with custom pattern."""
        fmt = DateTimeFormatter("en_US")
        dt = datetime(2024, 1, 15, 14, 30, 0)

        result = fmt.format(dt, pattern="yyyy-MM-dd")
        assert result == "2024-01-15"

        result = fmt.format(dt, pattern="HH:mm")
        assert result == "14:30"

    def test_format_date_only(self):
        """Test formatting date only."""
        fmt = DateTimeFormatter("en_US")
        dt = datetime(2024, 1, 15, 14, 30, 0)

        result = fmt.format(dt, date_style=STYLE_LONG, time_style=STYLE_NONE)
        assert "January" in result
        assert "15" in result
        assert "2024" in result

    def test_format_date_object(self):
        """Test formatting a date object."""
        fmt = DateTimeFormatter("en_US")
        d = date(2024, 1, 15)

        result = fmt.format(d, pattern="yyyy-MM-dd")
        assert result == "2024-01-15"

    def test_format_german_locale(self):
        """Test German locale formatting."""
        fmt = DateTimeFormatter("de_DE")
        dt = datetime(2024, 1, 15, 14, 30, 0)

        result = fmt.format(dt, style=STYLE_LONG)
        assert "Januar" in result or "15" in result

    def test_format_relative_yesterday(self):
        """Test relative time formatting for yesterday."""
        fmt = DateTimeFormatter("en_US")
        result = fmt.format_relative(days=-1)
        assert result  # Just verify non-empty

    def test_format_relative_tomorrow(self):
        """Test relative time formatting for tomorrow."""
        fmt = DateTimeFormatter("en_US")
        result = fmt.format_relative(days=1)
        assert result

    def test_format_relative_hours(self):
        """Test relative time formatting for hours."""
        fmt = DateTimeFormatter("en_US")
        result = fmt.format_relative(hours=-3)
        assert result
        assert "hour" in result.lower() or "3" in result

    def test_format_relative_timedelta(self):
        """Test relative time with timedelta."""
        fmt = DateTimeFormatter("en_US")
        result = fmt.format_relative(timedelta(days=-7))
        assert result

    def test_format_interval(self):
        """Test interval formatting."""
        fmt = DateTimeFormatter("en_US")
        start = date(2024, 1, 15)
        end = date(2024, 1, 20)

        result = fmt.format_interval(start, end)
        assert "15" in result
        assert "20" in result

    def test_parse(self):
        """Test parsing a date string."""
        fmt = DateTimeFormatter("en_US")
        result = fmt.parse("2024-01-15", pattern="yyyy-MM-dd")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_repr(self):
        """Test string representation."""
        fmt = DateTimeFormatter("en_US")
        assert "en_US" in repr(fmt)

    def test_calendar_buddhist(self):
        """Test Buddhist calendar."""
        fmt = DateTimeFormatter("en_US", calendar="buddhist")
        dt = datetime(2024, 1, 15)
        result = fmt.format(dt, pattern="yyyy-MM-dd")
        # Buddhist year = Gregorian + 543
        assert "2567" in result

    def test_calendar_hebrew(self):
        """Test Hebrew calendar."""
        fmt = DateTimeFormatter("en_US", calendar="hebrew")
        dt = datetime(2024, 1, 15)
        result = fmt.format(dt, pattern="yyyy")
        # Hebrew year around 5784
        assert "5784" in result

    def test_calendar_repr(self):
        """Test repr with calendar."""
        fmt = DateTimeFormatter("en_US", calendar="hebrew")
        assert "hebrew" in repr(fmt)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_format_datetime_basic(self):
        """Test format_datetime function."""
        dt = datetime(2024, 1, 15, 14, 30, 0)
        result = format_datetime(dt, pattern="yyyy-MM-dd")
        assert result == "2024-01-15"

    def test_format_relative(self):
        """Test format_relative function."""
        result = format_relative(days=-1, locale="en_US")
        assert result

    def test_parse_datetime(self):
        """Test parse_datetime function."""
        result = parse_datetime("2024-01-15", pattern="yyyy-MM-dd")
        assert result.year == 2024


class TestDateTimeCLI:
    """Tests for datetime CLI command."""

    def test_format_now(self):
        """Test formatting current time."""
        code, out, err = run_cli("datetime", "format")
        assert code == 0
        assert out.strip()

    def test_format_specific_date(self):
        """Test formatting specific date."""
        code, out, err = run_cli("datetime", "format", "2024-01-15T14:30:00")
        assert code == 0
        assert out.strip()

    def test_format_with_style(self):
        """Test format with style."""
        code, out, err = run_cli("datetime", "format", "--style", "SHORT")
        assert code == 0

    def test_format_with_pattern(self):
        """Test format with pattern."""
        code, out, err = run_cli(
            "datetime", "format", "2024-01-15T14:30:00", "--pattern", "yyyy-MM-dd"
        )
        assert code == 0
        assert "2024-01-15" in out

    def test_format_with_locale(self):
        """Test format with locale."""
        code, out, err = run_cli("datetime", "format", "2024-01-15T14:30:00", "--locale", "de_DE")
        assert code == 0

    def test_relative(self):
        """Test relative subcommand."""
        code, out, err = run_cli("datetime", "relative", "-1")
        assert code == 0
        assert out.strip()

    def test_relative_hours(self):
        """Test relative with hours."""
        code, out, err = run_cli("datetime", "relative", "0", "--hours", "2")
        assert code == 0
        assert out.strip()

    def test_interval(self):
        """Test interval subcommand."""
        code, out, err = run_cli("datetime", "interval", "2024-01-15", "2024-01-20")
        assert code == 0
        assert "15" in out
        assert "20" in out

    def test_parse(self):
        """Test parse subcommand."""
        code, out, err = run_cli("datetime", "parse", "2024-01-15", "--pattern", "yyyy-MM-dd")
        assert code == 0
        assert "2024-01-15" in out

    def test_patterns(self):
        """Test patterns subcommand."""
        code, out, err = run_cli("datetime", "patterns")
        assert code == 0
        assert "Year" in out
        assert "Month" in out

    def test_alias(self):
        """Test dt alias."""
        code, out, err = run_cli("dt", "format")
        assert code == 0

    def test_format_with_calendar(self):
        """Test format with calendar."""
        code, out, err = run_cli(
            "datetime", "format", "2024-01-15", "--calendar", "buddhist", "--pattern", "yyyy"
        )
        assert code == 0
        assert "2567" in out

    def test_calendars_list(self):
        """Test calendars subcommand."""
        code, out, err = run_cli("datetime", "calendars")
        assert code == 0
        assert "gregorian" in out
        assert "hebrew" in out
        assert "islamic" in out


class TestDateSymbols:
    """Tests for date/time symbol functions."""

    def test_get_month_names_en_wide(self):
        """Test getting wide month names in English."""
        months = get_month_names("en_US")
        assert len(months) == 12
        assert months[0] == "January"
        assert months[11] == "December"

    def test_get_month_names_en_abbreviated(self):
        """Test getting abbreviated month names in English."""
        months = get_month_names("en_US", WIDTH_ABBREVIATED)
        assert len(months) == 12
        assert months[0] == "Jan"
        assert months[11] == "Dec"

    def test_get_month_names_german(self):
        """Test getting month names in German."""
        months = get_month_names("de_DE")
        assert "Januar" in months
        assert "Dezember" in months

    def test_get_month_names_japanese(self):
        """Test getting month names in Japanese."""
        months = get_month_names("ja_JP")
        assert len(months) == 12
        assert "1月" in months
        assert "12月" in months

    def test_get_weekday_names_en(self):
        """Test getting weekday names in English."""
        result = get_weekday_names("en_US")
        assert "names" in result
        assert "first_day_index" in result
        assert "first_day" in result
        assert len(result["names"]) == 7
        assert result["names"][0] == "Sunday"
        assert result["names"][6] == "Saturday"
        assert result["first_day_index"] == 0  # Sunday in US

    def test_get_weekday_names_german(self):
        """Test getting weekday names in German."""
        result = get_weekday_names("de_DE")
        assert result["names"][0] == "Sonntag"
        assert result["first_day_index"] == 1  # Monday in Germany
        assert result["first_day"] == "Montag"

    def test_get_weekday_names_abbreviated(self):
        """Test getting abbreviated weekday names."""
        result = get_weekday_names("en_US", WIDTH_ABBREVIATED)
        assert result["names"][0] == "Sun"
        assert result["names"][1] == "Mon"

    def test_get_era_names_wide(self):
        """Test getting wide era names."""
        eras = get_era_names("en_US", WIDTH_WIDE)
        assert "Before Christ" in eras
        assert "Anno Domini" in eras

    def test_get_era_names_abbreviated(self):
        """Test getting abbreviated era names."""
        eras = get_era_names("en_US", WIDTH_ABBREVIATED)
        assert "BC" in eras
        assert "AD" in eras

    def test_get_am_pm_strings_en(self):
        """Test getting AM/PM strings in English."""
        strings = get_am_pm_strings("en_US")
        assert len(strings) == 2
        assert "AM" in strings
        assert "PM" in strings

    def test_get_am_pm_strings_japanese(self):
        """Test getting AM/PM strings in Japanese."""
        strings = get_am_pm_strings("ja_JP")
        assert len(strings) == 2
        assert "午前" in strings
        assert "午後" in strings

    def test_get_date_symbols_structure(self):
        """Test get_date_symbols returns correct structure."""
        symbols = get_date_symbols("en_US")
        assert "locale" in symbols
        assert "calendar" in symbols
        assert "months" in symbols
        assert "weekdays" in symbols
        assert "eras" in symbols
        assert "am_pm" in symbols

        assert "wide" in symbols["months"]
        assert "abbreviated" in symbols["months"]
        assert len(symbols["months"]["wide"]) == 12

        assert "wide" in symbols["weekdays"]
        assert "first_day_index" in symbols["weekdays"]
        assert len(symbols["weekdays"]["wide"]) == 7

    def test_get_date_symbols_french(self):
        """Test get_date_symbols for French."""
        symbols = get_date_symbols("fr_FR")
        assert symbols["locale"] == "fr_FR"
        assert "janvier" in symbols["months"]["wide"]
        assert "dimanche" in symbols["weekdays"]["wide"]
        assert symbols["weekdays"]["first_day_index"] == 1  # Monday in France


class TestDateSymbolsCLI:
    """Tests for date symbol CLI commands."""

    def test_months_default(self):
        """Test months subcommand."""
        code, out, err = run_cli("datetime", "months")
        assert code == 0
        assert "January" in out
        assert "December" in out

    def test_months_locale(self):
        """Test months with locale."""
        code, out, err = run_cli("datetime", "months", "--locale", "de_DE")
        assert code == 0
        assert "Januar" in out

    def test_months_abbreviated(self):
        """Test months with abbreviated width."""
        code, out, err = run_cli("datetime", "months", "--width", "ABBREVIATED")
        assert code == 0
        assert "Jan" in out

    def test_weekdays_default(self):
        """Test weekdays subcommand."""
        code, out, err = run_cli("datetime", "weekdays")
        assert code == 0
        assert "Sunday" in out
        assert "Saturday" in out
        assert "first" in out  # header column

    def test_weekdays_german(self):
        """Test weekdays for German locale."""
        code, out, err = run_cli("datetime", "weekdays", "--locale", "de_DE")
        assert code == 0
        assert "Sonntag" in out
        assert "Montag" in out

    def test_eras_default(self):
        """Test eras subcommand."""
        code, out, err = run_cli("datetime", "eras")
        assert code == 0
        assert "Before Christ" in out or "Anno Domini" in out

    def test_eras_abbreviated(self):
        """Test eras with abbreviated width."""
        code, out, err = run_cli("datetime", "eras", "--width", "ABBREVIATED")
        assert code == 0
        assert "BC" in out or "AD" in out

    def test_ampm_default(self):
        """Test ampm subcommand."""
        code, out, err = run_cli("datetime", "ampm")
        assert code == 0
        assert "AM" in out
        assert "PM" in out

    def test_ampm_japanese(self):
        """Test ampm for Japanese locale."""
        code, out, err = run_cli("datetime", "ampm", "--locale", "ja_JP")
        assert code == 0
        assert "午前" in out
        assert "午後" in out

    def test_symbols_default(self):
        """Test symbols subcommand."""
        code, out, err = run_cli("datetime", "symbols")
        assert code == 0
        assert "month" in out
        assert "weekday" in out
        assert "era" in out

    def test_symbols_json(self):
        """Test symbols with JSON output."""
        code, out, err = run_cli("datetime", "symbols", "--json")
        assert code == 0
        assert '"months"' in out
        assert '"weekdays"' in out

    def test_months_alias(self):
        """Test months alias."""
        code, out, err = run_cli("datetime", "mon")
        assert code == 0
        assert "January" in out
