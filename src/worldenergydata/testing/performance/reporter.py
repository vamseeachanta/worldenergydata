"""
Performance reporting for test execution metrics.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
from .database import PerformanceDatabase
from .analyzer import PerformanceAnalyzer


class PerformanceReporter:
    """Generate performance reports for test executions."""
    
    def __init__(self, db: Optional[PerformanceDatabase] = None):
        """
        Initialize performance reporter.
        
        Args:
            db: Performance database instance
        """
        self.db = db or PerformanceDatabase()
        self.analyzer = PerformanceAnalyzer(self.db)
    
    def generate_text_report(self, days: int = 7) -> str:
        """
        Generate a text-based performance report.
        
        Args:
            days: Number of days to include in report
            
        Returns:
            Formatted text report
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("TEST PERFORMANCE REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Period: Last {days} days")
        lines.append("=" * 80)
        lines.append("")
        
        # Overall trends
        trends = self.analyzer.analyze_trends(days)
        
        if trends['status'] == 'analyzed':
            lines.append("PERFORMANCE TRENDS")
            lines.append("-" * 40)
            lines.append(f"Total tests run: {trends['total_tests_run']:,}")
            lines.append(f"Average daily tests: {trends['avg_daily_tests']:.0f}")
            lines.append(f"Average test duration: {trends['avg_test_duration']:.3f}s")
            lines.append(f"Duration trend: {trends['duration_trend']} ({trends['duration_trend_rate']:.4f}s/day)")
            lines.append(f"Recent performance change: {trends['recent_performance_change']:+.1f}%")
            lines.append("")
        
        # Slowest tests
        lines.append("SLOWEST TESTS")
        lines.append("-" * 40)
        
        slow_tests = self.db.get_slowest_tests(limit=10, time_window=days)
        
        if not slow_tests.empty:
            for idx, row in slow_tests.iterrows():
                lines.append(f"{idx + 1}. {row['test_name'][:50]}")
                lines.append(f"   Avg: {row['avg_duration']:.3f}s | Max: {row['max_duration']:.3f}s | Runs: {row['execution_count']}")
        else:
            lines.append("No test execution data available")
        
        lines.append("")
        
        # Performance regressions
        lines.append("PERFORMANCE REGRESSIONS")
        lines.append("-" * 40)
        
        regressions = self.analyzer.detect_regressions(lookback_days=days)
        
        if regressions:
            for idx, reg in enumerate(regressions[:5], 1):
                lines.append(f"{idx}. {reg['test_name'][:50]}")
                lines.append(f"   Recent: {reg['recent_avg']:.3f}s | Historical: {reg['historical_avg']:.3f}s")
                lines.append(f"   Regression: {reg['regression_factor']:.2f}x slower")
        else:
            lines.append("No performance regressions detected")
        
        lines.append("")
        
        # Optimization recommendations
        lines.append("OPTIMIZATION RECOMMENDATIONS")
        lines.append("-" * 40)
        
        recommendations = self.analyzer.get_optimization_recommendations()
        
        if recommendations:
            for idx, rec in enumerate(recommendations[:3], 1):
                lines.append(f"{idx}. [{rec['priority'].upper()}] {rec['title']}")
                lines.append(f"   {rec['description']}")
                if 'potential_time_saved' in rec:
                    lines.append(f"   Potential time saved: {rec['potential_time_saved']:.1f}s")
        else:
            lines.append("No specific optimization recommendations at this time")
        
        lines.append("")
        
        # Parallelization analysis
        lines.append("PARALLELIZATION ANALYSIS")
        lines.append("-" * 40)
        
        parallel = self.analyzer.calculate_parallel_efficiency(num_workers=4)
        
        if parallel['status'] == 'calculated':
            lines.append(f"Serial execution time: {parallel['serial_execution_time']:.1f}s")
            lines.append(f"Parallel execution time (4 workers): {parallel['parallel_execution_time']:.1f}s")
            lines.append(f"Speedup factor: {parallel['speedup_factor']:.2f}x")
            lines.append(f"Efficiency: {parallel['efficiency_percentage']:.1f}%")
            lines.append(f"Time saved: {parallel['time_saved']:.1f}s")
        else:
            lines.append("Insufficient data for parallelization analysis")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def generate_json_report(self, days: int = 7) -> Dict[str, Any]:
        """
        Generate a JSON-formatted performance report.
        
        Args:
            days: Number of days to include in report
            
        Returns:
            Dictionary with report data
        """
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'period_days': days,
                'report_version': '1.0.0'
            }
        }
        
        # Trends
        report['trends'] = self.analyzer.analyze_trends(days)
        
        # Slowest tests
        slow_tests = self.db.get_slowest_tests(limit=10, time_window=days)
        report['slowest_tests'] = slow_tests.to_dict('records') if not slow_tests.empty else []
        
        # Regressions
        report['regressions'] = self.analyzer.detect_regressions(lookback_days=days)
        
        # Statistics
        stats = self.db.get_test_statistics()
        
        if not stats.empty:
            report['statistics'] = {
                'total_unique_tests': len(stats),
                'total_executions': int(stats['total_runs'].sum()),
                'overall_success_rate': float(stats['success_rate'].mean()),
                'total_duration': float(stats['avg_duration'].sum())
            }
        else:
            report['statistics'] = {}
        
        # Recommendations
        report['recommendations'] = self.analyzer.get_optimization_recommendations()
        
        # Parallelization
        report['parallelization'] = self.analyzer.calculate_parallel_efficiency(num_workers=4)
        
        return report
    
    def generate_html_report(self, days: int = 7) -> str:
        """
        Generate an HTML performance report.
        
        Args:
            days: Number of days to include in report
            
        Returns:
            HTML report content
        """
        data = self.generate_json_report(days)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Performance Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 4px;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .recommendation {{
            background-color: #d1ecf1;
            border: 1px solid #17a2b8;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .priority-high {{
            color: #dc3545;
            font-weight: bold;
        }}
        .priority-medium {{
            color: #ffc107;
            font-weight: bold;
        }}
        .priority-low {{
            color: #28a745;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Performance Report</h1>
        <p>Generated: {data['metadata']['generated_at']}</p>
        <p>Period: Last {data['metadata']['period_days']} days</p>
        
        <h2>Performance Overview</h2>
        <div>
"""
        
        if data.get('statistics'):
            stats = data['statistics']
            html += f"""
            <div class="metric">
                <div class="metric-label">Total Tests</div>
                <div class="metric-value">{stats.get('total_unique_tests', 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Executions</div>
                <div class="metric-value">{stats.get('total_executions', 0):,}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">{stats.get('overall_success_rate', 0):.1f}%</div>
            </div>
"""
        
        if data.get('trends', {}).get('status') == 'analyzed':
            trends = data['trends']
            html += f"""
            <div class="metric">
                <div class="metric-label">Avg Duration</div>
                <div class="metric-value">{trends['avg_test_duration']:.3f}s</div>
            </div>
            <div class="metric">
                <div class="metric-label">Performance Change</div>
                <div class="metric-value">{trends['recent_performance_change']:+.1f}%</div>
            </div>
"""
        
        html += """
        </div>
        
        <h2>Slowest Tests</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Avg Duration (s)</th>
                <th>Max Duration (s)</th>
                <th>Executions</th>
            </tr>
"""
        
        for test in data.get('slowest_tests', [])[:10]:
            html += f"""
            <tr>
                <td>{test['test_name'][:60]}</td>
                <td>{test['avg_duration']:.3f}</td>
                <td>{test['max_duration']:.3f}</td>
                <td>{test['execution_count']}</td>
            </tr>
"""
        
        html += """
        </table>
"""
        
        if data.get('regressions'):
            html += """
        <h2>Performance Regressions</h2>
        <div class="warning">
            <strong>Warning:</strong> The following tests have shown performance degradation:
        </div>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Recent Avg (s)</th>
                <th>Historical Avg (s)</th>
                <th>Regression Factor</th>
            </tr>
"""
            for reg in data['regressions'][:5]:
                html += f"""
            <tr>
                <td>{reg['test_name'][:60]}</td>
                <td>{reg['recent_avg']:.3f}</td>
                <td>{reg['historical_avg']:.3f}</td>
                <td>{reg['regression_factor']:.2f}x</td>
            </tr>
"""
            html += """
        </table>
"""
        
        if data.get('recommendations'):
            html += """
        <h2>Optimization Recommendations</h2>
"""
            for rec in data['recommendations']:
                priority_class = f"priority-{rec['priority']}"
                html += f"""
        <div class="recommendation">
            <strong class="{priority_class}">[{rec['priority'].upper()}]</strong> {rec['title']}<br>
            {rec['description']}
"""
                if 'potential_time_saved' in rec:
                    html += f"<br>Potential time saved: {rec['potential_time_saved']:.1f}s"
                html += """
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html
    
    def save_report(self, output_path: Path, format: str = 'text', days: int = 7):
        """
        Save performance report to file.
        
        Args:
            output_path: Path to save report
            format: Report format ('text', 'json', 'html')
            days: Number of days to include
        """
        output_path = Path(output_path)
        
        if format == 'text':
            content = self.generate_text_report(days)
            output_path.write_text(content)
        elif format == 'json':
            content = self.generate_json_report(days)
            output_path.write_text(json.dumps(content, indent=2, default=str))
        elif format == 'html':
            content = self.generate_html_report(days)
            output_path.write_text(content)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def generate_weekly_report(self) -> str:
        """Generate weekly performance report."""
        return self.generate_text_report(days=7)
    
    def generate_monthly_report(self) -> str:
        """Generate monthly performance report."""
        return self.generate_text_report(days=30)