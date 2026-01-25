#!/usr/bin/env python3
"""
Test Metrics Tracker for WorldEnergyData and All Repos

Tracks test coverage, pass rates, and metrics over time to enable rollback
if metrics degrade.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import os

class TestMetricsTracker:
    """Track test metrics for version control and rollback decisions."""
    
    def __init__(self, repo_path: Path = None):
        """Initialize tracker for a repository."""
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.metrics_dir = self.repo_path / 'tests' / '.metrics'
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / 'test_metrics_history.json'
        self.history = self.load_history()
        
    def load_history(self) -> List[Dict]:
        """Load historical metrics."""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_history(self):
        """Save metrics history."""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def run_tests_and_collect_metrics(self) -> Dict:
        """Run tests and collect comprehensive metrics."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'repo': str(self.repo_path),
            'git_commit': self.get_git_commit(),
            'git_branch': self.get_git_branch(),
        }
        
        # Set Python path
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.repo_path / 'src')
        
        # Count total tests
        print("Counting tests...")
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', 'tests/', '--co', '-q'],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                env=env,
                timeout=30
            )
            
            # Count test methods
            test_count = 0
            test_files = set()
            for line in result.stdout.split('\n'):
                if '::test_' in line:
                    test_count += 1
                    # Extract file name
                    if '::' in line:
                        file_part = line.split('::')[0]
                        if '.py' in file_part:
                            test_files.add(file_part)
            
            metrics['total_tests'] = test_count
            metrics['total_test_files'] = len(test_files)
            
        except Exception as e:
            print(f"Error counting tests: {e}")
            metrics['total_tests'] = 0
            metrics['total_test_files'] = 0
        
        # Run tests with coverage
        print("Running tests with coverage...")
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', 
                 'tests/', 
                 '--cov=src/worldenergydata',
                 '--cov-report=json',
                 '--cov-report=term',
                 '--tb=short',
                 '-q'],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                env=env,
                timeout=300  # 5 minutes
            )
            
            # Parse test results
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                # Look for test results
                if ' passed' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed':
                            try:
                                metrics['tests_passed'] = int(parts[i-1])
                            except:
                                pass
                                
                if ' failed' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'failed':
                            try:
                                metrics['tests_failed'] = int(parts[i-1])
                            except:
                                pass
                                
                if ' error' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'error' or part == 'errors':
                            try:
                                metrics['tests_errors'] = int(parts[i-1])
                            except:
                                pass
                
                # Look for coverage
                if 'TOTAL' in line and '%' in line:
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            try:
                                metrics['coverage_percent'] = float(part.replace('%', ''))
                                break
                            except:
                                pass
            
            # Default values if not found
            metrics.setdefault('tests_passed', 0)
            metrics.setdefault('tests_failed', 0)
            metrics.setdefault('tests_errors', 0)
            metrics.setdefault('coverage_percent', 0.0)
            
            # Calculate pass rate
            total_run = metrics['tests_passed'] + metrics['tests_failed'] + metrics['tests_errors']
            if total_run > 0:
                metrics['pass_rate'] = round((metrics['tests_passed'] / total_run) * 100, 2)
            else:
                metrics['pass_rate'] = 0.0
                
            # Load coverage.json if it exists
            coverage_file = self.repo_path / 'reports' / 'coverage' / 'coverage.json'
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                    if 'totals' in coverage_data:
                        metrics['coverage_lines'] = coverage_data['totals'].get('num_statements', 0)
                        metrics['coverage_covered'] = coverage_data['totals'].get('covered_lines', 0)
                        if metrics['coverage_lines'] > 0:
                            metrics['coverage_percent'] = round(
                                (metrics['coverage_covered'] / metrics['coverage_lines']) * 100, 2
                            )
            
        except subprocess.TimeoutExpired:
            print("Test run timed out")
            metrics['tests_passed'] = 0
            metrics['tests_failed'] = 0
            metrics['tests_errors'] = 0
            metrics['error'] = 'Test run timed out'
            
        except Exception as e:
            print(f"Error running tests: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    def get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()[:8]
        except:
            return 'unknown'
    
    def get_git_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()
        except:
            return 'unknown'
    
    def track_metrics(self) -> Dict:
        """Run tests and track metrics."""
        print(f"Tracking test metrics for: {self.repo_path}")
        print("=" * 60)
        
        metrics = self.run_tests_and_collect_metrics()
        
        # Add to history
        self.history.append(metrics)
        
        # Keep only last 100 runs
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        # Save history
        self.save_history()
        
        # Print summary
        self.print_summary(metrics)
        
        # Check for regression
        self.check_regression(metrics)
        
        return metrics
    
    def print_summary(self, metrics: Dict):
        """Print metrics summary."""
        print("\n📊 Test Metrics Summary")
        print("-" * 40)
        print(f"Repository: {metrics['repo']}")
        print(f"Timestamp: {metrics['timestamp']}")
        print(f"Git Commit: {metrics['git_commit']}")
        print(f"Git Branch: {metrics['git_branch']}")
        print()
        print(f"Total Tests: {metrics.get('total_tests', 0)}")
        print(f"Test Files: {metrics.get('total_test_files', 0)}")
        print(f"Tests Passed: {metrics.get('tests_passed', 0)}")
        print(f"Tests Failed: {metrics.get('tests_failed', 0)}")
        print(f"Tests Errors: {metrics.get('tests_errors', 0)}")
        print(f"Pass Rate: {metrics.get('pass_rate', 0):.1f}%")
        print(f"Coverage: {metrics.get('coverage_percent', 0):.1f}%")
        
        if 'error' in metrics:
            print(f"⚠️ Error: {metrics['error']}")
    
    def check_regression(self, current: Dict):
        """Check for test regression compared to previous run."""
        if len(self.history) < 2:
            return
        
        previous = self.history[-2]
        
        print("\n📈 Regression Check")
        print("-" * 40)
        
        warnings = []
        
        # Check pass rate
        if current.get('pass_rate', 0) < previous.get('pass_rate', 0) - 5:
            warnings.append(f"⚠️ Pass rate decreased: {previous.get('pass_rate', 0):.1f}% → {current.get('pass_rate', 0):.1f}%")
        
        # Check coverage
        if current.get('coverage_percent', 0) < previous.get('coverage_percent', 0) - 2:
            warnings.append(f"⚠️ Coverage decreased: {previous.get('coverage_percent', 0):.1f}% → {current.get('coverage_percent', 0):.1f}%")
        
        # Check test count
        if current.get('total_tests', 0) < previous.get('total_tests', 0) * 0.9:
            warnings.append(f"⚠️ Test count decreased: {previous.get('total_tests', 0)} → {current.get('total_tests', 0)}")
        
        if warnings:
            print("Regressions detected:")
            for warning in warnings:
                print(warning)
            print("\n🔄 Consider reverting recent changes if metrics don't improve")
        else:
            print("✅ No regressions detected")
    
    def get_trend(self, metric: str, last_n: int = 10) -> List[float]:
        """Get trend for a specific metric."""
        recent = self.history[-last_n:] if len(self.history) > last_n else self.history
        return [m.get(metric, 0) for m in recent]
    
    def print_trends(self):
        """Print metric trends."""
        if len(self.history) < 2:
            print("Not enough history for trends")
            return
        
        print("\n📈 Metric Trends (last 10 runs)")
        print("-" * 40)
        
        # Coverage trend
        coverage_trend = self.get_trend('coverage_percent')
        if coverage_trend:
            print(f"Coverage: {' → '.join(f'{c:.1f}%' for c in coverage_trend[-5:])}")
        
        # Pass rate trend
        pass_trend = self.get_trend('pass_rate')
        if pass_trend:
            print(f"Pass Rate: {' → '.join(f'{p:.1f}%' for p in pass_trend[-5:])}")
        
        # Test count trend
        test_trend = self.get_trend('total_tests')
        if test_trend:
            print(f"Test Count: {' → '.join(str(t) for t in test_trend[-5:])}")


def track_all_repos():
    """Track metrics for all repos in the github directory."""
    github_dir = Path('/mnt/github/github')
    
    all_metrics = {}
    
    # Find all repos with tests
    for repo_dir in github_dir.iterdir():
        if repo_dir.is_dir() and (repo_dir / 'tests').exists():
            print(f"\n{'=' * 60}")
            print(f"Processing: {repo_dir.name}")
            print('=' * 60)
            
            tracker = TestMetricsTracker(repo_dir)
            metrics = tracker.track_metrics()
            all_metrics[repo_dir.name] = metrics
    
    # Save summary
    summary_file = github_dir / 'test_metrics_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(all_metrics, f, indent=2)
    
    print(f"\n✅ All metrics saved to: {summary_file}")
    
    # Print overall summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    
    for repo, metrics in all_metrics.items():
        print(f"\n{repo}:")
        print(f"  Tests: {metrics.get('total_tests', 0)}")
        print(f"  Pass Rate: {metrics.get('pass_rate', 0):.1f}%")
        print(f"  Coverage: {metrics.get('coverage_percent', 0):.1f}%")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Track test metrics')
    parser.add_argument('--all', action='store_true', help='Track all repos')
    parser.add_argument('--repo', type=str, help='Specific repo path')
    parser.add_argument('--trends', action='store_true', help='Show trends')
    
    args = parser.parse_args()
    
    if args.all:
        track_all_repos()
    else:
        repo_path = Path(args.repo) if args.repo else Path.cwd()
        tracker = TestMetricsTracker(repo_path)
        tracker.track_metrics()
        
        if args.trends:
            tracker.print_trends()
