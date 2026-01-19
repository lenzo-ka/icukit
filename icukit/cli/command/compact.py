"""CLI command for compact number formatting."""

import argparse
import sys

from ...compact import STYLE_LONG, STYLE_SHORT, CompactFormatter
from ...errors import FormatError
from ..subcommand_base import SubcommandBase


class CompactCommand(SubcommandBase):
    """Compact number formatting command (no subcommands)."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the compact command."""
        parser = subparsers.add_parser(
            "compact",
            help="Format numbers in compact form (1.2M, 3.5K)",
            description="""
Format large numbers with locale-appropriate abbreviations.

Styles:
  SHORT - "1.2M", "3.5K" (default)
  LONG  - "1.2 million", "3.5 thousand"

Examples:
  # Basic usage
  icukit compact 1234567
  # → 1.2M

  icukit compact 1234567 --style LONG
  # → 1.2 million

  # German locale
  icukit compact 1234567 --locale de_DE
  # → 1,2 Mio.

  icukit compact 1000000000 --locale de_DE
  # → 1 Mrd.

  # Japanese (uses 万=10000, not K=1000)
  icukit compact 12345 --locale ja_JP
  # → 1.2万

  # Multiple numbers
  icukit compact 1000 10000 100000 1000000
  # → 1K  10K  100K  1M

  # Financial display
  icukit compact 1500000000 --style LONG --locale en_US
  # → 1.5 billion
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            "numbers",
            type=float,
            nargs="+",
            help="Number(s) to format",
        )
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-s",
            "--style",
            choices=[STYLE_SHORT, STYLE_LONG],
            default=STYLE_SHORT,
            help="Format style (default: SHORT)",
        )
        parser.add_argument(
            "--separator",
            default="\t",
            help="Separator for multiple numbers (default: tab)",
        )

        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
        """Format the numbers."""
        try:
            fmt = CompactFormatter(args.locale, args.style)
            results = [fmt.format(n) for n in args.numbers]

            if len(results) == 1:
                print(results[0])
            else:
                print(args.separator.join(results))

            return 0
        except FormatError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
