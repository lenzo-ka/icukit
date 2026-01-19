"""Script detection CLI command."""

import argparse
import sys

from ...errors import ScriptError
from ...formatters import print_output
from ...script import detect_script, detect_scripts, get_script_info, is_rtl, list_scripts_info
from ..base import open_output, process_input
from ..subcommand_base import SubcommandBase


class ScriptCommand(SubcommandBase):
    """Script detection and properties command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the script command with its subcommands."""
        parser = subparsers.add_parser(
            "script",
            help="Detect and query Unicode scripts",
            description="""
Detect writing systems (scripts) and query script properties.

Scripts include Latin, Greek, Cyrillic, Han, Arabic, Hebrew, and many more.

Examples:
  # Detect script of text
  echo 'Hello' | icukit script detect
  echo 'Ελληνικά' | icukit script detect
  icukit script detect -t '你好世界'

  # Detect all scripts in mixed text
  icukit script detect -t 'Hello Ελληνικά 你好' --all

  # Check if text is right-to-left
  icukit script rtl -t 'مرحبا'
  icukit script rtl -t 'Hello'

  # Get info about a script
  icukit script info Greek
  icukit script info Arabic --json

  # List all scripts
  icukit script list
  icukit script list --cased    # only cased scripts
  icukit script list --rtl      # only RTL scripts
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "detect": {
                    "aliases": ["d"],
                    "help": "Detect script of text",
                    "func": cls.cmd_detect,
                    "configure": cls._configure_detect,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get information about a script",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
                "rtl": {
                    "aliases": ["r"],
                    "help": "Check if text is right-to-left",
                    "func": cls.cmd_rtl,
                    "configure": cls._configure_rtl,
                },
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List all scripts",
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
        parser.add_argument("-a", "--all", action="store_true", help="Detect all scripts in text")
        cls._add_output_options(parser)

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        parser.add_argument("script", help="Script name (e.g., Greek, Latin, Han)")
        parser.add_argument(
            "-x",
            "--extended",
            action="store_true",
            help="Include extended attributes (sample_char)",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_rtl(cls, parser):
        """Configure rtl subcommand."""
        cls._add_input_options(parser)

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument("--cased", action="store_true", help="Only cased scripts")
        parser.add_argument("--rtl", action="store_true", help="Only RTL scripts")
        cls._add_output_options(parser)

    @classmethod
    def cmd_detect(cls, args):
        """Detect script of text."""
        try:
            detect_all = getattr(args, "all", False)
            as_json = getattr(args, "json", False)

            def processor(text):
                text = text.strip()
                if detect_all:
                    scripts = detect_scripts(text)
                    if as_json:
                        return None  # Handle in output
                    return "\n".join(scripts)
                else:
                    return detect_script(text)

            # For JSON output with --all, we need special handling
            if detect_all and as_json:
                text = cls._read_input(args).strip()
                scripts = detect_scripts(text)
                print_output(scripts, as_json=True)
                return 0

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, processor, output)
            return 0
        except ScriptError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Column definitions
    INFO_COLUMNS = ["code", "name", "is_cased", "is_rtl"]
    EXTENDED_COLUMNS = ["sample_char"]

    @classmethod
    def cmd_info(cls, args):
        """Get information about a script."""
        try:
            extended = getattr(args, "extended", False)
            info = get_script_info(args.script, extended=extended)
            if info is None:
                print(f"Error: Unknown script: {args.script}", file=sys.stderr)
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
        except ScriptError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_rtl(cls, args):
        """Check if text is right-to-left."""
        text = cls._read_input(args).strip()
        rtl = is_rtl(text)
        print("true" if rtl else "false")
        return 0 if rtl else 1  # Exit code indicates result

    @classmethod
    def cmd_list(cls, args):
        """List all scripts."""
        data = list_scripts_info()

        # Apply filters
        if getattr(args, "cased", False):
            data = [s for s in data if s["is_cased"]]
        if getattr(args, "rtl", False):
            data = [s for s in data if s["is_rtl"]]

        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        print_output(
            data,
            as_json=as_json,
            columns=["code", "name", "is_cased", "is_rtl"],
            headers=not no_header,
        )
        return 0
