"""Discovery utilities for icukit features and capabilities.

This module provides introspection of icukit's API and CLI, helping users
discover available functionality. It dynamically reflects the actual
exports and commands rather than hardcoding them.

Note: Import this module directly (from icukit.discover import ...) rather
than from icukit to avoid circular imports.
"""

import inspect
from typing import Any, Dict, List, Optional

import icukit
from icukit.cli.command_trie import get_all_commands, get_command_info
from icukit.cli.main import create_parser


def get_api_exports() -> List[str]:
    """Get all exported API functions and classes.

    Returns:
        List of exported names from icukit.__all__
    """
    return list(getattr(icukit, "__all__", []))


def get_api_info(name: str) -> Optional[Dict[str, Any]]:
    """Get information about an API export.

    Args:
        name: Name of the exported function/class

    Returns:
        Dictionary with name, type, signature, and docstring, or None if not found
    """
    try:
        obj = getattr(icukit, name)
        info = {
            "name": name,
            "type": type(obj).__name__,
            "doc": inspect.getdoc(obj) or "",
        }
        try:
            info["signature"] = str(inspect.signature(obj))
        except (ValueError, TypeError):
            info["signature"] = None
        return info
    except AttributeError:
        return None


def get_cli_commands() -> Dict[str, Dict[str, Any]]:
    """Get available CLI commands with their details.

    Returns:
        Dictionary mapping command names to their info (aliases, minimal_prefix)
    """
    # Trigger command registration by building the parser
    create_parser()

    return {
        name: get_command_info(name) or {"name": name, "aliases": [], "minimal_prefix": name}
        for name in get_all_commands()
    }


def discover_features() -> Dict[str, Any]:
    """Discover all available features in icukit.

    Returns:
        Dictionary with API exports and CLI commands
    """
    api_exports = get_api_exports()
    api_info = {name: get_api_info(name) for name in api_exports}

    cli_commands = get_cli_commands()

    return {
        "version": icukit.__version__,
        "api": {
            "exports": api_exports,
            "details": api_info,
        },
        "cli": {
            "commands": cli_commands,
        },
    }


def search_features(query: str) -> Dict[str, List[str]]:
    """Search for features matching a query.

    Args:
        query: Search term (case-insensitive)

    Returns:
        Dictionary with matching API exports and CLI commands
    """
    query_lower = query.lower()

    # Search API exports
    api_matches = []
    for name in get_api_exports():
        info = get_api_info(name)
        if info and (query_lower in name.lower() or query_lower in info.get("doc", "").lower()):
            api_matches.append(name)

    # Search CLI commands
    cli_matches = []
    cli_commands = get_cli_commands()
    for cmd_name, cmd_info in cli_commands.items():
        if query_lower in cmd_name.lower() or any(
            query_lower in alias.lower() for alias in cmd_info.get("aliases", [])
        ):
            cli_matches.append(cmd_name)

    return {
        "api": api_matches,
        "cli": cli_matches,
    }


def print_discovery_report():
    """Print a formatted discovery report to stdout."""
    features = discover_features()

    print(f"ICU Kit v{features['version']} - Feature Discovery")
    print("=" * 50)

    # API summary
    api_exports = features["api"]["exports"]
    print(f"\nAPI Exports ({len(api_exports)}):")
    for name in sorted(api_exports):
        info = features["api"]["details"].get(name, {})
        obj_type = info.get("type", "unknown")
        sig = info.get("signature", "")
        if sig:
            print(f"  {name}{sig} [{obj_type}]")
        else:
            print(f"  {name} [{obj_type}]")

    # CLI summary
    cli_commands = features["cli"]["commands"]
    print(f"\nCLI Commands ({len(cli_commands)}):")
    for cmd_name in sorted(cli_commands.keys()):
        cmd_info = cli_commands[cmd_name]
        aliases = cmd_info.get("aliases", [])
        min_prefix = cmd_info.get("minimal_prefix", cmd_name)
        parts = [cmd_name]
        if min_prefix and min_prefix != cmd_name:
            parts.append(f"[{min_prefix}]")
        if aliases:
            parts.append(f"(aliases: {', '.join(aliases)})")
        print(f"  {' '.join(parts)}")

    print(f"\nTotal: {len(api_exports)} API exports, {len(cli_commands)} CLI commands")


if __name__ == "__main__":
    print_discovery_report()
