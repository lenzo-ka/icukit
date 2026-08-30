"""CLI command for IDNA encoding/decoding."""

from __future__ import annotations

import argparse

from ...errors import IDNAError
from ...formatters import print_output
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

  # Machine-readable output: always a list of {input, output}, at any size
  echo -e 'münchen.de\\n例え.jp' | icukit idna encode --json
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
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _configure_decode(cls, parser):
        """Configure decode subcommand."""
        parser.add_argument(
            "domain",
            nargs="?",
            help="ASCII domain to decode (or read from stdin)",
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser, include_header=False)

    @classmethod
    def _convert_domains(cls, args, convert):
        """Convert every non-blank input domain, in order.

        The batch is a collection at every size, so JSON output is always a list of
        ``{"input", "output"}`` records: empty input gives ``[]``, and a single domain
        gives a one-element list, never a bare object.
        """
        if args.domain:
            domains = [args.domain]
        else:
            text = cls._read_input(args)
            domains = text.strip().split("\n") if text else []

        records = [
            {"input": stripped, "output": convert(stripped)}
            for stripped in (domain.strip() for domain in domains)
            if stripped
        ]

        if getattr(args, "json", False):
            print_output(records, as_json=True)
        else:
            for record in records:
                print(record["output"])
        return 0

    @classmethod
    @handles_errors(IDNAError)
    def cmd_encode(cls, args):
        """Encode Unicode domain to ASCII."""
        return cls._convert_domains(args, idna_encode)

    @classmethod
    @handles_errors(IDNAError)
    def cmd_decode(cls, args):
        """Decode ASCII domain to Unicode."""
        return cls._convert_domains(args, idna_decode)
