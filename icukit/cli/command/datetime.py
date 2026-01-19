"""CLI command for date/time formatting."""

import argparse
import sys
from datetime import datetime

from ...calendar import list_calendars_info
from ...datetime import (
    PATTERNS,
    STYLE_FULL,
    STYLE_LONG,
    STYLE_MEDIUM,
    STYLE_NONE,
    STYLE_SHORT,
    WIDTH_ABBREVIATED,
    WIDTH_WIDE,
    DateTimeFormatter,
    get_am_pm_strings,
    get_date_symbols,
    get_era_names,
    get_month_names,
    get_weekday_names,
)
from ...errors import DateTimeError
from ...formatters import print_output
from ..subcommand_base import SubcommandBase


class DateTimeCommand(SubcommandBase):
    """Date/time formatting command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the datetime command with its subcommands."""
        parser = subparsers.add_parser(
            "datetime",
            help="Format dates and times with locale awareness",
            description="""
Format dates and times according to locale conventions.

Styles:
  FULL   - Monday, January 15, 2024 at 3:45:30 PM Eastern Standard Time
  LONG   - January 15, 2024 at 3:45:30 PM EST
  MEDIUM - Jan 15, 2024, 3:45:30 PM (default)
  SHORT  - 1/15/24, 3:45 PM

Examples:
  # Format current date/time
  icukit datetime format
  icukit datetime format --style SHORT

  # Format with custom pattern
  icukit datetime format --pattern 'EEEE, MMMM d, yyyy'

  # Format specific date
  icukit datetime format '2024-01-15T14:30:00' --locale de_DE

  # Different calendar systems
  icukit datetime format '2024-01-15' --calendar hebrew
  icukit datetime format '2024-01-15' --calendar islamic
  icukit datetime format '2024-01-15' --calendar buddhist

  # Relative time
  icukit datetime relative -1
  icukit datetime relative --hours 2

  # Date interval
  icukit datetime interval 2024-01-15 2024-01-20

  # Parse date string
  icukit datetime parse '1/15/24'

  # List patterns and calendars
  icukit datetime patterns
  icukit datetime calendars

  # Localized date symbols
  icukit datetime months --locale fr_FR
  icukit datetime months --locale de_DE --width abbreviated
  icukit datetime weekdays --locale ja_JP
  icukit datetime eras --locale en_US
  icukit datetime ampm --locale zh_CN
  icukit datetime symbols --locale ar_SA --json
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "format": {
                    "aliases": ["f", "fmt"],
                    "help": "Format a date/time",
                    "configure": cls._configure_format,
                    "func": cls.cmd_format,
                },
                "relative": {
                    "aliases": ["r", "rel"],
                    "help": "Show relative time (yesterday, in 2 hours)",
                    "configure": cls._configure_relative,
                    "func": cls.cmd_relative,
                },
                "interval": {
                    "aliases": ["i", "int"],
                    "help": "Format a date/time interval",
                    "configure": cls._configure_interval,
                    "func": cls.cmd_interval,
                },
                "parse": {
                    "aliases": ["p"],
                    "help": "Parse a date/time string",
                    "configure": cls._configure_parse,
                    "func": cls.cmd_parse,
                },
                "patterns": {
                    "aliases": ["pat"],
                    "help": "List pattern symbols",
                    "configure": cls._configure_patterns,
                    "func": cls.cmd_patterns,
                },
                "calendars": {
                    "aliases": ["cal"],
                    "help": "List available calendar systems",
                    "configure": cls._configure_calendars,
                    "func": cls.cmd_calendars,
                },
                "months": {
                    "aliases": ["mon"],
                    "help": "Get localized month names",
                    "configure": cls._configure_months,
                    "func": cls.cmd_months,
                },
                "weekdays": {
                    "aliases": ["wd", "days"],
                    "help": "Get localized weekday names",
                    "configure": cls._configure_weekdays,
                    "func": cls.cmd_weekdays,
                },
                "eras": {
                    "aliases": ["era"],
                    "help": "Get localized era names (BC/AD)",
                    "configure": cls._configure_eras,
                    "func": cls.cmd_eras,
                },
                "ampm": {
                    "aliases": ["am"],
                    "help": "Get localized AM/PM strings",
                    "configure": cls._configure_ampm,
                    "func": cls.cmd_ampm,
                },
                "symbols": {
                    "aliases": ["sym"],
                    "help": "Get all date/time symbols for a locale",
                    "configure": cls._configure_symbols,
                    "func": cls.cmd_symbols,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_format(cls, parser):
        """Configure the format subcommand."""
        parser.add_argument(
            "datetime",
            nargs="?",
            help="Date/time to format (ISO format, default: now)",
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
            choices=[STYLE_FULL, STYLE_LONG, STYLE_MEDIUM, STYLE_SHORT],
            help="Format style for both date and time",
        )
        parser.add_argument(
            "--date-style",
            choices=[STYLE_FULL, STYLE_LONG, STYLE_MEDIUM, STYLE_SHORT, STYLE_NONE],
            help="Date style (NONE for time-only)",
        )
        parser.add_argument(
            "--time-style",
            choices=[STYLE_FULL, STYLE_LONG, STYLE_MEDIUM, STYLE_SHORT, STYLE_NONE],
            help="Time style (NONE for date-only)",
        )
        parser.add_argument(
            "-p",
            "--pattern",
            help="Custom ICU pattern (e.g., 'yyyy-MM-dd HH:mm')",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system (gregorian, buddhist, hebrew, islamic, japanese, etc.)",
        )

    @classmethod
    def _configure_relative(cls, parser):
        """Configure the relative subcommand."""
        parser.add_argument(
            "offset",
            type=int,
            nargs="?",
            default=0,
            help="Day offset (negative for past)",
        )
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument("--hours", type=int, default=0, help="Hour offset")
        parser.add_argument("--minutes", type=int, default=0, help="Minute offset")
        parser.add_argument("--seconds", type=int, default=0, help="Second offset")

    @classmethod
    def _configure_interval(cls, parser):
        """Configure the interval subcommand."""
        parser.add_argument("start", help="Start date (ISO format)")
        parser.add_argument("end", help="End date (ISO format)")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-k",
            "--skeleton",
            default="yMMMd",
            help="Format skeleton (default: yMMMd)",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system",
        )

    @classmethod
    def _configure_parse(cls, parser):
        """Configure the parse subcommand."""
        parser.add_argument("text", help="Date/time string to parse")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-p",
            "--pattern",
            help="Expected pattern (tries common formats if not given)",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system",
        )

    @classmethod
    def _configure_patterns(cls, parser):
        """Configure the patterns subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale for examples (default: en_US)",
        )

    @classmethod
    def _configure_calendars(cls, parser):
        """Configure the calendars subcommand."""
        pass  # No options needed

    @classmethod
    def cmd_format(cls, args):
        """Format a date/time."""
        try:
            if args.datetime:
                dt = datetime.fromisoformat(args.datetime)
            else:
                dt = datetime.now()

            fmt = DateTimeFormatter(args.locale, calendar=args.calendar)
            result = fmt.format(
                dt,
                style=args.style,
                date_style=args.date_style,
                time_style=args.time_style,
                pattern=args.pattern,
            )
            print(result)
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Error: Invalid datetime: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_relative(cls, args):
        """Show relative time."""
        try:
            fmt = DateTimeFormatter(args.locale)
            result = fmt.format_relative(
                days=args.offset,
                hours=args.hours,
                minutes=args.minutes,
                seconds=args.seconds,
            )
            print(result)
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_interval(cls, args):
        """Format a date/time interval."""
        try:
            start = datetime.fromisoformat(args.start)
            end = datetime.fromisoformat(args.end)

            fmt = DateTimeFormatter(args.locale, calendar=args.calendar)
            result = fmt.format_interval(start, end, skeleton=args.skeleton)
            print(result)
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Error: Invalid datetime: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_parse(cls, args):
        """Parse a date/time string."""
        try:
            fmt = DateTimeFormatter(args.locale, calendar=args.calendar)
            dt = fmt.parse(args.text, pattern=args.pattern)
            print(dt.isoformat())
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_patterns(cls, args):
        """List pattern symbols."""
        symbols = [
            ("y", "Year", "yyyy=2024, yy=24"),
            ("M", "Month", "M=1, MM=01, MMM=Jan, MMMM=January"),
            ("d", "Day of month", "d=1, dd=01"),
            ("E", "Day of week", "E=Mon, EEEE=Monday"),
            ("h", "Hour (1-12)", "h=3, hh=03"),
            ("H", "Hour (0-23)", "H=15, HH=15"),
            ("m", "Minute", "m=5, mm=05"),
            ("s", "Second", "s=9, ss=09"),
            ("S", "Millisecond", "SSS=123"),
            ("a", "AM/PM", "AM, PM"),
            ("z", "Time zone", "z=PST, zzzz=Pacific Standard Time"),
            ("Z", "Zone offset", "-0800"),
            ("G", "Era", "AD, BC"),
            ("Q", "Quarter", "Q=2, QQ=02, QQQ=Q2"),
            ("w", "Week of year", "1-52"),
            ("D", "Day of year", "1-366"),
            ("'", "Literal text", "'at' -> at"),
        ]

        print("Pattern Symbols:")
        print()
        for sym, name, example in symbols:
            print(f"  {sym:<3} {name:<15} {example}")

        print()
        print("Named Patterns:")
        print()

        now = datetime.now()
        fmt = DateTimeFormatter(args.locale)
        for name, pattern in PATTERNS.items():
            try:
                example = fmt.format(now, pattern=pattern)
                print(f"  {name:<14} {pattern:<28} {example}")
            except DateTimeError:
                print(f"  {name:<14} {pattern:<28} (error)")

        return 0

    @classmethod
    def cmd_calendars(cls, args):
        """List available calendar systems."""
        print("Available Calendar Systems:")
        print()
        for info in list_calendars_info():
            print(f"  {info['type']:<20} {info['description']}")
        return 0

    # -------------------------------------------------------------------------
    # Date/Time Symbol Subcommands
    # -------------------------------------------------------------------------

    @classmethod
    def _configure_months(cls, parser):
        """Configure the months subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-w",
            "--width",
            choices=[WIDTH_WIDE, WIDTH_ABBREVIATED],
            default=WIDTH_WIDE,
            help="Name width: wide (January) or abbreviated (Jan)",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system (gregorian, hebrew, islamic, etc.)",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_weekdays(cls, parser):
        """Configure the weekdays subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-w",
            "--width",
            choices=[WIDTH_WIDE, WIDTH_ABBREVIATED],
            default=WIDTH_WIDE,
            help="Name width: wide (Sunday) or abbreviated (Sun)",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_eras(cls, parser):
        """Configure the eras subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-w",
            "--width",
            choices=[WIDTH_WIDE, WIDTH_ABBREVIATED],
            default=WIDTH_WIDE,
            help="Name width: wide (Before Christ) or abbreviated (BC)",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_ampm(cls, parser):
        """Configure the ampm subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_symbols(cls, parser):
        """Configure the symbols subcommand."""
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale (default: en_US)",
        )
        parser.add_argument(
            "-c",
            "--calendar",
            help="Calendar system",
        )
        cls._add_output_options(parser)

    @classmethod
    def cmd_months(cls, args):
        """Get localized month names."""
        try:
            months = get_month_names(
                args.locale,
                width=args.width,
                calendar=args.calendar,
            )

            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            rows = [{"index": i, "name": name} for i, name in enumerate(months, 1)]
            print_output(
                rows,
                as_json=as_json,
                columns=["index", "name"],
                headers=not no_header,
            )
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_weekdays(cls, args):
        """Get localized weekday names."""
        try:
            result = get_weekday_names(
                args.locale,
                width=args.width,
                calendar=args.calendar,
            )

            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            if as_json:
                print_output(result, as_json=True)
            else:
                rows = [
                    {
                        "index": i,
                        "name": name,
                        "first": "yes" if i == result["first_day_index"] else "",
                    }
                    for i, name in enumerate(result["names"])
                ]
                print_output(
                    rows,
                    as_json=False,
                    columns=["index", "name", "first"],
                    headers=not no_header,
                )
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_eras(cls, args):
        """Get localized era names."""
        try:
            eras = get_era_names(
                args.locale,
                width=args.width,
                calendar=args.calendar,
            )

            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            rows = [{"index": i, "name": era} for i, era in enumerate(eras)]
            print_output(
                rows,
                as_json=as_json,
                columns=["index", "name"],
                headers=not no_header,
            )
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_ampm(cls, args):
        """Get localized AM/PM strings."""
        try:
            strings = get_am_pm_strings(args.locale, calendar=args.calendar)

            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            rows = [
                {"period": "AM", "name": strings[0]},
                {"period": "PM", "name": strings[1]},
            ]
            print_output(
                rows,
                as_json=as_json,
                columns=["period", "name"],
                headers=not no_header,
            )
            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_symbols(cls, args):
        """Get all date/time symbols for a locale."""
        try:
            symbols = get_date_symbols(args.locale, calendar=args.calendar)

            as_json = getattr(args, "json", False)
            if as_json:
                print_output(symbols, as_json=True)
            else:
                # Flatten to TSV-friendly format
                rows = []

                # Months
                for i, (wide, abbrev) in enumerate(
                    zip(symbols["months"]["wide"], symbols["months"]["abbreviated"]), 1
                ):
                    rows.append(
                        {
                            "category": "month",
                            "index": i,
                            "wide": wide,
                            "abbreviated": abbrev,
                        }
                    )

                # Weekdays
                wd = symbols["weekdays"]
                for i, (wide, abbrev) in enumerate(zip(wd["wide"], wd["abbreviated"])):
                    rows.append(
                        {
                            "category": "weekday",
                            "index": i,
                            "wide": wide,
                            "abbreviated": abbrev,
                            "first": "yes" if i == wd["first_day_index"] else "",
                        }
                    )

                # Eras
                for i, (wide, abbrev) in enumerate(
                    zip(symbols["eras"]["wide"], symbols["eras"]["abbreviated"])
                ):
                    rows.append(
                        {
                            "category": "era",
                            "index": i,
                            "wide": wide,
                            "abbreviated": abbrev,
                        }
                    )

                # AM/PM
                rows.append(
                    {
                        "category": "am_pm",
                        "index": 0,
                        "wide": symbols["am_pm"][0],
                        "abbreviated": symbols["am_pm"][0],
                    }
                )
                rows.append(
                    {
                        "category": "am_pm",
                        "index": 1,
                        "wide": symbols["am_pm"][1],
                        "abbreviated": symbols["am_pm"][1],
                    }
                )

                print_output(
                    rows,
                    as_json=False,
                    columns=["category", "index", "wide", "abbreviated"],
                    headers=not getattr(args, "no_header", False),
                )

            return 0
        except DateTimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
