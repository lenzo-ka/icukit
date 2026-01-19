"""Tests for command trie prefix matching."""

from icukit.cli.command_trie import CommandTrie, register_command, resolve_command


class TestCommandTrie:
    """Test CommandTrie prefix matching."""

    def test_exact_match(self):
        """Exact command names should resolve."""
        trie = CommandTrie()
        trie.insert("transliterate", ["tr"])
        trie.insert("timezone", ["tz"])

        resolved, suggestions = trie.find_command("transliterate")
        assert resolved == "transliterate"
        assert suggestions == []

    def test_alias_resolution(self):
        """Aliases should resolve to main command."""
        trie = CommandTrie()
        trie.insert("transliterate", ["tr", "trans"])

        resolved, _ = trie.find_command("tr")
        assert resolved == "transliterate"

        resolved, _ = trie.find_command("trans")
        assert resolved == "transliterate"

    def test_unambiguous_prefix(self):
        """Unambiguous prefix should resolve."""
        trie = CommandTrie()
        trie.insert("transliterate")
        trie.insert("break")

        # 't' is unambiguous -> transliterate
        resolved, _ = trie.find_command("t")
        assert resolved == "transliterate"

        # 'b' is unambiguous -> break
        resolved, _ = trie.find_command("b")
        assert resolved == "break"

    def test_ambiguous_prefix(self):
        """Ambiguous prefix should return suggestions."""
        trie = CommandTrie()
        trie.insert("transliterate")
        trie.insert("timezone")

        # 't' is now ambiguous
        resolved, suggestions = trie.find_command("t")
        assert resolved is None
        assert "transliterate" in suggestions
        assert "timezone" in suggestions

    def test_no_match(self):
        """Non-existent prefix should return no match."""
        trie = CommandTrie()
        trie.insert("transliterate")

        resolved, suggestions = trie.find_command("xyz")
        assert resolved is None
        assert suggestions == []

    def test_minimal_prefix(self):
        """Should find minimal unambiguous prefix."""
        trie = CommandTrie()
        trie.insert("transliterate")
        trie.insert("timezone")

        # 'tr' should be minimal prefix for transliterate
        assert trie.get_minimal_prefix("transliterate") == "tr"
        # 'ti' should be minimal prefix for timezone
        assert trie.get_minimal_prefix("timezone") == "ti"

    def test_command_info(self):
        """Should return command info with minimal prefix."""
        trie = CommandTrie()
        trie.insert("transliterate", ["tr", "trans"])

        info = trie.get_command_info("transliterate")
        assert info["name"] == "transliterate"
        assert info["aliases"] == ["tr", "trans"]
        assert "minimal_prefix" in info

    def test_get_all_commands(self):
        """Should return all registered commands."""
        trie = CommandTrie()
        trie.insert("transliterate", ["tr"])
        trie.insert("timezone", ["tz"])

        commands = trie.get_all_commands()
        assert "transliterate" in commands
        assert "timezone" in commands
        assert commands["transliterate"] == ["tr"]


class TestGlobalCommandTrie:
    """Test global command trie functions."""

    def test_register_and_resolve(self):
        """Should register and resolve commands globally."""
        # Register a command first
        register_command("testcmd", ["tc"])

        resolved, _ = resolve_command("testcmd")
        assert resolved == "testcmd"

        resolved, _ = resolve_command("tc")
        assert resolved == "testcmd"
