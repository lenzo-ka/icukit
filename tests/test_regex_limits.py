"""ICU regex resource limits and stateful-loop semantics."""

import json
import subprocess
import sys

import pytest

from icukit import (
    PatternError,
    RegexLimitError,
    UnicodeRegex,
    regex_replace,
    regex_search,
    regex_split,
)


@pytest.mark.parametrize(
    "operation",
    [
        "find_all",
        "search",
        "split",
        "replace",
        "regex_detect",
        "stateful_find_all",
    ],
)
def test_regex_catastrophic_raises(operation):  # R
    script = r"""
import json
import sys
import time
from icukit import PatternError, UnicodeRegex, regex_detect

operation = sys.argv[1]
pattern = r"\G(?:x|(a+)+$)" if operation == "stateful_find_all" else "(a+)+$"
text = ("x" if operation == "stateful_find_all" else "") + "a" * 65_536 + "b"
regex = UnicodeRegex(pattern)
operations = {
    "find_all": lambda: regex.find_all(text),
    "search": lambda: regex.search(text),
    "split": lambda: regex.split(text),
    "replace": lambda: regex.replace(text, "x"),
    "regex_detect": lambda: regex_detect(text, pattern, "test"),
    "stateful_find_all": lambda: regex.find_all(text),
}
started = time.perf_counter()
try:
    operations[operation]()
except PatternError as exc:
    result = {
        "type": type(exc).__name__,
        "message": str(exc),
        "cause": None if exc.__cause__ is None else type(exc.__cause__).__name__,
        "elapsed": time.perf_counter() - started,
    }
else:
    result = {"type": None, "elapsed": time.perf_counter() - started}
print(json.dumps(result))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, operation],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    result = json.loads(completed.stdout)

    assert result["type"] == "RegexLimitError"
    assert result["elapsed"] < 5
    if operation != "stateful_find_all":
        assert result["message"] == "regex exceeded its time limit of 10000 steps: '(a+)+$'"
        assert result["cause"] is None


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
    script = """
import json
import time
from icukit import RegexLimitError
from icukit.cli.locale_helpers import parse_multi_value

started = time.perf_counter()
try:
    parse_multi_value("(a|aa)+$", available_values=["a" * 48 + "b"])
except RegexLimitError as exc:
    result = {"type": type(exc).__name__, "elapsed": time.perf_counter() - started}
else:
    result = {"type": None, "elapsed": time.perf_counter() - started}
print(json.dumps(result))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    result = json.loads(completed.stdout)

    assert result["type"] == "RegexLimitError"
    assert result["elapsed"] < 5


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
