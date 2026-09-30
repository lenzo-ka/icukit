"""Tests for ICU classes, windows, shapes, and sentence-break token features."""

from __future__ import annotations

import icu
import pytest

from icukit import (
    Breaker,
    OverlappingProtectedSpans,
    char_classes,
    class_window,
    cvletters_counts,
    load_exception_inventory,
    shape,
    shape_scheme,
    token_features,
    tokens,
)
from icukit import classes as classes_module
from icukit.shape import _DEFINITIONS, _identity_digest


@pytest.mark.parametrize(
    ("text", "coarse", "cased"),
    [
        ("5-10", "N-N", "d-dd"),
        ("2008-09-30", "N-N-N", "dddd-dd-dd"),
        ("1,000", "N,N", "d,ddd"),
        ("e.g.", "A.A.", "x.x."),
        ("St.", "A.", "Xx."),
        ("Mr.", "A.", "Xx."),
        ("F.", "A.", "X."),
        ("Prof.", "A.", "Xxxx."),
        ("U.S.", "A.A.", "X.X."),
        ("3.", "N.", "d."),
        ("I", "<Lu>", "X"),
        ("$3.50", "¤N.N", "¤d.dd"),
        ("3:15", "N:N", "d:dd"),
        ("٣/٤", "N/N", "d/d"),
        ("McDonald", "A", "XxXxxxx"),
        ("iPhone", "A", "xXxxxx"),
        ("日本語", "A", "aaa"),
        ("ภาษาไทย", "A", "aaaa"),
        ("x86-64", "AN-N", "xdd-dd"),
        ("2nd", "NA", "dxx"),
        ("O'Neil", "A'A", "X'Xxxx"),
        ("Mr. Smith", "A. A", "Xx. Xxxxx"),
        ("–", "–", "–"),
        ("Ⅻ", "Ⅻ", "Ⅻ"),
        ("½", "½", "½"),
        ("\ue000", "\ue000", "\ue000"),
        ("😀", "😀", "😀"),
        ("", "", ""),
        ("e\u0301", "A", "x"),
        ("A\u030a", "<Lu>", "X"),
        ("ǅ", "A", "X"),
        ("हिन्दी", "A", "aaa"),
        ("q\u0303", "A", "x"),
        ("5 किलोमीटर", "N A", "d aaaa"),
        ("5⃣", "N", "d"),
        ("5️⃣", "N", "d"),
        ("\u1c89", "<Lu>", "X"),
        ("\U00016d40", "A", "a"),
        ("\U0001e5d0", "A", "a"),
        ("\U00010d40", "N", "d"),
    ],
)
def test_shape_plan_table(text, coarse, cased):
    assert shape(text, "coarse@1") == coarse
    assert shape(text, "cased@1") == cased


def test_shape_scheme_identity_uses_runtime_versions_and_canonical_definition():
    first = shape_scheme("coarse@1")
    second = shape_scheme("coarse@1")

    assert first == second
    assert first["name"] == "coarse"
    assert first["version"] == 1
    assert first["icu"] == icu.ICU_VERSION
    assert first["unicode"] == icu.UNICODE_VERSION
    assert first["extensions"] == []
    assert first["digest"].startswith("sha256:")
    assert len(first["digest"]) == len("sha256:") + 64

    coarse_definition = _DEFINITIONS["coarse@1"]
    changed_definition = {**coarse_definition, "other": "changed"}
    assert first["digest"] == _identity_digest(
        coarse_definition, icu.ICU_VERSION, icu.UNICODE_VERSION
    )
    assert first["digest"] != _identity_digest(
        changed_definition, icu.ICU_VERSION, icu.UNICODE_VERSION
    )
    assert first["digest"] != _identity_digest(
        coarse_definition, f"{icu.ICU_VERSION}-changed", icu.UNICODE_VERSION
    )
    assert first["digest"] != _identity_digest(
        coarse_definition, icu.ICU_VERSION, f"{icu.UNICODE_VERSION}-changed"
    )
    assert first["digest"] != shape_scheme("cased@1")["digest"]


def test_unknown_shape_scheme_is_refused():
    with pytest.raises(ValueError, match="unknown shape scheme"):
        shape("word", "coarse")
    with pytest.raises(ValueError, match="unknown shape scheme"):
        shape_scheme("cased@2")


def test_cased_shape_caps_a_run_at_four():
    assert shape("Kennedy", "cased@1") == "Xxxxx"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("pdf", "CCC"),
        ("Gbit", "CCVC"),
        ("fMRI", "CCCV"),
        ("Det", "CVC"),
        ("yew", "YVY"),
        ("strengths", "CCCVCCCC"),
        ("B2B", "CNC"),
        ("café", "CVCV"),
    ],
)
def test_cvletters_english_examples(text, expected):
    assert shape(text, "cvletters@1", locale="en_US") == expected


def test_cvletters_uses_runtime_indic_syllabic_categories_only_on_letters_and_marks():
    prop = icu.UProperty.INDIC_SYLLABIC_CATEGORY
    long = icu.UPropertyNameChoice.LONG_PROPERTY_NAME

    def indic_category(char):
        return icu.Char.getPropertyValueName(
            prop, icu.Char.getIntPropertyValue(ord(char), prop), long
        )

    assert [indic_category(char) for char in "नमस्ते"] == [
        "Consonant",
        "Consonant",
        "Consonant",
        "Virama",
        "Consonant",
        "Vowel_Dependent",
    ]
    assert indic_category("-") == indic_category("\N{NO-BREAK SPACE}") == "Consonant_Placeholder"
    assert shape("नमस्ते", "cvletters@1") == "CCCCV"
    assert shape("-\N{NO-BREAK SPACE}", "cvletters@1") == "-\N{NO-BREAK SPACE}"


@pytest.mark.parametrize(
    ("text", "locale", "expected"),
    [
        ("abc", None, "LLL"),
        ("abc", "fr", "LLL"),
        ("日本", None, "LL"),
        ("λόγος", "en", "LLLL"),
    ],
)
def test_cvletters_unknown_alphabet_fallback(text, locale, expected):
    assert shape(text, "cvletters@1", locale=locale) == expected


def test_cvletters_counts_are_uncapped_and_exclude_nonletters():
    assert cvletters_counts("pdf", locale="en_US") == {
        "letters": 3,
        "vowels": 0,
        "consonants": 3,
        "has_vowel": False,
    }
    assert cvletters_counts("Gbit", locale="en_US") == {
        "letters": 4,
        "vowels": 1,
        "consonants": 3,
        "has_vowel": True,
    }
    assert cvletters_counts("नमस्ते") == {
        "letters": 5,
        "vowels": 1,
        "consonants": 4,
        "has_vowel": True,
    }
    unknown = cvletters_counts("abc123")
    assert unknown == {"letters": 3, "vowels": 0, "consonants": 0, "has_vowel": False}
    assert unknown["letters"] > unknown["vowels"] + unknown["consonants"]


def test_cvletters_scheme_identity_is_stable_and_locale_independent():
    expected = "sha256:9a534bef51126e025d7a4a0a73f34294f16c75268b8df4be8ace3afcb12c449a"
    info = shape_scheme("cvletters@1")
    assert info["name"] == "cvletters"
    assert info["version"] == 1
    assert info["digest"] == expected
    assert shape_scheme("cvletters@1", locale="en_US") == info


@pytest.mark.parametrize(
    ("text", "coarse", "cased"),
    [
        ("ASCII", "A", "XXXX"),
        ("12345", "N", "dddd"),
        ("$£€", "¤", "¤¤¤"),
        ("e\u0301", "A", "x"),
        ("नमस्ते", "A", "aaaa"),
        ("日本", "A", "aa"),
        ("U.S.", "A.A.", "X.X."),
        ("I", "<Lu>", "X"),
    ],
)
def test_legacy_shape_outputs_remain_exact(text, coarse, cased):
    assert shape(text, "coarse@1") == coarse
    assert shape(text, "cased@1") == cased


def test_legacy_shape_digests_remain_exact():
    assert (
        shape_scheme("coarse@1")["digest"]
        == "sha256:c2a3a2a09014262563a18b3e2037a02a69245096c0bd8d76585b60743bd1269b"
    )
    assert (
        shape_scheme("cased@1")["digest"]
        == "sha256:9c7bdf87ed656cae0c137ce2cab6bb44bc8c83d48eb1acba0c278e378bbddba8"
    )


def test_char_classes_are_long_and_property_aliases_are_canonicalized():
    assert char_classes("Mr. 5", "sentence_break") == [
        "Upper",
        "Lower",
        "ATerm",
        "Sp",
        "Numeric",
    ]
    assert char_classes(".", "SB") == ["ATerm"]
    assert char_classes("A", "gc") == ["Uppercase_Letter"]
    assert classes_module._canonical_value("word_break", "LE") == "ALetter"
    assert classes_module._canonical_value("sentence_break", "LE") == "OLetter"


def test_property_alphabets_are_enumerated_from_the_runtime():
    runtime = {}
    for name, prop_id in classes_module._PROPERTY_IDS.items():
        runtime[name] = tuple(
            icu.Char.getPropertyValueName(
                prop_id, value, icu.UPropertyNameChoice.LONG_PROPERTY_NAME
            )
            for value in range(
                icu.Char.getIntPropertyMinValue(prop_id),
                icu.Char.getIntPropertyMaxValue(prop_id) + 1,
            )
        )
    assert classes_module._PROPERTY_ALPHABETS == runtime
    if icu.ICU_VERSION == "78.3":
        assert {name: len(values) for name, values in runtime.items()} == {
            "word_break": 23,
            "sentence_break": 15,
            "general_category": 30,
            "script": 213,
        }
        assert "WSegSpace" in runtime["word_break"]


def test_property_alphabet_enumeration_uses_supplied_accessors():
    prop_id = classes_module._PROPERTY_IDS["word_break"]
    real_maximum = icu.Char.getIntPropertyMaxValue(prop_id)

    def fake_maximum(candidate: int) -> int:
        return icu.Char.getIntPropertyMaxValue(candidate) + 1

    def fake_name(candidate: int, value: int, choice: int) -> str:
        if candidate == prop_id and value == real_maximum + 1:
            return "Future_Value"
        return icu.Char.getPropertyValueName(candidate, value, choice)

    values = classes_module._property_values(
        prop_id,
        icu.UPropertyNameChoice.LONG_PROPERTY_NAME,
        get_min_value=icu.Char.getIntPropertyMinValue,
        get_max_value=fake_maximum,
        get_value_name=fake_name,
    )

    assert values[:-1] == classes_module._PROPERTY_ALPHABETS["word_break"]
    assert values[-1] == "Future_Value"


def test_class_window_values_short_names_padding_and_identity():
    long = class_window("Mr. Smith", 3, before=3, after=2)
    short = class_window("Mr. Smith", 3, before=3, after=2, names="short")

    assert long.before[-1].text == "."
    assert (
        long.before[-1].word_break,
        long.before[-1].sentence_break,
        long.before[-1].general_category,
        long.before[-1].script,
    ) == ("MidNumLet", "ATerm", "Other_Punctuation", "Common")
    assert (
        short.before[-1].sentence_break,
        short.before[-1].general_category,
        short.before[-1].script,
    ) == ("AT", "Po", "Zyyy")
    assert long.identity == short.identity

    start = class_window("A", 0, before=2, after=0)
    cut_start = class_window("A", 0, before=2, after=0, text_starts=False)
    assert len(start.before) == len(cut_start.before) == 2
    assert all(
        point.word_break
        == point.sentence_break
        == point.general_category
        == point.script
        == "<BOS>"
        for point in start.before
    )
    assert all(point.word_break == "<PAD>" for point in cut_start.before)

    end = class_window("A", 1, before=0, after=2)
    cut_end = class_window("A", 1, before=0, after=2, text_ends=False)
    assert len(end.after) == len(cut_end.after) == 2
    assert all(point.word_break == "<EOS>" for point in end.after)
    assert all(point.word_break == "<PAD>" for point in cut_end.after)


def test_tokens_default_and_token_features_plan_examples():
    found = tokens("the U.S. Then", "en_US")
    assert found == [
        {"start": 0, "end": 3, "text": "the", "run": 0},
        {"start": 4, "end": 7, "text": "U.S", "run": 1},
        {"start": 7, "end": 8, "text": ".", "run": 1},
        {"start": 9, "end": 13, "text": "Then", "run": 2},
    ]
    assert token_features(found, 3, "the U.S. Then") == {
        "text": "Then",
        "lower": "then",
        "len": 4,
        "shape.coarse": "A",
        "shape.cased": "Xxxx",
        "shape.cvletters": "LLLL",
        "cvletters.has_vowel": False,
        "cvletters.letters": 4,
        "cvletters.vowels": 0,
        "cvletters.consonants": 0,
        "general_category.first": "Uppercase_Letter",
        "general_category.last": "Lowercase_Letter",
        "sentence_break.first": "Upper",
        "word_break.first": "ALetter",
        "script.first": "Latin",
        "ws.before": True,
        "run.shape.cased": "Xxxx",
        "lex": "none",
    }


def test_token_features_cvletters_values_use_token_surface_and_locale():
    found = tokens("a Gbit token", "en_US")
    features = token_features(found, 1, "a Gbit token", locale="en_US")
    assert {key: features[key] for key in features if key.startswith("cvletters.")} == {
        "cvletters.has_vowel": True,
        "cvletters.letters": 4,
        "cvletters.vowels": 1,
        "cvletters.consonants": 3,
    }
    assert features["shape.cvletters"] == "CCVC"


def test_token_features_lowercase_is_independent_of_default_locale():
    original = icu.Locale.getDefault()
    try:
        icu.Locale.setDefault(icu.Locale("tr_TR"))
        found = tokens("I", "en_US")
        assert token_features(found, 0, "I")["lower"] == "i"
    finally:
        icu.Locale.setDefault(original)


@pytest.mark.parametrize(
    ("text", "start", "end", "type_name"),
    [
        ("from 5-10 m", 5, 9, "range"),
        ("on 2008-09-30 now", 3, 13, "date:iso"),
        ("about 1,000 things", 6, 11, "number:cardinal"),
        ("say e.g. this", 4, 8, "abbreviation"),
        ("see https://x.test/a now", 4, 20, "url"),
    ],
)
def test_protected_span_is_one_token_with_exact_offsets(text, start, end, type_name):
    found = tokens(text, "en_US", protected=[{"start": start, "end": end, "type": type_name}])
    protected = next(token for token in found if token.get("protected"))
    assert protected == {
        "start": start,
        "end": end,
        "text": text[start:end],
        "run": protected["run"],
        "protected": type_name,
        "protected_types": (type_name,),
    }


def test_protected_span_run_numbers_are_literal():
    found = tokens(
        "from 5-10 m",
        "en_US",
        protected=[{"start": 5, "end": 9, "type": "range"}],
    )
    assert next(token for token in found if token["text"] == "5-10")["run"] == 1
    assert next(token for token in found if token["text"] == "m")["run"] == 2


def test_protected_span_collapses_runs_and_nested_outermost_wins():
    spans = [
        {"start": 0, "end": 9, "type": "person"},
        {"start": 4, "end": 9, "type": "surname"},
    ]
    found = tokens("Mr. Smith went", "en_US", protected=spans)

    assert found == [
        {
            "start": 0,
            "end": 9,
            "text": "Mr. Smith",
            "run": 0,
            "protected": "person",
            "protected_types": ("person",),
        },
        {"start": 10, "end": 14, "text": "went", "run": 1},
    ]
    assert found[0]["run"] == 0
    assert found[1]["run"] == 1


def test_equal_extent_types_coalesce_and_partial_overlap_raises():
    found = tokens(
        "5-10",
        "en_US",
        protected=[
            {"start": 0, "end": 4, "type": "number:range"},
            {"start": 0, "end": 4, "type": "date:span"},
        ],
    )
    assert found == [
        {
            "start": 0,
            "end": 4,
            "text": "5-10",
            "run": 0,
            "protected": "date:span",
            "protected_types": ("date:span", "number:range"),
        }
    ]
    with pytest.raises(OverlappingProtectedSpans):
        tokens(
            "abcdef",
            "en_US",
            protected=[
                {"start": 0, "end": 4, "type": "first"},
                {"start": 2, "end": 6, "type": "second"},
            ],
        )


def test_hint_spans_do_not_merge_tokens():
    assert tokens(
        "5-10",
        "en_US",
        protected=[{"start": 0, "end": 4, "type": "number:range", "scope": "hint"}],
    ) == tokens("5-10", "en_US")


def test_word_inventory_merges_before_tokens_are_returned():
    inventory = load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "authored token test",
            "named_lists": {},
            "rules": [
                {
                    "id": "eg-word",
                    "locale": "en",
                    "level": "word",
                    "effect": "suppress",
                    "surface": "e.g.",
                    "variant": "exact",
                    "conditions": [],
                    "unconditionality": "empirical",
                    "provenance": {"source": "authored"},
                    "witnesses": {
                        "positive": "Use e.g. this",
                        "near_miss": "Use Cone.g. this",
                        "condition_negatives": [],
                    },
                }
            ],
        }
    )
    assert tokens("Use e.g. this", "en_US", inventory=inventory) == [
        {"start": 0, "end": 3, "text": "Use", "run": 0},
        {"start": 4, "end": 8, "text": "e.g.", "run": 1},
        {"start": 9, "end": 13, "text": "this", "run": 2},
    ]


def _new_york_inventory():
    return load_exception_inventory(
        {
            "schema_version": 1,
            "corpus": "authored whitespace token test",
            "named_lists": {},
            "rules": [
                {
                    "id": "new-york-word",
                    "locale": "en",
                    "level": "word",
                    "effect": "suppress",
                    "surface": "New York",
                    "variant": "exact",
                    "conditions": [],
                    "unconditionality": "empirical",
                    "provenance": {"source": "authored"},
                    "witnesses": {
                        "positive": "New York City",
                        "near_miss": "OldNew York City",
                        "condition_negatives": [],
                    },
                }
            ],
        }
    )


def test_word_inventory_whitespace_merge_collapses_runs():
    inventory = _new_york_inventory()

    assert tokens("New York City", "en_US", inventory=inventory) == [
        {"start": 0, "end": 8, "text": "New York", "run": 0},
        {"start": 9, "end": 13, "text": "City", "run": 1},
    ]


def _token_details(found, text):
    return [
        (
            token["text"],
            token["start"],
            token["end"],
            token["run"],
            token_features(found, index, text)["ws.before"],
        )
        for index, token in enumerate(found)
    ]


def test_protected_span_partially_overlapping_inventory_merge_drops_whole_merge():
    text = "New York City"
    protected = [{"start": 4, "end": 13, "type": "place"}]

    for inventory in (None, _new_york_inventory()):
        found = tokens(text, "en_US", inventory=inventory, protected=protected)
        assert _token_details(found, text) == [
            ("New", 0, 3, 0, False),
            ("York City", 4, 13, 1, True),
        ]


def test_inventory_merge_wholly_inside_protected_span_disappears():
    text = "New York City"
    protected = [{"start": 0, "end": 13, "type": "place"}]

    for inventory in (None, _new_york_inventory()):
        found = tokens(text, "en_US", inventory=inventory, protected=protected)
        assert _token_details(found, text) == [("New York City", 0, 13, 0, False)]


def test_protected_span_wholly_inside_inventory_merge_drops_whole_merge():
    text = "New York City"
    protected = [{"start": 0, "end": 3, "type": "place"}]

    for inventory in (None, _new_york_inventory()):
        found = tokens(text, "en_US", inventory=inventory, protected=protected)
        assert _token_details(found, text) == [
            ("New", 0, 3, 0, False),
            ("York", 4, 8, 1, True),
            ("City", 9, 13, 2, True),
        ]


@pytest.mark.parametrize(
    ("text", "protected"),
    [
        ("New York City", [{"start": 0, "end": 3, "type": "place"}]),
        ("New York City", [{"start": 4, "end": 13, "type": "place"}]),
        ("Meet New York today", [{"start": 5, "end": 8, "type": "place"}]),
        ("New York City", [{"start": 3, "end": 8, "type": "place"}]),
    ],
)
def test_only_protected_tokens_may_have_edge_whitespace(text, protected):
    for inventory in (None, _new_york_inventory()):
        for token in tokens(text, "en_US", inventory=inventory, protected=protected):
            if "protected" not in token:
                assert not token["text"][0].isspace()
                assert not token["text"][-1].isspace()


def test_tokens_translate_icu_utf16_offsets_to_code_points():
    assert tokens("😀 Hi", "en_US") == [
        {"start": 0, "end": 1, "text": "😀", "run": 0},
        {"start": 2, "end": 4, "text": "Hi", "run": 1},
    ]


@pytest.mark.parametrize(
    ("text", "sentences", "words"),
    [
        ("Hello. World!", ["Hello. ", "World!"], ["Hello", ".", "World", "!"]),
        ("Mr. Smith left.", ["Mr. ", "Smith left."], ["Mr", ".", "Smith", "left", "."]),
        (
            "日本語です。次です。",
            ["日本語です。", "次です。"],
            ["日本語", "です", "。", "次", "です", "。"],
        ),
    ],
)
def test_breaker_authored_regression(text, sentences, words):
    breaker = Breaker("en_US")
    assert breaker.break_sentences(text) == sentences
    assert breaker.break_words(text) == words
