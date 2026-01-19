"""CLI command for parsing locale-formatted values."""

import argparse
import sys

from ...errors import ParseError
from ...formatters import print_output
from ...parse import parse_currency, parse_number, parse_percent
from ..subcommand_base import SubcommandBase


class ParseCommand(SubcommandBase):
    """Parse locale-formatted values command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the parse command with its subcommands."""
        parser = subparsers.add_parser(
            "parse",
            help="Parse locale-formatted numbers and currencies",
            description="""
Parse locale-formatted numbers, currencies, and percentages back to values.

This handles locale-specific conventions like:
  - Decimal separators (. vs ,)
  - Grouping separators (, vs . vs space)
  - Currency symbols and positions
  - Percent signs

Examples:
  # Parse numbers
  icukit parse number '1,234.56' --locale en_US
  # → 1234.56

  icukit parse number '1.234,56' --locale de_DE
  # → 1234.56

  icukit parse number '1 234,56' --locale fr_FR
  # → 1234.56

  # Parse currencies
  icukit parse currency '$1,234.56' --locale en_US
  # → {"value": 1234.56, "currency": "USD"}

  icukit parse currency '€1.234,56' --locale de_DE
  # → {"value": 1234.56, "currency": "EUR"}

  # Parse percentages
  icukit parse percent '50%' --locale en_US
  # → 0.5

  icukit parse percent '125%'
  # → 1.25
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "number": {
                    "aliases": ["n", "num"],
                    "help": "Parse a locale-formatted number",
                    "configure": cls._configure_number,
                    "func": cls.cmd_number,
                },
                "currency": {
                    "aliases": ["c", "cur"],
                    "help": "Parse a locale-formatted currency",
                    "configure": cls._configure_currency,
                    "func": cls.cmd_currency,
                },
                "percent": {
                    "aliases": ["p", "pct"],
                    "help": "Parse a locale-formatted percentage",
                    "configure": cls._configure_percent,
                    "func": cls.cmd_percent,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_number(cls, parser):
        """Configure the number subcommand."""
        parser.add_argument("text", help="Number string to parse")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Strict parsing (no lenient mode)",
        )

    @classmethod
    def _configure_currency(cls, parser):
        """Configure the currency subcommand."""
        parser.add_argument("text", help="Currency string to parse")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Strict parsing (no lenient mode)",
        )
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _configure_percent(cls, parser):
        """Configure the percent subcommand."""
        parser.add_argument("text", help="Percentage string to parse")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Strict parsing (no lenient mode)",
        )

    @classmethod
    def cmd_number(cls, args):
        """Parse a locale-formatted number."""
        try:
            result = parse_number(args.text, args.locale, lenient=not args.strict)
            # Print as integer if whole number, otherwise float
            if result == int(result):
                print(int(result))
            else:
                print(result)
            return 0
        except ParseError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_currency(cls, args):
        """Parse a locale-formatted currency."""
        try:
            result = parse_currency(args.text, args.locale, lenient=not args.strict)

            if args.json:
                print_output([result], as_json=True)
            else:
                value = result["value"]
                currency = result.get("currency") or "?"
                # Print as integer if whole number
                if value == int(value):
                    print(f"{int(value)}\t{currency}")
                else:
                    print(f"{value}\t{currency}")
            return 0
        except ParseError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_percent(cls, args):
        """Parse a locale-formatted percentage."""
        try:
            result = parse_percent(args.text, args.locale, lenient=not args.strict)
            print(result)
            return 0
        except ParseError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
