"""Detector candidates never split an extended grapheme cluster."""

from typing import get_args

import icu
import pytest

from icukit.breaker import break_grapheme_spans
from icukit.detectors import DateDetector, RefusalReason
from icukit.engine import flexible_detectors, generated_detectors

LOCALES = ("en_US", "de_DE", "ja_JP", "ar_EG")
KEYCAP_BASES = "0123456789#*"


def _instant() -> float:
    calendar = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale("en_US@calendar=gregorian")
    )
    calendar.clear()
    calendar.set(2024, 2, 24)
    return calendar.getTime()


def _boundaries(text: str, locale: str) -> frozenset[int]:
    spans = break_grapheme_spans(text, locale)
    span_offsets = (offset for span in spans for offset in (span["start"], span["end"]))
    return frozenset({0, len(text), *span_offsets})


def test_deprecated_mid_grapheme_refusal_reason_remains_public():
    assert "mid-grapheme-endpoint" in get_args(RefusalReason)


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("kind", ("generated", "flexible"))
def test_gangs_decline_mid_grapheme_candidates_and_keep_later_readings(locale, kind):
    keycaps = [
        *(base + "\u20e3" for base in KEYCAP_BASES),
        *(base + "\ufe0f\u20e3" for base in KEYCAP_BASES),
    ]
    continuations = [
        "1\u0301",
        "1\U0001f3fd\u200d\U0001f4bb",
    ]
    flag_adjacent = ["\U0001f1fa\U0001f1f81", "1\U0001f1fa\U0001f1f8"]

    if kind == "generated":
        gang = generated_detectors(locale)
        reader = next(
            detector
            for detector in gang.detectors
            if isinstance(detector, DateDetector) and detector.type == "date:Md"
        )
        ordinary = reader._df.format(_instant())
        expected = (reader.type, ordinary)
    else:
        gang = flexible_detectors(locale, guarded=True)
        ordinary = icu.NumberFormat.createInstance(icu.Locale(locale)).format(1)
        expected = ("number:decimal", ordinary)

    text = " | ".join((*keycaps, *continuations, *flag_adjacent, f"plain {ordinary}"))
    compiled = gang.compile(warm=False)
    detections = compiled.detect(text)
    boundaries = _boundaries(text, locale)

    assert compiled._scan_plans[id(text)].grapheme_boundaries[locale] == boundaries
    assert expected in {(detection["type"], detection["text"]) for detection in detections}
    assert all(
        detection["start"] in boundaries and detection["end"] in boundaries
        for detection in detections
    )
