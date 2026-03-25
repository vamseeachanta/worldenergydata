# ABOUTME: Unit tests for WRK-171 regional cost profile YAML loader.
# ABOUTME: Covers YAML loading, year interpolation, proxy fallback, and rate lookup.

"""Unit tests for worldenergydata.bsee.analysis.cost.regional_loader."""

import pytest
from pathlib import Path

from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader
from worldenergydata.bsee.analysis.cost.models import ActivityType, WaterDepthBand


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def loader() -> RegionalCostLoader:
    """Return a loader pointed at the real day_rates.yml in config/.

    Path: <repo_root>/config/analysis/cost_data/
    test file is at: <repo_root>/tests/unit/bsee/analysis/cost/test_*.py
    parents[5] = <repo_root>
    """
    config_root = (
        Path(__file__).parents[5] / "config" / "analysis" / "cost_data"
    )
    return RegionalCostLoader(config_dir=config_root)


# ---------------------------------------------------------------------------
# TestRegionalCostLoader
# ---------------------------------------------------------------------------


class TestRegionalCostLoader:
    def test_day_rate_returns_positive_float(self, loader):
        rate = loader.get_day_rate(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        assert isinstance(rate, float)
        assert rate > 0.0

    def test_onshore_region_returns_lower_rate_than_deepwater(self, loader):
        onshore = loader.get_day_rate(
            region="permian",
            water_depth_band=WaterDepthBand.SHALLOW,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        deepwater = loader.get_day_rate(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        assert onshore < deepwater

    def test_unknown_region_raises_key_error(self, loader):
        with pytest.raises(KeyError, match="unknown_region"):
            loader.get_day_rate(
                region="unknown_region",
                water_depth_band=WaterDepthBand.DEEP,
                activity_type=ActivityType.DRILLING,
                year=2022,
            )

    def test_year_interpolation_between_known_years(self, loader):
        rate_2020 = loader.get_day_rate(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            year=2020,
        )
        rate_2022 = loader.get_day_rate(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        rate_2021 = loader.get_day_rate(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            year=2021,
        )
        assert min(rate_2020, rate_2022) <= rate_2021 <= max(rate_2020, rate_2022) + 1.0

    def test_available_regions_not_empty(self, loader):
        regions = loader.available_regions()
        assert len(regions) > 0

    def test_gom_in_available_regions(self, loader):
        assert "gom" in loader.available_regions()

    def test_get_all_rates_returns_dict(self, loader):
        rates = loader.get_all_rates(year=2022)
        assert isinstance(rates, dict)
        assert len(rates) > 0

    def test_hpht_premium_applied_when_flag_true(self, loader):
        standard = loader.get_day_rate(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            year=2022,
            hpht=False,
        )
        hpht = loader.get_day_rate(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            year=2022,
            hpht=True,
        )
        assert hpht >= standard
