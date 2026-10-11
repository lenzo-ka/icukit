"""Behavior-schema loader and shared conformance fixtures."""

import copy
import enum
import hashlib
import inspect
import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from icukit import (
    BEHAVIOR_OPTION_NAMES,
    BehaviorLoadError,
    Breaker,
    DetectorSet,
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


@pytest.mark.parametrize(
    ("group", "option", "value"),
    [
        ("sentence", "base", ["none"]),
        ("sentence", "base", {"name": "none"}),
        ("stream", "boundary", ["paragraph"]),
        ("stream", "boundary", {"name": "paragraph"}),
    ],
)
def test_unhashable_option_values_are_refused(group, option, value, tmp_path):
    document = {"schema_version": 1, group: {option: value}}

    mapping_error = _error(document)
    path = tmp_path / "unhashable.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    file_error = _error(path)

    assert [item.code for item in mapping_error.refusals] == ["INVALID_VALUE"]
    assert [item.code for item in file_error.refusals] == ["INVALID_VALUE"]


def test_integers_have_a_signed_64_bit_magnitude_cap(tmp_path):
    maximum = 2**63 - 1
    loaded = load_behavior_schema({"schema_version": 1, "stream": {"max_pending_chars": maximum}})
    assert loaded.stream["max_pending_chars"] == maximum

    mapping_error = _error({"schema_version": 1, "stream": {"max_pending_chars": maximum + 1}})
    path = tmp_path / "huge-integer.json"
    path.write_text(
        '{"schema_version":1,"stream":{"max_pending_chars":' + "9" * 5000 + "}}",
        encoding="utf-8",
    )
    file_error = _error(path)

    assert [item.code for item in mapping_error.refusals] == ["INVALID_JSON"]
    assert [item.code for item in file_error.refusals] == ["INVALID_JSON"]
    assert "9223372036854775807" in mapping_error.refusals[0].detail
    assert "9223372036854775807" in file_error.refusals[0].detail


def test_invalid_icu_date_skeleton_is_refused_at_load():
    error = _error({"schema_version": 1, "detection": {"skeletons": ["!!!"]}})

    assert [item.code for item in error.refusals] == ["INVALID_VALUE"]
    assert "cannot detect skeleton '!!!'" in error.refusals[0].detail


def test_jm_skeleton_is_validated_for_en_us_at_load():
    error = _error(
        {
            "schema_version": 1,
            "detection": {"locales": ["en_US"], "skeletons": ["jm"]},
        }
    )

    assert [item.code for item in error.refusals] == ["INVALID_VALUE"]
    assert "invalid ICU date skeleton 'jm' for locale 'en_US'" in error.refusals[0].detail
    assert "12-hour/day-period" in error.refusals[0].detail


def test_skeleton_validation_checks_every_configured_locale(monkeypatch):
    checked = []

    def date_pattern(locale, skeleton):
        checked.append((locale, skeleton))
        return "HH:mm"

    monkeypatch.setattr("icukit.detectors._date_pattern", date_pattern)

    loaded = load_behavior_schema(
        {
            "schema_version": 1,
            "detection": {"locales": ["en_US", "en_GB"], "skeletons": ["jm", "Hm"]},
        }
    )

    assert loaded.detection["skeletons"] == ("jm", "Hm")
    assert checked == [
        ("en_US", "jm"),
        ("en_GB", "jm"),
        ("en_US", "Hm"),
        ("en_GB", "Hm"),
    ]


def test_multi_error_refusal_count_and_order_are_stable():
    error = _error(
        {
            "schema_version": 2,
            "unknown": True,
            "sentence": {"unknown": True, "base": "missing"},
            "detection": {"flexible": "yes", "guarded": 1},
            "stream": {"boundary": "page", "max_pending_chars": 0},
        }
    )

    assert len(error.refusals) == 8
    assert [(item.code, item.detail.split(": ", 2)[-1]) for item in error.refusals] == [
        (
            "INVALID_KEY",
            "unknown key 'unknown'; known keys: detection, regex, sentence, stream",
        ),
        ("INVALID_SCHEMA_VERSION", "sections.icukit.schema_version must be integer 1, got 2"),
        (
            "INVALID_KEY",
            "unknown key 'unknown'; known keys: base, max_sentence_chars",
        ),
        ("INVALID_VALUE", "sentence.base must be null or a named base, got 'missing'"),
        ("INVALID_VALUE", "detection.flexible must be a bool, got 'yes'"),
        ("INVALID_VALUE", "detection.guarded must be a bool, got 1"),
        (
            "INVALID_VALUE",
            "stream.boundary must be 'paragraph', 'line', or 'explicit', got 'page'",
        ),
        ("INVALID_VALUE", "stream.max_pending_chars must be a positive integer, got 0"),
    ]


def test_option_name_groups_match_receiving_keyword_parameters():
    def keyword_only(target):
        return {
            name
            for name, parameter in inspect.signature(target).parameters.items()
            if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        }

    assert set(BEHAVIOR_OPTION_NAMES["sentence"]) == keyword_only(Breaker)
    assert set(BEHAVIOR_OPTION_NAMES["detection"]) == keyword_only(reader_set) - {"material"}
    assert set(BEHAVIOR_OPTION_NAMES["stream"]) == keyword_only(DetectorSet.stream)
    assert set(BEHAVIOR_OPTION_NAMES["regex"]) == keyword_only(UnicodeRegex)


def test_mapping_input_is_normalized_to_plain_json_scalars():
    class Count(enum.IntEnum):
        SEVEN = 7

    loaded = load_behavior_schema(
        {"schema_version": 1, "stream": {"max_pending_chars": Count.SEVEN}}
    )

    assert loaded.stream["max_pending_chars"] == 7
    assert type(loaded.stream["max_pending_chars"]) is int


def test_duplicate_keys_from_custom_mapping_are_invalid_json():
    class DuplicateMapping(Mapping):
        def __iter__(self):
            return iter(("schema_version", "stream"))

        def __len__(self):
            return 2

        def __getitem__(self, key):
            if key == "schema_version":
                return 1
            if key == "stream":
                return {"max_pending_chars": 7}
            raise KeyError(key)

        def items(self):
            return (
                ("schema_version", 1),
                ("stream", {"max_pending_chars": 3}),
                ("stream", {"max_pending_chars": 7}),
            )

    error = _error(DuplicateMapping())

    assert [item.code for item in error.refusals] == ["INVALID_JSON"]
    assert "duplicate object key 'stream'" in error.refusals[0].detail


def test_too_large_fixture_padding_is_the_byte_cap_condition():
    path = DATA / "envelope/invalid/too-large.json"
    raw = path.read_bytes()

    assert len(raw) > 65_536
    assert len(raw.rstrip()) <= 65_536
    assert [item.code for item in _error(path).refusals] == ["TOO_LARGE"]


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


@pytest.mark.parametrize("value", [None, 1, 512])
def test_pr2_sentence_bound_acceptance_matches_breaker(value):
    document = {"schema_version": 1, "sentence": {"max_sentence_chars": value}}

    loaded = load_behavior_schema(document)
    breaker = Breaker("en_US", **loaded.sentence)

    assert breaker.max_sentence_chars == value


@pytest.mark.parametrize("option", ["time_limit", "stack_limit"])
@pytest.mark.parametrize("value", [None, 1, 1_000_000])
def test_pr2_regex_limit_acceptance_matches_unicode_regex(option, value):
    document = {"schema_version": 1, "regex": {option: value}}

    loaded = load_behavior_schema(document)
    regex = UnicodeRegex("a", **loaded.regex)

    assert getattr(regex, option) == value


@pytest.mark.parametrize(
    ("group", "option", "target"),
    [
        (
            "sentence",
            "max_sentence_chars",
            lambda value: Breaker("en_US", max_sentence_chars=value),
        ),
        ("regex", "time_limit", lambda value: UnicodeRegex("a", time_limit=value)),
        ("regex", "stack_limit", lambda value: UnicodeRegex("a", stack_limit=value)),
    ],
)
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "10"])
def test_pr2_limit_refusals_match_receiving_api(group, option, target, value):
    document = {"schema_version": 1, group: {option: value}}

    assert _error(document).refusals[0].code == "INVALID_VALUE"
    with pytest.raises(ValueError, match=rf"{option} must be a positive int or None"):
        target(value)
