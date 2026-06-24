# ABOUTME: HTML report generation module for incident cause analysis
# ABOUTME: Creates standalone interactive reports with embedded Plotly visualizations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import plotly.express as px
import plotly.graph_objects as go

from ..constants import CauseCategory, SeverityLevel


@dataclass
class ReportFilters:
    """Filters for incident data in reports.

    Attributes:
        start_date: Filter incidents after this date
        end_date: Filter incidents before this date
        cause_categories: Filter by specific cause categories
        min_severity: Filter by minimum severity level
    """

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    cause_categories: Optional[List[CauseCategory]] = None
    min_severity: Optional[SeverityLevel] = None

    def __post_init__(self):
        """Validate filter parameters."""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before end_date")

    def apply(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply filters to incident data.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Filtered list of incidents
        """
        filtered = incidents

        # Date range filter
        if self.start_date:
            filtered = [inc for inc in filtered if inc["date"] >= self.start_date]
        if self.end_date:
            filtered = [inc for inc in filtered if inc["date"] <= self.end_date]

        # Cause category filter
        if self.cause_categories:
            filtered = [
                inc
                for inc in filtered
                if inc["cause_category"] in self.cause_categories
            ]

        # Severity filter
        if self.min_severity:
            filtered = [inc for inc in filtered if inc["severity"] >= self.min_severity]

        return filtered


class CauseAnalysisReport:
    """Generate comprehensive HTML reports for incident cause analysis.

    Creates standalone HTML reports with:
    - Executive summary
    - Statistical findings with interactive tables
    - Embedded Plotly visualizations
    - Hatch/opening maloperation analysis
    - Responsive Bootstrap layout
    - Export capabilities

    Attributes:
        incidents: List of incident data dictionaries
        title: Report title
        filters: Applied data filters
    """

    def __init__(
        self,
        incidents: List[Dict[str, Any]],
        title: str = "Incident Cause Analysis Report",
        filters: Optional[ReportFilters] = None,
    ):
        """Initialize report with incident data.

        Args:
            incidents: List of incident dictionaries
            title: Custom report title
            filters: Optional filters to apply to data
        """
        self.title = title
        self.filters = filters or ReportFilters()
        self.incidents = self.filters.apply(incidents)
        self.generation_date = datetime.now()

    def generate_html(self, output_file: Path) -> None:
        """Generate complete HTML report.

        Args:
            output_file: Path to save HTML file
        """
        html = self._build_html_structure()
        output_file.write_text(html)

    def _build_html_structure(self) -> str:
        """Build complete HTML document structure."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    {self._get_css_styles()}
    {self._get_external_libraries()}
</head>
<body>
    {self._generate_navigation()}

    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <h1 class="text-center mt-4 mb-4">{self.title}</h1>
                {self._generate_metadata_section()}
            </div>
        </div>

        {self._generate_executive_summary()}
        {self._generate_statistical_findings()}
        {self._generate_visualizations()}
        {self._generate_hatch_analysis()}
    </div>

    {self._get_javascript()}
</body>
</html>"""

    def _get_css_styles(self) -> str:
        """Get embedded CSS styles including Bootstrap."""
        return """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">  # noqa: E501
<link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
<style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f8f9fa;
    }

    .navbar {
        background-color: #1e3a5f !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .navbar-brand, .nav-link {
        color: #ffffff !important;
    }

    .nav-link:hover {
        color: #ffc107 !important;
    }

    .section {
        background-color: white;
        border-radius: 8px;
        padding: 30px;
        margin-bottom: 30px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .section-title {
        color: #1e3a5f;
        border-bottom: 3px solid #ffc107;
        padding-bottom: 10px;
        margin-bottom: 25px;
    }

    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        text-align: center;
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 10px 0;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .table-responsive {
        margin-top: 20px;
    }

    table.dataTable {
        border-collapse: collapse !important;
    }

    .btn-export {
        margin: 5px;
    }

    .metadata {
        background-color: #e9ecef;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        font-size: 0.9rem;
    }

    .plotly-chart {
        margin: 20px 0;
    }

    .alert-warning {
        border-left: 4px solid #ffc107;
    }

    .alert-info {
        border-left: 4px solid #0dcaf0;
    }
</style>"""

    def _get_external_libraries(self) -> str:
        """Get external JavaScript library imports."""
        return """
<script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>"""  # noqa: E501

    def _generate_navigation(self) -> str:
        """Generate navigation menu."""
        return """
<nav class="navbar navbar-expand-lg navbar-dark sticky-top">
    <div class="container-fluid">
        <a class="navbar-brand" href="#top">Cause Analysis Report</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">  # noqa: E501
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav ms-auto">
                <li class="nav-item">
                    <a class="nav-link" href="#executive-summary">Summary</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#statistical-findings">Statistics</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#visualizations">Visualizations</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#hatch-analysis">Hatch Analysis</a>
                </li>
            </ul>
        </div>
    </div>
</nav>"""

    def _generate_metadata_section(self) -> str:
        """Generate report metadata section."""
        metadata_items = [
            f"<strong>Generated on:</strong> {self.generation_date.strftime('%B %d, %Y at %I:%M %p')}",  # noqa: E501
            f"<strong>Total Incidents:</strong> {len(self.incidents)}",
            "<strong>Data Source:</strong> Marine Safety Incident Database",
        ]

        # Add filter information
        if self.filters.start_date or self.filters.end_date:
            date_filter = "Date Range: "
            if self.filters.start_date:
                date_filter += self.filters.start_date.strftime("%Y-%m-%d")
            date_filter += " to "
            if self.filters.end_date:
                date_filter += self.filters.end_date.strftime("%Y-%m-%d")
            metadata_items.append(f"<strong>Filters Applied:</strong> {date_filter}")

        if self.filters.cause_categories:
            categories = ", ".join([cat.value for cat in self.filters.cause_categories])
            metadata_items.append(f"<strong>Cause Categories:</strong> {categories}")

        if self.filters.min_severity:
            metadata_items.append(
                f"<strong>Minimum Severity:</strong> {self.filters.min_severity.name}"
            )

        metadata_html = " | ".join(metadata_items)

        return f'<div class="metadata">{metadata_html}</div>'

    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        # Calculate summary statistics
        total_incidents = len(self.incidents)
        total_fatalities = sum(inc.get("fatalities", 0) for inc in self.incidents)
        total_injuries = sum(inc.get("injuries", 0) for inc in self.incidents)

        # Cause category breakdown
        cause_counts = Counter(inc["cause_category"].value for inc in self.incidents)
        most_common_cause = (
            cause_counts.most_common(1)[0] if cause_counts else ("Unknown", 0)
        )

        # Severity breakdown
        Counter(inc["severity"].name for inc in self.incidents)
        serious_or_higher = sum(
            1 for inc in self.incidents if inc["severity"] >= SeverityLevel.SERIOUS
        )

        return f"""
<div class="row mt-4" id="executive-summary">
    <div class="col-12">
        <div class="section">
            <h2 class="section-title">Executive Summary</h2>

            <div class="row">
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-label">Total Incidents</div>
                        <div class="metric-value">{total_incidents}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">  # noqa: E501
                        <div class="metric-label">Fatalities</div>
                        <div class="metric-value">{total_fatalities}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">  # noqa: E501
                        <div class="metric-label">Injuries</div>
                        <div class="metric-value">{total_injuries}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">  # noqa: E501
                        <div class="metric-label">Serious+</div>
                        <div class="metric-value">{serious_or_higher}</div>
                    </div>
                </div>
            </div>

            <div class="alert alert-info mt-4">
                <h5>Key Findings:</h5>
                <ul>
                    <li><strong>Most Common Cause:</strong> {most_common_cause[0].replace('_', ' ').title()} ({most_common_cause[1]} incidents)</li>  # noqa: E501
                    <li><strong>Severity Distribution:</strong> {serious_or_higher} incidents classified as Serious or higher ({(serious_or_higher/total_incidents*100):.1f}%)</li>  # noqa: E501
                    <li><strong>Safety Impact:</strong> {total_fatalities} fatalities and {total_injuries} injuries reported across all incidents</li>  # noqa: E501
                </ul>
            </div>
        </div>
    </div>
</div>"""

    def _generate_statistical_findings(self) -> str:
        """Generate statistical findings section with data tables."""
        # Create cause category table data
        cause_counts = Counter(inc["cause_category"].value for inc in self.incidents)
        cause_table_rows = ""
        for cause, count in cause_counts.most_common():
            percentage = (count / len(self.incidents) * 100) if self.incidents else 0
            cause_table_rows += f"""
                <tr>
                    <td>{cause.replace('_', ' ').title()}</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>"""

        # Create severity table data
        severity_counts = Counter(inc["severity"].name for inc in self.incidents)
        severity_table_rows = ""
        for severity in ["CATASTROPHIC", "SERIOUS", "MODERATE", "MINOR", "MINIMAL"]:
            count = severity_counts.get(severity, 0)
            percentage = (count / len(self.incidents) * 100) if self.incidents else 0
            severity_table_rows += f"""
                <tr>
                    <td>{severity.title()}</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>"""

        return f"""
<div class="row mt-4" id="statistical-findings">
    <div class="col-12">
        <div class="section">
            <h2 class="section-title">Statistical Findings</h2>

            <div class="row">
                <div class="col-md-6">
                    <h4>Incidents by Cause Category</h4>
                    <div class="text-end mb-2">
                        <button class="btn btn-sm btn-primary btn-export" onclick="exportTableToCSV('cause-table', 'cause_categories.csv')">  # noqa: E501
                            Export CSV
                        </button>
                    </div>
                    <div class="table-responsive">
                        <table id="cause-table" class="table table-striped table-hover">
                            <thead class="table-dark">
                                <tr>
                                    <th>Cause Category</th>
                                    <th>Count</th>
                                    <th>Percentage</th>
                                </tr>
                            </thead>
                            <tbody>
                                {cause_table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="col-md-6">
                    <h4>Incidents by Severity Level</h4>
                    <div class="text-end mb-2">
                        <button class="btn btn-sm btn-primary btn-export" onclick="exportTableToCSV('severity-table', 'severity_levels.csv')">  # noqa: E501
                            Export CSV
                        </button>
                    </div>
                    <div class="table-responsive">
                        <table id="severity-table" class="table table-striped table-hover">
                            <thead class="table-dark">
                                <tr>
                                    <th>Severity Level</th>
                                    <th>Count</th>
                                    <th>Percentage</th>
                                </tr>
                            </thead>
                            <tbody>
                                {severity_table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>"""

    def _generate_visualizations(self) -> str:
        """Generate interactive Plotly visualizations."""
        # Create visualizations
        cause_pie_chart = self._create_cause_distribution_chart()
        severity_trend_chart = self._create_severity_trend_chart()

        return f"""
<div class="row mt-4" id="visualizations">
    <div class="col-12">
        <div class="section">
            <h2 class="section-title">Interactive Visualizations</h2>

            <div class="row">
                <div class="col-md-6">
                    <h4>Cause Category Distribution</h4>
                    <div id="cause-pie-chart" class="plotly-chart"></div>
                </div>

                <div class="col-md-6">
                    <h4>Severity Trend Over Time</h4>
                    <div id="severity-trend-chart" class="plotly-chart"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    {cause_pie_chart}
    {severity_trend_chart}
</script>"""

    def _create_cause_distribution_chart(self) -> str:
        """Create Plotly pie chart for cause distribution."""
        cause_counts = Counter(inc["cause_category"].value for inc in self.incidents)

        labels = [cause.replace("_", " ").title() for cause in cause_counts.keys()]
        values = list(cause_counts.values())

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.3,
                    marker=dict(colors=px.colors.qualitative.Set3),
                )
            ]
        )

        fig.update_layout(
            title="Incident Cause Category Distribution", showlegend=True, height=400
        )

        plot_json = fig.to_json()

        return (
            f"Plotly.newPlot('cause-pie-chart', {plot_json}.data, {plot_json}.layout);"
        )

    def _create_severity_trend_chart(self) -> str:
        """Create Plotly line chart for severity trends over time."""
        # Group incidents by month and severity
        from collections import defaultdict

        monthly_severity = defaultdict(lambda: defaultdict(int))

        for inc in self.incidents:
            month_key = inc["date"].strftime("%Y-%m")
            severity = inc["severity"].name
            monthly_severity[month_key][severity] += 1

        # Sort months
        sorted_months = sorted(monthly_severity.keys())

        # Create traces for each severity level
        traces = []
        severities = ["CATASTROPHIC", "SERIOUS", "MODERATE", "MINOR", "MINIMAL"]
        colors = ["#d32f2f", "#f57c00", "#fbc02d", "#7cb342", "#388e3c"]

        for severity, color in zip(severities, colors):
            counts = [
                monthly_severity[month].get(severity, 0) for month in sorted_months
            ]
            if sum(counts) > 0:  # Only add if there's data
                traces.append(
                    go.Scatter(
                        x=sorted_months,
                        y=counts,
                        mode="lines+markers",
                        name=severity.title(),
                        line=dict(color=color, width=2),
                        marker=dict(size=8),
                    )
                )

        fig = go.Figure(data=traces)

        fig.update_layout(
            title="Severity Trend Over Time",
            xaxis_title="Month",
            yaxis_title="Number of Incidents",
            hovermode="x unified",
            height=400,
        )

        plot_json = fig.to_json()

        return f"Plotly.newPlot('severity-trend-chart', {plot_json}.data, {plot_json}.layout);"

    def _generate_hatch_analysis(self) -> str:
        """Generate hatch/opening maloperation analysis section."""
        # Filter incidents mentioning hatch or opening issues
        hatch_incidents = [
            inc
            for inc in self.incidents
            if "hatch" in inc.get("description", "").lower()
            or "opening" in inc.get("description", "").lower()
        ]

        hatch_count = len(hatch_incidents)
        hatch_percentage = (
            (hatch_count / len(self.incidents) * 100) if self.incidents else 0
        )

        # Analyze hatch-related incidents
        hatch_fatalities = sum(inc.get("fatalities", 0) for inc in hatch_incidents)
        hatch_injuries = sum(inc.get("injuries", 0) for inc in hatch_incidents)

        hatch_table_rows = ""
        for inc in hatch_incidents[:10]:  # Show top 10
            hatch_table_rows += f"""
                <tr>
                    <td>{inc.get('incident_id', 'N/A')}</td>
                    <td>{inc.get('date').strftime('%Y-%m-%d') if inc.get('date') else 'N/A'}</td>
                    <td>{inc.get('vessel_name', 'N/A')}</td>
                    <td>{inc.get('severity').name if inc.get('severity') else 'N/A'}</td>
                    <td>{inc.get('description', '')[:100]}...</td>
                </tr>"""

        return f"""
<div class="row mt-4" id="hatch-analysis">
    <div class="col-12">
        <div class="section">
            <h2 class="section-title">Hatch & Opening Maloperation Analysis</h2>

            <div class="alert alert-warning">
                <h5>Hatch-Related Incidents Overview:</h5>
                <ul>
                    <li><strong>Total Hatch/Opening Incidents:</strong> {hatch_count} ({hatch_percentage:.1f}% of all incidents)</li>  # noqa: E501
                    <li><strong>Associated Fatalities:</strong> {hatch_fatalities}</li>
                    <li><strong>Associated Injuries:</strong> {hatch_injuries}</li>
                </ul>
            </div>

            <h4 class="mt-4">Hatch-Related Incident Details</h4>
            <div class="text-end mb-2">
                <button class="btn btn-sm btn-primary btn-export" onclick="exportTableToCSV('hatch-table', 'hatch_incidents.csv')">  # noqa: E501
                    Export CSV
                </button>
            </div>
            <div class="table-responsive">
                <table id="hatch-table" class="table table-striped table-hover dataTable">
                    <thead class="table-dark">
                        <tr>
                            <th>Incident ID</th>
                            <th>Date</th>
                            <th>Vessel</th>
                            <th>Severity</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        {hatch_table_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>"""

    def _get_javascript(self) -> str:
        """Get JavaScript for interactivity."""
        return r"""
<script>
    // Initialize DataTables
    $(document).ready(function() {
        $('#cause-table').DataTable({
            pageLength: 10,
            order: [[1, 'desc']]
        });

        $('#severity-table').DataTable({
            pageLength: 10,
            order: [[1, 'desc']]
        });

        $('#hatch-table').DataTable({
            pageLength: 10,
            order: [[1, 'desc']]
        });
    });

    // Export table to CSV function
    function exportTableToCSV(tableId, filename) {
        var csv = [];
        var table = document.getElementById(tableId);
        var rows = table.querySelectorAll('tr');

        for (var i = 0; i < rows.length; i++) {
            var row = [], cols = rows[i].querySelectorAll('td, th');

            for (var j = 0; j < cols.length; j++) {
                var data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ')
                data = data.replace(/"/g, '""');
                row.push('"' + data + '"');
            }

            csv.push(row.join(','));
        }

        // Download CSV
        var csvString = csv.join('\n');
        var downloadLink = document.createElement('a');
        downloadLink.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvString);
        downloadLink.download = filename;

        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    }

    // Smooth scroll for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
</script>"""
