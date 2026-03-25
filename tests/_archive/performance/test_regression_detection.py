"""
Performance Regression Detection System

This module implements a comprehensive system for detecting and reporting
performance regressions in the WorldEnergyData codebase.
"""

import pytest
import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import statistics
import warnings

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class PerformanceBaseline:
    """Manage performance baselines for regression detection."""
    
    def __init__(self, baseline_file: Path = None):
        self.baseline_file = baseline_file or Path('tests/performance/baselines/baseline.json')
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.baselines = self.load_baselines()
        self.tolerance_levels = {
            'strict': 0.1,    # 10% tolerance
            'normal': 0.2,    # 20% tolerance
            'relaxed': 0.3    # 30% tolerance
        }
    
    def load_baselines(self) -> Dict:
        """Load existing baselines from file."""
        if self.baseline_file.exists():
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_baselines(self):
        """Save baselines to file."""
        with open(self.baseline_file, 'w') as f:
            json.dump(self.baselines, f, indent=2)
    
    def update_baseline(self, operation: str, metrics: Dict):
        """Update baseline for an operation."""
        self.baselines[operation] = {
            'metrics': metrics,
            'timestamp': datetime.now().isoformat(),
            'version': self._get_code_version()
        }
        self.save_baselines()
    
    def get_baseline(self, operation: str) -> Optional[Dict]:
        """Get baseline for an operation."""
        return self.baselines.get(operation)
    
    def _get_code_version(self) -> str:
        """Get current code version or commit hash."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()[:8]
        except:
            return 'unknown'


class RegressionDetector:
    """Detect performance regressions against baselines."""
    
    def __init__(self, baseline: PerformanceBaseline):
        self.baseline = baseline
        self.current_metrics = {}
        self.regressions = []
        self.improvements = []
    
    def measure_operation(self, operation: str, func: callable, *args, **kwargs) -> Tuple[any, Dict]:
        """Measure performance metrics for an operation."""
        import psutil
        import tracemalloc
        
        # Prepare measurement
        process = psutil.Process()
        tracemalloc.start()
        
        # Measure execution time
        start_time = time.perf_counter()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Collect metrics
        end_time = time.perf_counter()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        metrics = {
            'execution_time': end_time - start_time,
            'memory_delta': end_memory - start_memory,
            'peak_memory': peak / 1024 / 1024  # MB
        }
        
        self.current_metrics[operation] = metrics
        return result, metrics
    
    def check_regression(self, operation: str, metrics: Dict, 
                        tolerance: str = 'normal') -> Optional[Dict]:
        """Check if current metrics show regression against baseline."""
        baseline = self.baseline.get_baseline(operation)
        if not baseline:
            return None
        
        baseline_metrics = baseline['metrics']
        tolerance_value = self.baseline.tolerance_levels[tolerance]
        
        regression_info = {
            'operation': operation,
            'metrics': {}
        }
        
        has_regression = False
        
        for metric_name, current_value in metrics.items():
            baseline_value = baseline_metrics.get(metric_name)
            if baseline_value is None:
                continue
            
            # Calculate percentage change
            if baseline_value > 0:
                change = (current_value - baseline_value) / baseline_value
            else:
                change = 0
            
            if change > tolerance_value:
                has_regression = True
                regression_info['metrics'][metric_name] = {
                    'baseline': baseline_value,
                    'current': current_value,
                    'change_percent': change * 100,
                    'tolerance_percent': tolerance_value * 100
                }
            elif change < -tolerance_value:
                # Significant improvement
                if 'improvements' not in regression_info:
                    regression_info['improvements'] = {}
                regression_info['improvements'][metric_name] = {
                    'baseline': baseline_value,
                    'current': current_value,
                    'improvement_percent': abs(change) * 100
                }
        
        if has_regression:
            self.regressions.append(regression_info)
            return regression_info
        elif 'improvements' in regression_info:
            self.improvements.append(regression_info)
        
        return None
    
    def generate_report(self) -> str:
        """Generate a regression detection report."""
        report = []
        report.append("=" * 60)
        report.append("Performance Regression Detection Report")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        if self.regressions:
            report.append("⚠️  REGRESSIONS DETECTED:")
            report.append("-" * 40)
            for reg in self.regressions:
                report.append(f"\nOperation: {reg['operation']}")
                for metric, info in reg['metrics'].items():
                    report.append(f"  {metric}:")
                    report.append(f"    Baseline: {info['baseline']:.3f}")
                    report.append(f"    Current:  {info['current']:.3f}")
                    report.append(f"    Change:   +{info['change_percent']:.1f}% (tolerance: {info['tolerance_percent']:.0f}%)")
        else:
            report.append("✅ No regressions detected")
        
        if self.improvements:
            report.append("\n🎉 IMPROVEMENTS DETECTED:")
            report.append("-" * 40)
            for imp in self.improvements:
                report.append(f"\nOperation: {imp['operation']}")
                for metric, info in imp.get('improvements', {}).items():
                    report.append(f"  {metric}:")
                    report.append(f"    Improved by {info['improvement_percent']:.1f}%")
        
        report.append("\n" + "=" * 60)
        return "\n".join(report)


class TestRegressionDetection:
    """Test the regression detection system."""
    
    @pytest.fixture
    def baseline_manager(self, tmp_path):
        """Create a baseline manager for testing."""
        baseline_file = tmp_path / 'test_baseline.json'
        return PerformanceBaseline(baseline_file)
    
    @pytest.fixture
    def detector(self, baseline_manager):
        """Create a regression detector."""
        return RegressionDetector(baseline_manager)
    
    def test_baseline_creation(self, baseline_manager):
        """Test creating and updating baselines."""
        # Create initial baseline
        baseline_manager.update_baseline('test_operation', {
            'execution_time': 1.0,
            'memory_delta': 10.0,
            'peak_memory': 50.0
        })
        
        # Verify baseline was saved
        baseline = baseline_manager.get_baseline('test_operation')
        assert baseline is not None
        assert baseline['metrics']['execution_time'] == 1.0
        assert 'timestamp' in baseline
        assert 'version' in baseline
    
    def test_regression_detection(self, baseline_manager, detector):
        """Test detecting performance regressions."""
        # Set baseline
        baseline_manager.update_baseline('slow_operation', {
            'execution_time': 1.0,
            'memory_delta': 10.0
        })
        
        # Test with regression (30% slower)
        regression = detector.check_regression('slow_operation', {
            'execution_time': 1.3,
            'memory_delta': 10.0
        }, tolerance='normal')  # 20% tolerance
        
        assert regression is not None
        assert 'execution_time' in regression['metrics']
        assert regression['metrics']['execution_time']['change_percent'] == 30.0
        
        # Test without regression (15% slower, within tolerance)
        no_regression = detector.check_regression('slow_operation', {
            'execution_time': 1.15,
            'memory_delta': 10.0
        }, tolerance='normal')
        
        assert no_regression is None
    
    def test_improvement_detection(self, baseline_manager, detector):
        """Test detecting performance improvements."""
        # Set baseline
        baseline_manager.update_baseline('improved_operation', {
            'execution_time': 2.0,
            'memory_delta': 20.0
        })
        
        # Test with significant improvement (50% faster)
        detector.check_regression('improved_operation', {
            'execution_time': 1.0,
            'memory_delta': 10.0
        }, tolerance='normal')
        
        assert len(detector.improvements) > 0
        improvement = detector.improvements[0]
        assert 'improvements' in improvement
        assert 'execution_time' in improvement['improvements']
    
    def test_measure_operation(self, detector):
        """Test measuring operation performance."""
        
        def sample_operation(size: int):
            """Sample operation to measure."""
            data = np.random.randn(size)
            return np.mean(data)
        
        result, metrics = detector.measure_operation(
            'sample_op',
            sample_operation,
            10000
        )
        
        assert result is not None
        assert 'execution_time' in metrics
        assert 'memory_delta' in metrics
        assert 'peak_memory' in metrics
        assert metrics['execution_time'] > 0
    
    def test_report_generation(self, baseline_manager, detector):
        """Test generating regression report."""
        # Set baselines
        baseline_manager.update_baseline('op1', {'execution_time': 1.0})
        baseline_manager.update_baseline('op2', {'execution_time': 2.0})
        
        # Add regression
        detector.check_regression('op1', {'execution_time': 1.5})
        
        # Add improvement
        detector.check_regression('op2', {'execution_time': 1.0})
        
        # Generate report
        report = detector.generate_report()
        
        assert "REGRESSIONS DETECTED" in report
        assert "op1" in report
        assert "IMPROVEMENTS DETECTED" in report
        assert "op2" in report


class TestAutomatedRegressionMonitoring:
    """Test automated regression monitoring for CI/CD."""
    
    @pytest.mark.regression
    def test_critical_operations_regression(self):
        """Monitor critical operations for regressions."""
        baseline = PerformanceBaseline()
        detector = RegressionDetector(baseline)
        
        # Define critical operations to monitor
        critical_operations = [
            ('data_import', self._simulate_data_import),
            ('data_processing', self._simulate_data_processing),
            ('npv_calculation', self._simulate_npv_calculation),
            ('report_generation', self._simulate_report_generation)
        ]
        
        # Measure each operation
        for op_name, op_func in critical_operations:
            _, metrics = detector.measure_operation(op_name, op_func)
            
            # Check for regression
            regression = detector.check_regression(op_name, metrics, tolerance='strict')
            
            if regression:
                warnings.warn(
                    f"Performance regression detected in {op_name}: "
                    f"{json.dumps(regression['metrics'], indent=2)}"
                )
        
        # Generate and print report
        report = detector.generate_report()
        print("\n" + report)
        
        # Fail test if critical regressions detected
        critical_regressions = [
            r for r in detector.regressions 
            if r['operation'] in ['data_import', 'npv_calculation']
        ]
        
        if critical_regressions:
            pytest.fail(f"Critical performance regressions detected: {critical_regressions}")
    
    def _simulate_data_import(self):
        """Simulate data import operation."""
        df = pd.DataFrame(np.random.randn(10000, 10))
        return df
    
    def _simulate_data_processing(self):
        """Simulate data processing operation."""
        df = pd.DataFrame(np.random.randn(5000, 5))
        df['mean'] = df.mean(axis=1)
        df['std'] = df.std(axis=1)
        return df
    
    def _simulate_npv_calculation(self):
        """Simulate NPV calculation."""
        cash_flows = np.random.randn(100) * 1000
        discount_rate = 0.1
        periods = np.arange(len(cash_flows))
        npv = np.sum(cash_flows / (1 + discount_rate) ** periods)
        return npv
    
    def _simulate_report_generation(self):
        """Simulate report generation."""
        data = {
            'metrics': [np.random.randn() for _ in range(100)],
            'timestamps': pd.date_range('2020-01-01', periods=100)
        }
        report = pd.DataFrame(data)
        summary = report.describe()
        return summary


class TestHistoricalTrendAnalysis:
    """Analyze historical performance trends."""
    
    def test_trend_analysis(self, tmp_path):
        """Test analyzing performance trends over time."""
        # Create historical data
        history_dir = tmp_path / 'history'
        history_dir.mkdir()
        
        # Simulate historical performance data
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        
        for i, date in enumerate(dates):
            # Simulate gradual performance degradation
            metrics = {
                'execution_time': 1.0 + i * 0.01,  # Getting slower
                'memory_usage': 100 + i * 0.5       # Using more memory
            }
            
            file_path = history_dir / f"metrics_{date.strftime('%Y%m%d')}.json"
            with open(file_path, 'w') as f:
                json.dump({
                    'date': date.isoformat(),
                    'metrics': metrics
                }, f)
        
        # Analyze trends
        trend_data = []
        for file_path in sorted(history_dir.glob('metrics_*.json')):
            with open(file_path, 'r') as f:
                data = json.load(f)
                trend_data.append({
                    'date': pd.to_datetime(data['date']),
                    'execution_time': data['metrics']['execution_time'],
                    'memory_usage': data['metrics']['memory_usage']
                })
        
        df = pd.DataFrame(trend_data)
        
        # Calculate trend statistics
        exec_time_trend = np.polyfit(range(len(df)), df['execution_time'], 1)[0]
        memory_trend = np.polyfit(range(len(df)), df['memory_usage'], 1)[0]
        
        # Assert degradation is detected
        assert exec_time_trend > 0, "Execution time degradation not detected"
        assert memory_trend > 0, "Memory usage increase not detected"
        
        # Calculate degradation rate
        exec_degradation_rate = (df['execution_time'].iloc[-1] / df['execution_time'].iloc[0] - 1) * 100
        memory_degradation_rate = (df['memory_usage'].iloc[-1] / df['memory_usage'].iloc[0] - 1) * 100
        
        print(f"Execution time degraded by {exec_degradation_rate:.1f}% over period")
        print(f"Memory usage increased by {memory_degradation_rate:.1f}% over period")
        
        # Alert if degradation exceeds threshold
        if exec_degradation_rate > 20:
            warnings.warn(f"Significant performance degradation detected: {exec_degradation_rate:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "regression"])