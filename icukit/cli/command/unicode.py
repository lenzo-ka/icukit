"""Unicode normalization and character properties CLI command."""

import argparse
import codecs
import re
import sys

from ...errors import NormalizationError
from ...formatters import print_output
from ...unicode import (
    NFC,
    NFD,
    NFKC,
    NFKD,
    get_block_characters,
    get_category_characters,
    get_char_info,
    get_char_name,
    is_normalized,
    list_blocks,
    list_categories,
    normalize,
)
from ..base import open_output, process_input
from ..subcommand_base import SubcommandBase

# Unicode surrogate pair constants
_SURROGATE_OFFSET = 0x10000
_HIGH_SURROGATE_BASE = 0xD800
_LOW_SURROGATE_BASE = 0xDC00
_SURROGATE_SHIFT = 10
_SURROGATE_MASK = 0x3FF


class UnicodeCommand(SubcommandBase):
    """Unicode normalization and character properties command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the unicode command with its subcommands."""
        parser = subparsers.add_parser(
            "unicode",
            help="Unicode normalization and character info",
            description="""
Normalize Unicode text and query character properties.

Normalization forms:
  NFC  - Canonical composition (default, recommended for storage)
  NFD  - Canonical decomposition
  NFKC - Compatibility composition (normalizes ligatures, etc.)
  NFKD - Compatibility decomposition

Examples:
  # Normalize text to NFC (default)
  echo 'café' | icukit unicode normalize

  # Normalize to specific form
  echo 'café' | icukit unicode normalize --form NFD
  echo 'ﬁ' | icukit unicode normalize --form NFKC  # fi ligature -> fi

  # Check if text is normalized
  icukit unicode check -t 'café' --form NFC

  # Get character name
  icukit unicode name -t 'α'
  icukit unicode name -t '😀'

  # Get character info using escape sequences
  icukit unicode info -t '\\u03B1'      # Greek alpha
  icukit unicode info -t 'U+1F600'      # Grinning face emoji
  icukit unicode info -t '\\U0001F600'  # Same, 8-digit form

  # Get full character info
  icukit unicode info -t 'α' --json

  # List Unicode categories, blocks, or normalization forms
  icukit unicode list
  icukit unicode list categories
  icukit unicode list blocks
  icukit unicode list forms

  # Get characters in a Unicode block
  icukit unicode block 'Basic Latin'
  icukit unicode block 'Greek and Coptic' --json

  # Get characters in a Unicode category
  icukit unicode category Lu
  icukit unicode category Nd --json

  # Convert between escape formats
  icukit unicode encode -t 'α' --format u      # \\u03B1
  icukit unicode encode -t 'α' --format U      # \\U000003B1
  icukit unicode encode -t 'α' --format x      # \\xCE\\xB1 (UTF-8 bytes)
  icukit unicode encode -t 'α' --format uplus  # U+03B1
  icukit unicode encode -t '\\u03B1' --format char  # α (decode to char)
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "normalize": {
                    "aliases": ["norm", "n"],
                    "help": "Normalize text to a Unicode form",
                    "func": cls.cmd_normalize,
                    "configure": cls._configure_normalize,
                },
                "check": {
                    "aliases": ["c"],
                    "help": "Check if text is normalized",
                    "func": cls.cmd_check,
                    "configure": cls._configure_check,
                },
                "name": {
                    "aliases": ["charname"],
                    "help": "Get Unicode character name(s)",
                    "func": cls.cmd_name,
                    "configure": cls._configure_name,
                },
                "info": {
                    "aliases": ["i", "char"],
                    "help": "Get character information",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
                "list": {
                    "aliases": ["l", "ls", "categories", "cats", "cat"],
                    "help": "List Unicode categories, blocks, or forms",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
                "block": {
                    "help": "Get characters in a Unicode block",
                    "func": cls.cmd_block,
                    "configure": cls._configure_block,
                },
                "category": {
                    "aliases": ["cat-chars"],
                    "help": "Get characters in a Unicode category",
                    "func": cls.cmd_category,
                    "configure": cls._configure_category,
                },
                "encode": {
                    "aliases": ["e", "enc", "escape", "convert"],
                    "help": "Convert characters to/from escape formats",
                    "func": cls.cmd_encode,
                    "configure": cls._configure_encode,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_normalize(cls, parser):
        """Configure normalize subcommand."""
        cls._add_input_options(parser)
        parser.add_argument(
            "-f",
            "--form",
            choices=[NFC, NFD, NFKC, NFKD],
            default=NFC,
            help="Normalization form (default: NFC)",
        )
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _configure_check(cls, parser):
        """Configure check subcommand."""
        cls._add_input_options(parser)
        parser.add_argument(
            "-f",
            "--form",
            choices=[NFC, NFD, NFKC, NFKD],
            default=NFC,
            help="Normalization form to check (default: NFC)",
        )

    @classmethod
    def _configure_name(cls, parser):
        """Configure name subcommand."""
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument(
            "type",
            nargs="?",
            choices=["categories", "blocks", "forms"],
            default="categories",
            help="What to list (default: categories)",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_block(cls, parser):
        """Configure block subcommand."""
        parser.add_argument("name", help="Unicode block name (e.g., 'Basic Latin')")
        cls._add_output_options(parser)

    @classmethod
    def _configure_category(cls, parser):
        """Configure category subcommand."""
        parser.add_argument("code", help="Unicode category code (e.g., 'Lu', 'Nd')")
        cls._add_output_options(parser)

    @classmethod
    def _configure_encode(cls, parser):
        """Configure encode subcommand."""
        cls._add_input_options(parser)
        parser.add_argument(
            "-f",
            "--format",
            choices=["u", "U", "x", "uplus", "char"],
            default="uplus",
            help="Output format: u (\\uXXXX), U (\\UXXXXXXXX), x (\\xXX UTF-8), "
            "uplus (U+XXXX), char (decode to character). Default: uplus",
        )

    @classmethod
    def _decode_escapes(cls, text: str) -> str:
        """Decode Unicode escape sequences in text.

        Handles:
            - \\uXXXX (4-digit Unicode)
            - \\UXXXXXXXX (8-digit Unicode)
            - \\xXX (hex byte)
            - U+XXXX or U+XXXXXX (Unicode notation)
        """

        # Handle U+XXXX notation (not a Python escape)
        def replace_uplus(match):
            codepoint = int(match.group(1), 16)
            return chr(codepoint)

        text = re.sub(r"U\+([0-9A-Fa-f]{4,6})", replace_uplus, text)

        # Handle Python-style escapes (\uXXXX, \UXXXXXXXX, \xXX)
        try:
            text = codecs.decode(text, "unicode_escape")
        except (UnicodeDecodeError, ValueError):
            pass  # Not valid escapes, return as-is

        return text

    @classmethod
    def cmd_normalize(cls, args):
        """Normalize text to a Unicode form."""
        try:
            form = args.form

            def processor(text):
                return normalize(text, form)

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, processor, output)
            return 0
        except NormalizationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_check(cls, args):
        """Check if text is normalized."""
        try:
            text = cls._read_input(args)
            form = args.form
            normalized = is_normalized(text, form)
            print("true" if normalized else "false")
            return 0 if normalized else 1
        except NormalizationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_name(cls, args):
        """Get Unicode character name(s)."""
        text = cls._read_input(args).strip()
        text = cls._decode_escapes(text)
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        data = []
        for char in text:
            try:
                name = get_char_name(char)
                data.append({"char": char, "codepoint": f"U+{ord(char):04X}", "name": name})
            except ValueError:
                pass

        print_output(
            data,
            as_json=as_json,
            columns=["char", "codepoint", "name"],
            headers=not no_header,
        )
        return 0

    @classmethod
    def cmd_info(cls, args):
        """Get character information."""
        text = cls._read_input(args).strip()
        text = cls._decode_escapes(text)
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        data = []
        for char in text:
            try:
                info = get_char_info(char)
                data.append(info)
            except ValueError:
                pass

        columns = ["char", "codepoint", "name", "category", "script"]
        print_output(data, as_json=as_json, columns=columns, headers=not no_header)
        return 0

    @classmethod
    def cmd_list(cls, args):
        """List Unicode categories, blocks, or normalization forms."""
        list_type = getattr(args, "type", "categories")
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        if list_type == "forms":
            forms = [
                {"code": "NFC", "description": "Canonical composition (recommended)"},
                {"code": "NFD", "description": "Canonical decomposition"},
                {"code": "NFKC", "description": "Compatibility composition"},
                {"code": "NFKD", "description": "Compatibility decomposition"},
            ]
            print_output(
                forms,
                as_json=as_json,
                columns=["code", "description"],
                headers=not no_header,
            )
        elif list_type == "blocks":
            data = list_blocks()
            print_output(
                data,
                as_json=as_json,
                columns=["name", "range"],
                headers=not no_header,
            )
        else:
            # Default: categories
            data = list_categories()
            print_output(
                data,
                as_json=as_json,
                columns=["code", "description"],
                headers=not no_header,
            )
        return 0

    @classmethod
    def cmd_block(cls, args):
        """Get characters in a Unicode block."""
        try:
            chars = get_block_characters(args.name)
            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            data = []
            for char in chars:
                try:
                    info = get_char_info(char)
                    data.append(info)
                except ValueError:
                    pass

            columns = ["char", "codepoint", "name", "category", "script"]
            print_output(data, as_json=as_json, columns=columns, headers=not no_header)
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_category(cls, args):
        """Get characters in a Unicode category."""
        try:
            chars = get_category_characters(args.code)
            as_json = getattr(args, "json", False)
            no_header = getattr(args, "no_header", False)

            data = []
            for char in chars:
                try:
                    info = get_char_info(char)
                    data.append(info)
                except ValueError:
                    pass

            columns = ["char", "codepoint", "name", "category", "script"]
            print_output(data, as_json=as_json, columns=columns, headers=not no_header)
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def cmd_encode(cls, args):
        """Convert characters to/from escape formats."""
        text = cls._read_input(args).strip()
        fmt = getattr(args, "format", "uplus")

        # Always decode escapes first (so we work with actual chars)
        text = cls._decode_escapes(text)

        if fmt == "char":
            # Already decoded, just print
            print(text)
        elif fmt == "u":
            # \uXXXX format (surrogate pairs for > U+FFFF)
            result = []
            for char in text:
                cp = ord(char)
                if cp < _SURROGATE_OFFSET:
                    result.append(f"\\u{cp:04X}")
                else:
                    # Encode as surrogate pair
                    cp -= _SURROGATE_OFFSET
                    high = _HIGH_SURROGATE_BASE + (cp >> _SURROGATE_SHIFT)
                    low = _LOW_SURROGATE_BASE + (cp & _SURROGATE_MASK)
                    result.append(f"\\u{high:04X}\\u{low:04X}")
            print("".join(result))
        elif fmt == "U":
            # \UXXXXXXXX format
            print("".join(f"\\U{ord(c):08X}" for c in text))
        elif fmt == "x":
            # \xXX format (UTF-8 bytes)
            utf8_bytes = text.encode("utf-8")
            print("".join(f"\\x{b:02X}" for b in utf8_bytes))
        elif fmt == "uplus":
            # U+XXXX format
            print(" ".join(f"U+{ord(c):04X}" for c in text))

        return 0
