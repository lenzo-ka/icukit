"""Introspect ICU formatter surfaces and derive gangs of inverting detectors.

Each :class:`Family` enumerates formatter specifications from ICU and attempts to
construct one detector per specification.  Unsupported specifications are observable in
the generation report, rather than making generation fail or silently narrowing the
enumerated surface.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import icu

from .detectors import DateDetector, Detector, DetectorSet
from .recognize import FlexibleCompactDetector, FlexibleScientificDetector

__all__ = [
    "COMPACT_NUMBER_FAMILY",
    "DATE_TIME_SKELETON_FAMILY",
    "DEFAULT_FAMILIES",
    "Family",
    "GenerationReport",
    "SCIENTIFIC_NUMBER_FAMILY",
    "SkippedSpec",
    "generated_detectors",
    "generated_detectors_report",
]

Spec = object


@dataclass(frozen=True, repr=False)
class Family:
    """An introspective formatter family that can derive detectors for its specs."""

    name: str
    enumerate: Callable[[str], Iterable[Spec]]
    invert: Callable[[Spec, str], Detector | None]
    skip_reason: Callable[[Spec, str], str] | None = None

    def __repr__(self) -> str:
        return f"Family(name={self.name!r})"


@dataclass(frozen=True)
class SkippedSpec:
    """A formatter specification that its family could not invert."""

    family: str
    spec: Spec
    reason: str


@dataclass(frozen=True)
class GenerationReport:
    """Generated detectors together with every specification that was skipped."""

    detectors: DetectorSet
    skipped: tuple[SkippedSpec, ...]


def _date_time_skeletons(locale: str) -> Iterable[Spec]:
    generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(locale))
    return sorted(generator.getSkeletons())


def _date_time_invert(spec: Spec, locale: str) -> Detector | None:
    skeleton = str(spec)
    try:
        detector = DateDetector(locale, skeleton)
    except ValueError:
        return None
    return detector if detector.pattern else None


def _date_time_skip_reason(spec: Spec, locale: str) -> str:
    try:
        detector = DateDetector(locale, str(spec))
    except ValueError as error:
        return str(error)
    if not detector.pattern:
        return "ICU returned an empty best pattern"
    return "date/time skeleton was not invertible"


DATE_TIME_SKELETON_FAMILY = Family(
    "date-time-skeleton",
    _date_time_skeletons,
    _date_time_invert,
    _date_time_skip_reason,
)


def _compact_widths(locale: str) -> Iterable[Spec]:
    del locale
    return sorted(
        name.lower()
        for name in dir(icu.UNumberCompactStyle)
        if not name.startswith("_") and isinstance(getattr(icu.UNumberCompactStyle, name), int)
    )


def _compact_invert(spec: Spec, locale: str) -> Detector | None:
    try:
        detector = FlexibleCompactDetector(locale, str(spec))
    except ValueError:
        return None
    return detector if detector.has_affixes else None


def _compact_skip_reason(spec: Spec, locale: str) -> str:
    try:
        detector = FlexibleCompactDetector(locale, str(spec))
    except ValueError as error:
        return str(error)
    if not detector.has_affixes:
        return "ICU exposed no exactly invertible compact affixes"
    return "compact width was not invertible"


COMPACT_NUMBER_FAMILY = Family(
    "compact-number",
    _compact_widths,
    _compact_invert,
    _compact_skip_reason,
)

_SCIENTIFIC_STYLES = ("scientific",)


def _scientific_styles(locale: str) -> Iterable[Spec]:
    del locale
    return _SCIENTIFIC_STYLES


def _scientific_invert(spec: Spec, locale: str) -> Detector | None:
    try:
        detector = FlexibleScientificDetector(locale)
    except ValueError:
        return None
    return detector


def _scientific_skip_reason(spec: Spec, locale: str) -> str:
    try:
        FlexibleScientificDetector(locale)
    except ValueError as error:
        return str(error)
    return "scientific style was not invertible"


SCIENTIFIC_NUMBER_FAMILY = Family(
    "scientific-number",
    _scientific_styles,
    _scientific_invert,
    _scientific_skip_reason,
)

# note: Number-style, RBNF, measure, relative, and interval
# families belong here once their ICU surfaces have introspective inverters.
DEFAULT_FAMILIES = (
    DATE_TIME_SKELETON_FAMILY,
    COMPACT_NUMBER_FAMILY,
    SCIENTIFIC_NUMBER_FAMILY,
)


def generated_detectors_report(
    locale: str, families: Iterable[Family] = DEFAULT_FAMILIES
) -> GenerationReport:
    """Derive detectors for ``locale`` and report specs that could not be inverted."""
    detectors = DetectorSet(())
    skipped: list[SkippedSpec] = []
    for family in families:
        for spec in family.enumerate(locale):
            detector = family.invert(spec, locale)
            if detector is not None:
                detectors = detectors.with_(detector)
                continue
            reason = (
                family.skip_reason(spec, locale)
                if family.skip_reason is not None
                else "family returned no inverter"
            )
            skipped.append(SkippedSpec(family.name, spec, reason))
    return GenerationReport(detectors, tuple(skipped))


def generated_detectors(locale: str, families: Iterable[Family] = DEFAULT_FAMILIES) -> DetectorSet:
    """Derive all invertible detectors introspectively registered for ``locale``."""
    return generated_detectors_report(locale, families).detectors


# note: Flexible recall detectors do not yet generalize to partial date skeletons; that
# is a separate follow-on from exact formatter-surface generation.
