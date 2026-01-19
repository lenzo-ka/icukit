"""CLI command for text breaking/segmentation."""

import argparse

from ...breaker import Breaker
from ...errors import BreakerError
from ...formatters import print_output
from ..base import open_output, process_input
from ..subcommand_base import SubcommandBase, handles_errors


class BreakerCommand(SubcommandBase):
    """Text breaking/segmentation command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the break command with its subcommands."""
        parser = subparsers.add_parser(
            "break",
            help="Break text into sentences, words, or graphemes",
            description="""
Break text into linguistic units using ICU's BreakIterator.

Supports locale-aware segmentation for sentences, words, line breaks,
and grapheme clusters (user-perceived characters).

Examples:
  # Break into sentences
  echo 'Hello world. How are you?' | icukit break sentences

  # Break into words
  icukit break words -t 'Hello, world!'

  # Break into words, skipping punctuation
  icukit break words --skip-punctuation -t 'Hello, world!'

  # Use Japanese locale for word breaking
  icukit break words --locale ja -t 'こんにちは世界'

  # Break into grapheme clusters (handles emoji correctly)
  icukit break graphemes -t '👨‍👩‍👧‍👦'

  # Tokenize sentences (sentences then words)
  icukit break tokenize -t 'Hello world. How are you?'
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "sentences": {
                    "aliases": ["s", "sent"],
                    "help": "Break text into sentences",
                    "func": cls.cmd_sentences,
                    "configure": cls._configure_sentences,
                },
                "words": {
                    "aliases": ["w", "word"],
                    "help": "Break text into words",
                    "func": cls.cmd_words,
                    "configure": cls._configure_words,
                },
                "lines": {
                    "aliases": ["l", "line"],
                    "help": "Find line break opportunities",
                    "func": cls.cmd_lines,
                    "configure": cls._configure_lines,
                },
                "graphemes": {
                    "aliases": ["g", "chars"],
                    "help": "Break into grapheme clusters",
                    "func": cls.cmd_graphemes,
                    "configure": cls._configure_graphemes,
                },
                "tokenize": {
                    "aliases": ["t", "tok"],
                    "help": "Break into sentences then words",
                    "func": cls.cmd_tokenize,
                    "configure": cls._configure_tokenize,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _add_locale_option(cls, parser):
        """Add locale option."""
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for breaking rules (default: en_US)",
        )

    @classmethod
    def _configure_sentences(cls, parser):
        """Configure sentences subcommand."""
        cls._add_locale_option(parser)
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_words(cls, parser):
        """Configure words subcommand."""
        cls._add_locale_option(parser)
        parser.add_argument(
            "--skip-punctuation",
            "-p",
            action="store_true",
            help="Skip punctuation tokens",
        )
        parser.add_argument(
            "--include-whitespace",
            action="store_true",
            help="Include whitespace tokens (excluded by default)",
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_lines(cls, parser):
        """Configure lines subcommand."""
        cls._add_locale_option(parser)
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_graphemes(cls, parser):
        """Configure graphemes subcommand."""
        cls._add_locale_option(parser)
        parser.add_argument(
            "--show-codepoints",
            "-c",
            action="store_true",
            help="Show Unicode codepoints for each grapheme",
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    def _configure_tokenize(cls, parser):
        """Configure tokenize subcommand."""
        cls._add_locale_option(parser)
        parser.add_argument(
            "--skip-punctuation",
            "-p",
            action="store_true",
            help="Skip punctuation tokens",
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)

    @classmethod
    @handles_errors(BreakerError)
    def cmd_sentences(cls, args):
        """Break text into sentences."""
        breaker = Breaker(args.locale)

        def processor(text):
            for sentence in breaker.iter_sentences(text):
                yield sentence.strip()

        with open_output(getattr(args, "output", None)) as output:
            process_input(args, processor, output, process_whole_file=True)
        return 0

    @classmethod
    @handles_errors(BreakerError)
    def cmd_words(cls, args):
        """Break text into words."""
        breaker = Breaker(args.locale)
        skip_punct = getattr(args, "skip_punctuation", False)
        skip_ws = not getattr(args, "include_whitespace", False)

        as_json = getattr(args, "json", False)

        if as_json:
            # Collect all words for JSON output
            lines = cls._read_lines(args)
            text = "\n".join(lines)
            words = breaker.break_words(text, skip_ws, skip_punct)
            print_output(words, as_json=True)
        else:

            def processor(text):
                return breaker.iter_words(text, skip_ws, skip_punct)

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, processor, output, process_whole_file=True)
        return 0

    @classmethod
    @handles_errors(BreakerError)
    def cmd_lines(cls, args):
        """Find line break opportunities."""
        breaker = Breaker(args.locale)

        as_json = getattr(args, "json", False)

        if as_json:
            lines = cls._read_lines(args)
            text = "\n".join(lines)
            segments = breaker.break_lines(text)
            print_output(segments, as_json=True)
        else:

            def processor(text):
                return breaker.iter_lines(text)

            with open_output(getattr(args, "output", None)) as output:
                process_input(args, processor, output, process_whole_file=True)
        return 0

    @classmethod
    @handles_errors(BreakerError)
    def cmd_graphemes(cls, args):
        """Break text into grapheme clusters."""
        breaker = Breaker(args.locale)
        show_codepoints = getattr(args, "show_codepoints", False)
        as_json = getattr(args, "json", False)
        no_header = getattr(args, "no_header", False)

        lines = cls._read_lines(args)
        text = "\n".join(lines)
        graphemes = breaker.break_graphemes(text)

        if show_codepoints or as_json:
            data = []
            for g in graphemes:
                codepoints = " ".join(f"U+{ord(c):04X}" for c in g)
                data.append({"grapheme": g, "codepoints": codepoints, "length": len(g)})
            print_output(
                data,
                as_json=as_json,
                columns=["grapheme", "codepoints", "length"],
                headers=not no_header,
            )
        else:
            for g in graphemes:
                print(g)
        return 0

    @classmethod
    @handles_errors(BreakerError)
    def cmd_tokenize(cls, args):
        """Break into sentences then words."""
        breaker = Breaker(args.locale)
        skip_punct = getattr(args, "skip_punctuation", False)
        as_json = getattr(args, "json", False)

        lines = cls._read_lines(args)
        text = "\n".join(lines)
        tokenized = breaker.tokenize_sentences(text, skip_punctuation=skip_punct)

        if as_json:
            print_output(tokenized, as_json=True)
        else:
            for i, tokens in enumerate(tokenized, 1):
                print(f"{i}. {' '.join(tokens)}")
        return 0
