"""Forced maximum-length sentence breaks."""

import pytest

from icukit import Breaker, SentenceOverride, break_sentence_spans, break_sentences


def _bounds(spans):
    return [(span["start"], span["end"]) for span in spans]


def test_forced_break_default_1024():  # R
    spans = Breaker("en_US").break_sentence_spans("word " * 400)

    assert max(span["end"] - span["start"] for span in spans) <= 1024


def test_forced_break_hard_cut():  # R
    assert _bounds(Breaker("en_US").break_sentence_spans("a" * 3000)) == [
        (0, 1024),
        (1024, 2048),
        (2048, 3000),
    ]


def test_forced_break_grapheme():  # R
    spans = Breaker("en_US").break_sentence_spans("e\N{COMBINING ACUTE ACCENT}" * 1500)

    assert len(spans) >= 2
    assert max(span["end"] - span["start"] for span in spans) <= 1024
    assert all(span["end"] % 2 == 0 for span in spans[:-1])


def test_forced_break_clause_over_whitespace():  # R
    text = "a" * 699 + ", " + "word " * 200
    first = Breaker("en_US").break_sentence_spans(text)[0]

    assert first["end"] == 701


@pytest.mark.parametrize(("locale", "character"), [("ja_JP", "日"), ("th_TH", "ก")])
def test_forced_break_cjk(locale, character):  # R
    spans = Breaker(locale).break_sentence_spans(character * 1500)

    assert len(spans) >= 2
    assert max(span["end"] - span["start"] for span in spans) <= 1024


def test_forced_break_raw_ss_path():  # R
    assert _bounds(Breaker("en_US@ss=standard", base="none").break_sentence_spans("a" * 3000)) == [
        (0, 1024),
        (1024, 2048),
        (2048, 3000),
    ]


def test_forced_in_segmentations_boundaries():  # R
    segmentation = SentenceOverride("en_US", max_sentence_chars=10).segmentations("a" * 25)

    assert _bounds(segmentation["spans"]) == [(0, 10), (10, 20), (20, 25)]
    assert [item["id"] for item in segmentation["boundaries"]] == [
        "max-sentence-chars:grapheme",
        "max-sentence-chars:grapheme",
    ]


def test_forced_offsets_absolute_across_feeds():  # R
    text = "a" * 80
    stream = SentenceOverride("en_US", max_sentence_chars=16).stream()
    decisions = []
    for character in text:
        decisions.extend(stream.feed(character))
    decisions.extend(stream.close())

    assert [item["offset"] for item in decisions if item["layer"] == "forced"] == [
        16,
        32,
        48,
        64,
    ]


def test_pending_no_break_is_resolved_by_bounded_slice():  # R
    override = SentenceOverride("en_US", max_sentence_chars=16)
    stream = override.stream()

    assert stream.feed("Mr. Smith ") == []
    emitted = stream.feed("x" * 20)

    assert emitted == override.decide("Mr. Smith " + "x" * 20)[:-1]
    assert emitted[0]["decision"] == "no-break"
    assert emitted[1]["id"] == "max-sentence-chars:whitespace"


def test_forced_protected_span_bound():  # R
    text = "a" * 10_000
    protected = [{"start": 0, "end": len(text), "type": "name"}]

    assert SentenceOverride("en_US").decide(text, protected=protected)[0]["offset"] == 1024


def test_forced_stream_equals_whole():  # C
    text = "a" * 1500
    override = SentenceOverride("en_US")
    expected = override.decide(text)

    for cut in range(len(text) + 1):
        stream = override.stream()
        assert stream.feed(text[:cut]) + stream.feed(text[cut:]) + stream.close() == expected


def test_sentence_under_bound_unbroken():  # C
    text = "This sentence stays below the configured bound."

    assert break_sentences(text) == [text]


def test_forced_decision_literal():  # S
    assert SentenceOverride("en_US", max_sentence_chars=30).decide(
        "one two three, four five six seven eight nine ten."
    ) == [
        {
            "offset": 15,
            "end": 14,
            "decision": "break",
            "alternatives": ("break", "no-break"),
            "layer": "forced",
            "id": "max-sentence-chars:clause",
            "tokens_read": 0,
        },
        {
            "offset": 41,
            "end": 40,
            "decision": "break",
            "alternatives": ("break", "no-break"),
            "layer": "forced",
            "id": "max-sentence-chars:whitespace",
            "tokens_read": 0,
        },
        {
            "offset": 50,
            "end": 50,
            "decision": "break",
            "alternatives": ("break",),
            "layer": "icu",
            "id": None,
            "tokens_read": 0,
        },
    ]


def test_max_sentence_chars_none():  # S
    text = "a" * 3000

    assert _bounds(break_sentence_spans(text, max_sentence_chars=None)) == [(0, 3000)]


def test_codepoint_tier():  # S
    text = "e" + "\N{COMBINING ACUTE ACCENT}" * 40
    first = SentenceOverride("en_US", max_sentence_chars=10).decide(text)[0]

    assert (first["offset"], first["id"]) == (10, "max-sentence-chars:codepoint")


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "10"])
def test_max_sentence_chars_validation(value):  # S
    with pytest.raises(ValueError, match="max_sentence_chars must be a positive int or None"):
        SentenceOverride("en_US", max_sentence_chars=value)
