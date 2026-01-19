"""Tests for the parse module."""

import subprocess
import sys

from icukit import NumberParser, parse_currency, parse_number, parse_percent


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


class TestParseNumber:
    """Tests for parse_number function."""

    def test_basic_integer(self):
        """Test parsing basic integer."""
        assert parse_number("1234", "en_US") == 1234.0

    def test_with_grouping(self):
        """Test parsing with grouping separators."""
        assert parse_number("1,234", "en_US") == 1234.0
        assert parse_number("1,234,567", "en_US") == 1234567.0

    def test_with_decimal(self):
        """Test parsing with decimal."""
        assert parse_number("1,234.56", "en_US") == 1234.56

    def test_german_format(self):
        """Test German number format (. for grouping, , for decimal)."""
        assert parse_number("1.234,56", "de_DE") == 1234.56
        assert parse_number("1.234.567,89", "de_DE") == 1234567.89

    def test_french_format(self):
        """Test French number format (space for grouping)."""
        # French uses non-breaking space for grouping
        result = parse_number("1 234,56", "fr_FR")
        assert abs(result - 1234.56) < 0.01

    def test_negative(self):
        """Test negative number."""
        assert parse_number("-1,234", "en_US") == -1234.0

    def test_default_locale(self):
        """Test default locale."""
        assert parse_number("1,234.56") == 1234.56


class TestParseCurrency:
    """Tests for parse_currency function."""

    def test_usd(self):
        """Test parsing USD."""
        result = parse_currency("$1,234.56", "en_US")
        assert result["value"] == 1234.56
        # Currency code may or may not be available depending on ICU version
        assert "currency" in result

    def test_euro_german(self):
        """Test parsing Euro in German format."""
        result = parse_currency("1.234,56 €", "de_DE")
        assert abs(result["value"] - 1234.56) < 0.01

    def test_default_locale(self):
        """Test default locale."""
        result = parse_currency("$100.00")
        assert result["value"] == 100.0


class TestParsePercent:
    """Tests for parse_percent function."""

    def test_basic(self):
        """Test basic percentage."""
        assert parse_percent("50%", "en_US") == 0.5

    def test_over_100(self):
        """Test over 100%."""
        assert parse_percent("125%", "en_US") == 1.25

    def test_decimal_percent(self):
        """Test decimal percentage."""
        assert abs(parse_percent("12.5%", "en_US") - 0.125) < 0.001

    def test_default_locale(self):
        """Test default locale."""
        assert parse_percent("100%") == 1.0


class TestNumberParser:
    """Tests for NumberParser class."""

    def test_init(self):
        """Test initialization."""
        parser = NumberParser("en_US")
        assert parser.locale == "en_US"

    def test_parse_number(self):
        """Test parse_number method."""
        parser = NumberParser("en_US")
        assert parser.parse_number("1,234.56") == 1234.56

    def test_parse_currency(self):
        """Test parse_currency method."""
        parser = NumberParser("en_US")
        result = parser.parse_currency("$100.00")
        assert result["value"] == 100.0

    def test_parse_percent(self):
        """Test parse_percent method."""
        parser = NumberParser("en_US")
        assert parser.parse_percent("50%") == 0.5

    def test_repr(self):
        """Test string representation."""
        parser = NumberParser("de_DE")
        assert "de_DE" in repr(parser)

    def test_reuse(self):
        """Test reusing parser."""
        parser = NumberParser("en_US")
        assert parser.parse_number("100") == 100.0
        assert parser.parse_number("200") == 200.0


class TestParseCLI:
    """Tests for parse CLI command."""

    def test_number_basic(self):
        """Test number subcommand."""
        code, out, err = run_cli("parse", "number", "1234")
        assert code == 0
        assert "1234" in out

    def test_number_with_grouping(self):
        """Test number with grouping."""
        code, out, err = run_cli("parse", "number", "1,234.56")
        assert code == 0
        assert "1234.56" in out

    def test_number_german(self):
        """Test number with German locale."""
        code, out, err = run_cli("parse", "number", "1.234,56", "--locale", "de_DE")
        assert code == 0
        assert "1234.56" in out

    def test_currency_basic(self):
        """Test currency subcommand."""
        code, out, err = run_cli("parse", "currency", "$100.00")
        assert code == 0
        assert "100" in out

    def test_currency_json(self):
        """Test currency with JSON output."""
        code, out, err = run_cli("parse", "currency", "$100.00", "--json")
        assert code == 0
        assert "value" in out

    def test_percent_basic(self):
        """Test percent subcommand."""
        code, out, err = run_cli("parse", "percent", "50%")
        assert code == 0
        assert "0.5" in out

    def test_alias(self):
        """Test p alias."""
        code, out, err = run_cli("p", "number", "1234")
        assert code == 0
        assert "1234" in out

    def test_help(self):
        """Test help output."""
        code, out, err = run_cli("parse", "--help")
        assert code == 0
        assert "number" in out
        assert "currency" in out
        assert "percent" in out

    def test_whole_number_output(self):
        """Test that whole numbers display as integers."""
        code, out, err = run_cli("parse", "number", "1,234")
        assert code == 0
        # Should output 1234, not 1234.0
        assert out.strip() == "1234"
