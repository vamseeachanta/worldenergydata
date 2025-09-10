"""
Report generation module for well data verification.

Provides templates and generators for verification reports, leveraging
existing PDF and Excel exporters from the comprehensive reports module.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import pandas as pd
import json

# Import existing exporters from comprehensive reports  
try:
    from worldenergydata.modules.bsee.reports.comprehensive.exporters import (
        ExportConfig, ExportFormat
    )
    # For now, we'll create simple export functions since the actual exporters
    # have complex dependencies. In production, these would use the real exporters.
    EXPORTERS_AVAILABLE = True
except ImportError:
    # Create minimal stubs if exporters not available
    EXPORTERS_AVAILABLE = False
    
    from enum import Enum
    
    class ExportFormat(Enum):
        """Export format enum."""
        PDF = "pdf"
        EXCEL = "excel"
    
    @dataclass
    class ExportConfig:
        """Export configuration."""
        format: ExportFormat
        output_path: Path
        template_name: Optional[str] = None
        include_charts: bool = True


@dataclass
class ReportSection:
    """Individual section of a report."""
    title: str
    content: Any
    subsections: List['ReportSection'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_subsection(self, subsection: 'ReportSection'):
        """Add a subsection to this section."""
        self.subsections.append(subsection)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary."""
        return {
            'title': self.title,
            'content': self.content,
            'subsections': [s.to_dict() for s in self.subsections],
            'metadata': self.metadata
        }


@dataclass
class ReportTemplate:
    """Template for generating reports."""
    name: str
    title: str
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    data_tables: Dict[str, pd.DataFrame] = field(default_factory=dict)
    charts: Dict[str, Dict] = field(default_factory=dict)
    
    def add_section(self, section: ReportSection):
        """Add a section to the template."""
        self.sections.append(section)
    
    def add_data_table(self, name: str, data: pd.DataFrame):
        """Add a data table to the report."""
        self.data_tables[name] = data
    
    def add_chart(self, name: str, chart_config: Dict):
        """Add a chart configuration to the report."""
        self.charts[name] = chart_config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'name': self.name,
            'title': self.title,
            'sections': [s.to_dict() for s in self.sections],
            'metadata': self.metadata,
            'charts': self.charts
        }


@dataclass
class VerificationSummary:
    """Summary of verification results."""
    total_wells: int
    wells_verified: int
    issues_found: int
    critical_issues: int
    verification_rate: float = field(init=False)
    
    def __post_init__(self):
        """Calculate derived fields."""
        self.verification_rate = (
            self.wells_verified / self.total_wells 
            if self.total_wells > 0 else 0.0
        )
    
    def get_statistics(self) -> Dict[str, float]:
        """Get statistical summary."""
        return {
            'verification_rate': self.verification_rate,
            'issue_rate': self.issues_found / self.total_wells if self.total_wells > 0 else 0.0,
            'critical_rate': self.critical_issues / self.total_wells if self.total_wells > 0 else 0.0,
            'quality_score': (self.total_wells - self.issues_found) / self.total_wells if self.total_wells > 0 else 0.0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_wells': self.total_wells,
            'wells_verified': self.wells_verified,
            'issues_found': self.issues_found,
            'critical_issues': self.critical_issues,
            'verification_rate': self.verification_rate
        }


@dataclass
class DataQualityReport:
    """Report on data quality metrics."""
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    overall_score: float = field(init=False)
    validation_results: List[Dict] = field(default_factory=list)
    passed_validations: int = 0
    warnings: int = 0
    failures: int = 0
    
    def __post_init__(self):
        """Calculate overall score."""
        scores = [self.completeness_score, self.accuracy_score, self.consistency_score]
        self.overall_score = sum(scores) / len(scores) if scores else 0.0
    
    def add_validation_results(self, results: List[Dict]):
        """Add validation results and update counters."""
        self.validation_results.extend(results)
        
        for result in results:
            status = result.get('status', 'unknown')
            if status == 'pass':
                self.passed_validations += 1
            elif status == 'warning':
                self.warnings += 1
            elif status == 'fail':
                self.failures += 1
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics."""
        overall = self.overall_score
        
        # Determine grade based on overall score
        if overall >= 0.95:
            grade = 'A+'
        elif overall >= 0.90:
            grade = 'A'
        elif overall >= 0.85:
            grade = 'B+'
        elif overall >= 0.80:
            grade = 'B'
        elif overall >= 0.75:
            grade = 'C+'
        elif overall >= 0.70:
            grade = 'C'
        elif overall >= 0.60:
            grade = 'D'
        else:
            grade = 'F'
        
        return {
            'completeness': self.completeness_score,
            'accuracy': self.accuracy_score,
            'consistency': self.consistency_score,
            'overall': overall,
            'grade': grade
        }


@dataclass
class AuditTrailReport:
    """Report on audit trail activities."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    entries: List[Dict] = field(default_factory=list)
    unique_users: int = 0
    total_actions: int = 0
    
    @property
    def duration_minutes(self) -> float:
        """Calculate duration in minutes."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 60
        return 0.0
    
    def add_entries(self, entries: List[Dict]):
        """Add audit entries and update statistics."""
        self.entries.extend(entries)
        self.total_actions = len(self.entries)
        
        # Count unique users
        users = set()
        for entry in self.entries:
            if 'user' in entry:
                users.add(entry['user'])
        self.unique_users = len(users)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get audit summary."""
        duration_hours = self.duration_minutes / 60 if self.duration_minutes else 0
        
        return {
            'duration_hours': duration_hours,
            'total_actions': self.total_actions,
            'unique_users': self.unique_users,
            'actions_per_hour': self.total_actions / duration_hours if duration_hours > 0 else 0
        }


class VerificationReportGenerator:
    """Main generator for verification reports."""
    
    def __init__(self):
        """Initialize report generator."""
        self.templates: Dict[str, ReportTemplate] = {}
        self.current_report: Optional[ReportTemplate] = None
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default report templates."""
        # Create default verification template
        verification_template = ReportTemplate(
            name='verification',
            title='Well Data Verification Report',
            metadata={
                'created_at': datetime.now(),
                'version': '1.0.0',
                'type': 'verification'
            }
        )
        self.templates['verification'] = verification_template
        
        # Create summary template
        summary_template = ReportTemplate(
            name='summary',
            title='Verification Summary Report',
            metadata={
                'created_at': datetime.now(),
                'version': '1.0.0',
                'type': 'summary'
            }
        )
        self.templates['summary'] = summary_template
    
    def load_template(self, template: ReportTemplate):
        """Load a custom template."""
        self.templates[template.name] = template
    
    def create_verification_report(
        self,
        summary: VerificationSummary,
        quality: DataQualityReport,
        audit: AuditTrailReport,
        data_tables: Optional[Dict[str, pd.DataFrame]] = None,
        charts: Optional[Dict[str, Dict]] = None,
        title: Optional[str] = None
    ) -> ReportTemplate:
        """Create a complete verification report."""
        # Use custom title or default
        report_title = title or "Well Data Verification Report"
        
        # Create report from template
        report = ReportTemplate(
            name='verification_report',
            title=report_title,
            metadata={
                'generated_at': datetime.now(),
                'generator': 'VerificationReportGenerator',
                'version': '1.0.0'
            }
        )
        
        # Add summary section
        summary_section = ReportSection(
            title='Executive Summary',
            content=self._format_summary(summary),
            metadata={'type': 'summary'}
        )
        report.add_section(summary_section)
        
        # Add data quality section
        quality_section = ReportSection(
            title='Data Quality Assessment',
            content=self._format_quality_report(quality),
            metadata={'type': 'quality'}
        )
        report.add_section(quality_section)
        
        # Add audit trail section
        audit_section = ReportSection(
            title='Audit Trail',
            content=self._format_audit_report(audit),
            metadata={'type': 'audit'}
        )
        report.add_section(audit_section)
        
        # Add data tables if provided
        if data_tables:
            report.data_tables = data_tables
            
            # Add data tables section
            tables_section = ReportSection(
                title='Data Tables',
                content='Detailed data tables included in this report',
                metadata={'type': 'data_tables'}
            )
            
            for table_name in data_tables:
                table_subsection = ReportSection(
                    title=table_name.replace('_', ' ').title(),
                    content=f'Table: {table_name}'
                )
                tables_section.add_subsection(table_subsection)
            
            report.add_section(tables_section)
        
        # Add charts if provided
        if charts:
            report.charts = charts
            
            # Add visualizations section
            viz_section = ReportSection(
                title='Visualizations',
                content='Charts and graphs for data visualization',
                metadata={'type': 'visualizations'}
            )
            report.add_section(viz_section)
        
        self.current_report = report
        return report
    
    def _format_summary(self, summary: VerificationSummary) -> str:
        """Format verification summary for report."""
        stats = summary.get_statistics()
        
        content = f"""
        Verification Overview:
        - Total Wells: {summary.total_wells}
        - Wells Verified: {summary.wells_verified}
        - Verification Rate: {stats['verification_rate']:.1%}
        - Issues Found: {summary.issues_found}
        - Critical Issues: {summary.critical_issues}
        - Quality Score: {stats['quality_score']:.1%}
        """
        
        return content.strip()
    
    def _format_quality_report(self, quality: DataQualityReport) -> str:
        """Format data quality report."""
        metrics = quality.get_quality_metrics()
        
        content = f"""
        Data Quality Metrics:
        - Completeness: {metrics['completeness']:.1%}
        - Accuracy: {metrics['accuracy']:.1%}
        - Consistency: {metrics['consistency']:.1%}
        - Overall Score: {metrics['overall']:.1%}
        - Quality Grade: {metrics['grade']}
        
        Validation Results:
        - Passed: {quality.passed_validations}
        - Warnings: {quality.warnings}
        - Failures: {quality.failures}
        """
        
        return content.strip()
    
    def _format_audit_report(self, audit: AuditTrailReport) -> str:
        """Format audit trail report."""
        summary = audit.get_summary()
        
        content = f"""
        Audit Trail Summary:
        - Duration: {summary['duration_hours']:.1f} hours
        - Total Actions: {summary['total_actions']}
        - Unique Users: {summary['unique_users']}
        - Actions per Hour: {summary['actions_per_hour']:.1f}
        """
        
        if audit.start_time:
            content += f"\n- Start Time: {audit.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        if audit.end_time:
            content += f"\n- End Time: {audit.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return content.strip()
    
    def export_to_pdf(self, report: ReportTemplate, output_path: Path) -> Path:
        """Export report to PDF format."""
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # For now, export as formatted text file (would use reportlab in production)
        # This is a simplified implementation for testing
        report_data = self._prepare_report_data(report)
        
        # Create PDF-like text output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"{'=' * 60}\n")
            f.write(f"{report.title.center(60)}\n")
            f.write(f"{'=' * 60}\n\n")
            
            # Write metadata
            if report.metadata:
                f.write("Report Metadata:\n")
                for key, value in report.metadata.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
            
            # Write sections
            for section_data in report_data['sections']:
                f.write(f"\n{section_data['title']}\n")
                f.write(f"{'-' * len(section_data['title'])}\n")
                f.write(f"{section_data['content']}\n")
                
                # Write subsections
                for subsection in section_data.get('subsections', []):
                    f.write(f"\n  {subsection['title']}\n")
                    f.write(f"  {subsection['content']}\n")
            
            # Note about tables and charts
            if report.data_tables:
                f.write("\n\nData Tables:\n")
                for table_name in report.data_tables:
                    f.write(f"  - {table_name}\n")
            
            if report.charts:
                f.write("\n\nCharts:\n")
                for chart_name in report.charts:
                    f.write(f"  - {chart_name}\n")
        
        return output_path
    
    def export_to_excel(self, report: ReportTemplate, output_path: Path) -> Path:
        """Export report to Excel format."""
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare report data
        report_data = self._prepare_report_data(report)
        
        # Create Excel file using pandas
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Create summary sheet
            summary_data = {
                'Section': [],
                'Content': []
            }
            
            for section in report_data['sections']:
                summary_data['Section'].append(section['title'])
                summary_data['Content'].append(section['content'])
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add data tables as separate sheets
            if report.data_tables:
                for table_name, df in report.data_tables.items():
                    # Ensure sheet name is valid (max 31 chars, no special chars)
                    sheet_name = table_name[:31].replace('/', '_').replace('\\', '_')
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add metadata sheet
            metadata_data = {
                'Key': list(report.metadata.keys()),
                'Value': [str(v) for v in report.metadata.values()]
            }
            df_metadata = pd.DataFrame(metadata_data)
            df_metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        return output_path
    
    def _prepare_report_data(self, report: ReportTemplate) -> Dict[str, Any]:
        """Prepare report data for export."""
        # Convert report to exportable format
        data = {
            'title': report.title,
            'metadata': report.metadata,
            'sections': []
        }
        
        # Add sections
        for section in report.sections:
            section_data = {
                'title': section.title,
                'content': section.content,
                'subsections': [
                    {'title': s.title, 'content': s.content}
                    for s in section.subsections
                ]
            }
            data['sections'].append(section_data)
        
        # Add data tables
        if report.data_tables:
            data['tables'] = {}
            for name, df in report.data_tables.items():
                # Convert DataFrame to dict for export
                data['tables'][name] = df.to_dict('records')
        
        # Add charts configuration
        if report.charts:
            data['charts'] = report.charts
        
        return data
    
    def generate_batch_reports(
        self,
        datasets: List[Dict[str, Any]],
        output_dir: Path,
        format: str = 'pdf'
    ) -> List[Path]:
        """Generate reports for multiple datasets."""
        generated_reports = []
        
        for dataset in datasets:
            # Create report for each dataset
            summary = dataset.get('summary', VerificationSummary(0, 0, 0, 0))
            quality = dataset.get('quality', DataQualityReport())
            audit = dataset.get('audit', AuditTrailReport())
            title = dataset.get('title', f"Report - {dataset.get('name', 'Unknown')}")
            
            report = self.create_verification_report(
                summary=summary,
                quality=quality,
                audit=audit,
                title=title
            )
            
            # Generate filename
            safe_name = dataset.get('name', 'report').replace(' ', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_name}_{timestamp}.{format}"
            output_path = output_dir / filename
            
            # Export based on format
            if format.lower() == 'pdf':
                exported = self.export_to_pdf(report, output_path)
            elif format.lower() in ['excel', 'xlsx']:
                exported = self.export_to_excel(report, output_path)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            generated_reports.append(exported)
        
        return generated_reports