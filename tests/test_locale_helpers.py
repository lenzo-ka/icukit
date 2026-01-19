"""Tests for locale_helpers utilities."""

from icukit.cli.locale_helpers import MAJOR_SCRIPTS, parse_multi_value


class TestParseMultiValue:
    """Test parse_multi_value function."""

    def test_simple_value(self):
        """Single value should match."""
        available = ["Latin-Cyrillic", "Latin-Greek", "Latin-Arabic"]
        result = parse_multi_value("Latin-Cyrillic", "transliterator", available)
        assert result == ["Latin-Cyrillic"]

    def test_comma_separated(self):
        """Comma-separated values should all match."""
        available = ["Latin-Cyrillic", "Latin-Greek", "Latin-Arabic"]
        result = parse_multi_value("Latin-Cyrillic,Latin-Greek", "transliterator", available)
        assert "Latin-Cyrillic" in result
        assert "Latin-Greek" in result

    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        available = ["Latin-Cyrillic", "Latin-Greek"]
        result = parse_multi_value("latin-cyrillic", "transliterator", available)
        assert result == ["Latin-Cyrillic"]

    def test_regex_pattern(self):
        """Regex patterns should filter available values."""
        available = ["Latin-Cyrillic", "Latin-Greek", "Cyrillic-Latin", "Greek-Latin"]
        result = parse_multi_value("Latin-.*", "transliterator", available)
        assert "Latin-Cyrillic" in result
        assert "Latin-Greek" in result
        assert "Cyrillic-Latin" not in result

    def test_major_keyword_scripts(self):
        """'major' keyword should return major scripts."""
        result = parse_multi_value("major", "script")
        assert result == MAJOR_SCRIPTS

    def test_any_keyword(self):
        """'any' keyword should return all available values."""
        available = ["a", "b", "c"]
        result = parse_multi_value("any", "transliterator", available)
        assert result == available

    def test_empty_value(self):
        """Empty value should return empty list."""
        result = parse_multi_value("", "transliterator", ["a", "b"])
        assert result == []

    def test_no_match(self):
        """Non-matching value should return empty list."""
        available = ["Latin-Cyrillic", "Latin-Greek"]
        result = parse_multi_value("NonExistent", "transliterator", available)
        assert result == []

    def test_without_available_values(self):
        """Should return normalized values when no available list."""
        result = parse_multi_value("a,b,c", "other")
        assert result == ["a", "b", "c"]
