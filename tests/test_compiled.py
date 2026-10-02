"""Compilation, implicit reuse, and shared per-text scan plans."""

from __future__ import annotations

import copy
import json
import os
import pickle
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, dataclass

import pytest

import icukit.compiled as compiled_module
from icukit import ReaderSpec, compile_detectors, ungated
from icukit import cache as detector_cache
from icukit._gate import _SCAN_PLAN
from icukit.detectors import DateDetector, DetectorRefusal, DetectorSet, detect, detector_key
from icukit.engine import flexible_detectors, generated_detectors, reader_set
from icukit.recognize import FlexibleNumberDetector
from icukit.serialize import detections_to_json


@dataclass
class _UnhashableReader:
    type: str = "test:reader"
    group: str = "test"

    def detect(self, text):
        return []


@dataclass(frozen=True)
class _PickleReader:
    type: str = "test:reader"
    group: str = "test"

    def detect(self, text):
        return []


class _OddGateReader:
    type = "x:odd"
    group = "x"
    locale = "en_US"

    def detect(self, text):
        return []

    def start_gates(self):
        return {"sentinel": object()}


class _RaisingGateReader:
    type = "x:raising"
    group = "x"
    locale = "en_US"

    def detect(self, text):
        return []

    def start_gates(self):
        raise RuntimeError("not a gate protocol")


class _MalformedLocaleReader:
    type = "x:malformed-locale"
    group = "x"
    locale = "\ud800"

    def detect(self, text):
        return []


class _RefusingReader:
    type = "x:refusing"
    group = "x"
    locale = "en_US"

    def __init__(self, refusal):
        self.refusal = refusal

    def detect(self, text):
        raise self.refusal


@dataclass(frozen=True)
class _NamedSet(DetectorSet):
    label: str = "none"


class _SlottedSet(DetectorSet):
    __slots__ = ("label",)


def _small_gang() -> DetectorSet:
    return DetectorSet((DateDetector("en_US", "yMd"), FlexibleNumberDetector("en_US")))


@pytest.mark.parametrize("text", ("on 3/4/2020", "at -5 now", "😀 12.5 and Jan/4/2020"))
def test_compiled_detect_equals_ungated(text):
    gang = _small_gang()
    compiled = compile_detectors(gang, warm=False)
    with ungated():
        expected = detections_to_json(detect(text, gang.detectors))
    assert detections_to_json(compiled.detect(text)) == expected


def test_detectorset_detect_equals_ungated():
    gang = _small_gang()
    text = "on 3/4/2020 at -5"
    with ungated():
        expected = detections_to_json(detect(text, gang.detectors))
    assert detections_to_json(gang.detect(text)) == expected


def test_number_reader_built_once_per_key(monkeypatch):
    import icukit.recognize as recognize

    recognize._clear_shared_number_reader_cache()
    original = FlexibleNumberDetector.__init__
    keys = []

    def record(self, *args, **kwargs):
        original(self, *args, **kwargs)
        keys.append(recognize._number_reader_key(self))

    monkeypatch.setattr(FlexibleNumberDetector, "__init__", record)
    compile_detectors(ReaderSpec("en_US", flexible=True), warm=False)
    assert len(keys) == len(set(keys)) == 1


def test_compiled_threads_equal_ungated():
    script = """
import json
from icukit.detectors import DateDetector, DetectorSet
from icukit.recognize import FlexibleNumberDetector
from icukit.serialize import detections_to_json
g = DetectorSet((DateDetector('en_US', 'yMd'), FlexibleNumberDetector('en_US')))
rows = ('on 3/4/2020', 'at -5 now', '😀 12.5')
print(json.dumps([detections_to_json(g.detect(row)) for row in rows], sort_keys=True))
"""
    env = {**os.environ, "ICUKIT_GATES": "0"}
    reference = subprocess.run(
        [sys.executable, "-c", script], env=env, text=True, capture_output=True, check=True
    )
    rows = ("on 3/4/2020", "at -5 now", "😀 12.5")
    compiled = compile_detectors(_small_gang(), warm=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        actual = list(pool.map(lambda text: detections_to_json(compiled.detect(text)), rows))
    assert actual == json.loads(reference.stdout)


def test_utf16_text_and_maps_built_once(monkeypatch):
    gang = DetectorSet((DateDetector("en_US", "yMd"), DateDetector("en_US", "MMMd")))
    counts = {"ustr": 0, "maps": 0, "graphemes": 0, "interiors": 0}
    real_ustr = compiled_module.icu.UnicodeString
    real_maps = compiled_module.boundary_maps
    real_break_offsets = compiled_module._break_offsets
    real_interiors = compiled_module._word_interior_offsets

    def ustr(text):
        counts["ustr"] += 1
        return real_ustr(text)

    def maps(text):
        counts["maps"] += 1
        return real_maps(text)

    def break_offsets(ustr, locale, u16_to_cp, *, word):
        if not word:
            counts["graphemes"] += 1
        return real_break_offsets(ustr, locale, u16_to_cp, word=word)

    def interiors(text, locale, edges=None):
        counts["interiors"] += 1
        return real_interiors(text, locale, edges)

    monkeypatch.setattr(compiled_module.icu, "UnicodeString", ustr)
    monkeypatch.setattr(compiled_module, "boundary_maps", maps)
    monkeypatch.setattr(compiled_module, "_break_offsets", break_offsets)
    monkeypatch.setattr(compiled_module, "_word_interior_offsets", interiors)

    compiled = compile_detectors(gang, warm=False)
    text = "3/4/2020 and Mar 4"
    compiled.detect(text)
    compiled.detect(text)

    assert counts == {"ustr": 1, "maps": 1, "graphemes": 1, "interiors": 1}


def test_readerspec_build_s_measured():
    compiled = compile_detectors(ReaderSpec("en_US"), warm=False)
    assert compiled.stats.build_s is not None
    assert compiled.stats.build_s > 0


def test_compiled_set_is_frozen_identity_value():
    compiled = compile_detectors(_small_gang(), warm=False)
    with pytest.raises(FrozenInstanceError):
        compiled.detectors = DetectorSet(())
    assert compiled != compile_detectors(compiled.detectors, warm=False)


def test_readerspec_flexible_is_default_gang():
    actual = compile_detectors(ReaderSpec("en_US", flexible=True), warm=False).detectors
    expected = generated_detectors("en_US").with_(*flexible_detectors("en_US").detectors)
    assert [detector_key(item) for item in actual.detectors] == [
        detector_key(item) for item in expected.detectors
    ]
    assert [detector_key(item) for item in reader_set("en_US", flexible=True).detectors] == [
        detector_key(item) for item in expected.detectors
    ]


def test_compile_failure_falls_back(monkeypatch):
    gang = _small_gang()
    text = "on 3/4/2020"
    expected = detect(text, gang.detectors)

    def fail(_detectors):
        raise RuntimeError("compile failed")

    monkeypatch.setattr(compiled_module, "_implicit_compile", fail)
    assert gang.detect(text) == expected


def test_scan_plan_failure_falls_back_to_legacy_detection():
    reader = _MalformedLocaleReader()
    gang = DetectorSet((reader,))
    assert gang.detect("a") == detect("a", gang.detectors) == []


def test_member_refusal_propagates_from_compiled_detection():
    refusal = DetectorRefusal("x:refusing", 0, 1, "mid-grapheme-endpoint", "test refusal")
    compiled = compile_detectors(DetectorSet((_RefusingReader(refusal),)), warm=False)
    with pytest.raises(DetectorRefusal) as raised:
        compiled.detect("a")
    assert raised.value is refusal


def test_unhashable_member_detect_unchanged():
    gang = DetectorSet((_UnhashableReader(),))
    assert gang.detect("anything") == []
    assert gang._compiled is not None


def test_invalid_third_party_start_gates_leave_reader_ungated():
    gang = DetectorSet((_OddGateReader(),))
    assert gang.detect("hi") == []
    assert gang._compiled._scan_gates == frozenset({None})
    assert gang._compiled.gate_report() == (
        compiled_module.LaneGate(
            detector_key(_OddGateReader()),
            "sentinel",
            False,
            "invalid start_gates(): values must be StartGate or None; reader left ungated",
        ),
    )


def test_raising_third_party_start_gates_leave_reader_ungated():
    compiled = compile_detectors(DetectorSet((_RaisingGateReader(),)), warm=False)
    assert compiled.detect("hi") == []
    assert compiled._scan_gates == frozenset({None})
    assert compiled.gate_report()[0].lane == "<all>"
    assert compiled.gate_report()[0].reason == (
        "start_gates() raised RuntimeError; reader left ungated"
    )


def test_detectorset_pickle_after_detect():
    gang = _NamedSet((_PickleReader(),), "live")
    gang.detect("a")
    pickled = pickle.loads(pickle.dumps(gang))
    copied = copy.deepcopy(gang)
    assert pickled.label == copied.label == "live"
    assert pickled._compiled is copied._compiled is None
    assert pickled.detect("a") == copied.detect("a") == []


def test_detectorset_slotted_subclass_pickle_after_detect():
    gang = _SlottedSet((_PickleReader(),))
    object.__setattr__(gang, "label", "live")
    gang.detect("a")
    pickled = pickle.loads(pickle.dumps(gang))
    copied = copy.deepcopy(gang)
    assert pickled.label == copied.label == "live"
    assert pickled._compiled is copied._compiled is None
    assert pickled.detect("a") == copied.detect("a") == []


def test_plan_reset_after_refusal():
    compiled = compile_detectors(DetectorSet((DateDetector("en_US", "yMd"),)), warm=False)
    with pytest.raises(DetectorRefusal):
        compiled.detect("Jan/4/2020\u0301")
    assert _SCAN_PLAN.get() is None


def test_implicit_key_and_report_are_lazy(monkeypatch):
    gang = _small_gang()

    def fail(*_args, **_kwargs):
        raise AssertionError("reporting ran during detect")

    monkeypatch.setattr(compiled_module, "_compile_key", fail)
    monkeypatch.setattr(compiled_module, "_lane_report", fail)
    assert gang.detect("at 5")


def test_compile_counters_and_implicit_reuse():
    detector_cache._reset_counters()
    gang = _small_gang()
    gang.detect("at 5")
    gang.detect("at 6")
    gang.detect("at 7")
    info = detector_cache.cache_info()
    assert info["compiles"] == 1
    assert info["compiled_reuse"] == 1
    assert info["detect_hits"] == 3


def test_cache_opt_out_bypasses_implicit_compilation():
    gang = _small_gang()
    detector_cache.configure(enabled=False)
    try:
        assert gang.detect("at 5") == detect("at 5", gang.detectors)
        assert gang._compiled is None
    finally:
        detector_cache.configure(enabled=True)


def test_scan_plan_is_looked_up_once_per_lane(monkeypatch):
    import icukit.detectors as detectors_module
    import icukit.recognize as recognize

    calls = {"strict": 0, "flexible": 0}
    strict_plan_for = detectors_module._scan_plan_for
    flexible_plan_for = recognize._scan_plan_for

    def strict(*args):
        calls["strict"] += 1
        return strict_plan_for(*args)

    def flexible(*args):
        calls["flexible"] += 1
        return flexible_plan_for(*args)

    monkeypatch.setattr(detectors_module, "_scan_plan_for", strict)
    monkeypatch.setattr(recognize, "_scan_plan_for", flexible)
    compile_detectors(_small_gang(), warm=False).detect("at 5 on 3/4/2020")
    assert calls == {"strict": 1, "flexible": 4}


def test_number_reader_key_is_not_recomputed_during_matching(monkeypatch):
    import icukit.recognize as recognize

    reader = FlexibleNumberDetector("en_US")

    def fail(_reader):
        raise AssertionError("number-reader key recomputed in the match path")

    monkeypatch.setattr(recognize, "_number_reader_key", fail)
    assert recognize._plain_number_match(reader, "5", 0) is not None


def test_warm_builds_lazy_subreaders_in_build_phase():
    phases = []

    class Reader:
        type = "test:lazy"
        group = "test"

        def _endpoint_readers(self):
            phases.append(detector_cache._PHASE.get())
            return ()

        def detect(self, text):
            return []

    compile_detectors(DetectorSet((Reader(),)))
    assert phases == ["build"]
