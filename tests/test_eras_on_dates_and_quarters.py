"""An era on a full date, and quarters, as CLDR's patterns write them."""

import pytest

from icukit.recognize import FlexibleTextDateDetector


def _dates(text):
    return [(d["text"], d["value"].fields) for d in FlexibleTextDateDetector("en_US").detect(text)]


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Mar 5, 2024 AD", (("G", 1), ("y", 2024), ("M", 3), ("d", 5))),
        ("5 March 44 BC", (("G", 0), ("y", 44), ("M", 3), ("d", 5))),
    ],
)
def test_an_era_on_a_full_date_reads_with_it(text, fields):
    assert (text, fields) in _dates(text)


@pytest.mark.parametrize(
    "text, fields",
    [("Q1 2024", (("y", 2024), ("Q", 1))), ("3rd quarter 1999", (("y", 1999), ("Q", 3)))],
)
def test_a_quarter_reads_as_icu_writes_it(text, fields):
    assert _dates(text) == [(text, fields)]


def test_a_quarter_icu_does_not_write_is_not_read():
    assert _dates("Q5 2024") == []


def test_dates_without_an_era_or_quarter_are_unchanged():
    assert _dates("May 5, 2020") == [("May 5, 2020", (("y", 2020), ("M", 5), ("d", 5)))]
    assert _dates("500 BC") == [("500 BC", (("G", 0), ("y", 500)))]
