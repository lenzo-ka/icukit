"""No detector starts or ends a reading inside a word, whichever loop it runs.

The detectors are found when the test runs, from every ``*Detector`` class icukit exports,
so a detector added later with its own scanning loop is held to the guard without anyone
remembering to list it here.
"""

import inspect

import pytest

import icukit
from icukit.detectors import _word_interior_offsets

# Words with alphanumerics on both sides of an inner offset, plus the shapes the
# self-looping detectors read ("3D", "1990s", "C's", "II's").
_TEXTS = (
    "2788 29th asdf123@abc 2Q22 1/4th 2016/07/03 ab2,788 v2.0 x5.5% 1,2,3",
    "3D MP3 5pm 10am 1990s '90s 1990's C's Cs II's xI Ix I'm D'Angelo O'MIX",
    "e.g. U.S. Dr. Mon. sun. C's. 1st 21st 1,000th 1º 3/4s 10:30h 5:30 p.m.",
    "café5 abc­123 abc‍123 x_I A-1 we paid $1,234.50 on 12/25/2026",
)


def _is_letter_of_a_dotted_initialism(text, start, end):
    """One letter with a period or a word edge on each side: the "U" and "S" of "U.S.".

    ICU keeps "U.S." one word, since a period between letters joins them, but a speaker
    reads it letter by letter, so a letter reading there is a real path, not a fragment.
    """
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    return end - start == 1 and before in ". " and after in ". "


def _detectors(locale):
    for name in sorted(dir(icukit)):
        cls = getattr(icukit, name)
        if not (inspect.isclass(cls) and name.endswith("Detector")):
            continue
        try:
            yield name, cls(locale)
        except TypeError:
            continue  # needs arguments beyond the locale (a skeleton, a currency, a unit)


def _crossings(name, detector, locale):
    """Readings of ``detector`` that start or end inside a word, beyond the one exception."""
    found = []
    for text in _TEXTS:
        interior = _word_interior_offsets(text, locale)
        for detection in detector.detect(text):
            start, end = detection["start"], detection["end"]
            if detector.group in {"letter", "word"} and _is_letter_of_a_dotted_initialism(
                text, start, end
            ):
                continue
            if start in interior or end in interior:
                found.append((name, detection["text"]))
    return found


@pytest.mark.parametrize("locale", ["en_US"])
def test_no_detector_reads_across_a_word_interior(locale):
    checked = []
    for name, detector in _detectors(locale):
        checked.append(name)
        assert _crossings(name, detector, locale) == []

    # The self-looping detectors are among those checked, so the guard is not vacuous.
    assert {
        "AlphanumericRunsDetector",
        "PluralNumeralDetector",
        "LetterNameDetector",
        "SingleLetterWordDetector",
        "AbbreviationDetector",
    } <= set(checked)


def test_the_check_catches_a_detector_that_reads_a_fragment():
    class FragmentDetector:
        group = "number"

        def detect(self, text):
            if "2788" not in text:
                return []
            start = text.index("2788") + 1
            return [{"start": start, "end": start + 3, "text": text[start : start + 3]}]

    # A positive control: "788" inside "2788" is exactly what the check exists to refuse.
    assert ("FragmentDetector", "788") in _crossings(
        "FragmentDetector", FragmentDetector(), "en_US"
    )
