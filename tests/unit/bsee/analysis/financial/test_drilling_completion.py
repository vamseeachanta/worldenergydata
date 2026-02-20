"""Tests for BSEE drilling and completion cost module."""

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.financial.drilling_completion import (
    DrillingCompletionProcessor,
    allocate_dc_costs_monthly,
    build_dc_day_maps,
    calculate_completion_costs,
    calculate_drilling_costs,
)


# ---------------------------------------------------------------------------
# calculate_drilling_costs
# ---------------------------------------------------------------------------

class TestCalculateDrillingCosts:
    def test_basic(self):
        df = pd.DataFrame({
            "WELL_NAME": ["Well_A", "Well_B"],
            "DRILL_DAYS": [10, 20],
        })
        result = calculate_drilling_costs(df, cost_per_day=100000)
        assert result["Well_A"] == 1_000_000.0
        assert result["Well_B"] == 2_000_000.0

    def test_empty(self):
        assert calculate_drilling_costs(pd.DataFrame(), 100000) == {}

    def test_no_well_column(self):
        df = pd.DataFrame({"OTHER": ["A"], "DRILL_DAYS": [10]})
        assert calculate_drilling_costs(df, 100000) == {}

    def test_nan_days(self):
        df = pd.DataFrame({"WELL_NAME": ["A"], "DRILL_DAYS": ["N/A"]})
        result = calculate_drilling_costs(df, 100000, fill_na=5)
        assert result["A"] == 500_000.0


# ---------------------------------------------------------------------------
# calculate_completion_costs
# ---------------------------------------------------------------------------

class TestCalculateCompletionCosts:
    def test_basic(self):
        df = pd.DataFrame({
            "WELL_NAME": ["Well_A"],
            "COMP_DAYS": [15],
        })
        result = calculate_completion_costs(df, cost_per_day=75000)
        assert result["Well_A"] == 1_125_000.0

    def test_empty(self):
        assert calculate_completion_costs(pd.DataFrame(), 75000) == {}

    def test_no_well_column(self):
        df = pd.DataFrame({"OTHER": ["A"], "COMP_DAYS": [10]})
        assert calculate_completion_costs(df, 75000) == {}


# ---------------------------------------------------------------------------
# build_dc_day_maps
# ---------------------------------------------------------------------------

class TestBuildDcDayMaps:
    def test_from_totals(self):
        totals = pd.DataFrame({
            "WELL_NAME": ["Well_A"],
            "DRILL_DAYS": [30],
            "COMP_DAYS": [15],
        })
        drill_map, comp_map, input_totals = build_dc_day_maps(totals, pd.DataFrame())
        assert "Well_A" in input_totals
        assert input_totals["Well_A"][0] == 30.0  # drill days
        assert input_totals["Well_A"][1] == 15.0  # comp days

    def test_both_empty(self):
        drill_map, comp_map, input_totals = build_dc_day_maps(
            pd.DataFrame(), pd.DataFrame()
        )
        assert drill_map == {}
        assert comp_map == {}
        assert input_totals == {}

    def test_from_monthly(self):
        monthly = pd.DataFrame({
            "WELL_NAME": ["Well_A", "Well_A"],
            "DRILL_DAYS": [10, 20],
            "COMP_DAYS": [5, 10],
            "YearMonth": pd.to_datetime(["2023-01-01", "2023-02-01"]),
        })
        drill_map, comp_map, input_totals = build_dc_day_maps(
            pd.DataFrame(), monthly
        )
        assert "Well_A" in input_totals
        assert "2023-01" in drill_map
        assert "2023-02" in drill_map


# ---------------------------------------------------------------------------
# allocate_dc_costs_monthly
# ---------------------------------------------------------------------------

class TestAllocateDcCostsMonthly:
    def test_basic(self):
        df = pd.DataFrame({
            "DRILL_DAYS": [10, 20],
            "COMP_DAYS": [5, 10],
        })
        result = allocate_dc_costs_monthly(df, {})
        assert "DRILL_COST" in result.columns
        assert "COMP_COST" in result.columns
        assert "TOTAL_DC_COST" in result.columns

    def test_empty(self):
        result = allocate_dc_costs_monthly(pd.DataFrame(), {})
        assert result.empty

    def test_custom_rates(self):
        df = pd.DataFrame({"DRILL_DAYS": [10], "COMP_DAYS": [5]})
        costs = {"DRILL_COST_PER_DAY": 200000, "COMP_COST_PER_DAY": 150000}
        result = allocate_dc_costs_monthly(df, costs)
        assert result.iloc[0]["DRILL_COST"] == 2_000_000.0
        assert result.iloc[0]["COMP_COST"] == 750_000.0


# ---------------------------------------------------------------------------
# DrillingCompletionProcessor init
# ---------------------------------------------------------------------------

class TestDrillingCompletionProcessorInit:
    def test_defaults(self):
        proc = DrillingCompletionProcessor()
        assert proc.drill_cost_per_day == 100000
        assert proc.comp_cost_per_day == 75000
        assert proc.subsea_drill_cost == 150000
        assert proc.subsea_comp_cost == 100000

    def test_custom_costs(self):
        proc = DrillingCompletionProcessor({"DRILL_COST_PER_DAY": 200000})
        assert proc.drill_cost_per_day == 200000


# ---------------------------------------------------------------------------
# DrillingCompletionProcessor.calculate_*
# ---------------------------------------------------------------------------

class TestProcessorCalculate:
    def test_drilling(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({"WELL_NAME": ["A"], "DRILL_DAYS": [10]})
        result = proc.calculate_drilling_costs(df, 100000)
        assert result["A"] == 1_000_000.0

    def test_completion(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({"WELL_NAME": ["A"], "COMP_DAYS": [10]})
        result = proc.calculate_completion_costs(df, 75000)
        assert result["A"] == 750_000.0


# ---------------------------------------------------------------------------
# _filter_by_development
# ---------------------------------------------------------------------------

class TestFilterByDevelopment:
    def test_with_dev_name(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({
            "DEV_NAME": ["Alpha", "Beta", "Alpha"],
            "DRILL_DAYS": [10, 20, 30],
        })
        result = proc._filter_by_development(df, "alpha")
        assert len(result) == 2

    def test_empty(self):
        proc = DrillingCompletionProcessor()
        result = proc._filter_by_development(pd.DataFrame(), "dev")
        assert result.empty

    def test_none(self):
        proc = DrillingCompletionProcessor()
        result = proc._filter_by_development(None, "dev")
        assert result.empty


# ---------------------------------------------------------------------------
# allocate_costs_monthly
# ---------------------------------------------------------------------------

class TestAllocateCostsMonthly:
    def test_uses_instance_costs(self):
        proc = DrillingCompletionProcessor({"DRILL_COST_PER_DAY": 200000})
        df = pd.DataFrame({"DRILL_DAYS": [10], "COMP_DAYS": [5]})
        result = proc.allocate_costs_monthly(df)
        assert result.iloc[0]["DRILL_COST"] == 2_000_000.0

    def test_override_costs(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({"DRILL_DAYS": [10], "COMP_DAYS": [5]})
        result = proc.allocate_costs_monthly(df, {"DRILL_COST_PER_DAY": 300000})
        assert result.iloc[0]["DRILL_COST"] == 3_000_000.0


# ---------------------------------------------------------------------------
# validate_dates
# ---------------------------------------------------------------------------

class TestValidateDates:
    def test_valid_dates(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({
            "WELL_SPUD_DATE": ["2023-01-01"],
            "TOTAL_DEPTH_DATE": ["2023-02-01"],
        })
        proc.validate_dates(df)  # No exception

    def test_invalid_dates(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({
            "WELL_NAME": ["Well_A"],
            "WELL_SPUD_DATE": ["2023-06-01"],
            "TOTAL_DEPTH_DATE": ["2023-01-01"],  # Before spud
        })
        with pytest.raises(ValueError, match="Total depth date before spud date"):
            proc.validate_dates(df)

    def test_empty(self):
        proc = DrillingCompletionProcessor()
        proc.validate_dates(pd.DataFrame())  # No exception


# ---------------------------------------------------------------------------
# calculate_system_specific_costs
# ---------------------------------------------------------------------------

class TestCalculateSystemSpecificCosts:
    def test_subsea(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({
            "WELL_NAME": ["A"],
            "DRILL_DAYS": [10],
            "COMP_DAYS": [5],
            "DEV_TYPE": ["subsea"],
        })
        costs = {"SUBSEA_DRILL_COST_PER_DAY": 150000, "SUBSEA_COMP_COST_PER_DAY": 100000}
        result = proc.calculate_system_specific_costs(df, costs)
        assert result["A"] == (10 * 150000) + (5 * 100000)

    def test_dry_tree(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({
            "WELL_NAME": ["A"],
            "DRILL_DAYS": [10],
            "COMP_DAYS": [5],
            "DEV_TYPE": ["dry tree"],
        })
        costs = {"DRILL_COST_PER_DAY": 100000, "COMP_COST_PER_DAY": 75000}
        result = proc.calculate_system_specific_costs(df, costs)
        assert result["A"] == (10 * 100000) + (5 * 75000)


# ---------------------------------------------------------------------------
# calculate_efficiency_metrics
# ---------------------------------------------------------------------------

class TestCalculateEfficiencyMetrics:
    def test_basic(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({
            "WELL_NAME": ["A", "B", "C"],
            "DRILL_DAYS": [10, 20, 30],
            "COMP_DAYS": [5, 10, 15],
        })
        metrics = proc.calculate_efficiency_metrics(df)
        assert metrics["avg_drill_days"] == 20.0
        assert metrics["total_drill_days"] == 60.0
        assert metrics["well_count"] == 3

    def test_empty(self):
        proc = DrillingCompletionProcessor()
        assert proc.calculate_efficiency_metrics(pd.DataFrame()) == {}


# ---------------------------------------------------------------------------
# generate_capex_schedule
# ---------------------------------------------------------------------------

class TestGenerateCapexSchedule:
    def test_empty_monthly(self):
        proc = DrillingCompletionProcessor()
        result = proc.generate_capex_schedule(
            pd.DataFrame(), {}, "2023-01-01", "2023-06-01"
        )
        assert "TOTAL_CAPEX" in result.columns
        assert len(result) == 6

    def test_with_data(self):
        proc = DrillingCompletionProcessor()
        monthly = pd.DataFrame({
            "DRILL_DAYS": [10],
            "COMP_DAYS": [5],
            "YearMonth": pd.to_datetime(["2023-01-01"]),
        })
        result = proc.generate_capex_schedule(
            monthly, {}, "2023-01-01", "2023-03-01"
        )
        assert len(result) == 3


# ---------------------------------------------------------------------------
# aggregate_dc_by_lease
# ---------------------------------------------------------------------------

class TestAggregateDcByLease:
    def test_basic(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({
            "LEASE_NUM": ["L1", "L1", "L2"],
            "DRILL_DAYS": [10, 20, 15],
            "COMP_DAYS": [5, 10, 8],
            "DRILL_COST": [1e6, 2e6, 1.5e6],
            "COMP_COST": [375e3, 750e3, 600e3],
        })
        result = proc.aggregate_dc_by_lease(df)
        assert len(result) == 2
        assert "TOTAL_DC_COST" in result.columns
        assert "WELL_COUNT" in result.columns

    def test_empty(self):
        proc = DrillingCompletionProcessor()
        result = proc.aggregate_dc_by_lease(pd.DataFrame())
        assert result.empty

    def test_no_lease_column(self):
        proc = DrillingCompletionProcessor()
        df = pd.DataFrame({"DRILL_DAYS": [10]})
        result = proc.aggregate_dc_by_lease(df)
        assert result.empty
