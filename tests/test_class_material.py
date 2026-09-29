"""Add-only character-class and shape-refinement material."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import icu
import pytest

from icukit import (
    MaterialLoadError,
    char_classes,
    class_window,
    load_locale_material,
    shape,
    shape_scheme,
)

DATA = Path(__file__).parent / "data" / "material"
PUA_DIGEST = "sha256:295b930b1d8c0215769f070a219065a4ce1671a2edb629fa4250cbc106dc4f18"

# Recorded by executing shape.py from the A1 parent commit 9c97195. This fixed
# authored set is the complete plan table: ASCII, marks, PUA, and Unicode 17.
A1_SHAPE_GOLDEN = [
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
]
A1_CLASS_TEXT = "Az. 5\u0334\ue000\u1c89\U00016d40\U0001e5d0\U00010d40"
A1_CLASS_GOLDEN = {
    "word_break": [
        "ALetter",
        "ALetter",
        "MidNumLet",
        "WSegSpace",
        "Numeric",
        "Extend",
        "Other",
        "ALetter",
        "ALetter",
        "ALetter",
        "Numeric",
    ],
    "sentence_break": [
        "Upper",
        "Lower",
        "ATerm",
        "Sp",
        "Numeric",
        "Extend",
        "Other",
        "Upper",
        "OLetter",
        "OLetter",
        "Numeric",
    ],
    "general_category": [
        "Uppercase_Letter",
        "Lowercase_Letter",
        "Other_Punctuation",
        "Space_Separator",
        "Decimal_Number",
        "Nonspacing_Mark",
        "Private_Use",
        "Uppercase_Letter",
        "Modifier_Letter",
        "Other_Letter",
        "Decimal_Number",
    ],
    "script": [
        "Latin",
        "Latin",
        "Common",
        "Common",
        "Common",
        "Inherited",
        "Unknown",
        "Cyrillic",
        "Kirat_Rai",
        "Ol_Onal",
        "Garay",
    ],
}
A1_SCHEME_GOLDEN = {
    "name": "coarse",
    "version": 1,
    "icu": "78.3",
    "unicode": "17.0",
    "extensions": [],
    "digest": "sha256:c2a3a2a09014262563a18b3e2037a02a69245096c0bd8d76585b60743bd1269b",
}
A1_CASED_SCHEME_GOLDEN = {
    "name": "cased",
    "version": 1,
    "icu": "78.3",
    "unicode": "17.0",
    "extensions": [],
    "digest": "sha256:9c7bdf87ed656cae0c137ce2cab6bb44bc8c83d48eb1acba0c278e378bbddba8",
}


def _pua_mapping():
    return json.loads((DATA / "qaa-classlike.json").read_text())


def _char_material():
    return {
        "schema_version": 1,
        "kind": "char-classes",
        "id": "example/vowels",
        "status": "experimental",
        "locale": "qaa",
        "classes": [{"name": "example:vowel", "members": ["a", "U+0065"]}],
        "provenance": {"source": "synthetic test"},
        "witnesses": [
            {
                "id": "vowels-w1",
                "text": "axe",
                "expect": {"codepoint_classes": [["example:vowel"], [], ["example:vowel"]]},
            }
        ],
    }


def _shape_material():
    return {
        "schema_version": 1,
        "kind": "shape-refinement",
        "id": "example/uppercase",
        "status": "experimental",
        "locale": "qaa",
        "shape_refinements": [
            {"name": "example:uppercase-run", "class": "Lu", "symbol": "<upper>"}
        ],
        "provenance": {"source": "synthetic test"},
        "witnesses": [
            {
                "id": "uppercase-w1",
                "text": "AA",
                "expect": {"shapes": {"example:uppercase-run": "<upper>"}},
            }
        ],
    }


def _codes(error: MaterialLoadError) -> set[str]:
    return {item.code for item in error.refusals}


def _direct_icu_base_fields(char: str) -> tuple[str, str, str, str]:
    choice = icu.UPropertyNameChoice.LONG_PROPERTY_NAME
    return tuple(
        icu.Char.getPropertyValueName(
            prop,
            icu.Char.getIntPropertyValue(ord(char), prop),
            choice,
        )
        for prop in (
            icu.UProperty.WORD_BREAK,
            icu.UProperty.SENTENCE_BREAK,
            icu.UProperty.GENERAL_CATEGORY,
            icu.UProperty.SCRIPT,
        )
    )


def _base_fields(point) -> tuple[str, str, str, str]:
    return (
        point.word_break,
        point.sentence_break,
        point.general_category,
        point.script,
    )


def test_plan_pua_fixture_digest_witnesses_and_add_only_base_fields():
    material = load_locale_material(DATA / "qaa-classlike.json")
    assert material.digest == PUA_DIGEST

    extended = class_window("\ue000", 1, before=1, after=0, material=[material]).before[0]
    assert extended.extension_classes == ("qaa:tengwar-letter",)
    assert _base_fields(extended) == _direct_icu_base_fields("\ue000")
    assert extended.script == "Unknown"
    assert shape("\ue000\ue001", material=[material]) == "<qaa:L>"
    assert shape("\ue000\ue001") == "\ue000\ue001"


def test_standalone_kinds_execute_witnesses_and_refine_base_gc_runs():
    classes = load_locale_material(_char_material())
    refinement = load_locale_material(_shape_material())
    assert class_window("axe", 1, before=1, after=2, material=[classes]).before[
        0
    ].extension_classes == ("example:vowel",)
    assert shape("AA!", "coarse@1", material=[refinement]) == "<upper>!"
    assert shape("AA!", "cased@1", material=[refinement]) == "<upper>!"
    points = class_window("ae", 2, before=2, after=0, material=[classes]).before
    assert all(point.extension_classes == ("example:vowel",) for point in points)
    assert [_base_fields(point) for point in points] == [
        _direct_icu_base_fields(char) for char in "ae"
    ]


def test_scheme_name_extensions_and_identities_include_material_digests():
    material = load_locale_material(DATA / "qaa-classlike.json")
    plain_scheme = shape_scheme()
    extended_scheme = shape_scheme(material=[material])
    assert extended_scheme["name"] == "coarse@1+qaa/tengwar@295b930b1d8c"
    assert extended_scheme["extensions"] == [{"id": "qaa/tengwar", "digest": PUA_DIGEST}]
    assert shape("\ue000", extended_scheme["name"], material=[material]) == "<qaa:L>"
    assert shape_scheme(extended_scheme["name"], material=[material]) == extended_scheme
    with pytest.raises(ValueError, match="material mismatch"):
        shape("\ue000", extended_scheme["name"])
    changed = _pua_mapping()
    changed["provenance"]["source"] = "same rules, different identity"
    changed_material = load_locale_material(changed)
    with pytest.raises(ValueError, match="material mismatch"):
        shape("\ue000", extended_scheme["name"], material=[changed_material])
    assert extended_scheme["digest"] != plain_scheme["digest"]
    assert (
        class_window("x", 1, before=1, after=0, material=[material]).identity
        != class_window("x", 1, before=1, after=0).identity
    )


def test_empty_material_matches_a1_parent_golden():
    for prop, expected in A1_CLASS_GOLDEN.items():
        assert char_classes(A1_CLASS_TEXT, prop, material=()) == expected
    points = class_window(
        A1_CLASS_TEXT,
        len(A1_CLASS_TEXT),
        before=len(A1_CLASS_TEXT),
        after=0,
        material=(),
    ).before
    assert [point.text for point in points] == list(A1_CLASS_TEXT)
    assert [point.extension_classes for point in points] == [()] * len(A1_CLASS_TEXT)
    assert [[getattr(point, prop) for point in points] for prop in A1_CLASS_GOLDEN] == [
        A1_CLASS_GOLDEN[prop] for prop in A1_CLASS_GOLDEN
    ]
    for text, coarse, cased in A1_SHAPE_GOLDEN:
        assert shape(text, "coarse@1", material=()) == coarse
        assert shape(text, "cased@1", material=()) == cased
    assert shape_scheme("coarse@1", material=()) == A1_SCHEME_GOLDEN
    assert shape_scheme("cased@1", material=()) == A1_CASED_SCHEME_GOLDEN


def test_canonical_json_digest_not_file_bytes(tmp_path):
    mapping = _pua_mapping()
    compact = tmp_path / "compact.json"
    reordered = tmp_path / "reordered.json"
    compact.write_text(json.dumps(mapping, ensure_ascii=False, separators=(",", ":")))
    reordered.write_text(json.dumps(mapping, ensure_ascii=False, indent=4, sort_keys=True))
    assert load_locale_material(compact).digest == PUA_DIGEST
    assert load_locale_material(reordered).digest == PUA_DIGEST


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda data: data["classes"][0].update({"script": "Qaaa"}), "REDEFINES_BASE_SYMBOL"),
        (
            lambda data: data["classes"].append(deepcopy(data["classes"][0])),
            "DUPLICATE_ID",
        ),
        (
            lambda data: data["witnesses"][0]["expect"]["codepoint_classes"].__setitem__(0, []),
            "WITNESS_FAILED",
        ),
        (lambda data: data.__setitem__("status", "promoted"), "CLAIMS_PROMOTED"),
    ],
)
def test_required_refusals(mutation, code):
    data = _pua_mapping()
    mutation(data)
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(data)
    assert code in _codes(caught.value)


def test_duplicate_material_ids_refuse_the_complete_composition():
    first = load_locale_material(_char_material())
    changed = _char_material()
    changed["classes"][0]["name"] = "example:other-vowel"
    changed["witnesses"][0]["expect"]["codepoint_classes"] = [
        ["example:other-vowel"],
        [],
        ["example:other-vowel"],
    ]
    second = load_locale_material(changed)
    with pytest.raises(MaterialLoadError) as caught:
        class_window("a", 1, material=[first, second])
    assert "DUPLICATE_ID" in _codes(caught.value)


def test_shape_witness_failure_is_transactional():
    data = _shape_material()
    data["witnesses"][0]["expect"]["shapes"]["example:uppercase-run"] = "wrong"
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(data)
    assert _codes(caught.value) == {"WITNESS_FAILED"}


@pytest.mark.parametrize("kind", ["shape", "class"])
def test_every_witness_carries_a_nonempty_expectation(kind):
    if kind == "shape":
        data = _shape_material()
        unchecked = {"id": "unchecked", "text": "AA", "expect": {"shapes": {}}}
    else:
        data = _char_material()
        unchecked = {
            "id": "unchecked",
            "text": "AA",
            "expect": {"codepoint_classes": []},
        }
    data["witnesses"].append(unchecked)
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(data)
    assert _codes(caught.value) == {"WITNESS_FAILED"}


@pytest.mark.parametrize(
    "case", ["empty-list", "empty-text", "empty-shapes", "class", "refinement"]
)
def test_witnesses_must_be_nonempty_and_exercise_every_declaration(case):
    if case == "empty-list":
        data = _char_material()
        data["witnesses"] = []
    elif case == "empty-text":
        data = _char_material()
        data["witnesses"][0]["text"] = ""
        data["witnesses"][0]["expect"]["codepoint_classes"] = []
    elif case == "empty-shapes":
        data = _shape_material()
        data["witnesses"][0]["expect"]["shapes"] = {}
    elif case == "class":
        data = _char_material()
        data["classes"].append({"name": "example:unwitnessed", "members": ["i"]})
    else:
        data = _shape_material()
        data["shape_refinements"].append(
            {"name": "example:unwitnessed", "class": "Po", "symbol": "<punct>"}
        )
        data["witnesses"][0]["expect"]["shapes"]["example:unwitnessed"] = "<upper>"
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(data)
    assert "WITNESS_FAILED" in _codes(caught.value)


def test_shape_witness_coverage_is_attributed_to_selected_refinement():
    data = _shape_material()
    data["shape_refinements"] = [
        {"name": "example:uppercase", "class": "Lu", "symbol": "<u>"},
        {"name": "example:punctuation", "class": "Po", "symbol": "<u>!"},
    ]
    data["witnesses"] = [
        {
            "id": "punctuation-only",
            "text": ".",
            "expect": {
                "shapes": {
                    "example:uppercase": "<u>!",
                    "example:punctuation": "<u>!",
                }
            },
        }
    ]
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(data)
    assert _codes(caught.value) == {"WITNESS_FAILED"}
    assert any("example:uppercase" in item.detail for item in caught.value.refusals)


def test_refined_marks_win_over_absorption_and_refined_punctuation_does_not_absorb():
    mark_data = _shape_material()
    mark_data["id"] = "example/mark"
    mark_data["shape_refinements"] = [{"name": "example:mark", "class": "Mn", "symbol": "<mark>"}]
    mark_data["witnesses"] = [
        {
            "id": "mark-w1",
            "text": "\u0334",
            "expect": {"shapes": {"example:mark": "<mark>"}},
        }
    ]
    mark = load_locale_material(mark_data)
    assert shape("a\u0334", material=[mark]) == "A<mark>"

    punctuation_data = _shape_material()
    punctuation_data["id"] = "example/punctuation"
    punctuation_data["shape_refinements"] = [
        {"name": "example:stop", "class": "Po", "symbol": "<stop>"}
    ]
    punctuation_data["witnesses"] = [
        {
            "id": "punctuation-w1",
            "text": ".",
            "expect": {"shapes": {"example:stop": "<stop>"}},
        }
    ]
    punctuation = load_locale_material(punctuation_data)
    assert shape(".\u0334", material=[punctuation]) == "<stop>\u0334"


def test_overlapping_base_and_extension_refinements_are_refused():
    data = {
        "schema_version": 1,
        "kind": "classlike",
        "id": "example/overlap",
        "status": "experimental",
        "locale": "qaa",
        "classes": [{"name": "example:upper", "members": ["A"]}],
        "shape_refinements": [
            {"name": "example:a-general", "class": "Lu", "symbol": "<general>"},
            {
                "name": "example:z-specific",
                "class": "example:upper",
                "symbol": "<specific>",
            },
        ],
        "provenance": {"source": "fugu construction"},
        "witnesses": [
            {
                "id": "overlap-w1",
                "text": "A",
                "expect": {
                    "codepoint_classes": [["example:upper"]],
                    "shapes": {"example:a-general": "<general>"},
                },
            }
        ],
    }
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(data)
    assert _codes(caught.value) == {"AMBIGUOUS_REFINEMENT"}


@pytest.mark.parametrize(
    ("classes", "selectors"),
    [
        ([{"name": "example:dummy", "members": ["Z"]}], ("Lu", "Uppercase_Letter")),
        (
            [
                {"name": "example:left", "members": ["A"]},
                {"name": "example:right", "unicode_set": "[A-B]"},
            ],
            ("example:left", "example:right"),
        ),
    ],
)
def test_same_base_and_intersecting_extension_refinements_are_refused(classes, selectors):
    data = {
        "schema_version": 1,
        "kind": "classlike",
        "id": "example/other-overlap",
        "status": "experimental",
        "locale": "qaa",
        "classes": classes,
        "shape_refinements": [
            {"name": "example:left-run", "class": selectors[0], "symbol": "<left>"},
            {"name": "example:right-run", "class": selectors[1], "symbol": "<right>"},
        ],
        "provenance": {"source": "overlap test"},
        "witnesses": [
            {
                "id": "overlap-w1",
                "text": "A",
                "expect": {
                    "codepoint_classes": [[item["name"] for item in classes]],
                    "shapes": {"example:left-run": "<left>"},
                },
            }
        ],
    }
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(data)
    assert _codes(caught.value) == {"AMBIGUOUS_REFINEMENT"}


def test_overlapping_refinements_across_materials_are_refused_on_composition():
    first = load_locale_material(_shape_material())
    second_data = _shape_material()
    second_data["id"] = "example/other-uppercase"
    second_data["shape_refinements"][0] = {
        "name": "example:other-uppercase-run",
        "class": "Uppercase_Letter",
        "symbol": "<other-upper>",
    }
    second_data["witnesses"][0]["expect"]["shapes"] = {
        "example:other-uppercase-run": "<other-upper>"
    }
    second = load_locale_material(second_data)
    with pytest.raises(MaterialLoadError) as caught:
        shape("A", material=[first, second])
    assert _codes(caught.value) == {"AMBIGUOUS_REFINEMENT"}


def test_identifier_namespaces_are_separate_except_for_extension_names():
    data = _char_material()
    data["id"] = "example:vowel"
    data["witnesses"][0]["id"] = "example:vowel"
    assert load_locale_material(data).id == "example:vowel"

    duplicate_extension = _pua_mapping()
    duplicate_extension["shape_refinements"][0]["name"] = "qaa:tengwar-letter"
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(duplicate_extension)
    assert "DUPLICATE_ID" in _codes(caught.value)
