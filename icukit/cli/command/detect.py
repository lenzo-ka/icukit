"""CLI command for typed recognition in running text."""

from __future__ import annotations

import argparse
import json
import sys

import icu

from ...engine import reader_set
from ...formatters import format_json, format_tsv
from ...material import MaterialLoadError, load_locale_material
from ...recognize import _iso_currency_codes
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
Dates with an era are read in ICU's own forms, with four-digit years ("Mar 5, 2024
BC"). Ranges are read as ICU writes them: of numbers and percents ("3–5", "10–15%",
"~3") and of years ("1914–1918"). Currencies and measures require explicit --currency
and --measure options, and with them their ranges are read too ("$3–5", "10–15 kg").
Amount ranges keep "start", "separator", and "end" captures and add each endpoint's
own captures as "start.*" and "end.*"; approximate amounts similarly add "value.*".

--flexible adds the flexible readers, which read the forms text writes beyond ICU's
own: negative and accounting currency, mixed measures, other decimal styles, dates
with eras in other layouts, times with zone names, and the currencies and units ICU
chooses for the locale's language. It reads every locale of the language unless
--locales chooses them, and takes seconds to build. --guarded adds the readings the
default readers refuse on purpose ("one" alone, "May" alone as a month, "Mar 15,
44 BC" in ICU's own form, and years "44–45").

Overlapping candidates for a span are expected: recognition deposits a candidate
forest, and downstream consumers perform disambiguation.

Examples:
  # Dates and numbers
  icukit detect -t 'Due March 5, 2024, up 12%'

  # Accounting and negative currency, and mixed measures
  icukit detect --flexible -t 'Paid ($12.50), then -$5, for 5 ft 3 in'

  # With --currency, the strict reading "$12.50" inside "($12.50)" as well
  icukit detect --flexible --currency USD -t 'Paid ($12.50)'

  # A German decimal comma and a measure
  icukit detect --flexible --locale de_DE -t '3,5 kg'

  # Only en_US's own forms (no en_GB "kilometres")
  icukit detect --flexible --locales '' -t '12 kilometres'

  # en_US and en_GB forms only
  icukit detect --flexible --locales en_GB -t '12 kilometres'
  icukit detect --flexible --locales en_GB,en_IN notes.txt

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
            "--material",
            action="append",
            default=[],
            metavar="PATH",
            help="Add validated locale material from PATH (repeatable)",
        )
        parser.add_argument(
            "--currency",
            action="append",
            default=[],
            metavar="CODE",
            help="Add an ISO 4217 currency, in either case (with --flexible, the flexible "
            "currency readers read only the currencies given)",
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
            default=None,
            metavar="LOC[,LOC...]",
            help="With --flexible, the other locales of the language to read, comma-separated "
            '(default: every one; "" reads the locale alone)',
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

    @staticmethod
    def _checked_choices(args):
        """The chosen locales, currencies, and units, checked against ICU.

        Raises ValueError, with a message for the user, for a choice ICU does not know.
        """
        locales = None
        if args.locales is not None:
            if not args.flexible:
                raise ValueError("--locales requires --flexible")
            locales = tuple(name.strip() for name in args.locales.split(",") if name.strip())
            available = set(icu.Locale.getAvailableLocales())
            language = icu.Locale(args.locale).getLanguage()
            for name in locales:
                if icu.Locale(name).getName() not in available:
                    raise ValueError(f"unknown locale {name!r} in --locales")
                if icu.Locale(name).getLanguage() != language:
                    raise ValueError(
                        f"--locales {name!r} is not a locale of the language of "
                        f"{args.locale!r} ({language!r})"
                    )
        currencies = []
        known = _iso_currency_codes()
        for code in args.currency:
            if code.upper() not in known:
                raise ValueError(f"unknown ISO 4217 currency {code!r}")
            currencies.append(code.upper())
        units = []
        for unit in args.measure:
            try:
                identifier = icu.MeasureUnit.forIdentifier(unit).getIdentifier() if unit else ""
            except icu.ICUError:
                identifier = ""
            if not identifier:
                raise ValueError(f"unknown ICU measure unit {unit!r}")
            units.append(identifier)
        return locales, currencies, units

    @staticmethod
    def reader_set(
        locale,
        *,
        guarded=False,
        flexible=False,
        locales=None,
        currencies=(),
        units=(),
        skeletons=None,
        material=(),
    ):
        """The readers ``icukit detect`` reads with, for its options."""
        return reader_set(
            locale,
            guarded=guarded,
            flexible=flexible,
            locales=locales,
            currencies=currencies,
            units=units,
            skeletons=skeletons,
            material=material,
        )

    @classmethod
    def run(cls, args):
        """Recognize and render typed candidates."""
        try:
            locales, currencies, units = cls._checked_choices(args)
        except ValueError as error:
            print(f"icukit detect: {error}", file=sys.stderr)
            return 2
        materials = []
        for path in args.material:
            try:
                materials.append(load_locale_material(path))
            except MaterialLoadError as error:
                for refusal in error.refusals:
                    print(f"icukit detect: {refusal.code}: {refusal.detail}", file=sys.stderr)
                return 2
        # Honor an explicit --text "" (distinct from an omitted option, which reads stdin).
        if getattr(args, "text", None) is not None:
            text = args.text
        else:
            text = cls._read_input(args)
        if args.flexible and locales is None:
            language = icu.Locale(args.locale).getLanguage()
            print(
                f"icukit detect: building the flexible readers for every locale of "
                f"{language!r}; pass --locales to narrow",
                file=sys.stderr,
            )
        detectors = cls.reader_set(
            args.locale,
            guarded=args.guarded,
            flexible=args.flexible,
            locales=locales,
            currencies=currencies,
            units=units,
            skeletons=args.skeleton,
            material=materials,
        )
        # A strict and a flexible reader can give the same reading ("$5.00" as USD 5.00);
        # print it once. Distinct readings of one span are all kept, and a reading from
        # user material stays beside ICU's same reading, so its spec (and digest) shows.
        seen = set()
        detections = []
        for item in detectors.detect(text):
            reading = (
                item["start"],
                item["end"],
                item["type"],
                item["text"],
                repr(item["value"]),
                getattr(item["spec"], "material_digest", None),
            )
            if reading not in seen:
                seen.add(reading)
                detections.append(item)

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
