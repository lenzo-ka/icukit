"""Whole-text sentence-candidate override tests with authored witnesses."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import icukit.sentence_override as sentence_override_module
from icukit import (
    TOKEN_PROFILE,
    AbbreviationSentenceBreaker,
    Breaker,
    BreakRuleLoadError,
    SentenceOverride,
    break_rule_identity,
    compose_inventories,
    load_break_rules,
    load_exception_inventory,
    tokens,
)


def _rule(
    rule_id="test.mr",
    *,
    effect="no-break",
    lookahead=1,
    when=None,
    match=None,
    no_match=None,
):
    return {
        "id": rule_id,
        "effect": effect,
        "lookahead": lookahead,
        "when": when
        or [
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": 1, "f": "general_category.first", "in": ["Uppercase_Letter"]},
        ],
        "receipt": {"n": 2, "n_break": 1},
        "witnesses": {
            "match": match or ["Mr. Smith arrived."],
            "no_match": no_match or ["Hello. Smith arrived."],
        },
    }


def _rules(*rules, locale="en_US", inventories=(), set_id="tests/rules"):
    return {
        "schema_version": 1,
        "kind": "break-rules",
        "id": set_id,
        "locale": locale.split("_", 1)[0],
        "status": "experimental",
        "features": "icukit.features@1",
        "identity": break_rule_identity(locale, inventories=inventories),
        "provenance": {"source": "authored tests"},
        "rules": list(rules),
    }


def _loaded(*rules, locale="en_US", inventories=(), set_id="tests/rules"):
    return load_break_rules(
        _rules(*rules, locale=locale, inventories=inventories, set_id=set_id),
        locale=locale,
        inventories=inventories,
    )


def _suppression(rule_id, surface, levels):
    return {
        "id": rule_id,
        "locale": "en",
        "level": levels,
        "effect": "suppress",
        "type": None,
        "surface": surface,
        "variant": "exact",
        "conditions": [],
        "unconditionality": "empirical",
        "provenance": {"source": "authored tests"},
        "witnesses": {
            "positive": f"I met {surface} Smith today. ",
            "near_miss": f"I met Some{surface} Smith today. ",
            "condition_negatives": [],
        },
    }


def _inventory(rule_id="doctor", levels=("word", "sentence")):
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "authored tests",
            "named_lists": {},
            "rules": [_suppression(rule_id, "Dr.", list(levels))],
        }
    )


def test_existing_icu_and_uli_characterization():
    text = "Mr. Smith went to the U.S. Then he left. I saw Dr. No. It was 3 p.m. today."
    plain = Breaker("en_US", base="none").break_sentence_spans(text)
    uli = Breaker("en_US@ss=standard", base="none").break_sentence_spans(text)
    assert [span["end"] for span in plain] == [4, 27, 41, 51, 55, 75]
    assert [span["end"] for span in uli] == [27, 41, 51, 55, 75]

    default = SentenceOverride("en_US@calendar=gregorian;ss=standard")
    assert default.locale == "en_US@calendar=gregorian"
    assert default.spans(text) == SentenceOverride("en_US@calendar=gregorian").spans(text)
    assert Breaker("en_US@ss=standard").break_sentence_spans(text) == SentenceOverride(
        "en_US"
    ).spans(text)

    message = "candidates are raw ICU sentence breaks without ULI"
    with pytest.raises(ValueError, match=message):
        break_rule_identity("en_US@ss=standard")
    with pytest.raises(ValueError, match=message):
        load_break_rules(_rules(_rule()), locale="en_US@ss=standard")


def test_compose_inventory_last_wins_and_disable_characterization():
    first = {
        "schema_version": 1,
        "corpus": "first",
        "named_lists": {},
        "rules": [_suppression("same", "Dr.", "word")],
    }
    second = deepcopy(first)
    second["corpus"] = "second"
    second["rules"] = [_suppression("same", "Dr.", ["word", "sentence"])]
    assert compose_inventories([first, second])._rules[0].levels == ("word", "sentence")
    assert compose_inventories([first], disable=["same"])._rules == ()


def test_abbreviation_sentence_breaker_fixed_authored_output_unchanged():
    text = "Dr. Smith arrived. He waved."
    assert [span["text"] for span in AbbreviationSentenceBreaker("en").spans(text)] == [
        "Dr. Smith arrived. ",
        "He waved.",
    ]


def test_base_none_is_exactly_raw_icu_with_attribution():
    text = "Mr. Smith arrived. Next."
    expected = [span["end"] for span in Breaker("en_US", base="none").break_sentence_spans(text)]
    override = SentenceOverride(base="none")
    decisions = override.decide(text)
    assert [item["offset"] for item in decisions] == expected
    assert all(
        item["layer"] == "icu"
        and item["id"] is None
        and item["decision"] == "break"
        and item["tokens_read"] == 0
        for item in decisions
    )
    assert override.spans(text) == Breaker("en_US", base="none").break_sentence_spans(text)


def test_protected_token_suppresses_inside_candidate_but_hint_needs_rule():
    text = "Mr. Smith arrived."
    token_span = {"start": 0, "end": 9, "type": "name", "scope": "token"}
    hint_span = {**token_span, "scope": "hint"}
    token = SentenceOverride(base="none").decide(text, protected=[token_span])[0]
    hint = SentenceOverride(base="none").decide(text, protected=[hint_span])[0]
    assert (token["offset"], token["end"], token["decision"], token["layer"]) == (
        4,
        9,
        "no-break",
        "token",
    )
    assert (hint["decision"], hint["layer"]) == ("break", "icu")

    rule = _rule(
        "test.hint",
        lookahead=0,
        when=[{"at": "protected", "f": "protected.type", "in": ["name"]}],
        match=[
            {
                "text": "Mr. Smith arrived.",
                "protected": [{"start": 0, "end": 9, "type": "name", "scope": "hint"}],
            }
        ],
        no_match=["Hello. Smith arrived."],
    )
    before = _loaded(rule)
    decision = SentenceOverride(base="none", before=[before]).decide(text, protected=[hint_span])[0]
    assert (decision["decision"], decision["layer"], decision["id"]) == (
        "no-break",
        "before",
        "test.hint",
    )


def test_before_forces_after_overrides_and_core_first_match_wins():
    before = _loaded(_rule("before", effect="no-break"), set_id="tests/before")
    core_first = _rule("core-first", effect="no-break")
    core_second = _rule(
        "core-second",
        effect="break",
        when=[{"at": 1, "f": "general_category.first", "in": ["Uppercase_Letter"]}],
        match=["Prof. John arrived."],
        no_match=["Hello. there."],
    )
    base = _loaded(
        core_first,
        core_second,
        set_id="tests/base",
    )
    after = _loaded(_rule("after", effect="break"), set_id="tests/after")
    before_decision = SentenceOverride(before=[before], base=base, after=[after]).decide(
        "Mr. Smith arrived."
    )
    assert (
        before_decision[0]["decision"],
        before_decision[0]["layer"],
        before_decision[0]["id"],
    ) == ("no-break", "before", "before")
    decision = SentenceOverride(base=base, after=[after]).decide("Mr. Smith arrived.")[0]
    assert (decision["decision"], decision["layer"], decision["id"]) == (
        "break",
        "after",
        "after",
    )
    core = SentenceOverride(base=base).decide("Mr. Smith arrived.")[0]
    assert (core["decision"], core["id"]) == ("no-break", "core-first")
    assert [
        item["offset"] for item in SentenceOverride(base=base).decide("Mr. Smith arrived.")
    ] == [
        4,
        18,
    ]


def test_loader_bounds_beyond_and_real_code_point():
    too_short = _rules(
        _rule(
            lookahead=0,
            when=[{"at": "c+1", "f": "sentence_break", "in": ["Upper"]}],
        )
    )
    with pytest.raises(BreakRuleLoadError) as caught:
        load_break_rules(too_short)
    assert "LOOKAHEAD_TOO_SMALL" in caught.value.reason_codes

    beyond = _rule(
        "test.beyond",
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": "c+7", "f": "sentence_break", "in": ["<BEYOND>"]},
        ],
        match=["Mr. A B C D E"],
        no_match=["Mr. Alexander"],
    )
    loaded = _loaded(beyond)
    assert (
        SentenceOverride(base="none", before=[loaded]).decide("Mr. A B C D E")[0]["id"]
        == "test.beyond"
    )
    assert (
        SentenceOverride(base="none", before=[loaded]).decide("Mr. Alexander")[0]["layer"] == "icu"
    )

    gap = _rule(
        "test.gap",
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": "c+2", "f": "text", "in": [" "]},
        ],
        match=["Mr. A B"],
        no_match=["Mr. AB B"],
    )
    in_gap = SentenceOverride(base="none", before=[_loaded(gap)]).decide("Mr. A B")[0]
    assert (in_gap["id"], in_gap["tokens_read"]) == ("test.gap", 1)

    end_rule = _rule(
        "test.end",
        when=[
            {"at": "run-1", "f": "text", "in": ["Done."]},
            {"at": "c+1", "f": "sentence_break", "in": ["<EOS>"]},
        ],
        match=["Done."],
        no_match=["Done. Next."],
    )
    at_end = SentenceOverride(base="none", before=[_loaded(end_rule)]).decide("Done.")[-1]
    assert (at_end["id"], at_end["tokens_read"]) == ("test.end", 1)


def test_run_minus_one_stops_at_raw_candidate_inside_unspaced_run():
    text = 'He said."Then left.'
    truncated = _rule(
        "test.truncated-run",
        lookahead=0,
        when=[{"at": "run-1", "f": "text", "in": ['said."']}],
        match=[{"text": text, "offset": 9, "decision": "no-break"}],
        no_match=['He asked."Then left.'],
    )
    decision = SentenceOverride(base="none", before=[_loaded(truncated)]).decide(text)[0]
    assert (decision["offset"], decision["id"], decision["tokens_read"]) == (
        9,
        "test.truncated-run",
        0,
    )

    reads_past_cut = deepcopy(truncated)
    reads_past_cut["when"][0]["in"] = ['said."Then']
    with pytest.raises(BreakRuleLoadError) as caught:
        _loaded(reads_past_cut)
    assert "WITNESS_MATCH_FAILED" in caught.value.reason_codes


def test_run_minus_one_derives_every_feature_from_the_truncated_run():
    rule = _rule(
        "test.run-features",
        lookahead=0,
        when=[
            {"at": "run-1", "f": "text", "in": ["Mr."]},
            {"at": "run-1", "f": "lower", "in": ["mr."]},
            {"at": "run-1", "f": "len", "in": [3]},
            {"at": "run-1", "f": "shape.coarse", "in": ["A."]},
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {
                "at": "run-1",
                "f": "general_category.first",
                "in": ["Uppercase_Letter"],
            },
            {
                "at": "run-1",
                "f": "general_category.last",
                "in": ["Other_Punctuation"],
            },
            {"at": "run-1", "f": "sentence_break.first", "in": ["Upper"]},
            {"at": "run-1", "f": "word_break.first", "in": ["ALetter"]},
            {"at": "run-1", "f": "script.first", "in": ["Latin"]},
            {"at": "run-1", "f": "ws.before", "in": [False]},
            {"at": "run-1", "f": "run.shape.cased", "in": ["Xx."]},
            {"at": "run-1", "f": "lex", "in": ["none"]},
        ],
        match=[{"text": "Mr. Smith arrived.", "offset": 4, "decision": "no-break"}],
        no_match=["Hello. Smith arrived."],
    )
    decision = SentenceOverride(base="none", before=[_loaded(rule)]).decide("Mr. Smith arrived.")[0]

    assert (decision["offset"], decision["decision"], decision["id"]) == (
        4,
        "no-break",
        "test.run-features",
    )


def test_astral_offsets_and_character_predicates_are_code_point_based():
    text = "😀 Done. Next."
    rule = _rule(
        "test.astral",
        effect="ambiguous",
        when=[
            {"at": "run-1", "f": "text", "in": ["Done."]},
            {"at": "c-2", "f": "text", "in": ["."]},
            {"at": "c+1", "f": "text", "in": ["N"]},
        ],
        match=[{"text": text, "offset": 8, "decision": "ambiguous"}],
        no_match=["😀 Hello. Next."],
    )
    override = SentenceOverride(base="none", before=[_loaded(rule)])
    decisions = override.decide(text)
    assert [(item["offset"], item["end"]) for item in decisions] == [(8, 7), (13, 13)]
    assert decisions[0]["id"] == "test.astral"
    spans = override.spans(text)
    assert [span["text"] for span in spans] == [text]
    assert (spans[0]["start"], spans[0]["end"], spans[0]["codepoint_end"]) == (0, 13, 13)
    assert spans[0]["utf16_end"] == 14
    segmentation = override.segmentations(text)
    assert [span["text"] for span in segmentation["spans"]] == [text]
    assert segmentation["spans"][0]["codepoint_end"] == 13
    assert segmentation["boundaries"][0]["offset"] == 8

    beyond_text = "😀 Mr. A B C D E"
    beyond = _rule(
        "test.astral-beyond",
        when=[
            {"at": "run-1", "f": "text", "in": ["Mr."]},
            {"at": "c+7", "f": "text", "in": ["<BEYOND>"]},
        ],
        match=[{"text": beyond_text, "offset": 6, "decision": "no-break"}],
        no_match=["😀 Mr. Alexander"],
    )
    assert (
        SentenceOverride(base="none", before=[_loaded(beyond)]).decide(beyond_text)[0]["offset"]
        == 6
    )


def test_witnesses_execute_and_rule_order_is_observable():
    shadow = _rule(
        "shadow",
        when=[{"at": "run-1", "f": "shape.cased", "in": ["Xx."]}],
        no_match=["Hello. Smith arrived."],
    )
    target = _rule("target")
    with pytest.raises(BreakRuleLoadError) as caught:
        _loaded(shadow, target)
    assert "WITNESS_MATCH_FAILED" in caught.value.reason_codes


def test_tokens_read_includes_failed_rules_before_the_match():
    probing = _rule(
        "probe-three",
        effect="break",
        lookahead=3,
        when=[{"at": 3, "f": "text", "in": ["Never"]}],
        match=["Mr. Smith arrived Never."],
        no_match=["Hello. Smith arrived today."],
    )
    matching = _rule(
        "match-run",
        lookahead=0,
        when=[{"at": "run-1", "f": "text", "in": ["Mr."]}],
        match=["Mr. Smith arrived today."],
        no_match=["Hello. Smith arrived today."],
    )
    decision = SentenceOverride(base="none", before=[_loaded(probing, matching)]).decide(
        "Mr. Smith arrived today."
    )[0]
    assert (decision["id"], decision["tokens_read"]) == ("match-run", 3)


def test_witness_offset_and_optional_decision_pin_the_authored_result():
    expected = _rule(match=[{"text": "Mr. Smith arrived.", "offset": 4, "decision": "no-break"}])
    _loaded(expected)

    flipped = deepcopy(expected)
    flipped["effect"] = "break"
    with pytest.raises(BreakRuleLoadError) as caught:
        _loaded(flipped)
    assert "WITNESS_MATCH_FAILED" in caught.value.reason_codes

    unpinned = deepcopy(flipped)
    unpinned["witnesses"]["match"] = [{"text": "Mr. Smith arrived.", "offset": 4}]
    assert _loaded(unpinned)._rules[0].effect == "break"

    wrong_offset = deepcopy(expected)
    wrong_offset["witnesses"]["match"][0]["offset"] = 5
    with pytest.raises(BreakRuleLoadError) as caught:
        _loaded(wrong_offset)
    assert "WITNESS_MATCH_FAILED" in caught.value.reason_codes


def test_witness_no_break_rejects_ambiguous_alternatives():
    ambiguous = _rule(
        effect="ambiguous",
        match=[{"text": "Mr. Smith arrived.", "offset": 4, "decision": "no-break"}],
    )
    with pytest.raises(BreakRuleLoadError) as caught:
        _loaded(ambiguous)
    assert "WITNESS_MATCH_FAILED" in caught.value.reason_codes


def test_loaded_rules_snapshot_mutable_input_and_compile_immutable_operands():
    operand = ["Mr."]
    raw = _rules(
        _rule(
            when=[{"at": "run-1", "f": "text", "in": operand}],
            match=[{"text": "Mr. Smith arrived.", "decision": "no-break"}],
            no_match=["Hello. Smith arrived."],
        )
    )
    loaded = load_break_rules(raw)
    override = SentenceOverride(base="none", before=[loaded])
    before = override.decide("Hello. Smith arrived.")
    digest = loaded.digest

    operand.append("Hello.")
    raw["rules"][0]["effect"] = "break"
    raw["provenance"]["source"] = "mutated"

    assert isinstance(loaded._rules[0].when[0].operand, tuple)
    assert loaded.digest == digest
    assert override.decide("Hello. Smith arrived.") == before


def test_loaded_rule_set_is_deeply_immutable_and_cannot_be_relabeled():
    raw = _rules(_rule())
    raw["provenance"]["details"] = {"sources": ["authored"]}
    loaded = load_break_rules(raw)

    with pytest.raises(TypeError):
        loaded.runtime_identity["icu"] = "different"
    with pytest.raises(TypeError):
        loaded.provenance["source"] = "different"
    with pytest.raises(TypeError):
        loaded.provenance["details"]["sources"][0] = "different"
    with pytest.raises(FrozenInstanceError):
        loaded._rules[0].effect = "break"
    with pytest.raises(FrozenInstanceError):
        loaded._rules[0].when[0].operand = ("different",)

    with pytest.raises(BreakRuleLoadError) as caught:
        SentenceOverride("fr_FR", before=[loaded])
    assert "IDENTITY_MISMATCH" in caught.value.reason_codes


def test_sentence_override_rejects_replaced_rules_with_stale_digest():
    loaded = _loaded(_rule())
    altered = replace(loaded, _rules=())

    with pytest.raises(BreakRuleLoadError) as caught:
        SentenceOverride(base=altered)
    assert "DIGEST_MISMATCH" in caught.value.reason_codes


def test_loaded_rule_set_freezes_tuple_provenance_without_digest_drift():
    raw = _rules(_rule())
    raw["provenance"]["details"] = ({"source": "authored"},)
    loaded = load_break_rules(raw)
    digest = loaded.digest

    with pytest.raises(TypeError):
        loaded.provenance["details"][0]["source"] = "replaced"

    assert loaded.digest == digest


def test_witnesses_use_word_inventory_only_as_one_isolated_rule_layer():
    inventory = _inventory()
    word_sensitive = _rule(
        "word-sensitive",
        lookahead=0,
        when=[{"at": "run-1", "f": "text", "in": ["Dr."]}],
        match=[{"text": "Dr. Smith arrived.", "offset": 4, "decision": "no-break"}],
        no_match=["Hello. Smith arrived."],
    )
    loaded = _loaded(word_sensitive, inventories=(inventory,))
    deployed = SentenceOverride(base=loaded, inventories=[inventory]).decide("Dr. Smith arrived.")[
        0
    ]
    assert (deployed["layer"], deployed["id"]) == ("exceptions", "doctor")

    false_match_from_sentence_attribution = _rule(
        "doctor",
        lookahead=0,
        when=[{"at": "run-1", "f": "text", "in": ["Never."]}],
        match=["Dr. Smith arrived."],
        no_match=["Hello. Smith arrived."],
    )
    with pytest.raises(BreakRuleLoadError) as caught:
        _loaded(false_match_from_sentence_attribution, inventories=(inventory,))
    assert "WITNESS_MATCH_FAILED" in caught.value.reason_codes


@pytest.mark.parametrize(
    "field,bad",
    [
        ("schema_version", []),
        ("kind", []),
        ("id", []),
        ("locale", []),
        ("status", []),
        ("features", []),
        ("identity", []),
        ("provenance", []),
        ("rules", {}),
        ("rule.id", []),
        ("effect", []),
        ("lookahead", []),
        ("receipt", {"n": []}),
        ("witnesses", {"match": [[]], "no_match": ["Hello."]}),
        ("at", []),
        ("f", []),
        ("in", ["Xx.", []]),
    ],
)
def test_every_malformed_rule_field_is_a_transactional_refusal(field, bad):
    raw = _rules(_rule())
    if field in raw:
        raw[field] = bad
    elif field == "rule.id":
        raw["rules"][0]["id"] = bad
    elif field in {"effect", "lookahead", "receipt", "witnesses"}:
        raw["rules"][0][field] = bad
    else:
        raw["rules"][0]["when"][0][field] = bad
    with pytest.raises(BreakRuleLoadError):
        load_break_rules(raw)


@pytest.mark.parametrize("source", [[], 3, None])
def test_non_mapping_non_path_rule_sources_refuse(source):
    with pytest.raises(BreakRuleLoadError):
        load_break_rules(source)


def test_authored_witnesses_pin_rule_order():
    specific = _rule("specific")
    fallback = _rule(
        "fallback",
        when=[{"at": 1, "f": "general_category.first", "in": ["Uppercase_Letter"]}],
        match=["Prof. Jones arrived."],
        no_match=["Hello. there."],
    )
    loaded = _loaded(specific, fallback)
    assert [rule.id for rule in loaded._rules] == ["specific", "fallback"]


@pytest.mark.parametrize("field", ["icu", "unicode", "token_profile"])
def test_identity_mismatch_refuses_each_component(field):
    raw = _rules(_rule())
    raw["identity"][field] = "wrong"
    with pytest.raises(BreakRuleLoadError) as caught:
        load_break_rules(raw)
    assert "IDENTITY_MISMATCH" in caught.value.reason_codes


def test_ambiguous_rule_deposits_attributed_open_boundary_and_rebuilds_text():
    ambiguous = _rule(
        "st-open",
        effect="ambiguous",
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": 1, "f": "general_category.first", "in": ["Uppercase_Letter"]},
        ],
        match=["St. John went."],
        no_match=["Street. John went."],
    )
    result = SentenceOverride(base="none", before=[_loaded(ambiguous)]).segmentations(
        "St. John went."
    )
    assert result["boundaries"] == [
        {
            "offset": 4,
            "end": 3,
            "alternatives": ("break", "no-break"),
            "layer": "before",
            "id": "st-open",
        }
    ]
    text = "St. John went."
    no_break_reading = [span["text"] for span in result["spans"]]
    boundary = result["boundaries"][0]
    break_reading = [text[: boundary["offset"]], text[boundary["offset"] :]]
    assert no_break_reading == [text]
    assert break_reading == ["St. ", "John went."]
    assert "".join(no_break_reading) == "".join(break_reading) == text
    plain = SentenceOverride(base="none").segmentations("St. John went.")
    assert plain["spans"] == SentenceOverride(base="none").spans("St. John went.")
    assert plain["boundaries"] == []

    abbreviation = AbbreviationSentenceBreaker("en").segmentations("Go N. Then stop.")
    abbreviation_keys = set(abbreviation.ambiguous_boundaries[0])
    assert set(boundary) == (abbreviation_keys - {"left_surface"}) | {"end", "layer", "id"}


def test_prefix_matches_protected_type_family_only():
    family = _rule(
        "number-family",
        lookahead=0,
        when=[{"at": "protected", "f": "protected.type", "prefix": ["number:"]}],
        match=[
            {
                "text": "Mr. Smith arrived.",
                "protected": [
                    {
                        "start": 0,
                        "end": 9,
                        "type": "number:cardinal",
                        "scope": "hint",
                    }
                ],
            }
        ],
        no_match=["Hello. Smith arrived."],
    )
    override = SentenceOverride(base="none", before=[_loaded(family)])
    number = [{"start": 0, "end": 9, "type": "number:cardinal", "scope": "hint"}]
    date = [{"start": 0, "end": 9, "type": "date:iso", "scope": "hint"}]
    assert override.decide("Mr. Smith arrived.", protected=number)[0]["id"] == "number-family"
    assert override.decide("Mr. Smith arrived.", protected=date)[0]["layer"] == "icu"


@pytest.mark.parametrize(
    "operator,operand,match_text,no_match_text",
    [
        ("not_in", ["Lowercase_Letter"], "Mr. Smith arrived.", "He left! again."),
        ("le", 3, "Mr. Amy arrived.", "Mr. Alexander arrived."),
        ("ge", 5, "Mr. Alice arrived.", "Mr. Amy arrived."),
    ],
)
def test_remaining_flat_predicate_operators(operator, operand, match_text, no_match_text):
    feature = "len" if operator in {"le", "ge"} else "general_category.first"
    predicates = [{"at": 1, "f": feature, operator: operand}]
    if operator == "not_in":
        predicates.append({"at": 1, "f": "text", "not_in": ["<EOS>"]})
    rule = _rule(
        f"test.{operator}",
        when=predicates,
        match=[match_text],
        no_match=[no_match_text],
    )
    override = SentenceOverride(base="none", before=[_loaded(rule)])
    assert override.decide(match_text)[0]["id"] == f"test.{operator}"
    assert override.decide(no_match_text)[0]["layer"] == "icu"


def test_inventory_acts_at_word_and_sentence_levels_once_and_duplicates_refuse():
    inventory = _inventory()
    override = SentenceOverride(base="none", inventories=[inventory])
    decisions = override.decide("I met Dr. Smith today. Next.")
    assert [item["text"] for item in tokens("Dr. Smith", "en_US", inventory=inventory)[:2]] == [
        "Dr.",
        "Smith",
    ]
    claimed = [item for item in decisions if item["id"] == "doctor"]
    assert len(claimed) == 1
    assert (claimed[0]["decision"], claimed[0]["layer"]) == ("no-break", "exceptions")

    other = _inventory()
    with pytest.raises(BreakRuleLoadError) as caught:
        SentenceOverride(base="none", inventories=[inventory, other])
    assert "DUPLICATE_RULE_ID" in caught.value.reason_codes
    with pytest.raises(BreakRuleLoadError):
        SentenceOverride(base="none", inventories=[inventory, inventory])


def test_empty_decide_does_not_validate_unused_protected_spans():
    protected = [{"start": 0, "end": 1, "type": "outside-empty-text"}]
    assert SentenceOverride(base="none").decide("", protected=protected) == []


def test_backward_character_token_lookup_is_linear():
    class CountedTokens(list):
        visits = 0

        def __iter__(self):
            for item in super().__iter__():
                type(self).visits += 1
                yield item

    text = "A!" * 128
    toks = CountedTokens(tokens(text, "en_US"))
    predicate = sentence_override_module._CompiledPredicate("c-1", "text", "in", ("!",))
    rule = sentence_override_module._CompiledBreakRule("c-1", "no-break", 1, (predicate,))
    cache = sentence_override_module._TokenFeatureCache(True)
    for offset in range(2, len(text) + 1, 2):
        sentence_override_module._observed_feature_value(
            predicate, rule, text, offset, toks, (), "en_US", (), True, cache
        )
    assert CountedTokens.visits <= len(toks) * 4


def test_long_run_completion_and_feature_work_is_linear(monkeypatch):
    class CountedText(str):
        slices = 0

        def __getitem__(self, key):
            if isinstance(key, slice):
                type(self).slices += 1
            return super().__getitem__(key)

    text = "A!B!" * 64
    toks = tokens(text, "en_US")
    predicate = sentence_override_module._CompiledPredicate("run-1", "text", "in", ("never",))
    rule = sentence_override_module._CompiledBreakRule("run-1", "no-break", 0, (predicate,))
    cache = sentence_override_module._TokenFeatureCache(True)
    original = sentence_override_module._token_completion_horizon
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(sentence_override_module, "_token_completion_horizon", counted)
    for offset in range(2, len(text) + 1, 2):
        sentence_override_module._observed_feature_value(
            predicate, rule, text, offset, toks, (), "en_US", (), True, cache
        )
    counted_text = CountedText(text)
    for index in range(len(toks)):
        cache.get(toks, index, counted_text)
    assert calls == len(toks)
    assert CountedText.slices == 1


def test_sentence_inventory_claims_reuse_icu_candidates(monkeypatch):
    original = sentence_override_module._raw_break_sentence_spans
    calls = 0

    def counted(text, locale):
        nonlocal calls
        calls += 1
        return original(text, locale)

    monkeypatch.setattr(sentence_override_module, "_raw_break_sentence_spans", counted)
    SentenceOverride(base="none", inventories=[_inventory(levels=("sentence",))]).decide("A!" * 64)
    assert calls == 1


def test_anchored_claim_skips_unneeded_mandatory_line_pass(monkeypatch):
    import icukit.exceptions as exceptions_module

    override = SentenceOverride("en")
    original = exceptions_module.break_line_spans
    calls = 0

    def counted(text, locale):
        nonlocal calls
        calls += 1
        return original(text, locale)

    monkeypatch.setattr(exceptions_module, "break_line_spans", counted)
    override.decide("He met Mr. Smith today. He left.")
    assert calls == 0

    override.decide("He met Mr.\nSmith today.")
    assert calls == 1


def test_sentence_only_inventory_does_not_change_tokenization():
    from icukit.abbreviation_compile import _load_break_exception_inventory
    from icukit.tokens import tokens

    inventory = _load_break_exception_inventory("en")
    assert inventory is not None
    combined = sentence_override_module._combined_inventory(
        (inventory,), levels=frozenset({"word"})
    )
    assert combined is None
    text = "He met Mr. Smith today. He left."
    assert tokens(text, "en", inventory=combined) == tokens(text, "en")


def test_sentence_spans_build_offset_maps_once(monkeypatch):
    import icukit._offsets as offsets_module

    original = offsets_module._build_offset_maps
    calls = 0

    def counted(text):
        nonlocal calls
        calls += 1
        return original(text)

    monkeypatch.setattr(offsets_module, "_build_offset_maps", counted)
    SentenceOverride("en").spans("He met Mr. Smith today. He left.")
    assert calls == 1


def test_anchored_sentence_claims_match_legacy_on_repo_text_and_shipped_lists():
    from icukit.abbreviation_compile import _load_break_exception_inventory
    from icukit.tokens import tokens

    inventories = [
        _load_break_exception_inventory("en"),
        _load_break_exception_inventory("en_US"),
    ]
    text = Path("README.md").read_text(encoding="utf-8") + (
        "\nHe met Mr. Smith today. He left. The U.S. Supreme Court ruled. Markets moved."
    )
    for locale, inventory in zip(("en", "en_US"), inventories, strict=True):
        assert inventory is not None
        base = sentence_override_module._raw_break_sentence_spans(text, locale)
        assert sentence_override_module._inventory_claims(
            inventory, text, locale, base
        ) == sentence_override_module._inventory_claims_legacy(inventory, text, locale, base)
        word_inventory = sentence_override_module._combined_inventory(
            (inventory,), levels=frozenset({"word"})
        )
        assert tokens(text, locale, inventory=inventory) == tokens(
            text, locale, inventory=word_inventory
        )


def test_sentence_claims_reuse_token_run_boundaries_and_text():
    from icukit.abbreviation_compile import _load_break_exception_inventory
    from icukit.tokens import tokens

    inventory = _load_break_exception_inventory("en_US")
    assert inventory is not None
    text = "He met Mr. Smith. She said “go.” Then left."
    base = sentence_override_module._raw_break_sentence_spans(text, "en_US")
    toks = tokens(text, "en_US")
    cache = sentence_override_module._TokenFeatureCache(True)
    run_starts = cache.prime_candidates(toks, base)
    candidate_runs = {}

    expected = sentence_override_module._inventory_claims(inventory, text, "en_US", base)
    actual = sentence_override_module._inventory_claims(
        inventory,
        text,
        "en_US",
        base,
        run_starts=run_starts,
        candidate_runs=candidate_runs,
    )

    assert actual == expected
    assert candidate_runs == {
        base[0]["end"]: "Mr.",
        base[1]["end"]: "Smith.",
        base[2]["end"]: "“go.”",
        base[3]["end"]: "left.",
    }


def test_internal_candidate_exact_rule_routes_to_legacy_matcher():
    from icukit.breaker import _raw_break_sentence_spans
    from icukit.exceptions import (
        ExceptionPolicy,
        _boundary_claims,
        _mandatory_info_supplier,
        _sentence_boundary_claims,
    )

    seed = _inventory(levels=("sentence",))._rules[0]
    rule = replace(seed, id="multi-token", surface="Mr. Smith.")
    text = "He met Mr. Smith.today."
    base = _raw_break_sentence_spans(text, "en")
    arguments = (
        text,
        base,
        [rule],
        "en",
        ExceptionPolicy(),
        _mandatory_info_supplier(text, "en"),
    )

    assert _boundary_claims(*arguments) == {11: ["multi-token"]}
    assert _sentence_boundary_claims(*arguments) == _boundary_claims(*arguments)


def test_sentence_rule_routing_preserves_positions_conditions_and_attribution():
    from icukit.exceptions import (
        ExceptionPolicy,
        _boundary_claims,
        _mandatory_info_supplier,
        _sentence_boundary_claims,
    )

    condition_rule = _suppression("conditional-seed", "Dr.", ["sentence"])
    condition_rule["conditions"] = [
        {
            "id": "next-z",
            "kind": "unicode_set",
            "direction": "right",
            "set": "[Z]",
            "skip": {"kind": "whitespace", "max": 1},
        }
    ]
    condition_rule["unconditionality"] = "conditional"
    condition_rule["witnesses"] = {
        "positive": "Dr. Z",
        "near_miss": "SomeDr. Z",
        "condition_negatives": ["Dr. X"],
    }
    condition = (
        load_exception_inventory(
            {
                "schema_version": 1,
                "corpus": "condition seed",
                "named_lists": {},
                "rules": [condition_rule],
            }
        )
        ._rules[0]
        .conditions
    )
    seed = _inventory(levels=("sentence",))._rules[0]
    rules = [
        replace(seed, id="overlap", surface="Smith."),
        replace(seed, id="multi", surface="Mr. Smith."),
        replace(seed, id="multi-conditional", surface="Mr. Smith.", conditions=condition),
        replace(seed, id="at-end", surface="Capt."),
        replace(seed, id="after", surface="Dr."),
    ]
    text = "Before. Mr. Smith. Z Capt. Dr. Next."
    multi_start = text.index("Mr.")
    candidate_ends = sorted(
        {
            multi_start,
            multi_start + len("Mr. "),
            text.index("Capt.") + len("Capt."),
            text.index("Dr.") + len("Dr. "),
            len(text),
        }
    )
    base = [{"end": end} for end in candidate_ends]
    arguments = (
        text,
        base,
        rules,
        "en",
        ExceptionPolicy(),
        _mandatory_info_supplier(text, "en"),
    )

    legacy = _boundary_claims(*arguments)
    anchored = _sentence_boundary_claims(*arguments)

    assert anchored == legacy
    assert anchored[multi_start + len("Mr. ")] == ["multi", "multi-conditional"]
    assert anchored[text.index("Capt.") + len("Capt.")] == ["at-end"]
    assert anchored[text.index("Dr.") + len("Dr. ")] == ["after"]


def test_sentence_rule_index_cache_is_bounded():
    from icukit.exceptions import _sentence_rule_index

    seed = _inventory(levels=("sentence",))._rules[0]
    _sentence_rule_index.cache_clear()
    try:
        for index in range(256):
            rule = replace(seed, id=f"synthetic:{index}", surface=f"X{index}.")
            _sentence_rule_index((rule,), "en")
        assert _sentence_rule_index.cache_info().maxsize == 128
        assert _sentence_rule_index.cache_info().currsize == 128
    finally:
        _sentence_rule_index.cache_clear()


def test_collation_fallback_matches_legacy_with_a_different_surface():
    from icukit.breaker import _raw_break_sentence_spans
    from icukit.exceptions import (
        ExceptionPolicy,
        _boundary_claims,
        _mandatory_info_supplier,
        _sentence_boundary_claims,
    )

    seed = _inventory(levels=("sentence",))._rules[0]
    rule = replace(
        seed,
        id="street",
        locale="de",
        surface="Straße.",
        variant="collation",
        strength="primary",
    )
    text = "Er wohnt in STRASSE. Weiter."
    base = _raw_break_sentence_spans(text, "de")
    arguments = (
        text,
        base,
        [rule],
        "de",
        ExceptionPolicy(),
        _mandatory_info_supplier(text, "de"),
    )

    legacy = _boundary_claims(*arguments)
    assert legacy == {21: ["street"]}
    assert _sentence_boundary_claims(*arguments) == legacy


def test_anchored_sentence_matching_work_is_independent_of_list_size():
    from dataclasses import replace as replace_dataclass

    from icukit.abbreviation_compile import _load_break_exception_inventory
    from icukit.breaker import _raw_break_sentence_spans
    from icukit.exceptions import (
        ExceptionPolicy,
        _mandatory_info_supplier,
        _sentence_boundary_claims,
    )

    inventory = _load_break_exception_inventory("en")
    assert inventory is not None
    shipped = list(inventory._rules)
    synthetic = shipped + [
        replace_dataclass(rule, id=f"synthetic:{copy}:{rule.id}", surface=f"X{copy}{rule.surface}")
        for copy in range(1, 10)
        for rule in shipped
    ]
    assert len(synthetic) == len(shipped) * 10

    text = "He met Mr. Smith today. He left."
    base = _raw_break_sentence_spans(text, "en")
    small_stats: dict[str, int] = {}
    large_stats: dict[str, int] = {}
    for rules, stats in ((shipped, small_stats), (synthetic, large_stats)):
        _sentence_boundary_claims(
            text,
            base,
            rules,
            "en",
            ExceptionPolicy(),
            _mandatory_info_supplier(text, "en"),
            stats=stats,
        )
    assert small_stats == large_stats == {"lookups": 3, "confirm_attempts": 1}


def test_protected_candidate_index_handles_unsorted_overlapping_spans_linearly():
    class CountedSpan(dict):
        start_reads = 0

        def __getitem__(self, key):
            if key == "start":
                type(self).start_reads += 1
            return super().__getitem__(key)

    size = 128
    offsets = tuple(range(2, size * 2 + 1, 2))
    protected = tuple(
        CountedSpan(start=index % (size * 2 - 1), end=size * 2, type=f"t{index % 7}")
        for index in reversed(range(size))
    )
    found = sentence_override_module._protected_types_by_offset(protected, offsets)
    expected = {
        offset: tuple(
            sorted(
                {
                    item["type"]
                    for item in protected
                    if dict.__getitem__(item, "start") < offset < item["end"]
                }
            )
        )
        for offset in offsets
    }
    assert found == expected
    assert CountedSpan.start_reads <= size * 3


def test_word_only_and_sentence_only_inventory_controls_are_independent():
    text = "Dr. Smith"
    word_only = _inventory(levels=("word",))
    sentence_only = _inventory(levels=("sentence",))

    assert [item["text"] for item in tokens(text, "en_US", inventory=word_only)[:2]] == [
        "Dr.",
        "Smith",
    ]
    word_decision = SentenceOverride(base="none", inventories=[word_only]).decide(text)[0]
    assert (word_decision["decision"], word_decision["layer"]) == ("break", "icu")

    assert [item["text"] for item in tokens(text, "en_US", inventory=sentence_only)[:3]] == [
        "Dr",
        ".",
        "Smith",
    ]
    sentence_decision = SentenceOverride(base="none", inventories=[sentence_only]).decide(text)[0]
    assert (sentence_decision["decision"], sentence_decision["layer"]) == (
        "no-break",
        "exceptions",
    )


def test_duplicate_ids_across_rule_layers_refuse():
    first = _loaded(_rule("duplicate"), set_id="tests/one")
    second = _loaded(_rule("duplicate"), set_id="tests/two")
    with pytest.raises(BreakRuleLoadError) as caught:
        SentenceOverride(base="none", before=[first], after=[second])
    assert "DUPLICATE_RULE_ID" in caught.value.reason_codes

    same_name = _loaded(_rule("same-object"), set_id="tests/same")
    with pytest.raises(BreakRuleLoadError):
        SentenceOverride(base="none", before=[same_name], after=[same_name])

    first_same_id = _loaded(_rule("same-set-rule"), set_id="tests/same-set")
    second_same_id = _loaded(_rule("same-set-rule"), set_id="tests/same-set")
    with pytest.raises(BreakRuleLoadError):
        SentenceOverride(base="none", before=[first_same_id], after=[second_same_id])


def test_token_profile_golden_covers_authored_tokenization_policy():
    """Changing this golden requires bumping TOKEN_PROFILE."""
    assert TOKEN_PROFILE == "icukit.tokens@1"
    text = "O'Neil re-entered. 😀 Dr. Smith"
    found = tokens(
        text,
        "en_US",
        inventory=_inventory(levels=("word",)),
        protected=[{"start": 7, "end": 17, "type": "compound"}],
    )
    assert found == [
        {"start": 0, "end": 6, "text": "O'Neil", "run": 0},
        {
            "start": 7,
            "end": 17,
            "text": "re-entered",
            "run": 1,
            "protected": "compound",
            "protected_types": ("compound",),
        },
        {"start": 17, "end": 18, "text": ".", "run": 1},
        {"start": 19, "end": 20, "text": "😀", "run": 2},
        {"start": 21, "end": 24, "text": "Dr.", "run": 3},
        {"start": 25, "end": 30, "text": "Smith", "run": 4},
    ]


def test_path_base_and_stream_factory(tmp_path: Path):
    path = tmp_path / "rules.json"
    path.write_text(__import__("json").dumps(_rules(_rule())), encoding="utf-8")
    override = SentenceOverride(base=path)
    assert override.decide("Mr. Smith arrived.")[0]["layer"] == "rules"
    assert SentenceOverride(base=str(path)).decide("Mr. Smith arrived.")[0]["layer"] == "rules"
    assert override.stream().lookahead == override.lookahead


def test_named_en_tn_base_attributes_rules():
    text = "alpha a a a\n(1111). continues"
    plain = SentenceOverride(base="none").decide(text)[0]
    learned = SentenceOverride(base="en-tn@1").decide(text)[0]
    assert (plain["layer"], plain["id"], plain["decision"]) == ("icu", None, "break")
    assert (learned["layer"], learned["id"], learned["decision"]) == (
        "rules",
        "en.sb.0001",
        "no-break",
    )


def test_unknown_named_base_is_refused():
    with pytest.raises(ValueError, match="unknown sentence-override base"):
        SentenceOverride(base="en-tn@unknown")


def test_shipped_en_tn_identity_mismatch_is_refused(tmp_path: Path):
    source = Path(__file__).parents[1] / "icukit/data/break_rules/en/sentence-tn.json"
    document = __import__("json").loads(source.read_text(encoding="utf-8"))
    document["identity"]["unicode"] = "0.0"
    path = tmp_path / "mismatch.json"
    path.write_text(__import__("json").dumps(document), encoding="utf-8")
    with pytest.raises(BreakRuleLoadError) as caught:
        SentenceOverride(base=path)
    assert "IDENTITY_MISMATCH" in caught.value.reason_codes


def test_shipped_en_tn_authored_harness_cases():
    """Row 25: fixed authored cases agree with the harness's first-match semantics."""
    override = SentenceOverride(
        base=load_break_rules(sentence_override_module._NAMED_RULE_BASES["en-tn@1"])
    )
    cases = [
        ("alpha a a a\n(1111). continues", "en.sb.0001", "no-break"),
        ("alpha a a 2014.\na continues", "en.sb.0004", "break"),
        ("alpha beta,x ed. Author", "en.sb.0029", "break"),
        ("alpha beta word. ). A1234567890", "en.sb.0179", "no-break"),
    ]
    for text, rule_id, decision in cases:
        item = next(found for found in override.decide(text) if found["id"] == rule_id)
        assert (item["layer"], item["decision"]) == ("rules", decision)
