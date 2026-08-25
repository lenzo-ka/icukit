"""Discriminating end-to-end tests for the H2 v1 exception layer."""

from copy import deepcopy
from dataclasses import asdict, replace
from json import dumps

import icu
import pytest

from icukit import (
    ExceptionConflictError,
    ExceptionLoadError,
    ExceptionPolicy,
    compose_inventories,
    example_exception_inventory,
    load_exception_inventory,
)
from icukit.breaker import (
    BreakSpan,
    break_line_spans,
    break_sentence_spans,
    break_word_spans,
)
from icukit.detect import Detection, collation_detect
from icukit.exceptions import (
    ExceptionInventory,
    ExceptionRule,
    _condition_position,
    _mandatory_info_supplier,
    _merge_spans,
    merge_retypes,
)


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


def test_suppress_post_filter_prevents_word_break():
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


def test_line_suppression_drops_an_optional_punctuation_break():
    rule = _suppression("figure-line", "Fig.")
    rule["level"] = "line"
    rule["witnesses"] = {
        "positive": "Read Fig. more",
        "near_miss": "ConFig. more",
        "condition_negatives": [],
    }
    layer = load_exception_inventory(_inventory(rule))

    spans = layer.break_spans("Read Fig. more", "line", "en")

    assert [(span["text"], span["break_type"], span["statuses"]) for span in spans] == [
        ("Read ", "optional", [0]),
        ("Fig. more", "optional", [0]),
    ]


def test_line_suppression_never_drops_mandatory_breaks():
    rule = _suppression("figure-line", "Fig.")
    rule["level"] = "line"
    rule["witnesses"] = {
        "positive": "Read Fig. more",
        "near_miss": "ConFig. more",
        "condition_negatives": [],
    }
    layer = load_exception_inventory(_inventory(rule))

    assert layer.break_spans("Read Fig.\nThen stop", "line", "en") == break_line_spans(
        "Read Fig.\nThen stop", "en"
    )


def _sentence_suppression() -> ExceptionRule:
    rule = _suppression("captain-sentence", "Capt.")
    rule["level"] = "sentence"
    rule["witnesses"] = {
        "positive": "We met Capt. Smith today.",
        "near_miss": "We met SomeCapt. Smith today.",
        "condition_negatives": [],
    }
    return rule


def _paragraph_separator() -> str:
    mandatory = icu.UnicodeSet(r"[\p{lb=BK}]")
    for range_index in range(mandatory.getRangeCount()):
        start = ord(mandatory.getRangeStart(range_index))
        end = ord(mandatory.getRangeEnd(range_index))
        for code_point in range(start, end + 1):
            char = chr(code_point)
            if icu.Char.charName(char) == "PARAGRAPH SEPARATOR":
                return char
    raise AssertionError("ICU did not expose the paragraph separator")


def _barrier_rule(
    direction="right",
    maximum=8,
    *,
    kind="unicode_set",
    levels="word",
    conditions=None,
):
    target = "Z" if kind == "unicode_set" else "Zed"
    context = (
        {
            "id": "context",
            "kind": "unicode_set",
            "direction": direction,
            "set": "[Z]",
            "skip": {"kind": "whitespace", "max": maximum},
        }
        if kind == "unicode_set"
        else {
            "id": "context",
            "kind": "named_list",
            "direction": direction,
            "list": "contexts",
            "skip": {"kind": "whitespace", "max": maximum},
        }
    )
    rule = _rule(
        id="mandatory-context",
        level=levels,
        effect="retype",
        type="exception:barrier",
        surface="No",
        variant="exact",
        conditions=conditions or [context],
        witnesses={
            "positive": f"No {target}" if direction == "right" else f"{target} No",
            "near_miss": f"ConNo {target}" if direction == "right" else f"{target} ConNo",
            "condition_negatives": ["No X" if direction == "right" else "X No"],
        },
    )
    rule.pop("strength")
    inventory = _inventory(rule)
    inventory["named_lists"] = {"contexts": ["Zed"]}
    return rule, inventory


def _barrier_fired(layer, text, level="word", policy=None):
    spans = layer.break_spans(text, level, "en", policy=policy)
    return any("exception:barrier" in span["types"] for span in spans)


def test_mandatory_break_policy_values():
    assert ExceptionPolicy().mandatory_breaks == "barrier"
    assert ExceptionPolicy(mandatory_breaks="barrier").mandatory_breaks == "barrier"
    assert ExceptionPolicy(mandatory_breaks="cross").mandatory_breaks == "cross"
    with pytest.raises(ValueError, match="mandatory_breaks"):
        ExceptionPolicy(mandatory_breaks="invalid")


@pytest.mark.parametrize("direction", ["left", "right"])
@pytest.mark.parametrize("separator", ["\n", pytest.param(None, id="paragraph-separator")])
def test_mandatory_sequences_block_context_in_both_directions(direction, separator):
    separator = _paragraph_separator() if separator is None else separator
    _, inventory = _barrier_rule(direction)
    layer = load_exception_inventory(inventory)
    text = f"Z{separator}No" if direction == "left" else f"No{separator}Zed"

    assert not _barrier_fired(layer, text)
    assert _barrier_fired(layer, text, policy=ExceptionPolicy(mandatory_breaks="cross"))


@pytest.mark.parametrize(("direction", "text"), [("right", "No\r\nZed"), ("left", "Z\r\nNo")])
def test_crlf_constituent_nearest_the_match_is_barrier_blocked(direction, text):
    _, inventory = _barrier_rule(direction)
    layer = load_exception_inventory(inventory)

    assert not _barrier_fired(layer, text)
    assert _barrier_fired(layer, text, policy=ExceptionPolicy(mandatory_breaks="cross"))


@pytest.mark.parametrize(
    ("maximum", "direction", "text"),
    [
        (1, "right", "No \nZed"),
        (1, "left", "Z\n No"),
    ],
)
def test_skip_budget_landing_on_mandatory_character_is_symmetric(maximum, direction, text):
    rule, inventory = _barrier_rule(direction, maximum)
    layer = load_exception_inventory(inventory)
    condition = layer._rules[0].conditions[0]
    start = text.index(rule["surface"])
    result = _condition_position(
        text,
        start,
        start + len(rule["surface"]),
        condition,
        ExceptionPolicy(),
        _mandatory_info_supplier(text, "en"),
    )

    assert result.outcome == "barrier"
    assert not _barrier_fired(layer, text)


@pytest.mark.parametrize(("direction", "text"), [("right", "No\nZ"), ("left", "Z\nNo")])
def test_zero_skip_landing_on_break_character_is_blocked_in_both_directions(direction, text):
    rule, inventory = _barrier_rule(direction)
    layer = load_exception_inventory(inventory)
    condition = replace(layer._rules[0].conditions[0], skip_max=0)
    start = text.index(rule["surface"])
    result = _condition_position(
        text,
        start,
        start + len(rule["surface"]),
        condition,
        ExceptionPolicy(),
        _mandatory_info_supplier(text, "en"),
    )

    assert result.outcome == "barrier"


@pytest.mark.parametrize(("direction", "text"), [("right", "No.   \nZ"), ("left", "Z\n   No.")])
def test_unbounded_whitespace_skip_stops_at_barrier(direction, text):
    rule = _context_suppression(
        "unbounded-barrier", surface="No.", direction=direction, maximum=None
    )
    layer = load_exception_inventory(_inventory(rule))

    assert layer.break_spans(text, "word", "en") == break_word_spans(text, "en")
    assert layer.break_spans(
        text, "word", "en", policy=ExceptionPolicy(mandatory_breaks="cross")
    ) != break_word_spans(text, "en")


def test_barrier_block_does_not_consult_missing_context_but_true_edge_does():
    _, inventory = _barrier_rule("right")
    layer = load_exception_inventory(inventory)
    policy = ExceptionPolicy(missing_context="match")

    assert not _barrier_fired(layer, "No\nZed", policy=policy)
    assert _barrier_fired(layer, "No", policy=policy)


def test_any_and_all_treat_a_blocked_condition_as_false():
    blocked, _ = _barrier_rule("right")
    matching = {
        "id": "left",
        "kind": "unicode_set",
        "direction": "left",
        "set": "[A]",
        "skip": {"kind": "whitespace", "max": 1},
    }
    blocked_condition = blocked["conditions"][0]
    blocked["conditions"] = [blocked_condition, matching]
    blocked["witnesses"] = {
        "positive": "A No Zed",
        "near_miss": "A ConNo Zed",
        "condition_negatives": ["A No X", "B No Zed"],
    }
    layer = load_exception_inventory(_inventory(blocked))

    assert not _barrier_fired(layer, "A No\nZed")
    assert _barrier_fired(layer, "A No\nZed", policy=ExceptionPolicy(conditions="any"))
    assert not _barrier_fired(
        layer,
        "B No\nZed",
        policy=ExceptionPolicy(conditions="any", missing_context="match"),
    )


@pytest.mark.parametrize("kind", ["unicode_set", "named_list"])
@pytest.mark.parametrize("level", ["word", "sentence", "line"])
def test_barrier_applies_to_condition_kinds_and_break_levels(kind, level):
    _, inventory = _barrier_rule(kind=kind, levels=["word", "sentence", "line"])
    layer = load_exception_inventory(inventory)

    assert not _barrier_fired(layer, "No\nZed", level)


def test_ordinary_space_and_optional_line_opportunity_are_not_barriers():
    _, inventory = _barrier_rule("right", 1)
    layer = load_exception_inventory(inventory)

    assert _barrier_fired(layer, "No Zed")
    assert any(span["end"] == 3 for span in break_line_spans("No Zed", "en")[:-1])


def test_none_skip_remains_unchanged_and_does_not_request_mandatory_info(monkeypatch):
    layer = load_exception_inventory(_inventory(_rule()))
    import icukit.exceptions as exceptions

    def fail_line(*args):
        raise AssertionError("unexpected line pass")

    monkeypatch.setattr(exceptions, "break_line_spans", fail_line)

    assert layer.break_spans("No. Next", "word", "en")[0]["types"] == ["exception:abbreviation"]


@pytest.mark.parametrize("disposition", ["rule", "suppress", "retype", "mark"])
def test_barrier_blocks_suppression_and_forced_dispositions(disposition):
    rule = _context_suppression("barrier-disposition", surface="No.", maximum=None)
    layer = load_exception_inventory(_inventory(rule))
    text = "No.\nZ"
    barrier = ExceptionPolicy(disposition=disposition)
    cross = ExceptionPolicy(disposition=disposition, mandatory_breaks="cross")

    assert layer.break_spans(text, "word", "en", policy=barrier) == break_word_spans(text, "en")
    assert layer.break_spans(text, "word", "en", policy=cross) != break_word_spans(text, "en")


def test_many_barrier_conditions_share_one_mandatory_line_pass(monkeypatch):
    first, _ = _barrier_rule()
    second = deepcopy(first)
    second["id"] = "mandatory-context-two"
    layer = load_exception_inventory(_inventory(first, second))
    import icukit.exceptions as exceptions

    calls = 0
    line_breaker = exceptions.break_line_spans

    def count_line(text, locale):
        nonlocal calls
        calls += 1
        return line_breaker(text, locale)

    monkeypatch.setattr(exceptions, "break_line_spans", count_line)

    layer.break_spans("No\nZed No\nZed", "word", "en")

    assert calls == 1


@pytest.mark.parametrize("separator", ["\n", pytest.param(None, id="paragraph-separator")])
def test_sentence_suppression_never_drops_mandatory_break(separator):
    separator = _paragraph_separator() if separator is None else separator
    layer = load_exception_inventory(_inventory(_sentence_suppression()))
    text = f"We met Capt.{separator}Smith today."
    mandatory_offset = len("We met Capt.") + 1

    spans = layer.break_spans(text, "sentence", "en")

    assert mandatory_offset in {span["end"] for span in spans}


def test_sentence_suppression_preserves_each_consecutive_mandatory_break():
    layer = load_exception_inventory(_inventory(_sentence_suppression()))
    text = "We met Capt.\n\nSmith today."

    spans = layer.break_spans(text, "sentence", "en")

    assert {len("We met Capt.\n"), len("We met Capt.\n\n")} <= {span["end"] for span in spans}


def test_word_suppression_keeps_mandatory_offsets_as_a_guard():
    layer = load_exception_inventory(_inventory(_suppression("captain-word", "Capt.")))
    text = "We met Capt.\nSmith today."
    mandatory_offsets = {
        span["end"] for span in break_line_spans(text, "en") if span["break_type"] == "mandatory"
    }

    spans = layer.break_spans(text, "word", "en")

    assert mandatory_offsets <= {span["end"] for span in spans}


def test_line_suppression_reuses_base_line_pass(monkeypatch):
    rule = _suppression("figure-line-pass", "Fig.")
    rule["level"] = "line"
    rule["witnesses"] = {
        "positive": "Read Fig. more",
        "near_miss": "Read ConFig. more",
        "condition_negatives": [],
    }
    layer = load_exception_inventory(_inventory(rule))
    import icukit.exceptions as exceptions

    calls = 0
    line_breaker = exceptions.break_line_spans

    def count_line(text, locale):
        nonlocal calls
        calls += 1
        return line_breaker(text, locale)

    monkeypatch.setattr(exceptions, "break_line_spans", count_line)

    layer.break_spans("Read Fig.\nThen stop", "line", "en")

    assert calls == 1


def test_line_without_matching_detection_skips_mandatory_info(monkeypatch):
    rule = _suppression("figure-line-lazy", "Fig.")
    rule["level"] = "line"
    rule["witnesses"] = {
        "positive": "Read Fig. more",
        "near_miss": "Read ConFig. more",
        "condition_negatives": [],
    }
    layer = load_exception_inventory(_inventory(rule))
    import icukit.exceptions as exceptions

    line_calls = 0
    property_calls = 0
    line_breaker = exceptions.break_line_spans
    icu_char = exceptions.icu.Char

    def count_line(text, locale):
        nonlocal line_calls
        line_calls += 1
        return line_breaker(text, locale)

    class CountChar:
        @staticmethod
        def getIntPropertyValue(code_point, property_name):
            nonlocal property_calls
            property_calls += 1
            return icu_char.getIntPropertyValue(code_point, property_name)

    monkeypatch.setattr(exceptions, "break_line_spans", count_line)
    monkeypatch.setattr(exceptions.icu, "Char", CountChar)

    layer.break_spans("Nothing matches here.", "line", "en")

    assert line_calls == 1
    assert property_calls == 0


@pytest.mark.parametrize("disposition", ["rule", "suppress", "retype", "mark"])
def test_policy_dispositions_cannot_claim_mandatory_boundary(disposition):
    layer = load_exception_inventory(_inventory(_sentence_suppression()))
    text = "We met Capt.\nSmith today."

    assert layer.break_spans(
        text, "sentence", "en", policy=ExceptionPolicy(disposition=disposition)
    ) == break_sentence_spans(text, "en")


def test_no_matching_detection_skips_line_pass(monkeypatch):
    layer = load_exception_inventory(_inventory(_sentence_suppression()))
    import icukit.exceptions as exceptions

    def fail_line(*args):
        raise AssertionError("unexpected line pass")

    monkeypatch.setattr(exceptions, "break_line_spans", fail_line)

    layer.break_spans("Nothing matches here.", "sentence", "en")


def test_many_candidate_claims_use_at_most_one_line_pass(monkeypatch):
    layer = load_exception_inventory(_inventory(_sentence_suppression()))
    import icukit.exceptions as exceptions

    calls = 0
    line_breaker = exceptions.break_line_spans

    def count_line(text, locale):
        nonlocal calls
        calls += 1
        return line_breaker(text, locale)

    monkeypatch.setattr(exceptions, "break_line_spans", count_line)

    layer.break_spans("Capt. Smith met Capt. Jones.", "sentence", "en")

    assert calls <= 1


def test_merged_line_span_keeps_only_its_end_boundary_statuses():
    text = "See Fig.\nThen stop"
    base = break_line_spans(text, "en")

    merged = _merge_spans(text, base[1:3])

    assert merged["break_type"] == "optional"
    assert merged["statuses"] == [0]


@pytest.mark.parametrize(
    ("level", "surface", "text"),
    [("line", "日", "日本語を"), ("word", "co", "co-op time")],
)
def test_unpunctuated_suppression_fails_its_witness(level, surface, text):
    rule = _suppression(f"unpunctuated-{level}", surface)
    rule["level"] = level
    rule["witnesses"] = {
        "positive": text,
        "near_miss": f"x{surface}",
        "condition_negatives": [],
    }

    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(rule))

    assert "WITNESS_POSITIVE_FAILED" in caught.value.reason_codes


def test_omitted_policy_is_byte_identical_to_legacy_default():
    layer = load_exception_inventory(_inventory(_rule(), _suppression("figure-default", "Fig.")))
    text = "No. See Fig. 5"

    implicit = layer.break_spans(text, "word", "en")
    explicit = layer.break_spans(text, "word", "en", policy=ExceptionPolicy())

    assert implicit == explicit
    assert implicit == [
        {
            "text": "No",
            "start": 0,
            "end": 2,
            "types": ["exception:abbreviation"],
            "statuses": [200],
        },
        {"text": ".", "start": 2, "end": 3, "types": ["punctuation"], "statuses": [0]},
        {"text": " ", "start": 3, "end": 4, "types": ["whitespace"], "statuses": [0]},
        {"text": "See", "start": 4, "end": 7, "types": ["letter"], "statuses": [200]},
        {"text": " ", "start": 7, "end": 8, "types": ["whitespace"], "statuses": [0]},
        {
            "text": "Fig.",
            "start": 8,
            "end": 12,
            "types": ["letter", "punctuation"],
            "statuses": [200, 0],
        },
        {"text": " ", "start": 12, "end": 13, "types": ["whitespace"], "statuses": [0]},
        {"text": "5", "start": 13, "end": 14, "types": ["number"], "statuses": [100]},
    ]


def test_policy_can_retype_or_mark_without_changing_segmentation():
    layer = load_exception_inventory(_inventory(_suppression("figure-policy", "Fig.")))
    text = "See Fig. 5"
    vanilla = break_word_spans(text, "en")

    retyped = layer.break_spans(
        text,
        "word",
        "en",
        policy=ExceptionPolicy(disposition="retype", retype_as="exception:abbreviation"),
    )
    marked = layer.break_spans(text, "word", "en", policy=ExceptionPolicy(disposition="mark"))

    assert [(span["start"], span["end"]) for span in retyped] == [
        (span["start"], span["end"]) for span in vanilla
    ]
    assert "exception:abbreviation" in retyped[2]["types"]
    assert [(span["start"], span["end"]) for span in marked] == [
        (span["start"], span["end"]) for span in vanilla
    ]
    assert marked[2]["exceptions"] == [{"rule_id": "figure-policy", "relation": "boundary"}]


def test_one_rule_can_claim_word_and_sentence_levels():
    rule = _suppression("doctor-levels", "Dr.")
    rule["level"] = ["word", "sentence"]
    rule["witnesses"]["positive"] = "I met Dr. Smith today. "
    rule["witnesses"]["near_miss"] = "I met SomeDr. Smith today. "
    layer = load_exception_inventory(_inventory(rule))
    text = "I met Dr. Smith today. Next."

    words = layer.break_spans(text, "word", "en")
    sentences = layer.break_spans(text, "sentence", "en")

    assert [span["text"] for span in words[:7]] == ["I", " ", "met", " ", "Dr.", " ", "Smith"]
    assert sentences[0]["text"] == "I met Dr. Smith today. "


def test_multi_level_rule_uses_only_the_requested_breaker(monkeypatch):
    rule = _suppression("doctor-one-pass", "Dr.")
    rule["level"] = ["word", "sentence"]
    rule["witnesses"]["positive"] = "I met Dr. Smith today. "
    rule["witnesses"]["near_miss"] = "I met SomeDr. Smith today. "
    layer = load_exception_inventory(_inventory(rule))
    import icukit.exceptions as exceptions

    calls = {"word": 0, "sentence": 0}
    word_breaker = exceptions.break_word_spans
    sentence_breaker = exceptions.break_sentence_spans

    def count_word(text, locale):
        calls["word"] += 1
        return word_breaker(text, locale)

    def count_sentence(text, locale):
        calls["sentence"] += 1
        return sentence_breaker(text, locale)

    monkeypatch.setattr(exceptions, "break_word_spans", count_word)
    monkeypatch.setattr(exceptions, "break_sentence_spans", count_sentence)

    layer.break_spans("I met Dr. Smith today.", "sentence", "en")

    assert calls == {"word": 0, "sentence": 1}


def test_multi_level_rule_is_refused_when_one_level_is_not_witnessed():
    rule = _suppression("half-working", "Fig.")
    rule["level"] = ["word", "sentence"]
    rule["witnesses"]["positive"] = "See Fig."

    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(rule))

    assert any(
        refusal.reason == "WITNESS_POSITIVE_FAILED"
        and refusal.detail == "rule did not fire at sentence"
        for refusal in caught.value.refusals
    )


def test_single_level_spelling_remains_valid():
    layer = load_exception_inventory(_inventory(_suppression("single-level", "Fig.")))

    assert layer.break_spans("See Fig. 5", "word", "en")[2]["text"] == "Fig."


def test_policy_names_partial_missing_and_overlap_behavior():
    conditional = _rule(
        id="conditional-policy",
        effect="suppress",
        type=None,
        surface="No.",
        variant="exact",
        conditions=[
            {
                "id": "right-letter",
                "kind": "unicode_set",
                "direction": "right",
                "set": "[N]",
                "skip": {"kind": "whitespace", "max": 1},
            }
        ],
        witnesses={
            "positive": "No. Next",
            "near_miss": "ConNo. Next",
            "condition_negatives": ["No. Other"],
        },
    )
    conditional.pop("strength")
    duplicate = deepcopy(conditional)
    duplicate["id"] = "conditional-policy-2"
    layer = load_exception_inventory(_inventory(conditional, duplicate))

    assert layer.break_spans("No.", "word", "en") == break_word_spans("No.", "en")
    assert [
        span["text"]
        for span in layer.break_spans(
            "No.", "word", "en", policy=ExceptionPolicy(missing_context="match")
        )
    ] == ["No."]
    with pytest.raises(ExceptionConflictError, match="OVERLAPPING_EXCEPTION_RULES"):
        layer.break_spans("No. Next", "word", "en", policy=ExceptionPolicy(overlap="error"))


def test_sentence_suppression_joins_abbreviation_to_following_sentence():
    rule = _rule(
        id="mr-sentence",
        level="sentence",
        effect="suppress",
        type=None,
        surface="Mr.",
        variant="exact",
        conditions=[
            {
                "id": "uppercase",
                "kind": "unicode_set",
                "direction": "right",
                "set": "[[:Lu:]]",
                "skip": {"kind": "whitespace", "max": 1},
            }
        ],
        witnesses={
            "positive": "I met Mr. Smith today.",
            "near_miss": "SomeMr. Smith today.",
            "condition_negatives": ["I met Mr. smith today."],
        },
    )
    rule.pop("strength")
    layer = load_exception_inventory(_inventory(rule))
    text = "I met Mr. Smith today. He left."

    spans = layer.break_spans(text, "sentence", "en")

    assert [span["text"] for span in spans] == ["I met Mr. Smith today. ", "He left."]
    assert layer.break_spans("Mr.", "sentence", "en")[0]["text"] == "Mr."

    negative = "I met Ms. Smith today. She left."
    tailored = layer.break_spans(negative, "sentence", "en")
    vanilla = break_sentence_spans(negative, "en")
    assert [(span["text"], span["start"], span["end"]) for span in tailored] == [
        (span["text"], span["start"], span["end"]) for span in vanilla
    ]


def test_combining_cluster_may_not_be_bisected():
    text = "e\N{COMBINING ACUTE ACCENT}"
    base: list[BreakSpan] = [
        {"text": text, "start": 0, "end": 2, "types": ["letter"], "statuses": [200]}
    ]
    detection = Detection(text="e", start=0, end=1, type="exception:test")

    with pytest.raises(ExceptionConflictError, match="DETECTION_NOT_GRAPHEME_ALIGNED"):
        merge_retypes(text, base, [detection])


def test_left_context_suppression_loads_and_filters():
    left = _rule(
        id="left",
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
    left.pop("strength")
    layer = load_exception_inventory(_inventory(left))

    assert [span["text"] for span in layer.break_spans("A Fig.", "word", "en")] == [
        "A",
        " ",
        "Fig.",
    ]
    assert layer.break_spans("B Fig.", "word", "en") == break_word_spans("B Fig.", "en")


def test_transactional_loader_collects_remaining_refusals():
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
        load_exception_inventory(_inventory(bad_unbounded, bad_type))

    assert "UNHOSTABLE_UNBOUNDED_LEFT" in caught.value.reason_codes
    assert "INVALID_TYPE" in caught.value.reason_codes


def test_unbounded_context_suppression_loads_and_filters():
    rule = _rule(
        id="unbounded-left",
        effect="suppress",
        type=None,
        surface="Fig.",
        variant="exact",
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
            "positive": "A   Fig.",
            "near_miss": "Configure Fig.",
            "condition_negatives": ["B   Fig."],
        },
    )
    rule.pop("strength")
    layer = load_exception_inventory(_inventory(rule))

    assert any(span["text"] == "Fig." for span in layer.break_spans("A     Fig.", "word", "en"))


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


def test_named_list_condition_can_guard_suppression():
    named_list_suppression = _rule(
        id="named-list-suppression",
        effect="suppress",
        type=None,
        surface="Dr.",
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
            "positive": "Dr. Smith",
            "near_miss": "DroneDr. Smith",
            "condition_negatives": ["Dr. who"],
        },
    )
    named_list_suppression.pop("strength")
    inventory = _inventory(named_list_suppression)
    inventory["named_lists"] = {"surnames": ["Smith", "Jones"]}
    layer = load_exception_inventory(inventory)
    assert layer.break_spans("Dr. Smith", "word", "en")[0]["text"] == "Dr."


def test_unhostable_needs_replace_remains_for_retype_coalescing():

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


def _context_suppression(
    rule_id: str,
    *,
    surface: str = "Fig.",
    direction: str = "right",
    maximum: int | None = 1,
) -> ExceptionRule:
    spaces = " " * (maximum if isinstance(maximum, int) else 3)
    positive = f"A {surface}{spaces}Z" if direction == "right" else f"Z{spaces}{surface}"
    near_miss = f"A Con{surface}{spaces}Z" if direction == "right" else f"Z{spaces}Con{surface}"
    negative = f"A {surface}{spaces}X" if direction == "right" else f"X{spaces}{surface}"
    rule = _suppression(rule_id, surface)
    rule["conditions"] = [
        {
            "id": "context",
            "kind": "unicode_set",
            "direction": direction,
            "set": "[Z]",
            "skip": {"kind": "whitespace", "max": maximum},
        }
    ]
    rule["unconditionality"] = "conditional"
    rule["witnesses"] = {
        "positive": positive,
        "near_miss": near_miss,
        "condition_negatives": [negative],
    }
    return rule


def test_context_bounds_are_derived_from_surface_skip_and_direction():
    short = load_exception_inventory(
        _inventory(_context_suppression("short", surface="Fig.", maximum=3))
    )
    long = load_exception_inventory(
        _inventory(_context_suppression("long", surface="Figure.", maximum=5))
    )
    left = load_exception_inventory(
        _inventory(_context_suppression("left-bound", direction="left", maximum=3))
    )

    assert short.context_bounds.left == 0
    assert short.context_bounds.right == 3 + 1
    assert short.context_bounds.right_from_match_start == len("Fig.") + 3 + 1
    assert long.context_bounds.max_surface_length == len("Figure.")
    assert long.context_bounds.right_from_match_start == len("Figure.") + 5 + 1
    assert left.context_bounds.left == 3 + 1
    assert left.context_bounds.right == 0


def test_context_bounds_serialization_remains_byte_identical():
    loaded = load_exception_inventory(
        _inventory(_context_suppression("stable-bounds", surface="Fig.", maximum=3))
    )

    assert dumps(asdict(loaded.context_bounds), sort_keys=True, separators=(",", ":")) == (
        '{"left":0,"max_surface_length":4,"right":4,'
        '"right_from_match_start":8,"unbounded_left_rule_ids":[],'
        '"unbounded_right_rule_ids":[],"unbounded_rule_ids":[]}'
    )


def test_named_list_context_bound_uses_longest_loaded_member():
    rule = _context_suppression("named")
    rule["conditions"] = [
        {
            "id": "name",
            "kind": "named_list",
            "direction": "right",
            "list": "names",
            "skip": {"kind": "whitespace", "max": 1},
        }
    ]
    rule["witnesses"] = {
        "positive": "A Fig. Zedekiah",
        "near_miss": "A ConFig. Zedekiah",
        "condition_negatives": ["A Fig. Xavier"],
    }
    inventory = _inventory(rule)
    inventory["named_lists"] = {"names": ["Zed", "Zedekiah"]}

    loaded = load_exception_inventory(inventory)

    assert loaded.context_bounds.right == 1 + len("Zedekiah") + 1


@pytest.mark.parametrize(
    ("direction", "positive", "longer"),
    [
        ("right", "Dr. Smith", "Dr. Smithy"),
        ("left", "Smith Dr.", "XSmith Dr."),
    ],
)
def test_named_list_context_bound_includes_token_terminator(direction, positive, longer):
    rule = _context_suppression("smith", surface="Dr.", direction=direction)
    rule["conditions"] = [
        {
            "id": "name",
            "kind": "named_list",
            "direction": direction,
            "list": "names",
            "skip": {"kind": "whitespace", "max": 1},
        }
    ]
    rule["witnesses"] = {
        "positive": positive,
        "near_miss": "ConDr. Smith" if direction == "right" else "Smith ConDr.",
        "condition_negatives": [longer],
    }
    inventory = _inventory(rule)
    inventory["named_lists"] = {"names": ["Smith"]}

    loaded = load_exception_inventory(inventory)

    expected = 1 + len("Smith") + 1
    assert getattr(loaded.context_bounds, direction) == expected


def test_collation_combining_marks_make_match_extent_unbounded():
    text = "á" + "\N{COMBINING ACUTE ACCENT}" * 10 + " Z"
    detections = collation_detect(text, "a", "term", locale="de", strength="primary")
    assert detections[0]["end"] == 11

    rule = _rule(
        id="combining-collation",
        locale="de",
        surface="a",
        conditions=[
            {
                "id": "right-z",
                "kind": "unicode_set",
                "direction": "right",
                "set": "[Z]",
                "skip": {"kind": "whitespace", "max": 1},
            }
        ],
        witnesses={
            "positive": text,
            "near_miss": "X" + text,
            "condition_negatives": ["a X"],
        },
    )
    loaded = load_exception_inventory(_inventory(rule))

    assert loaded.context_bounds.right == 2
    assert loaded.context_bounds.right_from_match_start is None
    assert loaded.context_bounds.unbounded_rule_ids == ("combining-collation",)
    assert loaded.context_bounds.unbounded_right_rule_ids == ("combining-collation",)

    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(_inventory(rule), require_finite_context=True)
    assert caught.value.refusals[0].detail.endswith("collation match extent")


def test_collation_expansion_makes_match_extent_unbounded():
    detections = collation_detect("ss", "ß", "term", locale="de", strength="primary")
    assert [(item["start"], item["end"]) for item in detections] == [(0, 2)]

    rule = _rule(
        id="sharp-s-collation",
        locale="de",
        surface="ß",
        conditions=[],
        unconditionality="empirical",
        witnesses={
            "positive": "ss",
            "near_miss": "Xss",
            "condition_negatives": [],
        },
    )
    loaded = load_exception_inventory(_inventory(rule))

    assert loaded.context_bounds.max_surface_length == 1
    assert loaded.context_bounds.right_from_match_start is None
    assert loaded.context_bounds.unbounded_rule_ids == ("sharp-s-collation",)


def test_context_bounds_for_conditionless_and_mixed_unbounded_rules():
    conditionless = load_exception_inventory(_inventory(_suppression("plain", "Fig.")))
    mixed = load_exception_inventory(
        _inventory(
            _context_suppression("bounded", maximum=2),
            _context_suppression("unbounded", surface="Eq.", maximum=None),
        )
    )

    assert conditionless.context_bounds.left == 0
    assert conditionless.context_bounds.right == 0
    assert conditionless.context_bounds.max_surface_length == len("Fig.")
    assert conditionless.context_bounds.right_from_match_start == len("Fig.")
    assert conditionless.context_bounds.unbounded_rule_ids == ()
    assert mixed.context_bounds.left == 0
    assert mixed.context_bounds.right is None
    assert mixed.context_bounds.right_from_match_start is None
    assert mixed.context_bounds.unbounded_right_rule_ids == ("unbounded",)
    assert mixed.context_bounds.unbounded_rule_ids == ("unbounded",)


def test_finite_context_requirement_refuses_each_unbounded_rule_id():
    inventory = _inventory(
        _context_suppression("bounded", maximum=2),
        _context_suppression("right-unbounded", maximum=None),
        _context_suppression("left-unbounded", direction="left", maximum=None),
    )

    with pytest.raises(ExceptionLoadError) as caught:
        load_exception_inventory(inventory, require_finite_context=True)

    assert caught.value.reason_codes == ("UNBOUNDED_CONTEXT", "UNBOUNDED_CONTEXT")
    assert tuple(refusal.rule_id for refusal in caught.value.refusals) == (
        "right-unbounded",
        "left-unbounded",
    )

    with pytest.raises(ExceptionLoadError, match="right-unbounded: UNBOUNDED_CONTEXT"):
        compose_inventories([inventory], require_finite_context=True)


def test_default_loading_behavior_is_unchanged_for_unbounded_context():
    inventory = _inventory(_context_suppression("unbounded", maximum=None))
    text = "A Fig.     Z"

    implicit = load_exception_inventory(inventory)
    explicit = load_exception_inventory(inventory, require_finite_context=False)

    assert dumps(implicit.break_spans(text, "word", "en"), sort_keys=True) == dumps(
        explicit.break_spans(text, "word", "en"), sort_keys=True
    )


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


def test_compose_applies_multiple_suppressions_without_reserved_statuses():
    composed = compose_inventories(
        [
            _inventory(_suppression("figure", "Fig.")),
            _inventory(_suppression("equation", "Eq.")),
        ]
    )

    spans = composed.break_spans("Fig. 5 Eq. 6", "word", "en")
    assert [span["text"] for span in spans] == ["Fig.", " ", "5", " ", "Eq.", " ", "6"]
    assert all(status < 1000 for span in spans for status in span["statuses"])


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
