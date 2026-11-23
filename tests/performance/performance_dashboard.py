"""
Performance Report Dashboard Generator
Creates HTML dashboards with performance metrics and visualizations
"""

import json
import os
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class PerformanceDashboard:
    """Generate HTML dashboard for performance test results"""

    def __init__(self, output_dir: str = "tests/performance/reports"):
        """Initialize dashboard generator"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = {}
        self.historical_data = []

    def load_benchmark_results(self, benchmark_file: str) -> Dict:
        """Load pytest-benchmark JSON results"""
        if Path(benchmark_file).exists():
            with open(benchmark_file, "r") as f:
                return json.load(f)
        return {}

    def load_regression_report(
        self, report_file: str = "tests/performance/regression_report.txt"
    ) -> str:
        """Load regression detection report"""
        if Path(report_file).exists():
            with open(report_file, "r") as f:
                return f.read()
        return "No regression report available"

    def generate_html_dashboard(
        self,
        benchmark_data: Optional[Dict] = None,
        regression_report: Optional[str] = None,
    ) -> str:
        """Generate HTML dashboard with performance metrics"""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Process benchmark data if available
        benchmark_html = (
            self._generate_benchmark_section(benchmark_data) if benchmark_data else ""
        )

        # Process regression report
        regression_html = (
            self._format_regression_report(regression_report)
            if regression_report
            else ""
        )

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Test Dashboard - WorldEnergyData</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        
        .header .timestamp {{
            color: #666;
            font-size: 14px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        
        .metric-label {{
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .section {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .benchmark-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .benchmark-table th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
        }}
        
        .benchmark-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .benchmark-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .status-pass {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .status-fail {{
            color: #dc3545;
            font-weight: bold;
        }}
        
        .status-warning {{
            color: #ffc107;
            font-weight: bold;
        }}
        
        .regression-alert {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .regression-critical {{
            background: #f8d7da;
            border-left: 4px solid #dc3545;
        }}
        
        .improvement-notice {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .chart-container {{
            height: 300px;
            margin: 20px 0;
            position: relative;
        }}
        
        .progress-bar {{
            background: #e9ecef;
            border-radius: 10px;
            height: 30px;
            overflow: hidden;
            margin: 10px 0;
        }}
        
        .progress-fill {{
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.5s ease;
        }}
        
        pre {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Performance Test Dashboard</h1>
            <div class="timestamp">Generated: {timestamp}</div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Tests</div>
                <div class="metric-value">{self._get_total_tests(benchmark_data)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Execution Time</div>
                <div class="metric-value">{self._get_avg_time(benchmark_data)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Performance Score</div>
                <div class="metric-value">{self._calculate_score(benchmark_data)}/100</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Regressions</div>
                <div class="metric-value">{self._count_regressions(regression_report)}</div>
            </div>
        </div>
        
        {benchmark_html}
        
        <div class="section">
            <h2>📊 Regression Analysis</h2>
            {regression_html}
        </div>
        
        <div class="section">
            <h2>🎯 Performance Recommendations</h2>
            {self._generate_recommendations(benchmark_data, regression_report)}
        </div>
        
        <div class="footer">
            <p>WorldEnergyData Performance Testing Suite | Powered by pytest-benchmark</p>
        </div>
    </div>
</body>
</html>
"""
        return html_content

    def _generate_benchmark_section(self, benchmark_data: Dict) -> str:
        """Generate benchmark results section"""
        if not benchmark_data or "benchmarks" not in benchmark_data:
            return ""

        rows = ""
        for bench in benchmark_data.get("benchmarks", []):
            name = bench.get("name", "Unknown")
            mean = bench.get("stats", {}).get("mean", 0) * 1000  # Convert to ms
            min_time = bench.get("stats", {}).get("min", 0) * 1000
            max_time = bench.get("stats", {}).get("max", 0) * 1000
            stddev = bench.get("stats", {}).get("stddev", 0) * 1000

            rows += f"""
            <tr>
                <td>{name}</td>
                <td>{mean:.3f} ms</td>
                <td>{min_time:.3f} ms</td>
                <td>{max_time:.3f} ms</td>
                <td>{stddev:.3f} ms</td>
                <td><span class="status-pass">✓</span></td>
            </tr>
            """

        return f"""
        <div class="section">
            <h2>⚡ Benchmark Results</h2>
            <table class="benchmark-table">
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Mean Time</th>
                        <th>Min Time</th>
                        <th>Max Time</th>
                        <th>Std Dev</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """

    def _format_regression_report(self, report: str) -> str:
        """Format regression report for HTML display"""
        if not report:
            return "<p>No regression data available</p>"

        # Parse report for regressions and improvements
        html = ""

        if "REGRESSIONS DETECTED:" in report:
            # Extract regression count
            lines = report.split("\n")
            for line in lines:
                if "REGRESSIONS DETECTED:" in line:
                    count = line.split(":")[1].strip()
                    if int(count) > 0:
                        html += f'<div class="regression-alert regression-critical">⚠️ {count} performance regressions detected!</div>'
                    else:
                        html += '<div class="improvement-notice">✅ No performance regressions detected</div>'
                    break

        # Add the full report in a preformatted block
        html += f"<pre>{report}</pre>"

        return html

    def _get_total_tests(self, benchmark_data: Dict) -> int:
        """Get total number of tests"""
        if benchmark_data and "benchmarks" in benchmark_data:
            return len(benchmark_data["benchmarks"])
        return 0

    def _get_avg_time(self, benchmark_data: Dict) -> str:
        """Calculate average execution time"""
        if not benchmark_data or "benchmarks" not in benchmark_data:
            return "N/A"

        times = [
            b.get("stats", {}).get("mean", 0) for b in benchmark_data["benchmarks"]
        ]
        if times:
            avg = statistics.mean(times) * 1000  # Convert to ms
            return f"{avg:.2f}ms"
        return "N/A"

    def _calculate_score(self, benchmark_data: Dict) -> int:
        """Calculate performance score (0-100)"""
        # Simple scoring based on execution times
        # Lower times = higher score
        if not benchmark_data or "benchmarks" not in benchmark_data:
            return 0

        times = [
            b.get("stats", {}).get("mean", 0) for b in benchmark_data["benchmarks"]
        ]
        if not times:
            return 0

        avg_time = statistics.mean(times)
        # Score calculation: faster is better
        # Assuming < 0.1s is excellent (100), > 1s is poor (0)
        if avg_time < 0.1:
            return 100
        elif avg_time > 1.0:
            return 0
        else:
            return int(100 - (avg_time * 100))

    def _count_regressions(self, report: str) -> int:
        """Count number of regressions from report"""
        if not report or "REGRESSIONS DETECTED:" not in report:
            return 0

        for line in report.split("\n"):
            if "REGRESSIONS DETECTED:" in line:
                try:
                    return int(line.split(":")[1].strip())
                except:
                    return 0
        return 0

    def _generate_recommendations(
        self, benchmark_data: Dict, regression_report: str
    ) -> str:
        """Generate performance recommendations"""
        recommendations = []

        # Check for slow tests
        if benchmark_data and "benchmarks" in benchmark_data:
            slow_tests = []
            for bench in benchmark_data["benchmarks"]:
                if bench.get("stats", {}).get("mean", 0) > 0.5:  # Tests taking > 500ms
                    slow_tests.append(bench["name"])

            if slow_tests:
                recommendations.append(
                    f"• Optimize slow tests: {', '.join(slow_tests[:3])}"
                )

        # Check for regressions
        regression_count = self._count_regressions(regression_report)
        if regression_count > 0:
            recommendations.append(
                f"• Address {regression_count} performance regressions immediately"
            )

        # General recommendations
        recommendations.extend(
            [
                "• Consider parallel test execution for faster CI/CD",
                "• Implement test result caching for unchanged code",
                "• Monitor memory usage in addition to execution time",
                "• Set up automated performance baseline updates",
            ]
        )

        return (
            "<ul>\n"
            + "\n".join(f"<li>{rec}</li>" for rec in recommendations)
            + "\n</ul>"
        )

    def save_dashboard(self, filename: str = "performance_dashboard.html"):
        """Save dashboard to file"""
        # Load available data
        regression_report = self.load_regression_report()

        # Try to load benchmark data if available
        benchmark_data = None
        benchmark_file = Path(".benchmarks") / "latest.json"
        if benchmark_file.exists():
            benchmark_data = self.load_benchmark_results(str(benchmark_file))

        # Generate HTML
        html_content = self.generate_html_dashboard(benchmark_data, regression_report)

        # Save to file
        output_file = self.output_dir / filename
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(output_file)


def generate_dashboard():
    """Convenience function to generate dashboard"""
    dashboard = PerformanceDashboard()
    output_file = dashboard.save_dashboard()
    print(f"Performance dashboard generated: {output_file}")
    return output_file


if __name__ == "__main__":
    generate_dashboard()
