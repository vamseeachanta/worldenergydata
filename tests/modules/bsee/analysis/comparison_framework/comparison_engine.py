"""
ComparisonEngine for Drilling Days Analysis

Core comparison logic for analyzing differences between drilling days calculation methods.
"""

import logging
import warnings
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WellCoverageAnalysis:
    """Data structure for well coverage analysis results."""
    total_lease_wells: int
    total_api12_wells: int
    common_wells: int
    lease_only_wells: int
    api12_only_wells: int
    coverage_percentage: float


@dataclass 
class ComparisonResult:
    """Data structure for complete comparison results."""
    total_common_wells: int
    statistics: Dict[str, Dict[str, float]]
    well_coverage: WellCoverageAnalysis
    matched_data: pd.DataFrame
    discrepancies: pd.DataFrame


class ComparisonEngine:
    """
    Core engine for comparing drilling days analysis results between different methods.
    
    This class provides comprehensive comparison functionality including:
    - API number normalization and matching
    - Statistical analysis of differences
    - Well coverage analysis
    - Discrepancy detection and reporting
    """

    def __init__(self, tolerance_config: Optional[Dict[str, float]] = None):
        """
        Initialize the ComparisonEngine.
        
        Args:
            tolerance_config: Dictionary of tolerance values for discrepancy detection
                Expected keys: 'drilling_days', 'completion_days', 'dates'
        """
        self.tolerance_config = tolerance_config or {}
        
        # Validate tolerance config
        if tolerance_config:
            self._validate_tolerance_config(tolerance_config)
        
        logger.info("ComparisonEngine initialized")

    def _validate_tolerance_config(self, tolerance_config: Dict[str, float]) -> None:
        """
        Validate tolerance configuration values.
        
        Args:
            tolerance_config: Tolerance configuration to validate
        """
        for key, value in tolerance_config.items():
            if not isinstance(value, (int, float)) or value < 0:
                warnings.warn(f"Invalid tolerance value for {key}: {value}. Should be non-negative number.")

    def _normalize_api_number(self, api_number: str) -> str:
        """
        Normalize API number to consistent format (API12).
        
        Converts API14 format (14 digits) to API12 format (12 digits) by removing last 2 digits.
        
        Args:
            api_number: API number to normalize
            
        Returns:
            Normalized API number (API12 format)
        """
        if not isinstance(api_number, str):
            api_number = str(api_number)
            
        # Remove any non-digit characters
        api_digits = ''.join(filter(str.isdigit, api_number))
        
        # Convert API14 to API12 format
        if len(api_digits) == 14:
            return api_digits[:12]  # Remove last 2 digits (API14 -> API12)
        elif len(api_digits) == 15:
            return api_digits[:12]  # Remove last 3 digits (API15 -> API12)
        elif len(api_digits) == 12:
            return api_digits  # Already API12 format
        else:
            # Return as-is for non-standard formats
            logger.warning(f"Non-standard API number format: {api_number}")
            return api_digits

    def _prepare_data_for_comparison(
        self, 
        data: pd.DataFrame, 
        method_name: str,
        column_mapping: Dict[str, str]
    ) -> pd.DataFrame:
        """
        Prepare data for comparison by normalizing column names and API numbers.
        
        Args:
            data: Input dataframe
            method_name: Name of the method (for tracking)
            column_mapping: Mapping of standard names to actual column names
            
        Returns:
            Prepared dataframe with normalized columns
        """
        if data.empty:
            logger.warning(f"Empty dataset provided for {method_name}")
            return pd.DataFrame()
            
        # Create copy to avoid modifying original data
        prepared = data.copy()
        
        # Add method identifier
        prepared['method'] = method_name
        
        # Validate that all required columns exist
        missing_columns = []
        for standard_name, actual_name in column_mapping.items():
            if actual_name not in prepared.columns:
                missing_columns.append(f"{standard_name} ('{actual_name}')")
        
        if missing_columns:
            raise KeyError(f"Missing columns in {method_name} data: {', '.join(missing_columns)}")
        
        # Normalize API numbers
        api_col = column_mapping['api']
        prepared['api_normalized'] = prepared[api_col].apply(self._normalize_api_number)
        
        # Rename columns to standard names for easier processing
        rename_mapping = {}
        for standard_name, actual_name in column_mapping.items():
            if standard_name != 'api':  # Keep api_normalized separate
                # Use method prefix (lease or api12)
                method_prefix = method_name.split('_')[0]  # 'lease' or 'api12'
                rename_mapping[actual_name] = f"{standard_name}_{method_prefix}"
        
        prepared = prepared.rename(columns=rename_mapping)
        
        # Validate that required columns exist after mapping
        required_columns = ['api_normalized', 'method']
        missing_columns = [col for col in required_columns if col not in prepared.columns]
        if missing_columns:
            raise KeyError(f"Missing required columns after processing: {missing_columns}")
        
        logger.info(f"Prepared {len(prepared)} records for {method_name}")
        return prepared

    def _identify_common_wells(
        self, 
        lease_data: pd.DataFrame, 
        api12_data: pd.DataFrame
    ) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Identify common wells and wells unique to each method.
        
        Args:
            lease_data: Prepared lease method data
            api12_data: Prepared API12 method data
            
        Returns:
            Tuple of (common_wells, lease_only_wells, api12_only_wells)
        """
        if lease_data.empty or api12_data.empty:
            lease_wells = set(lease_data.get('api_normalized', []))
            api12_wells = set(api12_data.get('api_normalized', []))
            return set(), lease_wells, api12_wells
            
        lease_wells = set(lease_data['api_normalized'])
        api12_wells = set(api12_data['api_normalized'])
        
        common_wells = lease_wells.intersection(api12_wells)
        lease_only_wells = lease_wells - api12_wells
        api12_only_wells = api12_wells - lease_wells
        
        logger.info(
            f"Well analysis: {len(common_wells)} common, "
            f"{len(lease_only_wells)} lease-only, {len(api12_only_wells)} api12-only"
        )
        
        return common_wells, lease_only_wells, api12_only_wells

    def _calculate_differences(self, matched_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate differences between methods for matched wells.
        
        Args:
            matched_data: DataFrame with matched wells from both methods
            
        Returns:
            DataFrame with calculated differences
        """
        differences = matched_data.copy()
        
        # Calculate drilling days differences
        if 'drilling_days_lease' in differences.columns and 'drilling_days_api12' in differences.columns:
            differences['drilling_days_diff'] = (
                differences['drilling_days_lease'] - differences['drilling_days_api12']
            )
            differences['drilling_days_abs_diff'] = abs(differences['drilling_days_diff'])
        
        # Calculate completion days differences
        if 'completion_days_lease' in differences.columns and 'completion_days_api12' in differences.columns:
            differences['completion_days_diff'] = (
                differences['completion_days_lease'] - differences['completion_days_api12']
            )
            differences['completion_days_abs_diff'] = abs(differences['completion_days_diff'])
        
        # Calculate date differences if available
        for date_type in ['spud_date', 'td_date']:
            lease_col = f"{date_type}_lease"
            api12_col = f"{date_type}_api12"
            
            if lease_col in differences.columns and api12_col in differences.columns:
                try:
                    lease_dates = pd.to_datetime(differences[lease_col])
                    api12_dates = pd.to_datetime(differences[api12_col])
                    
                    differences[f"{date_type}_date_diff_days"] = (
                        (lease_dates - api12_dates).dt.days
                    )
                    differences[f"{date_type}_date_abs_diff_days"] = abs(
                        differences[f"{date_type}_date_diff_days"]
                    )
                except Exception as e:
                    logger.warning(f"Error calculating {date_type} date differences: {e}")
        
        logger.info(f"Calculated differences for {len(differences)} matched wells")
        return differences

    def _calculate_statistics(self, differences: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Calculate statistical summaries of differences.
        
        Args:
            differences: DataFrame with calculated differences
            
        Returns:
            Dictionary of statistics for each metric
        """
        statistics = {}
        
        # Define metrics to analyze
        metrics = {
            'drilling_days': ['drilling_days_diff', 'drilling_days_abs_diff'],
            'completion_days': ['completion_days_diff', 'completion_days_abs_diff'],
        }
        
        for metric_name, columns in metrics.items():
            diff_col, abs_diff_col = columns
            
            if diff_col in differences.columns and abs_diff_col in differences.columns:
                diff_values = differences[diff_col].dropna()
                abs_diff_values = differences[abs_diff_col].dropna()
                
                if len(diff_values) > 0:
                    statistics[metric_name] = {
                        'count': len(diff_values),
                        'mean': float(diff_values.mean()),
                        'std': float(diff_values.std()) if len(diff_values) > 1 else 0.0,
                        'median': float(diff_values.median()),
                        'min': float(diff_values.min()),
                        'max': float(diff_values.max()),
                        'mean_abs_diff': float(abs_diff_values.mean()),
                        'max_abs_diff': float(abs_diff_values.max()),
                        'q25': float(diff_values.quantile(0.25)),
                        'q75': float(diff_values.quantile(0.75))
                    }
                else:
                    statistics[metric_name] = {
                        'count': 0,
                        'mean': 0.0,
                        'std': 0.0,
                        'median': 0.0,
                        'min': 0.0,
                        'max': 0.0,
                        'mean_abs_diff': 0.0,
                        'max_abs_diff': 0.0,
                        'q25': 0.0,
                        'q75': 0.0
                    }
        
        logger.info(f"Calculated statistics for {len(statistics)} metrics")
        return statistics

    def _identify_discrepancies(
        self, 
        differences: pd.DataFrame, 
        tolerance: Dict[str, float]
    ) -> pd.DataFrame:
        """
        Identify wells with discrepancies beyond tolerance thresholds.
        
        Args:
            differences: DataFrame with calculated differences
            tolerance: Tolerance thresholds for each metric
            
        Returns:
            DataFrame containing only wells with discrepancies
        """
        if differences.empty:
            return pd.DataFrame()
            
        discrepancy_mask = pd.Series([False] * len(differences))
        
        # Check drilling days tolerance
        if 'drilling_days' in tolerance and 'drilling_days_abs_diff' in differences.columns:
            drilling_threshold = tolerance['drilling_days']
            drilling_discrepancies = differences['drilling_days_abs_diff'] > drilling_threshold
            discrepancy_mask = discrepancy_mask | drilling_discrepancies
            logger.info(f"Found {drilling_discrepancies.sum()} drilling days discrepancies (threshold: {drilling_threshold})")
        
        # Check completion days tolerance
        if 'completion_days' in tolerance and 'completion_days_abs_diff' in differences.columns:
            completion_threshold = tolerance['completion_days']
            completion_discrepancies = differences['completion_days_abs_diff'] > completion_threshold
            discrepancy_mask = discrepancy_mask | completion_discrepancies
            logger.info(f"Found {completion_discrepancies.sum()} completion days discrepancies (threshold: {completion_threshold})")
        
        # Check date tolerance if specified
        if 'dates' in tolerance:
            date_threshold = tolerance['dates']
            for date_type in ['spud', 'td']:
                date_col = f"{date_type}_date_abs_diff_days"
                if date_col in differences.columns:
                    date_discrepancies = differences[date_col] > date_threshold
                    discrepancy_mask = discrepancy_mask | date_discrepancies
                    logger.info(f"Found {date_discrepancies.sum()} {date_type} date discrepancies (threshold: {date_threshold})")
        
        discrepancies = differences[discrepancy_mask].copy()
        logger.info(f"Total wells with discrepancies: {len(discrepancies)}")
        
        return discrepancies

    def _analyze_well_coverage(
        self, 
        lease_data: pd.DataFrame, 
        api12_data: pd.DataFrame
    ) -> WellCoverageAnalysis:
        """
        Analyze well coverage between the two methods.
        
        Args:
            lease_data: Prepared lease method data
            api12_data: Prepared API12 method data
            
        Returns:
            WellCoverageAnalysis object with coverage metrics
        """
        total_lease_wells = len(lease_data) if not lease_data.empty else 0
        total_api12_wells = len(api12_data) if not api12_data.empty else 0
        
        if total_lease_wells == 0 and total_api12_wells == 0:
            return WellCoverageAnalysis(
                total_lease_wells=0,
                total_api12_wells=0,
                common_wells=0,
                lease_only_wells=0,
                api12_only_wells=0,
                coverage_percentage=0.0
            )
        
        common_wells, lease_only_wells, api12_only_wells = self._identify_common_wells(
            lease_data, api12_data
        )
        
        # Calculate coverage percentage (common wells / total unique wells)
        total_unique_wells = len(common_wells) + len(lease_only_wells) + len(api12_only_wells)
        coverage_percentage = (len(common_wells) / total_unique_wells * 100) if total_unique_wells > 0 else 0.0
        
        return WellCoverageAnalysis(
            total_lease_wells=total_lease_wells,
            total_api12_wells=total_api12_wells,
            common_wells=len(common_wells),
            lease_only_wells=len(lease_only_wells),
            api12_only_wells=len(api12_only_wells),
            coverage_percentage=coverage_percentage
        )

    def compare_methods(
        self,
        lease_data: pd.DataFrame,
        api12_data: pd.DataFrame,
        column_mapping: Dict[str, Dict[str, str]],
        tolerance: Optional[Dict[str, float]] = None
    ) -> ComparisonResult:
        """
        Compare drilling days analysis results between lease and API12 methods.
        
        Args:
            lease_data: DataFrame from lease method
            api12_data: DataFrame from API12 method  
            column_mapping: Column mapping for both methods
            tolerance: Tolerance thresholds for discrepancy detection
            
        Returns:
            ComparisonResult object with complete analysis
        """
        logger.info("Starting comprehensive method comparison")
        
        # Use provided tolerance or fall back to instance config
        tolerance = tolerance or self.tolerance_config
        
        # Prepare data for both methods
        lease_prepared = self._prepare_data_for_comparison(
            lease_data, 'lease_method', column_mapping['lease_method']
        )
        
        api12_prepared = self._prepare_data_for_comparison(
            api12_data, 'api12_method', column_mapping['api12_method']
        )
        
        # Analyze well coverage
        well_coverage = self._analyze_well_coverage(lease_prepared, api12_prepared)
        
        if well_coverage.common_wells == 0:
            logger.warning("No common wells found between methods")
            return ComparisonResult(
                total_common_wells=0,
                statistics={},
                well_coverage=well_coverage,
                matched_data=pd.DataFrame(),
                discrepancies=pd.DataFrame()
            )
        
        # Match wells between methods
        common_wells, _, _ = self._identify_common_wells(lease_prepared, api12_prepared)
        
        # Filter data to common wells only
        lease_common = lease_prepared[lease_prepared['api_normalized'].isin(common_wells)]
        api12_common = api12_prepared[api12_prepared['api_normalized'].isin(common_wells)]
        
        # Merge data on normalized API numbers
        matched_data = pd.merge(
            lease_common, 
            api12_common, 
            on='api_normalized', 
            how='inner',
            suffixes=('_lease', '_api12')
        )
        
        logger.info(f"Successfully matched {len(matched_data)} wells")
        
        # Calculate differences
        differences = self._calculate_differences(matched_data)
        
        # Calculate statistics
        statistics = self._calculate_statistics(differences)
        
        # Identify discrepancies
        discrepancies = self._identify_discrepancies(differences, tolerance)
        
        result = ComparisonResult(
            total_common_wells=len(matched_data),
            statistics=statistics,
            well_coverage=well_coverage,
            matched_data=differences,
            discrepancies=discrepancies
        )
        
        logger.info(
            f"Comparison completed: {result.total_common_wells} common wells, "
            f"{len(discrepancies)} discrepancies found"
        )
        
        return result

    def generate_summary_report(self, result: ComparisonResult) -> Dict[str, Any]:
        """
        Generate a summary report from comparison results.
        
        Args:
            result: ComparisonResult object
            
        Returns:
            Dictionary containing summary report data
        """
        if result.total_common_wells == 0:
            return {
                'summary': 'No common wells found for comparison',
                'well_coverage': result.well_coverage,
                'recommendations': ['Check API number formats', 'Verify data sources alignment']
            }
        
        # Generate summary statistics
        summary_stats = {}
        for metric, stats in result.statistics.items():
            if stats['count'] > 0:
                summary_stats[metric] = {
                    'mean_difference': stats['mean'],
                    'mean_absolute_difference': stats['mean_abs_diff'],
                    'standard_deviation': stats['std'],
                    'max_absolute_difference': stats['max_abs_diff']
                }
        
        # Generate recommendations based on analysis
        recommendations = []
        
        for metric, stats in result.statistics.items():
            if stats['count'] > 0:
                if stats['mean_abs_diff'] > 5:  # More than 5 days average difference
                    recommendations.append(f"High average difference in {metric}: {stats['mean_abs_diff']:.1f} days")
                
                if stats['max_abs_diff'] > 20:  # Large maximum difference
                    recommendations.append(f"Large maximum difference in {metric}: {stats['max_abs_diff']:.1f} days")
        
        if result.well_coverage.coverage_percentage < 80:
            recommendations.append(f"Low well coverage: {result.well_coverage.coverage_percentage:.1f}%")
        
        if len(result.discrepancies) > 0:
            discrepancy_rate = len(result.discrepancies) / result.total_common_wells * 100
            recommendations.append(f"Discrepancy rate: {discrepancy_rate:.1f}% of wells")
        
        return {
            'summary': f"Compared {result.total_common_wells} common wells between methods",
            'well_coverage': result.well_coverage,
            'statistics': summary_stats,
            'discrepancy_count': len(result.discrepancies),
            'discrepancy_rate': len(result.discrepancies) / result.total_common_wells * 100 if result.total_common_wells > 0 else 0,
            'recommendations': recommendations or ['Methods show good agreement']
        }