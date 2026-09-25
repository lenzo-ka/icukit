"""The language's other decimal styles, read only where the locale's own do not read."""

import pytest

from icukit.recognize import FlexibleNumberDetector


def _numbers(text, **options):
    return [
        (d["text"], d["value"].decimal)
        for d in FlexibleNumberDetector("en_US", **options).detect(text)
    ]


@pytest.mark.parametrize(
    "text, reading",
    [
        ("1,5", ("1,5", "1.5")),
        ("1.234,56", ("1.234,56", "1234.56")),
        ("1.234.567", ("1.234.567", "1234567")),
        ("1 234,56", ("1 234,56", "1234.56")),
        ("3,14 m", ("3,14", "3.14")),
    ],
)
def test_another_decimal_style_reads_where_en_us_reads_nothing(text, reading):
    assert reading in _numbers(text)


@pytest.mark.parametrize(
    "text, readings",
    [
        ("1,234", [("1,234", "1234")]),
        ("1.5", [("1.5", "1.5")]),
        ("12,345.67", [("12,345.67", "12345.67")]),
    ],
)
def test_text_en_us_reads_gets_no_rival_reading(text, readings):
    # kal's ruling: "1,234" stays 1234 alone, with no 1.234 beside it.
    assert _numbers(text) == readings


def test_the_choice_of_locales_governs_the_styles():
    assert _numbers("1,5 and 1.234,56", locales=()) == []
