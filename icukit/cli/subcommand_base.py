"""Base class for CLI commands with subcommands."""

import sys
from functools import wraps
from typing import Dict

from ..formatters import print_output
from .command_trie import CommandTrie


def handles_errors(*error_classes, code=1):
    """Decorator to handle errors in CLI command methods.

    Catches specified exception types, prints error message to stderr,
    and returns the specified exit code.

    Args:
        *error_classes: Exception classes to catch.
        code: Exit code to return on error (default: 1).

    Usage:
        @classmethod
        @handles_errors(BreakerError)
        def cmd_words(cls, args):
            ...

        # Multiple error types:
        @classmethod
        @handles_errors(ValueError, PatternError)
        def cmd_find(cls, args):
            ...

        # Custom exit code:
        @classmethod
        @handles_errors(BidiError, code=2)
        def cmd_check(cls, args):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_classes as e:
                print(f"Error: {e}", file=sys.stderr)
                return code

        return wrapper

    return decorator


class SubcommandBase:
    """Base class for commands with subcommands."""

    DEFAULT_SUBCOMMAND = None
    # If set, unknown subcommands that match this check will use FALLBACK_SUBCOMMAND
    FALLBACK_SUBCOMMAND = None  # e.g., "name" for transliterate

    @classmethod
    def is_valid_fallback_arg(cls, arg: str) -> bool:
        """Check if arg is valid for the fallback subcommand.

        Override this in subclasses to enable fallback behavior.
        Return True if arg should be treated as an argument to FALLBACK_SUBCOMMAND.
        """
        return False

    @classmethod
    def add_subparser(cls, subparsers):
        """Add this command to the main subparsers."""
        raise NotImplementedError("Subclasses must implement add_subparser")

    @classmethod
    def _run_list(
        cls, args, list_func, info_func, columns=None, headers=True, as_json=False, short=False
    ):
        """Helper to run standard list subcommand.

        Args:
            args: Argparse namespace.
            list_func: Function returning list of IDs/names.
            info_func: Function returning list of info dicts.
            columns: List of column names for info output.
            headers: Whether to show headers in info output.
            as_json: Whether to output as JSON.
            short: Whether to only show IDs/names.
        """
        if short:
            data = list_func()
            print_output(data, as_json=as_json)
        else:
            data = info_func()
            print_output(
                data,
                as_json=as_json,
                columns=columns,
                headers=headers,
            )
        return 0

    @classmethod
    def run(cls, args):
        """Main entry point - dispatch to subcommand or show help.

        Subclasses typically don't need to override this.
        """
        if hasattr(args, "func") and args.func != cls.run:
            return args.func(args)
        if hasattr(args, "_subparser"):
            args._subparser.print_help()
        return 0

    # -------------------------------------------------------------------------
    # Common argument group helpers - use in _configure_* methods
    # -------------------------------------------------------------------------

    @classmethod
    def _get_output_flags(cls, args):
        """Extract common output flags from args.

        Returns:
            tuple: (as_json, headers) where headers=True means show headers.
        """
        as_json = getattr(args, "json", False)
        headers = not getattr(args, "no_header", False)
        return as_json, headers

    @classmethod
    def _add_output_options(cls, parser, include_header=True):
        """Add common output options: -o, -j, -H."""
        output_group = parser.add_argument_group("output options")
        output_group.add_argument("-o", "--output", help="Output file (default: stdout)")
        output_group.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
        if include_header:
            output_group.add_argument(
                "-H", "--no-header", action="store_true", help="Suppress header in TSV output"
            )

    @classmethod
    def _add_input_options(cls, parser):
        """Add common input options: -t, FILE..."""
        input_group = parser.add_argument_group(
            "input", "Input: -t TEXT, or FILE..., or stdin (default)"
        )
        input_group.add_argument("-t", "--text", metavar="TEXT", help="Process TEXT directly")
        input_group.add_argument("files", nargs="*", metavar="FILE", help="Process FILE(s)")

    @classmethod
    def _read_lines(cls, args) -> list[str]:
        """Read input lines from text, files, or stdin.

        Use with commands that process line-oriented input (e.g., sort).
        Requires parser configured with _add_input_options().
        """
        if hasattr(args, "text") and args.text:
            return args.text.split("\n")
        elif hasattr(args, "files") and args.files:
            lines = []
            for filepath in args.files:
                with open(filepath, "r") as f:
                    lines.extend(line.rstrip("\n") for line in f)
            return lines
        else:
            return [line.rstrip("\n") for line in sys.stdin]

    @classmethod
    def _read_input(cls, args) -> str:
        """Read input text from args.text, args.files, or stdin.

        Use with commands that process full text (e.g., transliterate).
        Requires parser configured with _add_input_options().
        """
        if getattr(args, "text", None):
            return args.text
        elif getattr(args, "files", None):
            return "".join(open(f).read() for f in args.files)
        else:
            return sys.stdin.read()

    @classmethod
    def create_subcommand_parser(cls, parser, subcommands: Dict[str, Dict]):
        """Helper to create subcommand structure with prefix matching.

        Args:
            parser: The parser to add subcommands to
            subcommands: Dict mapping subcommand names to config:
                {
                    'list': {
                        'aliases': ['ls', 'l'],
                        'help': 'List items',
                        'func': cls.cmd_list,
                        'configure': cls._configure_list,  # optional
                    },
                }
        """
        # Add help subcommand if not present
        if "help" not in subcommands:
            subcommands["help"] = {
                "aliases": ["h"],
                "help": "Show help for a subcommand",
                "func": None,  # Set after subparsers created
                "configure": lambda sub: sub.add_argument(
                    "help_command", nargs="?", help="Subcommand to show help for"
                ),
            }

        # Create trie for prefix matching
        trie = CommandTrie()
        for name, config in subcommands.items():
            trie.insert(name, config.get("aliases", []))

        parser._subcommand_trie = trie

        subparsers_action = parser.add_subparsers(
            title="subcommands",
            dest="subcommand",
            required=False,
        )

        # Create help function now that we have subparsers_action
        def show_help(args):
            if hasattr(args, "help_command") and args.help_command:
                # Try to find specific subcommand
                resolved, suggestions = trie.find_command(args.help_command)
                if resolved and resolved in subparsers_action.choices:
                    subparsers_action.choices[resolved].print_help()
                    return 0
                elif suggestions and len(suggestions) > 1:
                    print(f"Ambiguous subcommand: '{args.help_command}'", file=sys.stderr)
                    print("Did you mean one of these?", file=sys.stderr)
                    for cmd in sorted(suggestions):
                        print(f"  {cmd}", file=sys.stderr)
                    return 1
                else:
                    print(f"Unknown subcommand: '{args.help_command}'", file=sys.stderr)
                    parser.print_help()
                    return 1
            parser.print_help()
            return 0

        # Update help subcommand with the function
        if "help" in subcommands and subcommands["help"]["func"] is None:
            subcommands["help"]["func"] = show_help

        # Track all names for prefix matching
        original_choices = {}

        for name, config in subcommands.items():
            aliases = config.get("aliases", [])
            help_text = config.get("help", "")
            func = config.get("func")

            sub = subparsers_action.add_parser(name, aliases=aliases, help=help_text)

            if func:
                sub.set_defaults(func=func)

            if "configure" in config:
                config["configure"](sub)

            original_choices[name] = name
            for alias in aliases:
                original_choices[alias] = name

        # Override parse to resolve prefixes
        original_parse_known_args = parser.parse_known_args

        def parse_known_args_with_prefix(args=None, namespace=None):
            if args is None:
                args = sys.argv[1:]
            else:
                args = list(args)

            # Find first non-flag argument (subcommand)
            subcommand_pos = None
            for i, arg in enumerate(args):
                if not arg.startswith("-"):
                    subcommand_pos = i
                    break

            if subcommand_pos is not None:
                prefix = args[subcommand_pos]
                resolved, suggestions = trie.find_command(prefix)

                if resolved:
                    args[subcommand_pos] = resolved
                elif suggestions and len(suggestions) > 1:
                    parser.error(
                        f"ambiguous subcommand: '{prefix}'\n\n"
                        + "Did you mean one of these?\n"
                        + "\n".join(f"  {cmd}" for cmd in sorted(suggestions))
                    )
                elif cls.FALLBACK_SUBCOMMAND and cls.is_valid_fallback_arg(prefix):
                    # Unknown subcommand but valid fallback arg - insert fallback subcommand
                    args.insert(subcommand_pos, cls.FALLBACK_SUBCOMMAND)

            return original_parse_known_args(args, namespace)

        parser.parse_known_args = parse_known_args_with_prefix
        parser.parse_args = lambda args=None, namespace=None: parse_known_args_with_prefix(
            args, namespace
        )[0]

        return parser
