"""Tests for the measure module."""

import subprocess
import sys

from icukit import (
    WIDTH_NARROW,
    WIDTH_SHORT,
    WIDTH_WIDE,
    MeasureFormatter,
    can_convert,
    convert_units,
    format_measure,
    get_unit_abbreviation,
    get_unit_info,
    get_units_by_type,
    list_unit_types,
    list_units,
    resolve_unit,
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


class TestMeasureFormatter:
    """Tests for MeasureFormatter class."""

    def test_init(self):
        """Test initialization."""
        fmt = MeasureFormatter("en_US")
        assert fmt.locale == "en_US"
        assert fmt.width == WIDTH_WIDE

    def test_format_kilometers(self):
        """Test formatting kilometers."""
        fmt = MeasureFormatter("en_US")
        result = fmt.format(5.5, "kilometer")
        assert "5.5" in result or "5,5" in result
        assert "kilometer" in result.lower()

    def test_format_fahrenheit(self):
        """Test formatting temperature."""
        fmt = MeasureFormatter("en_US")
        result = fmt.format(100, "fahrenheit")
        assert "100" in result

    def test_format_short_width(self):
        """Test SHORT width."""
        fmt = MeasureFormatter("en_US", WIDTH_SHORT)
        result = fmt.format(5, "kilometer")
        assert "km" in result

    def test_format_narrow_width(self):
        """Test NARROW width."""
        fmt = MeasureFormatter("en_US", WIDTH_NARROW)
        result = fmt.format(5, "kilometer")
        # Narrow usually has no space
        assert "5" in result

    def test_format_german_locale(self):
        """Test German locale."""
        fmt = MeasureFormatter("de_DE")
        result = fmt.format(5.5, "kilometer")
        # German uses comma for decimal
        assert "5,5" in result or "5.5" in result

    def test_format_range(self):
        """Test formatting a range."""
        fmt = MeasureFormatter("en_US")
        result = fmt.format_range(5, 10, "kilometer")
        assert "5" in result
        assert "10" in result

    def test_repr(self):
        """Test string representation."""
        fmt = MeasureFormatter("en_US", WIDTH_SHORT)
        assert "en_US" in repr(fmt)
        assert "SHORT" in repr(fmt)

    def test_convert_km_to_miles(self):
        """Test converting kilometers to miles."""
        fmt = MeasureFormatter("en_US")
        result = fmt.convert(10, "kilometer", "mile")
        assert 6.2 < result < 6.3  # ~6.21371

    def test_convert_celsius_to_fahrenheit(self):
        """Test converting celsius to fahrenheit."""
        fmt = MeasureFormatter("en_US")
        result = fmt.convert(100, "celsius", "fahrenheit")
        assert result == 212.0

    def test_convert_and_format(self):
        """Test convert_and_format."""
        fmt = MeasureFormatter("en_US")
        result = fmt.convert_and_format(10, "kilometer", "mile")
        assert "mile" in result.lower()

    def test_format_with_abbreviation(self):
        """Test formatting with abbreviation."""
        fmt = MeasureFormatter("en_US")
        result = fmt.format(5, "km")
        assert "kilometer" in result.lower()

    def test_convert_with_abbreviations(self):
        """Test converting with abbreviations."""
        fmt = MeasureFormatter("en_US")
        result = fmt.convert(10, "km", "mi")
        assert 6.2 < result < 6.3


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_format_measure(self):
        """Test format_measure function."""
        result = format_measure(5.5, "kilometer")
        assert "5.5" in result or "5,5" in result

    def test_list_unit_types(self):
        """Test list_unit_types function."""
        types = list_unit_types()
        assert "length" in types
        assert "mass" in types
        assert "temperature" in types

    def test_list_units_all(self):
        """Test list_units without type filter."""
        units = list_units()
        assert "meter" in units
        assert "kilogram" in units
        assert "celsius" in units

    def test_list_units_by_type(self):
        """Test list_units with type filter."""
        units = list_units("length")
        assert "meter" in units
        assert "kilometer" in units
        assert "kilogram" not in units

    def test_convert_units(self):
        """Test convert_units function."""
        result = convert_units(10, "kilometer", "mile")
        assert 6.2 < result < 6.3

    def test_resolve_unit_canonical(self):
        """Test resolve_unit with canonical name."""
        assert resolve_unit("kilometer") == "kilometer"

    def test_resolve_unit_abbreviation(self):
        """Test resolve_unit with abbreviation."""
        result = resolve_unit("km")
        assert result == "kilometer"

    def test_get_unit_abbreviation(self):
        """Test get_unit_abbreviation."""
        abbrev = get_unit_abbreviation("kilometer")
        assert abbrev == "km"

    def test_get_unit_info(self):
        """Test get_unit_info."""
        info = get_unit_info("kilometer")
        assert info["identifier"] == "kilometer"
        assert info["type"] == "length"

    def test_can_convert_true(self):
        """Test can_convert returns True for compatible units."""
        assert can_convert("kilometer", "mile") is True

    def test_can_convert_false(self):
        """Test can_convert returns False for incompatible units."""
        assert can_convert("kilometer", "celsius") is False

    def test_get_units_by_type(self):
        """Test get_units_by_type."""
        units_by_type = get_units_by_type()
        assert "length" in units_by_type
        assert "meter" in units_by_type["length"]


class TestMeasureFormatterAdvanced:
    """Tests for advanced MeasureFormatter features."""

    def test_format_sequence(self):
        """Test format_sequence for compound units."""
        fmt = MeasureFormatter("en_US")
        result = fmt.format_sequence([(5, "foot"), (10, "inch")])
        assert "5" in result
        assert "10" in result

    def test_format_for_usage(self):
        """Test format_for_usage."""
        fmt = MeasureFormatter("en_US")
        # This may or may not convert depending on ICU version
        result = fmt.format_for_usage(100, "kilometer", usage="road")
        assert result  # Just verify we get output


class TestMeasureCLI:
    """Tests for measure CLI command."""

    def test_format(self):
        """Test format subcommand."""
        code, out, err = run_cli("measure", "format", "5.5", "kilometer")
        assert code == 0
        assert "5.5" in out or "5,5" in out

    def test_format_with_width(self):
        """Test format with width option."""
        code, out, err = run_cli("measure", "format", "5", "kilometer", "--width", "SHORT")
        assert code == 0
        assert "km" in out

    def test_format_with_locale(self):
        """Test format with locale option."""
        code, out, err = run_cli("measure", "format", "5.5", "kilometer", "--locale", "de_DE")
        assert code == 0

    def test_range(self):
        """Test range subcommand."""
        code, out, err = run_cli("measure", "range", "5", "10", "kilometer")
        assert code == 0
        assert "5" in out
        assert "10" in out

    def test_types(self):
        """Test types subcommand."""
        code, out, err = run_cli("measure", "types")
        assert code == 0
        assert "length" in out
        assert "mass" in out

    def test_units(self):
        """Test units subcommand."""
        code, out, err = run_cli("measure", "units")
        assert code == 0
        assert "meter" in out

    def test_units_by_type(self):
        """Test units with type filter."""
        code, out, err = run_cli("measure", "units", "--type", "temperature")
        assert code == 0
        assert "celsius" in out
        assert "fahrenheit" in out

    def test_convert(self):
        """Test convert subcommand."""
        code, out, err = run_cli("measure", "convert", "10", "kilometer", "mile")
        assert code == 0
        assert "mi" in out.lower()  # Short form by default

    def test_convert_raw(self):
        """Test convert with --raw."""
        code, out, err = run_cli("measure", "convert", "100", "celsius", "fahrenheit", "--raw")
        assert code == 0
        assert "212" in out

    def test_convert_with_abbreviations(self):
        """Test convert with abbreviations."""
        code, out, err = run_cli("measure", "convert", "10", "km", "mi")
        assert code == 0
        assert "mi" in out.lower()  # Short form by default

    def test_sequence(self):
        """Test sequence subcommand."""
        code, out, err = run_cli("measure", "sequence", "5 foot, 10 inch")
        assert code == 0
        assert "5" in out

    def test_info(self):
        """Test info subcommand."""
        code, out, err = run_cli("measure", "info", "kilometer")
        assert code == 0
        assert "length" in out

    def test_check_compatible(self):
        """Test check subcommand for compatible units."""
        code, out, err = run_cli("measure", "check", "km", "mi")
        assert code == 0
        assert "Yes" in out

    def test_check_incompatible(self):
        """Test check subcommand for incompatible units."""
        code, out, err = run_cli("measure", "check", "km", "celsius")
        assert code == 1
        assert "No" in out

    def test_alias(self):
        """Test meas alias."""
        code, out, err = run_cli("meas", "format", "5", "meter")
        assert code == 0
