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

import icukit.recognize as recognize
from icukit import StartGate, candidate_starts, ungated
from icukit._gate import _SCAN_PLAN, _ScanPlan, gate_report
from icukit.detectors import (
    DateDetector,
    DetectorSet,
    NumberDetector,
    _scan_outcome,
)
from icukit.engine import flexible_detectors, generated_detectors
from icukit.recognize import (
    FlexibleCompactDetector,
    FlexibleCurrencyDetector,
    FlexibleCurrencyNameDetector,
    FlexibleDateDetector,
    FlexibleDateIntervalDetector,
    FlexibleFractionDetector,
    FlexibleMeasureDetector,
    FlexibleMixedMeasureDetector,
    FlexibleNumberDetector,
    FlexiblePercentDetector,
    FlexibleRelativeDateDetector,
    FlexibleSpelloutDetector,
    FlexibleTextDateDetector,
    FlexibleTimeDetector,
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
    number = StartGate(chars=frozenset("+-.0123456789"))
    assert FlexibleNumberDetector("en_US").start_gates() == {
        "decimal": number,
        "other-groupings": number,
        "decimal-styles": StartGate(chars=frozenset("+,-0123456789")),
        "roman": StartGate(chars=frozenset("CDILMVX")),
    }
    assert FlexibleSpelloutDetector("en_US").start_gates()["spellout"] == StartGate(
        folded=frozenset("befhmnostz")
    )
    assert FlexibleCurrencyDetector("en_US", "USD").start_gates()["signed"] == StartGate(
        chars=frozenset("$(+-.0123456789U")
    )
    assert FlexibleCurrencyNameDetector("en_US", "USD").start_gates()["named"] == number
    assert FlexiblePercentDetector("en_US").start_gates()["percent"] == StartGate(
        chars=frozenset("%+-.0123456789")
    )
    assert FlexibleMeasureDetector("en_US", "meter").start_gates() == {
        "amount": number,
        "per-form": StartGate(chars=frozenset("/p")),
    }
    assert FlexibleMixedMeasureDetector("en_US", "foot-and-inch").start_gates()["mixed"] == number
    assert FlexibleCompactDetector("en_US", "short").start_gates()["compact"] == number
    assert FlexibleDateDetector("en_US").start_gates()["date"] == StartGate(
        chars=frozenset("0123456789")
    )
    assert FlexibleTextDateDetector("en_US").start_gates() == {
        "date": StartGate(
            chars=frozenset("0123456789"),
            folded=frozenset("1234adfjmnoqstw"),
        ),
        "day-month": StartGate(
            chars=frozenset("0123456789"),
            folded=frozenset("adfjmnos"),
        ),
        "era": StartGate(chars=frozenset("0123456789")),
    }
    assert FlexibleRelativeDateDetector("en_US").start_gates()["relative"] == StartGate(
        chars=frozenset("+-.0123456789"),
        folded=frozenset("ilnty"),
    )
    assert FlexibleTimeDetector("en_US").start_gates() == {
        "plain": StartGate(chars=frozenset("0123456789")),
        "with-units": StartGate(chars=frozenset("0123456789")),
    }
    assert FlexibleFractionDetector("en_US").start_gates()["fraction"] == StartGate(
        chars=frozenset("+-0123456789¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞↉")
    )
    strict = StartGate(
        chars=frozenset("0123456789"),
        folded=frozenset("0123456789abdefijmnopstw"),
        tests=frozenset({"icu.not_isalpha"}),
    )
    assert DateDetector("en_US", "yMd").start_gates()["scan"] == strict
    assert DateDetector("en_US", "MMMd").start_gates()["scan"] == strict


def test_composite_and_text_prefix_starts_equal_ungated():
    cases = (
        (FlexibleCurrencyDetector("en_US", "USD"), "$5"),
        (FlexibleCurrencyDetector("en_US", "USD"), "USD 5"),
        (FlexibleCurrencyNameDetector("sw_KE", "USD"), "USD 5"),
        (FlexibleMeasureDetector("en_US", "meter"), "per meter"),
        (FlexibleMixedMeasureDetector("en_US", "foot-and-inch"), "5'10\""),
        (FlexibleCompactDetector("sw_KE", "short"), "M1.2"),
        (FlexibleDateDetector("en_US"), "3/5/2024"),
        (FlexibleDateDetector("ja_JP"), "西暦2024/3/5"),
        (FlexibleTextDateDetector("en_US"), "March 5, 2024"),
        (FlexibleTextDateDetector("th_TH"), "ค.ศ. 2024"),
        (FlexibleRelativeDateDetector("en_US"), "in 5 days"),
        (FlexiblePercentDetector("en_US"), "% 5"),
        (FlexibleFractionDetector("en_US"), "½"),
        (FlexibleTimeDetector("ko_KR"), "오전 5:30"),
        (FlexibleTimeDetector("ko_KR"), " 오전 5:30"),
        (
            FlexibleDateIntervalDetector("en_US", "yMMMMd"),
            "March 5\N{THIN SPACE}\N{EN DASH}\N{THIN SPACE}7, 2024",
        ),
    )
    for reader, text in cases:
        with ungated():
            expected = detections_to_json(reader.detect(text))
        assert expected, (type(reader).__name__, text)
        assert detections_to_json(reader.detect(text)) == expected


def test_strict_number_gate_admits_alphabetic_digits():
    reader = NumberDetector("en_US@numbers=hanidec", "decimal")
    digits = frozenset("〇一二三四五六七八九")
    gate = reader.start_gates()["scan"]
    assert gate is not None
    assert digits <= gate.chars
    assert digits <= gate.folded

    for text, expected in (
        ("九", [(0, 1, "number:decimal")]),
        ("x 九 y", [(2, 3, "number:decimal")]),
    ):
        actual = [(item["start"], item["end"], item["type"]) for item in reader.detect(text)]
        with ungated():
            reference = [(item["start"], item["end"], item["type"]) for item in reader.detect(text)]
        assert actual == reference == expected


def test_strict_date_gate_admits_number_formatter_digits():
    reader = DateDetector("en_US@numbers=hanidec", "yMd")
    digits = frozenset("〇一二三四五六七八九")
    gate = reader.start_gates()["scan"]
    assert gate is not None
    assert digits <= gate.chars
    assert digits <= gate.folded


def test_gate_report_accepts_single_detector():
    reader = NumberDetector("en_US", "decimal")
    report = gate_report(reader)
    assert report == gate_report([reader])
    assert len(report) == 1


_PINNED = {
    "yMd": {
        "a": ("Apr/4/2020\u0301", "miss"),
        "d": ("Dec/4/2020\u0301", "miss"),
        "f": ("Feb/4/2020\u0301", "miss"),
        "j": ("Jan/4/2020\u0301", "miss"),
        "m": ("Mar/4/2020\u0301", "miss"),
        "n": ("NaN/4/2020\u0301", "miss"),
        "o": ("Oct/4/2020\u0301", "miss"),
        "s": ("Sep/4/2020\u0301", "miss"),
    },
    "MMMd": {
        "a": ("Apr 4", "reading"),
        "d": ("Dec 4", "reading"),
        "f": ("Feb 4", "reading"),
        "j": ("Jan 4", "reading"),
        "m": ("Mar 4", "reading"),
        "o": ("Oct 4", "reading"),
        "s": ("Sep 4", "reading"),
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
        for head, (witness, expected) in witnesses.items():
            assert _scan_outcome(witness, 0, reader.locale, reader.type, reader._inv) == expected, (
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
            == "miss"
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


def test_strict_month_fallback_mid_grapheme_decline_kept():
    reader = DateDetector("en_US", "yMd")
    text = "Jan/4/2020\u0301"
    gated = reader.detect(text)
    with ungated():
        reference = reader.detect(text)
    assert gated == reference == []


def test_pattern_literal_heads_keep_date_readings():
    cases = {
        "dsb_DE": (
            ("Hm", "stw, zeg. 3:04"),
            ("Hm", "zeg. 3:04"),
            ("Hm", "wał, zeg. 16:27"),
        ),
        "nds_DE": (
            ("Hms", "Klock 16.27:38"),
            ("Hm", "2.1.2020 Kl. 3.04 – 19.8.2021 Kl. 16.27"),
            ("Hm", "Kl. 3.04"),
            ("Hms", "Klock 3.04:05"),
        ),
    }
    gangs = {
        locale: (
            generated_detectors(locale).with_(*flexible_detectors(locale).detectors),
            generated_detectors(locale).with_(*flexible_detectors(locale, guarded=True).detectors),
        )
        for locale in cases
    }
    readers = {
        (locale, skeleton): DateDetector(locale, skeleton)
        for locale, rows in cases.items()
        for skeleton in dict.fromkeys(skeleton for skeleton, _surface in rows)
    }

    for locale, rows in cases.items():
        for skeleton, surface in rows:
            for text in (surface, f"x {surface} y."):
                reader = readers[locale, skeleton]
                with ungated():
                    expected = detections_to_json(reader.detect(text))
                assert expected
                assert detections_to_json(reader.detect(text)) == expected
                for gang in gangs[locale]:
                    with ungated():
                        expected = detections_to_json(gang.detect(text))
                    assert expected
                    assert detections_to_json(gang.detect(text)) == expected


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


def test_supplied_plan_cannot_force_a_mid_grapheme_start():
    text = "1\u20e3"
    gate = StartGate(chars=frozenset("\u20e3"))
    plan = _ScanPlan(
        text,
        {"en_US": (1,)},
        {gate: {"en_US": (1,)}},
        grapheme_boundaries={"en_US": frozenset({0, len(text)})},
    )
    token = _SCAN_PLAN.set(plan)
    try:
        assert candidate_starts(text, "en_US", gate) == ()
    finally:
        _SCAN_PLAN.reset(token)


def test_mid_grapheme_decline_preserves_plan():
    text = "Jan/4/2020\u0301"
    plan = _ScanPlan(text, {"en_US": (0,)}, {})
    token = _SCAN_PLAN.set(plan)
    try:
        assert DateDetector("en_US", "yMd").detect(text) == []
        assert _SCAN_PLAN.get() is plan
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
    assert _scan_outcome("Jan/4/2020\u0301", 0, reader.locale, reader.type, reader._inv) == "miss"
    assert _scan_outcome("3/4/2020", 0, reader.locale, reader.type, reader._inv) == "reading"


def test_date_interval_gate_union_keeps_none_absorbing():
    digit = (None,) * 8 + (True,)
    text = (None,) * 8 + (False,)
    strict = StartGate(folded=frozenset("jm"), tests=frozenset({"icu.not_isalpha"}))
    assert _date_interval_gate((digit,)) == StartGate(tests=frozenset({"icu.isdigit"}))
    assert _date_interval_gate((digit, text)) is None
    assert _date_interval_gate((digit, text), (strict,)) == (
        StartGate(tests=frozenset({"icu.isdigit"})) | strict
    )
    assert _date_interval_gate((digit, text), (None,)) is None


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
