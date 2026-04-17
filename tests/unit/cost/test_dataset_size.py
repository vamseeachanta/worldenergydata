"""
ABOUTME: Tests verifying the public dataset meets the WRK-171 AC1 requirement.
ABOUTME: AC1: Sanctioned project cost dataset with at least 100 data points
ABOUTME: across multiple regions.
"""

from __future__ import annotations

import pytest

from worldenergydata.cost.data_collection.calibration_schema import (
    Confidence,
    CostDataPoint,
    WaterDepthBand,
)
from worldenergydata.cost.data_collection.public_dataset import load_public_dataset


class TestDatasetSizeRequirements:
    """AC1: Dataset meets minimum 100-record requirement."""

    def test_dataset_has_at_least_100_records(self):
        """load_public_dataset() returns >= 100 records (WRK-171 AC1)."""
        records = load_public_dataset()
        assert len(records) >= 100, f"AC1 requires >= 100 records, got {len(records)}"

    def test_all_records_are_valid_cost_data_points(self):
        """Every record is a valid CostDataPoint instance."""
        records = load_public_dataset()
        for rec in records:
            assert isinstance(rec, CostDataPoint)

    def test_dataset_covers_at_least_five_regions(self):
        """Dataset spans at least 5 distinct geographic regions."""
        records = load_public_dataset()
        regions = {r.region for r in records}
        assert (
            len(regions) >= 5
        ), f"Expected >= 5 regions, got {len(regions)}: {regions}"

    def test_dataset_includes_all_water_depth_bands(self):
        """Dataset contains records in all four water depth bands."""
        records = load_public_dataset()
        bands = {r.water_depth_band for r in records}
        assert bands == set(
            WaterDepthBand
        ), f"Missing depth bands: {set(WaterDepthBand) - bands}"

    def test_dataset_spans_at_least_15_years(self):
        """Year range spans at least 15 years for temporal coverage."""
        records = load_public_dataset()
        years = {r.year_sanction for r in records}
        assert (
            max(years) - min(years) >= 15
        ), f"Year span too narrow: {min(years)}-{max(years)}"

    def test_dataset_includes_hpht_records(self):
        """At least some records are HPHT (high-pressure high-temperature)."""
        records = load_public_dataset()
        hpht_count = sum(1 for r in records if r.hpht)
        assert hpht_count >= 3, f"Expected >= 3 HPHT records, got {hpht_count}"

    def test_high_confidence_records_present(self):
        """At least half the records have high or medium confidence."""
        records = load_public_dataset()
        high_or_medium = sum(
            1 for r in records if r.confidence in (Confidence.HIGH, Confidence.MEDIUM)
        )
        assert (
            high_or_medium >= len(records) * 0.5
        ), f"Too many low-confidence records: {high_or_medium}/{len(records)}"
