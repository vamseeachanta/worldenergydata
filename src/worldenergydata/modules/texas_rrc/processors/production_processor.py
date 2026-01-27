# ABOUTME: Production data processor for Texas RRC oil and gas production records
# ABOUTME: Handles aggregation, normalization, unit conversions, and DataFrame processing

"""
Production Data Processor for Texas RRC.

Processes and transforms oil and gas production data from Texas RRC
with support for aggregation, filtering, unit conversions, and DataFrame operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Union

import pandas as pd

from ..validators import TexasDataValidator

logger = logging.getLogger(__name__)


class ProductionProcessor:
    """
    Processor for Texas RRC production data.

    Features:
    - Production data aggregation by lease, field, or district
    - Date range filtering
    - Unit conversions (MCF, BBL, etc.)
    - Data validation and cleaning
    - Pandas DataFrame support
    """

    # Unit conversion factors
    UNIT_CONVERSIONS = {
        "mcf_to_mmcf": 0.001,  # MCF to MMCF
        "bbl_to_mbbl": 0.001,  # Barrels to thousand barrels
        "mcf_to_boe": 0.1714,  # MCF gas to BOE (barrel oil equivalent)
    }

    # Column name mappings for common PDQ formats
    COLUMN_MAPPINGS = {
        "DISTRICT_NO": "district",
        "LEASE_NO": "lease_number",
        "LEASE_NAME": "lease_name",
        "OPERATOR_NO": "operator_number",
        "OPERATOR_NAME": "operator_name",
        "FIELD_NO": "field_number",
        "FIELD_NAME": "field_name",
        "OIL_BBL": "oil_production",
        "OIL_PROD": "oil_production",
        "GAS_MCF": "gas_production",
        "GAS_PROD": "gas_production",
        "COND_BBL": "condensate",
        "CONDENSATE": "condensate",
        "WATER_BBL": "water_production",
        "WATER_PROD": "water_production",
        "CASINGHEAD_GAS_MCF": "casinghead_gas",
        "PROD_DATE": "production_date",
        "CYCLE_YEAR_MONTH": "production_date",
        "CYCLE_YEAR": "year",
        "CYCLE_MONTH": "month",
    }

    def __init__(self, validator: Optional[TexasDataValidator] = None):
        """
        Initialize production processor.

        Args:
            validator: Optional pre-configured validator
        """
        self.validator = validator or TexasDataValidator()
        self._records_processed = 0
        self._records_invalid = 0

    def process(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        validate: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Process production data from DataFrame or list of records.

        Args:
            data: Input data as DataFrame or list of dicts
            validate: Whether to validate records

        Returns:
            Processed data in the same format as input
        """
        if isinstance(data, pd.DataFrame):
            return self._process_dataframe(data, validate)
        return self._process_records(data, validate)

    def _process_dataframe(
        self,
        df: pd.DataFrame,
        validate: bool = True,
    ) -> pd.DataFrame:
        """
        Process production data from a pandas DataFrame.

        Args:
            df: Input DataFrame with production data
            validate: Whether to validate records

        Returns:
            Processed DataFrame with normalized columns
        """
        if df.empty:
            return df

        self._records_processed = 0
        self._records_invalid = 0

        # Create a copy to avoid modifying the original
        result = df.copy()

        # Normalize column names
        result = self._normalize_columns(result)

        # Normalize district values
        if "district" in result.columns:
            result["district"] = result["district"].apply(
                lambda x: (
                    self.validator.normalize_district(str(x)) if pd.notna(x) else None
                )
            )

        # Parse production date
        if "production_date" in result.columns:
            result["production_date"] = result["production_date"].apply(
                self._parse_production_date
            )
        elif "year" in result.columns and "month" in result.columns:
            result["production_date"] = result.apply(
                lambda row: (
                    f"{int(row['year'])}-{int(row['month']):02d}"
                    if pd.notna(row.get("year")) and pd.notna(row.get("month"))
                    else None
                ),
                axis=1,
            )

        # Convert numeric fields
        numeric_fields = [
            "oil_production",
            "gas_production",
            "water_production",
            "condensate",
            "casinghead_gas",
        ]
        for field in numeric_fields:
            if field in result.columns:
                result[field] = pd.to_numeric(result[field], errors="coerce").fillna(
                    0.0
                )

        # Calculate BOE (barrel oil equivalent)
        gas_col = "gas_production" if "gas_production" in result.columns else None
        oil_col = "oil_production" if "oil_production" in result.columns else None

        if gas_col and oil_col:
            result["boe_total"] = (
                result[oil_col] + result[gas_col] * self.UNIT_CONVERSIONS["mcf_to_boe"]
            )
        elif oil_col:
            result["boe_total"] = result[oil_col]
        else:
            result["boe_total"] = 0.0

        # Normalize API numbers if present
        if "api_number" in result.columns:
            result["api_number_14"] = result["api_number"].apply(
                self._normalize_api_to_14_digit
            )

        # Validation
        if validate:
            valid_mask = result.apply(self._validate_row, axis=1)
            invalid_count = (~valid_mask).sum()
            self._records_invalid = invalid_count
            self._records_processed = len(result) - invalid_count
            result = result[valid_mask].copy()
        else:
            self._records_processed = len(result)

        logger.info(
            f"Processed {self._records_processed} DataFrame rows, "
            f"{self._records_invalid} invalid"
        )
        return result

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names to standard format.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with normalized column names
        """
        # Create mapping from uppercase to standard names
        rename_map = {}
        for col in df.columns:
            upper_col = col.upper().replace(" ", "_")
            if upper_col in self.COLUMN_MAPPINGS:
                rename_map[col] = self.COLUMN_MAPPINGS[upper_col]
            else:
                rename_map[col] = col.lower().replace(" ", "_")

        return df.rename(columns=rename_map)

    def _validate_row(self, row: pd.Series) -> bool:
        """
        Validate a single row of production data.

        Args:
            row: DataFrame row

        Returns:
            True if valid
        """
        record = row.to_dict()
        is_valid, _ = self.validator.validate_production_data(record)
        return is_valid

    def _normalize_api_to_14_digit(self, api: Any) -> Optional[str]:
        """
        Normalize API number to 14-digit format.

        Texas uses 10-digit API (42-XXX-XXXXX), extended to 14-digit
        with sidetrack (2 digits) and completion (2 digits) suffixes.

        Args:
            api: API number in various formats

        Returns:
            14-digit API number or None
        """
        if pd.isna(api) or api is None:
            return None

        # Clean the input
        api_str = str(api).strip().replace("-", "").replace(" ", "")

        # Handle different lengths
        if len(api_str) == 10:
            # Standard Texas API: add 0000 suffix (original wellbore, first completion)
            return f"{api_str}0000"
        elif len(api_str) == 12:
            # Has sidetrack, add completion suffix
            return f"{api_str}00"
        elif len(api_str) == 14:
            return api_str
        elif len(api_str) > 14:
            return api_str[:14]
        else:
            # Invalid length
            return None

    def _process_records(
        self,
        records: List[Dict[str, Any]],
        validate: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Process production records from a list of dicts.

        Args:
            records: Raw production records
            validate: Whether to validate records

        Returns:
            Processed and validated records
        """
        processed = []
        self._records_processed = 0
        self._records_invalid = 0

        for record in records:
            try:
                processed_record = self._process_record(record)

                if validate:
                    is_valid, errors = self.validator.validate_production_data(
                        processed_record
                    )
                    if not is_valid:
                        logger.debug(f"Invalid record: {errors}")
                        self._records_invalid += 1
                        continue

                processed.append(processed_record)
                self._records_processed += 1

            except Exception as e:
                logger.warning(f"Error processing record: {e}")
                self._records_invalid += 1

        logger.info(
            f"Processed {self._records_processed} records, "
            f"{self._records_invalid} invalid"
        )
        return processed

    def _process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single production record.

        Args:
            record: Raw record

        Returns:
            Processed record
        """
        processed = record.copy()

        # Normalize district
        if "district" in processed:
            processed["district"] = self.validator.normalize_district(
                str(processed["district"])
            )

        # Parse production date
        if "production_date" in processed:
            processed["production_date"] = self._parse_production_date(
                processed["production_date"]
            )

        # Ensure numeric fields are floats
        numeric_fields = [
            "oil_production",
            "gas_production",
            "water_production",
            "condensate",
        ]
        for field in numeric_fields:
            if field in processed and processed[field] is not None:
                try:
                    processed[field] = float(processed[field])
                except (ValueError, TypeError):
                    processed[field] = 0.0

        # Calculate BOE if gas production exists
        gas_prod = processed.get("gas_production", 0) or 0
        oil_prod = processed.get("oil_production", 0) or 0
        if gas_prod > 0:
            boe_from_gas = gas_prod * self.UNIT_CONVERSIONS["mcf_to_boe"]
            processed["boe_total"] = oil_prod + boe_from_gas
        else:
            processed["boe_total"] = oil_prod

        # Normalize API to 14-digit if present
        if "api_number" in processed:
            processed["api_number_14"] = self._normalize_api_to_14_digit(
                processed["api_number"]
            )

        return processed

    def _parse_production_date(self, date_value: Any) -> Optional[str]:
        """
        Parse production date to ISO format (YYYY-MM).

        Args:
            date_value: Date value in various formats

        Returns:
            ISO date string or None
        """
        if date_value is None or pd.isna(date_value):
            return None

        date_str = str(date_value).strip()
        if not date_str:
            return None

        # Try various date formats
        formats = [
            "%Y%m",  # YYYYMM (common in PDQ)
            "%Y-%m",  # YYYY-MM
            "%m/%Y",  # MM/YYYY
            "%Y-%m-%d",  # YYYY-MM-DD
            "%m/%d/%Y",  # MM/DD/YYYY
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m")
            except ValueError:
                continue

        return date_str

    def aggregate_monthly(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Aggregate production data by month.

        Args:
            data: Production data

        Returns:
            DataFrame with monthly aggregates
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty:
            return df

        agg_cols = {
            "oil_production": "sum",
            "gas_production": "sum",
            "water_production": "sum",
            "condensate": "sum",
            "boe_total": "sum",
        }

        # Filter to columns that exist
        agg_cols = {k: v for k, v in agg_cols.items() if k in df.columns}

        if "production_date" not in df.columns:
            return df

        return df.groupby("production_date").agg(agg_cols).reset_index()

    def aggregate_annual(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Aggregate production data by year.

        Args:
            data: Production data

        Returns:
            DataFrame with annual aggregates
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty:
            return df

        # Extract year from production_date
        if "production_date" in df.columns:
            df["year"] = df["production_date"].apply(
                lambda x: x[:4] if x and len(x) >= 4 else None
            )
        elif "year" not in df.columns:
            return df

        agg_cols = {
            "oil_production": "sum",
            "gas_production": "sum",
            "water_production": "sum",
            "condensate": "sum",
            "boe_total": "sum",
        }

        # Filter to columns that exist
        agg_cols = {k: v for k, v in agg_cols.items() if k in df.columns}

        return df.groupby("year").agg(agg_cols).reset_index()

    def aggregate_by_district(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Aggregate production by RRC district.

        Args:
            data: Production data

        Returns:
            DataFrame with district-level aggregates
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty or "district" not in df.columns:
            return df

        agg_cols = {
            "oil_production": "sum",
            "gas_production": "sum",
            "water_production": "sum",
            "condensate": "sum",
            "boe_total": "sum",
        }

        # Filter to columns that exist
        agg_cols = {k: v for k, v in agg_cols.items() if k in df.columns}

        result = df.groupby("district").agg(agg_cols).reset_index()

        # Add lease count if available
        if "lease_number" in df.columns:
            lease_counts = (
                df.groupby("district")["lease_number"].nunique().reset_index()
            )
            lease_counts.columns = ["district", "lease_count"]
            result = result.merge(lease_counts, on="district", how="left")

        return result

    def aggregate_by_lease(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Aggregate production by lease number.

        Args:
            data: Production data

        Returns:
            DataFrame with lease-level aggregates
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty or "lease_number" not in df.columns:
            return df

        # Group by lease and aggregate
        group_cols = ["lease_number"]
        if "lease_name" in df.columns:
            group_cols.append("lease_name")
        if "operator_name" in df.columns:
            group_cols.append("operator_name")
        if "district" in df.columns:
            group_cols.append("district")

        agg_cols = {
            "oil_production": "sum",
            "gas_production": "sum",
            "water_production": "sum",
            "condensate": "sum",
            "boe_total": "sum",
        }

        # Filter to columns that exist
        agg_cols = {k: v for k, v in agg_cols.items() if k in df.columns}

        return df.groupby(group_cols, as_index=False).agg(agg_cols)

    def filter_by_date_range(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        start_date: str,
        end_date: str,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter data by date range.

        Args:
            data: Production data
            start_date: Start date (YYYY-MM format)
            end_date: End date (YYYY-MM format)

        Returns:
            Filtered data
        """
        if isinstance(data, pd.DataFrame):
            if "production_date" not in data.columns:
                return data
            mask = (data["production_date"] >= start_date) & (
                data["production_date"] <= end_date
            )
            return data[mask].copy()

        # List of dicts
        return [
            r
            for r in data
            if r.get("production_date")
            and start_date <= r["production_date"] <= end_date
        ]

    def iter_processed(
        self,
        records: Iterator[Dict[str, Any]],
        validate: bool = True,
    ) -> Iterator[Dict[str, Any]]:
        """
        Process records with streaming.

        Args:
            records: Iterator of raw records
            validate: Whether to validate

        Yields:
            Processed records
        """
        for record in records:
            try:
                processed = self._process_record(record)

                if validate:
                    is_valid, _ = self.validator.validate_production_data(processed)
                    if not is_valid:
                        continue

                yield processed

            except Exception as e:
                logger.warning(f"Error processing record: {e}")

    @property
    def stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            "records_processed": self._records_processed,
            "records_invalid": self._records_invalid,
            "validation_stats": self.validator.get_statistics(),
        }


__all__ = ["ProductionProcessor"]
