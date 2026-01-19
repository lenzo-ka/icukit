"""Region CLI command."""

import argparse
import sys

from ...errors import RegionError
from ...formatters import print_output
from ...region import (
    get_contained_regions,
    get_region_info,
    list_region_types,
    list_regions,
    list_regions_info,
)
from ..subcommand_base import SubcommandBase, handles_errors


class RegionCommand(SubcommandBase):
    """Region information command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the region command with its subcommands."""
        parser = subparsers.add_parser(
            "region",
            help="Query countries, territories, and regions",
            description="""
Query countries, territories, continents, and their relationships.

Region types:
  territory   - Countries and territories (US, FR, JP, ...)
  continent   - Continents (Africa, Americas, Asia, Europe, Oceania)
  subcontinent - Subcontinental regions (Northern America, ...)
  grouping    - Economic/political groupings (EU, UN, ...)
  world       - The world (001)

Examples:
  # List all countries/territories
  icukit region list

  # List continents
  icukit region list --type continent

  # Get info about a region
  icukit region info US
  icukit region info FR --json

  # What regions are in the Americas?
  icukit region contains 019

  # List region types
  icukit region list types
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List regions or region types",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get information about a region",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
                "contains": {
                    "aliases": ["c", "in"],
                    "help": "List regions contained by a region",
                    "func": cls.cmd_contains,
                    "configure": cls._configure_contains,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument(
            "what",
            nargs="?",
            choices=["regions", "types"],
            default="regions",
            help="What to list (default: regions)",
        )
        parser.add_argument(
            "--type",
            "-t",
            choices=["territory", "continent", "subcontinent", "grouping", "world"],
            default="territory",
            help="Region type filter (default: territory)",
        )
        parser.add_argument("-s", "--short", action="store_true", help="Show only region codes")
        cls._add_output_options(parser)

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        parser.add_argument("code", help="Region code (e.g., US, FR, 001)")
        parser.add_argument(
            "-x",
            "--extended",
            action="store_true",
            help="Include extended attributes (contained_regions)",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_contains(cls, parser):
        """Configure contains subcommand."""
        parser.add_argument("code", help="Region code to get contained regions for")
        cls._add_output_options(parser)

    # Column definitions
    INFO_COLUMNS = ["code", "name", "numeric_code", "type", "containing_region"]
    EXTENDED_COLUMNS = ["contained_regions"]

    @classmethod
    @handles_errors(RegionError)
    def cmd_list(cls, args):
        """List regions or region types."""
        what = getattr(args, "what", "regions")
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        if what == "types":
            data = list_region_types()
            print_output(
                data,
                as_json=as_json,
                columns=["type", "description"],
                headers=not no_header,
            )
            return 0

        # Default: list regions
        region_type = getattr(args, "type", "territory")
        short = getattr(args, "short", False)

        if short:
            codes = list_regions(region_type)
            print_output(codes, as_json=as_json)
        else:
            data = list_regions_info(region_type)
            print_output(
                data,
                as_json=as_json,
                columns=["code", "name", "numeric_code", "containing_region"],
                headers=not no_header,
            )
        return 0

    @classmethod
    def cmd_info(cls, args):
        """Get information about a region."""
        extended = getattr(args, "extended", False)
        info = get_region_info(args.code, extended=extended)
        if info is None:
            print(f"Error: Unknown region: {args.code}", file=sys.stderr)
            return 1

        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        print_output(
            [info],
            as_json=as_json,
            columns=cls.INFO_COLUMNS,
            headers=not no_header,
            extended_columns=cls.EXTENDED_COLUMNS if extended else None,
        )
        return 0

    @classmethod
    def cmd_contains(cls, args):
        """List regions contained by a region."""
        contained = get_contained_regions(args.code)
        if not contained:
            # Check if region exists
            info = get_region_info(args.code)
            if info is None:
                print(f"Error: Unknown region: {args.code}", file=sys.stderr)
                return 1
            # Region exists but has no contained regions
            print(f"Region {args.code} contains no subregions", file=sys.stderr)
            return 0

        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        # Get full info for each contained region
        data = [get_region_info(code) for code in contained]
        data = [d for d in data if d]  # Filter None

        print_output(
            data,
            as_json=as_json,
            columns=["code", "name", "type"],
            headers=not no_header,
        )
        return 0
