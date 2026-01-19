"""CLI command for bidirectional text handling."""

import argparse
import sys

from ...bidi import get_bidi_info, has_bidi_controls, list_bidi_controls, strip_bidi_controls
from ...errors import BidiError
from ...formatters import print_output
from ..base import open_output, process_input
from ..subcommand_base import SubcommandBase


class BidiCommand(SubcommandBase):
    """Bidirectional text handling command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the bidi command with its subcommands."""
        parser = subparsers.add_parser(
            "bidi",
            help="Bidirectional text analysis and manipulation",
            description="""
Analyze and manipulate bidirectional (mixed LTR/RTL) text.

Useful for:
  - Detecting text direction
  - Finding hidden bidi control characters (security)
  - Stripping bidi controls from text

Examples:
  # Detect text direction
  icukit bidi detect -t 'Hello שלום'

  # Check for bidi controls (security)
  icukit bidi detect -t $'hello\\u200fworld'

  # Strip bidi controls from text
  echo 'suspicious text' | icukit bidi strip

  # List all bidi control characters
  icukit bidi list
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "detect": {
                    "aliases": ["d", "info"],
                    "help": "Detect text direction and bidi properties",
                    "func": cls.cmd_detect,
                    "configure": cls._configure_detect,
                },
                "strip": {
                    "aliases": ["s", "clean"],
                    "help": "Strip bidi control characters",
                    "func": cls.cmd_strip,
                    "configure": cls._configure_strip,
                },
                "check": {
                    "aliases": ["c"],
                    "help": "Check if text contains bidi controls",
                    "func": cls.cmd_check,
                    "configure": cls._configure_check,
                },
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List bidi control characters",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_detect(cls, parser):
        """Configure detect subcommand."""
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_strip(cls, parser):
        """Configure strip subcommand."""
        cls._add_input_options(parser)

    @classmethod
    def _configure_check(cls, parser):
        """Configure check subcommand."""
        cls._add_input_options(parser)

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        cls._add_output_options(parser)

    INFO_COLUMNS = ["direction", "base_direction", "has_rtl", "has_ltr", "bidi_control_count"]

    @classmethod
    def cmd_detect(cls, args):
        """Detect text direction and bidi properties."""
        try:
            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            # Read all input as single text
            lines = cls._read_lines(args)
            text = "\n".join(lines)

            if not text:
                return 0

            info = get_bidi_info(text)

            print_output(
                [info],
                as_json=as_json,
                columns=cls.INFO_COLUMNS,
                headers=not no_header,
            )
            return 0
        except BidiError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_strip(cls, args):
        """Strip bidi control characters from text."""
        try:

            def processor(text):
                return strip_bidi_controls(text)

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, processor, output)
            return 0
        except BidiError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_check(cls, args):
        """Check if text contains bidi controls."""
        try:
            lines = cls._read_lines(args)
            text = "\n".join(lines)

            if has_bidi_controls(text):
                info = get_bidi_info(text)
                print(f"Found {info['bidi_control_count']} bidi control character(s)")
                return 1  # Exit 1 if controls found (like grep)
            else:
                print("No bidi controls found")
                return 0
        except BidiError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

    @classmethod
    def cmd_list(cls, args):
        """List bidi control characters."""
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        controls = list_bidi_controls()

        print_output(
            controls,
            as_json=as_json,
            columns=["codepoint", "abbrev", "name"],
            headers=not no_header,
        )
        return 0
