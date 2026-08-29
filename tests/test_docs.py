"""Tests for generated reference documentation."""

import subprocess
import sys
from pathlib import Path

import icukit

ROOT = Path(__file__).parent.parent
API_DOC = ROOT / "docs" / "api.md"


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
    ):
        assert f"[`{name}`](#icukitformatters)" in api
        assert f"### `{name}(" in api


def test_documentation_generation_is_idempotent(tmp_path):
    command = [sys.executable, str(ROOT / "docs" / "generate.py"), "--output", str(tmp_path)]
    subprocess.run(command, cwd=ROOT, check=True)
    first = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    subprocess.run(command, cwd=ROOT, check=True)
    second = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    assert second == first
