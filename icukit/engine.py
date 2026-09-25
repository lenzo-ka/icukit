"""Introspect ICU surfaces and inventories to derive gangs of detectors.

Each :class:`Family` enumerates specifications from ICU or a packaged typed inventory and
attempts to construct one detector per specification. Unsupported specifications are
observable in the generation report, rather than making generation fail or silently
narrowing the enumerated surface. The abbreviation family is inventory-driven because
expansion is intentionally not an invertible formatter operation.

:data:`DEFAULT_FAMILIES` is the default gang. :data:`GUARDED_FAMILIES` generates the
readers of the readings the default readers refuse on purpose -- a lone "one" or
"first", a lowercase Roman numeral, a month or weekday name alone, a bare hour, a date
with a two- or three-digit year -- each under its own type, so a consumer that wants
every path (a lattice for forced alignment) opts in with
``generated_detectors(locale, (*DEFAULT_FAMILIES, *GUARDED_FAMILIES))`` or adds one
reader to a gang with ``DetectorSet.with_``, and one that does not leaves them out.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import icu

from .detectors import DateDetector, Detector, DetectorSet
from .recognize import (
    FlexibleBareHourDetector,
    FlexibleCompactDetector,
    FlexibleDateIntervalDetector,
    FlexibleLoneSpelloutDetector,
    FlexibleLowercaseRomanDetector,
    FlexibleMonthNameDetector,
    FlexibleRelativeDateDetector,
    FlexibleScientificDetector,
    FlexibleShortYearDateDetector,
    FlexibleSpelloutDetector,
    FlexibleWeekdayNameDetector,
    _spellout_formatter_and_ruleset,
)
from .recognize import (
    _spellout_rulesets as _spellout_rulesets_of,
)

__all__ = [
    "ABBREVIATION_FAMILY",
    "BARE_HOUR_FAMILY",
    "COMPACT_NUMBER_FAMILY",
    "DATE_INTERVAL_FAMILY",
    "DATE_TIME_SKELETON_FAMILY",
    "DEFAULT_FAMILIES",
    "Family",
    "GUARDED_FAMILIES",
    "GenerationReport",
    "LONE_SPELLOUT_NUMBER_FAMILY",
    "LOWERCASE_ROMAN_FAMILY",
    "MONTH_NAME_FAMILY",
    "RELATIVE_DATE_FAMILY",
    "SCIENTIFIC_NUMBER_FAMILY",
    "SHORT_YEAR_FAMILY",
    "SPELLOUT_NUMBER_FAMILY",
    "WEEKDAY_NAME_FAMILY",
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


@dataclass(frozen=True)
class _Probe:
    detector: Detector | None
    reason: str = ""


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
    return _date_time_probe(spec, locale).detector


def _date_time_probe(spec: Spec, locale: str) -> _Probe:
    skeleton = str(spec)
    try:
        detector = DateDetector(locale, skeleton)
    except ValueError as error:
        return _Probe(None, str(error))
    if not detector.pattern:
        return _Probe(None, "ICU returned an empty best pattern")
    return _Probe(detector)


def _date_time_skip_reason(spec: Spec, locale: str) -> str:
    return _date_time_probe(spec, locale).reason or "date/time skeleton was not invertible"


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
    return _date_interval_probe(spec, locale).detector


def _date_interval_probe(spec: Spec, locale: str) -> _Probe:
    skeleton = str(spec)
    try:
        detector = FlexibleDateIntervalDetector(locale, skeleton)
    except (icu.ICUError, ValueError):
        return _Probe(None, f"no invertible interval pattern for skeleton {skeleton!r}")
    if not detector.has_patterns:
        return _Probe(None, f"no invertible interval pattern for skeleton {skeleton!r}")
    return _Probe(detector)


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
    return _compact_probe(spec, locale).detector


def _compact_probe(spec: Spec, locale: str) -> _Probe:
    try:
        detector = FlexibleCompactDetector(locale, str(spec))
    except ValueError as error:
        return _Probe(None, str(error))
    if not detector.has_affixes:
        return _Probe(None, "ICU exposed no exactly invertible compact affixes")
    return _Probe(detector)


def _compact_skip_reason(spec: Spec, locale: str) -> str:
    return _compact_probe(spec, locale).reason or "compact width was not invertible"


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
    return _scientific_probe(spec, locale).detector


def _scientific_probe(spec: Spec, locale: str) -> _Probe:
    del spec
    try:
        detector = FlexibleScientificDetector(locale)
    except ValueError as error:
        return _Probe(None, str(error))
    return _Probe(detector)


def _scientific_skip_reason(spec: Spec, locale: str) -> str:
    return _scientific_probe(spec, locale).reason or "scientific style was not invertible"


SCIENTIFIC_NUMBER_FAMILY = Family(
    "scientific-number",
    _scientific_styles,
    _scientific_invert,
    _scientific_skip_reason,
)


def _spellout_rulesets(locale: str) -> Iterable[Spec]:
    try:
        _, default = _spellout_formatter_and_ruleset(locale)
        rulesets = _spellout_rulesets_of(locale)
    except (icu.ICUError, ValueError):
        return ()
    return (default, *(ruleset for ruleset in rulesets if ruleset != default))


def _spellout_invert(spec: Spec, locale: str) -> Detector | None:
    return _spellout_probe(spec, locale).detector


def _spellout_probe(spec: Spec, locale: str) -> _Probe:
    try:
        detector = FlexibleSpelloutDetector(locale, ruleset=str(spec))
    except (icu.ICUError, ValueError) as error:
        return _Probe(None, str(error))
    if detector._ruleset != str(spec):
        return _Probe(None, "ICU selected a different spellout rule set")
    return _Probe(detector)


def _spellout_skip_reason(spec: Spec, locale: str) -> str:
    return _spellout_probe(spec, locale).reason or "spellout rule set was not invertible"


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
    return _relative_date_probe(spec, locale).detector


def _relative_date_probe(spec: Spec, locale: str) -> _Probe:
    try:
        detector = FlexibleRelativeDateDetector(locale)
    except (icu.ICUError, ValueError) as error:
        return _Probe(None, str(error))
    if not detector.has_vocabulary:
        return _Probe(None, "ICU exposed no invertible relative-date phrases")
    if str(spec) not in detector.reachable_units:
        return _Probe(None, f"ICU exposed no invertible relative-date phrase for unit {spec!r}")
    return _Probe(detector)


def _relative_date_skip_reason(spec: Spec, locale: str) -> str:
    return _relative_date_probe(spec, locale).reason or "relative-date unit was not invertible"


RELATIVE_DATE_FAMILY = Family(
    "relative-date",
    _relative_date_units,
    _relative_date_invert,
    _relative_date_skip_reason,
)


def _lone_spellout_invert(spec: Spec, locale: str) -> Detector | None:
    return _lone_spellout_probe(spec, locale).detector


def _lone_spellout_probe(spec: Spec, locale: str) -> _Probe:
    try:
        detector = FlexibleLoneSpelloutDetector(locale, ruleset=str(spec))
    except (icu.ICUError, ValueError) as error:
        return _Probe(None, str(error))
    if detector._ruleset != str(spec):
        return _Probe(None, "ICU selected a different spellout rule set")
    return _Probe(detector)


def _lone_spellout_skip_reason(spec: Spec, locale: str) -> str:
    return _lone_spellout_probe(spec, locale).reason or "spellout rule set was not invertible"


LONE_SPELLOUT_NUMBER_FAMILY = Family(
    "spellout-lone",
    _spellout_rulesets,
    _lone_spellout_invert,
    _lone_spellout_skip_reason,
)


def _guarded_family(
    name: str, build: Callable[[str], Detector], available: Callable[[Detector], bool], why: str
) -> Family:
    """A family of one reader per locale, skipped where ``available`` says ICU has none."""

    def probe(locale: str) -> _Probe:
        try:
            detector = build(locale)
        except (icu.ICUError, ValueError) as error:
            return _Probe(None, str(error))
        return _Probe(detector) if available(detector) else _Probe(None, why)

    def invert(spec: Spec, locale: str) -> Detector | None:
        del spec
        return probe(locale).detector

    def skip_reason(spec: Spec, locale: str) -> str:
        del spec
        return probe(locale).reason or why

    return Family(name, lambda locale: (name,), invert, skip_reason)


LOWERCASE_ROMAN_FAMILY = _guarded_family(
    "roman-lower",
    FlexibleLowercaseRomanDetector,
    lambda detector: detector.has_rule_sets,
    "ICU gives the locale no lowercase Roman rule set",
)

MONTH_NAME_FAMILY = _guarded_family(
    "month-name",
    FlexibleMonthNameDetector,
    lambda detector: detector.has_names,
    "ICU gives the locale's language no month names",
)

WEEKDAY_NAME_FAMILY = _guarded_family(
    "weekday-name",
    FlexibleWeekdayNameDetector,
    lambda detector: detector.has_names,
    "ICU gives the locale's language no weekday names",
)

BARE_HOUR_FAMILY = _guarded_family(
    "bare-hour",
    FlexibleBareHourDetector,
    lambda detector: detector.letter is not None,
    "ICU's best pattern for the j skeleton has no hour field",
)

SHORT_YEAR_FAMILY = _guarded_family(
    "short-year",
    FlexibleShortYearDateDetector,
    lambda detector: detector.has_year_patterns,
    "the locale's textual date patterns write no year",
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

# The readings the default readers refuse on purpose, each under its own type; not in
# DEFAULT_FAMILIES, so a consumer opts in (see the module docstring).
GUARDED_FAMILIES = (
    LONE_SPELLOUT_NUMBER_FAMILY,
    LOWERCASE_ROMAN_FAMILY,
    MONTH_NAME_FAMILY,
    WEEKDAY_NAME_FAMILY,
    SHORT_YEAR_FAMILY,
    BARE_HOUR_FAMILY,
)

_FAMILY_PROBES = (
    (DATE_TIME_SKELETON_FAMILY, _date_time_probe),
    (DATE_INTERVAL_FAMILY, _date_interval_probe),
    (COMPACT_NUMBER_FAMILY, _compact_probe),
    (RELATIVE_DATE_FAMILY, _relative_date_probe),
    (SCIENTIFIC_NUMBER_FAMILY, _scientific_probe),
    (SPELLOUT_NUMBER_FAMILY, _spellout_probe),
    (LONE_SPELLOUT_NUMBER_FAMILY, _lone_spellout_probe),
)


def generated_detectors_report(
    locale: str, families: Iterable[Family] = DEFAULT_FAMILIES
) -> GenerationReport:
    """Derive detectors for ``locale`` and report specs that could not be inverted."""
    detectors = DetectorSet(())
    skipped: list[SkippedSpec] = []
    for family in families:
        for spec in family.enumerate(locale):
            probe_function = next(
                (probe for known_family, probe in _FAMILY_PROBES if family is known_family), None
            )
            probe = probe_function(spec, locale) if probe_function is not None else None
            detector = probe.detector if probe is not None else family.invert(spec, locale)
            if detector is not None:
                detectors = detectors.with_(detector)
                continue
            reason = probe.reason if probe is not None else ""
            if not reason:
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
