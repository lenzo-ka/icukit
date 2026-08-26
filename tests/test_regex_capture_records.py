"""Tests for regex capture records and code-point positions."""

import io
import json
import sys

import pytest

from icukit import UnicodeRegex
from icukit._offsets import boundary_maps
from icukit.cli import main
from icukit.regex import _codepoint_boundary


def test_capture_record_distinguishes_unmatched_and_empty_groups():
    assert UnicodeRegex(r"(x)?(y)(z*)").find("😀yq") == {
        "text": "y",
        "start": 1,
        "end": 2,
        "groups": {
            1: {"text": None, "start": None, "end": None},
            2: {"text": "y", "start": 1, "end": 2},
            3: {"text": "", "start": 2, "end": 2},
        },
    }


def test_group_positions_with_astral_characters_and_repeated_text():
    match = UnicodeRegex(r"(a).(a)").find("a😀a-a😀a")
    assert match == {
        "text": "a😀a",
        "start": 0,
        "end": 3,
        "groups": {
            1: {"text": "a", "start": 0, "end": 1},
            2: {"text": "a", "start": 2, "end": 3},
        },
    }


@pytest.mark.parametrize("text", ["yq", "😀yq"])
def test_unmatched_group_sentinel_is_never_converted(text):
    match = UnicodeRegex(r"(x)?y").find(text)
    assert match is not None
    assert match["groups"][1] == {"text": None, "start": None, "end": None}


def test_nested_group_positions():
    assert UnicodeRegex(r"((ab)c)").find("abc")["groups"] == {
        1: {"text": "abc", "start": 0, "end": 3},
        2: {"text": "ab", "start": 0, "end": 2},
    }


def test_repeated_group_reports_final_capture():
    assert UnicodeRegex(r"(?:(a[0-9]))+").find("a1a2a3")["groups"][1] == {
        "text": "a3",
        "start": 4,
        "end": 6,
    }


def test_pattern_without_capture_groups_has_empty_group_mapping():
    assert UnicodeRegex("a").find("a")["groups"] == {}


def test_named_group_is_returned_by_numeric_index():
    assert UnicodeRegex(r"(?<yr>\d{4})").find("2026")["groups"] == {
        1: {"text": "2026", "start": 0, "end": 4}
    }


def test_find_start_uses_code_point_positions():
    regex = UnicodeRegex("a")
    assert regex.find("😀ab", start=2) is None
    assert regex.find("😀ab", start=1) == {
        "text": "a",
        "start": 1,
        "end": 2,
        "groups": {},
    }


def test_find_allows_astral_end_position_for_zero_width_match():
    assert UnicodeRegex(r"(?=.|$)").find("😀a", start=2) == {
        "text": "",
        "start": 2,
        "end": 2,
        "groups": {},
    }


def test_find_returns_none_when_start_exceeds_text_length():
    assert UnicodeRegex("$").find("abc", start=4) is None


def test_find_rejects_negative_start():
    with pytest.raises(ValueError, match="start must be non-negative"):
        UnicodeRegex("a").find("abc", start=-1)


def test_find_resume_loop_uses_code_point_ends_after_astral_character():
    regex = UnicodeRegex("a")
    text = "😀aa"
    positions = []
    start = 0
    while match := regex.find(text, start):
        positions.append((match["start"], match["end"]))
        start = match["end"]
    assert positions == [(1, 2), (2, 3)]


def test_find_resume_loop_progresses_past_zero_width_and_astral_text():
    regex = UnicodeRegex(r"a*")
    text = "a😀"
    positions = []
    start = 0
    while match := regex.find(text, start):
        positions.append((match["start"], match["end"]))
        if match["start"] == match["end"]:
            if match["end"] == len(text):
                break
            start = match["end"] + 1
        else:
            start = match["end"]
    assert positions == [(0, 1), (1, 1), (2, 2)]


def test_find_all_and_iter_matches_return_complete_identical_records():
    regex = UnicodeRegex(r"(a)?")
    expected = [
        {
            "text": "",
            "start": 0,
            "end": 0,
            "groups": {1: {"text": None, "start": None, "end": None}},
        },
        {
            "text": "a",
            "start": 1,
            "end": 2,
            "groups": {1: {"text": "a", "start": 1, "end": 2}},
        },
        {
            "text": "",
            "start": 2,
            "end": 2,
            "groups": {1: {"text": None, "start": None, "end": None}},
        },
    ]
    assert regex.find_all("😀a") == expected
    assert list(regex.iter_matches("😀a")) == expected


def test_strict_reverse_conversion_rejects_surrogate_interior():
    _, reverse = boundary_maps("😀a")
    assert _codepoint_boundary(reverse, 0) == 0
    assert _codepoint_boundary(reverse, 2) == 1
    assert _codepoint_boundary(reverse, 3) == 2
    with pytest.raises(RuntimeError, match="non-boundary UTF-16 offset 1"):
        _codepoint_boundary(reverse, 1)


def test_cli_groups_keep_list_of_text_json_shape(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("y"))
    monkeypatch.setattr(
        sys,
        "argv",
        ["icukit", "regex", "find", r"(x)?(y)(z*)", "--all", "--groups", "--json"],
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == [
        {"match": "y", "start": 0, "end": 1, "groups": [None, "y", ""]}
    ]


def test_replace_callback_can_inspect_capture_record():
    regex = UnicodeRegex(r"(a)?b")

    def replacement(match):
        capture = match["groups"][1]
        if capture["text"] is None:
            assert capture == {"text": None, "start": None, "end": None}
            return "missing"
        assert capture == {"text": "a", "start": 1, "end": 2}
        return f"{capture['start']}:{capture['end']}"

    assert regex.replace_with_callback("😀ab b", replacement) == "😀1:2 missing"


def test_other_regex_operations_remain_unchanged():
    regex = UnicodeRegex(r"(\d)")
    assert regex.replace("1 2 3", "<$1>", limit=2) == "<1> <2> 3"
    assert UnicodeRegex(",").split("a,b,c", limit=1) == ["a", "b,c"]
    assert regex.search("a1") is True
    assert regex.match("1") is True
