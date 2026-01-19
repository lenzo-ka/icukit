"""Tests for the displayname module."""

import subprocess
import sys

from icukit import (
    DisplayNames,
    get_currency_name,
    get_currency_symbol,
    get_language_name,
    get_locale_name,
    get_region_name,
    get_script_name,
)


def run_cli(*args, input_text=None):
    """Run icukit CLI and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "icukit.cli"] + list(args)
    result = subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


class TestGetLanguageName:
    """Tests for get_language_name function."""

    def test_english(self):
        """Test English language name."""
        result = get_language_name("en", "en_US")
        assert result.lower() == "english"

    def test_chinese_in_english(self):
        """Test Chinese in English."""
        result = get_language_name("zh", "en_US")
        assert "chinese" in result.lower()

    def test_chinese_in_german(self):
        """Test Chinese in German."""
        result = get_language_name("zh", "de")
        assert "chinesisch" in result.lower()

    def test_chinese_in_japanese(self):
        """Test Chinese in Japanese."""
        result = get_language_name("zh", "ja")
        # Should contain Chinese characters
        assert result  # Non-empty

    def test_arabic(self):
        """Test Arabic language name."""
        result = get_language_name("ar", "en_US")
        assert "arabic" in result.lower()


class TestGetScriptName:
    """Tests for get_script_name function."""

    def test_latin(self):
        """Test Latin script."""
        result = get_script_name("Latn", "en_US")
        assert "latin" in result.lower()

    def test_cyrillic(self):
        """Test Cyrillic script."""
        result = get_script_name("Cyrl", "en_US")
        assert "cyrillic" in result.lower()

    def test_simplified_chinese(self):
        """Test Simplified Chinese script."""
        result = get_script_name("Hans", "en_US")
        assert "simplified" in result.lower() or "han" in result.lower()

    def test_arabic_script(self):
        """Test Arabic script."""
        result = get_script_name("Arab", "en_US")
        assert "arabic" in result.lower()


class TestGetRegionName:
    """Tests for get_region_name function."""

    def test_us(self):
        """Test United States."""
        result = get_region_name("US", "en_US")
        assert "united states" in result.lower()

    def test_japan(self):
        """Test Japan."""
        result = get_region_name("JP", "en_US")
        assert "japan" in result.lower()

    def test_japan_in_japanese(self):
        """Test Japan in Japanese."""
        result = get_region_name("JP", "ja")
        assert "日本" in result

    def test_germany(self):
        """Test Germany."""
        result = get_region_name("DE", "en_US")
        assert "germany" in result.lower()


class TestGetCurrencyName:
    """Tests for get_currency_name function."""

    def test_usd(self):
        """Test US Dollar."""
        result = get_currency_name("USD", "en_US")
        # May be "US Dollar", "US Dollars", or similar
        assert "dollar" in result.lower() or "USD" in result

    def test_euro(self):
        """Test Euro."""
        result = get_currency_name("EUR", "en_US")
        assert "euro" in result.lower() or "EUR" in result

    def test_yen(self):
        """Test Japanese Yen."""
        result = get_currency_name("JPY", "en_US")
        assert "yen" in result.lower() or "JPY" in result


class TestGetCurrencySymbol:
    """Tests for get_currency_symbol function."""

    def test_usd(self):
        """Test USD symbol."""
        result = get_currency_symbol("USD", "en_US")
        assert result == "$"

    def test_euro(self):
        """Test Euro symbol."""
        result = get_currency_symbol("EUR", "en_US")
        assert result == "€"

    def test_pound(self):
        """Test British Pound symbol."""
        result = get_currency_symbol("GBP", "en_US")
        assert result == "£"

    def test_yen(self):
        """Test Yen symbol."""
        result = get_currency_symbol("JPY", "en_US")
        assert result in ["¥", "JP¥"]


class TestGetLocaleName:
    """Tests for get_locale_name function."""

    def test_en_us(self):
        """Test en_US locale."""
        result = get_locale_name("en_US", "en_US")
        assert "english" in result.lower()
        assert "united states" in result.lower() or "us" in result.lower()

    def test_zh_hans_cn(self):
        """Test zh_Hans_CN locale."""
        result = get_locale_name("zh_Hans_CN", "en_US")
        assert "chinese" in result.lower()
        assert "simplified" in result.lower() or "china" in result.lower()

    def test_de_de(self):
        """Test de_DE locale."""
        result = get_locale_name("de_DE", "en_US")
        assert "german" in result.lower()


class TestDisplayNames:
    """Tests for DisplayNames class."""

    def test_init(self):
        """Test initialization."""
        names = DisplayNames("en_US")
        assert names.display_locale == "en_US"

    def test_language(self):
        """Test language method."""
        names = DisplayNames("en_US")
        assert "chinese" in names.language("zh").lower()

    def test_script(self):
        """Test script method."""
        names = DisplayNames("en_US")
        assert "cyrillic" in names.script("Cyrl").lower()

    def test_region(self):
        """Test region method."""
        names = DisplayNames("en_US")
        assert "japan" in names.region("JP").lower()

    def test_currency(self):
        """Test currency method."""
        names = DisplayNames("en_US")
        result = names.currency("USD")
        assert "dollar" in result.lower() or "USD" in result

    def test_currency_symbol(self):
        """Test currency_symbol method."""
        names = DisplayNames("en_US")
        assert names.currency_symbol("USD") == "$"

    def test_locale(self):
        """Test locale method."""
        names = DisplayNames("en_US")
        result = names.locale("de_DE")
        assert "german" in result.lower()

    def test_repr(self):
        """Test string representation."""
        names = DisplayNames("de_DE")
        assert "de_DE" in repr(names)


class TestDisplayNameCLI:
    """Tests for displayname CLI command."""

    def test_language(self):
        """Test language subcommand."""
        code, out, err = run_cli("displayname", "language", "zh")
        assert code == 0
        assert "Chinese" in out

    def test_language_display_locale(self):
        """Test language with display locale."""
        code, out, err = run_cli("displayname", "language", "zh", "--display", "de")
        assert code == 0
        assert "Chinesisch" in out

    def test_script(self):
        """Test script subcommand."""
        code, out, err = run_cli("displayname", "script", "Cyrl")
        assert code == 0
        assert "Cyrillic" in out

    def test_region(self):
        """Test region subcommand."""
        code, out, err = run_cli("displayname", "region", "JP")
        assert code == 0
        assert "Japan" in out

    def test_region_display_locale(self):
        """Test region with display locale."""
        code, out, err = run_cli("displayname", "region", "JP", "--display", "ja")
        assert code == 0
        assert "日本" in out

    def test_currency(self):
        """Test currency subcommand."""
        code, out, err = run_cli("displayname", "currency", "USD")
        assert code == 0
        assert "Dollar" in out or "USD" in out

    def test_symbol(self):
        """Test symbol subcommand."""
        code, out, err = run_cli("displayname", "symbol", "USD")
        assert code == 0
        assert "$" in out

    def test_symbol_euro(self):
        """Test symbol for Euro."""
        code, out, err = run_cli("displayname", "symbol", "EUR")
        assert code == 0
        assert "€" in out

    def test_locale(self):
        """Test locale subcommand."""
        code, out, err = run_cli("displayname", "locale", "zh_Hans_CN")
        assert code == 0
        assert "Chinese" in out

    def test_alias_dn(self):
        """Test dn alias."""
        code, out, err = run_cli("dn", "language", "en")
        assert code == 0
        assert "English" in out

    def test_alias_name(self):
        """Test name alias."""
        code, out, err = run_cli("name", "region", "US")
        assert code == 0
        assert "United States" in out

    def test_help(self):
        """Test help output."""
        code, out, err = run_cli("displayname", "--help")
        assert code == 0
        assert "language" in out
        assert "script" in out
        assert "region" in out
        assert "currency" in out
        assert "symbol" in out
        assert "locale" in out

    def test_country_alias(self):
        """Test country alias for region."""
        code, out, err = run_cli("displayname", "country", "DE")
        assert code == 0
        assert "Germany" in out
