"""Tests for isolated-letter recall candidates."""

import pytest

import icukit.recognize as recognize
from icukit.detectors import NumberValue, detect


@pytest.mark.parametrize(
    ("surface", "name"),
    [("I", "i"), ("M", "em"), ("X", "ex"), ("a", "a"), ("Z", "zee")],
)
def test_isolated_latin_letters_have_english_names(surface, name):
    detection = recognize.LetterNameDetector("en_US").detect(surface)[0]

    assert (detection["start"], detection["end"]) == (0, 1)
    assert detection["type"] == "letter:name"
    assert detection["value"] == name


def test_letter_name_coexists_with_roman_cardinal_on_the_same_span():
    detections = detect(
        "I",
        (
            recognize.FlexibleNumberDetector("en_US"),
            recognize.LetterNameDetector("en_US"),
        ),
    )

    assert [(detection["type"], detection["value"]) for detection in detections] == [
        ("letter:name", "i"),
        ("number:cardinal:roman", NumberValue("1", None)),
    ]
    assert {(detection["start"], detection["end"]) for detection in detections} == {(0, 1)}


@pytest.mark.parametrize("surface", ["II", "xI", "Ix"])
def test_letter_names_require_one_isolated_letter(surface):
    assert recognize.LetterNameDetector("en_US").detect(surface) == []


def test_letter_names_are_inert_without_locale_lexical_data():
    assert recognize.LetterNameDetector("fr").detect("A") == []
