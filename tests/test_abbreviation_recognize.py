"""Lexicon-driven abbreviation recognizer tests."""

import pytest

from icukit.abbreviation_recognize import (
    AbbreviationDetector,
    AbbreviationValue,
    abbreviation_detectors,
)
from icukit.detectors import Detector


@pytest.mark.parametrize(
    "surface,expected",
    [
        ("Dr.", {("Doctor", "title"), ("Drive", "thoroughfare")}),
        ("St.", {("Saint", "saint"), ("Street", "thoroughfare")}),
        ("Mr.", {("Mister", "title")}),
    ],
)
def test_literal_expansions_are_colocated(surface, expected):
    detections = AbbreviationDetector("en").detect(surface)

    assert isinstance(AbbreviationDetector("en"), Detector)
    assert {(item["start"], item["end"]) for item in detections} == {(0, len(surface))}
    assert {(item["value"].expansion, item["value"].sense) for item in detections} == expected


def test_zero_expansion_deposits_one_bare_reading():
    detections = AbbreviationDetector("en").detect("Ms.")

    assert len(detections) == 1
    assert detections[0]["type"] == "abbreviation:none"
    assert detections[0]["value"] == AbbreviationValue("Ms.", None, "none", None, None, "suppress")


def test_token_boundaries_exclude_words_and_internal_dotted_fragments():
    detections = AbbreviationDetector("en").detect("Drive Andrew Andr. Dr.")

    assert {item["text"] for item in detections} == {"Dr."}


@pytest.mark.parametrize("surface", ["J.", "Q.Z."])
def test_productive_patterns_deposit_bare_readings(surface):
    detections = AbbreviationDetector("en").detect(surface)

    assert len(detections) == 1
    assert detections[0]["value"].expansion is None


def test_longest_literal_wins_without_internal_pattern_detections():
    detections = AbbreviationDetector("en").detect("Ph.D.")

    assert [item["text"] for item in detections] == ["Ph.D."]


def test_group_constructor_degrades_when_no_lexicon_ships():
    assert abbreviation_detectors("en").names() == ("abbreviation",)
    assert abbreviation_detectors("fr").names() == ()
