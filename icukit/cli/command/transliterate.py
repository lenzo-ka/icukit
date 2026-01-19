"""Text transliteration command."""

import argparse
import sys

from ...errors import TransliteratorError
from ...formatters import print_output
from ...transliterator import Transliterator, get_transliterator_info, list_transliterators
from ..base import open_output, process_input
from ..locale_helpers import parse_multi_value
from ..subcommand_base import SubcommandBase


class TransliterateCommand(SubcommandBase):
    """Transliterate command with subcommands."""

    DEFAULT_SUBCOMMAND = None
    FALLBACK_SUBCOMMAND = "name"  # Unknown args that look like transliterator IDs use 'name'

    # Cache for transliterator IDs
    _transliterator_ids = None

    @classmethod
    def is_valid_fallback_arg(cls, arg: str) -> bool:
        """Check if arg looks like a transliterator ID."""
        # Cache the list of transliterators
        if cls._transliterator_ids is None:
            cls._transliterator_ids = set(list_transliterators())
        # Check if it's a known transliterator ID
        if arg in cls._transliterator_ids:
            return True
        # Also accept compound expressions (contain semicolons or colons)
        # These are ICU transform rules like "NFD; [:M:] Remove; NFC"
        if ";" in arg or "::" in arg:
            return True
        # Accept patterns like "Script-Script" or "Script-Script/Variant"
        if "-" in arg and not arg.startswith("-"):
            return True
        return False

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the transliterate command with its subcommands."""
        parser = subparsers.add_parser(
            "transliterate",
            help="Transliterate text using ICU",
            description="""
Transliterate text using ICU transliterators or custom rules.

Shortcut: If a transliterator ID is given directly, 'name' is assumed:
  icukit tr Latin-Greek        # same as: icukit tr name Latin-Greek

Examples:
  # List available transliterators
  icukit transliterate list
  icukit transliterate list --name 'Latin-.*'

  # Convert text
  echo 'Hello World' | icukit transliterate name Latin-Greek

  # Reverse transliteration
  echo 'Ελληνικά' | icukit transliterate from Latin-Greek

  # Custom rules
  icukit transliterate rules my-rules.txt < input.txt

  # Remove accents using inline script
  echo 'Café' | icukit transliterate script 'NFD; [:Nonspacing Mark:] Remove; NFC'
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List available transliterators",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
                "name": {
                    "aliases": ["n"],
                    "help": "Convert text using named transliterator",
                    "func": cls.cmd_name,
                    "configure": cls._configure_name,
                },
                "from": {
                    "aliases": ["f", "reverse"],
                    "help": "Convert text from source script (reverse)",
                    "func": cls.cmd_from,
                    "configure": cls._configure_from,
                },
                "rules": {
                    "aliases": ["r", "custom"],
                    "help": "Convert using custom rules file",
                    "func": cls.cmd_rules,
                    "configure": cls._configure_rules,
                },
                "script": {
                    "aliases": ["s", "inline", "expr"],
                    "help": "Convert using inline ICU transform expression",
                    "func": cls.cmd_script,
                    "configure": cls._configure_script,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument("--name", help="Filter by transliterator name (regex supported)")
        parser.add_argument("--from", help="Filter by source script")
        parser.add_argument("--to", help="Filter by target script")
        parser.add_argument("--scripts", action="store_true", help="Group by source scripts")
        parser.add_argument("-s", "--short", action="store_true", help="Show only IDs")
        cls._add_output_options(parser)

    @classmethod
    def _configure_name(cls, parser):
        """Configure name subcommand."""
        parser.add_argument(
            "transliterators", help="Transliterator name(s) - comma-separated or regex"
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_from(cls, parser):
        """Configure from/reverse subcommand."""
        parser.add_argument("transliterators", help="Transliterator name(s) for reverse")
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_rules(cls, parser):
        """Configure rules subcommand."""
        parser.add_argument("rules_file", help="File containing transliteration rules")
        cls._add_input_options(parser)
        parser.add_argument("-n", "--name", default="custom", help="Name for custom transliterator")
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _configure_script(cls, parser):
        """Configure script subcommand."""
        parser.add_argument(
            "expression",
            help='ICU transform expression (e.g., "NFD; [:Nonspacing Mark:] Remove; NFC")',
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def cmd_list(cls, args):
        """List available transliterators."""
        try:
            trans_ids = list_transliterators()

            # Apply filters
            if hasattr(args, "name") and args.name:
                trans_ids = parse_multi_value(args.name, "transliterator", trans_ids)

            if hasattr(args, "from") and getattr(args, "from"):
                from_filter = getattr(args, "from")
                all_sources = {t.split("-")[0] for t in trans_ids if "-" in t}
                from_scripts = parse_multi_value(from_filter, "script", list(all_sources))
                if from_scripts:
                    trans_ids = [
                        t for t in trans_ids if "-" in t and t.split("-")[0] in from_scripts
                    ]

            if hasattr(args, "to") and args.to:
                all_targets = {
                    t.split("-")[1] for t in trans_ids if "-" in t and len(t.split("-")) >= 2
                }
                to_scripts = parse_multi_value(args.to, "script", list(all_targets))
                if to_scripts:
                    trans_ids = [
                        t
                        for t in trans_ids
                        if "-" in t and len(t.split("-")) >= 2 and t.split("-")[1] in to_scripts
                    ]

            # Build structured data
            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False) or getattr(args, "short", False)

            if getattr(args, "short", False):
                # Short mode: just IDs as list
                print_output(trans_ids, as_json=as_json)
            else:
                # Full mode: detailed info
                data = [get_transliterator_info(tid) for tid in trans_ids]

                # Group by script if requested
                if hasattr(args, "scripts") and args.scripts:
                    by_script = {}
                    for item in data:
                        source = item.get("source") or "Special"
                        by_script.setdefault(source, []).append(item)
                    print_output(by_script, as_json=as_json)
                else:
                    print_output(
                        data,
                        as_json=as_json,
                        columns=["id", "source", "target", "variant", "reversible"],
                        headers=not no_header,
                    )

            return 0
        except TransliteratorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_name(cls, args):
        """Convert text using named transliterator(s)."""
        try:
            all_trans = list_transliterators()
            trans_ids = parse_multi_value(args.transliterators, "transliterator", all_trans)

            # If no matches but input has no commas, try using it directly as a transliterator ID
            # (supports compound rules like "NFD; [:Nonspacing Mark:] Remove; NFC")
            if not trans_ids and "," not in args.transliterators:
                trans_ids = [args.transliterators]

            if not trans_ids:
                print("Error: No valid transliterators specified", file=sys.stderr)
                return 1

            as_json = getattr(args, "json", False)

            if len(trans_ids) == 1:
                trans = Transliterator(trans_ids[0])
                with open_output(getattr(args, "output", None)) as output:
                    if as_json:
                        content = cls._read_input(args)
                        result = trans.transliterate(content)
                        print_output(
                            [{"transliterator": trans_ids[0], "result": result}],
                            as_json=True,
                            file=output,
                        )
                    else:
                        process_input(args, trans.transliterate, output)
                return 0

            # Multiple transliterators
            content = cls._read_input(args)
            results = []
            for trans_id in trans_ids:
                try:
                    trans = Transliterator(trans_id)
                    results.append(
                        {"transliterator": trans_id, "result": trans.transliterate(content)}
                    )
                except TransliteratorError as e:
                    results.append({"transliterator": trans_id, "error": str(e)})

            with open_output(getattr(args, "output", None)) as output:
                if as_json:
                    print_output(results, as_json=True, file=output)
                else:
                    for i, result in enumerate(results):
                        if i > 0:
                            print(file=output)
                        if "error" in result:
                            print(
                                f"=== {result['transliterator']} (ERROR: {result['error']}) ===",
                                file=output,
                            )
                        else:
                            print(f"=== {result['transliterator']} ===", file=output)
                            output.write(result["result"])
                            if not result["result"].endswith("\n"):
                                print(file=output)
            return 0
        except TransliteratorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_from(cls, args):
        """Convert text from source script (reverse)."""
        try:
            all_trans = list_transliterators()
            trans_ids = parse_multi_value(args.transliterators, "transliterator", all_trans)

            # If no matches but input has no commas, try using it directly
            if not trans_ids and "," not in args.transliterators:
                trans_ids = [args.transliterators]

            if not trans_ids:
                print("Error: No valid transliterators specified", file=sys.stderr)
                return 1

            as_json = getattr(args, "json", False)

            if len(trans_ids) == 1:
                trans = Transliterator(trans_ids[0], reverse=True)
                with open_output(getattr(args, "output", None)) as output:
                    if as_json:
                        content = cls._read_input(args)
                        result = trans.transliterate(content)
                        print_output(
                            [{"transliterator": f"{trans_ids[0]} (reverse)", "result": result}],
                            as_json=True,
                            file=output,
                        )
                    else:
                        process_input(args, trans.transliterate, output)
                return 0

            content = cls._read_input(args)
            results = []
            for trans_id in trans_ids:
                try:
                    trans = Transliterator(trans_id, reverse=True)
                    results.append(
                        {
                            "transliterator": f"{trans_id} (reverse)",
                            "result": trans.transliterate(content),
                        }
                    )
                except TransliteratorError as e:
                    results.append({"transliterator": f"{trans_id} (reverse)", "error": str(e)})

            with open_output(getattr(args, "output", None)) as output:
                if as_json:
                    print_output(results, as_json=True, file=output)
                else:
                    for i, result in enumerate(results):
                        if i > 0:
                            print(file=output)
                        if "error" in result:
                            print(
                                f"=== {result['transliterator']} (ERROR: {result['error']}) ===",
                                file=output,
                            )
                        else:
                            print(f"=== {result['transliterator']} ===", file=output)
                            output.write(result["result"])
                            if not result["result"].endswith("\n"):
                                print(file=output)
            return 0
        except TransliteratorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_rules(cls, args):
        """Convert using custom rules."""
        try:
            with open(args.rules_file, "r", encoding="utf-8") as f:
                rules = f.read()
            trans = Transliterator.from_rules(args.name, rules)
            with open_output(getattr(args, "output", None)) as output:
                process_input(args, trans.transliterate, output)
            return 0
        except TransliteratorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_script(cls, args):
        """Convert using inline ICU transform expression."""
        try:
            trans = Transliterator(args.expression)
            as_json = getattr(args, "json", False)

            with open_output(getattr(args, "output", None)) as output:
                if as_json:
                    content = cls._read_input(args)
                    result = trans.transliterate(content)
                    print_output(
                        [{"expression": args.expression, "result": result}],
                        as_json=True,
                        file=output,
                    )
                else:
                    process_input(args, trans.transliterate, output)
            return 0
        except TransliteratorError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
