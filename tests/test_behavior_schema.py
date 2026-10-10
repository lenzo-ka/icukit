"""Behavior-schema loader and shared conformance fixtures."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from icukit import (
    BEHAVIOR_OPTION_NAMES,
    BehaviorLoadError,
    Breaker,
    UnicodeRegex,
    load_behavior_schema,
    reader_set,
)

DATA = Path(__file__).parent / "data/behaviors/conformance"


def _manifest(group):
    root = DATA / group
    return root, json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))["files"]


def _digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _error(source):
    with pytest.raises(BehaviorLoadError) as caught:
        load_behavior_schema(source)
    return caught.value


def test_shared_envelope_manifest_and_invalid_cases():
    root, files = _manifest("envelope")

    for relative, record in files.items():
        path = root / relative
        assert _digest(path) == record["sha256"]
        if relative.startswith("invalid/"):
            assert _error(path).refusals[0].code == record["expected"]


@pytest.mark.parametrize("name", ["empty.json", "frend.json"])
def test_shared_neutral_envelopes_load(name):
    loaded = load_behavior_schema(DATA / "envelope/valid" / name)

    assert loaded.section == {}
    assert loaded.sentence == {}
    assert loaded.detection == {}
    assert loaded.stream == {}
    assert loaded.regex == {}


def test_other_known_section_must_be_an_object():
    document = {
        "schema_version": 1,
        "kind": "behavior-schema",
        "name": "bad-frend",
        "version": 1,
        "extends": [],
        "provenance": {"source": "icukit tests"},
        "sections": {"frend": []},
    }

    assert _error(document).refusals[0].code == "INVALID_VALUE"


def test_present_bare_or_envelope_section_requires_its_version():
    assert _error({}).refusals[0].code == "INVALID_SCHEMA_VERSION"
    document = {
        "schema_version": 1,
        "kind": "behavior-schema",
        "name": "empty-section",
        "version": 1,
        "extends": [],
        "provenance": {"source": "icukit tests"},
        "sections": {"icukit": {}},
    }
    assert _error(document).refusals[0].code == "INVALID_SCHEMA_VERSION"


def test_shared_icukit_placeholder_waits_for_mirrored_replacement():
    root, files = _manifest("envelope")
    record = files["valid/icukit.json"]
    placeholder_digest = "sha256:56610f5392d6a425aa5917f593414c0efaf661ab5f09475d60e0cf356519da15"
    if record["sha256"] == placeholder_digest:
        pytest.xfail("shared fixture still has frend's provisional pipeline-shaped section")

    loaded = load_behavior_schema(root / "valid/icukit.json")
    assert loaded.section


def test_icukit_manifest_cases():
    root, files = _manifest("icukit")

    for relative, record in files.items():
        path = root / relative
        assert _digest(path) == record["sha256"]
        if record["expected"] == "valid":
            load_behavior_schema(path)
        else:
            assert _error(path).refusals[0].code == record["expected"]


def test_bare_section_maps_directly_to_public_options():
    loaded = load_behavior_schema(DATA / "icukit/valid/bare-current.json")

    assert loaded.name is None
    assert loaded.version is None
    assert loaded.extends == ()
    assert loaded.sentence == {"base": "en-tn@1"}
    assert loaded.stream == {"max_pending_chars": 2048, "boundary": "paragraph"}
    breaker = Breaker("en_US", **loaded.sentence)
    detectors = reader_set("en_US", **loaded.detection)
    stream = detectors.stream(**loaded.stream)
    assert breaker.base == "en-tn@1"
    assert stream.pending()["pending_from"] == 0


def test_full_envelope_digest_covers_opaque_frend_section_and_ignores_formatting(tmp_path):
    path = DATA / "icukit/valid/envelope-current.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    loaded = load_behavior_schema(path)
    reordered = {key: copy.deepcopy(raw[key]) for key in reversed(raw)}
    assert load_behavior_schema(reordered).digest == loaded.digest

    raw["sections"]["frend"]["opaque"] = False
    assert load_behavior_schema(raw).digest != loaded.digest

    formatted = tmp_path / "formatted.json"
    formatted.write_text(json.dumps(reordered, separators=(", ", ": ")), encoding="utf-8")
    assert load_behavior_schema(formatted).digest == loaded.digest


def test_returned_section_is_immutable():
    loaded = load_behavior_schema(DATA / "icukit/valid/bare-current.json")

    with pytest.raises(TypeError):
        loaded.section["sentence"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        loaded.sentence["base"] = "none"  # type: ignore[index]


def test_file_and_mapping_inputs_share_all_caps(tmp_path):
    too_deep = {"schema_version": 1}
    node = too_deep
    for _index in range(16):
        node["sentence"] = {}
        node = node["sentence"]
    too_many = {"schema_version": 1, "sentence": {"base": [None] * 4096}}
    too_long = {"schema_version": 1, "sentence": {"base": "x" * 257}}
    too_large = {
        "schema_version": 1,
        "sentence": {f"option-{index}": "x" * 256 for index in range(260)},
    }

    for index, value in enumerate((too_deep, too_many, too_long, too_large)):
        mapping_error = _error(value)
        path = tmp_path / f"cap-{index}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        file_error = _error(path)
        assert mapping_error.refusals[0].code == file_error.refusals[0].code
        assert mapping_error.refusals[0].code in {"INVALID_JSON", "TOO_LARGE"}


def test_mapping_cycles_and_non_json_values_are_invalid_json():
    cyclic = {"schema_version": 1}
    cyclic["sentence"] = cyclic

    assert _error(cyclic).refusals[0].code == "INVALID_JSON"
    assert _error({"schema_version": 1, "sentence": object()}).refusals[0].code == "INVALID_JSON"
    assert (
        _error({"schema_version": 1, "sentence": {"base": float("nan")}}).refusals[0].code
        == "INVALID_JSON"
    )


def test_excluded_settings_and_regex_patterns_are_unknown_keys():
    for group, option in [
        ("sentence", "path"),
        ("sentence", "exception_policy"),
        ("detection", "material"),
        ("detection", "cache_dir"),
        ("regex", "pattern"),
    ]:
        error = _error({"schema_version": 1, group: {option: "value"}})
        assert error.refusals[0].code == "INVALID_KEY"


@pytest.mark.skipif(
    "max_sentence_chars" not in BEHAVIOR_OPTION_NAMES["sentence"],
    reason="enable automatically when the sentence bound from PR2 reaches main",
)
def test_pr2_sentence_bound_is_wired_when_available():
    loaded = load_behavior_schema({"schema_version": 1, "sentence": {"max_sentence_chars": 512}})

    assert Breaker("en_US", **loaded.sentence).max_sentence_chars == 512


@pytest.mark.skipif(
    not {"time_limit", "stack_limit"} <= set(BEHAVIOR_OPTION_NAMES["regex"]),
    reason="enable automatically when the regex limits from PR2 reach main",
)
def test_pr2_regex_limits_are_wired_when_available():
    loaded = load_behavior_schema(
        {"schema_version": 1, "regex": {"time_limit": 1000, "stack_limit": 1_000_000}}
    )

    regex = UnicodeRegex("a", **loaded.regex)
    assert regex.search("a")
