"""
Command-line interface for test performance tracking.
"""

import click
from pathlib import Path
from datetime import datetime
from .database import PerformanceDatabase
from .analyzer import PerformanceAnalyzer
from .reporter import PerformanceReporter
from .dashboard import PerformanceDashboard


@click.group()
def cli():
    """Test performance tracking CLI."""
    pass


@cli.command()
@click.option('--days', default=7, help='Number of days to analyze')
@click.option('--format', type=click.Choice(['text', 'json', 'html']), default='text')
@click.option('--output', type=click.Path(), help='Output file path')
def report(days, format, output):
    """Generate performance report."""
    db = PerformanceDatabase()
    reporter = PerformanceReporter(db)
    
    if output:
        output_path = Path(output)
        reporter.save_report(output_path, format=format, days=days)
        click.echo(f"Report saved to {output_path}")
    else:
        if format == 'text':
            click.echo(reporter.generate_text_report(days))
        elif format == 'json':
            import json
            report_data = reporter.generate_json_report(days)
            click.echo(json.dumps(report_data, indent=2, default=str))
        elif format == 'html':
            click.echo(reporter.generate_html_report(days))


@cli.command()
@click.option('--limit', default=10, help='Number of tests to show')
@click.option('--days', help='Time window in days')
def slowest(limit, days):
    """Show slowest tests."""
    db = PerformanceDatabase()
    
    slow_tests = db.get_slowest_tests(limit=limit, time_window=days)
    
    if slow_tests.empty:
        click.echo("No test execution data available")
        return
    
    click.echo("Slowest Tests:")
    click.echo("-" * 80)
    
    for idx, row in slow_tests.iterrows():
        click.echo(f"{idx + 1}. {row['test_name'][:60]}")
        click.echo(f"   Avg: {row['avg_duration']:.3f}s | Max: {row['max_duration']:.3f}s | Runs: {row['execution_count']}")


@cli.command()
@click.option('--threshold', default=2.0, help='Standard deviations for regression detection')
@click.option('--days', default=7, help='Lookback period in days')
def regressions(threshold, days):
    """Detect performance regressions."""
    db = PerformanceDatabase()
    analyzer = PerformanceAnalyzer(db)
    
    regressions = analyzer.detect_regressions(threshold_std=threshold, lookback_days=days)
    
    if not regressions:
        click.echo("No performance regressions detected")
        return
    
    click.echo(f"Performance Regressions (>{threshold} std devs):")
    click.echo("-" * 80)
    
    for idx, reg in enumerate(regressions, 1):
        click.echo(f"{idx}. {reg['test_name'][:60]}")
        click.echo(f"   Recent: {reg['recent_avg']:.3f}s | Historical: {reg['historical_avg']:.3f}s")
        click.echo(f"   Regression: {reg['regression_factor']:.2f}x slower ({reg['std_deviations']:.1f} std devs)")


@cli.command()
@click.argument('test_name')
def analyze(test_name):
    """Analyze specific test stability."""
    db = PerformanceDatabase()
    analyzer = PerformanceAnalyzer(db)
    
    result = analyzer.analyze_test_stability(test_name)
    
    if result['status'] == 'no_data':
        click.echo(f"No data available for test: {test_name}")
        return
    
    click.echo(f"Stability Analysis: {test_name}")
    click.echo("-" * 80)
    click.echo(f"Total runs: {result.get('total_runs', 0)}")
    click.echo(f"Average duration: {result.get('avg_duration', 0):.3f}s")
    click.echo(f"Standard deviation: {result.get('std_duration', 0):.3f}s")
    click.echo(f"Min/Max: {result.get('min_duration', 0):.3f}s / {result.get('max_duration', 0):.3f}s")
    click.echo(f"Stability score: {result.get('stability_score', 0):.1f}/100")
    click.echo(f"Failure rate: {result.get('failure_rate', 0):.1f}%")
    click.echo(f"Recent trend: {result.get('recent_trend', 'unknown')}")


@cli.command()
@click.option('--workers', default=4, help='Number of parallel workers')
def parallel(workers):
    """Analyze parallelization efficiency."""
    db = PerformanceDatabase()
    analyzer = PerformanceAnalyzer(db)
    
    result = analyzer.calculate_parallel_efficiency(num_workers=workers)
    
    if result['status'] != 'calculated':
        click.echo("Insufficient data for parallelization analysis")
        return
    
    click.echo(f"Parallelization Analysis ({workers} workers):")
    click.echo("-" * 80)
    click.echo(f"Serial execution time: {result['serial_execution_time']:.1f}s")
    click.echo(f"Parallel execution time: {result['parallel_execution_time']:.1f}s")
    click.echo(f"Speedup factor: {result['speedup_factor']:.2f}x")
    click.echo(f"Efficiency: {result['efficiency_percentage']:.1f}%")
    click.echo(f"Time saved: {result['time_saved']:.1f}s")
    click.echo(f"Load balance ratio: {result['load_balance_ratio']:.2f}")


@cli.command()
@click.option('--output', type=click.Path(), default='performance_dashboard.html')
def dashboard(output):
    """Generate interactive dashboard."""
    db = PerformanceDatabase()
    dashboard = PerformanceDashboard(db)
    
    output_path = Path(output)
    dashboard.generate_dashboard(output_path)
    
    click.echo(f"Dashboard generated: {output_path}")
    click.echo(f"Open in browser: file://{output_path.absolute()}")


@cli.command()
@click.option('--days', default=90, help='Days of history to keep')
def cleanup(days):
    """Clean up old performance records."""
    db = PerformanceDatabase()
    
    click.echo(f"Cleaning up records older than {days} days...")
    db.cleanup_old_records(days)
    click.echo("Cleanup complete")


@cli.command()
def recommendations():
    """Get optimization recommendations."""
    db = PerformanceDatabase()
    analyzer = PerformanceAnalyzer(db)
    
    recommendations = analyzer.get_optimization_recommendations()
    
    if not recommendations:
        click.echo("No optimization recommendations at this time")
        return
    
    click.echo("Optimization Recommendations:")
    click.echo("-" * 80)
    
    for idx, rec in enumerate(recommendations, 1):
        priority_color = {
            'high': 'red',
            'medium': 'yellow',
            'low': 'green'
        }.get(rec['priority'], 'white')
        
        click.secho(f"{idx}. [{rec['priority'].upper()}] {rec['title']}", fg=priority_color)
        click.echo(f"   {rec['description']}")
        
        if 'tests' in rec and rec['tests']:
            click.echo(f"   Affected tests: {', '.join(rec['tests'][:3])}")
        
        if 'potential_time_saved' in rec:
            click.echo(f"   Potential time saved: {rec['potential_time_saved']:.1f}s")
        
        if 'impact' in rec:
            click.echo(f"   Impact: {rec['impact']}")


if __name__ == '__main__':
    cli()