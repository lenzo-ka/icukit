"""Discriminating end-to-end tests for the H2 v1 exception layer."""

from copy import deepcopy

import pytest

from icukit import ExceptionConflictError, ExceptionLoadError, load_exception_inventory
from icukit.breaker import BreakSpan
from icukit.detect import Detection
from icukit.exceptions import ExceptionInventory, ExceptionRule, merge_retypes


def _rule(**changes) -> ExceptionRule:
    rule: ExceptionRule = {
        "id": "no-word",
        "locale": "en",
        "level": "word",
        "effect": "retype",
        "type": "exception:abbreviation",
        "surface": "No",
        "variant": "collation",
        "strength": "primary",
        "conditions": [
            {
                "id": "period",
                "kind": "unicode_set",
                "direction": "right",
                "set": "[.]",
                "skip": {"kind": "none", "max": 0},
            }
        ],
        "unconditionality": "conditional",
        "provenance": {"source": "authored"},
        "witnesses": {
            "positive": "👍No. Next",
            "near_miss": "Casino. Next",
            "condition_negatives": ["No! Next"],
        },
    }
    rule.update(changes)
    return rule


def _inventory(*rules: ExceptionRule) -> ExceptionInventory:
    return {
        "schema_version": 1,
        "corpus": "tests",
        "named_lists": {},
        "rules": list(rules),
    }


def test_retype_owns_one_base_span_with_codepoint_offsets():
    layer = load_exception_inventory(_inventory(_rule()))

    spans = layer.break_spans("👍No. Next", "word", "en-US")

    assert [(s["text"], s["start"], s["end"], s["types"]) for s in spans] == [
        ("👍", 0, 1, ["other"]),
        ("No", 1, 3, ["exception:abbreviation"]),
        (".", 3, 4, ["punctuation"]),
        (" ", 4, 5, ["whitespace"]),
        ("Next", 5, 9, ["letter"]),
    ]


def test_real_no_casino_near_miss_is_mechanically_non_vacuous():
    layer = load_exception_inventory(_inventory(_rule()))

    casino = layer.break_spans("Casino. Next", "word", "en")

    assert casino[0]["text"] == "Casino"
    assert casino[0]["types"] == ["letter"]


def test_suppress_is_native_rbbi_and_prevents_word_break():
    rule = _rule(
        id="fig-suppress",
        effect="suppress",
        type=None,
        surface="Fig.",
        variant="exact",
        conditions=[],
        unconditionality="empirical",
        witnesses={
            "positive": "See Fig. 5",
            "near_miss": "ConFig. 5",
            "condition_negatives": [],
        },
    )
    rule.pop("strength")
    layer = load_exception_inventory(_inventory(rule))

    spans = layer.break_spans("See Fig. 5", "word", "en")

    assert [(s["text"], s["start"], s["end"]) for s in spans] == [
        ("See", 0, 3),
        (" ", 3, 4),
        ("Fig.", 4, 8),
        (" ", 8, 9),
        ("5", 9, 10),
    ]


def test_combining_cluster_may_not_be_bisected():
    text = "e\N{COMBINING ACUTE ACCENT}"
    base: list[BreakSpan] = [
        {"text": text, "start": 0, "end": 2, "types": ["letter"], "statuses": [200]}
    ]
    detection = Detection(text="e", start=0, end=1, type="exception:test")

    with pytest.raises(ExceptionConflictError, match="DETECTION_NOT_GRAPHEME_ALIGNED"):
        merge_retypes(text, base, [detection])


def test_transactional_loader_collects_all_refusals():
    bad_left = _rule(
        id="bad-left",
        effect="suppress",
        type=None,
        surface="Fig.",
        conditions=[
            {
                "id": "left",
                "kind": "unicode_set",
                "direction": "left",
                "set": "[A]",
                "skip": {"kind": "whitespace", "max": 1},
            }
        ],
        witnesses={
            "positive": "A Fig.",
            "near_miss": "Configure Fig.",
            "condition_negatives": ["B Fig."],
        },
    )
    bad_unbounded = _rule(
        id="bad-unbounded",
        effect="retype",
        conditions=[
            {
                "id": "left",
                "kind": "unicode_set",
                "direction": "left",
                "set": "[A]",
                "skip": {"kind": "whitespace", "max": None},
            }
        ],
        witnesses={
            "positive": "A No",
            "near_miss": "Casino",
            "condition_negatives": ["B No"],
        },
    )
    bad_type = _rule(id="bad-type", type="not-local-grammar")

    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(bad_left, bad_unbounded, bad_type))

    # bounded left context on a suppress rule refuses because RBBI has NO left context,
    # not because it is unbounded -- the two reasons are distinct codes.
    assert "UNHOSTABLE_SUPPRESS_LEFT" in caught.value.reason_codes
    assert "UNHOSTABLE_UNBOUNDED_LEFT" in caught.value.reason_codes
    assert "INVALID_TYPE" in caught.value.reason_codes


def test_nonseparable_unicode_conditions_refuse():
    rule = deepcopy(_rule())
    rule["conditions"].append(
        {
            "id": "punctuation",
            "kind": "unicode_set",
            "direction": "right",
            "set": "[[:P:]]",
            "skip": {"kind": "none", "max": 0},
        }
    )
    rule["witnesses"]["condition_negatives"].append("No A")

    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(rule))

    assert "NON_SEPARABLE_CONDITIONS" in caught.value.reason_codes
