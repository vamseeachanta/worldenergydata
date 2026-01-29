"""
Tests for the Operational Template and related metrics.
"""

import json
import unittest
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from worldenergydata.modules.bsee.reports.comprehensive.templates.operational_template import (
    EquipmentMetrics,
    FailureAnalysis,
    MaintenanceRecord,
    OperationalKPI,
    OperationalTemplate,
    ProductionEfficiencyMetrics,
    WellOperationalMetrics,
    WellStatus,
)


class TestWellOperationalMetrics(unittest.TestCase):
    """Test WellOperationalMetrics data class and calculations"""

    def setUp(self):
        """Set up test data"""
        self.metrics = WellOperationalMetrics(
            well_api=12345678,
            well_name="Test Well A-1",
            status=WellStatus.PRODUCING,
            report_date=date(2025, 8, 26),
            drilling_start_date=date(2025, 1, 1),
            drilling_end_date=date(2025, 2, 15),
            completion_start_date=date(2025, 2, 16),
            completion_end_date=date(2025, 3, 15),
            first_production_date=date(2025, 3, 20),
            last_production_date=date(2025, 8, 26),
            drilling_depth_ft=15000,
            total_depth_ft=18500,
            lateral_length_ft=3500,
            planned_drilling_days=40,
            actual_drilling_days=45,
            planned_completion_days=25,
            actual_completion_days=28,
            drilling_cost=5000000,
            completion_cost=3500000,
            daily_production_boe=1500,
            cumulative_production_boe=225000,
            uptime_hours=3840,
            total_hours=4320,
        )

    def test_metrics_initialization(self):
        """Test that metrics are properly initialized"""
        self.assertEqual(self.metrics.well_api, 12345678)
        self.assertEqual(self.metrics.well_name, "Test Well A-1")
        self.assertEqual(self.metrics.status, WellStatus.PRODUCING)
        self.assertEqual(self.metrics.drilling_depth_ft, 15000)

    def test_drilling_efficiency_calculation(self):
        """Test drilling efficiency calculation"""
        efficiency = self.metrics.drilling_efficiency()
        expected = (40 / 45) * 100  # 88.89%
        self.assertAlmostEqual(efficiency, expected, places=2)

    def test_completion_efficiency_calculation(self):
        """Test completion efficiency calculation"""
        efficiency = self.metrics.completion_efficiency()
        expected = (25 / 28) * 100  # 89.29%
        self.assertAlmostEqual(efficiency, expected, places=2)

    def test_well_cycle_time_calculation(self):
        """Test well cycle time calculation"""
        cycle_time = self.metrics.well_cycle_time()
        # From drilling start to first production
        expected = (date(2025, 3, 20) - date(2025, 1, 1)).days
        self.assertEqual(cycle_time, expected)

    def test_availability_calculation(self):
        """Test availability percentage calculation"""
        availability = self.metrics.availability_percentage()
        expected = (3840 / 4320) * 100  # 88.89%
        self.assertAlmostEqual(availability, expected, places=2)

    def test_drilling_rate_calculation(self):
        """Test drilling rate calculation"""
        rate = self.metrics.drilling_rate_ft_per_day()
        expected = 15000 / 45  # 333.33 ft/day
        self.assertAlmostEqual(rate, expected, places=2)

    def test_cost_per_foot_calculation(self):
        """Test cost per foot drilled calculation"""
        cost_per_ft = self.metrics.cost_per_foot_drilled()
        expected = (5000000 + 3500000) / 18500  # $459.46/ft
        self.assertAlmostEqual(cost_per_ft, expected, places=2)

    def test_production_days_calculation(self):
        """Test production days calculation"""
        prod_days = self.metrics.production_days()
        expected = (date(2025, 8, 26) - date(2025, 3, 20)).days + 1
        self.assertEqual(prod_days, expected)


class TestProductionEfficiencyMetrics(unittest.TestCase):
    """Test ProductionEfficiencyMetrics calculations"""

    def setUp(self):
        """Set up test data"""
        self.metrics = ProductionEfficiencyMetrics(
            entity_id="FIELD-001",
            entity_type="field",
            report_date=date(2025, 8, 26),
            production_oil_bbl=50000,
            production_gas_mcf=300000,
            production_water_bbl=10000,
            production_days=30,
            operating_days=28,
            design_capacity_boe=2000,
            actual_production_boe=55000,
            wells_producing=10,
            wells_shut_in=2,
            wells_offline=1,
            total_wells=13,
            processing_capacity_bbl=2500,
            processing_utilization_pct=85.0,
        )

    def test_production_efficiency_calculation(self):
        """Test production efficiency calculation"""
        efficiency = self.metrics.production_efficiency()
        # actual_production / (design_capacity * production_days)
        expected = 55000 / (2000 * 30) * 100
        self.assertAlmostEqual(efficiency, expected, places=2)

    def test_operating_efficiency_calculation(self):
        """Test operating efficiency calculation"""
        efficiency = self.metrics.operating_efficiency()
        expected = (28 / 30) * 100  # 93.33%
        self.assertAlmostEqual(efficiency, expected, places=2)

    def test_well_availability_calculation(self):
        """Test well availability calculation"""
        availability = self.metrics.well_availability()
        expected = (10 / 13) * 100  # 76.92%
        self.assertAlmostEqual(availability, expected, places=2)

    def test_daily_production_rate_calculation(self):
        """Test daily production rate calculation"""
        rate = self.metrics.daily_production_rate_boe()
        expected = 55000 / 30  # 1833.33 BOE/day
        self.assertAlmostEqual(rate, expected, places=2)

    def test_water_cut_calculation(self):
        """Test water cut percentage calculation"""
        water_cut = self.metrics.water_cut_percentage()
        expected = (10000 / (50000 + 10000)) * 100  # 16.67%
        self.assertAlmostEqual(water_cut, expected, places=2)

    def test_gas_oil_ratio_calculation(self):
        """Test gas-oil ratio calculation"""
        gor = self.metrics.gas_oil_ratio()
        expected = 300000 / 50000  # 6.0 mcf/bbl
        self.assertAlmostEqual(gor, expected, places=2)


class TestEquipmentMetrics(unittest.TestCase):
    """Test EquipmentMetrics data class"""

    def setUp(self):
        """Set up test equipment data"""
        self.metrics = EquipmentMetrics(
            equipment_id="PUMP-001",
            equipment_type="ESP",
            equipment_name="Submersible Pump 001",
            installation_date=date(2024, 1, 1),
            report_date=date(2025, 8, 26),
            total_runtime_hours=12000,
            planned_runtime_hours=13000,
            unplanned_downtime_hours=500,
            planned_downtime_hours=500,
            failure_count=3,
            mtbf_hours=4000,
            mttr_hours=24,
            maintenance_cost=50000,
            replacement_cost=250000,
            efficiency_rating=92.0,
        )

    def test_equipment_availability_calculation(self):
        """Test equipment availability calculation"""
        availability = self.metrics.equipment_availability()
        total = 12000 + 500 + 500  # runtime + downtime
        expected = (12000 / total) * 100
        self.assertAlmostEqual(availability, expected, places=2)

    def test_equipment_utilization_calculation(self):
        """Test equipment utilization calculation"""
        utilization = self.metrics.equipment_utilization()
        expected = (12000 / 13000) * 100
        self.assertAlmostEqual(utilization, expected, places=2)

    def test_equipment_reliability_calculation(self):
        """Test equipment reliability calculation"""
        reliability = self.metrics.equipment_reliability()
        # MTBF / (MTBF + MTTR) * 100
        expected = (4000 / (4000 + 24)) * 100
        self.assertAlmostEqual(reliability, expected, places=2)

    def test_equipment_age_calculation(self):
        """Test equipment age calculation"""
        age = self.metrics.equipment_age_days()
        expected = (date(2025, 8, 26) - date(2024, 1, 1)).days
        self.assertEqual(age, expected)

    def test_cost_effectiveness_calculation(self):
        """Test cost effectiveness calculation"""
        cost_eff = self.metrics.cost_effectiveness_ratio()
        expected = 50000 / 250000  # 0.2
        self.assertAlmostEqual(cost_eff, expected, places=2)


class TestMaintenanceRecord(unittest.TestCase):
    """Test MaintenanceRecord data class"""

    def setUp(self):
        """Set up test maintenance record"""
        self.record = MaintenanceRecord(
            maintenance_id="MAINT-2025-001",
            equipment_id="PUMP-001",
            maintenance_date=date(2025, 8, 15),
            maintenance_type="preventive",
            description="Annual pump inspection and service",
            duration_hours=8,
            cost=5000,
            performed_by="Service Team A",
            next_scheduled_date=date(2026, 8, 15),
            effectiveness_score=95.0,
        )

    def test_maintenance_record_creation(self):
        """Test maintenance record is properly created"""
        self.assertEqual(self.record.maintenance_id, "MAINT-2025-001")
        self.assertEqual(self.record.maintenance_type, "preventive")
        self.assertEqual(self.record.duration_hours, 8)
        self.assertEqual(self.record.cost, 5000)

    def test_is_overdue_calculation(self):
        """Test overdue status calculation"""
        # Not overdue - next date is in future
        self.assertFalse(self.record.is_overdue())

        # Create overdue record
        overdue_record = MaintenanceRecord(
            maintenance_id="MAINT-2025-002",
            equipment_id="PUMP-002",
            maintenance_date=date(2024, 8, 15),
            maintenance_type="preventive",
            description="Overdue maintenance",
            duration_hours=4,
            cost=2500,
            performed_by="Service Team B",
            next_scheduled_date=date(2025, 7, 15),
            effectiveness_score=90.0,
        )
        self.assertTrue(overdue_record.is_overdue())

    def test_days_until_next_calculation(self):
        """Test days until next maintenance calculation"""
        days = self.record.days_until_next()
        expected = (date(2026, 8, 15) - date(2025, 8, 26)).days
        self.assertEqual(days, expected)


class TestFailureAnalysis(unittest.TestCase):
    """Test FailureAnalysis data class"""

    def setUp(self):
        """Set up test failure record"""
        self.failure = FailureAnalysis(
            failure_id="FAIL-2025-001",
            equipment_id="PUMP-001",
            well_api=12345678,
            failure_date=datetime(2025, 8, 20, 14, 30),
            failure_type="mechanical",
            root_cause="Bearing wear due to sand ingression",
            severity="high",
            production_impact_boe=500,
            downtime_hours=48,
            repair_cost=25000,
            preventable=True,
            corrective_actions=[
                "Install sand screens",
                "Increase monitoring frequency",
            ],
            lessons_learned="Need better sand control measures",
        )

    def test_failure_analysis_creation(self):
        """Test failure analysis record creation"""
        self.assertEqual(self.failure.failure_id, "FAIL-2025-001")
        self.assertEqual(self.failure.failure_type, "mechanical")
        self.assertEqual(self.failure.severity, "high")
        self.assertEqual(self.failure.downtime_hours, 48)

    def test_total_impact_calculation(self):
        """Test total impact calculation"""
        # Assuming oil price of $80/bbl for BOE
        impact = self.failure.total_impact_cost(oil_price=80)
        expected = 25000 + (500 * 80)  # repair + lost production
        self.assertEqual(impact, expected)

    def test_failure_rate_calculation(self):
        """Test failure rate per 1000 hours"""
        # Single failure in 48 hours
        rate = self.failure.failure_rate_per_1000_hours(runtime_hours=4800)
        expected = (1 / 4800) * 1000
        self.assertAlmostEqual(rate, expected, places=4)


class TestOperationalKPI(unittest.TestCase):
    """Test OperationalKPI data class"""

    def setUp(self):
        """Set up test KPI"""
        self.kpi = OperationalKPI(
            kpi_id="KPI-001",
            kpi_name="Production Efficiency",
            kpi_category="production",
            target_value=95.0,
            actual_value=92.5,
            unit="percent",
            measurement_date=date(2025, 8, 26),
            trend="improving",
            variance=-2.5,
            status="warning",
        )

    def test_kpi_creation(self):
        """Test KPI creation"""
        self.assertEqual(self.kpi.kpi_name, "Production Efficiency")
        self.assertEqual(self.kpi.actual_value, 92.5)
        self.assertEqual(self.kpi.target_value, 95.0)

    def test_performance_percentage_calculation(self):
        """Test performance percentage calculation"""
        performance = self.kpi.performance_percentage()
        expected = (92.5 / 95.0) * 100
        self.assertAlmostEqual(performance, expected, places=2)

    def test_is_on_target(self):
        """Test target achievement check"""
        self.assertFalse(self.kpi.is_on_target())

        # Create on-target KPI
        on_target_kpi = OperationalKPI(
            kpi_id="KPI-002",
            kpi_name="Uptime",
            kpi_category="reliability",
            target_value=90.0,
            actual_value=92.0,
            unit="percent",
            measurement_date=date(2025, 8, 26),
            trend="stable",
            variance=2.0,
            status="good",
        )
        self.assertTrue(on_target_kpi.is_on_target())

    def test_variance_percentage_calculation(self):
        """Test variance percentage calculation"""
        variance = self.kpi.variance_percentage()
        expected = ((92.5 - 95.0) / 95.0) * 100
        self.assertAlmostEqual(variance, expected, places=2)


class TestOperationalTemplate(unittest.TestCase):
    """Test OperationalTemplate class"""

    def setUp(self):
        """Set up test template"""
        self.template = OperationalTemplate(
            template_name="test_operational", version="1.0.0"
        )

        # Create sample operational metrics
        self.well_metrics = WellOperationalMetrics(
            well_api=12345678,
            well_name="Test Well A-1",
            status=WellStatus.PRODUCING,
            report_date=date(2025, 8, 26),
            drilling_start_date=date(2025, 1, 1),
            drilling_end_date=date(2025, 2, 15),
            actual_drilling_days=45,
            planned_drilling_days=40,
            uptime_hours=3840,
            total_hours=4320,
        )

        self.production_metrics = ProductionEfficiencyMetrics(
            entity_id="FIELD-001",
            entity_type="field",
            report_date=date(2025, 8, 26),
            production_oil_bbl=50000,
            production_gas_mcf=300000,
            actual_production_boe=55000,
            design_capacity_boe=2000,
            production_days=30,
        )

    def test_template_initialization(self):
        """Test template is properly initialized"""
        self.assertEqual(self.template.template_type, "operational")
        self.assertEqual(self.template.version, "1.0.0")
        self.assertIsNotNone(self.template.env)

    def test_build_operational_context(self):
        """Test building operational context"""
        context = self.template.build_operational_context(
            well_metrics=[self.well_metrics],
            production_metrics=self.production_metrics,
            report_date=date(2025, 8, 26),
            entity_name="Test Field",
        )

        self.assertIn("operational_summary", context)
        self.assertIn("well_performance", context)
        self.assertIn("production_efficiency", context)
        self.assertIn("report_metadata", context)

    def test_add_drilling_performance_analysis(self):
        """Test adding drilling performance analysis"""
        context = {}
        self.template.add_drilling_performance_analysis(context, [self.well_metrics])

        self.assertIn("drilling_performance", context)
        drilling = context["drilling_performance"]
        self.assertIn("average_drilling_days", drilling)
        self.assertIn("drilling_efficiency", drilling)
        self.assertIn("total_wells_drilled", drilling)

    def test_add_production_optimization_tracking(self):
        """Test adding production optimization tracking"""
        context = {}
        self.template.add_production_optimization_tracking(
            context, self.production_metrics
        )

        self.assertIn("production_optimization", context)
        optimization = context["production_optimization"]
        self.assertIn("production_efficiency", optimization)
        self.assertIn("daily_rate", optimization)
        self.assertIn("capacity_utilization", optimization)

    def test_add_equipment_utilization_analysis(self):
        """Test adding equipment utilization analysis"""
        equipment = EquipmentMetrics(
            equipment_id="PUMP-001",
            equipment_type="ESP",
            equipment_name="Test Pump",
            total_runtime_hours=12000,
            planned_runtime_hours=13000,
            mtbf_hours=4000,
            mttr_hours=24,
        )

        context = {}
        self.template.add_equipment_utilization_analysis(context, [equipment])

        self.assertIn("equipment_analysis", context)
        analysis = context["equipment_analysis"]
        self.assertIn("total_equipment", analysis)
        self.assertIn("average_availability", analysis)
        self.assertIn("average_reliability", analysis)

    def test_calculate_operational_kpis(self):
        """Test operational KPI calculation"""
        kpis = self.template.calculate_operational_kpis(
            well_metrics=[self.well_metrics],
            production_metrics=self.production_metrics,
            equipment_metrics=[],
        )

        self.assertIsInstance(kpis, list)
        self.assertTrue(len(kpis) > 0)

        # Check for specific KPIs
        kpi_names = [kpi.kpi_name for kpi in kpis]
        self.assertIn("Overall Production Efficiency", kpi_names)
        self.assertIn("Well Availability", kpi_names)

    def test_render_template(self):
        """Test template rendering"""
        context = self.template.build_operational_context(
            well_metrics=[self.well_metrics],
            production_metrics=self.production_metrics,
            report_date=date(2025, 8, 26),
            entity_name="Test Field",
        )

        # Template content would normally come from file
        template_content = """
        Operational Report for {{ entity_name }}
        Date: {{ report_metadata.generated_date }}

        Production Efficiency: {{ production_efficiency.efficiency_percentage }}%
        Wells Producing: {{ well_performance.wells_producing }}
        """

        rendered = self.template.render_template_string(template_content, context)

        self.assertIn("Test Field", rendered)
        self.assertIn("Production Efficiency:", rendered)
        self.assertIn("Wells Producing:", rendered)


if __name__ == "__main__":
    unittest.main()
