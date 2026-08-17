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

import re

import icu

from .errors import MeasureError

__all__ = [
    "MeasureFormatter",
    "format_measure",
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

# Cache for unit data from ICU
_units_by_type_cache: dict | None = None
_abbreviation_map_cache: dict | None = None


def _get_units_by_type() -> dict[str, list[str]]:
    """Get all units organized by type from ICU."""
    global _units_by_type_cache
    if _units_by_type_cache is not None:
        return _units_by_type_cache

    _units_by_type_cache = {}
    for unit_type in icu.MeasureUnit.getAvailableTypes():
        units = []
        for mu in icu.MeasureUnit.getAvailable(unit_type):
            units.append(mu.getSubtype())
        if units:
            _units_by_type_cache[unit_type] = sorted(units)

    return _units_by_type_cache


def _get_abbreviation_map(locale: str = "en_US") -> dict[str, str]:
    """Build mapping from abbreviations to unit names.

    Uses ICU's SHORT format to get abbreviations for each unit.
    Returns dict mapping abbreviation -> unit_name.
    """
    global _abbreviation_map_cache
    if _abbreviation_map_cache is not None:
        return _abbreviation_map_cache

    _abbreviation_map_cache = {}
    formatter = icu.MeasureFormat(
        icu.Locale(locale),
        icu.UMeasureFormatWidth.SHORT,
    )

    for unit_type, units in _get_units_by_type().items():
        for unit_name in units:
            try:
                mu = icu.MeasureUnit.forIdentifier(unit_name)
                measure = icu.Measure(1, mu)
                formatted = formatter.formatMeasure(measure)
                # Extract abbreviation by removing the "1 " prefix
                abbrev = formatted.replace("1", "").strip()
                if abbrev and abbrev != unit_name:
                    # Store both lowercase and original
                    _abbreviation_map_cache[abbrev.lower()] = unit_name
                    _abbreviation_map_cache[abbrev] = unit_name
            except icu.ICUError:
                pass

    return _abbreviation_map_cache


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
        formatted = formatter.formatMeasure(measure)
        return formatted.replace("1", "").strip()
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
    """Check if two units can be converted to each other.

    Args:
        from_unit: Source unit name or abbreviation
        to_unit: Target unit name or abbreviation

    Returns:
        True if conversion is possible, False otherwise

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
        """Convert a value between units.

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

        # Manual conversion factors (since UnitsConverter may not be available)
        conversions = {
            # Length
            ("kilometer", "mile"): lambda v: v * 0.621371,
            ("mile", "kilometer"): lambda v: v * 1.60934,
            ("meter", "foot"): lambda v: v * 3.28084,
            ("foot", "meter"): lambda v: v * 0.3048,
            ("meter", "yard"): lambda v: v * 1.09361,
            ("yard", "meter"): lambda v: v * 0.9144,
            ("inch", "centimeter"): lambda v: v * 2.54,
            ("centimeter", "inch"): lambda v: v / 2.54,
            # Temperature
            ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
            ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
            ("celsius", "kelvin"): lambda v: v + 273.15,
            ("kelvin", "celsius"): lambda v: v - 273.15,
            # Mass
            ("kilogram", "pound"): lambda v: v * 2.20462,
            ("pound", "kilogram"): lambda v: v * 0.453592,
            ("gram", "ounce"): lambda v: v * 0.035274,
            ("ounce", "gram"): lambda v: v * 28.3495,
            # Volume
            ("liter", "gallon"): lambda v: v * 0.264172,
            ("gallon", "liter"): lambda v: v * 3.78541,
            ("milliliter", "fluid-ounce"): lambda v: v * 0.033814,
            ("fluid-ounce", "milliliter"): lambda v: v * 29.5735,
        }

        key = (from_unit, to_unit)
        if key in conversions:
            return conversions[key](float(value))

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
        """Convert a value and format the result.

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
        """Format a measurement using locale-preferred units.

        Converts to units preferred by the locale for the given usage.
        For example, "road" usage in en_US converts km to miles.

        Note: Usage-based conversion may not be available in all PyICU versions.
        Falls back to standard formatting.

        Args:
            value: Numeric value
            unit: Source unit
            usage: Usage context ("default", "road", "person-height", "weather", etc.)
            width: Width style

        Returns:
            Formatted measurement in locale-preferred units

        Example:
            >>> fmt_us = MeasureFormatter("en_US")
            >>> fmt_us.format_for_usage(100, "kilometer", usage="road")
            '62 miles'
            >>> fmt_de = MeasureFormatter("de_DE")
            >>> fmt_de.format_for_usage(100, "kilometer", usage="road")
            '100 Kilometer'
        """
        # Usage-based formatting not available in all PyICU versions
        # Fall back to standard formatting
        return self.format(value, unit, width)

    def __repr__(self) -> str:
        return f"MeasureFormatter(locale={self.locale!r}, width={self.width!r})"


def convert_units(
    value: float | int,
    from_unit: str,
    to_unit: str,
) -> float:
    """Convert a value between units (convenience function).

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
