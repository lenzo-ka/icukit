"""A word mixing letters and digits reads as its runs, beside any other reading."""

import pytest

from icukit.detectors import detect
from icukit.recognize import (
    AlphanumericRunsDetector,
    AlphanumericRunsValue,
    FlexibleCompactDetector,
)


def _runs(text, locale="en_US"):
    return [
        (d["start"], d["end"], [(c.name, c.text) for c in d["captures"]])
        for d in AlphanumericRunsDetector(locale).detect(text)
    ]


@pytest.mark.parametrize(
    "text, runs",
    [
        ("3D", [("digits", "3"), ("letters", "D")]),
        ("5pm", [("digits", "5"), ("letters", "pm")]),
        ("2Q22", [("digits", "2"), ("letters", "Q"), ("digits", "22")]),
        ("MP3", [("letters", "MP"), ("digits", "3")]),
        ("500cc", [("digits", "500"), ("letters", "cc")]),
        ("v2.0", [("letters", "v"), ("digits", "2"), ("separator", "."), ("digits", "0")]),
    ],
)
def test_a_mixed_word_reads_as_its_runs(text, runs):
    assert _runs(text) == [(0, len(text), runs)]


def test_the_value_mirrors_the_captures_and_the_span_is_the_word():
    detection = AlphanumericRunsDetector("en_US").detect("a 3D printer")[0]

    assert (detection["start"], detection["end"], detection["text"]) == (2, 4, "3D")
    assert detection["type"] == "alnum:runs"
    assert detection["value"] == AlphanumericRunsValue((("digits", "3"), ("letters", "D")))


@pytest.mark.parametrize("text", ["abc", "123", "3.5", "F-16", "C's"])
def test_a_word_without_both_letters_and_digits_has_no_runs_reading(text):
    assert AlphanumericRunsDetector("en_US").detect(text) == []


def test_a_mark_stays_in_the_run_it_extends():
    assert _runs("café5") == [(0, 6, [("letters", "café"), ("digits", "5")])]


def test_a_script_broken_between_letters_has_no_runs_reading():
    assert AlphanumericRunsDetector("th").detect("ราคา100บาท") == []


def test_runs_compete_with_a_reading_of_the_whole_word():
    detections = detect(
        "4K", [FlexibleCompactDetector("en_US", "short"), AlphanumericRunsDetector("en_US")]
    )

    assert {(d["type"], d["start"], d["end"]) for d in detections} == {
        ("number:compact:short", 0, 2),
        ("alnum:runs", 0, 2),
    }
