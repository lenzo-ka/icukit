"""ICU's ISO 8601 "Z" written against a time reads as its zone."""

import pytest

from icukit.recognize import FlexibleTimeDetector, _iso_utc_designator


def _times(text):
    return [
        (d["text"], [(c.name, c.text) for c in d["captures"] if c.name == "time-zone"])
        for d in FlexibleTimeDetector("en_US").detect(text)
    ]


def test_the_designator_is_what_icus_iso_pattern_writes_for_utc():
    assert _iso_utc_designator() == "Z"


@pytest.mark.parametrize("text", ["12:00:00Z", "06:00Z"])
def test_a_time_with_a_z_reads_whole_with_its_zone(text):
    assert _times(text) == [(text, [("time-zone", "Z")])]


def test_a_z_that_starts_a_word_is_not_a_zone():
    assert _times("12:00:00Zulu") == []
