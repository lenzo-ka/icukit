"""CLI command for confusable/homoglyph detection."""

import argparse

from ...errors import SpoofError
from ...formatters import print_output
from ...spoof import are_confusable, check_string, get_confusable_info, get_skeleton
from ..subcommand_base import SubcommandBase, handles_errors


class SpoofCommand(SubcommandBase):
    """Confusable and homoglyph detection."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the spoof command with its subcommands."""
        parser = subparsers.add_parser(
            "spoof",
            aliases=["confusable", "homoglyph"],
            help="Detect confusable/homoglyph strings",
            description="""
Detect visually confusable strings using ICU's SpoofChecker.

Useful for security applications to detect phishing attempts where
attackers use lookalike characters (e.g., Cyrillic 'а' vs Latin 'a').

Examples:
  # Check if two strings are confusable
  icukit spoof compare 'paypal' 'pаypal'

  # Get skeleton form (normalized for comparison)
  icukit spoof skeleton 'pаypal'

  # Check a string for suspicious characters
  icukit spoof check 'pаypal'

  # Detailed confusability info
  icukit spoof info 'paypal' 'pаypal' --json
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "compare": {
                    "aliases": ["cmp", "c"],
                    "help": "Check if two strings are confusable",
                    "func": cls.cmd_compare,
                    "configure": cls._configure_compare,
                },
                "skeleton": {
                    "aliases": ["skel", "s"],
                    "help": "Get skeleton form of a string",
                    "func": cls.cmd_skeleton,
                    "configure": cls._configure_skeleton,
                },
                "check": {
                    "aliases": ["chk"],
                    "help": "Check string for suspicious characters",
                    "func": cls.cmd_check,
                    "configure": cls._configure_check,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get detailed confusability info",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_compare(cls, parser):
        """Configure compare subcommand."""
        parser.add_argument("string1", help="First string")
        parser.add_argument("string2", help="Second string")

    @classmethod
    def _configure_skeleton(cls, parser):
        """Configure skeleton subcommand."""
        parser.add_argument("text", help="Text to get skeleton for")

    @classmethod
    def _configure_check(cls, parser):
        """Configure check subcommand."""
        parser.add_argument("text", help="Text to check")
        cls._add_output_options(parser)

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        parser.add_argument("string1", help="First string")
        parser.add_argument("string2", help="Second string")
        cls._add_output_options(parser)

    @classmethod
    @handles_errors(SpoofError)
    def cmd_compare(cls, args):
        """Check if two strings are confusable."""
        result = are_confusable(args.string1, args.string2)
        if result:
            print("confusable")
            return 0
        else:
            print("not confusable")
            return 1

    @classmethod
    @handles_errors(SpoofError)
    def cmd_skeleton(cls, args):
        """Get skeleton form of a string."""
        result = get_skeleton(args.text)
        print(result)
        return 0

    @classmethod
    @handles_errors(SpoofError)
    def cmd_check(cls, args):
        """Check string for suspicious characters."""
        result = check_string(args.text)
        if getattr(args, "json", False):
            print_output(result, as_json=True)
        else:
            if result["is_suspicious"]:
                print("suspicious")
                issues = []
                if result["mixed_script"]:
                    issues.append("mixed_script")
                if result["whole_script"]:
                    issues.append("whole_script")
                if result["invisible"]:
                    issues.append("invisible")
                if result["mixed_numbers"]:
                    issues.append("mixed_numbers")
                if issues:
                    print(f"issues: {', '.join(issues)}")
            else:
                print("clean")
        return 0 if not result["is_suspicious"] else 1

    @classmethod
    @handles_errors(SpoofError)
    def cmd_info(cls, args):
        """Get detailed confusability info."""
        result = get_confusable_info(args.string1, args.string2)
        if getattr(args, "json", False):
            print_output(result, as_json=True)
        else:
            print(f"confusable: {result['confusable']}")
            print(f"type: {result['type']} ({', '.join(result['type_names']) or 'none'})")
            print(f"skeleton1: {result['skeleton1']}")
            print(f"skeleton2: {result['skeleton2']}")
            print(f"same_skeleton: {result['same_skeleton']}")
        return 0
