"""Tests for typed recognition serialization."""

import json

import pytest

from icukit.abbreviation_recognize import AbbreviationSpec, AbbreviationValue
from icukit.detectors import (
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
from icukit.serialize import _to_json, detection_to_dict, detections_to_json


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (DateTimeValue((("y", 2025), ("M", 8)), "gregorian"), "datetime"),
        (
            DateIntervalValue(
                DateTimeValue((("d", 1),), "gregorian"),
                DateTimeValue((("d", 3),), "gregorian"),
            ),
            "date_interval",
        ),
        (NumberValue("123.40"), "number"),
        (MeasureValue("5", "meter"), "measure"),
        (RelativeDateValue(-1, "day", "past"), "relative_date"),
        (AbbreviationValue("Dr.", "Doctor", "title", None, None, "suppress"), "abbreviation"),
    ],
)
def test_value_kinds_are_first_and_json_native(value, kind):
    serialized = _to_json(value)
    assert next(iter(serialized)) == "kind"
    assert serialized["kind"] == kind
    json.dumps(serialized)


def test_datetime_fields_and_decimal_schema_are_stable():
    assert _to_json(DateTimeValue((("y", 2025), ("M", 8)), "gregorian"))["fields"] == [
        ["y", 2025],
        ["M", 8],
    ]
    number = _to_json(NumberValue("001.230", None))
    assert number["decimal"] == "001.230"
    assert "currency" in number
    assert number["currency"] is None


@pytest.mark.parametrize(
    ("spec", "kind"),
    [
        (DateFormatSpec("en_US", "yMd", "M/d/y", "gregorian"), "date_format_spec"),
        (DateIntervalSpec("en_US", "yMd"), "date_interval_spec"),
        (NumberFormatSpec("en_US", "decimal"), "number_format_spec"),
        (CompactFormatSpec("en_US", "short"), "compact_format_spec"),
        (SpelloutFormatSpec("en_US", "spellout-numbering"), "spellout_format_spec"),
        (MeasureFormatSpec("en_US", "meter", "short"), "measure_format_spec"),
        (RelativeDateSpec("en_US"), "relative_date_spec"),
        (AbbreviationSpec("en_US", "en"), "abbreviation_spec"),
    ],
)
def test_all_specs_have_stable_kinds(spec, kind):
    assert _to_json(spec)["kind"] == kind


def test_number_spec_retains_its_format_kind():
    assert _to_json(NumberFormatSpec("en_US", "decimal"))["format_kind"] == "decimal"


def test_detection_shape_and_non_ascii_json():
    detection = ValueDetection(
        text="5 km café",
        start=0,
        end=4,
        type="measure:meter",
        value=MeasureValue("5", "meter"),
        captures=(Capture("number", 0, 1, "5", 5, "numeric"),),
        spec=MeasureFormatSpec("fr_FR", "meter", "short"),
    )
    serialized = detection_to_dict(detection)
    assert list(serialized) == ["text", "start", "end", "type", "value", "captures", "spec"]
    assert next(iter(serialized["captures"][0])) == "kind"
    assert detections_to_json([detection]) == [serialized]
    assert "café" in json.dumps(serialized, ensure_ascii=False)
