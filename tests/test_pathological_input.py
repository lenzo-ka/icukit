"""Pathological detection inputs remain bounded and non-raising."""

import statistics
import time
from functools import cache

import pytest

from icukit.engine import reader_set
from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleFractionDetector,
    FlexibleMeasureDetector,
    FlexibleNumericDurationDetector,
    PluralNumeralDetector,
    _currency_amount_memo,
    _number_memo,
)

_PATHOLOGICAL_LOCALES = ("en_US", "de_DE", "fr_FR", "ja_JP", "zh_CN", "th_TH", "ar_EG")
_PATHOLOGICAL_RUNS = (
    ("a", "a"),
    ("1", "1"),
    ("period", "."),
    ("dash", "-"),
    ("space", " "),
    ("han", "一"),
    ("thai", "ก"),
    ("combining", "\N{COMBINING ACUTE ACCENT}"),
    ("nbsp", "\N{NO-BREAK SPACE}"),
    ("one-space", "1 "),
    ("minus-one", "-1"),
    ("spellout", "one "),
    ("slash", "1/"),
    ("fraction-slash", "1\N{FRACTION SLASH}"),
)


def _fixed_run(unit: str, size: int) -> str:
    return (unit * (size // len(unit) + 1))[:size]


@cache
def _pathological_gang(locale: str):
    return reader_set(locale, flexible=True, guarded=True)


@cache
def _realistic_64k_seconds(locale: str) -> float:
    text = ("Alice paid 12.50 for 3 meters on May 5, 2026. " * 1400)[:65_536]
    started = time.process_time()
    _pathological_gang(locale).detect(text)
    return time.process_time() - started


def test_64k_digit_run_does_not_raise():  # R
    text = "1" * 65_536

    assert PluralNumeralDetector("en_US").detect(text) == []
    assert FlexibleNumericDurationDetector("en_US").detect(text) == []


def test_long_digit_capture_is_kept_with_unrepresentable_int_value():  # R
    digits = "1" * 4301
    plural = PluralNumeralDetector("en_US").detect(digits + "s")[0]
    duration = FlexibleNumericDurationDetector("en_US").detect(digits + ":02")[0]

    assert plural["captures"][0].value is None
    assert plural["value"].decimal == digits
    assert duration["captures"][0].value is None
    assert duration["value"].decimal.isdecimal()
    assert len(duration["value"].decimal) >= len(digits)


@pytest.mark.parametrize(
    "surface",
    [
        "{digits} 1/2",
        "{digits}/2",
        "1/{digits}",
        "{digits}\N{FRACTION SLASH}2",
    ],
)
def test_long_fraction_digit_components_do_not_raise(surface):  # R
    text = surface.format(digits="1" * 4301)

    detections = FlexibleFractionDetector("en_US").detect(text)

    assert [item["text"] for item in detections] == (["1/2"] if " 1/2" in text else [])


def test_stream_cap_on_64k_run():  # S
    stream = reader_set("en_US", flexible=True).stream()

    batch = stream.feed("1" * 65_536)
    tail = stream.close()
    detections = (*batch.detections, *tail.detections)

    assert batch.cuts == tuple(range(4096, 65_536, 4096))
    assert any(item.get("truncated") for item in detections)
    assert batch.pending_from >= 65_536 - 4096


@pytest.mark.slow
@pytest.mark.parametrize("locale", _PATHOLOGICAL_LOCALES)
@pytest.mark.parametrize(
    ("run_name", "unit"),
    _PATHOLOGICAL_RUNS,
    ids=[name for name, _unit in _PATHOLOGICAL_RUNS],
)
def test_64k_runs(locale, run_name, unit):  # R; en_US a/period/dash are C
    gang = _pathological_gang(locale)
    timings = {}
    for size in (16_384, 65_536):
        started = time.process_time()
        gang.detect(_fixed_run(unit, size))
        timings[size] = time.process_time() - started

    assert timings[65_536] / timings[16_384] <= 6, (locale, run_name, timings)
    if locale == "en_US":
        assert timings[65_536] <= 3 * _realistic_64k_seconds(locale), (
            locale,
            run_name,
            timings,
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "detector",
    [
        FlexibleCurrencyDetector("en_US", "USD"),
        FlexibleMeasureDetector("en_US", "meter"),
    ],
    ids=["currency", "measure"],
)
def test_dash_run_scales_linearly(detector):  # C: scales linearly on current main
    timings = {}
    for size in (16_384, 65_536):
        trials = []
        for trial in range(3):
            _number_memo.cache_clear()
            _currency_amount_memo.cache_clear()
            text = "-" * size + chr(ord("A") + trial)
            started = time.process_time()
            assert detector.detect(text) == []
            trials.append(time.process_time() - started)
        timings[size] = statistics.median(trials)

    assert timings[65_536] / timings[16_384] <= 6, timings
