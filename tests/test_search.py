"""Tests for locale-aware search module and CLI."""

import subprocess
import sys

from icukit import (
    STRENGTH_PRIMARY,
    STRENGTH_SECONDARY,
    STRENGTH_TERTIARY,
    StringSearcher,
    search_all,
    search_count,
    search_first,
    search_replace,
)


class TestSearchLibrary:
    """Tests for search library functions."""

    def test_search_all_basic(self):
        """Test basic search_all."""
        matches = search_all("cafe", "The cafe is here", "en_US")
        assert len(matches) == 1
        assert matches[0]["text"] == "cafe"
        assert matches[0]["start"] == 4
        assert matches[0]["end"] == 8

    def test_search_all_case_insensitive(self):
        """Test case-insensitive search with primary strength."""
        text = "cafe Cafe CAFE"
        matches = search_all("cafe", text, "en_US", strength=STRENGTH_PRIMARY)
        assert len(matches) == 3

    def test_search_all_accent_insensitive(self):
        """Test accent-insensitive search."""
        text = "Visit the café for coffee"
        matches = search_all("cafe", text, "fr_FR", strength=STRENGTH_PRIMARY)
        assert len(matches) == 1
        assert matches[0]["text"] == "café"

    def test_search_all_no_matches(self):
        """Test search with no matches."""
        matches = search_all("xyz", "abc def ghi", "en_US")
        assert matches == []

    def test_search_all_empty_pattern(self):
        """Test search with empty pattern."""
        matches = search_all("", "some text", "en_US")
        assert matches == []

    def test_search_all_empty_text(self):
        """Test search with empty text."""
        matches = search_all("pattern", "", "en_US")
        assert matches == []

    def test_search_first_found(self):
        """Test search_first when pattern is found."""
        match = search_first("cafe", "The café and CAFE", "en_US", strength=STRENGTH_PRIMARY)
        assert match is not None
        assert match["text"] == "café"
        assert match["start"] == 4

    def test_search_first_not_found(self):
        """Test search_first when pattern is not found."""
        match = search_first("xyz", "abc def ghi", "en_US")
        assert match is None

    def test_search_count_multiple(self):
        """Test counting multiple matches."""
        count = search_count("a", "abracadabra", "en_US")
        assert count == 5

    def test_search_count_case_insensitive(self):
        """Test count with primary strength."""
        count = search_count("cafe", "café Cafe CAFE", "en_US", strength=STRENGTH_PRIMARY)
        assert count == 3

    def test_search_count_zero(self):
        """Test count with no matches."""
        count = search_count("xyz", "abc def ghi", "en_US")
        assert count == 0

    def test_search_replace_basic(self):
        """Test basic replace."""
        result = search_replace("cat", "The cat sat on the cat", "new", "en_US")
        assert result == "The new sat on the new"

    def test_search_replace_accent_insensitive(self):
        """Test accent-insensitive replace."""
        result = search_replace("cafe", "Visit the café", "tea", "en_US", strength=STRENGTH_PRIMARY)
        assert result == "Visit the tea"

    def test_search_replace_limited(self):
        """Test replace with count limit."""
        result = search_replace("a", "abracadabra", "X", "en_US", count=2)
        assert result == "XbrXcadabra"

    def test_search_replace_no_match(self):
        """Test replace with no matches."""
        result = search_replace("xyz", "abc def", "new", "en_US")
        assert result == "abc def"

    def test_strength_tertiary_case_sensitive(self):
        """Test tertiary strength is case-sensitive."""
        matches = search_all("Cafe", "cafe Cafe CAFE", "en_US", strength=STRENGTH_TERTIARY)
        assert len(matches) == 1
        assert matches[0]["text"] == "Cafe"

    def test_strength_secondary_accent_sensitive(self):
        """Test secondary strength is accent-sensitive but case-insensitive."""
        matches = search_all("cafe", "cafe Cafe café", "en_US", strength=STRENGTH_SECONDARY)
        assert len(matches) == 2  # cafe and Cafe match, but not café


class TestStringSearcher:
    """Tests for StringSearcher class."""

    def test_init(self):
        """Test searcher initialization."""
        searcher = StringSearcher("pattern", "en_US")
        assert searcher.pattern == "pattern"
        assert searcher.locale == "en_US"

    def test_init_with_strength(self):
        """Test searcher with strength."""
        searcher = StringSearcher("cafe", "en_US", strength=STRENGTH_PRIMARY)
        assert searcher.strength == STRENGTH_PRIMARY

    def test_find_all(self):
        """Test find_all method."""
        searcher = StringSearcher("cafe", "en_US", strength=STRENGTH_PRIMARY)
        matches = searcher.find_all("café Cafe CAFE")
        assert len(matches) == 3

    def test_find_first(self):
        """Test find_first method."""
        searcher = StringSearcher("cafe", "en_US", strength=STRENGTH_PRIMARY)
        match = searcher.find_first("The café is here")
        assert match is not None
        assert match["text"] == "café"

    def test_count(self):
        """Test count method."""
        searcher = StringSearcher("a", "en_US")
        count = searcher.count("abracadabra")
        assert count == 5

    def test_contains_true(self):
        """Test contains returns True when found."""
        searcher = StringSearcher("cafe", "en_US", strength=STRENGTH_PRIMARY)
        assert searcher.contains("The café is here") is True

    def test_contains_false(self):
        """Test contains returns False when not found."""
        searcher = StringSearcher("xyz", "en_US")
        assert searcher.contains("abc def ghi") is False

    def test_replace(self):
        """Test replace method."""
        searcher = StringSearcher("cafe", "en_US", strength=STRENGTH_PRIMARY)
        result = searcher.replace("Visit the café", "tea")
        assert result == "Visit the tea"

    def test_repr(self):
        """Test string representation."""
        searcher = StringSearcher("cafe", "en_US", strength=STRENGTH_PRIMARY)
        assert "cafe" in repr(searcher)
        assert "en_US" in repr(searcher)
        assert "primary" in repr(searcher)


class TestSearchCLI:
    """Tests for search CLI command."""

    def test_find_basic(self):
        """Test search find command."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "search",
                "find",
                "cafe",
                "-t",
                "The cafe is here",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "cafe" in result.stdout

    def test_find_case_insensitive(self):
        """Test case-insensitive search."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "search",
                "find",
                "cafe",
                "-t",
                "café Cafe CAFE",
                "-s",
                "primary",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "café" in result.stdout
        assert "Cafe" in result.stdout
        assert "CAFE" in result.stdout

    def test_find_json(self):
        """Test JSON output."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "search",
                "find",
                "cafe",
                "-t",
                "The cafe",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"start"' in result.stdout
        assert '"end"' in result.stdout
        assert '"text"' in result.stdout

    def test_first_found(self):
        """Test search first command when found."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "search",
                "first",
                "cafe",
                "-t",
                "The café is here",
                "-s",
                "primary",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "café" in result.stdout

    def test_first_not_found(self):
        """Test search first when not found."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "search", "first", "xyz", "-t", "abc def"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1

    def test_count(self):
        """Test search count command."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "search",
                "count",
                "cafe",
                "-t",
                "café Cafe CAFE",
                "-s",
                "primary",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "3" in result.stdout

    def test_replace(self):
        """Test search replace command."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "search",
                "replace",
                "cafe",
                "tea",
                "-t",
                "Visit the café",
                "-s",
                "primary",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "tea" in result.stdout

    def test_contains_true(self):
        """Test search contains when found."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "search",
                "contains",
                "cafe",
                "-t",
                "The café",
                "-s",
                "primary",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "true" in result.stdout

    def test_contains_false(self):
        """Test search contains when not found."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "search", "contains", "xyz", "-t", "abc def"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "false" in result.stdout

    def test_alias_find(self):
        """Test 'find' alias for search command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "find", "find", "cafe", "-t", "The cafe"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "cafe" in result.stdout

    def test_help(self):
        """Test search help."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "search", "help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "find" in result.stdout.lower() or "search" in result.stdout.lower()
