"""Tests for the collator module."""

import subprocess
import sys

from icukit import (
    STRENGTH_PRIMARY,
    STRENGTH_SECONDARY,
    compare_strings,
    get_collator_info,
    get_sort_key,
    list_collation_types,
    sort_strings,
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


class TestSortStrings:
    """Tests for sort_strings function."""

    def test_basic_sort_english(self):
        """Test basic English sorting."""
        words = ["café", "cafe", "Cafe", "CAFÉ"]
        result = sort_strings(words, "en_US")
        # Base letters first, then accents, then case
        assert result[0] == "cafe"
        assert "café" in result

    def test_german_sorting(self):
        """Test German sorting (ö sorts with o)."""
        words = ["Öl", "Ol", "öl", "ol", "p"]
        result = sort_strings(words, "de_DE")
        # In German, ö sorts with o, before p
        assert result[-1] == "p"

    def test_swedish_sorting(self):
        """Test Swedish sorting (ö sorts after z)."""
        words = ["ö", "o", "z"]
        result = sort_strings(words, "sv_SE")
        # In Swedish, ö comes after z
        assert result == ["o", "z", "ö"]

    def test_reverse_sort(self):
        """Test reverse sorting."""
        words = ["a", "b", "c"]
        result = sort_strings(words, "en_US", reverse=True)
        assert result == ["c", "b", "a"]

    def test_strength_primary(self):
        """Test primary strength (ignores accents and case)."""
        words = ["café", "cafe", "CAFE"]
        result = sort_strings(words, "en_US", strength=STRENGTH_PRIMARY)
        # With primary strength, order depends on original positions for equal items
        assert len(result) == 3

    def test_case_first_upper(self):
        """Test uppercase first sorting."""
        words = ["a", "A", "b", "B"]
        result = sort_strings(words, "en_US", case_first="upper")
        # Uppercase should come before lowercase
        assert result.index("A") < result.index("a")
        assert result.index("B") < result.index("b")

    def test_case_first_lower(self):
        """Test lowercase first sorting."""
        words = ["a", "A", "b", "B"]
        result = sort_strings(words, "en_US", case_first="lower")
        # Lowercase should come before uppercase
        assert result.index("a") < result.index("A")
        assert result.index("b") < result.index("B")


class TestCompareStrings:
    """Tests for compare_strings function."""

    def test_less_than(self):
        """Test string less than comparison."""
        result = compare_strings("cafe", "café", "en_US")
        assert result < 0

    def test_greater_than(self):
        """Test string greater than comparison."""
        result = compare_strings("café", "cafe", "en_US")
        assert result > 0

    def test_equal(self):
        """Test string equality."""
        result = compare_strings("hello", "hello", "en_US")
        assert result == 0

    def test_primary_strength_equal(self):
        """Test that accented chars are equal at primary strength."""
        result = compare_strings("cafe", "café", "en_US", strength=STRENGTH_PRIMARY)
        assert result == 0

    def test_secondary_strength_not_equal(self):
        """Test that accented chars differ at secondary strength."""
        result = compare_strings("cafe", "café", "en_US", strength=STRENGTH_SECONDARY)
        assert result != 0


class TestGetSortKey:
    """Tests for get_sort_key function."""

    def test_sort_key_comparison(self):
        """Test that sort keys compare correctly."""
        key_a = get_sort_key("apple", "en_US")
        key_b = get_sort_key("banana", "en_US")
        assert key_a < key_b

    def test_sort_key_type(self):
        """Test that sort key is bytes."""
        key = get_sort_key("hello", "en_US")
        assert isinstance(key, bytes)


class TestListCollationTypes:
    """Tests for list_collation_types function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        types = list_collation_types()
        assert isinstance(types, list)

    def test_common_types_present(self):
        """Test that common collation types are present."""
        types = list_collation_types()
        assert "standard" in types
        assert "phonebook" in types


class TestGetCollatorInfo:
    """Tests for get_collator_info function."""

    def test_basic_info(self):
        """Test basic collator info."""
        info = get_collator_info("en_US")
        assert info["locale"] == "en_US"
        assert info["strength"] == "tertiary"

    def test_extended_info(self):
        """Test extended collator info."""
        info = get_collator_info("de_DE", include_extended=True)
        assert "extended" in info
        assert "has_tailoring" in info["extended"]


class TestSortCLI:
    """Tests for sort CLI commands."""

    def test_direct_sort_command(self):
        """Test icukit sort (direct command)."""
        code, out, err = run_cli("sort", "-t", "c\nb\na")
        assert code == 0
        assert out.strip() == "a\nb\nc"

    def test_sort_with_locale(self):
        """Test sorting with Swedish locale."""
        code, out, err = run_cli("sort", "--locale", "sv_SE", "-t", "ö\no\nz")
        assert code == 0
        lines = out.strip().split("\n")
        assert lines == ["o", "z", "ö"]

    def test_sort_reverse(self):
        """Test reverse sorting."""
        code, out, err = run_cli("sort", "-r", "-t", "a\nb\nc")
        assert code == 0
        assert out.strip() == "c\nb\na"

    def test_sort_unique(self):
        """Test unique sorting."""
        code, out, err = run_cli("sort", "-u", "-t", "a\nb\na\nc\nb")
        assert code == 0
        lines = out.strip().split("\n")
        assert len(lines) == 3
        assert set(lines) == {"a", "b", "c"}

    def test_locale_sort_subcommand(self):
        """Test icukit locale sort."""
        code, out, err = run_cli("locale", "sort", "-t", "c\nb\na")
        assert code == 0
        assert out.strip() == "a\nb\nc"

    def test_collate_sort_subcommand(self):
        """Test icukit collate sort."""
        code, out, err = run_cli("collate", "sort", "-t", "c\nb\na")
        assert code == 0
        assert out.strip() == "a\nb\nc"


class TestCompareCLI:
    """Tests for compare CLI commands."""

    def test_compare_less_than(self):
        """Test compare showing less than."""
        code, out, err = run_cli("locale", "compare", "a", "b")
        assert code == 1  # Exit 1 for less than
        assert "<" in out

    def test_compare_greater_than(self):
        """Test compare showing greater than."""
        code, out, err = run_cli("locale", "compare", "b", "a")
        assert code == 2  # Exit 2 for greater than
        assert ">" in out

    def test_compare_equal(self):
        """Test compare showing equal."""
        code, out, err = run_cli("locale", "compare", "hello", "hello")
        assert code == 0  # Exit 0 for equal
        assert "=" in out

    def test_compare_primary_strength(self):
        """Test compare with primary strength."""
        code, out, err = run_cli("collate", "compare", "cafe", "café", "--strength", "primary")
        assert code == 0  # Equal at primary strength
        assert "=" in out


class TestCollateListCLI:
    """Tests for collate list CLI commands."""

    def test_list_types(self):
        """Test listing collation types."""
        code, out, err = run_cli("collate", "list", "types")
        assert code == 0
        assert "standard" in out

    def test_list_strengths(self):
        """Test listing collation strengths."""
        code, out, err = run_cli("collate", "list", "strengths")
        assert code == 0
        assert "primary" in out
        assert "tertiary" in out


class TestCollateInfoCLI:
    """Tests for collate info CLI commands."""

    def test_info_basic(self):
        """Test basic collator info."""
        code, out, err = run_cli("collate", "info", "de_DE")
        assert code == 0
        assert "de_DE" in out
        assert "tertiary" in out

    def test_info_extended(self):
        """Test extended collator info."""
        code, out, err = run_cli("collate", "info", "de_DE", "-x")
        assert code == 0
        assert "has_tailoring" in out
