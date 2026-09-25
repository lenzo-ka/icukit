"""Negative currency amounts, as ICU's standard and accounting forms write them."""

import pytest

from icukit.recognize import FlexibleCurrencyDetector, _negative_currency_wraps


def _money(code, text):
    return [
        (d["text"], d["value"].decimal)
        for d in FlexibleCurrencyDetector("en_US", code).detect(text)
    ]


def test_the_wraps_are_icus():
    assert set(_negative_currency_wraps("en_US", "USD")) == {("-", ""), ("(", ")")}


@pytest.mark.parametrize(
    "code, text, decimal",
    [
        ("USD", "-$42.50", "-42.50"),
        ("USD", "($42.50)", "-42.50"),
        ("EUR", "-€42", "-42"),
        ("EUR", "(€5)", "-5"),
    ],
)
def test_a_negative_amount_reads_negative(code, text, decimal):
    assert _money(code, text) == [(text, decimal)]


@pytest.mark.parametrize(
    "text, readings",
    [
        ("$42.50", [("$42.50", "42.50")]),
        ("US$-42.50", [("US$-42.50", "-42.50")]),
        ("(5) $3", [("$3", "3")]),
    ],
)
def test_other_amounts_are_unchanged(text, readings):
    assert _money("USD", text) == readings
