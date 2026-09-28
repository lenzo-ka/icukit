"""A four-digit number in a date is only ever its year, never a month or a day.

Checked on the readings themselves, not on ICU's surfaces: every run of four digits a
date or date-interval reading touches lies wholly inside it and is one of its year
values, and no month or day capture covers one.
"""

from functools import cache

import icu
import pytest

from icukit import DateIntervalValue, flexible_detectors, generated_detectors

LOCALES = ("en_US", "en_GB", "de_DE")
TEXTS = (
    "12/1918",
    "1918/12",
    "2008-09-30",
    "2008/09/10",
    "09/10/2008",
    "1914–1918",
    "2024-03",
    "1918.12",
)
YEAR_FIELDS = frozenset({"y", "Y", "u", "r", "U"})
DAY_OR_MONTH = frozenset({"M", "L", "d"})


@cache
def _reader_set(locale: str, kind: str):
    gang = generated_detectors(locale)
    if kind == "flexible-guarded":
        gang = gang.with_(*flexible_detectors(locale, guarded=True).detectors)
    return gang


def _four_digit_runs(text: str) -> list[tuple[int, int]]:
    runs, index = [], 0
    while index < len(text):
        if icu.Char.isdigit(text[index]):
            end = index
            while end < len(text) and icu.Char.isdigit(text[end]):
                end += 1
            if end - index == 4:
                runs.append((index, end))
            index = end
        else:
            index += 1
    return runs


def _years(value) -> set[int]:
    values = (value.start, value.end) if isinstance(value, DateIntervalValue) else (value,)
    return {number for v in values for name, number in v.fields if name in YEAR_FIELDS}


@pytest.mark.parametrize("kind", ["default", "flexible-guarded"])
@pytest.mark.parametrize("locale", LOCALES)
def test_a_four_digit_number_is_only_ever_the_year(locale, kind):
    checked = 0
    for text in TEXTS:
        runs = _four_digit_runs(text)
        for found in _reader_set(locale, kind).detect(text):
            if not found["type"].startswith("date"):
                continue
            start, end = found["start"], found["end"]
            years = _years(found["value"])
            for run_start, run_end in runs:
                if run_end <= start or run_start >= end:
                    continue
                checked += 1
                where = (text, found["type"], found["text"])
                assert start <= run_start and run_end <= end, where
                assert int(text[run_start:run_end]) in years, where
                for capture in found["captures"]:
                    if capture.name in DAY_OR_MONTH:
                        assert capture.end <= run_start or capture.start >= run_end, where
    assert checked  # the texts are read as dates at all
