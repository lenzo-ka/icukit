"""CLI provenance tests for ICU break output."""

import json
import subprocess
import sys
from argparse import Namespace

import icu

import icukit
import icukit.cli.command.breaker as breaker_command
from icukit.cli.command.breaker import BreakerCommand


def run_break(*args):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", "break", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def break_args(**overrides):
    values = {
        "files": [],
        "include_whitespace": False,
        "json": True,
        "locale": "en_US",
        "no_header": False,
        "output": None,
        "provenance": True,
        "show_codepoints": False,
        "skip_punctuation": False,
        "spans": False,
        "text": "Hello world.",
    }
    values.update(overrides)
    return Namespace(**values)


def test_provenance_versions_match_the_runtime(capsys):
    result = BreakerCommand.cmd_words(break_args())

    assert result == 0
    provenance = json.loads(capsys.readouterr().out)["provenance"]
    assert provenance == {
        "icu_version": icu.ICU_VERSION,
        "unicode_version": icu.UNICODE_VERSION,
        "pyicu_version": icu.VERSION,
        "icukit_version": icukit.__version__,
    }


def test_provenance_reads_version_sources_at_call_time(monkeypatch, capsys):
    sentinels = {
        "icu_version": "synthetic-icu-source-sentinel",
        "unicode_version": "synthetic-unicode-source-sentinel",
        "pyicu_version": "synthetic-pyicu-source-sentinel",
        "icukit_version": "synthetic-icukit-source-sentinel",
    }
    monkeypatch.setattr(icu, "ICU_VERSION", sentinels["icu_version"])
    monkeypatch.setattr(icu, "UNICODE_VERSION", sentinels["unicode_version"])
    monkeypatch.setattr(icu, "VERSION", sentinels["pyicu_version"])
    monkeypatch.setattr(breaker_command, "__version__", sentinels["icukit_version"], raising=False)

    assert BreakerCommand.cmd_words(break_args()) == 0

    assert json.loads(capsys.readouterr().out)["provenance"] == sentinels


def test_provenance_document_preserves_break_value_shape(capsys):
    assert BreakerCommand.cmd_tokenize(break_args(provenance=False)) == 0
    plain = json.loads(capsys.readouterr().out)
    assert BreakerCommand.cmd_tokenize(break_args()) == 0
    stamped = json.loads(capsys.readouterr().out)

    assert set(stamped) == {"provenance", "breaks"}
    assert stamped["breaks"] == plain


def test_provenance_is_json_only(capsys):
    result = BreakerCommand.cmd_lines(break_args(json=False))

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == "Error: --provenance requires --json\n"


def test_json_without_provenance_is_unchanged():
    result = run_break("words", "-t", "Hello world", "--json")

    assert result.returncode == 0, result.stderr
    assert result.stdout == '[\n  "Hello",\n  "world"\n]\n'
    assert result.stderr == ""
