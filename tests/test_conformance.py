"""Regression gate and positive controls for detector round-trip conformance.

The gate compares a committed inventory against the one this interpreter's ICU
produces, so it is only meaningful on the ICU the inventory was recorded on. That
made it easy for the gate to fall silent: the module used to skip itself whole
when the versions differed, and ``icukit-pyicu`` is declared with a floor rather
than an equality, so an ordinary dependency resolve could move ICU forward and
take the entire detector-conformance signal with it -- including the guard that
the inventory is not passing vacuously -- while the build stayed green.

Two changes close that. The mismatch is now reported rather than swallowed:
:func:`test_golden_records_the_running_icu` fails the build wherever a stale
golden must not pass unnoticed (see :func:`_stale_golden_is_fatal`), and warns
everywhere else. And only the one assertion that genuinely needs the recorded
ICU -- the byte-for-byte comparison against the committed file -- is conditional
on the version. The digest, the positive controls, the anti-vacuity guard and the
negative mutation controls describe live ICU behavior, so they run on every ICU
and keep their force exactly when the golden has gone stale.
"""

import json
import os
import warnings
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

GOLDEN_RECORDS_RUNNING_ICU = icu.ICU_VERSION == GOLDEN["icu_version"]

STALE_GOLDEN = (
    f"the detector conformance golden was recorded on ICU {GOLDEN['icu_version']} "
    f"(Unicode {GOLDEN['unicode_version']}), but this interpreter has ICU {icu.ICU_VERSION} "
    f"(Unicode {icu.UNICODE_VERSION}), and a recorded inventory does not carry across ICU "
    f"versions. Regenerate it with `python tools/update_detector_conformance.py --profile ci "
    f"--write` and commit the result, or install a backend carrying ICU {GOLDEN['icu_version']}."
)


class StaleConformanceGolden(UserWarning):
    """The committed inventory does not describe the ICU this run is using."""


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() not in ("", "0", "false", "no")


def _stale_golden_is_fatal() -> bool:
    """Where a stale golden stops the build rather than merely reporting itself.

    CI is that place. An ICU bump arriving in CI with no regenerated golden is
    precisely the drift this module exists to catch, and nobody is watching a
    warning there. A developer running against whatever ICU their machine has is
    not doing anything wrong, so locally the mismatch is warned about and only
    the byte-for-byte comparison steps aside; every other test here still runs.
    ``ICUKIT_CONFORMANCE_STRICT=1`` opts into the CI behavior locally.
    """
    return _truthy(os.environ.get("CI")) or _truthy(os.environ.get("ICUKIT_CONFORMANCE_STRICT"))


if not GOLDEN_RECORDS_RUNNING_ICU:
    # Surfaces in pytest's warnings summary, so the mismatch is visible even to a
    # run that only reads the last screen of output.
    warnings.warn(STALE_GOLDEN, StaleConformanceGolden, stacklevel=1)

requires_golden_icu = pytest.mark.skipif(
    not GOLDEN_RECORDS_RUNNING_ICU,
    reason="a recorded inventory is only comparable on the ICU that recorded it",
)


def test_golden_records_the_running_icu():
    """The version gate must announce itself, not disappear quietly.

    This is the whole point of the module's version handling: a mismatch is a
    maintenance task that somebody has to do, so it has to reach somebody. Where
    a stale golden must not pass unnoticed it fails here; elsewhere it warns and
    the run continues with one comparison skipped.
    """
    if GOLDEN_RECORDS_RUNNING_ICU:
        return
    if _stale_golden_is_fatal():
        pytest.fail(STALE_GOLDEN, pytrace=False)
    pytest.skip(STALE_GOLDEN)


def test_golden_file_name_agrees_with_what_it_records():
    """The versions in the name are load-bearing, so they must not drift from the body.

    Regenerating in place on a newer ICU leaves a file named for the old one, and
    a name that lies about its contents is how the next reader is misled about
    which ICU the gate speaks for. Runs on every ICU: the claim is about the file,
    not about the interpreter.
    """
    icu_slug = GOLDEN["icu_version"].replace(".", "_")
    unicode_slug = GOLDEN["unicode_version"].replace(".", "_")
    assert GOLDEN_PATH.name == f"detector_conformance_icu{icu_slug}_unicode{unicode_slug}.json"


@requires_golden_icu
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
    """The inventory has to be measuring something, on whatever ICU is running.

    Counted from the inventory this interpreter actually produces rather than from
    the recorded file, because the guard against a vacuous gate is worth least
    when it can only speak about the ICU the gate already agrees with. An ICU that
    made most cells unsupported would satisfy a byte-comparison against a freshly
    regenerated golden while measuring almost nothing; this fails instead.
    """
    inventory = build_inventory("ci")
    total = len(iter_cells("ci"))
    failed = len(inventory["defects"]) + len(inventory["unsupported_cells"])
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
