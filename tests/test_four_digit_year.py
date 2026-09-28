"""A four-digit number read in a date is its year, never its month or day.

This covers generated default readers, unguarded flexible readers alone, and generated
default readers combined with guarded flexible readers. Date readings expose field
captures at absolute source offsets. Date-interval readings instead expose absolute
``start``, ``separator``, and ``end`` side captures, so each year is tied to the value
of the side containing it. No month or day capture may cover a four-digit run.
"""

from functools import cache

import icu
import pytest

from icukit import DateIntervalValue, flexible_detectors, generated_detectors
from icukit.detectors import DateDetector
from icukit.recognize import FlexibleDateDetector, FlexibleDateIntervalDetector

LOCALES = ("en_US", "en_GB", "de_DE")
FIXTURE_TEXTS = (
    "12/1918",
    "1918/12",
    "2008-09-30",
    "2008/09/10",
    "09/10/2008",
    "1914–1918",
    "2024-03",
    "1918.12",
)
YEAR_FIELDS = frozenset({"y", "Y", "u", "r", "U"})
DAY_OR_MONTH = frozenset({"M", "L", "d"})


def _pattern_runs(pattern: str) -> tuple[tuple[str, int], ...]:
    """Return ICU pattern-letter runs, ignoring quoted literals."""
    runs, index, quoted = [], 0, False
    while index < len(pattern):
        if pattern[index] == "'":
            if index + 1 < len(pattern) and pattern[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
            index += 1
            continue
        if quoted or not pattern[index].isalpha():
            index += 1
            continue
        end = index + 1
        while end < len(pattern) and pattern[end] == pattern[index]:
            end += 1
        runs.append((pattern[index], end - index))
        index = end
    return tuple(runs)


def _calendar(locale: str, year: int, month: int, day: int):
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
    calendar.clear()
    calendar.set(year, month - 1, day, 12, 0, 0)
    return calendar


def _numeric_year_pattern(pattern: str) -> bool:
    runs = _pattern_runs(pattern)
    return any(letter == "y" and width != 2 for letter, width in runs) and not any(
        letter in {"G", "E", "e", "c"} or (letter in {"M", "L"} and width >= 3)
        for letter, width in runs
    )


@cache
def _generated_date_texts(locale: str) -> tuple[str, ...]:
    instant = _calendar(locale, 1918, 12, 9).getTime()
    texts = []
    for detector in generated_detectors(locale).detectors:
        if not isinstance(detector, DateDetector) or not _numeric_year_pattern(detector.pattern):
            continue
        formatter = icu.SimpleDateFormat(detector.pattern, icu.Locale(locale))
        formatter.setTimeZone(icu.TimeZone.getGMT())
        texts.append(formatter.format(instant))
    return tuple(dict.fromkeys(texts))


TEXTS = tuple(
    dict.fromkeys(
        (*FIXTURE_TEXTS, *(text for locale in LOCALES for text in _generated_date_texts(locale)))
    )
)


@cache
def _reader_set(locale: str, kind: str):
    if kind == "flexible":
        return flexible_detectors(locale, guarded=False)
    gang = generated_detectors(locale)
    if kind == "flexible-guarded":
        gang = gang.with_(*flexible_detectors(locale, guarded=True).detectors)
    return gang


def _icu_date_round_trips(locale: str, pattern: str, text: str) -> bool:
    formatter = icu.SimpleDateFormat(pattern, icu.Locale(locale))
    formatter.setTimeZone(icu.TimeZone.getGMT())
    formatter.setLenient(False)
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
    calendar.clear()
    source = icu.UnicodeString(text)
    position = icu.ParsePosition(0)
    formatter.parse(source, calendar, position)
    return (
        position.getErrorIndex() == -1
        and position.getIndex() == source.length()
        and formatter.format(calendar.getTime()) == text
    )


@cache
def _icu_interval_texts(locale: str, skeletons: tuple[str, ...]) -> frozenset[str]:
    start = _calendar(locale, 1914, 7, 1).getTime()
    end = _calendar(locale, 1918, 7, 1).getTime()
    texts = set()
    for skeleton in skeletons:
        formatter = icu.DateIntervalFormat.createInstance(skeleton, icu.Locale(locale))
        texts.add(formatter.format(icu.DateInterval(start, end)))
    return frozenset(texts)


@cache
def _must_read_texts(locale: str, kind: str) -> frozenset[str]:
    # The bare flexible set does not contain the generated set, so its obligation is
    # derived independently from the ICU patterns and skeletons its own readers expose.
    detectors = _reader_set(locale, kind).detectors
    if kind == "flexible-guarded":
        detectors = generated_detectors(locale).detectors
    patterns = {
        detector.pattern
        for detector in detectors
        if isinstance(detector, (DateDetector, FlexibleDateDetector))
    }
    skeletons = tuple(
        dict.fromkeys(
            detector.skeleton
            for detector in detectors
            if isinstance(detector, FlexibleDateIntervalDetector)
        )
    )
    interval_texts = _icu_interval_texts(locale, skeletons)
    return frozenset(
        text
        for text in TEXTS
        if text in interval_texts
        or any(_icu_date_round_trips(locale, pattern, text) for pattern in patterns)
    )


def _four_digit_runs(text: str) -> list[tuple[int, int]]:
    runs, index = [], 0
    while index < len(text):
        if icu.Char.isdigit(text[index]):
            end = index
            while end < len(text) and icu.Char.isdigit(text[end]):
                end += 1
            if end - index == 4:
                runs.append((index, end))
            index = end
        else:
            index += 1
    return runs


def _years(value) -> set[int]:
    values = (value.start, value.end) if isinstance(value, DateIntervalValue) else (value,)
    return {number for v in values for name, number in v.fields if name in YEAR_FIELDS}


def _year_values(value) -> set[int]:
    return {number for name, number in value.fields if name in YEAR_FIELDS}


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("kind", ["default", "flexible", "flexible-guarded"])
@pytest.mark.parametrize("locale", LOCALES)
def test_a_four_digit_number_is_only_ever_the_year(locale, kind, text):
    read = False
    runs = _four_digit_runs(text)
    for found in _reader_set(locale, kind).detect(text):
        if not found["type"].startswith("date"):
            continue
        start, end = found["start"], found["end"]
        for run_start, run_end in runs:
            if run_end <= start or run_start >= end:
                continue
            read = True
            number = int(text[run_start:run_end])
            where = (locale, kind, text, found["type"], found["text"])
            assert start <= run_start and run_end <= end, where
            assert number in _years(found["value"]), where

            captures = found["captures"]
            if isinstance(found["value"], DateIntervalValue):
                sides = [
                    capture
                    for capture in captures
                    if capture.name in {"start", "end"}
                    and capture.start <= run_start
                    and run_end <= capture.end
                ]
                assert len(sides) == 1, where
                side = sides[0]
                assert all(
                    capture.name != "separator"
                    or capture.end <= run_start
                    or capture.start >= run_end
                    for capture in captures
                ), where
                value = found["value"].start if side.name == "start" else found["value"].end
                assert number in _year_values(value), where
            else:
                assert any(
                    capture.name in YEAR_FIELDS
                    and (capture.start, capture.end) == (run_start, run_end)
                    for capture in captures
                ), where

            for capture in captures:
                if capture.name in DAY_OR_MONTH:
                    assert capture.end <= run_start or capture.start >= run_end, where

    if text in _must_read_texts(locale, kind):
        assert read, (locale, kind, text)
