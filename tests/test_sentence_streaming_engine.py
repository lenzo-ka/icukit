"""Equivalence and scaling checks for the shared sentence streaming core."""

from __future__ import annotations

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


def test_unbroken_run_is_the_documented_safe_retention_fallback():
    text = "a" * (sentence_override_module._STREAM_WINDOW * 2)
    override = SentenceOverride(base="none")
    stream = override.stream()

    emitted = stream.feed(text)

    assert emitted == []
    assert stream._text == text
    assert emitted + stream.close() == override.decide(text)


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
