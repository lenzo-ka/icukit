"""CLI command for alphabetic index buckets."""

import argparse

from ...alpha_index import create_index_buckets, get_bucket_for_name, get_bucket_labels
from ...errors import AlphaIndexError
from ...formatters import print_output
from ..subcommand_base import SubcommandBase, handles_errors


class AlphaIndexCommand(SubcommandBase):
    """Alphabetic index buckets for sorted lists."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the alpha-index command with its subcommands."""
        parser = subparsers.add_parser(
            "alpha-index",
            aliases=["index", "aindex", "ai"],
            help="Alphabetic index buckets (A-Z)",
            description="""
Create locale-aware alphabetic index buckets for sorted lists.

Organizes items into A-Z style buckets appropriate for the locale
(e.g., A-Z for English, あかさたな for Japanese hiragana index).

Examples:
  # Create buckets from names
  echo -e 'Alice\\nBob\\nCarol\\nZebra' | icukit alpha-index buckets

  # Get bucket labels for a locale
  icukit alpha-index labels ja_JP

  # Get bucket for a specific name
  icukit alpha-index bucket Alice

  # JSON output
  echo -e 'Alice\\nBob' | icukit alpha-index buckets --json
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "buckets": {
                    "aliases": ["b", "create"],
                    "help": "Create index buckets from items",
                    "func": cls.cmd_buckets,
                    "configure": cls._configure_buckets,
                },
                "labels": {
                    "aliases": ["l", "ls"],
                    "help": "List bucket labels for a locale",
                    "func": cls.cmd_labels,
                    "configure": cls._configure_labels,
                },
                "bucket": {
                    "aliases": ["get", "g"],
                    "help": "Get bucket label for a name",
                    "func": cls.cmd_bucket,
                    "configure": cls._configure_bucket,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_buckets(cls, parser):
        """Configure buckets subcommand."""
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for bucket labels (default: en_US)",
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_labels(cls, parser):
        """Configure labels subcommand."""
        parser.add_argument(
            "locale",
            nargs="?",
            default="en_US",
            help="Locale for bucket labels (default: en_US)",
        )

    @classmethod
    def _configure_bucket(cls, parser):
        """Configure bucket subcommand."""
        parser.add_argument("name", help="Name to get bucket for")
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale (default: en_US)",
        )

    @classmethod
    @handles_errors(AlphaIndexError)
    def cmd_buckets(cls, args):
        """Create index buckets from items."""
        text = cls._read_input(args)
        if not text:
            return 0

        items = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if not items:
            return 0

        buckets = create_index_buckets(items, args.locale)

        if getattr(args, "json", False):
            print_output(buckets, as_json=True)
        else:
            for label, names in buckets.items():
                print(f"[{label}]")
                for name in names:
                    print(f"  {name}")
        return 0

    @classmethod
    @handles_errors(AlphaIndexError)
    def cmd_labels(cls, args):
        """List bucket labels for a locale."""
        labels = get_bucket_labels(args.locale)
        for label in labels:
            print(label)
        return 0

    @classmethod
    @handles_errors(AlphaIndexError)
    def cmd_bucket(cls, args):
        """Get bucket label for a name."""
        label = get_bucket_for_name(args.name, args.locale)
        print(label)
        return 0
