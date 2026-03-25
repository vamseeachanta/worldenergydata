"""
Advanced Comparison Analysis Engine for Multiple Wells

This module provides advanced statistical comparison and analysis capabilities
for handling 120+ wells from different BSEE data processing methods.
"""

import json
import logging
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=RuntimeWarning)


@dataclass
class ComparisonConfig:
    """Configuration for comparison analysis operations."""

    outlier_threshold_std: float = 2.5  # Standard deviations for outlier detection
    outlier_threshold_iqr: float = 1.5  # IQR multiplier for outlier detection
    discrepancy_absolute_threshold: float = 5.0  # Days
    discrepancy_percentage_threshold: float = 10.0  # Percent
    enable_clustering: bool = True
    clustering_eps: float = 0.5
    clustering_min_samples: int = 5
    statistical_confidence_level: float = 0.95
    enable_detailed_logging: bool = True
    results_directory: str = (
        "tests/modules/bsee/analysis/multiple_wells_comparison_test/results"
    )


@dataclass
class ComparisonResult:
    """Data class for storing comparison results."""

    api12: str
    well_name: str
    lease_drilling_days: Optional[float]
    api12_drilling_days: Optional[float]
    lease_completion_days: Optional[float]
    api12_completion_days: Optional[float]
    drilling_diff: Optional[float]
    completion_diff: Optional[float]
    drilling_pct_diff: Optional[float]
    completion_pct_diff: Optional[float]
    overall_status: str
    outlier_flags: List[str]
    statistical_significance: Dict[str, float]


@dataclass
class StatisticalSummary:
    """Statistical summary of comparison results."""

    total_wells: int
    successful_matches: int
    drilling_days_stats: Dict[str, float]
    completion_days_stats: Dict[str, float]
    outlier_wells: List[str]
    cluster_analysis: Dict[str, Any]
    correlation_analysis: Dict[str, float]
    distribution_comparison: Dict[str, Any]


class OutlierDetector:
    """Advanced outlier detection for well comparison data."""

    def __init__(self, config: ComparisonConfig):
        """
        Initialize outlier detector.

        Args:
            config: Comparison configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def detect_outliers_statistical(
        self, data: pd.Series, method: str = "zscore"
    ) -> Dict[str, Any]:
        """
        Detect outliers using statistical methods.

        Args:
            data: Series of numerical data
            method: Method to use ('zscore', 'iqr', 'modified_zscore')

        Returns:
            Dict containing outlier detection results
        """
        if data.empty or data.isnull().all():
            return {"outlier_indices": [], "outlier_values": [], "method": method}

        clean_data = data.dropna()

        if method == "zscore":
            z_scores = np.abs(stats.zscore(clean_data))
            outlier_mask = z_scores > self.config.outlier_threshold_std

        elif method == "iqr":
            Q1 = clean_data.quantile(0.25)
            Q3 = clean_data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - self.config.outlier_threshold_iqr * IQR
            upper_bound = Q3 + self.config.outlier_threshold_iqr * IQR
            outlier_mask = (clean_data < lower_bound) | (clean_data > upper_bound)

        elif method == "modified_zscore":
            median = clean_data.median()
            mad = np.median(np.abs(clean_data - median))
            modified_z_scores = 0.6745 * (clean_data - median) / mad
            outlier_mask = np.abs(modified_z_scores) > self.config.outlier_threshold_std

        else:
            raise ValueError(f"Unknown outlier detection method: {method}")

        outlier_indices = clean_data.index[outlier_mask].tolist()
        outlier_values = clean_data[outlier_mask].tolist()

        return {
            "outlier_indices": outlier_indices,
            "outlier_values": outlier_values,
            "method": method,
            "threshold": (
                self.config.outlier_threshold_std
                if method != "iqr"
                else self.config.outlier_threshold_iqr
            ),
            "outlier_count": len(outlier_indices),
            "outlier_percentage": (
                (len(outlier_indices) / len(clean_data)) * 100
                if len(clean_data) > 0
                else 0
            ),
        }

    def detect_outliers_clustering(
        self, df: pd.DataFrame, features: List[str]
    ) -> Dict[str, Any]:
        """
        Detect outliers using clustering (DBSCAN).

        Args:
            df: DataFrame with well data
            features: List of feature columns to use for clustering

        Returns:
            Dict containing clustering results
        """
        if not self.config.enable_clustering:
            return {"method": "clustering_disabled"}

        # Prepare data for clustering
        feature_data = df[features].dropna()

        if len(feature_data) < self.config.clustering_min_samples:
            return {
                "method": "clustering",
                "status": "insufficient_data",
                "min_samples_required": self.config.clustering_min_samples,
                "available_samples": len(feature_data),
            }

        # Standardize features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(feature_data)

        # Apply DBSCAN clustering
        dbscan = DBSCAN(
            eps=self.config.clustering_eps,
            min_samples=self.config.clustering_min_samples,
        )
        cluster_labels = dbscan.fit_predict(scaled_features)

        # Identify outliers (points labeled as -1)
        outlier_mask = cluster_labels == -1
        outlier_indices = feature_data.index[outlier_mask].tolist()

        # Cluster statistics
        unique_clusters = np.unique(cluster_labels[cluster_labels != -1])
        cluster_sizes = [
            np.sum(cluster_labels == cluster) for cluster in unique_clusters
        ]

        return {
            "method": "clustering",
            "outlier_indices": outlier_indices,
            "outlier_count": len(outlier_indices),
            "outlier_percentage": (len(outlier_indices) / len(feature_data)) * 100,
            "num_clusters": len(unique_clusters),
            "cluster_sizes": cluster_sizes,
            "noise_points": len(outlier_indices),
            "eps": self.config.clustering_eps,
            "min_samples": self.config.clustering_min_samples,
        }


class StatisticalAnalyzer:
    """Advanced statistical analysis for well comparison data."""

    def __init__(self, config: ComparisonConfig):
        """
        Initialize statistical analyzer.

        Args:
            config: Comparison configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def analyze_distributions(
        self, lease_data: pd.Series, api12_data: pd.Series, metric_name: str
    ) -> Dict[str, Any]:
        """
        Analyze and compare distributions between two methods.

        Args:
            lease_data: Data from lease method
            api12_data: Data from API12 method
            metric_name: Name of the metric being analyzed

        Returns:
            Dict containing distribution analysis results
        """
        # Basic statistics
        lease_stats = self._calculate_descriptive_stats(
            lease_data, f"lease_{metric_name}"
        )
        api12_stats = self._calculate_descriptive_stats(
            api12_data, f"api12_{metric_name}"
        )

        # Statistical tests
        statistical_tests = self._perform_statistical_tests(lease_data, api12_data)

        # Distribution comparison
        distribution_comparison = {
            "lease_method": lease_stats,
            "api12_method": api12_stats,
            "statistical_tests": statistical_tests,
            "difference_analysis": self._analyze_differences(lease_data, api12_data),
        }

        return distribution_comparison

    def _calculate_descriptive_stats(
        self, data: pd.Series, name: str
    ) -> Dict[str, float]:
        """Calculate descriptive statistics for a data series."""
        clean_data = data.dropna()

        if clean_data.empty:
            return {"name": name, "count": 0, "error": "no_data"}

        stats_dict = {
            "name": name,
            "count": len(clean_data),
            "mean": clean_data.mean(),
            "median": clean_data.median(),
            "std": clean_data.std(),
            "min": clean_data.min(),
            "max": clean_data.max(),
            "q25": clean_data.quantile(0.25),
            "q75": clean_data.quantile(0.75),
            "skewness": stats.skew(clean_data),
            "kurtosis": stats.kurtosis(clean_data),
        }

        return stats_dict

    def _perform_statistical_tests(
        self, data1: pd.Series, data2: pd.Series
    ) -> Dict[str, Any]:
        """Perform statistical tests comparing two datasets."""
        clean_data1 = data1.dropna()
        clean_data2 = data2.dropna()

        if clean_data1.empty or clean_data2.empty:
            return {"error": "insufficient_data"}

        results = {}

        # Normality tests
        try:
            shapiro1 = stats.shapiro(clean_data1.sample(min(5000, len(clean_data1))))
            shapiro2 = stats.shapiro(clean_data2.sample(min(5000, len(clean_data2))))
            results["normality_test"] = {
                "data1_normal": shapiro1.pvalue > 0.05,
                "data2_normal": shapiro2.pvalue > 0.05,
                "data1_pvalue": shapiro1.pvalue,
                "data2_pvalue": shapiro2.pvalue,
            }
        except Exception as e:
            results["normality_test"] = {"error": str(e)}

        # Two-sample tests
        try:
            # T-test (parametric)
            ttest_result = stats.ttest_ind(clean_data1, clean_data2)
            results["ttest"] = {
                "statistic": ttest_result.statistic,
                "pvalue": ttest_result.pvalue,
                "significant": ttest_result.pvalue
                < (1 - self.config.statistical_confidence_level),
            }

            # Mann-Whitney U test (non-parametric)
            mannwhitney_result = stats.mannwhitneyu(
                clean_data1, clean_data2, alternative="two-sided"
            )
            results["mannwhitney"] = {
                "statistic": mannwhitney_result.statistic,
                "pvalue": mannwhitney_result.pvalue,
                "significant": mannwhitney_result.pvalue
                < (1 - self.config.statistical_confidence_level),
            }

            # Kolmogorov-Smirnov test
            ks_result = stats.ks_2samp(clean_data1, clean_data2)
            results["kolmogorov_smirnov"] = {
                "statistic": ks_result.statistic,
                "pvalue": ks_result.pvalue,
                "significant": ks_result.pvalue
                < (1 - self.config.statistical_confidence_level),
            }

        except Exception as e:
            results["statistical_tests_error"] = str(e)

        return results

    def _analyze_differences(
        self, data1: pd.Series, data2: pd.Series
    ) -> Dict[str, Any]:
        """Analyze differences between two datasets."""
        # Align the series by index
        aligned_data = pd.DataFrame({"data1": data1, "data2": data2}).dropna()

        if aligned_data.empty:
            return {"error": "no_aligned_data"}

        differences = aligned_data["data2"] - aligned_data["data1"]
        percentage_diffs = (differences / aligned_data["data1"]) * 100
        percentage_diffs = percentage_diffs.replace([np.inf, -np.inf], np.nan).dropna()

        return {
            "mean_difference": differences.mean(),
            "median_difference": differences.median(),
            "std_difference": differences.std(),
            "mean_percentage_difference": percentage_diffs.mean(),
            "median_percentage_difference": percentage_diffs.median(),
            "std_percentage_difference": percentage_diffs.std(),
            "correlation": aligned_data["data1"].corr(aligned_data["data2"]),
            "agreement_within_5_days": (np.abs(differences) <= 5).sum(),
            "agreement_within_10_percent": (
                (np.abs(percentage_diffs) <= 10).sum()
                if not percentage_diffs.empty
                else 0
            ),
        }

    def calculate_effect_size(
        self, data1: pd.Series, data2: pd.Series
    ) -> Dict[str, float]:
        """Calculate effect size measures."""
        clean_data1 = data1.dropna()
        clean_data2 = data2.dropna()

        if clean_data1.empty or clean_data2.empty:
            return {"error": "insufficient_data"}

        # Cohen's d
        pooled_std = np.sqrt(
            (
                (len(clean_data1) - 1) * clean_data1.var()
                + (len(clean_data2) - 1) * clean_data2.var()
            )
            / (len(clean_data1) + len(clean_data2) - 2)
        )

        cohens_d = (
            (clean_data1.mean() - clean_data2.mean()) / pooled_std
            if pooled_std > 0
            else 0
        )

        # Glass's delta
        glass_delta = (
            (clean_data1.mean() - clean_data2.mean()) / clean_data1.std()
            if clean_data1.std() > 0
            else 0
        )

        return {
            "cohens_d": cohens_d,
            "glass_delta": glass_delta,
            "effect_size_interpretation": self._interpret_effect_size(abs(cohens_d)),
        }

    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret effect size magnitude."""
        if effect_size < 0.2:
            return "negligible"
        elif effect_size < 0.5:
            return "small"
        elif effect_size < 0.8:
            return "medium"
        else:
            return "large"


class AdvancedComparisonEngine:
    """
    Advanced comparison analysis engine optimized for multiple wells processing.
    """

    def __init__(self, config: Optional[ComparisonConfig] = None):
        """
        Initialize the advanced comparison engine.

        Args:
            config: Configuration for comparison operations
        """
        self.config = config or ComparisonConfig()
        self.outlier_detector = OutlierDetector(self.config)
        self.statistical_analyzer = StatisticalAnalyzer(self.config)

        # Setup logging
        if self.config.enable_detailed_logging:
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
            )
            self.logger = logging.getLogger(__name__)

        # Initialize results storage
        Path(self.config.results_directory).mkdir(parents=True, exist_ok=True)

        # Processing statistics
        self.processing_stats = {
            "total_wells_analyzed": 0,
            "successful_comparisons": 0,
            "failed_comparisons": 0,
            "outliers_detected": 0,
            "significant_discrepancies": 0,
            "processing_time_seconds": 0,
        }

    def perform_comprehensive_comparison(
        self, lease_df: pd.DataFrame, api12_df: pd.DataFrame
    ) -> Tuple[List[ComparisonResult], StatisticalSummary]:
        """
        Perform comprehensive comparison analysis between lease and API12 methods.

        Args:
            lease_df: DataFrame with lease method data
            api12_df: DataFrame with API12 method data

        Returns:
            Tuple of comparison results and statistical summary
        """
        start_time = datetime.now()

        if self.config.enable_detailed_logging:
            self.logger.info(
                f"Starting comprehensive comparison: {len(lease_df)} lease wells, {len(api12_df)} API12 wells"
            )

        # Data matching and alignment
        aligned_data = self._match_and_align_data(lease_df, api12_df)

        if aligned_data.empty:
            raise ValueError("No matching wells found between datasets")

        # Individual well comparisons
        comparison_results = self._perform_individual_comparisons(aligned_data)

        # Statistical analysis
        statistical_summary = self._generate_statistical_summary(
            aligned_data, comparison_results
        )

        # Update processing statistics
        end_time = datetime.now()
        self.processing_stats["processing_time_seconds"] = (
            end_time - start_time
        ).total_seconds()
        self.processing_stats["total_wells_analyzed"] = len(comparison_results)

        if self.config.enable_detailed_logging:
            self.logger.info(
                f"Comparison completed in {self.processing_stats['processing_time_seconds']:.2f} seconds"
            )

        return comparison_results, statistical_summary

    def _match_and_align_data(
        self, lease_df: pd.DataFrame, api12_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Match and align data between lease and API12 methods."""
        # Standardize API12 column names
        lease_cols = {
            "API12": "API12",
            "Well Name": "Well_Name_Lease",
            "Drilling Days": "Drilling_Days_Lease",
            "Completion Days": "Completion_Days_Lease",
        }

        api12_cols = {
            "API12": "API12",
            "Well Name": "Well_Name_API12",
            "Drilling Days": "Drilling_Days_API12",
            "Completion Days": "Completion_Days_API12",
        }

        # Rename columns for clarity
        lease_clean = lease_df.rename(columns=lease_cols)
        api12_clean = api12_df.rename(columns=api12_cols)

        # Merge on API12
        aligned_data = pd.merge(
            lease_clean, api12_clean, on="API12", how="outer", indicator=True
        )

        # Log matching statistics
        both_count = (aligned_data["_merge"] == "both").sum()
        lease_only_count = (aligned_data["_merge"] == "left_only").sum()
        api12_only_count = (aligned_data["_merge"] == "right_only").sum()

        if self.config.enable_detailed_logging:
            self.logger.info(
                f"Data alignment: {both_count} matches, {lease_only_count} lease-only, {api12_only_count} API12-only"
            )

        return aligned_data

    def _perform_individual_comparisons(
        self, aligned_data: pd.DataFrame
    ) -> List[ComparisonResult]:
        """Perform individual well comparisons."""
        comparison_results = []

        for _, row in aligned_data.iterrows():
            try:
                result = self._compare_individual_well(row)
                comparison_results.append(result)
                self.processing_stats["successful_comparisons"] += 1
            except Exception as e:
                self.processing_stats["failed_comparisons"] += 1
                if self.config.enable_detailed_logging:
                    self.logger.warning(
                        f"Failed to compare well {row.get('API12', 'Unknown')}: {str(e)}"
                    )

        return comparison_results

    def _compare_individual_well(self, row: pd.Series) -> ComparisonResult:
        """Compare individual well data between methods."""
        api12 = str(row.get("API12", ""))
        well_name = row.get("Well_Name_Lease", "") or row.get("Well_Name_API12", "")

        # Extract values
        lease_drilling = row.get("Drilling_Days_Lease")
        api12_drilling = row.get("Drilling_Days_API12")
        lease_completion = row.get("Completion_Days_Lease")
        api12_completion = row.get("Completion_Days_API12")

        # Calculate differences
        drilling_diff = None
        completion_diff = None
        drilling_pct_diff = None
        completion_pct_diff = None

        if pd.notna(lease_drilling) and pd.notna(api12_drilling):
            drilling_diff = api12_drilling - lease_drilling
            if lease_drilling != 0:
                drilling_pct_diff = (drilling_diff / lease_drilling) * 100

        if pd.notna(lease_completion) and pd.notna(api12_completion):
            completion_diff = api12_completion - lease_completion
            if lease_completion != 0:
                completion_pct_diff = (completion_diff / lease_completion) * 100

        # Determine status and outlier flags
        status, outlier_flags = self._determine_well_status(
            drilling_diff, completion_diff, drilling_pct_diff, completion_pct_diff
        )

        # Statistical significance (placeholder for individual well analysis)
        statistical_significance = self._calculate_well_significance(
            lease_drilling, api12_drilling, lease_completion, api12_completion
        )

        return ComparisonResult(
            api12=api12,
            well_name=well_name,
            lease_drilling_days=lease_drilling,
            api12_drilling_days=api12_drilling,
            lease_completion_days=lease_completion,
            api12_completion_days=api12_completion,
            drilling_diff=drilling_diff,
            completion_diff=completion_diff,
            drilling_pct_diff=drilling_pct_diff,
            completion_pct_diff=completion_pct_diff,
            overall_status=status,
            outlier_flags=outlier_flags,
            statistical_significance=statistical_significance,
        )

    def _determine_well_status(
        self,
        drilling_diff: Optional[float],
        completion_diff: Optional[float],
        drilling_pct_diff: Optional[float],
        completion_pct_diff: Optional[float],
    ) -> Tuple[str, List[str]]:
        """Determine well status and outlier flags."""
        outlier_flags = []
        issues = 0

        # Check drilling days
        if drilling_diff is not None:
            if abs(drilling_diff) > self.config.discrepancy_absolute_threshold:
                outlier_flags.append("drilling_absolute_outlier")
                issues += 1

        if drilling_pct_diff is not None:
            if abs(drilling_pct_diff) > self.config.discrepancy_percentage_threshold:
                outlier_flags.append("drilling_percentage_outlier")
                issues += 1

        # Check completion days
        if completion_diff is not None:
            if abs(completion_diff) > self.config.discrepancy_absolute_threshold:
                outlier_flags.append("completion_absolute_outlier")
                issues += 1

        if completion_pct_diff is not None:
            if abs(completion_pct_diff) > self.config.discrepancy_percentage_threshold:
                outlier_flags.append("completion_percentage_outlier")
                issues += 1

        # Determine overall status
        if issues >= 3:
            status = "ERROR"
            self.processing_stats["significant_discrepancies"] += 1
        elif issues >= 1:
            status = "REVIEW"
        else:
            status = "OK"

        if outlier_flags:
            self.processing_stats["outliers_detected"] += 1

        return status, outlier_flags

    def _calculate_well_significance(
        self,
        lease_drilling: Optional[float],
        api12_drilling: Optional[float],
        lease_completion: Optional[float],
        api12_completion: Optional[float],
    ) -> Dict[str, float]:
        """Calculate statistical significance for individual well (placeholder)."""
        # This is a simplified placeholder for individual well significance
        # In practice, this might involve comparison with population statistics
        return {
            "drilling_z_score": 0.0,
            "completion_z_score": 0.0,
            "confidence_level": self.config.statistical_confidence_level,
        }

    def _generate_statistical_summary(
        self, aligned_data: pd.DataFrame, comparison_results: List[ComparisonResult]
    ) -> StatisticalSummary:
        """Generate comprehensive statistical summary."""
        # Extract data for analysis
        lease_drilling = aligned_data["Drilling_Days_Lease"].dropna()
        api12_drilling = aligned_data["Drilling_Days_API12"].dropna()
        lease_completion = aligned_data["Completion_Days_Lease"].dropna()
        api12_completion = aligned_data["Completion_Days_API12"].dropna()

        # Distribution analysis
        drilling_analysis = self.statistical_analyzer.analyze_distributions(
            lease_drilling, api12_drilling, "drilling_days"
        )

        completion_analysis = self.statistical_analyzer.analyze_distributions(
            lease_completion, api12_completion, "completion_days"
        )

        # Outlier detection
        drilling_outliers = self.outlier_detector.detect_outliers_statistical(
            pd.Series(
                [
                    r.drilling_diff
                    for r in comparison_results
                    if r.drilling_diff is not None
                ]
            ),
            method="zscore",
        )

        completion_outliers = self.outlier_detector.detect_outliers_statistical(
            pd.Series(
                [
                    r.completion_diff
                    for r in comparison_results
                    if r.completion_diff is not None
                ]
            ),
            method="zscore",
        )

        # Clustering analysis
        clustering_data = pd.DataFrame(
            [
                {
                    "drilling_diff": r.drilling_diff or 0,
                    "completion_diff": r.completion_diff or 0,
                    "drilling_pct_diff": r.drilling_pct_diff or 0,
                    "completion_pct_diff": r.completion_pct_diff or 0,
                }
                for r in comparison_results
            ]
        )

        cluster_analysis = self.outlier_detector.detect_outliers_clustering(
            clustering_data, ["drilling_diff", "completion_diff"]
        )

        # Correlation analysis
        correlation_analysis = self._perform_correlation_analysis(aligned_data)

        # Collect outlier wells
        outlier_wells = [r.api12 for r in comparison_results if r.outlier_flags]

        return StatisticalSummary(
            total_wells=len(comparison_results),
            successful_matches=len(
                [
                    r
                    for r in comparison_results
                    if r.overall_status in ["OK", "REVIEW", "ERROR"]
                ]
            ),
            drilling_days_stats=drilling_analysis,
            completion_days_stats=completion_analysis,
            outlier_wells=outlier_wells,
            cluster_analysis=cluster_analysis,
            correlation_analysis=correlation_analysis,
            distribution_comparison={
                "drilling_outliers": drilling_outliers,
                "completion_outliers": completion_outliers,
            },
        )

    def _perform_correlation_analysis(
        self, aligned_data: pd.DataFrame
    ) -> Dict[str, float]:
        """Perform correlation analysis between methods."""
        correlations = {}

        # Drilling days correlation
        if (
            "Drilling_Days_Lease" in aligned_data.columns
            and "Drilling_Days_API12" in aligned_data.columns
        ):
            drilling_corr = (
                aligned_data[["Drilling_Days_Lease", "Drilling_Days_API12"]]
                .corr()
                .iloc[0, 1]
            )
            correlations["drilling_days"] = (
                drilling_corr if not pd.isna(drilling_corr) else 0.0
            )

        # Completion days correlation
        if (
            "Completion_Days_Lease" in aligned_data.columns
            and "Completion_Days_API12" in aligned_data.columns
        ):
            completion_corr = (
                aligned_data[["Completion_Days_Lease", "Completion_Days_API12"]]
                .corr()
                .iloc[0, 1]
            )
            correlations["completion_days"] = (
                completion_corr if not pd.isna(completion_corr) else 0.0
            )

        return correlations

    def export_detailed_results(
        self,
        comparison_results: List[ComparisonResult],
        statistical_summary: StatisticalSummary,
    ) -> Dict[str, str]:
        """Export detailed comparison results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export individual results to CSV
        results_df = pd.DataFrame(
            [
                {
                    "API12": r.api12,
                    "Well_Name": r.well_name,
                    "Lease_Drilling_Days": r.lease_drilling_days,
                    "API12_Drilling_Days": r.api12_drilling_days,
                    "Lease_Completion_Days": r.lease_completion_days,
                    "API12_Completion_Days": r.api12_completion_days,
                    "Drilling_Diff": r.drilling_diff,
                    "Completion_Diff": r.completion_diff,
                    "Drilling_Pct_Diff": r.drilling_pct_diff,
                    "Completion_Pct_Diff": r.completion_pct_diff,
                    "Status": r.overall_status,
                    "Outlier_Flags": ",".join(r.outlier_flags),
                }
                for r in comparison_results
            ]
        )

        csv_path = (
            Path(self.config.results_directory)
            / f"advanced_comparison_results_{timestamp}.csv"
        )
        results_df.to_csv(csv_path, index=False)

        # Export statistical summary to JSON
        summary_dict = {
            "timestamp": timestamp,
            "total_wells": statistical_summary.total_wells,
            "successful_matches": statistical_summary.successful_matches,
            "drilling_days_stats": statistical_summary.drilling_days_stats,
            "completion_days_stats": statistical_summary.completion_days_stats,
            "outlier_wells_count": len(statistical_summary.outlier_wells),
            "cluster_analysis": statistical_summary.cluster_analysis,
            "correlation_analysis": statistical_summary.correlation_analysis,
            "processing_stats": self.processing_stats,
        }

        json_path = (
            Path(self.config.results_directory)
            / f"statistical_summary_{timestamp}.json"
        )
        with open(json_path, "w") as f:
            json.dump(summary_dict, f, indent=2, default=str)

        return {"csv_results": str(csv_path), "json_summary": str(json_path)}


if __name__ == "__main__":
    # Example usage
    config = ComparisonConfig(
        outlier_threshold_std=2.0,
        discrepancy_absolute_threshold=7.0,
        discrepancy_percentage_threshold=15.0,
        enable_clustering=True,
        enable_detailed_logging=True,
    )

    engine = AdvancedComparisonEngine(config)

    print("Advanced Comparison Engine initialized successfully!")
    print(
        f"Configuration: outlier_threshold={config.outlier_threshold_std}, discrepancy_threshold={config.discrepancy_absolute_threshold} days"
    )
