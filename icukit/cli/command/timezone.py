"""Timezone CLI command."""

import argparse
import sys

from ...errors import TimezoneError
from ...formatters import print_output
from ...timezone import (
    get_equivalent_timezones,
    get_timezone_info,
    list_timezones,
    list_timezones_info,
)
from ..subcommand_base import SubcommandBase, handles_errors


class TimezoneCommand(SubcommandBase):
    """Timezone information command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the timezone command with its subcommands."""
        parser = subparsers.add_parser(
            "timezone",
            help="Query timezone information",
            description="""
Query timezone data including offsets, DST rules, and display names.

Examples:
  # List all timezones
  icukit timezone list
  icukit tz list

  # List US timezones only
  icukit tz list --country US

  # Get info about a timezone
  icukit tz info America/New_York
  icukit tz info Europe/London --json

  # Get equivalent timezone IDs
  icukit tz equiv America/New_York
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List timezones",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get information about a timezone",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
                "equiv": {
                    "aliases": ["e", "eq"],
                    "help": "Get equivalent timezone IDs",
                    "func": cls.cmd_equiv,
                    "configure": cls._configure_equiv,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument(
            "--country",
            "-c",
            help="Filter by country code (e.g., US, DE, JP)",
        )
        parser.add_argument("-s", "--short", action="store_true", help="Show only timezone IDs")
        cls._add_output_options(parser)

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        parser.add_argument("timezone", help="Timezone ID (e.g., America/New_York)")
        parser.add_argument(
            "-x",
            "--extended",
            action="store_true",
            help="Include extended attributes (region, windows_id, equivalent_ids)",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_equiv(cls, parser):
        """Configure equiv subcommand."""
        parser.add_argument("timezone", help="Timezone ID to find equivalents for")
        cls._add_output_options(parser)

    # Column definitions
    INFO_COLUMNS = ["id", "offset_formatted", "uses_dst", "display_name"]
    EXTENDED_COLUMNS = ["region", "windows_id", "equivalent_ids"]

    @classmethod
    @handles_errors(TimezoneError)
    def cmd_list(cls, args):
        """List timezones."""
        country = getattr(args, "country", None)
        as_json, headers = cls._get_output_flags(args)

        return cls._run_list(
            args,
            lambda: list_timezones(country),
            lambda: list_timezones_info(country),
            columns=["id", "offset_formatted", "uses_dst", "display_name"],
            headers=headers,
            as_json=as_json,
            short=getattr(args, "short", False),
        )

    @classmethod
    @handles_errors(TimezoneError)
    def cmd_info(cls, args):
        """Get information about a timezone."""
        extended = getattr(args, "extended", False)
        info = get_timezone_info(args.timezone, extended=extended)
        if info is None:
            raise TimezoneError(f"Unknown timezone: {args.timezone}")

        as_json, headers = cls._get_output_flags(args)

        print_output(
            [info],
            as_json=as_json,
            columns=cls.INFO_COLUMNS,
            headers=headers,
            extended_columns=cls.EXTENDED_COLUMNS if extended else None,
        )
        return 0

    @classmethod
    @handles_errors(TimezoneError)
    def cmd_equiv(cls, args):
        """Get equivalent timezone IDs."""
        # Verify timezone exists
        info = get_timezone_info(args.timezone)
        if info is None:
            raise TimezoneError(f"Unknown timezone: {args.timezone}")

        equivs = get_equivalent_timezones(args.timezone)
        if not equivs:
            print(f"No equivalent timezones found for {args.timezone}", file=sys.stderr)
            return 0

        as_json, _ = cls._get_output_flags(args)
        print_output(equivs, as_json=as_json)
        return 0
