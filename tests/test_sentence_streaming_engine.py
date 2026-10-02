"""Equivalence and scaling checks for the shared sentence streaming core."""

from __future__ import annotations

import importlib
import random
from pathlib import Path

import pytest

import icukit.sentence_override as sentence_override_module
from icukit import SentenceOverride


def _random_chunks(text: str, seed: int) -> list[str]:
    rng = random.Random(seed)
    points = sorted(rng.randrange(len(text) + 1) for _ in range(80))
    boundaries = [0, *points, len(text)]
    return [text[start:end] for start, end in zip(boundaries, boundaries[1:], strict=False)]


@pytest.mark.parametrize("base", ["none", "en-tn@1", "en-tn-cart@1"])
def test_repo_text_random_chunkings_equal_whole_text(base):
    source = Path(__file__).with_name("test_sentence_override_incremental.py").read_text()
    text = source[:8192]
    override = SentenceOverride(base=base)
    expected = override.decide(text)

    stream = override.stream()
    actual = []
    for chunk in _random_chunks(text, 93017):
        actual.extend(stream.feed(chunk))
    actual.extend(stream.close())

    assert actual == expected


def test_retained_window_and_reprocessed_work_scale_linearly(monkeypatch):
    original = sentence_override_module._raw_break_sentence_spans

    def measure(size):
        work = 0

        def counted(text, locale):
            nonlocal work
            work += len(text)
            return original(text, locale)

        monkeypatch.setattr(sentence_override_module, "_raw_break_sentence_spans", counted)
        text = ("Alpha beta. Gamma delta! " * (size // 25 + 1))[:size]
        stream = SentenceOverride(base="none").stream()
        maximum = 0
        for start in range(0, len(text), 1024):
            stream.feed(text[start : start + 1024])
            maximum = max(maximum, len(stream._text))
        stream.close()
        return work, maximum

    small_work, small_maximum = measure(64 * 1024)
    large_work, large_maximum = measure(256 * 1024)

    assert large_work <= small_work * 5
    assert small_maximum <= sentence_override_module._STREAM_WINDOW
    assert large_maximum <= sentence_override_module._STREAM_WINDOW


def test_default_whole_text_inventory_work_scales_with_text(monkeypatch):
    override = SentenceOverride("en")
    original_build = sentence_override_module._TextLocalityIndex.build.__func__
    original_rules = sentence_override_module._inventory_rules
    original_words = sentence_override_module.break_word_spans
    work = {"indexed": 0, "rule_filters": 0, "word_tokenization": 0}

    def counted_build(cls, text, *args, **kwargs):
        work["indexed"] += len(text)
        return original_build(cls, text, *args, **kwargs)

    def counted_rules(*args, **kwargs):
        work["rule_filters"] += 1
        return original_rules(*args, **kwargs)

    def counted_words(text, *args, **kwargs):
        work["word_tokenization"] += len(text)
        return original_words(text, *args, **kwargs)

    monkeypatch.setattr(
        sentence_override_module._TextLocalityIndex, "build", classmethod(counted_build)
    )
    monkeypatch.setattr(sentence_override_module, "_inventory_rules", counted_rules)
    monkeypatch.setattr(sentence_override_module, "break_word_spans", counted_words)

    def measure(size):
        work.update(indexed=0, rule_filters=0, word_tokenization=0)
        text = ("Alpha beta. Gamma delta! " * (size // 25 + 1))[:size]
        override.decide(text)
        return dict(work)

    small = measure(64 * 1024 + 1)
    large = measure(256 * 1024 + 1)

    assert large["indexed"] <= small["indexed"] * 5
    assert small["rule_filters"] == large["rule_filters"] == 0
    assert small["word_tokenization"] == large["word_tokenization"] == 0


def test_unbroken_run_is_the_documented_safe_retention_fallback():
    text = "a" * (sentence_override_module._STREAM_WINDOW * 2)
    override = SentenceOverride(base="none")
    stream = override.stream()

    emitted = stream.feed(text)

    assert emitted == []
    assert stream._text == text
    assert emitted + stream.close() == override.decide(text)


@pytest.mark.parametrize("base", ["none", "en-tn@1", "en-tn-cart@1"])
@pytest.mark.parametrize("unit", ["Hello!World!", "你好。世界！"])
def test_whitespace_free_runs_have_bounded_retention_and_linear_icu_work(monkeypatch, base, unit):
    tokens_module = importlib.import_module("icukit.tokens")
    original_sentences = sentence_override_module._raw_break_sentence_spans
    original_words = tokens_module._raw_break_word_extents
    work = 0
    maximum_icu_input = 0

    def counted_sentences(text, locale):
        nonlocal maximum_icu_input, work
        work += len(text)
        maximum_icu_input = max(maximum_icu_input, len(text))
        return original_sentences(text, locale)

    def counted_words(text, locale):
        nonlocal maximum_icu_input, work
        work += len(text)
        maximum_icu_input = max(maximum_icu_input, len(text))
        return original_words(text, locale)

    monkeypatch.setattr(sentence_override_module, "_raw_break_sentence_spans", counted_sentences)
    monkeypatch.setattr(tokens_module, "_raw_break_word_extents", counted_words)

    def measure(repetitions):
        nonlocal maximum_icu_input, work
        text = unit * repetitions
        work = maximum_icu_input = 0
        expected = SentenceOverride(base=base).decide(text)
        whole_work, whole_maximum = work, maximum_icu_input
        work = maximum_icu_input = 0
        stream = SentenceOverride(base=base).stream()
        actual = []
        maximum = 0
        for start in range(0, len(text), 64):
            actual.extend(stream.feed(text[start : start + 64]))
            maximum = max(maximum, len(stream._text))
        actual.extend(stream.close())
        assert actual == expected
        return whole_work, whole_maximum, work, maximum

    small_whole_work, small_whole_maximum, small_work, small_maximum = measure(128)
    large_whole_work, large_whole_maximum, large_work, large_maximum = measure(256)

    assert small_whole_maximum <= sentence_override_module._RUN_WINDOW * 2
    assert large_whole_maximum <= sentence_override_module._RUN_WINDOW * 2
    assert large_whole_work <= small_whole_work * 3
    assert small_maximum <= sentence_override_module._RUN_WINDOW
    assert large_maximum <= sentence_override_module._RUN_WINDOW
    assert large_work <= small_work * 3


@pytest.mark.parametrize("separator", ["\n\n", "\r\n", "\u2029"])
def test_hard_break_is_a_bounded_restart_point(separator):
    paragraph = "Alpha beta. Gamma delta! " * 12
    text = separator.join(paragraph for _ in range(40))
    override = SentenceOverride(base="en-tn-cart@1")
    stream = override.stream()
    actual = []
    maximum = 0

    for start in range(0, len(text), 1024):
        actual.extend(stream.feed(text[start : start + 1024]))
        maximum = max(maximum, len(stream._text))
    actual.extend(stream.close())

    assert actual == override.decide(text)
    assert maximum <= sentence_override_module._STREAM_WINDOW


def test_large_whole_text_with_protection_stays_windowed(monkeypatch):
    original = sentence_override_module._raw_break_sentence_spans
    observed_lengths = []

    def measured(text, locale):
        observed_lengths.append(len(text))
        return original(text, locale)

    monkeypatch.setattr(sentence_override_module, "_raw_break_sentence_spans", measured)
    paragraph = "Alpha beta. Gamma delta! " * 100
    text = (paragraph + "\n\n") * 100
    start = sentence_override_module._WHOLE_WINDOW - 8
    protected = [{"start": start, "end": start + 32, "type": "cross-window"}]

    decisions = SentenceOverride(base="none").decide(text, protected=protected)

    assert decisions
    assert max(observed_lengths) <= (
        sentence_override_module._WHOLE_WINDOW
        + sentence_override_module._STREAM_WINDOW
        + len(text[start : start + 32])
    )
