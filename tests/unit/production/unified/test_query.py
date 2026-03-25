"""Tests for ProductionQuery and ProductionResult dataclasses."""

import pandas as pd
import pytest

from worldenergydata.production.unified.query import (
    ProductionQuery,
    ProductionResult,
    STANDARD_COLUMNS,
)


class TestProductionQuery:
    def test_query_requires_regions(self):
        q = ProductionQuery(regions=["ncs"])
        assert q.regions == ["ncs"]

    def test_query_defaults(self):
        q = ProductionQuery(regions=["gom"])
        assert q.fields is None
        assert q.start is None
        assert q.end is None
        assert "oil_bbl" in q.parameters

    def test_query_with_all_args(self):
        q = ProductionQuery(
            regions=["ncs", "ukcs"],
            fields=["Edvard Grieg"],
            start="2020-01",
            end="2023-12",
            parameters=("oil_bbl", "gas_mcf"),
        )
        assert q.start == "2020-01"
        assert q.end == "2023-12"
        assert q.fields == ["Edvard Grieg"]

    def test_multiple_regions_stored(self):
        q = ProductionQuery(regions=["ncs", "gom", "brazil"])
        assert len(q.regions) == 3


class TestProductionResult:
    def _make_result(self):
        q = ProductionQuery(regions=["ncs"])
        df = pd.DataFrame(
            {
                "region": ["ncs"],
                "field_name": ["Edvard Grieg"],
                "year": [2020],
                "month": [1],
                "oil_bbl": [5_800_000.0],
                "gas_mcf": [2_100_000.0],
                "water_bbl": [420_000.0],
                "condensate_bbl": [180_000.0],
                "source": ["sodir_mock"],
            }
        )
        summary = pd.DataFrame(
            {
                "region": ["ncs"],
                "field_name": ["Edvard Grieg"],
                "peak_rate": [5_800_000.0],
                "cumulative_oil_bbl": [5_800_000.0],
                "avg_monthly_oil_bbl": [5_800_000.0],
                "total_months": [1],
            }
        )
        return ProductionResult(
            query=q,
            data=df,
            summary=summary,
            sources_used=["sodir_mock"],
            coverage_gaps=[],
        )

    def test_result_is_not_empty(self):
        result = self._make_result()
        assert not result.is_empty()

    def test_empty_result_detected(self):
        q = ProductionQuery(regions=["ncs"])
        result = ProductionResult(
            query=q,
            data=pd.DataFrame(columns=list(STANDARD_COLUMNS)),
            summary=pd.DataFrame(),
            sources_used=[],
            coverage_gaps=[],
        )
        assert result.is_empty()

    def test_standard_columns_complete(self):
        assert "region" in STANDARD_COLUMNS
        assert "field_name" in STANDARD_COLUMNS
        assert "oil_bbl" in STANDARD_COLUMNS
        assert "gas_mcf" in STANDARD_COLUMNS
        assert "water_bbl" in STANDARD_COLUMNS
        assert "condensate_bbl" in STANDARD_COLUMNS
        assert "source" in STANDARD_COLUMNS
        assert "year" in STANDARD_COLUMNS
        assert "month" in STANDARD_COLUMNS
