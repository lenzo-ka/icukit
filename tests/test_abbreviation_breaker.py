"""Lexicon-driven sentence-break post-filter tests."""

import pytest

from icukit.abbreviation_breaker import AbbreviationSentenceBreaker


@pytest.mark.parametrize(
    "text",
    ["U.S.A. Is large.", "see e.g. This."],
)
def test_productive_suppression_merges_the_boundary(text):
    assert len(AbbreviationSentenceBreaker("en").spans(text)) == 1


def test_literal_suppression_and_provenance():
    spans = AbbreviationSentenceBreaker("en").spans("Dr. Smith arrived. He was late.")

    assert len(spans) == 2
    assert spans[0]["text"] == "Dr. Smith arrived. "
    assert "abbreviation" in spans[0]["types"]
    assert spans[0]["abbreviations"][0]["surface"] == "Dr."


def test_left_boundary_guard_does_not_match_literal_tail():
    spans = AbbreviationSentenceBreaker("en").spans("I need help. New line.")

    assert len(spans) == 2


@pytest.mark.parametrize(
    "text,surface",
    [
        ("Chapter I. Next.", "I."),
        ("No. 5 wins.", "No."),
        ("Go N. Then stop.", "N."),
    ],
)
def test_ambiguous_boundary_deposits_both_and_primary_is_merged(text, surface):
    result = AbbreviationSentenceBreaker("en").segmentations(text)

    assert len(result.spans) == 1
    assert result.ambiguous_boundaries == [
        {
            "offset": text.index(surface) + len(surface),
            "left_surface": surface,
            "alternatives": ["break", "no-break"],
        }
    ]


def test_abbreviation_at_eof_needs_no_boundary():
    assert len(AbbreviationSentenceBreaker("en").spans("He holds a Ph.D.")) == 1


def test_uncased_variant_inherits_ambiguous_break_behavior():
    result = AbbreviationSentenceBreaker("en").segmentations("e. Next.")

    assert [span["text"] for span in result.spans] == ["e. Next."]
    assert result.ambiguous_boundaries == [
        {"offset": 2, "left_surface": "e.", "alternatives": ["break", "no-break"]}
    ]


@pytest.mark.parametrize(
    "text,surface",
    [
        ('Dr." Smith.', "Dr."),
        ("Dr.’ Smith.", "Dr."),
    ],
)
def test_suppress_abbreviation_before_closing_punctuation_merges(text, surface):
    result = AbbreviationSentenceBreaker("en").segmentations(text)

    assert [span["text"] for span in result.spans] == [text]
    assert result.spans[0]["abbreviations"][0]["surface"] == surface


@pytest.mark.parametrize("text", ['Go N." Next.', "Go (N.) Next."])
def test_ambiguous_abbreviation_before_closing_punctuation_keeps_both(text):
    result = AbbreviationSentenceBreaker("en").segmentations(text)

    assert [span["text"] for span in result.spans] == [text]
    assert result.ambiguous_boundaries == [
        {
            "offset": text.index("N.") + 2,
            "left_surface": "N.",
            "alternatives": ["break", "no-break"],
        }
    ]


def test_non_abbreviation_before_closing_punctuation_still_breaks():
    spans = AbbreviationSentenceBreaker("en").spans('help." Next.')

    assert [span["text"] for span in spans] == ['help." ', "Next."]


def test_missing_locale_degrades_to_icu_segmentation():
    breaker = AbbreviationSentenceBreaker("fr")
    assert breaker.spans("Bonjour. Encore.") == breaker._breaker.break_sentence_spans(
        "Bonjour. Encore."
    )
