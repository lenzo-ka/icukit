"""Tests for script detection and properties."""

import pytest

from icukit import (
    detect_script,
    detect_scripts,
    get_char_script,
    get_script_info,
    is_cased,
    is_rtl,
    list_scripts,
    list_scripts_info,
)


class TestDetectScript:
    """Tests for detect_script function."""

    def test_latin(self):
        assert detect_script("Hello") == "Latin"

    def test_greek(self):
        assert detect_script("Ελληνικά") == "Greek"

    def test_han(self):
        assert detect_script("你好") == "Han"

    def test_arabic(self):
        assert detect_script("مرحبا") == "Arabic"

    def test_cyrillic(self):
        assert detect_script("Привет") == "Cyrillic"

    def test_empty(self):
        assert detect_script("") == "Unknown"


class TestDetectScripts:
    """Tests for detect_scripts function."""

    def test_single_script(self):
        scripts = detect_scripts("Hello")
        assert "Latin" in scripts

    def test_mixed_scripts(self):
        scripts = detect_scripts("Hello Ελληνικά")
        assert "Latin" in scripts
        assert "Greek" in scripts

    def test_with_common(self):
        # Spaces and numbers are "Common" script
        scripts = detect_scripts("abc 123")
        assert "Latin" in scripts
        assert "Common" in scripts

    def test_empty(self):
        assert detect_scripts("") == []


class TestGetCharScript:
    """Tests for get_char_script function."""

    def test_latin(self):
        assert get_char_script("A") == "Latin"

    def test_greek(self):
        assert get_char_script("α") == "Greek"

    def test_han(self):
        assert get_char_script("你") == "Han"

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            get_char_script("AB")

    def test_empty_input(self):
        with pytest.raises(ValueError):
            get_char_script("")


class TestIsCased:
    """Tests for is_cased function."""

    def test_latin_is_cased(self):
        assert is_cased("Latin") is True

    def test_greek_is_cased(self):
        assert is_cased("Greek") is True

    def test_cyrillic_is_cased(self):
        assert is_cased("Cyrillic") is True

    def test_han_not_cased(self):
        assert is_cased("Han") is False

    def test_arabic_not_cased(self):
        assert is_cased("Arabic") is False


class TestIsRtl:
    """Tests for is_rtl function."""

    def test_arabic_is_rtl(self):
        assert is_rtl("مرحبا") is True

    def test_hebrew_is_rtl(self):
        assert is_rtl("שלום") is True

    def test_latin_not_rtl(self):
        assert is_rtl("Hello") is False

    def test_greek_not_rtl(self):
        assert is_rtl("Ελληνικά") is False

    def test_empty(self):
        assert is_rtl("") is False


class TestListScripts:
    """Tests for list_scripts function."""

    def test_returns_list(self):
        scripts = list_scripts()
        assert isinstance(scripts, list)
        assert len(scripts) > 50  # There are many scripts

    def test_contains_common_scripts(self):
        scripts = list_scripts()
        assert "Latin" in scripts
        assert "Greek" in scripts
        assert "Arabic" in scripts
        assert "Han" in scripts

    def test_sorted(self):
        scripts = list_scripts()
        assert scripts == sorted(scripts)


class TestListScriptsInfo:
    """Tests for list_scripts_info function."""

    def test_returns_list_of_dicts(self):
        info = list_scripts_info()
        assert isinstance(info, list)
        assert all(isinstance(s, dict) for s in info)

    def test_dict_keys(self):
        info = list_scripts_info()
        for s in info[:5]:  # Check first few
            assert "code" in s
            assert "name" in s
            assert "is_cased" in s
            assert "is_rtl" in s


class TestGetScriptInfo:
    """Tests for get_script_info function."""

    def test_greek(self):
        info = get_script_info("Greek")
        assert info["code"] == "Grek"
        assert info["name"] == "Greek"
        assert info["is_cased"] is True
        assert info["is_rtl"] is False

    def test_arabic(self):
        info = get_script_info("Arabic")
        assert info["code"] == "Arab"
        assert info["is_rtl"] is True
        assert info["is_cased"] is False

    def test_by_code(self):
        info = get_script_info("Latn")
        assert info["name"] == "Latin"

    def test_invalid_script(self):
        # Invalid scripts return None
        assert get_script_info("NotAScript") is None
