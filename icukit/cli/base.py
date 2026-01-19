"""Base utilities for CLI commands."""

import json
import sys
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional, TextIO


@contextmanager
def open_output(output_path: Optional[str]) -> Iterator[TextIO]:
    """Open output file or return stdout."""
    if output_path:
        with open(output_path, "w") as f:
            yield f
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
            with open(filepath, "r") as infile:
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


def add_input_args(parser):
    """Add common input arguments to a parser."""
    parser.add_argument("-t", "--text", help="Text to process (instead of files/stdin)")
    parser.add_argument("files", nargs="*", help="Files to process (default: stdin)")


class OutputFormatters:
    """Common output formatting functions."""

    @staticmethod
    def one_per_line(items, output: TextIO):
        for item in items:
            print(item, file=output)

    @staticmethod
    def json_output(data: Any, output: TextIO, pretty: bool = True):
        if pretty:
            json.dump(data, output, ensure_ascii=False, indent=2)
        else:
            json.dump(data, output, ensure_ascii=False)
        output.write("\n")
