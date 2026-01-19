"""CLI command for display names."""

import argparse
import sys

from ...displayname import (
    get_currency_name,
    get_currency_symbol,
    get_language_name,
    get_locale_name,
    get_region_name,
    get_script_name,
)
from ...errors import DisplayNameError
from ..subcommand_base import SubcommandBase


class DisplayNameCommand(SubcommandBase):
    """Display names command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the displayname command with its subcommands."""
        parser = subparsers.add_parser(
            "displayname",
            help="Get localized display names for languages, regions, etc.",
            description="""
Get localized display names for languages, scripts, regions, currencies,
and locales.

Examples:
  # Language names
  icukit displayname language zh
  # → Chinese

  icukit displayname language zh --display de
  # → Chinesisch

  icukit displayname language zh --display ja
  # → 中国語

  # Script names
  icukit displayname script Cyrl
  # → Cyrillic

  icukit displayname script Hans --display zh
  # → 简体中文

  # Region/country names
  icukit displayname region JP
  # → Japan

  icukit displayname region JP --display ja
  # → 日本

  # Currency names
  icukit displayname currency USD
  # → US Dollar

  icukit displayname currency USD --display ja
  # → 米ドル

  # Currency symbols
  icukit displayname symbol USD
  # → $

  icukit displayname symbol EUR
  # → €

  # Full locale names
  icukit displayname locale zh_Hans_CN
  # → Chinese (Simplified, China)

  icukit displayname locale zh_Hans_CN --display de
  # → Chinesisch (Vereinfacht, China)
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "language": {
                    "aliases": ["l", "lang"],
                    "help": "Get display name for a language",
                    "configure": cls._configure_language,
                    "func": cls.cmd_language,
                },
                "script": {
                    "aliases": ["s", "scr"],
                    "help": "Get display name for a script",
                    "configure": cls._configure_script,
                    "func": cls.cmd_script,
                },
                "region": {
                    "aliases": ["r", "reg", "country"],
                    "help": "Get display name for a region/country",
                    "configure": cls._configure_region,
                    "func": cls.cmd_region,
                },
                "currency": {
                    "aliases": ["c", "cur"],
                    "help": "Get display name for a currency",
                    "configure": cls._configure_currency,
                    "func": cls.cmd_currency,
                },
                "symbol": {
                    "aliases": ["sym"],
                    "help": "Get currency symbol",
                    "configure": cls._configure_symbol,
                    "func": cls.cmd_symbol,
                },
                "locale": {
                    "aliases": ["loc"],
                    "help": "Get display name for a locale",
                    "configure": cls._configure_locale,
                    "func": cls.cmd_locale,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_language(cls, parser):
        """Configure the language subcommand."""
        parser.add_argument("code", help="ISO 639 language code (e.g., en, zh, ar)")
        parser.add_argument(
            "-d",
            "--display",
            default="en_US",
            help="Display locale (default: en_US)",
        )

    @classmethod
    def _configure_script(cls, parser):
        """Configure the script subcommand."""
        parser.add_argument("code", help="ISO 15924 script code (e.g., Latn, Cyrl, Hans)")
        parser.add_argument(
            "-d",
            "--display",
            default="en_US",
            help="Display locale (default: en_US)",
        )

    @classmethod
    def _configure_region(cls, parser):
        """Configure the region subcommand."""
        parser.add_argument("code", help="ISO 3166-1 alpha-2 region code (e.g., US, JP, DE)")
        parser.add_argument(
            "-d",
            "--display",
            default="en_US",
            help="Display locale (default: en_US)",
        )

    @classmethod
    def _configure_currency(cls, parser):
        """Configure the currency subcommand."""
        parser.add_argument("code", help="ISO 4217 currency code (e.g., USD, EUR, JPY)")
        parser.add_argument(
            "-d",
            "--display",
            default="en_US",
            help="Display locale (default: en_US)",
        )

    @classmethod
    def _configure_symbol(cls, parser):
        """Configure the symbol subcommand."""
        parser.add_argument("code", help="ISO 4217 currency code (e.g., USD, EUR, JPY)")
        parser.add_argument(
            "-d",
            "--display",
            default="en_US",
            help="Display locale (default: en_US)",
        )

    @classmethod
    def _configure_locale(cls, parser):
        """Configure the locale subcommand."""
        parser.add_argument("code", help="Locale code (e.g., en_US, zh_Hans_CN)")
        parser.add_argument(
            "-d",
            "--display",
            default="en_US",
            help="Display locale (default: en_US)",
        )

    @classmethod
    def cmd_language(cls, args):
        """Get display name for a language."""
        try:
            result = get_language_name(args.code, args.display)
            print(result)
            return 0
        except DisplayNameError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_script(cls, args):
        """Get display name for a script."""
        try:
            result = get_script_name(args.code, args.display)
            print(result)
            return 0
        except DisplayNameError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_region(cls, args):
        """Get display name for a region/country."""
        try:
            result = get_region_name(args.code, args.display)
            print(result)
            return 0
        except DisplayNameError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_currency(cls, args):
        """Get display name for a currency."""
        try:
            result = get_currency_name(args.code, args.display)
            print(result)
            return 0
        except DisplayNameError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_symbol(cls, args):
        """Get currency symbol."""
        try:
            result = get_currency_symbol(args.code, args.display)
            print(result)
            return 0
        except DisplayNameError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_locale(cls, args):
        """Get display name for a locale."""
        try:
            result = get_locale_name(args.code, args.display)
            print(result)
            return 0
        except DisplayNameError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
