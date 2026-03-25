"""
FDAS End-to-End Integration Tests

Tests complete workflows from BSEE data loading through financial
analysis and report generation.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import (
    CashflowEngine,
    generate_monthly_cashflow,
)
from worldenergydata.fdas.core.config import (
    AssumptionsManager,
    classify_dev_system_by_depth,
)
from worldenergydata.fdas.core.financial import (
    calculate_all_metrics,
    calculate_npv,
    excel_like_mirr,
)
from worldenergydata.fdas.data.drilling import (
    CompletionActivityClassifier,
    DrillingTimelineExtractor,
)
from worldenergydata.fdas.data.production import (
    ProductionProcessor,
    aggregate_monthly_production,
)


class TestEndToEndWorkflow:
    """Test complete FDAS workflow from data to analysis"""

    @pytest.fixture
    def sample_production_data(self):
        """Create sample production data"""
        dates = pd.date_range("2024-01-01", periods=12, freq="MS")
        data = {
            "API_WELL_NUMBER": ["608054011700"] * 12,
            "DEV_NAME": ["Anchor"] * 12,
            "PROD_DATE": dates,
            "OIL_VOLUME": [
                10000,
                15000,
                20000,
                25000,
                25000,
                24000,
                23000,
                22000,
                21000,
                20000,
                19000,
                18000,
            ],
            "WATER_VOLUME": [
                1000,
                1500,
                2000,
                2500,
                3000,
                3500,
                4000,
                4500,
                5000,
                5500,
                6000,
                6500,
            ],
            "GAS_VOLUME": [0] * 12,
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def sample_well_activity(self):
        """Create sample well activity data"""
        data = {
            "API_WELL_NUMBER": ["608054011700"],
            "SPUD_DATE": [datetime(2023, 6, 1)],
            "TD_DATE": [datetime(2023, 8, 15)],
            "COMPLETION_DATE": [datetime(2023, 11, 30)],
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def assumptions_manager(self):
        """Create assumptions manager with defaults"""
        return AssumptionsManager()

    def test_complete_analysis_workflow(
        self, sample_production_data, sample_well_activity, assumptions_manager
    ):
        """Test complete workflow: data → cashflow → metrics"""

        # Step 1: Process production data
        processor = ProductionProcessor(sample_production_data)
        monthly_prod = processor.aggregate_monthly(by="DEV_NAME")

        assert len(monthly_prod) == 12
        assert "MONTHLY_OIL_BBL" in monthly_prod.columns

        # Step 2: Extract drilling timeline
        extractor = DrillingTimelineExtractor(sample_well_activity)
        timeline = extractor.extract_well_timeline("608054011700")

        assert timeline["drilling_days"] > 0
        assert timeline["spud_date"] is not None

        # Step 3: Generate cashflow
        engine = CashflowEngine(assumptions_manager, "subsea20")

        # Mock WTI prices
        wti_prices = {f"2024-{i:02d}": 75.0 for i in range(1, 13)}

        cashflows = engine.generate_monthly_cashflow(
            monthly_prod, timeline, wti_prices, datetime(2024, 1, 1)
        )

        assert len(cashflows) > 0
        assert all(cf.year_month is not None for cf in cashflows)

        # Step 4: Calculate financial metrics
        cashflow_array = np.array([cf.net_cashflow_usd for cf in cashflows])

        metrics = calculate_all_metrics(cashflow_array, 0.10)

        assert "npv" in metrics
        assert "mirr_annual" in metrics
        assert "irr_annual" in metrics

    def test_production_aggregation_pipeline(self, sample_production_data):
        """Test production data aggregation pipeline"""

        # Monthly aggregation
        monthly = aggregate_monthly_production(sample_production_data, by="DEV_NAME")

        assert len(monthly) == 12
        assert monthly["MONTHLY_OIL_BBL"].sum() > 0

        # Production summary
        processor = ProductionProcessor(sample_production_data)
        summary = processor.generate_production_summary(by="DEV_NAME")

        assert len(summary) == 1
        assert "TOTAL_OIL_BBL" in summary.columns
        assert (
            summary["TOTAL_OIL_BBL"].iloc[0]
            == sample_production_data["OIL_VOLUME"].sum()
        )

    def test_drilling_timeline_extraction(self, sample_well_activity):
        """Test drilling timeline extraction workflow"""

        extractor = DrillingTimelineExtractor(sample_well_activity)

        # Single well timeline
        timeline = extractor.extract_well_timeline("608054011700")

        assert timeline["api_well_number"] == "608054011700"
        assert timeline["drilling_days"] == 75  # June 1 to Aug 15
        assert timeline["completion_days"] > 0

        # Verify monthly allocation
        assert len(timeline["drilling_monthly"]) > 0
        total_days = sum(timeline["drilling_monthly"].values())
        assert total_days == timeline["drilling_days"]

    def test_cashflow_calculations(self, assumptions_manager):
        """Test cashflow calculation components"""

        engine = CashflowEngine(assumptions_manager, "subsea15")

        # Test host CAPEX timing
        host_capex = engine.calculate_host_capex_timing(
            300.0, datetime(2025, 1, 1), 24  # $300MM  # 24 months
        )

        assert len(host_capex) == 24
        assert sum(host_capex.values()) == 300.0

        # Test drilling CAPEX
        drilling_days = {"2024-01": 30, "2024-02": 28, "2024-03": 15}
        drilling_capex = engine.calculate_drilling_capex(
            drilling_days, 0.8  # $0.8MM/day
        )

        assert drilling_capex["2024-01"] == 30 * 0.8
        assert drilling_capex["2024-02"] == 28 * 0.8

        # Test revenue calculation
        production = {"2024-01": 100000, "2024-02": 120000}
        wti_prices = {"2024-01": 75.0, "2024-02": 78.0}

        revenue = engine.calculate_revenue(production, wti_prices)

        assert revenue["2024-01"] == 100000 * 75.0
        assert revenue["2024-02"] == 120000 * 78.0

    def test_development_system_classification(self):
        """Test development system classification logic"""

        # Test depth-based classification
        assert classify_dev_system_by_depth(400) == "dry"
        assert classify_dev_system_by_depth(5000) == "subsea15"
        assert classify_dev_system_by_depth(7500) == "subsea20"

    def test_activity_classification(self):
        """Test completion activity classification"""

        classifier = CompletionActivityClassifier()

        # Test keyword matching
        assert (
            classifier.classify_activity("Perforated 15,000-15,500ft") == "completion"
        )
        assert classifier.classify_activity("Drilling at 10,000ft") == "drilling"
        assert classifier.classify_activity("Running production test") == "testing"
        assert classifier.classify_activity("Random remark") == "unknown"

        # Test mud weight extraction
        mud_weight = classifier.extract_mud_weight("Drilling with 12.5 ppg mud")
        assert mud_weight == 12.5

    def test_financial_metrics_calculation(self):
        """Test financial metrics from cashflow"""

        # Simulate simple profitable project
        cashflows = np.array(
            [
                -1000,  # Initial CAPEX
                100,
                200,
                300,
                400,
                500,  # Growing production
                500,
                450,
                400,
                350,
                300,  # Declining production
            ]
        )

        # Calculate metrics
        npv = calculate_npv(cashflows, 0.10, period="monthly")
        mirr_m, mirr_a = excel_like_mirr(cashflows, 0.10)

        # Should be profitable
        assert npv > 0
        assert mirr_a > 0.10  # Should exceed cost of capital

        # Comprehensive metrics
        metrics = calculate_all_metrics(cashflows, 0.10, period="monthly")

        assert metrics["npv"] > 0
        assert metrics["mirr_annual"] is not None
        assert metrics["payback_years"] < 10


class TestDataValidation:
    """Test data validation and error handling"""

    def test_missing_production_columns(self):
        """Test handling of missing required columns"""
        from worldenergydata.fdas.data.production import (
            ProductionProcessingError,
        )

        # Missing OIL_VOLUME
        bad_data = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["123"],
                "PROD_DATE": [datetime.now()],
                # Missing OIL_VOLUME
            }
        )

        with pytest.raises(ProductionProcessingError):
            ProductionProcessor(bad_data)

    def test_missing_drilling_columns(self):
        """Test handling of missing drilling data"""
        from worldenergydata.fdas.data.drilling import DrillingDataError

        # Missing SPUD_DATE
        bad_data = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["123"],
                # Missing SPUD_DATE
            }
        )

        with pytest.raises(DrillingDataError):
            DrillingTimelineExtractor(bad_data)

    def test_empty_production_data(self):
        """Test handling of empty production data"""

        empty_data = pd.DataFrame(
            {
                "API_WELL_NUMBER": [],
                "PROD_DATE": [],
                "OIL_VOLUME": [],
                "WATER_VOLUME": [],
            }
        )

        processor = ProductionProcessor(empty_data)
        monthly = processor.aggregate_monthly()

        assert len(monthly) == 0


class TestPerformance:
    """Performance tests for large datasets"""

    def test_large_production_dataset(self):
        """Test processing of large production dataset"""

        # 10 wells × 120 months = 1200 records
        num_wells = 10
        num_months = 120

        well_numbers = [f"60805401{i:04d}" for i in range(num_wells)]
        dates = pd.date_range("2015-01-01", periods=num_months, freq="MS")

        data = []
        for well in well_numbers:
            for date in dates:
                data.append(
                    {
                        "API_WELL_NUMBER": well,
                        "DEV_NAME": "TestField",
                        "PROD_DATE": date,
                        "OIL_VOLUME": np.random.randint(5000, 25000),
                        "WATER_VOLUME": np.random.randint(1000, 10000),
                    }
                )

        prod_df = pd.DataFrame(data)

        # Should process quickly
        import time

        start = time.time()

        processor = ProductionProcessor(prod_df)
        monthly = processor.aggregate_monthly(by="DEV_NAME")

        elapsed = time.time() - start

        assert len(monthly) == num_months
        assert elapsed < 2.0  # Should complete in under 2 seconds

    def test_cashflow_generation_performance(self):
        """Test cashflow generation performance"""

        # 30 years monthly = 360 periods
        dates = pd.date_range("2000-01-01", periods=360, freq="MS")

        production = pd.DataFrame(
            {
                "YEAR_MONTH": dates.to_period("M"),
                "MONTHLY_OIL_BBL": np.random.randint(50000, 200000, 360),
            }
        )

        assumptions = AssumptionsManager()
        engine = CashflowEngine(assumptions, "subsea15")

        wti_prices = {str(d.to_period("M")): 75.0 for d in dates}
        timeline = {"drilling_monthly": {}}

        import time

        start = time.time()

        cashflows = engine.generate_monthly_cashflow(
            production, timeline, wti_prices, datetime(2000, 1, 1)
        )

        elapsed = time.time() - start

        assert len(cashflows) >= 360
        assert elapsed < 2.0  # Should complete quickly


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
