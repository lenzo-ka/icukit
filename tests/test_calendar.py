"""Tests for calendar module and CLI."""

import subprocess
import sys

from icukit import get_calendar_info, is_valid_calendar, list_calendars, list_calendars_info


class TestCalendarLibrary:
    """Tests for calendar library functions."""

    def test_list_calendars(self):
        """Test listing all calendar types."""
        cals = list_calendars()
        assert len(cals) >= 17
        assert "gregorian" in cals
        assert "hebrew" in cals
        assert "islamic" in cals
        assert "buddhist" in cals
        assert "chinese" in cals

    def test_list_calendars_sorted(self):
        """Test calendar list is sorted."""
        cals = list_calendars()
        assert cals == sorted(cals)

    def test_list_calendars_info(self):
        """Test listing calendars with info."""
        cals = list_calendars_info()
        assert len(cals) >= 17
        greg = next(c for c in cals if c["type"] == "gregorian")
        assert "Western" in greg["description"]

    def test_get_calendar_info_gregorian(self):
        """Test getting Gregorian calendar info."""
        info = get_calendar_info("gregorian")
        assert info is not None
        assert info["type"] == "gregorian"
        assert info["icu_type"] == "gregorian"
        assert "Western" in info["description"]

    def test_get_calendar_info_hebrew(self):
        """Test getting Hebrew calendar info."""
        info = get_calendar_info("hebrew")
        assert info is not None
        assert info["type"] == "hebrew"
        assert "Hebrew" in info["description"] or "Jewish" in info["description"]

    def test_get_calendar_info_islamic(self):
        """Test getting Islamic calendar info."""
        info = get_calendar_info("islamic")
        assert info is not None
        assert info["type"] == "islamic"
        assert "Islamic" in info["description"] or "Hijri" in info["description"]

    def test_get_calendar_info_islamic_variants(self):
        """Test Islamic calendar variants."""
        variants = ["islamic-civil", "islamic-umalqura", "islamic-tbla"]
        for variant in variants:
            info = get_calendar_info(variant)
            assert info is not None
            assert info["type"] == variant

    def test_get_calendar_info_case_insensitive(self):
        """Test calendar type lookup is case insensitive."""
        info1 = get_calendar_info("GREGORIAN")
        info2 = get_calendar_info("Gregorian")
        info3 = get_calendar_info("gregorian")
        assert info1 is not None
        assert info2 is not None
        assert info3 is not None
        assert info1["type"] == info2["type"] == info3["type"]

    def test_get_calendar_info_invalid(self):
        """Test invalid calendar returns None."""
        info = get_calendar_info("invalid")
        assert info is None

    def test_is_valid_calendar_true(self):
        """Test valid calendar types."""
        assert is_valid_calendar("gregorian") is True
        assert is_valid_calendar("hebrew") is True
        assert is_valid_calendar("islamic") is True

    def test_is_valid_calendar_false(self):
        """Test invalid calendar types."""
        assert is_valid_calendar("invalid") is False
        assert is_valid_calendar("foo") is False

    def test_is_valid_calendar_case_insensitive(self):
        """Test is_valid_calendar is case insensitive."""
        assert is_valid_calendar("GREGORIAN") is True
        assert is_valid_calendar("Hebrew") is True


class TestCalendarCLI:
    """Tests for calendar CLI command."""

    def test_calendar_list(self):
        """Test icukit calendar list."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "calendar", "list"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "gregorian" in result.stdout
        assert "hebrew" in result.stdout
        assert "islamic" in result.stdout

    def test_calendar_list_short(self):
        """Test icukit calendar list --short."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "calendar", "list", "--short"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "gregorian" in result.stdout
        # Short mode should not have headers or descriptions
        assert "type\t" not in result.stdout
        assert "Western" not in result.stdout

    def test_calendar_list_json(self):
        """Test icukit calendar list --json."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "calendar", "list", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"type": "gregorian"' in result.stdout

    def test_calendar_info(self):
        """Test icukit calendar info."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "calendar", "info", "hebrew"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "hebrew" in result.stdout

    def test_calendar_info_json(self):
        """Test icukit calendar info --json."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "calendar", "info", "hebrew", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"type": "hebrew"' in result.stdout

    def test_calendar_info_invalid(self):
        """Test icukit calendar info with invalid type."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "calendar", "info", "invalid"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Unknown calendar type" in result.stderr

    def test_calendar_prefix_matching(self):
        """Test prefix matching works."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "cal", "list", "--short"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "gregorian" in result.stdout

    def test_calendar_help(self):
        """Test icukit calendar --help."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "calendar", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "list" in result.stdout
        assert "info" in result.stdout
