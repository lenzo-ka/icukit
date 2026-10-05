import random

import pytest

from icukit import DetectionBatch, Extent, number_detectors
from icukit.detectors import DetectorSet
from icukit.engine import reader_set
from icukit.stream import DetectionStream, _joinable, _seams, _shift_detection, extent_report

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
    assert stream.feed("I paid 1,2") == DetectionBatch((), 7)
    batch = stream.feed("34 and 56 ")
    assert [(d["text"], d["start"], d["end"]) for d in batch.detections] == [("1,234", 7, 12)]
    assert batch.pending_from == 17
    # ICU's signed exemplars ("-7") span two chunks, so "56 " waits for a complete,
    # non-joinable following chunk; "more." completes only at close.
    assert stream.feed("more.") == DetectionBatch((), 17)
    closing = stream.close()
    assert [d["text"] for d in closing.detections] == ["56"]
    assert closing.pending_from == 25


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
    # NumberDetector's extent is two chunks (ICU's signed exemplars), so "42" is
    # decided by T[:7] = "42 x x" (closing seam 5 plus the two-code-point peek).
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
    assert [(d["start"], d["end"], d.get("truncated")) for d in decimal] == [(0, 8, True)]
    assert first.reader_cuts == (("number:decimal", 8),)
    final = [d for d in stream.close().detections if d["type"] == "number:decimal"]
    assert [(d["start"], d["end"], d.get("truncated")) for d in final] == [(8, 20, None)]
    whole = [
        d
        for d in reader_set("en_US", flexible=True).detect("1" * 20 + " x")
        if d["type"] == "number:decimal"
    ]
    assert [(d["start"], d["end"]) for d in whole] == [(0, 20)]


def test_left_walk_cap_cut():
    stream = number_detectors("en_US").stream()
    text = "1 - " * 2000 + "x"
    cuts = []
    for offset in range(0, len(text), 1024):
        batch = stream.feed(text[offset : offset + 1024])
        cuts.extend(batch.cuts)
        state = stream.pending()
        assert state["total"] - state["buffered_from"] <= 2 * 4096
    cuts.extend(stream.close().cuts)
    assert cuts


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
