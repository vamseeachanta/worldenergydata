"""
Go-by report 14-row structure mapping
Maps standard BSEE report structures to template contexts
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ReportRowType(Enum):
    """Types of rows in go-by reports"""

    HEADER = "header"
    FIELD_INFO = "field_info"
    PRODUCTION_SUMMARY = "production_summary"
    WELL_DETAILS = "well_details"
    ECONOMICS = "economics"
    DRILLING = "drilling"
    COMPLETION = "completion"
    LEASE_INFO = "lease_info"
    ENVIRONMENTAL = "environmental"
    REGULATORY = "regulatory"
    NOTES = "notes"
    TOTALS = "totals"
    FOOTER = "footer"
    SPACER = "spacer"


@dataclass
class ReportRowData:
    """Data for a single row in the report"""

    row_number: int
    row_type: ReportRowType
    label: str
    value: Any = None
    format_type: str = "text"  # text, currency, percentage, number, date
    units: Optional[str] = None
    description: Optional[str] = None
    source_field: Optional[str] = None
    calculation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format_value(self) -> str:
        """Format the value according to its type"""
        if self.value is None:
            return "N/A"

        if self.format_type == "currency":
            return f"${self.value:,.2f}"
        elif self.format_type == "percentage":
            return f"{self.value:.1f}%"
        elif self.format_type == "number":
            return f"{self.value:,.0f}"
        elif self.format_type == "decimal":
            return f"{self.value:,.2f}"
        elif self.format_type == "date":
            if isinstance(self.value, (date, datetime)):
                return self.value.strftime("%Y-%m-%d")
            return str(self.value)
        elif self.format_type == "barrels":
            return f"{self.value:,.0f} bbl"
        elif self.format_type == "gas":
            return f"{self.value:,.0f} Mcf"
        elif self.format_type == "days":
            return f"{self.value:,} days"
        else:
            return str(self.value)


@dataclass
class GoByReportStructure:
    """Standard 14-row go-by report structure"""

    report_title: str
    report_date: date
    entity_id: str
    entity_name: str
    entity_type: str  # "field", "lease", "block"
    rows: List[ReportRowData] = field(default_factory=list)

    def __post_init__(self):
        """Initialize standard 14-row structure if not provided"""
        if not self.rows:
            self.rows = self._create_default_structure()

    def _create_default_structure(self) -> List[ReportRowData]:
        """Create the standard 14-row report structure"""
        return [
            # Row 1: Title/Header
            ReportRowData(
                row_number=1,
                row_type=ReportRowType.HEADER,
                label="Report Title",
                source_field="report_title",
            ),
            # Row 2: Entity Information
            ReportRowData(
                row_number=2,
                row_type=ReportRowType.FIELD_INFO,
                label=f"{self.entity_type.title()} Name",
                source_field="entity_name",
            ),
            # Row 3: Report Date
            ReportRowData(
                row_number=3,
                row_type=ReportRowType.FIELD_INFO,
                label="Report Date",
                format_type="date",
                source_field="report_date",
            ),
            # Row 4: Total Oil Production
            ReportRowData(
                row_number=4,
                row_type=ReportRowType.PRODUCTION_SUMMARY,
                label="Total Oil Production",
                format_type="barrels",
                units="bbl",
                source_field="total_oil_production",
            ),
            # Row 5: Total Gas Production
            ReportRowData(
                row_number=5,
                row_type=ReportRowType.PRODUCTION_SUMMARY,
                label="Total Gas Production",
                format_type="gas",
                units="Mcf",
                source_field="total_gas_production",
            ),
            # Row 6: Active Well Count
            ReportRowData(
                row_number=6,
                row_type=ReportRowType.WELL_DETAILS,
                label="Active Wells",
                format_type="number",
                units="wells",
                source_field="active_well_count",
            ),
            # Row 7: Total Revenue
            ReportRowData(
                row_number=7,
                row_type=ReportRowType.ECONOMICS,
                label="Total Revenue",
                format_type="currency",
                units="USD",
                source_field="total_revenue",
            ),
            # Row 8: Operating Costs
            ReportRowData(
                row_number=8,
                row_type=ReportRowType.ECONOMICS,
                label="Operating Costs",
                format_type="currency",
                units="USD",
                source_field="operating_costs",
            ),
            # Row 9: Net Income
            ReportRowData(
                row_number=9,
                row_type=ReportRowType.ECONOMICS,
                label="Net Income",
                format_type="currency",
                units="USD",
                source_field="net_income",
                calculation="total_revenue - operating_costs - royalties",
            ),
            # Row 10: Operating Margin
            ReportRowData(
                row_number=10,
                row_type=ReportRowType.ECONOMICS,
                label="Operating Margin",
                format_type="percentage",
                units="%",
                source_field="operating_margin",
                calculation="(net_income / total_revenue) * 100",
            ),
            # Row 11: Days on Production
            ReportRowData(
                row_number=11,
                row_type=ReportRowType.PRODUCTION_SUMMARY,
                label="Days on Production",
                format_type="days",
                units="days",
                source_field="days_on_production",
            ),
            # Row 12: Water Depth
            ReportRowData(
                row_number=12,
                row_type=ReportRowType.FIELD_INFO,
                label="Water Depth",
                format_type="number",
                units="ft",
                source_field="water_depth_ft",
            ),
            # Row 13: Discovery Date
            ReportRowData(
                row_number=13,
                row_type=ReportRowType.FIELD_INFO,
                label="Discovery Date",
                format_type="date",
                source_field="discovery_date",
            ),
            # Row 14: Status/Notes
            ReportRowData(
                row_number=14,
                row_type=ReportRowType.NOTES,
                label="Status",
                source_field="status",
            ),
        ]

    def get_row(self, row_number: int) -> Optional[ReportRowData]:
        """Get row by number"""
        for row in self.rows:
            if row.row_number == row_number:
                return row
        return None

    def get_rows_by_type(self, row_type: ReportRowType) -> List[ReportRowData]:
        """Get all rows of a specific type"""
        return [row for row in self.rows if row.row_type == row_type]

    def update_row_value(self, row_number: int, value: Any):
        """Update the value of a specific row"""
        row = self.get_row(row_number)
        if row:
            row.value = value

    def populate_from_context(self, context: Dict[str, Any]):
        """Populate row values from template context"""
        for row in self.rows:
            if row.source_field and row.source_field in context:
                row.value = context[row.source_field]
            elif row.source_field and "." in row.source_field:
                # Handle nested context fields like "production_metrics.oil_bbls"
                value = self._get_nested_value(context, row.source_field)
                if value is not None:
                    row.value = value

    def _get_nested_value(self, context: Dict[str, Any], field_path: str) -> Any:
        """Get nested value from context using dot notation"""
        keys = field_path.split(".")
        value = context

        try:
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        except (KeyError, TypeError):
            return None

    def to_template_context(self) -> Dict[str, Any]:
        """Convert to template context dictionary"""
        context = {
            "report_title": self.report_title,
            "report_date": self.report_date,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "rows": [],
        }

        for row in self.rows:
            row_context = {
                "row_number": row.row_number,
                "row_type": row.row_type.value,
                "label": row.label,
                "value": row.value,
                "formatted_value": row.format_value(),
                "format_type": row.format_type,
                "units": row.units,
                "description": row.description,
                "calculation": row.calculation,
                "metadata": row.metadata,
            }
            context["rows"].append(row_context)

        # Create section groupings
        context["header_rows"] = [
            r for r in context["rows"] if r["row_type"] == "header"
        ]
        context["field_info_rows"] = [
            r for r in context["rows"] if r["row_type"] == "field_info"
        ]
        context["production_rows"] = [
            r for r in context["rows"] if r["row_type"] == "production_summary"
        ]
        context["well_rows"] = [
            r for r in context["rows"] if r["row_type"] == "well_details"
        ]
        context["economic_rows"] = [
            r for r in context["rows"] if r["row_type"] == "economics"
        ]
        context["notes_rows"] = [r for r in context["rows"] if r["row_type"] == "notes"]

        return context

    def validate_structure(self) -> Dict[str, Any]:
        """Validate the report structure"""
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "row_count": len(self.rows),
        }

        # Check row count
        if len(self.rows) != 14:
            results["warnings"].append(f"Expected 14 rows, found {len(self.rows)}")

        # Check for duplicate row numbers
        row_numbers = [row.row_number for row in self.rows]
        if len(row_numbers) != len(set(row_numbers)):
            results["errors"].append("Duplicate row numbers found")
            results["valid"] = False

        # Check for missing required row types
        row_types = set(row.row_type for row in self.rows)
        required_types = {
            ReportRowType.HEADER,
            ReportRowType.PRODUCTION_SUMMARY,
            ReportRowType.ECONOMICS,
        }
        missing_types = required_types - row_types
        if missing_types:
            results["warnings"].append(
                f"Missing recommended row types: {[t.value for t in missing_types]}"
            )

        # Check for rows without values
        empty_rows = [
            row.row_number
            for row in self.rows
            if row.value is None and row.row_type != ReportRowType.SPACER
        ]
        if empty_rows:
            results["warnings"].append(f"Rows without values: {empty_rows}")

        return results


class GoByReportMapper:
    """Maps various data sources to go-by report structure"""

    @staticmethod
    def from_production_metrics(
        production_data: Any, entity_info: Dict[str, Any]
    ) -> GoByReportStructure:
        """Create go-by report from production metrics"""
        report = GoByReportStructure(
            report_title=f"{entity_info.get('entity_type', 'Field').title()} Production Report",
            report_date=date.today(),
            entity_id=entity_info.get("entity_id", ""),
            entity_name=entity_info.get("entity_name", ""),
            entity_type=entity_info.get("entity_type", "field"),
        )

        # Map production data to report context
        context = {
            "total_oil_production": getattr(production_data, "oil_production_bbls", 0),
            "total_gas_production": getattr(production_data, "gas_production_mcf", 0),
            "active_well_count": getattr(production_data, "active_well_count", 1),
            "total_revenue": getattr(production_data, "total_revenue", lambda: 0)(),
            "operating_costs": getattr(production_data, "operating_cost_usd", 0),
            "days_on_production": getattr(production_data, "days_in_period", 365),
            "water_depth_ft": entity_info.get("water_depth_ft"),
            "discovery_date": entity_info.get("discovery_date"),
            "status": "Active",
        }

        # Calculate derived values
        if context["total_revenue"] and context["operating_costs"]:
            context["net_income"] = (
                context["total_revenue"] - context["operating_costs"]
            )
            if context["total_revenue"] > 0:
                context["operating_margin"] = (
                    context["net_income"] / context["total_revenue"]
                ) * 100

        report.populate_from_context(context)
        return report

    @staticmethod
    def from_economic_metrics(
        economic_data: Any, entity_info: Dict[str, Any]
    ) -> GoByReportStructure:
        """Create go-by report from economic metrics"""
        report = GoByReportStructure(
            report_title=f"{entity_info.get('entity_type', 'Field').title()} Economic Report",
            report_date=date.today(),
            entity_id=entity_info.get("entity_id", ""),
            entity_name=entity_info.get("entity_name", ""),
            entity_type=entity_info.get("entity_type", "field"),
        )

        # Map economic data to report context
        context = {
            "total_revenue": getattr(economic_data, "revenue", 0),
            "operating_costs": getattr(economic_data, "operating_costs", 0),
            "net_income": getattr(economic_data, "net_income", 0),
            "operating_margin": getattr(economic_data, "profit_margin", 0) * 100,
            "total_oil_production": getattr(economic_data, "production_bbls", 0),
            "water_depth_ft": entity_info.get("water_depth_ft"),
            "discovery_date": entity_info.get("discovery_date"),
            "status": "Active",
        }

        report.populate_from_context(context)
        return report

    @staticmethod
    def create_custom_structure(
        row_definitions: List[Dict[str, Any]], entity_info: Dict[str, Any]
    ) -> GoByReportStructure:
        """Create custom report structure from row definitions"""
        # Create report with empty rows list initially
        report = GoByReportStructure.__new__(GoByReportStructure)

        # Manually set attributes without calling __post_init__
        report.report_title = entity_info.get("report_title", "Custom Report")
        report.report_date = date.today()
        report.entity_id = entity_info.get("entity_id", "")
        report.entity_name = entity_info.get("entity_name", "")
        report.entity_type = entity_info.get("entity_type", "field")
        report.rows = []

        # Create rows from definitions
        for i, row_def in enumerate(row_definitions):
            row = ReportRowData(
                row_number=i + 1,
                row_type=ReportRowType(row_def.get("row_type", "field_info")),
                label=row_def["label"],
                value=row_def.get("value"),
                format_type=row_def.get("format_type", "text"),
                units=row_def.get("units"),
                description=row_def.get("description"),
                source_field=row_def.get("source_field"),
                calculation=row_def.get("calculation"),
            )
            report.rows.append(row)

        return report
