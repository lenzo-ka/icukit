"""The abbreviation consumers share one compiled lexicon view."""

from icukit.abbreviation_breaker import AbbreviationSentenceBreaker
from icukit.abbreviation_compile import compile_lexicon
from icukit.abbreviation_recognize import AbbreviationDetector


def test_compiled_literal_inventory_is_shared_without_drift():
    compiled = compile_lexicon("en")
    assert compiled is not None

    breaker = AbbreviationSentenceBreaker("en", compiled)
    recognizer = AbbreviationDetector("en", compiled)

    assert recognizer.classified_surfaces == breaker.classified_surfaces
    assert recognizer.classified_surfaces == compiled.classified_surfaces


def test_missing_locale_compiles_to_none():
    assert compile_lexicon("zz") is None


def test_uncased_single_segment_inherits_backing_literal_behavior():
    compiled = compile_lexicon("en")
    assert compiled is not None

    assert compiled.classify("e.") == ("ambiguous", "uncased-latin")
    assert compiled.classify("no.") == ("ambiguous", "uncased-latin")
    assert compiled.classify("a.m.")[0] == "suppress"
