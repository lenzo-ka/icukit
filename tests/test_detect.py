"""Tests for the typed-span detector seam (icukit.detect).

Offsets are asserted as explicit code-point integers and token content, including across an
astral character, so a UTF-16 leak cannot pass unnoticed.
"""

from __future__ import annotations

import pytest

from icukit import Detection, collation_detect, regex_detect
from icukit.errors import PatternError

FIG_PERIOD = r"(?<=\bFig)\.(?=\s\p{Nd})"  # the abbreviation period, conditioned by context


# ------------------------------------------------------------------ F8: regex_detect


def test_regex_detect_match_is_span_not_context():
    # Bounded lookbehind/lookahead condition the match; only the period is the detection.
    d = regex_detect("See Fig. 5 now", FIG_PERIOD, "abbrev-period")
    assert d == [Detection(text=".", start=7, end=8, type="abbrev-period")]


@pytest.mark.parametrize("text", ["See Fig. now ok", "A trig. 5 thing", "figure 5"])
def test_regex_detect_declines_out_of_context(text):
    assert regex_detect(text, FIG_PERIOD, "abbrev-period") == []


def test_regex_detect_offsets_survive_astral():
    # 👍 is two UTF-16 units; a leak would shift the period off code point 4.
    d = regex_detect("👍Fig. 5", FIG_PERIOD, "abbrev-period")
    assert d == [Detection(text=".", start=4, end=5, type="abbrev-period")]


def test_regex_detect_all_matches_in_order():
    d = regex_detect("Fig. 5 and Fig. 9", FIG_PERIOD, "abbrev-period")
    assert [(x["start"], x["end"]) for x in d] == [(3, 4), (14, 15)]


def test_regex_detect_unbounded_lookbehind_is_refused():
    # ICU rejects unbounded lookbehind at compile: an unhostable rule is refused, not hosted.
    with pytest.raises(PatternError):
        regex_detect("Fig. 5", r"(?<=Fig+)\.", "abbrev-period")


def test_regex_detect_empty_on_no_match():
    assert regex_detect("nothing here", FIG_PERIOD, "abbrev-period") == []


# -------------------------------------------------------------- F9: collation_detect


def test_collation_detect_primary_collapses_case():
    d = collation_detect("fig. Fig. FIG.", "fig.", "abbrev", strength="primary")
    assert [(x["start"], x["end"], x["text"]) for x in d] == [
        (0, 4, "fig."),
        (5, 9, "Fig."),
        (10, 14, "FIG."),
    ]


def test_collation_detect_tertiary_is_case_sensitive():
    d = collation_detect("fig. Fig. FIG.", "fig.", "abbrev", strength="tertiary")
    assert [(x["start"], x["end"]) for x in d] == [(0, 4)]


def test_collation_detect_primary_collapses_accent():
    d = collation_detect("le café ici", "cafe", "term", strength="primary")
    assert d == [Detection(text="café", start=3, end=7, type="term")]


def test_collation_detect_offsets_survive_astral():
    # café begins at code point 1 (after 👍); assert the code-point extent, not UTF-16.
    d = collation_detect("👍café", "cafe", "term", strength="primary")
    assert d == [Detection(text="café", start=1, end=5, type="term")]


def test_collation_detect_empty_on_no_match():
    assert collation_detect("nothing here", "fig.", "abbrev") == []


# ------------------------------------------------------- composition with breaker offsets


def test_detections_share_breaker_offset_convention():
    # Detections use the same code-point offsets as break_* spans, so they compose with
    # segmentation. Here the abbrev-period detection coincides exactly with the period's own
    # word-break token and adds a type that segmentation does not carry.
    from icukit.breaker import break_word_spans

    text = "See Fig. 5 now"
    period = regex_detect(text, FIG_PERIOD, "abbrev-period")[0]
    assert (period["start"], period["end"]) == (7, 8)
    words = break_word_spans(text, "en")
    token = next(w for w in words if (w["start"], w["end"]) == (period["start"], period["end"]))
    assert token["text"] == "." and period["type"] == "abbrev-period"
