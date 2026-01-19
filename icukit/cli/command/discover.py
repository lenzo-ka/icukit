"""CLI command for discovering icukit features."""

import argparse

from ...discover import discover_features, get_api_info, search_features
from ...formatters import print_output
from ..subcommand_base import SubcommandBase


class DiscoverCommand(SubcommandBase):
    """Discover available icukit features and capabilities."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the discover command to the parser."""
        parser = subparsers.add_parser(
            "discover",
            help="Discover available features",
            description="""
Discover icukit's available features, API exports, and CLI commands.

Examples:
  # Show all features
  icukit discover all
  icukit discover

  # Show API details
  icukit discover api

  # Show CLI commands
  icukit discover cli

  # Search for features
  icukit discover search translit

  # JSON output
  icukit discover all --json
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "all": {
                    "aliases": ["a"],
                    "help": "Show all features (default)",
                    "func": cls.cmd_all,
                    "configure": cls._configure_all,
                },
                "api": {
                    "aliases": [],
                    "help": "Show API exports",
                    "func": cls.cmd_api,
                    "configure": cls._configure_output,
                },
                "cli": {
                    "aliases": ["commands", "cmds"],
                    "help": "Show CLI commands",
                    "func": cls.cmd_cli,
                    "configure": cls._configure_output,
                },
                "search": {
                    "aliases": ["s", "find"],
                    "help": "Search for features",
                    "func": cls.cmd_search,
                    "configure": cls._configure_search,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def run(cls, args):
        """Main entry point - default to 'all' if no subcommand."""
        if hasattr(args, "func") and args.func != cls.run:
            return args.func(args)
        # No subcommand - show all features
        args.json = False
        args.no_header = False
        return cls.cmd_all(args)

    @classmethod
    def _configure_all(cls, parser):
        cls._add_output_options(parser)

    @classmethod
    def _configure_output(cls, parser):
        cls._add_output_options(parser)

    @classmethod
    def _configure_search(cls, parser):
        parser.add_argument("query", help="Search query")
        cls._add_output_options(parser)

    @classmethod
    def cmd_all(cls, args):
        """Show all features."""
        features = discover_features()
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        if as_json:
            print_output(features, as_json=True)
            return 0

        # TSV-style output
        print("=== API Exports ===")
        cls._print_api_table(features, no_header)
        print()
        print("=== CLI Commands ===")
        cls._print_cli_table(features, no_header)
        return 0

    @classmethod
    def cmd_api(cls, args):
        """Show API exports."""
        features = discover_features()
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        if as_json:
            print_output(features["api"], as_json=True)
            return 0

        cls._print_api_table(features, no_header)
        return 0

    @classmethod
    def cmd_cli(cls, args):
        """Show CLI commands."""
        features = discover_features()
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        if as_json:
            print_output(features["cli"], as_json=True)
            return 0

        cls._print_cli_table(features, no_header)
        return 0

    @classmethod
    def cmd_search(cls, args):
        """Search for features."""
        results = search_features(args.query)
        as_json = getattr(args, "json", False)

        if as_json:
            print_output(results, as_json=True)
            return 0

        api_matches = results["api"]
        cli_matches = results["cli"]

        if not api_matches and not cli_matches:
            print(f"No features found matching '{args.query}'")
            return 1

        print(f"Search results for '{args.query}':")

        if api_matches:
            print(f"\nAPI ({len(api_matches)}):")
            for name in sorted(api_matches):
                info = get_api_info(name)
                if info:
                    sig = info.get("signature", "")
                    print(f"  {name}{sig}" if sig else f"  {name}")

        if cli_matches:
            print(f"\nCLI Commands ({len(cli_matches)}):")
            for cmd in sorted(cli_matches):
                print(f"  icukit {cmd}")

        return 0

    @classmethod
    def _print_api_table(cls, features, no_header):
        """Print API exports as TSV-style table."""
        api_exports = features["api"]["exports"]
        details = features["api"]["details"]

        data = []
        for name in sorted(api_exports):
            info = details.get(name, {})
            data.append(
                {
                    "name": name,
                    "type": info.get("type", "-"),
                    "signature": info.get("signature", "-"),
                }
            )

        print_output(data, columns=["name", "type", "signature"], headers=not no_header)

    @classmethod
    def _print_cli_table(cls, features, no_header):
        """Print CLI commands as TSV-style table."""
        cli_commands = features["cli"]["commands"]

        data = []
        for cmd_name in sorted(cli_commands.keys()):
            cmd_info = cli_commands[cmd_name]
            aliases = cmd_info.get("aliases", [])
            data.append(
                {
                    "command": cmd_name,
                    "aliases": ", ".join(aliases) if aliases else "-",
                    "prefix": cmd_info.get("minimal_prefix", "-"),
                }
            )

        print_output(data, columns=["command", "aliases", "prefix"], headers=not no_header)
