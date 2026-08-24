"""CLI command for typed recognition in running text."""

from __future__ import annotations

import argparse
import json

from ...detectors import date_detectors, number_detectors
from ...engine import generated_detectors
from ...formatters import format_json, format_tsv
from ...recognize import FlexibleMeasureDetector
from ...serialize import detection_to_dict, detections_to_json
from ..subcommand_base import SubcommandBase


class DetectCommand(SubcommandBase):
    """Typed running-text recognition command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the detect command."""
        parser = subparsers.add_parser(
            "detect",
            help="Recognize typed values in running text",
            description="""
Recognize typed values in running text. Offsets are half-open Unicode code-point
indices. The default set covers dates, date intervals, compact numbers, relative
dates, scientific numbers, spellout numbers, abbreviations, decimals, and percents.
Currencies and measures require explicit --currency and --measure options.

Overlapping candidates for a span are expected: recognition deposits a candidate
forest, and downstream consumers perform disambiguation.
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        cls._add_input_options(parser)
        cls._add_locale_option(parser)
        parser.add_argument(
            "--currency", action="append", default=[], metavar="CODE", help="Add an ISO currency"
        )
        parser.add_argument(
            "--measure", action="append", default=[], metavar="UNIT", help="Add an ICU measure unit"
        )
        parser.add_argument(
            "--skeleton", action="append", default=[], metavar="SKEL", help="Add a date skeleton"
        )
        cls._add_output_options(parser)
        parser.add_argument(
            "--jsonl",
            action="store_true",
            help="One JSON object per line (one detection per line)",
        )
        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
        """Recognize and render typed candidates."""
        # Honor an explicit --text "" (distinct from an omitted option, which reads stdin).
        if getattr(args, "text", None) is not None:
            text = args.text
        else:
            text = cls._read_input(args)
        detectors = generated_detectors(args.locale)
        numbers = number_detectors(
            args.locale, decimal=True, percent=True, currencies=args.currency
        )
        detectors = detectors.with_(*numbers.detectors)
        if args.skeleton:
            detectors = detectors.with_(*date_detectors(args.locale, args.skeleton).detectors)
        detectors = detectors.with_(
            *(FlexibleMeasureDetector(args.locale, unit) for unit in args.measure)
        )
        detections = detectors.detect(text)

        if args.jsonl:
            output = "\n".join(
                json.dumps(detection_to_dict(item), ensure_ascii=False) for item in detections
            )
        elif args.json:
            output = format_json(detections_to_json(detections))
        else:
            columns = ["start", "end", "type", "text"]
            rows = [
                {
                    "start": item["start"],
                    "end": item["end"],
                    "type": item["type"],
                    "text": item["text"].replace("\t", " ").replace("\n", " "),
                }
                for item in detections
            ]
            output = format_tsv(rows, columns=columns, headers=not args.no_header)
            # format_tsv returns "" for empty data; still emit the header when one is wanted.
            if not rows and not args.no_header:
                output = "\t".join(columns)

        # Only print when there is content, so empty JSONL/headerless output adds no blank line.
        if args.output:
            with open(args.output, "w") as output_file:
                if output:
                    print(output, file=output_file)
        elif output:
            print(output)
        return 0
