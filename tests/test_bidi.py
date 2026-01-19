"""Tests for the bidi module."""

import subprocess
import sys

from icukit import (
    DIRECTION_LTR,
    DIRECTION_MIXED,
    DIRECTION_NEUTRAL,
    DIRECTION_RTL,
    get_base_direction,
    get_bidi_info,
    has_bidi_controls,
    list_bidi_controls,
    strip_bidi_controls,
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


class TestGetBaseDirection:
    """Tests for get_base_direction function."""

    def test_ltr_text(self):
        """Test LTR text detection."""
        assert get_base_direction("Hello World") == DIRECTION_LTR

    def test_rtl_text(self):
        """Test RTL text detection."""
        assert get_base_direction("שלום") == DIRECTION_RTL

    def test_arabic_text(self):
        """Test Arabic RTL text detection."""
        assert get_base_direction("مرحبا") == DIRECTION_RTL

    def test_neutral_text(self):
        """Test neutral text (numbers only)."""
        assert get_base_direction("12345") == DIRECTION_NEUTRAL

    def test_empty_text(self):
        """Test empty text."""
        assert get_base_direction("") == DIRECTION_NEUTRAL


class TestGetBidiInfo:
    """Tests for get_bidi_info function."""

    def test_ltr_only(self):
        """Test LTR-only text."""
        info = get_bidi_info("Hello")
        assert info["direction"] == DIRECTION_LTR
        assert info["has_ltr"] is True
        assert info["has_rtl"] is False

    def test_rtl_only(self):
        """Test RTL-only text."""
        info = get_bidi_info("שלום")
        assert info["direction"] == DIRECTION_RTL
        assert info["has_rtl"] is True
        assert info["has_ltr"] is False

    def test_mixed_text(self):
        """Test mixed LTR/RTL text."""
        info = get_bidi_info("Hello שלום World")
        assert info["direction"] == DIRECTION_MIXED
        assert info["has_ltr"] is True
        assert info["has_rtl"] is True

    def test_with_bidi_controls(self):
        """Test text with bidi control characters."""
        info = get_bidi_info("hello\u200fworld")
        assert info["bidi_control_count"] == 1

    def test_neutral(self):
        """Test neutral text."""
        info = get_bidi_info("123 !@#")
        assert info["direction"] == DIRECTION_NEUTRAL


class TestStripBidiControls:
    """Tests for strip_bidi_controls function."""

    def test_strip_rlm(self):
        """Test stripping Right-to-Left Mark."""
        assert strip_bidi_controls("hello\u200fworld") == "helloworld"

    def test_strip_lrm(self):
        """Test stripping Left-to-Right Mark."""
        assert strip_bidi_controls("hello\u200eworld") == "helloworld"

    def test_strip_multiple(self):
        """Test stripping multiple controls."""
        text = "a\u202eb\u202cc\u200fd"
        assert strip_bidi_controls(text) == "abcd"

    def test_no_controls(self):
        """Test text without controls."""
        assert strip_bidi_controls("hello world") == "hello world"

    def test_empty(self):
        """Test empty text."""
        assert strip_bidi_controls("") == ""


class TestHasBidiControls:
    """Tests for has_bidi_controls function."""

    def test_has_controls(self):
        """Test text with controls."""
        assert has_bidi_controls("hello\u200fworld") is True

    def test_no_controls(self):
        """Test text without controls."""
        assert has_bidi_controls("hello world") is False

    def test_empty(self):
        """Test empty text."""
        assert has_bidi_controls("") is False


class TestListBidiControls:
    """Tests for list_bidi_controls function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        controls = list_bidi_controls()
        assert isinstance(controls, list)
        assert len(controls) > 0

    def test_control_structure(self):
        """Test control dict structure."""
        controls = list_bidi_controls()
        for ctrl in controls:
            assert "char" in ctrl
            assert "codepoint" in ctrl
            assert "abbrev" in ctrl
            assert "name" in ctrl

    def test_common_controls_present(self):
        """Test that common controls are present."""
        controls = list_bidi_controls()
        abbrevs = [c["abbrev"] for c in controls]
        assert "LRM" in abbrevs
        assert "RLM" in abbrevs
        assert "LRO" in abbrevs
        assert "RLO" in abbrevs


class TestBidiCLI:
    """Tests for bidi CLI commands."""

    def test_detect_ltr(self):
        """Test detect command with LTR text."""
        code, out, err = run_cli("bidi", "detect", "-t", "Hello World")
        assert code == 0
        assert "ltr" in out

    def test_detect_mixed(self):
        """Test detect command with mixed text."""
        code, out, err = run_cli("bidi", "detect", "-t", "Hello שלום")
        assert code == 0
        assert "mixed" in out

    def test_strip(self):
        """Test strip command."""
        code, out, err = run_cli("bidi", "strip", "-t", "hello\u200fworld")
        assert code == 0
        assert out.strip() == "helloworld"

    def test_check_no_controls(self):
        """Test check command with no controls."""
        code, out, err = run_cli("bidi", "check", "-t", "hello world")
        assert code == 0
        assert "No bidi controls" in out

    def test_check_with_controls(self):
        """Test check command with controls."""
        code, out, err = run_cli("bidi", "check", "-t", "hello\u200fworld")
        assert code == 1  # Exit 1 when controls found
        assert "Found" in out

    def test_list(self):
        """Test list command."""
        code, out, err = run_cli("bidi", "list")
        assert code == 0
        assert "LRM" in out
        assert "RLM" in out

    def test_list_json(self):
        """Test list command with JSON output."""
        code, out, err = run_cli("bidi", "list", "--json")
        assert code == 0
        assert '"abbrev"' in out

    def test_prefix_matching(self):
        """Test prefix matching for subcommands."""
        code, out, err = run_cli("bidi", "det", "-t", "Hello")
        assert code == 0
        assert "ltr" in out
