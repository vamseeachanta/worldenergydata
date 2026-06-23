"""
Cross-regional comparison module for SODIR and BSEE data.

This module enables comparison and analysis between Norwegian Continental Shelf (SODIR)
and US Gulf of Mexico (BSEE) offshore petroleum operations.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class NormalizationStrategy(Enum):
    """Normalization strategies for cross-regional data"""

    STANDARD = "standard"  # Z-score normalization
    MIN_MAX = "min_max"  # Min-max scaling
    PERCENTILE = "percentile"  # Percentile ranking
    LOG_TRANSFORM = "log_transform"  # Log transformation


@dataclass
class RegionalMetrics:
    """Metrics for a specific region"""

    region: str
    total_fields: int
    total_oil_reserves_mmbbl: float
    total_gas_reserves_bcf: float
    average_recovery_factor: float
    average_water_depth_m: float
    average_field_size_mmboe: float
    drilling_efficiency: float
    discovery_rate: float
    production_efficiency: float
    economic_indicators: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "region": self.region,
            "total_fields": self.total_fields,
            "total_oil_reserves_mmbbl": self.total_oil_reserves_mmbbl,
            "total_gas_reserves_bcf": self.total_gas_reserves_bcf,
            "average_recovery_factor": self.average_recovery_factor,
            "average_water_depth_m": self.average_water_depth_m,
            "average_field_size_mmboe": self.average_field_size_mmboe,
            "drilling_efficiency": self.drilling_efficiency,
            "discovery_rate": self.discovery_rate,
            "production_efficiency": self.production_efficiency,
            "economic_indicators": self.economic_indicators,
        }


@dataclass
class ComparisonResult:
    """Results from cross-regional comparison"""

    sodir_region: str
    bsee_region: str
    metrics_diff: Dict[str, float]
    statistical_significance: Dict[str, float]
    comparable_fields: List[Dict[str, Any]]
    insights: List[str]
    visualizations: Optional[List[Any]] = None

    def summary(self) -> Dict[str, Any]:
        """Get summary of comparison"""
        return {
            "regions_compared": [self.sodir_region, self.bsee_region],
            "key_differences": {
                metric: diff
                for metric, diff in self.metrics_diff.items()
                if abs(diff) > 0.1  # Significant differences only
            },
            "statistically_significant": [
                metric
                for metric, p_value in self.statistical_significance.items()
                if p_value < 0.05
            ],
            "comparable_fields_count": len(self.comparable_fields),
            "top_insights": self.insights[:3] if self.insights else [],
        }


class CrossRegionalAnalyzer:
    """Main analyzer for cross-regional comparisons"""

    def __init__(self):
        """Initialize cross-regional analyzer"""
        self.sodir_data = None
        self.bsee_data = None
        self.normalized_sodir = None
        self.normalized_bsee = None

    def normalize_data(
        self,
        data: Dict[str, pd.DataFrame],
        source: str = "SODIR",
        strategy: NormalizationStrategy = NormalizationStrategy.STANDARD,
    ) -> Dict[str, pd.DataFrame]:
        """
        Normalize data for cross-regional comparison.

        Args:
            data: Raw data from SODIR or BSEE
            source: Data source ('SODIR' or 'BSEE')
            strategy: Normalization strategy to use

        Returns:
            Normalized data with common structure
        """
        normalized = {}

        # Normalize fields data
        if "fields" in data:
            normalized["fields"] = self._normalize_fields(
                data["fields"], source, strategy
            )

        # Normalize wellbore data
        if "wellbores" in data:
            normalized["wellbores"] = self._normalize_wellbores(
                data["wellbores"], source
            )

        # Normalize production data
        if "production" in data:
            normalized["production"] = self._normalize_production(
                data["production"], source
            )

        return normalized

    def _normalize_fields(
        self, fields_df: pd.DataFrame, source: str, strategy: NormalizationStrategy
    ) -> pd.DataFrame:
        """Normalize fields data"""
        normalized = fields_df.copy()

        # Standardize column names
        column_mapping = {
            # SODIR -> Standard
            "field_name": "field_name",
            "discovery_year": "discovery_year",
            "production_start": "production_start",
            "recoverable_oil_mmbbl": "oil_reserves_mmbbl",
            "recoverable_gas_bcf": "gas_reserves_bcf",
            "water_depth_m": "water_depth_m",
            "recovery_factor": "recovery_factor",
            "status": "status",
            # BSEE -> Standard (if different)
            "water_depth_ft": "water_depth_m",  # Will convert units
        }

        # Apply column mapping
        normalized.columns = [
            column_mapping.get(col, col) for col in normalized.columns
        ]

        # Convert units if BSEE data
        if source == "BSEE" and "water_depth_ft" in fields_df.columns:
            normalized["water_depth_m"] = fields_df["water_depth_ft"] * 0.3048

        # Apply normalization strategy to numerical columns
        numerical_cols = [
            "oil_reserves_mmbbl",
            "gas_reserves_bcf",
            "water_depth_m",
            "recovery_factor",
        ]

        for col in numerical_cols:
            if col in normalized.columns:
                if strategy == NormalizationStrategy.STANDARD:
                    mean = normalized[col].mean()
                    std = normalized[col].std()
                    if std > 0:
                        normalized[f"{col}_normalized"] = (normalized[col] - mean) / std
                elif strategy == NormalizationStrategy.MIN_MAX:
                    min_val = normalized[col].min()
                    max_val = normalized[col].max()
                    if max_val > min_val:
                        normalized[f"{col}_normalized"] = (
                            normalized[col] - min_val
                        ) / (max_val - min_val)
                elif strategy == NormalizationStrategy.PERCENTILE:
                    normalized[f"{col}_normalized"] = normalized[col].rank(pct=True)
                elif strategy == NormalizationStrategy.LOG_TRANSFORM:
                    # Add small constant to avoid log(0)
                    normalized[f"{col}_normalized"] = np.log1p(normalized[col])

        # Add region identifier
        normalized["region"] = source

        # Add calculated fields
        normalized["total_boe_mmboe"] = (
            normalized["oil_reserves_mmbbl"] + normalized["gas_reserves_bcf"] / 6
        )
        normalized["gas_oil_ratio"] = normalized["gas_reserves_bcf"] / (
            normalized["oil_reserves_mmbbl"] + 1
        )  # Avoid division by zero

        # Classify field size
        normalized["size_class"] = pd.cut(
            normalized["total_boe_mmboe"],
            bins=[0, 50, 200, 1000, float("inf")],
            labels=["Small", "Medium", "Large", "Giant"],
        )

        # Classify water depth
        normalized["water_depth_class"] = pd.cut(
            normalized["water_depth_m"],
            bins=[0, 100, 500, 1500, float("inf")],
            labels=["Shallow", "Mid-depth", "Deep", "Ultra-deep"],
        )

        return normalized

    def _normalize_wellbores(
        self, wellbores_df: pd.DataFrame, source: str
    ) -> pd.DataFrame:
        """Normalize wellbore data"""
        normalized = wellbores_df.copy()

        # Standardize column names
        if (
            "depth_m" not in normalized.columns
            and "total_depth_ft" in normalized.columns
        ):
            normalized["depth_m"] = normalized["total_depth_ft"] * 0.3048

        # Add region identifier
        normalized["region"] = source

        # Calculate drilling efficiency metrics
        if "drilling_days" in normalized.columns and "depth_m" in normalized.columns:
            normalized["drilling_rate_m_per_day"] = normalized["depth_m"] / (
                normalized["drilling_days"] + 1
            )

        return normalized

    def _normalize_production(
        self, production_df: pd.DataFrame, source: str
    ) -> pd.DataFrame:
        """Normalize production data"""
        normalized = production_df.copy()

        # Add region identifier
        normalized["region"] = source

        # Calculate BOE for comparison
        normalized["production_boe"] = (
            normalized.get("oil_production_mmbbl", 0)
            + normalized.get("gas_production_bcf", 0) / 6
        )

        # Calculate water cut if available
        if (
            "water_production_mmbbl" in normalized.columns
            and "oil_production_mmbbl" in normalized.columns
        ):
            total_liquid = (
                normalized["water_production_mmbbl"]
                + normalized["oil_production_mmbbl"]
            )
            normalized["water_cut"] = normalized["water_production_mmbbl"] / (
                total_liquid + 0.001
            )

        return normalized

    def calculate_metrics(
        self, data: Dict[str, pd.DataFrame], region: str
    ) -> RegionalMetrics:
        """
        Calculate regional metrics from normalized data.

        Args:
            data: Normalized data
            region: Region name

        Returns:
            RegionalMetrics object
        """
        fields_df = data.get("fields", pd.DataFrame())
        wellbores_df = data.get("wellbores", pd.DataFrame())
        production_df = data.get("production", pd.DataFrame())

        # Basic field metrics
        total_fields = len(fields_df) if not fields_df.empty else 0
        total_oil = (
            fields_df["oil_reserves_mmbbl"].sum()
            if "oil_reserves_mmbbl" in fields_df
            else 0
        )
        total_gas = (
            fields_df["gas_reserves_bcf"].sum()
            if "gas_reserves_bcf" in fields_df
            else 0
        )
        avg_recovery = (
            fields_df["recovery_factor"].mean() if "recovery_factor" in fields_df else 0
        )
        avg_depth = (
            fields_df["water_depth_m"].mean() if "water_depth_m" in fields_df else 0
        )

        # Calculate average field size in BOE
        if not fields_df.empty and "total_boe_mmboe" in fields_df:
            avg_size = fields_df["total_boe_mmboe"].mean()
        else:
            avg_size = 0

        # Drilling efficiency
        drilling_eff = self._calculate_drilling_efficiency(wellbores_df)

        # Discovery rate
        discovery_rate = self._calculate_discovery_rate(fields_df)

        # Production efficiency
        production_eff = self._calculate_production_efficiency(production_df, fields_df)

        # Economic indicators
        economic = self._calculate_economic_indicators(fields_df, production_df)

        return RegionalMetrics(
            region=region,
            total_fields=total_fields,
            total_oil_reserves_mmbbl=total_oil,
            total_gas_reserves_bcf=total_gas,
            average_recovery_factor=avg_recovery,
            average_water_depth_m=avg_depth,
            average_field_size_mmboe=avg_size,
            drilling_efficiency=drilling_eff,
            discovery_rate=discovery_rate,
            production_efficiency=production_eff,
            economic_indicators=economic,
        )

    def _calculate_drilling_efficiency(self, wellbores_df: pd.DataFrame) -> float:
        """Calculate drilling efficiency metric"""
        if wellbores_df.empty:
            return 0.0

        if "drilling_rate_m_per_day" in wellbores_df:
            return wellbores_df["drilling_rate_m_per_day"].mean()
        elif "drilling_days" in wellbores_df and "depth_m" in wellbores_df:
            rates = wellbores_df["depth_m"] / (wellbores_df["drilling_days"] + 1)
            return rates.mean()

        return 0.0

    def _calculate_discovery_rate(self, fields_df: pd.DataFrame) -> float:
        """Calculate discovery rate (fields per decade)"""
        if fields_df.empty or "discovery_year" not in fields_df:
            return 0.0

        min_year = fields_df["discovery_year"].min()
        max_year = fields_df["discovery_year"].max()

        if max_year <= min_year:
            return 0.0

        decades = (max_year - min_year) / 10
        return len(fields_df) / decades if decades > 0 else 0.0

    def _calculate_production_efficiency(
        self, production_df: pd.DataFrame, fields_df: pd.DataFrame
    ) -> float:
        """Calculate production efficiency"""
        if production_df.empty or fields_df.empty:
            return 0.0

        # Calculate as production per field
        if "production_boe" in production_df:
            total_production = (
                production_df.groupby("field_name")["production_boe"].sum().mean()
            )
            return total_production

        return 0.0

    def _calculate_economic_indicators(
        self, fields_df: pd.DataFrame, production_df: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate economic indicators"""
        indicators = {}

        # Resource value (simplified)
        if not fields_df.empty:
            oil_value = (
                fields_df.get("oil_reserves_mmbbl", pd.Series([0])).sum() * 80
            )  # $80/bbl assumption
            gas_value = (
                fields_df.get("gas_reserves_bcf", pd.Series([0])).sum() * 3
            )  # $3/mcf assumption
            indicators["total_resource_value_mmusd"] = oil_value + gas_value

        # Development intensity (wells per field)
        # This would need wellbore counts per field
        indicators["development_intensity"] = 0.0  # Placeholder

        return indicators

    def compare_regions(
        self, sodir_metrics: RegionalMetrics, bsee_metrics: RegionalMetrics
    ) -> ComparisonResult:
        """
        Compare metrics between regions.

        Args:
            sodir_metrics: Metrics for Norwegian Continental Shelf
            bsee_metrics: Metrics for US Gulf of Mexico

        Returns:
            ComparisonResult with detailed comparison
        """
        # Calculate differences
        metrics_diff = {
            "recovery_factor_diff": sodir_metrics.average_recovery_factor
            - bsee_metrics.average_recovery_factor,
            "water_depth_diff_m": sodir_metrics.average_water_depth_m
            - bsee_metrics.average_water_depth_m,
            "field_size_diff_mmboe": sodir_metrics.average_field_size_mmboe
            - bsee_metrics.average_field_size_mmboe,
            "drilling_efficiency_diff": sodir_metrics.drilling_efficiency
            - bsee_metrics.drilling_efficiency,
            "discovery_rate_diff": sodir_metrics.discovery_rate
            - bsee_metrics.discovery_rate,
            "production_efficiency_diff": sodir_metrics.production_efficiency
            - bsee_metrics.production_efficiency,
        }

        # Calculate percentage differences (iterate over a snapshot to avoid
        # mutating dict during iteration)
        for key in list(metrics_diff):
            base_metric = (
                key.replace("_diff", "").replace("_m", "").replace("_mmboe", "")
            )
            sodir_val = getattr(
                sodir_metrics,
                (
                    base_metric
                    if hasattr(sodir_metrics, base_metric)
                    else key.replace("_diff", "")
                ),
                0,
            )
            bsee_val = getattr(
                bsee_metrics,
                (
                    base_metric
                    if hasattr(bsee_metrics, base_metric)
                    else key.replace("_diff", "")
                ),
                0,
            )

            if bsee_val != 0:
                metrics_diff[f"{key}_pct"] = (sodir_val - bsee_val) / bsee_val * 100

        # Statistical significance (simplified - would need actual data distributions)
        statistical_significance = self._calculate_statistical_significance(
            sodir_metrics, bsee_metrics
        )

        # Find comparable fields
        comparable_fields = []  # Would be populated by find_comparable_fields method

        # Generate insights
        insights = self._generate_insights(metrics_diff, sodir_metrics, bsee_metrics)

        return ComparisonResult(
            sodir_region="Norwegian Continental Shelf",
            bsee_region="US Gulf of Mexico",
            metrics_diff=metrics_diff,
            statistical_significance=statistical_significance,
            comparable_fields=comparable_fields,
            insights=insights,
        )

    def _calculate_statistical_significance(
        self, sodir_metrics: RegionalMetrics, bsee_metrics: RegionalMetrics
    ) -> Dict[str, float]:
        """Calculate statistical significance of differences"""
        # Simplified - would need actual data distributions for proper testing
        significance = {}

        # For now, use a simple threshold approach
        # In reality, would use t-tests, Mann-Whitney U, etc.
        significance["recovery_factor"] = (
            0.01
            if abs(
                sodir_metrics.average_recovery_factor
                - bsee_metrics.average_recovery_factor
            )
            > 0.1
            else 0.5
        )
        significance["water_depth"] = (
            0.01
            if abs(
                sodir_metrics.average_water_depth_m - bsee_metrics.average_water_depth_m
            )
            > 500
            else 0.5
        )
        significance["field_size"] = (
            0.01
            if abs(
                sodir_metrics.average_field_size_mmboe
                - bsee_metrics.average_field_size_mmboe
            )
            > 100
            else 0.5
        )

        return significance

    def _generate_insights(
        self,
        metrics_diff: Dict[str, float],
        sodir_metrics: RegionalMetrics,
        bsee_metrics: RegionalMetrics,
    ) -> List[str]:
        """Generate insights from comparison"""
        insights = []

        # Recovery factor insights
        if metrics_diff.get("recovery_factor_diff", 0) > 0.1:
            insights.append(
                f"Norwegian fields show {metrics_diff['recovery_factor_diff']:.1%} higher recovery factors, "  # noqa: E501
                "potentially due to advanced EOR techniques or reservoir characteristics"
            )
        elif metrics_diff.get("recovery_factor_diff", 0) < -0.1:
            insights.append(
                f"US Gulf fields show {abs(metrics_diff['recovery_factor_diff']):.1%} higher recovery factors"  # noqa: E501
            )

        # Water depth insights
        if metrics_diff.get("water_depth_diff_m", 0) > 500:
            insights.append(
                "US Gulf operations are significantly deeper water on average, "
                "requiring more advanced subsea technology"
            )
        elif metrics_diff.get("water_depth_diff_m", 0) < -500:
            insights.append(
                "Norwegian operations are in significantly deeper water on average"
            )

        # Field size insights
        if (
            sodir_metrics.average_field_size_mmboe
            > bsee_metrics.average_field_size_mmboe * 2
        ):
            insights.append(
                "Norwegian fields are substantially larger on average, "
                "potentially offering better economies of scale"
            )
        elif (
            bsee_metrics.average_field_size_mmboe
            > sodir_metrics.average_field_size_mmboe * 2
        ):
            insights.append("US Gulf fields are substantially larger on average")

        # Drilling efficiency
        if metrics_diff.get("drilling_efficiency_diff", 0) > 10:
            insights.append(
                "Norwegian drilling operations show higher efficiency, "
                f"averaging {sodir_metrics.drilling_efficiency:.0f} meters per day"
            )

        # Gas vs oil focus
        sodir_gor = sodir_metrics.total_gas_reserves_bcf / (
            sodir_metrics.total_oil_reserves_mmbbl + 1
        )
        bsee_gor = bsee_metrics.total_gas_reserves_bcf / (
            bsee_metrics.total_oil_reserves_mmbbl + 1
        )

        if sodir_gor > bsee_gor * 2:
            insights.append(
                "Norwegian Continental Shelf is more gas-focused compared to oil-dominant US Gulf"
            )
        elif bsee_gor > sodir_gor * 2:
            insights.append(
                "US Gulf is more gas-focused compared to Norwegian operations"
            )

        return insights

    def find_comparable_fields(
        self,
        sodir_fields: pd.DataFrame,
        bsee_fields: pd.DataFrame,
        criteria: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find comparable fields between regions.

        Args:
            sodir_fields: Norwegian fields data
            bsee_fields: US Gulf fields data
            criteria: Matching criteria to use

        Returns:
            List of comparable field pairs with similarity scores
        """
        if criteria is None:
            criteria = ["size_class", "water_depth_range", "recovery_factor"]

        matches = []

        # Ensure required columns exist
        for fields_df in [sodir_fields, bsee_fields]:
            if (
                "size_class" not in fields_df.columns
                and "total_boe_mmboe" in fields_df.columns
            ):
                fields_df["size_class"] = pd.cut(
                    fields_df["total_boe_mmboe"],
                    bins=[0, 50, 200, 1000, float("inf")],
                    labels=["Small", "Medium", "Large", "Giant"],
                )

            if (
                "water_depth_range" not in fields_df.columns
                and "water_depth_m" in fields_df.columns
            ):
                fields_df["water_depth_range"] = pd.cut(
                    fields_df["water_depth_m"],
                    bins=[0, 100, 500, 1500, float("inf")],
                    labels=["Shallow", "Mid-depth", "Deep", "Ultra-deep"],
                )

        # Find matches based on criteria
        for _, sodir_field in sodir_fields.iterrows():
            best_match = None
            best_score = 0

            for _, bsee_field in bsee_fields.iterrows():
                score = self._calculate_similarity(sodir_field, bsee_field, criteria)

                if score > best_score:
                    best_score = score
                    best_match = bsee_field

            if best_match is not None and best_score > 0.5:  # Threshold for matching
                matches.append(
                    {
                        "sodir_field": sodir_field["field_name"],
                        "bsee_field": best_match["field_name"],
                        "similarity_score": best_score,
                        "matched_criteria": self._get_matched_criteria(
                            sodir_field, best_match, criteria
                        ),
                    }
                )

        # Sort by similarity score
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)

        return matches

    def _calculate_similarity(
        self, field1: pd.Series, field2: pd.Series, criteria: List[str]
    ) -> float:
        """Calculate similarity score between two fields"""
        score = 0
        weight = 1.0 / len(criteria)

        for criterion in criteria:
            if criterion in field1.index and criterion in field2.index:
                if criterion in ["size_class", "water_depth_range"]:
                    # Categorical comparison
                    if field1[criterion] == field2[criterion]:
                        score += weight
                else:
                    # Numerical comparison
                    val1 = field1[criterion]
                    val2 = field2[criterion]

                    if pd.notna(val1) and pd.notna(val2) and val2 != 0:
                        # Calculate relative difference
                        diff = abs(val1 - val2) / val2
                        if diff < 0.2:  # Within 20%
                            score += weight * (1 - diff / 0.2)

        return score

    def _get_matched_criteria(
        self, field1: pd.Series, field2: pd.Series, criteria: List[str]
    ) -> List[str]:
        """Get list of matched criteria between fields"""
        matched = []

        for criterion in criteria:
            if criterion in field1.index and criterion in field2.index:
                if criterion in ["size_class", "water_depth_range"]:
                    if field1[criterion] == field2[criterion]:
                        matched.append(criterion)
                else:
                    val1 = field1[criterion]
                    val2 = field2[criterion]

                    if pd.notna(val1) and pd.notna(val2) and val2 != 0:
                        diff = abs(val1 - val2) / val2
                        if diff < 0.2:  # Within 20%
                            matched.append(criterion)

        return matched

    def compare_production_efficiency(
        self, sodir_production: pd.DataFrame, bsee_production: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compare production efficiency between regions.

        Args:
            sodir_production: Norwegian production data
            bsee_production: US Gulf production data

        Returns:
            Dictionary with efficiency comparisons
        """
        efficiency = {}

        # Calculate recovery rates
        if (
            not sodir_production.empty
            and "cumulative_oil" in sodir_production
            and "recoverable_oil" in sodir_production
        ):
            sodir_recovery = (
                sodir_production["cumulative_oil"].sum()
                / sodir_production["recoverable_oil"].sum()
            )
            efficiency["recovery_rate_sodir"] = sodir_recovery

        if (
            not bsee_production.empty
            and "cumulative_oil" in bsee_production
            and "recoverable_oil" in bsee_production
        ):
            bsee_recovery = (
                bsee_production["cumulative_oil"].sum()
                / bsee_production["recoverable_oil"].sum()
            )
            efficiency["recovery_rate_bsee"] = bsee_recovery

        # Calculate production per well
        if "wells_count" in sodir_production and "cumulative_oil" in sodir_production:
            sodir_well_prod = (
                sodir_production["cumulative_oil"].sum()
                / sodir_production["wells_count"].sum()
            )
            efficiency["oil_per_well_sodir"] = sodir_well_prod

        if "wells_count" in bsee_production and "cumulative_oil" in bsee_production:
            bsee_well_prod = (
                bsee_production["cumulative_oil"].sum()
                / bsee_production["wells_count"].sum()
            )
            efficiency["oil_per_well_bsee"] = bsee_well_prod

        # Calculate productivity ratio
        if "oil_per_well_sodir" in efficiency and "oil_per_well_bsee" in efficiency:
            efficiency["wells_productivity_ratio"] = (
                efficiency["oil_per_well_sodir"] / efficiency["oil_per_well_bsee"]
            )

        # Water cut comparison
        if "water_cut" in sodir_production:
            efficiency["avg_water_cut_sodir"] = sodir_production["water_cut"].mean()

        if "water_cut" in bsee_production:
            efficiency["avg_water_cut_bsee"] = bsee_production["water_cut"].mean()

        return efficiency

    def perform_statistical_tests(
        self, sodir_data: pd.DataFrame, bsee_data: pd.DataFrame, variables: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Perform statistical tests between regions.

        Args:
            sodir_data: Norwegian data
            bsee_data: US Gulf data
            variables: Variables to test

        Returns:
            Dictionary with test results
        """
        results = {}

        for var in variables:
            if var in sodir_data.columns and var in bsee_data.columns:
                sodir_values = sodir_data[var].dropna()
                bsee_values = bsee_data[var].dropna()

                if len(sodir_values) > 1 and len(bsee_values) > 1:
                    # T-test for means
                    t_stat, p_value_t = stats.ttest_ind(sodir_values, bsee_values)

                    # Mann-Whitney U test (non-parametric)
                    u_stat, p_value_u = stats.mannwhitneyu(
                        sodir_values, bsee_values, alternative="two-sided"
                    )

                    # Levene's test for variance
                    levene_stat, p_value_levene = stats.levene(
                        sodir_values, bsee_values
                    )

                    results[var] = {
                        "t_statistic": t_stat,
                        "t_test_p_value": p_value_t,
                        "mann_whitney_u": u_stat,
                        "mann_whitney_p_value": p_value_u,
                        "levene_statistic": levene_stat,
                        "levene_p_value": p_value_levene,
                        "sodir_mean": sodir_values.mean(),
                        "bsee_mean": bsee_values.mean(),
                        "sodir_std": sodir_values.std(),
                        "bsee_std": bsee_values.std(),
                    }

        return results

    def normalize_fields(
        self, fields_data: pd.DataFrame, source: str = "SODIR"
    ) -> pd.DataFrame:
        """
        Normalize field data for cross-regional comparison.

        Args:
            fields_data: DataFrame containing field data
            source: Data source ('SODIR' or 'BSEE')

        Returns:
            Normalized DataFrame
        """
        return self._normalize_fields(
            fields_data, source, NormalizationStrategy.STANDARD
        )

    def normalize_blocks(
        self, blocks_data: pd.DataFrame, source: str = "SODIR"
    ) -> pd.DataFrame:
        """
        Normalize block data for cross-regional comparison.

        Args:
            blocks_data: DataFrame containing block data
            source: Data source ('SODIR' or 'BSEE')

        Returns:
            Normalized DataFrame
        """
        normalized = blocks_data.copy()

        # Standardize column names
        column_mapping = {
            "block_name": "block_id",
            "area_km2": "area_size",
            "water_depth_m": "water_depth",
            "latitude": "lat",
            "longitude": "lon",
        }

        normalized = normalized.rename(columns=column_mapping)

        # Convert units if needed
        if source == "BSEE" and "water_depth" in normalized.columns:
            # Convert feet to meters if BSEE data
            normalized["water_depth"] = normalized["water_depth"] * 0.3048

        if source == "BSEE" and "area_size" in normalized.columns:
            # Convert square miles to km2 if BSEE data
            normalized["area_size"] = normalized["area_size"] * 2.58999

        # Add source identifier
        normalized["source_region"] = source

        return normalized

    def validate_data_quality(
        self, data: pd.DataFrame, data_type: str = "fields"
    ) -> Dict[str, Any]:
        """
        Validate data quality and completeness.

        Args:
            data: DataFrame to validate
            data_type: Type of data ('fields', 'blocks', 'wellbores', etc.)

        Returns:
            Dictionary with quality metrics
        """
        quality_report = {
            "total_records": len(data),
            "completeness": {},
            "data_types": {},
            "issues": [],
            "quality_score": 0.0,
        }

        # Check completeness for each column
        for col in data.columns:
            non_null_count = data[col].notna().sum()
            completeness = non_null_count / len(data) * 100 if len(data) > 0 else 0
            quality_report["completeness"][col] = completeness

            # Check data types
            quality_report["data_types"][col] = str(data[col].dtype)

            # Flag columns with low completeness
            if completeness < 50:
                quality_report["issues"].append(
                    f"Column '{col}' has low completeness: {completeness:.1f}%"
                )

        # Check for duplicate records based on key fields
        key_fields = {
            "fields": ["field_name"],
            "blocks": ["block_id", "block_name"],
            "wellbores": ["wellbore_name"],
        }

        if data_type in key_fields:
            key_cols = [col for col in key_fields[data_type] if col in data.columns]
            if key_cols:
                duplicates = data.duplicated(subset=key_cols).sum()
                if duplicates > 0:
                    quality_report["issues"].append(
                        f"Found {duplicates} duplicate records"
                    )

        # Calculate overall quality score
        avg_completeness = np.mean(list(quality_report["completeness"].values()))
        duplicate_penalty = (
            10
            if any("duplicate" in issue.lower() for issue in quality_report["issues"])
            else 0
        )
        quality_report["quality_score"] = max(0, avg_completeness - duplicate_penalty)

        return quality_report

    def aggregate_cross_regional(
        self,
        sodir_data: pd.DataFrame,
        bsee_data: pd.DataFrame,
        aggregation_level: str = "field",
    ) -> pd.DataFrame:
        """
        Aggregate data from both regions for unified analysis.

        Args:
            sodir_data: SODIR data DataFrame
            bsee_data: BSEE data DataFrame
            aggregation_level: Level of aggregation ('field', 'block', 'operator')

        Returns:
            Aggregated DataFrame with both regions
        """
        # Normalize column names for both datasets
        sodir_normalized = sodir_data.copy()
        sodir_normalized["region"] = "SODIR"

        bsee_normalized = bsee_data.copy()
        bsee_normalized["region"] = "BSEE"

        # Common column mapping
        column_mapping = {
            "field_name": "name",
            "operator_name": "operator",
            "oil_reserves_mmbbl": "oil_reserves",
            "gas_reserves_bcf": "gas_reserves",
            "water_depth_m": "water_depth",
            "production_start": "start_date",
        }

        # Apply column mapping
        sodir_normalized = sodir_normalized.rename(columns=column_mapping)
        bsee_normalized = bsee_normalized.rename(columns=column_mapping)

        # Select common columns
        common_columns = list(
            set(sodir_normalized.columns) & set(bsee_normalized.columns)
        )

        # Combine datasets
        aggregated = pd.concat(
            [sodir_normalized[common_columns], bsee_normalized[common_columns]],
            ignore_index=True,
        )

        # Perform aggregation based on level
        if aggregation_level == "operator" and "operator" in aggregated.columns:
            aggregated = (
                aggregated.groupby(["operator", "region"])
                .agg(
                    {
                        "name": "count",  # Count of fields
                        "oil_reserves": "sum",
                        "gas_reserves": "sum",
                        "water_depth": "mean",
                    }
                )
                .reset_index()
            )
            aggregated = aggregated.rename(columns={"name": "field_count"})

        elif aggregation_level == "block" and "block_id" in aggregated.columns:
            aggregated = (
                aggregated.groupby(["block_id", "region"])
                .agg({"name": "count", "oil_reserves": "sum", "gas_reserves": "sum"})
                .reset_index()
            )
            aggregated = aggregated.rename(columns={"name": "field_count"})

        return aggregated
