"""Report which reader specifications a locale can build and from which source."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path

import icu

from .abbreviations import available_locales as abbreviation_locales
from .abbreviations import load_lexicon, locale_chain
from .engine import (
    DEFAULT_FAMILIES,
    GUARDED_FAMILIES,
    LONE_SPELLOUT_NUMBER_FAMILY,
    SPELLOUT_NUMBER_FAMILY,
    Family,
    _family_specs,
    _flexible_families,
    _material_readers,
)
from .material import LocaleMaterial
from .unit_surfaces import (
    curated_composed_units,
    curated_currency_surfaces,
    curated_unit_surfaces,
)

__all__ = ["AvailabilityRow", "availability", "available_languages"]

_PACKAGE = Path(__file__).parent
_LEXICON_FAMILIES = frozenset(
    {"abbreviation", "text-date", "date-time", "month-name", "weekday-name", "short-year"}
)
_CURATED_ONLY_FAMILIES = frozenset({"abbreviation", "letter-name", "single-letter-word"})

_AVAILABILITY_CHECKS: dict[str, tuple[Callable[[object], bool], str]] = {
    "letter-name": (
        attrgetter("has_names"),
        "icukit has no curated letter-name table for {language}",
    ),
    "plural-numeral": (
        attrgetter("has_suffixes"),
        "icukit has no curated plural-numeral suffix table for {language}",
    ),
    "single-letter-word": (
        attrgetter("has_words"),
        "icukit has no curated single-letter-word table for {language}",
    ),
}


@dataclass(frozen=True)
class AvailabilityRow:
    """One enumerated reader specification and the source that contributes to it."""

    locale: str
    family: str
    spec: str
    type: str | None
    source: str | None
    served_by: str | None
    material: str | None
    provenance: str | None
    reason: str | None


def available_languages() -> tuple[str, ...]:
    """Return the distinct ICU language identifiers covered by availability reports."""
    return tuple(
        sorted(
            {
                language
                for name in icu.Locale.getAvailableLocales()
                if (language := icu.Locale(name).getLanguage())
            }
        )
    )


def _actual_spellout_locale(locale: str) -> str:
    """Return ICU's actual-locale name for the locale's spell-out rules."""
    formatter = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.SPELLOUT, icu.Locale(locale))
    return formatter.getLocale(icu.ULocDataLocaleType.ACTUAL_LOCALE).getName()


def _served_by(locale: str, family: Family) -> str | None:
    if family not in {SPELLOUT_NUMBER_FAMILY, LONE_SPELLOUT_NUMBER_FAMILY}:
        return None
    actual = _actual_spellout_locale(locale) or "root"
    if actual == "root":
        return actual
    return actual if icu.Locale(actual).getLanguage() != icu.Locale(locale).getLanguage() else None


def _relative(path: Path) -> str:
    return f"icukit/{path.relative_to(_PACKAGE).as_posix()}"


def _lexicon_paths(locale: str, family: str) -> tuple[str, ...]:
    shipped = set(abbreviation_locales())
    senses = {
        "month-name": {"month"},
        "weekday-name": {"weekday"},
    }.get(family, {"month", "weekday"})
    names = []
    for name in reversed(locale_chain(locale)):
        if name not in shipped:
            continue
        if family != "abbreviation":
            lexicon = load_lexicon(name)
            if not any(
                expansion.sense in senses
                for entry in lexicon.entries
                for expansion in entry.expansions
            ):
                continue
        names.append(name)
    return tuple(_relative(_PACKAGE / "data" / "abbreviations" / f"{name}.xml") for name in names)


def _curated_paths(locale: str, family: str, spec: str, detector: object) -> tuple[str, ...]:
    """Return shipped tables that the built family/spec actually consumes."""
    paths: list[str] = []
    if family in _LEXICON_FAMILIES:
        paths.extend(_lexicon_paths(locale, family))
    check = _AVAILABILITY_CHECKS.get(family)
    if check is not None and check[0](detector):
        paths.append("icukit/recognize.py")

    language = icu.Locale(locale).getLanguage()
    unit_path = _PACKAGE / "data" / "unit_surfaces" / f"{language}.tsv"
    if unit_path.is_file():
        if family == "currency" and any(
            code == spec for _surface, code in curated_currency_surfaces(language)
        ):
            paths.append(_relative(unit_path))
        elif family == "measure":
            targets = {unit for _surface, unit in curated_unit_surfaces(language)}
            if (
                spec in targets
                or f"per-{spec}" in targets
                or spec in curated_composed_units(language)
            ):
                paths.append(_relative(unit_path))
        elif family == "mixed-measure":
            targets = {
                unit.removeprefix("per-") for _surface, unit in curated_unit_surfaces(language)
            }
            if targets.intersection(spec.split("-and-")):
                paths.append(_relative(unit_path))
    return tuple(dict.fromkeys(paths))


def _families(guarded: bool) -> tuple[Family, ...]:
    flexible = _flexible_families(None, None, None, guarded)
    generated = (*DEFAULT_FAMILIES, *GUARDED_FAMILIES) if guarded else DEFAULT_FAMILIES
    return tuple(dict.fromkeys((*generated, *flexible)))


def availability(
    locale: str, *, material: Iterable[LocaleMaterial] = (), guarded: bool = False
) -> tuple[AvailabilityRow, ...]:
    """Report every generated and flexible reader spec available for ``locale``.

    ICU/CLDR, shipped curated tables, and explicitly supplied user material are
    separate rows. An enumerated spec that cannot be built is retained with its reason.
    """
    families = _families(guarded)
    materials = tuple(material)
    for item in materials:
        if not isinstance(item, LocaleMaterial):
            raise TypeError(f"material must contain LocaleMaterial, got {type(item).__name__}")

    rows: list[AvailabilityRow] = []
    for family, raw_spec, detector, reason in _family_specs(locale, families):
        spec = str(raw_spec)
        if detector is None:
            rows.append(
                AvailabilityRow(locale, family.name, spec, None, None, None, None, None, reason)
            )
            continue
        if (check := _AVAILABILITY_CHECKS.get(family.name)) is not None and not check[0](detector):
            language = icu.Locale(locale).getLanguage()
            rows.append(
                AvailabilityRow(
                    locale,
                    family.name,
                    spec,
                    None,
                    None,
                    None,
                    None,
                    None,
                    check[1].format(language=language),
                )
            )
            continue
        detector_type = str(detector.type)
        if family.name not in _CURATED_ONLY_FAMILIES:
            rows.append(
                AvailabilityRow(
                    locale,
                    family.name,
                    spec,
                    detector_type,
                    "icu",
                    _served_by(locale, family),
                    None,
                    None,
                    None,
                )
            )
        for path in _curated_paths(locale, family.name, spec, detector):
            rows.append(
                AvailabilityRow(
                    locale, family.name, spec, detector_type, "curated", None, None, path, None
                )
            )

    material_readers, material_skipped = _material_readers(locale, families, materials)
    by_digest = {item.digest: item for item in materials}
    for detector in material_readers:
        family = (
            "spellout-lone"
            if type(detector).__name__ == "MaterialLoneSpelloutDetector"
            else "spellout-number"
        )
        digest = detector.material_digest
        rows.append(
            AvailabilityRow(
                locale,
                family,
                str(detector._ruleset),
                str(detector.type),
                "user",
                None,
                digest,
                by_digest[digest].provenance["source"],
                None,
            )
        )
    rows.extend(
        AvailabilityRow(
            locale, item.family, str(item.spec), None, None, None, None, None, item.reason
        )
        for item in material_skipped
    )
    return tuple(dict.fromkeys(rows))


def _language_summary(locale: str) -> tuple[tuple[str, str], ...]:
    """Cheap, true family summary for generated defaults and shipped curated tables."""
    found: list[tuple[str, str]] = []
    for family in DEFAULT_FAMILIES:
        detector = next(
            (
                detector
                for _family, _spec, detector, _reason in _family_specs(locale, (family,))
                if detector is not None
            ),
            None,
        )
        if detector is None:
            continue
        if family.name == "abbreviation":
            paths = _lexicon_paths(locale, family.name)
            label = f"curated ({', '.join(paths)})"
        else:
            label = "ICU"
            if (served_by := _served_by(locale, family)) is not None:
                label += f" (served by {served_by})"
        found.append((family.name, label))

    language = icu.Locale(locale).getLanguage()
    unit_path = _PACKAGE / "data" / "unit_surfaces" / f"{language}.tsv"
    if unit_path.is_file() and (
        curated_unit_surfaces(language)
        or curated_currency_surfaces(language)
        or curated_composed_units(language)
    ):
        found.append(
            (
                "measure",
                f"curated surfaces beside ICU's units ({_relative(unit_path)})",
            )
        )
    return tuple(found)
