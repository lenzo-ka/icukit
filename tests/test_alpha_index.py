"""Tests for alphabetic index module and CLI."""

import subprocess
import sys

from icukit import AlphabeticIndex, create_index_buckets, get_bucket_for_name, get_bucket_labels


class TestAlphaIndexLibrary:
    """Tests for alphabetic index library functions."""

    def test_create_index_buckets(self):
        """Test creating index buckets."""
        buckets = create_index_buckets(["Alice", "Bob", "Carol", "Zebra"], "en_US")
        assert "A" in buckets
        assert "B" in buckets
        assert "C" in buckets
        assert "Z" in buckets
        assert "Alice" in buckets["A"]
        assert "Bob" in buckets["B"]

    def test_create_index_buckets_same_letter(self):
        """Test buckets with multiple items in same bucket."""
        buckets = create_index_buckets(["Alice", "Amanda", "Anna"], "en_US")
        assert "A" in buckets
        assert len(buckets["A"]) == 3

    def test_get_bucket_labels_english(self):
        """Test getting English bucket labels."""
        labels = get_bucket_labels("en_US")
        assert "A" in labels
        assert "Z" in labels

    def test_get_bucket_labels_japanese(self):
        """Test getting Japanese bucket labels."""
        labels = get_bucket_labels("ja_JP")
        # Japanese uses hiragana for index
        assert "あ" in labels or len(labels) > 0

    def test_get_bucket_for_name(self):
        """Test getting bucket for a name."""
        bucket = get_bucket_for_name("Alice", "en_US")
        assert bucket == "A"

    def test_get_bucket_for_name_lowercase(self):
        """Test bucket for lowercase name."""
        bucket = get_bucket_for_name("alice", "en_US")
        assert bucket == "A"


class TestAlphabeticIndex:
    """Tests for AlphabeticIndex class."""

    def test_init(self):
        """Test index initialization."""
        index = AlphabeticIndex("en_US")
        assert index.locale == "en_US"

    def test_add(self):
        """Test adding items."""
        index = AlphabeticIndex("en_US")
        index.add("Alice")
        index.add("Bob")
        assert index.record_count == 2

    def test_add_many(self):
        """Test adding multiple items."""
        index = AlphabeticIndex("en_US")
        index.add_many(["Alice", "Bob", "Carol"])
        assert index.record_count == 3

    def test_get_buckets(self):
        """Test getting buckets."""
        index = AlphabeticIndex("en_US")
        index.add_many(["Alice", "Bob", "Zebra"])
        buckets = index.get_buckets()
        assert "A" in buckets
        assert "B" in buckets
        assert "Z" in buckets

    def test_get_bucket_for(self):
        """Test getting bucket for a name."""
        index = AlphabeticIndex("en_US")
        bucket = index.get_bucket_for("Alice")
        assert bucket == "A"

    def test_get_labels(self):
        """Test getting labels."""
        index = AlphabeticIndex("en_US")
        labels = index.get_labels()
        assert "A" in labels
        assert "Z" in labels

    def test_bucket_count(self):
        """Test bucket count."""
        index = AlphabeticIndex("en_US")
        assert index.bucket_count > 0

    def test_clear(self):
        """Test clearing records."""
        index = AlphabeticIndex("en_US")
        index.add_many(["Alice", "Bob"])
        assert index.record_count == 2
        index.clear()
        assert index.record_count == 0

    def test_chaining(self):
        """Test method chaining."""
        index = AlphabeticIndex("en_US")
        result = index.add("Alice").add("Bob").add("Carol")
        assert result is index
        assert index.record_count == 3

    def test_repr(self):
        """Test string representation."""
        index = AlphabeticIndex("en_US")
        index.add("Alice")
        assert "AlphabeticIndex" in repr(index)
        assert "en_US" in repr(index)


class TestAlphaIndexCLI:
    """Tests for alpha-index CLI command."""

    def test_buckets(self):
        """Test buckets command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "alpha-index", "buckets"],
            input="Alice\nBob\nCarol\nZebra\n",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "[A]" in result.stdout
        assert "Alice" in result.stdout

    def test_buckets_json(self):
        """Test buckets with JSON output."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "alpha-index", "buckets", "--json"],
            input="Alice\nBob\n",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"A"' in result.stdout

    def test_labels(self):
        """Test labels command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "alpha-index", "labels", "en_US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "A" in result.stdout

    def test_bucket(self):
        """Test bucket command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "alpha-index", "bucket", "Alice"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "A" in result.stdout

    def test_alias_index(self):
        """Test 'index' alias."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "index", "bucket", "Bob"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "B" in result.stdout

    def test_help(self):
        """Test help output."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "alpha-index", "help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
