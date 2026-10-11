import random
import re
from dataclasses import replace

import pytest

from icukit import DetectionBatch, DetectorSet, number_detectors, reflow
from icukit.detectors import DetectorRefusal
from icukit.engine import reader_set
from icukit.recognize import FlexibleNumberRangeDetector
from icukit.stream import DetectionStream, _boundary_ends, _boundary_violations


def _run(detectors, text, chunks, **options):
    stream = detectors.stream(**options)
    found = []
    batches = []
    cursor = 0
    for size in chunks:
        batch = stream.feed(text[cursor : cursor + size])
        cursor += size
        found.extend(batch.detections)
        batches.append(batch)
    assert cursor == len(text)
    batch = stream.close()
    found.extend(batch.detections)
    batches.append(batch)
    return found, batches, stream


def _random_chunks(length, seed=20261009):
    randomizer = random.Random(seed)
    chunks = []
    while length:
        size = randomizer.randint(1, min(17, length))
        chunks.append(size)
        length -= size
    return chunks


def _chunkings(text):
    tokens = [len(chunk) for chunk in re.findall(r"\S+|\s+", text)]
    return ([len(text)], [1] * len(text), tokens, _random_chunks(len(text)))


def _restore_original_surfaces(found, source):
    restored = []
    for item in found:
        original = dict(item)
        original["text"] = source[item["start"] : item["end"]]
        original["captures"] = tuple(
            replace(capture, text=source[capture.start : capture.end])
            for capture in item["captures"]
        )
        restored.append(original)
    return restored


def _reflow_reference(detectors, text, *, mode, boundary, max_pending_chars):
    view = reflow(text, mode)
    found, batches, stream = _run(
        detectors,
        view,
        [len(view)],
        boundary=boundary,
        max_pending_chars=max_pending_chars,
    )
    return _restore_original_surfaces(found, text), batches, stream


@pytest.mark.parametrize("chunks_index", range(4))
def test_default_paragraph_stream_is_whole_text_identical(chunks_index):
    text = (
        "I paid $12.50 on May 5, 2024.\n\n"
        "The next values are 1,234 and 3–5 kg.\n \t\n"
        "最後は2024年5月3日と45円。\u2029Done."
    )
    detectors = reader_set("en_US", flexible=True).compile(warm=False)
    expected = detectors.detect(text)

    found, batches, _stream = _run(detectors, text, _chunkings(text)[chunks_index])

    assert found == expected
    assert batches[-1].pending_from == len(text)


@pytest.mark.parametrize(
    "boundary",
    ["\n\n", "\n \t\n", "\r\n\r\n", "\r\n \t\r\n", "\u2029"],
)
def test_paragraph_boundary_split_across_every_feed_position(boundary):
    text = f"12{boundary}34"
    detectors = number_detectors("en_US")
    expected = detectors.detect(text)

    for split in range(len(text) + 1):
        found, _batches, _stream = _run(detectors, text, [split, len(text) - split])
        assert found == expected


def test_boundary_settlement_uses_absolute_offsets_and_shifts_captures():
    text = "x 12.50\n\ny 34.75"
    detectors = number_detectors("en_US")
    stream = detectors.stream()

    first = stream.feed(text)
    second = stream.close()
    found = [*first.detections, *second.detections]

    assert found == detectors.detect(text)
    assert first.pending_from == len("x 12.50\n\n")
    assert all(text[item["start"] : item["end"]] == item["text"] for item in found)
    assert all(
        text[capture.start : capture.end] == capture.text
        for item in found
        for capture in item["captures"]
    )


def test_each_closed_segment_is_detected_once():
    text = "12\n\n34\u202956"
    stream = number_detectors("en_US").stream()

    batch = stream.feed(text)

    assert [item["text"] for item in batch.detections] == ["12", "34"]
    assert stream.window_detect_count == 2
    assert [item["text"] for item in stream.close().detections] == ["56"]
    assert stream.window_detect_count == 3


def test_line_mode_settles_crlf_as_one_boundary_even_when_split():
    stream = number_detectors("en_US").stream(boundary="line")

    assert stream.feed("12\r").pending_from == 0
    batch = stream.feed("\n34")

    assert [item["text"] for item in batch.detections] == ["12"]
    assert batch.pending_from == 4
    assert [item["text"] for item in stream.close().detections] == ["34"]


def test_line_mode_is_documented_not_to_preserve_a_wrapped_range():
    text = "3–\n5"
    detectors = DetectorSet((FlexibleNumberRangeDetector("en_US"),))
    assert [item["text"] for item in detectors.detect(text)] == [text]

    found, _batches, _stream = _run(detectors, text, [1] * len(text), boundary="line")

    assert found == []


def test_flush_records_an_identity_cut_and_marks_both_sides_truncated():
    detectors = number_detectors("en_US")
    identity_stream = detectors.stream()

    assert identity_stream.feed("3–\n").detections == ()
    identity_cut = identity_stream.flush()
    assert identity_cut.cuts == (3,)
    after = identity_stream.feed("5")
    assert after.detections == ()
    identity_stream.close()

    edge_stream = detectors.stream()
    assert edge_stream.feed("12").detections == ()
    before = edge_stream.flush()
    assert before.cuts == (2,)
    assert edge_stream.feed("34").detections == ()
    final = edge_stream.close()

    touching = [
        item
        for item in (*before.detections, *final.detections)
        if item["end"] == 2 or item["start"] == 2
    ]
    assert {(item["start"], item["end"]) for item in touching} == {(0, 2), (2, 4)}
    assert all(item.get("truncated") is True for item in touching)


def test_explicit_mode_settles_only_at_explicit_boundaries():
    stream = number_detectors("en_US").stream(boundary="explicit")

    assert stream.feed("12\n\n34").detections == ()
    first = stream.boundary()
    assert [item["text"] for item in first.detections] == ["12", "34"]
    assert first.pending_from == 6
    assert stream.feed("56").detections == ()
    assert [item["text"] for item in stream.flush().detections] == ["56"]


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


def _cap_run(text, chunks, cap=8):
    stream = DetectionStream((PrefixDetector(),), max_pending_chars=cap)
    detections = []
    cuts = []
    pending = []
    cursor = 0
    for size in chunks:
        batch = stream.feed(text[cursor : cursor + size])
        cursor += size
        detections.extend(batch.detections)
        cuts.extend(batch.cuts)
        pending.append(batch.pending_from)
        state = stream.pending()
        assert state["total"] - state["buffered_from"] <= cap
    batch = stream.close()
    detections.extend(batch.detections)
    cuts.extend(batch.cuts)
    pending.append(batch.pending_from)
    return detections, cuts, pending[-1]


def test_cap_cuts_and_output_are_chunk_invariant():
    text = "a" * 20
    expected = _cap_run(text, [len(text)])

    assert _cap_run(text, [1] * len(text)) == expected
    assert _cap_run(text, _random_chunks(len(text))) == expected
    detections, cuts, pending = expected
    assert cuts == [8, 16]
    assert [(item["start"], item["end"], item.get("truncated")) for item in detections] == [
        (0, 8, True),
        (8, 16, True),
        (16, 20, True),
    ]
    assert pending == len(text)


def test_detection_starting_at_a_cap_cut_is_truncated():
    stream = number_detectors("en_US").stream(max_pending_chars=8)

    first = stream.feed("1" * 10)
    final = stream.close()

    assert first.cuts == (8,)
    after_cut = [item for item in final.detections if (item["start"], item["end"]) == (8, 10)]
    assert after_cut
    assert all(item.get("truncated") is True for item in after_cut)


def test_cap_prefers_the_last_complete_whitespace_boundary():
    _detections, cuts, _pending = _cap_run("abc def ghi", [11])
    assert cuts == [8]


@pytest.mark.parametrize("feed_width", [1, 32, 1024])
def test_cap_uses_last_whitespace_edge_in_fixed_prefix_across_feed_widths(feed_width):
    text = "a" + " " * 40 + "b"
    chunks = [feed_width] * (len(text) // feed_width)
    if remainder := len(text) % feed_width:
        chunks.append(remainder)

    _detections, cuts, _pending = _cap_run(text, chunks)

    assert cuts == [8, 16, 24, 32, 40]


def test_cap_falls_back_to_a_codepoint_for_one_overlong_grapheme():
    text = "a" + "\u0301" * 16
    _detections, cuts, _pending = _cap_run(text, [len(text)])
    assert cuts == [8, 16]


def test_cap_bounds_a_64k_single_paragraph():
    text = "a" * 65_536
    detections, cuts, pending = _cap_run(text, [1024] * 64, cap=4096)

    assert cuts == list(range(4096, 65_536, 4096))
    assert len([item for item in detections if item.get("truncated")]) == len(cuts) + 1
    assert pending == len(text)


def test_large_single_feed_has_linear_character_copy_count():
    class CountedString(str):
        copied = 0

        def __add__(self, other):
            result = type(self)(super().__add__(other))
            type(self).copied += len(result)
            return result

        def __getitem__(self, key):
            result = super().__getitem__(key)
            if isinstance(result, str):
                type(self).copied += len(result)
                return type(self)(result)
            return result

    size = 65_536
    stream = DetectionStream((PrefixDetector(),), max_pending_chars=256)
    stream._text = CountedString("")

    batch = stream.feed("x" * size)

    assert len(batch.cuts) == size // 256 - 1
    assert CountedString.copied <= size * 5


def test_cap_prefers_a_real_boundary_before_the_limit():
    text = "12\n\n" + "a" * 20
    stream = DetectionStream((PrefixDetector(),), max_pending_chars=8)

    batch = stream.feed(text)

    assert batch.cuts == (12, 20)
    assert [(item["start"], item["end"], item.get("truncated")) for item in batch.detections] == [
        (0, 4, None),
        (4, 12, True),
        (12, 20, True),
    ]


def test_pending_from_is_monotone_and_marks_the_open_segment():
    stream = number_detectors("en_US").stream()
    positions = []
    for chunk in ("12\n", "\n34", "\u2029", "56"):
        positions.append(stream.feed(chunk).pending_from)
    positions.append(stream.close().pending_from)

    assert positions == sorted(positions)
    assert positions == [0, 4, 7, 7, 9]


def test_flush_close_and_closed_contract():
    stream = number_detectors("en_US").stream()
    assert stream.feed("12").detections == ()
    assert [item["text"] for item in stream.flush().detections] == ["12"]
    stream.feed("34")
    assert [item["text"] for item in stream.close().detections] == ["34"]
    assert stream.close() == DetectionBatch((), 4)
    with pytest.raises(RuntimeError, match="^detection stream is closed$"):
        stream.feed("")
    with pytest.raises(RuntimeError, match="^detection stream is closed$"):
        stream.flush()


def test_option_validation_and_feed_type():
    for value in (None, 0, -1, True, 1.5):
        with pytest.raises(ValueError, match="^max_pending_chars must be a positive int$"):
            number_detectors("en_US").stream(max_pending_chars=value)
    for value in (None, "", "sentence", 1):
        with pytest.raises(
            ValueError, match="^boundary must be 'paragraph', 'line', or 'explicit'$"
        ):
            number_detectors("en_US").stream(boundary=value)
    with pytest.raises(TypeError, match="^chunk must be str$"):
        number_detectors("en_US").stream().feed(None)


def test_third_party_detector_needs_no_extent_declaration():
    stream = DetectionStream((PrefixDetector(),))
    assert stream.feed("abc\n\n").detections[0]["text"] == "abc\n\n"


def test_compiled_stream_uses_the_compiled_whole_text_path():
    compiled = number_detectors("en_US").compile(warm=False)
    stream = compiled.stream()
    batch = stream.feed("12\n\n")
    stream.close()
    assert [item["text"] for item in batch.detections] == ["12"]
    assert stream.window_detect_count == 1


def test_detector_refusal_offsets_are_absolute_after_a_segment():
    class RefusingDetector:
        type = group = "demo:refusing"

        def detect(self, text):
            if text.startswith("boom"):
                raise DetectorRefusal(
                    self.type,
                    1,
                    2,
                    "mid-grapheme-endpoint",
                    "test refusal",
                )
            return []

    stream = DetectionStream((RefusingDetector(),))
    assert stream.feed("ok\n\n").pending_from == 4
    with pytest.raises(DetectorRefusal) as caught:
        stream.feed("boom\n\n")
    assert (caught.value.start, caught.value.endpoint) == (5, 6)


def test_feed_is_transactional_when_a_later_segment_raises():
    class FailingDetector(PrefixDetector):
        fail = True

        def detect(self, text):
            if self.fail and text == "boom\u2029":
                raise RuntimeError("later segment failed")
            return super().detect(text)

    detector = FailingDetector()
    stream = DetectionStream((detector,))
    text = "ok\n\nboom\u2029"

    with pytest.raises(RuntimeError, match="later segment failed"):
        stream.feed(text)

    assert stream.pending() == {
        "pending_from": 0,
        "decided_through": 0,
        "buffered_from": 0,
        "total": 0,
        "open_chunk": None,
    }
    assert stream.window_detect_count == 0

    detector.fail = False
    batch = stream.feed(text)
    assert [item["text"] for item in batch.detections] == ["ok\n\n", "boom\u2029"]


def test_boundary_helpers_cover_the_public_modes():
    text = "a\r\n\r\nb\n c\n d\u2028e\u2029f"
    assert _boundary_ends(text, "paragraph", final=True) == (5, 15)
    assert _boundary_ends("a\r", "line") == ()
    assert _boundary_ends("a\r", "line", final=True) == (2,)
    assert _boundary_ends(text, "explicit", final=True) == ()


def test_boundary_violation_audit_reports_crossing_spans():
    detection = {
        "text": "3–\n5",
        "start": 0,
        "end": 4,
        "type": "number:range",
        "value": None,
        "captures": (),
        "spec": None,
    }
    assert _boundary_violations("3–\n5", (detection,), "paragraph") == ()
    assert _boundary_violations("3–\n5", (detection,), "line") == ("number:range:0:4@3",)


def _capital_bound_text(terminator, distance):
    sample = terminator.join(
        [
            "a hard wrapped sample line that has a stable representative width",
            "a second sample line that has a stable representative width here",
            "a third sample line that has a stable representative width here",
            "a fourth sample line that has a stable representative width here",
            "a fifth sample line that has a stable representative width here",
            "The quick brown fox jumps over the lazy dog and more",
        ]
    )
    first = len(sample)
    padding = distance - len(terminator) - 1
    text = (
        sample
        + terminator
        + "B"
        + "y" * padding
        + terminator
        + "Cats are nice"
        + terminator
        + "Dogs too."
        + terminator
    )
    assert text.index(terminator, first + len(terminator)) - first == distance
    return text + "z" * (2100 - len(text))


@pytest.mark.parametrize("mode", ["none", "lines", "paragraphs", "auto"])
@pytest.mark.parametrize("boundary", ["paragraph", "line", "explicit"])
@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
@pytest.mark.parametrize("distance", [1023, 1024, 1025])
@pytest.mark.parametrize("chunking", ["one", "random"])
def test_detection_reflow_freezes_at_the_whole_text_bound(
    mode, boundary, terminator, distance, chunking
):
    text = _capital_bound_text(terminator, distance)
    detectors = DetectorSet((PrefixDetector(),))
    options = {"reflow": mode, "boundary": boundary, "max_pending_chars": 256}
    expected, expected_batches, _reference_stream = _reflow_reference(
        detectors,
        text,
        mode=mode,
        boundary=boundary,
        max_pending_chars=256,
    )
    chunks = [1] * len(text) if chunking == "one" else _random_chunks(len(text), distance)

    found, batches, _stream = _run(detectors, text, chunks, **options)

    assert found == expected
    assert [cut for batch in batches for cut in batch.cuts] == [
        cut for batch in expected_batches for cut in batch.cuts
    ]


@pytest.mark.parametrize("mode", ["none", "lines", "paragraphs", "auto"])
@pytest.mark.parametrize("boundary", ["paragraph", "line", "explicit"])
@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
@pytest.mark.parametrize("chunking", ["one", "random"])
def test_detection_reflow_freezes_long_separators(mode, boundary, terminator, chunking):
    first = "this paragraph runs on without terminal punctuation at its end"
    following = "the next paragraph begins here and continues for a long while on and on " * 30
    text = first + terminator * 5 + following + terminator
    detectors = DetectorSet((PrefixDetector(),))
    expected, expected_batches, _reference_stream = _reflow_reference(
        detectors,
        text,
        mode=mode,
        boundary=boundary,
        max_pending_chars=256,
    )
    chunks = [1] * len(text) if chunking == "one" else _random_chunks(len(text), 147)

    found, batches, _stream = _run(
        detectors,
        text,
        chunks,
        reflow=mode,
        boundary=boundary,
        max_pending_chars=256,
    )

    assert found == expected
    assert [cut for batch in batches for cut in batch.cuts] == [
        cut for batch in expected_batches for cut in batch.cuts
    ]


@pytest.mark.parametrize("mode", ["none", "lines", "paragraphs", "auto"])
@pytest.mark.parametrize("boundary", ["paragraph", "line", "explicit"])
@pytest.mark.parametrize("chunking", ["one", "random"])
def test_detection_reflow_reads_wrapped_values(mode, boundary, chunking):
    hard_wrap = "ordinary words make this source line long enough for joining and finish with "
    text = (
        hard_wrap
        + "more ordinary prose across the first line ending here\n"
        + hard_wrap
        + "more ordinary prose across the second line ending here\n"
        + hard_wrap
        + "more ordinary prose across the third line ending here\n"
        + hard_wrap
        + "$\n12.50, followed by enough ordinary words to make this source line very long, "
        + "then a measured value of 3\nkg, followed by enough ordinary words to make this "
        + "source line very long, and the date May\n5, 2024."
    )
    detectors = reader_set(
        "en_US",
        flexible=True,
        locales=(),
        currencies=("USD",),
        units=("kilogram",),
    )
    expected, _expected_batches, _reference_stream = _reflow_reference(
        detectors,
        text,
        mode=mode,
        boundary=boundary,
        max_pending_chars=4096,
    )
    chunks = [1] * len(text) if chunking == "one" else _random_chunks(len(text), 911)

    found, _batches, _stream = _run(
        detectors,
        text,
        chunks,
        reflow=mode,
        boundary=boundary,
    )

    assert found == expected
    assert all(text[item["start"] : item["end"]] == item["text"] for item in found)
    assert all(
        text[capture.start : capture.end] == capture.text
        for item in found
        for capture in item["captures"]
    )
    if mode != "none":
        assert any(item["text"] == "$\n12.50" for item in found)
        assert any(item["text"] == "3\nkg" for item in found)
        assert any(item["text"] == "May\n5, 2024" for item in found)


@pytest.mark.parametrize("mode", ["lines", "paragraphs", "auto"])
def test_detection_reflow_retention_is_bounded_on_unterminated_input(mode):
    stream = DetectionStream(
        (PrefixDetector(),),
        max_pending_chars=4096,
        boundary="explicit",
        reflow=mode,
    )
    maximum = 0
    for _ in range(4):
        stream.feed("word " * 13_108)
        state = stream.pending()
        maximum = max(maximum, state["total"] - state["buffered_from"])
    stream.close()

    assert maximum <= 4096 + 3 * 1024


def test_detection_stream_reflow_validation_is_shared_by_both_factories():
    message = "^reflow must be one of 'none', 'lines', 'paragraphs', 'auto'$"
    with pytest.raises(ValueError, match=message):
        number_detectors("en_US").stream(reflow="invalid")
    with pytest.raises(ValueError, match=message):
        number_detectors("en_US").compile(warm=False).stream(reflow="invalid")


def test_compiled_detection_stream_reflows_and_restores_original_surfaces():
    text = "A sufficiently long source line describes the measured value 3\nkg."
    stream = (
        reader_set("en_US", flexible=True, locales=(), currencies=(), units=("kilogram",))
        .compile(warm=False)
        .stream(reflow="lines")
    )

    stream.feed(text[:20])
    stream.feed(text[20:])
    found = stream.close().detections

    assert any(item["text"] == "3\nkg" for item in found)
    assert all(text[item["start"] : item["end"]] == item["text"] for item in found)
