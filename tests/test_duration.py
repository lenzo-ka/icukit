"""Tests for the duration module."""

import subprocess
import sys

import pytest

from icukit import (
    DURATION_WIDTH_NARROW,
    DURATION_WIDTH_SHORT,
    DURATION_WIDTH_WIDE,
    DurationError,
    DurationFormatter,
    format_duration,
    parse_iso_duration,
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


class TestParseIsoDuration:
    """Tests for parse_iso_duration function."""

    def test_days_and_time(self):
        """Test parsing days and time."""
        result = parse_iso_duration("P2DT3H30M")
        assert result["days"] == 2
        assert result["hours"] == 3
        assert result["minutes"] == 30
        assert result["seconds"] == 0

    def test_time_only(self):
        """Test parsing time only."""
        result = parse_iso_duration("PT1H30M15S")
        assert result["hours"] == 1
        assert result["minutes"] == 30
        assert result["seconds"] == 15

    def test_years_months(self):
        """Test parsing years and months."""
        result = parse_iso_duration("P1Y2M")
        assert result["years"] == 1
        assert result["months"] == 2

    def test_weeks(self):
        """Test parsing weeks."""
        result = parse_iso_duration("P2W")
        assert result["weeks"] == 2

    def test_fractional(self):
        """Test parsing fractional values."""
        result = parse_iso_duration("PT1.5H")
        assert result["hours"] == 1.5

    def test_full_duration(self):
        """Test parsing full duration."""
        result = parse_iso_duration("P1Y2M3W4DT5H6M7S")
        assert result["years"] == 1
        assert result["months"] == 2
        assert result["weeks"] == 3
        assert result["days"] == 4
        assert result["hours"] == 5
        assert result["minutes"] == 6
        assert result["seconds"] == 7

    def test_invalid_no_p(self):
        """Test error for missing P prefix."""
        with pytest.raises(DurationError):
            parse_iso_duration("2DT3H")


class TestDurationFormatter:
    """Tests for DurationFormatter class."""

    def test_init(self):
        """Test initialization."""
        fmt = DurationFormatter("en_US")
        assert fmt.locale == "en_US"
        assert fmt.width == DURATION_WIDTH_WIDE

    def test_init_with_width(self):
        """Test initialization with width."""
        fmt = DurationFormatter("en_US", DURATION_WIDTH_SHORT)
        assert fmt.width == DURATION_WIDTH_SHORT

    def test_format_total_seconds(self):
        """Test formatting from total seconds."""
        fmt = DurationFormatter("en_US")
        result = fmt.format(seconds=3661)
        assert "hour" in result.lower()
        assert "minute" in result.lower()
        assert "second" in result.lower()

    def test_format_components(self):
        """Test formatting from components."""
        fmt = DurationFormatter("en_US")
        result = fmt.format(hours=2, minutes=30)
        assert "2" in result
        assert "hour" in result.lower()
        assert "30" in result
        assert "minute" in result.lower()

    def test_format_short(self):
        """Test short width."""
        fmt = DurationFormatter("en_US", DURATION_WIDTH_SHORT)
        result = fmt.format(hours=2, minutes=30)
        # Short format uses abbreviations
        assert "hr" in result.lower() or "h" in result.lower()

    def test_format_narrow(self):
        """Test narrow width."""
        fmt = DurationFormatter("en_US", DURATION_WIDTH_NARROW)
        result = fmt.format(hours=2, minutes=30)
        # Narrow format is minimal
        assert "2" in result
        assert "30" in result

    def test_format_german(self):
        """Test German locale."""
        fmt = DurationFormatter("de_DE")
        result = fmt.format(hours=1, minutes=1)
        assert "Stunde" in result or "Std" in result

    def test_format_iso(self):
        """Test format_iso method."""
        fmt = DurationFormatter("en_US")
        result = fmt.format_iso("P2DT3H30M")
        assert "day" in result.lower()
        assert "hour" in result.lower()
        assert "minute" in result.lower()

    def test_format_zero(self):
        """Test formatting zero duration."""
        fmt = DurationFormatter("en_US")
        result = fmt.format(seconds=0)
        assert "0" in result
        assert "second" in result.lower()

    def test_repr(self):
        """Test string representation."""
        fmt = DurationFormatter("en_US", DURATION_WIDTH_SHORT)
        assert "en_US" in repr(fmt)
        assert "SHORT" in repr(fmt)

    def test_invalid_width(self):
        """Test error for invalid width."""
        with pytest.raises(DurationError):
            DurationFormatter("en_US", "INVALID")


class TestFormatDuration:
    """Tests for format_duration convenience function."""

    def test_basic(self):
        """Test basic usage."""
        result = format_duration(3661)
        assert "hour" in result.lower()
        assert "minute" in result.lower()
        assert "second" in result.lower()

    def test_with_locale(self):
        """Test with locale."""
        result = format_duration(3600, locale="de_DE")
        assert "Stunde" in result or "Std" in result

    def test_with_width(self):
        """Test with width."""
        result = format_duration(3600, width=DURATION_WIDTH_SHORT)
        assert "hr" in result.lower() or "h" in result.lower()

    def test_with_components(self):
        """Test with components."""
        result = format_duration(hours=2, minutes=30)
        assert "2" in result
        assert "30" in result


class TestDurationCLI:
    """Tests for duration CLI command."""

    def test_format_seconds(self):
        """Test format with total seconds."""
        code, out, err = run_cli("duration", "format", "3661")
        assert code == 0
        assert "hour" in out.lower()
        assert "minute" in out.lower()
        assert "second" in out.lower()

    def test_format_with_locale(self):
        """Test format with locale."""
        code, out, err = run_cli("duration", "format", "3600", "--locale", "de_DE")
        assert code == 0
        assert "Stunde" in out or "Std" in out

    def test_format_with_width(self):
        """Test format with width."""
        code, out, err = run_cli("duration", "format", "3600", "--width", "SHORT")
        assert code == 0
        assert "hr" in out.lower() or "h" in out.lower()

    def test_format_with_components(self):
        """Test format with component flags."""
        code, out, err = run_cli("duration", "format", "--hours", "2", "--minutes", "30")
        assert code == 0
        assert "2" in out
        assert "hour" in out.lower()
        assert "30" in out
        assert "minute" in out.lower()

    def test_iso(self):
        """Test iso subcommand."""
        code, out, err = run_cli("duration", "iso", "P2DT3H30M")
        assert code == 0
        assert "day" in out.lower()
        assert "hour" in out.lower()
        assert "minute" in out.lower()

    def test_iso_with_locale(self):
        """Test iso with locale."""
        code, out, err = run_cli("duration", "iso", "PT1H", "--locale", "de_DE")
        assert code == 0
        assert "Stunde" in out or "Std" in out

    def test_parse(self):
        """Test parse subcommand."""
        code, out, err = run_cli("duration", "parse", "P2DT3H30M")
        assert code == 0
        assert "days=2" in out
        assert "hours=3" in out
        assert "minutes=30" in out

    def test_parse_json(self):
        """Test parse with JSON output."""
        code, out, err = run_cli("duration", "parse", "PT1H30M", "--json")
        assert code == 0
        assert "hours" in out
        assert "minutes" in out

    def test_alias(self):
        """Test dur alias."""
        code, out, err = run_cli("dur", "format", "3600")
        assert code == 0
        assert "hour" in out.lower()

    def test_help(self):
        """Test help output."""
        code, out, err = run_cli("duration", "--help")
        assert code == 0
        assert "format" in out
        assert "iso" in out
        assert "parse" in out

    def test_no_args_error(self):
        """Test error when no args provided."""
        code, out, err = run_cli("duration", "format")
        assert code == 1
        assert "error" in err.lower() or "Error" in err
