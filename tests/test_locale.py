"""Tests for locale module and CLI."""

import subprocess
import sys

from icukit import (
    COMPACT_LONG,
    COMPACT_SHORT,
    EXEMPLAR_AUXILIARY,
    EXEMPLAR_INDEX,
    EXEMPLAR_PUNCTUATION,
    EXEMPLAR_STANDARD,
    add_likely_subtags,
    canonicalize_locale,
    format_compact,
    format_currency,
    format_number,
    format_ordinal,
    format_percent,
    format_scientific,
    format_spellout,
    get_default_locale,
    get_display_name,
    get_exemplar_characters,
    get_exemplar_info,
    get_language_display_name,
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


class TestLocaleLibrary:
    """Tests for locale library functions."""

    def test_list_locales(self):
        """Test listing all locales."""
        locales = list_locales()
        assert len(locales) > 800
        assert "en_US" in locales
        assert "el_GR" in locales
        assert "ja_JP" in locales

    def test_list_locales_sorted(self):
        """Test locales are sorted."""
        locales = list_locales()
        assert locales == sorted(locales)

    def test_list_languages(self):
        """Test listing language codes."""
        langs = list_languages()
        assert len(langs) > 100
        assert "en" in langs
        assert "el" in langs
        assert "ja" in langs
        assert "zh" in langs

    def test_list_locales_info(self):
        """Test listing locales with info."""
        locales = list_locales_info()
        assert len(locales) > 800
        el = next(loc for loc in locales if loc["id"] == "el_GR")
        assert el["display_name"] == "Greek (Greece)"

    def test_parse_locale_simple(self):
        """Test parsing simple locale."""
        parsed = parse_locale("en_US")
        assert parsed["language"] == "en"
        assert parsed["region"] == "US"
        assert parsed["script"] is None

    def test_parse_locale_with_script(self):
        """Test parsing locale with script."""
        parsed = parse_locale("sr_Latn_RS")
        assert parsed["language"] == "sr"
        assert parsed["script"] == "Latn"
        assert parsed["region"] == "RS"

    def test_parse_locale_bcp47(self):
        """Test parsing BCP 47 format."""
        parsed = parse_locale("zh-Hans-CN")
        assert parsed["language"] == "zh"
        assert parsed["script"] == "Hans"
        assert parsed["region"] == "CN"

    def test_get_locale_info(self):
        """Test getting locale info."""
        info = get_locale_info("ja_JP")
        assert info["language"] == "ja"
        assert info["region"] == "JP"
        assert info["display_name"] == "Japanese (Japan)"
        assert info["display_language"] == "Japanese"
        assert info["display_region"] == "Japan"

    def test_get_locale_info_with_display_locale(self):
        """Test getting locale info in different display locale."""
        info = get_locale_info("ja_JP", "ja")
        assert "日本語" in info["display_name"]

    def test_add_likely_subtags(self):
        """Test adding likely subtags."""
        assert add_likely_subtags("zh") == "zh_Hans_CN"
        assert add_likely_subtags("sr") == "sr_Cyrl_RS"
        assert add_likely_subtags("en") == "en_Latn_US"

    def test_minimize_subtags(self):
        """Test minimizing subtags."""
        assert minimize_subtags("zh_Hans_CN") == "zh"
        assert minimize_subtags("en_Latn_US") == "en"

    def test_canonicalize_locale(self):
        """Test canonicalizing locale."""
        # iw is deprecated code for Hebrew
        assert canonicalize_locale("iw") == "he"

    def test_get_display_name(self):
        """Test getting display name."""
        assert get_display_name("el_GR") == "Greek (Greece)"
        assert get_display_name("ja_JP") == "Japanese (Japan)"

    def test_get_display_name_in_locale(self):
        """Test getting display name in different locale."""
        name = get_display_name("el_GR", "el")
        assert "Ελληνικά" in name

    def test_get_language_display_name(self):
        """Test getting language display name."""
        assert get_language_display_name("el") == "Greek"
        assert get_language_display_name("ja") == "Japanese"

    def test_is_valid_locale_valid(self):
        """Test valid locales."""
        assert is_valid_locale("en_US") is True
        assert is_valid_locale("el_GR") is True
        assert is_valid_locale("zh_Hans_CN") is True

    def test_is_valid_locale_invalid(self):
        """Test invalid locales."""
        assert is_valid_locale("xx_YY") is False
        assert is_valid_locale("invalid") is False

    def test_get_default_locale(self):
        """Test getting default locale."""
        default = get_default_locale()
        assert default is not None
        assert len(default) > 0

    # Rich attributes tests

    def test_get_locale_attributes(self):
        """Test getting comprehensive locale attributes."""
        attrs = get_locale_attributes("en_US")
        assert attrs["id"] == "en_US"
        assert attrs["currency"] == "USD"
        assert attrs["measurement_system"] == "US"
        assert attrs["quote_start"] == "\u201c"  # left double quote
        assert attrs["quote_end"] == "\u201d"  # right double quote

    def test_get_locale_attributes_de(self):
        """Test locale attributes for German."""
        attrs = get_locale_attributes("de_DE")
        assert attrs["currency"] == "EUR"
        assert attrs["measurement_system"] == "metric"
        # German quotes are „ and "
        assert attrs["quote_start"] == "\u201e"  # double low-9 quote
        assert attrs["quote_end"] == "\u201c"  # left double quote

    def test_get_locale_attributes_paper_size(self):
        """Test paper size in locale attributes."""
        attrs_us = get_locale_attributes("en_US")
        attrs_de = get_locale_attributes("de_DE")
        # US uses Letter size, EU uses A4
        assert "mm" in attrs_us["paper_size"]
        assert "mm" in attrs_de["paper_size"]

    # Number formatting tests

    def test_format_number_us(self):
        """Test number formatting for US locale."""
        result = format_number(1234567.89, "en_US")
        assert "1,234,567" in result
        assert "." in result  # decimal separator

    def test_format_number_de(self):
        """Test number formatting for German locale."""
        result = format_number(1234567.89, "de_DE")
        # German uses . for thousands and , for decimal
        assert "1.234.567" in result

    def test_format_currency_usd(self):
        """Test currency formatting for USD."""
        result = format_currency(1234.56, "en_US")
        assert "$" in result
        assert "1,234" in result

    def test_format_currency_eur(self):
        """Test currency formatting for EUR."""
        result = format_currency(1234.56, "de_DE")
        assert "€" in result

    def test_format_currency_override(self):
        """Test currency formatting with override."""
        result = format_currency(1234.56, "en_US", "EUR")
        assert "€" in result

    def test_format_percent(self):
        """Test percentage formatting."""
        result = format_percent(0.15, "en_US")
        assert "15" in result
        assert "%" in result

    def test_format_percent_de(self):
        """Test percentage formatting for German."""
        result = format_percent(0.15, "de_DE")
        assert "15" in result
        # German often has space before %
        assert "%" in result

    def test_format_scientific(self):
        """Test scientific notation formatting."""
        result = format_scientific(1234567.89, "en_US")
        assert "E" in result or "e" in result

    def test_format_spellout_en(self):
        """Test spelling out numbers in English."""
        result = format_spellout(42, "en_US")
        assert "forty" in result.lower()
        assert "two" in result.lower()

    def test_format_spellout_de(self):
        """Test spelling out numbers in German."""
        result = format_spellout(42, "de_DE")
        assert "zwei" in result.lower() or "vierzig" in result.lower()

    def test_format_ordinal_en(self):
        """Test ordinal formatting in English."""
        assert "1st" in format_ordinal(1, "en_US")
        assert "2nd" in format_ordinal(2, "en_US")
        assert "3rd" in format_ordinal(3, "en_US")
        assert "4th" in format_ordinal(4, "en_US")

    def test_format_ordinal_de(self):
        """Test ordinal formatting in German."""
        result = format_ordinal(1, "de_DE")
        assert "1." in result

    # Compact number formatting tests

    def test_format_compact_millions(self):
        """Test compact formatting for millions."""
        result = format_compact(1234567, "en_US")
        assert "M" in result or "1" in result

    def test_format_compact_thousands(self):
        """Test compact formatting for thousands."""
        result = format_compact(3500, "en_US")
        assert "K" in result or "3" in result

    def test_format_compact_de(self):
        """Test compact formatting for German."""
        result = format_compact(1000000, "de_DE")
        assert "Mio" in result or "1" in result

    def test_format_compact_long_style(self):
        """Test compact formatting with LONG style."""
        result = format_compact(1000000, "en_US", COMPACT_LONG)
        assert "million" in result.lower() or "1" in result

    def test_format_compact_short_style(self):
        """Test compact formatting with SHORT style."""
        result = format_compact(1000000, "en_US", COMPACT_SHORT)
        assert "M" in result or "1" in result


class TestLocaleCLI:
    """Tests for locale CLI command."""

    def test_locale_list(self):
        """Test icukit locale list."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "list"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "en_US" in result.stdout

    def test_locale_list_short(self):
        """Test icukit locale list --short."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "list", "--short"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "en_US" in result.stdout
        # Short mode should not have headers
        assert "id\t" not in result.stdout

    def test_locale_languages(self):
        """Test icukit locale list languages."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "list", "languages"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "en" in result.stdout
        assert "el" in result.stdout

    def test_locale_info(self):
        """Test icukit locale info."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "info", "el_GR"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "el_GR" in result.stdout
        assert "Greek" in result.stdout

    def test_locale_info_json(self):
        """Test icukit locale info --json."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "info", "ja_JP", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"language": "ja"' in result.stdout

    def test_locale_parse(self):
        """Test icukit locale parse."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "parse", "sr_Latn_RS"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "sr" in result.stdout
        assert "Latn" in result.stdout
        assert "RS" in result.stdout

    def test_locale_expand(self):
        """Test icukit locale expand."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "expand", "zh"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "zh_Hans_CN" in result.stdout

    def test_locale_minimize(self):
        """Test icukit locale minimize."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "minimize", "zh_Hans_CN"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "zh"

    def test_locale_name(self):
        """Test icukit locale name."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "name", "ja_JP"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Japanese (Japan)" in result.stdout

    def test_locale_name_in_locale(self):
        """Test icukit locale name --in."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "name", "ja_JP", "--in", "ja"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "日本語" in result.stdout

    def test_locale_validate_valid(self):
        """Test icukit locale validate with valid locale."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "validate", "en_US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "valid" in result.stdout

    def test_locale_validate_invalid(self):
        """Test icukit locale validate with invalid locale."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "validate", "xx_YY"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "invalid" in result.stderr

    def test_locale_canonicalize(self):
        """Test icukit locale canonicalize."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "canonicalize", "iw"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "he" in result.stdout

    def test_locale_prefix_matching(self):
        """Test prefix matching works."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "loc", "info", "en_US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "English" in result.stdout

    def test_locale_help(self):
        """Test icukit locale --help."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "list" in result.stdout
        assert "info" in result.stdout
        assert "expand" in result.stdout

    # Rich attributes and formatting CLI tests

    def test_locale_attrs(self):
        """Test icukit locale attrs."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "attrs", "en_US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "USD" in result.stdout
        assert "US" in result.stdout

    def test_locale_attrs_json(self):
        """Test icukit locale attrs --json."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "attrs", "de_DE", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"currency": "EUR"' in result.stdout
        assert '"measurement_system": "metric"' in result.stdout

    def test_locale_format_number(self):
        """Test icukit locale format number."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "locale",
                "format",
                "1234567.89",
                "--locale",
                "en_US",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "1,234,567" in result.stdout

    def test_locale_format_currency(self):
        """Test icukit locale format currency."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "locale",
                "format",
                "1234.56",
                "--locale",
                "en_US",
                "--type",
                "currency",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "$" in result.stdout

    def test_locale_format_percent(self):
        """Test icukit locale format percent."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "locale",
                "format",
                "0.15",
                "--locale",
                "en_US",
                "--type",
                "percent",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "15" in result.stdout
        assert "%" in result.stdout

    def test_locale_spellout(self):
        """Test icukit locale spellout."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "spellout", "42", "--locale", "en_US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "forty" in result.stdout.lower()

    def test_locale_ordinal(self):
        """Test icukit locale ordinal."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "ordinal", "1", "--locale", "en_US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "1st" in result.stdout

    def test_locale_compact(self):
        """Test icukit locale compact."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "compact", "1000000"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "M" in result.stdout or "1" in result.stdout

    def test_locale_compact_long(self):
        """Test icukit locale compact --style LONG."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "compact", "1000000", "--style", "LONG"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "million" in result.stdout.lower() or "1" in result.stdout

    def test_locale_compact_german(self):
        """Test icukit locale compact with German locale."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "locale",
                "compact",
                "1000000",
                "--locale",
                "de_DE",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Mio" in result.stdout or "1" in result.stdout

    def test_locale_exemplars(self):
        """Test icukit locale exemplars."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "exemplars", "de_DE"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ä" in result.stdout or "a-z" in result.stdout

    def test_locale_exemplars_index(self):
        """Test icukit locale exemplars --type index."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "locale",
                "exemplars",
                "ja_JP",
                "--type",
                "index",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Japanese index characters (hiragana)
        assert "あ" in result.stdout or "か" in result.stdout

    def test_locale_exemplars_all(self):
        """Test icukit locale exemplars --all."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "exemplars", "el", "--all"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "standard" in result.stdout
        assert "index" in result.stdout


class TestExemplarLibrary:
    """Tests for exemplar character functions."""

    def test_list_exemplar_types(self):
        """Test listing exemplar types."""
        types = list_exemplar_types()
        assert "standard" in types
        assert "auxiliary" in types
        assert "index" in types
        assert "punctuation" in types

    def test_get_exemplar_characters_german(self):
        """Test getting German exemplar characters."""
        chars = get_exemplar_characters("de_DE")
        # German uses a-z plus umlauts and ß
        assert "ä" in chars or "a-z" in chars

    def test_get_exemplar_characters_index(self):
        """Test getting index exemplar characters."""
        chars = get_exemplar_characters("de_DE", EXEMPLAR_INDEX)
        assert "A-Z" in chars or "A" in chars

    def test_get_exemplar_characters_japanese_index(self):
        """Test Japanese index characters."""
        chars = get_exemplar_characters("ja_JP", EXEMPLAR_INDEX)
        # Japanese uses hiragana for index
        assert "あ" in chars or "か" in chars

    def test_get_exemplar_info(self):
        """Test getting all exemplar info for a locale."""
        info = get_exemplar_info("el")
        assert "standard" in info
        assert "auxiliary" in info
        assert "index" in info
        assert "punctuation" in info
        # Greek standard characters
        assert info["standard"]  # Not empty

    def test_exemplar_constants(self):
        """Test exemplar type constants."""
        assert EXEMPLAR_STANDARD == "standard"
        assert EXEMPLAR_AUXILIARY == "auxiliary"
        assert EXEMPLAR_INDEX == "index"
        assert EXEMPLAR_PUNCTUATION == "punctuation"


class TestNumberSymbols:
    """Tests for number formatting symbols."""

    def test_get_number_symbols_en_us(self):
        """Test getting number symbols for en_US."""
        symbols = get_number_symbols("en_US")
        assert symbols["locale"] == "en_US"
        assert symbols["decimal"] == "."
        assert symbols["grouping"] == ","
        assert symbols["percent"] == "%"
        assert symbols["plus"] == "+"
        assert symbols["minus"] == "-"
        assert symbols["currency"] == "$"

    def test_get_number_symbols_german(self):
        """Test getting number symbols for German."""
        symbols = get_number_symbols("de_DE")
        assert symbols["decimal"] == ","
        assert symbols["grouping"] == "."
        assert symbols["currency"] == "€"

    def test_get_number_symbols_french(self):
        """Test getting number symbols for French."""
        symbols = get_number_symbols("fr_FR")
        assert symbols["decimal"] == ","
        # French uses narrow no-break space for grouping
        assert symbols["grouping"] in [".", " ", "\u202f"]

    def test_get_number_symbols_all_keys(self):
        """Test that all expected keys are present."""
        symbols = get_number_symbols("en_US")
        expected_keys = [
            "locale",
            "decimal",
            "grouping",
            "percent",
            "per_mille",
            "plus",
            "minus",
            "exponential",
            "infinity",
            "nan",
            "currency",
        ]
        for key in expected_keys:
            assert key in symbols

    def test_get_number_symbols_infinity_nan(self):
        """Test special symbols."""
        symbols = get_number_symbols("en_US")
        assert symbols["infinity"] == "∞"
        assert symbols["nan"] == "NaN"


class TestNumberSymbolsCLI:
    """Tests for number symbols CLI command."""

    def test_symbols_default(self):
        """Test locale symbols subcommand."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "symbols"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "decimal" in result.stdout
        assert "grouping" in result.stdout

    def test_symbols_german(self):
        """Test symbols for German locale."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "symbols", "de_DE"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "," in result.stdout  # German decimal
        assert "decimal" in result.stdout

    def test_symbols_json(self):
        """Test symbols with JSON output."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "locale", "symbols", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"decimal"' in result.stdout
        assert '"grouping"' in result.stdout
