"""Tests for spoof/confusable detection module and CLI."""

import subprocess
import sys

from icukit import (
    CONFUSABLE_MIXED_SCRIPT,
    CONFUSABLE_NONE,
    SpoofChecker,
    are_confusable,
    check_string,
    get_confusable_info,
    get_confusable_type,
    get_skeleton,
)


class TestSpoofLibrary:
    """Tests for spoof library functions."""

    def test_are_confusable_true(self):
        """Test confusable strings."""
        # Cyrillic 'а' vs Latin 'a'
        assert are_confusable("paypal", "pаypal") is True

    def test_are_confusable_false(self):
        """Test non-confusable strings."""
        assert are_confusable("hello", "world") is False

    def test_are_confusable_identical(self):
        """Test identical strings."""
        assert are_confusable("hello", "hello") is True

    def test_get_confusable_type_none(self):
        """Test confusable type for non-confusable."""
        result = get_confusable_type("hello", "world")
        assert result == CONFUSABLE_NONE

    def test_get_confusable_type_mixed(self):
        """Test confusable type for mixed script."""
        result = get_confusable_type("paypal", "pаypal")
        assert result & CONFUSABLE_MIXED_SCRIPT

    def test_get_skeleton(self):
        """Test skeleton generation."""
        skel1 = get_skeleton("paypal")
        skel2 = get_skeleton("pаypal")  # Cyrillic а
        assert skel1 == skel2

    def test_check_string_clean(self):
        """Test check on clean string."""
        result = check_string("hello")
        assert result["is_suspicious"] is False

    def test_check_string_suspicious(self):
        """Test check on suspicious string."""
        result = check_string("pаypal")  # Cyrillic а
        assert result["is_suspicious"] is True

    def test_get_confusable_info(self):
        """Test detailed confusable info."""
        info = get_confusable_info("paypal", "pаypal")
        assert info["confusable"] is True
        assert info["same_skeleton"] is True
        assert "mixed_script" in info["type_names"]


class TestSpoofChecker:
    """Tests for SpoofChecker class."""

    def test_init(self):
        """Test checker initialization."""
        checker = SpoofChecker()
        assert checker is not None

    def test_are_confusable(self):
        """Test are_confusable method."""
        checker = SpoofChecker()
        assert checker.are_confusable("paypal", "pаypal") is True
        assert checker.are_confusable("hello", "world") is False

    def test_get_skeleton(self):
        """Test get_skeleton method."""
        checker = SpoofChecker()
        assert checker.get_skeleton("pаypal") == "paypal"

    def test_check(self):
        """Test check method."""
        checker = SpoofChecker()
        result = checker.check("pаypal")
        assert result["is_suspicious"] is True

    def test_repr(self):
        """Test string representation."""
        checker = SpoofChecker()
        assert "SpoofChecker" in repr(checker)


class TestSpoofCLI:
    """Tests for spoof CLI command."""

    def test_compare_confusable(self):
        """Test compare with confusable strings."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "compare", "paypal", "pаypal"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "confusable" in result.stdout

    def test_compare_not_confusable(self):
        """Test compare with non-confusable strings."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "compare", "hello", "world"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "not confusable" in result.stdout

    def test_skeleton(self):
        """Test skeleton command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "skeleton", "pаypal"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "paypal" in result.stdout

    def test_check_suspicious(self):
        """Test check command with suspicious string."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "check", "pаypal"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "suspicious" in result.stdout

    def test_check_clean(self):
        """Test check command with clean string."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "check", "hello"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "clean" in result.stdout

    def test_info_json(self):
        """Test info command with JSON output."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "spoof",
                "info",
                "paypal",
                "pаypal",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"confusable"' in result.stdout

    def test_alias_confusable(self):
        """Test 'confusable' alias."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "confusable", "compare", "a", "а"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_help(self):
        """Test help output."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
