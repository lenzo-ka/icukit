"""A numeric date with its era, as CLDR's GyMd patterns write it."""

import pytest

from icukit.recognize import FlexibleDateDetector


def _readings(locale, text):
    return {(d["text"], d["value"].fields) for d in FlexibleDateDetector(locale).detect(text)}


@pytest.mark.parametrize(
    "locale, text, surface, fields",
    [
        ("en_US", "On 3/5/2024 AD it", "3/5/2024 AD", (("G", 1), ("y", 2024), ("M", 3), ("d", 5))),
        ("en_GB", "15/03/44 BC", "15/03/44 BC", (("G", 0), ("y", 44), ("M", 3), ("d", 15))),
        ("en_US", "3/5/2024 CE", "3/5/2024 CE", (("G", 1), ("y", 2024), ("M", 3), ("d", 5))),
        ("ja_JP", "西暦2024/3/5です", "西暦2024/3/5", (("G", 1), ("y", 2024), ("M", 3), ("d", 5))),
    ],
)
def test_a_numeric_date_reads_with_its_era(locale, text, surface, fields):
    assert (surface, fields) in _readings(locale, text)


def test_the_date_without_its_era_is_its_own_reading():
    assert ("3/5/2024", (("y", 2024), ("M", 3), ("d", 5))) in _readings("en_US", "3/5/2024 AD")


def test_the_date_is_checked_in_its_era():
    # 45 BC was a leap year in the Julian calendar ICU uses before 1582; 45 AD was not.
    assert _readings("en_US", "2/29/45 BC") == {
        ("2/29/45 BC", (("G", 0), ("y", 45), ("M", 2), ("d", 29)))
    }
    assert _readings("en_US", "2/30/45 BC") == set()


def test_an_era_must_end_its_word():
    assert all("ADX" not in text for text, _ in _readings("en_US", "3/5/2024 ADX"))
    assert all(fields[0][0] != "G" for _, fields in _readings("en_US", "3/5/2024 ADX"))
