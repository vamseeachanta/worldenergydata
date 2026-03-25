# ABOUTME: Well data processor for Texas RRC wellbore records with DataFrame support
# ABOUTME: Handles API number normalization, coordinate conversion, status mapping, and sidetrack wells

"""
Well Data Processor for Texas RRC.

Processes and transforms wellbore data from Texas RRC
with support for API number validation, coordinate processing,
well status classification, and sidetrack/directional well handling.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import pandas as pd

from ..validators import TexasDataValidator

logger = logging.getLogger(__name__)


class WellProcessor:
    """
    Processor for Texas RRC well data.

    Features:
    - API number normalization to 14-digit format
    - Coordinate validation and WGS84 transformation
    - Well status classification
    - Well type categorization
    - Sidetrack and directional well handling
    - Completion data extraction
    - Pandas DataFrame support
    """

    # Well status mapping (RRC codes to descriptive names)
    STATUS_MAPPING = {
        "A": "active",
        "I": "inactive",
        "P": "plugged",
        "S": "shut_in",
        "T": "temporarily_abandoned",
        "TA": "temporarily_abandoned",
        "N": "new_drill",
        "C": "cancelled",
        "D": "drilling",
        "W": "waiting_on_completion",
        "PA": "plugged_and_abandoned",
        "SI": "shut_in",
        "AC": "active",
    }

    # Well type mapping (RRC codes to descriptive names)
    WELL_TYPE_MAPPING = {
        "O": "oil",
        "G": "gas",
        "GW": "gas_well",
        "OW": "oil_well",
        "OG": "oil_gas",
        "I": "injection",
        "D": "disposal",
        "SW": "salt_water_disposal",
        "W": "water_supply",
        "SWD": "salt_water_disposal",
        "WI": "water_injection",
        "GI": "gas_injection",
        "WS": "water_supply",
        "HZ": "horizontal",
        "VT": "vertical",
        "DI": "directional",
    }

    # Column name mappings for common RRC formats
    COLUMN_MAPPINGS = {
        "API_NO": "api_number",
        "API_NUMBER": "api_number",
        "API": "api_number",
        "WELL_NO": "well_number",
        "WELL_NUMBER": "well_number",
        "WELL_NAME": "well_name",
        "LEASE_NO": "lease_number",
        "LEASE_NAME": "lease_name",
        "OPERATOR_NO": "operator_number",
        "OPERATOR_NAME": "operator_name",
        "DISTRICT_NO": "district",
        "DISTRICT": "district",
        "FIELD_NO": "field_number",
        "FIELD_NAME": "field_name",
        "COUNTY_NO": "county_code",
        "COUNTY_NAME": "county_name",
        "WELL_STATUS": "well_status",
        "STATUS": "well_status",
        "WELL_TYPE": "well_type",
        "TYPE": "well_type",
        "TOTAL_DEPTH": "total_depth",
        "TD": "total_depth",
        "LATITUDE": "latitude",
        "LAT": "latitude",
        "LONGITUDE": "longitude",
        "LON": "longitude",
        "LONG": "longitude",
        "SPUD_DATE": "spud_date",
        "COMPLETION_DATE": "completion_date",
        "COMPL_DATE": "completion_date",
        "PLUG_DATE": "plug_date",
        "FIRST_PROD_DATE": "first_production_date",
        "WELLBORE_PROFILE": "wellbore_profile",
        "PROFILE": "wellbore_profile",
    }

    def __init__(self, validator: Optional[TexasDataValidator] = None):
        """
        Initialize well processor.

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
        Process well data from DataFrame or list of records.

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
        Process well data from a pandas DataFrame.

        Args:
            df: Input DataFrame with well data
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

        # Normalize API numbers to 14-digit format
        if "api_number" in result.columns:
            result["api_number_14"] = result["api_number"].apply(
                self._normalize_api_to_14_digit
            )
            result["api_number_formatted"] = result["api_number"].apply(
                lambda x: (
                    self.validator.normalize_api_number(str(x)) if pd.notna(x) else None
                )
            )

        # Extract sidetrack and completion info from API
        if "api_number_14" in result.columns:
            result["sidetrack_code"] = result["api_number_14"].apply(
                self._extract_sidetrack_code
            )
            result["completion_code"] = result["api_number_14"].apply(
                self._extract_completion_code
            )
            result["is_sidetrack"] = result["sidetrack_code"].apply(
                lambda x: x is not None and x != "00"
            )

        # Normalize district values
        if "district" in result.columns:
            result["district"] = result["district"].apply(
                lambda x: (
                    self.validator.normalize_district(str(x)) if pd.notna(x) else None
                )
            )

        # Process well status
        if "well_status" in result.columns:
            result["well_status_code"] = (
                result["well_status"].astype(str).str.upper().str.strip()
            )
            result["well_status"] = result["well_status_code"].apply(
                lambda x: self.STATUS_MAPPING.get(x, x.lower() if x else None)
            )

        # Process well type
        if "well_type" in result.columns:
            result["well_type_code"] = (
                result["well_type"].astype(str).str.upper().str.strip()
            )
            result["well_type"] = result["well_type_code"].apply(
                lambda x: self.WELL_TYPE_MAPPING.get(x, x.lower() if x else None)
            )

        # Detect directional/horizontal wells
        result["is_horizontal"] = self._detect_horizontal_wells(result)
        result["is_directional"] = self._detect_directional_wells(result)

        # Process coordinates
        result = self._process_coordinates(result)

        # Convert numeric fields
        numeric_fields = ["total_depth", "kelly_bushing_elevation", "ground_elevation"]
        for field in numeric_fields:
            if field in result.columns:
                result[field] = pd.to_numeric(result[field], errors="coerce")

        # Parse dates
        date_fields = [
            "spud_date",
            "completion_date",
            "plug_date",
            "first_production_date",
        ]
        for field in date_fields:
            if field in result.columns:
                result[field] = result[field].apply(self._parse_date)

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
            f"Processed {self._records_processed} well records, "
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

        Texas uses 10-digit API (42-XXX-XXXXX), extended to 14-digit:
        - Digits 1-2: State code (42 for Texas)
        - Digits 3-5: County code
        - Digits 6-10: Unique well identifier
        - Digits 11-12: Sidetrack code (00 for original wellbore)
        - Digits 13-14: Completion code (00 for first completion)

        Args:
            api: API number in various formats

        Returns:
            14-digit API number or None
        """
        if pd.isna(api) or api is None:
            return None

        # Clean the input
        api_str = str(api).strip().replace("-", "").replace(" ", "")

        # Remove any non-numeric characters
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

    def _extract_sidetrack_code(self, api_14: Optional[str]) -> Optional[str]:
        """
        Extract sidetrack code from 14-digit API.

        Args:
            api_14: 14-digit API number

        Returns:
            2-digit sidetrack code or None
        """
        if api_14 and len(api_14) >= 12:
            return api_14[10:12]
        return None

    def _extract_completion_code(self, api_14: Optional[str]) -> Optional[str]:
        """
        Extract completion code from 14-digit API.

        Args:
            api_14: 14-digit API number

        Returns:
            2-digit completion code or None
        """
        if api_14 and len(api_14) >= 14:
            return api_14[12:14]
        return None

    def _detect_horizontal_wells(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect horizontal wells from available indicators.

        Args:
            df: DataFrame with well data

        Returns:
            Boolean Series indicating horizontal wells
        """
        # Check wellbore_profile column
        if "wellbore_profile" in df.columns:
            profile_horizontal = (
                df["wellbore_profile"]
                .str.upper()
                .str.contains("HORIZONTAL|HZ", na=False)
            )
        else:
            profile_horizontal = pd.Series([False] * len(df), index=df.index)

        # Check well_type column
        if "well_type_code" in df.columns:
            type_horizontal = df["well_type_code"].isin(["HZ", "H"])
        else:
            type_horizontal = pd.Series([False] * len(df), index=df.index)

        return profile_horizontal | type_horizontal

    def _detect_directional_wells(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect directional wells from available indicators.

        Args:
            df: DataFrame with well data

        Returns:
            Boolean Series indicating directional wells
        """
        # Check wellbore_profile column
        if "wellbore_profile" in df.columns:
            profile_directional = (
                df["wellbore_profile"]
                .str.upper()
                .str.contains("DIRECTIONAL|DIR|DI", na=False)
            )
        else:
            profile_directional = pd.Series([False] * len(df), index=df.index)

        # Check well_type column
        if "well_type_code" in df.columns:
            type_directional = df["well_type_code"].isin(["DI", "DIR"])
        else:
            type_directional = pd.Series([False] * len(df), index=df.index)

        return profile_directional | type_directional

    def _process_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process and validate coordinates, converting to WGS84 if needed.

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
            result["coordinates_valid"] = result.apply(
                lambda row: self._validate_coordinates(
                    row.get("latitude"), row.get("longitude")
                ),
                axis=1,
            )

            # Flag coordinates that need correction (positive longitude)
            if "longitude" in result.columns:
                # Texas longitudes should be negative (west of prime meridian)
                needs_correction = (result["longitude"] > 0) & (
                    result["longitude"] < 107
                )
                result.loc[needs_correction, "longitude"] = -result.loc[
                    needs_correction, "longitude"
                ]

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

    def _validate_row(self, row: pd.Series) -> bool:
        """
        Validate a single row of well data.

        Args:
            row: DataFrame row

        Returns:
            True if valid
        """
        record = row.to_dict()
        is_valid, _ = self.validator.validate_well_data(record)
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

    def _process_records(
        self,
        records: List[Dict[str, Any]],
        validate: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Process well records from a list of dicts.

        Args:
            records: Raw well records
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
                    is_valid, errors = self.validator.validate_well_data(
                        processed_record
                    )
                    if not is_valid:
                        logger.debug(f"Invalid well record: {errors}")
                        self._records_invalid += 1
                        continue

                processed.append(processed_record)
                self._records_processed += 1

            except Exception as e:
                logger.warning(f"Error processing well record: {e}")
                self._records_invalid += 1

        logger.info(
            f"Processed {self._records_processed} well records, "
            f"{self._records_invalid} invalid"
        )
        return processed

    def _process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single well record.

        Args:
            record: Raw record

        Returns:
            Processed record
        """
        processed = record.copy()

        # Normalize API number
        if "api_number" in processed:
            api = str(processed["api_number"])
            processed["api_number_formatted"] = self.validator.normalize_api_number(api)
            processed["api_number_14"] = self._normalize_api_to_14_digit(api)

            if processed["api_number_14"]:
                processed["sidetrack_code"] = self._extract_sidetrack_code(
                    processed["api_number_14"]
                )
                processed["completion_code"] = self._extract_completion_code(
                    processed["api_number_14"]
                )
                processed["is_sidetrack"] = (
                    processed["sidetrack_code"] is not None
                    and processed["sidetrack_code"] != "00"
                )

        # Normalize district
        if "district" in processed:
            processed["district"] = self.validator.normalize_district(
                str(processed["district"])
            )

        # Process well status
        if "well_status" in processed:
            status_code = str(processed["well_status"]).upper().strip()
            processed["well_status_code"] = status_code
            processed["well_status"] = self.STATUS_MAPPING.get(
                status_code, status_code.lower()
            )

        # Process well type
        if "well_type" in processed:
            type_code = str(processed["well_type"]).upper().strip()
            processed["well_type_code"] = type_code
            processed["well_type"] = self.WELL_TYPE_MAPPING.get(
                type_code, type_code.lower()
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

        # Parse dates
        for date_field in ["completion_date", "plug_date", "spud_date"]:
            if date_field in processed:
                processed[date_field] = self._parse_date(processed[date_field])

        return processed

    def filter_by_status(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        statuses: List[str],
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter wells by status.

        Args:
            data: Well data
            statuses: List of status values to include

        Returns:
            Filtered data
        """
        normalized_statuses = [s.lower() for s in statuses]

        if isinstance(data, pd.DataFrame):
            if "well_status" not in data.columns:
                return data
            mask = data["well_status"].str.lower().isin(normalized_statuses)
            return data[mask].copy()

        return [
            r for r in data if r.get("well_status", "").lower() in normalized_statuses
        ]

    def filter_by_well_type(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        well_types: List[str],
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter wells by type.

        Args:
            data: Well data
            well_types: List of well types to include

        Returns:
            Filtered data
        """
        normalized_types = [t.lower() for t in well_types]

        if isinstance(data, pd.DataFrame):
            if "well_type" not in data.columns:
                return data
            mask = data["well_type"].str.lower().isin(normalized_types)
            return data[mask].copy()

        return [r for r in data if r.get("well_type", "").lower() in normalized_types]

    def filter_sidetracks(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        include_original: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Filter to sidetrack wells only or exclude them.

        Args:
            data: Well data
            include_original: If True, include original wellbores; if False, only sidetracks

        Returns:
            Filtered data
        """
        if isinstance(data, pd.DataFrame):
            if "is_sidetrack" not in data.columns:
                return data
            if include_original:
                return data[~data["is_sidetrack"]].copy()
            else:
                return data[data["is_sidetrack"]].copy()

        if include_original:
            return [r for r in data if not r.get("is_sidetrack", False)]
        return [r for r in data if r.get("is_sidetrack", False)]

    def summarize_by_district(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Summarize well data by district.

        Args:
            data: Well data

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
                total_wells=("district", "size"),
                active_wells=("well_status", lambda x: (x == "active").sum()),
                plugged_wells=("well_status", lambda x: (x == "plugged").sum()),
                horizontal_wells=(
                    "is_horizontal",
                    lambda x: x.sum() if "is_horizontal" in df.columns else 0,
                ),
                sidetrack_wells=(
                    "is_sidetrack",
                    lambda x: x.sum() if "is_sidetrack" in df.columns else 0,
                ),
                avg_depth=(
                    "total_depth",
                    lambda x: x.mean() if "total_depth" in df.columns else None,
                ),
            )
            .reset_index()
        )

        return summary

    def iter_processed(
        self,
        records: Iterator[Dict[str, Any]],
        validate: bool = True,
    ) -> Iterator[Dict[str, Any]]:
        """
        Process well records with streaming.

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
                    is_valid, _ = self.validator.validate_well_data(processed)
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


__all__ = ["WellProcessor"]
