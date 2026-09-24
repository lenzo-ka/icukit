"""A detector keeps no per-call state, so a call nested inside another cannot disturb it."""

import icukit.recognize as recognize
from icukit.recognize import FlexibleDateIntervalDetector, FlexibleTimeDetector


def _nest_once(monkeypatch, detector, nested_text, on_call):
    """Run ``detector.detect(nested_text)`` inside the ``on_call``-th scan of an outer call."""
    real = recognize._detect_flexible
    calls = {"count": 0, "nested": False}

    def wrapped(text, locale, type_label, spec, match):
        calls["count"] += 1
        if calls["count"] == on_call and not calls["nested"]:
            calls["nested"] = True
            detector.detect(nested_text)
        return real(text, locale, type_label, spec, match)

    monkeypatch.setattr(recognize, "_detect_flexible", wrapped)
    return calls


def test_a_nested_time_call_does_not_turn_off_the_outer_unit_pass(monkeypatch):
    detector = FlexibleTimeDetector("en_US")
    # The outer call's second scan is the one that reads a trailing hour unit.
    calls = _nest_once(monkeypatch, detector, "at 5pm", on_call=2)

    surfaces = [d["text"] for d in detector.detect("10:30 hr later")]

    assert calls["nested"]
    assert surfaces == ["10:30", "10:30 hr"]


def test_a_nested_interval_call_does_not_clear_the_outer_offset_maps(monkeypatch):
    detector = FlexibleDateIntervalDetector("en_US", "yMMMd")
    expected = [d["text"] for d in detector.detect("from Jan 3 – 5, 2026 on")]
    calls = _nest_once(monkeypatch, detector, "nothing here", on_call=1)

    surfaces = [d["text"] for d in detector.detect("from Jan 3 – 5, 2026 on")]

    assert calls["nested"]
    assert surfaces == expected
