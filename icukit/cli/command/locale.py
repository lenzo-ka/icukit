"""Locale CLI command."""

import argparse
import sys

from ...collator import compare_strings, sort_strings
from ...errors import CollatorError
from ...formatters import print_output
from ...locale import (
    COMPACT_LONG,
    COMPACT_SHORT,
    EXEMPLAR_STANDARD,
    LocaleError,
    add_likely_subtags,
    canonicalize_locale,
    format_compact,
    format_currency,
    format_number,
    format_ordinal,
    format_percent,
    format_spellout,
    get_display_name,
    get_exemplar_characters,
    get_exemplar_info,
    get_locale_attributes,
    get_locale_info,
    get_number_symbols,
    is_valid_locale,
    list_exemplar_types,
    list_languages,
    list_locales,
    list_locales_info,
    minimize_subtags,
    parse_locale,
)
from ..subcommand_base import SubcommandBase, handles_errors


class LocaleCommand(SubcommandBase):
    """Locale parsing and information command."""

    @classmethod
    def add_subparser(cls, subparsers):
        """Add the locale command with its subcommands."""
        parser = subparsers.add_parser(
            "locale",
            help="Parse and query locale identifiers",
            description="""
Parse, validate, and query locale identifiers (language + region + script).
Format numbers, currency, and percentages according to locale conventions.

Locale format: language[_Script][_REGION][@keywords]
  Examples: en, en_US, zh_Hans, zh_Hans_CN, sr_Latn_RS

Examples:
  # Get comprehensive locale attributes
  icukit locale attrs en_US
  icukit locale attrs de_DE --json

  # Format numbers
  icukit locale format 1234567.89 --locale de_DE
  icukit locale format 1234.56 --locale ja_JP --type currency
  icukit locale format 0.15 --locale fr_FR --type percent

  # Spell out numbers
  icukit locale spellout 42 --locale en_US
  icukit locale ordinal 1 --locale en_US

  # Compact numbers (1.2M, 3.5K)
  icukit locale compact 1234567
  icukit locale compact 1234567 --style LONG

  # Get display name
  icukit locale name ja_JP
  icukit locale name ja_JP --in ja

  # List locales/languages
  icukit locale list --short
  icukit locale languages

  # Parse and manipulate
  icukit locale parse sr_Latn_RS
  icukit locale expand zh
  icukit locale minimize zh_Hans_CN

  # Number formatting symbols
  icukit locale symbols --locale de_DE
  icukit locale symbols --locale ar_SA --json
""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cls.create_subcommand_parser(
            parser,
            {
                "attrs": {
                    "aliases": ["a", "attributes"],
                    "help": "Get comprehensive locale attributes",
                    "func": cls.cmd_attrs,
                    "configure": cls._configure_attrs,
                },
                "format": {
                    "aliases": ["f", "fmt"],
                    "help": "Format number/currency/percent",
                    "func": cls.cmd_format,
                    "configure": cls._configure_format,
                },
                "spellout": {
                    "aliases": ["spell", "words"],
                    "help": "Spell out a number in words",
                    "func": cls.cmd_spellout,
                    "configure": cls._configure_spellout,
                },
                "ordinal": {
                    "aliases": ["ord"],
                    "help": "Format number as ordinal",
                    "func": cls.cmd_ordinal,
                    "configure": cls._configure_ordinal,
                },
                "compact": {
                    "aliases": ["comp"],
                    "help": "Format number in compact form (1.2M)",
                    "func": cls.cmd_compact,
                    "configure": cls._configure_compact,
                },
                "name": {
                    "aliases": ["n", "display"],
                    "help": "Get display name for locale",
                    "func": cls.cmd_name,
                    "configure": cls._configure_name,
                },
                "list": {
                    "aliases": ["l", "ls"],
                    "help": "List locales, languages, or other locale data",
                    "func": cls.cmd_list,
                    "configure": cls._configure_list,
                },
                "info": {
                    "aliases": ["i"],
                    "help": "Get basic locale info",
                    "func": cls.cmd_info,
                    "configure": cls._configure_info,
                },
                "parse": {
                    "aliases": ["p"],
                    "help": "Parse locale into components",
                    "func": cls.cmd_parse,
                    "configure": cls._configure_parse,
                },
                "expand": {
                    "aliases": ["e", "likely"],
                    "help": "Add likely subtags to locale",
                    "func": cls.cmd_expand,
                    "configure": cls._configure_expand,
                },
                "minimize": {
                    "aliases": ["min", "m"],
                    "help": "Minimize locale subtags",
                    "func": cls.cmd_minimize,
                    "configure": cls._configure_minimize,
                },
                "validate": {
                    "aliases": ["v", "check"],
                    "help": "Validate a locale string",
                    "func": cls.cmd_validate,
                    "configure": cls._configure_validate,
                },
                "canonicalize": {
                    "aliases": ["canon", "c"],
                    "help": "Canonicalize locale identifier",
                    "func": cls.cmd_canonicalize,
                    "configure": cls._configure_canonicalize,
                },
                "sort": {
                    "aliases": ["s"],
                    "help": "Sort lines using locale-aware collation",
                    "func": cls.cmd_sort,
                    "configure": cls._configure_sort,
                },
                "compare": {
                    "aliases": ["cmp"],
                    "help": "Compare two strings",
                    "func": cls.cmd_compare,
                    "configure": cls._configure_compare,
                },
                "exemplars": {
                    "aliases": ["ex", "chars"],
                    "help": "Get exemplar characters for a locale",
                    "func": cls.cmd_exemplars,
                    "configure": cls._configure_exemplars,
                },
                "symbols": {
                    "aliases": ["sym", "numsym"],
                    "help": "Get number formatting symbols for a locale",
                    "func": cls.cmd_symbols,
                    "configure": cls._configure_symbols,
                },
            },
        )

        parser.set_defaults(func=cls.run, _subparser=parser)
        return parser

    @classmethod
    def _configure_attrs(cls, parser):
        """Configure attrs subcommand."""
        parser.add_argument("locale", help="Locale identifier (e.g., en_US)")
        parser.add_argument(
            "--display", "-d", default="en", help="Locale for display names (default: en)"
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_format(cls, parser):
        """Configure format subcommand."""
        parser.add_argument("value", type=float, help="Number to format")
        parser.add_argument(
            "--locale", "-l", default="en_US", help="Locale for formatting (default: en_US)"
        )
        parser.add_argument(
            "--type",
            "-t",
            choices=["number", "currency", "percent"],
            default="number",
            help="Format type (default: number)",
        )
        parser.add_argument(
            "--currency", "-c", help="Currency code for currency format (e.g., EUR)"
        )

    @classmethod
    def _configure_spellout(cls, parser):
        """Configure spellout subcommand."""
        parser.add_argument("value", type=int, help="Integer to spell out")
        parser.add_argument(
            "--locale", "-l", default="en_US", help="Locale for spelling (default: en_US)"
        )

    @classmethod
    def _configure_ordinal(cls, parser):
        """Configure ordinal subcommand."""
        parser.add_argument("value", type=int, help="Integer to format as ordinal")
        parser.add_argument(
            "--locale", "-l", default="en_US", help="Locale for formatting (default: en_US)"
        )

    @classmethod
    def _configure_compact(cls, parser):
        """Configure compact subcommand."""
        parser.add_argument("value", type=float, help="Number to format in compact form")
        parser.add_argument(
            "--locale", "-l", default="en_US", help="Locale for formatting (default: en_US)"
        )
        parser.add_argument(
            "--style",
            "-s",
            choices=[COMPACT_SHORT, COMPACT_LONG],
            default=COMPACT_SHORT,
            help="Format style (default: SHORT)",
        )

    @classmethod
    def _configure_list(cls, parser):
        """Configure list subcommand."""
        parser.add_argument(
            "type",
            nargs="?",
            choices=["locales", "languages"],
            default="locales",
            help="What to list (default: locales)",
        )
        parser.add_argument("-s", "--short", action="store_true", help="Show only IDs/codes")
        parser.add_argument(
            "--display", "-d", default="en", help="Locale for display names (default: en)"
        )
        # Filter options (for locales)
        filter_group = parser.add_argument_group("filters", "Filters for locale listing")
        filter_group.add_argument("--language", help="Filter by language code (e.g., en, es)")
        filter_group.add_argument("--region", help="Filter by region code (e.g., US, MX)")
        filter_group.add_argument("--script", help="Filter by script code (e.g., Latn, Hans)")
        cls._add_output_options(parser)

    @classmethod
    def _configure_info(cls, parser):
        """Configure info subcommand."""
        parser.add_argument(
            "locales", nargs="+", metavar="LOCALE", help="Locale identifier(s) (e.g., en_US)"
        )
        parser.add_argument(
            "--display", "-d", default="en", help="Locale for display names (default: en)"
        )
        parser.add_argument(
            "-x",
            "--extended",
            action="store_true",
            help="Include extended attributes (calendar, currency, RTL, etc.)",
        )
        cls._add_output_options(parser)

    @classmethod
    def _configure_parse(cls, parser):
        """Configure parse subcommand."""
        parser.add_argument("locale", help="Locale string to parse")
        cls._add_output_options(parser)

    @classmethod
    def _configure_expand(cls, parser):
        """Configure expand subcommand."""
        parser.add_argument("locale", help="Minimal locale to expand (e.g., zh, sr)")

    @classmethod
    def _configure_minimize(cls, parser):
        """Configure minimize subcommand."""
        parser.add_argument("locale", help="Full locale to minimize")

    @classmethod
    def _configure_name(cls, parser):
        """Configure name subcommand."""
        parser.add_argument("locale", help="Locale to get display name for")
        parser.add_argument(
            "--in",
            "-i",
            dest="display_locale",
            default="en",
            help="Locale for the display name (default: en)",
        )

    @classmethod
    def _configure_validate(cls, parser):
        """Configure validate subcommand."""
        parser.add_argument("locale", help="Locale string to validate")

    @classmethod
    def _configure_canonicalize(cls, parser):
        """Configure canonicalize subcommand."""
        parser.add_argument("locale", help="Locale string to canonicalize")

    @classmethod
    @handles_errors(LocaleError)
    def cmd_attrs(cls, args):
        """Get comprehensive locale attributes."""
        display_locale = getattr(args, "display", "en")
        attrs = get_locale_attributes(args.locale, display_locale)

        as_json, headers = cls._get_output_flags(args)

        print_output(
            [attrs],
            as_json=as_json,
            columns=[
                "id",
                "display_name",
                "currency",
                "currency_format_example",
                "measurement_system",
                "paper_size",
                "quote_start",
                "quote_end",
                "number_format_example",
            ],
            headers=headers,
        )
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_format(cls, args):
        """Format a number."""
        locale_str = getattr(args, "locale", "en_US")
        fmt_type = getattr(args, "type", "number")
        currency = getattr(args, "currency", None)

        if fmt_type == "number":
            result = format_number(args.value, locale_str)
        elif fmt_type == "currency":
            result = format_currency(args.value, locale_str, currency)
        elif fmt_type == "percent":
            result = format_percent(args.value, locale_str)
        else:
            result = format_number(args.value, locale_str)

        print(result)
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_spellout(cls, args):
        """Spell out a number in words."""
        locale_str = getattr(args, "locale", "en_US")
        result = format_spellout(args.value, locale_str)
        print(result)
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_ordinal(cls, args):
        """Format a number as ordinal."""
        locale_str = getattr(args, "locale", "en_US")
        result = format_ordinal(args.value, locale_str)
        print(result)
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_compact(cls, args):
        """Format a number in compact form."""
        locale_str = getattr(args, "locale", "en_US")
        style = getattr(args, "style", COMPACT_SHORT)
        result = format_compact(args.value, locale_str, style)
        print(result)
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_list(cls, args):
        """List locales or languages."""
        list_type = getattr(args, "type", "locales")
        as_json, headers = cls._get_output_flags(args)
        short = getattr(args, "short", False)

        if list_type == "languages":
            return cls._run_list(
                args,
                list_languages,
                list_languages,  # Just IDs
                as_json=as_json,
                short=True,
            )

        # Default: list locales
        display_locale = getattr(args, "display", "en")
        filter_lang = getattr(args, "language", None)
        filter_region = getattr(args, "region", None)
        filter_script = getattr(args, "script", None)

        def get_filtered_info():
            data = list_locales_info(display_locale)
            return cls._apply_filters(data, filter_lang, filter_region, filter_script)

        def get_filtered_list():
            if filter_lang or filter_region or filter_script:
                return [loc["id"] for loc in get_filtered_info()]
            return list_locales()

        return cls._run_list(
            args,
            get_filtered_list,
            get_filtered_info,
            columns=["id", "language", "script", "region", "display_name"],
            headers=headers,
            as_json=as_json,
            short=short,
        )

    @classmethod
    def _apply_filters(cls, data, language=None, region=None, script=None):
        """Apply filters to locale data."""
        if language:
            data = [loc for loc in data if loc.get("language") == language]
        if region:
            data = [loc for loc in data if loc.get("region") == region]
        if script:
            data = [loc for loc in data if loc.get("script") == script]
        return data

    # Column definitions for reuse
    INFO_COLUMNS = [
        "id",
        "language",
        "script",
        "region",
        "scripts",
        "display_name",
    ]
    EXTENDED_COLUMNS = [
        "rtl",
        "calendar",
        "first_day_of_week",
        "currency",
        "measurement_system",
    ]

    @classmethod
    @handles_errors(LocaleError)
    def cmd_info(cls, args):
        """Get locale information."""
        display_locale = getattr(args, "display", "en")
        extended = getattr(args, "extended", False)
        infos = [get_locale_info(loc, display_locale, extended=extended) for loc in args.locales]

        as_json, headers = cls._get_output_flags(args)

        print_output(
            infos,
            as_json=as_json,
            columns=cls.INFO_COLUMNS,
            headers=headers,
            extended_columns=cls.EXTENDED_COLUMNS if extended else None,
        )
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_parse(cls, args):
        """Parse locale into components."""
        parsed = parse_locale(args.locale)

        as_json, headers = cls._get_output_flags(args)

        print_output(
            [parsed],
            as_json=as_json,
            columns=["id", "language", "script", "region", "variant"],
            headers=headers,
        )
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_expand(cls, args):
        """Add likely subtags."""
        expanded = add_likely_subtags(args.locale)
        print(expanded)
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_minimize(cls, args):
        """Minimize locale subtags."""
        minimized = minimize_subtags(args.locale)
        print(minimized)
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_name(cls, args):
        """Get display name."""
        display_locale = getattr(args, "display_locale", "en")
        name = get_display_name(args.locale, display_locale)
        print(name)
        return 0

    @classmethod
    @handles_errors(LocaleError)
    def cmd_validate(cls, args):
        """Validate a locale string."""
        valid = is_valid_locale(args.locale)
        if valid:
            print(f"{args.locale}: valid")
            return 0
        else:
            print(f"{args.locale}: invalid", file=sys.stderr)
            return 1

    @classmethod
    @handles_errors(LocaleError)
    def cmd_canonicalize(cls, args):
        """Canonicalize locale identifier."""
        canonical = canonicalize_locale(args.locale)
        print(canonical)
        return 0

    # -------------------------------------------------------------------------
    # Sort/Compare subcommands (locale-aware collation)
    # -------------------------------------------------------------------------

    @classmethod
    def _configure_sort(cls, parser):
        """Configure sort subcommand."""
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for sorting rules (default: en_US)",
        )
        parser.add_argument(
            "--reverse",
            "-r",
            action="store_true",
            help="Sort in descending order",
        )
        parser.add_argument(
            "--unique",
            "-u",
            action="store_true",
            help="Remove duplicate lines",
        )
        parser.add_argument(
            "--strength",
            "-s",
            choices=["primary", "secondary", "tertiary", "quaternary", "identical"],
            help="Collation strength (default: tertiary)",
        )
        parser.add_argument(
            "--case-first",
            choices=["upper", "lower"],
            help="Sort uppercase or lowercase first",
        )
        cls._add_input_options(parser)

    @classmethod
    def _configure_compare(cls, parser):
        """Configure compare subcommand."""
        parser.add_argument("string_a", help="First string")
        parser.add_argument("string_b", help="Second string")
        parser.add_argument(
            "--locale",
            "-l",
            default="en_US",
            help="Locale for comparison (default: en_US)",
        )
        parser.add_argument(
            "--strength",
            "-s",
            choices=["primary", "secondary", "tertiary", "quaternary", "identical"],
            help="Collation strength",
        )

    @classmethod
    @handles_errors(CollatorError)
    def cmd_sort(cls, args):
        """Sort lines using locale-aware collation."""
        lines = cls._read_lines(args)
        if not lines:
            return 0

        if args.unique:
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            lines = unique_lines

        sorted_lines = sort_strings(
            lines,
            args.locale,
            reverse=args.reverse,
            strength=args.strength,
            case_first=getattr(args, "case_first", None),
        )

        for line in sorted_lines:
            print(line)
        return 0

    @classmethod
    @handles_errors(CollatorError)
    def cmd_compare(cls, args):
        """Compare two strings."""
        result = compare_strings(
            args.string_a,
            args.string_b,
            args.locale,
            strength=args.strength,
        )

        if result < 0:
            print(f'"{args.string_a}" < "{args.string_b}"')
            return 1
        elif result > 0:
            print(f'"{args.string_a}" > "{args.string_b}"')
            return 2
        else:
            print(f'"{args.string_a}" = "{args.string_b}"')
            return 0

    @classmethod
    def _configure_exemplars(cls, parser):
        """Configure exemplars subcommand."""
        parser.add_argument(
            "locale",
            nargs="?",
            default="en_US",
            help="Locale code (default: en_US)",
        )
        parser.add_argument(
            "--type",
            "-t",
            choices=list_exemplar_types(),
            default=EXEMPLAR_STANDARD,
            help="Exemplar type: standard, auxiliary, index, punctuation (default: standard)",
        )
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            help="Show all exemplar types",
        )
        cls._add_output_options(parser)

    @classmethod
    @handles_errors(LocaleError)
    def cmd_exemplars(cls, args):
        """Get exemplar characters for a locale."""
        as_json, headers = cls._get_output_flags(args)

        if args.all:
            info = get_exemplar_info(args.locale)
            rows = [{"type": k, "characters": v} for k, v in info.items() if v]
            print_output(
                rows,
                columns=["type", "characters"],
                as_json=as_json,
                headers=headers,
            )
        else:
            result = get_exemplar_characters(args.locale, args.type)
            print(result)
        return 0

    # -------------------------------------------------------------------------
    # Number Symbols Subcommand
    # -------------------------------------------------------------------------

    @classmethod
    def _configure_symbols(cls, parser):
        """Configure symbols subcommand."""
        parser.add_argument(
            "locale",
            nargs="?",
            default="en_US",
            help="Locale code (default: en_US)",
        )
        cls._add_output_options(parser)

    @classmethod
    @handles_errors(LocaleError)
    def cmd_symbols(cls, args):
        """Get number formatting symbols for a locale."""
        symbols = get_number_symbols(args.locale)

        as_json, headers = cls._get_output_flags(args)

        if as_json:
            print_output(symbols, as_json=True)
        else:
            rows = [
                {"symbol": "decimal", "value": symbols["decimal"]},
                {"symbol": "grouping", "value": symbols["grouping"]},
                {"symbol": "percent", "value": symbols["percent"]},
                {"symbol": "per_mille", "value": symbols["per_mille"]},
                {"symbol": "plus", "value": symbols["plus"]},
                {"symbol": "minus", "value": symbols["minus"]},
                {"symbol": "exponential", "value": symbols["exponential"]},
                {"symbol": "infinity", "value": symbols["infinity"]},
                {"symbol": "nan", "value": symbols["nan"]},
                {"symbol": "currency", "value": symbols["currency"]},
            ]
            print_output(
                rows,
                as_json=False,
                columns=["symbol", "value"],
                headers=headers,
            )
        return 0
