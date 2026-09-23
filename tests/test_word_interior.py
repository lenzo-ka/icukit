"""A reading may neither start nor end between two alphanumerics inside one ICU word."""

from __future__ import annotations

import pytest

from icukit.detectors import DateDetector, NumberDetector, all_detectors
from icukit.recognize import (
    FlexibleDateDetector,
    FlexibleFractionDetector,
    FlexibleNumberDetector,
    FlexiblePercentDetector,
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


@pytest.mark.parametrize(
    "detector, text",
    [
        (FlexibleNumberDetector("en_US"), "ab2,788"),
        (NumberDetector("en_US", "decimal"), "ab2,788"),
        (FlexibleNumberDetector("en_US"), "x1,000"),
        (FlexibleNumberDetector("en_US"), "v2.0"),
        (FlexibleNumberDetector("en_US"), "iOS17.2"),
        (FlexibleNumberDetector("en_US"), "rev3.1.4"),
        (FlexiblePercentDetector("en_US"), "x5.5%"),
    ],
)
def test_the_tail_after_a_separator_inside_a_word_is_a_fragment(detector, text):
    # Refusing the true start must not leave the scan to read the tail after "," or ".".
    assert _spans(detector, text) == []


@pytest.mark.parametrize(
    "text",
    [
        "café5",
        "café5",  # the same word decomposed: a combining mark ends the letters
        "abc­123",  # soft hyphen
        "abc‍123",  # zero width joiner
        "abc⁠123",  # word joiner
    ],
)
def test_marks_and_format_characters_do_not_hide_a_word_interior(text):
    assert _spans(FlexibleNumberDetector("en_US"), text) == []


def test_a_vowel_sign_does_not_hide_a_word_interior():
    assert _spans(FlexibleNumberDetector("hi"), "किताबें5") == []


@pytest.mark.parametrize(
    "locale, text, expected",
    [
        ("th", "ราคา100บาท", [(4, 7, "100")]),
        ("th-u-nu-thai", "ราคา๑๐๐บาท", [(4, 7, "๑๐๐")]),
        ("lo", "ລາຄາ100ກີບ", [(4, 7, "100")]),
        ("km", "តម្លៃ100រៀល", [(5, 8, "100")]),
        ("my", "၅ခု", [(0, 1, "၅")]),
    ],
)
def test_digits_against_a_script_written_without_spaces_are_a_token(locale, text, expected):
    # ICU's dictionary segmentation leaves these digits inside one "word" with their
    # neighbors, but ICU marks the scripts as breaking between letters.
    assert _spans(FlexibleNumberDetector(locale), text) == expected
