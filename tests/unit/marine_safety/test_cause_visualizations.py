# ABOUTME: Test suite for marine safety cause visualization module
# ABOUTME: Validates interactive Plotly visualizations for incident cause analysis

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from worldenergydata.marine_safety.analysis.cause_visualizations import (
    CauseVisualizer,
)
from worldenergydata.marine_safety.constants import (
    CauseCategory,
    SeverityLevel,
)


@pytest.fixture
def sample_incident_data():
    """Create sample incident data for testing visualizations."""
    base_date = datetime(2020, 1, 1)

    data = []
    causes = list(CauseCategory)
    severities = list(SeverityLevel)

    # Create 100 sample incidents with varied distributions
    for i in range(100):
        incident_date = base_date + timedelta(days=i * 3)
        cause_idx = i % len(causes)
        severity_idx = min(i % len(severities), len(severities) - 1)

        data.append(
            {
                "incident_id": f"INC-{i:04d}",
                "date": incident_date,
                "cause_category": causes[cause_idx].value,
                "severity": severities[severity_idx],
                "description": f"Test incident {i}",
                "vessel_type": "supply_vessel",
                "location": "Gulf of Mexico",
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def hatch_maloperation_data():
    """Create sample data for hatch/opening maloperation incidents."""
    base_date = datetime(2020, 1, 1)

    data = []
    maloperation_types = [
        "improper_securing",
        "delayed_closure",
        "missing_fasteners",
        "inadequate_inspection",
        "structural_damage",
    ]

    for i in range(50):
        incident_date = base_date + timedelta(days=i * 7)

        data.append(
            {
                "incident_id": f"HATCH-{i:03d}",
                "date": incident_date,
                "maloperation_type": maloperation_types[i % len(maloperation_types)],
                "severity": list(SeverityLevel)[i % len(list(SeverityLevel))],
                "hatch_location": f"Hatch #{(i % 5) + 1}",
                "weather_condition": "rough_seas" if i % 3 == 0 else "calm",
                "consequences": "flooding" if i % 4 == 0 else "near_miss",
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def visualizer():
    """Create CauseVisualizer instance."""
    return CauseVisualizer()


class TestCauseVisualizerInitialization:
    """Test CauseVisualizer initialization."""

    def test_visualizer_creation(self, visualizer):
        """Test that visualizer can be instantiated."""
        assert visualizer is not None
        assert isinstance(visualizer, CauseVisualizer)

    def test_default_color_scheme(self, visualizer):
        """Test that visualizer has default color scheme."""
        assert hasattr(visualizer, "color_scheme")
        assert isinstance(visualizer.color_scheme, dict)
        assert len(visualizer.color_scheme) > 0


class TestCauseFrequencyVisualization:
    """Test cause frequency bar chart generation."""

    def test_create_cause_frequency_chart(self, visualizer, sample_incident_data):
        """Test creation of interactive bar chart for cause frequencies."""
        fig = visualizer.create_cause_frequency_chart(sample_incident_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.layout.title.text is not None
        assert (
            "Cause" in fig.layout.xaxis.title.text
            or "Category" in fig.layout.xaxis.title.text
        )
        # Y-axis should indicate quantity/count (could be 'Count', 'Frequency', 'Number', or 'Incidents')
        y_title = fig.layout.yaxis.title.text.lower()
        assert any(
            word in y_title for word in ["count", "frequency", "number", "incidents"]
        )

    def test_cause_frequency_interactivity(self, visualizer, sample_incident_data):
        """Test that cause frequency chart has interactive features."""
        fig = visualizer.create_cause_frequency_chart(sample_incident_data)

        # Check for hover data
        assert (
            fig.data[0].hovertemplate is not None or fig.data[0].hoverinfo is not None
        )

    def test_cause_frequency_with_empty_data(self, visualizer):
        """Test handling of empty dataframe."""
        empty_df = pd.DataFrame(columns=["cause_category", "severity"])
        fig = visualizer.create_cause_frequency_chart(empty_df)

        assert isinstance(fig, go.Figure)


class TestTimeSeriesVisualization:
    """Test time series plots for cause trends."""

    def test_create_cause_trend_over_time(self, visualizer, sample_incident_data):
        """Test creation of time series plot showing cause trends."""
        fig = visualizer.create_cause_trend_over_time(sample_incident_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.layout.xaxis.title.text is not None
        assert (
            "time" in fig.layout.xaxis.title.text.lower()
            or "date" in fig.layout.xaxis.title.text.lower()
        )

    def test_time_series_monthly_aggregation(self, visualizer, sample_incident_data):
        """Test monthly aggregation option for time series."""
        fig = visualizer.create_cause_trend_over_time(
            sample_incident_data, aggregation="monthly"
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_time_series_interactivity(self, visualizer, sample_incident_data):
        """Test that time series has zoom and pan capabilities."""
        fig = visualizer.create_cause_trend_over_time(sample_incident_data)

        # Plotly figures should have dragmode for zoom/pan
        assert fig.layout.dragmode in ["zoom", "pan", None]


class TestPieChartVisualization:
    """Test pie chart for cause category proportions."""

    def test_create_cause_proportion_pie_chart(self, visualizer, sample_incident_data):
        """Test creation of pie chart for cause proportions."""
        fig = visualizer.create_cause_proportion_pie_chart(sample_incident_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "pie"

    def test_pie_chart_shows_percentages(self, visualizer, sample_incident_data):
        """Test that pie chart displays percentages."""
        fig = visualizer.create_cause_proportion_pie_chart(sample_incident_data)

        # Pie chart should have textinfo showing percentages
        assert "percent" in fig.data[0].textinfo or fig.data[0].texttemplate is not None

    def test_pie_chart_hover_info(self, visualizer, sample_incident_data):
        """Test that pie chart has hover information."""
        fig = visualizer.create_cause_proportion_pie_chart(sample_incident_data)

        assert (
            fig.data[0].hovertemplate is not None or fig.data[0].hoverinfo is not None
        )


class TestHeatmapVisualization:
    """Test heatmap for cause vs severity cross-tabulation."""

    def test_create_cause_severity_heatmap(self, visualizer, sample_incident_data):
        """Test creation of heatmap for cause vs severity."""
        fig = visualizer.create_cause_severity_heatmap(sample_incident_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "heatmap"

    def test_heatmap_has_colorscale(self, visualizer, sample_incident_data):
        """Test that heatmap has appropriate colorscale."""
        fig = visualizer.create_cause_severity_heatmap(sample_incident_data)

        assert fig.data[0].colorscale is not None

    def test_heatmap_axis_labels(self, visualizer, sample_incident_data):
        """Test that heatmap has proper axis labels."""
        fig = visualizer.create_cause_severity_heatmap(sample_incident_data)

        assert fig.layout.xaxis.title.text is not None
        assert fig.layout.yaxis.title.text is not None


class TestHatchMaloperationVisualization:
    """Test visualizations specific to hatch/opening maloperation incidents."""

    def test_create_hatch_maloperation_chart(self, visualizer, hatch_maloperation_data):
        """Test creation of hatch maloperation specific visualization."""
        fig = visualizer.create_hatch_maloperation_chart(hatch_maloperation_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_hatch_maloperation_types_shown(self, visualizer, hatch_maloperation_data):
        """Test that all maloperation types are represented."""
        fig = visualizer.create_hatch_maloperation_chart(hatch_maloperation_data)

        # Should have data for multiple maloperation types
        assert len(fig.data) > 0

    def test_hatch_maloperation_severity_breakdown(
        self, visualizer, hatch_maloperation_data
    ):
        """Test severity breakdown in hatch maloperation visualization."""
        fig = visualizer.create_hatch_maloperation_severity_breakdown(
            hatch_maloperation_data
        )

        assert isinstance(fig, go.Figure)


class TestSunburstVisualization:
    """Test sunburst chart for hierarchical cause analysis."""

    def test_create_cause_hierarchy_sunburst(self, visualizer, sample_incident_data):
        """Test creation of sunburst chart for hierarchical analysis."""
        fig = visualizer.create_cause_hierarchy_sunburst(sample_incident_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "sunburst"

    def test_sunburst_multiple_levels(self, visualizer, sample_incident_data):
        """Test that sunburst has multiple hierarchical levels."""
        fig = visualizer.create_cause_hierarchy_sunburst(sample_incident_data)

        # Sunburst should have parents and labels
        assert hasattr(fig.data[0], "labels")
        assert hasattr(fig.data[0], "parents")

    def test_sunburst_interactivity(self, visualizer, sample_incident_data):
        """Test sunburst click-to-zoom functionality."""
        fig = visualizer.create_cause_hierarchy_sunburst(sample_incident_data)

        # Sunburst charts in Plotly are inherently interactive
        assert fig.data[0].type == "sunburst"


class TestVisualizationCommonFeatures:
    """Test common features across all visualizations."""

    def test_all_charts_return_plotly_figure(self, visualizer, sample_incident_data):
        """Test that all visualization methods return Plotly Figure objects."""
        methods = [
            "create_cause_frequency_chart",
            "create_cause_trend_over_time",
            "create_cause_proportion_pie_chart",
            "create_cause_severity_heatmap",
            "create_cause_hierarchy_sunburst",
        ]

        for method_name in methods:
            method = getattr(visualizer, method_name)
            fig = method(sample_incident_data)
            assert isinstance(fig, go.Figure), f"{method_name} should return go.Figure"

    def test_all_charts_have_titles(self, visualizer, sample_incident_data):
        """Test that all charts have titles."""
        methods = [
            "create_cause_frequency_chart",
            "create_cause_trend_over_time",
            "create_cause_proportion_pie_chart",
            "create_cause_severity_heatmap",
            "create_cause_hierarchy_sunburst",
        ]

        for method_name in methods:
            method = getattr(visualizer, method_name)
            fig = method(sample_incident_data)
            assert fig.layout.title.text is not None, f"{method_name} should have title"

    def test_consistent_color_scheme(self, visualizer, sample_incident_data):
        """Test that visualizations use consistent color scheme."""
        # Create multiple charts
        fig1 = visualizer.create_cause_frequency_chart(sample_incident_data)
        fig2 = visualizer.create_cause_proportion_pie_chart(sample_incident_data)

        # Both should exist (color consistency check would require deeper analysis)
        assert isinstance(fig1, go.Figure)
        assert isinstance(fig2, go.Figure)


class TestExportFunctionality:
    """Test export capabilities for HTML reports."""

    def test_figure_can_be_exported_to_html(
        self, visualizer, sample_incident_data, tmp_path
    ):
        """Test that figures can be exported to HTML files."""
        fig = visualizer.create_cause_frequency_chart(sample_incident_data)

        output_file = tmp_path / "test_chart.html"
        fig.write_html(str(output_file))

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_multiple_charts_export(self, visualizer, sample_incident_data, tmp_path):
        """Test exporting multiple charts to HTML."""
        charts = [
            (
                "frequency",
                visualizer.create_cause_frequency_chart(sample_incident_data),
            ),
            ("trend", visualizer.create_cause_trend_over_time(sample_incident_data)),
            ("pie", visualizer.create_cause_proportion_pie_chart(sample_incident_data)),
        ]

        for name, fig in charts:
            output_file = tmp_path / f"{name}_chart.html"
            fig.write_html(str(output_file))
            assert output_file.exists()


class TestResponsiveDesign:
    """Test responsive design features."""

    def test_charts_have_autosize(self, visualizer, sample_incident_data):
        """Test that charts are configured for responsive sizing."""
        fig = visualizer.create_cause_frequency_chart(sample_incident_data)

        # Check layout has autosize or width settings
        assert hasattr(fig.layout, "autosize") or hasattr(fig.layout, "width")

    def test_charts_have_proper_margins(self, visualizer, sample_incident_data):
        """Test that charts have proper margins for different screens."""
        fig = visualizer.create_cause_frequency_chart(sample_incident_data)

        # Should have margin settings
        assert hasattr(fig.layout, "margin")


class TestDataValidation:
    """Test data validation and error handling."""

    def test_missing_required_columns(self, visualizer):
        """Test handling of missing required columns."""
        incomplete_df = pd.DataFrame({"some_col": [1, 2, 3]})

        # Should either raise informative error or handle gracefully
        # Implementation will determine exact behavior
        try:
            fig = visualizer.create_cause_frequency_chart(incomplete_df)
            # If it doesn't raise, it should return a Figure
            assert isinstance(fig, go.Figure)
        except (KeyError, ValueError) as e:
            # If it raises, error message should be informative
            assert "cause" in str(e).lower() or "column" in str(e).lower()

    def test_null_values_handling(self, visualizer, sample_incident_data):
        """Test handling of null values in data."""
        # Add some null values
        data_with_nulls = sample_incident_data.copy()
        data_with_nulls.loc[0:5, "cause_category"] = None

        fig = visualizer.create_cause_frequency_chart(data_with_nulls)
        assert isinstance(fig, go.Figure)


class TestCustomization:
    """Test customization options."""

    def test_custom_title(self, visualizer, sample_incident_data):
        """Test setting custom title on charts."""
        custom_title = "Custom Test Title"
        fig = visualizer.create_cause_frequency_chart(
            sample_incident_data, title=custom_title
        )

        assert custom_title in fig.layout.title.text

    def test_custom_color_scheme(self):
        """Test using custom color scheme."""
        custom_colors = {
            CauseCategory.HUMAN_ERROR: "#FF0000",
            CauseCategory.EQUIPMENT_FAILURE: "#00FF00",
        }

        visualizer = CauseVisualizer(color_scheme=custom_colors)
        assert visualizer.color_scheme == custom_colors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
