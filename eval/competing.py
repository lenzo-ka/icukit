"""Evaluate conjunctive typed-span expectations outside normalization classes."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from icukit.detectors import detect
from icukit.recognize import (
    FlexibleNumberDetector,
    LetterNameDetector,
    SingleLetterWordDetector,
)

from .runner import LOCALE

DEFAULT_COMPETING_ORACLE = Path(__file__).parent / "data" / "competing.json"


class ExpectedSpan(TypedDict):
    """One typed source span required by a competing-reading record."""

    type: str
    start: int
    end: int


class CompetingReading(TypedDict):
    """An input whose measured readings coexist or are forbidden.

    ``characterizes`` explains when a passing record pins behavior without endorsing it.
    """

    input: str
    expected: list[ExpectedSpan]
    forbidden: list[ExpectedSpan]
    exact: NotRequired[bool]
    characterizes: NotRequired[str]


def load_competing(path: Path = DEFAULT_COMPETING_ORACLE) -> list[CompetingReading]:
    """Load conjunctive typed-span expectations from JSON."""
    return cast(list[CompetingReading], json.loads(path.read_text(encoding="utf-8")))


def evaluate_competing(records: Sequence[CompetingReading]) -> dict[str, Any]:
    """Score records only when every expected typed span is detected."""
    detectors = (
        FlexibleNumberDetector(LOCALE),
        LetterNameDetector(LOCALE),
        SingleLetterWordDetector(LOCALE),
    )
    recognized = 0
    for record in records:
        expected_items = record.get("expected", [])
        forbidden_items = record.get("forbidden", [])
        if not expected_items and not forbidden_items:
            raise ValueError("competing-reading record has no expectations")
        actual = {
            (item["type"], item["start"], item["end"])
            for item in detect(record["input"], detectors)
        }
        expected = {(item["type"], item["start"], item["end"]) for item in expected_items}
        forbidden = {(item["type"], item["start"], item["end"]) for item in forbidden_items}
        matches = expected <= actual and actual.isdisjoint(forbidden)
        if record.get("exact", False):
            matches = matches and actual == expected
        recognized += matches

    total = len(records)
    return {
        "criterion": "expected spans present; forbidden spans absent; exact records have no others",
        "total": total,
        "recognized": recognized,
        "characterizing_records": sum("characterizes" in record for record in records),
        "recall": recognized / total if total else 0.0,
    }
