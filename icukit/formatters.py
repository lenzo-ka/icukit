"""Output formatters for rendering structured data.

This module provides formatters for rendering JSON-serializable data
in various output formats (TSV, JSON, etc.).

Usage:
    data = [{"id": "foo", "value": 1}, {"id": "bar", "value": 2}]

    # TSV output (default)
    print(format_tsv(data))

    # JSON output
    print(format_json(data))

    # Auto-format based on args
    print(format_output(data, json=args.json))
"""

import json
import sys
from typing import Any, Dict, List, Optional, Sequence, TextIO


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON.

    Args:
        data: JSON-serializable data.
        indent: Indentation level.

    Returns:
        JSON string.
    """
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def format_tsv(
    data: Sequence[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    headers: bool = True,
) -> str:
    """Format list of dicts as TSV.

    Args:
        data: List of dictionaries with consistent keys.
        columns: Column order. If None, uses keys from first row.
        headers: Whether to include header row. Auto-disabled for single column.

    Returns:
        TSV string.
    """
    if not data:
        return ""

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    # Auto-omit headers for single column (e.g., --short output)
    show_headers = headers and len(columns) > 1

    lines = []

    # Header
    if show_headers:
        lines.append("\t".join(columns))

    # Rows
    for row in data:
        values = [_format_value(row.get(col, "")) for col in columns]
        lines.append("\t".join(values))

    return "\n".join(lines)


def _format_value(value: Any, null_str: str = "-") -> str:
    """Format a single value for TSV output.

    Args:
        value: Value to format.
        null_str: String to use for None/empty values.

    Returns:
        Formatted string.
    """
    if value is None:
        return null_str
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        if not value:
            return null_str
        return ",".join(str(v) for v in value)
    if isinstance(value, str) and not value:
        return null_str
    return str(value)


def format_simple_list(data: Sequence[str]) -> str:
    """Format a simple list as newline-separated values.

    Args:
        data: List of strings.

    Returns:
        Newline-separated string.
    """
    return "\n".join(str(item) for item in data)


def format_output(
    data: Any,
    as_json: bool = False,
    columns: Optional[List[str]] = None,
    headers: bool = True,
) -> str:
    """Format data for output based on format preference.

    Args:
        data: Data to format (list of dicts for TSV, any for JSON).
        as_json: If True, output JSON. Otherwise TSV.
        columns: Column order for TSV.
        headers: Whether to include headers in TSV.

    Returns:
        Formatted string.
    """
    if as_json:
        # Unwrap single-item lists for cleaner JSON output
        if isinstance(data, (list, tuple)) and len(data) == 1:
            return format_json(data[0])
        return format_json(data)
    if isinstance(data, (list, tuple)) and data:
        if isinstance(data[0], dict):
            return format_tsv(data, columns=columns, headers=headers)
        if isinstance(data[0], str):
            return format_simple_list(data)
    if isinstance(data, dict):
        # Dict of lists (grouped output) - render as sections
        lines = []
        for key, items in sorted(data.items()):
            lines.append(f"\n{key}:")
            for item in items:
                if isinstance(item, dict):
                    lines.append(f"  {item.get('id', item)}")
                else:
                    lines.append(f"  {item}")
        return "\n".join(lines)
    return format_json(data)


def print_output(
    data: Any,
    as_json: bool = False,
    columns: Optional[List[str]] = None,
    headers: bool = True,
    file: TextIO = None,
    extended_columns: Optional[List[str]] = None,
) -> None:
    """Format and print data.

    Args:
        data: Data to format.
        as_json: If True, output JSON.
        columns: Column order for TSV (basic columns).
        headers: Whether to include headers in TSV.
        file: Output file (default: stdout).
        extended_columns: Additional columns from 'extended' dict to flatten for TSV.
    """
    # For TSV with extended columns, flatten the extended dict
    if not as_json and extended_columns and isinstance(data, (list, tuple)):
        data = flatten_extended(data, extended_columns)
        if columns:
            columns = columns + extended_columns

    output = format_output(data, as_json=as_json, columns=columns, headers=headers)
    print(output, file=file or sys.stdout)


def flatten_extended(
    data: Sequence[Dict[str, Any]],
    extended_columns: List[str],
) -> List[Dict[str, Any]]:
    """Flatten 'extended' dict fields into top-level for TSV output.

    Args:
        data: List of dicts, each may have an 'extended' sub-dict.
        extended_columns: Keys to extract from 'extended' and promote to top-level.

    Returns:
        List of dicts with extended fields flattened.

    Example:
        >>> data = [{"id": "x", "extended": {"currency": "USD", "rtl": False}}]
        >>> flatten_extended(data, ["currency", "rtl"])
        [{'id': 'x', 'extended': {...}, 'currency': 'USD', 'rtl': False}]
    """
    result = []
    for row in data:
        new_row = dict(row)
        ext = row.get("extended", {})
        for col in extended_columns:
            val = ext.get(col)
            # Handle nested dicts (like quotes, paper_size)
            if isinstance(val, dict):
                val = ",".join(f"{k}={v}" for k, v in val.items())
            new_row[col] = val
        result.append(new_row)
    return result
