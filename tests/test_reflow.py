"""Reflow policy, offset preservation, and sentence-stream composition."""

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

from icukit import Breaker, SentenceOverride, break_sentence_spans, break_sentences, reflow
from icukit.reflow import _substitute


def _long(text: str) -> str:
    return text + " with enough additional words to exceed the short-line protection threshold"


def test_hard_wrap_fake_sentences_today():  # C
    text = (
        _long("The first part of this sentence has no terminal punctuation") + "\ncontinues here."
    )

    assert len(Breaker("en_US").break_sentence_spans(text)) == 2
    assert len(Breaker("en_US", reflow="lines").break_sentence_spans(text)) == 1


def test_reflow_none_is_identity():  # C
    text = _long("One hard-wrapped sentence") + "\ncontinues here. Next."

    assert Breaker("en_US").break_sentence_spans(text) == Breaker(
        "en_US", reflow="none"
    ).break_sentence_spans(text)
    assert break_sentences(text) == break_sentences(text, reflow="none")
    assert break_sentence_spans(text) == break_sentence_spans(text, reflow="none")
    assert SentenceOverride("en_US").decide(text) == SentenceOverride(
        "en_US", reflow="none"
    ).decide(text)
    assert reflow(text, "none") == text


def test_reflow_raw_icu_sentence_path():
    text = _long("One hard-wrapped raw ICU sentence") + "\ncontinues here."

    assert len(Breaker("en_US@ss=standard", base="none").break_sentence_spans(text)) == 2
    assert (
        len(Breaker("en_US@ss=standard", base="none", reflow="lines").break_sentence_spans(text))
        == 1
    )


def test_reflow_mode_validation():
    message = "reflow must be one of 'none', 'lines', 'paragraphs', 'auto'"

    with pytest.raises(ValueError, match=message):
        reflow("text", "invalid")
    with pytest.raises(ValueError, match=message):
        Breaker("en_US", reflow="invalid")
    with pytest.raises(ValueError, match=message):
        SentenceOverride("en_US", reflow="invalid")


def test_no_keep_offsets_parameter():  # C
    callables = (reflow, Breaker, SentenceOverride, break_sentences, break_sentence_spans)
    assert all("keep_offsets" not in inspect.signature(item).parameters for item in callables)


def test_substitute_rule_conforming_literal():  # S
    first = "It was the very best of all imaginable and memorable times"
    text = first + "\nbest of times.\n\nIt was"

    assert _substitute(text, "lines") == first + " best of times.\n\nIt was"


def test_crlf_two_spaces():  # S
    first = _long("This sentence continues after a Windows line ending")
    assert _substitute(first + "\r\ncontinues.", "lines") == first + "  continues."


def test_u2029_kept():  # S
    text = _long("This block ends at a paragraph separator") + "\u2029continues."
    assert "\u2029" in _substitute(text, "paragraphs")


def test_vt_ff_untouched():  # S
    text = _long("This line includes untouched controls") + "\vnext\fform"
    assert _substitute(text, "lines") == text


def test_reflow_contract():  # S
    first = "It was the very best of all imaginable and memorable times"
    text = first + "\nbest of times.\n\nIt was"

    assert reflow(text) == first + " best of times.\n\nIt was"
    assert len(reflow(text)) == len(text)


def test_reflow_protections():  # S
    long_previous = _long("This preceding line would ordinarily reflow")
    fixtures = [
        long_previous + "\n- a list item",
        long_previous + "\nALL CAPS HEADING",
        long_previous + "\n  indented verse",
        "How doth the little crocodile\n    Improve his shining tail,\n"
        "And pour the waters of the Nile\n    On every golden scale!",
        "12 High Street\nSpringfield, IL 62704\nUSA\n\n",
        _long("When winter winds arise across the silent and unbounded sea")
        + "\n"
        + _long("Bright lanterns answer softly from the distant harbor wall")
        + "\n"
        + _long("Cold travelers remember every road that led them home")
        + "\n"
        + _long("Warm morning gathers slowly over every field and stone"),
    ]
    for text in fixtures:
        assert "\n" in _substitute(text, "lines")
        assert reflow(text, "lines") == _substitute(text, "lines")

    joining = _long("this unfinished block has no terminal punctuation") + "\n\nlower continues"
    protected = _long("this unfinished block has no terminal punctuation") + "\n\nUpper continues"
    assert "\n" not in _substitute(joining, "paragraphs")
    assert "\n\n" in _substitute(protected, "paragraphs")


def test_pg11_excerpt_exercises_prose_and_verse():  # S
    text = (Path(__file__).with_name("data") / "pg11_excerpt.txt").read_text()
    substituted = _substitute(text, "lines")

    assert "sister on the bank," in substituted
    assert "How doth the little crocodile\n    Improve his shining tail," in substituted


def test_reflow_spans_keep_original_unicode_offsets():  # S
    first = _long("A smiling face 😀 begins this hard-wrapped sentence")
    text = first + "\u2028continues with café."
    spans = Breaker("en_US", reflow="lines").break_sentence_spans(text)

    assert len(spans) == 1
    assert spans[0]["text"] == text
    assert spans[0]["utf8_end"] == len(text.encode())
    assert spans[0]["utf16_end"] == len(text.encode("utf-16-le")) // 2


def test_reflow_hold_bound():  # S
    assert "\n" in _substitute("a\n" + " " * 5000 + "b", "lines")

    text = "a\n" + "b" * 100_000
    stream = SentenceOverride("en_US", reflow="auto").stream()
    emitted = []
    first_decision_length = None
    for start in range(0, len(text), 1024):
        emitted.extend(stream.feed(text[start : start + 1024]))
        if first_decision_length is None and emitted:
            first_decision_length = min(start + 1024, len(text))
    emitted.extend(stream.close())

    assert first_decision_length is not None
    assert first_decision_length <= 2048
    assert emitted == SentenceOverride("en_US", reflow="auto").decide(text)


def test_reflow_forced_composition():  # S
    text = "a" * 1022 + "\n\n" + " " * 1000 + "b" + "c" * 3000
    override = SentenceOverride("en_US", reflow="paragraphs", max_sentence_chars=1024)
    stream = override.stream()
    emitted = []
    first_forced_seen = None
    for length, character in enumerate(text, 1):
        emitted.extend(stream.feed(character))
        if first_forced_seen is None and any(item["layer"] == "forced" for item in emitted):
            first_forced_seen = length
    emitted.extend(stream.close())

    assert first_forced_seen is not None and first_forced_seen <= 2048
    assert emitted == override.decide(text)
    offsets = [0, *(item["offset"] for item in emitted if item["decision"] == "break")]
    assert all(end - start <= 1024 for start, end in zip(offsets, offsets[1:], strict=False))


@pytest.mark.parametrize("mode", ["lines", "paragraphs", "auto"])
@pytest.mark.parametrize("chunk_size", [1, 7, 1024])
def test_reflow_stream_equals_whole(mode, chunk_size):  # S
    text = (
        _long("This unfinished hard-wrapped line continues")
        + "\non the next line.\n\n"
        + _long("this unfinished block")
        + "\n\nlower continuation."
    )
    override = SentenceOverride("en_US", reflow=mode, max_sentence_chars=64)
    stream = override.stream()
    emitted = []
    for start in range(0, len(text), chunk_size):
        emitted.extend(stream.feed(text[start : start + chunk_size]))
    emitted.extend(stream.close())

    assert emitted == override.decide(text)


@pytest.mark.parametrize("mode", ["lines", "paragraphs", "auto"])
def test_reflow_stream_crlf_equals_whole(mode):
    text = _long("This unfinished hard-wrapped line continues") + "\r\non this line.\r\n\r\nNext."
    override = SentenceOverride("en_US", reflow=mode)
    stream = override.stream()
    emitted = []
    for character in text:
        emitted.extend(stream.feed(character))
    emitted.extend(stream.close())

    assert emitted == override.decide(text)


def test_reflow_pending_crlf_offset_is_after_the_pair():
    first = _long("This unfinished hard-wrapped line continues")
    stream = SentenceOverride("en_US", reflow="lines").stream()

    stream.feed(first + "\r\n")

    assert any(
        item["waiting_on"] == "reflow" and item["offset"] == len(first) + 2
        for item in stream.pending()
    )


def test_cli_reflow_bare_is_lines():  # S
    text = _long("This unfinished hard-wrapped sentence continues") + "\non this line."
    command = [
        sys.executable,
        "-m",
        "icukit.cli",
        "break",
        "sentences",
        "--json",
        "-t",
        text,
    ]
    plain = subprocess.run(command, check=True, capture_output=True, text=True)
    bare = subprocess.run(
        [*command[:-3], "--reflow", *command[-3:]], check=True, capture_output=True, text=True
    )
    explicit = subprocess.run(
        [*command[:-3], "--reflow", "lines", *command[-3:]],
        check=True,
        capture_output=True,
        text=True,
    )

    assert len(json.loads(plain.stdout)) == 2
    assert json.loads(bare.stdout) == json.loads(explicit.stdout)
    assert len(json.loads(bare.stdout)) == 1
