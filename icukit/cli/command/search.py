"""CLI command for locale-aware text search."""

import argparse
import sys

from ...errors import SearchError
from ...formatters import print_output
from ...search import (
    STRENGTH_IDENTICAL,
    STRENGTH_PRIMARY,
    STRENGTH_QUATERNARY,
    STRENGTH_SECONDARY,
    STRENGTH_TERTIARY,
    search_all,
    search_count,
    search_first,
    search_replace,
)
from ..subcommand_base import SubcommandBase

_STRENGTHS = [
    STRENGTH_PRIMARY,
    STRENGTH_SECONDARY,
    STRENGTH_TERTIARY,
    STRENGTH_QUATERNARY,
    STRENGTH_IDENTICAL,
]


class SearchCommand(SubcommandBase):
    """Locale-aware text search using ICU collation."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the search command with its subcommands."""
        parser = subparsers.add_parser(
            "search",
            aliases=["find"],
            help="Locale-aware text search",
            description="""
Search text using ICU's locale-aware collation rules.

Unlike simple string matching, locale-aware search can find matches
that are linguistically equivalent. For example, with primary strength,
"cafe" matches "café" and "CAFE".

Strength levels control matching:
  primary    - Base letters only (cafe=café=CAFE)
  secondary  - Base + accents (cafe=CAFE, but café≠cafe)
  tertiary   - Base + accents + case (exact match, default)
  quaternary - Tertiary + punctuation differences
  identical  - Bit-for-bit identical

Examples:
  # Find all matches (case-insensitive)
  echo 'The café and CAFE' | icukit search find cafe --strength primary

  # Count matches
  icukit search count cafe -t 'café, Cafe, CAFE' -s primary

  # Replace matches
  echo 'Visit the café' | icukit search replace cafe tea -s primary

  # Search with French locale
  icukit search find cafe -t 'Un café au lait' -l fr_FR -s primary
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "find": {
                    "aliases": ["f", "all"],
                    "help": "Find all occurrences of pattern",
                    "func": cls.cmd_find,
                    "configure": cls._configure_find,
                },
                "first": {
                    "aliases": ["1"],
                    "help": "Find first occurrence of pattern",
                    "func": cls.cmd_first,
                    "configure": cls._configure_first,
                },
                "count": {
                    "aliases": ["c", "cnt"],
                    "help": "Count occurrences of pattern",
                    "func": cls.cmd_count,
                    "configure": cls._configure_count,
                },
                "replace": {
                    "aliases": ["r", "sub"],
                    "help": "Replace occurrences of pattern",
                    "func": cls.cmd_replace,
                    "configure": cls._configure_replace,
                },
                "contains": {
                    "aliases": ["has"],
                    "help": "Check if pattern exists in text",
                    "func": cls.cmd_contains,
                    "configure": cls._configure_contains,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _add_common_args(cls, parser):
        """Add common arguments for search commands."""
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for collation rules (default: en_US)",
        )
        parser.add_argument(
            "--strength",
            "-s",
            choices=_STRENGTHS,
            help="Collation strength (default: tertiary/exact)",
        )

    @classmethod
    def _configure_find(cls, parser):
        """Configure find subcommand."""
        parser.add_argument("pattern", help="Pattern to search for")
        cls._add_input_options(parser)
        cls._add_common_args(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_first(cls, parser):
        """Configure first subcommand."""
        parser.add_argument("pattern", help="Pattern to search for")
        cls._add_input_options(parser)
        cls._add_common_args(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_count(cls, parser):
        """Configure count subcommand."""
        parser.add_argument("pattern", help="Pattern to search for")
        cls._add_input_options(parser)
        cls._add_common_args(parser)

    @classmethod
    def _configure_replace(cls, parser):
        """Configure replace subcommand."""
        parser.add_argument("pattern", help="Pattern to search for")
        parser.add_argument("replacement", help="Replacement string")
        parser.add_argument(
            "--max",
            "-n",
            type=int,
            default=0,
            help="Maximum replacements (0=unlimited)",
        )
        cls._add_input_options(parser)
        cls._add_common_args(parser)

    @classmethod
    def _configure_contains(cls, parser):
        """Configure contains subcommand."""
        parser.add_argument("pattern", help="Pattern to search for")
        cls._add_input_options(parser)
        cls._add_common_args(parser)

    @classmethod
    def cmd_find(cls, args):
        """Find all occurrences of pattern."""
        try:
            text = cls._read_input(args)
            if not text:
                return 0

            matches = search_all(
                args.pattern,
                text,
                args.locale,
                strength=args.strength,
            )

            if not matches:
                return 0

            print_output(
                matches,
                columns=["start", "end", "text"],
                as_json=getattr(args, "json", False),
                headers=not getattr(args, "no_header", False),
            )
            return 0
        except SearchError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_first(cls, args):
        """Find first occurrence of pattern."""
        try:
            text = cls._read_input(args)
            if not text:
                return 1

            match = search_first(
                args.pattern,
                text,
                args.locale,
                strength=args.strength,
            )

            if not match:
                return 1

            if getattr(args, "json", False):
                print_output(match, as_json=True)
            else:
                print(f"{match['start']}\t{match['end']}\t{match['text']}")
            return 0
        except SearchError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_count(cls, args):
        """Count occurrences of pattern."""
        try:
            text = cls._read_input(args)
            if not text:
                print(0)
                return 0

            count = search_count(
                args.pattern,
                text,
                args.locale,
                strength=args.strength,
            )
            print(count)
            return 0
        except SearchError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_replace(cls, args):
        """Replace occurrences of pattern."""
        try:
            text = cls._read_input(args)
            if not text:
                return 0

            result = search_replace(
                args.pattern,
                text,
                args.replacement,
                args.locale,
                strength=args.strength,
                count=args.max,
            )
            print(result, end="")
            return 0
        except SearchError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_contains(cls, args):
        """Check if pattern exists in text."""
        try:
            text = cls._read_input(args)
            if not text:
                print("false")
                return 1

            match = search_first(
                args.pattern,
                text,
                args.locale,
                strength=args.strength,
            )

            if match:
                print("true")
                return 0
            else:
                print("false")
                return 1
        except SearchError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
