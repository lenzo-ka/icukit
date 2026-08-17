"""Tests for typed segmentation spans."""

import json

import pytest

from icukit import (
    Breaker,
    break_grapheme_spans,
    break_line_spans,
    break_sentence_spans,
    break_word_spans,
)


@pytest.mark.parametrize(
    ("text", "offsets"),
    [
        ("a\U0001f44db", [(0, 1), (1, 2), (2, 3)]),
        ("e\u0301", [(0, 2)]),
        ("\U0001f468\u200d\U0001f469", [(0, 3)]),
        ("\U0001f1fa\U0001f1f8", [(0, 2)]),
    ],
)
def test_grapheme_offsets_are_code_points(text, offsets):
    spans = break_grapheme_spans(text, "en")
    assert [(span["start"], span["end"]) for span in spans] == offsets


@pytest.mark.parametrize(
    "method_name",
    [
        "break_word_spans",
        "break_sentence_spans",
        "break_line_spans",
        "break_grapheme_spans",
    ],
)
def test_spans_tile_source_and_empty_input(method_name):
    method = getattr(Breaker("en"), method_name)
    text = "Hi, 世界.\nNext\U0001f600"
    spans = method(text)
    assert "".join(span["text"] for span in spans) == text
    assert [(span["start"], span["end"]) for span in spans] == [
        (spans[i - 1]["end"] if i else 0, span["end"])
        for i, span in enumerate(spans)
    ]
    assert spans[-1]["end"] == len(text)
    assert method("") == []


@pytest.mark.parametrize(
    ("stem", "module_function"),
    [
        ("word", break_word_spans),
        ("sentence", break_sentence_spans),
        ("line", break_line_spans),
        ("grapheme", break_grapheme_spans),
    ],
)
def test_iter_list_and_module_forms_agree(stem, module_function):
    text = "Hello, 世界."
    breaker = Breaker("en")
    expected = getattr(breaker, f"break_{stem}_spans")(text)
    assert list(getattr(breaker, f"iter_{stem}_spans")(text)) == expected
    assert module_function(text, "en") == expected


def test_word_none_refinements_and_legacy_skip_filters():
    breaker = Breaker("en")
    spans = breaker.break_word_spans("a\xa0,\U0001f600")
    by_text = {span["text"]: span for span in spans}
    assert by_text["\xa0"]["types"] == ["whitespace"]
    assert by_text[","]["types"] == ["punctuation"]
    assert by_text["\U0001f600"]["types"] == ["other"]
    assert breaker.break_words("a\xa0b", skip_whitespace=True) == ["a", "b"]
    assert breaker.break_words("a\xa0b", skip_whitespace=False) == ["a", "\xa0", "b"]
    assert breaker.break_words("a,b", skip_punctuation=True) == ["a", "b"]
    assert breaker.break_words("a,b", skip_punctuation=False) == ["a", ",", "b"]


def test_real_icu_word_status_ranges():
    spans = break_word_spans("5 The 世界", "en")
    lexical = {span["text"]: span for span in spans if span["text"].strip()}
    assert lexical["5"]["types"] == ["number"]
    assert lexical["The"]["types"] == ["letter"]
    assert lexical["世界"]["types"] == ["ideo"]
    assert lexical["5"]["statuses"] == [100]
    assert lexical["The"]["statuses"] == [200]
    assert lexical["世界"]["statuses"] == [400]
    assert Breaker("en").break_words("世界", True, True) == ["世界"]


def test_line_break_strength_and_crlf_boundary():
    spans = break_line_spans("a b\nc", "en")
    assert [(span["text"], span["break_type"]) for span in spans] == [
        ("a ", "optional"),
        ("b\n", "mandatory"),
        ("c", "optional"),
    ]
    crlf = break_line_spans("a\r\nb", "en")
    assert crlf[0]["text"] == "a\r\n"
    assert (crlf[0]["start"], crlf[0]["end"]) == (0, 3)
    assert crlf[0]["break_type"] == "mandatory"
    assert crlf[0]["statuses"] == [100]


def test_sentence_and_grapheme_metadata_is_empty():
    for span in break_sentence_spans("Hello.", "en") + break_grapheme_spans("é", "en"):
        assert span["types"] == []
        assert span["statuses"] == []
        assert "break_type" not in span


def test_spans_are_json_round_trip_safe():
    spans = break_word_spans("5 世界 a\xa0b.", "en")
    assert json.loads(json.dumps(spans)) == spans
