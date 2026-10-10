"""ICU regex resource limits and stateful-loop semantics."""

import pytest

from icukit import (
    PatternError,
    RegexLimitError,
    UnicodeRegex,
    regex_detect,
    regex_replace,
    regex_search,
    regex_split,
)
from icukit.cli.locale_helpers import parse_multi_value


@pytest.mark.parametrize(
    "operation",
    [
        lambda text: UnicodeRegex("(a+)+$").find_all(text),
        lambda text: UnicodeRegex("(a+)+$").search(text),
        lambda text: UnicodeRegex("(a+)+$").split(text),
        lambda text: UnicodeRegex("(a+)+$").replace(text, "x"),
        lambda text: regex_detect(text, "(a+)+$", "test"),
    ],
)
def test_regex_catastrophic_raises(operation):  # R
    with pytest.raises(PatternError) as caught:
        operation("a" * 65_536 + "b")

    assert type(caught.value).__name__ == "RegexLimitError"
    assert str(caught.value) == "regex exceeded its time limit of 10000 steps: '(a+)+$'"
    assert caught.value.__cause__ is None


def test_regex_stateful_g_catastrophic_raises():  # R
    with pytest.raises(PatternError) as caught:
        UnicodeRegex(r"\G(?:x|(a+)+$)").find_all("x" + "a" * 65_536 + "b")

    assert type(caught.value).__name__ == "RegexLimitError"


@pytest.mark.parametrize(
    ("pattern", "operation"),
    [
        ("(a|b)*c", lambda regex, text: regex.search(text)),
        (r"\G(?:x|(a|b)*c)", lambda regex, text: regex.find_all(text)),
    ],
)
def test_regex_stack_overflow_not_silent(pattern, operation):  # R
    with pytest.raises(PatternError) as caught:
        operation(UnicodeRegex(pattern), "ab" * 1_000_000 + "c")

    assert type(caught.value).__name__ == "RegexLimitError"
    assert caught.value.limit == "stack"
    assert isinstance(caught.value.__cause__, Exception)


def test_locale_filter_pattern_bounded():  # R
    with pytest.raises(RegexLimitError):
        parse_multi_value("(a|aa)+$", available_values=["a" * 48 + "b"])


def test_regex_find_all_not_truncated():  # C
    assert len(UnicodeRegex(r"\p{L}+").find_all("ab " * 100_000)) == 100_000


def test_regex_loop_semantics():  # C
    assert [item["text"] for item in UnicodeRegex(r"\Ga").find_all("aaa")] == ["a"] * 3
    assert UnicodeRegex(r"\G\w").split("abc!") == ["", "", "", "!"]
    assert UnicodeRegex("x*").replace("ab", "-") == "-a-b-"


def test_regex_replace_matches_icu():  # C
    assert UnicodeRegex("(?x)# (?<fake>b)\n(?<word>a)").replace("xaya", "[${word}]") == "x[a]y[a]"
    assert regex_replace("(a)(b)", "xabz", "$0-$2$1") == "xab-baz"


def test_regex_limits_configurable():  # S
    regex = UnicodeRegex("a", time_limit=None, stack_limit=None)
    assert regex.search("a")
    with pytest.raises(ValueError, match="time_limit must be a positive int or None"):
        UnicodeRegex("a", time_limit=0)
    with pytest.raises(ValueError, match="stack_limit must be a positive int or None"):
        UnicodeRegex("a", stack_limit=True)

    with pytest.raises(RegexLimitError) as caught:
        regex_search("(a+)+$", "a" * 65_536 + "b", time_limit=100)
    assert (caught.value.limit, caught.value.value, caught.value.pattern) == (
        "time",
        100,
        "(a+)+$",
    )


def test_regex_convenience_limits_reach_split_and_replace():  # S
    text = "a" * 65_536 + "b"
    with pytest.raises(RegexLimitError):
        regex_split("(a+)+$", text, time_limit=100)
    with pytest.raises(RegexLimitError):
        regex_replace("(a+)+$", text, "x", time_limit=100)
