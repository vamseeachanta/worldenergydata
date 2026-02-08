# ABOUTME: Drilling permit processor for Texas RRC permit data with DataFrame support
# ABOUTME: Handles permit type classification, date parsing, horizontal well data, and field/lease linking

"""
Drilling Permit Processor for Texas RRC.

Processes and transforms drilling permit data from Texas RRC
with support for permit type classification, status tracking,
horizontal well data handling, and field/lease linkage.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Union

import pandas as pd

from ..validators import TexasDataValidator

logger = logging.getLogger(__name__)


class PermitProcessor:
    """
    Processor for Texas RRC drilling permit data.

    Features:
    - Permit type classification (new drill, recompletion, etc.)
    - Permit status tracking
    - Date parsing and validation
    - Location validation
    - Horizontal well data handling
    - Field and lease linkage
    - Pandas DataFrame support
    """

    # Permit type mapping (RRC codes to descriptive names)
    PERMIT_TYPE_MAPPING = {
        "01": "new_drill",
        "02": "recompletion",
        "03": "reenter",
        "04": "field_transfer",
        "05": "amended",
        "06": "plug_back",
        "07": "sidetrack",
        "08": "workover",
        "1": "new_drill",
        "2": "recompletion",
        "3": "reenter",
        "4": "field_transfer",
        "5": "amended",
        "6": "plug_back",
        "7": "sidetrack",
        "8": "workover",
        "N": "new_drill",
        "ND": "new_drill",
        "R": "recompletion",
        "RE": "reenter",
        "W": "workover",
        "ST": "sidetrack",
        "AM": "amended",
    }

    # Permit status mapping
    PERMIT_STATUS_MAPPING = {
        "A": "approved",
        "P": "pending",
        "D": "denied",
        "E": "expired",
        "C": "cancelled",
        "W": "withdrawn",
        "AP": "approved",
        "PN": "pending",
        "DN": "denied",
        "EX": "expired",
        "CA": "cancelled",
        "WD": "withdrawn",
    }

    # Well type classification
    WELL_PURPOSE_MAPPING = {
        "O": "oil",
        "G": "gas",
        "I": "injection",
        "D": "disposal",
        "S": "service",
        "W": "water",
        "OIL": "oil",
        "GAS": "gas",
        "INJ": "injection",
        "DSP": "disposal",
        "SVC": "service",
        "WAT": "water",
        "SWD": "salt_water_disposal",
    }

    # Column name mappings for RRC permit formats
    COLUMN_MAPPINGS = {
        "PERMIT_NO": "permit_number",
        "PERMIT_NUMBER": "permit_number",
        "PERMIT_TYPE": "permit_type",
        "TYPE": "permit_type",
        "PERMIT_STATUS": "permit_status",
        "STATUS": "permit_status",
        "API_NO": "api_number",
        "API_NUMBER": "api_number",
        "API": "api_number",
        "DISTRICT_NO": "district",
        "DISTRICT": "district",
        "LEASE_NO": "lease_number",
        "LEASE_NAME": "lease_name",
        "WELL_NO": "well_number",
        "WELL_NAME": "well_name",
        "OPERATOR_NO": "operator_number",
        "OPERATOR_NAME": "operator_name",
        "FIELD_NO": "field_number",
        "FIELD_NAME": "field_name",
        "COUNTY_NO": "county_code",
        "COUNTY_NAME": "county_name",
        "APPROVED_DATE": "approved_date",
        "APPROVAL_DATE": "approved_date",
        "FILED_DATE": "filed_date",
        "FILE_DATE": "filed_date",
        "EXPIRATION_DATE": "expiration_date",
        "EXPIRE_DATE": "expiration_date",
        "TOTAL_DEPTH": "total_depth",
        "PROPOSED_DEPTH": "total_depth",
        "TD": "total_depth",
        "LATITUDE": "latitude",
        "LAT": "latitude",
        "LONGITUDE": "longitude",
        "LON": "longitude",
        "LONG": "longitude",
        "WELL_PURPOSE": "well_purpose",
        "PURPOSE": "well_purpose",
        "WELLBORE_PROFILE": "wellbore_profile",
        "PROFILE": "wellbore_profile",
        "HORIZONTAL_LENGTH": "horizontal_length",
        "HZ_LENGTH": "horizontal_length",
        "LATERAL_LENGTH": "horizontal_length",
    }

    def __init__(self, validator: Optional[TexasDataValidator] = None):
        """
        Initialize permit processor.

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
        Process permit data from DataFrame or list of records.

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
        Process permit data from a pandas DataFrame.

        Args:
            df: Input DataFrame with permit data
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

        # Normalize API numbers if present
        if "api_number" in result.columns:
            result["api_number_formatted"] = result["api_number"].apply(
                lambda x: (
                    self.validator.normalize_api_number(str(x)) if pd.notna(x) else None
                )
            )
            result["api_number_14"] = result["api_number"].apply(
                self._normalize_api_to_14_digit
            )

        # Normalize district values
        if "district" in result.columns:
            result["district"] = result["district"].apply(
                lambda x: (
                    self.validator.normalize_district(str(x)) if pd.notna(x) else None
                )
            )

        # Process permit type
        if "permit_type" in result.columns:
            result["permit_type_code"] = result["permit_type"].astype(str).str.strip()
            result["permit_type"] = result["permit_type_code"].apply(
                lambda x: self.PERMIT_TYPE_MAPPING.get(
                    x.upper() if x else "", x.lower() if x else None
                )
            )

        # Process permit status
        if "permit_status" in result.columns:
            result["permit_status_code"] = (
                result["permit_status"].astype(str).str.upper().str.strip()
            )
            result["permit_status"] = result["permit_status_code"].apply(
                lambda x: self.PERMIT_STATUS_MAPPING.get(x, x.lower() if x else None)
            )

        # Process well purpose
        if "well_purpose" in result.columns:
            result["well_purpose_code"] = (
                result["well_purpose"].astype(str).str.upper().str.strip()
            )
            result["well_purpose"] = result["well_purpose_code"].apply(
                lambda x: self.WELL_PURPOSE_MAPPING.get(x, x.lower() if x else None)
            )

        # Detect horizontal wells
        result["is_horizontal"] = self._detect_horizontal_wells(result)

        # Process coordinates
        result = self._process_coordinates(result)

        # Convert numeric fields
        numeric_fields = ["total_depth", "horizontal_length"]
        for field in numeric_fields:
            if field in result.columns:
                result[field] = pd.to_numeric(result[field], errors="coerce")

        # Parse dates
        date_fields = ["approved_date", "filed_date", "expiration_date"]
        for field in date_fields:
            if field in result.columns:
                result[field] = result[field].apply(self._parse_date)

        # Calculate permit age (days since approval)
        if "approved_date" in result.columns:
            result["permit_age_days"] = result["approved_date"].apply(
                self._calculate_permit_age
            )

        # Link fields and leases
        result = self._link_field_lease(result)

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
            f"Processed {self._records_processed} permit records, "
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
        rename_map = {}
        for col in df.columns:
            upper_col = col.upper().replace(" ", "_")
            if upper_col in self.COLUMN_MAPPINGS:
                rename_map[col] = self.COLUMN_MAPPINGS[upper_col]
            else:
                rename_map[col] = col.lower().replace(" ", "_")

        return df.rename(columns=rename_map)

    def _normalize_api_to_14_digit(self, api: Any) -> Optional[str]:
        """
        Normalize API number to 14-digit format.

        Args:
            api: API number in various formats

        Returns:
            14-digit API number or None
        """
        if pd.isna(api) or api is None:
            return None

        # Clean the input
        api_str = str(api).strip().replace("-", "").replace(" ", "")
        api_str = re.sub(r"[^\d]", "", api_str)

        # Handle different lengths
        if len(api_str) == 10:
            return f"{api_str}0000"
        elif len(api_str) == 12:
            return f"{api_str}00"
        elif len(api_str) == 14:
            return api_str
        elif len(api_str) > 14:
            return api_str[:14]
        else:
            return None

    def _detect_horizontal_wells(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect horizontal wells from available indicators.

        Args:
            df: DataFrame with permit data

        Returns:
            Boolean Series indicating horizontal wells
        """
        indicators = pd.Series([False] * len(df), index=df.index)

        # Check wellbore_profile column
        if "wellbore_profile" in df.columns:
            indicators = indicators | df["wellbore_profile"].str.upper().str.contains(
                "HORIZONTAL|HZ", na=False
            )

        # Check permit_type column
        if "permit_type" in df.columns:
            indicators = indicators | df["permit_type"].str.lower().str.contains(
                "horizontal", na=False
            )

        # Check for horizontal_length > 0
        if "horizontal_length" in df.columns:
            indicators = indicators | (
                pd.to_numeric(df["horizontal_length"], errors="coerce") > 0
            )

        return indicators

    def _process_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process and validate coordinates.

        Args:
            df: DataFrame with coordinate columns

        Returns:
            DataFrame with processed coordinates
        """
        result = df.copy()

        # Convert latitude/longitude to float
        if "latitude" in result.columns:
            result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")

        if "longitude" in result.columns:
            result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")

        # Validate coordinates are within Texas bounds
        if "latitude" in result.columns and "longitude" in result.columns:
            # Correct positive longitudes (should be negative for Texas)
            needs_correction = (result["longitude"] > 0) & (result["longitude"] < 107)
            result.loc[needs_correction, "longitude"] = -result.loc[
                needs_correction, "longitude"
            ]

            result["coordinates_valid"] = result.apply(
                lambda row: self._validate_coordinates(
                    row.get("latitude"), row.get("longitude")
                ),
                axis=1,
            )

        return result

    def _validate_coordinates(self, lat: Optional[float], lon: Optional[float]) -> bool:
        """
        Validate coordinates are within Texas bounds.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            True if valid
        """
        if pd.isna(lat) or pd.isna(lon):
            return False

        is_valid, _ = self.validator.validate_texas_coordinates(lat, lon)
        return is_valid

    def _link_field_lease(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create composite keys for field and lease linkage.

        Args:
            df: DataFrame with permit data

        Returns:
            DataFrame with linkage keys
        """
        result = df.copy()

        # Create field key (district + field_number)
        if "district" in result.columns and "field_number" in result.columns:
            result["field_key"] = result.apply(
                lambda row: (
                    f"{row['district']}-{row['field_number']}"
                    if pd.notna(row.get("district"))
                    and pd.notna(row.get("field_number"))
                    else None
                ),
                axis=1,
            )

        # Create lease key (district + lease_number)
        if "district" in result.columns and "lease_number" in result.columns:
            result["lease_key"] = result.apply(
                lambda row: (
                    f"{row['district']}-{row['lease_number']}"
                    if pd.notna(row.get("district"))
                    and pd.notna(row.get("lease_number"))
                    else None
                ),
                axis=1,
            )

        return result

    def _validate_row(self, row: pd.Series) -> bool:
        """
        Validate a single row of permit data.

        Args:
            row: DataFrame row

        Returns:
            True if valid
        """
        record = row.to_dict()
        is_valid, _ = self.validator.validate_permit_data(record)
        return is_valid

    def _parse_date(self, date_value: Any) -> Optional[str]:
        """
        Parse date to ISO format.

        Args:
            date_value: Date value

        Returns:
            ISO date string or None
        """
        if date_value is None or pd.isna(date_value):
            return None

        date_str = str(date_value).strip()
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%Y%m%d",
            "%m-%d-%Y",
            "%d-%b-%Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.split()[0], fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str

    def _calculate_permit_age(self, approved_date: Optional[str]) -> Optional[int]:
        """
        Calculate permit age in days from approval date.

        Args:
            approved_date: Approval date in ISO format

        Returns:
            Age in days or None
        """
        if not approved_date or pd.isna(approved_date):
            return None

        try:
            dt = datetime.strptime(approved_date, "%Y-%m-%d")
            return (datetime.now() - dt).days
        except (ValueError, TypeError):
            return None

    def _process_records(
        self,
        records: List[Dict[str, Any]],
        validate: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Process permit records from a list of dicts.

        Args:
            records: Raw permit records
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
                    is_valid, errors = self.validator.validate_permit_data(
                        processed_record
                    )
                    if not is_valid:
                        logger.debug(f"Invalid permit record: {errors}")
                        self._records_invalid += 1
                        continue

                processed.append(processed_record)
                self._records_processed += 1

            except Exception as e:
                logger.warning(f"Error processing permit record: {e}")
                self._records_invalid += 1

        logger.info(
            f"Processed {self._records_processed} permit records, "
            f"{self._records_invalid} invalid"
        )
        return processed

    def _process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single permit record.

        Args:
            record: Raw record

        Returns:
            Processed record
        """
        processed = record.copy()

        # Normalize API number if present
        if "api_number" in processed:
            api = str(processed["api_number"])
            processed["api_number_formatted"] = self.validator.normalize_api_number(api)
            processed["api_number_14"] = self._normalize_api_to_14_digit(api)

        # Normalize district
        if "district" in processed:
            processed["district"] = self.validator.normalize_district(
                str(processed["district"])
            )

        # Process permit type
        if "permit_type" in processed:
            type_code = str(processed["permit_type"]).strip()
            processed["permit_type_code"] = type_code
            processed["permit_type"] = self.PERMIT_TYPE_MAPPING.get(
                type_code.upper(), type_code.lower()
            )

        # Process permit status
        if "permit_status" in processed:
            status_code = str(processed["permit_status"]).upper().strip()
            processed["permit_status_code"] = status_code
            processed["permit_status"] = self.PERMIT_STATUS_MAPPING.get(
                status_code, status_code.lower()
            )

        # Process well purpose
        if "well_purpose" in processed:
            purpose_code = str(processed["well_purpose"]).upper().strip()
            processed["well_purpose_code"] = purpose_code
            processed["well_purpose"] = self.WELL_PURPOSE_MAPPING.get(
                purpose_code, purpose_code.lower()
            )

        # Parse dates
        for date_field in ["approved_date", "filed_date", "expiration_date"]:
            if date_field in processed:
                processed[date_field] = self._parse_date(processed[date_field])

        # Calculate permit age
        if processed.get("approved_date"):
            processed["permit_age_days"] = self._calculate_permit_age(
                processed["approved_date"]
            )

        # Validate and process coordinates
        lat = processed.get("latitude")
        lon = processed.get("longitude")
        if lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)

                # Correct positive longitudes
                if lon_f > 0 and lon_f < 107:
                    lon_f = -lon_f

                processed["latitude"] = lat_f
                processed["longitude"] = lon_f
                is_valid, _ = self.validator.validate_texas_coordinates(lat_f, lon_f)
                processed["coordinates_valid"] = is_valid
            except (ValueError, TypeError):
                processed["coordinates_valid"] = False

        # Process total depth
        if "total_depth" in processed:
            try:
                processed["total_depth"] = float(processed["total_depth"])
            except (ValueError, TypeError):
                processed["total_depth"] = None

        # Process horizontal length
        if "horizontal_length" in processed:
            try:
                processed["horizontal_length"] = float(processed["horizontal_length"])
                processed["is_horizontal"] = processed["horizontal_length"] > 0
            except (ValueError, TypeError):
                processed["horizontal_length"] = None
                processed["is_horizontal"] = False
        else:
            # Check wellbore profile
            profile = str(processed.get("wellbore_profile", "")).upper()
            processed["is_horizontal"] = "HORIZONTAL" in profile or "HZ" in profile

        # Create linkage keys
        if processed.get("district") and processed.get("field_number"):
            processed["field_key"] = (
                f"{processed['district']}-{processed['field_number']}"
            )
        if processed.get("district") and processed.get("lease_number"):
            processed["lease_key"] = (
                f"{processed['district']}-{processed['lease_number']}"
            )

        return processed

    def filter_by_permit_type(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        permit_types: List[str],
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter permits by type.

        Args:
            data: Permit data
            permit_types: List of permit types to include

        Returns:
            Filtered data
        """
        normalized_types = [t.lower() for t in permit_types]

        if isinstance(data, pd.DataFrame):
            if "permit_type" not in data.columns:
                return data
            mask = data["permit_type"].str.lower().isin(normalized_types)
            return data[mask].copy()

        return [r for r in data if r.get("permit_type", "").lower() in normalized_types]

    def filter_by_status(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        statuses: List[str],
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter permits by status.

        Args:
            data: Permit data
            statuses: List of statuses to include

        Returns:
            Filtered data
        """
        normalized_statuses = [s.lower() for s in statuses]

        if isinstance(data, pd.DataFrame):
            if "permit_status" not in data.columns:
                return data
            mask = data["permit_status"].str.lower().isin(normalized_statuses)
            return data[mask].copy()

        return [
            r for r in data if r.get("permit_status", "").lower() in normalized_statuses
        ]

    def filter_by_date_range(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        start_date: str,
        end_date: str,
        date_field: str = "approved_date",
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter permits by date range.

        Args:
            data: Permit data
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            date_field: Which date field to filter on

        Returns:
            Filtered data
        """
        if isinstance(data, pd.DataFrame):
            if date_field not in data.columns:
                return data
            mask = (data[date_field] >= start_date) & (data[date_field] <= end_date)
            return data[mask].copy()

        return [
            r
            for r in data
            if r.get(date_field) and start_date <= r[date_field] <= end_date
        ]

    def filter_horizontal_wells(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        horizontal_only: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter to horizontal wells only or exclude them.

        Args:
            data: Permit data
            horizontal_only: If True, only horizontal; if False, exclude horizontal

        Returns:
            Filtered data
        """
        if isinstance(data, pd.DataFrame):
            if "is_horizontal" not in data.columns:
                return data
            if horizontal_only:
                return data[data["is_horizontal"]].copy()
            return data[~data["is_horizontal"]].copy()

        if horizontal_only:
            return [r for r in data if r.get("is_horizontal", False)]
        return [r for r in data if not r.get("is_horizontal", False)]

    def summarize_by_district(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Summarize permit data by district.

        Args:
            data: Permit data

        Returns:
            DataFrame with district summaries
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty or "district" not in df.columns:
            return pd.DataFrame()

        summary = (
            df.groupby("district")
            .agg(
                total_permits=("district", "size"),
                new_drill=("permit_type", lambda x: (x == "new_drill").sum()),
                recompletion=("permit_type", lambda x: (x == "recompletion").sum()),
                approved=("permit_status", lambda x: (x == "approved").sum()),
                pending=("permit_status", lambda x: (x == "pending").sum()),
                horizontal_wells=(
                    "is_horizontal",
                    lambda x: x.sum() if "is_horizontal" in df.columns else 0,
                ),
                avg_proposed_depth=(
                    "total_depth",
                    lambda x: x.mean() if "total_depth" in df.columns else None,
                ),
            )
            .reset_index()
        )

        return summary

    def summarize_by_operator(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Summarize permit data by operator.

        Args:
            data: Permit data

        Returns:
            DataFrame with operator summaries
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty or "operator_name" not in df.columns:
            return pd.DataFrame()

        summary = (
            df.groupby("operator_name")
            .agg(
                total_permits=("operator_name", "size"),
                new_drill=("permit_type", lambda x: (x == "new_drill").sum()),
                approved=("permit_status", lambda x: (x == "approved").sum()),
                horizontal_wells=(
                    "is_horizontal",
                    lambda x: x.sum() if "is_horizontal" in df.columns else 0,
                ),
                districts=("district", lambda x: list(x.dropna().unique())),
            )
            .reset_index()
        )

        summary["district_count"] = summary["districts"].apply(len)

        return summary

    def iter_processed(
        self,
        records: Iterator[Dict[str, Any]],
        validate: bool = True,
    ) -> Iterator[Dict[str, Any]]:
        """
        Process permit records with streaming.

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
                    is_valid, _ = self.validator.validate_permit_data(processed)
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


__all__ = ["PermitProcessor"]
