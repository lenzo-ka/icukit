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

__all__ = [
    "DATE_TIME_SKELETON_FAMILY",
    "DEFAULT_FAMILIES",
    "Family",
    "GenerationReport",
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

# note: Number-style, RBNF, compact, scientific, measure, relative, and interval
# families belong here once their ICU surfaces have introspective inverters.
DEFAULT_FAMILIES = (DATE_TIME_SKELETON_FAMILY,)


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
