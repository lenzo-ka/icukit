"""Introspect ICU surfaces and inventories to derive gangs of detectors.

Each :class:`Family` enumerates specifications from ICU or a packaged typed inventory and
attempts to construct one detector per specification. Unsupported specifications are
observable in the generation report, rather than making generation fail or silently
narrowing the enumerated surface. The abbreviation family is inventory-driven because
expansion is intentionally not an invertible formatter operation.

:data:`DEFAULT_FAMILIES` is the default gang. :data:`GUARDED_FAMILIES` generates the
readers of the readings the default readers refuse on purpose -- a lone "one" or
"first", a lowercase Roman numeral, a month or weekday name alone, a bare hour, a date
with a two- or three-digit year, a year range ICU never writes ("1914-1918",
"1893–94"), or a detached unit mark or one-letter abbreviation that ICU writes attached
(``84 \"`` beside ``84\"``, "62 d" beside "62d") -- each under its own type, so a
consumer that wants every path (a lattice for forced alignment) opts in with
``generated_detectors(locale, (*DEFAULT_FAMILIES, *GUARDED_FAMILIES))`` or adds one
reader to a gang with ``DetectorSet.with_``, and one that does not leaves them out.

:func:`flexible_detectors` assembles the flexible (recall) readers of
:mod:`icukit.recognize` for a locale, each reader that takes a parameter built for the
values it chooses from ICU; ``guarded=True`` adds the guarded readers.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache
from threading import Event, Lock, get_ident
from typing import cast

import icu

from .cache import _build_phase, cache_enabled
from .detectors import (
    DateDetector,
    Detector,
    DetectorSet,
    NumberDetector,
    date_detectors,
    number_detectors,
)
from .material import LocaleMaterial, _require_loaded, locale_descends_from
from .recognize import (
    AlphanumericRunsDetector,
    FlexibleBareHourDetector,
    FlexibleCompactDetector,
    FlexibleCurrencyDetector,
    FlexibleCurrencyNameDetector,
    FlexibleDateDetector,
    FlexibleDateIntervalDetector,
    FlexibleDateTimeDetector,
    FlexibleDetachedUnitDetector,
    FlexibleFractionDetector,
    FlexibleLoneSpelloutDetector,
    FlexibleLowercaseRomanDetector,
    FlexibleMeasureDetector,
    FlexibleMixedMeasureDetector,
    FlexibleMonthNameDetector,
    FlexibleNumberDetector,
    FlexibleNumberRangeDetector,
    FlexibleNumericDurationDetector,
    FlexibleOrdinalDetector,
    FlexiblePercentDetector,
    FlexibleRelativeDateDetector,
    FlexibleScientificDetector,
    FlexibleShortYearDateDetector,
    FlexibleSpelloutDetector,
    FlexibleTextDateDetector,
    FlexibleTimeDetector,
    FlexibleWeekdayNameDetector,
    LetterNameDetector,
    MaterialLoneSpelloutDetector,
    MaterialSpelloutDetector,
    PluralNumeralDetector,
    SingleLetterWordDetector,
    _clear_derived_locale_caches,
    _clear_shared_number_reader_cache,
    _iso_currency_codes,
    _language_locales,
    _locale_selection,
    _shared_number_reader,
    _spellout_formatter_and_ruleset,
)
from .recognize import (
    _spellout_rulesets as _spellout_rulesets_of,
)
from .unit_surfaces import curated_composed_units

__all__ = [
    "ABBREVIATION_FAMILY",
    "BARE_HOUR_FAMILY",
    "COMPACT_NUMBER_FAMILY",
    "DATE_INTERVAL_FAMILY",
    "DATE_TIME_SKELETON_FAMILY",
    "DEFAULT_FAMILIES",
    "DETACHED_UNIT_FAMILY",
    "Family",
    "GUARDED_FAMILIES",
    "GenerationReport",
    "LONE_SPELLOUT_NUMBER_FAMILY",
    "LOWERCASE_ROMAN_FAMILY",
    "MONTH_NAME_FAMILY",
    "RELATIVE_DATE_FAMILY",
    "SCIENTIFIC_NUMBER_FAMILY",
    "NUMBER_RANGE_FAMILY",
    "SHORT_YEAR_ERA_FAMILY",
    "SHORT_YEAR_FAMILY",
    "SHORT_YEAR_INTERVAL_FAMILY",
    "SPELLOUT_NUMBER_FAMILY",
    "WEEKDAY_NAME_FAMILY",
    "SkippedSpec",
    "clear_detector_caches",
    "flexible_detectors",
    "flexible_detectors_report",
    "generated_detectors",
    "generated_detectors_report",
    "range_detectors",
    "reader_set",
]

Spec = object


class _IdentityTuple:
    """A tuple key whose items compare by identity and stay alive with the key."""

    __slots__ = ("items", "_hash")

    def __init__(self, items: tuple[object, ...]) -> None:
        self.items = items
        self._hash = hash(tuple(map(id, items)))

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _IdentityTuple)
            and len(self.items) == len(other.items)
            and all(left is right for left, right in zip(self.items, other.items, strict=True))
        )


@dataclass
class _GangFlight:
    """One in-progress gang build whose waiters do not hold the memo lock."""

    event: Event
    generation: int
    thread: int
    result: object | None = None
    error: BaseException | None = None


class _GangMemo:
    """A bounded LRU with per-key single-flight construction."""

    def __init__(self, maxsize: int) -> None:
        self.maxsize = maxsize
        self._lock = Lock()
        self._cache: OrderedDict[tuple, object] = OrderedDict()
        self._flights: dict[tuple, _GangFlight] = {}
        self._generation = 0

    def get_or_build(self, key: tuple, build: Callable[[], object]) -> object:
        if not cache_enabled():
            return build()
        with self._lock:
            found = self._cache.pop(key, None)
            if found is not None:
                self._cache[key] = found
                return found
            flight = self._flights.get(key)
            owner = flight is None
            if owner:
                flight = _GangFlight(Event(), self._generation, get_ident())
                self._flights[key] = flight
        assert flight is not None
        if not owner and flight.thread == get_ident():
            # The same request, made again while this thread builds it (a family that
            # builds a gang as it enumerates): build it uncached, as waiting would
            # wait on this thread itself.
            return build()
        if not owner:
            flight.event.wait()
            if flight.error is not None:
                raise flight.error
            return flight.result
        try:
            result = build()
        except BaseException as error:
            with self._lock:
                flight.error = error
                if self._flights.get(key) is flight:
                    del self._flights[key]
                flight.event.set()
            raise
        with self._lock:
            flight.result = result
            if flight.generation == self._generation:
                self._cache[key] = result
                while len(self._cache) > self.maxsize:
                    self._cache.popitem(last=False)
            if self._flights.get(key) is flight:
                del self._flights[key]
            flight.event.set()
        return result

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            # A request made after clearing builds anew rather than joining a build
            # begun before it; that build's own waiters still receive its result.
            self._flights.clear()
            self._generation += 1


_GENERATED_GANGS = _GangMemo(maxsize=32)
_FLEXIBLE_GANGS = _GangMemo(maxsize=32)


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
    skeletons = set(generator.getSkeletons())
    # ICU may enumerate only the unpadded complete numeric date skeleton even though
    # its pattern generator gives a distinct pattern when every numeric month/day field
    # is requested at width two (en_US yMd -> M/d/y, widened -> MM/dd/y). Derive that
    # request from ICU's own complete numeric skeletons and keep it only when ICU gives
    # it a distinct pattern. This is CLDR skeleton grammar, not a locale inventory.
    for skeleton in tuple(skeletons):
        letters = set(skeleton)
        if letters != {"y", "M", "d"} or skeleton.count("M") != 1 or skeleton.count("d") != 1:
            continue
        padded = skeleton.replace("M", "MM").replace("d", "dd")
        if generator.getBestPattern(padded) != generator.getBestPattern(skeleton):
            skeletons.add(padded)
    return sorted(skeletons)


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


_ZONE_COUNTERPART = str.maketrans("vz", "zv")


def _bundle_keys(bundle: icu.ResourceBundle) -> list[str]:
    bundle.resetIterator()
    keys = []
    while bundle.hasNext():
        keys.append(bundle.getNext().getKey())
    return keys


def _is_lone_number_skeleton(skeleton: str) -> bool:
    """Whether ``skeleton`` is one numeric field other than the year ("d", "M", "H")."""
    return len(set(skeleton)) == 1 and len(skeleton) <= 2 and skeleton[0] != "y"


def _cldr_interval_skeletons(locale: str) -> set[str]:
    """The skeletons CLDR gives interval formats for, in ``locale`` and the locales it
    inherits from, in its calendar.

    The pattern generator does not list them all: "y" ("1624 – 1713") is CLDR's and
    not the generator's. A lone numeric field other than the year ("d", "M", "H") is
    left out: its interval writes two bare numbers ("3–5"), which the number range
    readers read, so it would give every such range a day, month, or hour reading.
    """
    icu_locale = icu.Locale(locale)
    calendar = icu.Calendar.createInstance(icu_locale).getType()
    parts = icu_locale.getName().split("_")
    names = ["_".join(parts[:count]) for count in range(len(parts), 0, -1)] + ["root"]
    found: set[str] = set()
    for name in dict.fromkeys(names):
        try:
            formats = (
                icu.ResourceBundle("", icu.Locale(name))
                .get("calendar")
                .get(calendar)
                .get("intervalFormats")
            )
        except icu.ICUError:
            continue
        found.update(_bundle_keys(formats))
    found.discard("fallback")
    return {skeleton for skeleton in found if not _is_lone_number_skeleton(skeleton)}


def _date_interval_skeletons(locale: str) -> Iterable[Spec]:
    # The pattern generator's skeletons and those CLDR gives interval formats for, and
    # for each one with a time zone field, its counterpart in the other zone family at
    # the same width (hmv and hmz). CLDR gives interval patterns for the generic zone
    # (v) alone, and ICU's interval formatter writes a specific-zone (z) skeleton
    # through them, so "2:07 – 4:07 PM EDT" has a skeleton of its own only this way;
    # the probe keeps the counterparts ICU gives patterns for.
    generator = icu.DateTimePatternGenerator.createInstance(icu.Locale(locale))
    skeletons = set(generator.getSkeletons()) | _cldr_interval_skeletons(locale)
    skeletons |= {
        skeleton.translate(_ZONE_COUNTERPART)
        for skeleton in tuple(skeletons)
        if "v" in skeleton or "z" in skeleton
    }
    return sorted(skeletons)


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


def _short_year_era_invert(spec: Spec, locale: str) -> Detector | None:
    return _short_year_era_probe(spec, locale).detector


def _short_year_era_probe(spec: Spec, locale: str) -> _Probe:
    try:
        return _Probe(DateDetector(locale, str(spec), short_years=True))
    except ValueError as error:
        return _Probe(None, str(error))


# The skeletons whose patterns write an era, each read with a year of one to three
# digits, which the default skeleton readers refuse (see DateDetector); the type is
# date:short-year:<skeleton>, one reader per skeleton as in the default family.
SHORT_YEAR_ERA_FAMILY = Family(
    "short-year-era",
    _date_time_skeletons,
    _short_year_era_invert,
    lambda spec, locale: _short_year_era_probe(spec, locale).reason,
)


def _short_year_interval_invert(spec: Spec, locale: str) -> Detector | None:
    return _short_year_interval_probe(spec, locale).detector


def _short_year_interval_probe(spec: Spec, locale: str) -> _Probe:
    try:
        detector = FlexibleDateIntervalDetector(locale, str(spec), short_years=True)
    except (icu.ICUError, ValueError) as error:
        return _Probe(None, str(error))
    if not detector.has_patterns:
        return _Probe(None, f"no invertible interval pattern for skeleton {str(spec)!r}")
    return _Probe(detector)


# The interval skeletons whose patterns write a "y" year, each read with a year of one to
# three digits, which the default interval readers refuse ("3–5" is not years 3 to 5);
# the type is date-interval:short-year:<skeleton>.
SHORT_YEAR_INTERVAL_FAMILY = Family(
    "short-year-interval",
    _date_interval_skeletons,
    _short_year_interval_invert,
    lambda spec, locale: _short_year_interval_probe(spec, locale).reason,
)


# Why a range reader is not built: ICU writes the locale no separator or sign for the
# form (a range's separator, or the approximately sign).
_NO_MARK = "ICU writes the locale no separator or sign for the form"


def _range_family(name: str, forms: tuple[str, ...]) -> Family:
    """A family of one number range reader per form, over a number and a percent reader.

    The generated set reads no currency or measure without a caller's choice, so its
    ranges are those of numbers and percents; a set that reads currencies or measures
    reads their ranges too (see :func:`range_detectors`). The endpoint readers are built
    on the reader's first read of a range.
    """

    def probe(spec: Spec, locale: str) -> _Probe:
        try:
            reader = FlexibleNumberRangeDetector(locale, form=str(spec))
        except (icu.ICUError, ValueError) as error:
            return _Probe(None, str(error))
        if not reader.has_marks:
            return _Probe(None, _NO_MARK)
        return _Probe(reader)

    return Family(
        name,
        lambda locale: forms,
        lambda spec, locale: probe(spec, locale).detector,
        lambda spec, locale: probe(spec, locale).reason,
    )


NUMBER_RANGE_FAMILY = _range_family("number-range", ("range", "approximately"))

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
    NUMBER_RANGE_FAMILY,
)

_FAMILY_PROBES = (
    (DATE_TIME_SKELETON_FAMILY, _date_time_probe),
    (DATE_INTERVAL_FAMILY, _date_interval_probe),
    (COMPACT_NUMBER_FAMILY, _compact_probe),
    (RELATIVE_DATE_FAMILY, _relative_date_probe),
    (SCIENTIFIC_NUMBER_FAMILY, _scientific_probe),
    (SPELLOUT_NUMBER_FAMILY, _spellout_probe),
    (LONE_SPELLOUT_NUMBER_FAMILY, _lone_spellout_probe),
    (SHORT_YEAR_ERA_FAMILY, _short_year_era_probe),
    (SHORT_YEAR_INTERVAL_FAMILY, _short_year_interval_probe),
)


_MATERIAL_KIND_FAMILIES = {
    "rbnf-spellout": {
        SPELLOUT_NUMBER_FAMILY: MaterialSpelloutDetector,
        LONE_SPELLOUT_NUMBER_FAMILY: MaterialLoneSpelloutDetector,
    }
}


def _material_readers(
    locale: str, families: tuple[Family, ...], materials: tuple[LocaleMaterial, ...]
) -> tuple[list[Detector], list[SkippedSpec]]:
    """Build applicable material readers for requested families, reporting refusals."""
    readers: list[Detector] = []
    skipped: list[SkippedSpec] = []
    base_locale = icu.Locale(locale).getBaseName()
    for item in materials:
        extensions = _MATERIAL_KIND_FAMILIES.get(item.kind)
        if extensions is None:
            skipped.append(
                SkippedSpec(
                    SPELLOUT_NUMBER_FAMILY.name,
                    item.digest,
                    f"material kind {item.kind!r} does not extend a detector family",
                )
            )
            continue
        if not locale_descends_from(base_locale, item.locale):
            skipped.append(
                SkippedSpec(
                    SPELLOUT_NUMBER_FAMILY.name,
                    item.digest,
                    f"material locale {item.locale!r} does not apply to "
                    f"gang locale {base_locale!r}",
                )
            )
            continue
        for family, build in extensions.items():
            if family not in families:
                continue
            readers.extend(build(locale, item, ruleset=ruleset) for ruleset in item.rulesets)
    return readers, skipped


def generated_detectors_report(
    locale: str,
    families: Iterable[Family] = DEFAULT_FAMILIES,
    *,
    material: Iterable[LocaleMaterial] = (),
) -> GenerationReport:
    """Derive detectors for ``locale`` and report specs that could not be inverted.

    The immutable report is memoized in-process by the complete request, including
    family and material-object identity, so a family must enumerate and build the same
    readers each time it is given the same locale. Calling
    :func:`icukit.cache.configure` with ``enabled=False`` or setting
    ``ICUKIT_CACHE=0`` bypasses this gang memo; :func:`clear_detector_caches` clears it
    explicitly.
    """
    families = tuple(families)
    materials = tuple(_require_loaded(item) for item in material)
    key = (locale, _IdentityTuple(families), _IdentityTuple(materials))
    return cast(
        GenerationReport,
        _GENERATED_GANGS.get_or_build(
            key, lambda: _build_generated_detectors_report(locale, families, materials)
        ),
    )


def _build_generated_detectors_report(
    locale: str, families: tuple[Family, ...], materials: tuple[LocaleMaterial, ...]
) -> GenerationReport:
    """Build a generated report after its complete inputs have been normalized."""
    with _build_phase():
        detectors = DetectorSet(())
        skipped: list[SkippedSpec] = []
        for family, spec, detector, reason in _family_specs(locale, families):
            if detector is not None:
                detectors = detectors.with_(detector)
            else:
                skipped.append(SkippedSpec(family.name, spec, reason))
        material_readers, material_skipped = _material_readers(locale, families, materials)
        return GenerationReport(detectors.with_(*material_readers), (*skipped, *material_skipped))


def _family_specs(
    locale: str, families: Iterable[Family]
) -> Iterable[tuple[Family, Spec, Detector | None, str]]:
    """Yield each enumerated family spec with its detector or reported skip reason.

    Generation and availability share enumeration, probes, exception handling, and skip
    reasons. Availability additionally reports readers that are built but have no data.
    """
    for family in families:
        for spec in family.enumerate(locale):
            probe_function = next(
                (probe for known_family, probe in _FAMILY_PROBES if family is known_family), None
            )
            probe = probe_function(spec, locale) if probe_function is not None else None
            detector = probe.detector if probe is not None else family.invert(spec, locale)
            reason = probe.reason if probe is not None else ""
            if detector is None and not reason:
                reason = (
                    family.skip_reason(spec, locale)
                    if family.skip_reason is not None
                    else "family returned no inverter"
                )
            yield family, spec, detector, reason


def generated_detectors(
    locale: str,
    families: Iterable[Family] = DEFAULT_FAMILIES,
    *,
    material: Iterable[LocaleMaterial] = (),
) -> DetectorSet:
    """Derive all invertible detectors introspectively registered for ``locale``.

    Repeated equal calls return the detector set from the process-wide bounded gang
    memo. Calling :func:`icukit.cache.configure` with ``enabled=False`` or setting
    ``ICUKIT_CACHE=0`` bypasses that memo, and :func:`clear_detector_caches` clears
    every detector-construction cache.
    """
    return generated_detectors_report(locale, families, material=material).detectors


# --------------------------------------------------------------------------- flexible set


def _parameter_family(
    name: str, specs: Callable[[str], Iterable[Spec]], build: Callable[[str, str], Detector]
) -> Family:
    """A family of one reader per spec, the spec skipped with ICU's reason where it fails."""

    def probe(spec: Spec, locale: str) -> _Probe:
        try:
            return _Probe(build(locale, str(spec)))
        except (icu.ICUError, ValueError) as error:
            return _Probe(None, str(error))

    def invert(spec: Spec, locale: str) -> Detector | None:
        return probe(spec, locale).detector

    def skip_reason(spec: Spec, locale: str) -> str:
        return probe(spec, locale).reason or f"{name} spec {spec!r} was not invertible"

    return Family(name, specs, invert, skip_reason)


def _bundle_items(bundle: icu.ResourceBundle) -> list[icu.ResourceBundle]:
    bundle.resetIterator()
    items = []
    while bundle.hasNext():
        items.append(bundle.getNext())
    return items


@cache
def _unit_preferences() -> tuple[tuple[str, str, str, tuple[str, ...]], ...]:
    """CLDR's unit preferences as ICU carries them: ``(category, usage, region, units)``.

    Read from ICU's own ``units`` resource (``unitPreferenceData``), the table
    ``NumberFormatter.usage`` formats from; each ``units`` is in CLDR's order, largest
    first.
    """
    table = icu.ResourceBundle("", icu.Locale("units")).get("unitPreferenceData")
    found = []
    for category in _bundle_items(table):
        for usage in _bundle_items(category):
            for region in _bundle_items(usage):
                units = tuple(
                    preference.get("unit").getString() for preference in _bundle_items(region)
                )
                found.append((category.getKey(), usage.getKey(), region.getKey(), units))
    return tuple(found)


def _read_regions(locale: str, locales: tuple[str, ...] | None) -> frozenset[str]:
    """The world (``001``) and the regions of the locales a reader for ``locale`` reads."""
    regions = {icu.Locale(name).getCountry() for name in _language_locales(locale, locales)}
    return frozenset({"001", *(region for region in regions if region)})


def _preferred_units(locale: str, locales: tuple[str, ...] | None) -> tuple[str, ...]:
    """The single units CLDR's unit preferences give the regions the reader reads.

    A unit is read only where a region the reader reads prefers it: German text's "°F"
    is not read, since no German locale's region prefers Fahrenheit, and "900 MHz" is
    read in no locale. The full ICU unit inventory reads them at a larger cost to build
    and to run; a caller who wants it passes ``units=``.
    """
    regions = _read_regions(locale, locales)
    found = dict.fromkeys(
        unit
        for _category, _usage, region, units in _unit_preferences()
        if region in regions
        for unit in units
        if "-and-" not in unit
    )
    return tuple(sorted(found))


def _duration_chain() -> tuple[str, ...]:
    """CLDR's default duration units for the world, largest first (day ... nanosecond)."""
    for category, usage, region, units in _unit_preferences():
        if (category, usage, region) == ("duration", "default", "001"):
            return units
    return ()


def _mixed_units(locale: str, locales: tuple[str, ...] | None) -> tuple[str, ...]:
    """The mixed units a text in ``locale``'s language writes.

    Those CLDR's unit preferences give the regions the reader reads ("foot-and-inch" for
    US person-height, "stone-and-pound" for GB), and each run of adjacent units in CLDR's
    default duration order ("hour-and-minute", "hour-and-minute-and-second"), since
    ICU's ``MeasureFormat`` writes a duration of several units ("1 hr, 15 min, 27 sec")
    and no preference names those.
    """
    regions = _read_regions(locale, locales)
    found = dict.fromkeys(
        unit
        for _category, _usage, region, units in _unit_preferences()
        if region in regions
        for unit in units
        if "-and-" in unit
    )
    chain = _duration_chain()
    for start in range(len(chain)):
        for end in range(start + 2, len(chain) + 1):
            found.setdefault("-and-".join(chain[start:end]))
    return tuple(found)


# ISO 4217's "no currency" code: ICU gives it to a locale of no country and writes it "¤".
_NO_CURRENCY = "XXX"


@cache
def _current_currencies() -> frozenset[str]:
    """The currencies ICU gives some territory today.

    PyICU exposes neither ``ucurr_isAvailable`` nor CLDR's currency map, so a currency
    counts as current when ICU's currency formatter chooses it for a territory's
    locale: "und_<territory>" ("und_DE" is EUR) or any available locale of the
    territory. A withdrawn one (DEM, FRF) is no territory's. The formatter chooses one
    currency a territory, so a second currency in use beside it is not counted: the
    loti (LSL) beside the rand in Lesotho, whose locales ICU all gives ZAR, is a known
    gap, and a caller who wants it passes ``currencies=``.
    """
    names = [f"und_{region}" for region in icu.Region.getAvailable(icu.URegionType.TERRITORY)]
    names += [name for name in icu.Locale.getAvailableLocales() if icu.Locale(name).getCountry()]
    found = set()
    for name in names:
        code = icu.NumberFormat.createCurrencyInstance(icu.Locale(name)).getCurrency()
        if code:
            found.add(code)
    found.discard(_NO_CURRENCY)
    return frozenset(found)


def _chosen_currencies(locale: str, locales: tuple[str, ...] | None) -> tuple[str, ...]:
    """The currencies a text in ``locale``'s language names, chosen from CLDR.

    Each read locale's own currency (en_IN's INR, en_GB's GBP), and each currency
    ``locale`` writes with a symbol of its own rather than its ISO code (en_US's "¥",
    ja_JP's "$"), since CLDR gives a locale a symbol for the currencies its text names.
    Only currencies still in use are kept (see ``_current_currencies``): de_DE's own
    symbols for the Mark and the Schilling ("DM", "öS") name currencies ICU gives no
    territory today. The full ICU inventory costs several times as much to build and to
    run; a caller who wants it passes ``currencies=``.
    """
    found = set()
    for name in _language_locales(locale, locales):
        code = icu.NumberFormat.createCurrencyInstance(icu.Locale(name)).getCurrency()
        if code:
            found.add(code)
    icu_locale = icu.Locale(locale)
    for code in _iso_currency_codes():
        surface = (
            icu.NumberFormatter.withLocale(icu_locale)
            .unit(icu.CurrencyUnit(code))
            .unitWidth(icu.UNumberUnitWidth.SHORT)
            .formatInt(1)
        )
        if code not in surface:
            found.add(code)
    return tuple(sorted(found & _current_currencies()))


# The ICU unit types whose every unit the set reads in any locale: running text writes a
# duration ("3 weeks", "2 fortnights") or a data size ("2 GB") whatever the region, and
# CLDR's unit preferences name few of them (no week, no byte). Both types are small.
# The "-person" durations (week-person, year-person) are left out: ICU writes them as it
# writes week and year, so each duration would read twice. They come in where CLDR's
# preferences name them (person-age's year-person-and-month-person).
_EVERY_REGION_UNIT_TYPES = ("duration", "digital")


def _every_region_units() -> tuple[str, ...]:
    """Every unit ICU's inventory holds of :data:`_EVERY_REGION_UNIT_TYPES`, less the
    "-person" durations."""
    return tuple(
        unit.getIdentifier()
        for unit_type in _EVERY_REGION_UNIT_TYPES
        for unit in icu.MeasureUnit.getAvailable(unit_type)
        if unit.getIdentifier() and not unit.getIdentifier().endswith("-person")
    )


def _single_units(
    locale: str, locales: tuple[str, ...] | None, units: tuple[str, ...] | None
) -> tuple[str, ...]:
    """The selected non-mixed units for one flexible or detached-unit family."""
    if units is not None:
        return tuple(unit for unit in units if "-and-" not in unit)
    language = icu.Locale(locale).getLanguage()
    return tuple(
        dict.fromkeys(
            (
                *_preferred_units(locale, locales),
                *_every_region_units(),
                *curated_composed_units(language),
            )
        )
    )


DETACHED_UNIT_FAMILY = _parameter_family(
    "detached-unit",
    lambda locale: _single_units(locale, None, None),
    FlexibleDetachedUnitDetector,
)

# The readings the default readers refuse on purpose, each under its own type; not in
# DEFAULT_FAMILIES, so a consumer opts in (see the module docstring).
GUARDED_FAMILIES = (
    LONE_SPELLOUT_NUMBER_FAMILY,
    LOWERCASE_ROMAN_FAMILY,
    MONTH_NAME_FAMILY,
    WEEKDAY_NAME_FAMILY,
    SHORT_YEAR_FAMILY,
    SHORT_YEAR_ERA_FAMILY,
    BARE_HOUR_FAMILY,
    SHORT_YEAR_INTERVAL_FAMILY,
    DETACHED_UNIT_FAMILY,
)


def _flexible_families(
    locales: tuple[str, ...] | None,
    currencies: tuple[str, ...] | None,
    units: tuple[str, ...] | None,
    guarded: bool,
) -> tuple[Family, ...]:
    """The families of :func:`flexible_detectors`, each reader bound to ``locales``."""

    def one(name: str, build: Callable[..., Detector], widened: bool = True) -> Family:
        def make(locale: str) -> Detector:
            return build(locale, locales=locales) if widened else build(locale)

        return _guarded_family(name, make, lambda detector: True, f"{name} was not built")

    def currency_codes(locale: str) -> Iterable[Spec]:
        return currencies if currencies is not None else _chosen_currencies(locale, locales)

    # A mixed unit ("foot-and-inch") has a reader of its own; a caller's ``units`` may
    # hold both kinds.
    def single_units(locale: str) -> Iterable[Spec]:
        return _single_units(locale, locales, units)

    def mixed_units(locale: str) -> Iterable[Spec]:
        if units is not None:
            return tuple(unit for unit in units if "-and-" in unit)
        return _mixed_units(locale, locales)

    families = [
        one(
            "number",
            lambda locale, *, locales=None: _shared_number_reader(locale, locales, True, False),
        ),
        one("percent", FlexiblePercentDetector),
        one("fraction", FlexibleFractionDetector, widened=False),
        one("ordinal", FlexibleOrdinalDetector, widened=False),
        one("plural-numeral", PluralNumeralDetector, widened=False),
        SCIENTIFIC_NUMBER_FAMILY,
        COMPACT_NUMBER_FAMILY,
        SPELLOUT_NUMBER_FAMILY,
        _parameter_family(
            "currency",
            currency_codes,
            lambda locale, code: FlexibleCurrencyDetector(locale, code, locales=locales),
        ),
        _parameter_family("currency-name", currency_codes, FlexibleCurrencyNameDetector),
        _parameter_family(
            "measure",
            single_units,
            lambda locale, unit: FlexibleMeasureDetector(locale, unit, locales=locales),
        ),
        _parameter_family(
            "mixed-measure",
            mixed_units,
            lambda locale, unit: FlexibleMixedMeasureDetector(locale, unit, locales=locales),
        ),
        one("numeric-duration", FlexibleNumericDurationDetector),
        one("date", FlexibleDateDetector),
        one("text-date", FlexibleTextDateDetector),
        one("date-time", FlexibleDateTimeDetector),
        one("time", FlexibleTimeDetector),
        RELATIVE_DATE_FAMILY,
        DATE_INTERVAL_FAMILY,
        one("letter-name", LetterNameDetector, widened=False),
        one("single-letter-word", SingleLetterWordDetector, widened=False),
        one("alphanumeric-runs", AlphanumericRunsDetector, widened=False),
    ]
    if guarded:
        families += [
            LONE_SPELLOUT_NUMBER_FAMILY,
            LOWERCASE_ROMAN_FAMILY,
            _guarded_family(
                "month-name",
                lambda locale: FlexibleMonthNameDetector(locale, locales=locales),
                lambda detector: detector.has_names,
                "ICU gives the locale's language no month names",
            ),
            _guarded_family(
                "weekday-name",
                lambda locale: FlexibleWeekdayNameDetector(locale, locales=locales),
                lambda detector: detector.has_names,
                "ICU gives the locale's language no weekday names",
            ),
            _guarded_family(
                "short-year",
                lambda locale: FlexibleShortYearDateDetector(locale, locales=locales),
                lambda detector: detector.has_year_patterns,
                "the locale's textual date patterns write no year",
            ),
            _guarded_family(
                "bare-hour",
                lambda locale: FlexibleBareHourDetector(locale, locales=locales),
                lambda detector: detector.letter is not None,
                "ICU's best pattern for the j skeleton has no hour field",
            ),
            SHORT_YEAR_INTERVAL_FAMILY,
            DETACHED_UNIT_FAMILY
            if locales is None and units is None
            else _parameter_family(
                "detached-unit",
                single_units,
                lambda locale, unit: FlexibleDetachedUnitDetector(locale, unit, locales=locales),
            ),
        ]
    return tuple(families)


# The endpoint readers of the number range readers, by the group of each range reader.
_RANGE_ENDPOINTS = (
    (FlexibleNumberDetector, FlexiblePercentDetector, FlexibleCurrencyDetector, NumberDetector),
    (FlexibleMeasureDetector,),
)


def range_detectors(
    locale: str,
    detectors: DetectorSet,
    *,
    locales: Iterable[str] | None = None,
) -> DetectorSet:
    """The number range readers over the amount readers ``detectors`` holds.

    A range's endpoints follow the set: one reader over its number, percent, and
    currency readers, strict or flexible (``number:range``), and one over its measure
    readers (``measure:range``), each also reading the approximately form. So a set that
    reads a currency or a unit reads its ranges ("$3–5", "10–15 kg"), and one that does
    not, does not. Add them with
    ``detectors.with_(*range_detectors(locale, detectors).detectors)``: each replaces the
    set's own reader of its type, a generated set's ``number:range`` among them.
    """
    readers, _ = _range_readers(locale, detectors, _locale_selection(locale, locales))
    return DetectorSet(tuple(readers))


def _range_readers(
    locale: str, detectors: DetectorSet, locales: tuple[str, ...] | None
) -> tuple[list[Detector], list[SkippedSpec]]:
    """:func:`range_detectors`, and each form ICU gives no separator, as skipped."""
    readers: list[Detector] = []
    skipped: list[SkippedSpec] = []
    for kinds in _RANGE_ENDPOINTS:
        endpoints = [detector for detector in detectors.detectors if type(detector) in kinds]
        if not endpoints:
            continue
        for form in ("range", "approximately"):
            reader = FlexibleNumberRangeDetector(locale, endpoints, form=form, locales=locales)
            if reader.has_marks:
                readers.append(reader)
            else:
                skipped.append(SkippedSpec(f"number-{form}", reader.type, _NO_MARK))
    return readers, skipped


def flexible_detectors_report(
    locale: str,
    *,
    locales: Iterable[str] | None = None,
    currencies: Iterable[str] | None = None,
    units: Iterable[str] | None = None,
    guarded: bool = False,
    material: Iterable[LocaleMaterial] = (),
) -> GenerationReport:
    """The flexible readers for ``locale``, and every spec that could not be built.

    See :func:`flexible_detectors`. The frozen report is memoized by the complete,
    normalized request. Calling :func:`icukit.cache.configure` with ``enabled=False``
    or setting ``ICUKIT_CACHE=0`` bypasses the gang memo;
    :func:`clear_detector_caches` clears it explicitly.
    """
    selection = _locale_selection(locale, locales)
    currency_selection = None if currencies is None else tuple(currencies)
    unit_selection = None if units is None else tuple(units)
    materials = tuple(_require_loaded(item) for item in material)
    key = (
        locale,
        selection,
        currency_selection,
        unit_selection,
        guarded,
        _IdentityTuple(materials),
    )
    return cast(
        GenerationReport,
        _FLEXIBLE_GANGS.get_or_build(
            key,
            lambda: _build_flexible_detectors_report(
                locale,
                selection,
                currency_selection,
                unit_selection,
                guarded,
                materials,
            ),
        ),
    )


def _build_flexible_detectors_report(
    locale: str,
    selection: tuple[str, ...] | None,
    currencies: tuple[str, ...] | None,
    units: tuple[str, ...] | None,
    guarded: bool,
    materials: tuple[LocaleMaterial, ...],
) -> GenerationReport:
    """Build a flexible report after its complete inputs have been normalized."""
    with _build_phase():
        families = _flexible_families(
            selection,
            currencies,
            units,
            guarded,
        )
        # These families are closures freshly bound to this flexible request. The
        # outer memo owns their stable identity boundary, so do not populate the
        # generated memo with one-use family objects.
        report = _build_generated_detectors_report(locale, families, materials)
        readers, skipped = _range_readers(locale, report.detectors, selection)
        return GenerationReport(report.detectors.with_(*readers), (*report.skipped, *skipped))


def flexible_detectors(
    locale: str,
    *,
    locales: Iterable[str] | None = None,
    currencies: Iterable[str] | None = None,
    units: Iterable[str] | None = None,
    guarded: bool = False,
    material: Iterable[LocaleMaterial] = (),
) -> DetectorSet:
    """A gang of every flexible (recall) reader of :mod:`icukit.recognize` for ``locale``.

    It holds the numeric, percent, fraction, ordinal, plural-numeral, scientific,
    compact (each ICU width), spell-out (each RBNF spell-out rule set), currency and
    currency-name, measure, mixed-measure, numeric-duration, numeric-date, text-date,
    date-time, time, relative-date, and date-interval (each skeleton ICU gives an
    interval, a zoned one in both the generic and the specific zone family, hmv and
    hmz) readers, the letter-name, single-letter-word, and alphanumeric-run readers,
    and the number range readers over the set's own number, percent, and currency
    readers (``number:range``, ``number:approximately``) and over its measure readers
    (``measure:range``, ``measure:approximately``). Where :func:`generated_detectors`
    builds a reader of the same type, class, and locales, the two share a key (see
    :func:`~icukit.detectors.detector_key`) and the one added last stands, so
    ``generated_detectors(locale).with_(*flexible_detectors(locale).detectors)`` is the
    strict and flexible readers together. Most such pairs are one reader built twice;
    the range readers are not: the generated ``number:range`` reads over a number and a
    percent reader, and the flexible one that replaces it over the set's own number,
    percent, and currency readers.

    A reader that takes a parameter is built for each value chosen from ICU:

    * ``currencies`` -- each read locale's own currency (en_IN's INR) and each currency
      ``locale`` writes with a symbol of its own rather than its ISO code (en_US's "¥");
      pass ISO codes to choose others.
    * ``units`` -- the units CLDR's unit preferences give the world and the regions of
      the read locales, every unit of ICU's ``duration`` and ``digital`` types ("3
      weeks", "2 GB"), and the composed units icukit's curated table chooses; and the
      preferences' mixed units ("foot-and-inch") with each run of CLDR's default
      duration order ("hour-and-minute-and-second"). A unit no read region prefers is
      not read (German text's "°F", "900 MHz" anywhere). Pass ICU unit identifiers,
      single or mixed, to choose others; the full ICU inventory reads more at more
      cost.

    ``locales`` chooses the other locales of the language the language-wide readers
    read, and the locales the currencies and units are chosen from (every one by
    default). ``guarded`` adds the readers of the readings the default readers refuse on
    purpose (:data:`GUARDED_FAMILIES`), each under its own type. A member that cannot be
    built is left out; :func:`flexible_detectors_report` names it and why.

    Construction is cached process-wide in a bounded memo keyed by every option; equal
    calls return the same frozen set. Calling :func:`icukit.cache.configure` with
    ``enabled=False`` or setting ``ICUKIT_CACHE=0`` bypasses the gang memo; use
    :func:`clear_detector_caches` to clear it. A ``detect`` costs a small multiple of
    the generated set's, since the currency and measure readers share the numbers they
    read within a text. The shared readings are kept for the 16 texts read last (about
    110 bytes per character each for en_US).
    """
    return flexible_detectors_report(
        locale,
        locales=locales,
        currencies=currencies,
        units=units,
        guarded=guarded,
        material=material,
    ).detectors


def clear_detector_caches() -> None:
    """Clear all process-wide detector-construction caches.

    This clears generated and flexible gang memos, shared number readers, derived
    per-locale currency, measure, digit, plural, and time-zone tables, and the table
    store's loaded values. It does not delete table-store files. Compiled sets and their
    text plans belong to individual :class:`DetectorSet` instances, not a process-global
    cache, so they are not reset here. Use :func:`icukit.cache.configure` or
    ``ICUKIT_CACHE=0`` to bypass the gang memo, implicit compilation, and table store.
    """
    _GENERATED_GANGS.clear()
    _FLEXIBLE_GANGS.clear()
    _clear_shared_number_reader_cache()
    _clear_derived_locale_caches()


def reader_set(
    locale: str,
    *,
    guarded: bool = False,
    flexible: bool = False,
    locales: Iterable[str] | None = None,
    currencies: Iterable[str] = (),
    units: Iterable[str] = (),
    skeletons: Iterable[str] | None = None,
    material: Iterable[LocaleMaterial] = (),
) -> DetectorSet:
    """Build the detector gang selected by the corresponding ``ik detect`` options.

    ``reader_set(locale, flexible=True)`` is the default generated-plus-flexible gang.
    The order is part of the public result and matches the command-line detector set.
    """
    with _build_phase():
        currencies = tuple(currencies)
        units = tuple(units)
        material = tuple(material)
        families = (*DEFAULT_FAMILIES, *GUARDED_FAMILIES) if guarded else DEFAULT_FAMILIES
        detectors = generated_detectors(locale, families, material=material)
        plain = not flexible
        numbers = number_detectors(locale, decimal=plain, percent=plain, currencies=currencies)
        detectors = detectors.with_(*numbers.detectors)
        if flexible:
            flexible_set = flexible_detectors(
                locale,
                locales=locales,
                currencies=currencies or None,
                units=units or None,
                guarded=guarded,
                material=material,
            )
            detectors = detectors.with_(*flexible_set.detectors)
        else:
            detectors = detectors.with_(*(FlexibleMeasureDetector(locale, unit) for unit in units))
            if currencies or units:
                detectors = detectors.with_(*range_detectors(locale, detectors).detectors)
        if skeletons:
            detectors = detectors.with_(*date_detectors(locale, skeletons).detectors)
        return detectors


# note: Flexible recall detectors do not yet generalize to partial date skeletons; that
# is a separate follow-on from exact formatter-surface generation.
