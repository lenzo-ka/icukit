"""Detection-side k=1 pruning."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from icukit import cache
from icukit.detectors import NumberFormatSpec, NumberValue, ValueDetection, detect
from icukit.engine import clear_detector_caches, reader_set
from icukit.serialize import detections_to_json


@pytest.fixture(autouse=True)
def _clear_gang_cache_after_test():
    yield
    clear_detector_caches()


def test_none_is_the_keep_all_identity():
    gang = reader_set("en_US")
    text = "Due March 5, 2024, up 12%"
    assert detections_to_json(gang.detect(text, k=None)) == detections_to_json(gang.detect(text))
    assert all("near_tie" not in item for item in gang.detect(text, k=None))


def test_one_best_is_leftmost_longest_and_keeps_same_span_alternatives():
    gang = reader_set("en_US", flexible=True)
    readings = gang.detect("1/2", k=1)
    assert {(item["start"], item["end"]) for item in readings} == {(0, 3)}
    assert {item["type"] for item in readings} >= {"date:Md", "fraction:flexible"}


def test_real_default_gang_near_tie_flags_winner_and_rival():
    # At offset 4, "-3" wins by leftmost order; the equal-or-longer "3/4" starts
    # inside it. The later "4" is a legitimate next winner overlapping that rival.
    found = reader_set("en_US").detect("21/2-3/4", k=1)
    flagged = {(item["text"], item["start"], item["end"]) for item in found if item.get("near_tie")}
    assert flagged == {("-3", 4, 6), ("3/4", 5, 8)}
    assert ("4", 7, 8) in {(item["text"], item["start"], item["end"]) for item in found}


def test_without_near_tie_search_starts_inside_winner_are_not_tried(monkeypatch):
    import icukit._gate as gate

    class Reader:
        group = "test"
        locale = "en_US"

        def __init__(self, type_, readings):
            self.type = type_
            self.readings = readings

        def start_gates(self):
            return {"read": None}

        def _prepare_readings(self, text):
            def read(start):
                gate._record_member_attempt(f"Reader|en_US|{self.type}|read", start)
                end = self.readings.get(start)
                if end is None:
                    return []
                return [
                    ValueDetection(
                        text=text[start:end],
                        start=start,
                        end=end,
                        type=self.type,
                        value=NumberValue(str(start)),
                        captures=(),
                        spec=NumberFormatSpec("en_US", "decimal"),
                    )
                ]

            return read

        def detect(self, text):
            return [
                item for start in range(len(text)) for item in self._prepare_readings(text)(start)
            ]

    monkeypatch.setattr(gate, "GATE_STATS", True)
    monkeypatch.setenv("ICUKIT_KBEST_NEAR_TIES", "0")
    gate.reset_lane_stats()
    winner = Reader("test:winner", {0: 5})
    hidden = Reader("test:hidden", {1: 6})
    found = detect("abcdef", (winner, hidden), k=1)
    assert [(item["start"], item["end"]) for item in found] == [(0, 5)]
    # Both members are tried at 0 and again at cursor 5; none is tried at starts 1..4.
    assert gate.attempt_stats()["1"] == 4


@pytest.mark.parametrize("k", [0, 2, 4])
def test_unsupported_k_needs_path_scores(k):
    with pytest.raises(ValueError, match="needs path scores.*pass k=None.*cap paths downstream"):
        detect("1", (), k=k)


def test_cache_on_and_off_agree():
    text = "21/2-3/4 and 1/2"
    gang = reader_set("en_US", flexible=True)
    cache.configure(enabled=True)
    expected = detections_to_json(gang.detect(text, k=1))
    try:
        cache.configure(enabled=False)
        actual = detections_to_json(gang.detect(text, k=1))
    finally:
        cache.configure(enabled=True)
    assert actual == expected


def test_cli_k_one_json():
    result = subprocess.run(
        [sys.executable, "-m", "icukit.cli", "detect", "--k", "1", "-t", "21/2-3/4", "--json"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert {(item["text"], item.get("near_tie")) for item in payload} >= {
        ("-3", True),
        ("3/4", True),
    }
