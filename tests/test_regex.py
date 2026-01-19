"""Tests for Unicode Regex module."""

import pytest

from icukit import (
    CASE_INSENSITIVE,
    PatternError,
    UnicodeRegex,
    list_unicode_categories,
    list_unicode_properties,
    list_unicode_scripts,
    regex_find,
    regex_replace,
    regex_split,
)


class TestUnicodeRegex:
    """Test Unicode regex functionality."""

    def test_regex_find(self):
        """Test finding matches."""
        text = "Hello 世界"
        matches = regex_find(r"\p{Script=Han}+", text)
        assert len(matches) == 1
        assert matches[0]["text"] == "世界"

    def test_regex_find_greek(self):
        """Test finding Greek matches."""
        text = "Hello Αθήνα World"
        matches = regex_find(r"\p{Script=Greek}+", text)
        assert len(matches) == 1
        assert matches[0]["text"] == "Αθήνα"

    def test_regex_replace(self):
        """Test regex replacement."""
        text = "Hello123World"
        result = regex_replace(r"\d+", text, " ")
        assert "Hello" in result
        assert "World" in result
        assert "123" not in result

    def test_regex_split(self):
        """Test regex split."""
        text = "apple,banana;orange:grape"
        parts = regex_split(r"[,;:]", text)
        assert "apple" in parts
        assert "banana" in parts
        assert "orange" in parts
        assert "grape" in parts

    def test_unicode_properties(self):
        """Test Unicode property matching."""
        regex = UnicodeRegex(r"\p{L}+")  # All letters
        matches = regex.find_all("Hello123World")
        assert len(matches) == 2
        assert matches[0]["text"] == "Hello"
        assert matches[1]["text"] == "World"

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        regex = UnicodeRegex(r"café", CASE_INSENSITIVE)
        matches = regex.find_all("Café CAFÉ café")
        assert len(matches) == 3

    def test_script_matching(self):
        """Test matching by Unicode script."""
        regex = UnicodeRegex(r"\p{Script=Arabic}+")
        text = "Hello مرحبا world"
        matches = regex.find_all(text)
        assert len(matches) == 1
        assert "مرحبا" in matches[0]["text"]

    def test_regex_groups(self):
        """Test regex with capture groups."""
        regex = UnicodeRegex(r"(\w+)@(\w+)\.(com)")
        result = regex.replace("test@example.com", r"$1 at $2 dot $3")
        assert "test" in result
        assert "example" in result

    def test_invalid_pattern_raises_error(self):
        """Test that invalid patterns raise PatternError."""
        with pytest.raises(PatternError):
            UnicodeRegex(r"[invalid")

    def test_search(self):
        """Test search method."""
        regex = UnicodeRegex(r"\d+")
        assert regex.search("abc123def") is True
        assert regex.search("abcdef") is False

    def test_match(self):
        """Test match method (anchored)."""
        regex = UnicodeRegex(r"\d+")
        assert regex.match("123") is True
        assert regex.match("abc123") is False

    def test_find_with_start(self):
        """Test find with start position."""
        regex = UnicodeRegex(r"\d+")
        match = regex.find("abc123def456", start=7)
        assert match is not None
        assert match["text"] == "456"

    def test_replace_with_limit(self):
        """Test replace with limit."""
        regex = UnicodeRegex(r"\d+")
        result = regex.replace("a1b2c3d4", "X", limit=2)
        assert result == "aXbXc3d4"

    def test_split_with_limit(self):
        """Test split with limit."""
        regex = UnicodeRegex(r",")
        parts = regex.split("a,b,c,d", limit=2)
        assert len(parts) == 3
        assert parts == ["a", "b", "c,d"]

    def test_list_properties(self):
        """Test listing properties."""
        props = UnicodeRegex.list_properties()
        assert "Letter" in props
        assert "Digit" in props

    def test_list_categories(self):
        """Test listing categories."""
        cats = UnicodeRegex.list_categories()
        assert "L" in cats
        assert "N" in cats
        assert cats["L"] == "Letter"

    def test_list_scripts(self):
        """Test listing scripts."""
        scripts = UnicodeRegex.list_scripts()
        assert "Latin" in scripts
        assert "Greek" in scripts

    def test_escape(self):
        """Test escaping special characters."""
        escaped = UnicodeRegex.escape("a.b*c?d")
        assert escaped == r"a\.b\*c\?d"

    def test_iter_matches(self):
        """Test iterating over matches."""
        regex = UnicodeRegex(r"\d+")
        matches = list(regex.iter_matches("a1b22c333"))
        assert len(matches) == 3
        assert matches[0]["text"] == "1"
        assert matches[1]["text"] == "22"
        assert matches[2]["text"] == "333"


class TestUnicodeListFunctions:
    """Test module-level list functions for structured output."""

    def test_list_unicode_properties(self):
        """Test listing properties as structured data."""
        props = list_unicode_properties()
        assert isinstance(props, list)
        assert len(props) > 0
        # Check structure
        first = props[0]
        assert "category" in first
        assert "pattern" in first
        assert "description" in first

    def test_list_unicode_properties_content(self):
        """Test property content."""
        props = list_unicode_properties()
        patterns = [p["pattern"] for p in props]
        assert r"\p{L}" in patterns
        assert r"\p{N}" in patterns

    def test_list_unicode_categories(self):
        """Test listing categories as structured data."""
        cats = list_unicode_categories()
        assert isinstance(cats, list)
        assert len(cats) > 0
        # Check structure
        first = cats[0]
        assert "code" in first
        assert "description" in first

    def test_list_unicode_categories_content(self):
        """Test category content."""
        cats = list_unicode_categories()
        codes = [c["code"] for c in cats]
        assert "L" in codes
        assert "N" in codes
        assert "P" in codes

    def test_list_unicode_scripts(self):
        """Test listing scripts as structured data."""
        scripts = list_unicode_scripts()
        assert isinstance(scripts, list)
        assert len(scripts) > 0
        # Check structure
        first = scripts[0]
        assert "name" in first
        assert "pattern" in first

    def test_list_unicode_scripts_content(self):
        """Test script content."""
        scripts = list_unicode_scripts()
        names = [s["name"] for s in scripts]
        assert "Latin" in names
        assert "Greek" in names
        assert "Arabic" in names

    def test_list_unicode_scripts_pattern_format(self):
        """Test that script patterns are properly formatted."""
        scripts = list_unicode_scripts()
        latin = next(s for s in scripts if s["name"] == "Latin")
        assert latin["pattern"] == r"\p{Script=Latin}"
