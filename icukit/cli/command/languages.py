"""CLI command for reader availability by language."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from ...availability import AvailabilityRow, _language_summary, availability, available_languages
from ...formatters import print_output
from ...material import MaterialLoadError, load_locale_material
from ..subcommand_base import SubcommandBase


class LanguagesCommand(SubcommandBase):
    """Report reader availability and its ICU, curated, or user source."""

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser(
            "languages",
            help="Report reader availability by language",
            description="""
With LANG, report the default selection of generated and flexible reader families:
default locales, currencies, and units, plus guarded families with --guarded, including
detached quote and prime marks that ICU writes attached to their numbers. Rows with no
source have no usable reader: they were not built or were built with nothing to read.
For a user row, provenance is the material's own provenance.source, verbatim user text
that icukit does not interpret. icukit computes and reports no measured shares.

Without LANG, quickly summarize generated default families and shipped curated tables
for each ICU language. Use a LANG for the specification-level report.
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("lang", nargs="?", metavar="LANG", help="ICU locale or language")
        parser.add_argument(
            "--material",
            action="append",
            default=[],
            metavar="PATH",
            help="Add validated locale material from PATH (repeatable; requires LANG)",
        )
        parser.add_argument(
            "--guarded",
            action="store_true",
            help="Include readers of deliberately guarded readings (requires LANG)",
        )
        parser.add_argument("-j", "--json", action="store_true", help="Output JSON lines")
        parser.set_defaults(func=cls.run)
        return parser

    @staticmethod
    def _materials(paths):
        loaded = []
        failed = False
        for path in paths:
            try:
                loaded.append(load_locale_material(path))
            except MaterialLoadError as error:
                failed = True
                for refusal in error.refusals:
                    print(f"icukit languages: {refusal.code}: {refusal.detail}", file=sys.stderr)
        return None if failed else loaded

    @classmethod
    def run(cls, args):
        if args.lang is None:
            if args.material or args.guarded:
                print("icukit languages: --material and --guarded require LANG", file=sys.stderr)
                return 2
            records = []
            for language in available_languages():
                summary = [f"{family}: {label}" for family, label in _language_summary(language)]
                records.append({"language": language, "availability": "; ".join(summary)})
            if args.json:
                for record in records:
                    print(json.dumps(record, ensure_ascii=False))
            else:
                for record in records:
                    print(f"{record['language']}\t{record['availability']}")
            return 0

        materials = cls._materials(args.material)
        if materials is None:
            return 2
        rows = availability(args.lang, material=materials, guarded=args.guarded)
        records = [asdict(row) for row in rows]
        if args.json:
            for record in records:
                print(json.dumps(record, ensure_ascii=False))
        else:
            for record in records:
                if record["source"] == "icu":
                    record["source"] = "ICU"
            print_output(records, columns=list(AvailabilityRow.__dataclass_fields__))
        return 0
