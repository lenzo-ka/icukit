"""Regression tests for CLI output-option consumption and routing."""

import argparse
import ast
import inspect
import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from icukit.cli.main import create_parser

ROOT = Path(__file__).parents[1]
OUTPUT_DESTS = {"output", "json", "jsonl", "no_header"}
OUTPUT_HELP_WORDS = {"output", "header", "json", "show", "short", "span"}
INTENTIONAL_UNUSED = {
    ("alpha-index buckets", "no_header"): "section output has no tabular header",
    ("discover search", "no_header"): "search output has labeled prose, not a table",
    ("regex find", "no_header"): "find output is JSON or headerless matching lines",
    ("regex replace", "no_header"): "replacement output is headerless text",
    ("regex split", "no_header"): "split output is JSON or headerless text",
    ("regex script", "no_header"): "substitution output is headerless text",
    ("script detect", "no_header"): "detection output is a single value or JSON list",
    ("search first", "no_header"): "the single match row has no header by design",
    ("spoof check", "no_header"): "check output is JSON or labeled prose",
    ("spoof info", "no_header"): "info output is JSON or labeled prose",
    ("transliterate name", "no_header"): "transliterated text has no header",
    ("transliterate from", "no_header"): "transliterated text has no header",
    ("transliterate script", "no_header"): "transliterated text has no header",
}


def _leaf_parsers(parser):
    """Yield each canonical leaf command and its parser from the real CLI tree."""
    subcommands = next(
        (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
        None,
    )
    if subcommands is None:
        yield tuple(parser.prog.split()[1:]), parser
        return

    seen = set()
    for child in subcommands.choices.values():
        if id(child) in seen:
            continue
        seen.add(id(child))
        yield from _leaf_parsers(child)


def _local_output_dests(parser):
    """Return output-affecting options registered directly on a leaf parser."""
    dests = set()
    for action in parser._actions:
        if not action.option_strings or action.dest == "help":
            continue
        help_words = set((action.help or "").lower().replace("-", " ").split())
        if action.dest in OUTPUT_DESTS or help_words & OUTPUT_HELP_WORDS:
            dests.add(action.dest)
    return dests


class _ConsumptionVisitor(ast.NodeVisitor):
    """Collect argument reads and statically resolvable helper calls."""

    def __init__(self, argument_name):
        self.argument_name = argument_name
        self.reads = set()
        self.calls = set()

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == self.argument_name:
            self.reads.add(node.attr)
        self.generic_visit(node)

    def visit_Call(self, node):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in {"getattr", "hasattr"}
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == self.argument_name
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            self.reads.add(node.args[1].value)
        if isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        elif isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        self.generic_visit(node)


def _consumed_dests(handler):
    """Follow a handler's same-class/module helpers and return read argument names."""
    owner = handler.__self__ if inspect.ismethod(handler) else None
    handler = inspect.unwrap(handler)
    module = inspect.getmodule(handler)
    pending = [handler]
    visited = set()
    consumed = set()

    while pending:
        function = inspect.unwrap(pending.pop())
        if function in visited:
            continue
        visited.add(function)
        parameters = list(inspect.signature(function).parameters)
        if not parameters:
            continue
        argument_name = "args" if "args" in parameters else parameters[0]
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        visitor = _ConsumptionVisitor(argument_name)
        visitor.visit(tree)
        consumed.update(visitor.reads)
        for name in visitor.calls:
            helper = getattr(owner, name, None) if owner is not None else None
            if helper is None:
                helper = getattr(module, name, None)
            if inspect.ismethod(helper):
                pending.append(helper)
            elif inspect.isfunction(helper) and inspect.getmodule(inspect.unwrap(helper)) is module:
                pending.append(helper)
    return consumed


def enumerate_output_option_mismatches():
    """Return the complete leaf/option consumption report and mismatches."""
    rows = []
    mismatches = []
    for command, parser in _leaf_parsers(create_parser()):
        registered = _local_output_dests(parser)
        if not registered:
            continue
        handler = parser.get_default("func")
        consumed = _consumed_dests(handler)
        unused = registered - consumed
        # Output paths are consumed by the common dispatch seam and verified
        # behaviorally below; leaf handlers must not each implement routing.
        unused.discard("output")
        path = " ".join(command)
        rows.append((path, sorted(registered), sorted(unused)))
        for dest in unused:
            if (path, dest) not in INTENTIONAL_UNUSED:
                mismatches.append((path, dest))
    return rows, mismatches


def _format_enumeration(rows):
    lines = ["leaf | registered output options | unconsumed"]
    for path, registered, unused in rows:
        statuses = [
            f"{dest} (allowed: {INTENTIONAL_UNUSED[(path, dest)]})"
            if (path, dest) in INTENTIONAL_UNUSED
            else dest
            for dest in unused
        ]
        lines.append(f"{path} | {','.join(registered)} | {','.join(statuses) or '-'}")
    return "\n".join(lines)


def run_cli(*args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", *args],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_every_registered_output_option_is_consumed(capsys):
    rows, mismatches = enumerate_output_option_mismatches()
    report = _format_enumeration(rows)
    print(report)
    assert not mismatches, f"registered output options are ignored:\n{report}"


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("break", "words", "--json", "-t", "café 日本語"), ["café", "日本語"]),
        (("break", "words", "--spans", "-t", "café"), "text\tcodepoint_start"),
    ],
)
def test_output_file_receives_structured_output_and_stdout_is_empty(tmp_path, arguments, expected):
    destination = tmp_path / "output.txt"
    result = run_cli(*arguments, "-o", str(destination))
    content = destination.read_text(encoding="utf-8")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    if isinstance(expected, list):
        assert json.loads(content) == expected
    else:
        assert content.startswith(expected)


def test_output_file_overwrites_existing_content(tmp_path):
    destination = tmp_path / "output.txt"
    destination.write_text("stale", encoding="utf-8")
    result = run_cli("break", "words", "--json", "-t", "fresh", "-o", str(destination))
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert json.loads(destination.read_text(encoding="utf-8")) == ["fresh"]


@pytest.mark.parametrize("destination_exists", [True, False])
def test_failed_command_does_not_replace_or_create_output(tmp_path, destination_exists):
    destination = tmp_path / "output.txt"
    original_content = "IMPORTANT PRIOR CONTENT\n"
    original_mode = 0o640
    if destination_exists:
        destination.write_text(original_content, encoding="utf-8")
        destination.chmod(original_mode)

    result = run_cli("regex", "find", "[", "-t", "abc", "-o", str(destination))

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.startswith("Error: Invalid regex pattern '['")
    if destination_exists:
        assert destination.read_text(encoding="utf-8") == original_content
        assert stat.S_IMODE(destination.stat().st_mode) == original_mode
    else:
        assert not destination.exists()


def test_output_file_modes_preserve_existing_mode_and_respect_umask(tmp_path):
    existing = tmp_path / "existing.txt"
    existing.write_text("old\n", encoding="utf-8")
    existing.chmod(0o644)
    replacement = run_cli("break", "words", "--json", "-t", "new", "-o", str(existing))
    assert replacement.returncode == 0
    assert stat.S_IMODE(existing.stat().st_mode) == 0o644

    current_umask = os.umask(0)
    os.umask(current_umask)
    fresh = tmp_path / "fresh.txt"
    creation = run_cli("break", "words", "--json", "-t", "new", "-o", str(fresh))
    assert creation.returncode == 0
    assert stat.S_IMODE(fresh.stat().st_mode) == 0o666 & ~current_umask


def test_output_file_in_missing_directory_fails_without_partial_file(tmp_path):
    destination = tmp_path / "missing" / "output.txt"
    result = run_cli("break", "words", "--json", "-t", "text", "-o", str(destination))
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.startswith(f"Error: cannot write {destination}:")
    assert not destination.exists()


def test_unopenable_output_path_fails_without_partial_file(tmp_path):
    directory = tmp_path / "readonly"
    directory.mkdir()
    directory.chmod(stat.S_IREAD | stat.S_IEXEC)
    destination = directory / "output.txt"
    try:
        result = run_cli("break", "words", "--json", "-t", "text", "-o", str(destination))
    finally:
        directory.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    if os.geteuid() == 0:
        pytest.skip("root can write to read-only directories")
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.startswith(f"Error: cannot write {destination}:")
    assert not destination.exists()


def test_break_sentences_honors_json_with_and_without_spans():
    plain = run_cli("break", "sentences", "--json", "-t", "One. Two.")
    spans = run_cli("break", "sentences", "--spans", "--json", "-t", "One. Two.")
    assert (plain.returncode, plain.stderr, json.loads(plain.stdout)) == (
        0,
        "",
        ["One.", "Two."],
    )
    assert (spans.returncode, spans.stderr) == (0, "")
    assert [item["text"] for item in json.loads(spans.stdout)] == ["One. ", "Two."]
