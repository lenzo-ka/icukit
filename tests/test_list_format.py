"""Tests for the list_format module."""

import subprocess
import sys

from icukit import STYLE_AND, STYLE_OR, STYLE_UNIT, ListFormatter, format_list


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


class TestFormatList:
    """Tests for format_list function."""

    def test_basic_and(self):
        """Test basic 'and' list."""
        result = format_list(["apples", "oranges", "bananas"], "en_US")
        assert "apples" in result
        assert "oranges" in result
        assert "bananas" in result
        assert "and" in result

    def test_style_or(self):
        """Test 'or' style."""
        result = format_list(["red", "green", "blue"], "en_US", style=STYLE_OR)
        assert "or" in result

    def test_style_unit(self):
        """Test 'unit' style (no conjunction)."""
        result = format_list(["a", "b", "c"], "en_US", style=STYLE_UNIT)
        assert "and" not in result
        assert "or" not in result

    def test_two_items(self):
        """Test two-item list."""
        result = format_list(["yes", "no"], "en_US")
        assert "yes" in result
        assert "no" in result

    def test_single_item(self):
        """Test single item."""
        result = format_list(["only"], "en_US")
        assert result == "only"

    def test_empty_list(self):
        """Test empty list."""
        result = format_list([], "en_US")
        assert result == ""

    def test_german_locale(self):
        """Test German locale."""
        result = format_list(["Äpfel", "Orangen", "Bananen"], "de_DE")
        assert "und" in result
        # German doesn't use Oxford comma


class TestListFormatter:
    """Tests for ListFormatter class."""

    def test_init(self):
        """Test initialization."""
        lf = ListFormatter("en_US", STYLE_AND)
        assert lf.locale == "en_US"
        assert lf.style == STYLE_AND

    def test_format(self):
        """Test format method."""
        lf = ListFormatter("en_US")
        result = lf.format(["a", "b", "c"])
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_reuse(self):
        """Test reusing formatter."""
        lf = ListFormatter("en_US")
        result1 = lf.format(["a", "b"])
        result2 = lf.format(["x", "y", "z"])
        assert "a" in result1
        assert "x" in result2

    def test_repr(self):
        """Test string representation."""
        lf = ListFormatter("en_US", STYLE_OR)
        assert "en_US" in repr(lf)
        assert "or" in repr(lf)


class TestListFmtCLI:
    """Tests for listfmt CLI command."""

    def test_basic(self):
        """Test basic usage."""
        code, out, err = run_cli("listfmt", "apples,oranges,bananas")
        assert code == 0
        assert "apples" in out
        assert "and" in out

    def test_style_or(self):
        """Test --style or."""
        code, out, err = run_cli("listfmt", "red,green,blue", "--style", "or")
        assert code == 0
        assert "or" in out

    def test_style_unit(self):
        """Test --style unit."""
        code, out, err = run_cli("listfmt", "a,b,c", "--style", "unit")
        assert code == 0
        assert "and" not in out

    def test_locale(self):
        """Test --locale."""
        code, out, err = run_cli("listfmt", "Äpfel,Orangen,Bananen", "--locale", "de_DE")
        assert code == 0
        assert "und" in out

    def test_custom_delimiter(self):
        """Test --delimiter."""
        code, out, err = run_cli("listfmt", "a|b|c", "--delimiter", "|")
        assert code == 0
        assert "a" in out
        assert "b" in out
        assert "c" in out

    def test_two_items(self):
        """Test two items."""
        code, out, err = run_cli("listfmt", "yes,no", "--style", "or")
        assert code == 0
        assert "yes" in out
        assert "no" in out

    def test_alias(self):
        """Test alias."""
        code, out, err = run_cli("lf", "a,b,c")
        assert code == 0
        assert "a" in out
