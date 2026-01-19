"""Tests for Unicode normalization and character properties."""

import pytest

from icukit import (
    NFC,
    NFD,
    NFKC,
    NFKD,
    NormalizationError,
    get_block_characters,
    get_category_characters,
    get_char_category,
    get_char_info,
    get_char_name,
    is_normalized,
    list_blocks,
    list_categories,
    normalize,
)


class TestNormalize:
    """Tests for normalize function."""

    def test_nfc_default(self):
        # é composed should stay composed
        result = normalize("café")
        assert result == "café"

    def test_nfd_decomposes(self):
        # NFD should decompose
        composed = "é"  # single codepoint
        result = normalize(composed, NFD)
        # Should be e + combining acute accent (2 codepoints)
        assert len(result) >= len(composed)

    def test_nfkc_compatibility(self):
        # fi ligature should become "fi"
        result = normalize("ﬁ", NFKC)
        assert result == "fi"

    def test_nfkd_compatibility(self):
        # Circled digit should become regular digit
        result = normalize("①", NFKD)
        assert result == "1"

    def test_invalid_form(self):
        with pytest.raises(NormalizationError):
            normalize("text", "INVALID")

    def test_case_insensitive_form(self):
        # Form names should be case-insensitive
        result = normalize("café", "nfc")
        assert result == "café"


class TestIsNormalized:
    """Tests for is_normalized function."""

    def test_nfc_normalized(self):
        # Pre-composed text is NFC normalized
        assert is_normalized("café", NFC) is True

    def test_nfd_check(self):
        # Check NFD form
        nfd_text = normalize("café", NFD)
        assert is_normalized(nfd_text, NFD) is True

    def test_invalid_form(self):
        with pytest.raises(NormalizationError):
            is_normalized("text", "INVALID")


class TestGetCharName:
    """Tests for get_char_name function."""

    def test_latin_letter(self):
        assert get_char_name("A") == "LATIN CAPITAL LETTER A"

    def test_greek_letter(self):
        assert get_char_name("α") == "GREEK SMALL LETTER ALPHA"

    def test_cjk(self):
        name = get_char_name("你")
        assert "CJK" in name

    def test_emoji(self):
        name = get_char_name("😀")
        assert "GRINNING" in name or "FACE" in name

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            get_char_name("AB")

    def test_empty_input(self):
        with pytest.raises(ValueError):
            get_char_name("")


class TestGetCharCategory:
    """Tests for get_char_category function."""

    def test_uppercase_letter(self):
        assert get_char_category("A") == "Lu"

    def test_lowercase_letter(self):
        assert get_char_category("a") == "Ll"

    def test_digit(self):
        assert get_char_category("5") == "Nd"

    def test_space(self):
        assert get_char_category(" ") == "Zs"

    def test_punctuation(self):
        assert get_char_category("!") == "Po"

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            get_char_category("AB")


class TestGetCharInfo:
    """Tests for get_char_info function."""

    def test_returns_dict(self):
        info = get_char_info("α")
        assert isinstance(info, dict)

    def test_dict_keys(self):
        info = get_char_info("A")
        assert "char" in info
        assert "codepoint" in info
        assert "name" in info
        assert "category" in info
        assert "script" in info
        assert "is_letter" in info

    def test_values(self):
        info = get_char_info("α")
        assert info["char"] == "α"
        assert info["codepoint"] == "U+03B1"
        assert info["name"] == "GREEK SMALL LETTER ALPHA"
        assert info["category"] == "Ll"
        assert info["script"] == "Greek"
        assert info["is_letter"] is True
        assert info["is_lower"] is True

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            get_char_info("AB")


class TestListCategories:
    """Tests for list_categories function."""

    def test_returns_list(self):
        cats = list_categories()
        assert isinstance(cats, list)
        assert len(cats) == 30  # There are 30 general categories

    def test_dict_structure(self):
        cats = list_categories()
        for cat in cats:
            assert "code" in cat
            assert "description" in cat

    def test_contains_common_categories(self):
        cats = list_categories()
        codes = [c["code"] for c in cats]
        assert "Lu" in codes  # Uppercase Letter
        assert "Ll" in codes  # Lowercase Letter
        assert "Nd" in codes  # Decimal Number
        assert "Zs" in codes  # Space Separator


class TestNormalizationConstants:
    """Tests for normalization form constants."""

    def test_constants_exist(self):
        assert NFC == "NFC"
        assert NFD == "NFD"
        assert NFKC == "NFKC"
        assert NFKD == "NFKD"


class TestBlocks:
    """Tests for Unicode block functions."""

    def test_list_blocks(self):
        blocks = list_blocks()
        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # Basic Latin should be the first block
        assert blocks[0]["name"] == "Basic Latin"
        assert blocks[0]["range"] == "U+0000-U+007F"

        # Check structure
        for block in blocks:
            assert "name" in block
            assert "range" in block
            assert "start" in block
            assert "end" in block

    def test_get_block_characters(self):
        # Basic Latin has 128 characters
        chars = get_block_characters("Basic Latin")
        assert len(chars) == 128
        assert "A" in chars
        assert "z" in chars
        assert "!" in chars

        # Greek and Coptic
        greek_chars = get_block_characters("Greek and Coptic")
        assert "α" in greek_chars
        assert "Ω" in greek_chars

    def test_get_block_characters_invalid(self):
        with pytest.raises(ValueError):
            get_block_characters("Invalid Block Name")

    def test_get_block_characters_with_underscores(self):
        # Should handle underscores as well
        chars = get_block_characters("Basic_Latin")
        assert len(chars) == 128


class TestCategoryChars:
    """Tests for get_category_characters function."""

    def test_get_category_characters(self):
        # Lu (Uppercase Letters)
        chars = get_category_characters("Lu")
        assert len(chars) > 0
        assert "A" in chars
        assert "Z" in chars
        assert "a" not in chars

        # Nd (Decimal Numbers)
        chars = get_category_characters("Nd")
        assert "0" in chars
        assert "9" in chars
        assert "A" not in chars

    def test_invalid_category(self):
        with pytest.raises(ValueError):
            get_category_characters("Invalid")
