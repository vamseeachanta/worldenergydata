#!/usr/bin/env python
"""
Demo script for test performance tracking system.
"""

import sys
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from worldenergydata.testing.performance.database import PerformanceDatabase, TestExecutionRecord
from worldenergydata.testing.performance.analyzer import PerformanceAnalyzer
from worldenergydata.testing.performance.reporter import PerformanceReporter


def create_sample_data(db: PerformanceDatabase):
    """Create sample test execution data for demo."""
    print("Creating sample test execution data...")
    
    # Define test scenarios
    tests = [
        {"name": "test_bsee_production_processing", "base_duration": 2.5, "module": "tests/test_bsee.py"},
        {"name": "test_well_data_validation", "base_duration": 1.2, "module": "tests/test_bsee.py"},
        {"name": "test_npv_calculation", "base_duration": 0.8, "module": "tests/test_financial.py"},
        {"name": "test_data_import", "base_duration": 3.0, "module": "tests/test_import.py"},
        {"name": "test_export_csv", "base_duration": 0.5, "module": "tests/test_export.py"},
        {"name": "test_wind_data_processing", "base_duration": 1.8, "module": "tests/test_wind.py"},
        {"name": "test_validation_framework", "base_duration": 0.3, "module": "tests/test_validation.py"},
        {"name": "test_performance_tracking", "base_duration": 0.2, "module": "tests/test_performance.py"},
    ]
    
    # Generate historical data for last 14 days
    for day_offset in range(14, -1, -1):
        timestamp = datetime.now() - timedelta(days=day_offset)
        
        for test in tests:
            # Add some variation
            import random
            
            # Simulate multiple runs per day
            for run in range(random.randint(1, 3)):
                duration = test["base_duration"] * random.uniform(0.8, 1.2)
                
                # Introduce regression in one test
                if test["name"] == "test_data_import" and day_offset < 3:
                    duration *= 2.5  # Performance regression!
                
                # Random failures
                status = "passed" if random.random() > 0.05 else "failed"
                
                record = TestExecutionRecord(
                    test_name=test["name"],
                    module=test["module"],
                    duration=duration,
                    status=status,
                    timestamp=timestamp + timedelta(hours=run * 8),
                    memory_usage=random.uniform(50, 200),
                    cpu_usage=random.uniform(10, 50)
                )
                
                db.record_execution(record)
    
    print(f"✅ Created sample data for {len(tests)} tests over 14 days")


def demo_performance_analysis():
    """Demonstrate performance tracking capabilities."""
    print("\n" + "="*80)
    print("TEST PERFORMANCE TRACKING SYSTEM DEMONSTRATION")
    print("="*80)
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "demo_performance.db"
        db = PerformanceDatabase(db_path)
        
        # Create sample data
        create_sample_data(db)
        
        # Initialize analyzer and reporter
        analyzer = PerformanceAnalyzer(db)
        reporter = PerformanceReporter(db)
        
        # 1. Show performance trends
        print("\n📈 PERFORMANCE TRENDS (Last 7 Days)")
        print("-" * 40)
        
        trends = analyzer.analyze_trends(days=7)
        if trends['status'] == 'analyzed':
            print(f"Total tests run: {trends['total_tests_run']:,}")
            print(f"Average test duration: {trends['avg_test_duration']:.3f}s")
            print(f"Duration trend: {trends['duration_trend']} ({trends['duration_trend_rate']:.4f}s/day)")
            print(f"Recent performance change: {trends['recent_performance_change']:+.1f}%")
        
        # 2. Show slowest tests
        print("\n🐌 SLOWEST TESTS")
        print("-" * 40)
        
        slow_tests = db.get_slowest_tests(limit=5)
        for idx, row in slow_tests.iterrows():
            print(f"{idx + 1}. {row['test_name']}")
            print(f"   Avg: {row['avg_duration']:.3f}s | Max: {row['max_duration']:.3f}s")
        
        # 3. Detect regressions
        print("\n⚠️  PERFORMANCE REGRESSIONS")
        print("-" * 40)
        
        regressions = analyzer.detect_regressions(lookback_days=7)
        if regressions:
            for reg in regressions[:3]:
                print(f"• {reg['test_name']}")
                print(f"  Recent: {reg['recent_avg']:.3f}s | Historical: {reg['historical_avg']:.3f}s")
                print(f"  Regression: {reg['regression_factor']:.2f}x slower")
        else:
            print("No regressions detected")
        
        # 4. Test stability analysis
        print("\n🎯 TEST STABILITY ANALYSIS")
        print("-" * 40)
        
        test_name = "test_npv_calculation"
        stability = analyzer.analyze_test_stability(test_name)
        
        if stability['status'] == 'analyzed':
            print(f"Test: {test_name}")
            print(f"Stability score: {stability['stability_score']:.1f}/100")
            print(f"Average duration: {stability['avg_duration']:.3f}s ± {stability['std_duration']:.3f}s")
            print(f"Failure rate: {stability['failure_rate']:.1f}%")
            print(f"Recent trend: {stability['recent_trend']}")
        
        # 5. Parallelization analysis
        print("\n⚡ PARALLELIZATION ANALYSIS")
        print("-" * 40)
        
        for workers in [1, 2, 4, 8]:
            parallel = analyzer.calculate_parallel_efficiency(num_workers=workers)
            if parallel['status'] == 'calculated':
                print(f"{workers} workers: {parallel['parallel_execution_time']:.1f}s "
                      f"(speedup: {parallel['speedup_factor']:.2f}x, "
                      f"efficiency: {parallel['efficiency_percentage']:.0f}%)")
        
        # 6. Optimization recommendations
        print("\n💡 OPTIMIZATION RECOMMENDATIONS")
        print("-" * 40)
        
        recommendations = analyzer.get_optimization_recommendations()
        for idx, rec in enumerate(recommendations[:3], 1):
            print(f"{idx}. [{rec['priority'].upper()}] {rec['title']}")
            print(f"   {rec['description']}")
            if 'potential_time_saved' in rec:
                print(f"   Potential time saved: {rec['potential_time_saved']:.1f}s")
        
        # 7. Generate sample report
        print("\n📊 GENERATING PERFORMANCE REPORT")
        print("-" * 40)
        
        # Save text report
        text_report_path = Path(tmpdir) / "performance_report.txt"
        reporter.save_report(text_report_path, format='text', days=7)
        print(f"✅ Text report saved to: {text_report_path}")
        
        # Save HTML report
        html_report_path = Path(tmpdir) / "performance_report.html"
        reporter.save_report(html_report_path, format='html', days=7)
        print(f"✅ HTML report saved to: {html_report_path}")
        
        # Save JSON report
        json_report_path = Path(tmpdir) / "performance_report.json"
        reporter.save_report(json_report_path, format='json', days=7)
        print(f"✅ JSON report saved to: {json_report_path}")
        
        # Show summary statistics
        print("\n📈 DATABASE STATISTICS")
        print("-" * 40)
        
        stats = db.get_test_statistics()
        print(f"Total unique tests: {len(stats)}")
        print(f"Total test executions: {stats['total_runs'].sum()}")
        print(f"Overall success rate: {stats['success_rate'].mean():.1f}%")
        print(f"Total test duration: {stats['avg_duration'].sum():.1f}s")


def demo_cli_usage():
    """Show CLI usage examples."""
    print("\n" + "="*80)
    print("CLI USAGE EXAMPLES")
    print("="*80)
    
    print("""
The performance tracking system includes a comprehensive CLI:

# Generate performance report
python -m worldenergydata.testing.performance.cli report --days 7

# Show slowest tests
python -m worldenergydata.testing.performance.cli slowest --limit 10

# Detect regressions
python -m worldenergydata.testing.performance.cli regressions --days 7

# Analyze specific test
python -m worldenergydata.testing.performance.cli analyze test_name

# Check parallelization efficiency
python -m worldenergydata.testing.performance.cli parallel --workers 4

# Generate interactive dashboard
python -m worldenergydata.testing.performance.cli dashboard --output dashboard.html

# Get optimization recommendations
python -m worldenergydata.testing.performance.cli recommendations

# Clean old records
python -m worldenergydata.testing.performance.cli cleanup --days 90
""")


def demo_pytest_integration():
    """Show pytest integration."""
    print("\n" + "="*80)
    print("PYTEST INTEGRATION")
    print("="*80)
    
    print("""
The performance tracking is automatically integrated with pytest:

1. Performance tracking is enabled by default via conftest.py
2. All test executions are automatically recorded
3. Performance summary is shown after test runs
4. Regressions are detected and reported

Example pytest run with performance tracking:

    pytest tests/ -v
    
    ============================================================
    Test Performance Summary
    ============================================================
    Total Tests: 156
    Total Duration: 45.23s
    Average Duration: 0.290s
    Success Rate: 98.7%
    
    ⚠️  Performance Regressions Detected:
      - test_data_import: 2.5x slower
    ============================================================

Custom markers are available:
    
    @pytest.mark.slow        # Mark slow tests
    @pytest.mark.performance # Mark for performance tracking
    @pytest.mark.benchmark   # Mark benchmark tests
    
Run specific test categories:
    
    pytest -m "not slow"     # Skip slow tests
    pytest -m performance    # Run only performance tests
""")


if __name__ == "__main__":
    print("\n" + "*"*80)
    print("TEST PERFORMANCE TRACKING SYSTEM - COMPREHENSIVE DEMO")
    print("*"*80)
    
    # Run demonstrations
    demo_performance_analysis()
    demo_cli_usage()
    demo_pytest_integration()
    
    print("\n" + "*"*80)
    print("DEMONSTRATION COMPLETE")
    print("*"*80)
    
    print("""
✅ The test performance tracking system is now fully operational!

Key Features:
- Automatic pytest integration
- Performance regression detection
- Interactive dashboards
- Parallelization analysis
- CLI tools for analysis
- Multi-format reporting

Next steps:
1. Run your tests to start collecting performance data
2. Use the CLI tools to analyze results
3. Generate dashboards for visualization
4. Set up CI/CD integration (Task 8)
""")