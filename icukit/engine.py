"""Introspect ICU surfaces and inventories to derive gangs of detectors.

Each :class:`Family` enumerates specifications from ICU or a packaged typed inventory and
attempts to construct one detector per specification. Unsupported specifications are
observable in the generation report, rather than making generation fail or silently
narrowing the enumerated surface. The abbreviation family is inventory-driven because
expansion is intentionally not an invertible formatter operation.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import icu

from .detectors import DateDetector, Detector, DetectorSet
from .recognize import (
    FlexibleCompactDetector,
    FlexibleDateIntervalDetector,
    FlexibleRelativeDateDetector,
    FlexibleScientificDetector,
    FlexibleSpelloutDetector,
    _spellout_formatter_and_ruleset,
)

__all__ = [
    "ABBREVIATION_FAMILY",
    "COMPACT_NUMBER_FAMILY",
    "DATE_INTERVAL_FAMILY",
    "DATE_TIME_SKELETON_FAMILY",
    "DEFAULT_FAMILIES",
    "Family",
    "GenerationReport",
    "RELATIVE_DATE_FAMILY",
    "SCIENTIFIC_NUMBER_FAMILY",
    "SPELLOUT_NUMBER_FAMILY",
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


def _abbreviation_specs(locale: str) -> Iterable[Spec]:
    from .abbreviation_compile import compile_lexicon

    compiled = compile_lexicon(locale)
    return () if compiled is None else (compiled.lexicon.language,)


def _abbreviation_invert(spec: Spec, locale: str) -> Detector | None:
    del spec
    from .abbreviation_recognize import AbbreviationDetector

    detector = AbbreviationDetector(locale)
    return detector if detector.compiled is not None else None


def _abbreviation_skip_reason(spec: Spec, locale: str) -> str:
    del spec
    return f"no abbreviation lexicon ships for locale {locale!r}"


ABBREVIATION_FAMILY = Family(
    "abbreviation", _abbreviation_specs, _abbreviation_invert, _abbreviation_skip_reason
)


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


def _date_interval_skeletons(locale: str) -> Iterable[Spec]:
    generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(locale))
    return sorted(generator.getSkeletons())


def _date_interval_invert(spec: Spec, locale: str) -> Detector | None:
    skeleton = str(spec)
    try:
        detector = FlexibleDateIntervalDetector(locale, skeleton)
    except (icu.ICUError, ValueError):
        return None
    return detector if detector.has_patterns else None


def _date_interval_skip_reason(spec: Spec, locale: str) -> str:
    del locale
    return f"no invertible interval pattern for skeleton {str(spec)!r}"


DATE_INTERVAL_FAMILY = Family(
    "date-interval",
    _date_interval_skeletons,
    _date_interval_invert,
    _date_interval_skip_reason,
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


def _spellout_rulesets(locale: str) -> Iterable[Spec]:
    try:
        _, ruleset = _spellout_formatter_and_ruleset(locale)
    except (icu.ICUError, ValueError):
        return ()
    return (ruleset,)


def _spellout_invert(spec: Spec, locale: str) -> Detector | None:
    try:
        detector = FlexibleSpelloutDetector(locale)
    except (icu.ICUError, ValueError):
        return None
    return detector if detector._ruleset == str(spec) else None


def _spellout_skip_reason(spec: Spec, locale: str) -> str:
    try:
        detector = FlexibleSpelloutDetector(locale)
    except (icu.ICUError, ValueError) as error:
        return str(error)
    if detector._ruleset != str(spec):
        return "ICU selected a different cardinal spellout rule set"
    return "spellout rule set was not invertible"


SPELLOUT_NUMBER_FAMILY = Family(
    "spellout-number",
    _spellout_rulesets,
    _spellout_invert,
    _spellout_skip_reason,
)


# Relative-date specs expose the reachable unit inventory; DetectorSet intentionally
# deduplicates the identical detector generated for each unit.
def _relative_date_units(locale: str) -> Iterable[Spec]:
    try:
        detector = FlexibleRelativeDateDetector(locale)
    except (icu.ICUError, ValueError):
        return ()
    return detector.reachable_units


def _relative_date_invert(spec: Spec, locale: str) -> Detector | None:
    try:
        detector = FlexibleRelativeDateDetector(locale)
    except (icu.ICUError, ValueError):
        return None
    return detector if detector.has_vocabulary and str(spec) in detector.reachable_units else None


def _relative_date_skip_reason(spec: Spec, locale: str) -> str:
    try:
        detector = FlexibleRelativeDateDetector(locale)
    except (icu.ICUError, ValueError) as error:
        return str(error)
    if not detector.has_vocabulary:
        return "ICU exposed no invertible relative-date phrases"
    if str(spec) not in detector.reachable_units:
        return f"ICU exposed no invertible relative-date phrase for unit {spec!r}"
    return "relative-date unit was not invertible"


RELATIVE_DATE_FAMILY = Family(
    "relative-date",
    _relative_date_units,
    _relative_date_invert,
    _relative_date_skip_reason,
)

# note: A measure family belongs here once its ICU surfaces have an introspective
# inverter. Abbreviations use their typed lexicon.
DEFAULT_FAMILIES = (
    ABBREVIATION_FAMILY,
    DATE_TIME_SKELETON_FAMILY,
    DATE_INTERVAL_FAMILY,
    COMPACT_NUMBER_FAMILY,
    RELATIVE_DATE_FAMILY,
    SCIENTIFIC_NUMBER_FAMILY,
    SPELLOUT_NUMBER_FAMILY,
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
