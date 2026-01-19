"""Tests for the breaker module."""

import subprocess
import sys

from icukit import Breaker, break_graphemes, break_lines, break_sentences, break_words


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


class TestBreakSentences:
    """Tests for break_sentences function."""

    def test_basic_sentences(self):
        """Test basic sentence breaking."""
        text = "Hello world. How are you?"
        sentences = break_sentences(text, "en")
        assert len(sentences) == 2
        assert "Hello world" in sentences[0]
        assert "How are you" in sentences[1]

    def test_empty_text(self):
        """Test empty text."""
        assert break_sentences("", "en") == []

    def test_single_sentence(self):
        """Test single sentence."""
        sentences = break_sentences("Hello world", "en")
        assert len(sentences) == 1

    def test_multiple_punctuation(self):
        """Test different punctuation."""
        text = "Hello! How are you? I'm fine."
        sentences = break_sentences(text, "en")
        assert len(sentences) == 3


class TestBreakWords:
    """Tests for break_words function."""

    def test_basic_words(self):
        """Test basic word breaking."""
        words = break_words("Hello, world!", "en")
        assert "Hello" in words
        assert "world" in words

    def test_skip_punctuation(self):
        """Test skipping punctuation."""
        words = break_words("Hello, world!", "en", skip_punctuation=True)
        assert "Hello" in words
        assert "world" in words
        assert "," not in words
        assert "!" not in words

    def test_include_whitespace(self):
        """Test including whitespace."""
        words = break_words("Hello world", "en", skip_whitespace=False)
        assert " " in words

    def test_empty_text(self):
        """Test empty text."""
        assert break_words("", "en") == []


class TestBreakLines:
    """Tests for break_lines function."""

    def test_basic_lines(self):
        """Test basic line breaking."""
        text = "Hello world how are you"
        segments = break_lines(text, "en")
        assert len(segments) > 0
        # Line breaks typically occur at word boundaries
        assert "".join(segments) == text

    def test_empty_text(self):
        """Test empty text."""
        assert break_lines("", "en") == []


class TestBreakGraphemes:
    """Tests for break_graphemes function."""

    def test_basic_graphemes(self):
        """Test basic grapheme breaking."""
        graphemes = break_graphemes("Hello", "en")
        assert graphemes == ["H", "e", "l", "l", "o"]

    def test_combining_characters(self):
        """Test combining characters stay together."""
        # e + combining acute accent = é
        graphemes = break_graphemes("e\u0301", "en")
        assert len(graphemes) == 1
        # The grapheme keeps original characters (not normalized)
        assert graphemes[0] == "e\u0301"

    def test_empty_text(self):
        """Test empty text."""
        assert break_graphemes("", "en") == []


class TestBreakerClass:
    """Tests for Breaker class."""

    def test_init(self):
        """Test initialization."""
        breaker = Breaker("en")
        assert breaker.locale == "en"

    def test_repr(self):
        """Test string representation."""
        breaker = Breaker("en_US")
        assert "en_US" in repr(breaker)

    def test_iter_sentences(self):
        """Test sentence iteration."""
        breaker = Breaker("en")
        sentences = list(breaker.iter_sentences("Hello. World."))
        assert len(sentences) == 2

    def test_iter_words(self):
        """Test word iteration."""
        breaker = Breaker("en")
        words = list(breaker.iter_words("Hello world"))
        assert "Hello" in words
        assert "world" in words

    def test_tokenize_sentences(self):
        """Test sentence tokenization."""
        breaker = Breaker("en")
        tokenized = breaker.tokenize_sentences("Hello world. How are you?")
        assert len(tokenized) == 2
        assert "Hello" in tokenized[0]
        assert "world" in tokenized[0]


class TestBreakerCLI:
    """Tests for breaker CLI commands."""

    def test_sentences(self):
        """Test sentences subcommand."""
        code, out, err = run_cli("break", "sentences", "-t", "Hello. World.")
        assert code == 0
        assert "Hello" in out
        assert "World" in out

    def test_words(self):
        """Test words subcommand."""
        code, out, err = run_cli("break", "words", "-t", "Hello, world!")
        assert code == 0
        assert "Hello" in out
        assert "world" in out

    def test_words_skip_punctuation(self):
        """Test words with --skip-punctuation."""
        code, out, err = run_cli("break", "words", "--skip-punctuation", "-t", "Hello, world!")
        assert code == 0
        assert "Hello" in out
        assert "world" in out
        # Punctuation should not be in output
        lines = out.strip().split("\n")
        assert "," not in lines
        assert "!" not in lines

    def test_graphemes(self):
        """Test graphemes subcommand."""
        code, out, err = run_cli("break", "graphemes", "-t", "Hello")
        assert code == 0
        assert "H" in out
        assert "e" in out

    def test_graphemes_with_codepoints(self):
        """Test graphemes with --show-codepoints."""
        code, out, err = run_cli("break", "graphemes", "--show-codepoints", "-t", "AB")
        assert code == 0
        assert "U+0041" in out  # A
        assert "U+0042" in out  # B

    def test_tokenize(self):
        """Test tokenize subcommand."""
        code, out, err = run_cli("break", "tokenize", "-t", "Hello world. Bye.")
        assert code == 0
        assert "1." in out
        assert "2." in out

    def test_lines(self):
        """Test lines subcommand."""
        code, out, err = run_cli("break", "lines", "-t", "Hello world")
        assert code == 0
        assert "Hello" in out or "world" in out

    def test_locale_option(self):
        """Test --locale option."""
        code, out, err = run_cli("break", "words", "--locale", "ja", "-t", "こんにちは")
        assert code == 0
        # Japanese word breaking should work

    def test_prefix_matching(self):
        """Test prefix matching for subcommands."""
        code, out, err = run_cli("break", "sent", "-t", "Hello. World.")
        assert code == 0
        assert "Hello" in out

    def test_json_output(self):
        """Test JSON output."""
        code, out, err = run_cli("break", "words", "--json", "-t", "Hello world")
        assert code == 0
        assert "[" in out
        assert "Hello" in out
