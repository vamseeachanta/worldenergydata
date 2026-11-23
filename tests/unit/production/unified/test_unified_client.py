"""Tests for UnifiedProductionClient — integration across all layers."""

import pandas as pd
import pytest

from worldenergydata.production.unified import UnifiedProductionClient
from worldenergydata.production.unified.query import (
    STANDARD_COLUMNS,
    ProductionQuery,
    ProductionResult,
)


class TestUnifiedProductionClientQuery:
    def setup_method(self):
        self.client = UnifiedProductionClient()

    def test_query_single_region_returns_result(self):
        q = ProductionQuery(regions=["ncs"])
        result = self.client.query(q)
        assert isinstance(result, ProductionResult)

    def test_query_multiple_regions(self):
        q = ProductionQuery(regions=["ncs", "gom", "brazil"])
        result = self.client.query(q)
        assert not result.is_empty()
        regions_in_data = set(result.data["region"].unique())
        assert "ncs" in regions_in_data
        assert "gom" in regions_in_data
        assert "brazil" in regions_in_data

    def test_query_all_nine_regions(self):
        q = ProductionQuery(
            regions=[
                "ncs",
                "gom",
                "brazil",
                "ukcs",
                "spain",
                "eia_us",
                "mexico",
                "texas",
                "canada",
            ]
        )
        result = self.client.query(q)
        assert not result.is_empty()
        assert len(result.sources_used) == 9

    def test_query_result_has_standard_columns(self):
        q = ProductionQuery(regions=["ncs"])
        result = self.client.query(q)
        for col in STANDARD_COLUMNS:
            assert col in result.data.columns

    def test_query_result_summary_has_data(self):
        q = ProductionQuery(regions=["ncs"])
        result = self.client.query(q)
        assert not result.summary.empty
        assert "peak_rate" in result.summary.columns

    def test_query_with_date_filter(self):
        q = ProductionQuery(regions=["ncs"], start="2020-01", end="2021-12")
        result = self.client.query(q)
        assert not result.is_empty()
        assert result.data["year"].between(2020, 2021).all()

    def test_query_with_field_filter(self):
        q = ProductionQuery(regions=["ncs"], fields=["Edvard Grieg"])
        result = self.client.query(q)
        assert not result.is_empty()
        assert set(result.data["field_name"].unique()) == {"Edvard Grieg"}

    def test_query_with_alias_region(self):
        q = ProductionQuery(regions=["norway"])
        result = self.client.query(q)
        assert not result.is_empty()
        assert "ncs" in result.data["region"].values

    def test_query_sources_used_populated(self):
        q = ProductionQuery(regions=["ncs", "gom"])
        result = self.client.query(q)
        assert len(result.sources_used) >= 2

    def test_query_coverage_gaps_is_list(self):
        q = ProductionQuery(regions=["ncs"])
        result = self.client.query(q)
        assert isinstance(result.coverage_gaps, list)

    def test_query_result_data_sorted_within_field(self):
        """Data is sorted by (region, field_name, year, month) so periods
        within a single field must be non-decreasing."""
        q = ProductionQuery(regions=["ncs"], fields=["Valhall"])
        result = self.client.query(q)
        df = result.data
        periods = (df["year"] * 100 + df["month"]).tolist()
        assert periods == sorted(periods)

    def test_query_unknown_region_raises(self):
        q = ProductionQuery(regions=["unknown_basin_xyz"])
        with pytest.raises(KeyError):
            self.client.query(q)

    def test_query_empty_region_list_returns_empty(self):
        q = ProductionQuery(regions=[])
        result = self.client.query(q)
        assert result.is_empty()
        assert result.sources_used == []


class TestUnifiedProductionClientListRegions:
    def setup_method(self):
        self.client = UnifiedProductionClient()

    def test_list_regions_returns_list(self):
        regions = self.client.list_regions()
        assert isinstance(regions, list)

    def test_list_regions_has_ten_entries(self):
        regions = self.client.list_regions()
        assert len(regions) == 10

    def test_list_regions_contains_all_canonical(self):
        regions = self.client.list_regions()
        for expected in [
            "ncs",
            "gom",
            "brazil",
            "ukcs",
            "spain",
            "eia_us",
            "mexico",
            "texas",
            "canada",
            "australia",
        ]:
            assert expected in regions
