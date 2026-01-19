"""CLI command for duration formatting."""

import argparse
import sys

from ...duration import WIDTH_NARROW, WIDTH_SHORT, WIDTH_WIDE, DurationFormatter, parse_iso_duration
from ...errors import DurationError
from ...formatters import print_output
from ..subcommand_base import SubcommandBase


class DurationCommand(SubcommandBase):
    """Duration formatting command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the duration command with its subcommands."""
        parser = subparsers.add_parser(
            "duration",
            help="Format time durations with locale awareness",
            description="""
Format time durations with proper locale conventions.

Width Styles:
  WIDE   - "2 hours, 30 minutes, 15 seconds"
  SHORT  - "2 hr, 30 min, 15 sec"
  NARROW - "2h 30m 15s"

Input Formats:
  - Total seconds: 3661
  - ISO 8601: P2DT3H30M (2 days, 3 hours, 30 minutes)
  - Components: --hours 2 --minutes 30

Examples:
  # Format from total seconds
  icukit duration format 3661
  # → 1 hour, 1 minute, 1 second

  icukit duration format 3661 --width SHORT
  # → 1 hr, 1 min, 1 sec

  icukit duration format 3661 --locale de_DE
  # → 1 Stunde, 1 Minute und 1 Sekunde

  # Format with individual components
  icukit duration format --hours 2 --minutes 30
  # → 2 hours, 30 minutes

  # Format ISO 8601 duration
  icukit duration iso P2DT3H30M
  # → 2 days, 3 hours, 30 minutes

  icukit duration iso PT1H30M15S --locale ja_JP
  # → 1時間30分15秒

  # Parse ISO 8601 (show components)
  icukit duration parse P2DT3H30M
  # → days=2, hours=3, minutes=30
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "format": {
                    "aliases": ["f", "fmt"],
                    "help": "Format a duration",
                    "configure": cls._configure_format,
                    "func": cls.cmd_format,
                },
                "iso": {
                    "aliases": ["i"],
                    "help": "Format an ISO 8601 duration string",
                    "configure": cls._configure_iso,
                    "func": cls.cmd_iso,
                },
                "parse": {
                    "aliases": ["p"],
                    "help": "Parse an ISO 8601 duration to components",
                    "configure": cls._configure_parse,
                    "func": cls.cmd_parse,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_format(cls, parser):
        """Configure the format subcommand."""
        parser.add_argument(
            "seconds",
            type=float,
            nargs="?",
            help="Total seconds (optional if using component flags)",
        )
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-w",
            "--width",
            choices=[WIDTH_WIDE, WIDTH_SHORT, WIDTH_NARROW],
            default=WIDTH_WIDE,
            help="Width style (default: WIDE)",
        )
        # Component arguments
        parser.add_argument("--years", type=float, default=0, help="Years")
        parser.add_argument("--months", type=float, default=0, help="Months")
        parser.add_argument("--weeks", type=float, default=0, help="Weeks")
        parser.add_argument("--days", type=float, default=0, help="Days")
        parser.add_argument("--hours", type=float, default=0, help="Hours")
        parser.add_argument("--minutes", type=float, default=0, help="Minutes")

    @classmethod
    def _configure_iso(cls, parser):
        """Configure the iso subcommand."""
        parser.add_argument(
            "duration",
            help="ISO 8601 duration string (e.g., P2DT3H30M)",
        )
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-w",
            "--width",
            choices=[WIDTH_WIDE, WIDTH_SHORT, WIDTH_NARROW],
            default=WIDTH_WIDE,
            help="Width style (default: WIDE)",
        )

    @classmethod
    def _configure_parse(cls, parser):
        """Configure the parse subcommand."""
        parser.add_argument(
            "duration",
            help="ISO 8601 duration string to parse",
        )
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def cmd_format(cls, args):
        """Format a duration."""
        try:
            fmt = DurationFormatter(args.locale, args.width)

            # Check if any component flags were provided
            has_components = any(
                [
                    args.years,
                    args.months,
                    args.weeks,
                    args.days,
                    args.hours,
                    args.minutes,
                ]
            )

            if args.seconds is not None:
                if has_components:
                    # seconds is the seconds component, not total
                    result = fmt.format(
                        seconds=args.seconds,
                        minutes=args.minutes,
                        hours=args.hours,
                        days=args.days,
                        weeks=args.weeks,
                        months=args.months,
                        years=args.years,
                    )
                else:
                    # seconds is total seconds to decompose
                    result = fmt.format(seconds=args.seconds)
            elif has_components:
                result = fmt.format(
                    seconds=0,
                    minutes=args.minutes,
                    hours=args.hours,
                    days=args.days,
                    weeks=args.weeks,
                    months=args.months,
                    years=args.years,
                )
            else:
                print(
                    "Error: Provide seconds or component flags (--hours, --minutes, etc.)",
                    file=sys.stderr,
                )
                return 1

            print(result)
            return 0
        except DurationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_iso(cls, args):
        """Format an ISO 8601 duration string."""
        try:
            fmt = DurationFormatter(args.locale, args.width)
            result = fmt.format_iso(args.duration)
            print(result)
            return 0
        except DurationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_parse(cls, args):
        """Parse an ISO 8601 duration to components."""
        try:
            components = parse_iso_duration(args.duration)

            if args.json:
                print_output([components], as_json=True)
            else:
                # Print non-zero components
                parts = []
                for key in ["years", "months", "weeks", "days", "hours", "minutes", "seconds"]:
                    value = components[key]
                    if value:
                        if value == int(value):
                            parts.append(f"{key}={int(value)}")
                        else:
                            parts.append(f"{key}={value}")
                if parts:
                    print(", ".join(parts))
                else:
                    print("(empty duration)")
            return 0
        except DurationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
