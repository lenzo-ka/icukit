"""A detector's group is the first segment of its type."""

import inspect

import pytest

import icukit.recognize
from icukit.engine import DEFAULT_FAMILIES, GUARDED_FAMILIES, generated_detectors

LOCALES = ("en_US", "de_DE", "ja_JP")

# The flexible readers whose constructor needs more than a locale: a width, a currency, a
# skeleton, or a unit.
NEEDS_MORE_THAN_A_LOCALE = {
    "FlexibleCompactDetector",
    "FlexibleCurrencyDetector",
    "FlexibleCurrencyNameDetector",
    "FlexibleDateIntervalDetector",
    "FlexibleMeasureDetector",
    "FlexibleMixedMeasureDetector",
}


def _flexible_detector_classes():
    return [
        (name, cls)
        for name, cls in inspect.getmembers(icukit.recognize, inspect.isclass)
        if name.startswith("Flexible")
        and name.endswith("Detector")
        and cls.__module__ == icukit.recognize.__name__
    ]


def _needs_more_than_a_locale(cls):
    parameters = list(inspect.signature(cls).parameters.values())[1:]
    return any(
        parameter.default is inspect.Parameter.empty
        and parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for parameter in parameters
    )


@pytest.mark.parametrize("locale", LOCALES)
def test_every_generated_detector_types_within_its_group(locale):
    detectors = generated_detectors(locale, (*DEFAULT_FAMILIES, *GUARDED_FAMILIES)).detectors
    assert detectors
    mismatched = [
        (detector.type, detector.group)
        for detector in detectors
        if detector.type.split(":")[0] != detector.group
    ]
    assert mismatched == []


def test_the_readers_skipped_below_are_the_ones_needing_more_than_a_locale():
    skipped = {name for name, cls in _flexible_detector_classes() if _needs_more_than_a_locale(cls)}
    assert skipped == NEEDS_MORE_THAN_A_LOCALE


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize(
    "name, cls",
    [
        (name, cls)
        for name, cls in _flexible_detector_classes()
        if name not in NEEDS_MORE_THAN_A_LOCALE
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_every_locale_only_flexible_reader_types_within_its_group(locale, name, cls):
    detector = cls(locale)
    assert detector.type.split(":")[0] == detector.group, name
