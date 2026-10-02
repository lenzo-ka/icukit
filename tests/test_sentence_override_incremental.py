"""Incremental sentence override contract tests over authored text."""

import random

import pytest

import icukit.sentence_override as sentence_override_module
from icukit import (
    Breaker,
    LateProtectedSpan,
    SentenceOverride,
    break_rule_identity,
    collation_detect,
    load_break_rules,
    load_exception_inventory,
)


def _rule(rule_id, *, lookahead, when, effect="no-break", match="Mr. Smith Jones Zebra."):
    return {
        "id": rule_id,
        "effect": effect,
        "lookahead": lookahead,
        "when": when,
        "receipt": {"n": 1},
        "witnesses": {"match": [match], "no_match": ["Hello. smith went home."]},
    }


def _loaded(*rules, set_id="tests/incremental", inventories=()):
    return load_break_rules(
        {
            "schema_version": 1,
            "kind": "break-rules",
            "id": set_id,
            "locale": "en",
            "status": "experimental",
            "features": "icukit.features@1",
            "identity": break_rule_identity(inventories=inventories),
            "rules": list(rules),
        },
        inventories=inventories,
    )


def _next_upper(rule_id="next-upper", lookahead=1):
    return _rule(
        rule_id,
        lookahead=lookahead,
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": 1, "f": "general_category.first", "in": ["Uppercase_Letter"]},
        ],
    )


def _stream(override, chunks):
    breaker = override.stream()
    result = []
    for chunk in chunks:
        result.extend(breaker.feed(chunk))
    result.extend(breaker.close())
    return result


def _stream_with_prefix_checks(override, chunks, expected):
    """Stream chunks, checking every prefix emission against whole text."""
    breaker = override.stream()
    expected_by_offset = {item["offset"]: item for item in expected}
    result = []
    for chunk in chunks:
        emitted = breaker.feed(chunk)
        assert all(item == expected_by_offset[item["offset"]] for item in emitted)
        result.extend(emitted)
    result.extend(breaker.close())
    return result


def _word_only_inventory(surface="Dr.", rule_id="doctor-word-only"):
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "incremental word-only control",
            "named_lists": {},
            "rules": [
                {
                    "id": rule_id,
                    "locale": "en",
                    "level": ["word"],
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
            ],
        }
    )


def _exact_word_inventory(surface, rule_id):
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": f"incremental exact word surface {surface}",
            "named_lists": {},
            "rules": [
                {
                    "id": rule_id,
                    "locale": "en",
                    "level": ["word"],
                    "effect": "suppress",
                    "type": None,
                    "surface": surface,
                    "variant": "exact",
                    "conditions": [],
                    "unconditionality": "empirical",
                    "provenance": {"source": "authored tests"},
                    "witnesses": {
                        "positive": f"I met {surface} today.",
                        "near_miss": f"I met Some{surface} today.",
                        "condition_negatives": [],
                    },
                }
            ],
        }
    )


def _cross_candidate_inventory(*, variant="exact", level="word"):
    rule = {
        "id": "mr-smith-word",
        "locale": "en",
        "level": [level],
        "effect": "suppress",
        "type": None,
        "surface": "Mr. Smith",
        "variant": variant,
        "conditions": [],
        "unconditionality": "empirical",
        "provenance": {"source": "authored tests"},
        "witnesses": {
            "positive": "I met Mr. Smith today.",
            "near_miss": "I met SomeMr. Smith today.",
            "condition_negatives": [],
        },
    }
    if variant == "collation":
        rule["strength"] = "primary"
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": f"incremental cross-candidate {level} rule",
            "named_lists": {},
            "rules": [rule],
        }
    )


def _strasse_word_inventory():
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "incremental collation expansion",
            "named_lists": {},
            "rules": [
                {
                    "id": "mr-strasse-word",
                    "locale": "de",
                    "level": ["word"],
                    "effect": "suppress",
                    "type": None,
                    "surface": "Mr. Straße",
                    "variant": "collation",
                    "strength": "primary",
                    "conditions": [],
                    "unconditionality": "empirical",
                    "provenance": {"source": "authored tests"},
                    "witnesses": {
                        "positive": "Mr. Strasse arrived.",
                        "near_miss": "SomeMr. Strasse arrived.",
                        "condition_negatives": [],
                    },
                }
            ],
        }
    )


def _conditional_word_inventory():
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "incremental conditional word merge",
            "named_lists": {"lowercase_words": ["arrived"]},
            "rules": [
                {
                    "id": "mr-smith-before-lowercase-word",
                    "locale": "en",
                    "level": ["word"],
                    "effect": "suppress",
                    "type": None,
                    "surface": "Mr. Smith",
                    "variant": "exact",
                    "conditions": [
                        {
                            "id": "lowercase-word-next",
                            "kind": "named_list",
                            "direction": "right",
                            "list": "lowercase_words",
                            "skip": {"kind": "whitespace", "max": 8},
                        }
                    ],
                    "unconditionality": "conditional",
                    "provenance": {"source": "authored tests"},
                    "witnesses": {
                        "positive": "Mr. Smith arrived.",
                        "near_miss": "SomeMr. Smith arrived.",
                        "condition_negatives": ["Mr. Smith Jones."],
                    },
                }
            ],
        }
    )


def _lowercase_sentence_inventory():
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "incremental right-condition exclusion",
            "named_lists": {},
            "rules": [
                {
                    "id": "mr-before-lowercase",
                    "locale": "en",
                    "level": ["sentence"],
                    "effect": "suppress",
                    "type": None,
                    "surface": "Mr. Smith",
                    "variant": "exact",
                    "conditions": [
                        {
                            "id": "lowercase-next",
                            "kind": "unicode_set",
                            "direction": "right",
                            "set": "[[:Lowercase:]]",
                            "skip": {"kind": "whitespace", "max": 8},
                        }
                    ],
                    "unconditionality": "conditional",
                    "provenance": {"source": "authored tests"},
                    "witnesses": {
                        "positive": "Mr. Smith arrived.",
                        "near_miss": "SomeMr. Smith arrived.",
                        "condition_negatives": ["Mr. Smith Jones arrived."],
                    },
                }
            ],
        }
    )


def _unbounded_right_sentence_inventory(surface, rule_id, following="arrived"):
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": f"incremental unbounded right context for {surface}",
            "named_lists": {"following": [following]},
            "rules": [
                {
                    "id": rule_id,
                    "locale": "en",
                    "level": ["sentence"],
                    "effect": "suppress",
                    "type": None,
                    "surface": surface,
                    "variant": "exact",
                    "conditions": [
                        {
                            "id": "following-word",
                            "kind": "named_list",
                            "direction": "right",
                            "list": "following",
                            "skip": {"kind": "whitespace", "max": None},
                        }
                    ],
                    "unconditionality": "conditional",
                    "provenance": {"source": "authored tests"},
                    "witnesses": {
                        "positive": f"{surface} {following}. Next",
                        "near_miss": f"Some{surface} {following}. Next",
                        "condition_negatives": [f"{surface} departed. Next"],
                    },
                }
            ],
        }
    )


def _apostrophe_sentence_inventory():
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "incremental apostrophe condition",
            "named_lists": {"following": ["arrived's"]},
            "rules": [
                {
                    "id": "mr-before-arrived-possessive",
                    "locale": "en",
                    "level": ["sentence"],
                    "effect": "suppress",
                    "type": None,
                    "surface": "Mr. Smith",
                    "variant": "exact",
                    "conditions": [
                        {
                            "id": "possessive-next",
                            "kind": "named_list",
                            "direction": "right",
                            "list": "following",
                            "skip": {"kind": "whitespace", "max": 8},
                        }
                    ],
                    "unconditionality": "conditional",
                    "provenance": {"source": "authored tests"},
                    "witnesses": {
                        "positive": "Mr. Smith arrived's.",
                        "near_miss": "SomeMr. Smith arrived's.",
                        "condition_negatives": ["Mr. Smith arrived."],
                    },
                }
            ],
        }
    )


def _quoted_mr_sentence_inventory():
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "quoted sentence surface with named right context",
            "named_lists": {"names": ["Smith"]},
            "rules": [
                {
                    "id": "quoted-mr-before-smith",
                    "locale": "en",
                    "level": ["sentence"],
                    "effect": "suppress",
                    "type": None,
                    "surface": "Mr.",
                    "variant": "exact",
                    "conditions": [
                        {
                            "id": "smith-next",
                            "kind": "named_list",
                            "direction": "right",
                            "list": "names",
                            "skip": {"kind": "whitespace"},
                        }
                    ],
                    "unconditionality": "conditional",
                    "provenance": {"source": "authored tests"},
                    "witnesses": {
                        "positive": "I met Mr. Smith left.",
                        "near_miss": "I met SomeMr. Smith left.",
                        "condition_negatives": ["I met Mr. Jones left."],
                    },
                }
            ],
        }
    )


def _assert_all_chunkings(override, text, *, seed, random_count=200):
    expected = override.decide(text)
    for first in range(len(text) + 1):
        for second in range(first, len(text) + 1):
            assert (
                _stream_with_prefix_checks(
                    override,
                    [text[:first], text[first:second], text[second:]],
                    expected,
                )
                == expected
            )
    rng = random.Random(seed)
    for _ in range(random_count):
        cuts = sorted(rng.randrange(len(text) + 1) for _ in range(rng.randint(0, 8)))
        points = [0, *cuts, len(text)]
        chunks = [text[start:end] for start, end in zip(points, points[1:], strict=False)]
        assert _stream_with_prefix_checks(override, chunks, expected) == expected


def _random_watermark_stream(override, text, protected, rng):
    breaker = override.stream(protection="watermark")
    emitted = []
    emitted_at = []
    supplied = 0
    watermark = 0
    remaining = list(protected)
    cuts = sorted(rng.randrange(len(text) + 1) for _ in range(rng.randint(2, 10)))
    for end in [*cuts, len(text)]:
        chunk = text[supplied:end]
        supplied = end
        additions = [span for span in remaining if span["end"] <= supplied]
        remaining = [span for span in remaining if span not in additions]
        limit = supplied if not remaining else min(supplied, remaining[0]["start"])
        watermark = rng.randint(watermark, limit)
        got = breaker.feed(chunk, protected=additions, protected_through=watermark)
        assert breaker._read_horizon <= watermark
        emitted.extend(got)
        emitted_at.extend((item, breaker._read_horizon, watermark) for item in got)
    got = breaker.close()
    assert breaker._read_horizon <= len(text)
    emitted.extend(got)
    emitted_at.extend((item, breaker._read_horizon, len(text)) for item in got)
    return emitted, emitted_at


def test_icu_prefix_stability_seeded_characterization():
    rng = random.Random(1705)
    atoms = ["Alpha.", '"No."', "beta?", "Gamma!", "😀", "42.", "\r", "\n", " "]
    for _ in range(100):
        text = " ".join(rng.choice(atoms) for _ in range(rng.randint(2, 9)))
        full = [item["end"] for item in Breaker("en_US", base="none").break_sentence_spans(text)]
        for cut in range(1, len(text) + 1):
            prefix = text[:cut]
            letters = [index for index, char in enumerate(prefix) if char.isalpha()]
            if not letters:
                continue
            horizon = letters[-1]
            observed = [
                item["end"]
                for item in Breaker("en_US", base="none").break_sentence_spans(prefix)
                if item["end"] <= horizon
            ]
            assert observed == [offset for offset in full if offset <= horizon]


def test_crlf_candidate_waits_and_matches_independent_icu_oracle():
    simple = SentenceOverride(base="none").stream()
    simple_streamed = simple.feed("A\r") + simple.feed("\nB") + simple.close()
    assert simple_streamed == SentenceOverride(base="none").decide("A\r\nB")

    text = "😀A\r\nB."
    expected_offsets = [
        item["end"] for item in Breaker("en_US", base="none").break_sentence_spans(text)
    ]
    breaker = SentenceOverride(base="none").stream()
    first = breaker.feed("😀A\r")
    assert first == []
    assert any(item["waiting_on"] == "icu" for item in breaker.pending())
    streamed = first + breaker.feed("\n") + breaker.feed("B.") + breaker.close()
    assert [item["offset"] for item in streamed] == expected_offsets
    assert streamed == SentenceOverride(base="none").decide(text)


@pytest.mark.parametrize(
    "text",
    [
        'He said "No." then left.',
        'She answered." lowercase followed.',
        "Mr. Smith arrived. Next.",
    ],
)
def test_icu_stable_and_token_complete_holds(text):
    override = SentenceOverride(base="none", before=[_loaded(_next_upper())])
    expected = override.decide(text)
    for cut in range(len(text) + 1):
        assert _stream(override, [text[:cut], text[cut:]]) == expected

    breaker = override.stream()
    assert breaker.feed("Mr. S") == []
    assert any(item["offset"] == 4 for item in breaker.pending())
    assert breaker.feed("mith") == []

    single_letter = _rule(
        "single-letter",
        lookahead=1,
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": 1, "f": "shape.cased", "in": ["X"]},
        ],
        match="Mr. S arrived.",
    )
    breaker = SentenceOverride(base="none", before=[_loaded(single_letter)]).stream()
    assert breaker.feed("Mr. S") == []
    assert breaker.feed("mith") == []


def test_emitted_immutable_close_and_earlier_rule_exclusion():
    earlier = _rule(
        "earlier-three",
        lookahead=3,
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": 3, "f": "lower", "in": ["never"]},
        ],
        match="Mr. Smith Jones never.",
    )
    later = _next_upper("later-one")
    override = SentenceOverride(base="none", before=[_loaded(earlier, later)])
    breaker = override.stream()
    assert breaker.feed("Mr. Smith J") == []
    assert breaker.pending()[0]["waiting_on"] == "earlier-three"
    emitted = breaker.feed("ones Zebra ok")
    assert [(item["offset"], item["id"]) for item in emitted] == [(4, "later-one")]
    assert all(item["offset"] != 4 for item in breaker.pending())
    assert breaker.close()
    assert breaker.pending() == []
    assert breaker.close() == []
    with pytest.raises(RuntimeError, match="closed"):
        breaker.feed(" more")


def test_candidates_are_emitted_in_offset_order_behind_earlier_pending_rule():
    earlier = _rule(
        "earlier-three",
        lookahead=3,
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": 3, "f": "lower", "in": ["never"]},
        ],
        match="Mr. Smith Jones never.",
    )
    inventory = _word_only_inventory("arrived.", "arrived-word-only")
    rules = _loaded(earlier, _next_upper("later-one"), inventories=(inventory,))
    override = SentenceOverride(base="none", before=[rules], inventories=[inventory])
    breaker = override.stream()
    emitted = breaker.feed("Mr. Smith arrived. N")
    assert emitted == []
    assert [item["offset"] for item in breaker.pending()][:2] == [4, 19]
    emitted += breaker.feed("ext words.")
    emitted += breaker.close()
    assert emitted == override.decide("Mr. Smith arrived. Next words.")
    assert [item["offset"] for item in emitted] == sorted(item["offset"] for item in emitted)


def test_word_only_inventory_waits_for_its_locality_horizon():
    override = SentenceOverride(base="none", inventories=[_word_only_inventory()])
    breaker = override.stream()
    assert breaker.feed("Hello. N") == []
    assert breaker.pending()[0]["waiting_on"] == "exceptions"


def test_cross_candidate_exact_word_surface_waits_until_complete_or_divergent():
    override = SentenceOverride(base="none", inventories=[_cross_candidate_inventory()])
    prefix = "Mr. S"
    completion = "mith arrived."
    full_text = prefix + completion
    breaker = override.stream()
    assert breaker.feed(prefix) == []
    assert (
        next(item for item in breaker.pending() if item["offset"] == 4)["waiting_on"]
        == "exceptions"
    )
    streamed = breaker.feed(completion) + breaker.close()
    assert streamed == override.decide(full_text)
    assert (streamed[0]["offset"], streamed[0]["decision"], streamed[0]["layer"]) == (
        4,
        "no-break",
        "token",
    )

    near_miss = override.stream()
    assert near_miss.feed("Mr. Sm") == []
    emitted = near_miss.feed("y enough context. ")
    assert [(item["offset"], item["decision"], item["layer"]) for item in emitted] == [
        (4, "break", "icu")
    ]


def test_word_surface_starting_at_read_token_waits_under_every_chunking():
    inventory = _exact_word_inventory("Smith Jones", "smith-jones-word")
    rule = _rule(
        "next-smith",
        lookahead=1,
        when=[{"at": 1, "f": "text", "in": ["Smith"]}],
        match="Mr. Smith arrived.",
    )
    override = SentenceOverride(
        base="none", before=[_loaded(rule, inventories=(inventory,))], inventories=[inventory]
    )
    text = "Mr. Smith Jones."
    breaker = override.stream()
    assert breaker.feed("Mr. Smith Jo") == []
    streamed = breaker.feed("nes.") + breaker.close()
    assert streamed == override.decide(text)
    assert (streamed[0]["decision"], streamed[0]["layer"], streamed[0]["tokens_read"]) == (
        "break",
        "icu",
        1,
    )
    _assert_all_chunkings(override, text, seed=92971)


def test_word_surface_starting_after_plus_one_waits_under_every_chunking():
    inventory = _exact_word_inventory("Smith Jones", "later-smith-jones-word")
    rule = _rule(
        "second-smith",
        lookahead=2,
        when=[{"at": 2, "f": "text", "in": ["Smith"]}],
        match="Mr. Alpha Smith arrived.",
    )
    override = SentenceOverride(
        base="none", before=[_loaded(rule, inventories=(inventory,))], inventories=[inventory]
    )
    text = "Mr. Alpha Smith Jones."
    breaker = override.stream()
    assert breaker.feed("Mr. Alpha Smith Jo") == []
    streamed = breaker.feed("nes.") + breaker.close()
    assert streamed == override.decide(text)
    assert (streamed[0]["decision"], streamed[0]["layer"], streamed[0]["tokens_read"]) == (
        "break",
        "icu",
        2,
    )
    _assert_all_chunkings(override, text, seed=92972)


def test_collation_word_rule_unbounded_prefix_is_refused_by_stream_but_decide_works():
    text = "Mr. S" + "\N{COMBINING ACUTE ACCENT}" * 40 + "mith arrived."
    matches = collation_detect(text, "Mr. Smith", "test", locale="en", strength="primary")
    assert [(item["start"], item["end"]) for item in matches] == [(0, 49)]

    override = SentenceOverride(
        base="none", inventories=[_cross_candidate_inventory(variant="collation")]
    )
    with pytest.raises(
        ValueError,
        match="collation-variant word- or sentence-level exception rules.*whole-text API",
    ):
        override.stream()
    whole = override.decide(text)
    assert (whole[0]["offset"], whole[0]["decision"], whole[0]["layer"]) == (
        4,
        "no-break",
        "token",
    )


def test_collation_sentence_rule_is_also_refused_by_stream_but_decide_works():
    text = "Mr. S" + "\N{COMBINING ACUTE ACCENT}" * 40 + "mith arrived."
    override = SentenceOverride(
        base="none", inventories=[_cross_candidate_inventory(variant="collation", level="sentence")]
    )
    with pytest.raises(ValueError, match="collation-variant word- or sentence-level"):
        override.stream()
    whole = override.decide(text)
    assert (whole[0]["offset"], whole[0]["decision"], whole[0]["layer"]) == (
        4,
        "no-break",
        "exceptions",
    )


def test_collation_expansion_remains_supported_by_whole_text_decide():
    matches = collation_detect("Mr. Strasse", "Mr. Straße", "test", locale="de", strength="primary")
    assert [(item["start"], item["end"]) for item in matches] == [(0, 11)]

    override = SentenceOverride("de", inventories=[_strasse_word_inventory()])
    whole = override.decide("Mr. Strasse arrived.")
    assert (whole[0]["offset"], whole[0]["decision"], whole[0]["layer"]) == (
        4,
        "no-break",
        "token",
    )


def test_completed_conditional_word_surface_waits_until_right_context_is_decided():
    override = SentenceOverride(base="none", inventories=[_conditional_word_inventory()])

    matching = override.stream()
    assert matching.feed("Mr. Smith") == []
    assert matching.pending()[0]["waiting_on"] == "exceptions"
    assert matching.feed(" a") == []
    streamed = matching.feed("rrived.") + matching.close()
    assert streamed == override.decide("Mr. Smith arrived.")
    assert (streamed[0]["offset"], streamed[0]["decision"], streamed[0]["layer"]) == (
        4,
        "no-break",
        "token",
    )

    excluded = override.stream()
    assert excluded.feed("Mr. Smith") == []
    assert excluded.feed(" Jones.") == []
    emitted = excluded.feed(" X enough context beyond reach. ")
    assert (emitted[0]["offset"], emitted[0]["decision"], emitted[0]["layer"]) == (
        4,
        "break",
        "icu",
    )

    _assert_all_chunkings(override, "Mr. Smith arrived.", seed=7311)
    _assert_all_chunkings(override, "Mr. Smith Jones.", seed=7312)


def test_matching_word_condition_waits_until_adjacent_word_is_stable():
    override = SentenceOverride(base="none", inventories=[_conditional_word_inventory()])
    breaker = override.stream()
    assert breaker.feed("Mr. Smith arrived") == []
    assert breaker.pending()[0]["waiting_on"] == "exceptions"
    streamed = breaker.feed("x.") + breaker.close()
    assert streamed == override.decide("Mr. Smith arrivedx.")
    assert streamed[0]["decision"] == "break"


def test_named_list_condition_waits_for_icu_apostrophe_lookahead():
    override = SentenceOverride(base="none", inventories=[_apostrophe_sentence_inventory()])
    breaker = override.stream()
    assert breaker.feed("Mr. Smith arrived'") == []
    assert breaker.pending()[0]["waiting_on"] == "exceptions"
    streamed = breaker.feed("s.") + breaker.close()
    assert streamed == override.decide("Mr. Smith arrived's.")
    assert (streamed[0]["decision"], streamed[0]["layer"]) == ("no-break", "exceptions")


def test_wb4_format_run_named_list_matches_whole_text_under_every_chunking():
    override = SentenceOverride(base="none", inventories=[_conditional_word_inventory()])
    text = "Mr. Smith arrived'\N{SOFT HYPHEN}s."
    breaker = override.stream()
    assert breaker.feed("Mr. Smith arrived'\N{SOFT HYPHEN}") == []
    streamed = breaker.feed("s.") + breaker.close()
    assert streamed == override.decide(text)
    _assert_all_chunkings(override, text, seed=8801, random_count=300)


@pytest.mark.parametrize(
    ("text", "prefix", "expected", "witness"),
    [
        (
            "Mr. Smith'\N{COMBINING ACUTE ACCENT}\N{COMBINING ACUTE ACCENT}s arrived.",
            "Mr. Smith'\N{COMBINING ACUTE ACCENT}\N{COMBINING ACUTE ACCENT}",
            "Smith",
            "Mr. Smith arrived.",
        ),
        (
            "Mr. 42.\N{SOFT HYPHEN}5 arrived.",
            "Mr. 42.\N{SOFT HYPHEN}",
            "42",
            "Mr. 42. arrived.",
        ),
    ],
)
def test_wb4_token_reads_match_whole_text_under_every_chunking(text, prefix, expected, witness):
    rule = _rule(
        "wb4-token-read",
        lookahead=1,
        when=[{"at": 1, "f": "text", "in": [expected]}],
        match=witness,
    )
    override = SentenceOverride(base="none", before=[_loaded(rule)])
    breaker = override.stream()
    assert breaker.feed(prefix) == []
    streamed = breaker.feed(text[len(prefix) :]) + breaker.close()
    assert streamed == override.decide(text)
    _assert_all_chunkings(override, text, seed=8802 + len(text), random_count=300)


def test_real_matcher_handles_close_and_named_list_growth_under_every_chunking():
    override = SentenceOverride(base="none", inventories=[_quoted_mr_sentence_inventory()])
    text = 'I met "Mr." Smithson left.'
    prefix = 'I met "Mr." Smith'
    breaker = override.stream()
    assert breaker.feed(prefix) == []
    streamed = breaker.feed(text[len(prefix) :]) + breaker.close()
    assert streamed == override.decide(text)
    _assert_all_chunkings(override, text, seed=8805, random_count=300)


def test_unbounded_right_condition_waits_beyond_maximum_multiword_surface():
    inventory = _unbounded_right_sentence_inventory(
        "Mr. John Smith", "mr-john-smith-before-arrived"
    )
    override = SentenceOverride(base="none", inventories=[inventory])
    text = "Mr. John Smith arrived. Next"
    breaker = override.stream()
    assert breaker.feed("Mr. John Smith ") == []
    streamed = breaker.feed("arrived. Next") + breaker.close()
    assert streamed == override.decide(text)
    assert (streamed[0]["decision"], streamed[0]["layer"]) == ("no-break", "exceptions")
    _assert_all_chunkings(override, text, seed=8812, random_count=300)


@pytest.mark.parametrize("separator", ["\n", "\t", "\N{PARAGRAPH SEPARATOR}"])
def test_trailing_whitespace_candidate_waits_for_non_whitespace(separator):
    override = SentenceOverride(base="none")
    text = f"Hello{separator}  World."
    breaker = override.stream()
    assert breaker.feed(f"Hello{separator}  ") == []
    streamed = breaker.feed("World.") + breaker.close()
    assert streamed == override.decide(text)
    _assert_all_chunkings(override, text, seed=8810 + ord(separator), random_count=300)


def test_run_minus_one_survives_restart_before_hard_break_candidate():
    rule = _rule(
        "preceding-upper-run",
        lookahead=0,
        when=[{"at": "run-1", "f": "shape.cased", "in": ["XXXX."]}],
        match="UPPER.\n  target. Next.",
    )
    override = SentenceOverride(base="none", before=[_loaded(rule)])
    prefix = "Alpha. Beta. " * 400 + "UPPER.\n  "
    text = prefix + "target. Next."
    expected = override.decide(text)
    breaker = override.stream()
    emitted = breaker.feed(prefix)

    hard_break = prefix.index("\n") + 1
    assert any(item["offset"] == hard_break for item in breaker.pending())
    assert "UPPER." in breaker._text
    emitted += breaker.feed("target. Next.")
    emitted += breaker.close()
    assert emitted == expected
    decision = next(item for item in emitted if item["offset"] == hard_break)
    assert (decision["decision"], decision["id"]) == (
        "no-break",
        "preceding-upper-run",
    )


def test_false_sentence_exception_right_condition_does_not_hold_candidate():
    override = SentenceOverride(base="none", inventories=[_lowercase_sentence_inventory()])
    breaker = override.stream()
    emitted = breaker.feed("Mr. Smith J enough locality follows. ")
    assert [(item["offset"], item["decision"], item["layer"]) for item in emitted] == [
        (4, "break", "icu")
    ]
    assert all(item["offset"] != 4 for item in breaker.pending())


def test_early_decision_does_not_wait_for_maximum_lookahead():
    first = _next_upper("one-token")
    later = _rule(
        "three-token",
        lookahead=3,
        when=[{"at": 3, "f": "shape.cased", "in": ["Xxxxx"]}],
        match="Hello. A B Zebra.",
    )
    breaker = SentenceOverride(base="none", before=[_loaded(first, later)]).stream()
    # The feed completes token +1 by observing its whitespace terminator.
    decisions = breaker.feed("Mr. Smith J ")
    assert [(item["offset"], item["id"]) for item in decisions] == [(4, "one-token")]
    assert all(item["offset"] != 4 for item in breaker.pending())


def test_other_punctuation_edge_releases_zero_lookahead_rule_without_whitespace():
    rule = _rule(
        "bang",
        lookahead=0,
        when=[{"at": -1, "f": "text", "in": ["!"]}],
        match="A! B",
    )
    override = SentenceOverride(base="none", before=[_loaded(rule)])
    text = "A!B!C!D"
    expected = override.decide(text)
    breaker = override.stream()

    emitted = breaker.feed(text)

    assert emitted == expected[:3]
    assert [item["offset"] for item in emitted] == [2, 4, 6]
    assert breaker.pending() == [{"offset": 7, "tokens_after": 0, "waiting_on": "icu"}]
    assert emitted + breaker.close() == expected


def test_decided_before_rule_does_not_wait_for_sentence_inventory_locality():
    inventory = _cross_candidate_inventory(level="sentence")
    override = SentenceOverride(
        base="none",
        before=[_loaded(_next_upper(), inventories=(inventory,))],
        inventories=[inventory],
    )
    text = "Mr. Smith J "
    expected = override.decide(text)
    breaker = override.stream()

    emitted = breaker.feed(text)

    assert emitted == [expected[0]]
    assert (emitted[0]["offset"], emitted[0]["layer"], emitted[0]["id"]) == (
        4,
        "before",
        "next-upper",
    )
    assert all(item["offset"] != 4 for item in breaker.pending())
    assert emitted + breaker.close() == expected


def test_decided_before_rule_waits_for_word_inventory_merge():
    inventory = _cross_candidate_inventory()
    rule = _rule(
        "left-context-bos",
        lookahead=0,
        effect="break",
        when=[{"at": -3, "f": "text", "in": ["<BOS>"]}],
        match="Mr. Jones arrived.",
    )
    override = SentenceOverride(
        base="none",
        before=[_loaded(rule, inventories=(inventory,))],
        inventories=[inventory],
    )
    text = "Mr. Smith arrived."
    expected = override.decide(text)
    breaker = override.stream()

    assert breaker.feed("Mr. S") == []
    assert next(item for item in breaker.pending() if item["offset"] == 4)["waiting_on"] == (
        "exceptions"
    )
    streamed = breaker.feed("mith arrived.") + breaker.close()

    assert streamed == expected
    assert (streamed[0]["offset"], streamed[0]["decision"], streamed[0]["layer"]) == (
        4,
        "no-break",
        "token",
    )


def test_token_features_are_cached_once_and_cache_flag_is_semantic_noop(monkeypatch):
    calls = {}
    original = sentence_override_module._token_features_base

    def counted(toks, index, text, **kwargs):
        key = (toks[index]["start"], toks[index]["end"], toks[index]["text"])
        calls[key] = calls.get(key, 0) + 1
        return original(toks, index, text, **kwargs)

    monkeypatch.setattr(sentence_override_module, "_token_features_base", counted)
    cached = SentenceOverride(base="none", before=[_loaded(_next_upper())], cache=True)
    calls.clear()
    text = "Mr. Smith arrived. Next."
    expected = cached.decide(text)
    calls.clear()
    assert _stream(cached, ["Mr. S", "mith a", "rrived. Next."]) == expected
    assert calls and max(calls.values()) == 1
    uncached = SentenceOverride(base="none", before=[_loaded(_next_upper())], cache=False)
    assert _stream(uncached, ["Mr. S", "mith a", "rrived. Next."]) == expected


def test_cache_retains_future_lookbehind_tokens_after_pending_empties(monkeypatch):
    calls = {}
    original = sentence_override_module._token_features_base

    def counted(toks, index, text, **kwargs):
        key = (toks[index]["start"], toks[index]["end"], toks[index]["text"])
        calls[key] = calls.get(key, 0) + 1
        return original(toks, index, text, **kwargs)

    rule = _rule(
        "two-token-lookbehind",
        lookahead=0,
        when=[
            {"at": -1, "f": "text", "in": ["."]},
            {"at": -2, "f": "text", "in": ["B"]},
        ],
        match="A. B.\n\n",
    )
    loaded = _loaded(rule)
    monkeypatch.setattr(sentence_override_module, "_token_features_base", counted)
    breaker = SentenceOverride(base="none", before=[loaded], cache=True).stream()
    breaker.feed("A. B.\n\nC ")
    assert [item["offset"] for item in breaker.pending()] == [9]
    assert any(key[2] == "B" for key in breaker._cache.values)
    breaker.feed("C. D.\n\n")
    breaker.close()
    assert calls and max(calls.values()) == 1


def test_beyond_is_identical_under_every_two_piece_chunking():
    beyond = _rule(
        "beyond",
        lookahead=1,
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": "c+7", "f": "text", "in": ["<BEYOND>"]},
        ],
        match="Mr. A B C D E",
    )
    override = SentenceOverride(base="none", before=[_loaded(beyond)])
    for text in ("Mr. A B C D E", "Mr. Alexander"):
        expected = override.decide(text)
        if text == "Mr. A B C D E":
            assert expected[0]["id"] == "beyond"
        else:
            assert expected[0]["layer"] == "icu"
        for cut in range(len(text) + 1):
            assert _stream(override, [text[:cut], text[cut:]]) == expected


def test_gap_character_horizon_is_identical_under_every_chunking():
    gap = _rule(
        "gap",
        lookahead=1,
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": "c+2", "f": "text", "in": [" "]},
        ],
        match="Mr. A B",
    )
    override = SentenceOverride(base="none", before=[_loaded(gap)])
    text = "Mr. A B"
    expected = override.decide(text)
    assert (expected[0]["id"], expected[0]["tokens_read"]) == ("gap", 1)

    breaker = override.stream()
    emitted = breaker.feed("Mr. A ")
    assert emitted == expected[:1]
    assert emitted + breaker.feed("B") + breaker.close() == expected
    _assert_all_chunkings(override, text, seed=9141)


def test_beyond_at_next_token_start_is_identical_under_every_chunking():
    beyond = _rule(
        "beyond-at-start",
        lookahead=1,
        when=[
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
            {"at": "c+3", "f": "text", "in": ["<BEYOND>"]},
        ],
        match="Mr. A B continues.",
    )
    override = SentenceOverride(base="none", before=[_loaded(beyond)])
    text = "Mr. A B continues."
    expected = override.decide(text)
    assert (expected[0]["id"], expected[0]["tokens_read"]) == ("beyond-at-start", 1)

    breaker = override.stream()
    emitted = breaker.feed("Mr. A B")
    assert emitted == expected[:1]
    assert emitted + breaker.feed(" continues.") + breaker.close() == expected
    _assert_all_chunkings(override, text, seed=9142)


def test_unavailable_predicate_short_circuits_before_later_falsifier():
    rule = _rule(
        "unavailable-then-false",
        lookahead=1,
        when=[
            {"at": "c+7", "f": "text", "in": ["<BEYOND>"]},
            {"at": "run-1", "f": "shape.cased", "in": ["Xx."]},
        ],
        match="Mr. Smith Jones Zebra.",
    )
    override = SentenceOverride(base="none", before=[_loaded(rule)])
    text = "Hello. Alpha X"
    expected = override.decide(text)
    assert _stream(override, [text]) == expected
    assert _stream(override, ["Hello. A", "lpha X"]) == expected
    _assert_all_chunkings(override, text, seed=9138)


def test_streaming_protection_timing_and_watermark_seal():
    span = {"start": 0, "end": 9, "type": "name", "scope": "token"}
    watermark = SentenceOverride(base="none").stream(protection="watermark")
    assert watermark.feed("Mr. S") == []
    protected_decisions = watermark.feed("mith", protected=[span], protected_through=9)
    assert protected_decisions[0]["layer"] == "token"
    assert all(item["offset"] != 4 for item in watermark.close())

    unprotected = SentenceOverride(base="none").stream()
    assert unprotected.feed("Mr. S")[0]["offset"] == 4
    with pytest.raises(LateProtectedSpan):
        unprotected.feed("mith", protected=[span])

    override = SentenceOverride(base="none", before=[_loaded(_next_upper())])
    none = override.stream()
    assert none.feed("Mr. Smith J")[0]["offset"] == 4
    with pytest.raises(LateProtectedSpan):
        none.feed("ones", protected=[{"start": 5, "end": 9, "type": "name"}])

    protected = {"start": 6, "end": 9, "type": "name", "scope": "token"}
    marked = override.stream(protection="watermark")
    assert marked.feed("Mr. Smith J", protected_through=5) == []
    got = marked.feed("ones", protected=[protected], protected_through=15) + marked.close()
    assert got == override.decide("Mr. Smith Jones", protected=[protected])

    sealed = SentenceOverride(base="none").stream(protection="watermark")
    assert sealed.feed("Mr. Smith", protected_through=0) == []
    assert sealed.close() == SentenceOverride(base="none").decide("Mr. Smith")
    assert sealed.pending() == []

    flushed = SentenceOverride(base="none").stream(protection="watermark")
    flushed.feed("Mr. Smith", protected_through=0)
    flushed.flush()
    with pytest.raises(LateProtectedSpan):
        flushed.feed(" Jones", protected=[{"start": 2, "end": 4, "type": "late"}])


def test_protected_token_read_horizon_obeys_watermark():
    span = {"start": 0, "end": 9, "type": "name", "scope": "token"}
    breaker = SentenceOverride(base="none").stream(protection="watermark")
    assert breaker.feed("Mr. Smith N", protected=[span], protected_through=4) == []
    assert breaker.pending()[0] == {
        "offset": 4,
        "tokens_after": 1,
        "waiting_on": "protection",
    }
    emitted = breaker.feed("", protected_through=9)
    assert [(item["offset"], item["end"], item["decision"], item["layer"]) for item in emitted] == [
        (4, 9, "no-break", "token")
    ]


def test_inventory_locality_read_horizon_obeys_watermark():
    override = SentenceOverride(
        base="none", inventories=[_cross_candidate_inventory(level="sentence")]
    )
    text = "Mr. Smith " + "context " * 20
    breaker = override.stream(protection="watermark")
    assert breaker.feed(text, protected_through=4) == []
    assert breaker.pending()[0]["waiting_on"] == "protection"
    emitted = breaker.feed("", protected_through=len(text))
    assert emitted == override.decide(text)[: len(emitted)]
    assert (emitted[0]["offset"], emitted[0]["decision"], emitted[0]["layer"]) == (
        4,
        "no-break",
        "exceptions",
    )


def _shifted(decisions, offset):
    return [
        {**item, "offset": item["offset"] + offset, "end": item["end"] + offset}
        for item in decisions
    ]


def test_flush_starts_a_new_logical_segment():
    override = SentenceOverride(base="none")
    breaker = override.stream()
    emitted = breaker.feed("Hello.") + breaker.flush()
    emitted += breaker.feed(" Next. More") + breaker.close()
    assert [item["offset"] for item in emitted] == [6, 13, 17]
    assert emitted == override.decide("Hello.") + _shifted(override.decide(" Next. More"), 6)


def test_flush_discards_segment_local_feature_cache_coordinates():
    override = SentenceOverride(base="none", before=[_loaded(_next_upper())])
    breaker = override.stream()
    first = "Mr. Smith"
    emitted = breaker.feed(first) + breaker.flush()
    assert breaker._cache.values == {}
    emitted += breaker.feed(first) + breaker.close()
    assert emitted == override.decide(first) + _shifted(override.decide(first), len(first))


def test_random_flush_split_matches_two_shifted_whole_text_decisions():
    override = SentenceOverride(base="none")
    rng = random.Random(9303)
    atoms = ["Alpha.", '"No."', "beta?", "Gamma!", "😀", "42.", "\r\n", " "]
    for _ in range(100):
        text = " ".join(rng.choice(atoms) for _ in range(rng.randint(1, 8)))
        split = rng.randrange(len(text) + 1)
        left, right = text[:split], text[split:]
        breaker = override.stream()
        actual = breaker.feed(left) + breaker.flush() + breaker.feed(right) + breaker.close()
        expected = override.decide(left) + _shifted(override.decide(right), split)
        assert actual == expected


def test_every_authored_chunking_matches_whole_text_with_and_without_cache():
    texts = [
        "Mr. Smith met Dr. Jones.",
        'He said "No." then left.',
        "Prof. Ada wrote 42. Next line.\nDone.",
        "😀 Mr. Smith arrived. Why?",
        "U.S. policy changed. lower words followed.",
    ]
    rule_sets = [(), (_next_upper(),)]
    rng = random.Random(26017)
    for cache in (True, False):
        for rules in rule_sets:
            override = SentenceOverride(
                base="none",
                before=[_loaded(*rules, set_id=f"tests/property-{cache}-{len(rules)}")]
                if rules
                else (),
                cache=cache,
            )
            for text in texts:
                expected = override.decide(text)
                for first in range(len(text) + 1):
                    for second in range(first, len(text) + 1):
                        assert (
                            _stream_with_prefix_checks(
                                override,
                                [text[:first], text[first:second], text[second:]],
                                expected,
                            )
                            == expected
                        )
                for _ in range(200):
                    cuts = sorted(rng.randrange(len(text) + 1) for _ in range(rng.randint(0, 8)))
                    points = [0, *cuts, len(text)]
                    chunks = [
                        text[start:end] for start, end in zip(points, points[1:], strict=False)
                    ]
                    streamed = _stream_with_prefix_checks(override, chunks, expected)
                    assert streamed == expected
                    assert [item["offset"] for item in streamed] == sorted(
                        item["offset"] for item in streamed
                    )


def test_inventory_regressions_match_whole_text_under_every_authored_chunking():
    cases = [
        (
            SentenceOverride(base="none", inventories=[_cross_candidate_inventory()]),
            "Mr. Smith arrived.",
            7241,
        ),
        (
            SentenceOverride(base="none", inventories=[_cross_candidate_inventory()]),
            "Mr. Smyth arrived.",
            7242,
        ),
        (
            SentenceOverride(base="none", inventories=[_lowercase_sentence_inventory()]),
            "Mr. Smith Jones arrived.",
            7243,
        ),
        (
            SentenceOverride(base="none", inventories=[_conditional_word_inventory()]),
            "Mr. Smith arrived.",
            7245,
        ),
        (
            SentenceOverride(base="none", inventories=[_conditional_word_inventory()]),
            "Mr. Smith Jones.",
            7246,
        ),
    ]
    for override, text, seed in cases:
        _assert_all_chunkings(override, text, seed=seed)


def test_random_authored_exact_inventories_match_whole_text_under_every_chunking():
    vocabulary = [
        (level, condition)
        for level in ("word", "sentence")
        for condition in (None, "named_list", "unicode_set")
    ]
    rng = random.Random(90421)
    rng.shuffle(vocabulary)
    for index, (level, condition_kind) in enumerate(vocabulary):
        condition = None
        if condition_kind is not None:
            condition = {
                "id": f"right-{condition_kind}",
                "kind": condition_kind,
                "direction": "right",
                "skip": {"kind": "whitespace", "max": 8},
            }
        if condition_kind is None:
            positive_tail = "co-authored arrived's. Follow-up."
            negative_tail = "Jones-style. Follow-up."
        elif condition_kind == "named_list":
            assert condition is not None
            condition["list"] = "following"
            positive_tail = "arrived's. Follow-up."
            negative_tail = "Jones-style. Follow-up."
        else:
            assert condition is not None
            condition["set"] = "[[:Lowercase:]]"
            positive_tail = "co-authored. Follow-up."
            negative_tail = "Jones-style. Follow-up."
        rule = {
            "id": f"random-{index}-{level}-exact-{condition_kind}",
            "locale": "en",
            "level": [level],
            "effect": "suppress",
            "type": None,
            "surface": "Mr. Smith",
            "variant": "exact",
            "conditions": [] if condition is None else [condition],
            "unconditionality": "empirical" if condition is None else "conditional",
            "provenance": {"source": "authored randomized tests"},
            "witnesses": {
                "positive": f"Mr. Smith {positive_tail}",
                "near_miss": f"SomeMr. Smith {positive_tail}",
                "condition_negatives": (
                    [] if condition is None else [f"Mr. Smith {negative_tail}"]
                ),
            },
        }
        inventory = load_exception_inventory(
            {
                "schema_version": 1,
                "corpus": f"random authored inventory {index}",
                "named_lists": {"following": ["arrived's"]},
                "rules": [rule],
            }
        )
        override = SentenceOverride(base="none", inventories=[inventory])
        for text in (
            f"Mr. Smith {positive_tail}",
            f"Mr. Smith {negative_tail}",
        ):
            _assert_all_chunkings(override, text, seed=rng.randrange(1 << 30))


def test_random_multiword_exact_surfaces_match_whole_text_under_every_chunking():
    rng = random.Random(92973)
    words = ["Smith", "Jones", "Taylor", "Morgan", "River"]
    for index in range(8):
        surface_words = rng.sample(words, rng.randint(2, 4))
        surface = " ".join(surface_words)
        lead = rng.choice(([], ["Alpha"]))
        at = len(lead) + 1
        inventory = _exact_word_inventory(surface, f"random-multiword-{index}")
        rule = _rule(
            f"read-multiword-start-{index}",
            lookahead=at,
            when=[{"at": at, "f": "text", "in": [surface_words[0]]}],
            match=f"Mr. {' '.join([*lead, surface_words[0], 'Solo.'])}",
        )
        override = SentenceOverride(
            base="none",
            before=[_loaded(rule, set_id=f"random-multiword-{index}", inventories=(inventory,))],
            inventories=[inventory],
        )
        text = f"Mr. {' '.join([*lead, *surface_words])}."
        _assert_all_chunkings(override, text, seed=rng.randrange(1 << 30))


def test_random_word_inventories_precede_zero_lookahead_left_context_rules():
    rng = random.Random(92981)
    abbreviations = [("Mr.", "Mr"), ("Dr.", "Dr"), ("Prof.", "Prof")]
    words = ["Smith", "Jones", "Taylor", "Morgan", "River"]
    for index in range(8):
        abbreviation, stem = rng.choice(abbreviations)
        surface = " ".join([abbreviation, *rng.sample(words, rng.randint(1, 3))])
        inventory = _exact_word_inventory(surface, f"random-left-word-{index}")
        predicates = [{"at": -3, "f": "text", "in": ["<BOS>"]}]
        if rng.choice((False, True)):
            predicates.append({"at": -2, "f": "text", "in": [stem]})
        if rng.choice((False, True)):
            predicates.append({"at": -1, "f": "text", "in": ["."]})
        rule = _rule(
            f"random-left-before-{index}",
            lookahead=0,
            effect=rng.choice(("break", "ambiguous")),
            when=predicates,
            match=f"{abbreviation} Solo arrived.",
        )
        rule["witnesses"]["no_match"] = ["One two three. More followed."]
        override = SentenceOverride(
            base="none",
            before=[
                _loaded(
                    rule,
                    set_id=f"random-left-before-{index}",
                    inventories=(inventory,),
                )
            ],
            inventories=[inventory],
        )
        text = f"{surface} arrived. Next."

        _assert_all_chunkings(
            override,
            text,
            seed=rng.randrange(1 << 30),
            random_count=300,
        )


def test_random_multiword_unbounded_inventories_obey_chunking_and_watermarks():
    rng = random.Random(92979)
    words = ["Smith", "Jones", "Taylor", "Morgan", "River"]
    following_words = ["arrived", "continued", "answered", "returned"]
    for index in range(8):
        surface = " ".join(["Mr.", *rng.sample(words, rng.randint(2, 4))])
        following = rng.choice(following_words)
        inventory = _unbounded_right_sentence_inventory(
            surface,
            f"random-unbounded-multiword-{index}",
            following,
        )
        override = SentenceOverride(base="none", inventories=[inventory])
        separator = rng.choice([" ", "  ", "\t"])
        text = f"{surface}{separator}{following}. Next protected tail "
        _assert_all_chunkings(
            override,
            text,
            seed=rng.randrange(1 << 30),
            random_count=300,
        )

        protected_start = text.index("protected")
        protected = [
            {
                "start": protected_start,
                "end": protected_start + len("protected"),
                "type": "property-tail",
                "scope": "token",
            }
        ]
        expected = override.decide(text, protected=protected)
        for _ in range(30):
            streamed, emitted_at = _random_watermark_stream(
                override,
                text,
                protected,
                rng,
            )
            assert streamed == expected
            assert all(
                item in expected and horizon <= watermark for item, horizon, watermark in emitted_at
            )


def test_random_unicode_prefixes_inventories_and_rules_match_every_chunking():
    rng = random.Random(8808)
    alphabet = [
        "'",
        ".",
        ":",
        "\N{SOFT HYPHEN}",
        "\N{COMBINING ACUTE ACCENT}",
        "\N{ZERO WIDTH JOINER}",
        "\N{NO-BREAK SPACE}",
        '"',
        "\r",
        "\n",
        "\N{PARAGRAPH SEPARATOR}",
        "4",
        "A",
        "s",
    ]
    surfaces = ["Mr.", "A.", "7."]
    for index in range(8):
        surface = rng.choice(surfaces)
        level = rng.choice(["word", "sentence"])
        inventory = load_exception_inventory(
            {
                "schema_version": 1,
                "corpus": f"random unicode inventory {index}",
                "named_lists": {},
                "rules": [
                    {
                        "id": f"random-unicode-inventory-{index}",
                        "locale": "en",
                        "level": [level],
                        "effect": "suppress",
                        "type": None,
                        "surface": surface,
                        "variant": "exact",
                        "conditions": [],
                        "unconditionality": "empirical",
                        "provenance": {"source": "authored randomized tests"},
                        "witnesses": {
                            "positive": f"I met {surface} Smith today. ",
                            "near_miss": f"I met Some{surface} Smith today. ",
                            "condition_negatives": [],
                        },
                    }
                ],
            }
        )
        rule = _next_upper(f"random-unicode-rule-{index}")
        rules = _loaded(
            rule,
            set_id=f"tests/random-unicode-{index}",
            inventories=(inventory,),
        )
        override = SentenceOverride(base="none", before=[rules], inventories=[inventory])
        # The first cases cover every alphabet member; later cases resample it.
        if index < 2:
            body = "".join(alphabet[index * 7 : (index + 1) * 7])
        else:
            body = "".join(rng.choice(alphabet) for _ in range(7))
        text = f"Mr. {body} Z."
        _assert_all_chunkings(
            override,
            text,
            seed=rng.randrange(1 << 30),
            random_count=300,
        )
