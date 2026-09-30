"""Tests for the breaker module."""

import json
import subprocess
import sys

import pytest

from icukit import (
    Breaker,
    BreakRuleLoadError,
    SentenceOverride,
    break_graphemes,
    break_lines,
    break_sentence_spans,
    break_sentences,
    break_words,
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

    def test_english_default_matches_sentence_override_default(self):
        text = "The U.S. Supreme Court ruled. Markets moved."
        assert Breaker("en_US").break_sentence_spans(text) == SentenceOverride("en_US").spans(text)
        assert break_sentence_spans(text, "en_US") == SentenceOverride("en_US").spans(text)

    def test_english_default_loads_shipped_exception_list_and_none_stays_raw(self):
        text = "He met Mr. Smith today. He left."

        assert Breaker("en").break_sentences(text) == [
            "He met Mr. Smith today. ",
            "He left.",
        ]
        assert Breaker("en", base="en-tn-cart@1").break_sentences(text) == [
            "He met Mr. Smith today. ",
            "He left.",
        ]
        assert Breaker("en", base="none").break_sentences(text) == [
            "He met Mr. ",
            "Smith today. ",
            "He left.",
        ]
        first = SentenceOverride("en").decide(text)[0]
        assert (first["decision"], first["layer"], first["id"]) == (
            "no-break",
            "exceptions",
            "abbreviation:Mr.",
        )

    def test_posix_variant_defaults_and_explicit_learned_bases(self):
        text = "The U.S. Supreme Court ruled. Markets moved."
        for locale in ("en_US_POSIX", "en_US_POSIX_FOO", "en_POSIX"):
            assert Breaker(locale).break_sentence_spans(text) == Breaker(
                locale, base="none"
            ).break_sentence_spans(text)
            for base in ("en-tn-cart@1", "en-tn@1"):
                with pytest.raises(BreakRuleLoadError, match="IDENTITY_MISMATCH"):
                    Breaker(locale, base=base).break_sentence_spans(text)

        assert Breaker("en_US").break_sentence_spans(text) == Breaker(
            "en_US", base="en-tn-cart@1"
        ).break_sentence_spans(text)
        assert Breaker("en_US").break_sentence_spans(text) != Breaker(
            "en_US", base="none"
        ).break_sentence_spans(text)

    def test_base_none_preserves_parent_raw_icu_span_golden(self):
        text = "The U.S. Supreme Court ruled. Markets moved."
        expected = [
            {
                "text": "The U.S. ",
                "start": 0,
                "end": 9,
                "codepoint_start": 0,
                "codepoint_end": 9,
                "utf8_start": 0,
                "utf8_end": 9,
                "utf16_start": 0,
                "utf16_end": 9,
                "types": [],
                "statuses": [],
            },
            {
                "text": "Supreme Court ruled. ",
                "start": 9,
                "end": 30,
                "codepoint_start": 9,
                "codepoint_end": 30,
                "utf8_start": 9,
                "utf8_end": 30,
                "utf16_start": 9,
                "utf16_end": 30,
                "types": [],
                "statuses": [],
            },
            {
                "text": "Markets moved.",
                "start": 30,
                "end": 44,
                "codepoint_start": 30,
                "codepoint_end": 44,
                "utf8_start": 30,
                "utf8_end": 44,
                "utf16_start": 30,
                "utf16_end": 44,
                "types": [],
                "statuses": [],
            },
        ]
        assert Breaker("en_US", base="none").break_sentence_spans(text) == expected
        assert break_sentence_spans(text, "en_US", base="none") == expected
        assert break_sentences(text, "en_US", base="none") == [span["text"] for span in expected]

    def test_non_english_default_and_non_sentence_levels_are_unchanged(self):
        french = "M. Dupont est arrivé. Ensuite, il est parti."
        assert Breaker("fr_FR").break_sentence_spans(french) == Breaker(
            "fr_FR", base="none"
        ).break_sentence_spans(french)

        text = "The U.S. Supreme Court ruled. Markets moved."
        default = Breaker("en_US")
        raw = Breaker("en_US", base="none")
        assert default.break_word_spans(text) == raw.break_word_spans(text)
        assert default.break_line_spans(text) == raw.break_line_spans(text)
        assert default.break_grapheme_spans(text) == raw.break_grapheme_spans(text)

    def test_sentence_override_is_cached_per_locale_and_base(self):
        from icukit.breaker import _sentence_override

        _sentence_override.cache_clear()
        try:
            assert _sentence_override("en_US", None) is _sentence_override("en_US", None)
            assert _sentence_override("en_US", None) is not _sentence_override("en_US", "en-tn@1")
        finally:
            _sentence_override.cache_clear()


class TestBreakerCLI:
    """Tests for breaker CLI commands."""

    def test_sentences(self):
        """Test sentences subcommand."""
        code, out, err = run_cli("break", "sentences", "-t", "Hello. World.")
        assert code == 0
        assert "Hello" in out
        assert "World" in out

    def test_sentence_base_none_preserves_old_cli_output_and_default_uses_model(self):
        text = "The U.S. Supreme Court ruled. Markets moved."
        code, raw, err = run_cli("break", "sentences", "--base", "none", "--json", "-t", text)
        assert (code, err) == (0, "")
        assert raw == '[\n  "The U.S.",\n  "Supreme Court ruled.",\n  "Markets moved."\n]\n'

        code, learned, err = run_cli("break", "sentences", "--json", "-t", text)
        assert (code, err) == (0, "")
        assert learned == '[\n  "The U.S. Supreme Court ruled.",\n  "Markets moved."\n]\n'

        code, raw_tokens, err = run_cli("break", "tokenize", "--base", "none", "--json", "-t", text)
        assert (code, err) == (0, "")
        assert len(json.loads(raw_tokens)) == 3

        code, learned_tokens, err = run_cli("break", "tokenize", "--json", "-t", text)
        assert (code, err) == (0, "")
        assert len(json.loads(learned_tokens)) == 2

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


class TestAstralOffsets:
    """F1: ICU BreakIterator reports UTF-16 code-unit offsets, but Python str
    slices by code point. An astral character (above U+FFFF, stored as a
    surrogate pair) shifts every subsequent boundary, corrupting all four
    iterators. Each test pins the corrected boundary and names the buggy output.
    """

    def test_word_tokens_not_shifted_by_astral(self):
        # buggy output: ['👍 ', 'F', 'ig.', '5', 'h', 'olds']
        words = break_words("\U0001f44d Fig. 5 holds", "en")
        assert "\U0001f44d" in words
        assert "Fig" in words
        assert "holds" in words
        assert "F" not in words
        assert "ig." not in words
        assert "h" not in words

    def test_graphemes_not_merged_across_astral(self):
        # buggy output merged the following char: ['a', '👍b']
        assert break_graphemes("a\U0001f44db") == ["a", "\U0001f44d", "b"]

    def test_sentence_boundary_not_shifted_by_astral(self):
        # buggy output: ['👍 One. T', 'wo.']
        sentences = break_sentences("\U0001f44d One. Two.", "en")
        assert len(sentences) == 2
        assert sentences[1] == "Two."

    def test_line_segments_not_shifted_by_astral(self):
        # buggy first segment ran into the next word: '👍 F'
        segments = break_lines("\U0001f44d Fig 5 holds", "en")
        assert "".join(segments) == "\U0001f44d Fig 5 holds"
        assert segments[0] == "\U0001f44d "


class TestTokenizeWholeText:
    """F3: tokenize_sentences must segment words over the whole text, not
    re-segment each sentence substring. Re-segmenting loses left context and,
    once F1's shift mis-cuts a sentence substring, splits a word across the
    sentence edge. Non-astral text has no visible symptom (the offsets that go
    wrong are not exposed until extents land, F4); the astral case witnesses it.
    """

    def test_word_not_split_across_sentence_boundary(self):
        # buggy output split "It" into "I" (sentence 1) and "t" (sentence 2)
        b = Breaker("en")
        toks = b.tokenize_sentences("\U0001f44d Fig. 5 holds. It works.")
        assert len(toks) == 2
        flat = [t for sentence in toks for t in sentence]
        assert "It" in flat
        assert all(t for t in flat), "no empty tokens"
        assert "It" in toks[1]

    def test_tokenize_matches_whole_text_segmentation(self):
        b = Breaker("en")
        text = "\U0001f44d Fig. 5 holds. It works."
        flat = [t for sentence in b.tokenize_sentences(text) for t in sentence]
        assert flat == b.break_words(text)
