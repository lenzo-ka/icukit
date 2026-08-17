"""Tests for custom rule-based text segmentation."""

import json

import pytest

from icukit import BreakerError, RuleBreaker, default_rules

BASE_RULES = r"""
!!chain;
$Letter = [\p{Letter}];
$Digit = [\p{Number}];
$Space = [\p{White_Space}];
[Ff][Ii][Gg] \. {907};
$Letter+ {200};
$Digit+ {100};
$Space+ {0};
. {0};
"""


def test_custom_abbreviation_status_and_types():
    spans = RuleBreaker(BASE_RULES, {907: "abbrev"}).spans("See Fig. 5 now")
    by_text = {span["text"]: span for span in spans}

    assert "abbrev" in by_text["Fig."]["types"]
    assert 907 in by_text["Fig."]["statuses"]
    assert "number" in by_text["5"]["types"]
    assert "letter" in by_text["See"]["types"]
    assert "letter" in by_text["now"]["types"]


def test_right_context_controls_abbreviation_match():
    rules = r"""
!!chain;
$Letter = [\p{Letter}];
$Digit = [\p{Number}];
$Space = [\p{White_Space}];
[Ff][Ii][Gg] \. / $Space $Digit {907};
$Letter+ {200};
$Digit+ {100};
$Space+ {0};
. {0};
"""
    breaker = RuleBreaker(rules, {907: "abbrev"})

    assert "Fig." in breaker.tokens("Fig. 5 now")
    assert breaker.tokens("Fig. now ok")[:2] == ["Fig", "."]


def test_invalid_rules_raise_breaker_error():
    with pytest.raises(BreakerError, match="Invalid break rules"):
        RuleBreaker("!!chain; [unterminated")


def test_default_word_rules_can_be_recompiled():
    rules = default_rules("word")

    assert isinstance(rules, str)
    assert rules
    assert RuleBreaker(rules).tokens("Hello world") == ["Hello", " ", "world"]


def test_astral_offsets_are_code_points():
    text = "👍 Fig. 5"
    spans = RuleBreaker(BASE_RULES).spans(text)

    assert all(text[span["start"] : span["end"]] == span["text"] for span in spans)
    emoji = next(span for span in spans if span["text"] == "👍")
    assert (emoji["start"], emoji["end"]) == (0, 1)


def test_rule_spans_are_json_round_trip_safe():
    spans = RuleBreaker(BASE_RULES, {907: "abbrev"}).spans("See Fig. 5 now")

    assert json.loads(json.dumps(spans)) == spans
