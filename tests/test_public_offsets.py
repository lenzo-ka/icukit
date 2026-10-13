"""Public conversion among code-point, UTF-8, and UTF-16 boundaries."""

import pytest

from icukit import TextOffsets


def test_astral_and_multibyte_boundaries_convert_in_every_direction():
    offsets = TextOffsets("A😀é中")
    boundaries = {
        "codepoint": (0, 1, 2, 3, 4),
        "utf8": (0, 1, 5, 7, 10),
        "utf16": (0, 1, 3, 4, 5),
    }

    for source, source_offsets in boundaries.items():
        for target, target_offsets in boundaries.items():
            assert offsets.convert(source_offsets, source=source, target=target) == target_offsets


def test_conversion_preserves_order_duplicates_and_round_trips():
    offsets = TextOffsets("😀abé")
    original = (4, 0, 2, 2, 1)

    utf8 = offsets.convert(original, source="codepoint", target="utf8")
    utf16 = offsets.convert(utf8, source="utf8", target="utf16")

    assert offsets.convert(utf16, source="utf16", target="codepoint") == original


@pytest.mark.parametrize(
    "source, offset",
    [
        ("codepoint", -1),
        ("codepoint", 3),
        ("utf8", -1),
        ("utf8", 6),
        ("utf16", -1),
        ("utf16", 4),
    ],
)
def test_out_of_range_offsets_raise_index_error(source, offset):
    with pytest.raises(IndexError, match="outside"):
        TextOffsets("😀a").convert((offset,), source=source, target=source)


@pytest.mark.parametrize(("source", "offset"), [("utf8", 1), ("utf8", 3), ("utf16", 1)])
def test_offsets_inside_an_astral_character_are_not_boundaries(source, offset):
    with pytest.raises(ValueError, match="not a code-point boundary"):
        TextOffsets("😀a").convert((offset,), source=source, target="codepoint")


def test_empty_text_has_one_boundary():
    offsets = TextOffsets("")
    assert offsets.convert((0,), source="utf8", target="utf16") == (0,)


def test_lone_surrogates_use_surrogatepass_utf8_widths():
    offsets = TextOffsets("\ud800a\udcff")

    assert offsets.convert((0, 1, 2, 3), source="codepoint", target="utf8") == (0, 3, 4, 7)
    assert offsets.convert((0, 3, 4, 7), source="utf8", target="utf16") == (0, 1, 2, 3)


def test_text_must_be_a_string():
    with pytest.raises(TypeError, match="text must be a str, not bytes"):
        TextOffsets(b"ab")


def test_text_is_read_only():
    offsets = TextOffsets("ab")

    assert offsets.text == "ab"
    with pytest.raises(AttributeError):
        offsets.text = "😀😀"


def test_offsets_must_be_integers():
    with pytest.raises(TypeError, match="offset must be an int"):
        TextOffsets("a").convert((True,), source="codepoint", target="utf8")


def test_unknown_coordinate_system_is_rejected():
    with pytest.raises(ValueError, match="unknown source offset unit"):
        TextOffsets("a").convert((0,), source="bytes", target="codepoint")
