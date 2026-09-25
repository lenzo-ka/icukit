"""Curated currency surfaces: "Rs" as the Indian rupee beside ICU's own rupees."""

import pytest

from icukit import icu_abbreviations
from icukit.recognize import FlexibleCurrencyDetector, FlexibleMeasureDetector
from icukit.unit_surfaces import curated_composed_units, curated_currency_surfaces


def _money(code, text):
    return [
        (d["text"], d["value"].decimal, d["value"].currency)
        for d in FlexibleCurrencyDetector("en_US", code).detect(text)
    ]


@pytest.mark.parametrize("text", ["Rs 100", "Rs. 500", "Rs500"])
def test_rs_reads_as_the_indian_rupee(text):
    amount = "".join(character for character in text if character.isdigit())
    assert _money("INR", text) == [(text, amount, "INR")]


@pytest.mark.parametrize("code", ["PKR", "MUR", "SCR", "LKR", "NPR"])
def test_rs_also_reads_as_each_rupee_icu_writes_it_for(code):
    assert _money(code, "Rs 100") == [("Rs 100", "100", code)]


def test_a_dollar_still_reads_only_as_the_locales_own():
    # The curated rows add "Rs" only; no other locale's "$" is taken.
    assert _money("AUD", "$5") == []
    assert _money("USD", "$5") == [("$5", "5", "USD")]


def test_the_list_gives_rs_for_inr_as_curated_with_icus_names():
    rows = [
        row
        for row in icu_abbreviations("en_US", kinds=["currency"])
        if row.surface == "Rs" and row.key == "INR"
    ]
    assert [(row.source, row.expansions) for row in rows] == [
        ("curated", ("Indian rupee", "Indian rupees"))
    ]
    assert ("Rs", "INR") in curated_currency_surfaces("en")


def test_compound_units_icu_composes_read():
    assert "megajoule-per-kilogram" in curated_composed_units("en")
    detector = FlexibleMeasureDetector("en_US", "cubic-meter-per-second")
    assert [d["text"] for d in detector.detect("5 m³/s")] == ["5 m³/s"]
