"""End-to-end tests for line-delimited JSON break output."""

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import icu
import pytest

import icukit

ROOT = Path(__file__).parents[1]
MODES = ("sentences", "words", "lines", "graphemes", "tokenize")
TEXT = "Hi 😀 there. Bye 😀!"


def run_break(mode, *args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", "break", mode, *args],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def parse_jsonl(output):
    assert output.endswith("\n")
    records = [json.loads(line) for line in output.splitlines()]
    assert records
    assert all(isinstance(record, dict) for record in records)
    if len(records) > 1:
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)
    return records


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("spans", [False, True])
def test_jsonl_all_modes_shapes_and_provenance(mode, spans):
    options = ["--jsonl", "-t", TEXT]
    if spans:
        options.insert(1, "--spans")
    plain_result = run_break(mode, *options)
    stamped_result = run_break(mode, *options, "--provenance")
    assert (plain_result.returncode, plain_result.stderr) == (0, "")
    assert (stamped_result.returncode, stamped_result.stderr) == (0, "")
    plain = parse_jsonl(plain_result.stdout)
    stamped = parse_jsonl(stamped_result.stdout)

    expected_provenance = {
        "icu_version": icu.ICU_VERSION,
        "unicode_version": icu.UNICODE_VERSION,
        "pyicu_version": icu.VERSION,
        "icukit_version": icukit.__version__,
    }
    assert [record.pop("provenance") for record in stamped] == [expected_provenance] * len(stamped)
    assert stamped == plain


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "extra", [(), ("--spans",), ("--provenance",), ("--spans", "--provenance")]
)
def test_jsonl_output_file_matches_stdout(mode, extra, tmp_path):
    expected = run_break(mode, "--jsonl", *extra, "-t", TEXT)
    destination = tmp_path / f"{mode}.jsonl"
    actual = run_break(mode, "--jsonl", *extra, "-t", TEXT, "-o", str(destination))
    assert (expected.returncode, expected.stderr) == (0, "")
    assert (actual.returncode, actual.stdout, actual.stderr) == (0, "", "")
    assert destination.read_text(encoding="utf-8") == expected.stdout
    parse_jsonl(destination.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mode", ("sentences", "words", "lines", "graphemes"))
@pytest.mark.parametrize("spans", [False, True])
def test_jsonl_records_carry_the_same_data_as_json(mode, spans):
    """Each JSONL line holds exactly what --json puts in the corresponding array item."""
    options = ["--spans", "-t", TEXT] if spans else ["-t", TEXT]
    records = parse_jsonl(run_break(mode, "--jsonl", *options).stdout)
    document = json.loads(run_break(mode, "--json", *options).stdout)
    if spans or mode == "graphemes":
        assert records == document
    else:
        assert [record["text"] for record in records] == document
        assert all(list(record) == ["text"] for record in records)


@pytest.mark.parametrize("mode", MODES)
def test_jsonl_span_offsets_round_trip_in_all_coordinate_spaces(mode):
    result = run_break(mode, "--jsonl", "--spans", "-t", TEXT)
    assert (result.returncode, result.stderr) == (0, "")
    records = parse_jsonl(result.stdout)
    for record in records:
        assert TEXT[record["codepoint_start"] : record["codepoint_end"]] == record["text"]
        assert (
            TEXT.encode("utf-8")[record["utf8_start"] : record["utf8_end"]].decode("utf-8")
            == record["text"]
        )
        assert (
            TEXT.encode("utf-16-le")[record["utf16_start"] * 2 : record["utf16_end"] * 2].decode(
                "utf-16-le"
            )
            == record["text"]
        )

    emoji = next(record for record in records if "😀" in record["text"])
    lengths = (
        emoji["utf8_end"] - emoji["utf8_start"],
        emoji["utf16_end"] - emoji["utf16_start"],
        emoji["codepoint_end"] - emoji["codepoint_start"],
    )
    if mode == "graphemes":
        assert lengths == (4, 2, 1)
    else:
        assert lengths[0] > lengths[1] > lengths[2]


@pytest.mark.parametrize("spans", [False, True])
def test_tokenize_jsonl_sentence_groups_reproduce_json(spans):
    options = ["--spans"] if spans else []
    line_result = run_break("tokenize", "--jsonl", *options, "-t", TEXT)
    json_result = run_break("tokenize", "--json", *options, "-t", TEXT)
    records = parse_jsonl(line_result.stdout)
    numbers = [record["sentence"] for record in records]
    assert numbers == sorted(numbers)
    assert numbers[0] == 1

    grouped = defaultdict(list)
    for record in records:
        sentence = record.pop("sentence")
        grouped[sentence].append(record if spans else record["text"])
    assert [grouped[number] for number in sorted(grouped)] == json.loads(json_result.stdout)


@pytest.mark.parametrize("mode", MODES)
def test_jsonl_empty_stdin_emits_nothing(mode):
    result = run_break(mode, "--jsonl", input_text="")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("spans", [False, True])
def test_jsonl_takes_precedence_over_json_in_every_mode(mode, spans):
    """--jsonl wins wherever both are passed, spans branch included."""
    options = ["--spans", "-t", TEXT] if spans else ["-t", TEXT]
    both = run_break(mode, "--json", "--jsonl", *options)
    only_jsonl = run_break(mode, "--jsonl", *options)
    assert (both.returncode, both.stderr) == (0, "")
    assert both.stdout == only_jsonl.stdout
    assert len(parse_jsonl(both.stdout)) > 1


def test_jsonl_wins_over_json_and_json_shapes_are_unchanged():
    winner = run_break("words", "--json", "--jsonl", "-t", "Hello world.")
    assert parse_jsonl(winner.stdout) == [
        {"text": "Hello"},
        {"text": "world"},
        {"text": "."},
    ]

    words = run_break("words", "--json", "-t", "Hello world.")
    sentences = run_break("sentences", "--spans", "--json", "-t", "One. Two.")
    assert json.loads(words.stdout) == ["Hello", "world", "."]
    assert isinstance(json.loads(sentences.stdout), list)
    assert all(isinstance(record, dict) for record in json.loads(sentences.stdout))
