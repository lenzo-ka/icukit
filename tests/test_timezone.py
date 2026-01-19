"""Tests for timezone module and CLI."""

import subprocess
import sys

import pytest

from icukit import (
    TimezoneError,
    get_equivalent_timezones,
    get_timezone_info,
    get_timezone_offset,
    list_timezones,
    list_timezones_info,
)


class TestTimezoneLibrary:
    """Tests for timezone library functions."""

    def test_list_timezones(self):
        """Test listing all timezones."""
        tzs = list_timezones()
        assert len(tzs) > 600  # Should have 600+ timezones
        assert "America/New_York" in tzs
        assert "Europe/London" in tzs
        assert "Asia/Tokyo" in tzs

    def test_list_timezones_by_country(self):
        """Test listing timezones by country."""
        us_tzs = list_timezones("US")
        assert "America/New_York" in us_tzs
        assert "America/Los_Angeles" in us_tzs
        # Non-US timezone should not be in list
        assert "Europe/London" not in us_tzs

    def test_list_timezones_info(self):
        """Test listing timezones with info."""
        tzs = list_timezones_info("US")
        nyc = next(t for t in tzs if t["id"] == "America/New_York")
        assert nyc["uses_dst"] is True
        assert nyc["offset_hours"] == -5.0

    def test_get_timezone_info_nyc(self):
        """Test getting NYC timezone info."""
        info = get_timezone_info("America/New_York")
        assert info is not None
        assert info["id"] == "America/New_York"
        assert info["offset_hours"] == -5.0
        assert info["offset_formatted"] == "UTC-5"
        assert info["uses_dst"] is True
        assert info["dst_savings_hours"] == 1.0

    def test_get_timezone_info_utc(self):
        """Test getting UTC timezone info."""
        info = get_timezone_info("UTC")
        assert info is not None
        assert info["offset_hours"] == 0.0
        assert info["uses_dst"] is False

    def test_get_timezone_info_tokyo(self):
        """Test getting Tokyo timezone info."""
        info = get_timezone_info("Asia/Tokyo")
        assert info is not None
        assert info["offset_hours"] == 9.0
        assert info["uses_dst"] is False

    def test_get_timezone_info_invalid(self):
        """Test invalid timezone returns None."""
        info = get_timezone_info("Invalid/Timezone")
        assert info is None

    def test_get_timezone_offset(self):
        """Test getting timezone offset."""
        offset = get_timezone_offset("America/New_York")
        assert offset == -5.0

    def test_get_timezone_offset_invalid(self):
        """Test invalid timezone raises error."""
        with pytest.raises(TimezoneError):
            get_timezone_offset("Invalid/Timezone")

    def test_get_equivalent_timezones(self):
        """Test getting equivalent timezones."""
        equivs = get_equivalent_timezones("America/New_York")
        assert "US/Eastern" in equivs

    def test_get_equivalent_timezones_empty(self):
        """Test timezone with no equivalents."""
        equivs = get_equivalent_timezones("UTC")
        # UTC may or may not have equivalents depending on ICU version
        assert isinstance(equivs, list)

    def test_offset_formatting_positive(self):
        """Test positive offset formatting."""
        info = get_timezone_info("Asia/Tokyo")
        assert info["offset_formatted"] == "UTC+9"

    def test_offset_formatting_negative(self):
        """Test negative offset formatting."""
        info = get_timezone_info("America/New_York")
        assert info["offset_formatted"] == "UTC-5"

    def test_offset_formatting_half_hour(self):
        """Test half-hour offset formatting."""
        info = get_timezone_info("Asia/Kolkata")
        assert info["offset_formatted"] == "UTC+05:30"


class TestTimezoneCLI:
    """Tests for timezone CLI command."""

    def test_timezone_list(self):
        """Test icukit timezone list."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", "list"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "America/New_York" in result.stdout

    def test_timezone_list_short(self):
        """Test icukit timezone list --short."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", "list", "--short"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "America/New_York" in result.stdout
        # Short mode should not have headers
        assert "id\t" not in result.stdout

    def test_timezone_list_country(self):
        """Test icukit timezone list --country US."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", "list", "--country", "US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "America/New_York" in result.stdout
        assert "America/Los_Angeles" in result.stdout

    def test_timezone_info(self):
        """Test icukit timezone info."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", "info", "America/New_York"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "America/New_York" in result.stdout
        assert "UTC-5" in result.stdout

    def test_timezone_info_json(self):
        """Test icukit timezone info --json."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", "info", "America/New_York", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"id": "America/New_York"' in result.stdout
        assert '"offset_hours": -5.0' in result.stdout

    def test_timezone_info_invalid(self):
        """Test icukit timezone info with invalid timezone."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", "info", "Invalid/Timezone"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Unknown timezone" in result.stderr

    def test_timezone_equiv(self):
        """Test icukit timezone equiv."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", "equiv", "America/New_York"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "US/Eastern" in result.stdout

    def test_timezone_prefix_matching(self):
        """Test prefix matching works."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "tz", "info", "UTC"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "UTC" in result.stdout
