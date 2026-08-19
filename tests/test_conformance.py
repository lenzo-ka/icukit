"""Regression gate and positive controls for detector round-trip conformance."""

import json
from dataclasses import replace
from pathlib import Path

import icu
import pytest

from icukit.conformance import (
    Cell,
    build_inventory,
    canonical_json,
    classify,
    compare_expected,
    iter_cells,
    matrix_digest,
)
from icukit.detectors import DateDetector, NumberDetector

GOLDEN_PATH = Path(__file__).parent / "data/detector_conformance_icu78_3_unicode17_0.json"
GOLDEN = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

if icu.ICU_VERSION != GOLDEN["icu_version"]:
    pytest.skip(
        f"conformance golden requires ICU {GOLDEN['icu_version']}; found {icu.ICU_VERSION}",
        allow_module_level=True,
    )


def test_ci_inventory_matches_committed_golden():
    assert canonical_json(build_inventory("ci")) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_golden_digest_matches_current_matrix():
    assert GOLDEN["matrix_digest"] == matrix_digest("ci")


def test_positive_controls_recover():
    thai = Cell("th_TH", "date", "yMMMd", "2026-01-03T15:45:00Z", "bare")
    assert classify(thai).reason == "recovered"
    detector_inventory = build_inventory("ci")
    thai_defects = {record["cell_id"] for record in detector_inventory["defects"]}
    assert thai.cell_id not in thai_defects
    instant = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale("en_US@calendar=gregorian")
    )
    instant.clear()
    instant.set(2026, 0, 3, 15, 45, 0)
    thai_detector = DateDetector("th_TH", "yMMMd")
    pattern = icu.DateTimePatternGenerator.createInstance(icu.Locale("th_TH")).getBestPattern(
        "yMMMd"
    )
    formatter = icu.SimpleDateFormat(pattern, icu.Locale("th_TH"))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    thai_detection = thai_detector.detect(formatter.format(instant.getTime()))[0]
    assert dict(thai_detection["value"].fields)["y"] == 2569

    percent = Cell("en_US", "number", "percent", "0.07", "bare")
    assert classify(percent).reason == "recovered"
    number_detector = NumberDetector("en_US", "decimal")
    number_surface = icu.NumberFormat.createInstance(icu.Locale("en_US")).format(-1234567.5)
    assert number_detector.detect(number_surface)[0]["value"].decimal == "-1234567.5"


def test_inventory_cannot_pass_vacuously():
    total = len(iter_cells("ci"))
    failed = len(GOLDEN["defects"]) + len(GOLDEN["unsupported_cells"])
    assert total - failed >= 100


def test_negative_mutation_controls_discriminate_value_captures_and_spec():
    detector = NumberDetector("en_US", "decimal")
    surface = icu.NumberFormat.createInstance(icu.Locale("en_US")).format(-1234567.5)
    detection = detector.detect(surface)[0]
    value = detection["value"]
    captures = detection["captures"]
    spec = detection["spec"]

    wrong_value = replace(value, decimal="999")
    assert (
        compare_expected(detection, surface, wrong_value, captures, spec, surface).reason
        == "value-mismatch"
    )

    dropped_capture = tuple(capture for capture in captures if capture.name != "sign")
    assert (
        compare_expected(detection, surface, value, dropped_capture, spec, surface).reason
        == "capture-mismatch"
    )
    wrong_capture_value = tuple(
        replace(capture, value="corrupt") if capture.name == "integer" else capture
        for capture in captures
    )
    assert (
        compare_expected(detection, surface, value, wrong_capture_value, spec, surface).reason
        == "capture-mismatch"
    )

    wrong_spec = replace(spec, max_fraction=spec.max_fraction + 1)
    assert (
        compare_expected(detection, surface, value, captures, wrong_spec, surface).reason
        == "spec-mismatch"
    )
