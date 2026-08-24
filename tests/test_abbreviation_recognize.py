"""Lexicon-driven abbreviation recognizer tests."""

import pytest

from icukit.abbreviation_recognize import (
    AbbreviationDetector,
    AbbreviationExpansion,
    AbbreviationValue,
    abbreviation_detectors,
    reformat_abbreviation,
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
    assert len(detections) == 1
    assert (detections[0]["start"], detections[0]["end"]) == (0, len(surface))
    assert {(item.text, item.sense) for item in detections[0]["value"].expansions} == expected


def test_zero_expansion_deposits_one_bare_reading():
    detections = AbbreviationDetector("en").detect("Ms.")

    assert len(detections) == 1
    assert detections[0]["type"] == "abbreviation"
    assert detections[0]["value"] == AbbreviationValue("Ms.")


def test_token_boundaries_exclude_words_and_internal_dotted_fragments():
    detections = AbbreviationDetector("en").detect("Drive Andrew Andr. Dr.")

    assert {item["text"] for item in detections} == {"Dr."}


@pytest.mark.parametrize("surface", ["J.", "Q.Z."])
def test_productive_patterns_deposit_bare_readings(surface):
    detections = AbbreviationDetector("en").detect(surface)

    assert len(detections) == 1
    assert detections[0]["value"].expansions == ()


def test_surface_identity_round_trips_and_expansions_are_annotations():
    detection = AbbreviationDetector("en").detect("Dr.")[0]

    assert reformat_abbreviation(detection["spec"], detection["value"]) == detection["text"]
    assert detection["value"].expansions == (
        AbbreviationExpansion("Doctor", "title", "precedes-name"),
        AbbreviationExpansion("Drive", "thoroughfare", "address"),
    )
    assert all(
        reformat_abbreviation(detection["spec"], detection["value"]) != expansion.text
        for expansion in detection["value"].expansions
    )


def test_longest_literal_wins_without_internal_pattern_detections():
    detections = AbbreviationDetector("en").detect("Ph.D.")

    assert [item["text"] for item in detections] == ["Ph.D."]


def test_group_constructor_degrades_when_no_lexicon_ships():
    assert abbreviation_detectors("en").names() == ("abbreviation",)
    assert abbreviation_detectors("fr").names() == ()
