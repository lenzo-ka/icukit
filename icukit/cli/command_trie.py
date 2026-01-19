"""Trie-based command prefix matching for CLI."""

from typing import Dict, List, Optional, Tuple


class CommandTrie:
    """Trie for command prefix matching.

    Allows any unambiguous prefix of a command to be used.
    For example, if commands are ['break', 'charset', 'transliterate']:
    - 'b' -> 'break' (unambiguous)
    - 'c' -> 'charset' (unambiguous)
    - 't' -> 'transliterate' (unambiguous)
    """

    class TrieNode:
        def __init__(self):
            self.children: Dict[str, "CommandTrie.TrieNode"] = {}
            self.is_command = False
            self.command_name = None
            self.aliases: List[str] = []

    def __init__(self):
        self.root = self.TrieNode()
        self._commands: Dict[str, List[str]] = {}

    def insert(self, command: str, aliases: Optional[List[str]] = None):
        """Insert a command and its aliases into the trie."""
        self._commands[command] = aliases or []
        self._insert_word(command, command, aliases or [])
        if aliases:
            for alias in aliases:
                self._insert_word(alias, command, [])

    def _insert_word(self, word: str, command_name: str, aliases: List[str]):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = self.TrieNode()
            node = node.children[char]
        node.is_command = True
        node.command_name = command_name
        node.aliases = aliases

    def find_command(self, prefix: str) -> Tuple[Optional[str], List[str]]:
        """Find command matching the given prefix.

        Returns:
            Tuple of (matched_command, possible_matches)
            - If unambiguous: (command_name, [])
            - If ambiguous: (None, [list of possible commands])
            - If no match: (None, [])
        """
        node = self.root
        for char in prefix:
            if char not in node.children:
                return (None, [])
            node = node.children[char]

        if node.is_command:
            return (node.command_name, [])

        commands = self._collect_commands(node)
        if len(commands) == 1:
            return (commands[0], [])
        return (None, commands)

    def _collect_commands(self, node: "TrieNode") -> List[str]:
        commands = []
        if node.is_command:
            commands.append(node.command_name)
        for child in node.children.values():
            commands.extend(self._collect_commands(child))
        seen = set()
        return [c for c in commands if not (c in seen or seen.add(c))]

    def get_all_commands(self) -> Dict[str, List[str]]:
        return self._commands.copy()

    def get_minimal_prefix(self, command: str) -> str:
        """Get the minimal unambiguous prefix for a command."""
        for i in range(1, len(command) + 1):
            prefix = command[:i]
            resolved, _ = self.find_command(prefix)
            if resolved == command:
                return prefix
        return command

    def get_command_info(self, command: str) -> Optional[Dict]:
        if command not in self._commands:
            return None
        return {
            "name": command,
            "minimal_prefix": self.get_minimal_prefix(command),
            "aliases": self._commands[command],
        }


# Global command trie instance
_command_trie = CommandTrie()


def register_command(command: str, aliases: Optional[List[str]] = None):
    _command_trie.insert(command, aliases)


def resolve_command(prefix: str) -> Tuple[Optional[str], List[str]]:
    return _command_trie.find_command(prefix)


def get_all_commands() -> Dict[str, List[str]]:
    return _command_trie.get_all_commands()


def get_command_info(command: str) -> Optional[Dict]:
    return _command_trie.get_command_info(command)
