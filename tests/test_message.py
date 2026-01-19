"""Tests for the message module."""

import subprocess
import sys

from icukit import MessageFormatter, format_message


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


class TestFormatMessage:
    """Tests for format_message function."""

    def test_simple_placeholder(self):
        """Test simple placeholder substitution."""
        result = format_message("Hello, {name}!", {"name": "World"}, "en")
        assert result == "Hello, World!"

    def test_multiple_placeholders(self):
        """Test multiple placeholders."""
        result = format_message("{a} and {b}", {"a": "Alice", "b": "Bob"}, "en")
        assert result == "Alice and Bob"

    def test_number_formatting(self):
        """Test number formatting."""
        result = format_message("Count: {n, number}", {"n": 1234567}, "en_US")
        assert "1,234,567" in result or "1234567" in result

    def test_plural_one(self):
        """Test plural with one item."""
        pattern = "{count, plural, one {# item} other {# items}}"
        result = format_message(pattern, {"count": 1}, "en")
        assert "1 item" in result
        assert "items" not in result

    def test_plural_other(self):
        """Test plural with multiple items."""
        pattern = "{count, plural, one {# item} other {# items}}"
        result = format_message(pattern, {"count": 5}, "en")
        assert "5 items" in result

    def test_plural_zero(self):
        """Test plural with zero."""
        pattern = "{count, plural, =0 {no items} one {# item} other {# items}}"
        result = format_message(pattern, {"count": 0}, "en")
        assert "no items" in result

    def test_select(self):
        """Test select formatting."""
        pattern = "{gender, select, male {He} female {She} other {They}}"
        assert "He" in format_message(pattern, {"gender": "male"}, "en")
        assert "She" in format_message(pattern, {"gender": "female"}, "en")
        assert "They" in format_message(pattern, {"gender": "other"}, "en")


class TestMessageFormatter:
    """Tests for MessageFormatter class."""

    def test_init(self):
        """Test initialization."""
        mf = MessageFormatter("Hello, {name}!", "en")
        assert mf.pattern == "Hello, {name}!"
        assert mf.locale == "en"

    def test_format(self):
        """Test format method."""
        mf = MessageFormatter("Hello, {name}!", "en")
        result = mf.format({"name": "World"})
        assert result == "Hello, World!"

    def test_reuse(self):
        """Test reusing formatter."""
        mf = MessageFormatter("{n, plural, one {# cat} other {# cats}}", "en")
        assert "1 cat" in mf.format({"n": 1})
        assert "5 cats" in mf.format({"n": 5})

    def test_repr(self):
        """Test string representation."""
        mf = MessageFormatter("Hello!", "en_US")
        assert "Hello!" in repr(mf)
        assert "en_US" in repr(mf)


class TestMessageCLI:
    """Tests for message CLI commands."""

    def test_format_simple(self):
        """Test simple format."""
        code, out, err = run_cli("message", "format", "Hello, {name}!", "--arg", "name=World")
        assert code == 0
        assert "Hello, World!" in out

    def test_format_plural(self):
        """Test plural format."""
        pattern = "{count, plural, one {# item} other {# items}}"
        code, out, err = run_cli("message", "format", pattern, "--arg", "count=5")
        assert code == 0
        assert "5 items" in out

    def test_format_plural_one(self):
        """Test plural format with one."""
        pattern = "{count, plural, one {# item} other {# items}}"
        code, out, err = run_cli("message", "format", pattern, "--arg", "count=1")
        assert code == 0
        assert "1 item" in out

    def test_format_select(self):
        """Test select format."""
        pattern = "{g, select, male {He} female {She} other {They}}"
        code, out, err = run_cli("message", "format", pattern, "--arg", "g=female")
        assert code == 0
        assert "She" in out

    def test_format_multiple_args(self):
        """Test multiple arguments."""
        pattern = "{name} has {n, plural, one {# cat} other {# cats}}"
        code, out, err = run_cli(
            "message", "format", pattern, "--arg", "name=Alice", "--arg", "n=3"
        )
        assert code == 0
        assert "Alice" in out
        assert "3 cats" in out

    def test_format_with_locale(self):
        """Test format with locale."""
        pattern = "{n, number}"
        code, out, err = run_cli(
            "message", "format", pattern, "--arg", "n=1234567", "--locale", "de_DE"
        )
        assert code == 0
        # German uses . as thousands separator
        assert "1.234.567" in out or "1234567" in out

    def test_examples(self):
        """Test examples subcommand."""
        code, out, err = run_cli("message", "examples")
        assert code == 0
        assert "plural" in out.lower()
        assert "select" in out.lower()

    def test_invalid_pattern(self):
        """Test invalid pattern."""
        code, out, err = run_cli("message", "format", "{unclosed", "--arg", "x=1")
        assert code == 1
        assert "Error" in err

    def test_prefix_matching(self):
        """Test prefix matching."""
        code, out, err = run_cli("msg", "fmt", "Hello, {name}!", "--arg", "name=World")
        assert code == 0
        assert "Hello, World!" in out
