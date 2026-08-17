"""CLI command for ICU MessageFormat."""

import argparse
import sys

from ...errors import MessageError
from ...message import format_message
from ..subcommand_base import SubcommandBase


class MessageCommand(SubcommandBase):
    """ICU MessageFormat command for localized string formatting."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the message command with its subcommands."""
        parser = subparsers.add_parser(
            "message",
            aliases=["msg"],
            help="Format localized messages with ICU MessageFormat",
            description="""
Format messages using ICU MessageFormat syntax.

Supports placeholders, plurals, selects, and number/date formatting.

Pattern syntax:
  {name}                              Simple placeholder
  {count, number}                     Number formatting
  {price, number, currency}           Currency formatting
  {date, date, short}                 Date formatting
  {count, plural, one {# item} other {# items}}   Plural rules
  {gender, select, male {He} female {She} other {They}}  Select

Examples:
  # Simple substitution
  icukit message format 'Hello, {name}!' --arg name=World

  # Plural rules (locale-aware)
  icukit message format '{count, plural, one {# item} other {# items}}' --arg count=5
  icukit message format '{count, plural, one {# item} other {# items}}' --arg count=1

  # Select (gender, etc.)
  icukit message format '{g, select, male {He} female {She} other {They}} liked it' --arg g=female

  # Number formatting
  icukit message format 'Total: {n, number, currency}' --arg n=1234.56 --locale de_DE

  # Multiple arguments
  icukit message format '{name} has {count, plural, one {# cat} other {# cats}}' \\
      --arg name=Alice --arg count=3

  # Russian plurals (1 кот, 2 кота, 5 котов)
  icukit message format '{n, plural, one {# кот} few {# кота} many {# котов} other {# кота}}' \\
      --arg n=5 --locale ru
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "format": {
                    "aliases": ["f", "fmt"],
                    "help": "Format a message with arguments",
                    "func": cls.cmd_format,
                    "configure": cls._configure_format,
                },
                "examples": {
                    "aliases": ["ex"],
                    "help": "Show example patterns",
                    "func": cls.cmd_examples,
                    "configure": lambda p: None,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_format(cls, parser):
        """Configure format subcommand."""
        parser.add_argument(
            "pattern",
            help="ICU message format pattern",
        )
        parser.add_argument(
            "-a",
            "--arg",
            action="append",
            dest="args",
            metavar="NAME=VALUE",
            help="Argument in name=value format (can be repeated)",
        )
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for formatting (default: en_US)",
        )

    @classmethod
    def _parse_args(cls, arg_list: list[str] | None) -> dict:
        """Parse name=value arguments into a dict."""
        result = {}
        if not arg_list:
            return result

        for arg in arg_list:
            if "=" not in arg:
                print(
                    f"Warning: Invalid argument format '{arg}', expected name=value",
                    file=sys.stderr,
                )
                continue
            name, value = arg.split("=", 1)
            # Try to convert to number if possible
            try:
                if "." in value:
                    result[name] = float(value)
                else:
                    result[name] = int(value)
            except ValueError:
                result[name] = value
        return result

    @classmethod
    def cmd_format(cls, args):
        """Format a message with arguments."""
        try:
            msg_args = cls._parse_args(args.args)
            result = format_message(args.pattern, msg_args, args.locale)
            print(result)
            return 0
        except MessageError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_examples(cls, args):
        """Show example patterns."""
        examples = [
            ("Simple placeholder", "Hello, {name}!", "name=World"),
            ("Number", "Count: {n, number}", "n=1234567"),
            ("Currency", "Price: {n, number, currency}", "n=99.99"),
            ("Percent", "Rate: {n, number, percent}", "n=0.15"),
            ("Plural (English)", "{n, plural, one {# item} other {# items}}", "n=1 or n=5"),
            (
                "Plural (Russian)",
                "{n, plural, one {# кот} few {# кота} many {# котов} other {# кота}}",
                "n=1,2,5,21",
            ),
            ("Select", "{g, select, male {He} female {She} other {They}}", "g=female"),
            (
                "Ordinal",
                "{n, selectordinal, one {#st} two {#nd} few {#rd} other {#th}}",
                "n=1,2,3,4",
            ),
            ("Combined", "{name} has {n, plural, one {# cat} other {# cats}}", "name=Alice n=3"),
        ]

        print("ICU MessageFormat Examples\n")
        print(f"{'Type':<20} {'Pattern':<60} {'Args':<20}")
        print("-" * 100)
        for name, pattern, args in examples:
            print(f"{name:<20} {pattern:<60} {args:<20}")

        print("\nTry: icukit message format '<pattern>' --arg <name>=<value>")
        return 0
