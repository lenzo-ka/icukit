"""Tests for region module and CLI."""

import subprocess
import sys

import pytest

from icukit import (
    RegionError,
    get_contained_regions,
    get_region_info,
    list_region_types,
    list_regions,
    list_regions_info,
)


class TestRegionLibrary:
    """Tests for region library functions."""

    def test_list_regions_default(self):
        """Test listing territories (default)."""
        regions = list_regions()
        assert len(regions) > 200  # Should have 250+ territories
        assert "US" in regions
        assert "FR" in regions
        assert "JP" in regions

    def test_list_regions_continent(self):
        """Test listing continents."""
        regions = list_regions("continent")
        assert len(regions) == 5  # Africa, Americas, Asia, Europe, Oceania
        assert "002" in regions  # Africa
        assert "019" in regions  # Americas

    def test_list_regions_subcontinent(self):
        """Test listing subcontinents."""
        regions = list_regions("subcontinent")
        assert len(regions) > 10
        assert "021" in regions  # Northern America

    def test_list_regions_invalid_type(self):
        """Test invalid region type raises error."""
        with pytest.raises(RegionError):
            list_regions("invalid")

    def test_list_regions_info(self):
        """Test listing regions with info."""
        regions = list_regions_info("territory")
        assert len(regions) > 200
        us = next(r for r in regions if r["code"] == "US")
        assert us["numeric_code"] == 840
        assert us["name"] == "United States"

    def test_get_region_info_us(self):
        """Test getting US region info."""
        info = get_region_info("US")
        assert info is not None
        assert info["code"] == "US"
        assert info["numeric_code"] == 840
        assert info["type"] == "territory"
        assert info["containing_region"] == "021"  # Northern America

    def test_get_region_info_france(self):
        """Test getting France region info."""
        info = get_region_info("FR")
        assert info is not None
        assert info["code"] == "FR"
        assert info["name"] == "France"

    def test_get_region_info_invalid(self):
        """Test invalid region returns None."""
        info = get_region_info("INVALID")
        assert info is None

    def test_get_contained_regions_world(self):
        """Test getting regions contained in World."""
        contained = get_contained_regions("001")
        assert len(contained) == 5  # 5 continents
        assert "019" in contained  # Americas

    def test_get_contained_regions_americas(self):
        """Test getting regions contained in Americas."""
        contained = get_contained_regions("019")
        assert "021" in contained  # Northern America
        assert "005" in contained  # South America

    def test_get_contained_regions_territory(self):
        """Test territory has no contained regions."""
        contained = get_contained_regions("US")
        assert contained == []

    def test_list_region_types(self):
        """Test listing region types."""
        types = list_region_types()
        assert len(types) == 5
        type_names = [t["type"] for t in types]
        assert "territory" in type_names
        assert "continent" in type_names


class TestRegionCLI:
    """Tests for region CLI command."""

    def test_region_list(self):
        """Test icukit region list."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "list"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "US" in result.stdout
        assert "United States" in result.stdout

    def test_region_list_short(self):
        """Test icukit region list --short."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "list", "--short"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "US" in result.stdout
        # Short mode should not have headers or names
        assert "code\t" not in result.stdout

    def test_region_list_continent(self):
        """Test icukit region list --type continent."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "list", "--type", "continent"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "002" in result.stdout  # Africa
        assert "019" in result.stdout  # Americas

    def test_region_info(self):
        """Test icukit region info US."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "info", "US"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "US" in result.stdout
        assert "840" in result.stdout
        assert "United States" in result.stdout

    def test_region_info_json(self):
        """Test icukit region info US --json."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "info", "US", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"code": "US"' in result.stdout
        assert '"numeric_code": 840' in result.stdout

    def test_region_info_invalid(self):
        """Test icukit region info with invalid code."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "info", "INVALID"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Unknown region" in result.stderr

    def test_region_contains(self):
        """Test icukit region contains 019."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "contains", "019"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "021" in result.stdout  # Northern America

    def test_region_list_types(self):
        """Test icukit region list with type filter."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "region", "list", "--type", "continent"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Should list continents - check for continent codes or names
        assert "Africa" in result.stdout or "002" in result.stdout

    def test_region_prefix_matching(self):
        """Test prefix matching works."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "reg", "list", "--short"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "US" in result.stdout
