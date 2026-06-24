"""
Main well detail view component.

Orchestrates all view components to render complete well detail pages
with production charts, economic metrics, and verification status.
"""

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional

import pandas as pd

from .views_decline import DeclineCurveAnalyzer
from .views_financial import EconomicMetricsCalculator
from .views_production import ProductionChartBuilder
from .views_utils import WellDetailConfig, logger
from .views_verification import AuditTrailLink, VerificationStatusBadge


class WellDetailView:
    """Main well detail view component."""

    def __init__(self, config: Optional[WellDetailConfig] = None):
        """Initialize well detail view."""
        self.config = config or WellDetailConfig()
        self.chart_builder = ProductionChartBuilder()
        self.metrics_calculator = EconomicMetricsCalculator()
        self.decline_analyzer = DeclineCurveAnalyzer()
        self.status_badge = VerificationStatusBadge()
        self.audit_link = AuditTrailLink()

    def render(self, well_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render complete well detail page."""
        page = {
            "well_id": well_data.get("well_id"),
            "well_name": well_data.get("well_name"),
            "field": well_data.get("field"),
            "header": self._create_header(well_data),
            "charts": {},
            "metrics": {},
            "verification_status": {},
        }

        # Create production section
        if "production" in well_data:
            production_section = self.create_production_section(
                well_data["production"], well_data.get("verification", pd.DataFrame())
            )
            page["charts"].update(production_section)

        # Create economic section
        if "economics" in well_data:
            economic_section = self.create_economic_section(
                well_data.get("economics"), well_data.get("production")
            )
            page["metrics"].update(economic_section)

        # Create verification section
        if "verification" in well_data:
            verification_section = self.create_verification_section(
                well_data["verification"]
            )
            page["verification_status"] = verification_section

        return page

    def _create_header(self, well_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create page header with key information."""
        return {
            "title": f"Well Detail: {well_data.get('well_name', 'Unknown')}",
            "subtitle": f"Field: {well_data.get('field', 'Unknown')}",
            "well_id": well_data.get("well_id"),
            "last_updated": datetime.now().isoformat(),
        }

    def create_production_section(
        self, production_data: pd.DataFrame, verification_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Create production charts section."""
        section = {}
        well_name = "Well"

        # Time series chart
        if "production_time_series" in self.config.chart_types:
            chart = self.chart_builder.create_time_series_chart(
                production_data, well_name
            )

            # Add quality indicators if available
            if not verification_data.empty and self.config.show_quality_indicators:
                if "quality_score" in verification_data.columns:
                    chart = self.chart_builder.add_quality_indicators(
                        chart,
                        verification_data["quality_score"],
                        verification_data.get("status", pd.Series()),
                    )

            section["time_series_chart"] = chart

        # Decline curve
        if "decline_curve" in self.config.chart_types:
            oil_col = "oil" if "oil" in production_data.columns else "oil_production"
            if oil_col in production_data.columns:
                dates = (
                    production_data["date"]
                    if "date" in production_data.columns
                    else production_data.index
                )
                chart = self.decline_analyzer.create_decline_curve_chart(
                    production_data[oil_col].values, dates.values, well_name
                )
                section["decline_curve"] = chart

        # Quality indicators summary
        if not verification_data.empty and self.config.show_quality_indicators:
            section["quality_indicators"] = self._create_quality_summary(
                verification_data
            )

        return section

    def create_economic_section(
        self,
        economic_data: Optional[pd.DataFrame],
        production_data: Optional[pd.DataFrame],
    ) -> Dict[str, Any]:
        """Create economic metrics section."""
        section = {}

        if economic_data is None or economic_data.empty:
            return section

        # Calculate key metrics
        if "revenue" in economic_data.columns and "opex" in economic_data.columns:
            cash_flows = economic_data["revenue"] - economic_data["opex"]
            if "capex" in economic_data.columns:
                cash_flows -= economic_data["capex"]

            # NPV
            npv = self.metrics_calculator.calculate_npv(cash_flows.values)
            section["npv"] = {"value": npv, "formatted": f"${npv:,.0f}"}

            # IRR
            irr = self.metrics_calculator.calculate_irr(cash_flows.values)
            section["irr"] = {"value": irr, "formatted": f"{irr*100:.1f}%"}

            # Payback period
            payback = self.metrics_calculator.calculate_payback_period(
                cash_flows.values
            )
            section["payback_period"] = {
                "value": payback,
                "formatted": f"{payback:.1f} months",
            }

        # Waterfall chart
        if "economic_waterfall" in self.config.chart_types:
            total_revenue = (
                economic_data["revenue"].sum()
                if "revenue" in economic_data.columns
                else 0
            )
            total_opex = (
                economic_data["opex"].sum() if "opex" in economic_data.columns else 0
            )
            total_capex = (
                economic_data["capex"].sum() if "capex" in economic_data.columns else 0
            )
            taxes = total_revenue * 0.25  # Assumed tax rate

            chart = self.metrics_calculator.create_waterfall_chart(
                total_revenue, total_opex, total_capex, taxes, "Well"
            )
            section["waterfall_chart"] = chart

        return section

    def create_verification_section(
        self, verification_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Create verification status section."""
        section = {}

        if verification_data.empty:
            return section

        # Current status
        latest_verification = (
            verification_data.iloc[-1] if not verification_data.empty else {}
        )
        if isinstance(latest_verification, pd.Series):
            latest_verification = latest_verification.to_dict()

        status = latest_verification.get("status", "pending")
        quality_score = latest_verification.get("quality_score", 0.0)
        timestamp = latest_verification.get("date", datetime.now())

        section["current_status"] = self.status_badge.create(
            status, quality_score, timestamp
        )

        # Quality timeline
        if "quality_score" in verification_data.columns:
            section["quality_timeline"] = {
                "dates": (
                    verification_data.index.tolist()
                    if isinstance(verification_data.index, pd.DatetimeIndex)
                    else verification_data["date"].tolist()
                ),
                "scores": verification_data["quality_score"].tolist(),
                "average": verification_data["quality_score"].mean(),
            }

        # Audit links
        if "verification_id" in verification_data.columns:
            verification_ids = (
                verification_data["verification_id"].dropna().unique().tolist()
            )
            section["audit_links"] = self.audit_link.create_batch(
                "WELL-001", verification_ids[:5]  # Limit to recent 5
            )

        # Summary statistics
        if "status" in verification_data.columns:
            status_counts = verification_data["status"].value_counts()
            section["summary"] = self.audit_link.format_summary(
                total_verifications=len(verification_data),
                passed=status_counts.get("verified", 0),
                failed=status_counts.get("failed", 0),
                pending=status_counts.get("pending", 0),
            )

        return section

    def _create_quality_summary(
        self, verification_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Create quality indicators summary."""
        summary = {}

        if "quality_score" in verification_data.columns:
            summary["average_quality"] = verification_data["quality_score"].mean()
            summary["min_quality"] = verification_data["quality_score"].min()
            summary["max_quality"] = verification_data["quality_score"].max()
            summary["below_threshold"] = (
                verification_data["quality_score"] < self.config.quality_threshold
            ).sum()

        if "status" in verification_data.columns:
            status_counts = verification_data["status"].value_counts().to_dict()
            summary["status_distribution"] = status_counts

        return summary

    def export_to_pdf(self, well_data: Dict[str, Any]) -> bytes:
        """Export well detail view to PDF."""
        # Simplified PDF export
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)

            # Add basic content
            p.drawString(
                100, 750, f"Well Detail Report: {well_data.get('well_name', 'Unknown')}"
            )
            p.drawString(100, 730, f"Field: {well_data.get('field', 'Unknown')}")
            p.drawString(
                100, 710, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            p.showPage()
            p.save()

            buffer.seek(0)
            return buffer.getvalue()
        except ImportError:
            logger.warning("ReportLab not available for PDF export")
            return b""

    def export_to_excel(self, well_data: Dict[str, Any]) -> bytes:
        """Export well detail view to Excel."""
        try:
            buffer = BytesIO()

            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                # Export production data
                if "production" in well_data:
                    well_data["production"].to_excel(
                        writer, sheet_name="Production", index=False
                    )

                # Export economic data
                if "economics" in well_data:
                    well_data["economics"].to_excel(
                        writer, sheet_name="Economics", index=False
                    )

                # Export verification data
                if "verification" in well_data:
                    well_data["verification"].to_excel(
                        writer, sheet_name="Verification", index=False
                    )

            buffer.seek(0)
            return buffer.getvalue()
        except ImportError:
            logger.warning("OpenPyXL not available for Excel export")
            return b""

    def update_real_time(
        self, current_page: Dict[str, Any], new_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Update page with real-time data."""
        # Update production charts with new data
        if "charts" in current_page and "time_series_chart" in current_page["charts"]:
            # Append new data and recreate chart
            # This is a simplified implementation
            current_page["last_updated"] = datetime.now().isoformat()
            current_page["real_time_update"] = True

        return current_page

    def get_verification_details(
        self, well_id: str, verification_id: str
    ) -> Dict[str, Any]:
        """Get detailed verification information."""
        # Placeholder for verification details retrieval
        return {
            "well_id": well_id,
            "verification_id": verification_id,
            "audit_trail": [
                {"timestamp": datetime.now().isoformat(), "action": "Data loaded"},
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "Quality checks performed",
                },
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "Verification completed",
                },
            ],
            "quality_checks": {
                "completeness": 0.95,
                "accuracy": 0.92,
                "consistency": 0.88,
            },
            "validation_rules": [
                {"rule": "Production > 0", "passed": True},
                {"rule": "Date sequence valid", "passed": True},
                {"rule": "No duplicate entries", "passed": True},
            ],
        }


# Export all public names
__all__ = ["WellDetailView"]
