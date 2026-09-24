"""Grouped ordinals, other locales' ordinal suffixes, and Roman numerals with a suffix."""

import pytest

from icukit.recognize import (
    FlexibleNumberDetector,
    FlexibleOrdinalDetector,
    _foreign_ordinal_suffixes,
)


def _ordinals(text, locale="en_US"):
    return [(d["text"], d["value"].decimal) for d in FlexibleOrdinalDetector(locale).detect(text)]


@pytest.mark.parametrize(
    "text, value", [("1,000th", "1000"), ("1,000,000th", "1000000"), ("12,345th", "12345")]
)
def test_a_grouped_ordinal_reads_when_icu_renders_the_same_surface(text, value):
    assert _ordinals(text) == [(text, value)]


def test_a_misgrouped_ordinal_does_not_read():
    assert _ordinals("10,00th") == []


@pytest.mark.parametrize("text", ["1º", "1ª", "2ª", "1.º"])
def test_an_ordinal_indicator_from_another_locale_reads_in_english(text):
    assert _ordinals(text) == [(text, text[0])]


@pytest.mark.parametrize("text", ["1e", "1a", "chapter 1."])
def test_a_suffix_made_of_this_locales_letters_or_punctuation_is_not_foreign(text):
    assert _ordinals(text) == []


def test_foreign_suffixes_hold_a_letter_outside_the_locales_exemplars():
    suffixes = _foreign_ordinal_suffixes("en_US")

    assert {"º", "ª", ".º"} <= suffixes
    assert not {"e", "a", "r", "."} & suffixes


@pytest.mark.parametrize("text, surface", [("Henry II's reign", "II's"), ("the III's", "III's")])
def test_a_roman_numeral_spans_its_possessive(text, surface):
    romans = [
        (d["text"], [c.name for c in d["captures"]])
        for d in FlexibleNumberDetector("en_US").detect(text)
        if d["type"] == "number:cardinal:roman"
    ]

    assert romans == [(surface, ["integer", "apostrophe", "suffix"])]


def test_a_roman_numeral_takes_no_suffix_in_a_language_without_a_plural_entry():
    romans = [
        d["text"]
        for d in FlexibleNumberDetector("fr_FR").detect("Henri VIII's")
        if d["type"] == "number:cardinal:roman"
    ]

    assert "VIII's" not in romans


def test_a_foreign_ordinal_suffix_must_end_its_word():
    assert _ordinals("1ºx") == []


def test_no_foreign_ordinal_suffix_holds_a_space():
    assert not any(" " in suffix for suffix in _foreign_ordinal_suffixes("ru_RU"))


def test_the_ordinal_scan_does_work_linear_in_the_text(monkeypatch):
    # Each start used to probe every later digit run in the text; the work is counted
    # rather than timed so the test cannot flake on a slow machine.
    detector = FlexibleOrdinalDetector("en_US")
    probes = {"count": 0}
    real = detector._digit_run

    def counting(text, start):
        probes["count"] += 1
        return real(text, start)

    monkeypatch.setattr(detector, "_digit_run", counting)
    base = "On the 21st of March, 3 people saw 42 cats. "
    counts = []
    for repeats in (20, 40):
        probes["count"] = 0
        detector.detect(base * repeats)
        counts.append(probes["count"])

    assert counts[1] <= counts[0] * 2.5
