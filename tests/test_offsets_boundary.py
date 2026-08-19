"""L0: strict bidirectional UTF-16 <-> code-point boundary maps."""

from icukit._offsets import boundary_maps, u16_boundary_to_codepoint


def test_ascii_is_identity():
    cp_to_u16, u16_to_cp = boundary_maps("abc")

    assert cp_to_u16 == [0, 1, 2, 3]
    assert u16_to_cp == {0: 0, 1: 1, 2: 2, 3: 3}


def test_astral_char_takes_two_utf16_units():
    # U+1F600 is astral: one code point, two UTF-16 units.
    text = "a\U0001f600b"
    cp_to_u16, u16_to_cp = boundary_maps(text)

    # code points 0..3 map to UTF-16 offsets 0,1,3,4 (the emoji spans [1,3)).
    assert cp_to_u16 == [0, 1, 3, 4]
    assert u16_to_cp == {0: 0, 1: 1, 3: 2, 4: 3}


def test_surrogate_interior_is_not_a_boundary():
    text = "a\U0001f600b"
    _, u16_to_cp = boundary_maps(text)

    # Offset 2 lands inside the surrogate pair -> not a genuine boundary.
    assert u16_boundary_to_codepoint(u16_to_cp, 2) is None
    assert u16_boundary_to_codepoint(u16_to_cp, 3) == 2
    assert u16_boundary_to_codepoint(u16_to_cp, 0) == 0


def test_end_offset_maps_to_length():
    text = "a\U0001f600b"
    cp_to_u16, u16_to_cp = boundary_maps(text)

    assert cp_to_u16[len(text)] == 4
    assert u16_to_cp[4] == len(text)


def test_empty_text():
    cp_to_u16, u16_to_cp = boundary_maps("")

    assert cp_to_u16 == [0]
    assert u16_to_cp == {0: 0}
