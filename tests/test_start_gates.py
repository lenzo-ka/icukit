"""Soundness, isolation, and change-detector tests for detection start gates."""

import inspect
import json
import os
import random
import subprocess
import sys
import threading
import time
import unicodedata

import icu
import pytest

import icukit.recognize as recognize
from icukit import StartGate, candidate_starts, ungated
from icukit._gate import _SCAN_PLAN, _ScanPlan
from icukit.detectors import (
    DateDetector,
    DetectorRefusal,
    DetectorSet,
    NumberDetector,
    _scan_outcome,
)
from icukit.engine import flexible_detectors, generated_detectors
from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleDateIntervalDetector,
    FlexibleNumberDetector,
    FlexibleSpelloutDetector,
    _date_interval_gate,
)
from icukit.serialize import detections_to_json


def _default_gang() -> DetectorSet:
    return generated_detectors("en_US").with_(*flexible_detectors("en_US").detectors)


def test_every_start_lane_declares_gate():
    for _name, reader_class in inspect.getmembers(recognize, inspect.isclass):
        if reader_class.__module__ != recognize.__name__:
            continue
        source = inspect.getsource(reader_class)
        if "_detect_flexible(" in source or "_detect_flexible_alternatives(" in source:
            assert hasattr(reader_class, "start_gates"), reader_class.__name__
    readers = (
        DateDetector("en_US", "yMd"),
        NumberDetector("en_US", "decimal"),
        FlexibleDateIntervalDetector("en_US", "yMd"),
        FlexibleNumberDetector("en_US"),
        FlexibleCurrencyDetector("en_US", "USD"),
        FlexibleSpelloutDetector("en_US"),
    )
    expected = (
        {"scan"},
        {"scan"},
        {"interval"},
        {"decimal", "other-groupings", "decimal-styles", "roman"},
        {"signed"},
        {"spellout"},
    )
    for reader, lanes in zip(readers, expected, strict=True):
        assert set(reader.start_gates()) == lanes


def test_en_US_gate_literals():
    assert FlexibleNumberDetector("en_US").start_gates() == {
        "decimal": StartGate(chars=frozenset("+-.0123456789")),
        "other-groupings": StartGate(chars=frozenset("+-.0123456789")),
        "decimal-styles": StartGate(chars=frozenset("+,-0123456789")),
        "roman": StartGate(chars=frozenset("CDILMVX")),
    }
    assert FlexibleSpelloutDetector("en_US").start_gates()["spellout"] == StartGate(
        folded=frozenset("befhmnostz")
    )
    assert FlexibleCurrencyDetector("en_US", "USD").start_gates()["signed"] == StartGate(
        chars=frozenset("$(+-.0123456789U")
    )
    strict = StartGate(
        folded=frozenset("abdefijmnopstw"),
        tests=frozenset({"icu.not_isalpha"}),
    )
    assert DateDetector("en_US", "yMd").start_gates()["scan"] == strict
    assert DateDetector("en_US", "MMMd").start_gates()["scan"] == strict


_PINNED = {
    "yMd": {
        "a": "Apr/4/2020\u0301",
        "d": "Dec/4/2020\u0301",
        "f": "Feb/4/2020\u0301",
        "j": "Jan/4/2020\u0301",
        "m": "Mar/4/2020\u0301",
        "n": "NaN/4/2020\u0301",
        "o": "Oct/4/2020\u0301",
        "s": "Sep/4/2020\u0301",
    },
    "MMMd": {
        "a": "Apr 4",
        "d": "Dec 4",
        "f": "Feb 4",
        "j": "Jan 4",
        "m": "Mar 4",
        "n": "NaN 4\u0301",
        "o": "Oct 4",
        "s": "Sep 4",
    },
}


def _unicode_scalars():
    unassigned_signatures = set()
    for value in range(0x110000):
        if 0xD800 <= value <= 0xDFFF:
            continue
        char = chr(value)
        if icu.Char.charType(char) != icu.UCharCategory.UNASSIGNED:
            yield char
            continue
        signature = (
            bool(icu.Char.hasBinaryProperty(char, icu.UProperty.DEFAULT_IGNORABLE_CODE_POINT)),
            bool(icu.Char.hasBinaryProperty(char, icu.UProperty.WHITE_SPACE)),
            bool(icu.Char.isalpha(char)),
            bool(icu.Char.isdigit(char)),
        )
        if signature not in unassigned_signatures:
            unassigned_signatures.add(signature)
            yield char


def _rejected_sample(gate: StartGate, size: int = 2000) -> tuple[str, ...]:
    rng = random.Random(0)
    reservoir = []
    seen = 0
    for char in _unicode_scalars():
        if gate.admits(char):
            continue
        seen += 1
        if len(reservoir) < size:
            reservoir.append(char)
            continue
        slot = rng.randrange(seen)
        if slot < size:
            reservoir[slot] = char
    return tuple(reservoir)


def test_gate_complement_reduced_en_US():
    """Reduced V7; measured at 2.65 s locally, with a hard 60-second budget."""
    started = time.perf_counter()
    sample = None
    for skeleton, witnesses in _PINNED.items():
        reader = DateDetector("en_US", skeleton)
        gate = reader.start_gates()["scan"]
        assert gate is not None
        if sample is None:
            sample = _rejected_sample(gate)
        for head in gate.folded:
            relatives = {
                head,
                head.upper(),
                head.lower(),
                head.title(),
                head.casefold(),
                unicodedata.normalize("NFKC", head),
                unicodedata.normalize("NFKC", head.upper()),
            }
            assert all(not relative or gate.admits(relative[0]) for relative in relatives)
        for head, witness in witnesses.items():
            assert _scan_outcome(witness, 0, reader.locale, reader.type, reader._inv) != "miss", (
                head
            )
        assert (
            _scan_outcome(
                "Jan/4/2020\u0301" if skeleton == "yMd" else "Jan 4\u0301",
                0,
                reader.locale,
                reader.type,
                reader._inv,
            )
            == "raise"
        )
        tail = "/4/2020\u0301" if skeleton == "yMd" else " 4\u0301"
        for char in sample:
            assert _scan_outcome(char + tail, 0, reader.locale, reader.type, reader._inv) == "miss"
    assert time.perf_counter() - started <= 60


def test_ungated_not_served_from_gated_cache():
    text = "$5"
    gate = StartGate(chars=frozenset("5"))
    assert candidate_starts(text, "en_US", gate) == (1,)
    with ungated():
        assert candidate_starts(text, "en_US", gate) == (0, 1)


def test_strict_month_fallback_refusal_kept():
    reader = DateDetector("en_US", "yMd")
    text = "Jan/4/2020\u0301"
    with pytest.raises(DetectorRefusal) as gated:
        reader.detect(text)
    with ungated(), pytest.raises(DetectorRefusal) as reference:
        reader.detect(text)
    assert (gated.value.reason, gated.value.start) == (
        reference.value.reason,
        reference.value.start,
    )


def test_gate_audit_catches_canary():
    script = """
import json
from icukit import _gate
from icukit.recognize import FlexibleCurrencyDetector
r = FlexibleCurrencyDetector('en_US', 'USD')
assert r.detect('$5') == []
print(json.dumps(_gate.lane_stats(), sort_keys=True))
"""
    env = {
        **os.environ,
        "ICUKIT_GATE_AUDIT": "1",
        "ICUKIT_GATE_CANARY": "FlexibleCurrencyDetector:USD:signed:$",
    }
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, text=True, capture_output=True, check=True
    )
    stats = json.loads(result.stdout)
    lane = "FlexibleCurrencyDetector|en_US|number:currency:USD|signed"
    assert stats[lane]["audit_probed"] > 0
    assert stats[lane]["audit_violations"] > 0


def test_substring_subreader_ignores_plan():
    parent = "xx5"
    child = (" " + parent[2:])[1:]
    gate = StartGate(chars=frozenset("5"))
    plan = _ScanPlan(parent, {"en_US": (0, 1, 2)}, {gate: {"en_US": (2,)}})
    token = _SCAN_PLAN.set(plan)
    try:
        assert child == "5" and child is not parent
        assert candidate_starts(child, "en_US", gate) == (0,)
    finally:
        _SCAN_PLAN.reset(token)


def test_fulltext_nonmember_subreader_falls_back():
    text = "a5"
    member = StartGate(chars=frozenset("a"))
    nonmember = StartGate(chars=frozenset("5"))
    plan = _ScanPlan(text, {"en_US": (0, 1)}, {member: {"en_US": (0,)}})
    token = _SCAN_PLAN.set(plan)
    try:
        assert candidate_starts(text, "en_US", nonmember) == (1,)
    finally:
        _SCAN_PLAN.reset(token)


def test_plan_reset_after_refusal():
    text = "Jan/4/2020\u0301"
    plan = _ScanPlan(text, {"en_US": (0,)}, {})
    token = _SCAN_PLAN.set(plan)
    try:
        with pytest.raises(DetectorRefusal):
            DateDetector("en_US", "yMd").detect(text)
    finally:
        _SCAN_PLAN.reset(token)
    assert _SCAN_PLAN.get() is None


def test_ungated_is_context_local():
    barrier = threading.Barrier(2)
    release = threading.Event()
    results = {}
    gate = StartGate(chars=frozenset("5"))

    def first():
        with ungated():
            barrier.wait()
        results["first"] = candidate_starts("a5", "en_US", gate)
        release.set()

    def second():
        with ungated():
            barrier.wait()
            release.wait()
            results["second"] = candidate_starts("a5", "en_US", gate)

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == {"first": (1,), "second": (0, 1)}


def test_fuzz_witnesses_keep_readings():
    gang = DetectorSet(
        (
            DateDetector("en_US", "yMd"),
            FlexibleNumberDetector("en_US"),
            FlexibleCurrencyDetector("en_US", "USD"),
            FlexibleSpelloutDetector("en_US"),
        )
    )
    rows = (
        "at -5 now",
        "at (5) now",
        "paid ($5.00) today",
        "costs ,5 more",
        "Jan/4/2020",
        "😀 before 5 after",
        "twenty-three",
    )
    for text in rows:
        actual = detections_to_json(gang.detect(text))
        with ungated():
            assert actual == detections_to_json(gang.detect(text))


def test_scan_outcome_mapping():
    reader = DateDetector("en_US", "yMd")
    assert _scan_outcome("Jan/4/2020\u0301", 0, reader.locale, reader.type, reader._inv) == "raise"
    assert _scan_outcome("3/4/2020", 0, reader.locale, reader.type, reader._inv) == "reading"


def test_mixed_date_interval_lane_is_ungated():
    digit = (None,) * 8 + (True,)
    text = (None,) * 8 + (False,)
    assert _date_interval_gate((digit,)) == StartGate(tests=frozenset({"icu.isdigit"}))
    assert _date_interval_gate((digit, text)) is None


def test_detectorset_detect_equals_ungated():
    gang = _default_gang()
    rows = (
        "Retrieved 23 September 2010 .",
        "Retrieved July 25, 2015 .",
        "Finedon : J.L.H. Bailey .",
        "at -5 now",
        "paid ($5.00) today",
        "costs ,5 more",
        "Jan/4/2020",
        "5 kg at 10:30 PM",
    )
    for text in rows:
        actual = detections_to_json(gang.detect(text))
        with ungated():
            assert actual == detections_to_json(gang.detect(text))
