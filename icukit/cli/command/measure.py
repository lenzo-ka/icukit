"""CLI command for measurement formatting."""

import argparse
import sys

from ...errors import MeasureError
from ...formatters import print_output
from ...measure import (
    WIDTH_NARROW,
    WIDTH_SHORT,
    WIDTH_WIDE,
    MeasureFormatter,
    can_convert,
    get_unit_info,
    get_units_by_type,
    list_unit_types,
    list_units,
)
from ..subcommand_base import SubcommandBase


class MeasureCommand(SubcommandBase):
    """Measurement formatting command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the measure command with its subcommands."""
        parser = subparsers.add_parser(
            "measure",
            help="Format measurements with locale-aware units",
            description="""
Format measurements with locale-appropriate unit names.

Width styles:
  WIDE   - "5.5 kilometers" (full unit names)
  SHORT  - "5.5 km" (abbreviated)
  NARROW - "5.5km" (minimal)

Examples:
  # Format a measurement (abbreviations work: km, mi, C, F, etc.)
  icukit measure format 5.5 kilometer
  icukit measure format 5.5 km
  icukit measure format 100 fahrenheit --width SHORT

  # Convert between units
  icukit measure convert 10 km mi
  icukit measure convert 100 C F
  icukit measure convert 1 lb kg

  # Compound measurements
  icukit measure sequence '5 foot, 10 inch'
  icukit measure sequence '1 hour, 30 minute'

  # Format for locale usage (converts to preferred units)
  icukit measure usage 100 km --usage road --locale en_US

  # Unit info and compatibility
  icukit measure info kilometer
  icukit measure check km mi

  # Format a range
  icukit measure range 5 10 kilometer

  # List unit types and units
  icukit measure types
  icukit measure units --type length
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "format": {
                    "aliases": ["f", "fmt"],
                    "help": "Format a measurement",
                    "configure": cls._configure_format,
                    "func": cls.cmd_format,
                },
                "convert": {
                    "aliases": ["c", "conv"],
                    "help": "Convert between units",
                    "configure": cls._configure_convert,
                    "func": cls.cmd_convert,
                },
                "range": {
                    "aliases": ["r"],
                    "help": "Format a measurement range",
                    "configure": cls._configure_range,
                    "func": cls.cmd_range,
                },
                "types": {
                    "aliases": ["t"],
                    "help": "List unit types",
                    "configure": cls._configure_types,
                    "func": cls.cmd_types,
                },
                "units": {
                    "aliases": ["u", "list"],
                    "help": "List units",
                    "configure": cls._configure_units,
                    "func": cls.cmd_units,
                },
                "sequence": {
                    "aliases": ["seq", "compound"],
                    "help": "Format compound measurements (5 ft 10 in)",
                    "configure": cls._configure_sequence,
                    "func": cls.cmd_sequence,
                },
                "usage": {
                    "aliases": ["use"],
                    "help": "Format with locale-preferred units",
                    "configure": cls._configure_usage,
                    "func": cls.cmd_usage,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get unit information",
                    "configure": cls._configure_info,
                    "func": cls.cmd_info,
                },
                "check": {
                    "aliases": ["compat"],
                    "help": "Check if units can convert",
                    "configure": cls._configure_check,
                    "func": cls.cmd_check,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_format(cls, parser):
        """Configure the format subcommand."""
        parser.add_argument("value", type=float, help="Numeric value")
        parser.add_argument("unit", help="Unit name (e.g., kilometer, fahrenheit)")
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
    def _configure_convert(cls, parser):
        """Configure the convert subcommand."""
        parser.add_argument("value", type=float, help="Value to convert")
        parser.add_argument("from_unit", help="Source unit (e.g., kilometer)")
        parser.add_argument("to_unit", help="Target unit (e.g., mile)")
        parser.add_argument(
            "-l",
            "--locale",
            default="en_US",
            help="Locale for formatted output (default: en_US)",
        )
        parser.add_argument(
            "-w",
            "--width",
            choices=[WIDTH_WIDE, WIDTH_SHORT, WIDTH_NARROW],
            default=WIDTH_SHORT,
            help="Width style for formatted output (default: SHORT)",
        )
        parser.add_argument(
            "-r",
            "--raw",
            action="store_true",
            help="Output raw number only (no formatting)",
        )

    @classmethod
    def _configure_range(cls, parser):
        """Configure the range subcommand."""
        parser.add_argument("low", type=float, help="Low value")
        parser.add_argument("high", type=float, help="High value")
        parser.add_argument("unit", help="Unit name")
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
    def _configure_types(cls, parser):
        """Configure the types subcommand."""
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _configure_units(cls, parser):
        """Configure the units subcommand."""
        parser.add_argument(
            "-t",
            "--type",
            help="Filter by unit type (e.g., length, mass, temperature)",
        )
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def cmd_format(cls, args):
        """Format a measurement."""
        try:
            fmt = MeasureFormatter(args.locale, args.width)
            result = fmt.format(args.value, args.unit)
            print(result)
            return 0
        except MeasureError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_convert(cls, args):
        """Convert between units."""
        try:
            fmt = MeasureFormatter(args.locale, args.width)
            converted = fmt.convert(args.value, args.from_unit, args.to_unit)

            if args.raw:
                print(converted)
            else:
                result = fmt.format(converted, args.to_unit)
                print(result)
            return 0
        except MeasureError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_range(cls, args):
        """Format a measurement range."""
        try:
            fmt = MeasureFormatter(args.locale, args.width)
            result = fmt.format_range(args.low, args.high, args.unit)
            print(result)
            return 0
        except MeasureError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_types(cls, args):
        """List unit types."""
        types = list_unit_types()
        units_by_type = get_units_by_type()

        if args.json:
            print_output(
                [{"type": t, "unit_count": len(units_by_type[t])} for t in types],
                columns=["type", "unit_count"],
                json_output=True,
            )
        else:
            for t in types:
                count = len(units_by_type[t])
                print(f"{t:<15} ({count} units)")
        return 0

    @classmethod
    def cmd_units(cls, args):
        """List units."""
        try:
            unit_type = getattr(args, "type", None)
            units_by_type = get_units_by_type()

            if unit_type:
                units = list_units(unit_type)
                data = [{"unit": u, "type": unit_type} for u in units]
            else:
                # Group by type
                data = []
                for t in sorted(units_by_type.keys()):
                    for u in sorted(units_by_type[t]):
                        data.append({"unit": u, "type": t})

            if args.json:
                print_output(data, columns=["unit", "type"], json_output=True)
            else:
                if unit_type:
                    for item in data:
                        print(item["unit"])
                else:
                    current_type = None
                    for item in data:
                        if item["type"] != current_type:
                            if current_type is not None:
                                print()
                            print(f"{item['type']}:")
                            current_type = item["type"]
                        print(f"  {item['unit']}")
            return 0
        except MeasureError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def _configure_sequence(cls, parser):
        """Configure the sequence subcommand."""
        parser.add_argument(
            "measures",
            help="Comma-separated measures (e.g., '5 foot, 10 inch')",
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
    def _configure_usage(cls, parser):
        """Configure the usage subcommand."""
        parser.add_argument("value", type=float, help="Numeric value")
        parser.add_argument("unit", help="Unit name or abbreviation")
        parser.add_argument(
            "-u",
            "--usage",
            default="default",
            help="Usage context (default, road, person-height, weather, etc.)",
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
            default=WIDTH_SHORT,
            help="Width style (default: SHORT)",
        )

    @classmethod
    def _configure_info(cls, parser):
        """Configure the info subcommand."""
        parser.add_argument("unit", help="Unit name or abbreviation")
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _configure_check(cls, parser):
        """Configure the check subcommand."""
        parser.add_argument("from_unit", help="Source unit")
        parser.add_argument("to_unit", help="Target unit")

    @classmethod
    def cmd_sequence(cls, args):
        """Format a sequence of measurements."""
        try:
            # Parse "5 foot, 10 inch" format
            measures = []
            for part in args.measures.split(","):
                part = part.strip()
                tokens = part.split()
                if len(tokens) >= 2:
                    value = float(tokens[0])
                    unit = tokens[1]
                    measures.append((value, unit))

            if not measures:
                print("Error: No valid measures found", file=sys.stderr)
                return 1

            fmt = MeasureFormatter(args.locale, args.width)
            result = fmt.format_sequence(measures)
            print(result)
            return 0
        except (ValueError, MeasureError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_usage(cls, args):
        """Format with locale-preferred units."""
        try:
            fmt = MeasureFormatter(args.locale, args.width)
            result = fmt.format_for_usage(args.value, args.unit, args.usage)
            print(result)
            return 0
        except MeasureError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_info(cls, args):
        """Get unit information."""
        try:
            info = get_unit_info(args.unit)
            if args.json:
                print_output([info], columns=list(info.keys()), json_output=True)
            else:
                for key, value in info.items():
                    print(f"{key}: {value}")
            return 0
        except MeasureError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_check(cls, args):
        """Check if units can convert."""
        try:
            result = can_convert(args.from_unit, args.to_unit)
            if result:
                print(f"Yes, {args.from_unit} can convert to {args.to_unit}")
            else:
                print(f"No, {args.from_unit} cannot convert to {args.to_unit}")
            return 0 if result else 1
        except MeasureError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
