"""
Interactive dashboard for test performance metrics.
"""

from pathlib import Path
from typing import Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .analyzer import PerformanceAnalyzer
from .database import PerformanceDatabase


class PerformanceDashboard:
    """Interactive dashboard for test performance visualization."""

    def __init__(self, db: Optional[PerformanceDatabase] = None):
        """
        Initialize performance dashboard.

        Args:
            db: Performance database instance
        """
        self.db = db or PerformanceDatabase()
        self.analyzer = PerformanceAnalyzer(self.db)

    def create_trends_chart(self, days: int = 30) -> go.Figure:
        """
        Create performance trends chart.

        Args:
            days: Number of days to display

        Returns:
            Plotly figure object
        """
        trends = self.db.get_performance_trends(days)

        if trends.empty:
            return self._create_empty_figure("No test execution data available")

        # Create subplots
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Test Execution Count",
                "Average Test Duration",
                "Success Rate",
                "Total Execution Time",
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}],
            ],
        )

        # Test execution count
        fig.add_trace(
            go.Scatter(
                x=trends["date"],
                y=trends["total_tests"],
                mode="lines+markers",
                name="Tests Run",
                line=dict(color="blue", width=2),
            ),
            row=1,
            col=1,
        )

        # Average duration
        fig.add_trace(
            go.Scatter(
                x=trends["date"],
                y=trends["avg_duration"],
                mode="lines+markers",
                name="Avg Duration",
                line=dict(color="orange", width=2),
            ),
            row=1,
            col=2,
        )

        # Success rate
        fig.add_trace(
            go.Scatter(
                x=trends["date"],
                y=trends["success_rate"],
                mode="lines+markers",
                name="Success Rate",
                line=dict(color="green", width=2),
            ),
            row=2,
            col=1,
        )

        # Total execution time
        fig.add_trace(
            go.Scatter(
                x=trends["date"],
                y=trends["total_duration"],
                mode="lines+markers",
                name="Total Duration",
                line=dict(color="red", width=2),
            ),
            row=2,
            col=2,
        )

        # Update layout
        fig.update_layout(
            title="Test Performance Trends",
            showlegend=False,
            height=600,
            hovermode="x unified",
        )

        # Update axes
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=2)
        fig.update_yaxes(title_text="Count", row=1, col=1)
        fig.update_yaxes(title_text="Seconds", row=1, col=2)
        fig.update_yaxes(title_text="Percentage", row=2, col=1)
        fig.update_yaxes(title_text="Seconds", row=2, col=2)

        return fig

    def create_slowest_tests_chart(self, limit: int = 20) -> go.Figure:
        """
        Create bar chart of slowest tests.

        Args:
            limit: Number of tests to display

        Returns:
            Plotly figure object
        """
        slow_tests = self.db.get_slowest_tests(limit=limit)

        if slow_tests.empty:
            return self._create_empty_figure("No test execution data available")

        # Truncate long test names
        slow_tests["short_name"] = slow_tests["test_name"].apply(
            lambda x: x[:40] + "..." if len(x) > 40 else x
        )

        fig = go.Figure()

        # Add bar chart
        fig.add_trace(
            go.Bar(
                x=slow_tests["avg_duration"],
                y=slow_tests["short_name"],
                orientation="h",
                marker=dict(
                    color=slow_tests["avg_duration"],
                    colorscale="Reds",
                    showscale=True,
                    colorbar=dict(title="Duration (s)"),
                ),
                text=slow_tests["avg_duration"].round(3),
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>"
                + "Avg Duration: %{x:.3f}s<br>"
                + "<extra></extra>",
            )
        )

        fig.update_layout(
            title=f"Top {limit} Slowest Tests",
            xaxis_title="Average Duration (seconds)",
            yaxis_title="Test Name",
            height=max(400, limit * 30),
            margin=dict(l=250),
            showlegend=False,
        )

        return fig

    def create_test_distribution_chart(self) -> go.Figure:
        """
        Create test duration distribution chart.

        Returns:
            Plotly figure object
        """
        stats = self.db.get_test_statistics()

        if stats.empty:
            return self._create_empty_figure("No test statistics available")

        # Create histogram
        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=stats["avg_duration"],
                nbinsx=50,
                marker=dict(color="lightblue", line=dict(color="darkblue", width=1)),
                hovertemplate="Duration: %{x:.3f}s<br>Count: %{y}<extra></extra>",
            )
        )

        # Add percentile lines
        percentiles = [50, 90, 95, 99]
        colors = ["green", "yellow", "orange", "red"]

        for p, color in zip(percentiles, colors):
            value = stats["avg_duration"].quantile(p / 100)
            fig.add_vline(
                x=value,
                line_dash="dash",
                line_color=color,
                annotation_text=f"P{p}: {value:.3f}s",
            )

        fig.update_layout(
            title="Test Duration Distribution",
            xaxis_title="Average Duration (seconds)",
            yaxis_title="Number of Tests",
            height=400,
            showlegend=False,
        )

        return fig

    def create_regression_chart(self, test_name: str) -> go.Figure:
        """
        Create regression analysis chart for a specific test.

        Args:
            test_name: Name of the test

        Returns:
            Plotly figure object
        """
        history = self.db.get_test_history(test_name, limit=100)

        if history.empty:
            return self._create_empty_figure(
                f"No history available for test: {test_name}"
            )

        # Filter successful runs
        history = history[history["status"] == "passed"]

        if history.empty:
            return self._create_empty_figure(
                f"No successful runs for test: {test_name}"
            )

        fig = go.Figure()

        # Add scatter plot of durations
        fig.add_trace(
            go.Scatter(
                x=history["timestamp"],
                y=history["duration"],
                mode="markers+lines",
                name="Duration",
                marker=dict(size=8, color="blue", opacity=0.6),
                line=dict(color="lightblue", width=1),
            )
        )

        # Add moving average
        window = min(10, len(history) // 3)
        if window > 1:
            history["ma"] = history["duration"].rolling(window=window).mean()

            fig.add_trace(
                go.Scatter(
                    x=history["timestamp"],
                    y=history["ma"],
                    mode="lines",
                    name=f"{window}-run Moving Average",
                    line=dict(color="red", width=2),
                )
            )

        # Add mean line
        mean_duration = history["duration"].mean()
        fig.add_hline(
            y=mean_duration,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Mean: {mean_duration:.3f}s",
        )

        # Add standard deviation bands
        std_duration = history["duration"].std()

        fig.add_hrect(
            y0=mean_duration - std_duration,
            y1=mean_duration + std_duration,
            fillcolor="green",
            opacity=0.1,
            line_width=0,
        )

        fig.add_hrect(
            y0=mean_duration - 2 * std_duration,
            y1=mean_duration + 2 * std_duration,
            fillcolor="yellow",
            opacity=0.1,
            line_width=0,
        )

        fig.update_layout(
            title=f"Performance History: {test_name[:60]}",
            xaxis_title="Timestamp",
            yaxis_title="Duration (seconds)",
            height=400,
            hovermode="x unified",
        )

        return fig

    def create_parallelization_chart(self, max_workers: int = 8) -> go.Figure:
        """
        Create parallelization efficiency chart.

        Args:
            max_workers: Maximum number of workers to analyze

        Returns:
            Plotly figure object
        """
        worker_counts = list(range(1, max_workers + 1))
        speedups = []
        efficiencies = []
        times = []

        for workers in worker_counts:
            result = self.analyzer.calculate_parallel_efficiency(num_workers=workers)

            if result["status"] == "calculated":
                speedups.append(result["speedup_factor"])
                efficiencies.append(result["efficiency_percentage"])
                times.append(result["parallel_execution_time"])
            else:
                speedups.append(1)
                efficiencies.append(100)
                times.append(0)

        # Create subplots
        fig = make_subplots(
            rows=1,
            cols=3,
            subplot_titles=("Speedup Factor", "Efficiency", "Execution Time"),
        )

        # Speedup chart
        fig.add_trace(
            go.Scatter(
                x=worker_counts,
                y=speedups,
                mode="lines+markers",
                name="Speedup",
                line=dict(color="blue", width=2),
            ),
            row=1,
            col=1,
        )

        # Add ideal speedup line
        fig.add_trace(
            go.Scatter(
                x=worker_counts,
                y=worker_counts,
                mode="lines",
                name="Ideal",
                line=dict(color="gray", width=1, dash="dash"),
            ),
            row=1,
            col=1,
        )

        # Efficiency chart
        fig.add_trace(
            go.Bar(
                x=worker_counts,
                y=efficiencies,
                name="Efficiency",
                marker=dict(color=efficiencies, colorscale="RdYlGn", cmin=0, cmax=100),
            ),
            row=1,
            col=2,
        )

        # Execution time chart
        fig.add_trace(
            go.Scatter(
                x=worker_counts,
                y=times,
                mode="lines+markers",
                name="Time",
                line=dict(color="red", width=2),
            ),
            row=1,
            col=3,
        )

        fig.update_layout(
            title="Parallelization Analysis", height=400, showlegend=False
        )

        fig.update_xaxes(title_text="Workers", row=1, col=1)
        fig.update_xaxes(title_text="Workers", row=1, col=2)
        fig.update_xaxes(title_text="Workers", row=1, col=3)
        fig.update_yaxes(title_text="Speedup", row=1, col=1)
        fig.update_yaxes(title_text="Efficiency (%)", row=1, col=2)
        fig.update_yaxes(title_text="Time (s)", row=1, col=3)

        return fig

    def _create_empty_figure(self, message: str) -> go.Figure:
        """Create empty figure with message."""
        fig = go.Figure()

        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text=message,
            showarrow=False,
            font=dict(size=20, color="gray"),
            xanchor="center",
            yanchor="middle",
        )

        fig.update_layout(
            xaxis=dict(visible=False), yaxis=dict(visible=False), height=400
        )

        return fig

    def generate_dashboard(self, output_path: Path):
        """
        Generate complete dashboard HTML file.

        Args:
            output_path: Path to save dashboard HTML
        """
        # Create all charts
        trends_chart = self.create_trends_chart()
        slowest_chart = self.create_slowest_tests_chart()
        distribution_chart = self.create_test_distribution_chart()
        parallel_chart = self.create_parallelization_chart()

        # Convert to HTML
        trends_html = trends_chart.to_html(include_plotlyjs=False, div_id="trends")
        slowest_html = slowest_chart.to_html(include_plotlyjs=False, div_id="slowest")
        distribution_html = distribution_chart.to_html(
            include_plotlyjs=False, div_id="distribution"
        )
        parallel_html = parallel_chart.to_html(
            include_plotlyjs=False, div_id="parallel"
        )

        # Create complete HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Performance Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .chart-container {{
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0;
        }}
        h2 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Test Performance Dashboard</h1>
            <p>Interactive visualization of test execution metrics</p>
        </div>

        <div class="chart-container">
            <h2>Performance Trends</h2>
            {trends_html}
        </div>

        <div class="chart-container">
            <h2>Slowest Tests</h2>
            {slowest_html}
        </div>

        <div class="chart-container">
            <h2>Duration Distribution</h2>
            {distribution_html}
        </div>

        <div class="chart-container">
            <h2>Parallelization Analysis</h2>
            {parallel_html}
        </div>
    </div>
</body>
</html>
"""

        output_path.write_text(html)
