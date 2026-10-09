import random
import re

import pytest

from icukit import DetectionBatch, Extent, number_detectors
from icukit.detectors import DetectorRefusal, DetectorSet, NumberDetector
from icukit.engine import flexible_detectors, generated_detectors, reader_set
from icukit.stream import (
    DetectionStream,
    _calendar_closing_surfaces,
    _extent_for_reader,
    _joinable,
    _seams,
    _shift_detection,
    extent_report,
)

_STREAM_FIXTURES = (
    ("en_US", "I paid 1,234 and 56 more."),
    ("en_US", "123456789 – 123456790 – 123456791 x"),
    ("en_US", "1 – 2 – 3 – 4 x"),
    ("en_US", "14-3-3 and 7 – 3–5 y"),
    ("en_US", "10 - 20 - 30 kg"),
    ("en_US", "a 1/2/2024 – 3/4/2024 b"),
    ("en_US", "pay 5 - 10 - 15 + 3 = 33 now"),
    ("en_US", "9:00–10:00 – 11:00 x"),
    ("en_US", "x5   May 2024 ok"),
    ("en_US", "1.   2 ok"),
    ("fr_FR", "a1 2,5E3 b"),
    ("fr_FR", "de 1 à 2 – 3 – 4 x"),
    ("fr_FR", "1\u202f234 x"),
    ("de_DE", "1.234,5 und 67"),
    ("ja_JP", "2024年5月3日 12時30分"),
    ("zh_CN", "2024年5月3日 12时30分"),
    ("th_TH", "12 34 56"),
    ("ar_EG", "١٢٣ و٤٥٦"),
    ("en_US", "$12.50 and 7%"),
    ("en_US", "five hundred and 12"),
    ("en_US", "about 3.5 kg"),
    ("en_US", "May 5, 2024 at 2 PM"),
    ("en_US", "Monday, June 3"),
    ("en_US", "1/2 plus 3/4"),
    ("en_US", "1st 2nd 3rd"),
    ("en_US", "1e3 and 2E-4"),
    ("en_US", "3–5 and 8–13"),
    ("en_US", "0:30 and 23:59"),
    ("en_US", "Jan. 5 and Feb. 6"),
    ("en_US", "A1 B2 C3"),
    ("en_US", "-5 + 7 = 2"),
    ("en_US", "1,000,000.25"),
    ("fr_FR", "12,5 € et 3 kg"),
    ("de_DE", "5. Mai 2024"),
    ("ja_JP", "１２３円と４５円"),
    ("zh_CN", "一百二十三和45"),
    ("th_TH", "วันที่ 5 พฤษภาคม 2024"),
    ("ar_EG", "٥ مايو ٢٠٢٤"),
    ("en_US", "nothing detected here"),
    ("en_US", "42"),
    ("ks_Arab_IN", "\u200e-\u200e۱٫۵×۱۰^\u200e-\u200e۹"),
    ("lrc_IR", "۱٫۲×۱۰^\u200e-\u200e۴"),
    ("mzn_IR", "۶٫۰۲×۱۰^۲۳"),
)

_LEFT_MIXED_FIXTURES = tuple(
    fixture for index, fixture in enumerate(_STREAM_FIXTURES) if index not in {21, 22, 28}
) + (
    ("en_US", "The total was 99 dollars."),
    ("fr_FR", "prix 7,25 euros"),
    ("de_DE", "um 14:30 Uhr"),
)


def _run(detectors, text, chunks, stride=32, **options):
    stream = detectors.stream(detect_stride_chars=stride, **options)
    found = []
    batches = []
    cursor = 0
    for size in chunks:
        batch = stream.feed(text[cursor : cursor + size])
        found.extend(batch.detections)
        batches.append(batch)
        cursor += size
    batch = stream.close()
    found.extend(batch.detections)
    batches.append(batch)
    return found, batches


def test_number_literal():
    stream = number_detectors("en_US").stream(detect_stride_chars=1)
    assert stream.feed("I paid 1,2") == DetectionBatch((), 2)
    batch = stream.feed("34 and 56 ")
    assert [(d["text"], d["start"], d["end"]) for d in batch.detections] == [("1,234", 7, 12)]
    assert batch.pending_from == 13
    # The non-joinable "more." chunk closes the bounded number extent once the
    # two-code-point peek is present.
    third = stream.feed("more.")
    assert [d["text"] for d in third.detections] == ["56"]
    assert third.pending_from == 20
    closing = stream.close()
    assert closing.detections == ()
    assert closing.pending_from == 25


def test_report_interval_waits_for_composite_competitor():
    text = "2024-03-05 2:07\u202fnm. New York-tyd\u2009–\u20092024-03-07 2:07\u202fnm. New York-tyd"
    detectors = generated_detectors("af_ZA").compile(warm=False)
    expected = detectors.detect(text)
    assert any(item["type"] == "date-interval:hmv" for item in expected)

    for chunks in ([text], re.findall(r"\S+|\s+", text), list(text)):
        found, _batches = _run(detectors, text, [len(chunk) for chunk in chunks], stride=1)
        assert found == expected


def test_report_stream_whole_keeps_left_sensitive_month():
    text = "\u200f2024 Oshù Ɛrɛ̀nà 5\u2009–\u20092025 Oshù Ìgbé 9"
    detectors = generated_detectors("yo_NG").with_(
        *flexible_detectors("yo_NG", guarded=True).detectors
    )
    expected = detectors.detect(text)
    found, _batches = _run(detectors, text, [len(text)])
    assert found == expected
    months = [(item["start"], item["end"]) for item in found if item["type"] == "date:month-name"]
    assert months == [
        (6, 17),
        (27, 36),
    ]


def test_report_default_cap_chunking_is_invariant_without_cuts():
    text = "x 25 Desember 2024 om 9:30:00\u202fvm. GMT-5 y."
    detectors = reader_set("af_ZA", flexible=True).compile(warm=False)
    whole = _cap_invariance_run(detectors, text, [len(text)], None)
    cp1 = _cap_invariance_run(detectors, text, [1] * len(text), None)
    assert whole == cp1
    assert whole[1:3] == ([], [])


def test_report_codepoint_stream_keeps_signed_grouped_number():
    text = "-1,234.56"
    detectors = number_detectors("yo_NG").compile(warm=False)
    found, _batches = _run(detectors, text, [1] * len(text), stride=1)
    assert found == detectors.detect(text)


@pytest.mark.parametrize(
    ("locale", "text", "chunks"),
    [
        (
            "tg_TJ",
            "\u041c\u0430\u0440\u0442\u0438 2024 \u2013 \u0410\u043f\u0440\u0435\u043b\u0438 2025",
            "tokens",
        ),
        ("ja_JP", "1 \u30ae\u30ac\u30d3\u30c3\u30c8", "codepoints"),
        ("ja_JP", "1 \u30b0\u30e9\u30e0", "codepoints"),
        ("si_LK", "\u0daf\u0dc4\u0dc3 1.2", "codepoints"),
        (
            "shn_MM",
            "00:05:00 \u1076\u1062\u101d\u103a\u1038\u101a\u1062\u1019\u103a\u1038 "
            "\u1075\u1062\u1004\u103a\u101d\u107c\u103a\u1038 "
            "\u107a\u103d\u1010\u103a\u1038\u1022\u103d\u1075\u103a\u1087",
            "codepoints",
        ),
    ],
)
def test_report_prefix_segmentation_does_not_settle_early(locale, text, chunks):
    detectors = reader_set(locale, flexible=True).compile(warm=False)
    pieces = re.findall(r"\S+|\s+", text) if chunks == "tokens" else list(text)
    found, _batches = _run(detectors, text, [len(piece) for piece in pieces], stride=1)
    assert found == detectors.detect(text)


def test_window_refusal_offsets_are_absolute():
    text = "NaN/4/2020\u0301"
    detectors = number_detectors("en_US").compile(warm=False)
    with pytest.raises(DetectorRefusal) as whole:
        detectors.detect(text)
    with pytest.raises(DetectorRefusal) as streamed:
        _run(detectors, text, [1] * len(text), stride=1)
    assert streamed.value.args == whole.value.args


def test_stream_retries_si_date_refusal_at_nonfinal_feed_boundary():
    # Reduced from fix4's accepted 9,780-character si_LK document at feed size 1024.
    # The first feed ends inside the grapheme consumed by date:GyMMMEd; that incomplete
    # prefix can refuse, but it is not the end of the stream input.
    text = (
        "x" * 963
        + "2024 මැදින් 5, අඟහරුවාදා දින ග්\u200dරිමවේ-5 14.07\n"
        + "2024 ඉල් 7, බ්\u200dරහස්පතින්දා දින ග්\u200dරිමවේ-5 22.59"
    )
    detectors = reader_set("si_LK")
    expected = detectors.detect(text)
    found, _batches = _run(
        detectors,
        text,
        [1024, len(text) - 1024],
        max_pending_chars=1_000_000,
        reader_cap_chars={detector.type: 1_000_000 for detector in detectors.detectors},
    )
    assert found == expected


def test_prefix_refusal_cannot_bypass_cap_threshold():
    class RefusingDetector:
        type = group = "demo:refusing"

        def extent(self):
            return Extent(None, frozenset({"a"}), cap_chars=4, source="test a+ reader")

        def detect(self, text):
            if not text.endswith("!"):
                raise DetectorRefusal(
                    self.type,
                    0,
                    len(text),
                    "mid-grapheme-endpoint",
                    "test refusal",
                )
            return []

    stream = DetectionStream(
        (RefusingDetector(),),
        max_pending_chars=4,
        reader_cap_chars={"demo:refusing": 4},
        detect_stride_chars=1,
    )
    for character in "aaaa":
        batch = stream.feed(character)
        assert batch.cuts == ()
        assert batch.reader_cuts == ()
    with pytest.raises(DetectorRefusal, match="test refusal"):
        stream.feed("a")
    assert stream.pending()["total"] - stream.pending()["buffered_from"] == 5


def test_calendar_closing_vocabulary_uses_all_day_period_resource_forms():
    from icukit._gate import _day_period_resource_strings

    for locale in ("en_US", "de_DE", "fr_FR", "es_MX", "ja_JP", "zh_CN"):
        reader = next(
            detector
            for detector in reader_set(locale, flexible=True).detectors
            if type(detector).__name__ == "FlexibleTimeDetector"
        )
        surfaces = frozenset(_calendar_closing_surfaces(reader))
        assert frozenset(_day_period_resource_strings(locale)) <= surfaces

    en_reader = next(
        detector
        for detector in reader_set("en_US", flexible=True).detectors
        if type(detector).__name__ == "FlexibleTimeDetector"
    )
    assert {"midnight", "noon"} <= frozenset(_calendar_closing_surfaces(en_reader))


def test_special_day_period_stream_matches_whole_detection():
    text = "12:00 noon x"
    detectors = reader_set("en_US", flexible=True).compile(warm=False)
    found, _batches = _run(detectors, text, [1] * len(text), stride=1)
    assert any(item["text"] == "12:00 noon" for item in found)
    assert found == detectors.detect(text)


def test_relative_number_group_count_is_not_sample_bounded():
    detectors = reader_set("bas_CM", flexible=True, guarded=True)
    relative_extent = next(
        row.extent
        for row in extent_report(detectors)
        if row.reader == "FlexibleRelativeDateDetector"
    )
    assert relative_extent.chunks is None
    for groups in range(1, 6):
        text = "-" + "\N{NO-BREAK SPACE}".join(("1", *(("234",) * groups))) + " w"
        expected = detectors.detect(text)
        assert any(item["type"] == "date:relative" for item in expected)
        found, _batches = _run(detectors, text, [1] * len(text), stride=1)
        assert found == expected


def test_interval_extent_does_not_pair_sampled_longest_surfaces():
    class FlexibleDateIntervalDetector:
        group = "date-interval:synthetic"

        def __init__(self):
            self.type = "date-interval:synthetic"
            self.locale = "en_US"
            self._matchers = ()
            self._left_surfaces = ("a b", "abcdefghij")
            self._right_surfaces = ("c d", "klmnopqrst")

        def extent(self):
            return _extent_for_reader(self)

        def detect(self, text):
            found = []
            for left in self._left_surfaces:
                for right in self._right_surfaces:
                    surface = f"{left}–{right}"
                    start = text.find(surface)
                    if start >= 0:
                        found.append(
                            {
                                "text": surface,
                                "start": start,
                                "end": start + len(surface),
                                "type": self.type,
                                "value": surface,
                                "captures": (),
                                "spec": None,
                            }
                        )
            return sorted(found, key=lambda item: (item["start"], item["end"]))

    detector = FlexibleDateIntervalDetector()
    assert detector.extent().chunks is None
    detectors = DetectorSet((detector,))
    for left in detector._left_surfaces:
        for right in detector._right_surfaces:
            text = f"{left}–{right} x"
            found, _batches = _run(detectors, text, [1] * len(text), stride=1)
            assert found == detectors.detect(text)


def test_number_extent_reads_whitespace_exponent_symbol_itself():
    exponent = "\N{NO-BREAK SPACE}×10^"

    class Symbols:
        def getSymbol(self, _symbol):
            return exponent

    class Formatter:
        def getDecimalFormatSymbols(self):
            return Symbols()

    class NumberDetector:
        type = group = "number:synthetic"
        locale = "en_US"
        _nf = Formatter()
        _decimal = "."
        _grouping = ","
        _zero = "0"
        _minus = "-"
        _plus = "+"
        _currency_symbol = "$"
        _percent = "%"

        def extent(self):
            return _extent_for_reader(self)

        def detect(self, text):
            surface = f"1{exponent}2"
            start = text.find(surface)
            if start < 0:
                return []
            return [
                {
                    "text": surface,
                    "start": start,
                    "end": start + len(surface),
                    "type": self.type,
                    "value": surface,
                    "captures": (),
                    "spec": None,
                }
            ]

    detector = NumberDetector()
    assert detector.extent().chunks is None
    text = f"1{exponent}2 x"
    found, _batches = _run(DetectorSet((detector,)), text, [1] * len(text), stride=1)
    assert found == detector.detect(text)


@pytest.mark.parametrize("stride", [1, 32])
@pytest.mark.parametrize(("locale", "text"), _STREAM_FIXTURES)
def test_stream_every_split_point(locale, text, stride):
    detectors = reader_set(locale, flexible=True, guarded=True).compile(warm=False)
    expected = detectors.detect(text)
    for split in range(len(text) + 1):
        found, _ = _run(detectors, text, (split, len(text) - split), stride)
        assert found == expected


def test_stream_random_chunkings():
    rng = random.Random(20261004)
    compiled = {}
    for locale, text in _STREAM_FIXTURES:
        detectors = compiled.setdefault(locale, number_detectors(locale).compile(warm=False))
        expected = detectors.detect(text)
        for _ in range(200):
            chunks = []
            remaining = len(text)
            while remaining:
                size = rng.randint(1, min(8, remaining))
                chunks.append(size)
                remaining -= size
            found, _ = _run(detectors, text, chunks)
            assert found == expected
        found, _ = _run(detectors, text, [1] * len(text))
        assert found == expected


def _declared_left(text, seam, detectors):
    extent = Extent(0)
    for row in extent_report(detectors):
        extent = extent.union(row.extent)
    seams = _seams(text)
    edges = (0, *seams, len(text))
    cursor = max(index for index, edge in enumerate(edges) if edge <= seam)
    crossed = 0
    while cursor > 0 and (extent.left_chunks is None or crossed < extent.left_chunks):
        if not _joinable(
            text[edges[cursor - 1] : edges[cursor]],
            extent.left_joins,
            extent.left_join_chars,
        ):
            break
        cursor -= 1
        crossed += 1
    start = edges[cursor]
    index = start - 1
    while index >= 0 and text[index].isspace():
        index -= 1
    return max(0, index - 1)


@pytest.mark.parametrize(
    ("locale", "text"),
    (
        ("en_US", "123456789 – 123456790 – 123456791 x"),
        ("en_US", "1 – 2 – 3 – 4 x"),
        ("en_US", "14-3-3 and 7 – 3–5 y"),
        ("en_US", "10 - 20 - 30 kg"),
        ("en_US", "a 1/2/2024 – 3/4/2024 b"),
        ("en_US", "pay 5 - 10 - 15 + 3 = 33 now"),
        ("en_US", "9:00–10:00 – 11:00 x"),
        ("en_US", "x5   May 2024 ok"),
        ("en_US", "1.   2 ok"),
        ("fr_FR", "a1 2,5E3 b"),
        ("fr_FR", "de 1 à 2 – 3 – 4 x"),
    )
    + _LEFT_MIXED_FIXTURES,
)
def test_left_context_rule_identity(locale, text):
    detectors = reader_set(locale, flexible=True, guarded=True)
    whole = detectors.detect(text)
    for seam in _seams(text):
        start = _declared_left(text, seam, detectors)
        window = [_shift_detection(item, start) for item in detectors.detect(text[start:])]
        assert [item for item in whole if item["start"] >= seam] == [
            item for item in window if item["start"] >= seam
        ]


def test_left_rule_without_walk_is_insufficient():
    fixtures = (
        "123456789 – 123456790 – 123456791 x",
        "1 – 2 – 3 – 4 x",
    )
    detectors = reader_set("en_US", flexible=True, guarded=True)
    for text in fixtures:
        whole = detectors.detect(text)
        witnesses = []
        for seam in _seams(text):
            index = seam - 1
            while index >= 0 and text[index].isspace():
                index -= 1
            start = max(0, index - 1)
            window = [_shift_detection(item, start) for item in detectors.detect(text[start:])]
            if [item for item in whole if item["start"] >= seam] != [
                item for item in window if item["start"] >= seam
            ]:
                witnesses.append(seam)
        assert witnesses

    p7_fixtures = (
        ("fr_FR", "a1 2,5E3 b"),
        ("en_US", "x5   May 2024 ok"),
    )
    for locale, text in p7_fixtures:
        detectors = reader_set(locale, flexible=True, guarded=True)
        whole = detectors.detect(text)
        assert any(
            [item for item in whole if item["start"] >= seam]
            != [
                item
                for item in (
                    _shift_detection(found, seam - 1)
                    for found in detectors.detect(text[seam - 1 :])
                )
                if item["start"] >= seam
            ]
            for seam in _seams(text)
            if seam
        )


def test_seam_prefix_stability():
    texts = (
        "alpha\r\nbeta e\u0301 👩\u200d💻 🇺🇸 1\u00a0234 end",
        "ภาษาไทย 日本語 中文",
        "1\u202f234,50 € puis fin",
    )
    for text in texts:
        complete = _seams(text)
        for end in range(1, len(text) + 1):
            prefix = _seams(text[:end])
            if prefix:
                last = prefix[-1]
                assert tuple(value for value in complete if value <= last) == tuple(
                    value for value in prefix if value <= last
                )


def test_stride_latency_bound():
    stream = reader_set("en_US", flexible=True).stream(detect_stride_chars=32)
    assert stream.feed("42  xy").detections == ()
    assert any(d["text"] == "42" for d in stream.feed("z" * 1000).detections)

    stream = number_detectors("en_US").stream(detect_stride_chars=32)
    seen_at = None
    # NumberDetector's grammar-derived closing rule rejects the first word chunk, so
    # "42" is decided by T[:7] = "42 x x" (closing seam 5 plus the two-code-point peek).
    text = "42 " + "x " * 48
    for total, character in enumerate(text, 1):
        if any(d["text"] == "42" for d in stream.feed(character).detections):
            seen_at = total
            break
    assert seen_at is not None
    assert seen_at <= 7 + 32


class EmptyDetector:
    type = group = "empty"

    def detect(self, text):
        return []

    def extent(self):
        return Extent(1, source="test one-chunk detector")


def test_cap_multiple_cuts_one_feed():
    batch = DetectionStream((EmptyDetector(),)).feed("x" * 20_000)
    assert len(batch.cuts) >= 4
    assert all(b <= a + 4096 for a, b in zip((0, *batch.cuts), batch.cuts, strict=False))


def test_cap_literal_and_chunk_invariant():
    text = "1,234,567,890"
    expected = [("1,234,567", 0, 9, True), ("890", 10, 13, None)]
    for split in range(len(text) + 1):
        found, batches = _run(
            number_detectors("en_US"),
            text,
            (split, len(text) - split),
            stride=1,
            max_pending_chars=10,
        )
        assert [(d["text"], d["start"], d["end"], d.get("truncated")) for d in found] == expected
        assert tuple(cut for batch in batches for cut in batch.cuts) == (10,)


def test_cap_long_grapheme_codepoint_cut():
    stream = DetectionStream((EmptyDetector(),), detect_stride_chars=1)
    assert stream.feed("a" + "\u0301" * 4096).cuts == (4096,)


def test_cap_without_prefix_reading():
    class ClosingOnlyDetector:
        type = group = "demo:closing"

        def detect(self, text):
            if text.startswith("#") and text.endswith("!"):
                return [
                    {
                        "text": text,
                        "start": 0,
                        "end": len(text),
                        "type": self.type,
                        "value": text,
                        "captures": (),
                        "spec": None,
                    }
                ]
            return []

        def extent(self):
            return Extent(None, frozenset({"a"}), cap_chars=8, source="test #a+! reader")

    stream = DetectionStream((ClosingOnlyDetector(),), max_pending_chars=8)
    batch = stream.feed("#" + "a" * 20 + "!")
    assert batch.cuts
    assert batch.detections == ()


def test_reader_cap():
    stream = reader_set("en_US", flexible=True).stream(
        reader_cap_chars={"number:decimal": 8}, detect_stride_chars=1
    )
    first = stream.feed("1" * 20 + " x")
    decimal = [d for d in first.detections if d["type"] == "number:decimal"]
    assert [(d["start"], d["end"], d.get("truncated")) for d in decimal] == [
        (0, 8, True),
        (8, 16, True),
    ]
    assert first.reader_cuts == (("number:decimal", 8), ("number:decimal", 16))
    final = [d for d in stream.close().detections if d["type"] == "number:decimal"]
    assert [(d["start"], d["end"], d.get("truncated")) for d in final] == [(16, 20, None)]
    whole = [
        d
        for d in reader_set("en_US", flexible=True).detect("1" * 20 + " x")
        if d["type"] == "number:decimal"
    ]
    assert [(d["start"], d["end"]) for d in whole] == [(0, 20)]


def test_reader_cap_literal_chunk_invariant():
    text = "1" * 20 + " x"
    detectors = reader_set("en_US", flexible=True).compile(warm=False)
    expected = None
    for chunks in ([len(text)], [1] * len(text), [5, 5, 5, 5, 2]):
        found, batches = _run(
            detectors,
            text,
            chunks,
            stride=1,
            reader_cap_chars={"number:decimal": 8},
        )
        result = (
            [
                (d["start"], d["end"], d.get("truncated"))
                for d in found
                if d["type"] == "number:decimal"
            ],
            [cut for batch in batches for cut in batch.reader_cuts],
        )
        if expected is None:
            expected = result
        assert result == expected
    assert expected == (
        [(0, 8, True), (8, 16, True), (16, 20, None)],
        [("number:decimal", 8), ("number:decimal", 16)],
    )


def test_left_walk_cut_literal_chunk_invariant():
    text = "1 " * 12 + "x 9"
    detector = NumberDetector("en_US", "decimal")
    expected = None
    for chunks in ([len(text)], [1] * len(text), [3] * 9):
        stream = DetectionStream((detector,), max_pending_chars=8, detect_stride_chars=1)
        found = []
        cuts = []
        cursor = 0
        for size in chunks:
            batch = stream.feed(text[cursor : cursor + size])
            cursor += size
            found.extend(batch.detections)
            cuts.extend(batch.cuts)
        found.extend(stream.close().detections)
        result = (found, cuts)
        if expected is None:
            expected = result
        assert result == expected
    assert expected is not None
    assert expected[1] == [8, 16, 24]


class _CutTrackingStream(DetectionStream):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cut_pending_from = []

    def _stream_cut_at(self, end, *, start, decided_through):
        detections, cut = super()._stream_cut_at(end, start=start, decided_through=decided_through)
        assert start < cut <= start + self._max_pending
        self.cut_pending_from.append(self._pending_from)
        return detections, cut


def _cap_invariance_run(detectors, text, chunks, cap):
    options = {}
    if cap is not None:
        options["max_pending_chars"] = cap
        options["reader_cap_chars"] = {
            row.type: cap for row in extent_report(detectors) if row.extent.chunks is None
        }
    stream = _CutTrackingStream(detectors, detect_stride_chars=32, **options)
    detections = []
    cuts = []
    reader_cuts = []
    cursor = 0
    for size in chunks:
        batch = stream.feed(text[cursor : cursor + size])
        cursor += size
        detections.extend(batch.detections)
        cuts.extend(batch.cuts)
        reader_cuts.extend(batch.reader_cuts)
    batch = stream.close()
    detections.extend(batch.detections)
    cuts.extend(batch.cuts)
    reader_cuts.extend(batch.reader_cuts)
    pending_positions = [*stream.cut_pending_from, batch.pending_from]
    return detections, cuts, reader_cuts, pending_positions


def _random_chunks(length, randomizer):
    chunks = []
    while length:
        size = randomizer.randint(1, min(64, length))
        chunks.append(size)
        length -= size
    return chunks


def test_cap_decisions_are_chunk_invariant_property():
    gangs = {
        locale: reader_set(locale, flexible=True, guarded=True).compile(warm=False)
        for locale in ("en_US", "fr_FR", "ja_JP")
    }
    numbers = number_detectors("en_US").compile(warm=False)
    cases = (
        (gangs["en_US"], "1" * 20 + " x", 8),
        (gangs["fr_FR"], "un " * 12 + "x", 16),
        (gangs["ja_JP"], "1 " * 40 + "x", 64),
        (numbers, "1 - " * 20 + "x", 8),
        (numbers, "one " * 20 + "x", 16),
        (numbers, "1" * 80 + " x", 64),
        (numbers, "x" * 5000, None),
        (gangs["en_US"], "a" + "\u0301" * 5000, None),
    )
    expected = []
    for detectors, text, cap in cases:
        cp1 = _cap_invariance_run(detectors, text, [1] * len(text), cap)
        assert _cap_invariance_run(detectors, text, [len(text)], cap) == cp1
        expected.append(cp1)

    randomizer = random.Random(20261005)
    for index in range(30):
        detectors, text, cap = cases[index % len(cases)]
        chunks = _random_chunks(len(text), randomizer)
        assert _cap_invariance_run(detectors, text, chunks, cap) == expected[index % len(cases)]


def test_left_walk_cap_cut():
    stream = number_detectors("en_US").stream()
    text = "1 - " * 2000 + "x"
    cuts = []
    reader_cuts = []
    for offset in range(0, len(text), 1024):
        batch = stream.feed(text[offset : offset + 1024])
        cuts.extend(batch.cuts)
        reader_cuts.extend(batch.reader_cuts)
        state = stream.pending()
        assert state["total"] - state["buffered_from"] <= 2 * 4096
    final = stream.close()
    cuts.extend(final.cuts)
    reader_cuts.extend(final.reader_cuts)
    assert cuts or reader_cuts


def test_numeric_left_walk_has_independent_reader_and_stream_cuts():
    text = "1 - " * 2050 + "x"
    stream = number_detectors("en_US").stream()
    cuts = []
    reader_cuts = []
    truncated = []
    maximum_retained = 0
    for offset in range(0, len(text), 1024):
        batch = stream.feed(text[offset : offset + 1024])
        cuts.extend(batch.cuts)
        reader_cuts.extend(batch.reader_cuts)
        truncated.extend(item for item in batch.detections if item.get("truncated"))
        state = stream.pending()
        maximum_retained = max(maximum_retained, state["total"] - state["buffered_from"])

    assert cuts == [8192]
    assert ("number:decimal", 4096) in reader_cuts
    assert ("number:decimal", 8192) in reader_cuts
    assert truncated
    assert all(item["end"] <= 8192 for item in truncated)
    assert maximum_retained == 8192


def test_stream_cap_on_64k_run():
    class PrefixDetector:
        type = group = "demo:prefix"

        def detect(self, text):
            if not text:
                return []
            return [
                {
                    "text": text,
                    "start": 0,
                    "end": len(text),
                    "type": self.type,
                    "value": text,
                    "captures": (),
                    "spec": None,
                }
            ]

        def extent(self):
            return Extent(None, frozenset({"a"}), cap_chars=4096, source="test open run")

    stream = DetectionStream((PrefixDetector(),))
    truncated = []
    cuts = []
    for _ in range(64):
        batch = stream.feed("a" * 1024)
        truncated.extend(d for d in batch.detections if d.get("truncated"))
        cuts.extend(batch.cuts)
    final = stream.close()
    truncated.extend(d for d in final.detections if d.get("truncated"))
    assert cuts
    assert truncated


def test_flush_segments_and_close_contract():
    stream = number_detectors("en_US").stream(detect_stride_chars=1)
    assert stream.feed("12").detections == ()
    assert [d["text"] for d in stream.flush().detections] == ["12"]
    stream.feed("34")
    assert [d["text"] for d in stream.close().detections] == ["34"]
    assert stream.close() == DetectionBatch((), 4)
    with pytest.raises(RuntimeError, match="^detection stream is closed$"):
        stream.feed("")


def test_option_validation_and_feed_type():
    for name in ("max_pending_chars", "detect_stride_chars"):
        for value in (None, 0, -1, True, 1.5):
            with pytest.raises(ValueError, match=rf"^{name} must be a positive int$"):
                number_detectors("en_US").stream(**{name: value})
    with pytest.raises(TypeError, match="^chunk must be str$"):
        number_detectors("en_US").stream().feed(None)
    for value in ({"number:decimal": True}, {"number:decimal": 0}, {1: 2}, []):
        with pytest.raises(
            ValueError, match="^reader_cap_chars must map detector types to positive ints$"
        ):
            number_detectors("en_US").stream(reader_cap_chars=value)


def test_unstreamable_extent_refused():
    class Bad:
        type = group = "bad"

        def detect(self, text):
            return []

        def extent(self):
            return Extent(None, None)

    with pytest.raises(ValueError, match="declares no streamable extent"):
        DetectorSet((Bad(),)).stream()

    class Missing(EmptyDetector):
        extent = None

    class MissingCap(EmptyDetector):
        def extent(self):
            return Extent(None, frozenset())

    for detector in (Missing(), MissingCap()):
        message = (
            "detector 'empty' ("
            + type(detector).__name__
            + ") declares no streamable extent; define extent() -> Extent with a closing "
            "condition and cap_chars on each unbounded side"
        )
        with pytest.raises(ValueError, match=f"^{__import__('re').escape(message)}$"):
            DetectorSet((detector,)).stream()


def test_compiled_window_does_not_fill_scan_plan_cache():
    compiled = number_detectors("en_US").compile(warm=False)
    stream = compiled.stream(detect_stride_chars=1)
    stream.feed("12 done")
    stream.close()
    assert compiled._scan_plans == {}


@pytest.mark.parametrize(
    "text",
    ["x" * 65536, "one " * 16384, "a" + "\u0301" * 65535, "1 - " * 16384],
)
def test_retained_buffer_bound(text):
    stream = number_detectors("en_US").stream()
    for offset in range(0, len(text), 1024):
        stream.feed(text[offset : offset + 1024])
        pending = stream.pending()
        assert pending["total"] - pending["buffered_from"] <= 2 * 4096


def test_pending_from_contract_and_no_later_overlap():
    stream = number_detectors("en_US").stream(detect_stride_chars=1)
    emitted = []
    for chunk in ("I paid 1,2", "34 and 56 ", "more."):
        batch = stream.feed(chunk)
        assert all(item["end"] <= batch.pending_from for item in batch.detections)
        assert all(not (old["start"] < batch.pending_from < old["end"]) for old in emitted)
        emitted.extend(batch.detections)
    batch = stream.close()
    assert batch.pending_from == len("I paid 1,234 and 56 more.")


def test_stream_exception_parity():
    class RaisingDetector(EmptyDetector):
        def detect(self, text):
            raise LookupError(text)

    with pytest.raises(LookupError, match="boom"):
        DetectionStream((RaisingDetector(),)).feed("boom" * 2000)


def test_seam_excludes_crlf_interior():
    assert 2 not in _seams("a\r\nb")


def test_no_seam_inside_u202f_grouping():
    assert _seams("1\u202f234 x") == (6,)


def test_reader_cap_only_cuts_an_open_join_chain():
    class ClosedReader(EmptyDetector):
        type = group = "demo:closed"

        def extent(self):
            return Extent(None, frozenset(), r"[\p{Nd}]", cap_chars=8, source="test digits")

    batch = DetectionStream((ClosedReader(),), max_pending_chars=100).feed("a b c d e f")
    assert batch.reader_cuts == ()
