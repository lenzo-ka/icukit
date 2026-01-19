"""Calendar CLI command."""

import argparse

from ...calendar import get_calendar_info, is_valid_calendar, list_calendars, list_calendars_info
from ...errors import CalendarError
from ...formatters import print_output
from ..subcommand_base import SubcommandBase, handles_errors


class CalendarCommand(SubcommandBase):
    """Calendar system information command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the calendar command with its subcommands."""
        parser = subparsers.add_parser(
            "calendar",
            help="Query calendar systems",
            description="""
Query available calendar systems (Gregorian, Buddhist, Hebrew, Islamic, etc.).

Calendar types include:
  gregorian  - Western standard calendar
  buddhist   - Thai Buddhist calendar
  chinese    - Chinese lunar calendar
  hebrew     - Hebrew/Jewish calendar
  islamic    - Islamic/Hijri calendar (multiple variants)
  japanese   - Japanese Imperial calendar
  persian    - Persian/Jalali calendar

Examples:
  # List all calendar types
  icukit calendar list
  icukit cal list

  # Get info about a calendar
  icukit cal info hebrew
  icukit cal info islamic --json
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List calendar types",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get information about a calendar type",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument(
            "-s", "--short", action="store_true", help="Show only calendar type names"
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        parser.add_argument("calendar", help="Calendar type (e.g., gregorian, hebrew)")
        cls._add_output_options(parser)

    @classmethod
    @handles_errors(CalendarError)
    def cmd_list(cls, args):
        """List calendar types."""
        as_json, headers = cls._get_output_flags(args)
        return cls._run_list(
            args,
            list_calendars,
            list_calendars_info,
            columns=["type", "description"],
            headers=headers,
            as_json=as_json,
            short=getattr(args, "short", False),
        )

    @classmethod
    @handles_errors(CalendarError)
    def cmd_info(cls, args):
        """Get information about a calendar type."""
        if not is_valid_calendar(args.calendar):
            raise CalendarError(
                f"Unknown calendar type: {args.calendar}. "
                f"Available types: {', '.join(list_calendars())}"
            )

        info = get_calendar_info(args.calendar)
        as_json, headers = cls._get_output_flags(args)

        print_output(
            [info],
            as_json=as_json,
            columns=["type", "icu_type", "description"],
            headers=headers,
        )
        return 0
