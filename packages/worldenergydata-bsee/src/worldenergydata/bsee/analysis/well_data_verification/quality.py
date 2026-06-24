"""
Data quality framework for well data verification.

Provides production volume validators, completeness checks, outlier detection,
and rule building capabilities.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import yaml
from loguru import logger
from scipy import stats

from worldenergydata.bsee.analysis.well_data_verification.base import (
    VerificationResult,
)
from worldenergydata.validation.base import ValidationResult, ValidationRule


@dataclass
class QualityConfig:
    """Configuration for data quality checks."""

    enable_outlier_detection: bool = True
    outlier_threshold: float = 3.0  # Z-score threshold
    iqr_multiplier: float = 1.5
    enable_completeness_check: bool = True
    required_fields: List[str] = field(default_factory=list)
    production_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_content: Union[str, Path]) -> "QualityConfig":
        """Load configuration from YAML."""
        if isinstance(yaml_content, Path):
            yaml_content = yaml_content.read_text()

        data = yaml.safe_load(yaml_content)
        config_data = data.get("quality_config", data)

        # Convert production ranges from dict format
        if "production_ranges" in config_data:
            ranges = {}
            for field_name, range_data in config_data["production_ranges"].items():
                if isinstance(range_data, dict):
                    ranges[field_name] = (
                        range_data.get("min", 0),
                        range_data.get("max", float("inf")),
                    )
                elif isinstance(range_data, (list, tuple)) and len(range_data) == 2:
                    ranges[field_name] = tuple(range_data)
            config_data["production_ranges"] = ranges

        return cls(**config_data)

    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file."""
        config_dict = {
            "quality_config": {
                "enable_outlier_detection": self.enable_outlier_detection,
                "outlier_threshold": self.outlier_threshold,
                "iqr_multiplier": self.iqr_multiplier,
                "enable_completeness_check": self.enable_completeness_check,
                "required_fields": self.required_fields,
                "production_ranges": {
                    field_name: {"min": min_val, "max": max_val}
                    for field_name, (min_val, max_val) in self.production_ranges.items()
                },
                "validation_rules": self.validation_rules,
            }
        }

        with open(path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)


class ProductionVolumeValidator:
    """Validator for oil and gas production volumes."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize production volume validator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

        # Default ranges (can be overridden by config)
        self.oil_min = self.config.get("oil_min", 0)
        self.oil_max = self.config.get("oil_max", 100000)  # BBL/month
        self.gas_min = self.config.get("gas_min", 0)
        self.gas_max = self.config.get("gas_max", 1000000)  # MCF/month

        # Monthly variation threshold
        self.variation_threshold = self.config.get(
            "variation_threshold", 5.0
        )  # 5x normal variation

    def validate_oil_volumes(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate oil production volumes.

        Args:
            data: DataFrame with oil_volume column

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        result.metadata["validator"] = "ProductionVolumeValidator"
        result.metadata["field"] = "oil_volume"

        if "oil_volume" not in data.columns:
            result.add_error("oil_volume", "Oil volume column not found")
            return result

        # Check for negative values
        negative_mask = data["oil_volume"] < 0
        if negative_mask.any():
            negative_indices = data[negative_mask].index.tolist()
            for idx in negative_indices:
                result.add_error(
                    "oil_volume",
                    f'Negative oil volume: {data.loc[idx, "oil_volume"]}',
                    value=data.loc[idx, "oil_volume"],
                    row_index=idx,
                    rule="non_negative",
                )

        # Check for excessive values
        excessive_mask = data["oil_volume"] > self.oil_max
        if excessive_mask.any():
            excessive_indices = data[excessive_mask].index.tolist()
            for idx in excessive_indices:
                result.add_error(
                    "oil_volume",
                    f'Excessive oil volume: {data.loc[idx, "oil_volume"]} (max: {self.oil_max})',
                    value=data.loc[idx, "oil_volume"],
                    row_index=idx,
                    rule="range_check",
                )

        # Check for zero values (warning)
        zero_mask = data["oil_volume"] == 0
        if zero_mask.any():
            zero_count = zero_mask.sum()
            result.add_warning(
                "oil_volume",
                f"{zero_count} zero oil volume entries found",
                rule="zero_check",
            )

        return result

    def validate_gas_volumes(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate gas production volumes.

        Args:
            data: DataFrame with gas_volume column

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        result.metadata["validator"] = "ProductionVolumeValidator"
        result.metadata["field"] = "gas_volume"

        if "gas_volume" not in data.columns:
            result.add_error("gas_volume", "Gas volume column not found")
            return result

        # Check for negative values
        negative_mask = data["gas_volume"] < 0
        if negative_mask.any():
            negative_indices = data[negative_mask].index.tolist()
            for idx in negative_indices:
                result.add_error(
                    "gas_volume",
                    f'Negative gas volume: {data.loc[idx, "gas_volume"]}',
                    value=data.loc[idx, "gas_volume"],
                    row_index=idx,
                    rule="non_negative",
                )

        # Check for excessive values
        excessive_mask = data["gas_volume"] > self.gas_max
        if excessive_mask.any():
            excessive_indices = data[excessive_mask].index.tolist()
            for idx in excessive_indices:
                result.add_error(
                    "gas_volume",
                    f'Excessive gas volume: {data.loc[idx, "gas_volume"]} (max: {self.gas_max})',
                    value=data.loc[idx, "gas_volume"],
                    row_index=idx,
                    rule="range_check",
                )

        return result

    def validate_monthly_consistency(self, data: pd.DataFrame) -> ValidationResult:
        """
        Check for consistency in monthly production values.

        Args:
            data: DataFrame with date and production columns

        Returns:
            ValidationResult with warnings for inconsistencies
        """
        result = ValidationResult()
        result.metadata["validator"] = "ProductionVolumeValidator"
        result.metadata["check"] = "monthly_consistency"

        if "oil_volume" not in data.columns or "date" not in data.columns:
            result.add_error("data", "Required columns (date, oil_volume) not found")
            return result

        # Group by well if well_id exists
        if "well_id" in data.columns:
            for well_id, well_data in data.groupby("well_id"):
                self._check_well_consistency(well_data, well_id, result)
        else:
            self._check_well_consistency(data, None, result)

        return result

    def _check_well_consistency(
        self, data: pd.DataFrame, well_id: Optional[str], result: ValidationResult
    ) -> None:
        """Check consistency for a single well's data."""
        sorted_data = data.sort_values("date")
        oil_volumes = sorted_data["oil_volume"].values

        if len(oil_volumes) < 2:
            return

        # Calculate month-to-month changes
        changes = np.diff(oil_volumes)

        # Calculate mean and std of absolute changes
        abs_changes = np.abs(changes)
        mean_change = np.mean(abs_changes)
        std_change = np.std(abs_changes)

        # Detect spikes as changes that exceed mean + threshold * std
        # This is more sensitive to detecting unusual variations
        if std_change > 0:
            for i, change in enumerate(changes):
                # Check if this change is unusually large
                z_score = (abs(change) - mean_change) / std_change

                # If z-score exceeds threshold, it's a spike
                if z_score > self.variation_threshold:
                    date_str = sorted_data.iloc[i + 1]["date"]
                    well_context = f" for well {well_id}" if well_id else ""

                    result.add_warning(
                        "oil_volume",
                        f"Unusual production change of {change:.0f} BBL at {date_str}{well_context}",  # noqa: E501
                        value=change,
                        rule="consistency_check",
                    )


class CompletenessChecker:
    """Check data completeness and identify missing values."""

    def check_time_series_completeness(
        self, data: pd.DataFrame, date_column: str
    ) -> ValidationResult:
        """
        Check for missing time periods in time series data.

        Args:
            data: DataFrame with time series data
            date_column: Name of date column

        Returns:
            ValidationResult with missing period errors
        """
        result = ValidationResult()
        result.metadata["validator"] = "CompletenessChecker"
        result.metadata["check"] = "time_series_completeness"

        if date_column not in data.columns:
            result.add_error(date_column, f"Date column {date_column} not found")
            return result

        # Convert to datetime
        dates = pd.to_datetime(data[date_column])

        # Find expected date range
        min_date = dates.min()
        max_date = dates.max()

        # Generate expected monthly dates
        expected_dates = pd.date_range(start=min_date, end=max_date, freq="MS")

        # Find missing dates
        actual_dates = pd.to_datetime(dates).dt.to_period("M").unique()
        expected_periods = expected_dates.to_period("M")

        missing_periods = set(expected_periods) - set(actual_dates)

        if missing_periods:
            missing_list = sorted([str(p) for p in missing_periods])
            result.add_error(
                date_column,
                f'Missing data for periods: {", ".join(missing_list)}',
                rule="time_series_completeness",
            )

        return result

    def check_zero_values(
        self, data: pd.DataFrame, columns: List[str]
    ) -> ValidationResult:
        """
        Check for zero values in specified columns.

        Args:
            data: DataFrame to check
            columns: List of column names to check

        Returns:
            ValidationResult with zero value warnings
        """
        result = ValidationResult()
        result.metadata["validator"] = "CompletenessChecker"
        result.metadata["check"] = "zero_values"

        for col in columns:
            if col not in data.columns:
                continue

            zero_mask = data[col] == 0
            if zero_mask.any():
                zero_count = zero_mask.sum()
                zero_pct = (zero_count / len(data)) * 100

                result.add_warning(
                    col,
                    f"{zero_count} zero values found ({zero_pct:.1f}% of data)",
                    rule="zero_check",
                )

        return result

    def check_required_fields(
        self, data: pd.DataFrame, required_fields: List[str]
    ) -> ValidationResult:
        """
        Check for null values in required fields.

        Args:
            data: DataFrame to check
            required_fields: List of required field names

        Returns:
            ValidationResult with null value errors
        """
        result = ValidationResult()
        result.metadata["validator"] = "CompletenessChecker"
        result.metadata["check"] = "required_fields"

        for field in required_fields:  # noqa: F402
            if field not in data.columns:
                result.add_error(field, f"Required field {field} not found in data")
                continue

            null_mask = data[field].isna()
            if null_mask.any():
                null_indices = data[null_mask].index.tolist()
                result.add_error(
                    field,
                    f"{len(null_indices)} null values in required field",
                    rule="not_null",
                )

        return result

    def generate_completeness_report(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a comprehensive completeness report.

        Args:
            data: DataFrame to analyze

        Returns:
            Dictionary with completeness statistics
        """
        report = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "missing_values": {},
            "zero_values": {},
            "completeness_percentage": {},
        }

        for col in data.columns:
            missing_count = data[col].isna().sum()
            zero_count = (
                (data[col] == 0).sum()
                if pd.api.types.is_numeric_dtype(data[col])
                else 0
            )

            report["missing_values"][col] = missing_count
            report["zero_values"][col] = zero_count
            report["completeness_percentage"][col] = (
                (len(data) - missing_count) / len(data)
            ) * 100

        report["overall_completeness"] = np.mean(
            list(report["completeness_percentage"].values())
        )

        return report


class OutlierDetector:
    """Detect outliers in production data using statistical methods."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize outlier detector.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.default_zscore_threshold = self.config.get("zscore_threshold", 3.0)
        self.default_iqr_multiplier = self.config.get("iqr_multiplier", 1.5)

    def detect_outliers_zscore(
        self, data: pd.DataFrame, column: str, threshold: Optional[float] = None
    ) -> ValidationResult:
        """
        Detect outliers using Z-score method.

        Args:
            data: DataFrame with data to check
            column: Column name to check for outliers
            threshold: Z-score threshold (default 3.0)

        Returns:
            ValidationResult with outlier warnings
        """
        result = ValidationResult()
        result.metadata["validator"] = "OutlierDetector"
        result.metadata["method"] = "zscore"

        if column not in data.columns:
            result.add_error(column, f"Column {column} not found")
            return result

        threshold = threshold or self.default_zscore_threshold

        # Calculate Z-scores
        values = data[column].dropna()
        if len(values) < 2:
            return result

        z_scores = np.abs(stats.zscore(values))
        outlier_mask = z_scores > threshold

        if outlier_mask.any():
            outlier_indices = values[outlier_mask].index.tolist()
            for idx in outlier_indices:
                value = data.loc[idx, column]
                z_score = z_scores[values.index.get_loc(idx)]

                result.add_warning(
                    column,
                    f"Potential outlier detected: {value} (Z-score: {z_score:.2f})",
                    value=value,
                    row_index=idx,
                    rule="zscore_outlier",
                )

        return result

    def detect_outliers_iqr(
        self, data: pd.DataFrame, column: str, multiplier: Optional[float] = None
    ) -> ValidationResult:
        """
        Detect outliers using IQR (Interquartile Range) method.

        Args:
            data: DataFrame with data to check
            column: Column name to check for outliers
            multiplier: IQR multiplier (default 1.5)

        Returns:
            ValidationResult with outlier warnings
        """
        result = ValidationResult()
        result.metadata["validator"] = "OutlierDetector"
        result.metadata["method"] = "iqr"

        if column not in data.columns:
            result.add_error(column, f"Column {column} not found")
            return result

        multiplier = multiplier or self.default_iqr_multiplier

        # Calculate IQR
        values = data[column].dropna()
        if len(values) < 4:
            return result

        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR

        outlier_mask = (values < lower_bound) | (values > upper_bound)

        if outlier_mask.any():
            outlier_indices = values[outlier_mask].index.tolist()
            for idx in outlier_indices:
                value = data.loc[idx, column]

                result.add_warning(
                    column,
                    f"Outlier detected: {value} (outside [{lower_bound:.2f}, {upper_bound:.2f}])",
                    value=value,
                    row_index=idx,
                    rule="iqr_outlier",
                )

        return result

    def detect_multivariate_outliers(
        self, data: pd.DataFrame, columns: List[str]
    ) -> ValidationResult:
        """
        Detect multivariate outliers using Mahalanobis distance.

        Args:
            data: DataFrame with data to check
            columns: List of column names to include in multivariate analysis

        Returns:
            ValidationResult with outlier warnings
        """
        result = ValidationResult()
        result.metadata["validator"] = "OutlierDetector"
        result.metadata["method"] = "mahalanobis"

        # Check columns exist
        missing_cols = [col for col in columns if col not in data.columns]
        if missing_cols:
            result.add_error("columns", f"Columns not found: {missing_cols}")
            return result

        # Get data for specified columns
        subset = data[columns].dropna()
        if len(subset) < len(columns) + 1:
            result.add_warning(
                "data", "Insufficient data for multivariate outlier detection"
            )
            return result

        # Calculate Mahalanobis distance
        mean = subset.mean()
        cov_matrix = subset.cov()

        # Check if covariance matrix is singular
        if np.linalg.det(cov_matrix) == 0:
            result.add_warning(
                "data",
                "Singular covariance matrix - cannot compute Mahalanobis distance",
            )
            return result

        inv_cov_matrix = np.linalg.inv(cov_matrix)

        mahal_distances = []
        for idx, row in subset.iterrows():
            diff = row - mean
            mahal_dist = np.sqrt(diff.values @ inv_cov_matrix @ diff.values.T)
            mahal_distances.append(mahal_dist)

        mahal_distances = np.array(mahal_distances)

        # Use chi-square distribution for threshold
        threshold = np.sqrt(stats.chi2.ppf(0.975, df=len(columns)))

        outlier_mask = mahal_distances > threshold
        if outlier_mask.any():
            outlier_indices = subset[outlier_mask].index.tolist()
            for i, idx in enumerate(outlier_indices):
                distance = mahal_distances[subset.index.get_loc(idx)]

                result.add_warning(
                    "multivariate",
                    f"Multivariate outlier detected (Mahalanobis distance: {distance:.2f})",
                    row_index=idx,
                    rule="mahalanobis_outlier",
                )

        return result


class RangeValidationRule(ValidationRule):
    """Validation rule for checking value ranges."""

    def __init__(
        self,
        field_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ):
        super().__init__(name=f"range_{field_name}")
        self.field_name = field_name
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, data: Any, field_name: str = None) -> ValidationResult:
        """Validate that values are within specified range."""
        result = ValidationResult()
        field_name = field_name or self.field_name

        if isinstance(data, pd.DataFrame):
            if self.field_name not in data.columns:
                result.add_error(self.field_name, f"Field {self.field_name} not found")
                return result
            values = data[self.field_name]
        else:
            values = data

        # Check minimum
        if self.min_value is not None:
            below_min = values < self.min_value
            if isinstance(below_min, bool) and below_min:
                result.add_error(
                    field_name, f"Value {values} below minimum {self.min_value}"
                )
            elif hasattr(below_min, "any") and below_min.any():
                for idx in values[below_min].index:
                    result.add_error(
                        field_name,
                        f"Value {values[idx]} below minimum {self.min_value}",
                        value=values[idx],
                        row_index=idx,
                    )

        # Check maximum
        if self.max_value is not None:
            above_max = values > self.max_value
            if isinstance(above_max, bool) and above_max:
                result.add_error(
                    field_name, f"Value {values} above maximum {self.max_value}"
                )
            elif hasattr(above_max, "any") and above_max.any():
                for idx in values[above_max].index:
                    result.add_error(
                        field_name,
                        f"Value {values[idx]} above maximum {self.max_value}",
                        value=values[idx],
                        row_index=idx,
                    )

        return result


class PatternValidationRule(ValidationRule):
    """Validation rule for checking string patterns."""

    def __init__(self, field_name: str, pattern: str):
        super().__init__(name=f"pattern_{field_name}")
        self.field_name = field_name
        self.pattern = pattern
        import re

        self.regex = re.compile(pattern)

    def validate(self, data: Any, field_name: str = None) -> ValidationResult:
        """Validate that values match the specified pattern."""
        result = ValidationResult()
        field_name = field_name or self.field_name

        if isinstance(data, pd.DataFrame):
            if self.field_name not in data.columns:
                result.add_error(self.field_name, f"Field {self.field_name} not found")
                return result
            values = data[self.field_name]
        else:
            values = data

        # Check pattern for each value
        if isinstance(values, pd.Series):
            for idx, value in values.items():
                if pd.notna(value) and not self.regex.match(str(value)):
                    result.add_error(
                        field_name,
                        f'Value "{value}" does not match pattern {self.pattern}',
                        value=value,
                        row_index=idx,
                    )
        else:
            if pd.notna(values) and not self.regex.match(str(values)):
                result.add_error(
                    field_name,
                    f'Value "{values}" does not match pattern {self.pattern}',
                    value=values,
                )

        return result


class CustomValidationRule(ValidationRule):
    """Custom validation rule with user-defined logic."""

    def __init__(self, field_name: str, validator_func: Callable, error_message: str):
        super().__init__(name=f"custom_{field_name}")
        self.field_name = field_name
        self.validator_func = validator_func
        self.error_message = error_message

    def validate(self, data: Any, field_name: str = None) -> ValidationResult:
        """Validate using custom function."""
        result = ValidationResult()
        field_name = field_name or self.field_name

        if isinstance(data, pd.DataFrame):
            if self.field_name not in data.columns:
                result.add_error(self.field_name, f"Field {self.field_name} not found")
                return result
            values = data[self.field_name]
        else:
            values = data

        # Apply custom validator
        if isinstance(values, pd.Series):
            for idx, value in values.items():
                if pd.notna(value) and not self.validator_func(value):
                    result.add_error(
                        field_name, self.error_message, value=value, row_index=idx
                    )
        else:
            if pd.notna(values) and not self.validator_func(values):
                result.add_error(field_name, self.error_message, value=values)

        return result


class NotNullValidationRule(ValidationRule):
    """Validation rule for checking non-null values."""

    def __init__(self, field_name: str):
        super().__init__(name=f"not_null_{field_name}")
        self.field_name = field_name

    def validate(self, data: Any, field_name: str = None) -> ValidationResult:
        """Validate that values are not null."""
        result = ValidationResult()
        field_name = field_name or self.field_name

        if isinstance(data, pd.DataFrame):
            if self.field_name not in data.columns:
                result.add_error(self.field_name, f"Field {self.field_name} not found")
                return result
            null_mask = data[self.field_name].isna()
            if null_mask.any():
                for idx in data[null_mask].index:
                    result.add_error(field_name, "Value cannot be null", row_index=idx)
        else:
            if pd.isna(data):
                result.add_error(field_name, "Value cannot be null")

        return result


class CombinedValidationRule(ValidationRule):
    """Combines multiple validation rules."""

    def __init__(self, rules: List[ValidationRule]):
        super().__init__(name="combined")
        self.rules = rules

    def validate(self, data: Any, field_name: str = None) -> ValidationResult:
        """Apply all rules and combine results."""
        result = ValidationResult()

        for rule in self.rules:
            rule_result = rule.validate(data, field_name)
            result.merge(rule_result)

        return result


class ValidationRuleBuilder:
    """Builder for creating validation rules."""

    def range_rule(
        self,
        field_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> RangeValidationRule:
        """Create a range validation rule."""
        return RangeValidationRule(field_name, min_value, max_value)

    def pattern_rule(self, field_name: str, pattern: str) -> PatternValidationRule:
        """Create a pattern validation rule."""
        return PatternValidationRule(field_name, pattern)

    def custom_rule(
        self, field_name: str, validator_func: Callable, error_message: str
    ) -> CustomValidationRule:
        """Create a custom validation rule."""
        return CustomValidationRule(field_name, validator_func, error_message)

    def not_null_rule(self, field_name: str) -> NotNullValidationRule:
        """Create a not-null validation rule."""
        return NotNullValidationRule(field_name)

    def combine_rules(self, rules: List[ValidationRule]) -> CombinedValidationRule:
        """Combine multiple rules into one."""
        return CombinedValidationRule(rules)

    def from_yaml(self, yaml_content: str) -> List[ValidationRule]:
        """
        Load validation rules from YAML configuration.

        Args:
            yaml_content: YAML string with rule definitions

        Returns:
            List of ValidationRule instances
        """
        data = yaml.safe_load(yaml_content)
        rules_data = data.get("rules", data)

        rules = []
        for rule_config in rules_data:
            field = rule_config["field"]
            rule_type = rule_config["type"]

            if rule_type == "range":
                rule = self.range_rule(
                    field, rule_config.get("min"), rule_config.get("max")
                )
            elif rule_type == "pattern":
                rule = self.pattern_rule(field, rule_config["pattern"])
            elif rule_type == "not_null":
                rule = self.not_null_rule(field)
            else:
                continue

            rules.append(rule)

        return rules


class DataQualityFramework:
    """Integrated data quality framework for well data verification."""

    def __init__(self, config: Optional[QualityConfig] = None):
        """
        Initialize data quality framework.

        Args:
            config: Quality configuration
        """
        self.config = config or QualityConfig()

        # Configure volume validator with production ranges from config
        volume_config = {}
        if "oil_volume" in self.config.production_ranges:
            oil_min, oil_max = self.config.production_ranges["oil_volume"]
            volume_config["oil_min"] = oil_min
            volume_config["oil_max"] = oil_max
        if "gas_volume" in self.config.production_ranges:
            gas_min, gas_max = self.config.production_ranges["gas_volume"]
            volume_config["gas_min"] = gas_min
            volume_config["gas_max"] = gas_max

        self.volume_validator = ProductionVolumeValidator(config=volume_config)
        self.completeness_checker = CompletenessChecker()
        self.outlier_detector = OutlierDetector()
        self.rule_builder = ValidationRuleBuilder()

    def run_quality_checks(self, data: pd.DataFrame) -> VerificationResult:
        """
        Run comprehensive quality checks on data.

        Args:
            data: DataFrame to check

        Returns:
            VerificationResult with all quality issues
        """
        result = VerificationResult()
        result.metadata["quality_framework"] = "DataQualityFramework"

        # Run completeness checks
        if self.config.enable_completeness_check:
            if self.config.required_fields:
                completeness_result = self.completeness_checker.check_required_fields(
                    data, self.config.required_fields
                )
                result.merge(completeness_result)

            # Check for zero values in numeric columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            zero_result = self.completeness_checker.check_zero_values(
                data, numeric_cols
            )
            result.merge(zero_result)

        # Run production volume validation
        if "oil_volume" in data.columns:
            oil_result = self.volume_validator.validate_oil_volumes(data)
            result.merge(oil_result)

        if "gas_volume" in data.columns:
            gas_result = self.volume_validator.validate_gas_volumes(data)
            result.merge(gas_result)

        # Run outlier detection
        if self.config.enable_outlier_detection:
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            for col in numeric_cols:
                outlier_result = self.outlier_detector.detect_outliers_zscore(
                    data, col, self.config.outlier_threshold
                )
                result.merge(outlier_result)

        # Apply configured validation rules
        for rule_config in self.config.validation_rules:
            # Create rule from config (simplified for now)
            pass

        # Calculate quality score
        total_issues = len(result.errors) + len(result.warnings)
        total_checks = len(data) * len(data.columns)
        quality_score = (
            max(0, 1 - (total_issues / total_checks)) if total_checks > 0 else 1.0
        )

        result.metadata["quality_score"] = quality_score
        result.metadata["total_rows"] = len(data)
        result.metadata["total_columns"] = len(data.columns)

        return result

    def generate_quality_report(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive quality report.

        Args:
            data: DataFrame to analyze

        Returns:
            Dictionary with quality report
        """
        report = {
            "summary": {},
            "completeness": {},
            "validity": {},
            "outliers": {},
            "recommendations": [],
        }

        # Run quality checks
        result = self.run_quality_checks(data)

        # Summary section
        report["summary"] = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "quality_score": result.metadata.get("quality_score", 0),
            "total_errors": len(result.errors),
            "total_warnings": len(result.warnings),
            "is_valid": result.is_valid,
        }

        # Completeness section
        report["completeness"] = self.completeness_checker.generate_completeness_report(
            data
        )

        # Validity section
        report["validity"] = {"errors_by_field": {}, "warnings_by_field": {}}

        for error in result.errors:
            field = error.field
            if field not in report["validity"]["errors_by_field"]:
                report["validity"]["errors_by_field"][field] = []
            report["validity"]["errors_by_field"][field].append(str(error))

        for warning in result.warnings:
            field = warning.field
            if field not in report["validity"]["warnings_by_field"]:
                report["validity"]["warnings_by_field"][field] = []
            report["validity"]["warnings_by_field"][field].append(str(warning))

        # Outliers section
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        report["outliers"] = {col: [] for col in numeric_cols}

        # Recommendations
        if report["summary"]["quality_score"] < 0.9:
            report["recommendations"].append(
                "Data quality is below acceptable threshold (90%)"
            )

        if report["summary"]["total_errors"] > 0:
            report["recommendations"].append(
                f'Address {report["summary"]["total_errors"]} critical errors before analysis'
            )

        if report["completeness"]["overall_completeness"] < 95:
            report["recommendations"].append(
                "Improve data completeness to at least 95%"
            )

        return report

    def export_results(
        self, result: VerificationResult, path: Path, format: str = "json"
    ) -> None:
        """
        Export quality check results to file.

        Args:
            result: VerificationResult to export
            path: Output file path
            format: Export format ('json', 'csv')
        """
        if format == "json":
            with open(path, "w") as f:
                json.dump(result.to_dict(), f, indent=2, default=str)

        elif format == "csv":
            # Convert errors and warnings to DataFrame
            issues = []
            for error in result.errors:
                issues.append(
                    {
                        "severity": "error",
                        "field": error.field,
                        "message": error.message,
                        "value": str(error.value) if error.value is not None else "",
                        "row_index": error.row_index,
                    }
                )

            for warning in result.warnings:
                issues.append(
                    {
                        "severity": "warning",
                        "field": warning.field,
                        "message": warning.message,
                        "value": (
                            str(warning.value) if warning.value is not None else ""
                        ),
                        "row_index": warning.row_index,
                    }
                )

            df = pd.DataFrame(issues)
            df.to_csv(path, index=False)

        logger.info(f"Exported quality results to {path}")
