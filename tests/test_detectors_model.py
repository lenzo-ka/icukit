"""L1: the detector value model -- immutable records, protocol, refusal."""

import pytest

from icukit.detectors import (
    Capture,
    DateFormatSpec,
    DateTimeValue,
    Detector,
    DetectorRefusal,
    NumberFormatSpec,
    NumberValue,
)


def test_value_records_are_frozen_and_value_equal():
    a = DateTimeValue(fields=(("y", 2569), ("M", 1), ("d", 3)), calendar="buddhist")
    b = DateTimeValue(fields=(("y", 2569), ("M", 1), ("d", 3)), calendar="buddhist")

    assert a == b
    with pytest.raises(AttributeError):
        a.calendar = "gregorian"  # type: ignore[misc]


def test_number_value_is_a_decimal_string_not_a_float():
    v = NumberValue(decimal="0.07")

    assert isinstance(v.decimal, str)
    assert v.currency is None
    assert NumberValue(decimal="1234.56", currency="EUR").currency == "EUR"


def test_capture_carries_string_value_and_form():
    cap = Capture(name="weekday", start=5, end=8, text="Wed", value="wednesday", form="short")

    assert (cap.text, cap.value, cap.form) == ("Wed", "wednesday", "short")
    with pytest.raises(AttributeError):
        cap.value = "thursday"  # type: ignore[misc]


def test_specs_require_observed_calendar_and_carry_grouping():
    date_spec = DateFormatSpec(
        locale="th_TH", skeleton="yMMMd", pattern="d MMM y", calendar="buddhist"
    )
    num_spec = NumberFormatSpec(locale="hi_IN", kind="decimal", grouping_sizes=(2, 3))

    assert date_spec.calendar == "buddhist"
    assert num_spec.grouping_sizes == (2, 3)
    # calendar is observed from the formatter, never defaulted -- omitting it is an error,
    # not a silent "gregorian" that would misprint every th/fa surface (fugu #4).
    with pytest.raises(TypeError):
        DateFormatSpec(locale="en_US", skeleton="yMd", pattern="M/d/y")


def test_detector_refusal_carries_stable_reason():
    err = DetectorRefusal(
        type="date:yMd",
        start=4,
        endpoint=2,
        reason="reversed-endpoint",
        message="ended before start",
    )

    assert err.reason == "reversed-endpoint"
    assert err.type == "date:yMd"
    assert err.start == 4 and err.endpoint == 2
    assert "reversed-endpoint" in str(err)


def test_detector_protocol_is_runtime_checkable():
    class Stub:
        type = "date:yMd"
        group = "date"

        def detect(self, text):
            return []

    assert isinstance(Stub(), Detector)
    assert not isinstance(object(), Detector)
