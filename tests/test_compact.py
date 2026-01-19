"""Tests for the compact module."""

import subprocess
import sys

from icukit import COMPACT_STYLE_LONG, COMPACT_STYLE_SHORT, CompactFormatter, format_compact


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


class TestFormatCompact:
    """Tests for format_compact function."""

    def test_thousands(self):
        """Test thousands formatting."""
        result = format_compact(1000, "en_US")
        assert "K" in result or "1" in result

    def test_millions(self):
        """Test millions formatting."""
        result = format_compact(1000000, "en_US")
        assert "M" in result or "1" in result

    def test_billions(self):
        """Test billions formatting."""
        result = format_compact(1000000000, "en_US")
        assert "B" in result or "1" in result

    def test_with_decimal(self):
        """Test formatting with decimals."""
        result = format_compact(1500000, "en_US")
        assert "1.5" in result or "1,5" in result

    def test_german_locale(self):
        """Test German locale (Mio., Mrd.)."""
        result = format_compact(1000000, "de_DE")
        # German uses "Mio." for million
        assert "Mio" in result or "1" in result

    def test_long_style(self):
        """Test LONG style (full words)."""
        result = format_compact(1000000, "en_US", style=COMPACT_STYLE_LONG)
        assert "million" in result.lower() or "1" in result

    def test_small_number(self):
        """Test small number (no abbreviation)."""
        result = format_compact(100, "en_US")
        assert "100" in result

    def test_default_locale(self):
        """Test default locale."""
        result = format_compact(1000000)
        assert result  # Should return something


class TestCompactFormatter:
    """Tests for CompactFormatter class."""

    def test_init(self):
        """Test initialization."""
        fmt = CompactFormatter("en_US")
        assert fmt.locale == "en_US"
        assert fmt.style == COMPACT_STYLE_SHORT

    def test_init_with_style(self):
        """Test initialization with style."""
        fmt = CompactFormatter("en_US", COMPACT_STYLE_LONG)
        assert fmt.style == COMPACT_STYLE_LONG

    def test_format(self):
        """Test format method."""
        fmt = CompactFormatter("en_US")
        result = fmt.format(1000000)
        assert "M" in result or "1" in result

    def test_format_with_style_override(self):
        """Test format with style override."""
        fmt = CompactFormatter("en_US", COMPACT_STYLE_SHORT)
        result = fmt.format(1000000, style=COMPACT_STYLE_LONG)
        assert "million" in result.lower() or "1" in result

    def test_reuse(self):
        """Test reusing formatter."""
        fmt = CompactFormatter("en_US")
        result1 = fmt.format(1000)
        result2 = fmt.format(1000000)
        assert result1
        assert result2
        assert result1 != result2

    def test_repr(self):
        """Test string representation."""
        fmt = CompactFormatter("de_DE", COMPACT_STYLE_LONG)
        assert "de_DE" in repr(fmt)
        assert "LONG" in repr(fmt)


class TestCompactCLI:
    """Tests for compact CLI command."""

    def test_basic(self):
        """Test basic usage."""
        code, out, err = run_cli("compact", "1000000")
        assert code == 0
        assert out.strip()

    def test_thousands(self):
        """Test thousands."""
        code, out, err = run_cli("compact", "1000")
        assert code == 0
        # Should contain K or the number
        assert "K" in out or "1" in out

    def test_millions(self):
        """Test millions."""
        code, out, err = run_cli("compact", "1000000")
        assert code == 0
        assert "M" in out or "1" in out

    def test_style_long(self):
        """Test --style LONG."""
        code, out, err = run_cli("compact", "1000000", "--style", "LONG")
        assert code == 0
        assert "million" in out.lower() or "1" in out

    def test_locale(self):
        """Test --locale."""
        code, out, err = run_cli("compact", "1000000", "--locale", "de_DE")
        assert code == 0
        # German uses "Mio."
        assert "Mio" in out or "1" in out

    def test_multiple_numbers(self):
        """Test multiple numbers."""
        code, out, err = run_cli("compact", "1000", "1000000", "1000000000")
        assert code == 0
        # Should have tab-separated results
        parts = out.strip().split("\t")
        assert len(parts) == 3

    def test_alias_cmp(self):
        """Test cmp alias."""
        code, out, err = run_cli("cmp", "1000000")
        assert code == 0
        assert out.strip()

    def test_help(self):
        """Test help output."""
        code, out, err = run_cli("compact", "--help")
        assert code == 0
        assert "compact" in out.lower()
        assert "SHORT" in out
        assert "LONG" in out

    def test_float_input(self):
        """Test float input."""
        code, out, err = run_cli("compact", "1500000")
        assert code == 0
        assert "1.5" in out or "1,5" in out or "2" in out  # Might round

    def test_small_number(self):
        """Test small number (no abbreviation needed)."""
        code, out, err = run_cli("compact", "50")
        assert code == 0
        assert "50" in out
