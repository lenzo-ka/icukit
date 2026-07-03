"""Discovery utilities for icukit features and capabilities.

This module provides introspection of icukit's API and CLI, helping users
discover available functionality. It dynamically reflects the actual
exports and commands rather than hardcoding them.

Note: Import this module directly (from icukit.discover import ...) rather
than from icukit to avoid circular imports.
"""

from __future__ import annotations

import inspect
from typing import Any

import icukit


def get_api_exports() -> list[str]:
    """Get all exported API functions and classes.

    Returns:
        List of exported names from icukit.__all__
    """
    return list(getattr(icukit, "__all__", []))


def get_api_info(name: str) -> dict[str, Any] | None:
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


def get_cli_commands() -> dict[str, dict[str, Any]]:
    """Get available CLI commands with their details.

    Returns:
        Dictionary mapping command names to their info (aliases, minimal_prefix)
    """
    # Import lazily to avoid circular import
    from icukit.cli.command_trie import get_all_commands, get_command_info
    from icukit.cli.main import create_parser

    # Trigger command registration by building the parser
    create_parser()

    return {
        name: get_command_info(name) or {"name": name, "aliases": [], "minimal_prefix": name}
        for name in get_all_commands()
    }


def discover_features() -> dict[str, Any]:
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


def search_features(query: str) -> dict[str, list[str]]:
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


def render_discovery_report() -> str:
    """Build a formatted discovery report string.

    Returns:
        The report as a multi-line string (the caller decides where to print).
    """
    features = discover_features()
    lines = [
        f"ICU Kit v{features['version']} - Feature Discovery",
        "=" * 50,
    ]

    # API summary
    api_exports = features["api"]["exports"]
    lines.append(f"\nAPI Exports ({len(api_exports)}):")
    for name in sorted(api_exports):
        # details[name] may be None when an __all__ entry isn't importable
        # from the package namespace (e.g. the discover functions themselves).
        info = features["api"]["details"].get(name) or {}
        obj_type = info.get("type", "unknown")
        sig = info.get("signature", "")
        lines.append(f"  {name}{sig} [{obj_type}]" if sig else f"  {name} [{obj_type}]")

    # CLI summary
    cli_commands = features["cli"]["commands"]
    lines.append(f"\nCLI Commands ({len(cli_commands)}):")
    for cmd_name in sorted(cli_commands.keys()):
        cmd_info = cli_commands[cmd_name]
        aliases = cmd_info.get("aliases", [])
        min_prefix = cmd_info.get("minimal_prefix", cmd_name)
        parts = [cmd_name]
        if min_prefix and min_prefix != cmd_name:
            parts.append(f"[{min_prefix}]")
        if aliases:
            parts.append(f"(aliases: {', '.join(aliases)})")
        lines.append(f"  {' '.join(parts)}")

    lines.append(f"\nTotal: {len(api_exports)} API exports, {len(cli_commands)} CLI commands")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_discovery_report())
