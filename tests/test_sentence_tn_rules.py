from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from icukit import BreakRuleLoadError, SentenceOverride, load_break_rules

RULES = Path(__file__).parents[1] / "icukit/data/break_rules/en/sentence-tn.json"


def _document() -> dict:
    return json.loads(RULES.read_text(encoding="utf-8"))


def test_all_shipped_rule_witnesses_reach_and_pass_in_order():
    document = _document()
    loaded = load_break_rules(document)
    assert len(document["rules"]) == 200
    assert [rule["id"] for rule in document["rules"]] == [
        f"en.sb.{index:04d}" for index in range(1, 201)
    ]
    assert all(set(rule["receipt"]) == {"n", "n_break"} for rule in document["rules"])
    assert document["training"] == {"k": "1"}
    assert loaded.id == "icukit/en/sentence-tn"


def test_reordering_rules_is_detected_by_authored_witnesses():
    document = _document()
    mutated = deepcopy(document)
    later = mutated["rules"].pop(99)
    mutated["rules"].insert(0, later)
    with pytest.raises(BreakRuleLoadError) as caught:
        load_break_rules(mutated)
    assert "WITNESS_MATCH_FAILED" in caught.value.reason_codes


def test_named_base_reports_measured_rule_ids():
    decision = SentenceOverride(base="en-tn@1").decide("alpha beta word. ). A1234567890")[1]
    assert (decision["layer"], decision["id"], decision["decision"]) == (
        "rules",
        "en.sb.0179",
        "no-break",
    )
