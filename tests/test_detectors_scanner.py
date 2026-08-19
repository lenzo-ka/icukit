"""L2/L3: the windowed scanner and the detect()/DetectorSet orchestration.

The scanner is exercised through a stub _Inverter with controllable parse behavior --
which is also fugu's fake-parser seam for the refusal paths that conforming ICU will
not naturally produce.
"""

import pytest

from icukit._offsets import boundary_maps
from icukit.detectors import (
    Capture,
    DateFormatSpec,
    DateTimeValue,
    DetectorRefusal,
    DetectorSet,
    NumberFormatSpec,
    NumberValue,
    ValueDetection,
    _Inverter,
    _scan,
    _value_key,
    detect,
)


def _stub(text, token="12", *, reform=None, end_u16_of=None):
    """An _Inverter that matches a literal token by code point, with overridable endpoint.

    Works in code-point space (converting the incoming UTF-16 offset) so it is correct
    across astral and combining input, then returns a UTF-16 endpoint like a real parser.
    """
    cp_to_u16, u16_to_cp = boundary_maps(text)

    def parse(us, start_u16):
        start_cp = u16_to_cp.get(start_u16)
        if start_cp is None:
            return None
        if text[start_cp : start_cp + len(token)] == token:
            end = end_u16_of(start_u16) if end_u16_of else cp_to_u16[start_cp + len(token)]
            return (end, token)
        return None

    def reformat(parsed):
        return reform if reform is not None else parsed

    def build(parsed, surface, start_cp, cp_to_u16, u16_to_cp):
        cap = Capture("integer", start_cp, start_cp + len(surface), surface, form="numeric")
        return (NumberValue(decimal=surface), (cap,), NumberFormatSpec("und", "decimal"))

    return _Inverter(parse, reformat, build)


def test_scan_matches_and_carries_structure():
    text = "n=12 m=12"
    out = _scan(text, "en_US", "number:decimal", _stub(text))

    assert [(d["text"], d["start"], d["end"]) for d in out] == [("12", 2, 4), ("12", 7, 9)]
    assert out[0]["captures"][0].name == "integer"
    assert out[0]["value"] == NumberValue(decimal="12")


def test_parse_miss_is_silent():
    text = "no digits here"
    assert _scan(text, "en_US", "number:decimal", _stub(text)) == []


def test_reformat_mismatch_is_rejected_not_fatal():
    text = "12"
    # stub reformats to "XX" != surface "12" -> permissive coercion, dropped silently.
    assert _scan(text, "en_US", "number:decimal", _stub(text, reform="XX")) == []


def test_build_emitting_a_float_is_rejected():
    text = "12"

    def build_with_float(parsed, surface, start_cp, cp_to_u16, u16_to_cp):
        # A mis-built detector that smuggles a binary float into the spec record.
        spec = NumberFormatSpec("und", "decimal", min_fraction=0.5)
        return (NumberValue(decimal=surface), (), spec)

    inv = _stub(text)
    inv = _Inverter(inv.parse, inv.reformat, build_with_float)
    with pytest.raises(ValueError, match="float"):
        _scan(text, "en_US", "number:decimal", inv)


def test_greedy_resume_no_self_overlap():
    text = "1212"  # token "12" at cp0 and cp2; greedy resume at end means both, non-overlapping
    out = _scan(text, "en_US", "number:decimal", _stub(text))
    assert [(d["start"], d["end"]) for d in out] == [(0, 2), (2, 4)]


def test_reversed_endpoint_refuses():
    text = "12"
    inv = _stub(text, end_u16_of=lambda s: s - 1)
    with pytest.raises(DetectorRefusal) as caught:
        _scan(text, "en_US", "number:decimal", inv)
    assert caught.value.reason == "reversed-endpoint"


def test_out_of_range_endpoint_refuses():
    text = "12"  # utf-16 length 2; an endpoint past it is not a surrogate interior (fugu #8)
    inv = _stub(text, end_u16_of=lambda s: 999)
    with pytest.raises(DetectorRefusal) as caught:
        _scan(text, "en_US", "number:decimal", inv)
    assert caught.value.reason == "out-of-range-endpoint"


def test_surrogate_interior_endpoint_refuses():
    text = "\U0001f600b"  # emoji (cp0, utf16 [0,2)) then b
    # match at start 0, but claim endpoint utf16=1 -> interior to the surrogate pair
    inv = _stub(text, token=text[0], end_u16_of=lambda s: 1)
    with pytest.raises(DetectorRefusal) as caught:
        _scan(text, "en_US", "number:decimal", inv)
    assert caught.value.reason == "surrogate-interior-endpoint"


def test_mid_grapheme_endpoint_refuses():
    text = "e\u0301x"  # e + combining acute = one grapheme [0,2); x at cp2
    # match at start 0, claim endpoint cp/utf16 = 1 -> interior to the grapheme cluster
    inv = _stub(text, token="e", end_u16_of=lambda s: 1)
    with pytest.raises(DetectorRefusal) as caught:
        _scan(text, "en_US", "number:decimal", inv)
    assert caught.value.reason == "mid-grapheme-endpoint"


def test_astral_prefix_does_not_shift_offsets():
    text = "\U0001f600 12"  # emoji (cp0), space (cp1), then "12" at cp2..4
    # The stub indexes the real Python string by code point; the scanner converts the
    # UTF-16 endpoint back, so the emoji's two UTF-16 units must not shift the extent.
    out = _scan(text, "en_US", "number:decimal", _stub(text, token="12"))
    assert [(d["text"], d["start"], d["end"]) for d in out] == [("12", 2, 4)]


# ---- orchestration (L2) ----


class _FixedDetector:
    def __init__(self, type_, dets):
        self.type = type_
        self.group = type_.split(":")[0]
        self._dets = dets

    def detect(self, text):
        return list(self._dets)


def _vd(start, end, type_, dec):
    return ValueDetection(
        text="x" * (end - start),
        start=start,
        end=end,
        type=type_,
        value=NumberValue(decimal=dec),
        captures=(),
        spec=NumberFormatSpec("und", "decimal"),
    )


def test_detect_merges_in_deterministic_order_regardless_of_input_order():
    a = _FixedDetector("number:decimal", [_vd(5, 7, "number:decimal", "5")])
    b = _FixedDetector("date:yMd", [_vd(0, 4, "date:yMd", "0"), _vd(5, 9, "date:yMd", "9")])

    one = detect("irrelevant", [a, b])
    two = detect("irrelevant", [b, a])

    order = [(d["start"], d["end"], d["type"]) for d in one]
    assert order == [(0, 4, "date:yMd"), (5, 9, "date:yMd"), (5, 7, "number:decimal")]
    assert order == [(d["start"], d["end"], d["type"]) for d in two]


def test_detector_set_is_immutable_gang_equals_individual_merge():
    a = _FixedDetector("number:decimal", [_vd(5, 7, "number:decimal", "5")])
    b = _FixedDetector("date:yMd", [_vd(0, 4, "date:yMd", "0")])
    gang = DetectorSet((a, b))

    assert gang.detect("t") == detect("t", [a, b])
    assert gang.names() == ("number:decimal", "date:yMd")
    assert gang.without("number:decimal").names() == ("date:yMd",)
    c = _FixedDetector("number:percent", [])
    assert gang.with_(c).names() == ("number:decimal", "date:yMd", "number:percent")


def _vdate(start, end, fields):
    return ValueDetection(
        text="x" * (end - start),
        start=start,
        end=end,
        type="date:yMd",
        value=DateTimeValue(fields=fields, calendar="buddhist"),
        captures=(),
        spec=DateFormatSpec("th_TH", "yMd", "d/M/y", calendar="buddhist"),
    )


def test_value_key_discriminates_distinct_dates():
    # The sort tiebreaker keys on the value; distinct civil dates must key distinctly, or
    # same-span/type detections order by detector input rather than deterministically (fugu #3).
    a = DateTimeValue(fields=(("y", 2569), ("M", 1), ("d", 3)), calendar="buddhist")
    b = DateTimeValue(fields=(("y", 2569), ("M", 1), ("d", 4)), calendar="buddhist")
    assert _value_key(a) != _value_key(b)


def test_same_span_distinct_dates_sort_deterministically():
    d3 = _vdate(0, 4, (("y", 2569), ("M", 1), ("d", 3)))
    d4 = _vdate(0, 4, (("y", 2569), ("M", 1), ("d", 4)))
    # Same start/end/type: only the value key breaks the tie, so input order must not matter.
    one = [d["value"].fields for d in detect("t", [_FixedDetector("date:yMd", [d3, d4])])]
    two = [d["value"].fields for d in detect("t", [_FixedDetector("date:yMd", [d4, d3])])]
    assert one == two
