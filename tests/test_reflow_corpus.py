"""Optional full-corpus round trip for original reflow offsets."""

import os
from pathlib import Path

import pytest

from icukit import Breaker, SentenceOverride
from icukit.reflow import _substitute


def _assert_original_offsets(text, spans):
    assert spans[0]["start"] == 0
    assert spans[-1]["end"] == len(text)
    assert all(left["end"] == right["start"] for left, right in zip(spans, spans[1:], strict=False))
    utf8 = text.encode("utf-8")
    utf16 = text.encode("utf-16-le")
    for span in spans:
        assert span["text"] == text[span["start"] : span["end"]]
        assert utf8[span["utf8_start"] : span["utf8_end"]] == span["text"].encode()
        assert utf16[2 * span["utf16_start"] : 2 * span["utf16_end"]] == span["text"].encode(
            "utf-16-le"
        )


def _stream_decisions(text, mode):
    stream = SentenceOverride("en_US", reflow=mode).stream()
    result = []
    for start in range(0, len(text), 997):
        result.extend(stream.feed(text[start : start + 997]))
    result.extend(stream.close())
    return result


def _assert_corpus(text):
    for mode in ("none", "lines", "paragraphs", "auto"):
        substituted = _substitute(text, mode)
        spans = Breaker("en_US", reflow=mode).break_sentence_spans(text)
        expected = Breaker("en_US").break_sentence_spans(substituted)

        assert len(substituted) == len(text)
        assert [(item["start"], item["end"]) for item in spans] == [
            (item["start"], item["end"]) for item in expected
        ]
        assert _stream_decisions(text, mode) == SentenceOverride("en_US", reflow=mode).decide(text)
        _assert_original_offsets(text, spans)


def test_reflow_round_trip_excerpt():
    text = (Path(__file__).with_name("data") / "pg11_excerpt.txt").read_text()

    _assert_corpus(text)


def test_reflow_round_trip_pg11():  # S
    configured = os.environ.get("ICUKIT_PG11")
    if not configured:
        if os.environ.get("ICUKIT_REQUIRE_PG11") == "1":
            pytest.fail("ICUKIT_PG11 is required when ICUKIT_REQUIRE_PG11=1")
        pytest.skip("set ICUKIT_PG11 to run the full-corpus reflow round trip")
    path = Path(configured)
    if not path.is_file():
        if os.environ.get("ICUKIT_REQUIRE_PG11") == "1":
            pytest.fail("ICUKIT_PG11 does not name a readable file")
        pytest.skip("ICUKIT_PG11 does not name a readable file")
    text = path.read_text()

    _assert_corpus(text)
