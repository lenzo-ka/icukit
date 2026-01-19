#!/usr/bin/env python
"""Main CLI entry point for ICU Kit."""

import argparse
import sys
from typing import List

from .. import __version__
from .command import (
    AlphaIndexCommand,
    BidiCommand,
    BreakerCommand,
    CalendarCommand,
    CollatorCommand,
    CompactCommand,
    DateTimeCommand,
    DiscoverCommand,
    DisplayNameCommand,
    DurationCommand,
    IDNACommand,
    ListFmtCommand,
    LocaleCommand,
    MeasureCommand,
    MessageCommand,
    ParseCommand,
    PluralCommand,
    RegexCommand,
    RegionCommand,
    ScriptCommand,
    SearchCommand,
    SortCommand,
    SpoofCommand,
    TimezoneCommand,
    TransliterateCommand,
    UnicodeCommand,
    add_help_subparser,
)
from .command_trie import register_command, resolve_command
from .logging_setup import setup_logging

DESCRIPTION = r"""
ICU Kit - Unicode ICU utilities for text processing

A toolkit for international text processing, providing:
  - Text transliteration between scripts
  - Unicode-aware regular expressions
  - Script detection and properties
  - Unicode normalization and character info

Examples:
  # Transliterate to Greek
  echo 'Hello' | icukit transliterate name Latin-Greek

  # Unicode regex with script matching
  echo 'Hello Αθήνα' | icukit regex find '\p{Script=Greek}+'

  # Detect script of text
  icukit script detect -t 'Ελληνικά'

  # Normalize Unicode text
  echo 'café' | icukit unicode normalize --form NFC

  # Get character info
  icukit unicode info -t 'α'

For detailed help on any command:
  icukit <command> --help
"""


class PrefixArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that supports command prefix matching."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subparsers_action = None

    def add_subparsers(self, **kwargs):
        self._subparsers_action = super().add_subparsers(**kwargs)
        return self._subparsers_action

    def parse_args(self, args=None, namespace=None):
        if args is None:
            args = sys.argv[1:]

        if len(args) > 0 and self._subparsers_action and not args[0].startswith("-"):
            command_prefix = args[0]
            resolved, suggestions = resolve_command(command_prefix)

            if resolved:
                args = [resolved] + list(args[1:])
            elif suggestions:
                self._show_ambiguous_error(command_prefix, suggestions)

        return super().parse_args(args, namespace)

    def _show_ambiguous_error(self, prefix: str, suggestions: List[str]):
        error_lines = [f"ambiguous command: '{prefix}'", "\nDid you mean one of these?"]
        for cmd in sorted(suggestions):
            error_lines.append(f"  {cmd}")
        self.error("\n".join(error_lines))


def create_parser():
    """Create the argument parser."""
    parser = PrefixArgumentParser(
        prog="icukit",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG)",
    )

    subparsers = parser.add_subparsers(
        title="Available Commands",
        dest="command",
        metavar="<command>",
    )

    # Register commands (alphabetical order)
    register_command("alpha-index", ["index", "aindex", "ai"])
    AlphaIndexCommand.add_subparser(subparsers)

    register_command("bidi", ["bi", "dir"])
    BidiCommand.add_subparser(subparsers)

    register_command("break", ["br", "brk"])
    BreakerCommand.add_subparser(subparsers)

    register_command("calendar", ["cal"])
    CalendarCommand.add_subparser(subparsers)

    register_command("collate", ["col"])
    CollatorCommand.add_subparser(subparsers)

    register_command("compact", ["cmp", "abbrev"])
    CompactCommand.add_subparser(subparsers)

    register_command("datetime", ["dt", "date"])
    DateTimeCommand.add_subparser(subparsers)

    register_command("discover", ["disc", "features"])
    DiscoverCommand.add_subparser(subparsers)

    register_command("displayname", ["dn", "name", "display"])
    DisplayNameCommand.add_subparser(subparsers)

    register_command("duration", ["dur"])
    DurationCommand.add_subparser(subparsers)

    register_command("help", ["h", "?"])
    add_help_subparser(subparsers)

    register_command("idna", ["punycode", "idn"])
    IDNACommand.add_subparser(subparsers)

    register_command("listfmt", ["lf", "listformat"])
    ListFmtCommand.add_subparser(subparsers)

    register_command("locale", ["loc", "l"])
    LocaleCommand.add_subparser(subparsers)

    register_command("measure", ["meas", "unit"])
    MeasureCommand.add_subparser(subparsers)

    register_command("message", ["msg"])
    MessageCommand.add_subparser(subparsers)

    register_command("parse", ["p"])
    ParseCommand.add_subparser(subparsers)

    register_command("plural", ["pl", "plr"])
    PluralCommand.add_subparser(subparsers)

    register_command("regex", ["re", "rx"])
    RegexCommand.add_subparser(subparsers)

    register_command("region", ["reg", "country"])
    RegionCommand.add_subparser(subparsers)

    register_command("script", ["sc"])
    ScriptCommand.add_subparser(subparsers)

    register_command("search", ["find"])
    SearchCommand.add_subparser(subparsers)

    register_command("sort", [])
    SortCommand.add_subparser(subparsers)

    register_command("spoof", ["confusable", "homoglyph"])
    SpoofCommand.add_subparser(subparsers)

    register_command("timezone", ["tz", "time"])
    TimezoneCommand.add_subparser(subparsers)

    register_command("transliterate", ["tr", "trans"])
    TransliterateCommand.add_subparser(subparsers)

    register_command("unicode", ["uni", "u", "char"])
    UnicodeCommand.add_subparser(subparsers)

    return parser


def main():
    """Main entry point for the icukit CLI."""
    parser = create_parser()

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()

    verbose = getattr(args, "verbose", 0)
    setup_logging(verbose)

    if hasattr(args, "func"):
        args._parser = parser
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
