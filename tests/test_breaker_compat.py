"""Golden compatibility tests captured before the typed-span refactor."""

import pytest

from icukit import Breaker


@pytest.mark.parametrize(
    ("text", "skip_whitespace", "skip_punctuation", "expected"),
    [
        ("a\x1cb", True, False, ["a", "b"]),
        ("a\x1cb", False, False, ["a", "\x1c", "b"]),
        ("a\xa0b", True, False, ["a", "b"]),
        ("a\xa0b", False, False, ["a", "\xa0", "b"]),
        ("a, b", True, False, ["a", ",", "b"]),
        ("a, b", False, False, ["a", ",", " ", "b"]),
        ("a, b", True, True, ["a", "b"]),
        ("a, b", False, True, ["a", " ", "b"]),
    ],
)
def test_words_golden(text, skip_whitespace, skip_punctuation, expected):
    breaker = Breaker("en_US")
    assert breaker.break_words(text, skip_whitespace, skip_punctuation) == expected
    assert list(breaker.iter_words(text, skip_whitespace, skip_punctuation)) == expected


def test_sentences_golden():
    breaker = Breaker("en_US")
    assert breaker.break_sentences("   ", skip_empty=True) == []
    assert list(breaker.iter_sentences("   ", skip_empty=True)) == []
    assert breaker.break_sentences("   ", skip_empty=False) == ["   "]
    assert list(breaker.iter_sentences("   ", skip_empty=False)) == ["   "]


def test_tokenize_sentences_golden():
    breaker = Breaker("en_US")
    assert breaker.tokenize_sentences(" \n") == []
    assert breaker.tokenize_sentences("Hello world. How are you?") == [
        ["Hello", "world", "."],
        ["How", "are", "you", "?"],
    ]


def test_graphemes_golden():
    breaker = Breaker("en_US")
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466"
    assert breaker.break_graphemes(family) == [family]
    assert list(breaker.iter_graphemes(family)) == [family]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a\r\nb", ["a\r\n", "b"]),
        ("Hello world. How are you?", ["Hello ", "world. ", "How ", "are ", "you?"]),
    ],
)
def test_lines_golden(text, expected):
    breaker = Breaker("en_US")
    assert breaker.break_lines(text) == expected
    assert list(breaker.iter_lines(text)) == expected

