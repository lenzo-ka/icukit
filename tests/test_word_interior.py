"""A reading may neither start nor end between two alphanumerics inside one ICU word."""

from __future__ import annotations

import pytest

from icukit.detectors import DateDetector, NumberDetector, all_detectors
from icukit.recognize import (
    FlexibleDateDetector,
    FlexibleFractionDetector,
    FlexibleNumberDetector,
)


def _spans(detector, text: str) -> list[tuple[int, int, str]]:
    return [(d["start"], d["end"], text[d["start"] : d["end"]]) for d in detector.detect(text)]


@pytest.mark.parametrize(
    "detector, text, expected",
    [
        # Starting inside digits.
        (NumberDetector("en_US", "decimal"), "2788", []),
        (DateDetector("en_US", "y"), "16", []),
        (DateDetector("en_US", "y"), "1908", [(0, 4, "1908")]),
        (all_detectors("en_US", ("y",)), "16", [(0, 2, "16")]),
        (FlexibleDateDetector("en_US"), "2016/07/03", []),
        # Ending before a letter.
        (NumberDetector("en_US", "decimal"), "29th", []),
        (DateDetector("en_US", "y"), "29th", []),
        (FlexibleNumberDetector("en_US"), "29th", []),
        (FlexibleFractionDetector("en_US"), "1/4th", []),
        # Starting after a letter.
        (DateDetector("en_US", "y"), "asdf123@abc", []),
        (FlexibleNumberDetector("en_US"), "2Q22", []),
        (NumberDetector("en_US", "decimal"), "2Q22", []),
    ],
)
def test_fragments_of_a_longer_token_are_refused(detector, text, expected):
    assert _spans(detector, text) == expected


@pytest.mark.parametrize(
    "detector, text, expected",
    [
        (NumberDetector("en_US", "decimal"), "see 2,788 now", [(4, 9, "2,788")]),
        (FlexibleNumberDetector("en_US"), "(29)", [(1, 3, "29")]),
        (FlexibleNumberDetector("en_US"), "3.5", [(0, 3, "3.5")]),
        (FlexibleFractionDetector("en_US"), "1/4 cup", [(0, 3, "1/4")]),
    ],
)
def test_readings_flanked_by_non_alphanumerics_survive(detector, text, expected):
    assert _spans(detector, text) == expected


@pytest.mark.parametrize(
    "locale, text, expected",
    [
        ("zh", "我有3个", [(2, 3, "3")]),
        ("ja", "3冊", [(0, 1, "3")]),
    ],
)
def test_an_icu_word_boundary_between_alphanumerics_still_admits_a_reading(locale, text, expected):
    # Ideographs are alphanumeric, but ICU's word segmentation separates them from the
    # digit, so the digit is its own token rather than a fragment of one.
    assert _spans(FlexibleNumberDetector(locale), text) == expected
