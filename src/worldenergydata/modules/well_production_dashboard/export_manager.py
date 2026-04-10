"""
Well Production Dashboard Export Manager

This module provides export functionality for the well production dashboard,
integrating with the comprehensive report framework to generate PDF, Excel,
and JSON exports with verification metadata.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

# Import comprehensive report exporters
try:
    # Import verification components
    from worldenergydata.modules.analysis.verification.models import VerificationResult
    from worldenergydata.bsee.reports.comprehensive.exporters.base import (
        ExportConfig,
        ExportFormat,
    )
    from worldenergydata.bsee.reports.comprehensive.exporters.base import (
        ExportResult as BaseExportResult,
    )
    from worldenergydata.bsee.reports.comprehensive.exporters.base import (
        ReportExporter,
    )
    from worldenergydata.bsee.reports.comprehensive.exporters.batch import (
        BatchExporter,
    )
    from worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter import (
        ExcelExporter,
    )
    from worldenergydata.bsee.reports.comprehensive.exporters.pdf_exporter import (
        PDFExporter,
    )

    # Import report builder for BSEE standard formatting
    from worldenergydata.bsee.reports.comprehensive.report_builder import (
        GoByReportBuilder,
    )
except (ImportError, ModuleNotFoundError):
    # Create mock classes if imports fail
    class ReportExporter:
        pass

    class ExportFormat:
        PDF = "pdf"
        EXCEL = "excel"
        JSON = "json"

    class ExportConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class BaseExportResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ExcelExporter:
        def __init__(self, config=None):
            self.config = config

        def export(self, data, output_path):
            return BaseExportResult(success=True, path=output_path)

    class PDFExporter:
        def __init__(self, config=None):
            self.config = config

        def export(self, data, output_path):
            return BaseExportResult(success=True, path=output_path)

    class BatchExporter:
        def __init__(self, config=None):
            self.config = config

        def export_batch(self, data, formats):
            return [
                BaseExportResult(success=True, path=f"output.{fmt}") for fmt in formats
            ]

    class GoByReportBuilder:
        def __init__(self):
            pass

        def format_bsee_standard(self, data):
            return data

    class VerificationResult:
        def __init__(self, **kwargs):
            self.wells_verified = kwargs.get("wells_verified", 0)
            self.wells_failed = kwargs.get("wells_failed", 0)
            self.quality_score = kwargs.get("quality_score", 0.0)
            self.verification_date = kwargs.get("verification_date", datetime.now())
            self.metadata = kwargs.get("metadata", {})

        def to_dict(self):
            return {
                "wells_verified": self.wells_verified,
                "wells_failed": self.wells_failed,
                "quality_score": self.quality_score,
                "verification_date": self.verification_date,
                "metadata": self.metadata,
            }


logger = logging.getLogger(__name__)


@dataclass
class VerificationMetadata:
    """Verification metadata for exports"""

    quality_score: float
    verification_date: datetime = field(default_factory=datetime.now)
    audit_trail_id: Optional[str] = None
    anomalies_detected: int = 0
    data_completeness: float = 1.0
    verification_status: str = "Verified"
    last_audit_date: Optional[datetime] = None
    data_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "quality_score": self.quality_score,
            "verification_date": (
                self.verification_date.isoformat() if self.verification_date else None
            ),
            "audit_trail_id": self.audit_trail_id,
            "anomalies_detected": self.anomalies_detected,
            "data_completeness": self.data_completeness,
            "verification_status": self.verification_status,
            "last_audit_date": (
                self.last_audit_date.isoformat() if self.last_audit_date else None
            ),
            "data_sources": self.data_sources,
        }


@dataclass
class ExportConfiguration:
    """Configuration for dashboard exports"""

    formats: List[str] = field(default_factory=lambda: ["excel"])
    include_verification: bool = True
    include_charts: bool = True
    include_raw_data: bool = True
    include_field_aggregation: bool = False
    chart_format: str = "base64"  # 'base64' or 'embedded'
    date_range: Optional[tuple] = None
    wells_filter: Optional[List[str]] = None
    quality_threshold: Optional[float] = None

    def __post_init__(self):
        """Validate configuration"""
        valid_formats = ["excel", "pdf", "json", "html", "powerpoint"]
        if not self.formats:
            raise ValueError("At least one export format must be specified")

        for fmt in self.formats:
            if fmt not in valid_formats:
                raise ValueError(
                    f"Invalid format: {fmt}. Valid formats: {valid_formats}"
                )


@dataclass
class ExportResult:
    """Result of an export operation"""

    success: bool
    format: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    export_date: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class WellDashboardExportManager:
    """Manager for well production dashboard exports"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize export manager

        Args:
            config_path: Optional path to configuration file
        """
        self.config = self._load_config(config_path)

        # Initialize exporters
        self.excel_exporter = ExcelExporter()
        self.pdf_exporter = PDFExporter()
        self.batch_exporter = BatchExporter()

        # Initialize report builder for BSEE formatting
        self.report_builder = GoByReportBuilder()

        logger.info("WellDashboardExportManager initialized")

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            "export_dir": "exports",
            "max_file_size": 100 * 1024 * 1024,  # 100MB
            "quality_thresholds": {
                "excellent": 0.9,
                "good": 0.8,
                "fair": 0.7,
                "poor": 0.0,
            },
            "bsee_standard": {
                "enable_14_row_format": True,
                "include_cumulative": True,
                "include_forecasts": False,
            },
        }

        if config_path and Path(config_path).exists():
            # Load from file (implementation would go here)
            pass

        return default_config

    def export_batch(
        self,
        dashboard_data: Dict[str, Any],
        base_filename: str,
        config: ExportConfiguration,
    ) -> List[ExportResult]:
        """
        Export dashboard data in multiple formats

        Args:
            dashboard_data: Dashboard data to export
            base_filename: Base filename for exports
            config: Export configuration

        Returns:
            List of export results
        """
        results = []

        # Prepare data once for all formats
        prepared_data = self.prepare_export_data(dashboard_data, config)

        for format_type in config.formats:
            try:
                if format_type == "excel":
                    result = self.export_to_excel(
                        prepared_data, f"{base_filename}.xlsx", config
                    )
                elif format_type == "pdf":
                    result = self.export_to_pdf(
                        prepared_data, f"{base_filename}.pdf", config
                    )
                elif format_type == "json":
                    result = self.export_to_json(
                        prepared_data, f"{base_filename}.json", config
                    )
                else:
                    result = ExportResult(
                        success=False,
                        format=format_type,
                        error_message=f"Unsupported format: {format_type}",
                    )

                results.append(result)

            except Exception as e:
                logger.error(f"Error exporting to {format_type}: {str(e)}")
                results.append(
                    ExportResult(
                        success=False, format=format_type, error_message=str(e)
                    )
                )

        return results

    def export_to_excel(
        self,
        dashboard_data: Dict[str, Any],
        output_path: str,
        config: ExportConfiguration,
    ) -> ExportResult:
        """
        Export dashboard data to Excel format

        Args:
            dashboard_data: Dashboard data to export
            output_path: Output file path
            config: Export configuration

        Returns:
            Export result
        """
        try:
            # Prepare Excel-specific data structure
            excel_data = self._prepare_excel_data(dashboard_data, config)

            # Create export configuration for comprehensive exporter
            export_config = ExportConfig(
                format=ExportFormat.EXCEL,
                include_charts=config.include_charts,
                include_metadata=config.include_verification,
            )

            # Use comprehensive Excel exporter
            base_result = self.excel_exporter.export(
                data=excel_data, output_path=output_path, config=export_config
            )

            # Convert to our result format
            return ExportResult(
                success=base_result.success,
                format="excel",
                file_path=base_result.file_path,
                file_size=base_result.file_size,
                error_message=base_result.error_message,
                metadata={"sheets": list(excel_data.keys())},
            )

        except Exception as e:
            logger.error(f"Excel export failed: {str(e)}")
            return ExportResult(success=False, format="excel", error_message=str(e))

    def export_to_pdf(
        self,
        dashboard_data: Dict[str, Any],
        output_path: str,
        config: ExportConfiguration,
    ) -> ExportResult:
        """
        Export dashboard data to PDF format

        Args:
            dashboard_data: Dashboard data to export
            output_path: Output file path
            config: Export configuration

        Returns:
            Export result
        """
        try:
            # Prepare PDF-specific data structure
            pdf_data = self._prepare_pdf_data(dashboard_data, config)

            # Create export configuration
            export_config = ExportConfig(
                format=ExportFormat.PDF,
                include_charts=config.include_charts,
                include_metadata=config.include_verification,
            )

            # Use comprehensive PDF exporter
            base_result = self.pdf_exporter.export(
                data=pdf_data, output_path=output_path, config=export_config
            )

            return ExportResult(
                success=base_result.success,
                format="pdf",
                file_path=base_result.file_path,
                file_size=base_result.file_size,
                error_message=base_result.error_message,
                metadata={"pages": pdf_data.get("total_pages", 0)},
            )

        except Exception as e:
            logger.error(f"PDF export failed: {str(e)}")
            return ExportResult(success=False, format="pdf", error_message=str(e))

    def export_to_json(
        self,
        dashboard_data: Dict[str, Any],
        output_path: str,
        config: ExportConfiguration,
    ) -> ExportResult:
        """
        Export dashboard data to JSON format

        Args:
            dashboard_data: Dashboard data to export
            output_path: Output file path
            config: Export configuration

        Returns:
            Export result
        """
        try:
            # Prepare JSON-serializable data
            json_data = self._prepare_json_data(dashboard_data, config)

            # Write to file
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(json_data, f, indent=2, default=str)

            file_size = output_path.stat().st_size

            return ExportResult(
                success=True,
                format="json",
                file_path=str(output_path),
                file_size=file_size,
                metadata={"records": len(json_data.get("well_data", []))},
            )

        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            return ExportResult(success=False, format="json", error_message=str(e))

    def prepare_export_data(
        self, dashboard_data: Dict[str, Any], config: ExportConfiguration
    ) -> Dict[str, Any]:
        """
        Prepare dashboard data for export

        Args:
            dashboard_data: Raw dashboard data
            config: Export configuration

        Returns:
            Prepared data for export
        """
        prepared_data = {
            "export_date": datetime.now().isoformat(),
            "configuration": asdict(config),
        }

        # Add summary section
        prepared_data["summary"] = self._create_summary(dashboard_data)

        # Add production data
        if "well_data" in dashboard_data:
            prepared_data["production_data"] = self._format_production_data(
                dashboard_data["well_data"]
            )

        # Add economic data
        if "economic_metrics" in dashboard_data:
            prepared_data["economic_data"] = dashboard_data["economic_metrics"]

        # Add verification data if requested
        if config.include_verification and "verification_metadata" in dashboard_data:
            prepared_data["verification_data"] = self._format_verification_data(
                dashboard_data["verification_metadata"]
            )

        # Add charts if requested
        if config.include_charts and "charts" in dashboard_data:
            prepared_data["charts"] = self._prepare_charts(
                dashboard_data["charts"], config.chart_format
            )

        # Add raw data if requested
        if config.include_raw_data:
            prepared_data["raw_data"] = dashboard_data.get("well_data", pd.DataFrame())

        # Add field aggregation if requested
        if config.include_field_aggregation and "field_data" in dashboard_data:
            prepared_data["field_aggregation"] = dashboard_data["field_data"]

        return prepared_data

    def add_verification_report(
        self, export_data: Dict[str, Any], verification_metadata: VerificationMetadata
    ) -> None:
        """
        Add verification report section to export data

        Args:
            export_data: Export data dictionary
            verification_metadata: Verification metadata
        """
        verification_report = {
            "quality_score": verification_metadata.quality_score,
            "verification_date": verification_metadata.verification_date.isoformat(),
            "audit_trail_id": verification_metadata.audit_trail_id,
            "anomalies_detected": verification_metadata.anomalies_detected,
            "data_completeness": verification_metadata.data_completeness,
            "verification_status": verification_metadata.verification_status,
            "quality_assessment": self.get_quality_assessment(verification_metadata),
            "data_sources": verification_metadata.data_sources,
        }

        # Add quality indicators
        verification_report["quality_indicators"] = {
            "data_quality": (
                "Pass" if verification_metadata.quality_score >= 0.7 else "Fail"
            ),
            "completeness": (
                "Complete"
                if verification_metadata.data_completeness >= 0.95
                else "Partial"
            ),
            "anomaly_status": (
                "Clean"
                if verification_metadata.anomalies_detected == 0
                else f"{verification_metadata.anomalies_detected} detected"
            ),
        }

        export_data["verification_report"] = verification_report

    def format_bsee_standard(self, well_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Format well data according to BSEE 14-row standard

        Args:
            well_data: Well production data

        Returns:
            BSEE formatted data
        """
        bsee_data = {}

        # Standard BSEE rows
        bsee_rows = [
            "Field/Block/Lease",
            "Well Name",
            "Oil Production (BBL)",
            "Gas Production (MCF)",
            "Water Production (BBL)",
            "Operating Days",
            "Oil Sales (BBL)",
            "Gas Sales (MCF)",
            "Revenue ($)",
            "Operating Cost ($)",
            "Net Income ($)",
            "Cumulative Oil (BBL)",
            "Cumulative Gas (MCF)",
            "Quality Score",
        ]

        # Map dashboard data to BSEE format
        for row in bsee_rows:
            if row == "Well Name" and "well_name" in well_data.columns:
                bsee_data[row] = well_data["well_name"].tolist()
            elif (
                row == "Oil Production (BBL)" and "oil_production" in well_data.columns
            ):
                bsee_data[row] = well_data["oil_production"].tolist()
            elif (
                row == "Gas Production (MCF)" and "gas_production" in well_data.columns
            ):
                bsee_data[row] = well_data["gas_production"].tolist()
            elif (
                row == "Water Production (BBL)"
                and "water_production" in well_data.columns
            ):
                bsee_data[row] = well_data["water_production"].tolist()
            elif row == "Operating Days" and "operating_days" in well_data.columns:
                bsee_data[row] = well_data["operating_days"].tolist()
            elif row == "Quality Score" and "quality_score" in well_data.columns:
                bsee_data[row] = well_data["quality_score"].tolist()
            else:
                # Fill with default values or calculate
                bsee_data[row] = [0] * len(well_data)

        return bsee_data

    def get_quality_assessment(self, metadata: VerificationMetadata) -> str:
        """
        Get quality assessment based on verification metadata

        Args:
            metadata: Verification metadata

        Returns:
            Quality assessment string
        """
        score = metadata.quality_score
        thresholds = self.config["quality_thresholds"]

        if score >= thresholds["excellent"]:
            return "Excellent"
        elif score >= thresholds["good"]:
            return "Good"
        elif score >= thresholds["fair"]:
            return "Fair"
        else:
            return "Poor"

    def _prepare_excel_data(
        self, dashboard_data: Dict[str, Any], config: ExportConfiguration
    ) -> Dict[str, pd.DataFrame]:
        """Prepare data for Excel export"""
        excel_sheets = {}

        # Summary sheet
        if "summary" in dashboard_data:
            excel_sheets["Summary"] = pd.DataFrame([dashboard_data["summary"]])

        # Production data sheet
        if "production_data" in dashboard_data:
            excel_sheets["Production Data"] = pd.DataFrame(
                dashboard_data["production_data"]
            )

        # Economic metrics sheet
        if "economic_data" in dashboard_data:
            excel_sheets["Economic Metrics"] = pd.DataFrame(
                [dashboard_data["economic_data"]]
            )

        # Verification sheet
        if config.include_verification and "verification_data" in dashboard_data:
            excel_sheets["Verification"] = pd.DataFrame(
                [dashboard_data["verification_data"]]
            )

        # Raw data sheet
        if config.include_raw_data and "raw_data" in dashboard_data:
            excel_sheets["Raw Data"] = dashboard_data["raw_data"]

        return excel_sheets

    def _prepare_pdf_data(
        self, dashboard_data: Dict[str, Any], config: ExportConfiguration
    ) -> Dict[str, Any]:
        """Prepare data for PDF export"""
        pdf_data = {"title": "Well Production Dashboard Report", "sections": []}

        # Executive summary section
        if "summary" in dashboard_data:
            pdf_data["sections"].append(
                {"title": "Executive Summary", "content": dashboard_data["summary"]}
            )

        # Production analysis section
        if "production_data" in dashboard_data:
            pdf_data["sections"].append(
                {
                    "title": "Production Analysis",
                    "content": dashboard_data["production_data"],
                }
            )

        # Economic analysis section
        if "economic_data" in dashboard_data:
            pdf_data["sections"].append(
                {
                    "title": "Economic Analysis",
                    "content": dashboard_data["economic_data"],
                }
            )

        # Verification section
        if config.include_verification and "verification_data" in dashboard_data:
            pdf_data["sections"].append(
                {
                    "title": "Data Verification Report",
                    "content": dashboard_data["verification_data"],
                }
            )

        # Charts section
        if config.include_charts and "charts" in dashboard_data:
            pdf_data["sections"].append(
                {
                    "title": "Charts and Visualizations",
                    "content": dashboard_data["charts"],
                }
            )

        return pdf_data

    def _prepare_json_data(
        self, dashboard_data: Dict[str, Any], config: ExportConfiguration
    ) -> Dict[str, Any]:
        """Prepare data for JSON export"""
        json_data = {}

        # Convert DataFrames to dictionaries
        for key, value in dashboard_data.items():
            if isinstance(value, pd.DataFrame):
                json_data[key] = value.to_dict("records")
            elif isinstance(value, VerificationMetadata):
                json_data[key] = value.to_dict()
            elif hasattr(value, "to_dict"):
                json_data[key] = value.to_dict()
            else:
                json_data[key] = value

        return json_data

    def _create_summary(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary section for export"""
        summary = {
            "report_date": datetime.now().isoformat(),
            "total_wells": 0,
            "total_production_oil": 0,
            "total_production_gas": 0,
            "average_quality_score": 0,
        }

        if "well_data" in dashboard_data and isinstance(
            dashboard_data["well_data"], pd.DataFrame
        ):
            df = dashboard_data["well_data"]
            summary["total_wells"] = len(df)

            if "oil_production" in df.columns:
                summary["total_production_oil"] = df["oil_production"].sum()

            if "gas_production" in df.columns:
                summary["total_production_gas"] = df["gas_production"].sum()

            if "quality_score" in df.columns:
                summary["average_quality_score"] = df["quality_score"].mean()

        return summary

    def _format_production_data(self, well_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Format production data for export"""
        if self.config["bsee_standard"]["enable_14_row_format"]:
            return self.format_bsee_standard(well_data)
        else:
            return well_data.to_dict("records")

    def _format_verification_data(
        self, verification_metadata: VerificationMetadata
    ) -> Dict[str, Any]:
        """Format verification data for export"""
        return verification_metadata.to_dict()

    def _prepare_charts(
        self, charts: Dict[str, Any], chart_format: str
    ) -> Dict[str, Any]:
        """Prepare charts for export"""
        prepared_charts = {}

        for chart_name, chart_obj in charts.items():
            if chart_format == "base64" and hasattr(chart_obj, "to_image"):
                # Convert to base64 image
                prepared_charts[chart_name] = {
                    "type": "image",
                    "format": "base64",
                    "data": chart_obj.to_image(),  # This would return base64 string
                }
            elif hasattr(chart_obj, "to_json"):
                # Convert to JSON representation
                prepared_charts[chart_name] = {
                    "type": "json",
                    "data": chart_obj.to_json(),
                }
            else:
                prepared_charts[chart_name] = str(chart_obj)

        return prepared_charts
