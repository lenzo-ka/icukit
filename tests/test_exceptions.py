"""Discriminating end-to-end tests for the H2 v1 exception layer."""

from copy import deepcopy

import pytest

from icukit import (
    ExceptionConflictError,
    ExceptionLoadError,
    compose_inventories,
    example_exception_inventory,
    load_exception_inventory,
)
from icukit.breaker import BreakSpan, break_word_spans
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


def test_named_list_condition_retypes_only_adjacent_listed_word():
    rule = _rule(
        id="title-before-surname",
        type="exception:title",
        surface="Dr",
        variant="exact",
        conditions=[
            {
                "id": "surname",
                "kind": "named_list",
                "direction": "right",
                "list": "surnames",
                "skip": {"kind": "whitespace", "max": 1},
            }
        ],
        witnesses={
            "positive": "Dr Smith",
            "near_miss": "Drone Smith",
            "condition_negatives": ["Dr who"],
        },
    )
    rule.pop("strength")
    inventory = _inventory(rule)
    inventory["named_lists"] = {"surnames": ["Smith", "Jones"]}
    layer = load_exception_inventory(inventory)

    positive = layer.break_spans("Dr Smith", "word", "en")
    negative = layer.break_spans("Dr who", "word", "en")

    assert [(s["text"], s["start"], s["end"], s["types"]) for s in positive] == [
        ("Dr", 0, 2, ["exception:title"]),
        (" ", 2, 3, ["whitespace"]),
        ("Smith", 3, 8, ["letter"]),
    ]
    assert [(s["text"], s["start"], s["end"], s["types"]) for s in negative] == [
        ("Dr", 0, 2, ["letter"]),
        (" ", 2, 3, ["whitespace"]),
        ("who", 3, 6, ["letter"]),
    ]


def test_collation_primary_strength_retypes_case_folded_surface():
    rule = _rule(
        id="lowercase-no",
        type="exception:abbr",
        surface="no",
        witnesses={
            "positive": "no. Next",
            "near_miss": "casino. Next",
            "condition_negatives": ["no! Next"],
        },
    )
    layer = load_exception_inventory(_inventory(rule))

    spans = layer.break_spans("No. Next", "word", "en")

    assert [(s["text"], s["start"], s["end"], s["types"]) for s in spans] == [
        ("No", 0, 2, ["exception:abbr"]),
        (".", 2, 3, ["punctuation"]),
        (" ", 3, 4, ["whitespace"]),
        ("Next", 4, 8, ["letter"]),
    ]


def test_unhostable_needs_replace_refuses_all_three_paths():
    collation_suppression = _rule(
        id="collation-suppression",
        effect="suppress",
        type=None,
        conditions=[],
        unconditionality="empirical",
    )
    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(collation_suppression))
    assert "UNHOSTABLE_NEEDS_REPLACE" in caught.value.reason_codes

    named_list_suppression = _rule(
        id="named-list-suppression",
        effect="suppress",
        type=None,
        surface="Dr",
        variant="exact",
        conditions=[
            {
                "id": "surname",
                "kind": "named_list",
                "direction": "right",
                "list": "surnames",
                "skip": {"kind": "whitespace", "max": 1},
            }
        ],
        witnesses={
            "positive": "Dr Smith",
            "near_miss": "Drone Smith",
            "condition_negatives": ["Dr who"],
        },
    )
    named_list_suppression.pop("strength")
    inventory = _inventory(named_list_suppression)
    inventory["named_lists"] = {"surnames": ["Smith", "Jones"]}
    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(inventory)
    assert "UNHOSTABLE_NEEDS_REPLACE" in caught.value.reason_codes

    base: list[BreakSpan] = [
        {"text": "a", "start": 0, "end": 1, "types": ["letter"], "statuses": [200]},
        {"text": "b", "start": 1, "end": 2, "types": ["letter"], "statuses": [200]},
    ]
    detection = Detection(text="ab", start=0, end=2, type="exception:x")
    with pytest.raises(ExceptionConflictError, match="UNHOSTABLE_NEEDS_REPLACE"):
        merge_retypes("ab", base, [detection])


def test_witness_gate_refuses_broken_witnesses():
    positive_failed = _rule(
        id="positive-failed",
        witnesses={
            "positive": "nothing here",
            "near_miss": "Casino. Next",
            "condition_negatives": ["No! Next"],
        },
    )
    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(positive_failed))
    assert "WITNESS_POSITIVE_FAILED" in caught.value.reason_codes

    near_miss_failed = _rule(
        id="near-miss-failed",
        witnesses={
            "positive": "No. Next",
            "near_miss": "No. Again",
            "condition_negatives": ["No! Next"],
        },
    )
    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(near_miss_failed))
    assert "WITNESS_NEAR_MISS_FAILED" in caught.value.reason_codes

    near_miss_vacuous = _rule(
        id="near-miss-vacuous",
        witnesses={
            "positive": "No. Next",
            "near_miss": "absent here",
            "condition_negatives": ["No! Next"],
        },
    )
    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(near_miss_vacuous))
    assert "WITNESS_NEAR_MISS_VACUOUS" in caught.value.reason_codes


def test_collation_condition_negative_requires_literal_surface_case():
    rule = _rule(
        id="literal-case-negative",
        surface="no",
        witnesses={
            "positive": "no. Next",
            "near_miss": "casino. Next",
            "condition_negatives": ["No! Next"],
        },
    )

    # The v1 witness harness uses exact find for collation surfaces.
    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(rule))

    assert "VACUOUS_CONDITION_NEGATIVE" in caught.value.reason_codes


def _suppression(rule_id: str, surface: str) -> ExceptionRule:
    rule = _rule(
        id=rule_id,
        effect="suppress",
        type=None,
        surface=surface,
        variant="exact",
        conditions=[],
        unconditionality="empirical",
        witnesses={
            "positive": f"See {surface} 5",
            "near_miss": f"Con{surface} 5",
            "condition_negatives": [],
        },
    )
    rule.pop("strength")
    return rule


def test_compose_adds_rules_from_an_overlay():
    composed = compose_inventories(
        [_inventory(_rule()), _inventory(_suppression("figure", "Fig."))]
    )

    spans = composed.break_spans("No. See Fig. 5", "word", "en")

    assert spans[0]["types"] == ["exception:abbreviation"]
    assert any(span["text"] == "Fig." for span in spans)
    assert composed.corpus == "tests + tests"


def test_compose_disables_a_rule_and_refuses_an_unknown_id():
    base = _inventory(_suppression("figure", "Fig."))
    composed = compose_inventories([base], disable=["figure"])

    assert composed.break_spans("See Fig. 5", "word", "en") == break_word_spans("See Fig. 5", "en")
    with pytest.raises(ExceptionLoadError) as caught:
        compose_inventories([base], disable=["missing"])
    assert "UNKNOWN_DISABLED_ID" in caught.value.reason_codes


def test_compose_later_rule_with_same_id_wins():
    first = _rule(id="shared", type="exception:first")
    second = _rule(id="shared", type="exception:second")

    spans = compose_inventories([_inventory(first), _inventory(second)]).break_spans(
        "No. Next", "word", "en"
    )

    assert spans[0]["types"] == ["exception:second"]


def test_compose_assigns_distinct_suppression_statuses():
    composed = compose_inventories(
        [
            _inventory(_suppression("figure", "Fig.")),
            _inventory(_suppression("equation", "Eq.")),
        ]
    )

    spans = composed.break_spans("Fig. 5 Eq. 6", "word", "en")
    generated = [
        next(status for status in span["statuses"] if 1000 <= status < 2000)
        for span in spans
        if span["text"] in {"Fig.", "Eq."}
    ]
    assert len(generated) == 2
    assert len(set(generated)) == 2


def test_compose_is_transactional_when_a_witness_fails():
    bad = _rule(
        id="bad",
        witnesses={
            "positive": "absent",
            "near_miss": "Casino. Next",
            "condition_negatives": ["No! Next"],
        },
    )

    with pytest.raises(ExceptionLoadError) as caught:
        compose_inventories([_inventory(_rule()), _inventory(bad)])

    assert "WITNESS_POSITIVE_FAILED" in caught.value.reason_codes
    assert {refusal.rule_id for refusal in caught.value.refusals} == {"bad"}


def test_composition_is_inert_until_explicitly_applied():
    text = "See Fig. 5"
    vanilla = break_word_spans(text, "en")
    compose_inventories([_inventory(_suppression("figure", "Fig."))])

    assert break_word_spans(text, "en") == vanilla


def test_example_inventory_is_electable_and_passes_its_witnesses():
    text = "See Fig. 5"
    vanilla = break_word_spans(text, "en")
    inventory = example_exception_inventory()

    assert inventory["corpus"] == "examples"
    assert break_word_spans(text, "en") == vanilla
    loaded = compose_inventories([inventory])
    assert any(span["text"] == "Fig." for span in loaded.break_spans(text, "word", "en"))
