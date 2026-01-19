"""CLI command for locale-aware string sorting."""

import argparse
import sys

from ...collator import (
    STRENGTH_IDENTICAL,
    STRENGTH_PRIMARY,
    STRENGTH_QUATERNARY,
    STRENGTH_SECONDARY,
    STRENGTH_TERTIARY,
    compare_strings,
    get_collator_info,
    list_collation_types,
    sort_strings,
)
from ...errors import CollatorError
from ...formatters import print_output
from ..subcommand_base import SubcommandBase


class CollatorCommand(SubcommandBase):
    """Locale-aware string sorting and comparison."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the collate command with its subcommands."""
        parser = subparsers.add_parser(
            "collate",
            aliases=["col"],
            help="Locale-aware string sorting and comparison",
            description="""
Sort and compare strings using ICU's locale-aware collation.

Different languages have different sorting rules. For example, Swedish
sorts 'o' after 'z', while German sorts 'o' with 'o'.

Strength levels control how strings are compared:
  primary    - Base letters only (a=A=a)
  secondary  - Base + accents (a=A, a!=a)
  tertiary   - Base + accents + case (default)
  quaternary - Tertiary + punctuation
  identical  - Bit-for-bit comparison

Examples:
  # Sort lines from stdin
  echo -e 'cafe\\ncafe\\nCafe' | icukit collate sort

  # Sort with Swedish rules (o after z)
  echo -e 'o\\no\\nz' | icukit collate sort --locale sv_SE

  # Sort ignoring accents
  icukit collate sort --strength primary < words.txt

  # Compare two strings
  icukit collate compare 'cafe' 'cafe'

  # List collation types
  icukit collate list types
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "sort": {
                    "aliases": ["s"],
                    "help": "Sort lines using locale-aware collation",
                    "func": cls.cmd_sort,
                    "configure": cls._configure_sort,
                },
                "compare": {
                    "aliases": ["cmp", "c"],
                    "help": "Compare two strings",
                    "func": cls.cmd_compare,
                    "configure": cls._configure_compare,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get collator information for a locale",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
                "list": {
                    "aliases": ["ls", "l"],
                    "help": "List collation types or strengths",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_sort(cls, parser):
        """Configure sort subcommand."""
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for sorting rules (default: en_US)",
        )
        parser.add_argument(
            "--reverse",
            "-r",
            action="store_true",
            help="Sort in descending order",
        )
        parser.add_argument(
            "--unique",
            "-u",
            action="store_true",
            help="Remove duplicate lines",
        )
        parser.add_argument(
            "--strength",
            "-s",
            choices=["primary", "secondary", "tertiary", "quaternary", "identical"],
            help="Collation strength (default: tertiary)",
        )
        parser.add_argument(
            "--case-first",
            choices=["upper", "lower"],
            help="Sort uppercase or lowercase first",
        )
        cls._add_input_options(parser)

    @classmethod
    def _configure_compare(cls, parser):
        """Configure compare subcommand."""
        parser.add_argument(
            "string_a",
            help="First string",
        )
        parser.add_argument(
            "string_b",
            help="Second string",
        )
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for comparison (default: en_US)",
        )
        parser.add_argument(
            "--strength",
            "-s",
            choices=["primary", "secondary", "tertiary", "quaternary", "identical"],
            help="Collation strength",
        )

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        parser.add_argument(
            "locale",
            nargs="?",
            default="en_US",
            help="Locale to get collator info for (default: en_US)",
        )
        parser.add_argument(
            "--extended",
            "-x",
            action="store_true",
            help="Include extended attributes",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument(
            "what",
            nargs="?",
            choices=["types", "strengths"],
            default="types",
            help="What to list (default: types)",
        )
        cls._add_output_options(parser)

    INFO_COLUMNS = ["locale", "actual_locale", "strength"]
    EXTENDED_COLUMNS = ["has_tailoring", "rules_length"]

    @classmethod
    def cmd_sort(cls, args):
        """Sort lines using locale-aware collation."""
        try:
            lines = cls._read_lines(args)
            if not lines:
                return 0

            if args.unique:
                seen = set()
                unique_lines = []
                for line in lines:
                    if line not in seen:
                        seen.add(line)
                        unique_lines.append(line)
                lines = unique_lines

            sorted_lines = sort_strings(
                lines,
                args.locale,
                reverse=args.reverse,
                strength=args.strength,
                case_first=getattr(args, "case_first", None),
            )

            for line in sorted_lines:
                print(line)
            return 0
        except CollatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_compare(cls, args):
        """Compare two strings."""
        try:
            result = compare_strings(
                args.string_a,
                args.string_b,
                args.locale,
                strength=args.strength,
            )

            if result < 0:
                print(f'"{args.string_a}" < "{args.string_b}"')
                return 1
            elif result > 0:
                print(f'"{args.string_a}" > "{args.string_b}"')
                return 2
            else:
                print(f'"{args.string_a}" = "{args.string_b}"')
                return 0
        except CollatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_info(cls, args):
        """Show collator information for a locale."""
        try:
            extended = getattr(args, "extended", False)
            info = get_collator_info(args.locale, include_extended=extended)

            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            print_output(
                [info],
                as_json=as_json,
                columns=cls.INFO_COLUMNS,
                headers=not no_header,
                extended_columns=cls.EXTENDED_COLUMNS if extended else None,
            )
            return 0
        except CollatorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_list(cls, args):
        """List collation types or strengths."""
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        if args.what == "strengths":
            items = [
                {"strength": STRENGTH_PRIMARY, "description": "Base letters only (a=A=a)"},
                {"strength": STRENGTH_SECONDARY, "description": "Base + accents (a=A, a!=a)"},
                {"strength": STRENGTH_TERTIARY, "description": "Base + accents + case (default)"},
                {"strength": STRENGTH_QUATERNARY, "description": "Tertiary + punctuation"},
                {"strength": STRENGTH_IDENTICAL, "description": "Bit-for-bit comparison"},
            ]
            columns = ["strength", "description"]
        else:
            types = list_collation_types()
            items = [{"type": t} for t in types]
            columns = ["type"]

        print_output(items, as_json=as_json, columns=columns, headers=not no_header)
        return 0
