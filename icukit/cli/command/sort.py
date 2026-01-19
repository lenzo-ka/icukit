"""Direct sort command - top-level locale-aware sorting."""

import argparse
import sys

from ...collator import sort_strings
from ...errors import CollatorError
from ..subcommand_base import SubcommandBase


class SortCommand(SubcommandBase):
    """Direct top-level sort command (no subcommands)."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the sort command."""
        parser = subparsers.add_parser(
            "sort",
            help="Sort lines using locale-aware collation",
            description="""
Sort lines using ICU's locale-aware collation.

Different languages have different sorting rules. For example, Swedish
sorts 'o' after 'z', while German sorts 'o' with 'o'.

Examples:
  # Sort lines from stdin
  echo -e 'cafe\\ncafe\\nCafe' | icukit sort

  # Sort with Swedish rules (o after z)
  echo -e 'o\\no\\nz' | icukit sort --locale sv_SE

  # Sort ignoring accents
  icukit sort --strength primary < words.txt

  # Sort with uppercase first
  icukit sort --case-first upper < words.txt
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

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
        parser.add_argument(
            "-t",
            "--text",
            metavar="TEXT",
            help="Process TEXT directly",
        )
        parser.add_argument(
            "files",
            nargs="*",
            metavar="FILE",
            help="Files to process (default: stdin)",
        )

        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
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
