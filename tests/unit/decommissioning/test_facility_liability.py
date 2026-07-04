# ABOUTME: Unit tests for facility-level regional decommissioning liability mapping.
# ABOUTME: Pure-logic tests for HOST_TYPE->asset and COUNTRY/GoM->region classifiers.

"""Unit tests for worldenergydata.decommissioning.facility_liability."""

import pandas as pd

from worldenergydata.decommissioning.facility_liability import (
    classify_asset_type,
    price_portfolio,
    region_of,
)


# ---------------------------------------------------------------------------
# classify_asset_type
# ---------------------------------------------------------------------------


def test_fixed_platform_is_jacket():
    assert classify_asset_type("Fixed Platform") == "jacket"


def test_fpso_is_fpso():
    assert classify_asset_type("FPSO") == "fpso"


def test_tlp_is_tlp():
    assert classify_asset_type("TLP") == "tlp"


def test_spar_is_spar():
    assert classify_asset_type("SPAR") == "spar"


def test_artificial_island_is_unmapped():
    assert classify_asset_type("Artificial Island") is None


def test_asset_type_strips_whitespace():
    assert classify_asset_type("  FPSO  ") == "fpso"


# ---------------------------------------------------------------------------
# region_of
# ---------------------------------------------------------------------------


def test_us_with_gom_flag_is_gom():
    assert region_of("United States", "Y") == "gom"


def test_united_kingdom_is_ukcs():
    assert region_of("United Kingdom", None) == "ukcs"


def test_norway_is_ncs():
    assert region_of("Norway", None) == "ncs"


def test_brazil_is_brazil():
    assert region_of("Brazil", None) == "brazil"


def test_nigeria_is_west_africa():
    assert region_of("Nigeria", None) == "west_africa"


def test_australia_is_unmodeled():
    assert region_of("Australia", None) is None


def test_gom_flag_overrides_country():
    # US_GOM_FLAG takes precedence even when country string is empty
    assert region_of("", "YES") == "gom"


# ---------------------------------------------------------------------------
# price_portfolio (pure logic over a tiny in-memory frame)
# ---------------------------------------------------------------------------


def test_price_portfolio_counts_and_exclusions():
    df = pd.DataFrame(
        [
            {
                "FACILITY_ID": 1,
                "HOST_TYPE": "FPSO",
                "COUNTRY": "Brazil",
                "US_GOM_FLAG": "N",
                "WATER_DEPTH_M": 1000.0,
            },
            {
                "FACILITY_ID": 2,
                "HOST_TYPE": "Artificial Island",
                "COUNTRY": "United States",
                "US_GOM_FLAG": "Y",
                "WATER_DEPTH_M": 5.0,
            },
            {
                "FACILITY_ID": 3,
                "HOST_TYPE": "Fixed Platform",
                "COUNTRY": "Australia",
                "US_GOM_FLAG": "N",
                "WATER_DEPTH_M": 50.0,
            },
        ]
    )
    result = price_portfolio(df)
    assert result["counts"]["modeled"] == 1
    assert result["counts"]["unmapped_asset"] == 1  # Artificial Island
    assert result["counts"]["unmodeled_region"] == 1  # Australia
    assert result["by_region"]["brazil"]["count"] == 1
    assert result["by_asset"]["fpso"]["count"] == 1
    assert result["total_musd"] > 0
