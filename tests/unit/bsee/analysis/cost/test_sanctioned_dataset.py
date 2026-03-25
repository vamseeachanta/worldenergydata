# ABOUTME: Unit tests for WRK-171 sanctioned project dataset builder.
# ABOUTME: Covers synthetic data generation, schema validation, inflation adjustment,
# ABOUTME: and band classification for the calibration dataset.

"""Unit tests for worldenergydata.bsee.analysis.cost.sanctioned_dataset."""

import pytest
import pandas as pd

from worldenergydata.bsee.analysis.cost.sanctioned_dataset import (
    SanctionedProjectDataset,
)
from worldenergydata.bsee.analysis.cost.models import (
    ConfidenceLevel,
    WaterDepthBand,
    WellDepthBand,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def dataset() -> SanctionedProjectDataset:
    return SanctionedProjectDataset()


@pytest.fixture()
def synthetic_df(dataset: SanctionedProjectDataset) -> pd.DataFrame:
    return dataset.synthetic_dataset(n_records=120, seed=42)


# ---------------------------------------------------------------------------
# TestSyntheticDataset
# ---------------------------------------------------------------------------


class TestSyntheticDataset:
    def test_has_minimum_100_records(self, synthetic_df):
        assert len(synthetic_df) >= 100

    def test_required_schema_columns_present(self, synthetic_df):
        required = {
            "project_name",
            "region",
            "water_depth_m",
            "water_depth_band",
            "well_depth_m",
            "well_depth_band",
            "operator",
            "year_sanction",
            "year_drilling",
            "rig_type",
            "activity_type",
            "hpht",
            "subsea",
            "cost_usd_mm",
            "cost_type",
            "source",
            "confidence",
        }
        assert required.issubset(set(synthetic_df.columns))

    def test_costs_are_positive(self, synthetic_df):
        assert (synthetic_df["cost_usd_mm"] > 0).all()

    def test_regions_are_valid(self, synthetic_df):
        valid_regions = {"gom", "north_sea", "brazil", "west_africa", "asia_pacific"}
        assert set(synthetic_df["region"].unique()).issubset(valid_regions)

    def test_water_depth_bands_are_valid(self, synthetic_df):
        valid = {b.value for b in WaterDepthBand}
        assert set(synthetic_df["water_depth_band"].unique()).issubset(valid)

    def test_well_depth_bands_are_valid(self, synthetic_df):
        valid = {b.value for b in WellDepthBand}
        assert set(synthetic_df["well_depth_band"].unique()).issubset(valid)

    def test_confidence_values_are_valid(self, synthetic_df):
        valid = {c.value for c in ConfidenceLevel}
        assert set(synthetic_df["confidence"].unique()).issubset(valid)

    def test_seeded_generation_is_reproducible(self, dataset):
        df1 = dataset.synthetic_dataset(n_records=50, seed=99)
        df2 = dataset.synthetic_dataset(n_records=50, seed=99)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_produce_different_data(self, dataset):
        df1 = dataset.synthetic_dataset(n_records=50, seed=1)
        df2 = dataset.synthetic_dataset(n_records=50, seed=2)
        assert not df1["cost_usd_mm"].equals(df2["cost_usd_mm"])


# ---------------------------------------------------------------------------
# TestInflationAdjust
# ---------------------------------------------------------------------------


class TestInflationAdjust:
    def test_adjust_returns_dataframe(self, dataset, synthetic_df):
        adjusted = dataset.inflation_adjust(synthetic_df, base_year=2022)
        assert isinstance(adjusted, pd.DataFrame)

    def test_adjusted_has_cost_real_column(self, dataset, synthetic_df):
        adjusted = dataset.inflation_adjust(synthetic_df, base_year=2022)
        assert "cost_usd_mm_real" in adjusted.columns

    def test_base_year_records_unchanged(self, dataset, synthetic_df):
        base_year = 2022
        adjusted = dataset.inflation_adjust(synthetic_df, base_year=base_year)
        mask = adjusted["year_drilling"] == base_year
        if mask.any():
            orig_costs = synthetic_df.loc[mask, "cost_usd_mm"].values
            adj_costs = adjusted.loc[mask, "cost_usd_mm_real"].values
            for orig, adj in zip(orig_costs, adj_costs):
                assert abs(orig - adj) < 1e-6, (
                    f"Base-year cost should be unchanged: {orig} vs {adj}"
                )

    def test_older_costs_adjusted_upward(self, dataset):
        rows = [
            {
                "project_name": "Old Project",
                "region": "gom",
                "water_depth_m": 1500.0,
                "water_depth_band": "deep",
                "well_depth_m": 8000.0,
                "well_depth_band": "deep",
                "operator": "BP",
                "year_sanction": 2010,
                "year_drilling": 2010,
                "rig_type": "drillship",
                "activity_type": "drilling",
                "hpht": False,
                "subsea": True,
                "cost_usd_mm": 100.0,
                "cost_type": "well_cost",
                "source": "test",
                "confidence": "high",
            }
        ]
        df = pd.DataFrame(rows)
        adjusted = dataset.inflation_adjust(df, base_year=2022)
        assert adjusted["cost_usd_mm_real"].iloc[0] > 100.0


# ---------------------------------------------------------------------------
# TestValidateSchema
# ---------------------------------------------------------------------------


class TestValidateSchema:
    def test_valid_dataframe_passes(self, dataset, synthetic_df):
        errors = dataset.validate_schema(synthetic_df)
        assert errors == []

    def test_missing_column_returns_error(self, dataset, synthetic_df):
        bad_df = synthetic_df.drop(columns=["cost_usd_mm"])
        errors = dataset.validate_schema(bad_df)
        assert any("cost_usd_mm" in e for e in errors)

    def test_negative_cost_returns_error(self, dataset, synthetic_df):
        bad_df = synthetic_df.copy()
        bad_df.loc[0, "cost_usd_mm"] = -5.0
        errors = dataset.validate_schema(bad_df)
        assert any("cost_usd_mm" in e for e in errors)

    def test_empty_dataframe_returns_error(self, dataset):
        errors = dataset.validate_schema(pd.DataFrame())
        assert len(errors) > 0
