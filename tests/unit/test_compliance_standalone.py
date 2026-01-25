"""
Standalone test of ComplianceTemplate without package dependencies
"""

import sys
from pathlib import Path
from datetime import date
import tempfile
import shutil

# Import base template first
from worldenergydata.modules.bsee.reports.comprehensive.templates.base import BaseReportTemplate

# Import the compliance template classes directly
from worldenergydata.modules.bsee.reports.comprehensive.templates.compliance_template import (
    ComplianceMetrics,
    EnvironmentalMetrics,
    SafetyMetrics,
    ComplianceTemplate
)

def test_compliance_metrics():
    """Test ComplianceMetrics functionality"""
    print("Testing ComplianceMetrics...")
    
    metrics = ComplianceMetrics(
        entity_id="GC_001",
        entity_type="field",
        report_date=date(2024, 1, 31),
        permitted_production_bbls=100000,
        actual_production_bbls=95000,
        compliance_score=0.95
    )
    
    assert metrics.entity_id == "GC_001"
    assert metrics.production_compliance_percentage() == 95.0
    assert not metrics.is_over_production()
    assert metrics.over_production_amount() == 0
    print("✓ ComplianceMetrics tests passed")

def test_environmental_metrics():
    """Test EnvironmentalMetrics functionality"""
    print("Testing EnvironmentalMetrics...")
    
    metrics = EnvironmentalMetrics(
        entity_id="GC_001",
        spill_incidents=2,
        total_spill_volume_bbls=15.5,
        air_emissions_tons=125.0,
        environmental_violations=0
    )
    
    score = metrics.calculate_environmental_score()
    assert 0.0 <= score <= 1.0
    status = metrics.environmental_status()
    assert status in ["Excellent", "Good", "Fair", "Poor"]
    print("✓ EnvironmentalMetrics tests passed")

def test_safety_metrics():
    """Test SafetyMetrics functionality"""
    print("Testing SafetyMetrics...")
    
    metrics = SafetyMetrics(
        entity_id="GC_001",
        incident_count=1,
        lost_time_incidents=0,
        total_recordables=2,
        man_hours_worked=50000
    )
    
    trir = metrics.calculate_trir()
    ltir = metrics.calculate_ltir()
    safety_score = metrics.calculate_safety_score()
    
    assert trir >= 0
    assert ltir >= 0
    assert 0.0 <= safety_score <= 1.0
    print("✓ SafetyMetrics tests passed")

def test_production_quota():
    """Test ProductionQuota functionality"""
    print("Testing ProductionQuota...")
    
    quota = ProductionQuota(
        entity_id="GC_001",
        oil_quota_bbls=100000,
        gas_quota_mcf=500000,
        actual_oil_bbls=95000,
        actual_gas_mcf=480000
    )
    
    oil_compliance = quota.oil_compliance_percentage()
    gas_compliance = quota.gas_compliance_percentage()
    overall_score = quota.overall_compliance_score()
    
    assert oil_compliance == 95.0
    assert gas_compliance == 96.0
    assert 0.0 <= overall_score <= 1.0
    print("✓ ProductionQuota tests passed")

def test_regulatory_milestone():
    """Test RegulatoryMilestone functionality"""
    print("Testing RegulatoryMilestone...")
    
    milestone = RegulatoryMilestone(
        milestone_id="BSEE_2024_001",
        entity_id="GC_001",
        description="Submit annual production report",
        due_date=date(2024, 3, 31),
        completion_date=date(2024, 3, 28),
        status="completed"
    )
    
    assert milestone.is_completed() is True
    assert milestone.completion_status() == "Completed"
    print("✓ RegulatoryMilestone tests passed")

def test_compliance_template():
    """Test ComplianceTemplate functionality"""
    print("Testing ComplianceTemplate...")
    
    # Create temporary directory for templates
    temp_dir = Path(tempfile.mkdtemp())
    template_path = temp_dir / "compliance"
    template_path.mkdir(parents=True, exist_ok=True)
    
    try:
        template = ComplianceTemplate(
            template_name="compliance_report",
            version="1.0.0",
            template_path=template_path
        )
        
        assert template.template_name == "compliance_report"
        assert template.template_type == "compliance"
        assert template.version == "1.0.0"
        
        # Test context building
        compliance_metrics = ComplianceMetrics(
            entity_id="GC_001",
            permitted_production_bbls=100000,
            actual_production_bbls=95000
        )
        
        environmental_metrics = EnvironmentalMetrics(
            entity_id="GC_001",
            spill_incidents=1,
            total_spill_volume_bbls=5.0
        )
        
        context = template.build_compliance_context(
            compliance_metrics=compliance_metrics,
            environmental_metrics=environmental_metrics
        )
        
        assert "compliance_metrics" in context
        assert "environmental_metrics" in context
        assert "compliance_summary" in context
        
        # Test regulatory references
        template.add_regulatory_references()
        assert "regulatory_references" in template.context
        refs = template.context["regulatory_references"]
        assert len(refs) > 0
        assert all("title" in ref and "url" in ref for ref in refs)
        
        print("✓ ComplianceTemplate tests passed")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    print("Running ComplianceTemplate standalone tests...")
    
    test_compliance_metrics()
    test_environmental_metrics()
    test_safety_metrics()
    test_production_quota()
    test_regulatory_milestone()
    test_compliance_template()
    
    print("\n🎉 All ComplianceTemplate tests passed successfully!")