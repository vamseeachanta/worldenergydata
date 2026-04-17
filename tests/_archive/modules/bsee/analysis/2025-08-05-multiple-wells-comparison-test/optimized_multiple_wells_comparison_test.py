"""
Optimized Multiple Wells Comparison Test Framework

This module integrates performance optimization and memory management
with the multiple wells comparison framework for handling 120+ wells efficiently.
"""

import gc
import os
import shutil
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from advanced_comparison_engine import (
        AdvancedComparisonEngine,
        ComparisonConfig,
        ComparisonResult,
        StatisticalSummary,
    )
    from multiple_wells_comparison_test import MultipleWellsDataProcessor
    from performance_optimizer import (
        PerformanceMetrics,
        PerformanceOptimizer,
        ResourceConstraints,
        benchmark_comparison_performance,
    )
    from strategic_report_generator import ReportConfig, StrategicReportGenerator

    OPTIMIZER_INTEGRATION_AVAILABLE = True
except ImportError as e:
    OPTIMIZER_INTEGRATION_AVAILABLE = False
    print(f"Warning: Could not import all required modules: {e}")


class OptimizedMultipleWellsComparisonFramework:
    """
    Performance-optimized framework for comparing drilling days and completion days
    analysis outputs from two different BSEE data processing methods across 120+ wells.
    """

    def __init__(
        self,
        performance_constraints: Optional[ResourceConstraints] = None,
        comparison_config: Optional[ComparisonConfig] = None,
        report_config: Optional[ReportConfig] = None,
        results_directory: Optional[str] = None,
    ):
        """
        Initialize optimized comparison framework.

        Args:
            performance_constraints: Resource constraints for optimization
            comparison_config: Configuration for comparison analysis
            report_config: Configuration for report generation
            results_directory: Directory for output files
        """
        # Set up results directory
        if results_directory:
            self.results_directory = Path(results_directory)
        else:
            self.results_directory = (
                Path("optimized_multiple_wells_comparison_test") / "results"
            )

        self.results_directory.mkdir(parents=True, exist_ok=True)

        # Initialize performance optimizer
        self.performance_constraints = performance_constraints or ResourceConstraints(
            max_chunk_size=50,  # Optimized for 120+ wells
            memory_warning_threshold=0.7,
            enable_gc_optimization=True,
        )
        self.performance_optimizer = PerformanceOptimizer(self.performance_constraints)

        # Initialize comparison engine
        self.comparison_config = comparison_config or ComparisonConfig(
            outlier_threshold_std=2.5,
            discrepancy_absolute_threshold=5.0,
            discrepancy_percentage_threshold=10.0,
            enable_clustering=True,
            results_directory=str(self.results_directory),
        )
        self.comparison_engine = AdvancedComparisonEngine(self.comparison_config)

        # Initialize report generator
        self.report_config = report_config or ReportConfig(
            max_detailed_wells=20,  # Strategic limiting for 120+ wells
            summary_top_n=15,
            include_charts=True,
            enable_appendix=False,
            results_directory=str(self.results_directory),
        )
        self.report_generator = StrategicReportGenerator(self.report_config)

        # Processing statistics
        self.processing_stats = {
            "total_wells_processed": 0,
            "optimization_performance": [],
            "comparison_performance": [],
            "report_generation_performance": [],
            "memory_efficiency_scores": [],
        }

    def run_optimized_comparison(
        self,
        lease_data: pd.DataFrame,
        api12_data: pd.DataFrame,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Run optimized comparison analysis on multiple wells data.

        Args:
            lease_data: DataFrame with lease method results
            api12_data: DataFrame with API12 method results
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with comparison results and performance metrics
        """
        start_time = time.time()

        if progress_callback:
            progress_callback("Starting optimized comparison analysis...")

        # Step 1: Optimize data loading and preparation
        if progress_callback:
            progress_callback("Optimizing data types and memory usage...")

        optimized_lease_data, lease_metrics = (
            self.performance_optimizer.optimize_for_large_dataset(
                lease_data,
                lambda df: df,  # Identity function for optimization
                lambda msg: (
                    progress_callback(f"Lease data: {msg}")
                    if progress_callback
                    else None
                ),
            )
        )

        optimized_api12_data, api12_metrics = (
            self.performance_optimizer.optimize_for_large_dataset(
                api12_data,
                lambda df: df,  # Identity function for optimization
                lambda msg: (
                    progress_callback(f"API12 data: {msg}")
                    if progress_callback
                    else None
                ),
            )
        )

        # Record optimization performance
        self.processing_stats["optimization_performance"].extend(
            [lease_metrics, api12_metrics]
        )

        # Step 2: Perform comparison analysis with optimization
        if progress_callback:
            progress_callback("Performing optimized comparison analysis...")

        def comparison_analysis(data_tuple):
            lease_df, api12_df = data_tuple
            return self.comparison_engine.perform_comprehensive_comparison(
                lease_df, api12_df
            )

        combined_data = (optimized_lease_data, optimized_api12_data)
        comparison_result, comparison_metrics = (
            self.performance_optimizer.optimize_for_large_dataset(
                pd.DataFrame({"placeholder": [1]}),  # Dummy DataFrame for metrics
                lambda _: comparison_analysis(combined_data),
                lambda msg: (
                    progress_callback(f"Comparison: {msg}")
                    if progress_callback
                    else None
                ),
            )
        )

        comparison_results, statistical_summary = comparison_result
        self.processing_stats["comparison_performance"].append(comparison_metrics)

        # Step 3: Generate strategic report with optimization
        if progress_callback:
            progress_callback("Generating optimized strategic report...")

        def report_generation(dummy_df):
            processing_stats = {
                "total_wells_analyzed": len(comparison_results),
                "successful_comparisons": len(
                    [r for r in comparison_results if r.overall_status != "ERROR"]
                ),
                "processing_time_seconds": comparison_metrics.execution_time_seconds,
                "outliers_detected": len(
                    [r for r in comparison_results if r.outlier_flags]
                ),
                "significant_discrepancies": len(
                    [r for r in comparison_results if r.overall_status == "ERROR"]
                ),
            }

            return self.report_generator.generate_comprehensive_report(
                comparison_results, statistical_summary, processing_stats
            )

        report_path, report_metrics = (
            self.performance_optimizer.optimize_for_large_dataset(
                pd.DataFrame({"placeholder": [1]}),  # Dummy DataFrame
                report_generation,
                lambda msg: (
                    progress_callback(f"Report: {msg}") if progress_callback else None
                ),
            )
        )

        self.processing_stats["report_generation_performance"].append(report_metrics)

        # Step 4: Export detailed results with optimization
        if progress_callback:
            progress_callback("Exporting optimized results...")

        export_paths = self.comparison_engine.export_detailed_results(
            comparison_results, statistical_summary
        )

        # Calculate overall performance metrics
        total_time = time.time() - start_time
        total_wells = len(comparison_results)

        # Update processing statistics
        self.processing_stats["total_wells_processed"] += total_wells
        self.processing_stats["memory_efficiency_scores"].extend(
            [
                lease_metrics.memory_efficiency_score,
                api12_metrics.memory_efficiency_score,
                comparison_metrics.memory_efficiency_score,
                report_metrics.memory_efficiency_score,
            ]
        )

        if progress_callback:
            progress_callback(
                f"Analysis complete! Processed {total_wells} wells in {total_time:.2f} seconds"
            )

        return {
            "comparison_results": comparison_results,
            "statistical_summary": statistical_summary,
            "report_path": report_path,
            "export_paths": export_paths,
            "performance_metrics": {
                "total_execution_time": total_time,
                "wells_processed": total_wells,
                "wells_per_second": total_wells / total_time if total_time > 0 else 0,
                "optimization_metrics": {
                    "lease_data": lease_metrics,
                    "api12_data": api12_metrics,
                    "comparison": comparison_metrics,
                    "report_generation": report_metrics,
                },
                "average_memory_efficiency": np.mean(
                    self.processing_stats["memory_efficiency_scores"]
                ),
                "system_resources": self.performance_optimizer.check_system_resources(),
            },
        }

    def benchmark_performance(
        self, lease_data: pd.DataFrame, api12_data: pd.DataFrame, iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Benchmark performance of optimized comparison framework.

        Args:
            lease_data: Lease method DataFrame
            api12_data: API12 method DataFrame
            iterations: Number of benchmark iterations

        Returns:
            Benchmark results and performance analysis
        """

        def optimized_comparison_func(df1, df2):
            """Optimized comparison function for benchmarking."""
            framework = OptimizedMultipleWellsComparisonFramework(
                performance_constraints=ResourceConstraints(
                    max_chunk_size=25,  # Smaller chunks for benchmarking
                    enable_gc_optimization=True,
                ),
                report_config=ReportConfig(
                    include_charts=False,  # Disable charts for speed
                    enable_appendix=False,
                ),
            )

            result = framework.run_optimized_comparison(df1, df2)
            return result["comparison_results"]

        benchmark_results = benchmark_comparison_performance(
            lease_data, api12_data, optimized_comparison_func, iterations
        )

        # Add framework-specific analysis
        benchmark_results["framework_analysis"] = {
            "optimization_enabled": True,
            "memory_management": "Active",
            "batch_processing": "Enabled",
            "strategic_reporting": "Enabled",
            "recommended_settings": {
                "max_chunk_size": 50 if len(lease_data) > 100 else 25,
                "enable_charts": len(lease_data) < 200,
                "enable_appendix": len(lease_data) < 50,
            },
        }

        return benchmark_results

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization performance."""
        if not self.processing_stats["optimization_performance"]:
            return {"message": "No optimization data available"}

        opt_metrics = self.processing_stats["optimization_performance"]
        comp_metrics = self.processing_stats["comparison_performance"]
        report_metrics = self.processing_stats["report_generation_performance"]

        return {
            "total_wells_processed": self.processing_stats["total_wells_processed"],
            "total_operations": len(opt_metrics)
            + len(comp_metrics)
            + len(report_metrics),
            "optimization_performance": {
                "average_execution_time": np.mean(
                    [m.execution_time_seconds for m in opt_metrics]
                ),
                "average_memory_efficiency": np.mean(
                    [m.memory_efficiency_score for m in opt_metrics]
                ),
                "total_rows_optimized": sum(m.rows_processed for m in opt_metrics),
            },
            "comparison_performance": {
                "average_execution_time": (
                    np.mean([m.execution_time_seconds for m in comp_metrics])
                    if comp_metrics
                    else 0
                ),
                "average_memory_efficiency": (
                    np.mean([m.memory_efficiency_score for m in comp_metrics])
                    if comp_metrics
                    else 0
                ),
            },
            "report_generation_performance": {
                "average_execution_time": (
                    np.mean([m.execution_time_seconds for m in report_metrics])
                    if report_metrics
                    else 0
                ),
                "average_memory_efficiency": (
                    np.mean([m.memory_efficiency_score for m in report_metrics])
                    if report_metrics
                    else 0
                ),
            },
            "overall_memory_efficiency": (
                np.mean(self.processing_stats["memory_efficiency_scores"])
                if self.processing_stats["memory_efficiency_scores"]
                else 0
            ),
            "system_recommendations": self.performance_optimizer.check_system_resources()[
                "recommendations"
            ],
        }

    def validate_performance_targets(self, target_wells: int = 120) -> Dict[str, bool]:
        """
        Validate that performance targets are met for target number of wells.

        Args:
            target_wells: Target number of wells to validate against

        Returns:
            Dictionary with validation results
        """
        # Create synthetic test data
        np.random.seed(42)

        lease_test_data = pd.DataFrame(
            {
                "API12": [f"60812400{i:05d}" for i in range(target_wells)],
                "Well Name": [f"Lease Well {i}" for i in range(target_wells)],
                "Drilling Days": np.random.normal(50, 12, target_wells).astype(int),
                "Completion Days": np.random.normal(18, 5, target_wells).astype(int),
            }
        )

        api12_test_data = pd.DataFrame(
            {
                "API12": [f"60812400{i:05d}" for i in range(target_wells)],
                "Well Name": [f"API12 Well {i}" for i in range(target_wells)],
                "Drilling Days": np.random.normal(52, 10, target_wells).astype(int),
                "Completion Days": np.random.normal(19, 4, target_wells).astype(int),
            }
        )

        # Run performance test
        start_time = time.time()
        result = self.run_optimized_comparison(lease_test_data, api12_test_data)
        total_time = time.time() - start_time

        performance_metrics = result["performance_metrics"]

        # Define performance targets
        targets = {
            "execution_time_under_60s": total_time < 60,  # Complete within 1 minute
            "wells_per_second_over_2": performance_metrics["wells_per_second"]
            > 2,  # At least 2 wells/sec
            "memory_efficiency_over_70": performance_metrics[
                "average_memory_efficiency"
            ]
            > 70,  # >70% efficiency
            "successful_processing": len(result["comparison_results"])
            == target_wells,  # All wells processed
            "report_generated": os.path.exists(result["report_path"]),  # Report created
            "exports_created": all(
                os.path.exists(path) for path in result["export_paths"].values()
            ),  # Exports created
        }

        targets["all_targets_met"] = all(targets.values())

        return {
            "validation_results": targets,
            "performance_details": {
                "total_execution_time": total_time,
                "wells_processed": target_wells,
                "wells_per_second": performance_metrics["wells_per_second"],
                "memory_efficiency": performance_metrics["average_memory_efficiency"],
                "system_resources": performance_metrics["system_resources"],
            },
            "recommendations": self._get_performance_recommendations(
                targets, performance_metrics
            ),
        }

    def _get_performance_recommendations(
        self, targets: Dict[str, bool], metrics: Dict[str, Any]
    ) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []

        if not targets["execution_time_under_60s"]:
            recommendations.append(
                "Consider reducing chunk size or enabling more aggressive memory optimization"
            )

        if not targets["wells_per_second_over_2"]:
            recommendations.append(
                "Processing speed below optimal. Consider optimizing comparison algorithms"
            )

        if not targets["memory_efficiency_over_70"]:
            recommendations.append(
                "Memory efficiency could be improved. Enable aggressive data type optimization"
            )

        # System-based recommendations
        system_info = metrics["system_resources"]
        if system_info["memory"]["used_percent"] > 80:
            recommendations.append(
                "High system memory usage. Consider smaller chunk sizes"
            )

        if system_info["cpu"]["usage_percent"] > 80:
            recommendations.append(
                "High CPU usage detected. Consider reducing processing concurrency"
            )

        if not recommendations:
            recommendations.append(
                "Performance is optimal for current system configuration"
            )

        return recommendations


def create_sample_data(num_wells: int = 125) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create sample data for testing optimized comparison framework.

    Args:
        num_wells: Number of wells to generate

    Returns:
        Tuple of (lease_data, api12_data) DataFrames
    """
    np.random.seed(42)

    lease_data = pd.DataFrame(
        {
            "API12": [f"60812400{i:05d}" for i in range(num_wells)],
            "Well Name": [f"Lease Well {i+1}" for i in range(num_wells)],
            "Drilling Days": np.random.normal(48, 15, num_wells).astype(int),
            "Completion Days": np.random.normal(17, 6, num_wells).astype(int),
            "Operator": np.random.choice(
                ["Shell", "BP", "Exxon", "Chevron", "ConocoPhillips"], num_wells
            ),
            "Field": np.random.choice(
                ["Thunder Horse", "Atlantis", "Mad Dog", "Na Kika"], num_wells
            ),
        }
    )

    # API12 data with systematic differences and some noise
    api12_data = pd.DataFrame(
        {
            "API12": [f"60812400{i:05d}" for i in range(num_wells)],
            "Well Name": [f"API12 Well {i+1}" for i in range(num_wells)],
            "Drilling Days": (
                np.random.normal(48, 15, num_wells) + np.random.normal(2, 5, num_wells)
            ).astype(
                int
            ),  # +2 days average difference
            "Completion Days": (
                np.random.normal(17, 6, num_wells) + np.random.normal(1, 3, num_wells)
            ).astype(
                int
            ),  # +1 day average difference
            "Operator": np.random.choice(
                ["Shell", "BP", "Exxon", "Chevron", "ConocoPhillips"], num_wells
            ),
            "Field": np.random.choice(
                ["Thunder Horse", "Atlantis", "Mad Dog", "Na Kika"], num_wells
            ),
        }
    )

    return lease_data, api12_data


if __name__ == "__main__":
    # Example usage of optimized comparison framework
    if OPTIMIZER_INTEGRATION_AVAILABLE:
        print("Testing Optimized Multiple Wells Comparison Framework")
        print("=" * 60)

        # Create sample data with 125 wells
        lease_data, api12_data = create_sample_data(125)
        print(f"Created sample data: {len(lease_data)} wells")

        # Initialize optimized framework
        framework = OptimizedMultipleWellsComparisonFramework()

        # Progress tracking
        def progress_tracker(message):
            print(f"Progress: {message}")

        # Run optimized comparison
        print("\nRunning optimized comparison...")
        results = framework.run_optimized_comparison(
            lease_data, api12_data, progress_tracker
        )

        # Display results summary
        print(f"\nComparison Results:")
        print(f"- Wells processed: {len(results['comparison_results'])}")
        print(
            f"- Execution time: {results['performance_metrics']['total_execution_time']:.2f} seconds"
        )
        print(
            f"- Wells per second: {results['performance_metrics']['wells_per_second']:.1f}"
        )
        print(
            f"- Memory efficiency: {results['performance_metrics']['average_memory_efficiency']:.1f}%"
        )
        print(f"- Report generated: {results['report_path']}")

        # Validate performance targets
        print(f"\nValidating performance targets...")
        validation = framework.validate_performance_targets(125)

        print(f"Performance validation results:")
        for target, result in validation["validation_results"].items():
            status = "✓" if result else "✗"
            print(f"  {status} {target}: {result}")

        print(f"\nRecommendations:")
        for rec in validation["recommendations"]:
            print(f"  - {rec}")

        print(f"\nOptimization summary:")
        summary = framework.get_optimization_summary()
        print(f"  - Total wells processed: {summary['total_wells_processed']}")
        print(
            f"  - Overall memory efficiency: {summary['overall_memory_efficiency']:.1f}%"
        )

    else:
        print("Required modules not available for optimized comparison framework")
