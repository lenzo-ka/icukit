"""Tests for icukit CLI."""

import subprocess
import sys


def run_cli(*args, input_text=None):
    """Run icukit CLI and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "icukit.cli"] + list(args)
    result = subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_help(self):
        """CLI should show help."""
        code, out, err = run_cli("--help")
        assert code == 0
        assert "icukit" in out.lower()
        assert "transliterate" in out

    def test_version(self):
        """CLI should show version."""
        code, out, err = run_cli("--version")
        assert code == 0
        assert "0.1.0" in out

    def test_no_args_shows_help(self):
        """CLI with no args should show help."""
        code, out, err = run_cli()
        assert code == 0
        assert "transliterate" in out


class TestTransliterateCommand:
    """Test transliterate command."""

    def test_transliterate_help(self):
        """Transliterate should show help."""
        code, out, err = run_cli("transliterate", "--help")
        assert code == 0
        assert "list" in out
        assert "name" in out

    def test_transliterate_list(self):
        """Should list transliterators."""
        code, out, err = run_cli("transliterate", "list", "-s")
        assert code == 0
        assert "Latin-Cyrillic" in out
        assert "Latin-Greek" in out

    def test_transliterate_list_filter(self):
        """Should filter transliterators by name."""
        code, out, err = run_cli("transliterate", "list", "--name", "Latin-Cyrillic", "-s")
        assert code == 0
        assert "Latin-Cyrillic" in out
        # Should not contain unrelated transliterators
        lines = [line for line in out.strip().split("\n") if line]
        assert all("Latin-Cyrillic" in line or "Cyrillic" in line for line in lines)

    def test_transliterate_name(self):
        """Should transliterate text."""
        code, out, err = run_cli("transliterate", "name", "Latin-Cyrillic", input_text="Hello")
        assert code == 0
        assert len(out.strip()) > 0
        # Output should be different from input (Cyrillic)
        assert out.strip() != "Hello"

    def test_transliterate_remove_accents(self):
        """Should handle compound transliterator rules."""
        code, out, err = run_cli(
            "transliterate",
            "name",
            "NFD; [:Nonspacing Mark:] Remove; NFC",
            input_text="Café résumé",
        )
        assert code == 0
        assert "Cafe resume" in out

    def test_transliterate_prefix_matching(self):
        """Command prefix matching should work."""
        # 'tr' should resolve to 'transliterate'
        code, out, err = run_cli("tr", "list", "-s")
        assert code == 0
        assert "Latin-Cyrillic" in out

    def test_transliterate_subcommand_prefix(self):
        """Subcommand prefix matching should work."""
        # 'n' should resolve to 'name'
        code, out, err = run_cli("tr", "n", "Upper", input_text="hello")
        assert code == 0
        assert "HELLO" in out

    def test_transliterate_json_output(self):
        """Should output JSON when requested."""
        code, out, err = run_cli("transliterate", "list", "--name", "Latin-Cyrillic", "-j")
        assert code == 0
        assert "{" in out  # JSON object (single result unwrapped from array)
        assert "Latin-Cyrillic" in out

    def test_transliterate_shortcut(self):
        """Should accept transliterator ID directly without 'name' subcommand."""
        code, out, err = run_cli("tr", "Latin-Greek", input_text="Hello")
        assert code == 0
        assert len(out.strip()) > 0
        assert out.strip() != "Hello"


class TestRegexCommand:
    """Test regex command."""

    def test_regex_help(self):
        """Regex should show help."""
        code, out, err = run_cli("regex", "--help")
        assert code == 0
        assert "find" in out
        assert "replace" in out
        assert "split" in out

    def test_regex_find(self):
        """Should find regex matches."""
        code, out, err = run_cli("regex", "find", r"\d+", input_text="abc123def456")
        assert code == 0
        assert "123" in out

    def test_regex_find_all(self):
        """Should find all regex matches."""
        code, out, err = run_cli("regex", "find", r"\d+", "--all", input_text="abc123def456")
        assert code == 0
        assert "123" in out
        assert "456" in out

    def test_regex_find_unicode_property(self):
        """Should match Unicode properties."""
        code, out, err = run_cli(
            "regex", "find", r"\p{Script=Greek}+", input_text="Hello Αθήνα World"
        )
        assert code == 0
        assert "Αθήνα" in out

    def test_regex_find_count(self):
        """Should count matches."""
        code, out, err = run_cli("regex", "find", r"\d+", "--count", input_text="a1b2c3d4")
        assert code == 0
        assert "4" in out

    def test_regex_replace(self):
        """Should replace regex matches."""
        code, out, err = run_cli("regex", "replace", r"\d+", "X", input_text="abc123def456")
        assert code == 0
        assert "abcXdefX" in out

    def test_regex_replace_with_groups(self):
        """Should support capture group references in replacement."""
        code, out, err = run_cli(
            "regex", "replace", r"(\w+)@(\w+)", "$1 at $2", input_text="test@example"
        )
        assert code == 0
        assert "test at example" in out

    def test_regex_split(self):
        """Should split by regex."""
        code, out, err = run_cli("regex", "split", r"[,;:]", input_text="apple,banana;orange:grape")
        assert code == 0
        assert "apple" in out
        assert "banana" in out
        assert "orange" in out
        assert "grape" in out

    def test_regex_case_insensitive(self):
        """Should support case-insensitive matching."""
        code, out, err = run_cli(
            "regex", "find", "hello", "-i", "--all", input_text="Hello HELLO hello"
        )
        assert code == 0
        # Should find all three
        lines = [line for line in out.strip().split("\n") if line]
        assert len(lines) == 3

    def test_regex_search_found(self):
        """Search should return 0 when pattern found."""
        code, out, err = run_cli("regex", "search", r"\d+", input_text="abc123")
        assert code == 0

    def test_regex_search_not_found(self):
        """Search should return 1 when pattern not found."""
        code, out, err = run_cli("regex", "search", r"\d+", input_text="abc")
        assert code == 1

    def test_regex_match_success(self):
        """Match should return MATCH for full match."""
        code, out, err = run_cli("regex", "match", r"\d+", input_text="123")
        assert code == 0
        assert "MATCH" in out

    def test_regex_match_failure(self):
        """Match should not match partial input."""
        code, out, err = run_cli("regex", "match", r"\d+", input_text="abc123")
        assert code == 0
        assert "MATCH" not in out or "NO MATCH" in out

    def test_regex_list_properties(self):
        """Should list Unicode properties."""
        code, out, err = run_cli("regex", "list", "properties")
        assert code == 0
        assert r"\p{L}" in out
        assert "Letter" in out

    def test_regex_list_categories(self):
        """Should list Unicode categories."""
        code, out, err = run_cli("regex", "list", "categories")
        assert code == 0
        assert "L" in out
        assert "Letter" in out

    def test_regex_list_scripts(self):
        """Should list Unicode scripts."""
        code, out, err = run_cli("regex", "list", "scripts")
        assert code == 0
        assert "Latin" in out
        assert "Greek" in out

    def test_regex_list_json(self):
        """Should output JSON when requested."""
        code, out, err = run_cli("regex", "list", "categories", "-j")
        assert code == 0
        assert "[" in out
        assert '"code"' in out

    def test_regex_list_no_header(self):
        """Should suppress header with -H."""
        code, out, err = run_cli("regex", "list", "categories", "-H")
        assert code == 0
        # First line should be data, not header
        first_line = out.strip().split("\n")[0]
        assert "code" not in first_line.lower() or first_line.startswith("L\t")

    def test_regex_prefix_matching(self):
        """Command prefix matching should work."""
        # 're' should resolve to 'regex'
        code, out, err = run_cli("re", "find", r"\d+", input_text="abc123")
        assert code == 0
        assert "123" in out

    def test_regex_subcommand_prefix(self):
        """Subcommand prefix matching should work."""
        # 'f' should resolve to 'find'
        code, out, err = run_cli("regex", "f", r"\d+", input_text="abc123")
        assert code == 0
        assert "123" in out

    def test_regex_invalid_pattern(self):
        """Should error on invalid pattern."""
        code, out, err = run_cli("regex", "find", r"[invalid", input_text="test")
        assert code != 0
        assert "error" in err.lower() or "Error" in err
