"""CLI command for IDNA encoding/decoding."""

import argparse

from ...errors import IDNAError
from ...idna import idna_decode, idna_encode
from ..subcommand_base import SubcommandBase, handles_errors


class IDNACommand(SubcommandBase):
    """Internationalized domain name encoding/decoding."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the idna command with its subcommands."""
        parser = subparsers.add_parser(
            "idna",
            aliases=["punycode", "idn"],
            help="IDNA/Punycode encoding and decoding",
            description="""
Convert between Unicode domain names and ASCII (Punycode) encoding.

Internationalized domain names (IDN) allow non-ASCII characters in
domain names. IDNA encoding converts them to ASCII-compatible format.

Examples:
  # Encode Unicode domain to Punycode
  icukit idna encode 'münchen.de'
  # Output: xn--mnchen-3ya.de

  # Decode Punycode to Unicode
  icukit idna decode 'xn--mnchen-3ya.de'
  # Output: münchen.de

  # Process multiple domains
  echo -e 'münchen.de\\n例え.jp' | icukit idna encode
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "encode": {
                    "aliases": ["e", "to-ascii", "ascii"],
                    "help": "Encode Unicode domain to ASCII (Punycode)",
                    "func": cls.cmd_encode,
                    "configure": cls._configure_encode,
                },
                "decode": {
                    "aliases": ["d", "to-unicode", "unicode"],
                    "help": "Decode ASCII (Punycode) to Unicode",
                    "func": cls.cmd_decode,
                    "configure": cls._configure_decode,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_encode(cls, parser):
        """Configure encode subcommand."""
        parser.add_argument(
            "domain",
            nargs="?",
            help="Unicode domain to encode (or read from stdin)",
        )
        cls._add_input_options(parser)

    @classmethod
    def _configure_decode(cls, parser):
        """Configure decode subcommand."""
        parser.add_argument(
            "domain",
            nargs="?",
            help="ASCII domain to decode (or read from stdin)",
        )
        cls._add_input_options(parser)

    @classmethod
    @handles_errors(IDNAError)
    def cmd_encode(cls, args):
        """Encode Unicode domain to ASCII."""
        if args.domain:
            domains = [args.domain]
        else:
            text = cls._read_input(args)
            if not text:
                return 0
            domains = text.strip().split("\n")

        for domain in domains:
            domain = domain.strip()
            if domain:
                result = idna_encode(domain)
                print(result)
        return 0

    @classmethod
    @handles_errors(IDNAError)
    def cmd_decode(cls, args):
        """Decode ASCII domain to Unicode."""
        if args.domain:
            domains = [args.domain]
        else:
            text = cls._read_input(args)
            if not text:
                return 0
            domains = text.strip().split("\n")

        for domain in domains:
            domain = domain.strip()
            if domain:
                result = idna_decode(domain)
                print(result)
        return 0
