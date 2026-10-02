"""CLI command for preparing detector gangs in the current process."""

from __future__ import annotations

import argparse
import sys

import icu

from ... import cache
from ...compiled import ReaderSpec, compile_detectors
from ...formatters import format_json, format_tsv
from ...material import MaterialLoadError, load_locale_material
from ...recognize import _iso_currency_codes
from ..subcommand_base import SubcommandBase


class CompileCommand(SubcommandBase):
    """Prepare detector gangs and report their compile identities and timings."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the compile command."""
        parser = subparsers.add_parser(
            "compile",
            help="Prepare detector gangs without reading text",
            description="""
Prepare one detector gang per locale without reading input text. Reader construction,
lazy sub-readers, and zone tables are completed in the build phase. L3 keeps the
result in process only; the configured cache directory is reported for the on-disk
table store added in the next cache layer.

Example:
  ik compile --locales en_US,de_DE --flexible --json
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--locales",
            required=True,
            metavar="LOC[,LOC...]",
            help="Locales whose detector gangs to prepare, comma-separated",
        )
        parser.add_argument("--flexible", action="store_true", help="Add flexible readers")
        parser.add_argument("--guarded", action="store_true", help="Add guarded readers")
        parser.add_argument(
            "--read-locales",
            default=None,
            metavar="LOC[,LOC...]",
            help='Other locales read by flexible readers ("" reads each locale alone)',
        )
        parser.add_argument(
            "--currency", action="append", default=[], metavar="CODE", help="Add an ISO currency"
        )
        parser.add_argument(
            "--measure", action="append", default=[], metavar="UNIT", help="Add an ICU measure unit"
        )
        parser.add_argument(
            "--skeleton", action="append", default=[], metavar="SKEL", help="Add a date skeleton"
        )
        parser.add_argument(
            "--material",
            action="append",
            default=[],
            metavar="PATH",
            help="Add validated locale material from PATH (repeatable)",
        )
        parser.add_argument(
            "--cache-dir",
            metavar="DIR",
            help="Set the cache root reported now and used by the later disk table store",
        )
        parser.add_argument("--json", action="store_true", help="Output JSON")
        parser.set_defaults(func=cls.run)
        return parser

    @staticmethod
    def _split(value: str) -> tuple[str, ...]:
        return tuple(part.strip() for part in value.split(",") if part.strip())

    @classmethod
    def run(cls, args):
        """Build, warm, and report each requested detector gang."""
        locales = cls._split(args.locales)
        if not locales:
            print("icukit compile: --locales names at least one locale", file=sys.stderr)
            return 2
        known_locales = set(icu.Locale.getAvailableLocales())
        for locale in locales:
            if icu.Locale(locale).getName() not in known_locales:
                print(f"icukit compile: unknown locale {locale!r}", file=sys.stderr)
                return 2
        read_locales = None if args.read_locales is None else cls._split(args.read_locales)
        if read_locales is not None and not args.flexible:
            print("icukit compile: --read-locales requires --flexible", file=sys.stderr)
            return 2
        for name in read_locales or ():
            canonical = icu.Locale(name).getName()
            if canonical not in known_locales:
                print(f"icukit compile: unknown locale {name!r} in --read-locales", file=sys.stderr)
                return 2
            for locale in locales:
                language = icu.Locale(locale).getLanguage()
                if icu.Locale(name).getLanguage() != language:
                    print(
                        f"icukit compile: --read-locales {name!r} is not a locale of "
                        f"the language of {locale!r} ({language!r})",
                        file=sys.stderr,
                    )
                    return 2
        currencies = []
        known_currencies = _iso_currency_codes()
        for code in args.currency:
            canonical = code.upper()
            if canonical not in known_currencies:
                print(f"icukit compile: unknown ISO 4217 currency {code!r}", file=sys.stderr)
                return 2
            currencies.append(canonical)
        units = []
        for unit in args.measure:
            try:
                canonical = icu.MeasureUnit.forIdentifier(unit).getIdentifier() if unit else ""
            except icu.ICUError:
                canonical = ""
            if not canonical:
                print(f"icukit compile: unknown ICU measure unit {unit!r}", file=sys.stderr)
                return 2
            units.append(canonical)
        materials = []
        for path in args.material:
            try:
                materials.append(load_locale_material(path))
            except MaterialLoadError as error:
                for refusal in error.refusals:
                    print(f"icukit compile: {refusal.code}: {refusal.detail}", file=sys.stderr)
                return 2
        if args.cache_dir:
            cache.configure(directory=args.cache_dir)
        rows = []
        for locale in locales:
            compiled = compile_detectors(
                ReaderSpec(
                    locale,
                    guarded=args.guarded,
                    flexible=args.flexible,
                    locales=read_locales,
                    currencies=tuple(currencies),
                    units=tuple(units),
                    skeletons=tuple(args.skeleton) or None,
                    material=tuple(materials),
                )
            )
            info = cache.cache_info()
            rows.append(
                {
                    "locale": locale,
                    "readers": len(compiled.detectors.detectors),
                    "build_s": compiled.stats.build_s,
                    "warm_s": compiled.stats.warm_s,
                    "tables_loaded": compiled.stats.tables_loaded,
                    "tables_computed": compiled.stats.tables_computed,
                    "lanes_gated": compiled.stats.lanes_gated,
                    "lanes_ungated": compiled.stats.lanes_ungated,
                    "tables_digest": compiled.key.tables,
                    "compile_digest": compiled.key.digest(),
                    "path": info["root"],
                }
            )
        print(format_json(rows) if args.json else format_tsv(rows))
        return 0
