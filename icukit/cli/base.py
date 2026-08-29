"""Base utilities for CLI commands."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TextIO

from ..errors import ICUKitError


@contextmanager
def open_output(
    output_path: str | None, should_commit: Callable[[], bool] | None = None
) -> Iterator[TextIO]:
    """Open stdout or atomically replace an output file with UTF-8 text.

    A named output is written to a temporary file in the destination directory
    and moved into place only after the producer completes successfully. Existing
    files are replaced; missing or unwritable directories fail without changing
    the destination.

    Args:
        output_path: Destination path, or ``None`` to yield standard output.
        should_commit: Optional callback evaluated after output closes. When it
            returns false, discard the temporary output instead of replacing the
            destination.

    Yields:
        A writable text stream.
    """
    if output_path:
        directory = os.path.dirname(os.path.abspath(output_path))
        try:
            try:
                output_mode = stat.S_IMODE(os.stat(output_path).st_mode)
            except FileNotFoundError:
                current_umask = os.umask(0)
                os.umask(current_umask)
                output_mode = 0o666 & ~current_umask
            fd, temporary_path = tempfile.mkstemp(prefix=".icukit-", dir=directory)
        except OSError as e:
            raise ICUKitError(f"cannot write {output_path}: {e.strerror}") from e
        try:
            os.fchmod(fd, output_mode)
            f = os.fdopen(fd, "w", encoding="utf-8")
        except OSError as e:
            os.close(fd)
            os.unlink(temporary_path)
            raise ICUKitError(f"cannot write {output_path}: {e.strerror}") from e
        try:
            with f:
                yield f
            if should_commit is not None and not should_commit():
                return
            try:
                os.replace(temporary_path, output_path)
            except OSError as e:
                raise ICUKitError(f"cannot write {output_path}: {e.strerror}") from e
        finally:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
    else:
        yield sys.stdout


def process_input(
    args,
    processor: Callable[[str], Any],
    output: TextIO,
    process_whole_file: bool = False,
):
    """Process input from files or stdin.

    Args:
        args: Command arguments with 'text', 'files' attributes
        processor: Function to process text
        output: Output file handle
        process_whole_file: If True, read entire file before processing
    """
    if hasattr(args, "text") and args.text:
        _process_content(processor, args.text, output)
    elif hasattr(args, "files") and args.files:
        for filepath in args.files:
            try:
                infile = open(filepath)
            except OSError as e:
                raise ICUKitError(f"cannot read {filepath}: {e.strerror}") from e
            with infile:
                if process_whole_file:
                    content = infile.read()
                    _process_content(processor, content, output)
                else:
                    for line in infile:
                        _process_content(processor, line.rstrip("\n"), output)
    else:
        if process_whole_file:
            content = sys.stdin.read()
            _process_content(processor, content, output)
        else:
            for line in sys.stdin:
                _process_content(processor, line.rstrip("\n"), output)


def _process_content(processor: Callable, content: str, output: TextIO):
    if not content:
        return
    result = processor(content)
    if hasattr(result, "__iter__") and not isinstance(result, str):
        for item in result:
            if isinstance(item, list):
                print(" ".join(str(x) for x in item), file=output)
            else:
                print(item, file=output)
    elif result is not None:
        print(result, file=output)
