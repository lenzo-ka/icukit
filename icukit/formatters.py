"""Output formatters for rendering structured data.

This module provides formatters for rendering data as JSON, TSV, or the
human-readable output used by icukit's command-line interface.

Usage:
    data = [{"id": "foo", "value": 1}, {"id": "bar", "value": 2}]

    # TSV output (default)
    print(format_tsv(data))

    # JSON output
    print(format_json(data))

    # Auto-format based on args
    print(format_output(data, as_json=args.json))
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from typing import Any, TextIO

__all__ = [
    "flatten_extended",
    "format_json",
    "format_output",
    "format_simple_list",
    "format_tsv",
    "print_output",
]


def format_json(data: Any, indent: int | None = 2) -> str:
    """Serialize data as JSON text.

    Args:
        data: Data to serialize. Values unsupported by JSON are converted to strings.
        indent: Number of spaces to use for each indentation level, or ``None`` for
            compact output.

    Returns:
        JSON text containing non-ASCII characters without ASCII escaping.
    """
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def format_tsv(
    data: Sequence[dict[str, Any]],
    columns: list[str] | None = None,
    headers: bool = True,
) -> str:
    """Render a sequence of mappings as tab-separated text.

    Args:
        data: Rows to render. Missing columns and empty values are displayed as ``-``.
        columns: Columns to include, in order. By default, use the first row's keys.
        headers: Include a header when rendering more than one column. Single-column
            output never includes a header.

    Returns:
        TSV text without a trailing newline, or an empty string when *data* is empty.
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


def format_simple_list(data: Sequence[Any]) -> str:
    """Render a sequence as newline-separated text.

    Args:
        data: Items to render. Each item is converted to a string.

    Returns:
        Newline-separated text without a trailing newline, or an empty string when
        *data* is empty.
    """
    return "\n".join(str(item) for item in data)


def format_output(
    data: Any,
    as_json: bool = False,
    columns: list[str] | None = None,
    headers: bool = True,
) -> str:
    """Render data as JSON or as icukit's human-readable command output.

    Args:
        data: Data to render. In non-JSON mode, non-empty sequences of mappings become
            TSV, non-empty sequences of strings become newline-separated text, and
            mappings become sorted labeled sections, with a newline before each label.
            Other values fall back to JSON.
        as_json: Render as JSON. A sequence containing one item is unwrapped first.
        columns: Columns to include in TSV output, in order.
        headers: Include a TSV header when more than one column is rendered.

    Returns:
        Formatted text without a trailing newline.
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
    columns: list[str] | None = None,
    headers: bool = True,
    file: TextIO | None = None,
    extended_columns: list[str] | None = None,
) -> None:
    """Render data and write it followed by a newline.

    Args:
        data: Data accepted by :func:`format_output`.
        as_json: Render as JSON.
        columns: Base columns to include in TSV output, in order.
        headers: Include a TSV header when more than one column is rendered.
        file: Text stream to write to. Defaults to standard output.
        extended_columns: Keys from each row's ``extended`` mapping to append as TSV
            columns. Nested mapping values are rendered as comma-separated ``key=value``
            pairs. This transformation is not applied to JSON output.
    """
    # For TSV with extended columns, flatten the extended dict
    if not as_json and extended_columns and isinstance(data, (list, tuple)):
        data = flatten_extended(data, extended_columns)
        if columns:
            columns = columns + extended_columns

    output = format_output(data, as_json=as_json, columns=columns, headers=headers)
    print(output, file=file or sys.stdout)


def flatten_extended(
    data: Sequence[dict[str, Any]],
    extended_columns: list[str],
) -> list[dict[str, Any]]:
    """Copy rows and promote selected ``extended`` values to top-level keys.

    Args:
        data: Rows to copy. Each row may contain an ``extended`` mapping.
        extended_columns: Keys to read from each row's ``extended`` mapping. A missing
            key is promoted with the value ``None``. Nested dictionaries are rendered
            as comma-separated ``key=value`` pairs in their iteration order.

    Returns:
        New shallow copies with the requested keys promoted. Input rows are not
        mutated, and the ``extended`` key is retained in each copied row.
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
