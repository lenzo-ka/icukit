"""CLI command for plural rules."""

import argparse
import sys

from ...errors import PluralError
from ...formatters import print_output
from ...plural import (
    TYPE_CARDINAL,
    TYPE_ORDINAL,
    get_ordinal_category,
    get_plural_category,
    get_plural_rules_info,
    list_ordinal_categories,
    list_plural_categories,
)
from ..subcommand_base import SubcommandBase


class PluralCommand(SubcommandBase):
    """Plural rules command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the plural command with its subcommands."""
        parser = subparsers.add_parser(
            "plural",
            help="Determine plural categories for numbers",
            description="""
Determine which plural category a number falls into for a given locale.

Plural Categories:
  zero  - For 0 in some languages (Arabic)
  one   - Singular form (1 in English, complex rules in other languages)
  two   - Dual form (Arabic, Hebrew, Slovenian)
  few   - Paucal form (2-4 in Slavic languages)
  many  - "Many" category (5+ in Slavic, 11-99 in Maltese)
  other - General plural (default fallback)

Examples:
  # Get plural category for a number
  icukit plural select 1 --locale en
  # → one

  icukit plural select 2 --locale ru
  # → few

  icukit plural select 5 --locale ru
  # → many

  # Get ordinal category (1st, 2nd, 3rd...)
  icukit plural ordinal 1 --locale en
  # → one (for "1st")

  icukit plural ordinal 2 --locale en
  # → two (for "2nd")

  # List categories used by a locale
  icukit plural categories --locale en
  icukit plural categories --locale ar
  icukit plural categories --locale ru --type ordinal

  # Show detailed info about locale's plural rules
  icukit plural info --locale ru
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "select": {
                    "aliases": ["s", "get"],
                    "help": "Get plural category for a number",
                    "configure": cls._configure_select,
                    "func": cls.cmd_select,
                },
                "ordinal": {
                    "aliases": ["o", "ord"],
                    "help": "Get ordinal category for a number",
                    "configure": cls._configure_ordinal,
                    "func": cls.cmd_ordinal,
                },
                "categories": {
                    "aliases": ["c", "cat", "list"],
                    "help": "List plural categories for a locale",
                    "configure": cls._configure_categories,
                    "func": cls.cmd_categories,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Show detailed plural rules info",
                    "configure": cls._configure_info,
                    "func": cls.cmd_info,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_select(cls, parser):
        """Configure the select subcommand."""
        parser.add_argument("number", type=float, help="Number to categorize")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )

    @classmethod
    def _configure_ordinal(cls, parser):
        """Configure the ordinal subcommand."""
        parser.add_argument("number", type=float, help="Number to categorize")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )

    @classmethod
    def _configure_categories(cls, parser):
        """Configure the categories subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-t",
            "--type",
            choices=[TYPE_CARDINAL, TYPE_ORDINAL],
            default=TYPE_CARDINAL,
            help="Plural type (default: cardinal)",
        )
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _configure_info(cls, parser):
        """Configure the info subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def cmd_select(cls, args):
        """Get plural category for a number."""
        try:
            category = get_plural_category(args.number, args.locale)
            print(category)
            return 0
        except PluralError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_ordinal(cls, args):
        """Get ordinal category for a number."""
        try:
            category = get_ordinal_category(args.number, args.locale)
            print(category)
            return 0
        except PluralError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_categories(cls, args):
        """List plural categories for a locale."""
        try:
            if args.type == TYPE_ORDINAL:
                categories = list_ordinal_categories(args.locale)
            else:
                categories = list_plural_categories(args.locale)

            if args.json:
                print_output(
                    [{"category": c} for c in categories],
                    columns=["category"],
                    as_json=True,
                )
            else:
                for cat in categories:
                    print(cat)
            return 0
        except PluralError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_info(cls, args):
        """Show detailed plural rules info."""
        try:
            info = get_plural_rules_info(args.locale)

            if args.json:
                print_output([info], as_json=True)
            else:
                print(f"Locale: {info['locale']}")
                print()
                print("Cardinal categories:")
                for cat in info["cardinal_categories"]:
                    examples = info["examples"].get(cat, [])
                    examples_str = ", ".join(str(n) for n in examples)
                    print(f"  {cat:<8} examples: {examples_str}")
                print()
                print("Ordinal categories:")
                for cat in info["ordinal_categories"]:
                    print(f"  {cat}")
            return 0
        except PluralError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
