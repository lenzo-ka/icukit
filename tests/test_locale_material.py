import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import icu
import pytest

from icukit.material import (
    LABEL_KEYS,
    REQUIRED_WITNESS_KEYS,
    VALUE_KEYS,
    WITNESS_KEYS,
    LocaleMaterial,
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
    refused = set()
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
        for value in (21, 45, 145, 1234):
            text = formatter.format(value, detector._ruleset)
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
        material = {
            "schema_version": 1,
            "kind": "rbnf-spellout",
            "locale": language,
            "rules": formatter.getRules().splitlines(),
            "provenance": {"source": "ICU test reflection"},
            "witnesses": witnesses,
        }
        try:
            loaded = load_locale_material(material)
        except MaterialLoadError as error:
            refused.add(language)
            assert {item.code for item in error.refusals} == {"WITNESS_READ_FAILED"}
            refused_ids = {
                match.group(1)
                for item in error.refusals
                if (match := re.match(r"witness '([^']+)'", item.detail))
            }
            assert refused_ids
            for witness in (item for item in witnesses if item["id"] in refused_ids):
                expected = witness["x-icukit"]["values"][0]["value"]["decimal"]
                assert not any(
                    item["start"] == 0
                    and item["end"] == len(witness["text"])
                    and item["value"].decimal == expected
                    for item in detector.detect(witness["text"])
                ), language
            continue
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
    # Characterization: these ICU-formatted witnesses exceed the flexible reader's
    # inherited coverage; Chakma also exposes its UTF-16/code-point offset mismatch.
    assert refused == {"ak", "ccp", "lb"}


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


def _material_like_text(text, *, check_signature=True):
    if (
        check_signature
        and re.search(r'"kind"\s*:\s*"rbnf-spellout"', text)
        and re.search(r'"witnesses"\s*:\s*\[', text)
    ):
        yield "material signature"
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        yield from _material_like_objects(value)


@pytest.mark.parametrize(
    "value",
    [
        dict(kind="rbnf-spellout"),
        dict(rules="malformed", witnesses=None),
        dict(schema_version=999, kind="unknown"),
        {"nested": [dict(kind="rbnf-spellout")]},
    ],
)
def test_b16_material_shape_probe_catches_valid_or_malformed_material(value):
    assert list(_material_like_objects(value))


def test_b16_distributions_and_package_data_ship_no_locale_material(tmp_path):
    root = Path(__file__).parent.parent
    # uv builds in a development checkout; CI installs the dev extra's ``build``.
    if shutil.which("uv"):
        command = ["uv", "build", "--out-dir", str(tmp_path)]
    elif importlib.util.find_spec("build") is not None:
        command = [sys.executable, "-m", "build", "--outdir", str(tmp_path)]
    else:
        pytest.fail("neither uv nor build is available to build the distributions")
    subprocess.run(command, cwd=root, check=True, capture_output=True)
    archives = sorted(path for path in tmp_path.iterdir() if path.suffix in {".whl", ".gz"})
    assert {path.suffix for path in archives} >= {".whl", ".gz"}
    for archive in archives:
        for name, content in _archive_files(archive):
            assert "tests/data/material" not in name
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                continue
            assert not list(_material_like_text(text, check_signature=not name.endswith(".py"))), (
                name
            )
    for path in (root / "icukit/data").rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert not list(_material_like_text(text)), path


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


def test_every_malformed_input_in_the_refusal_sweep_raises_material_load_error(tmp_path):
    bad_values = (None, [], {}, 0, 1.5, True, "x")
    for field in ("schema_version", "kind", "locale", "rules", "provenance", "witnesses"):
        for bad_value in bad_values:
            material = _fixture()
            material[field] = copy.deepcopy(bad_value)
            with pytest.raises(MaterialLoadError):
                load_locale_material(material)

    for field in ("witnesses", "labels", "values", "near_misses"):
        for bad_value in bad_values:
            material = _fixture()
            if field == "witnesses":
                material[field] = [copy.deepcopy(bad_value)]
            elif field == "labels":
                material["witnesses"][0][field] = [copy.deepcopy(bad_value)]
            elif field == "values":
                material["witnesses"][0]["x-icukit"][field] = [copy.deepcopy(bad_value)]
            else:
                material[field] = [copy.deepcopy(bad_value)]
            with pytest.raises(MaterialLoadError):
                load_locale_material(material)

    for collection in ("labels", "values"):
        for offset in (1.5, True, -1, 10**100):
            for field in ("start", "end"):
                material = _fixture()
                record = material["witnesses"][0]
                if collection == "labels":
                    record[collection][0][field] = offset
                else:
                    record["x-icukit"][collection][0][field] = offset
                with pytest.raises(MaterialLoadError):
                    load_locale_material(material)

    malformed_mappings = (
        {**_fixture(), 1: "non-string top-level key"},
        {**_fixture(), "provenance": {1: "non-string nested key"}},
        {**_fixture(), "provenance": {"source": object()}},
        {**_fixture(), "witnesses": [{"nested": object()}]},
    )
    for material in malformed_mappings:
        with pytest.raises(MaterialLoadError):
            load_locale_material(material)

    non_utf8 = tmp_path / "non-utf8.json"
    non_utf8.write_bytes(b"\xff")
    for path in (non_utf8, tmp_path):
        with pytest.raises(MaterialLoadError):
            load_locale_material(path)


@pytest.mark.parametrize("text_hash", [None, 0, True, [], {}, "A" * 64, "0" * 63])
def test_present_invalid_witness_hash_is_refused(text_hash):
    material = _fixture()
    material["witnesses"][0]["text_sha256"] = text_hash
    assert _codes(material) == ["INVALID_WITNESS"]


def test_two_public_rule_sets_cannot_collapse_to_one_reader_type():
    material = _fixture()
    material["rules"].extend(
        [
            "%spellout-ordinal:",
            "0: =%spellout-cardinal=;",
            "%ordinal:",
            "0: =%spellout-cardinal=;",
        ]
    )
    material["witnesses"][1]["labels"].append(
        {"start": 0, "end": 12, "class": "number:spellout:ordinal"}
    )
    refusals = _refusals(material)
    ambiguous = [item for item in refusals if item.code == "AMBIGUOUS_RULESET"]
    assert len(ambiguous) == 1
    assert "%spellout-ordinal" in ambiguous[0].detail
    assert "%ordinal" in ambiguous[0].detail


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
    assert MaterialSpelloutDetector("qaa", copy.copy(material))
    assert MaterialSpelloutDetector("qaa", copy.deepcopy(material))
    with pytest.raises(TypeError):
        material.provenance["source"] = "changed"


def test_only_loaded_unchanged_material_is_accepted_by_the_reader():
    material = load_locale_material(FIXTURE)
    assert MaterialSpelloutDetector("qaa", material)
    forged = (
        replace(material, rules=material.rules + "\n# changed"),
        replace(material, rulesets=("%other",)),
        replace(material, locale="qaa_Latn"),
        replace(material, digest="sha256:" + "0" * 64),
        LocaleMaterial(
            material.kind,
            material.locale,
            material.digest,
            material.rules,
            material.rulesets,
            MappingProxyType(dict(material.provenance)),
        ),
    )
    for item in forged:
        with pytest.raises(ValueError, match="locale material must come from load_locale_material"):
            MaterialSpelloutDetector("qaa", item)
    with pytest.raises(TypeError, match="material must be a LocaleMaterial"):
        MaterialSpelloutDetector("qaa", object())


def test_provenance_changes_material_and_reader_identity():
    first = load_locale_material(FIXTURE)
    changed = _fixture()
    changed["provenance"]["note"] += " Different provenance."
    second = load_locale_material(changed)
    first_reader = MaterialSpelloutDetector("qaa", first)
    second_reader = MaterialSpelloutDetector("qaa", second)
    assert first.digest != second.digest
    assert first_reader._spec != second_reader._spec
    assert first_reader.material_digest != second_reader.material_digest


def test_descendant_witness_uses_its_own_formatter_and_reader_locale(monkeypatch):
    import icukit.recognize as recognize

    actual_reader = recognize.MaterialSpelloutDetector
    reader_locales = []

    class RecordingMaterialReader(actual_reader):
        def __init__(self, locale, *args, **kwargs):
            reader_locales.append(locale)
            super().__init__(locale, *args, **kwargs)

    monkeypatch.setattr(recognize, "MaterialSpelloutDetector", RecordingMaterialReader)
    material = _fixture()
    material["locale"] = "pt"
    material["near_misses"] = []
    material["rules"] = [
        line.replace("0: zero;", "0: zero $(cardinal,one{one}other{other})$;")
        for line in material["rules"]
    ]
    text = "zero other"
    material["witnesses"] = [
        {
            "id": "pt-PT-zero",
            "text": text,
            "locale": "pt_PT",
            "labels": [{"start": 0, "end": len(text), "class": "number:spellout"}],
            "x-icukit": {
                "values": [
                    {
                        "start": 0,
                        "end": len(text),
                        "type": "number:spellout",
                        "value": {"kind": "number", "decimal": "0", "currency": None},
                    }
                ]
            },
        }
    ]
    # Portuguese formats zero with the one branch; European Portuguese uses other.
    # ICU's RBNF parser cannot parse this plural construct back, so the honest inherited
    # reader limitation remains, but formatting succeeds only in the witness locale.
    assert set(_codes(material)) == {"WITNESS_READ_FAILED"}
    assert reader_locales == ["pt", "pt_PT"]


def test_material_detector_allows_descendants_only():
    material = load_locale_material(FIXTURE)
    assert MaterialSpelloutDetector("qaa_Latn", material).locale == "qaa_Latn"
    with pytest.raises(ValueError):
        MaterialSpelloutDetector("en", material)
