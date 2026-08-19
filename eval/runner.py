"""Run icukit's flexible recognizers against the recall oracle."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleDateDetector,
    FlexibleFractionDetector,
    FlexibleNumberDetector,
    FlexibleOrdinalDetector,
    FlexibleTimeDetector,
)

from .loader import CLASSES

LOCALE = "en_US"
DEFAULT_BASELINE = Path(__file__).parent / "baseline.json"

DetectorFactory = Callable[[], Any]
DETECTORS: dict[str, DetectorFactory] = {
    "cardinal": lambda: FlexibleNumberDetector(LOCALE),
    "decimal": lambda: FlexibleNumberDetector(LOCALE),
    "date": lambda: FlexibleDateDetector(LOCALE),
    "time": lambda: FlexibleTimeDetector(LOCALE),
    "money": lambda: FlexibleCurrencyDetector(LOCALE, "USD"),
    "fraction": lambda: FlexibleFractionDetector(LOCALE),
    "ordinal": lambda: FlexibleOrdinalDetector(LOCALE),
}


def evaluate(
    oracle: Mapping[str, Sequence[tuple[str, str]]],
) -> dict[str, object]:
    """Evaluate strict full-input and lenient any-match recall for every class.

    A strict recognition is a detection of the mapped detector's type whose half-open
    source span is exactly ``[0, len(written))``. A lenient recognition is a detection
    of that type anywhere in the written input. The spoken form is reserved for future
    evaluations and is not used here.
    """
    class_reports: dict[str, dict[str, int | float]] = {}
    overall_total = 0
    overall_strict = 0
    overall_lenient = 0

    for name in CLASSES:
        detector = DETECTORS[name]()
        expected_type = detector.type
        strict_count = 0
        lenient_count = 0
        pairs = oracle[name]
        for written, _spoken in pairs:
            detections = [
                detection
                for detection in detector.detect(written)
                if detection["type"] == expected_type
            ]
            if detections:
                lenient_count += 1
            if any(
                detection["start"] == 0 and detection["end"] == len(written)
                for detection in detections
            ):
                strict_count += 1

        total = len(pairs)
        class_reports[name] = _metrics(total, strict_count, lenient_count)
        overall_total += total
        overall_strict += strict_count
        overall_lenient += lenient_count

    return {
        "criterion": {
            "strict": "expected-type detection spans the full written input",
            "lenient": "expected-type detection occurs anywhere in the written input",
        },
        "locale": LOCALE,
        "classes": class_reports,
        "overall": _metrics(overall_total, overall_strict, overall_lenient),
    }


def _metrics(total: int, strict_count: int, lenient_count: int) -> dict[str, int | float]:
    return {
        "total": total,
        "recognized_strict": strict_count,
        "recognized_lenient": lenient_count,
        "recall_strict": strict_count / total if total else 0.0,
        "recall_lenient": lenient_count / total if total else 0.0,
    }


def format_report(report: Mapping[str, object]) -> str:
    """Format an evaluation report as a readable fixed-width table."""
    header = f"{'class':<10} {'strict':>12} {'recall':>8} {'lenient':>12} {'recall':>8}"
    lines = [header, "-" * len(header)]
    classes = report["classes"]
    assert isinstance(classes, Mapping)
    for name in (*CLASSES, "overall"):
        metrics = report["overall"] if name == "overall" else classes[name]
        assert isinstance(metrics, Mapping)
        total = metrics["total"]
        strict = metrics["recognized_strict"]
        lenient = metrics["recognized_lenient"]
        strict_recall = metrics["recall_strict"]
        lenient_recall = metrics["recall_lenient"]
        lines.append(
            f"{name:<10} {strict:>5}/{total:<6} {strict_recall:>7.1%} "
            f"{lenient:>5}/{total:<6} {lenient_recall:>7.1%}"
        )
    return "\n".join(lines)


def write_report(report: Mapping[str, object], path: Path = DEFAULT_BASELINE) -> None:
    """Write an evaluation report as deterministic, machine-readable JSON."""
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
