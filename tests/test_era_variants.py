"""CLDR's variant and wide era names read like its abbreviated ones."""

import pytest

from icukit.recognize import FlexibleTextDateDetector, _language_eras


def _eras(text):
    return [
        (
            d["text"],
            d["value"].fields,
            next(c.form for c in d["captures"] if c.name == "era"),
            d["spec"].pattern,
        )
        for d in FlexibleTextDateDetector("en_US").detect(text)
    ]


@pytest.mark.parametrize(
    "text, surface, era, year, width, pattern",
    [
        ("300 BCE", "300 BCE", 0, 300, "short", "y G"),
        ("in 200 CE.", "200 CE", 1, 200, "short", "y G"),
        ("300 Before Christ", "300 Before Christ", 0, 300, "wide", "y GGGG"),
        ("44 Before Common Era", "44 Before Common Era", 0, 44, "wide", "y GGGG"),
        ("1066 Anno Domini", "1066 Anno Domini", 1, 1066, "wide", "y GGGG"),
    ],
)
def test_a_variant_or_wide_era_reads_with_its_index_and_width(
    text, surface, era, year, width, pattern
):
    assert _eras(text) == [(surface, (("G", era), ("y", year)), width, pattern)]


def test_the_variants_come_from_cldrs_era_table():
    eras = {form: (index, width) for form, index, width in _language_eras("en")}
    assert eras["BCE"] == (0, "short") and eras["CE"] == (1, "short")
    assert eras["Common Era"] == (1, "wide")


@pytest.mark.parametrize("text", ["CE 200", "300BCE", "Vancouver, BC 2010"])
def test_an_era_still_reads_only_in_cldrs_order_and_spacing(text):
    assert _eras(text) == []
