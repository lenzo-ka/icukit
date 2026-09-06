"""Tests for isolated-letter recall candidates."""

import pytest

import icukit.recognize as recognize
from icukit.detectors import NumberValue, detect
from icukit.resolve import weight


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


@pytest.mark.parametrize("surface", ["İ", "K"])
def test_non_ascii_case_variants_are_not_ascii_letter_names(surface):
    assert recognize.LetterNameDetector("en").detect(surface) == []


@pytest.mark.parametrize("surface", ["x_I", "I'm", "I’m"])
def test_identifier_and_contraction_letters_are_not_isolated(surface):
    assert recognize.LetterNameDetector("en").detect(surface) == []
    assert recognize.SingleLetterWordDetector("en").detect(surface) == []


@pytest.mark.parametrize("surface", ["x_I", "I'm", "I’m", "D'Angelo"])
def test_identifier_and_contraction_letters_are_not_roman_cardinals(surface):
    assert recognize.FlexibleNumberDetector("en").detect(surface) == []


def test_hyphen_does_not_join_a_letter_token():
    # Whether hyphens should join tokens is unsettled; pin the observed behavior so a later
    # policy change is deliberate.
    detection = recognize.LetterNameDetector("en").detect("A-1")[0]

    assert (detection["text"], detection["start"], detection["value"]) == ("A", 0, "a")


def test_english_z_name_follows_the_locale_region():
    assert recognize.LetterNameDetector("en_US").detect("Z")[0]["value"] == "zee"
    assert recognize.LetterNameDetector("en_GB").detect("Z")[0]["value"] == "zed"


def _english_letter_readings(surface):
    return detect(
        surface,
        (
            recognize.FlexibleNumberDetector("en_US"),
            recognize.LetterNameDetector("en_US"),
            recognize.SingleLetterWordDetector("en_US"),
        ),
    )


def test_i_has_cardinal_letter_name_and_word_candidates_on_one_span():
    detections = _english_letter_readings("I")

    assert [(detection["type"], detection["value"]) for detection in detections] == [
        ("letter:name", "i"),
        ("number:cardinal:roman", NumberValue("1", None)),
        ("word:single-letter", "I"),
    ]
    assert {(detection["start"], detection["end"]) for detection in detections} == {(0, 1)}


def test_isolated_i_readings_tie_on_capture_geometry():
    detections = _english_letter_readings("I")

    assert [
        tuple(
            (capture.name, capture.start, capture.end, capture.text, capture.value)
            for capture in detection["captures"]
        )
        for detection in detections
    ] == [
        (("letter", 0, 1, "I", "I"),),
        (("integer", 0, 1, "I", "1"),),
        (("letter", 0, 1, "I", "I"),),
    ]
    assert len({weight(detection) for detection in detections}) == 1


def test_m_has_cardinal_and_letter_name_but_no_word_candidate():
    detections = _english_letter_readings("M")

    assert [(detection["type"], detection["value"]) for detection in detections] == [
        ("letter:name", "em"),
        ("number:cardinal:roman", NumberValue("1000", None)),
    ]


def test_lowercase_a_has_letter_name_and_word_but_no_cardinal_candidate():
    detections = _english_letter_readings("a")

    assert [(detection["type"], detection["value"]) for detection in detections] == [
        ("letter:name", "a"),
        ("word:single-letter", "a"),
    ]


def test_multi_letter_roman_has_only_its_cardinal_candidate():
    detections = _english_letter_readings("II")

    assert [(detection["type"], detection["value"]) for detection in detections] == [
        ("number:cardinal:roman", NumberValue("2", None)),
    ]


@pytest.mark.parametrize(
    ("multi_surface", "single_surface", "start", "end"),
    [("_MIX", "_I", 1, 4), ("O’MIX", "O’I", 2, 5)],
)
def test_multi_letter_roman_boundary_scope_limit(multi_surface, single_surface, start, end):
    # This pins the accepted scope limit rather than endorsing the boundary asymmetry.
    detections = _english_letter_readings(multi_surface)

    assert [
        (detection["type"], detection["start"], detection["end"], detection["text"])
        for detection in detections
    ] == [("number:cardinal:roman", start, end, "MIX")]
    assert _english_letter_readings(single_surface) == []


@pytest.mark.parametrize("surface", ["xI", "Ix"])
def test_letters_inside_words_have_no_letter_reading_or_cardinal(surface):
    assert _english_letter_readings(surface) == []


@pytest.mark.parametrize("surface", ["I", "a", "A", "O"])
def test_english_one_letter_words_preserve_their_surface(surface):
    detection = recognize.SingleLetterWordDetector("en").detect(surface)[0]

    assert detection["type"] == "word:single-letter"
    assert detection["value"] == surface


@pytest.mark.parametrize("surface", ["i", "o", "M", "II", "xI", "Ix"])
def test_non_words_and_non_isolated_letters_have_no_word_candidate(surface):
    assert recognize.SingleLetterWordDetector("en").detect(surface) == []
