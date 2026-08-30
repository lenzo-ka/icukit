"""CLI command for text breaking/segmentation."""

from __future__ import annotations

import argparse
import hashlib
import json

import icu

from ... import __version__
from ...breaker import Breaker, RuleBreaker, default_rules
from ...errors import BreakerError, ICUKitError
from ...formatters import print_output
from ..base import open_output, process_input
from ..subcommand_base import SubcommandBase, _read_text_file, handles_errors


class BreakerCommand(SubcommandBase):
    """Text breaking/segmentation command."""

    SPAN_COLUMNS = [
        "text",
        "codepoint_start",
        "codepoint_end",
        "utf8_start",
        "utf8_end",
        "utf16_start",
        "utf16_end",
        "types",
        "statuses",
    ]

    @classmethod
    def _add_provenance_option(cls, parser):
        parser.add_argument(
            "--provenance",
            action="store_true",
            help="Wrap JSON output with ICU, Unicode, PyICU, and icukit versions",
        )

    @classmethod
    def _add_jsonl_option(cls, parser, unit):
        parser.add_argument(
            "--jsonl",
            action="store_true",
            help=f"One JSON object per line: {unit}; takes precedence over --json",
        )

    @classmethod
    def _provenance(cls, extra=None):
        """Return the runtime version stamp used by JSON and JSONL output."""
        return {
            "icu_version": icu.ICU_VERSION,
            "unicode_version": icu.UNICODE_VERSION,
            "pyicu_version": icu.VERSION,
            "icukit_version": __version__,
            **(extra or {}),
        }

    @classmethod
    def _print_jsonl(cls, args, records, extra=None):
        """Print one compact JSON object per line, if there are any records."""
        provenance = cls._provenance(extra) if getattr(args, "provenance", False) else None
        if provenance is not None:
            records = ({**record, "provenance": provenance} for record in records)
        output = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
        if output:
            print(output)

    @classmethod
    def _print_json(cls, args, breaks, extra=None):
        """Print break data, optionally wrapped in a reproducibility document."""
        if not getattr(args, "provenance", False):
            print_output(breaks, as_json=True)
            return

        # Match print_output's established single-item JSON unwrapping inside the
        # document so that --provenance only adds the wrapper and version stamp.
        if isinstance(breaks, (list, tuple)) and len(breaks) == 1:
            breaks = breaks[0]
        print_output(
            {
                "provenance": cls._provenance(extra),
                "breaks": breaks,
            },
            as_json=True,
        )

    @classmethod
    def _validate_provenance(cls, args):
        if (
            getattr(args, "provenance", False)
            and not getattr(args, "json", False)
            and not getattr(args, "jsonl", False)
        ):
            raise BreakerError("--provenance requires --json or --jsonl")

    @classmethod
    def _add_spans_option(cls, parser, *, line_break_type=False):
        fields = (
            "JSON includes text, compatibility start/end, explicit code-point, UTF-8 byte, "
            "UTF-16 code-unit offsets, types, and statuses; TSV shows explicitly named offsets"
        )
        if line_break_type:
            fields += ", plus the break_type at each span's end boundary"
        parser.add_argument(
            "--spans",
            action="store_true",
            help=f"Output structured spans ({fields})",
        )

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

  # Emit one word object per line
  icukit break words --jsonl -t 'Hello, world!'

  # Show the standard ICU word rules to start a tailoring from
  icukit break rules --kind word

  # Segment with a custom RBBI rule file
  icukit break custom -r my.rules -t 'See Fig. 5 now'
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
                    # "c" was already an unambiguous prefix of "chars" before
                    # "custom" existed; naming it keeps that resolution.
                    "aliases": ["g", "c", "chars"],
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
                "rules": {
                    "aliases": ["r", "rule"],
                    "help": "Show standard ICU rule source for tailoring",
                    "func": cls.cmd_rules,
                    "configure": cls._configure_rules,
                },
                "custom": {
                    "aliases": ["cust"],
                    "help": "Segment text with caller-supplied ICU RBBI rules",
                    "func": cls.cmd_custom,
                    "configure": cls._configure_custom,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_sentences(cls, parser):
        """Configure sentences subcommand."""
        cls._add_locale_option(parser)
        cls._add_spans_option(parser)
        cls._add_input_options(parser)
        cls._add_output_options(parser)
        cls._add_jsonl_option(parser, "one sentence per line (a full span object with --spans)")
        cls._add_provenance_option(parser)

    @classmethod
    def _configure_words(cls, parser):
        """Configure words subcommand."""
        cls._add_locale_option(parser)
        cls._add_spans_option(parser)
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
        cls._add_jsonl_option(parser, "one word per line (a full span object with --spans)")
        cls._add_provenance_option(parser)

    @classmethod
    def _configure_lines(cls, parser):
        """Configure lines subcommand."""
        cls._add_locale_option(parser)
        cls._add_spans_option(parser, line_break_type=True)
        cls._add_input_options(parser)
        cls._add_output_options(parser)
        cls._add_jsonl_option(parser, "one line segment per line (a full span object with --spans)")
        cls._add_provenance_option(parser)

    @classmethod
    def _configure_graphemes(cls, parser):
        """Configure graphemes subcommand."""
        cls._add_locale_option(parser)
        display_group = parser.add_mutually_exclusive_group()
        display_group.add_argument(
            "--show-codepoints",
            "-c",
            action="store_true",
            help="Show Unicode codepoints for each grapheme",
        )
        cls._add_spans_option(display_group)
        cls._add_input_options(parser)
        cls._add_output_options(parser)
        cls._add_jsonl_option(
            parser, "one grapheme cluster per line (a full span object with --spans)"
        )
        cls._add_provenance_option(parser)

    @classmethod
    def _configure_tokenize(cls, parser):
        """Configure tokenize subcommand."""
        cls._add_locale_option(parser)
        cls._add_spans_option(parser)
        parser.add_argument(
            "--skip-punctuation",
            "-p",
            action="store_true",
            help="Skip punctuation tokens",
        )
        cls._add_input_options(parser)
        cls._add_output_options(parser)
        cls._add_jsonl_option(parser, "one token per line, each with a 1-based sentence number")
        cls._add_provenance_option(parser)

    @classmethod
    def _configure_rules(cls, parser):
        """Configure standard-rule source display."""
        parser.description = (
            "Show ICU's standard root rule source as a tailoring base. Locale dictionary "
            "and keyword behavior, including CJK dictionary breaking and lw= line options, "
            "is not represented, so recompiling the text may not faithfully clone the "
            "locale iterator."
        )
        parser.add_argument(
            "-k",
            "--kind",
            choices=["word", "sentence", "line", "grapheme"],
            default="word",
            help="Iterator kind (default: word)",
        )
        cls._add_locale_option(parser)
        cls._add_output_options(parser, include_header=False)
        cls._add_jsonl_option(parser, "a single rule-set record")
        cls._add_provenance_option(parser)

    @classmethod
    def _configure_custom(cls, parser):
        """Configure custom-rule segmentation."""
        parser.description = (
            "Segment text with a caller-supplied ICU RBBI rule set rather than a "
            "locale's standard iterator. Segment types come only from --status-type, "
            "since rule statuses are defined by the rule set, not by ICU. Because "
            "the rule set determines the boundaries, --provenance adds a rules_sha256 "
            "digest of it to the version stamp; the four standard version keys alone "
            "do not identify a custom rule set."
        )
        parser.add_argument(
            "-r",
            "--rules",
            required=True,
            metavar="FILE",
            help="ICU RBBI rule file to segment with",
        )
        parser.add_argument(
            "--status-type",
            action="append",
            dest="status_types",
            metavar="N=NAME",
            help="Map numeric rule status N to type name NAME (repeatable)",
        )
        cls._add_spans_option(parser)
        cls._add_input_options(parser)
        cls._add_output_options(parser)
        cls._add_jsonl_option(parser, "one segment per line (a full span object with --spans)")
        cls._add_provenance_option(parser)

    @classmethod
    @handles_errors(BreakerError)
    def cmd_rules(cls, args):
        """Show standard ICU rule source for use as a tailoring base."""
        cls._validate_provenance(args)
        rules = default_rules(args.kind, args.locale)
        record = {"kind": args.kind, "locale": args.locale, "rules": rules}
        if getattr(args, "jsonl", False):
            cls._print_jsonl(args, [record])
        elif getattr(args, "json", False):
            cls._print_json(args, record)
        else:
            print(rules)
        return 0

    @classmethod
    @handles_errors(BreakerError, ICUKitError)
    def cmd_custom(cls, args):
        """Segment text using caller-supplied ICU RBBI rules."""
        cls._validate_provenance(args)
        rules_text = _read_text_file(args.rules)
        status_types = {}
        for entry in args.status_types or []:
            try:
                number, name = entry.split("=", 1)
                number = int(number)
            except (ValueError, TypeError) as e:
                raise BreakerError(f"Invalid --status-type '{entry}': expected N=NAME") from e
            status_types[number] = name

        breaker = RuleBreaker(rules_text, status_types)
        text = "\n".join(cls._read_lines(args))
        extra = {"rules_sha256": hashlib.sha256(rules_text.encode("utf-8")).hexdigest()}
        if getattr(args, "spans", False):
            spans = breaker.spans(text)
            if getattr(args, "jsonl", False):
                cls._print_jsonl(args, spans, extra)
            elif getattr(args, "json", False):
                cls._print_json(args, spans, extra)
            else:
                print_output(
                    spans,
                    columns=cls.SPAN_COLUMNS,
                    headers=not getattr(args, "no_header", False),
                )
            return 0

        tokens = breaker.tokens(text)
        if getattr(args, "jsonl", False):
            cls._print_jsonl(args, ({"text": token} for token in tokens), extra)
        elif getattr(args, "json", False):
            cls._print_json(args, tokens, extra)
        else:
            for token in tokens:
                print(token)
        return 0

    @classmethod
    @handles_errors(BreakerError)
    def cmd_sentences(cls, args):
        """Break text into sentences; spans retain unstripped source segments."""
        breaker = Breaker(args.locale)
        cls._validate_provenance(args)
        as_json = getattr(args, "json", False)
        as_jsonl = getattr(args, "jsonl", False)

        if getattr(args, "spans", False):
            text = "\n".join(cls._read_lines(args))
            spans = breaker.break_sentence_spans(text)
            if as_jsonl:
                cls._print_jsonl(args, spans)
            elif as_json:
                cls._print_json(args, spans)
            else:
                print_output(
                    spans,
                    columns=cls.SPAN_COLUMNS,
                    headers=not getattr(args, "no_header", False),
                )
            return 0

        if as_jsonl or as_json:
            text = "\n".join(cls._read_lines(args))
            sentences = [sentence.strip() for sentence in breaker.iter_sentences(text)]
            if as_jsonl:
                cls._print_jsonl(args, ({"text": sentence} for sentence in sentences))
            else:
                cls._print_json(args, sentences)
            return 0

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
        cls._validate_provenance(args)
        skip_punct = getattr(args, "skip_punctuation", False)
        skip_ws = not getattr(args, "include_whitespace", False)

        as_json = getattr(args, "json", False)
        as_jsonl = getattr(args, "jsonl", False)

        if getattr(args, "spans", False):
            text = "\n".join(cls._read_lines(args))
            spans = breaker.break_word_spans(text, skip_ws, skip_punct)
            if as_jsonl:
                cls._print_jsonl(args, spans)
            elif as_json:
                cls._print_json(args, spans)
            else:
                print_output(
                    spans,
                    columns=cls.SPAN_COLUMNS,
                    headers=not getattr(args, "no_header", False),
                )
            return 0

        if as_jsonl or as_json:
            # Collect all words for JSON output
            lines = cls._read_lines(args)
            text = "\n".join(lines)
            words = breaker.break_words(text, skip_ws, skip_punct)
            if as_jsonl:
                cls._print_jsonl(args, ({"text": word} for word in words))
            else:
                cls._print_json(args, words)
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
        cls._validate_provenance(args)

        as_json = getattr(args, "json", False)
        as_jsonl = getattr(args, "jsonl", False)

        if getattr(args, "spans", False):
            text = "\n".join(cls._read_lines(args))
            spans = breaker.break_line_spans(text)
            if as_jsonl:
                cls._print_jsonl(args, spans)
            elif as_json:
                cls._print_json(args, spans)
            else:
                print_output(
                    spans,
                    columns=[*cls.SPAN_COLUMNS, "break_type"],
                    headers=not getattr(args, "no_header", False),
                )
            return 0

        if as_jsonl or as_json:
            lines = cls._read_lines(args)
            text = "\n".join(lines)
            segments = breaker.break_lines(text)
            if as_jsonl:
                cls._print_jsonl(args, ({"text": segment} for segment in segments))
            else:
                cls._print_json(args, segments)
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
        cls._validate_provenance(args)
        show_codepoints = getattr(args, "show_codepoints", False)
        as_json = getattr(args, "json", False)
        as_jsonl = getattr(args, "jsonl", False)
        no_header = getattr(args, "no_header", False)

        lines = cls._read_lines(args)
        text = "\n".join(lines)
        if getattr(args, "spans", False):
            spans = breaker.break_grapheme_spans(text)
            if as_jsonl:
                cls._print_jsonl(args, spans)
            elif as_json:
                cls._print_json(args, spans)
            else:
                print_output(spans, columns=cls.SPAN_COLUMNS, headers=not no_header)
            return 0

        graphemes = breaker.break_graphemes(text)

        if show_codepoints or as_json or as_jsonl:
            data = []
            for g in graphemes:
                codepoints = " ".join(f"U+{ord(c):04X}" for c in g)
                data.append({"grapheme": g, "codepoints": codepoints, "length": len(g)})
            if as_jsonl:
                cls._print_jsonl(args, data)
            elif as_json:
                cls._print_json(args, data)
            else:
                print_output(
                    data,
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
        cls._validate_provenance(args)
        skip_punct = getattr(args, "skip_punctuation", False)
        as_json = getattr(args, "json", False)
        as_jsonl = getattr(args, "jsonl", False)

        lines = cls._read_lines(args)
        text = "\n".join(lines)
        if getattr(args, "spans", False):
            tokenized = breaker.tokenize_sentence_spans(text, skip_punctuation=skip_punct)
            if as_jsonl:
                rows = [
                    {"sentence": sentence_number, **span}
                    for sentence_number, sentence in enumerate(tokenized, 1)
                    for span in sentence
                ]
                cls._print_jsonl(args, rows)
            elif as_json:
                cls._print_json(args, tokenized)
            else:
                rows = [
                    {"sentence": sentence_number, **span}
                    for sentence_number, sentence in enumerate(tokenized, 1)
                    for span in sentence
                ]
                print_output(
                    rows,
                    columns=["sentence", *cls.SPAN_COLUMNS],
                    headers=not getattr(args, "no_header", False),
                )
            return 0

        tokenized = breaker.tokenize_sentences(text, skip_punctuation=skip_punct)

        if as_jsonl:
            rows = [
                {"sentence": sentence_number, "text": token}
                for sentence_number, sentence in enumerate(tokenized, 1)
                for token in sentence
            ]
            cls._print_jsonl(args, rows)
        elif as_json:
            cls._print_json(args, tokenized)
        else:
            for i, tokens in enumerate(tokenized, 1):
                print(f"{i}. {' '.join(tokens)}")
        return 0
