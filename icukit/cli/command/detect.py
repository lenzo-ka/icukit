"""CLI command for typed recognition in running text."""

from __future__ import annotations

import argparse
import json
import sys

from ...detectors import date_detectors, number_detectors
from ...engine import DEFAULT_FAMILIES, GUARDED_FAMILIES, flexible_detectors, generated_detectors
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

--flexible adds the flexible readers, which read the forms text writes beyond ICU's
own: negative and accounting currency, mixed measures, other decimal styles, dates
with eras, times with zone names, and the currencies and units ICU chooses for the
locale's language. It reads every locale of the language unless --locales chooses
them, and takes seconds to build. --guarded adds the readings the default readers
refuse on purpose ("one" alone, "May" alone as a month).

Overlapping candidates for a span are expected: recognition deposits a candidate
forest, and downstream consumers perform disambiguation.

Examples:
  # Dates and numbers
  icukit detect -t 'Due March 5, 2024, up 12%'

  # Accounting and negative currency, and mixed measures
  icukit detect --flexible -t 'Paid ($12.50), then -$5, for 5 ft 3 in'

  # A German decimal comma and a measure
  icukit detect --flexible --locale de_DE -t '3,5 kg'

  # Only en_US's own forms (no en_GB "kilometres")
  icukit detect --flexible --locales -t '12 kilometres'

  # en_US and en_GB forms only
  icukit detect --flexible --locales en_GB -t '12 kilometres'

  # The flexible readers of chosen currencies and units only
  icukit detect --flexible --currency EUR --measure kilogram -t '-€5 for 3 kg'

  # A lone spelled-out number
  icukit detect --guarded -t 'one'
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        cls._add_input_options(parser)
        cls._add_locale_option(parser)
        parser.add_argument(
            "--currency",
            action="append",
            default=[],
            metavar="CODE",
            help="Add an ISO currency (with --flexible, the flexible currency readers read "
            "only the currencies given)",
        )
        parser.add_argument(
            "--measure",
            action="append",
            default=[],
            metavar="UNIT",
            help="Add an ICU measure unit, single or mixed (with --flexible, the measure "
            "readers read only the units given)",
        )
        parser.add_argument(
            "--flexible",
            action="store_true",
            help="Add the flexible readers (seconds to build)",
        )
        parser.add_argument(
            "--guarded",
            action="store_true",
            help="Add the readings the default readers refuse on purpose",
        )
        parser.add_argument(
            "--locales",
            nargs="*",
            default=None,
            metavar="LOC",
            help="With --flexible, the other locales of the language to read (default: "
            "every one; none given: the locale alone)",
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
        if args.locales is not None and not args.flexible:
            print("icukit detect: --locales requires --flexible", file=sys.stderr)
            return 2
        # Honor an explicit --text "" (distinct from an omitted option, which reads stdin).
        if getattr(args, "text", None) is not None:
            text = args.text
        else:
            text = cls._read_input(args)
        families = (*DEFAULT_FAMILIES, *GUARDED_FAMILIES) if args.guarded else DEFAULT_FAMILIES
        detectors = generated_detectors(args.locale, families)
        if args.flexible:
            # The flexible set reads decimals, percents, and the currencies and units asked
            # for (or ICU's choice) itself, so the strict number readers and the
            # per-unit measure readers below would only repeat its readings.
            flexible = flexible_detectors(
                args.locale,
                locales=args.locales,
                currencies=args.currency or None,
                units=args.measure or None,
                guarded=args.guarded,
            )
            detectors = detectors.with_(*flexible.detectors)
        else:
            numbers = number_detectors(
                args.locale, decimal=True, percent=True, currencies=args.currency
            )
            detectors = detectors.with_(*numbers.detectors)
            detectors = detectors.with_(
                *(FlexibleMeasureDetector(args.locale, unit) for unit in args.measure)
            )
        if args.skeleton:
            detectors = detectors.with_(*date_detectors(args.locale, args.skeleton).detectors)
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
