"""A four-digit number read in a numeric date is its year, never its month or day.

This covers generated default readers, unguarded flexible readers alone, and generated
default readers combined with guarded flexible readers. Date readings expose field
captures at absolute source offsets. Date-interval readings instead expose absolute
``start``, ``separator``, and ``end`` side captures, so each year is tied to the value
of the side containing it. No month or day capture may cover a four-digit run.

Textual-month, weekday, and era patterns are out of scope.
"""

from functools import cache

import icu
import pytest

from icukit import DateIntervalValue, flexible_detectors, generated_detectors

LOCALES = ("en_US", "en_GB", "de_DE")
DATE_SKELETONS = ("yMd", "yM", "yMMdd")
INTERVAL_SKELETON = "y"

# This is the intended contract, not a list inferred from the readers that happen to
# exist. ``yMMdd`` applies only where ICU gives it a pattern distinct from ``yMd`` and
# ``yM``. All three configurations are intended to read ICU's numeric date shapes and
# its year interval shape.
EXPECTED_ICU_COVERAGE = {
    "default": {"dates": DATE_SKELETONS, "intervals": (INTERVAL_SKELETON,)},
    "flexible": {"dates": DATE_SKELETONS, "intervals": (INTERVAL_SKELETON,)},
    "flexible-guarded": {"dates": DATE_SKELETONS, "intervals": (INTERVAL_SKELETON,)},
}

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


def _calendar(locale: str, year: int, month: int, day: int):
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
    calendar.clear()
    calendar.set(year, month - 1, day, 12, 0, 0)
    return calendar


@cache
def _icu_date_cases(locale: str) -> tuple[tuple[str, str, str], ...]:
    """Return fixed-skeleton ICU patterns and texts, independently of icukit readers."""
    generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(locale))
    instant = _calendar(locale, 1918, 12, 9).getTime()
    cases = []
    patterns = set()
    for skeleton in DATE_SKELETONS:
        pattern = generator.getBestPattern(skeleton)
        if skeleton == "yMMdd" and pattern in patterns:
            continue
        formatter = icu.SimpleDateFormat(pattern, icu.Locale(locale))
        formatter.setTimeZone(icu.TimeZone.getGMT())
        cases.append((skeleton, pattern, formatter.format(instant)))
        patterns.add(pattern)
    return tuple(cases)


@cache
def _icu_interval_text(locale: str) -> str:
    start = _calendar(locale, 1914, 7, 1).getTime()
    end = _calendar(locale, 1918, 7, 1).getTime()
    formatter = icu.DateIntervalFormat.createInstance(INTERVAL_SKELETON, icu.Locale(locale))
    return formatter.format(icu.DateInterval(start, end))


TEXTS = tuple(
    dict.fromkeys(
        (
            *FIXTURE_TEXTS,
            *(text for locale in LOCALES for _, _, text in _icu_date_cases(locale)),
            *(_icu_interval_text(locale) for locale in LOCALES),
        )
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


def _date_coverage_cases():
    cases = []
    for locale in LOCALES:
        for kind, coverage in EXPECTED_ICU_COVERAGE.items():
            for skeleton, pattern, text in _icu_date_cases(locale):
                if skeleton not in coverage["dates"]:
                    continue
                marks = []
                if kind == "flexible" and skeleton == "yM":
                    marks.append(
                        pytest.mark.xfail(
                            strict=True,
                            reason="unguarded flexible readers do not yet read ICU's yM text",
                        )
                    )
                cases.append(
                    pytest.param(
                        locale,
                        kind,
                        skeleton,
                        pattern,
                        text,
                        marks=marks,
                        id=f"{locale}-{kind}-{skeleton}",
                    )
                )
    return cases


def _interval_coverage_cases():
    return [
        pytest.param(locale, kind, id=f"{locale}-{kind}-{INTERVAL_SKELETON}")
        for locale in LOCALES
        for kind, coverage in EXPECTED_ICU_COVERAGE.items()
        if INTERVAL_SKELETON in coverage["intervals"]
    ]


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
    runs = _four_digit_runs(text)
    for found in _reader_set(locale, kind).detect(text):
        if not found["type"].startswith("date"):
            continue
        start, end = found["start"], found["end"]
        for run_start, run_end in runs:
            if run_end <= start or run_start >= end:
                continue
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


@pytest.mark.parametrize(("locale", "kind", "skeleton", "pattern", "text"), _date_coverage_cases())
def test_each_configuration_reads_its_expected_icu_date_whole(
    locale, kind, skeleton, pattern, text
):
    whole_dates = [
        found
        for found in _reader_set(locale, kind).detect(text)
        if found["type"].startswith("date")
        and not isinstance(found["value"], DateIntervalValue)
        and (found["start"], found["end"]) == (0, len(text))
    ]

    assert whole_dates, (locale, kind, skeleton, pattern, text)


@pytest.mark.parametrize(("locale", "kind"), _interval_coverage_cases())
def test_each_interval_configuration_reads_icus_year_interval_whole(locale, kind):
    text = _icu_interval_text(locale)
    witnesses = [
        found
        for found in _reader_set(locale, kind).detect(text)
        if isinstance(found["value"], DateIntervalValue)
        and (found["start"], found["end"]) == (0, len(text))
    ]

    assert witnesses, (locale, kind, INTERVAL_SKELETON, text)
    found = witnesses[0]
    value = found["value"]
    assert dict(value.start.fields)["y"] == 1914
    assert dict(value.end.fields)["y"] == 1918

    starts = [capture for capture in found["captures"] if capture.name == "start"]
    ends = [capture for capture in found["captures"] if capture.name == "end"]
    assert len(starts) == len(ends) == 1
    start_side, end_side = starts[0], ends[0]
    assert start_side.end <= end_side.start

    runs = {int(text[start:end]): (start, end) for start, end in _four_digit_runs(text)}
    assert start_side.start <= runs[1914][0] and runs[1914][1] <= start_side.end
    assert end_side.start <= runs[1918][0] and runs[1918][1] <= end_side.end
