"""Tests for the shape of ``--json`` output across the CLI.

The invariant under test: a consumer never has to branch on cardinality. A command
that returns a collection returns a JSON array at every size, including one and zero.
A command that returns exactly one thing by nature returns a bare JSON object.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from icukit.formatters import format_output, print_record

ROOT = Path(__file__).parents[1]


def run_cli(*args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", *args],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def json_stdout(*args, input_text=None, expected_returncode=0):
    result = run_cli(*args, input_text=input_text)
    assert result.returncode == expected_returncode, result.stderr
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# format_output preserves the shape it is given
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ([], "[]"),
        (["aa"], '[\n  "aa"\n]'),
        (["aa", "bb"], '[\n  "aa",\n  "bb"\n]'),
        ([{"a": 1}], '[\n  {\n    "a": 1\n  }\n]'),
        ({"a": 1}, '{\n  "a": 1\n}'),
    ],
)
def test_format_output_json_preserves_cardinality(data, expected):
    """A sequence renders as an array at every length; a mapping renders bare."""
    assert format_output(data, as_json=True) == expected


def test_print_record_renders_a_bare_object_in_json(capsys):
    print_record({"unit": "meter"}, as_json=True)
    assert json.loads(capsys.readouterr().out) == {"unit": "meter"}


def test_print_record_renders_a_single_row_in_tsv(capsys):
    print_record({"unit": "meter", "type": "length"}, columns=["unit", "type"])
    assert capsys.readouterr().out == "unit\ttype\nmeter\tlength\n"


# ---------------------------------------------------------------------------
# Collections: a list at every size
# ---------------------------------------------------------------------------


def test_plural_categories_is_a_list_for_a_single_category_locale():
    """Japanese has exactly one cardinal category; the array must still be an array."""
    assert json_stdout("plural", "categories", "-l", "ja", "--json") == [{"category": "other"}]


def test_plural_categories_is_a_list_for_a_many_category_locale():
    categories = json_stdout("plural", "categories", "-l", "ar", "--json")
    assert isinstance(categories, list) and len(categories) > 1


def test_script_detect_all_is_a_list_for_single_script_text():
    assert json_stdout("script", "detect", "--all", "--json", "-t", "abc") == ["Latin"]


def test_script_detect_all_is_a_list_for_mixed_script_text():
    scripts = json_stdout("script", "detect", "--all", "--json", "-t", "abc Ελληνικά")
    assert isinstance(scripts, list) and len(scripts) > 1


@pytest.mark.parametrize(
    ("input_text", "expected"),
    [
        ("", []),
        ("b\n", ["b"]),
        ("b\na\nc\n", ["a", "b", "c"]),
    ],
)
def test_collate_sort_json_is_a_list_at_every_size(input_text, expected):
    assert json_stdout("collate", "sort", "--json", input_text=input_text) == expected


@pytest.mark.parametrize(
    ("input_text", "expected"),
    [
        ("", []),
        ("münchen.de\n", [{"input": "münchen.de", "output": "xn--mnchen-3ya.de"}]),
        (
            "münchen.de\n例え.jp\n",
            [
                {"input": "münchen.de", "output": "xn--mnchen-3ya.de"},
                {"input": "例え.jp", "output": "xn--r8jz45g.jp"},
            ],
        ),
    ],
)
def test_idna_encode_json_is_a_list_at_every_size(input_text, expected):
    assert json_stdout("idna", "encode", "--json", input_text=input_text) == expected


@pytest.mark.parametrize(
    ("input_text", "expected"),
    [
        ("", []),
        ("xn--mnchen-3ya.de\n", [{"input": "xn--mnchen-3ya.de", "output": "münchen.de"}]),
        (
            "xn--mnchen-3ya.de\nxn--r8jz45g.jp\n",
            [
                {"input": "xn--mnchen-3ya.de", "output": "münchen.de"},
                {"input": "xn--r8jz45g.jp", "output": "例え.jp"},
            ],
        ),
    ],
)
def test_idna_decode_json_is_a_list_at_every_size(input_text, expected):
    assert json_stdout("idna", "decode", "--json", input_text=input_text) == expected


def test_idna_encode_json_wraps_a_positional_domain_in_a_list():
    assert json_stdout("idna", "encode", "münchen.de", "--json") == [
        {"input": "münchen.de", "output": "xn--mnchen-3ya.de"}
    ]


def test_datetime_calendars_json_is_a_list():
    """``list_calendars_info()`` takes no arguments, so its length is fixed by the
    ICU build; the empty and single-element cases are unreachable from the CLI."""
    calendars = json_stdout("datetime", "calendars", "--json")
    assert isinstance(calendars, list) and len(calendars) > 1
    assert {"type", "description"} <= set(calendars[0])


# ---------------------------------------------------------------------------
# Single records: a bare object, not a list of one
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arguments", "keys"),
    [
        (("measure", "info", "meter", "--json"), {"identifier", "type"}),
        (("parse", "currency", "$1,234.56", "--json"), {"value", "currency"}),
        (("duration", "parse", "PT1H30M", "--json"), {"hours", "minutes"}),
        (("collate", "info", "en_US", "--json"), {"locale", "strength"}),
        (("calendar", "info", "gregorian", "--json"), {"type", "description"}),
        (("timezone", "info", "America/New_York", "--json"), {"id"}),
        (("script", "info", "Greek", "--json"), {"code", "name"}),
        (("region", "info", "US", "--json"), {"code", "name"}),
    ],
)
def test_single_record_commands_emit_a_bare_object(arguments, keys):
    payload = json_stdout(*arguments)
    assert isinstance(payload, dict), f"{' '.join(arguments)} emitted {type(payload).__name__}"
    assert keys <= set(payload)


def test_bidi_detect_emits_a_bare_object():
    payload = json_stdout("bidi", "detect", "--json", "-t", "abc")
    assert isinstance(payload, dict)
    assert "direction" in payload


def test_plural_info_emits_a_bare_object():
    result = run_cli("plural", "info", "-l", "en", "--json")
    if "Ordinal rules not supported" in result.stderr:
        pytest.skip("this PyICU build has no ordinal plural rules")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert {"locale", "cardinal_categories"} <= set(payload)


# ---------------------------------------------------------------------------
# Newly added --json on single-result commands
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (
            ("collate", "compare", "abc", "abd", "--json"),
            {"a": "abc", "b": "abd", "order": -1, "relation": "<"},
        ),
        (
            ("collate", "compare", "abc", "abc", "--json"),
            {"a": "abc", "b": "abc", "order": 0, "relation": "="},
        ),
        (
            ("collate", "compare", "abd", "abc", "--json"),
            {"a": "abd", "b": "abc", "order": 1, "relation": ">"},
        ),
        (
            ("measure", "format", "5.5", "kilometer", "--json"),
            {"value": 5.5, "unit": "kilometer", "formatted": "5.5 kilometers"},
        ),
        (
            ("measure", "convert", "10", "km", "mi", "--json"),
            {"value": 10.0, "from_unit": "km", "to_unit": "mi", "formatted": "6.214 mi"},
        ),
        (
            ("measure", "range", "5", "10", "kilometer", "--json"),
            {"low": 5.0, "high": 10.0, "unit": "kilometer"},
        ),
        (
            ("measure", "sequence", "5 foot, 10 inch", "--json"),
            {
                "measures": [{"value": 5.0, "unit": "foot"}, {"value": 10.0, "unit": "inch"}],
                "formatted": "5 feet 10 inches",
            },
        ),
        (
            ("measure", "usage", "100", "km", "--usage", "road", "--json"),
            {"value": 100.0, "unit": "km", "usage": "road"},
        ),
        (
            ("measure", "check", "km", "mi", "--json"),
            {"from_unit": "km", "to_unit": "mi", "same_type": True},
        ),
        (
            ("datetime", "parse", "January 15, 2024", "--json"),
            {"text": "January 15, 2024", "parsed": "2024-01-15T00:00:00"},
        ),
        (
            ("datetime", "format", "2024-01-15T10:30:00", "--json"),
            {"datetime": "2024-01-15T10:30:00", "locale": "en_US"},
        ),
        (
            ("datetime", "relative", "-5", "--json"),
            {"days": -5, "hours": 0, "formatted": "5 days ago"},
        ),
        (
            ("datetime", "interval", "2024-01-15", "2024-01-20", "--json"),
            {"start": "2024-01-15T00:00:00", "end": "2024-01-20T00:00:00"},
        ),
    ],
)
def test_new_json_commands_emit_a_bare_object_with_the_expected_fields(arguments, expected):
    result = run_cli(*arguments)
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    for key, value in expected.items():
        assert payload[key] == value, key


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        (("measure", "format", "5.5", "kilometer"), "formatted"),
        (("measure", "range", "5", "10", "kilometer"), "formatted"),
        (("measure", "sequence", "5 foot, 10 inch"), "formatted"),
        (("measure", "usage", "100", "km", "--usage", "road"), "formatted"),
        (("datetime", "format", "2024-01-15T10:30:00"), "formatted"),
        (("datetime", "relative", "-5"), "formatted"),
        (("datetime", "interval", "2024-01-15", "2024-01-20"), "formatted"),
        (("datetime", "parse", "January 15, 2024"), "parsed"),
    ],
)
def test_the_rendered_field_matches_the_human_output(arguments, field):
    """The JSON record carries the same string the command prints without --json."""
    plain = run_cli(*arguments)
    assert plain.returncode == 0, plain.stderr
    payload = json_stdout(*arguments, "--json")
    assert payload[field] == plain.stdout.rstrip("\n")


def test_datetime_patterns_json_is_one_document_of_two_collections():
    payload = json_stdout("datetime", "patterns", "--json")
    assert isinstance(payload, dict)
    assert isinstance(payload["symbols"], list) and payload["symbols"]
    assert isinstance(payload["named_patterns"], list) and payload["named_patterns"]
    assert {"symbol", "name", "example"} == set(payload["symbols"][0])
    assert {"name", "pattern", "example"} == set(payload["named_patterns"][0])


# ---------------------------------------------------------------------------
# --json does not disturb the exit status these commands report their result with
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arguments", "returncode"),
    [
        (("collate", "compare", "abc", "abd"), 1),
        (("collate", "compare", "abc", "abc"), 0),
        (("collate", "compare", "abd", "abc"), 2),
        (("measure", "check", "km", "mi"), 0),
        (("measure", "check", "km", "kilogram"), 1),
    ],
)
def test_exit_status_is_the_same_with_and_without_json(arguments, returncode):
    assert run_cli(*arguments).returncode == returncode
    assert run_cli(*arguments, "--json").returncode == returncode


# ---------------------------------------------------------------------------
# Human output is unchanged on the commands that gained --json
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("collate", "compare", "abc", "abd"), '"abc" < "abd"\n'),
        (("measure", "format", "5.5", "kilometer"), "5.5 kilometers\n"),
        (("measure", "convert", "10", "km", "mi"), "6.214 mi\n"),
        (("measure", "convert", "10", "km", "mi", "--raw"), "6.21371\n"),
        (("measure", "range", "5", "10", "kilometer"), "5.0–10.0 kilometers\n"),
        (("measure", "sequence", "5 foot, 10 inch"), "5 feet 10 inches\n"),
        (("measure", "check", "km", "mi"), "Yes, km and mi have the same unit type\n"),
        (("datetime", "parse", "January 15, 2024"), "2024-01-15T00:00:00\n"),
        (("idna", "encode", "münchen.de"), "xn--mnchen-3ya.de\n"),
        (("idna", "decode", "xn--mnchen-3ya.de"), "münchen.de\n"),
    ],
)
def test_human_output_is_unchanged(arguments, expected):
    assert run_cli(*arguments).stdout == expected


def test_datetime_calendars_human_output_is_unchanged():
    stdout = run_cli("datetime", "calendars").stdout
    assert stdout.startswith("Available Calendar Systems:\n\n")
    assert "  gregorian            Gregorian calendar (Western standard)\n" in stdout


def test_datetime_patterns_human_output_is_unchanged():
    stdout = run_cli("datetime", "patterns").stdout
    assert stdout.startswith("Pattern Symbols:\n\n")
    assert "  y   Year            yyyy=2024, yy=24\n" in stdout
    assert "\nNamed Patterns:\n\n" in stdout
