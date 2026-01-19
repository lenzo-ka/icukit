"""Smoke tests to verify PyICU is working."""

import icu


def test_icu_version():
    """ICU version should be accessible."""
    assert icu.ICU_VERSION
    assert isinstance(icu.ICU_VERSION, str)


def test_transliterate():
    """Basic transliteration should work."""
    t = icu.Transliterator.createInstance("Latin-Cyrillic")
    assert t.transliterate("hello") == "хелло"


def test_normalize():
    """Unicode normalization should work."""
    nfc = icu.Normalizer2.getNFCInstance()
    # é as e + combining acute vs precomposed
    assert nfc.normalize("e\u0301") == "é"


def test_break_iterator():
    """Word break iteration should work."""
    bi = icu.BreakIterator.createWordInstance(icu.Locale.getUS())
    bi.setText("hello world")
    breaks = list(bi)
    assert 5 in breaks  # after "hello"
    assert 6 in breaks  # after space
    assert 11 in breaks  # after "world"
