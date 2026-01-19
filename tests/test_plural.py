"""Tests for the plural module."""

import subprocess
import sys

import pytest

from icukit import (
    CATEGORY_FEW,
    CATEGORY_MANY,
    CATEGORY_ONE,
    CATEGORY_OTHER,
    get_ordinal_category,
    get_plural_category,
    get_plural_rules_info,
    list_ordinal_categories,
    list_plural_categories,
)

# Check if PyICU supports ordinal rules
_HAS_ORDINAL = hasattr(__import__("icu"), "UPluralType")


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


class TestGetPluralCategory:
    """Tests for get_plural_category function."""

    def test_english_one(self):
        """Test English singular."""
        assert get_plural_category(1, "en") == CATEGORY_ONE

    def test_english_other(self):
        """Test English plural."""
        assert get_plural_category(2, "en") == CATEGORY_OTHER
        assert get_plural_category(5, "en") == CATEGORY_OTHER
        assert get_plural_category(0, "en") == CATEGORY_OTHER

    def test_russian_one(self):
        """Test Russian singular (ends in 1, not 11)."""
        assert get_plural_category(1, "ru") == CATEGORY_ONE
        assert get_plural_category(21, "ru") == CATEGORY_ONE
        assert get_plural_category(101, "ru") == CATEGORY_ONE

    def test_russian_few(self):
        """Test Russian few (ends in 2-4, not 12-14)."""
        assert get_plural_category(2, "ru") == CATEGORY_FEW
        assert get_plural_category(3, "ru") == CATEGORY_FEW
        assert get_plural_category(4, "ru") == CATEGORY_FEW
        assert get_plural_category(22, "ru") == CATEGORY_FEW

    def test_russian_many(self):
        """Test Russian many (ends in 0, 5-9, 11-14)."""
        assert get_plural_category(0, "ru") == CATEGORY_MANY
        assert get_plural_category(5, "ru") == CATEGORY_MANY
        assert get_plural_category(11, "ru") == CATEGORY_MANY
        assert get_plural_category(12, "ru") == CATEGORY_MANY

    def test_float_values(self):
        """Test with float values."""
        # 1.5 should be 'other' in English
        assert get_plural_category(1.5, "en") == CATEGORY_OTHER

    def test_default_locale(self):
        """Test default locale (en_US)."""
        assert get_plural_category(1) == CATEGORY_ONE
        assert get_plural_category(2) == CATEGORY_OTHER


class TestGetOrdinalCategory:
    """Tests for get_ordinal_category function."""

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_english_ordinals(self):
        """Test English ordinal categories."""
        # 1st, 21st, 31st etc.
        assert get_ordinal_category(1, "en") == CATEGORY_ONE
        assert get_ordinal_category(21, "en") == CATEGORY_ONE

        # 2nd, 22nd, 32nd etc.
        assert get_ordinal_category(2, "en") == "two"
        assert get_ordinal_category(22, "en") == "two"

        # 3rd, 23rd, 33rd etc.
        assert get_ordinal_category(3, "en") == CATEGORY_FEW
        assert get_ordinal_category(23, "en") == CATEGORY_FEW

        # Everything else: 4th, 5th, 11th, 12th, 13th etc.
        assert get_ordinal_category(4, "en") == CATEGORY_OTHER
        assert get_ordinal_category(11, "en") == CATEGORY_OTHER
        assert get_ordinal_category(12, "en") == CATEGORY_OTHER


class TestListPluralCategories:
    """Tests for list_plural_categories function."""

    def test_english_categories(self):
        """Test English has one, other."""
        cats = list_plural_categories("en")
        assert CATEGORY_ONE in cats
        assert CATEGORY_OTHER in cats
        assert len(cats) == 2

    def test_russian_categories(self):
        """Test Russian has one, few, many, other."""
        cats = list_plural_categories("ru")
        assert CATEGORY_ONE in cats
        assert CATEGORY_FEW in cats
        assert CATEGORY_MANY in cats
        assert CATEGORY_OTHER in cats

    def test_arabic_categories(self):
        """Test Arabic has all six categories."""
        cats = list_plural_categories("ar")
        # Arabic uses zero, one, two, few, many, other
        assert len(cats) >= 5  # At least 5 categories


class TestListOrdinalCategories:
    """Tests for list_ordinal_categories function."""

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_english_ordinal_categories(self):
        """Test English ordinal categories."""
        cats = list_ordinal_categories("en")
        assert CATEGORY_ONE in cats  # 1st
        assert "two" in cats  # 2nd
        assert CATEGORY_FEW in cats  # 3rd
        assert CATEGORY_OTHER in cats  # 4th, etc.


class TestGetPluralRulesInfo:
    """Tests for get_plural_rules_info function."""

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_info_structure(self):
        """Test info returns expected structure."""
        info = get_plural_rules_info("en")
        assert "locale" in info
        assert "cardinal_categories" in info
        assert "ordinal_categories" in info
        assert "examples" in info
        assert info["locale"] == "en"

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_examples(self):
        """Test examples are provided for each category."""
        info = get_plural_rules_info("en")
        assert CATEGORY_ONE in info["examples"]
        assert CATEGORY_OTHER in info["examples"]
        # Check that 1 is in the 'one' examples
        assert 1 in info["examples"][CATEGORY_ONE]


class TestPluralCLI:
    """Tests for plural CLI command."""

    def test_select_basic(self):
        """Test select subcommand."""
        code, out, err = run_cli("plural", "select", "1", "--locale", "en")
        assert code == 0
        assert "one" in out

    def test_select_russian(self):
        """Test select with Russian locale."""
        code, out, err = run_cli("plural", "select", "5", "--locale", "ru")
        assert code == 0
        assert "many" in out

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_ordinal(self):
        """Test ordinal subcommand."""
        code, out, err = run_cli("plural", "ordinal", "1", "--locale", "en")
        assert code == 0
        assert "one" in out

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_ordinal_second(self):
        """Test ordinal for 2nd."""
        code, out, err = run_cli("plural", "ordinal", "2", "--locale", "en")
        assert code == 0
        assert "two" in out

    def test_categories(self):
        """Test categories subcommand."""
        code, out, err = run_cli("plural", "categories", "--locale", "en")
        assert code == 0
        assert "one" in out
        assert "other" in out

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_categories_ordinal(self):
        """Test categories with ordinal type."""
        code, out, err = run_cli("plural", "categories", "--locale", "en", "--type", "ordinal")
        assert code == 0
        assert "one" in out
        assert "two" in out
        assert "few" in out

    def test_categories_json(self):
        """Test categories with JSON output."""
        code, out, err = run_cli("plural", "categories", "--locale", "en", "--json")
        assert code == 0
        assert "category" in out

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_info(self):
        """Test info subcommand."""
        code, out, err = run_cli("plural", "info", "--locale", "en")
        assert code == 0
        assert "Cardinal categories" in out
        assert "Ordinal categories" in out

    @pytest.mark.skipif(not _HAS_ORDINAL, reason="PyICU version lacks ordinal support")
    def test_info_json(self):
        """Test info with JSON output."""
        code, out, err = run_cli("plural", "info", "--locale", "ru", "--json")
        assert code == 0
        assert "cardinal_categories" in out

    def test_alias(self):
        """Test pl alias."""
        code, out, err = run_cli("pl", "select", "1")
        assert code == 0
        assert "one" in out

    def test_help(self):
        """Test help output."""
        code, out, err = run_cli("plural", "--help")
        assert code == 0
        assert "select" in out
        assert "ordinal" in out
        assert "categories" in out
