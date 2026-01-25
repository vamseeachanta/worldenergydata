"""
Tests for report generation functionality.

Tests verification report templates, export functionality, and integration
with existing PDF and Excel exporters.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime
import pandas as pd
import json

from worldenergydata.modules.analysis.verification.reports import (
    VerificationReportGenerator,
    ReportTemplate,
    ReportSection,
    VerificationSummary,
    DataQualityReport,
    AuditTrailReport
)


class TestReportTemplate:
    """Test report template functionality."""
    
    def test_template_creation(self):
        """Test creating a report template."""
        template = ReportTemplate(
            name="verification_report",
            title="Well Data Verification Report",
            sections=[]
        )
        
        assert template.name == "verification_report"
        assert template.title == "Well Data Verification Report"
        assert template.sections == []
    
    def test_add_section(self):
        """Test adding sections to template."""
        template = ReportTemplate(
            name="test",
            title="Test Report"
        )
        
        section = ReportSection(
            title="Summary",
            content="Test content"
        )
        
        template.add_section(section)
        assert len(template.sections) == 1
        assert template.sections[0].title == "Summary"
    
    def test_template_metadata(self):
        """Test template metadata."""
        template = ReportTemplate(
            name="test",
            title="Test Report",
            metadata={
                "author": "System",
                "version": "1.0.0",
                "date": datetime.now()
            }
        )
        
        assert template.metadata["author"] == "System"
        assert template.metadata["version"] == "1.0.0"
        assert "date" in template.metadata


class TestVerificationSummary:
    """Test verification summary generation."""
    
    def test_summary_creation(self):
        """Test creating verification summary."""
        summary = VerificationSummary(
            total_wells=100,
            wells_verified=95,
            issues_found=10,
            critical_issues=2
        )
        
        assert summary.total_wells == 100
        assert summary.wells_verified == 95
        assert summary.issues_found == 10
        assert summary.critical_issues == 2
        assert summary.verification_rate == 0.95
    
    def test_summary_statistics(self):
        """Test summary statistics calculation."""
        summary = VerificationSummary(
            total_wells=100,
            wells_verified=80,
            issues_found=15,
            critical_issues=3
        )
        
        stats = summary.get_statistics()
        assert stats["verification_rate"] == 0.80
        assert stats["issue_rate"] == 0.15
        assert stats["critical_rate"] == 0.03
        assert stats["quality_score"] == 0.85  # 100 - 15 issues / 100
    
    def test_summary_to_dict(self):
        """Test converting summary to dictionary."""
        summary = VerificationSummary(
            total_wells=50,
            wells_verified=50,
            issues_found=5,
            critical_issues=1
        )
        
        data = summary.to_dict()
        assert data["total_wells"] == 50
        assert data["wells_verified"] == 50
        assert data["issues_found"] == 5
        assert data["critical_issues"] == 1
        assert data["verification_rate"] == 1.0


class TestDataQualityReport:
    """Test data quality report generation."""
    
    def test_quality_report_creation(self):
        """Test creating data quality report."""
        report = DataQualityReport(
            completeness_score=0.95,
            accuracy_score=0.92,
            consistency_score=0.88
        )
        
        assert report.completeness_score == 0.95
        assert report.accuracy_score == 0.92
        assert report.consistency_score == 0.88
        assert report.overall_score == pytest.approx(0.916, rel=1e-3)
    
    def test_add_validation_results(self):
        """Test adding validation results to report."""
        report = DataQualityReport()
        
        validation_results = [
            {"field": "production_date", "status": "pass", "message": "All dates valid"},
            {"field": "oil_volume", "status": "warning", "message": "5 outliers detected"},
            {"field": "gas_volume", "status": "fail", "message": "Missing 10% of values"}
        ]
        
        report.add_validation_results(validation_results)
        assert len(report.validation_results) == 3
        assert report.passed_validations == 1
        assert report.warnings == 1
        assert report.failures == 1
    
    def test_quality_metrics(self):
        """Test quality metrics calculation."""
        report = DataQualityReport(
            completeness_score=0.90,
            accuracy_score=0.85,
            consistency_score=0.95
        )
        
        metrics = report.get_quality_metrics()
        assert metrics["completeness"] == 0.90
        assert metrics["accuracy"] == 0.85
        assert metrics["consistency"] == 0.95
        assert metrics["overall"] == pytest.approx(0.90, rel=1e-2)
        assert metrics["grade"] == "A"  # 90% = A grade


class TestAuditTrailReport:
    """Test audit trail report generation."""
    
    def test_audit_report_creation(self):
        """Test creating audit trail report."""
        report = AuditTrailReport(
            start_time=datetime(2025, 1, 1, 9, 0),
            end_time=datetime(2025, 1, 1, 10, 30)
        )
        
        assert report.start_time == datetime(2025, 1, 1, 9, 0)
        assert report.end_time == datetime(2025, 1, 1, 10, 30)
        assert report.duration_minutes == 90
    
    def test_add_audit_entries(self):
        """Test adding audit entries."""
        report = AuditTrailReport()
        
        entries = [
            {"timestamp": datetime.now(), "user": "analyst1", "action": "verified_well", "well_id": "W001"},
            {"timestamp": datetime.now(), "user": "analyst1", "action": "flagged_issue", "well_id": "W002"},
            {"timestamp": datetime.now(), "user": "analyst2", "action": "approved_data", "well_id": "W003"}
        ]
        
        report.add_entries(entries)
        assert len(report.entries) == 3
        assert report.unique_users == 2
        assert report.total_actions == 3
    
    def test_audit_summary(self):
        """Test audit summary generation."""
        report = AuditTrailReport(
            start_time=datetime(2025, 1, 1, 9, 0),
            end_time=datetime(2025, 1, 1, 11, 0)
        )
        
        entries = [
            {"timestamp": datetime.now(), "user": "user1", "action": "login"},
            {"timestamp": datetime.now(), "user": "user1", "action": "verify"},
            {"timestamp": datetime.now(), "user": "user2", "action": "review"}
        ]
        
        report.add_entries(entries)
        summary = report.get_summary()
        
        assert summary["duration_hours"] == 2.0
        assert summary["total_actions"] == 3
        assert summary["unique_users"] == 2
        assert summary["actions_per_hour"] == 1.5


class TestVerificationReportGenerator:
    """Test main report generator."""
    
    def test_generator_initialization(self):
        """Test report generator initialization."""
        generator = VerificationReportGenerator()
        
        # Generator now initializes with default templates
        assert 'verification' in generator.templates
        assert 'summary' in generator.templates
        assert generator.current_report is None
    
    def test_load_template(self):
        """Test loading report template."""
        generator = VerificationReportGenerator()
        
        template = ReportTemplate(
            name="verification",
            title="Verification Report"
        )
        
        generator.load_template(template)
        assert "verification" in generator.templates
        assert generator.templates["verification"] == template
    
    def test_create_verification_report(self):
        """Test creating full verification report."""
        generator = VerificationReportGenerator()
        
        # Create mock data
        summary = VerificationSummary(
            total_wells=100,
            wells_verified=95,
            issues_found=10,
            critical_issues=2
        )
        
        quality = DataQualityReport(
            completeness_score=0.95,
            accuracy_score=0.92,
            consistency_score=0.88
        )
        
        audit = AuditTrailReport(
            start_time=datetime(2025, 1, 1, 9, 0),
            end_time=datetime(2025, 1, 1, 10, 0)
        )
        
        report = generator.create_verification_report(
            summary=summary,
            quality=quality,
            audit=audit
        )
        
        assert report is not None
        assert report.title == "Well Data Verification Report"
        assert len(report.sections) >= 3  # At least summary, quality, audit sections
    
    def test_export_to_pdf(self):
        """Test exporting report to PDF."""
        import tempfile
        import os
        
        generator = VerificationReportGenerator()
        
        # Create a simple report
        report = generator.create_verification_report(
            summary=VerificationSummary(100, 95, 10, 2),
            quality=DataQualityReport(0.95, 0.92, 0.88),
            audit=AuditTrailReport()
        )
        
        # Create temporary file for output
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.pdf"
            result_path = generator.export_to_pdf(report, output_path)
            
            # Check file was created
            assert result_path.exists()
            assert result_path == output_path
            
            # Check file has content
            assert os.path.getsize(result_path) > 0
    
    def test_export_to_excel(self):
        """Test exporting report to Excel."""
        import tempfile
        import os
        
        generator = VerificationReportGenerator()
        
        # Create a simple report
        report = generator.create_verification_report(
            summary=VerificationSummary(100, 95, 10, 2),
            quality=DataQualityReport(0.95, 0.92, 0.88),
            audit=AuditTrailReport()
        )
        
        # Create temporary file for output
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.xlsx"
            result_path = generator.export_to_excel(report, output_path)
            
            # Check file was created
            assert result_path.exists()
            assert result_path == output_path
            
            # Check file has content
            assert os.path.getsize(result_path) > 0
    
    def test_report_with_data_tables(self):
        """Test report with data tables."""
        generator = VerificationReportGenerator()
        
        # Create report with data tables
        df_wells = pd.DataFrame({
            'well_id': ['W001', 'W002', 'W003'],
            'status': ['verified', 'pending', 'verified'],
            'issues': [0, 2, 1]
        })
        
        report = generator.create_verification_report(
            summary=VerificationSummary(100, 95, 10, 2),
            quality=DataQualityReport(0.95, 0.92, 0.88),
            audit=AuditTrailReport(),
            data_tables={'wells': df_wells}
        )
        
        assert 'wells' in report.data_tables
        assert len(report.data_tables['wells']) == 3
    
    def test_report_with_charts(self):
        """Test report with charts configuration."""
        generator = VerificationReportGenerator()
        
        charts_config = {
            'verification_progress': {
                'type': 'bar',
                'data': {'verified': 95, 'pending': 5}
            },
            'quality_scores': {
                'type': 'radar',
                'data': {'completeness': 0.95, 'accuracy': 0.92, 'consistency': 0.88}
            }
        }
        
        report = generator.create_verification_report(
            summary=VerificationSummary(100, 95, 10, 2),
            quality=DataQualityReport(0.95, 0.92, 0.88),
            audit=AuditTrailReport(),
            charts=charts_config
        )
        
        assert 'verification_progress' in report.charts
        assert report.charts['verification_progress']['type'] == 'bar'
    
    def test_batch_report_generation(self):
        """Test generating reports for multiple datasets."""
        generator = VerificationReportGenerator()
        
        datasets = [
            {'name': 'Field_A', 'wells': 50, 'verified': 48},
            {'name': 'Field_B', 'wells': 75, 'verified': 70},
            {'name': 'Field_C', 'wells': 100, 'verified': 95}
        ]
        
        reports = []
        for data in datasets:
            summary = VerificationSummary(
                total_wells=data['wells'],
                wells_verified=data['verified'],
                issues_found=data['wells'] - data['verified'],
                critical_issues=0
            )
            
            report = generator.create_verification_report(
                summary=summary,
                quality=DataQualityReport(0.95, 0.92, 0.88),
                audit=AuditTrailReport(),
                title=f"Verification Report - {data['name']}"
            )
            reports.append(report)
        
        assert len(reports) == 3
        assert reports[0].title == "Verification Report - Field_A"
        assert reports[1].title == "Verification Report - Field_B"
        assert reports[2].title == "Verification Report - Field_C"