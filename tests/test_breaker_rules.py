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
    status_types = {907: "abbrev", 200: "letter", 100: "number"}
    spans = RuleBreaker(BASE_RULES, status_types).spans("See Fig. 5 now")
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


def test_default_english_word_rules_can_be_recompiled():
    rules = default_rules("word", "en")

    assert isinstance(rules, str)
    assert rules
    assert RuleBreaker(rules).tokens("Hello world") == ["Hello", " ", "world"]


def test_astral_offsets_are_code_points():
    text = "👍 Fig. 5"
    spans = RuleBreaker(BASE_RULES).spans(text)

    assert [(span["text"], span["start"], span["end"]) for span in spans] == [
        ("👍", 0, 1),
        (" ", 1, 2),
        ("Fig.", 2, 6),
        (" ", 6, 7),
        ("5", 7, 8),
    ]
    assert spans[0]["start"] == 0
    assert all(
        current["start"] == previous["end"]
        for previous, current in zip(spans, spans[1:], strict=False)
    )
    assert all(span["start"] < span["end"] for span in spans)
    assert spans[-1]["end"] == len(text)


def test_iter_spans_is_reentrant():
    breaker = RuleBreaker(BASE_RULES, {200: "letter"})
    first = breaker.iter_spans("AB 12")
    second = breaker.iter_spans("CD")

    assert next(first)["text"] == "AB"
    assert next(second)["text"] == "CD"
    assert [span["text"] for span in first] == [" ", "12"]
    assert list(second) == []


def test_unmapped_custom_status_has_no_inferred_type():
    rules = r"!!chain; [\p{Letter}]+ {150}; . {0};"

    span = RuleBreaker(rules).spans("abc")[0]

    assert span["types"] == []
    assert 150 in span["statuses"]


def test_empty_text_has_no_spans():
    assert RuleBreaker(BASE_RULES).spans("") == []


def test_rules_without_status_tags_have_raw_statuses_and_no_types():
    rules = r"!!chain; [\p{Letter}]+; .;"

    spans = RuleBreaker(rules).spans("ab!")

    assert all(span["types"] == [] for span in spans)
    assert all(span["statuses"] for span in spans)


def test_default_rules_rejects_filtered_iterator():
    with pytest.raises(
        BreakerError,
        match=r"No extractable rules.*kind=sentence.*locale=en_US@ss=standard",
    ):
        default_rules("sentence", "en_US@ss=standard")


def test_rule_spans_are_json_round_trip_safe():
    spans = RuleBreaker(BASE_RULES, {907: "abbrev"}).spans("See Fig. 5 now")

    assert json.loads(json.dumps(spans)) == spans
