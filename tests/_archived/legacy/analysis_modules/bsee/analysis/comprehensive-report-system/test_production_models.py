"""
Tests for WellSummary and ProductionMetrics data models
Following TDD approach - tests written before implementation
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from worldenergydata.modules.bsee.reports.comprehensive.models import (
    WellSummary,
    ProductionMetrics,
    ProductionPeriod,
    EconomicMetrics
)


class TestWellSummary:
    """Test WellSummary data model"""
    
    def test_well_summary_initialization(self):
        """Test basic WellSummary initialization"""
        summary = WellSummary(
            well_id="WELL-001",
            api_number="1234567890",
            well_name="PS001",
            operator="Test Oil Corp",
            field_name="Jack",
            lease_number="OCS-G-12345"
        )
        
        assert summary.well_id == "WELL-001"
        assert summary.api_number == "1234567890"
        assert summary.well_name == "PS001"
        assert summary.operator == "Test Oil Corp"
        assert summary.field_name == "Jack"
        assert summary.lease_number == "OCS-G-12345"
    
    def test_well_summary_with_dates(self):
        """Test WellSummary with date fields"""
        summary = WellSummary(
            well_id="WELL-002",
            api_number="1234567891",
            well_name="PS002",
            spud_date=date(2020, 1, 15),
            completion_date=date(2020, 4, 30),
            first_production_date=date(2020, 5, 15),
            last_production_date=date(2024, 6, 30)
        )
        
        assert summary.spud_date == date(2020, 1, 15)
        assert summary.completion_date == date(2020, 4, 30)
        assert summary.first_production_date == date(2020, 5, 15)
        assert summary.last_production_date == date(2024, 6, 30)
        
        # Calculate days
        assert summary.days_to_completion() == 105
        assert summary.production_days() > 1500
    
    def test_well_summary_with_metrics(self):
        """Test WellSummary with production metrics"""
        summary = WellSummary(
            well_id="WELL-003",
            api_number="1234567892",
            well_name="PS003",
            water_depth_ft=7000,
            total_depth_ft=25000,
            peak_oil_rate_bopd=12000,
            peak_gas_rate_mcfd=8000,
            cumulative_oil_bbl=5000000,
            cumulative_gas_mcf=3500000
        )
        
        assert summary.water_depth_ft == 7000
        assert summary.total_depth_ft == 25000
        assert summary.peak_oil_rate_bopd == 12000
        assert summary.peak_gas_rate_mcfd == 8000
        assert summary.cumulative_oil_bbl == 5000000
        assert summary.cumulative_gas_mcf == 3500000
    
    def test_well_summary_status_tracking(self):
        """Test well status and completion type tracking"""
        summary = WellSummary(
            well_id="WELL-004",
            api_number="1234567893",
            well_name="PS004",
            wellbore_status="ACTIVE",
            completion_type="GRAVEL PACK",
            well_purpose="D",  # Development
            side_tracks=2
        )
        
        assert summary.wellbore_status == "ACTIVE"
        assert summary.completion_type == "GRAVEL PACK"
        assert summary.well_purpose == "D"
        assert summary.side_tracks == 2
        assert summary.is_active() is True
        
        # Test status change
        summary.wellbore_status = "P&A"
        assert summary.is_active() is False


class TestProductionMetrics:
    """Test ProductionMetrics data model"""
    
    def test_production_metrics_initialization(self):
        """Test basic ProductionMetrics initialization"""
        metrics = ProductionMetrics(
            entity_id="WELL-001",
            entity_type="well",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31)
        )
        
        assert metrics.entity_id == "WELL-001"
        assert metrics.entity_type == "well"
        assert metrics.period_start == date(2024, 1, 1)
        assert metrics.period_end == date(2024, 1, 31)
        assert metrics.period_days() == 30
    
    def test_production_metrics_volumes(self):
        """Test production volume tracking"""
        metrics = ProductionMetrics(
            entity_id="WELL-002",
            entity_type="well",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            oil_volume_bbl=150000,
            gas_volume_mcf=100000,
            water_volume_bbl=5000,
            production_days=28
        )
        
        assert metrics.oil_volume_bbl == 150000
        assert metrics.gas_volume_mcf == 100000
        assert metrics.water_volume_bbl == 5000
        assert metrics.production_days == 28
        
        # Calculate daily rates
        assert metrics.daily_oil_rate() == pytest.approx(5357.14, 0.01)
        assert metrics.daily_gas_rate() == pytest.approx(3571.43, 0.01)
        assert metrics.water_cut() == pytest.approx(0.0323, 0.001)
    
    def test_production_metrics_aggregation(self):
        """Test aggregating multiple production metrics"""
        metrics_jan = ProductionMetrics(
            entity_id="WELL-003",
            entity_type="well",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            oil_volume_bbl=150000,
            gas_volume_mcf=100000
        )
        
        metrics_feb = ProductionMetrics(
            entity_id="WELL-003",
            entity_type="well",
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
            oil_volume_bbl=140000,
            gas_volume_mcf=95000
        )
        
        # Aggregate metrics
        total_metrics = ProductionMetrics.aggregate([metrics_jan, metrics_feb])
        assert total_metrics.oil_volume_bbl == 290000
        assert total_metrics.gas_volume_mcf == 195000
    
    def test_production_metrics_with_economics(self):
        """Test production metrics with economic calculations"""
        metrics = ProductionMetrics(
            entity_id="FIELD-001",
            entity_type="field",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            oil_volume_bbl=1000000,
            gas_volume_mcf=750000,
            oil_price_usd=75.00,
            gas_price_usd=3.50,
            operating_cost_usd=5000000
        )
        
        # Calculate revenues
        assert metrics.oil_revenue() == 75000000
        assert metrics.gas_revenue() == 2625000
        assert metrics.total_revenue() == 77625000
        assert metrics.net_revenue() == 72625000  # Revenue - operating cost
        
        # Calculate metrics
        assert metrics.operating_margin() == pytest.approx(0.936, 0.001)


class TestProductionPeriod:
    """Test ProductionPeriod enum and utilities"""
    
    def test_production_period_types(self):
        """Test different production period types"""
        assert ProductionPeriod.DAILY.value == "daily"
        assert ProductionPeriod.MONTHLY.value == "monthly"
        assert ProductionPeriod.YEARLY.value == "yearly"
        assert ProductionPeriod.CUMULATIVE.value == "cumulative"
    
    def test_period_date_range_calculation(self):
        """Test calculating date ranges for different periods"""
        # Daily period
        daily_range = ProductionPeriod.get_date_range(
            ProductionPeriod.DAILY,
            date(2024, 1, 15)
        )
        assert daily_range == (date(2024, 1, 15), date(2024, 1, 15))
        
        # Monthly period
        monthly_range = ProductionPeriod.get_date_range(
            ProductionPeriod.MONTHLY,
            date(2024, 1, 15)
        )
        assert monthly_range == (date(2024, 1, 1), date(2024, 1, 31))
        
        # Yearly period
        yearly_range = ProductionPeriod.get_date_range(
            ProductionPeriod.YEARLY,
            date(2024, 6, 15)
        )
        assert yearly_range == (date(2024, 1, 1), date(2024, 12, 31))


class TestEconomicMetrics:
    """Test EconomicMetrics data model"""
    
    def test_economic_metrics_initialization(self):
        """Test basic EconomicMetrics initialization"""
        metrics = EconomicMetrics(
            entity_id="FIELD-001",
            entity_type="field",
            calculation_date=date(2024, 1, 1)
        )
        
        assert metrics.entity_id == "FIELD-001"
        assert metrics.entity_type == "field"
        assert metrics.calculation_date == date(2024, 1, 1)
    
    def test_economic_metrics_npv_calculation(self):
        """Test NPV and economic calculations"""
        metrics = EconomicMetrics(
            entity_id="FIELD-002",
            entity_type="field",
            calculation_date=date(2024, 1, 1),
            gross_revenue_usd=500000000,
            operating_costs_usd=150000000,
            capital_costs_usd=200000000,
            abandonment_costs_usd=50000000,
            discount_rate=0.10
        )
        
        # Calculate cash flows
        assert metrics.net_revenue() == 350000000
        assert metrics.free_cash_flow() == 150000000
        assert metrics.project_margin() == 0.30
        
        # NPV would require cash flow schedule
        metrics.cash_flows = [
            -200000000,  # Initial investment
            50000000,    # Year 1
            75000000,    # Year 2
            100000000,   # Year 3
            125000000,   # Year 4
            100000000,   # Year 5
        ]
        
        assert metrics.calculate_npv() > 0
        assert metrics.calculate_irr() > 0.10
    
    def test_economic_metrics_reserves(self):
        """Test reserve and recovery metrics"""
        metrics = EconomicMetrics(
            entity_id="FIELD-003",
            entity_type="field",
            proved_reserves_mmbbl=150,
            probable_reserves_mmbbl=75,
            possible_reserves_mmbbl=50,
            cumulative_production_mmbbl=25,
            original_oil_in_place_mmbbl=500
        )
        
        assert metrics.total_2p_reserves() == 225  # Proved + Probable
        assert metrics.total_3p_reserves() == 275  # Proved + Probable + Possible
        assert metrics.remaining_reserves() == 125  # Proved - Cumulative
        assert metrics.recovery_factor() == 0.30  # (Proved + Cumulative) / OOIP
    
    def test_economic_metrics_price_sensitivity(self):
        """Test price sensitivity analysis"""
        base_metrics = EconomicMetrics(
            entity_id="FIELD-004",
            entity_type="field",
            oil_price_assumption_usd=75.00,
            gas_price_assumption_usd=3.50,
            proved_reserves_mmbbl=100,
            gas_reserves_bcf=500
        )
        
        # Calculate base case value
        base_value = base_metrics.calculate_resource_value()
        
        # Test sensitivity to oil price
        high_price_metrics = base_metrics.copy()
        high_price_metrics.oil_price_assumption_usd = 90.00
        high_value = high_price_metrics.calculate_resource_value()
        
        assert high_value > base_value
        
        # Test sensitivity to gas price
        low_gas_metrics = base_metrics.copy()
        low_gas_metrics.gas_price_assumption_usd = 2.50
        low_value = low_gas_metrics.calculate_resource_value()
        
        assert low_value < base_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])