import copy
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path

import icu
import pytest

from icukit.material import (
    LABEL_KEYS,
    REQUIRED_WITNESS_KEYS,
    VALUE_KEYS,
    WITNESS_KEYS,
    MaterialLoadError,
    load_locale_material,
)
from icukit.recognize import FlexibleSpelloutDetector, MaterialSpelloutDetector
from icukit.serialize import _to_json

FIXTURE = Path(__file__).parent / "data/material/qaa-spellout.json"
DIGEST = "sha256:e3eb2afa6f80b7aea0778fa05a4ee3089a9b7bcf7e9242fe0151dd3cfe589eb7"


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _refusals(material):
    with pytest.raises(MaterialLoadError) as caught:
        load_locale_material(material)
    assert str(caught.value)
    return caught.value.refusals


def _codes(material):
    return [refusal.code for refusal in _refusals(material)]


def test_b1_toy_rule_edit_is_caught_by_the_witnesses():
    material = _fixture()
    material["rules"] = [
        "100: << hundred[ >>>];" if line.startswith("100:") else line for line in material["rules"]
    ]
    # ICU 78.3 verifiably renders 145 as "one hundred ninety-five" with this edit.
    formatter = icu.RuleBasedNumberFormat("\n".join(material["rules"]), icu.Locale("qaa"))
    assert formatter.format(145, "%spellout-cardinal") == "one hundred ninety-five"
    assert "WITNESS_FORMAT_FAILED" in _codes(material)


def test_b2_garbage_that_icu_compiles_has_no_cardinal_ruleset():
    material = _fixture()
    material["rules"] = ["garbage without colon"]
    assert _codes(material) == ["NO_CARDINAL_RULESET"]


def test_b3_noninjective_cardinal_rules_are_refused():
    material = _fixture()
    material["rules"] = ["%spellout-cardinal: 0: zero; 10: <<;"]
    assert "NOT_INJECTIVE" in _codes(material)


def test_b4_every_icu_language_with_own_rules_loads_with_real_witnesses():
    languages = sorted(
        {icu.Locale(name).getLanguage() for name in icu.Locale.getAvailableLocales()}
    )
    checked = 0
    no_readings = set()
    for language in languages:
        if not language or language == "root":
            continue
        locale = icu.Locale(language)
        formatter = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.SPELLOUT, locale)
        actual = formatter.getLocale(icu.ULocDataLocaleType.ACTUAL_LOCALE)
        if actual.getLanguage() != language:
            continue
        detector = FlexibleSpelloutDetector(language)
        witnesses = []
        for value in (21, 45, 145, 1234, 2025, 99, 310):
            text = formatter.format(value, detector._ruleset)
            detections = detector.detect(text)
            if not any(
                item["start"] == 0
                and item["end"] == len(text)
                and item["value"].decimal == str(value)
                for item in detections
            ):
                continue
            witnesses.append(
                {
                    "id": f"{language}-{value}",
                    "text": text,
                    "locale": language,
                    "labels": [{"start": 0, "end": len(text), "class": "number:spellout"}],
                    "x-icukit": {
                        "values": [
                            {
                                "start": 0,
                                "end": len(text),
                                "type": "number:spellout",
                                "value": {
                                    "kind": "number",
                                    "decimal": str(value),
                                    "currency": None,
                                },
                            }
                        ]
                    },
                }
            )
            if len(witnesses) == 3:
                break
        if not witnesses:
            no_readings.add(language)
            continue
        material = {
            "schema_version": 1,
            "kind": "rbnf-spellout",
            "locale": language,
            "rules": formatter.getRules().splitlines(),
            "provenance": {"source": "ICU test reflection"},
            "witnesses": witnesses,
        }
        loaded = load_locale_material(material)
        reader = MaterialSpelloutDetector(language, loaded)
        for witness in witnesses:
            assert any(
                item["start"] == 0
                and item["end"] == len(witness["text"])
                and item["value"].decimal == witness["x-icukit"]["values"][0]["value"]["decimal"]
                for item in reader.detect(witness["text"])
            ), language
        checked += 1
    assert checked > 70
    # Characterization: the ICU reader compares ICU's UTF-16 parse position with
    # code-point offsets, so supplementary-plane Chakma currently yields no readings.
    assert no_readings == {"ccp"}

    ccp_locale = icu.Locale("ccp")
    ccp_formatter = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.SPELLOUT, ccp_locale)
    ccp_detector = FlexibleSpelloutDetector("ccp")
    ccp_witnesses = []
    for value in (21, 145):
        text = ccp_formatter.format(value, ccp_detector._ruleset)
        ccp_witnesses.append(
            {
                "id": f"ccp-{value}",
                "text": text,
                "locale": "ccp",
                "labels": [{"start": 0, "end": len(text), "class": "number:spellout"}],
                "x-icukit": {
                    "values": [
                        {
                            "start": 0,
                            "end": len(text),
                            "type": "number:spellout",
                            "value": {
                                "kind": "number",
                                "decimal": str(value),
                                "currency": None,
                            },
                        }
                    ]
                },
            }
        )
    ccp_material = {
        "schema_version": 1,
        "kind": "rbnf-spellout",
        "locale": "ccp",
        "rules": ccp_formatter.getRules().splitlines(),
        "provenance": {"source": "ICU test reflection"},
        "witnesses": ccp_witnesses,
    }
    # Characterization: real ccp rules clear syntax, structure, injectivity, and
    # formatting checks; only the inherited reader offset defect refuses them.
    ccp_codes = _codes(ccp_material)
    assert ccp_codes
    assert set(ccp_codes) == {"WITNESS_READ_FAILED"}


def test_b5_loading_is_transactional_and_lists_every_semantic_refusal():
    material = _fixture()
    material["witnesses"][1]["x-icukit"]["values"][0]["value"]["decimal"] = "24"
    material["near_misses"].append(
        {"id": "qaa-n2", "text": "twenty-three", "locale": "qaa", "type": "number:spellout"}
    )
    assert _codes(material) == [
        "WITNESS_FORMAT_FAILED",
        "WITNESS_READ_FAILED",
        "NEAR_MISS_READ",
    ]


def test_b6_digest_tracks_content_but_not_json_formatting(tmp_path):
    original = load_locale_material(FIXTURE)
    material = _fixture()
    material["provenance"]["note"] += " Edited."
    assert load_locale_material(material).digest != original.digest
    reordered = {key: _fixture()[key] for key in reversed(_fixture())}
    path = tmp_path / "reordered.json"
    path.write_text(json.dumps(reordered, separators=(", ", ": ")), encoding="utf-8")
    assert load_locale_material(path).digest == original.digest


def test_b7_extra_top_level_key_and_noncanonical_locale_are_refused():
    extra = _fixture()
    extra["extra"] = True
    assert _codes(extra) == ["INVALID_KEY"]
    uppercase = _fixture()
    uppercase["locale"] = "YO"
    assert _codes(uppercase) == ["INVALID_LOCALE"]


def _archive_files(path):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return [(name, archive.read(name)) for name in archive.namelist()]
    with tarfile.open(path) as archive:
        return [
            (member.name, file.read())
            for member in archive.getmembers()
            if member.isfile() and (file := archive.extractfile(member)) is not None
        ]


def _material_like_objects(value):
    if isinstance(value, dict):
        keys = set(value)
        if (
            value.get("kind") == "rbnf-spellout"
            or {"rules", "witnesses"} <= keys
            or {"schema_version", "kind"} <= keys
        ):
            yield value
        for item in value.values():
            yield from _material_like_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from _material_like_objects(item)


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "rbnf-spellout"},
        {"rules": "malformed", "witnesses": None},
        {"schema_version": 999, "kind": "unknown"},
        {"nested": [{"kind": "rbnf-spellout"}]},
    ],
)
def test_b16_material_shape_probe_catches_valid_or_malformed_material(value):
    assert list(_material_like_objects(value))


def test_b16_distributions_and_package_data_ship_no_locale_material(tmp_path):
    root = Path(__file__).parent.parent
    subprocess.run(
        ["uv", "build", "--out-dir", str(tmp_path)], cwd=root, check=True, capture_output=True
    )
    archives = sorted(path for path in tmp_path.iterdir() if path.suffix in {".whl", ".gz"})
    assert {path.suffix for path in archives} >= {".whl", ".gz"}
    for archive in archives:
        for name, content in _archive_files(archive):
            assert "tests/data/material" not in name
            if not name.endswith(".json"):
                continue
            try:
                value = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            assert not list(_material_like_objects(value)), name
    for path in (root / "icukit/data").rglob("*"):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        assert not list(_material_like_objects(value)), path


def test_b17_whole_near_miss_is_refused_but_partial_fixture_read_passes():
    assert load_locale_material(FIXTURE).digest == DIGEST
    material = _fixture()
    material["near_misses"][0]["text"] = "twenty-three"
    assert _codes(material) == ["NEAR_MISS_READ"]


def test_b18_literal_fixture_and_reader():
    material = load_locale_material(FIXTURE)
    assert material.digest == DIGEST
    assert material.rulesets == ("%spellout-cardinal",)
    reader = MaterialSpelloutDetector("qaa", material)
    first = reader.detect("one hundred forty-five goats")[0]
    second = reader.detect("twenty-three")[0]
    assert (first["start"], first["end"], first["value"].decimal) == (0, 22, "145")
    assert (second["start"], second["end"], second["value"].decimal) == (0, 12, "23")


def test_l2_public_record_field_sets_are_pinned():
    assert WITNESS_KEYS == {"id", "text", "text_sha256", "locale", "labels", "x-icukit"}
    assert LABEL_KEYS == {"start", "end", "text", "class", "scheme"}
    assert VALUE_KEYS == {"start", "end", "text", "type", "value"}
    assert REQUIRED_WITNESS_KEYS == {"id", "text", "locale"}


def test_duplicate_keys_and_nonfinite_numbers_are_invalid_json(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    assert _codes(duplicate) == ["INVALID_JSON"]
    assert _codes({**_fixture(), "bad": float("nan")}) == ["INVALID_JSON"]
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"value":Infinity}', encoding="utf-8")
    assert _codes(nonfinite) == ["INVALID_JSON"]


@pytest.mark.parametrize(
    "mutation, code",
    [
        (lambda item: item.update(schema_version=True), "INVALID_SCHEMA_VERSION"),
        (lambda item: item.update(kind="unknown"), "INVALID_KIND"),
        (lambda item: item.update(rules=[]), "INVALID_RULES"),
        (lambda item: item.update(provenance={}), "INVALID_PROVENANCE"),
        (lambda item: item.update(witnesses=[]), "NO_WITNESS"),
        (lambda item: item["witnesses"][0].update(id="bad\n"), "INVALID_WITNESS"),
        (lambda item: item.update(near_misses=[{}]), "INVALID_NEAR_MISS"),
    ],
)
def test_each_envelope_refusal_code(mutation, code):
    material = _fixture()
    mutation(material)
    assert code in _codes(material)


def test_witness_locale_must_equal_or_descend_from_material_locale():
    descendant = _fixture()
    descendant["witnesses"][0]["locale"] = "qaa_Latn"
    assert load_locale_material(descendant)
    unrelated = _fixture()
    unrelated["witnesses"][0]["locale"] = "en"
    assert _codes(unrelated) == ["INVALID_WITNESS"]


def test_echo_catches_utf16_offsets():
    material = _fixture()
    witness = material["witnesses"][1]
    witness["text"] = "😀twenty-three"
    witness["labels"][0].update(start=2, end=14, text="twenty-three")
    witness["x-icukit"]["values"][0].update(start=2, end=14, text="twenty-three")
    assert set(_codes(material)) == {"INVALID_WITNESS"}


def test_refusal_details_name_the_record_field_and_reason():
    extra = _fixture()
    extra["extra"] = True
    assert _refusals(extra)[0].detail == "unknown top-level key 'extra'"

    bad_hash = _fixture()
    bad_hash["witnesses"][0]["text_sha256"] = "0" * 64
    assert _refusals(bad_hash)[0].detail == "witness 'qaa-w1': text_sha256 does not match"

    bad_extent = _fixture()
    bad_extent["witnesses"][0]["labels"][0]["end"] = 40
    details = [refusal.detail for refusal in _refusals(bad_extent)]
    assert "witness 'qaa-w1' label 0: end 40 > len(text) 28" in details

    bad_locale = _fixture()
    bad_locale["witnesses"][1]["locale"] = "fr"
    assert _refusals(bad_locale)[0].detail == (
        "witness 'qaa-w2': locale 'fr' does not descend from 'qaa'"
    )

    bad_value = _fixture()
    bad_value["witnesses"][1]["x-icukit"]["values"][0]["value"]["decimal"] = "24"
    refusals = _refusals(bad_value)
    format_detail = next(item.detail for item in refusals if item.code == "WITNESS_FORMAT_FAILED")
    read_detail = next(item.detail for item in refusals if item.code == "WITNESS_READ_FAILED")
    assert "witness 'qaa-w2' value 0" in format_detail
    assert "rule set '%spellout-cardinal' formats as 'twenty-four'" in format_detail
    assert "witness slice is 'twenty-three'" in format_detail
    assert "witness 'qaa-w2'" in read_detail
    assert "expected extent (0, 12), type 'number:spellout'" in read_detail
    assert "'decimal': '24'" in read_detail
    assert "reader read" in read_detail

    whole_near_miss = _fixture()
    whole_near_miss["near_misses"][0]["text"] = "twenty-three"
    assert _refusals(whole_near_miss)[0].detail == (
        "near miss 'qaa-n1': reader type 'number:spellout' read the whole text"
    )


def test_material_reader_construction_failure_becomes_rbnf_syntax(monkeypatch):
    import icukit.recognize as recognize

    class BrokenMaterialReader:
        def __init__(self, *args, **kwargs):
            raise ValueError("pathological formatter")

    monkeypatch.setattr(recognize, "MaterialSpelloutDetector", BrokenMaterialReader)
    refusals = _refusals(_fixture())
    assert [item.code for item in refusals] == ["RBNF_SYNTAX"]
    assert refusals[0].detail == (
        "rule set '%spellout-cardinal': material reader construction failed: pathological formatter"
    )


def test_material_detector_spec_serializes_with_digest_and_material_is_hashable():
    material = load_locale_material(FIXTURE)
    detector = MaterialSpelloutDetector("qaa", material)
    assert _to_json(detector._spec) == {
        "kind": "material_spellout_format_spec",
        "locale": "qaa",
        "ruleset": "%spellout-cardinal",
        "material_digest": DIGEST,
    }
    assert isinstance(hash(material), int)
    assert material == copy.copy(material)
    with pytest.raises(TypeError):
        material.provenance["source"] = "changed"


def test_material_detector_allows_descendants_only():
    material = load_locale_material(FIXTURE)
    assert MaterialSpelloutDetector("qaa_Latn", material).locale == "qaa_Latn"
    with pytest.raises(ValueError):
        MaterialSpelloutDetector("en", material)
