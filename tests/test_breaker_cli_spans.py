"""CLI coverage for structured break spans."""

import json
import subprocess
import sys

import pytest

from icukit import Breaker

SOURCE = "Hi é中 👨‍👩‍👧‍👦 world. Next line!"
SPAN_FIELDS = {
    "text",
    "start",
    "end",
    "codepoint_start",
    "codepoint_end",
    "utf8_start",
    "utf8_end",
    "utf16_start",
    "utf16_end",
    "types",
    "statuses",
}


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "icukit.cli", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def assert_offsets(spans, text=SOURCE):
    utf8 = text.encode("utf-8")
    utf16 = text.encode("utf-16-le")
    for span in spans:
        segment = span["text"]
        assert text[span["start"] : span["end"]] == segment
        assert text[span["codepoint_start"] : span["codepoint_end"]] == segment
        assert utf8[span["utf8_start"] : span["utf8_end"]] == segment.encode("utf-8")
        assert utf16[2 * span["utf16_start"] : 2 * span["utf16_end"]] == segment.encode("utf-16-le")
        assert (span["start"], span["end"]) == (
            span["codepoint_start"],
            span["codepoint_end"],
        )


@pytest.mark.parametrize(
    ("mode", "legacy"),
    [
        ("words", ["Dr", ".", "Smith"]),
        ("lines", ["Dr. ", "Smith"]),
        (
            "graphemes",
            [
                {"grapheme": "A", "codepoints": "U+0041", "length": 1},
                {"grapheme": "B", "codepoints": "U+0042", "length": 1},
            ],
        ),
        ("tokenize", [["Hi", "."], ["Bye", "."]]),
    ],
)
def test_legacy_json_shapes_are_unchanged_and_spans_are_additive(mode, legacy):
    text = "AB" if mode == "graphemes" else "Hi. Bye." if mode == "tokenize" else "Dr. Smith"
    code, out, err = run_cli("break", mode, "--json", "-t", text)
    assert (code, err, json.loads(out)) == (0, "", legacy)

    code, _out, _err = run_cli("break", mode, "--spans", "--json", "-t", text)
    assert code == 0


@pytest.mark.parametrize("mode", ["sentences", "words", "lines", "graphemes"])
def test_flat_span_json_has_integral_codepoint_offsets_and_mode_metadata(mode):
    code, out, err = run_cli("break", mode, "--spans", "--json", "-t", SOURCE)
    assert (code, err) == (0, "")
    spans = json.loads(out)
    assert_offsets(spans)
    assert all(SPAN_FIELDS <= span.keys() for span in spans)
    assert all(("break_type" in span) == (mode == "lines") for span in spans)


def test_sentence_spans_retain_trailing_whitespace_while_plain_json_strips_it():
    text = "One. Two."
    code, plain, err = run_cli("break", "sentences", "--json", "-t", text)
    assert (code, err, json.loads(plain)) == (0, "", ["One.", "Two."])

    code, out, err = run_cli("break", "sentences", "--spans", "--json", "-t", text)
    spans = json.loads(out)
    assert (code, err) == (0, "")
    assert spans[0]["text"] == "One. "


def test_word_span_filters_match_legacy_word_filters():
    text = "Hi, there"
    breaker = Breaker("en")
    spans = breaker.break_word_spans(text, skip_whitespace=True, skip_punctuation=True)
    assert [span["text"] for span in spans] == breaker.break_words(
        text, skip_whitespace=True, skip_punctuation=True
    )

    code, out, err = run_cli(
        "break", "words", "--spans", "--json", "--skip-punctuation", "-t", text
    )
    assert (code, err) == (0, "")
    assert [span["text"] for span in json.loads(out)] == ["Hi", "there"]


def test_tokenize_spans_preserve_nesting_offsets_filters_and_metadata():
    code, out, err = run_cli(
        "break", "tokenize", "--spans", "--json", "--skip-punctuation", "-t", SOURCE
    )
    assert (code, err) == (0, "")
    sentences = json.loads(out)
    assert len(sentences) == 2
    assert [[span["text"] for span in sentence] for sentence in sentences] == [
        ["Hi", "é", "中", "👨‍👩‍👧‍👦", "world"],
        ["Next", "line"],
    ]
    for sentence in sentences:
        assert_offsets(sentence)
        assert all("break_type" not in span for span in sentence)


@pytest.mark.parametrize("mode", ["sentences", "words", "lines", "graphemes", "tokenize"])
def test_span_tables_have_headers_and_honor_no_header(mode):
    code, out, err = run_cli("break", mode, "--spans", "-t", "One. Two.")
    assert (code, err) == (0, "")
    expected = (
        "sentence\ttext\tcodepoint_start"
        if mode == "tokenize"
        else "text\tcodepoint_start\tcodepoint_end"
    )
    assert out.startswith(expected)

    code, out, err = run_cli("break", mode, "--spans", "--no-header", "-t", "One. Two.")
    assert (code, err) == (0, "")
    assert not out.startswith(expected)


def test_grapheme_spans_and_show_codepoints_are_mutually_exclusive():
    code, _out, err = run_cli("break", "graphemes", "--spans", "--show-codepoints", "-t", "AB")
    assert code == 2
    assert "not allowed with argument" in err


def test_plain_and_json_words_match_for_file_with_exotic_separators(tmp_path):
    path = tmp_path / "separators.txt"
    path.write_text("one\u2028two\fthree\r\nfour\x85five", encoding="utf-8")

    code, structured, err = run_cli("break", "words", "--json", "--include-whitespace", str(path))
    assert (code, err) == (0, "")
    tokens = json.loads(structured)
    plain = subprocess.run(
        [
            sys.executable,
            "-m",
            "icukit.cli",
            "break",
            "words",
            "--include-whitespace",
            str(path),
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    assert (plain.returncode, plain.stderr) == (0, b"")
    assert plain.stdout == "".join(f"{token}\n" for token in tokens).encode("utf-8")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", []), ("aa", ["aa"]), ("aa bb", ["aa", "bb"])],
)
def test_break_json_is_always_a_list(text, expected):
    code, out, err = run_cli("break", "words", "--json", "-t", text)
    assert (code, err, json.loads(out)) == (0, "", expected)


def test_single_span_json_is_a_list_of_one_object():
    code, out, err = run_cli("break", "words", "--spans", "--json", "-t", "aa")
    assert (code, err) == (0, "")
    spans = json.loads(out)
    assert isinstance(spans, list)
    assert len(spans) == 1
    assert spans[0]["text"] == "aa"
