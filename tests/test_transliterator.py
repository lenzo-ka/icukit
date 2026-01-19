"""Tests for Transliterator module."""

from icukit import CommonTransliterators, Transliterator, list_transliterators, transliterate


class TestTransliterator:
    """Test transliteration functionality."""

    def test_transliterate_function(self):
        """Test simple transliterate function."""
        result = transliterate("Hello", "Latin-Cyrillic")
        assert result is not None
        assert len(result) > 0

    def test_transliterator_class(self):
        """Test Transliterator class."""
        trans = Transliterator("Latin-Greek")
        result = trans.transliterate("Hello")
        assert result is not None
        assert len(result) > 0

    def test_list_transliterators(self):
        """Test listing transliterators."""
        trans_list = list_transliterators()
        assert isinstance(trans_list, list)
        assert len(trans_list) > 0
        assert "Latin-Cyrillic" in trans_list
        assert "Latin-Greek" in trans_list

    def test_multiple_transliterations(self):
        """Test different transliterations."""
        text = "Hello"
        cyrillic = transliterate(text, "Latin-Cyrillic")
        greek = transliterate(text, "Latin-Greek")
        arabic = transliterate(text, "Latin-Arabic")
        assert cyrillic != greek
        assert greek != arabic

    def test_any_latin(self):
        """Test Any-Latin transliteration."""
        result = transliterate("你好", "Any-Latin")
        assert result is not None
        assert any(c.isascii() for c in result)

    def test_reverse_transliteration(self):
        """Test reverse transliteration."""
        trans = Transliterator("Latin-Cyrillic")
        forward = trans.transliterate("Hello")
        inverse = trans.create_inverse()
        back = inverse.transliterate(forward)
        assert "H" in back or "h" in back

    def test_from_rules(self):
        """Test creating transliterator from custom rules."""
        rules = "a > A; b > B; c > C;"
        trans = Transliterator.from_rules("test-upper", rules)
        result = trans.transliterate("abc")
        assert result == "ABC"

    def test_repr(self):
        """Test string representation."""
        trans = Transliterator("Latin-Cyrillic")
        assert "Latin-Cyrillic" in repr(trans)


class TestCommonTransliterators:
    """Test CommonTransliterators helper class."""

    def test_remove_accents(self):
        """Test accent removal."""
        result = CommonTransliterators.remove_accents("café résumé")
        assert result == "cafe resume"

    def test_to_ascii(self):
        """Test conversion to ASCII."""
        result = CommonTransliterators.to_ascii("café")
        assert result.isascii()

    def test_to_latin(self):
        """Test conversion to Latin script."""
        result = CommonTransliterators.to_latin("Москва")
        assert any(c.isascii() for c in result)

    def test_normalize(self):
        """Test Unicode normalization."""
        # e + combining acute should normalize to precomposed é
        result = CommonTransliterators.normalize("e\u0301", "NFC")
        assert result == "é"

    def test_case_transforms(self):
        """Test case transformations."""
        assert CommonTransliterators.to_upper("hello") == "HELLO"
        assert CommonTransliterators.to_lower("HELLO") == "hello"
        assert CommonTransliterators.to_title("hello world") == "Hello World"
