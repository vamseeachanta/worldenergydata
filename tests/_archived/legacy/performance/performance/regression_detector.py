"""
Performance Regression Detection System
Detects performance regressions in test execution and module operations
"""

import json
import os
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import warnings


class PerformanceRegressionDetector:
    """Detects performance regressions by comparing current metrics with historical baselines"""
    
    def __init__(self, baseline_path: str = "tests/performance/baselines", 
                 threshold_percent: float = 20.0):
        """
        Initialize regression detector
        
        Args:
            baseline_path: Path to store performance baselines
            threshold_percent: Percentage increase that triggers regression alert
        """
        self.baseline_path = Path(baseline_path)
        self.baseline_path.mkdir(parents=True, exist_ok=True)
        self.threshold_percent = threshold_percent
        self.current_metrics = {}
        self.baselines = {}
        
    def load_baselines(self, module: str = "all") -> Dict:
        """Load performance baselines from file"""
        baseline_file = self.baseline_path / f"{module}_baseline.json"
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                self.baselines = json.load(f)
        return self.baselines
    
    def save_baselines(self, module: str = "all"):
        """Save current metrics as new baselines"""
        baseline_file = self.baseline_path / f"{module}_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump(self.baselines, f, indent=2)
    
    def record_metric(self, test_name: str, execution_time: float, 
                      memory_usage: Optional[float] = None):
        """Record a performance metric for comparison"""
        if test_name not in self.current_metrics:
            self.current_metrics[test_name] = {
                'execution_times': [],
                'memory_usage': []
            }
        
        self.current_metrics[test_name]['execution_times'].append(execution_time)
        if memory_usage:
            self.current_metrics[test_name]['memory_usage'].append(memory_usage)
    
    def detect_regression(self, test_name: str) -> Tuple[bool, Dict]:
        """
        Detect if current performance shows regression
        
        Returns:
            Tuple of (has_regression, details_dict)
        """
        if test_name not in self.current_metrics:
            return False, {"error": "No current metrics for test"}
        
        if test_name not in self.baselines:
            return False, {"warning": "No baseline for comparison"}
        
        current = self.current_metrics[test_name]
        baseline = self.baselines[test_name]
        
        # Calculate averages
        current_avg_time = statistics.mean(current['execution_times'])
        baseline_avg_time = baseline.get('avg_execution_time', 0)
        
        if baseline_avg_time == 0:
            return False, {"warning": "Invalid baseline"}
        
        # Calculate percentage change
        percent_change = ((current_avg_time - baseline_avg_time) / baseline_avg_time) * 100
        
        has_regression = percent_change > self.threshold_percent
        
        details = {
            'current_avg_time': current_avg_time,
            'baseline_avg_time': baseline_avg_time,
            'percent_change': percent_change,
            'threshold': self.threshold_percent,
            'has_regression': has_regression
        }
        
        if current['memory_usage'] and baseline.get('avg_memory_usage'):
            current_avg_mem = statistics.mean(current['memory_usage'])
            baseline_avg_mem = baseline['avg_memory_usage']
            mem_percent_change = ((current_avg_mem - baseline_avg_mem) / baseline_avg_mem) * 100
            details['memory_percent_change'] = mem_percent_change
            details['has_memory_regression'] = mem_percent_change > self.threshold_percent
        
        return has_regression, details
    
    def analyze_all_tests(self) -> Dict:
        """Analyze all recorded tests for regressions"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.current_metrics),
            'regressions': [],
            'improvements': [],
            'stable': []
        }
        
        for test_name in self.current_metrics:
            has_regression, details = self.detect_regression(test_name)
            
            if 'error' in details or 'warning' in details:
                continue
                
            test_result = {
                'test': test_name,
                'details': details
            }
            
            if has_regression:
                results['regressions'].append(test_result)
            elif details['percent_change'] < -10:  # 10% improvement
                results['improvements'].append(test_result)
            else:
                results['stable'].append(test_result)
        
        return results
    
    def update_baselines_smart(self):
        """Update baselines only for improved or stable tests"""
        for test_name in self.current_metrics:
            current = self.current_metrics[test_name]
            
            # Check if we have existing baseline
            if test_name in self.baselines:
                has_regression, details = self.detect_regression(test_name)
                # Skip if regression detected
                if has_regression:
                    continue
            
            # Update or create baseline
            self.baselines[test_name] = {
                'avg_execution_time': statistics.mean(current['execution_times']),
                'std_execution_time': statistics.stdev(current['execution_times']) if len(current['execution_times']) > 1 else 0,
                'sample_count': len(current['execution_times']),
                'last_updated': datetime.now().isoformat()
            }
            
            if current['memory_usage']:
                self.baselines[test_name]['avg_memory_usage'] = statistics.mean(current['memory_usage'])
    
    def generate_report(self) -> str:
        """Generate a regression detection report"""
        analysis = self.analyze_all_tests()
        
        report = f"""
Performance Regression Detection Report
======================================
Generated: {analysis['timestamp']}
Total Tests Analyzed: {analysis['total_tests']}

REGRESSIONS DETECTED: {len(analysis['regressions'])}
{'='*50}
"""
        
        if analysis['regressions']:
            for reg in analysis['regressions']:
                report += f"\n❌ {reg['test']}\n"
                report += f"   Current: {reg['details']['current_avg_time']:.4f}s\n"
                report += f"   Baseline: {reg['details']['baseline_avg_time']:.4f}s\n"
                report += f"   Change: +{reg['details']['percent_change']:.1f}%\n"
        
        report += f"\n\nIMPROVEMENTS: {len(analysis['improvements'])}\n"
        report += "="*50 + "\n"
        
        if analysis['improvements']:
            for imp in analysis['improvements']:
                report += f"\n✅ {imp['test']}\n"
                report += f"   Change: {imp['details']['percent_change']:.1f}%\n"
        
        report += f"\n\nSTABLE: {len(analysis['stable'])} tests\n"
        
        return report


class RegressionMonitor:
    """Monitor for continuous regression detection during test runs"""
    
    def __init__(self, detector: PerformanceRegressionDetector):
        self.detector = detector
        self.start_times = {}
    
    def start_test(self, test_name: str):
        """Mark test start time"""
        self.start_times[test_name] = datetime.now()
    
    def end_test(self, test_name: str, memory_usage: Optional[float] = None):
        """Mark test end and check for regression"""
        if test_name not in self.start_times:
            warnings.warn(f"Test {test_name} was not started")
            return
        
        execution_time = (datetime.now() - self.start_times[test_name]).total_seconds()
        self.detector.record_metric(test_name, execution_time, memory_usage)
        
        # Check for immediate regression
        has_regression, details = self.detector.detect_regression(test_name)
        if has_regression:
            warnings.warn(
                f"Performance regression detected in {test_name}: "
                f"+{details['percent_change']:.1f}% slower than baseline"
            )
        
        del self.start_times[test_name]
    
    def pytest_fixture(self):
        """Pytest fixture for easy integration"""
        import pytest
        
        @pytest.fixture
        def regression_monitor():
            return self
        
        return regression_monitor


# Pytest plugin integration
def pytest_configure(config):
    """Configure pytest with regression detection"""
    detector = PerformanceRegressionDetector()
    detector.load_baselines()
    config.regression_detector = detector
    config.regression_monitor = RegressionMonitor(detector)


def pytest_runtest_setup(item):
    """Start monitoring test"""
    if hasattr(item.config, 'regression_monitor'):
        item.config.regression_monitor.start_test(item.nodeid)


def pytest_runtest_teardown(item):
    """End monitoring and check for regression"""
    if hasattr(item.config, 'regression_monitor'):
        item.config.regression_monitor.end_test(item.nodeid)


def pytest_sessionfinish(session):
    """Generate regression report at end of session"""
    if hasattr(session.config, 'regression_detector'):
        detector = session.config.regression_detector
        report = detector.generate_report()
        print(report)
        
        # Save report to file
        report_path = Path("tests/performance/regression_report.txt")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Update baselines for non-regression tests
        detector.update_baselines_smart()
        detector.save_baselines()