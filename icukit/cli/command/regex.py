"""Unicode regex CLI commands."""

from __future__ import annotations

import argparse
import sys

from ...errors import PatternError
from ...formatters import format_json, print_output
from ...regex import (
    CASE_INSENSITIVE,
    DOTALL,
    MULTILINE,
    list_unicode_categories,
    list_unicode_properties,
    list_unicode_scripts,
    parse_substitution,
    regex_find,
    regex_fullmatch,
    regex_replace,
    regex_search,
    regex_split,
)
from ..base import open_output, process_input
from ..subcommand_base import SubcommandBase


class RegexCommand(SubcommandBase):
    """Regex command with subcommands."""

    DEFAULT_SUBCOMMAND = None  # Show help by default

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the regex command with its subcommands."""
        parser = subparsers.add_parser(
            "regex",
            help="Unicode-aware regular expressions with ICU",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=r"""
Unicode-aware regular expressions with full Unicode support.

Features:
  - Unicode properties and categories (\p{L}, \p{Script=Greek})
  - List available properties, categories, and scripts
  - Find/replace with Unicode awareness
  - Named capture groups
  - Split text by patterns

Examples:
  # List Unicode properties and categories
  icukit regex list properties
  icukit regex list categories
  icukit regex list scripts

  # Find matches
  echo 'Hello Αθήνα مرحبا' | icukit regex find '\p{Script=Greek}+'
  echo 'abc123def456' | icukit regex find '\d+' --all

  # Replace text
  echo 'Hello123World' | icukit regex replace '\d+' ' '
  echo 'test@example.com' | icukit regex replace '(\w+)@(\w+\.\w+)' '$1 at $2'

  # Split text
  echo 'apple,banana;orange:grape' | icukit regex split '[,;:]'

  # Case-insensitive Unicode matching
  echo 'Café CAFÉ café' | icukit regex find 'café' -i

Common Properties:
  \p{L}          - Any letter
  \p{N}          - Any number
  \p{P}          - Any punctuation
  \p{Z}          - Any separator
  \p{Ll}, \p{Lu} - Lowercase/uppercase letters
  \p{Script=X}   - Characters from script X

Common Scripts:
  Latin, Cyrillic, Greek, Arabic, Hebrew, Devanagari,
  Han (Chinese), Hiragana, Katakana, Thai
""",
        )

        # Create subcommands
        cls.create_subcommand_parser(
            parser,
            {
                "find": {
                    "aliases": ["f"],
                    "help": "Find pattern matches in text",
                    "func": cls.cmd_find,
                    "configure": cls._configure_find,
                },
                "replace": {
                    "aliases": ["r", "sub"],
                    "help": "Replace pattern matches with text",
                    "func": cls.cmd_replace,
                    "configure": cls._configure_replace,
                },
                "split": {
                    "aliases": ["sp"],
                    "help": "Split text by pattern",
                    "func": cls.cmd_split,
                    "configure": cls._configure_split,
                },
                "match": {
                    "aliases": ["m"],
                    "help": "Match entire input (anchored)",
                    "func": cls.cmd_match,
                    "configure": cls._configure_match,
                },
                "search": {
                    "aliases": ["test", "t"],
                    "help": "Test if pattern exists (exit code only)",
                    "func": cls.cmd_search,
                    "configure": cls._configure_search,
                },
                "script": {
                    "aliases": ["s", "sed", "expr"],
                    "help": "Substitution using s/pattern/replacement/flags syntax",
                    "func": cls.cmd_script,
                    "configure": cls._configure_script,
                },
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List Unicode properties, categories, or scripts",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _add_regex_flags(cls, parser):
        """Add common regex flag arguments."""
        regex_group = parser.add_argument_group("regex options")
        regex_group.add_argument(
            "-i",
            "--ignore-case",
            action="store_true",
            help="Case-insensitive matching (Unicode-aware)",
        )
        regex_group.add_argument(
            "-m",
            "--multiline",
            action="store_true",
            help="Multiline mode (^ and $ match line boundaries)",
        )
        regex_group.add_argument("-s", "--dotall", action="store_true", help="Dot matches newlines")

    @classmethod
    def _configure_find(cls, parser):
        """Configure the find subcommand."""
        parser.add_argument("pattern", help="ICU regex pattern")
        cls._add_input_options(parser)

        # Find options
        find_group = parser.add_argument_group("find options")
        find_group.add_argument(
            "--all", action="store_true", help="Find all matches (default: first only)"
        )
        find_group.add_argument("-g", "--groups", action="store_true", help="Show capture groups")
        find_group.add_argument(
            "-n", "--line-numbers", action="store_true", help="Show line numbers"
        )
        find_group.add_argument(
            "--only-matching", action="store_true", help="Show only matching parts"
        )
        find_group.add_argument("-c", "--count", action="store_true", help="Count matches only")
        find_group.add_argument("--limit", type=int, help="Maximum matches to find")

        cls._add_regex_flags(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_replace(cls, parser):
        """Configure the replace subcommand."""
        parser.add_argument("pattern", help="ICU regex pattern to find")
        parser.add_argument("replacement", help="Replacement text (use $1, $2 for groups)")
        cls._add_input_options(parser)

        # Replace options
        replace_group = parser.add_argument_group("replace options")
        replace_group.add_argument("--limit", type=int, help="Maximum replacements per line")

        cls._add_regex_flags(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_split(cls, parser):
        """Configure the split subcommand."""
        parser.add_argument("pattern", help="ICU regex pattern to split by")
        cls._add_input_options(parser)

        # Split options
        split_group = parser.add_argument_group("split options")
        split_group.add_argument("--limit", type=int, help="Maximum number of splits")

        cls._add_regex_flags(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_match(cls, parser):
        """Configure the match subcommand."""
        parser.add_argument("pattern", help="ICU regex pattern")
        cls._add_input_options(parser)

        cls._add_regex_flags(parser)
        parser.add_argument("-v", "--verbose", action="store_true", help="Show match details")

    @classmethod
    def _configure_search(cls, parser):
        """Configure the search subcommand."""
        parser.add_argument("pattern", help="ICU regex pattern")
        cls._add_input_options(parser)

        cls._add_regex_flags(parser)

    @classmethod
    def _configure_script(cls, parser):
        """Configure the script subcommand."""
        parser.add_argument(
            "expression",
            help="Substitution expression: s/pattern/replacement/[gi] (delimiter can be any char)",
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_list(cls, parser):
        """Configure the list subcommand."""
        parser.add_argument(
            "what",
            nargs="?",
            choices=["properties", "categories", "scripts"],
            default="all",
            help="What to list (default: all)",
        )
        parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
        parser.add_argument(
            "-H", "--no-header", action="store_true", help="Suppress header in TSV output"
        )

    @classmethod
    def _get_flags(cls, args):
        """Get regex flags from arguments."""
        flags = 0
        if getattr(args, "ignore_case", False):
            flags |= CASE_INSENSITIVE
        if getattr(args, "multiline", False):
            flags |= MULTILINE
        if getattr(args, "dotall", False):
            flags |= DOTALL
        return flags

    @classmethod
    def cmd_find(cls, args):
        """Find pattern matches in text."""
        try:
            flags = cls._get_flags(args)
            line_number = 0

            def find_processor(text):
                nonlocal line_number
                line_number += 1
                matches = regex_find(args.pattern, text, flags=flags)

                def add_line_number(result):
                    if getattr(args, "line_numbers", False) and result:
                        return "\n".join(f"{line_number}:{line}" for line in result.splitlines())
                    return result

                if args.count:
                    result = str(len(matches))
                elif args.all:
                    if args.limit:
                        matches = matches[: args.limit]

                    if args.only_matching:
                        result = [m["text"] for m in matches]
                        if getattr(args, "json", False):
                            return format_json(result)
                        else:
                            return add_line_number("\n".join(result))
                    elif args.groups:
                        result = []
                        for m in matches:
                            match_info = {
                                "match": m["text"],
                                "start": m["start"],
                                "end": m["end"],
                            }
                            if m["groups"]:
                                match_info["groups"] = [
                                    group["text"] for group in m["groups"].values()
                                ]
                            result.append(match_info)
                        if getattr(args, "json", False):
                            return format_json(result)
                        else:
                            return add_line_number("\n".join(m["match"] for m in result))
                    else:
                        if getattr(args, "json", False):
                            return format_json(matches)
                        else:
                            return add_line_number("\n".join(m["text"] for m in matches))
                else:
                    # Find first match
                    if matches:
                        match = matches[0]
                        if getattr(args, "json", False):
                            return format_json(match)
                        else:
                            return add_line_number(match["text"])
                    else:
                        result = ""

                return add_line_number(result)

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, find_processor, output)

            return 0
        except PatternError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_replace(cls, args):
        """Replace pattern matches with text."""
        try:
            flags = cls._get_flags(args)
            as_json = getattr(args, "json", False)

            def replace_processor(text):
                result = regex_replace(
                    args.pattern,
                    text,
                    args.replacement,
                    flags=flags,
                    limit=args.limit if args.limit else -1,
                )
                return format_json(result) if as_json else result

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, replace_processor, output)

            return 0
        except PatternError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_split(cls, args):
        """Split text by pattern."""
        try:
            flags = cls._get_flags(args)

            def split_processor(text):
                parts = regex_split(args.pattern, text, flags=flags)
                if args.limit:
                    parts = parts[: args.limit]

                if getattr(args, "json", False):
                    return format_json(parts)
                else:
                    return "\n".join(parts)

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, split_processor, output)

            return 0
        except PatternError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_match(cls, args):
        """Match entire input (anchored)."""
        try:
            flags = cls._get_flags(args)

            def match_processor(text):
                if regex_fullmatch(args.pattern, text, flags=flags):
                    if getattr(args, "verbose", False):
                        matches = regex_find(f"^{args.pattern}$", text.strip(), flags=flags)
                        return f"MATCH: {matches[0]['text']}"
                    return "MATCH"
                else:
                    if getattr(args, "verbose", False):
                        return "NO MATCH"
                    return ""

            with open_output(None) as output:
                process_input(args, match_processor, output)

            return 0
        except PatternError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_search(cls, args):
        """Test if pattern exists (exit code only)."""
        try:
            flags = cls._get_flags(args)
            found = False

            def search_processor(text):
                nonlocal found
                if regex_search(args.pattern, text, flags=flags):
                    found = True
                return ""  # No output

            with open_output(None) as output:
                process_input(args, search_processor, output)

            # Return 0 if found, 1 if not found
            return 0 if found else 1
        except PatternError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

    @classmethod
    def cmd_script(cls, args):
        """Execute sed-style substitution expression."""
        try:
            pattern, replacement, global_flag, ignore_case = parse_substitution(args.expression)

            flags = cls._get_flags(args)
            as_json = getattr(args, "json", False)
            if ignore_case:
                flags |= CASE_INSENSITIVE

            limit = -1 if global_flag else 1

            def script_processor(text):
                result = regex_replace(pattern, text, replacement, flags=flags, limit=limit)
                return format_json(result) if as_json else result

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, script_processor, output)

            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except PatternError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_list(cls, args):
        """List Unicode properties, categories, or scripts."""
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        if args.what == "properties" or args.what == "all":
            data = list_unicode_properties()
            print_output(
                data,
                as_json=as_json,
                columns=["category", "pattern", "description"],
                headers=not no_header,
            )
            if args.what == "all" and not as_json:
                print()

        if args.what == "categories" or args.what == "all":
            data = list_unicode_categories()
            print_output(
                data,
                as_json=as_json,
                columns=["code", "description"],
                headers=not no_header,
            )
            if args.what == "all" and not as_json:
                print()

        if args.what == "scripts" or args.what == "all":
            data = list_unicode_scripts()
            print_output(
                data,
                as_json=as_json,
                columns=["name", "pattern"],
                headers=not no_header,
            )

        return 0
