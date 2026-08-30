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
import ast
import enum
import inspect
import sys
import types
from pathlib import Path
from typing import Any, get_origin

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_module_doc(module) -> str:
    """Extract module-level docstring."""
    return inspect.getdoc(module) or ""


def get_class_info(cls) -> dict[str, Any]:
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


def get_function_info(func) -> dict[str, Any]:
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


def get_source_assignments(module) -> dict[str, dict[str, str]]:
    """Return stable source forms and nearby documentation for assignments."""
    source = inspect.getsource(module)
    tree = ast.parse(source)
    lines = source.splitlines()
    assignments = {}

    for index, node in enumerate(tree.body):
        names = []
        value = None
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [target.id for target in targets if isinstance(target, ast.Name)]
            value = node.value
        if not names or value is None:
            continue

        doc = ""
        if index + 1 < len(tree.body):
            next_node = tree.body[index + 1]
            if (
                isinstance(next_node, ast.Expr)
                and isinstance(next_node.value, ast.Constant)
                and isinstance(next_node.value.value, str)
            ):
                doc = next_node.value.value
        if not doc and node.lineno > 1:
            previous = lines[node.lineno - 2].strip()
            if previous.startswith("#"):
                doc = previous.removeprefix("#").strip()

        annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
        for name in names:
            assignments[name] = {
                "value": ast.unparse(value),
                "annotation": ast.unparse(annotation) if annotation else "",
                "doc": doc,
            }

    return assignments


def is_type_alias(name: str, obj: Any, source_info: dict[str, str]) -> bool:
    """Identify explicit and conventional exported type aliases."""
    if source_info.get("annotation") in {"TypeAlias", "typing.TypeAlias"}:
        return True
    if isinstance(obj, types.UnionType) or get_origin(obj) is not None:
        return True
    return bool(name[:1].isupper() and not name.isupper())


def stable_repr(value: Any) -> str:
    """Return a compact representation with deterministic container ordering."""
    if isinstance(value, enum.Enum):
        return f"{type(value).__name__}.{value.name}"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: stable_repr(item[0]))
        return (
            "{" + ", ".join(f"{stable_repr(key)}: {stable_repr(item)}" for key, item in items) + "}"
        )
    if isinstance(value, (set, frozenset)):
        rendered = ", ".join(sorted(stable_repr(item) for item in value))
        return f"{type(value).__name__}({{{rendered}}})"
    if isinstance(value, tuple):
        rendered = ", ".join(stable_repr(item) for item in value)
        if len(value) == 1:
            rendered += ","
        return f"({rendered})"
    if isinstance(value, list):
        return "[" + ", ".join(stable_repr(item) for item in value) + "]"
    if isinstance(value, (str, bytes, int, float, complex, bool, type(None))):
        return repr(value)
    return f"<{type(value).__module__}.{type(value).__qualname__}>"


def get_data_info(name: str, obj: Any, source_info: dict[str, str]) -> dict[str, str]:
    """Extract documentation for an exported constant or type alias."""
    alias = is_type_alias(name, obj, source_info)
    if alias:
        annotation = source_info.get("annotation")
        value = source_info.get("value") or stable_repr(obj)
        form = value if not annotation or annotation.endswith("TypeAlias") else annotation
    else:
        form = stable_repr(obj)
    return {
        "name": name,
        "kind": "alias" if alias else "constant",
        "form": form,
        "doc": source_info.get("doc", ""),
    }


def extract_lib_docs() -> dict[str, Any]:
    """Extract documentation from the icukit library modules."""
    import importlib

    import icukit

    docs = {
        "version": icukit.__version__,
        "modules": {},
        "root_exports": [],
    }

    docs["package_doc"] = get_module_doc(icukit)

    # Discover public submodules by looking at icukit package directory.
    pkg_path = Path(icukit.__file__).parent
    module_names = sorted(p.stem for p in pkg_path.glob("*.py") if not p.stem.startswith("_"))

    # Put errors at end since it's just reference
    if "errors" in module_names:
        module_names.remove("errors")
        module_names.append("errors")

    for mod_name in module_names:
        module = importlib.import_module(f"icukit.{mod_name}")
        mod_doc = get_module_doc(module)

        classes = []
        functions = []
        data = []
        source_assignments = get_source_assignments(module)

        exported_names = getattr(module, "__all__", None)
        if exported_names is None:
            member_names = sorted(
                name
                for name, obj in inspect.getmembers(module)
                if not name.startswith("_")
                and (
                    name in source_assignments
                    or getattr(obj, "__module__", None) == f"icukit.{mod_name}"
                )
            )
        else:
            member_names = list(exported_names)

        for name in member_names:
            obj = getattr(module, name)
            if inspect.isclass(obj):
                classes.append(get_class_info(obj))
            elif inspect.isfunction(obj):
                functions.append(get_function_info(obj))
            else:
                data.append(get_data_info(name, obj, source_assignments.get(name, {})))

        # Sort by name for consistent output
        classes.sort(key=lambda x: x["name"])
        functions.sort(key=lambda x: x["name"])
        data.sort(key=lambda x: x["name"])

        docs["modules"][mod_name] = {
            "doc": mod_doc,
            "classes": classes,
            "functions": functions,
            "data": data,
        }

    root_origins = {}
    init_tree = ast.parse(inspect.getsource(icukit))
    for node in init_tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            origin = node.module.lstrip(".")
            for imported in node.names:
                root_origins[imported.asname or imported.name] = origin

    module_entries = {
        (mod_name, entry["name"]): entry["kind"]
        for mod_name, mod_info in docs["modules"].items()
        for entry in mod_info["data"]
    }
    for name in icukit.__all__:
        obj = getattr(icukit, name)
        origin = root_origins.get(name) or getattr(obj, "__module__", "icukit")
        origin = origin.removeprefix("icukit.")
        if origin == "icukit":
            origin = ""
        if inspect.isclass(obj):
            kind = "class"
        elif inspect.isfunction(obj):
            kind = "function"
        else:
            kind = module_entries.get(
                (origin, name), "alias" if is_type_alias(name, obj, {}) else "constant"
            )
        docs["root_exports"].append({"name": name, "kind": kind, "origin": origin})

    return docs


def canonical_subcommand_name(subparser: argparse.ArgumentParser, names: list[str]) -> str:
    """Return the name a subparser was created with, given every name it answers to.

    ``add_parser`` records the canonical name in the subparser's ``prog`` and
    registers it before any alias, so either source identifies it. Aliases are
    never canonical, however long they are.
    """
    from_prog = subparser.prog.split()[-1] if subparser.prog else ""
    return from_prog if from_prog in names else names[0]


def extract_parser_info(parser: argparse.ArgumentParser, prefix: str = "") -> dict[str, Any]:
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
            # Group the names by the parser they share: one entry per command,
            # keyed by its canonical name, carrying its aliases alongside.
            by_parser: dict[int, tuple[argparse.ArgumentParser, list[str]]] = {}
            for name, subparser in action.choices.items():
                by_parser.setdefault(id(subparser), (subparser, []))[1].append(name)
            for subparser, names in by_parser.values():
                canonical = canonical_subcommand_name(subparser, names)
                subinfo = extract_parser_info(subparser, f"{prefix}{canonical} ")
                subinfo["aliases"] = sorted(name for name in names if name != canonical)
                info["subcommands"][canonical] = subinfo
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


def extract_cli_docs() -> dict[str, Any]:
    """Extract documentation from the CLI."""
    from icukit.cli.main import create_parser

    parser = create_parser()
    return extract_parser_info(parser)


def generate_api_markdown(lib_docs: dict[str, Any]) -> str:
    """Generate markdown documentation for the library API."""
    lines = [
        "# icukit API Reference",
        "",
        f"Version: {lib_docs['version']}",
        "",
        "## Root API index",
        "",
        "Names exported by `icukit.__all__` (the `from icukit import ...` surface):",
        "",
    ]

    for entry in lib_docs["root_exports"]:
        origin = entry["origin"]
        module_name = f"icukit.{origin}" if origin else "icukit"
        anchor = f"icukit{origin.replace('_', '-')}" if origin else "root-api-index"
        lines.append(f"- [`{entry['name']}`](#{anchor}) — {entry['kind']}, `{module_name}`")
    lines.append("")

    for mod_name, mod_info in lib_docs["modules"].items():
        lines.extend(
            [
                f"## icukit.{mod_name}",
                "",
                mod_info["doc"],
                "",
            ]
        )

        if mod_info["data"]:
            lines.extend(["### Constants and type aliases", ""])
            for entry in mod_info["data"]:
                label = "type alias" if entry["kind"] == "alias" else "constant"
                lines.extend([f"#### `{entry['name']}` ({label})", "", f"`{entry['form']}`", ""])
                if entry["doc"]:
                    lines.extend([entry["doc"], ""])

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


def generate_cli_markdown(cli_docs: dict[str, Any], level: int = 1, parent_cmd: str = "") -> str:
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

        # Each entry is already keyed by its canonical name and carries its own
        # aliases, so no name is ever promoted over the one it aliases.
        for canonical in sorted(cli_docs["subcommands"]):
            subcmd = cli_docs["subcommands"][canonical]
            aliases = subcmd.get("aliases", [])
            full_cmd = f"{parent_cmd} {canonical}".strip()
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


def write_docs(output_dir: Path) -> list[Path]:
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
