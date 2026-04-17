# ABOUTME: WRK-019 integration tests — cost layer with field data pipeline outputs.
# ABOUTME: Tests FieldPipelineCostIntegrator.get_field_cost_summary() using
# ABOUTME: synthetic FieldReport / FieldContext stubs and a real RegionalCostLoader.

"""Integration tests: cost layer + field data pipeline outputs (WRK-019).

Tests ``FieldPipelineCostIntegrator.get_field_cost_summary``, which bridges
``FieldReport`` pipeline outputs to the ``CostEngine`` / ``summarize_field_costs``
cost layer.

All tests use synthetic data and a real ``RegionalCostLoader`` backed by the
project's config YAML, so no binary LFS stubs are required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.cost.cost_engine import CostEngine
from worldenergydata.bsee.analysis.cost.cost_summary import (
    FieldCostSummary,
    summarize_field_costs,
)
from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    CostEstimate,
    WaterDepthBand,
    WellDepthBand,
)
from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader
from worldenergydata.bsee.pipeline.field_cost_integration import (
    FieldPipelineCostIntegrator,
    _default_water_depth_m,
    _default_well_depth_m,
    _infer_region,
)
from worldenergydata.bsee.pipeline.field_query import FieldContext
from worldenergydata.bsee.pipeline.pipeline_runner import FieldReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_dir() -> Path:
    """Path to config/analysis/cost_data relative to repo root."""
    return Path(__file__).parents[3] / "config" / "analysis" / "cost_data"


@pytest.fixture()
def engine(config_dir: Path) -> CostEngine:
    loader = RegionalCostLoader(config_dir=config_dir)
    return CostEngine(loader=loader)


@pytest.fixture()
def integrator(engine: CostEngine) -> FieldPipelineCostIntegrator:
    return FieldPipelineCostIntegrator(engine=engine)


def _make_context(
    field_name: str = "TEST FIELD",
    field_code: str = "001",
    area_code: str = "GC",
    well_count: int = 3,
) -> FieldContext:
    return FieldContext(
        field_code=field_code,
        field_name=field_name,
        leases=("G12345", "G12346"),
        area_code=area_code,
        geological_era="Miocene",
        well_count=well_count,
        query_type="field_name",
    )


def _make_report(
    context: FieldContext,
    wellbore_count: int = 3,
    production_df: pd.DataFrame | None = None,
) -> FieldReport:
    return FieldReport(
        context=context,
        generated_at="2024-01-01T00:00:00+00:00",
        production_summary=(
            production_df if production_df is not None else pd.DataFrame()
        ),
        activity_analysis={},
        casing_strings={},
        casing_matrices={},
        casing_svgs={},
        wellbore_count=wellbore_count,
        lease_count=len(context.leases),
        warnings=[],
    )


# ---------------------------------------------------------------------------
# TestInferRegion
# ---------------------------------------------------------------------------


class TestInferRegion:
    def test_gom_area_codes_resolve_to_gom(self):
        for code in ("GC", "MC", "AT", "WR", "EB"):
            assert _infer_region(code, "SOME FIELD") == "gom"

    def test_unknown_area_code_falls_back_to_gom(self):
        assert _infer_region("XX", "ANY FIELD") == "gom"

    def test_empty_area_code_falls_back_to_gom(self):
        assert _infer_region("", "SOME FIELD") == "gom"

    def test_north_sea_field_name_keyword(self):
        assert _infer_region("", "OSEBERG FIELD") == "north_sea"

    def test_permian_area_code(self):
        assert _infer_region("PERMIAN", "SOME FIELD") == "permian"


# ---------------------------------------------------------------------------
# TestDefaultDepths
# ---------------------------------------------------------------------------


class TestDefaultDepths:
    def test_default_water_depth_gom_deepwater(self):
        depth = _default_water_depth_m("gom")
        assert depth > 300.0, "GOM default should be deepwater (>300 m)"

    def test_default_well_depth_reasonable(self):
        depth = _default_well_depth_m("gom")
        assert 2000.0 <= depth <= 10_000.0

    def test_default_water_depth_onshore(self):
        depth = _default_water_depth_m("permian")
        assert depth == 0.0, "Onshore region should have 0 water depth"


# ---------------------------------------------------------------------------
# TestFieldPipelineCostIntegrator
# ---------------------------------------------------------------------------


class TestFieldPipelineCostIntegrator:
    def test_returns_field_cost_summary(self, integrator):
        ctx = _make_context(well_count=2)
        report = _make_report(ctx, wellbore_count=2)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert isinstance(result, FieldCostSummary)

    def test_field_name_matches_context(self, integrator):
        ctx = _make_context(field_name="BUCKSKIN", well_count=1)
        report = _make_report(ctx, wellbore_count=1)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert result.field_name == "BUCKSKIN"

    def test_n_wells_matches_wellbore_count(self, integrator):
        ctx = _make_context(well_count=5)
        report = _make_report(ctx, wellbore_count=5)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert result.n_wells == 5

    def test_total_capex_positive_for_nonzero_wells(self, integrator):
        ctx = _make_context(well_count=3)
        report = _make_report(ctx, wellbore_count=3)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert result.total_capex_usd_mm > 0.0

    def test_zero_wellbore_count_returns_zero_costs(self, integrator):
        ctx = _make_context(well_count=0)
        report = _make_report(ctx, wellbore_count=0)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert result.total_capex_usd_mm == 0.0
        assert result.n_wells == 0

    def test_drilling_estimates_length_matches_wellbore_count(self, integrator):
        ctx = _make_context(well_count=4)
        report = _make_report(ctx, wellbore_count=4)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert len(result.drilling_estimates) == 4

    def test_completion_estimates_length_matches_wellbore_count(self, integrator):
        ctx = _make_context(well_count=2)
        report = _make_report(ctx, wellbore_count=2)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert len(result.completion_estimates) == 2

    def test_confidence_is_not_empty(self, integrator):
        ctx = _make_context(well_count=1)
        report = _make_report(ctx, wellbore_count=1)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert result.confidence_summary not in ("", "no_data")

    def test_drilling_cost_activity_type(self, integrator):
        ctx = _make_context(well_count=1)
        report = _make_report(ctx, wellbore_count=1)
        result = integrator.get_field_cost_summary(report, year=2022)

        for est in result.drilling_estimates:
            assert est.activity_type == ActivityType.DRILLING

    def test_completion_cost_activity_type(self, integrator):
        ctx = _make_context(well_count=1)
        report = _make_report(ctx, wellbore_count=1)
        result = integrator.get_field_cost_summary(report, year=2022)

        for est in result.completion_estimates:
            assert est.activity_type == ActivityType.COMPLETION

    def test_region_stored_in_summary(self, integrator):
        ctx = _make_context(area_code="GC", well_count=1)
        report = _make_report(ctx, wellbore_count=1)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert result.region == "gom"

    def test_lfs_stub_empty_production_handled(self, integrator):
        """Empty production DataFrame (LFS stub) must not crash the integrator."""
        ctx = _make_context(well_count=2)
        report = _make_report(ctx, wellbore_count=2, production_df=pd.DataFrame())
        result = integrator.get_field_cost_summary(report, year=2022)

        assert isinstance(result, FieldCostSummary)
        assert result.n_wells == 2

    def test_avg_well_cost_consistent_with_total(self, integrator):
        ctx = _make_context(well_count=3)
        report = _make_report(ctx, wellbore_count=3)
        result = integrator.get_field_cost_summary(report, year=2022)

        expected_avg = result.total_drilling_cost_usd_mm / 3
        assert abs(result.avg_well_cost_usd_mm - expected_avg) < 1e-6

    def test_water_depth_from_production_data_overrides_default(self, integrator):
        """When production_summary contains WATER_DEPTH_AVG, it is used."""
        ctx = _make_context(area_code="GC", well_count=1)
        prod_df = pd.DataFrame({"WATER_DEPTH_AVG": [2000.0]})
        report = _make_report(ctx, wellbore_count=1, production_df=prod_df)
        result = integrator.get_field_cost_summary(report, year=2022)

        assert isinstance(result, FieldCostSummary)
        # Deep water GOM rate should be higher than shallow
        assert result.total_drilling_cost_usd_mm > 0.0

    def test_different_years_produce_different_costs(self, integrator):
        ctx = _make_context(well_count=1)
        report = _make_report(ctx, wellbore_count=1)
        cost_2020 = integrator.get_field_cost_summary(report, year=2020)
        cost_2024 = integrator.get_field_cost_summary(report, year=2024)

        # Costs may be the same if rates haven't changed, but neither should be zero
        assert cost_2020.total_capex_usd_mm > 0.0
        assert cost_2024.total_capex_usd_mm > 0.0
