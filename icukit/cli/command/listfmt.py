"""CLI command for list formatting."""

import argparse
import sys

from ...errors import ListFormatError
from ...list_format import STYLE_AND, STYLE_OR, STYLE_UNIT, format_list
from ..subcommand_base import SubcommandBase


class ListFmtCommand(SubcommandBase):
    """Direct list formatting command (no subcommands)."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the listfmt command."""
        parser = subparsers.add_parser(
            "listfmt",
            help="Format lists with locale-aware conjunctions",
            description="""
Format lists of items with locale-appropriate conjunctions and separators.

Styles:
  and   - "a, b, and c" (default)
  or    - "a, b, or c"
  unit  - "a, b, c" (no conjunction)

Examples:
  # Basic usage (comma-separated input)
  icukit listfmt 'apples,oranges,bananas'
  # → apples, oranges, and bananas

  # With "or" style
  icukit listfmt 'red,green,blue' --style or
  # → red, green, or blue

  # German (no Oxford comma)
  icukit listfmt 'Äpfel,Orangen,Bananen' --locale de
  # → Äpfel, Orangen und Bananen

  # Two items (special case)
  icukit listfmt 'yes,no' --style or
  # → yes or no

  # Custom delimiter
  icukit listfmt 'apples|oranges|bananas' --delimiter '|'
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            "items",
            help="Items to format (comma-separated, or use --delimiter)",
        )
        parser.add_argument(
            "--style",
            "-s",
            choices=[STYLE_AND, STYLE_OR, STYLE_UNIT],
            default=STYLE_AND,
            help="List style (default: and)",
        )
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for formatting (default: en_US)",
        )
        parser.add_argument(
            "--delimiter",
            "-d",
            default=",",
            help="Input delimiter (default: comma)",
        )

        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
        """Format the list."""
        try:
            items = [item.strip() for item in args.items.split(args.delimiter)]
            items = [item for item in items if item]  # Remove empty

            if not items:
                print("")
                return 0

            result = format_list(items, args.locale, args.style)
            print(result)
            return 0
        except ListFormatError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
