"""Tests for Unicode normalization and character properties."""

import codecs
import json
import subprocess
import sys
import warnings

import pytest

from icukit import (
    NFC,
    NFD,
    NFKC,
    NFKD,
    NormalizationError,
    char_from_name,
    decode_unicode_escapes,
    encode_unicode_escapes,
    get_block_characters,
    get_category_characters,
    get_char_category,
    get_char_info,
    get_char_name,
    get_char_names,
    is_normalized,
    list_blocks,
    list_categories,
    normalize,
)


class TestUnicodeEscapes:
    """Tests for Unicode escape conversion."""

    @pytest.mark.parametrize(
        ("escaped", "expected"),
        [
            (r"\u03B1", "α"),
            (r"\U0001F600", "😀"),
            (r"\x41", "A"),
            ("U+03B1 U+1F600", "α 😀"),
            (r"\uD83D\uDE00", "\ud83d\ude00"),
            (r"\xC3\xA9", "Ã©"),
            (r"\101", "A"),
            (r"a\nb\tc", "a\nb\tc"),
            (r"\'\"\\", "'\"\\"),
            (r"\N{GREEK SMALL LETTER ALPHA}", "α"),
            (r"\N{NO SUCH CHARACTER}", r"\N{NO SUCH CHARACTER}"),
            (r"\\u03B1", r"\u03B1"),
            (r"\uZZZZ", r"\uZZZZ"),
            (r"\U00110000", r"\U00110000"),
            (r"\q", r"\q"),
        ],
    )
    def test_decode_unicode_escapes(self, escaped, expected):
        assert decode_unicode_escapes(escaped) == expected

    @pytest.mark.parametrize(
        "text",
        [
            r"\u03B1\U0001F600\x41\xC3\xA9\101",
            r"a\nb\tc\rd\\e\'f\"g\a\b\f\v",
            r"\N{LATIN SMALL LETTER E WITH ACUTE} \0 \12 \777",
            r"plain ASCII, no escapes",
            r"C:\path\to\file",
        ],
    )
    def test_ascii_input_decodes_as_the_unicode_escape_codec_does(self, text):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            expected = codecs.decode(text, "unicode_escape")
        assert decode_unicode_escapes(text) == expected

    @pytest.mark.parametrize("text", ["α", "café", "Москва", "世界", "😀", "Ã©", "a\\é"])
    def test_non_ascii_text_passes_through(self, text):
        assert decode_unicode_escapes(text) == text

    def test_decode_mixes_escapes_with_non_ascii_text(self):
        assert decode_unicode_escapes(r"α=\u03B1, é=\xE9, \n") == "α=α, é=é, \n"

    def test_decode_inverts_the_long_escape_format(self):
        text = "aé α😀"
        assert decode_unicode_escapes(encode_unicode_escapes(text, format="U")) == text

    @pytest.mark.parametrize(
        ("format", "expected"),
        [
            ("u", r"\u03B1\uD83D\uDE00"),
            ("U", r"\U000003B1\U0001F600"),
            ("x", r"\xCE\xB1\xF0\x9F\x98\x80"),
            ("uplus", "U+03B1 U+1F600"),
            ("char", "α😀"),
        ],
    )
    def test_encode_unicode_escapes_formats(self, format, expected):
        assert encode_unicode_escapes(r"\u03B1\U0001F600", format=format) == expected

    def test_encode_keeps_literal_non_ascii_text(self):
        assert encode_unicode_escapes("α", format="char") == "α"
        assert encode_unicode_escapes("α") == "U+03B1"

    def test_encode_decodes_input_first(self):
        assert encode_unicode_escapes(r"\u03B1") == "U+03B1"

    def test_encode_rejects_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid escape format: bad"):
            encode_unicode_escapes("A", format="bad")


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


class TestCharNameChoices:
    """The three names ICU keeps for a code point, and the lookup from name to character."""

    @pytest.mark.parametrize(
        ("codepoint", "unicode", "alias", "extended"),
        [
            (
                0x01A2,
                "LATIN CAPITAL LETTER OI",
                "LATIN CAPITAL LETTER GHA",
                "LATIN CAPITAL LETTER OI",
            ),
            (0x0041, "LATIN CAPITAL LETTER A", "", "LATIN CAPITAL LETTER A"),
            (0x0007, "", "", "<control-0007>"),
            (0xD7A4, "", "", "<unassigned-D7A4>"),
            (0xAC01, "HANGUL SYLLABLE GAG", "", "HANGUL SYLLABLE GAG"),
            (0x4F60, "CJK UNIFIED IDEOGRAPH-4F60", "", "CJK UNIFIED IDEOGRAPH-4F60"),
            (0x1F600, "GRINNING FACE", "", "GRINNING FACE"),
            (0xFFFF, "", "", "<noncharacter-FFFF>"),
            (0xD800, "", "", "<lead surrogate-D800>"),
            (0xDC00, "", "", "<trail surrogate-DC00>"),
        ],
    )
    def test_names(self, codepoint, unicode, alias, extended):
        char = chr(codepoint)
        assert get_char_name(char) == unicode
        assert get_char_name(char, "unicode") == unicode
        assert get_char_name(char, "alias") == alias
        assert get_char_name(char, "extended") == extended
        assert get_char_names(char) == {"unicode": unicode, "alias": alias, "extended": extended}

    @pytest.mark.parametrize("choice", ["any", "Unicode", "", None])
    def test_invalid_choice(self, choice):
        with pytest.raises(ValueError, match="Invalid name choice"):
            get_char_name("A", choice)

    @pytest.mark.parametrize(
        ("name", "codepoint"),
        [
            ("GREEK SMALL LETTER ALPHA", 0x03B1),
            ("LATIN CAPITAL LETTER OI", 0x01A2),
            ("LATIN CAPITAL LETTER GHA", 0x01A2),
            ("<control-0007>", 0x0007),
            ("<unassigned-D7A4>", 0xD7A4),
            ("HANGUL SYLLABLE GAG", 0xAC01),
            ("CJK UNIFIED IDEOGRAPH-4F60", 0x4F60),
            ("GRINNING FACE", 0x1F600),
            ("<noncharacter-FFFF>", 0xFFFF),
            ("<lead surrogate-D800>", 0xD800),
        ],
    )
    def test_char_from_name(self, name, codepoint):
        assert char_from_name(name) == chr(codepoint)

    @pytest.mark.parametrize(
        "codepoint", [0x0041, 0x01A2, 0x0007, 0xAC01, 0x4F60, 0x1F600, 0xFFFF, 0xD800]
    )
    def test_every_name_round_trips(self, codepoint):
        char = chr(codepoint)
        for choice, name in get_char_names(char).items():
            if name:
                assert char_from_name(name, choice) == char
                assert char_from_name(name) == char

    def test_icu_matches_without_regard_to_case(self):
        assert char_from_name("greek small letter alpha") == "α"
        assert char_from_name("Latin Capital Letter Gha") == "Ƣ"
        assert char_from_name("<CONTROL-0007>") == "\x07"

    @pytest.mark.parametrize(
        ("name", "choice"),
        [
            ("LATIN CAPITAL LETTER GHA", "unicode"),
            ("LATIN CAPITAL LETTER GHA", "extended"),
            ("LATIN CAPITAL LETTER OI", "alias"),
            ("<control-0007>", "unicode"),
        ],
    )
    def test_each_choice_searches_only_its_names(self, name, choice):
        with pytest.raises(ValueError, match="Unknown character name"):
            char_from_name(name, choice)

    @pytest.mark.parametrize(
        "name",
        [
            "NO SUCH CHARACTER",
            "",
            " GREEK SMALL LETTER ALPHA",
            "GREEK SMALL LETTER  ALPHA",
            "GREEK SMALL LETTER ÅLPHA",
            "\ud800",
            "BEL",  # a control alias, which ICU does not carry
        ],
    )
    def test_unknown_name(self, name):
        with pytest.raises(ValueError, match="Unknown character name"):
            char_from_name(name)

    def test_char_from_name_invalid_choice(self):
        with pytest.raises(ValueError, match="Invalid name choice"):
            char_from_name("GREEK SMALL LETTER ALPHA", "formal")


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

    def test_alias_and_extended_name(self):
        info = get_char_info("Ƣ")
        assert info["name"] == "LATIN CAPITAL LETTER OI"
        assert info["alias"] == "LATIN CAPITAL LETTER GHA"
        assert info["extended_name"] == "LATIN CAPITAL LETTER OI"
        info = get_char_info("\x07")
        assert info["name"] == ""
        assert info["alias"] == ""
        assert info["extended_name"] == "<control-0007>"

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


class TestUnicodeInfoCli:
    """``unicode info`` reads the characters it is given, and decodes only escapes."""

    @staticmethod
    def _codepoints(text):
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "unicode", "info", "-H", "-t", text],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return [line.split("\t")[1] for line in result.stdout.splitlines()]

    def test_non_ascii_input(self):
        assert self._codepoints("αé😀") == ["U+03B1", "U+00E9", "U+1F600"]

    def test_escapes_beside_non_ascii_input(self):
        assert self._codepoints(r"α\u00E9\N{GREEK SMALL LETTER BETA}") == [
            "U+03B1",
            "U+00E9",
            "U+03B2",
        ]

    @pytest.mark.parametrize(("given", "codepoint"), [(r"\ud83d", "U+D83D"), ("U+D800", "U+D800")])
    def test_a_lone_surrogate_prints_as_its_escape(self, given, codepoint):
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "unicode", "info", "-H", "-t", given],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        char, shown_codepoint = result.stdout.rstrip("\n").split("\t")[:2]
        assert shown_codepoint == codepoint
        assert char == "\\u" + codepoint[2:].lower()

    def test_a_lone_surrogate_is_a_json_escape(self):
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "unicode", "info", "-j", "-t", r"\ud83d"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        assert json.loads(result.stdout)[0]["char"] == "\ud83d"


def _run_unicode_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", "unicode", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestUnicodeNameCli:
    """``unicode name`` picks a name, and ``unicode lookup`` goes from name to character."""

    def test_name_default_is_the_formal_name(self):
        result = _run_unicode_cli("name", "-H", "-t", "Ƣ")
        assert result.returncode == 0, result.stderr
        assert result.stdout == "Ƣ\tU+01A2\tLATIN CAPITAL LETTER OI\n"

    @pytest.mark.parametrize(
        ("text", "choice", "name"),
        [
            ("Ƣ", "alias", "LATIN CAPITAL LETTER GHA"),
            (r"\u0007", "extended", "<control-0007>"),
            ("U+FFFF", "extended", "<noncharacter-FFFF>"),
        ],
    )
    def test_name_choice(self, text, choice, name):
        result = _run_unicode_cli("name", "-j", "-t", text, "--choice", choice)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)[0]["name"] == name

    def test_name_all(self):
        result = _run_unicode_cli("name", "-t", "Ƣ", "--choice", "all")
        assert result.returncode == 0, result.stderr
        header, row = result.stdout.splitlines()
        assert header.split("\t") == ["char", "codepoint", "name", "alias", "extended_name"]
        assert row.split("\t")[2:] == [
            "LATIN CAPITAL LETTER OI",
            "LATIN CAPITAL LETTER GHA",
            "LATIN CAPITAL LETTER OI",
        ]

    def test_info_columns_are_unchanged_without_all_names(self):
        result = _run_unicode_cli("info", "-t", "Ƣ")
        assert result.returncode == 0, result.stderr
        header = result.stdout.splitlines()[0]
        assert header.split("\t") == ["char", "codepoint", "name", "category", "script"]

    def test_info_all_names(self):
        result = _run_unicode_cli("info", "-H", "-t", "Ƣ", "--all-names")
        assert result.returncode == 0, result.stderr
        assert result.stdout.rstrip("\n").split("\t")[-2:] == [
            "LATIN CAPITAL LETTER GHA",
            "LATIN CAPITAL LETTER OI",
        ]

    def test_info_json_has_the_names(self):
        result = _run_unicode_cli("info", "-j", "-t", r"\u0007")
        assert result.returncode == 0, result.stderr
        info = json.loads(result.stdout)[0]
        assert info["alias"] == ""
        assert info["extended_name"] == "<control-0007>"

    def test_lookup(self):
        text = "GREEK SMALL LETTER ALPHA\nlatin capital letter gha\n<control-0007>"
        result = _run_unicode_cli("lookup", "-j", "-t", text)
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert [row["char"] for row in data] == ["α", "Ƣ", "\x07"]
        assert [row["codepoint"] for row in data] == ["U+03B1", "U+01A2", "U+0007"]
        assert data[1]["query"] == "latin capital letter gha"
        assert data[1]["name"] == "LATIN CAPITAL LETTER OI"

    def test_lookup_choice(self):
        result = _run_unicode_cli("lookup", "-t", "LATIN CAPITAL LETTER GHA", "--choice", "unicode")
        assert result.returncode == 1
        assert "Unknown character name" in result.stderr

    def test_lookup_unknown_name_reports_and_keeps_going(self):
        result = _run_unicode_cli("lookup", "-H", "-t", "NO SUCH CHARACTER\nGRINNING FACE")
        assert result.returncode == 1
        assert "Unknown character name: 'NO SUCH CHARACTER'" in result.stderr
        assert result.stdout == "GRINNING FACE\t😀\tU+1F600\tGRINNING FACE\n"
