"""
Data Validators for SME Financial Analysis
Validates input and output data for correctness and consistency
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .data_loader import normalize_lease_number

logger = logging.getLogger(__name__)


def validate_required_columns(df: pd.DataFrame, required_cols: List[str]) -> bool:
    """
    Validate that required columns exist in dataframe

    Args:
        df: DataFrame to validate
        required_cols: List of required column names

    Returns:
        True if all columns present

    Raises:
        ValueError: If required columns missing
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return True


def validate_date_columns(df: pd.DataFrame, date_cols: List[str]) -> pd.DataFrame:
    """
    Validate and convert date columns to datetime

    Args:
        df: DataFrame with date columns
        date_cols: List of column names to convert

    Returns:
        DataFrame with converted date columns
    """
    result = df.copy()

    for col in date_cols:
        if col in result.columns:
            # Try to convert to datetime
            result[col] = pd.to_datetime(result[col], errors="coerce")

            # Log warning for invalid dates
            invalid_count = result[col].isna().sum()
            if invalid_count > 0:
                logger.warning(
                    f"Column '{col}' has {invalid_count} invalid date values"
                )

    return result


def validate_numeric_columns(
    df: pd.DataFrame, numeric_cols: List[str], fill_invalid: Optional[float] = None
) -> pd.DataFrame:
    """
    Validate and convert numeric columns

    Args:
        df: DataFrame with numeric columns
        numeric_cols: List of column names to convert
        fill_invalid: Value to fill invalid entries (None to keep NaN)

    Returns:
        DataFrame with converted numeric columns
    """
    result = df.copy()

    for col in numeric_cols:
        if col in result.columns:
            # Convert to numeric
            result[col] = pd.to_numeric(result[col], errors="coerce")

            # Fill invalid values if requested
            if fill_invalid is not None:
                result[col] = result[col].fillna(fill_invalid)

            # Log warning for invalid values
            invalid_count = result[col].isna().sum()
            if invalid_count > 0:
                logger.warning(
                    f"Column '{col}' has {invalid_count} invalid numeric values"
                )

    return result


def validate_lease_numbers(
    df: pd.DataFrame, lease_col: str = "LEASE_NUM"
) -> pd.DataFrame:
    """
    Validate and normalize lease numbers

    Args:
        df: DataFrame with lease numbers
        lease_col: Name of lease number column

    Returns:
        DataFrame with normalized lease numbers
    """
    if df.empty or lease_col not in df.columns:
        return df

    result = df.copy()
    warnings = []

    # Normalize lease numbers
    for idx, val in enumerate(result[lease_col]):
        original = str(val).strip()
        normalized = normalize_lease_number(original)

        # Check if normalization failed (non-standard format)
        if normalized == original and not re.match(r"^G\d+$", normalized):
            warnings.append(f"Non-standard lease number format: {original}")

        result.loc[idx, lease_col] = normalized

    if warnings:
        logger.warning(f"Found {len(warnings)} non-standard lease numbers")

    return result


def validate_production_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate production data

    Args:
        df: Production data DataFrame

    Returns:
        Tuple of (is_valid, error_list)
    """
    errors = []

    # Check for required columns
    if "YearMonth" not in df.columns:
        errors.append("Missing required column: YearMonth")
        return False, errors

    # Check for negative production
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col != "YearMonth" and (df[col] < 0).any():
            errors.append(f"Column '{col}' contains negative production values")

    # Check date validity
    if not pd.api.types.is_datetime64_any_dtype(df["YearMonth"]):
        try:
            df["YearMonth"] = pd.to_datetime(df["YearMonth"])
        except Exception:
            errors.append("YearMonth column contains invalid dates")

    return len(errors) == 0, errors


def validate_drilling_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate drilling and completion data

    Args:
        df: D&C data DataFrame

    Returns:
        Tuple of (is_valid, error_list)
    """
    errors = []

    # Check for negative days
    if (
        "DRILL_DAYS" in df.columns
        and (pd.to_numeric(df["DRILL_DAYS"], errors="coerce") < 0).any()
    ):
        errors.append("DRILL_DAYS contains negative values")

    if (
        "COMP_DAYS" in df.columns
        and (pd.to_numeric(df["COMP_DAYS"], errors="coerce") < 0).any()
    ):
        errors.append("COMP_DAYS contains negative values")

    # Check date consistency
    if "WELL_SPUD_DATE" in df.columns and "TOTAL_DEPTH_DATE" in df.columns:
        spud_dates = pd.to_datetime(df["WELL_SPUD_DATE"], errors="coerce")
        td_dates = pd.to_datetime(df["TOTAL_DEPTH_DATE"], errors="coerce")

        # Check if TD is before spud
        invalid_dates = (
            (td_dates < spud_dates) & pd.notna(spud_dates) & pd.notna(td_dates)
        )
        if invalid_dates.any():
            count = invalid_dates.sum()
            errors.append(f"{count} wells have total depth date before spud date")

    return len(errors) == 0, errors


def validate_financial_assumptions(
    assumptions: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Validate financial assumptions

    Args:
        assumptions: Financial assumptions dictionary

    Returns:
        Tuple of (is_valid, error_list)
    """
    errors = []

    # Required assumptions
    required = [
        "NPV_Discount_Rate",
        "Drilling_Cost_Per_Day_USD",
        "Completion_Cost_Per_Day_USD",
        "Oil_Price_Per_Barrel",
        "OPEX_Per_Barrel",
        "Tax_Rate",
    ]

    # Check for missing required assumptions
    missing = [key for key in required if key not in assumptions]
    if missing:
        errors.append(f"Missing required assumptions: {missing}")

    # Validate discount rate
    if "NPV_Discount_Rate" in assumptions:
        rate = assumptions["NPV_Discount_Rate"]
        if rate < 0:
            errors.append("NPV discount rate cannot be negative")
        elif rate > 1:
            errors.append("NPV discount rate seems too high (>100%)")

    # Validate tax rate
    if "Tax_Rate" in assumptions:
        tax = assumptions["Tax_Rate"]
        if tax < 0:
            errors.append("Tax rate cannot be negative")
        elif tax > 1:
            errors.append("Tax rate cannot exceed 100%")

    # Validate costs
    cost_keys = [
        "Drilling_Cost_Per_Day_USD",
        "Completion_Cost_Per_Day_USD",
        "OPEX_Per_Barrel",
    ]
    for key in cost_keys:
        if key in assumptions and assumptions[key] < 0:
            errors.append(f"{key} cannot be negative")

    # Validate oil price
    if "Oil_Price_Per_Barrel" in assumptions:
        price = assumptions["Oil_Price_Per_Barrel"]
        if price <= 0:
            errors.append("Oil price must be positive")

    return len(errors) == 0, errors


class DataValidator:
    """
    Comprehensive data validator for SME financial analysis
    """

    def __init__(self):
        """Initialize validator"""
        self._validation_report = {"warnings": [], "errors": [], "info": []}
        self._validation_count = 0
        self._passed_count = 0
        self._failed_count = 0

    def validate_lease_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and normalize lease numbers

        Args:
            df: DataFrame with lease numbers

        Returns:
            DataFrame with normalized lease numbers
        """
        self._validation_count += 1

        try:
            result = validate_lease_numbers(df)
            self._passed_count += 1
            return result
        except Exception as e:
            self._failed_count += 1
            self._validation_report["errors"].append(str(e))
            raise

    def validate_production_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate production data"""
        self._validation_count += 1
        is_valid, errors = validate_production_data(df)

        if is_valid:
            self._passed_count += 1
        else:
            self._failed_count += 1
            self._validation_report["errors"].extend(errors)

        return is_valid, errors

    def validate_drilling_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate drilling data"""
        self._validation_count += 1
        is_valid, errors = validate_drilling_data(df)

        if is_valid:
            self._passed_count += 1
        else:
            self._failed_count += 1
            self._validation_report["errors"].extend(errors)

        return is_valid, errors

    def validate_financial_assumptions(
        self, assumptions: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate financial assumptions"""
        self._validation_count += 1
        is_valid, errors = validate_financial_assumptions(assumptions)

        if is_valid:
            self._passed_count += 1
        else:
            self._failed_count += 1
            self._validation_report["errors"].extend(errors)

        return is_valid, errors

    def check_data_consistency(
        self, production_df: pd.DataFrame, drilling_df: pd.DataFrame
    ) -> List[str]:
        """
        Check consistency between different data sources

        Args:
            production_df: Production data
            drilling_df: Drilling data

        Returns:
            List of warnings
        """
        warnings = []

        # Get wells from production
        prod_wells = set()
        if not production_df.empty:
            # Check if wells are columns
            if "YearMonth" in production_df.columns:
                prod_wells = set([c for c in production_df.columns if c != "YearMonth"])
            elif "WELL_NAME" in production_df.columns:
                prod_wells = set(production_df["WELL_NAME"].unique())

        # Get wells from drilling
        drill_wells = set()
        if not drilling_df.empty:
            for col in ["WELL_NAME", "WELL", "API_WELL_NUMBER"]:
                if col in drilling_df.columns:
                    drill_wells = set(drilling_df[col].unique())
                    break

        # Check for mismatches
        prod_only = prod_wells - drill_wells
        drill_only = drill_wells - prod_wells

        if prod_only:
            warnings.append(f"Wells in production but not drilling: {prod_only}")
            self._validation_report["warnings"].append(
                f"Production-only wells: {len(prod_only)}"
            )

        if drill_only:
            warnings.append(f"Wells in drilling but not production: {drill_only}")
            self._validation_report["warnings"].append(
                f"Drilling-only wells: {len(drill_only)}"
            )

        return warnings

    def validate_data_types(
        self, df: pd.DataFrame, type_map: Dict[str, str]
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Validate data types of columns

        Args:
            df: DataFrame to validate
            type_map: Expected types for columns

        Returns:
            Tuple of (is_valid, mismatches)
        """
        mismatches = {}

        for col, expected_type in type_map.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if actual_type != expected_type:
                    mismatches[col] = f"Expected {expected_type}, got {actual_type}"

        return len(mismatches) == 0, mismatches

    def validate_ranges(
        self,
        df: pd.DataFrame,
        range_rules: Dict[str, Tuple[Optional[float], Optional[float]]],
    ) -> Dict[str, List[int]]:
        """
        Validate value ranges

        Args:
            df: DataFrame to validate
            range_rules: Dict of column to (min, max) tuples

        Returns:
            Dictionary of column to list of violating row indices
        """
        violations = {}

        for col, (min_val, max_val) in range_rules.items():
            if col not in df.columns:
                continue

            col_violations = []
            values = pd.to_numeric(df[col], errors="coerce")

            # Check minimum
            if min_val is not None:
                below_min = values < min_val
                if below_min.any():
                    col_violations.extend(df.index[below_min].tolist())

            # Check maximum
            if max_val is not None:
                above_max = values > max_val
                if above_max.any():
                    col_violations.extend(df.index[above_max].tolist())

            if col_violations:
                violations[col] = list(set(col_violations))

        return violations

    def run_comprehensive_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive validation on all data

        Args:
            data: Dictionary with data components

        Returns:
            Validation results dictionary
        """
        results = {"all_valid": True, "errors": [], "warnings": []}

        # Validate leases
        if "leases" in data:
            try:
                validate_required_columns(data["leases"], ["LEASE_NUM", "DEV_NAME"])
                results["leases_valid"] = True
            except Exception as e:
                results["leases_valid"] = False
                results["errors"].append(f"Lease validation: {str(e)}")
                results["all_valid"] = False

        # Validate production
        if "production" in data:
            is_valid, errors = self.validate_production_data(data["production"])
            results["production_valid"] = is_valid
            if not is_valid:
                results["errors"].extend(errors)
                results["all_valid"] = False

        # Validate drilling
        if "drilling" in data:
            is_valid, errors = self.validate_drilling_data(data["drilling"])
            results["drilling_valid"] = is_valid
            if not is_valid:
                results["errors"].extend(errors)
                results["all_valid"] = False

        # Validate assumptions
        if "assumptions" in data:
            is_valid, errors = self.validate_financial_assumptions(data["assumptions"])
            results["assumptions_valid"] = is_valid
            if not is_valid:
                results["errors"].extend(errors)
                results["all_valid"] = False

        # Check consistency
        if "production" in data and "drilling" in data:
            warnings = self.check_data_consistency(data["production"], data["drilling"])
            results["warnings"].extend(warnings)

        return results

    def get_validation_report(self) -> Dict[str, Any]:
        """
        Get validation report

        Returns:
            Validation report dictionary
        """
        return {
            "summary": {
                "total_validations": self._validation_count,
                "passed": self._passed_count,
                "failed": self._failed_count,
            },
            "details": self._validation_report,
            "warnings": self._validation_report["warnings"],
            "errors": self._validation_report["errors"],
        }

    def generate_validation_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive validation report

        Returns:
            Validation report with timestamp
        """
        report = self.get_validation_report()
        report["timestamp"] = datetime.now().isoformat()
        return report

    def reset_validation_state(self):
        """Reset validation counters and reports"""
        self._validation_report = {"warnings": [], "errors": [], "info": []}
        self._validation_count = 0
        self._passed_count = 0
        self._failed_count = 0
