"""Output formatting helpers for CLI commands."""

import json
import sys
from typing import Any, Dict, List, Optional, TextIO


def print_simple_list(
    items: List[str],
    header: Optional[str] = None,
    output: TextIO = None,
    show_header: bool = True,
) -> None:
    """Print simple list with optional header."""
    if output is None:
        output = sys.stdout
    if show_header and header:
        print(header, file=output)
    for item in items:
        print(item, file=output)


def print_tabular(
    data: List[Dict[str, Any]],
    columns: List[str],
    output: TextIO = None,
    show_header: bool = True,
) -> None:
    """Print data in tabular format."""
    if output is None:
        output = sys.stdout
    if show_header:
        print("\t".join(columns), file=output)
    for row in data:
        values = [str(row.get(col, "")) for col in columns]
        print("\t".join(values), file=output)


def handle_list_output(items: List[Any], columns: List[str], output: TextIO, args: Any) -> None:
    """Standard list output handler."""
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False), file=output)
    elif args.short:
        for item in items:
            if isinstance(item, dict):
                print(item.get(columns[0], ""), file=output)
            else:
                print(item, file=output)
    else:
        if items and isinstance(items[0], dict):
            print_tabular(items, columns, output, show_header=not args.no_header)
        else:
            print_simple_list(
                items, columns[0] if columns else None, output, show_header=not args.no_header
            )
