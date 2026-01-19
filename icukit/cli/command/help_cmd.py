"""Help command for showing help for other commands."""

import argparse
import sys

from ..command_trie import resolve_command


def add_subparser(subparsers):
    """Add the help subcommand to the parser."""
    parser = subparsers.add_parser(
        "help",
        help="Show help for a command",
        description="Show help information for icukit commands",
        epilog='You can also use "icukit <command> --help" directly.',
    )

    parser.add_argument("command", nargs="?", help="Command to show help for")

    parser.set_defaults(func=run)
    # Store reference to main subparsers for help lookup
    parser._subparsers = subparsers


def run(args):
    """Execute the help command."""
    if not args.command:
        # No specific command, show main help
        if hasattr(args, "_parser"):
            args._parser.print_help()
        else:
            print("Usage: icukit help <command>", file=sys.stderr)
        return 0

    # Try to resolve the command prefix
    resolved_command, suggestions = resolve_command(args.command)

    if resolved_command:
        # Found a unique match
        command_to_help = resolved_command
    elif suggestions:
        # Ambiguous prefix
        print(f"Error: Ambiguous command '{args.command}' could match:", file=sys.stderr)
        for cmd in sorted(suggestions):
            print(f"  {cmd}", file=sys.stderr)
        return 1
    else:
        # No match - use the original command name
        command_to_help = args.command

    # Try to find the command in subparsers
    parser = args._parser if hasattr(args, "_parser") else None
    if parser:
        # Get subparsers from the main parser
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                if command_to_help in action.choices:
                    action.choices[command_to_help].print_help()
                    return 0

        # Command not found
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)

        # Show available commands that might match
        if args.command and len(args.command) > 0:
            print("\nDid you mean one of these?", file=sys.stderr)
            for action in parser._subparsers._actions:
                if isinstance(action, argparse._SubParsersAction):
                    matching_cmds = [
                        cmd for cmd in action.choices.keys() if cmd.startswith(args.command[0])
                    ]
                    for cmd in sorted(matching_cmds):
                        if cmd != "help":
                            print(f"  {cmd}", file=sys.stderr)

        print("\nAll available commands:", file=sys.stderr)
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                for cmd in sorted(action.choices.keys()):
                    if cmd != "help":  # Don't list help in the help
                        print(f"  {cmd}", file=sys.stderr)
        return 1

    # Fallback
    print(f"Error: Cannot find help for '{args.command}'", file=sys.stderr)
    return 1
