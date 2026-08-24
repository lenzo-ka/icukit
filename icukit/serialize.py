"""recognition-output serializer — converts typed ValueDetection candidates to plain JSON;
no external deps; reusable by downstream consumers.
"""

from __future__ import annotations

import re
from dataclasses import fields, is_dataclass

from .abbreviation_recognize import AbbreviationExpansion, AbbreviationSpec, AbbreviationValue
from .detectors import (
    Capture,
    CompactFormatSpec,
    DateFormatSpec,
    DateIntervalSpec,
    DateIntervalValue,
    DateTimeValue,
    MeasureFormatSpec,
    MeasureValue,
    NumberFormatSpec,
    NumberValue,
    RelativeDateSpec,
    RelativeDateValue,
    SpelloutFormatSpec,
    ValueDetection,
)

__all__ = ["detection_to_dict", "detections_to_json"]


def _snake_case(name: str) -> str:
    """Convert a model class name to its stable JSON kind."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


_KINDS = {
    DateTimeValue: "datetime",
    DateIntervalValue: "date_interval",
    NumberValue: "number",
    MeasureValue: "measure",
    RelativeDateValue: "relative_date",
    AbbreviationValue: "abbreviation",
    AbbreviationExpansion: "abbreviation_expansion",
    Capture: "capture",
    DateFormatSpec: _snake_case(DateFormatSpec.__name__),
    DateIntervalSpec: _snake_case(DateIntervalSpec.__name__),
    NumberFormatSpec: _snake_case(NumberFormatSpec.__name__),
    CompactFormatSpec: _snake_case(CompactFormatSpec.__name__),
    SpelloutFormatSpec: _snake_case(SpelloutFormatSpec.__name__),
    MeasureFormatSpec: _snake_case(MeasureFormatSpec.__name__),
    RelativeDateSpec: _snake_case(RelativeDateSpec.__name__),
    AbbreviationSpec: _snake_case(AbbreviationSpec.__name__),
}


def _to_json(obj):
    """Recursively convert recognition model objects to JSON-native values."""
    if is_dataclass(obj) and not isinstance(obj, type):
        kind = _KINDS.get(type(obj), _snake_case(type(obj).__name__))
        result = {"kind": kind}
        for field in fields(obj):
            name = "format_kind" if field.name == "kind" else field.name
            result[name] = _to_json(getattr(obj, field.name))
        return result
    if isinstance(obj, (tuple, list)):
        return [_to_json(item) for item in obj]
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


def detection_to_dict(detection: ValueDetection) -> dict:
    """Convert one typed detection to an ordered, plain JSON-native dictionary."""
    return {
        "text": detection["text"],
        "start": detection["start"],
        "end": detection["end"],
        "type": detection["type"],
        "value": _to_json(detection["value"]),
        "captures": _to_json(detection["captures"]),
        "spec": _to_json(detection["spec"]),
    }


def detections_to_json(detections) -> list[dict]:
    """Convert typed detections to a list containing only JSON-native values."""
    return [detection_to_dict(detection) for detection in detections]
