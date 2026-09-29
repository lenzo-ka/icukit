"""Locale material composition with generated and flexible detector gangs."""

from __future__ import annotations

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from icukit.detectors import DetectorSet, detector_key
from icukit.engine import flexible_detectors, generated_detectors, generated_detectors_report
from icukit.material import LocaleMaterial, load_locale_material
from icukit.recognize import MaterialLoneSpelloutDetector, MaterialSpelloutDetector
from icukit.serialize import detections_to_json

FIXTURE = Path(__file__).parent / "data" / "material" / "qaa-spellout.json"
TEXT = "On March 5, 2024 at 3:30 PM, twenty-one people paid $45.50 for 3 kg, about 12% more."
BASE_SNAPSHOTS = {
    "en": (90, "f6684ec1793c5e84e8c215c9549a2d020ff24ba2b63b78cb1f888339ee08ab6d"),
    "en_US": (90, "32be62c702598e8ef20a7b9eaff62e50ea16c1e3aaee0d711eedf8c53ba3c380"),
    "en_GB": (99, "e1b2c13392e53b0086f88261049cf851f21730b0dda0f5a1481e251cfbb9d76b"),
    "fr": (91, "ff7986ac1df6248d2e74b51fa841e6392702f2e6b1b0c5dd4f85148f751f194a"),
    "de": (106, "3afdf46552c50dc59bdaaf70bb4d1a2771d912155c620e03cdb11b79a803b927"),
    "es": (111, "24973d025344f85cc663b5a49783c58fcb261ebc60da285e493daf7607e29b6a"),
    "ja": (98, "7dbe1298a0c22bb57777d8ee405f908c98215e09784ca16ac51231872eddb5e0"),
    "zh": (90, "913a5b8c1c263d1eee627c0e7eb5c6389875214cc0ea2486dd34c2189ce74c59"),
    "ar": (94, "8f4d0e7fc20447d6ae34da4168a60589a4213c28d5ada6bab28b975a4e3ef92d"),
    "ru": (154, "73973f1048def4df988ce0a07496d804ef91af559fb342d0d3696502d10d44c9"),
    "hi": (96, "dd2003a22df3e281f36907576358838621f0675b3a6dabce3eef14d9d8a80490"),
    "yo": (86, "d66f88b9edbaa3ee6a580d38918fe61db2df12059e4bee904befda5cab3977c5"),
}


def _material_for(locale: str, *, note: str | None = None):
    raw = json.loads(FIXTURE.read_text())
    raw["locale"] = locale
    for witness in raw["witnesses"]:
        witness["locale"] = locale
    for near_miss in raw["near_misses"]:
        near_miss["locale"] = locale
    if note is not None:
        raw["provenance"]["note"] = note
    return load_locale_material(raw)


def _legacy_keys(locale: str, *, material=()):
    detectors = generated_detectors(locale, material=material).detectors
    keys = [
        [key[0], key[1], key[2], list(key[3]) if key[3] is not None else None]
        for key in (detector_key(detector)[:4] for detector in detectors)
    ]
    return detectors, keys


@pytest.mark.parametrize("locale", BASE_SNAPSHOTS)
def test_b8_default_generated_gangs_are_unchanged(locale):
    detectors, keys = _legacy_keys(locale)
    count, digest = BASE_SNAPSHOTS[locale]
    assert len(keys) == count
    assert sha256(json.dumps(keys, sort_keys=True).encode()).hexdigest() == digest
    assert all(detector_key(detector)[4] is None for detector in detectors)


def test_b9_default_detection_serialization_is_unchanged():
    expected = "83b3102b459b4bba4f7dd5442625b44e21f6b7c5e730d0a123747d284d0426ed"
    for detectors in (generated_detectors("en_US"), generated_detectors("en_US", material=())):
        encoded = json.dumps(detections_to_json(detectors.detect(TEXT)), ensure_ascii=False)
        assert len(encoded) == 2405
        assert sha256(encoded.encode()).hexdigest() == expected


def test_b10_material_is_added_after_all_existing_yo_readers():
    material = _material_for("yo")
    baseline = generated_detectors("yo")
    extended = generated_detectors("yo", material=[material])
    baseline_keys = tuple(map(detector_key, baseline.detectors))
    extended_keys = tuple(map(detector_key, extended.detectors))
    assert extended_keys[: len(baseline_keys)] == baseline_keys
    assert sum(detector.type.startswith("number:spellout") for detector in baseline.detectors) == 5
    material_reader = next(
        detector
        for detector in extended.detectors
        if isinstance(detector, MaterialSpelloutDetector)
    )
    assert material_reader.material_digest == material.digest
    assert material_reader.detect("twenty-one people")
    assert any(
        detector.detect("twenty-one people")
        for detector in baseline.detectors
        if detector.type.startswith("number:spellout")
    )


def test_b11_distinct_material_digests_coexist_and_keys_are_hashable():
    first = _material_for("yo", note="first")
    second = _material_for("yo", note="second")
    gang = DetectorSet(()).with_(
        MaterialSpelloutDetector("yo", first, ruleset="%spellout-cardinal"),
        MaterialSpelloutDetector("yo", second, ruleset="%spellout-cardinal"),
    )
    keys = {detector_key(detector) for detector in gang.detectors}
    assert len(gang.detectors) == len(keys) == 2


def test_b12_material_application_follows_locale_descent():
    yo = _material_for("yo")
    yo_ng = _material_for("yo_NG")
    assert any(
        detector_key(detector)[4] == yo.digest
        for detector in generated_detectors("yo_NG", material=[yo]).detectors
    )
    report = generated_detectors_report("yo", material=[yo_ng])
    assert all(detector_key(detector)[4] is None for detector in report.detectors.detectors)
    skipped = next(item for item in report.skipped if item.spec == yo_ng.digest)
    assert skipped.family == "spellout-number"
    assert "yo_NG" in skipped.reason and "yo" in skipped.reason


def test_b13_material_detection_serializes_digest_and_number_value():
    material = load_locale_material(FIXTURE)
    detector = MaterialSpelloutDetector("qaa", material, ruleset="%spellout-cardinal")
    serialized = detections_to_json(detector.detect("twenty-three"))[0]
    assert serialized["spec"] == {
        "kind": "material_spellout_format_spec",
        "locale": "qaa",
        "ruleset": "%spellout-cardinal",
        "material_digest": material.digest,
    }
    assert serialized["value"] == {"kind": "number", "decimal": "23", "currency": None}


def test_flexible_material_reads_phrase_and_guarded_adds_lone_reader():
    material = load_locale_material(FIXTURE)
    default = flexible_detectors("qaa", locales=(), material=[material])
    assert any(
        item["text"] == "one hundred forty-five"
        for item in default.detect("one hundred forty-five goats")
    )
    default_material = next(
        detector for detector in default.detectors if isinstance(detector, MaterialSpelloutDetector)
    )
    assert not default_material.detect("seven")
    guarded = flexible_detectors("qaa", locales=(), guarded=True, material=[material])
    lone = next(
        detector
        for detector in guarded.detectors
        if isinstance(detector, MaterialLoneSpelloutDetector)
    )
    assert lone.type == "number:spellout-lone"
    assert lone.material_digest == material.digest
    assert lone.detect("seven")[0]["value"].decimal == "7"


def test_flexible_default_material_argument_is_unchanged():
    assert tuple(map(detector_key, flexible_detectors("en_US", locales=()).detectors)) == tuple(
        map(detector_key, flexible_detectors("en_US", locales=(), material=()).detectors)
    )


def test_non_material_element_is_a_type_error():
    with pytest.raises(TypeError, match="LocaleMaterial"):
        generated_detectors("en", material=[object()])  # type: ignore[list-item]


def test_unknown_material_kind_is_reported_as_skipped():
    material = LocaleMaterial("future-kind", "qaa", "sha256:future", "", (), {})
    report = generated_detectors_report("qaa", material=[material])
    skipped = next(item for item in report.skipped if item.spec == material.digest)
    assert skipped.family == "spellout-number"
    assert "future-kind" in skipped.reason


def _run_cli(*args: str):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_material_finds_reading():
    result = _run_cli(
        "detect",
        "--locale",
        "qaa",
        "--material",
        str(FIXTURE),
        "-H",
        "-t",
        "one hundred forty-five goats",
    )
    assert result.returncode == 0, result.stderr
    assert "number:spellout\tone hundred forty-five" in result.stdout


def test_cli_bad_material_prints_every_refusal(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version": 2, "kind": "bad"}')
    result = _run_cli("detect", "--material", str(path), "-t", "one")
    assert result.returncode != 0
    assert "INVALID_KEY:" in result.stderr
    assert "INVALID_SCHEMA_VERSION:" in result.stderr
    assert "INVALID_KIND:" in result.stderr
