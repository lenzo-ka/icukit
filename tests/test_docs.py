"""Tests for generated reference documentation."""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import icukit

ROOT = Path(__file__).parent.parent
API_DOC = ROOT / "docs" / "api.md"
CLI_DOC = ROOT / "docs" / "cli.md"


def _generator():
    """Load docs/generate.py, which is a script rather than an importable module."""
    spec = importlib.util.spec_from_file_location("_docs_generate", ROOT / "docs" / "generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _markdown_for(build):
    """Render CLI markdown for a throwaway parser built by ``build``."""
    generate = _generator()
    parser = argparse.ArgumentParser(prog="icukit")
    build(parser.add_subparsers())
    return generate.generate_cli_markdown(generate.extract_parser_info(parser))


def test_api_reference_covers_exported_data_and_root_surface():
    api = API_DOC.read_text()

    assert "### Constants and type aliases" in api
    assert "`PATTERNS`" in api
    assert "`Condition`" in api
    for name in ("DateTimeFormatter", "PATTERNS", "Condition", "break_words"):
        assert name in icukit.__all__
        assert f"[`{name}`]" in api


def test_api_reference_covers_formatters_module():
    api = API_DOC.read_text()

    assert "## icukit.formatters" in api
    for name in (
        "flatten_extended",
        "format_json",
        "format_output",
        "format_simple_list",
        "format_tsv",
        "print_output",
        "print_record",
    ):
        assert f"[`{name}`](#icukitformatters)" in api
        assert f"### `{name}(" in api


def test_heading_names_the_canonical_command_however_long_its_aliases_are():
    """An alias longer than the command it aliases must not take over the heading.

    The name a command is documented under is the one its parser was created
    with. Anything else silently renames a command when an alias is added, and
    would make alias length a constraint on naming.
    """

    def build(subparsers):
        subparsers.add_parser("tz", aliases=["timezone-information"], help="Query timezones")

    markdown = _markdown_for(build)

    assert "## `icukit tz` (aliases: timezone-information)" in markdown
    assert "## `icukit timezone-information`" not in markdown


def test_commands_sharing_a_description_and_arguments_are_documented_separately():
    """Two commands that happen to look alike are still two commands.

    Identifying aliases by content rather than by parser identity collapsed
    distinct subcommands into one entry and dropped the rest from the reference.
    """

    def build(subparsers):
        for name in ("alpha", "beta"):
            sub = subparsers.add_parser(name, help="Same help", description="Same description")
            sub.add_argument("value", help="A value")

    markdown = _markdown_for(build)

    assert "## `icukit alpha`" in markdown
    assert "## `icukit beta`" in markdown


def test_cli_reference_documents_commands_under_their_canonical_names():
    cli = CLI_DOC.read_text()

    assert "## `icukit spoof` (aliases: confusable, homoglyph)" in cli
    assert "## `icukit idna` (aliases: idn, punycode)" in cli
    assert "## `icukit confusable`" not in cli
    assert "## `icukit punycode`" not in cli


def test_a_constants_comment_is_documented_whole(tmp_path):
    """A truncated comment still reads as prose, which is why nothing caught it.

    The generator took only the line directly above an assignment, so a comment
    running to two lines was published as its own last line: ``DEFAULT_FAMILIES``
    was documented in the API reference as "inverter. Abbreviations use their
    typed lexicon." Nothing was malformed and nothing failed -- the reference just
    said something other than what the source said.
    """
    module_path = tmp_path / "_fixture.py"
    module_path.write_text(
        "# The first line of the reason.\n"
        "# The second line, which is the only one that used to survive.\n"
        "SAMPLE = 1\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("_docs_fixture", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    doc = _generator().get_source_assignments(module)["SAMPLE"]["doc"]

    assert doc.splitlines() == [
        "The first line of the reason.",
        "The second line, which is the only one that used to survive.",
    ]


def test_an_assignment_docstring_still_wins_over_a_comment(tmp_path):
    """The documented convention keeps precedence; the comment is the fallback."""
    module_path = tmp_path / "_fixture_docstring.py"
    module_path.write_text(
        '# A comment that must not be preferred.\nSAMPLE = 1\n"""The docstring."""\n',
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("_docs_fixture_docstring", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert _generator().get_source_assignments(module)["SAMPLE"]["doc"] == "The docstring."


def test_documentation_generation_is_idempotent(tmp_path):
    command = [sys.executable, str(ROOT / "docs" / "generate.py"), "--output", str(tmp_path)]
    subprocess.run(command, cwd=ROOT, check=True)
    first = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    subprocess.run(command, cwd=ROOT, check=True)
    second = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    assert second == first
