"""Geographic region and territory information.

Query countries, territories, continents, and their relationships
using ICU's region data.

Key Features:
    * List all regions by type (territory, continent, etc.)
    * Get region info (code, numeric code, containing region)
    * Query containment hierarchy (which regions contain which)

Region Types:
    * TERRITORY - Countries and territories (US, FR, JP, etc.)
    * CONTINENT - Continents (Africa, Americas, Asia, Europe, Oceania)
    * SUBCONTINENT - Subcontinental regions (Northern America, Western Europe)
    * GROUPING - Economic/political groupings (EU, UN, etc.)
    * WORLD - The world (001)

Example:
    List and query regions::

        >>> from icukit import list_regions, get_region_info
        >>>
        >>> # List all territories (countries)
        >>> territories = list_regions('territory')
        >>> len(territories)
        257
        >>>
        >>> # Get info about a region
        >>> info = get_region_info('US')
        >>> info['name']
        'United States'
        >>> info['numeric_code']
        840
        >>> info['containing_region']
        '021'  # Northern America
"""

from typing import Any, Dict, List, Optional

import icu
from icu import URegionType

from .errors import RegionError

# Build region type mapping dynamically from URegionType enum
# Excludes UNKNOWN (not useful) and DEPRECATED (historical)
_REGION_TYPES = {
    name.lower(): getattr(URegionType, name)
    for name in dir(URegionType)
    if not name.startswith("_") and name not in ("UNKNOWN", "DEPRECATED")
}


def list_regions(region_type: str = "territory") -> List[str]:
    """List all regions of a given type.

    Args:
        region_type: Type of regions to list. One of:
            'territory', 'continent', 'subcontinent', 'grouping', 'world'.
            Defaults to 'territory' (countries).

    Returns:
        List of region codes sorted alphabetically.

    Raises:
        RegionError: If region_type is invalid.

    Example:
        >>> territories = list_regions('territory')
        >>> 'US' in territories
        True
        >>> continents = list_regions('continent')
        >>> len(continents)
        5
    """
    rtype = region_type.lower()
    if rtype not in _REGION_TYPES:
        valid = ", ".join(_REGION_TYPES.keys())
        raise RegionError(f"Invalid region type: {region_type}. Valid types: {valid}")

    regions = icu.Region.getAvailable(_REGION_TYPES[rtype])
    return sorted(list(regions))


def list_regions_info(region_type: str = "territory") -> List[Dict[str, Any]]:
    """List all regions with their info.

    Args:
        region_type: Type of regions to list.

    Returns:
        List of dicts with region info.

    Example:
        >>> regions = list_regions_info('territory')
        >>> us = next(r for r in regions if r['code'] == 'US')
        >>> us['numeric_code']
        840
    """
    codes = list_regions(region_type)
    return [get_region_info(code) for code in codes]


def get_region_info(code: str, extended: bool = False) -> Optional[Dict[str, Any]]:
    """Get information about a region.

    Args:
        code: Region code (e.g., 'US', 'FR', '001' for World).
        extended: Include extended attributes (contained_regions).

    Returns:
        Dict with region info, or None if not found.

    Example:
        >>> info = get_region_info('US')
        >>> info['code']
        'US'
        >>> info['numeric_code']
        840
        >>> info['type']
        'territory'
        >>> info = get_region_info('019', extended=True)
        >>> 'contained_regions' in info['extended']
        True
    """
    try:
        region = icu.Region.getInstance(code)
        rtype = region.getType()

        # Map numeric type back to string
        type_name = "unknown"
        for name, val in _REGION_TYPES.items():
            if val == rtype:
                type_name = name
                break

        # Get containing region
        containing = region.getContainingRegion()
        containing_code = containing.getRegionCode() if containing else None

        # Get display name via Locale
        display_name = _get_region_display_name(code)

        info = {
            "code": region.getRegionCode(),
            "numeric_code": region.getNumericCode(),
            "name": display_name,
            "type": type_name,
            "containing_region": containing_code,
        }

        if extended:
            contained = list(region.getContainedRegions())
            info["extended"] = {
                "contained_regions": contained if contained else None,
            }

        return info
    except icu.ICUError:
        return None


def get_contained_regions(code: str) -> List[str]:
    """Get regions directly contained by a region.

    Args:
        code: Region code (e.g., '001' for World, '019' for Americas).

    Returns:
        List of contained region codes.

    Example:
        >>> # What's in the Americas?
        >>> get_contained_regions('019')
        ['005', '013', '021', '029']  # South/Central/North America, Caribbean
    """
    try:
        region = icu.Region.getInstance(code)
        contained = region.getContainedRegions()
        return sorted(list(contained)) if contained else []
    except icu.ICUError:
        return []


def _get_region_display_name(code: str, display_locale: str = "en") -> str:
    """Get the display name for a region code.

    Args:
        code: Region code.
        display_locale: Locale for display name.

    Returns:
        Display name string.
    """
    try:
        # Use Locale to get region display name
        loc = icu.Locale(f"und_{code}")  # und = undefined language
        display_loc = icu.Locale(display_locale)
        name = loc.getDisplayCountry(display_loc)
        return name if name else code
    except icu.ICUError:
        return code


def list_region_types() -> List[Dict[str, str]]:
    """List available region types.

    Returns:
        List of dicts with type name and description.

    Example:
        >>> types = list_region_types()
        >>> types[0]
        {'type': 'continent', 'description': 'Continents (Africa, Americas, ...)'}
    """
    return [
        {"type": "territory", "description": "Countries and territories (US, FR, JP, ...)"},
        {
            "type": "continent",
            "description": "Continents (Africa, Americas, Asia, Europe, Oceania)",
        },
        {"type": "subcontinent", "description": "Subcontinental regions (Northern America, ...)"},
        {"type": "grouping", "description": "Economic/political groupings (EU, UN, ...)"},
        {"type": "world", "description": "The world (001)"},
    ]
