# ABOUTME: Data validation utilities for Texas RRC data processing
# ABOUTME: Validates API numbers, districts, coordinates, and data integrity

"""
Data validation utilities for Texas RRC data processing.

Provides validation for:
- Texas API numbers (42-XXX-XXXXX format)
- RRC district codes (01-10, 7B, 7C, 8A)
- Geographic coordinates within Texas bounds
- Required fields and data types
- Date ranges and numeric values
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TexasDataValidator:
    """Validate Texas RRC data for quality and consistency."""

    # Texas geographic bounds (approximate)
    TEXAS_LAT_MIN = 25.84
    TEXAS_LAT_MAX = 36.50
    TEXAS_LON_MIN = -106.65
    TEXAS_LON_MAX = -93.51

    # Valid Texas RRC districts
    VALID_DISTRICTS = [
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "7B",
        "7C",
        "08",
        "8A",
        "09",
        "10",
    ]

    # Texas state FIPS code
    TEXAS_STATE_FIPS = "42"

    # Valid county FIPS codes (3-digit, 001-507 range for Texas)
    COUNTY_CODE_MIN = 1
    COUNTY_CODE_MAX = 507

    def __init__(self):
        """Initialize the TexasDataValidator."""
        self.validation_count = 0
        self.error_count = 0

    def validate_api_number(self, api_number: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Texas API number format.

        Texas API numbers follow the format: 42-XXX-XXXXX
        - 42: Texas state FIPS code
        - XXX: 3-digit county code (001-507)
        - XXXXX: 5-digit unique well identifier

        Args:
            api_number: API number to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not api_number:
            return False, "API number is empty"

        # Normalize by removing spaces and converting to uppercase
        normalized = api_number.strip().upper()

        # Pattern for Texas API number: 42-XXX-XXXXX or 42XXXXXXXXX
        # With or without dashes
        pattern_with_dashes = r"^42-(\d{3})-(\d{5})$"
        pattern_without_dashes = r"^42(\d{3})(\d{5})$"

        match = re.match(pattern_with_dashes, normalized)
        if not match:
            match = re.match(pattern_without_dashes, normalized)

        if not match:
            return False, f"Invalid format. Expected 42-XXX-XXXXX, got '{api_number}'"

        county_code = int(match.group(1))
        if county_code < self.COUNTY_CODE_MIN or county_code > self.COUNTY_CODE_MAX:
            return (
                False,
                f"Invalid county code: {county_code}. Must be between {self.COUNTY_CODE_MIN} and {self.COUNTY_CODE_MAX}",
            )

        return True, None

    def validate_district(self, district: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Texas RRC district code.

        Valid districts: 01, 02, 03, 04, 05, 06, 7B, 7C, 08, 8A, 09, 10

        Args:
            district: District code to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not district:
            return False, "District is empty"

        # Normalize: uppercase and pad single digits
        normalized = district.strip().upper()
        if normalized.isdigit() and len(normalized) == 1:
            normalized = normalized.zfill(2)

        if normalized not in self.VALID_DISTRICTS:
            return (
                False,
                f"Invalid district: '{district}'. Valid districts: {', '.join(self.VALID_DISTRICTS)}",
            )

        return True, None

    def validate_texas_coordinates(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if coordinates are within Texas bounds.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if latitude is None or longitude is None:
            return False, "Latitude or longitude is missing"

        try:
            lat = float(latitude)
            lon = float(longitude)

            if lat < self.TEXAS_LAT_MIN or lat > self.TEXAS_LAT_MAX:
                return (
                    False,
                    f"Latitude {lat} is outside Texas bounds ({self.TEXAS_LAT_MIN} to {self.TEXAS_LAT_MAX})",
                )

            if lon < self.TEXAS_LON_MIN or lon > self.TEXAS_LON_MAX:
                return (
                    False,
                    f"Longitude {lon} is outside Texas bounds ({self.TEXAS_LON_MIN} to {self.TEXAS_LON_MAX})",
                )

            return True, None

        except (ValueError, TypeError) as e:
            return False, f"Invalid coordinate format: {e}"

    def validate_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate data against a schema definition.

        Args:
            data: Data to validate
            schema: Schema definition with 'required' and 'optional' fields

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in data or data[field] is None or data[field] == "":
                    errors.append(f"Missing required field: {field}")

        # Check for unexpected fields (optional)
        if schema.get("strict", False):
            allowed_fields = set(schema.get("required", [])) | set(
                schema.get("optional", [])
            )
            for field in data:
                if field not in allowed_fields:
                    errors.append(f"Unexpected field: {field}")

        self.validation_count += 1
        if errors:
            self.error_count += 1

        return len(errors) == 0, errors

    def validate_types(
        self,
        data: Dict[str, Any],
        type_schema: Dict[str, type],
    ) -> Tuple[bool, List[str]]:
        """
        Validate data types for fields.

        Args:
            data: Data to validate
            type_schema: Dictionary mapping field names to expected types

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        for field, expected_type in type_schema.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    try:
                        # Try to convert
                        expected_type(data[field])
                    except (ValueError, TypeError):
                        errors.append(
                            f"Type validation failed for {field}: "
                            f"expected {expected_type.__name__}, got {type(data[field]).__name__}"
                        )
        return len(errors) == 0, errors

    def validate_date_range(
        self,
        date_str: Optional[str],
        min_year: int = 1900,
        max_year: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if date is within reasonable range.

        Args:
            date_str: Date string (supports ISO format or MM/DD/YYYY)
            min_year: Minimum valid year
            max_year: Maximum valid year (current year + 10 if None)

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not date_str:
            return False, "Date is empty"

        try:
            # Try parsing different formats
            dt = None
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%m-%d-%Y"]:
                try:
                    dt = datetime.strptime(date_str.split("T")[0], fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                return False, f"Unable to parse date: {date_str}"

            year = dt.year
            if max_year is None:
                max_year = datetime.now().year + 10

            if year < min_year or year > max_year:
                return (
                    False,
                    f"Year {year} is outside valid range ({min_year}-{max_year})",
                )

            return True, None

        except Exception as e:
            return False, f"Date validation error: {e}"

    def validate_numeric_range(
        self,
        value: Any,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        allow_zero: bool = True,
        allow_negative: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if numeric value is within specified range.

        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            allow_zero: Whether zero is allowed
            allow_negative: Whether negative values are allowed

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if value is None:
            return True, None  # None is considered valid (optional field)

        try:
            num_val = float(value)

            if not allow_negative and num_val < 0:
                return False, f"Negative values not allowed: {num_val}"

            if not allow_zero and num_val == 0:
                return False, "Zero value not allowed"

            if min_val is not None and num_val < min_val:
                return False, f"Value {num_val} is below minimum {min_val}"

            if max_val is not None and num_val > max_val:
                return False, f"Value {num_val} is above maximum {max_val}"

            return True, None

        except (ValueError, TypeError):
            return False, f"Invalid numeric value: {value}"

    def validate_lease_number(self, lease_number: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Texas RRC lease number format.

        Args:
            lease_number: Lease number to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not lease_number:
            return False, "Lease number is empty"

        # Lease numbers are typically 6-8 digit numbers
        normalized = lease_number.strip()
        if not normalized.isdigit():
            return False, f"Lease number must be numeric: {lease_number}"

        if len(normalized) < 1 or len(normalized) > 10:
            return False, f"Lease number length out of range: {lease_number}"

        return True, None

    def validate_operator_number(
        self, operator_number: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate Texas RRC operator number format.

        Args:
            operator_number: Operator number to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not operator_number:
            return False, "Operator number is empty"

        # Operator numbers are typically 6-digit numbers
        normalized = operator_number.strip()
        if not normalized.isdigit():
            return False, f"Operator number must be numeric: {operator_number}"

        if len(normalized) < 1 or len(normalized) > 8:
            return False, f"Operator number length out of range: {operator_number}"

        return True, None

    def validate_well_data(self, well_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for well data.

        Args:
            well_data: Well data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate API number if present
        api_number = well_data.get("api_number")
        if api_number:
            is_valid, error = self.validate_api_number(api_number)
            if not is_valid:
                errors.append(f"API number: {error}")

        # Validate district if present
        district = well_data.get("district")
        if district:
            is_valid, error = self.validate_district(district)
            if not is_valid:
                errors.append(f"District: {error}")

        # Validate coordinates if present
        lat = well_data.get("latitude")
        lon = well_data.get("longitude")
        if lat is not None and lon is not None:
            is_valid, error = self.validate_texas_coordinates(lat, lon)
            if not is_valid:
                errors.append(f"Coordinates: {error}")

        # Validate depth
        total_depth = well_data.get("total_depth")
        if total_depth is not None:
            is_valid, error = self.validate_numeric_range(
                total_depth, min_val=0, max_val=40000  # Max ~40,000 ft
            )
            if not is_valid:
                errors.append(f"Total depth: {error}")

        # Validate dates
        completion_date = well_data.get("completion_date")
        if completion_date:
            is_valid, error = self.validate_date_range(completion_date)
            if not is_valid:
                errors.append(f"Completion date: {error}")

        return len(errors) == 0, errors

    def validate_production_data(
        self, production_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for production data.

        Args:
            production_data: Production data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate district if present
        district = production_data.get("district")
        if district:
            is_valid, error = self.validate_district(district)
            if not is_valid:
                errors.append(f"District: {error}")

        # Validate production values (must be non-negative)
        for field in [
            "oil_production",
            "gas_production",
            "water_production",
            "condensate",
        ]:
            value = production_data.get(field)
            if value is not None:
                is_valid, error = self.validate_numeric_range(value, min_val=0)
                if not is_valid:
                    errors.append(f"{field}: {error}")

        # Validate production date
        prod_date = production_data.get("production_date")
        if prod_date:
            is_valid, error = self.validate_date_range(prod_date, min_year=1900)
            if not is_valid:
                errors.append(f"Production date: {error}")

        return len(errors) == 0, errors

    def validate_permit_data(
        self, permit_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for drilling permit data.

        Args:
            permit_data: Permit data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate API number if present
        api_number = permit_data.get("api_number")
        if api_number:
            is_valid, error = self.validate_api_number(api_number)
            if not is_valid:
                errors.append(f"API number: {error}")

        # Validate district
        district = permit_data.get("district")
        if district:
            is_valid, error = self.validate_district(district)
            if not is_valid:
                errors.append(f"District: {error}")

        # Validate coordinates
        lat = permit_data.get("latitude")
        lon = permit_data.get("longitude")
        if lat is not None and lon is not None:
            is_valid, error = self.validate_texas_coordinates(lat, lon)
            if not is_valid:
                errors.append(f"Coordinates: {error}")

        # Validate approved date
        approved_date = permit_data.get("approved_date")
        if approved_date:
            is_valid, error = self.validate_date_range(approved_date, min_year=1900)
            if not is_valid:
                errors.append(f"Approved date: {error}")

        # Validate proposed depth
        total_depth = permit_data.get("total_depth")
        if total_depth is not None:
            is_valid, error = self.validate_numeric_range(
                total_depth, min_val=0, max_val=40000
            )
            if not is_valid:
                errors.append(f"Total depth: {error}")

        return len(errors) == 0, errors

    def normalize_api_number(self, api_number: str) -> Optional[str]:
        """
        Normalize API number to standard format (42-XXX-XXXXX).

        Args:
            api_number: API number in any valid format

        Returns:
            Normalized API number or None if invalid
        """
        if not api_number:
            return None

        # Remove any non-digit characters except dashes
        cleaned = re.sub(r"[^\d-]", "", api_number.strip())

        # Remove dashes and re-format
        digits = re.sub(r"-", "", cleaned)

        if len(digits) != 10:
            return None

        # Verify Texas state code
        if not digits.startswith(self.TEXAS_STATE_FIPS):
            return None

        return f"{digits[:2]}-{digits[2:5]}-{digits[5:10]}"

    def normalize_district(self, district: str) -> Optional[str]:
        """
        Normalize district code to standard format.

        Args:
            district: District code in any valid format

        Returns:
            Normalized district code or None if invalid
        """
        if not district:
            return None

        normalized = district.strip().upper()

        # Handle single digit districts
        if normalized.isdigit() and len(normalized) == 1:
            normalized = normalized.zfill(2)

        if normalized not in self.VALID_DISTRICTS:
            return None

        return normalized

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics.

        Returns:
            Dictionary with validation counts
        """
        return {
            "validations": self.validation_count,
            "errors": self.error_count,
            "success_rate": (
                (self.validation_count - self.error_count)
                / max(self.validation_count, 1)
            ),
        }


# Convenience functions for common validations
def is_valid_texas_api_number(api_number: str) -> bool:
    """Check if API number is valid Texas format."""
    validator = TexasDataValidator()
    is_valid, _ = validator.validate_api_number(api_number)
    return is_valid


def is_valid_texas_district(district: str) -> bool:
    """Check if district code is valid."""
    validator = TexasDataValidator()
    is_valid, _ = validator.validate_district(district)
    return is_valid


def is_valid_texas_coordinates(latitude: float, longitude: float) -> bool:
    """Check if coordinates are within Texas bounds."""
    validator = TexasDataValidator()
    is_valid, _ = validator.validate_texas_coordinates(latitude, longitude)
    return is_valid
