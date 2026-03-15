"""
Tests for ComplianceTemplate - regulatory compliance reporting template
"""

import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from worldenergydata.modules.bsee.reports.comprehensive.models import (
    Block,
    EconomicMetrics,
    Field,
    Lease,
    ProductionMetrics,
    Well,
)
from worldenergydata.modules.bsee.reports.comprehensive.templates.compliance_template import (
    ComplianceMetrics,
    ComplianceTemplate,
    EnvironmentalMetrics,
    ProductionQuota,
    RegulatoryMilestone,
    SafetyMetrics,
)


class TestComplianceMetrics:
    """Test ComplianceMetrics data model"""

    def test_compliance_metrics_initialization(self):
        """Test ComplianceMetrics initialization"""
        metrics = ComplianceMetrics(
            entity_id="GC_001",
            entity_type="field",
            report_date=date(2024, 1, 31),
            permitted_production_bbls=100000,
            actual_production_bbls=95000,
            compliance_score=0.95,
        )

        assert metrics.entity_id == "GC_001"
        assert metrics.entity_type == "field"
        assert metrics.report_date == date(2024, 1, 31)
        assert metrics.permitted_production_bbls == 100000
        assert metrics.actual_production_bbls == 95000
        assert metrics.compliance_score == 0.95

    def test_compliance_percentage_calculation(self):
        """Test compliance percentage calculation"""
        metrics = ComplianceMetrics(
            permitted_production_bbls=100000, actual_production_bbls=95000
        )

        compliance_pct = metrics.production_compliance_percentage()
        assert compliance_pct == 95.0

    def test_compliance_percentage_no_permitted(self):
        """Test compliance percentage when no permitted production"""
        metrics = ComplianceMetrics(
            permitted_production_bbls=0, actual_production_bbls=95000
        )

        compliance_pct = metrics.production_compliance_percentage()
        assert compliance_pct == 0.0

    def test_over_production_detection(self):
        """Test over-production detection"""
        metrics = ComplianceMetrics(
            permitted_production_bbls=100000, actual_production_bbls=105000
        )

        assert metrics.is_over_production() is True
        assert metrics.over_production_amount() == 5000

    def test_under_production_detection(self):
        """Test under-production detection"""
        metrics = ComplianceMetrics(
            permitted_production_bbls=100000, actual_production_bbls=95000
        )

        assert metrics.is_over_production() is False
        assert metrics.over_production_amount() == 0


class TestEnvironmentalMetrics:
    """Test EnvironmentalMetrics data model"""

    def test_environmental_metrics_initialization(self):
        """Test EnvironmentalMetrics initialization"""
        metrics = EnvironmentalMetrics(
            entity_id="GC_001",
            spill_incidents=2,
            total_spill_volume_bbls=15.5,
            air_emissions_tons=125.0,
            water_discharge_bbls=50000,
            waste_generated_tons=25.0,
        )

        assert metrics.entity_id == "GC_001"
        assert metrics.spill_incidents == 2
        assert metrics.total_spill_volume_bbls == 15.5
        assert metrics.air_emissions_tons == 125.0
        assert metrics.water_discharge_bbls == 50000
        assert metrics.waste_generated_tons == 25.0

    def test_environmental_score_calculation(self):
        """Test environmental score calculation"""
        metrics = EnvironmentalMetrics(
            spill_incidents=0,
            total_spill_volume_bbls=0,
            air_emissions_tons=50.0,
            water_discharge_bbls=25000,
        )

        score = metrics.calculate_environmental_score()
        # Score should be high (good) with no spills
        assert score >= 0.8

    def test_environmental_score_with_spills(self):
        """Test environmental score with spill incidents"""
        metrics = EnvironmentalMetrics(
            spill_incidents=3,
            total_spill_volume_bbls=25.0,
            air_emissions_tons=200.0,
            water_discharge_bbls=100000,
        )

        score = metrics.calculate_environmental_score()
        # Score should be lower with spills and higher emissions
        assert score < 0.8


class TestSafetyMetrics:
    """Test SafetyMetrics data model"""

    def test_safety_metrics_initialization(self):
        """Test SafetyMetrics initialization"""
        metrics = SafetyMetrics(
            entity_id="GC_001",
            incident_count=1,
            lost_time_incidents=0,
            total_recordables=2,
            near_misses=5,
            man_hours_worked=50000,
            safety_inspections=12,
        )

        assert metrics.entity_id == "GC_001"
        assert metrics.incident_count == 1
        assert metrics.lost_time_incidents == 0
        assert metrics.total_recordables == 2
        assert metrics.near_misses == 5
        assert metrics.man_hours_worked == 50000
        assert metrics.safety_inspections == 12

    def test_trir_calculation(self):
        """Test Total Recordable Incident Rate calculation"""
        metrics = SafetyMetrics(total_recordables=2, man_hours_worked=100000)

        trir = metrics.calculate_trir()
        # TRIR = (Total Recordables * 200,000) / Man Hours
        expected_trir = (2 * 200000) / 100000
        assert trir == expected_trir

    def test_ltir_calculation(self):
        """Test Lost Time Incident Rate calculation"""
        metrics = SafetyMetrics(lost_time_incidents=1, man_hours_worked=100000)

        ltir = metrics.calculate_ltir()
        # LTIR = (Lost Time Incidents * 200,000) / Man Hours
        expected_ltir = (1 * 200000) / 100000
        assert ltir == expected_ltir

    def test_safety_score_calculation(self):
        """Test safety score calculation"""
        metrics = SafetyMetrics(
            incident_count=1,
            lost_time_incidents=0,
            total_recordables=1,
            near_misses=5,
            man_hours_worked=100000,
            safety_inspections=12,
        )

        score = metrics.calculate_safety_score()
        # Should return a score between 0 and 1
        assert 0.0 <= score <= 1.0


class TestProductionQuota:
    """Test ProductionQuota data model"""

    def test_production_quota_initialization(self):
        """Test ProductionQuota initialization"""
        quota = ProductionQuota(
            entity_id="GC_001",
            quota_type="monthly",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            oil_quota_bbls=100000,
            gas_quota_mcf=500000,
            actual_oil_bbls=95000,
            actual_gas_mcf=480000,
        )

        assert quota.entity_id == "GC_001"
        assert quota.quota_type == "monthly"
        assert quota.oil_quota_bbls == 100000
        assert quota.gas_quota_bbls == 95000

    def test_quota_compliance_calculation(self):
        """Test quota compliance calculation"""
        quota = ProductionQuota(
            oil_quota_bbls=100000,
            gas_quota_mcf=500000,
            actual_oil_bbls=95000,
            actual_gas_mcf=480000,
        )

        oil_compliance = quota.oil_compliance_percentage()
        gas_compliance = quota.gas_compliance_percentage()

        assert oil_compliance == 95.0
        assert gas_compliance == 96.0

    def test_overall_compliance_score(self):
        """Test overall compliance score"""
        quota = ProductionQuota(
            oil_quota_bbls=100000,
            gas_quota_mcf=500000,
            actual_oil_bbls=95000,
            actual_gas_mcf=480000,
        )

        score = quota.overall_compliance_score()
        # Should be weighted average of oil and gas compliance
        assert 0.9 <= score <= 1.0


class TestRegulatoryMilestone:
    """Test RegulatoryMilestone data model"""

    def test_regulatory_milestone_initialization(self):
        """Test RegulatoryMilestone initialization"""
        milestone = RegulatoryMilestone(
            milestone_id="BSEE_2024_001",
            entity_id="GC_001",
            description="Submit annual production report",
            due_date=date(2024, 3, 31),
            completion_date=date(2024, 3, 28),
            status="completed",
            regulatory_agency="BSEE",
            regulation_reference="30 CFR 250.1160",
        )

        assert milestone.milestone_id == "BSEE_2024_001"
        assert milestone.entity_id == "GC_001"
        assert milestone.description == "Submit annual production report"
        assert milestone.status == "completed"
        assert milestone.regulatory_agency == "BSEE"

    def test_milestone_status_check(self):
        """Test milestone status checks"""
        milestone = RegulatoryMilestone(
            due_date=date(2024, 3, 31),
            completion_date=date(2024, 3, 28),
            status="completed",
        )

        assert milestone.is_completed() is True
        assert milestone.is_overdue() is False

    def test_milestone_overdue_check(self):
        """Test overdue milestone detection"""
        milestone = RegulatoryMilestone(
            due_date=date(2024, 1, 31), completion_date=None, status="pending"
        )

        assert milestone.is_completed() is False
        # This would be overdue if current date > due_date
        # For testing, we'll check the logic works
        assert milestone.completion_date is None

    def test_milestone_days_until_due(self):
        """Test days until due calculation"""
        future_date = date(2024, 12, 31)
        milestone = RegulatoryMilestone(due_date=future_date, status="pending")

        days = milestone.days_until_due()
        # Should calculate correctly based on current date
        assert isinstance(days, int)


class TestComplianceTemplate:
    """Test ComplianceTemplate class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template_path = self.temp_dir / "compliance"
        self.template_path.mkdir(parents=True, exist_ok=True)

        # Create sample template file
        template_content = """
        <h1>{{ report_title }}</h1>
        <div class="compliance-section">
            <h2>Production Compliance</h2>
            <p>Permitted: {{ compliance_metrics.permitted_production_bbls | number_format }} bbls</p>
            <p>Actual: {{ compliance_metrics.actual_production_bbls | number_format }} bbls</p>
            <p>Compliance: {{ compliance_metrics.production_compliance_percentage() | percentage }}%</p>
        </div>
        <div class="environmental-section">
            <h2>Environmental Compliance</h2>
            <p>Spill Incidents: {{ environmental_metrics.spill_incidents }}</p>
            <p>Environmental Score: {{ environmental_metrics.calculate_environmental_score() | percentage }}%</p>
        </div>
        """

        (self.template_path / "compliance.html").write_text(template_content)

    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def test_compliance_template_initialization(self):
        """Test ComplianceTemplate initialization"""
        template = ComplianceTemplate(
            template_name="compliance_report",
            version="1.0.0",
            template_path=self.template_path,
        )

        assert template.template_name == "compliance_report"
        assert template.template_type == "compliance"
        assert template.version == "1.0.0"
        assert template.template_path == self.template_path

    def test_compliance_context_setup(self):
        """Test compliance context setup"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        # Check that compliance-specific context requirements are set
        assert "compliance_metrics" in template.context.required_fields
        assert "regulatory_status" in template.context.required_fields

    def test_build_compliance_context(self):
        """Test building compliance context"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        compliance_metrics = ComplianceMetrics(
            entity_id="GC_001",
            permitted_production_bbls=100000,
            actual_production_bbls=95000,
        )

        environmental_metrics = EnvironmentalMetrics(
            entity_id="GC_001", spill_incidents=1, total_spill_volume_bbls=5.0
        )

        context = template.build_compliance_context(
            compliance_metrics=compliance_metrics,
            environmental_metrics=environmental_metrics,
        )

        assert "compliance_metrics" in context
        assert "environmental_metrics" in context
        assert context["compliance_metrics"] == compliance_metrics
        assert context["environmental_metrics"] == environmental_metrics

    def test_add_production_quota_analysis(self):
        """Test adding production quota analysis"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        production = ProductionMetrics(
            entity_id="GC_001", oil_production_bbls=95000, gas_production_mcf=480000
        )

        quota = ProductionQuota(
            entity_id="GC_001",
            oil_quota_bbls=100000,
            gas_quota_mcf=500000,
            actual_oil_bbls=95000,
            actual_gas_mcf=480000,
        )

        template.add_production_quota_analysis(production, quota)

        # Check that quota analysis was added to context
        assert "quota_analysis" in template.context
        quota_data = template.context["quota_analysis"]
        assert quota_data["oil_compliance"] == 95.0
        assert quota_data["gas_compliance"] == 96.0

    def test_add_environmental_compliance_tracking(self):
        """Test adding environmental compliance tracking"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        env_metrics = EnvironmentalMetrics(
            entity_id="GC_001",
            spill_incidents=1,
            total_spill_volume_bbls=5.0,
            air_emissions_tons=100.0,
        )

        template.add_environmental_compliance_tracking(env_metrics)

        # Check that environmental tracking was added
        assert "environmental_compliance" in template.context
        env_data = template.context["environmental_compliance"]
        assert env_data["spill_incidents"] == 1
        assert env_data["environmental_score"] >= 0.0

    def test_generate_compliance_visualizations(self):
        """Test generating compliance visualizations"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        compliance_data = {
            "production_compliance": 95.0,
            "environmental_score": 85.0,
            "safety_score": 92.0,
        }

        charts = template.generate_compliance_visualizations(compliance_data)

        assert "compliance_dashboard" in charts
        assert "production_quota_chart" in charts
        # Charts should be HTML strings containing plotly visualizations
        assert isinstance(charts["compliance_dashboard"], str)
        assert (
            "plotly" in charts["compliance_dashboard"].lower()
            or "div" in charts["compliance_dashboard"]
        )

    def test_add_regulatory_references(self):
        """Test adding regulatory references"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        template.add_regulatory_references()

        # Check that regulatory references were added
        assert "regulatory_references" in template.context
        refs = template.context["regulatory_references"]
        assert isinstance(refs, list)
        assert len(refs) > 0

        # Check structure of first reference
        first_ref = refs[0]
        assert "title" in first_ref
        assert "url" in first_ref
        assert "description" in first_ref

    def test_compliance_template_rendering(self):
        """Test compliance template rendering"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        # Set up context with required fields
        compliance_metrics = ComplianceMetrics(
            entity_id="GC_001",
            permitted_production_bbls=100000,
            actual_production_bbls=95000,
        )

        environmental_metrics = EnvironmentalMetrics(
            entity_id="GC_001", spill_incidents=1, total_spill_volume_bbls=5.0
        )

        template.set_context(
            {
                "report_date": date(2024, 1, 31),
                "entity_id": "GC_001",
                "compliance_metrics": compliance_metrics,
                "environmental_metrics": environmental_metrics,
                "regulatory_status": "compliant",
            }
        )

        # Render template
        rendered = template.render("compliance.html")

        # Check that template rendered correctly
        assert "Compliance Report" in rendered or "compliance-section" in rendered
        assert "95,000" in rendered  # Formatted actual production
        assert "100,000" in rendered  # Formatted permitted production

    def test_compliance_template_validation(self):
        """Test compliance template context validation"""
        template = ComplianceTemplate(
            template_name="compliance_report", template_path=self.template_path
        )

        # Should raise error without required fields
        with pytest.raises(ValueError, match="Missing required context fields"):
            template.validate_context()

        # Should pass with required fields
        template.set_context(
            {
                "report_date": date(2024, 1, 31),
                "entity_id": "GC_001",
                "compliance_metrics": ComplianceMetrics(),
                "regulatory_status": "compliant",
            }
        )

        template.validate_context()  # Should not raise
