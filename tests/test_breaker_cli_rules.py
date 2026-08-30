"""End-to-end tests for standard and custom break-rule commands."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import icu
import pytest

import icukit
from icukit.breaker import default_rules

ROOT = Path(__file__).parents[1]
CUSTOM_RULES = r"""!!chain;
$Letter = [\p{Letter}];
$Digit = [\p{Number}];
$Space = [\p{White_Space}];
[Ff][Ii][Gg] \. {907};
$Letter+ {200};
$Digit+ {100};
$Space+ {0};
. {0};
"""
TEXT = "See Fig. 5 now"
STANDARD_PROVENANCE = {
    "icu_version": icu.ICU_VERSION,
    "unicode_version": icu.UNICODE_VERSION,
    "pyicu_version": icu.VERSION,
    "icukit_version": icukit.__version__,
}


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


@pytest.fixture
def rule_file(tmp_path):
    path = tmp_path / "custom.rules"
    path.write_text(CUSTOM_RULES, encoding="utf-8")
    return path


def parse_jsonl(output):
    assert output.endswith("\n")
    records = [json.loads(line) for line in output.splitlines()]
    assert records
    if len(records) > 1:
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)
    return records


def test_custom_rules_produce_boundaries_different_from_default(rule_file):
    custom = run_break("custom", "-r", str(rule_file), "--json", "-t", TEXT)
    standard = run_break("words", "--json", "-t", TEXT)
    assert (custom.returncode, custom.stderr) == (0, "")
    assert (standard.returncode, standard.stderr) == (0, "")
    assert json.loads(custom.stdout) == ["See", " ", "Fig.", " ", "5", " ", "now"]
    assert json.loads(standard.stdout) == ["See", "Fig", ".", "5", "now"]


def test_status_type_maps_custom_status_in_span(rule_file):
    result = run_break(
        "custom",
        "-r",
        str(rule_file),
        "--status-type",
        "907=abbrev",
        "--spans",
        "--json",
        "-t",
        TEXT,
    )
    spans = json.loads(result.stdout)
    abbreviation = next(span for span in spans if span["text"] == "Fig.")
    assert (result.returncode, result.stderr) == (0, "")
    assert abbreviation["types"] == ["abbrev"]
    assert abbreviation["statuses"] == [0, 907]


def test_custom_span_offsets_round_trip_in_all_index_spaces(rule_file):
    text = "é 😀 Fig."
    result = run_break("custom", "-r", str(rule_file), "--spans", "--json", "-t", text)
    assert (result.returncode, result.stderr) == (0, "")
    spans = json.loads(result.stdout)
    utf8 = text.encode("utf-8")
    utf16le = text.encode("utf-16-le")
    cp_start = 0
    for span in spans:
        expected = span["text"]
        cp_end = cp_start + len(expected)
        assert (span["codepoint_start"], span["codepoint_end"]) == (cp_start, cp_end)
        assert text[cp_start:cp_end] == expected
        u8_start = len(text[:cp_start].encode("utf-8"))
        u8_end = len(text[:cp_end].encode("utf-8"))
        assert (span["utf8_start"], span["utf8_end"]) == (u8_start, u8_end)
        assert utf8[u8_start:u8_end] == expected.encode("utf-8")
        u16_start = len(text[:cp_start].encode("utf-16-le")) // 2
        u16_end = len(text[:cp_end].encode("utf-16-le")) // 2
        assert (span["utf16_start"], span["utf16_end"]) == (u16_start, u16_end)
        assert utf16le[2 * u16_start : 2 * u16_end] == expected.encode("utf-16-le")
        cp_start = cp_end


@pytest.mark.parametrize("kind", ("word", "sentence", "line", "grapheme"))
def test_rules_plain_output_is_default_rule_text(kind):
    result = run_break("rules", "-k", kind, "-l", "en_US")
    assert (result.returncode, result.stderr) == (0, "")
    assert result.stdout == default_rules(kind, "en_US") + "\n"


def test_standard_rules_compile_and_segment_when_piped_to_custom(tmp_path):
    generated = run_break("rules", "-k", "word")
    path = tmp_path / "word.rules"
    path.write_text(generated.stdout, encoding="utf-8")
    consumed = run_break("custom", "-r", str(path), "--json", "-t", TEXT)
    default = run_break("words", "--json", "--include-whitespace", "-t", TEXT)
    assert (generated.returncode, generated.stderr) == (0, "")
    assert (consumed.returncode, consumed.stderr) == (0, "")
    assert json.loads(consumed.stdout) == json.loads(default.stdout)


def test_json_and_jsonl_shapes_for_both_commands(rule_file):
    custom_json = run_break("custom", "-r", str(rule_file), "--json", "-t", TEXT)
    custom_jsonl = run_break("custom", "-r", str(rule_file), "--jsonl", "-t", TEXT)
    rules_json = run_break("rules", "--json")
    rules_jsonl = run_break("rules", "--jsonl")
    tokens = json.loads(custom_json.stdout)
    assert parse_jsonl(custom_jsonl.stdout) == [{"text": token} for token in tokens]
    rule_record = json.loads(rules_json.stdout)
    assert set(rule_record) == {"kind", "locale", "rules"}
    assert parse_jsonl(rules_jsonl.stdout) == [rule_record]


def test_provenance_is_extended_only_for_custom_rules(rule_file):
    custom = json.loads(
        run_break("custom", "-r", str(rule_file), "--json", "--provenance", "-t", TEXT).stdout
    )
    rules = json.loads(run_break("rules", "--json", "--provenance").stdout)
    words = json.loads(run_break("words", "--json", "--provenance", "-t", TEXT).stdout)
    assert custom["provenance"] == {
        **STANDARD_PROVENANCE,
        "rules_sha256": hashlib.sha256(CUSTOM_RULES.encode()).hexdigest(),
    }
    assert rules["provenance"] == STANDARD_PROVENANCE
    assert words["provenance"] == STANDARD_PROVENANCE


def test_jsonl_provenance_repeats_the_rule_digest_on_every_record(rule_file):
    result = run_break("custom", "-r", str(rule_file), "--jsonl", "--provenance", "-t", TEXT)
    records = parse_jsonl(result.stdout)
    expected = {
        **STANDARD_PROVENANCE,
        "rules_sha256": hashlib.sha256(CUSTOM_RULES.encode()).hexdigest(),
    }
    assert (result.returncode, result.stderr) == (0, "")
    assert len(records) > 1
    assert [record["provenance"] for record in records] == [expected] * len(records)


def test_adding_custom_does_not_steal_the_c_prefix_from_graphemes():
    """`break c` resolved to graphemes before `custom` existed; it still must."""
    abbreviated = run_break("c", "-t", "See Fig. 5 😀")
    graphemes = run_break("graphemes", "-t", "See Fig. 5 😀")
    assert (abbreviated.returncode, abbreviated.stderr) == (0, "")
    assert abbreviated.stdout == graphemes.stdout
    assert graphemes.stdout.splitlines()[0] == "S"


@pytest.mark.parametrize("mode", ("rules", "custom"))
def test_provenance_requires_structured_format(mode, rule_file):
    options = ["-r", str(rule_file), "-t", TEXT] if mode == "custom" else []
    result = run_break(mode, *options, "--provenance")
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Error: --provenance requires --json or --jsonl\n"


def test_custom_spans_route_to_output_file(rule_file, tmp_path):
    destination = tmp_path / "spans.tsv"
    result = run_break(
        "custom", "-r", str(rule_file), "--spans", "-o", str(destination), "-t", TEXT
    )
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert destination.read_text(encoding="utf-8").startswith("text\tcodepoint_start\t")


@pytest.mark.parametrize("existing", (False, True))
def test_bad_rules_do_not_create_or_replace_output(tmp_path, existing):
    bad_rules = tmp_path / "bad.rules"
    bad_rules.write_text("this is not valid RBBI", encoding="utf-8")
    destination = tmp_path / "destination.tsv"
    if existing:
        destination.write_text("keep me\n", encoding="utf-8")
    result = run_break(
        "custom", "-r", str(bad_rules), "--spans", "-o", str(destination), "-t", TEXT
    )
    assert result.returncode == 1
    assert "Error: Invalid break rules:" in result.stderr
    assert "Traceback" not in result.stderr
    if existing:
        assert destination.read_text(encoding="utf-8") == "keep me\n"
    else:
        assert not destination.exists()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (("custom", "-r", "missing.rules", "-t", TEXT), "Error: cannot read"),
        (("custom", "-r", "{bad}", "-t", TEXT), "Error: Invalid break rules:"),
        (
            ("custom", "--status-type", "foo", "-r", "{rules}", "-t", TEXT),
            "Error: Invalid --status-type 'foo': expected N=NAME",
        ),
        (
            ("custom", "--status-type", "x=name", "-r", "{rules}", "-t", TEXT),
            "Error: Invalid --status-type 'x=name': expected N=NAME",
        ),
        (
            ("rules", "-k", "sentence", "-l", "en_US@ss=standard"),
            "Error: No extractable rules",
        ),
    ],
)
def test_error_paths_are_clean(options, message, rule_file, tmp_path):
    bad = tmp_path / "bad.rules"
    bad.write_text("this is not valid RBBI", encoding="utf-8")
    expanded = tuple(
        str(rule_file) if item == "{rules}" else str(bad) if item == "{bad}" else item
        for item in options
    )
    result = run_break(*expanded)
    assert result.returncode == 1
    assert result.stdout == ""
    assert message in result.stderr
    assert "Traceback" not in result.stderr
