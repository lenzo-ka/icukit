"""
Every abbreviation ICU writes for a language, with the expansions ICU gives it.

Generated from ICU at call time, not stored: for each kind of short form ICU formats,
the short and narrow surfaces, and the long forms ICU writes for the same thing. A
consumer that speaks text (a TTS front end) can expand what it reads from here
without keeping its own list.

Kinds:

    * ``unit``: unit symbols ("km") with the unit's wide names ("kilometers");
    * ``per-unit``: a rate's per form ("/km²") with its wide form ("per square
      kilometer");
    * ``month`` and ``weekday``: abbreviated and narrow names ("Sep") with the wide
      name ("September");
    * ``era``: abbreviated names and their variants ("BC", "BCE") with the wide names
      ("Before Christ", "Before Common Era");
    * ``day-period``: "AM", "PM", with a wide form where the language has one;
    * ``time-zone``: zone abbreviations ("EST", "ET") with the long names ("Eastern
      Standard Time", "Eastern Time");
    * ``currency``: symbols and ISO codes ("$", "USD") with the currency's names ("US
      dollars");
    * ``compact``: compact-number suffixes ("K") with the long ones ("thousand");
    * ``relative-unit``: relative-time unit abbreviations ("hr.", "mo") with the long
      ones ("hours", "months");
    * ``territory``: region codes ("US", "EU", "UN") and CLDR's short territory names
      ("UK") with the territory's names ("United States", "European Union").

``key`` names what the surface stands for in ICU's terms: a unit identifier, a month
or weekday number (ICU's, Sunday 1), an era index, a zone's long name (one
abbreviation serves many zone IDs), an ISO 4217 code, a power of ten, a relative
unit, or a region code. ``expansions`` are ICU's long forms, singular and
plural where they differ, in the order ICU gave them; empty where ICU writes no longer
form (English "AM"). The locales read are the locale's language's, or the ones a
caller chooses, as for the readers.

Example:
    >>> from icukit import icu_abbreviations
    >>> [a.expansions for a in icu_abbreviations("en_US", kinds=["unit"]) if a.surface == "km"]
    [('kilometer', 'kilometers')]
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache

import icu

from .recognize import (
    _language_day_periods,
    _language_eras,
    _language_locale_names,
    _language_locales,
    _locale_selection,
    _plural_samples,
)
from .unit_surfaces import (
    curated_composed_units,
    curated_currency_surfaces,
    curated_unit_surfaces,
)

__all__ = ["IcuAbbreviation", "ABBREVIATION_KINDS", "icu_abbreviations"]

ABBREVIATION_KINDS = (
    "unit",
    "per-unit",
    "month",
    "weekday",
    "era",
    "day-period",
    "time-zone",
    "currency",
    "compact",
    "relative-unit",
    "territory",
)

_SPACES = "    "


@dataclass(frozen=True)
class IcuAbbreviation:
    """One short form ICU writes, with the long forms ICU gives the same thing."""

    surface: str
    kind: str
    key: str
    width: str
    expansions: tuple[str, ...]
    source: str = "icu"


class _Table:
    """Entries keyed by ``(surface, kind, key)``; the first width seen is kept."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], tuple[str, list[str], str]] = {}

    def add(
        self,
        surface: str,
        kind: str,
        key: str,
        width: str,
        expansions: Iterable[str],
        source: str = "icu",
    ):
        if not surface:
            return
        entry = self._entries.setdefault((surface, kind, key), (width, [], source))
        for expansion in expansions:
            if expansion and expansion != surface and expansion not in entry[1]:
                entry[1].append(expansion)

    def expansions_of(self, key: str) -> list[str]:
        for (_surface, _kind, entry_key), (_width, expansions, _source) in self._entries.items():
            if entry_key == key and expansions:
                return list(expansions)
        return []

    def rows(self) -> tuple[IcuAbbreviation, ...]:
        return tuple(
            IcuAbbreviation(surface, kind, key, width, tuple(expansions), source)
            for (surface, kind, key), (width, expansions, source) in self._entries.items()
        )


def _without_number(text: str, number: str) -> str:
    """``text`` with its number taken out, trimmed of the spaces around it.

    The number is taken where no digit touches it, so a date inside a name stays
    whole ("Afghan afghani (1927–2002)" keeps its 1).
    """
    index = text.find(number)
    while index >= 0:
        before = text[index - 1 : index]
        after = text[index + len(number) : index + len(number) + 1]
        if not before.isdigit() and not after.isdigit():
            break
        index = text.find(number, index + 1)
    if index < 0:
        return ""
    rest = text[:index] + " " + text[index + len(number) :]
    return " ".join(rest.replace(" ", " ").replace(" ", " ").split())


def _currency_name(text: str, number: str, marks: set[str]) -> str:
    """A currency's name in its long form, without the number, code, or symbol.

    Some English locales write the long form with the code or symbol in it as well
    ("US$ 2 US dollars" in en_AT, "ARS  Argentine pesos2" in en_DE); the name is
    what is left once the number and any word that is the code or a symbol go.
    """
    words = _without_number(text, number).split()
    return " ".join(word for word in words if word not in marks)


def _units_available(language: str):
    """ICU's unit inventory, and the composed units the language's table chooses."""
    units = [
        unit
        for unit_type in icu.MeasureUnit.getAvailableTypes()
        if unit_type != "currency"
        for unit in icu.MeasureUnit.getAvailable(unit_type)
        if unit.getIdentifier()
    ]
    return units + [icu.MeasureUnit.forIdentifier(u) for u in curated_composed_units(language)]


@cache
def _unit_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    table = _Table()
    per = _Table()
    language = icu.Locale(locale).getLanguage()
    units = _units_available(language)
    widths = ((icu.UNumberUnitWidth.SHORT, "short"), (icu.UNumberUnitWidth.NARROW, "narrow"))
    wide = icu.UNumberUnitWidth.FULL_NAME
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        numbers = icu.NumberFormat.createInstance(icu_locale)
        base = icu.NumberFormatter.withLocale(icu_locale)
        samples = [(amount, numbers.format(amount)) for amount in _plural_samples(name)]
        meter = icu.MeasureUnit.createMeter()
        for unit in units:
            identifier = unit.getIdentifier()
            expansions = [
                _without_number(str(base.unit(unit).unitWidth(wide).formatDouble(a)), n)
                for a, n in samples
            ]
            per_expansions = []
            for amount, _number in samples:
                try:
                    plain = str(base.unit(meter).unitWidth(wide).formatDouble(amount))
                    rate = str(base.unit(meter).perUnit(unit).unitWidth(wide).formatDouble(amount))
                except icu.ICUError:
                    continue
                if rate.startswith(plain):
                    per_expansions.append(rate[len(plain) :].strip())
            for width, width_name in widths:
                for amount, number in samples:
                    formatter = base.unit(unit).unitWidth(width)
                    table.add(
                        _without_number(str(formatter.formatDouble(amount)), number),
                        "unit",
                        identifier,
                        width_name,
                        expansions,
                    )
                    try:
                        plain = str(base.unit(meter).unitWidth(width).formatDouble(amount))
                        rate = str(
                            base.unit(meter).perUnit(unit).unitWidth(width).formatDouble(amount)
                        )
                    except icu.ICUError:
                        continue
                    if rate.startswith(plain) and len(rate) > len(plain):
                        per.add(
                            rate[len(plain) :].strip(),
                            "per-unit",
                            f"per-{identifier}",
                            width_name,
                            per_expansions,
                        )
    # The curated surfaces ICU does not write, with the expansions ICU gives their
    # unit (see icukit.unit_surfaces).
    for surface, target in curated_unit_surfaces(language):
        kind, rows = ("per-unit", per) if target.startswith("per-") else ("unit", table)
        expansions = rows.expansions_of(target) or _wide_names(locale, target)
        rows.add(surface, kind, target, "curated", expansions, "curated")
    return table.rows() + per.rows()


def _wide_names(locale: str, target: str) -> list[str]:
    """ICU's wide names for a unit outside its inventory ("revolutions per minute")."""
    icu_locale = icu.Locale(locale)
    numbers = icu.NumberFormat.createInstance(icu_locale)
    base = icu.NumberFormatter.withLocale(icu_locale).unitWidth(icu.UNumberUnitWidth.FULL_NAME)
    names = []
    for amount in _plural_samples(locale):
        number = numbers.format(amount)
        try:
            if target.startswith("per-"):
                meter = icu.MeasureUnit.createMeter()
                unit = icu.MeasureUnit.forIdentifier(target.removeprefix("per-"))
                plain = str(base.unit(meter).formatDouble(amount))
                rate = str(base.unit(meter).perUnit(unit).formatDouble(amount))
                name = rate[len(plain) :].strip() if rate.startswith(plain) else ""
            else:
                unit = icu.MeasureUnit.forIdentifier(target)
                name = _without_number(str(base.unit(unit).formatDouble(amount)), number)
        except icu.ICUError:
            continue
        if name and name not in names:
            names.append(name)
    return names


@cache
def _name_rows(
    locale: str, names: tuple[str, ...] | None, field: str
) -> tuple[IcuAbbreviation, ...]:
    table = _Table()
    symbol = icu.DateFormatSymbols
    for name in _language_locales(locale, names):
        symbols = icu.DateFormatSymbols(icu.Locale(name))
        for context in (symbol.FORMAT, symbol.STANDALONE):

            def names_at(width, symbols=symbols, context=context):
                return (
                    symbols.getMonths(context, width)
                    if field == "month"
                    else symbols.getWeekdays(context, width)
                )

            wide = names_at(symbol.WIDE)
            for width, width_name in ((symbol.ABBREVIATED, "short"), (symbol.NARROW, "narrow")):
                for index, surface in enumerate(names_at(width)):
                    if not surface:
                        continue
                    number = index + 1 if field == "month" else index
                    table.add(surface, field, str(number), width_name, [wide[index]])
    return table.rows()


@cache
def _era_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    table = _Table()
    eras = _language_eras(icu.Locale(locale).getLanguage(), names)
    wide = {}
    for form, index, width in eras:
        if width == "wide":
            wide.setdefault(index, []).append(form)
    for form, index, width in eras:
        if width == "short":
            table.add(form, "era", str(index), "short", wide.get(index, []))
    return table.rows()


@cache
def _day_period_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    table = _Table()
    language = icu.Locale(locale).getLanguage()
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale("en_US"))
    instants = []
    for hour in (1, 13):
        calendar.clear()
        calendar.set(2026, 0, 3, hour, 0, 0)
        instants.append(calendar.getTime())
    for name in _language_locale_names(language, names):
        wide = icu.SimpleDateFormat("aaaa", icu.Locale(name))
        wide.setTimeZone(icu.TimeZone.getGMT())
        for form, index, narrow in _language_day_periods(language, (name,)):
            table.add(
                form,
                "day-period",
                ("am", "pm")[index],
                "narrow" if narrow else "short",
                [wide.format(instants[index])],
            )
    return table.rows()


@cache
def _zone_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    """Zone abbreviations of two to five capitals, as the time reader takes them."""
    table = _Table()
    styles = (
        (icu.TimeZone.SHORT, icu.TimeZone.LONG),
        (icu.TimeZone.SHORT_GENERIC, icu.TimeZone.LONG_GENERIC),
    )
    locales = [icu.Locale(name) for name in _language_locales(locale, names)]
    for zone_id in icu.TimeZone.createEnumeration():
        zone = icu.TimeZone.createTimeZone(zone_id)
        for icu_locale in locales:
            for short, long in styles:
                for daylight in (False, True):
                    try:
                        form = zone.getDisplayName(daylight, short, icu_locale)
                        expansion = zone.getDisplayName(daylight, long, icu_locale)
                    except icu.ICUError:
                        continue
                    if 2 <= len(form) <= 5 and form.isalpha() and form.isupper():
                        # Keyed by what it names, not by the first of the many zones
                        # sharing it ("EST": Eastern Standard Time).
                        table.add(form, "time-zone", expansion, "short", [expansion])
    return table.rows()


@cache
def _currency_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    table = _Table()
    codes = sorted(unit.getSubtype() for unit in icu.CurrencyUnit.getAvailable("currency"))
    widths = (
        (icu.UNumberUnitWidth.SHORT, "short"),
        (icu.UNumberUnitWidth.NARROW, "narrow"),
        (icu.UNumberUnitWidth.ISO_CODE, "code"),
    )
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        base = icu.NumberFormatter.withLocale(icu_locale).precision(icu.Precision.integer())
        numbers = icu.NumberFormat.createInstance(icu_locale)
        samples = [(amount, numbers.format(amount)) for amount in (1, 2)]
        for code in codes:
            try:
                currency = icu.CurrencyUnit(code)
                surfaces = [
                    (
                        _without_number(
                            str(base.unit(currency).unitWidth(width).formatDouble(2)),
                            samples[1][1],
                        ),
                        width_name,
                    )
                    for width, width_name in widths
                ]
                marks = {surface for surface, _width in surfaces} | {code}
                full = base.unit(currency).unitWidth(icu.UNumberUnitWidth.FULL_NAME)
                expansions = [
                    _currency_name(str(full.formatDouble(a)), n, marks) for a, n in samples
                ]
                for surface, width_name in surfaces:
                    table.add(surface, "currency", code, width_name, expansions)
            except icu.ICUError:
                continue
    # The curated surfaces ICU does not write for the currency ("Rs" for INR); those that
    # are ICU's own elsewhere in the language ("Rs" for PKR) are already listed as ICU's.
    language = icu.Locale(locale).getLanguage()
    for surface, code in curated_currency_surfaces(language):
        if any(r.surface == surface and r.key == code for r in table.rows()):
            continue
        table.add(surface, "currency", code, "curated", _currency_names(locale, code), "curated")
    return table.rows()


def _currency_names(locale: str, code: str) -> list[str]:
    """ICU's names for a currency, singular and plural ("Indian rupee", "Indian rupees")."""
    icu_locale = icu.Locale(locale)
    numbers = icu.NumberFormat.createInstance(icu_locale)
    base = icu.NumberFormatter.withLocale(icu_locale).precision(icu.Precision.integer())
    full = base.unit(icu.CurrencyUnit(code)).unitWidth(icu.UNumberUnitWidth.FULL_NAME)
    return [
        _currency_name(str(full.formatDouble(amount)), numbers.format(amount), {code})
        for amount in (1, 2)
    ]


@cache
def _compact_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    table = _Table()
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        short = icu.CompactDecimalFormat.createInstance(icu_locale, icu.UNumberCompactStyle.SHORT)
        long = icu.CompactDecimalFormat.createInstance(icu_locale, icu.UNumberCompactStyle.LONG)
        numbers = icu.NumberFormat.createInstance(icu_locale)
        for power in range(3, 16):
            for leading in (1, 2):
                value = leading * 10**power
                number = numbers.format(leading)
                surface = _without_number(short.format(value), number)
                expansion = _without_number(long.format(value), number)
                if surface and not any(character.isdigit() for character in surface):
                    table.add(surface, "compact", f"1e{power}", "short", [expansion])
    return table.rows()


_RELATIVE_UNITS = ("SECOND", "MINUTE", "HOUR", "DAY", "WEEK", "MONTH", "QUARTER", "YEAR")


def _unit_word(short: str, long: str) -> tuple[str, str]:
    """The words where two phrasings of one relative time differ ("hr." / "hours")."""
    a, b = short.split(), long.split()
    while a and b and a[0] == b[0]:
        a, b = a[1:], b[1:]
    while a and b and a[-1] == b[-1]:
        a, b = a[:-1], b[:-1]
    return " ".join(a), " ".join(b)


@cache
def _relative_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    table = _Table()
    style = icu.UDateRelativeDateTimeFormatterStyle
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        numbers = icu.NumberFormat.createInstance(icu_locale)

        def formatter(which, icu_locale=icu_locale):
            return icu.RelativeDateTimeFormatter(
                icu_locale,
                icu.NumberFormat.createInstance(icu_locale),
                which,
                icu.UDisplayContext.CAPITALIZATION_NONE,
            )

        long = formatter(style.LONG)
        for which, width_name in ((style.SHORT, "short"), (style.NARROW, "narrow")):
            other = formatter(which)
            for member in _RELATIVE_UNITS:
                unit = getattr(icu.URelativeDateTimeUnit, member)
                for amount in (1, 2, -1, -2):
                    number = numbers.format(abs(amount))
                    surface, expansion = _unit_word(
                        _without_number(other.formatNumeric(amount, unit), number),
                        _without_number(long.formatNumeric(amount, unit), number),
                    )
                    if surface and surface != expansion:
                        table.add(surface, "relative-unit", member.lower(), width_name, [expansion])
    return table.rows()


def _region_names(icu_locale, key: str) -> dict[str, str]:
    """A locale's table of territory names under ``key`` ("Countries%short"), by code."""
    try:
        table = icu.ResourceBundle("ICUDATA-region", icu_locale).get(key)
    except icu.ICUError:
        return {}
    return {table.get(i).getKey(): table.get(i).getString() for i in range(table.getSize())}


@cache
def _territory_rows(locale: str, names: tuple[str, ...] | None) -> tuple[IcuAbbreviation, ...]:
    """Region codes and CLDR's short territory names, expanded by the territory's names.

    The codes are ICU's territories and groupings ("EU", "UN") that are letters
    ("419" and "001" are not abbreviations); the short names are CLDR's ("UK", "US").
    """
    table = _Table()
    kinds = (icu.URegionType.TERRITORY, icu.URegionType.GROUPING)
    codes = sorted(
        str(code) for kind in kinds for code in icu.Region.getAvailable(kind) if str(code).isalpha()
    )
    for name in _language_locales(locale, names):
        icu_locale = icu.Locale(name)
        short = _region_names(icu_locale, "Countries%short")
        variant = _region_names(icu_locale, "Countries%variant")
        for code in codes:
            wide = icu.Locale("und_" + code).getDisplayCountry(icu_locale)
            if not wide or wide == code:
                continue
            expansions = [wide] + ([variant[code]] if code in variant else [])
            table.add(code, "territory", code, "code", expansions)
            if code in short:
                table.add(short[code], "territory", code, "short", expansions)
    return table.rows()


_GENERATORS = {
    "unit": lambda locale, names: tuple(r for r in _unit_rows(locale, names) if r.kind == "unit"),
    "per-unit": lambda locale, names: tuple(
        r for r in _unit_rows(locale, names) if r.kind == "per-unit"
    ),
    "month": lambda locale, names: _name_rows(locale, names, "month"),
    "weekday": lambda locale, names: _name_rows(locale, names, "weekday"),
    "era": _era_rows,
    "day-period": _day_period_rows,
    "time-zone": _zone_rows,
    "currency": _currency_rows,
    "compact": _compact_rows,
    "relative-unit": _relative_rows,
    "territory": _territory_rows,
}


def icu_abbreviations(
    locale: str,
    *,
    locales: Iterable[str] | None = None,
    kinds: Iterable[str] | None = None,
) -> tuple[IcuAbbreviation, ...]:
    """The short forms ICU writes in ``locale``'s language, with their expansions.

    ``locales`` chooses the other locales of the language read, as for the readers
    (``None``: all of them); ``kinds`` narrows the kinds (see ``ABBREVIATION_KINDS``).
    A kind's rows are generated once per locale and choice, then cached.
    """
    names = _locale_selection(locale, locales)
    wanted = ABBREVIATION_KINDS if kinds is None else tuple(kinds)
    unknown = sorted(set(wanted) - set(ABBREVIATION_KINDS))
    if unknown:
        raise ValueError(f"unknown abbreviation kinds: {unknown}")
    rows: list[IcuAbbreviation] = []
    for kind in wanted:
        rows.extend(_GENERATORS[kind](locale, names))
    return tuple(rows)
