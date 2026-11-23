"""
Test suite for Advanced Comparison Analysis Engine

This module tests the statistical comparison algorithms and analysis capabilities
for handling 120+ wells from different analysis methods.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from advanced_comparison_engine import (
        AdvancedComparisonEngine,
        ComparisonConfig,
        ComparisonResult,
        OutlierDetector,
        StatisticalAnalyzer,
        StatisticalSummary,
    )

    ENGINE_AVAILABLE = True
except ImportError as e:
    ENGINE_AVAILABLE = False
    print(f"Warning: Could not import advanced comparison engine: {e}")


@pytest.mark.skipif(
    not ENGINE_AVAILABLE, reason="Advanced comparison engine not available"
)
class TestComparisonConfig:
    """Test configuration class for comparison analysis."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ComparisonConfig()

        assert config.outlier_threshold_std == 2.5
        assert config.outlier_threshold_iqr == 1.5
        assert config.discrepancy_absolute_threshold == 5.0
        assert config.discrepancy_percentage_threshold == 10.0
        assert config.enable_clustering == True
        assert config.statistical_confidence_level == 0.95

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ComparisonConfig(
            outlier_threshold_std=3.0,
            discrepancy_absolute_threshold=7.0,
            discrepancy_percentage_threshold=15.0,
            enable_clustering=False,
        )

        assert config.outlier_threshold_std == 3.0
        assert config.discrepancy_absolute_threshold == 7.0
        assert config.discrepancy_percentage_threshold == 15.0
        assert config.enable_clustering == False


@pytest.mark.skipif(
    not ENGINE_AVAILABLE, reason="Advanced comparison engine not available"
)
class TestOutlierDetector:
    """Test outlier detection functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ComparisonConfig(
            outlier_threshold_std=2.0,
            outlier_threshold_iqr=1.5,
            enable_detailed_logging=False,
        )

    @pytest.fixture
    def detector(self, config):
        """Create outlier detector instance."""
        return OutlierDetector(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample data with known outliers."""
        np.random.seed(42)  # For reproducible results
        normal_data = np.random.normal(50, 10, 100)  # Mean=50, std=10
        outliers = [100, 120, 0, -10]  # Clear outliers
        return pd.Series(list(normal_data) + outliers)

    def test_zscore_outlier_detection(self, detector, sample_data):
        """Test Z-score based outlier detection."""
        results = detector.detect_outliers_statistical(sample_data, method="zscore")

        assert "outlier_indices" in results
        assert "outlier_values" in results
        assert "method" in results
        assert results["method"] == "zscore"
        assert results["outlier_count"] > 0
        assert results["outlier_percentage"] > 0

    def test_iqr_outlier_detection(self, detector, sample_data):
        """Test IQR based outlier detection."""
        results = detector.detect_outliers_statistical(sample_data, method="iqr")

        assert results["method"] == "iqr"
        assert results["outlier_count"] > 0
        assert results["threshold"] == 1.5

    def test_modified_zscore_outlier_detection(self, detector, sample_data):
        """Test modified Z-score outlier detection."""
        results = detector.detect_outliers_statistical(
            sample_data, method="modified_zscore"
        )

        assert results["method"] == "modified_zscore"
        assert results["outlier_count"] >= 0

    def test_clustering_outlier_detection(self, detector):
        """Test clustering-based outlier detection."""
        # Create data with clear clusters and outliers
        np.random.seed(42)
        cluster1 = np.random.multivariate_normal([10, 10], [[1, 0], [0, 1]], 20)
        cluster2 = np.random.multivariate_normal([50, 50], [[1, 0], [0, 1]], 20)
        outliers = np.array([[100, 100], [-10, -10], [75, 25]])

        data = np.vstack([cluster1, cluster2, outliers])
        df = pd.DataFrame(data, columns=["feature1", "feature2"])

        results = detector.detect_outliers_clustering(df, ["feature1", "feature2"])

        assert "method" in results
        assert results["method"] == "clustering"
        assert "outlier_count" in results
        assert "num_clusters" in results

    def test_empty_data_handling(self, detector):
        """Test handling of empty data."""
        empty_series = pd.Series([])
        results = detector.detect_outliers_statistical(empty_series)

        assert results["outlier_indices"] == []
        assert results["outlier_values"] == []
        assert results["outlier_count"] == 0

    def test_insufficient_data_clustering(self, detector):
        """Test clustering with insufficient data."""
        small_df = pd.DataFrame({"feature1": [1, 2], "feature2": [3, 4]})

        results = detector.detect_outliers_clustering(
            small_df, ["feature1", "feature2"]
        )

        assert results["status"] == "insufficient_data"
        assert "min_samples_required" in results


@pytest.mark.skipif(
    not ENGINE_AVAILABLE, reason="Advanced comparison engine not available"
)
class TestStatisticalAnalyzer:
    """Test statistical analysis functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ComparisonConfig(
            statistical_confidence_level=0.95, enable_detailed_logging=False
        )

    @pytest.fixture
    def analyzer(self, config):
        """Create statistical analyzer instance."""
        return StatisticalAnalyzer(config)

    @pytest.fixture
    def sample_data_sets(self):
        """Create sample data sets for comparison."""
        np.random.seed(42)
        data1 = pd.Series(np.random.normal(45, 8, 100))  # Drilling days - lease method
        data2 = pd.Series(np.random.normal(47, 9, 100))  # Drilling days - API12 method
        return data1, data2

    def test_descriptive_statistics(self, analyzer, sample_data_sets):
        """Test descriptive statistics calculation."""
        data1, _ = sample_data_sets

        stats = analyzer._calculate_descriptive_stats(data1, "test_data")

        assert "count" in stats
        assert "mean" in stats
        assert "median" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert "q25" in stats
        assert "q75" in stats
        assert "skewness" in stats
        assert "kurtosis" in stats
        assert stats["count"] == 100

    def test_statistical_tests(self, analyzer, sample_data_sets):
        """Test statistical tests between datasets."""
        data1, data2 = sample_data_sets

        results = analyzer._perform_statistical_tests(data1, data2)

        assert "normality_test" in results
        assert "ttest" in results
        assert "mannwhitney" in results
        assert "kolmogorov_smirnov" in results

        # Check t-test results
        assert "statistic" in results["ttest"]
        assert "pvalue" in results["ttest"]
        assert "significant" in results["ttest"]

    def test_distribution_analysis(self, analyzer, sample_data_sets):
        """Test distribution analysis."""
        data1, data2 = sample_data_sets

        analysis = analyzer.analyze_distributions(data1, data2, "drilling_days")

        assert "lease_method" in analysis
        assert "api12_method" in analysis
        assert "statistical_tests" in analysis
        assert "difference_analysis" in analysis

    def test_effect_size_calculation(self, analyzer, sample_data_sets):
        """Test effect size calculation."""
        data1, data2 = sample_data_sets

        effect_size = analyzer.calculate_effect_size(data1, data2)

        assert "cohens_d" in effect_size
        assert "glass_delta" in effect_size
        assert "effect_size_interpretation" in effect_size
        assert effect_size["effect_size_interpretation"] in [
            "negligible",
            "small",
            "medium",
            "large",
        ]

    def test_empty_data_handling(self, analyzer):
        """Test handling of empty data in statistical analysis."""
        empty_series = pd.Series([])
        data_series = pd.Series([1, 2, 3, 4, 5])

        stats = analyzer._calculate_descriptive_stats(empty_series, "empty_data")
        assert stats["count"] == 0
        assert "error" in stats

        tests = analyzer._perform_statistical_tests(empty_series, data_series)
        assert "error" in tests


@pytest.mark.skipif(
    not ENGINE_AVAILABLE, reason="Advanced comparison engine not available"
)
class TestAdvancedComparisonEngine:
    """Test advanced comparison engine functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return ComparisonConfig(
            outlier_threshold_std=2.0,
            discrepancy_absolute_threshold=5.0,
            discrepancy_percentage_threshold=10.0,
            enable_clustering=True,
            enable_detailed_logging=False,
            results_directory=temp_dir,
        )

    @pytest.fixture
    def engine(self, config):
        """Create comparison engine instance."""
        return AdvancedComparisonEngine(config)

    @pytest.fixture
    def sample_well_data(self):
        """Create sample well data for testing."""
        np.random.seed(42)

        # Create lease method data
        lease_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 123)],  # 122 wells
                "Well Name": [f"Lease Well {i}" for i in range(1, 123)],
                "Drilling Days": np.random.normal(45, 12, 122).astype(int),
                "Completion Days": np.random.normal(15, 5, 122).astype(int),
            }
        )

        # Create API12 method data with some systematic differences
        api12_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 123)],  # Same wells
                "Well Name": [f"API12 Well {i}" for i in range(1, 123)],
                "Drilling Days": (
                    np.random.normal(47, 10, 122) + np.random.normal(0, 3, 122)
                ).astype(int),
                "Completion Days": (
                    np.random.normal(16, 4, 122) + np.random.normal(0, 2, 122)
                ).astype(int),
            }
        )

        # Add some clear outliers for testing
        lease_df.loc[0, "Drilling Days"] = 150  # Major outlier
        api12_df.loc[0, "Drilling Days"] = 25  # Corresponding outlier
        lease_df.loc[1, "Completion Days"] = 50  # Completion outlier
        api12_df.loc[1, "Completion Days"] = 5  # Corresponding outlier

        return lease_df, api12_df

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine.config is not None
        assert engine.outlier_detector is not None
        assert engine.statistical_analyzer is not None
        assert engine.processing_stats["total_wells_analyzed"] == 0

    def test_data_matching_and_alignment(self, engine, sample_well_data):
        """Test data matching and alignment functionality."""
        lease_df, api12_df = sample_well_data

        aligned_data = engine._match_and_align_data(lease_df, api12_df)

        assert not aligned_data.empty
        assert "API12" in aligned_data.columns
        assert "Drilling_Days_Lease" in aligned_data.columns
        assert "Drilling_Days_API12" in aligned_data.columns
        assert "Completion_Days_Lease" in aligned_data.columns
        assert "Completion_Days_API12" in aligned_data.columns
        assert "_merge" in aligned_data.columns

        # Should have perfect match since we created matching data
        both_matches = (aligned_data["_merge"] == "both").sum()
        assert both_matches == 122

    def test_individual_well_comparison(self, engine):
        """Test individual well comparison logic."""
        # Create test row with known values
        test_row = pd.Series(
            {
                "API12": "608124001000",
                "Well_Name_Lease": "Test Well",
                "Drilling_Days_Lease": 40,
                "Drilling_Days_API12": 50,  # 10 day difference, 25% increase
                "Completion_Days_Lease": 10,
                "Completion_Days_API12": 12,  # 2 day difference, 20% increase
                "_merge": "both",
            }
        )

        result = engine._compare_individual_well(test_row)

        assert isinstance(result, ComparisonResult)
        assert result.api12 == "608124001000"
        assert result.drilling_diff == 10
        assert result.completion_diff == 2
        assert result.drilling_pct_diff == 25.0
        assert result.completion_pct_diff == 20.0
        assert result.overall_status in ["OK", "REVIEW", "ERROR"]

    def test_comprehensive_comparison(self, engine, sample_well_data):
        """Test comprehensive comparison analysis."""
        lease_df, api12_df = sample_well_data

        comparison_results, statistical_summary = (
            engine.perform_comprehensive_comparison(lease_df, api12_df)
        )

        # Check comparison results
        assert len(comparison_results) == 122
        assert all(
            isinstance(result, ComparisonResult) for result in comparison_results
        )

        # Check statistical summary
        assert isinstance(statistical_summary, StatisticalSummary)
        assert statistical_summary.total_wells == 122
        assert statistical_summary.successful_matches <= 125
        assert "drilling_days_stats" in statistical_summary.__dict__
        assert "completion_days_stats" in statistical_summary.__dict__

        # Check processing stats were updated
        assert engine.processing_stats["total_wells_analyzed"] == 122
        assert engine.processing_stats["successful_comparisons"] > 0

    def test_outlier_detection_in_comparison(self, engine, sample_well_data):
        """Test that outliers are properly detected in comparison."""
        lease_df, api12_df = sample_well_data

        comparison_results, statistical_summary = (
            engine.perform_comprehensive_comparison(lease_df, api12_df)
        )

        # Should detect outliers (we added some in the fixture)
        outlier_results = [r for r in comparison_results if r.outlier_flags]
        assert len(outlier_results) > 0

        # Check that outlier wells are identified in statistical summary
        assert len(statistical_summary.outlier_wells) > 0
        assert engine.processing_stats["outliers_detected"] > 0

    def test_status_determination(self, engine):
        """Test well status determination logic."""
        # Test OK status
        status, flags = engine._determine_well_status(2, 1, 4.0, 8.0)
        assert status == "OK"
        assert len(flags) == 0

        # Test REVIEW status
        status, flags = engine._determine_well_status(
            6, 1, 4.0, 8.0
        )  # One threshold exceeded
        assert status == "REVIEW"
        assert len(flags) > 0

        # Test ERROR status
        status, flags = engine._determine_well_status(
            10, 8, 25.0, 30.0
        )  # Multiple thresholds exceeded
        assert status == "ERROR"
        assert len(flags) >= 3

    def test_correlation_analysis(self, engine, sample_well_data):
        """Test correlation analysis between methods."""
        lease_df, api12_df = sample_well_data
        aligned_data = engine._match_and_align_data(lease_df, api12_df)

        correlations = engine._perform_correlation_analysis(aligned_data)

        assert "drilling_days" in correlations
        assert "completion_days" in correlations
        assert -1 <= correlations["drilling_days"] <= 1
        assert -1 <= correlations["completion_days"] <= 1

    def test_results_export(self, engine, sample_well_data, temp_dir):
        """Test results export functionality."""
        lease_df, api12_df = sample_well_data

        comparison_results, statistical_summary = (
            engine.perform_comprehensive_comparison(lease_df, api12_df)
        )

        export_paths = engine.export_detailed_results(
            comparison_results, statistical_summary
        )

        assert "csv_results" in export_paths
        assert "json_summary" in export_paths

        # Check that files were created
        assert os.path.exists(export_paths["csv_results"])
        assert os.path.exists(export_paths["json_summary"])

        # Verify CSV content
        results_df = pd.read_csv(export_paths["csv_results"])
        assert len(results_df) == 122
        assert "API12" in results_df.columns
        assert "Status" in results_df.columns

        # Verify JSON content
        with open(export_paths["json_summary"], "r") as f:
            summary_data = json.load(f)

        assert "total_wells" in summary_data
        assert "processing_stats" in summary_data
        assert summary_data["total_wells"] == 122

    def test_error_handling_mismatched_data(self, engine):
        """Test error handling with mismatched data."""
        # Create datasets with no matching wells
        lease_df = pd.DataFrame(
            {
                "API12": ["608124001000", "608124001001"],
                "Well Name": ["Well A", "Well B"],
                "Drilling Days": [40, 35],
                "Completion Days": [10, 8],
            }
        )

        api12_df = pd.DataFrame(
            {
                "API12": ["608124002000", "608124002001"],  # Different API12s
                "Well Name": ["Well C", "Well D"],
                "Drilling Days": [42, 38],
                "Completion Days": [12, 9],
            }
        )

        with pytest.raises(ValueError, match="No matching wells found"):
            engine.perform_comprehensive_comparison(lease_df, api12_df)

    def test_missing_data_handling(self, engine):
        """Test handling of missing data in comparisons."""
        # Create datasets with missing values
        lease_df = pd.DataFrame(
            {
                "API12": ["608124001000", "608124001001", "608124001002"],
                "Well Name": ["Well A", "Well B", "Well C"],
                "Drilling Days": [40, np.nan, 35],  # Missing value
                "Completion Days": [10, 8, np.nan],  # Missing value
            }
        )

        api12_df = pd.DataFrame(
            {
                "API12": ["608124001000", "608124001001", "608124001002"],
                "Well Name": ["Well A", "Well B", "Well C"],
                "Drilling Days": [42, 38, np.nan],  # Missing value
                "Completion Days": [12, np.nan, 9],  # Missing value
            }
        )

        comparison_results, statistical_summary = (
            engine.perform_comprehensive_comparison(lease_df, api12_df)
        )

        # Should handle missing data gracefully
        assert len(comparison_results) == 3
        assert statistical_summary.total_wells == 3

        # Check that missing values are handled in individual results
        for result in comparison_results:
            if pd.isna(result.lease_drilling_days) or pd.isna(
                result.api12_drilling_days
            ):
                assert result.drilling_diff is None
                assert result.drilling_pct_diff is None


@pytest.mark.skipif(
    not ENGINE_AVAILABLE, reason="Advanced comparison engine not available"
)
class TestAdvancedComparisonEngineIntegration:
    """Integration tests for advanced comparison engine with large datasets."""

    def test_120_plus_wells_comparison(self):
        """Test comprehensive comparison with 120+ wells."""
        config = ComparisonConfig(
            outlier_threshold_std=2.5,
            discrepancy_absolute_threshold=6.0,
            discrepancy_percentage_threshold=12.0,
            enable_clustering=True,
            enable_detailed_logging=False,
        )

        engine = AdvancedComparisonEngine(config)

        # Create 125 wells dataset
        np.random.seed(123)

        lease_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 123)],
                "Well Name": [f"Lease Well {i}" for i in range(1, 123)],
                "Drilling Days": np.random.normal(50, 15, 122).astype(int),
                "Completion Days": np.random.normal(18, 6, 122).astype(int),
            }
        )

        api12_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 123)],
                "Well Name": [f"API12 Well {i}" for i in range(1, 123)],
                "Drilling Days": (
                    np.random.normal(52, 14, 122) + np.random.normal(0, 5, 122)
                ).astype(int),
                "Completion Days": (
                    np.random.normal(19, 5, 122) + np.random.normal(0, 3, 122)
                ).astype(int),
            }
        )

        # Perform comprehensive comparison
        comparison_results, statistical_summary = (
            engine.perform_comprehensive_comparison(lease_df, api12_df)
        )

        # Verify results
        assert len(comparison_results) == 122
        assert statistical_summary.total_wells == 122
        assert engine.processing_stats["total_wells_analyzed"] == 122

        # Verify statistical analysis was performed
        assert "lease_method" in statistical_summary.drilling_days_stats
        assert "api12_method" in statistical_summary.drilling_days_stats
        assert "statistical_tests" in statistical_summary.drilling_days_stats

        # Verify correlation analysis
        assert "drilling_days" in statistical_summary.correlation_analysis
        assert "completion_days" in statistical_summary.correlation_analysis

        # Verify outlier detection worked
        assert "drilling_outliers" in statistical_summary.distribution_comparison
        assert "completion_outliers" in statistical_summary.distribution_comparison

    def test_performance_with_large_dataset(self):
        """Test performance and memory efficiency with large dataset."""
        config = ComparisonConfig(enable_clustering=True, enable_detailed_logging=False)

        engine = AdvancedComparisonEngine(config)

        # Create larger dataset (200 wells)
        np.random.seed(456)

        lease_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:05d}" for i in range(1, 201)],
                "Well Name": [f"Lease Well {i}" for i in range(1, 201)],
                "Drilling Days": np.random.normal(45, 12, 200).astype(int),
                "Completion Days": np.random.normal(16, 5, 200).astype(int),
            }
        )

        api12_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:05d}" for i in range(1, 201)],
                "Well Name": [f"API12 Well {i}" for i in range(1, 201)],
                "Drilling Days": np.random.normal(47, 11, 200).astype(int),
                "Completion Days": np.random.normal(17, 4, 200).astype(int),
            }
        )

        # Measure performance
        import time

        start_time = time.time()

        comparison_results, statistical_summary = (
            engine.perform_comprehensive_comparison(lease_df, api12_df)
        )

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify results and performance
        assert len(comparison_results) == 200
        assert statistical_summary.total_wells == 200
        assert processing_time < 30  # Should complete within 30 seconds
        assert engine.processing_stats["processing_time_seconds"] > 0

    def test_systematic_discrepancy_detection(self):
        """Test systematic discrepancy detection across well population."""
        config = ComparisonConfig(
            discrepancy_absolute_threshold=3.0,  # Lower threshold for testing
            discrepancy_percentage_threshold=8.0,
            enable_detailed_logging=False,
        )

        engine = AdvancedComparisonEngine(config)

        # Create data with systematic bias
        np.random.seed(789)

        lease_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 101)],
                "Well Name": [f"Lease Well {i}" for i in range(1, 101)],
                "Drilling Days": np.random.normal(40, 8, 100).astype(int),
                "Completion Days": np.random.normal(12, 3, 100).astype(int),
            }
        )

        # Create API12 data with systematic bias (consistently higher)
        api12_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 101)],
                "Well Name": [f"API12 Well {i}" for i in range(1, 101)],
                "Drilling Days": (np.random.normal(40, 8, 100) + 8).astype(
                    int
                ),  # +8 days bias
                "Completion Days": (np.random.normal(12, 3, 100) + 3).astype(
                    int
                ),  # +3 days bias
            }
        )

        comparison_results, statistical_summary = (
            engine.perform_comprehensive_comparison(lease_df, api12_df)
        )

        # Should detect systematic discrepancies
        assert engine.processing_stats["significant_discrepancies"] > 0
        assert len(statistical_summary.outlier_wells) > 0

        # Check that statistical tests detect the systematic difference
        drilling_stats = statistical_summary.drilling_days_stats
        if "statistical_tests" in drilling_stats:
            tests = drilling_stats["statistical_tests"]
            if "ttest" in tests:
                assert (
                    tests["ttest"]["significant"] == True
                )  # Should detect systematic difference


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
