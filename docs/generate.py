#!/usr/bin/env python
"""Generate documentation from library and CLI source code.

This script introspects the icukit library and CLI to generate markdown
documentation. It ensures documentation stays in sync with the code by
using docstrings and argparse help text as the single source of truth.

Usage:
    python docs/generate.py           # Generate all docs
    python docs/generate.py --check   # Verify docs are up to date
"""

import argparse
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_module_doc(module) -> str:
    """Extract module-level docstring."""
    return inspect.getdoc(module) or ""


def get_class_info(cls) -> Dict[str, Any]:
    """Extract class documentation and methods."""
    info = {
        "name": cls.__name__,
        "doc": inspect.getdoc(cls) or "",
        "methods": [],
    }

    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_") and name != "__init__":
            continue
        method_doc = inspect.getdoc(method) or ""
        sig = ""
        try:
            sig = str(inspect.signature(method))
        except (ValueError, TypeError):
            pass
        info["methods"].append(
            {
                "name": name,
                "signature": sig,
                "doc": method_doc,
            }
        )

    return info


def get_function_info(func) -> Dict[str, Any]:
    """Extract function documentation."""
    sig = ""
    try:
        sig = str(inspect.signature(func))
    except (ValueError, TypeError):
        pass
    return {
        "name": func.__name__,
        "signature": sig,
        "doc": inspect.getdoc(func) or "",
    }


def extract_lib_docs() -> Dict[str, Any]:
    """Extract documentation from the icukit library modules."""
    import importlib

    import icukit

    docs = {
        "version": icukit.__version__,
        "modules": {},
    }

    docs["package_doc"] = get_module_doc(icukit)

    # Discover submodules by looking at icukit package directory
    # Exclude internal modules (formatters)
    pkg_path = Path(icukit.__file__).parent
    exclude = {"formatters"}
    module_names = sorted(
        p.stem
        for p in pkg_path.glob("*.py")
        if not p.stem.startswith("_") and p.stem not in exclude
    )

    # Put errors at end since it's just reference
    if "errors" in module_names:
        module_names.remove("errors")
        module_names.append("errors")

    for mod_name in module_names:
        module = importlib.import_module(f"icukit.{mod_name}")
        mod_doc = get_module_doc(module)

        classes = []
        functions = []

        # Get public members defined in this module
        for name, obj in inspect.getmembers(module):
            if name.startswith("_"):
                continue
            # Only include items defined in this module (not imports)
            if getattr(obj, "__module__", None) != f"icukit.{mod_name}":
                continue

            if inspect.isclass(obj):
                classes.append(get_class_info(obj))
            elif inspect.isfunction(obj):
                functions.append(get_function_info(obj))

        # Sort by name for consistent output
        classes.sort(key=lambda x: x["name"])
        functions.sort(key=lambda x: x["name"])

        docs["modules"][mod_name] = {
            "doc": mod_doc,
            "classes": classes,
            "functions": functions,
        }

    return docs


def extract_parser_info(parser: argparse.ArgumentParser, prefix: str = "") -> Dict[str, Any]:
    """Recursively extract argparse parser information."""
    info = {
        "prog": parser.prog,
        "description": parser.description or "",
        "epilog": parser.epilog or "",
        "arguments": [],
        "subcommands": {},
    }

    # Extract arguments
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            # Handle subparsers
            for name, subparser in action.choices.items():
                # Skip aliases (they point to the same parser)
                if hasattr(action, "_parser_class"):
                    info["subcommands"][name] = extract_parser_info(subparser, f"{prefix}{name} ")
        elif isinstance(action, argparse._HelpAction):
            continue  # Skip help action
        elif isinstance(action, argparse._VersionAction):
            info["arguments"].append(
                {
                    "name": (
                        ", ".join(action.option_strings) if action.option_strings else action.dest
                    ),
                    "help": "Show version and exit",
                    "required": False,
                    "default": None,
                }
            )
        else:
            arg_info = {
                "name": ", ".join(action.option_strings) if action.option_strings else action.dest,
                "help": action.help or "",
                "required": getattr(action, "required", False),
                "default": action.default if action.default != argparse.SUPPRESS else None,
                "choices": list(action.choices) if action.choices else None,
                "nargs": action.nargs,
            }
            info["arguments"].append(arg_info)

    return info


def extract_cli_docs() -> Dict[str, Any]:
    """Extract documentation from the CLI."""
    from icukit.cli.main import create_parser

    parser = create_parser()
    return extract_parser_info(parser)


def generate_api_markdown(lib_docs: Dict[str, Any]) -> str:
    """Generate markdown documentation for the library API."""
    lines = [
        "# icukit API Reference",
        "",
        f"Version: {lib_docs['version']}",
        "",
    ]

    for mod_name, mod_info in lib_docs["modules"].items():
        lines.extend(
            [
                f"## icukit.{mod_name}",
                "",
                mod_info["doc"],
                "",
            ]
        )

        # Classes
        for cls_info in mod_info["classes"]:
            lines.extend(
                [
                    f"### class `{cls_info['name']}`",
                    "",
                    cls_info["doc"],
                    "",
                ]
            )

            for method in cls_info["methods"]:
                if method["name"] == "__init__":
                    sig = method["signature"].replace("(self, ", "(").replace("(self)", "()")
                    lines.append(f"#### `{cls_info['name']}{sig}`")
                else:
                    sig = method["signature"].replace("(self, ", "(").replace("(self)", "()")
                    lines.append(f"#### `{method['name']}{sig}`")
                lines.extend(["", method["doc"], ""])

        # Functions
        for func_info in mod_info["functions"]:
            lines.extend(
                [
                    f"### `{func_info['name']}{func_info['signature']}`",
                    "",
                    func_info["doc"],
                    "",
                ]
            )

    return "\n".join(lines)


def generate_cli_markdown(cli_docs: Dict[str, Any], level: int = 1, parent_cmd: str = "") -> str:
    """Generate markdown documentation for the CLI."""
    lines = []

    if level == 1:
        lines.extend(
            [
                "# icukit CLI Reference",
                "",
            ]
        )

    # Description
    if cli_docs["description"]:
        desc = cli_docs["description"].strip()
        lines.extend([desc, ""])

    # Arguments
    if cli_docs["arguments"]:
        lines.extend(["**Options:**", ""])
        for arg in cli_docs["arguments"]:
            name = arg["name"]
            help_text = arg["help"] or ""
            if arg["default"] is not None and arg["default"] != "==SUPPRESS==":
                help_text += f" (default: `{arg['default']}`)"
            lines.append(f"- `{name}`: {help_text}")
        lines.append("")

    # Subcommands
    if cli_docs["subcommands"]:
        if level == 1:
            lines.extend(["## Commands", ""])

        # Group by description + arguments signature to identify aliases
        # (argparse creates separate objects for aliases but they have same content)
        def subcmd_signature(subcmd):
            args_sig = tuple((a["name"], a["help"]) for a in subcmd.get("arguments", []))
            return (subcmd.get("description", ""), args_sig)

        sig_to_names: Dict[tuple, List[str]] = {}
        for name, subcmd in cli_docs["subcommands"].items():
            sig = subcmd_signature(subcmd)
            sig_to_names.setdefault(sig, []).append(name)

        # Sort and process each unique command group
        processed = []
        seen_sigs = set()
        for name in sorted(cli_docs["subcommands"].keys()):
            subcmd = cli_docs["subcommands"][name]
            sig = subcmd_signature(subcmd)
            if sig in seen_sigs:
                continue
            seen_sigs.add(sig)

            names = sig_to_names[sig]
            # Primary name: longest name (descriptive), ties broken alphabetically
            primary = sorted(names, key=lambda x: (-len(x), x))[0]
            aliases = sorted([n for n in names if n != primary])
            processed.append((primary, aliases, subcmd))

        # Sort by primary name
        processed.sort(key=lambda x: x[0])

        for primary, aliases, subcmd in processed:
            full_cmd = f"{parent_cmd} {primary}".strip()
            heading_level = "#" * (level + 1)
            heading = f"{heading_level} `icukit {full_cmd}`"
            if aliases:
                heading += f" (aliases: {', '.join(sorted(aliases))})"
            lines.append(heading)
            lines.append("")

            # Recursively document subcommands
            sub_md = generate_cli_markdown(subcmd, level + 1, full_cmd)
            lines.append(sub_md)

    return "\n".join(lines)


def write_docs(output_dir: Path) -> List[Path]:
    """Generate and write all documentation files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files = []

    # Generate API docs
    lib_docs = extract_lib_docs()
    api_md = generate_api_markdown(lib_docs)
    api_file = output_dir / "api.md"
    api_file.write_text(api_md)
    written_files.append(api_file)
    print(f"Generated {api_file}")

    # Generate CLI docs
    cli_docs = extract_cli_docs()
    cli_md = generate_cli_markdown(cli_docs)
    cli_file = output_dir / "cli.md"
    cli_file.write_text(cli_md)
    written_files.append(cli_file)
    print(f"Generated {cli_file}")

    return written_files


def check_docs(output_dir: Path) -> bool:
    """Check if documentation is up to date."""
    import tempfile

    with tempfile.TemporaryDirectory():
        # Generate fresh docs
        lib_docs = extract_lib_docs()
        api_md = generate_api_markdown(lib_docs)

        cli_docs = extract_cli_docs()
        cli_md = generate_cli_markdown(cli_docs)

        # Compare with existing
        api_file = output_dir / "api.md"
        cli_file = output_dir / "cli.md"

        all_match = True

        if not api_file.exists():
            print(f"Missing: {api_file}")
            all_match = False
        elif api_file.read_text() != api_md:
            print(f"Out of date: {api_file}")
            all_match = False

        if not cli_file.exists():
            print(f"Missing: {cli_file}")
            all_match = False
        elif cli_file.read_text() != cli_md:
            print(f"Out of date: {cli_file}")
            all_match = False

        if all_match:
            print("Documentation is up to date.")

        return all_match


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if docs are up to date instead of generating",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).parent,
        help="Output directory for generated docs",
    )
    args = parser.parse_args()

    if args.check:
        success = check_docs(args.output)
        sys.exit(0 if success else 1)
    else:
        write_docs(args.output)


if __name__ == "__main__":
    main()
