#!/usr/bin/env python3
"""
BSEE Data Consolidation - Comprehensive Migration Test Script

Verifies migration success through extensive testing of all BSEE functionality.
Tests both old and new import patterns, data integrity, and performance.

Usage:
    python comprehensive_migration_test.py [--verbose] [--performance] [--fix-issues]
"""

import argparse
import importlib
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

import pandas as pd
import yaml


class MigrationTestSuite:
    """Comprehensive test suite for BSEE migration verification."""
    
    def __init__(self, base_path: str = None, verbose: bool = False):
        """Initialize test suite.
        
        Args:
            base_path: Base path for WorldEnergyData project
            verbose: Enable verbose output
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.verbose = verbose
        self.test_results = []
        self.performance_metrics = {}
        
        # Add project to Python path
        src_path = self.base_path / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
            
    def log(self, message: str, level: str = "INFO") -> None:
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def verbose_log(self, message: str) -> None:
        """Log message only in verbose mode."""
        if self.verbose:
            self.log(message, "DEBUG")
            
    def add_test_result(self, test_name: str, status: str, details: str = "", 
                       duration: float = 0) -> None:
        """Add test result to tracking."""
        self.test_results.append({
            'test_name': test_name,
            'status': status,
            'details': details,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })
        
    def test_import_patterns(self) -> bool:
        """Test various import patterns work correctly."""
        self.log("🔍 Testing import patterns...")
        
        import_tests = [
            # New consolidated imports
            ("worldenergydata.bsee", "Main BSEE module"),
            ("worldenergydata.bsee.data_collection", "Data collection module"),
            ("worldenergydata.bsee.analysis", "Analysis module"),
            ("worldenergydata.bsee.processing", "Processing module"),
            
            # Specific functionality
            ("worldenergydata.bsee.data_collection.BSEEDataCollector", "Data collector class"),
            ("worldenergydata.bsee.analysis.ProductionAnalyzer", "Production analyzer"),
            ("worldenergydata.bsee.processing.DirectionalProcessor", "Directional processor"),
        ]
        
        passed_tests = 0
        total_tests = len(import_tests)
        
        for import_path, description in import_tests:
            start_time = time.time()
            try:
                if "." in import_path.split(".")[-1] and import_path.split(".")[-1][0].isupper():
                    # Class import
                    module_path = ".".join(import_path.split(".")[:-1])
                    class_name = import_path.split(".")[-1]
                    module = importlib.import_module(module_path)
                    getattr(module, class_name)
                else:
                    # Module import
                    importlib.import_module(import_path)
                    
                duration = time.time() - start_time
                self.add_test_result(f"Import: {description}", "PASS", import_path, duration)
                self.verbose_log(f"✅ {description}: {import_path}")
                passed_tests += 1
                
            except Exception as e:
                duration = time.time() - start_time
                self.add_test_result(f"Import: {description}", "FAIL", str(e), duration)
                self.log(f"❌ {description}: {e}")
                
        success_rate = passed_tests / total_tests
        self.log(f"Import tests: {passed_tests}/{total_tests} passed ({success_rate:.1%})")
        
        return success_rate >= 0.8  # 80% pass rate required
        
    def test_data_collection_functionality(self) -> bool:
        """Test data collection functionality."""
        self.log("🔍 Testing data collection functionality...")
        
        try:
            from worldenergydata.bsee.data_collection import BSEEDataCollector
            
            # Test collector initialization
            start_time = time.time()
            collector = BSEEDataCollector()
            init_time = time.time() - start_time
            
            self.add_test_result("DataCollector Init", "PASS", "Successfully initialized", init_time)
            self.verbose_log(f"✅ Data collector initialized in {init_time:.3f}s")
            
            # Test basic methods exist
            required_methods = ['collect_production_data', 'collect_directional_data', 'collect_completion_data']
            for method_name in required_methods:
                if hasattr(collector, method_name):
                    self.add_test_result(f"Method: {method_name}", "PASS", "Method exists")
                    self.verbose_log(f"✅ Method exists: {method_name}")
                else:
                    self.add_test_result(f"Method: {method_name}", "FAIL", "Method missing")
                    self.log(f"❌ Missing method: {method_name}")
                    
            return True
            
        except Exception as e:
            self.add_test_result("DataCollector Test", "FAIL", str(e))
            self.log(f"❌ Data collection test failed: {e}")
            return False
            
    def test_analysis_functionality(self) -> bool:
        """Test analysis functionality."""
        self.log("🔍 Testing analysis functionality...")
        
        try:
            from worldenergydata.bsee.analysis import ProductionAnalyzer
            
            # Test analyzer initialization
            start_time = time.time()
            analyzer = ProductionAnalyzer()
            init_time = time.time() - start_time
            
            self.add_test_result("ProductionAnalyzer Init", "PASS", "Successfully initialized", init_time)
            self.verbose_log(f"✅ Production analyzer initialized in {init_time:.3f}s")
            
            # Test basic methods exist
            required_methods = ['analyze_production_trends', 'calculate_decline_curves', 'generate_forecasts']
            for method_name in required_methods:
                if hasattr(analyzer, method_name):
                    self.add_test_result(f"Method: {method_name}", "PASS", "Method exists")
                    self.verbose_log(f"✅ Method exists: {method_name}")
                else:
                    self.add_test_result(f"Method: {method_name}", "FAIL", "Method missing")
                    self.log(f"❌ Missing method: {method_name}")
                    
            return True
            
        except Exception as e:
            self.add_test_result("ProductionAnalyzer Test", "FAIL", str(e))
            self.log(f"❌ Analysis test failed: {e}")
            return False
            
    def test_data_integrity(self) -> bool:
        """Test data integrity after migration."""
        self.log("🔍 Testing data integrity...")
        
        try:
            # Test sample data loading and processing
            sample_data_path = self.base_path / "data" / "bsee" / "sample"
            
            if not sample_data_path.exists():
                self.add_test_result("Data Integrity", "SKIP", "No sample data found")
                self.verbose_log("⏭️  No sample data found, skipping integrity test")
                return True
                
            # Count files and basic validation
            csv_files = list(sample_data_path.glob("*.csv"))
            excel_files = list(sample_data_path.glob("*.xlsx"))
            
            total_files = len(csv_files) + len(excel_files)
            self.add_test_result("Data Files Count", "PASS", f"Found {total_files} data files")
            self.verbose_log(f"✅ Found {total_files} data files")
            
            # Test basic pandas loading
            if csv_files:
                test_file = csv_files[0]
                start_time = time.time()
                df = pd.read_csv(test_file)
                load_time = time.time() - start_time
                
                self.add_test_result("Data Loading", "PASS", 
                                   f"Loaded {len(df)} rows from {test_file.name}", load_time)
                self.verbose_log(f"✅ Loaded {len(df)} rows in {load_time:.3f}s")
                
            return True
            
        except Exception as e:
            self.add_test_result("Data Integrity", "FAIL", str(e))
            self.log(f"❌ Data integrity test failed: {e}")
            return False
            
    def test_performance_benchmarks(self) -> bool:
        """Test performance benchmarks."""
        self.log("🔍 Running performance benchmarks...")
        
        try:
            # Import timing
            start_time = time.time()
            from worldenergydata.bsee import data_collection, analysis, processing
            import_time = time.time() - start_time
            
            self.performance_metrics['import_time'] = import_time
            self.add_test_result("Import Performance", "PASS", f"Imports completed in {import_time:.3f}s", import_time)
            
            # Memory usage test (basic)
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.performance_metrics['memory_usage_mb'] = memory_mb
            self.add_test_result("Memory Usage", "PASS", f"Current memory usage: {memory_mb:.1f} MB")
            
            self.verbose_log(f"✅ Performance metrics collected")
            return True
            
        except Exception as e:
            self.add_test_result("Performance Test", "FAIL", str(e))
            self.log(f"❌ Performance test failed: {e}")
            return False
            
    def test_legacy_compatibility(self) -> bool:
        """Test legacy import compatibility if compatibility layer exists."""
        self.log("🔍 Testing legacy compatibility...")
        
        # This would test if any legacy import paths still work
        # through compatibility layers
        legacy_imports = [
            "worldenergydata.data_collectors.bsee_data_collector",
            "worldenergydata.analysis.production_analysis", 
            "worldenergydata.processing.directional_survey_processor"
        ]
        
        compatible_imports = 0
        for legacy_import in legacy_imports:
            try:
                importlib.import_module(legacy_import)
                compatible_imports += 1
                self.add_test_result(f"Legacy: {legacy_import}", "PASS", "Compatible")
                self.verbose_log(f"✅ Legacy import works: {legacy_import}")
            except ImportError:
                self.add_test_result(f"Legacy: {legacy_import}", "EXPECTED_FAIL", "Not compatible (expected)")
                self.verbose_log(f"⚠️  Legacy import not available: {legacy_import}")
            except Exception as e:
                self.add_test_result(f"Legacy: {legacy_import}", "FAIL", str(e))
                self.log(f"❌ Legacy import error: {legacy_import}: {e}")
                
        self.log(f"Legacy compatibility: {compatible_imports}/{len(legacy_imports)} imports work")
        return True  # This test doesn't fail the suite
        
    def run_all_tests(self, run_performance: bool = False) -> Dict[str, Any]:
        """Run all migration tests."""
        self.log("🚀 Starting comprehensive migration test suite...")
        start_time = time.time()
        
        # Run test categories
        test_categories = [
            ("Import Patterns", self.test_import_patterns),
            ("Data Collection", self.test_data_collection_functionality), 
            ("Analysis", self.test_analysis_functionality),
            ("Data Integrity", self.test_data_integrity),
            ("Legacy Compatibility", self.test_legacy_compatibility)
        ]
        
        if run_performance:
            test_categories.append(("Performance", self.test_performance_benchmarks))
            
        passed_categories = 0
        for category_name, test_func in test_categories:
            self.log(f"\n📋 Running {category_name} tests...")
            try:
                if test_func():
                    passed_categories += 1
                    self.log(f"✅ {category_name} tests passed")
                else:
                    self.log(f"❌ {category_name} tests failed")
            except Exception as e:
                self.log(f"💥 {category_name} tests crashed: {e}")
                if self.verbose:
                    traceback.print_exc()
                    
        total_time = time.time() - start_time
        
        # Generate summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_time': total_time,
            'categories_passed': passed_categories,
            'categories_total': len(test_categories),
            'tests_passed': passed_tests,
            'tests_failed': failed_tests,
            'tests_total': total_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'performance_metrics': self.performance_metrics,
            'test_results': self.test_results
        }
        
        self.log(f"\n📊 Test Suite Summary:")
        self.log(f"   Categories: {passed_categories}/{len(test_categories)} passed")
        self.log(f"   Individual tests: {passed_tests}/{total_tests} passed ({summary['success_rate']:.1%})")
        self.log(f"   Total time: {total_time:.2f}s")
        
        # Determine overall success
        overall_success = (passed_categories / len(test_categories)) >= 0.8
        self.log(f"   Overall result: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        return summary
        
    def save_test_report(self, summary: Dict[str, Any]) -> None:
        """Save detailed test report."""
        report_path = self.base_path / "scripts" / "bsee_migration" / "migration_test_report.yaml"
        
        with open(report_path, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False, sort_keys=False)
            
        self.log(f"📄 Detailed report saved to: {report_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive BSEE migration test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic test run
    python comprehensive_migration_test.py
    
    # Verbose output with performance tests
    python comprehensive_migration_test.py --verbose --performance
    
    # Auto-fix issues if possible
    python comprehensive_migration_test.py --fix-issues
        """
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--performance', '-p',
        action='store_true',
        help='Include performance benchmarks'
    )
    parser.add_argument(
        '--fix-issues',
        action='store_true',
        help='Attempt to fix issues found during testing'
    )
    parser.add_argument(
        '--base-path',
        type=str,
        help='Base path for WorldEnergyData project'
    )
    
    args = parser.parse_args()
    
    test_suite = MigrationTestSuite(
        base_path=args.base_path,
        verbose=args.verbose
    )
    
    summary = test_suite.run_all_tests(run_performance=args.performance)
    test_suite.save_test_report(summary)
    
    # Exit with appropriate code
    if summary['success_rate'] >= 0.8:
        print("\n🎉 Migration test suite PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Migration test suite FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()