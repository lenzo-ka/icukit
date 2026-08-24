"""
Locale-aware unit measurement formatting.

ICU's MeasureFormat formats measurements with proper unit names and
locale-specific conventions.

Unit Types:
    length      - meter, kilometer, mile, foot, inch, yard, etc.
    mass        - gram, kilogram, pound, ounce, etc.
    temperature - celsius, fahrenheit, kelvin
    speed       - kilometer-per-hour, mile-per-hour, meter-per-second
    volume      - liter, milliliter, gallon, cup, tablespoon
    area        - square-meter, square-kilometer, acre, hectare
    duration    - second, minute, hour, day, week, month, year
    pressure    - hectopascal, millibar, inch-ofhg
    energy      - joule, kilocalorie, kilojoule
    power       - watt, kilowatt, horsepower
    digital     - byte, kilobyte, megabyte, gigabyte, terabyte

Width Styles:
    WIDE   - "5 kilometers" (full unit names)
    SHORT  - "5 km" (abbreviated)
    NARROW - "5km" (minimal, no space)

Example:
    >>> from icukit import MeasureFormatter
    >>>
    >>> fmt = MeasureFormatter("en_US")
    >>> fmt.format(5.5, "kilometer")
    '5.5 kilometers'
    >>> fmt.format(100, "fahrenheit", width="SHORT")
    '100°F'
    >>>
    >>> fmt_de = MeasureFormatter("de_DE")
    >>> fmt_de.format(5.5, "kilometer")
    '5,5 Kilometer'
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

import icu

from ._offsets import boundary_maps
from .errors import MeasureError

__all__ = [
    "MeasureFormatter",
    "format_measure",
    "format_preferred",
    "convert_units",
    "can_convert",
    "get_unit_info",
    "get_units_by_type",
    "list_units",
    "list_unit_types",
    "resolve_unit",
    "get_unit_abbreviation",
    "WIDTH_WIDE",
    "WIDTH_SHORT",
    "WIDTH_NARROW",
]

# Width constants
WIDTH_WIDE = "WIDE"
WIDTH_SHORT = "SHORT"
WIDTH_NARROW = "NARROW"

_WIDTH_MAP = {
    WIDTH_WIDE: icu.UMeasureFormatWidth.WIDE,
    WIDTH_SHORT: icu.UMeasureFormatWidth.SHORT,
    WIDTH_NARROW: icu.UMeasureFormatWidth.NARROW,
}

_NUMBER_UNIT_WIDTH_MAP = {
    WIDTH_WIDE: icu.UNumberUnitWidth.FULL_NAME,
    WIDTH_SHORT: icu.UNumberUnitWidth.SHORT,
    WIDTH_NARROW: icu.UNumberUnitWidth.NARROW,
}

_LOCALE_PATTERN = re.compile(
    r"^(?:root|[A-Za-z]{2,8})(?:[-_][A-Za-z0-9]{1,8})*"
    r"(?:\.[A-Za-z0-9-]+)?"
    r"(?:@[A-Za-z0-9][A-Za-z0-9_-]*(?:=[A-Za-z0-9][A-Za-z0-9_-]*)?"
    r"(?:;[A-Za-z0-9][A-Za-z0-9_-]*(?:=[A-Za-z0-9][A-Za-z0-9_-]*)?)*)?$"
)

# Cache for unit data from ICU
_units_by_type_cache: dict[str, list[str]] | None = None
_abbreviation_map_cache: dict[str, str] | None = None


def _get_units_by_type() -> dict[str, list[str]]:
    """Get all units organized by type from ICU."""
    global _units_by_type_cache
    if _units_by_type_cache is not None:
        return _units_by_type_cache

    # Assign the (empty) dict to the global before populating so a mid-loop
    # ICU failure memoizes the partial state, matching prior cache semantics.
    units_by_type: dict[str, list[str]] = {}
    _units_by_type_cache = units_by_type
    for unit_type in icu.MeasureUnit.getAvailableTypes():
        units = []
        for mu in icu.MeasureUnit.getAvailable(unit_type):
            units.append(mu.getSubtype())
        if units:
            units_by_type[unit_type] = sorted(units)

    return _units_by_type_cache


def _get_abbreviation_map(locale: str = "en_US") -> dict[str, str]:
    """Build mapping from abbreviations to unit names.

    Uses ICU's SHORT format to get abbreviations for each unit.
    Returns dict mapping abbreviation -> unit_name.
    """
    global _abbreviation_map_cache
    if _abbreviation_map_cache is not None:
        return _abbreviation_map_cache

    # Assign the (empty) dict to the global before populating so a mid-build
    # ICU failure memoizes the partial state, matching prior cache semantics.
    abbreviation_map: dict[str, str] = {}
    _abbreviation_map_cache = abbreviation_map
    formatter = icu.MeasureFormat(
        icu.Locale(locale),
        icu.UMeasureFormatWidth.SHORT,
    )

    for _unit_type, units in _get_units_by_type().items():
        for unit_name in units:
            try:
                mu = icu.MeasureUnit.forIdentifier(unit_name)
                measure = icu.Measure(1, mu)
                abbrev = _format_unit_without_value(formatter, measure)
                if abbrev and abbrev != unit_name:
                    # Store both lowercase and original
                    abbreviation_map[abbrev.lower()] = unit_name
                    abbreviation_map[abbrev] = unit_name
            except icu.ICUError:
                pass

    return _abbreviation_map_cache


_CONVERSIONS: dict[tuple[str, str], Callable[[float], float]] = {
    ("meter", "kilometer"): lambda value: value / 1000,
    ("kilometer", "meter"): lambda value: value * 1000,
    ("kilometer", "mile"): lambda value: value * 0.621371,
    ("mile", "kilometer"): lambda value: value * 1.60934,
    ("meter", "foot"): lambda value: value * 3.28084,
    ("foot", "meter"): lambda value: value * 0.3048,
    ("meter", "yard"): lambda value: value * 1.09361,
    ("yard", "meter"): lambda value: value * 0.9144,
    ("inch", "centimeter"): lambda value: value * 2.54,
    ("centimeter", "inch"): lambda value: value / 2.54,
    ("celsius", "fahrenheit"): lambda value: value * 9 / 5 + 32,
    ("fahrenheit", "celsius"): lambda value: (value - 32) * 5 / 9,
    ("celsius", "kelvin"): lambda value: value + 273.15,
    ("kelvin", "celsius"): lambda value: value - 273.15,
    ("kilogram", "pound"): lambda value: value * 2.20462,
    ("pound", "kilogram"): lambda value: value * 0.453592,
    ("gram", "ounce"): lambda value: value * 0.035274,
    ("ounce", "gram"): lambda value: value * 28.3495,
    ("liter", "gallon"): lambda value: value * 0.264172,
    ("gallon", "liter"): lambda value: value * 3.78541,
    ("milliliter", "fluid-ounce"): lambda value: value * 0.033814,
    ("fluid-ounce", "milliliter"): lambda value: value * 29.5735,
}


def _format_unit_without_value(formatter: icu.MeasureFormat, measure: icu.Measure) -> str:
    """Format ``measure`` and remove only its numeric value field."""
    position = icu.FieldPosition(icu.NumberFormat.kIntegerField)
    formatted = formatter.formatMeasure(measure, position)
    _, u16_to_cp = boundary_maps(formatted)
    start = u16_to_cp[position.getBeginIndex()]
    end = u16_to_cp[position.getEndIndex()]

    def is_wrapper(character: str) -> bool:
        return character.isspace() or unicodedata.category(character) == "Cf"

    while start > 0 and is_wrapper(formatted[start - 1]):
        start -= 1
    while end < len(formatted) and is_wrapper(formatted[end]):
        end += 1
    return (formatted[:start] + formatted[end:]).strip()


def resolve_unit(unit: str) -> str:
    """Resolve a unit name or abbreviation to the canonical ICU unit name.

    Args:
        unit: Unit name or abbreviation (e.g., "km", "kilometer", "mi")

    Returns:
        Canonical ICU unit name (e.g., "kilometer", "mile")

    Example:
        >>> resolve_unit("km")
        'kilometer'
        >>> resolve_unit("kilometer")
        'kilometer'
    """
    # First try as-is (already canonical)
    try:
        icu.MeasureUnit.forIdentifier(unit)
        return unit
    except icu.ICUError:
        pass

    # Try abbreviation lookup
    abbrev_map = _get_abbreviation_map()
    if unit in abbrev_map:
        return abbrev_map[unit]
    if unit.lower() in abbrev_map:
        return abbrev_map[unit.lower()]

    raise MeasureError(f"Unknown unit: {unit}")


def get_unit_abbreviation(unit: str, locale: str = "en_US") -> str:
    """Get the abbreviation for a unit.

    Args:
        unit: Unit name (e.g., "kilometer")
        locale: Locale for abbreviation

    Returns:
        Abbreviated form (e.g., "km")
    """
    formatter = icu.MeasureFormat(
        icu.Locale(locale),
        icu.UMeasureFormatWidth.SHORT,
    )
    try:
        mu = icu.MeasureUnit.forIdentifier(resolve_unit(unit))
        measure = icu.Measure(1, mu)
        return _format_unit_without_value(formatter, measure)
    except icu.ICUError as e:
        raise MeasureError(f"Cannot get abbreviation for {unit}: {e}") from e


def get_unit_info(unit: str) -> dict:
    """Get information about a unit.

    Args:
        unit: Unit name or abbreviation

    Returns:
        Dict with unit info: type, identifier, complexity

    Example:
        >>> get_unit_info("mile")
        {'identifier': 'mile', 'type': 'length', 'complexity': 'single'}
    """
    unit = resolve_unit(unit)
    try:
        mu = icu.MeasureUnit.forIdentifier(unit)
        unit_type = mu.getType()
        complexity = mu.getComplexity()

        # Map complexity enum to string
        complexity_map = {
            icu.UMeasureUnitComplexity.SINGLE: "single",
            icu.UMeasureUnitComplexity.COMPOUND: "compound",
            icu.UMeasureUnitComplexity.MIXED: "mixed",
        }

        return {
            "identifier": unit,
            "type": unit_type,
            "complexity": complexity_map.get(complexity, str(complexity)),
        }
    except icu.ICUError as e:
        raise MeasureError(f"Cannot get info for {unit}: {e}") from e


def can_convert(from_unit: str, to_unit: str) -> bool:
    """Check whether ICU classifies two units as the same unit type.

    This checks compatibility only; it does not guarantee that the limited
    :meth:`MeasureFormatter.convert` helper supports the pair.

    Args:
        from_unit: Source unit name or abbreviation
        to_unit: Target unit name or abbreviation

    Returns:
        True if the units have the same ICU unit type, False otherwise

    Example:
        >>> can_convert("kilometer", "mile")
        True
        >>> can_convert("kilometer", "celsius")
        False
    """
    from_unit = resolve_unit(from_unit)
    to_unit = resolve_unit(to_unit)

    try:
        from_mu = icu.MeasureUnit.forIdentifier(from_unit)
        to_mu = icu.MeasureUnit.forIdentifier(to_unit)
        # Units can convert if they're of the same type
        return from_mu.getType() == to_mu.getType()
    except icu.ICUError:
        return False


def get_units_by_type() -> dict[str, list[str]]:
    """Get all units organized by type.

    Returns:
        Dict mapping unit type to list of unit names.

    Example:
        >>> units = get_units_by_type()
        >>> "meter" in units["length"]
        True
    """
    return _get_units_by_type()


def list_unit_types() -> list[str]:
    """List available unit types.

    Returns:
        List of unit type names (length, mass, temperature, etc.)
    """
    return sorted(_get_units_by_type().keys())


def list_units(unit_type: str | None = None) -> list[str]:
    """List available units.

    Args:
        unit_type: Optional type to filter by (e.g., "length", "mass")

    Returns:
        List of unit names
    """
    units_by_type = _get_units_by_type()
    if unit_type:
        unit_type = unit_type.lower()
        if unit_type not in units_by_type:
            raise MeasureError(f"Unknown unit type: {unit_type}. Valid: {list_unit_types()}")
        return sorted(units_by_type[unit_type])

    # Return all units
    all_units = []
    for units in units_by_type.values():
        all_units.extend(units)
    return sorted(set(all_units))


class MeasureFormatter:
    """Locale-aware measurement formatter.

    Example:
        >>> fmt = MeasureFormatter("en_US")
        >>> fmt.format(5.5, "kilometer")
        '5.5 kilometers'
        >>> fmt.format(100, "fahrenheit", width="SHORT")
        '100°F'
    """

    def __init__(self, locale: str = "en_US", width: str = WIDTH_WIDE):
        """Create a MeasureFormatter.

        Args:
            locale: Locale code (e.g., "en_US", "de_DE")
            width: Default width style (WIDE, SHORT, NARROW)
        """
        if not isinstance(locale, str) or not _LOCALE_PATTERN.fullmatch(locale):
            raise MeasureError(f"Malformed locale: {locale!r}")

        self.locale = locale
        self.width = width
        self._icu_locale = icu.Locale(locale)
        self._formatters: dict = {}

    def format(
        self,
        value: float | int,
        unit: str,
        width: str | None = None,
    ) -> str:
        """Format a measurement.

        Args:
            value: Numeric value
            unit: Unit name or abbreviation (e.g., "kilometer", "km", "fahrenheit", "F")
            width: Width style (WIDE, SHORT, NARROW), overrides default

        Returns:
            Formatted measurement string

        Example:
            >>> fmt.format(5.5, "kilometer")
            '5.5 kilometers'
            >>> fmt.format(5.5, "km")  # abbreviation works too
            '5.5 kilometers'
            >>> fmt.format(100, "fahrenheit", width="SHORT")
            '100°F'
        """
        width = width or self.width
        formatter = self._get_formatter(width)
        unit = resolve_unit(unit)

        try:
            measure = icu.Measure(float(value), icu.MeasureUnit.forIdentifier(unit))
            return formatter.formatMeasure(measure)
        except icu.ICUError as e:
            raise MeasureError(f"Failed to format {value} {unit}: {e}") from e

    def format_range(
        self,
        low: float | int,
        high: float | int,
        unit: str,
        width: str | None = None,
    ) -> str:
        """Format a measurement range.

        Args:
            low: Low value
            high: High value
            unit: Unit name or abbreviation
            width: Width style

        Returns:
            Formatted range (e.g., "5-10 kilometers")
        """
        width = width or self.width
        formatter = self._get_formatter(width)
        unit = resolve_unit(unit)

        try:
            mu = icu.MeasureUnit.forIdentifier(unit)
            measure_high = icu.Measure(float(high), mu)
            # Format range as "low-high unit" since formatMeasureRange may not be available
            formatted_high = formatter.formatMeasure(measure_high)
            # Replace the number with the range
            return re.sub(r"[\d.,]+", f"{low}–{high}", formatted_high, count=1)
        except icu.ICUError as e:
            raise MeasureError(f"Failed to format range {low}-{high} {unit}: {e}") from e

    def _get_formatter(self, width: str):
        """Get or create a formatter for the given width."""
        if width not in _WIDTH_MAP:
            raise MeasureError(f"Invalid width: {width}. Valid: {list(_WIDTH_MAP.keys())}")

        if width not in self._formatters:
            self._formatters[width] = icu.MeasureFormat(
                self._icu_locale,
                _WIDTH_MAP[width],
            )
        return self._formatters[width]

    def convert(
        self,
        value: float | int,
        from_unit: str,
        to_unit: str,
    ) -> float:
        """Convert a value using a limited set of explicit conversion factors.

        This helper is not reflective or ICU-driven. PyICU does not expose ICU's
        general unit converter, so only the pairs listed by this implementation are
        supported. Unit compatibility reported by :func:`can_convert` does not imply
        that this helper can convert a particular pair.

        Args:
            value: Numeric value to convert
            from_unit: Source unit or abbreviation (e.g., "kilometer", "km")
            to_unit: Target unit or abbreviation (e.g., "mile", "mi")

        Returns:
            Converted value

        Example:
            >>> fmt.convert(10, "kilometer", "mile")
            6.21371...
            >>> fmt.convert(10, "km", "mi")  # abbreviations work too
            6.21371...
            >>> fmt.convert(100, "celsius", "fahrenheit")
            212.0
        """
        from_unit = resolve_unit(from_unit)
        to_unit = resolve_unit(to_unit)

        key = (from_unit, to_unit)
        if key in _CONVERSIONS:
            return _CONVERSIONS[key](float(value))

        # If same unit, return as-is
        if from_unit == to_unit:
            return float(value)

        raise MeasureError(f"Cannot convert {from_unit} to {to_unit}: conversion not supported")

    def convert_and_format(
        self,
        value: float | int,
        from_unit: str,
        to_unit: str,
        width: str | None = None,
    ) -> str:
        """Convert with the limited explicit factors and format the result.

        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit
            width: Width style for formatting

        Returns:
            Formatted converted measurement

        Example:
            >>> fmt.convert_and_format(10, "kilometer", "mile")
            '6.21371 miles'
        """
        converted = self.convert(value, from_unit, to_unit)
        return self.format(converted, to_unit, width)

    def format_sequence(
        self,
        measures: list[tuple[float | int, str]],
        width: str | None = None,
    ) -> str:
        """Format a sequence of measurements (compound units).

        Args:
            measures: List of (value, unit) tuples
            width: Width style

        Returns:
            Formatted compound measurement

        Example:
            >>> fmt.format_sequence([(5, "foot"), (10, "inch")])
            '5 feet, 10 inches'
            >>> fmt.format_sequence([(1, "hour"), (30, "minute")])
            '1 hour, 30 minutes'
        """
        width = width or self.width
        formatter = self._get_formatter(width)

        try:
            # Format each measure individually and join
            # (formatMeasures doesn't work in some PyICU versions)
            parts = []
            for value, unit in measures:
                unit = resolve_unit(unit)
                measure = icu.Measure(float(value), icu.MeasureUnit.forIdentifier(unit))
                parts.append(formatter.formatMeasure(measure))
            return " ".join(parts)
        except icu.ICUError as e:
            raise MeasureError(f"Failed to format sequence: {e}") from e

    def format_for_usage(
        self,
        value: float | int,
        unit: str,
        usage: str = "default",
        width: str | None = None,
    ) -> str:
        """Format a measurement in the locale's preferred unit for a usage.

        ICU and CLDR choose the output unit from ``locale`` and ``usage``. This returns
        formatted text, not a numeric conversion to a caller-specified target unit.
        If ICU does not recognize a nonempty usage, it falls back to the locale's
        default unit preferences.

        Args:
            value: Numeric value
            unit: Source unit
            usage: Nonempty usage context ("default", "road", "person-height", etc.)
            width: Width style

        Returns:
            Locale- and usage-preferred formatted measurement

        Example:
            >>> fmt_us = MeasureFormatter("en_US")
            >>> fmt_us.format_for_usage(100, "kilometer", usage="road")
            '62 miles'
            >>> fmt_de = MeasureFormatter("de_DE")
            >>> fmt_de.format_for_usage(100, "kilometer", usage="road")
            '100 Kilometer'
        """
        if not isinstance(usage, str) or not usage.strip():
            raise MeasureError("Usage must be a nonempty string")

        width = width or self.width
        if width not in _NUMBER_UNIT_WIDTH_MAP:
            raise MeasureError(f"Invalid width: {width}. Valid: {list(_WIDTH_MAP.keys())}")

        unit = resolve_unit(unit)
        try:
            formatter = (
                icu.NumberFormatter.withLocale(self._icu_locale)
                .unit(icu.MeasureUnit.forIdentifier(unit))
                .usage(usage)
                .unitWidth(_NUMBER_UNIT_WIDTH_MAP[width])
            )
            return formatter.formatDouble(float(value))
        except (icu.ICUError, icu.InvalidArgsError) as e:
            raise MeasureError(f"Failed to format {value} {unit} for usage {usage}: {e}") from e

    def __repr__(self) -> str:
        return f"MeasureFormatter(locale={self.locale!r}, width={self.width!r})"


def convert_units(
    value: float | int,
    from_unit: str,
    to_unit: str,
) -> float:
    """Convert a value using the limited explicit factors.

    This convenience function is not reflective or ICU-driven. See
    :meth:`MeasureFormatter.convert` for the supported-pair behavior.

    Args:
        value: Numeric value to convert
        from_unit: Source unit (e.g., "kilometer")
        to_unit: Target unit (e.g., "mile")

    Returns:
        Converted value

    Example:
        >>> convert_units(10, "kilometer", "mile")
        6.21371...
        >>> convert_units(100, "celsius", "fahrenheit")
        212.0
    """
    return MeasureFormatter().convert(value, from_unit, to_unit)


def format_preferred(
    value: float | int,
    unit: str,
    locale: str,
    usage: str,
) -> str:
    """Format a measurement in ICU's locale- and usage-preferred unit.

    ICU and CLDR choose the output unit. The result is formatted text, not a numeric
    conversion to a caller-specified target unit. If ICU does not recognize a
    nonempty usage, it falls back to the locale's default unit preferences.

    Args:
        value: Numeric value
        unit: Source unit name or abbreviation
        locale: Locale code
        usage: Nonempty usage context (for example, "road" or "person-height")

    Returns:
        Locale- and usage-preferred formatted measurement

    Example:
        >>> format_preferred(100, "kilometer", "en_US", "road")
        '62 mi'
    """
    return MeasureFormatter(locale, WIDTH_SHORT).format_for_usage(value, unit, usage)


def format_measure(
    value: float | int,
    unit: str,
    locale: str = "en_US",
    width: str = WIDTH_WIDE,
) -> str:
    """Format a measurement (convenience function).

    Args:
        value: Numeric value
        unit: Unit name
        locale: Locale code
        width: Width style (WIDE, SHORT, NARROW)

    Returns:
        Formatted measurement string
    """
    return MeasureFormatter(locale, width).format(value, unit)
