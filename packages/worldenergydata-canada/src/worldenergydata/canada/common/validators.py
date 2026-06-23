# ABOUTME: Data validators for Canadian energy data including UWI, coordinates, and province codes.
# ABOUTME: Provides validation for NAD83 coordinates and Canada-specific well identifiers.

"""
Canadian Energy Data Validators.

Provides validation for:
- UWI (Unique Well Identifier) format and components
- NAD83 coordinate validation (Canadian standard datum)
- Province code validation (AB, BC, SK, MB, YT, NT, NU)
- Well status codes
- License and permit numbers
- Date format validation

Coordinate bounds are based on the Canadian landmass and offshore areas
where energy exploration occurs.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from worldenergydata.canada.common.uwi_parser import (
    UWIComponents,
    UWIParser,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error."""

    field: str
    message: str
    value: Any = None
    code: str = ""
    severity: str = "error"  # error, warning, info

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "message": self.message,
            "value": str(self.value) if self.value is not None else None,
            "code": self.code,
            "severity": self.severity,
        }


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(
        self,
        field: str,
        message: str,
        value: Any = None,
        code: str = "",
    ) -> None:
        """Add a validation error."""
        self.errors.append(
            ValidationError(
                field=field,
                message=message,
                value=value,
                code=code,
                severity="error",
            )
        )
        self.is_valid = False

    def add_warning(
        self,
        field: str,
        message: str,
        value: Any = None,
        code: str = "",
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(
            ValidationError(
                field=field,
                message=message,
                value=value,
                code=code,
                severity="warning",
            )
        )

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if other.errors:
            self.is_valid = False
        self.metadata.update(other.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "metadata": self.metadata,
        }


class CanadaDataValidator:
    """
    Validator for Canadian energy data.

    Validates:
    - UWI (Unique Well Identifier) format
    - NAD83 coordinates (latitude/longitude)
    - Province codes
    - Well status codes
    - License numbers
    - Dates and date ranges

    Example:
        validator = CanadaDataValidator()

        # Validate a UWI
        result = validator.validate_uwi("100.16-09-010-09W4.00")
        logger.info(f"Valid: {result.is_valid}")

        # Validate coordinates
        result = validator.validate_coordinates(53.5461, -113.4938)
        logger.info(f"Within Canada: {result.is_valid}")

        # Validate a complete well record
        record = {
            "uwi": "100.16-09-010-09W4.00",
            "latitude": 53.5461,
            "longitude": -113.4938,
            "province": "AB",
        }
        result = validator.validate_well_record(record)
    """

    # Canadian province and territory codes
    VALID_PROVINCE_CODES = {
        "AB": "Alberta",
        "BC": "British Columbia",
        "SK": "Saskatchewan",
        "MB": "Manitoba",
        "ON": "Ontario",
        "QC": "Quebec",
        "NB": "New Brunswick",
        "NS": "Nova Scotia",
        "PE": "Prince Edward Island",
        "NL": "Newfoundland and Labrador",
        "YT": "Yukon",
        "NT": "Northwest Territories",
        "NU": "Nunavut",
    }

    # Oil and gas producing provinces
    OIL_GAS_PROVINCES = {"AB", "BC", "SK", "MB", "NT", "YT", "NL"}

    # NAD83 coordinate bounds for Canadian provinces with oil/gas activity
    # These are approximate bounding boxes for validation
    PROVINCE_BOUNDS = {
        "AB": {
            "lat_min": 49.0,
            "lat_max": 60.0,
            "lon_min": -120.0,
            "lon_max": -110.0,
        },
        "BC": {
            "lat_min": 48.3,
            "lat_max": 60.0,
            "lon_min": -139.0,
            "lon_max": -114.0,
        },
        "SK": {
            "lat_min": 49.0,
            "lat_max": 60.0,
            "lon_min": -110.0,
            "lon_max": -102.0,
        },
        "MB": {
            "lat_min": 49.0,
            "lat_max": 60.0,
            "lon_min": -102.0,
            "lon_max": -89.0,
        },
        "NT": {
            "lat_min": 60.0,
            "lat_max": 78.0,
            "lon_min": -137.0,
            "lon_max": -102.0,
        },
        "YT": {
            "lat_min": 60.0,
            "lat_max": 69.6,
            "lon_min": -141.0,
            "lon_max": -124.0,
        },
        "NL": {
            "lat_min": 46.6,
            "lat_max": 60.4,
            "lon_min": -67.8,
            "lon_max": -52.6,
        },
    }

    # Overall Canada bounds (including offshore)
    CANADA_BOUNDS = {
        "lat_min": 41.7,  # Southern Ontario
        "lat_max": 83.1,  # Northern tip
        "lon_min": -141.0,  # Yukon-Alaska border
        "lon_max": -52.6,  # Eastern Newfoundland
    }

    # Well status codes (AER-compatible)
    VALID_WELL_STATUSES = {
        "ACTIVE": "Well is currently producing or capable of producing",
        "SUSPENDED": "Well operations temporarily suspended",
        "ABANDONED": "Well has been permanently abandoned",
        "COMPLETED": "Well has been completed",
        "DRILLING": "Well is currently being drilled",
        "LICENSED": "Well has been licensed but not yet drilled",
        "CANCELLED": "Well license has been cancelled",
        "RE-ENTERED": "Well has been re-entered for additional work",
    }

    # Fluid types
    VALID_FLUID_TYPES = {
        "OIL": "Crude oil",
        "GAS": "Natural gas",
        "BITUMEN": "Oil sands bitumen",
        "WATER": "Produced water",
        "CBM": "Coalbed methane",
        "SOLVENT": "Solvent (in-situ operations)",
        "STEAM": "Steam (in-situ operations)",
        "CONDENSATE": "Gas condensate",
    }

    def __init__(self, strict: bool = False):
        """
        Initialize the validator.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
        self.uwi_parser = UWIParser(strict=False)

    def validate_uwi(self, uwi: str) -> ValidationResult:
        """
        Validate a Canadian UWI (Unique Well Identifier).

        Args:
            uwi: The UWI string to validate

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata["uwi"] = uwi

        if not uwi:
            result.add_error("uwi", "UWI cannot be empty", uwi, "UWI_EMPTY")
            return result

        if not isinstance(uwi, str):
            result.add_error("uwi", "UWI must be a string", uwi, "UWI_TYPE")
            return result

        # Use the UWI parser to validate
        is_valid, error_msg = self.uwi_parser.validate(uwi)

        if not is_valid:
            result.add_error(
                "uwi", error_msg or "Invalid UWI format", uwi, "UWI_FORMAT"
            )
        else:
            # Parse to get additional info
            components = self.uwi_parser.parse(uwi)
            result.metadata["survey_system"] = components.survey_system.value
            result.metadata["province"] = components.province
            result.metadata["normalized_uwi"] = components.normalized_uwi

            # Additional semantic validation
            self._validate_uwi_semantics(components, result)

        return result

    def _validate_uwi_semantics(
        self, components: UWIComponents, result: ValidationResult
    ) -> None:
        """Perform semantic validation on UWI components."""
        # Check for unusual location exceptions
        loc_ex = (
            int(components.location_exception) if components.location_exception else 0
        )
        if loc_ex > 199:
            result.add_warning(
                "uwi",
                f"Unusual location exception: {loc_ex}",
                components.raw_uwi,
                "UWI_LOCATION_EXCEPTION",
            )

        # Check event sequence
        event_seq = int(components.event_sequence) if components.event_sequence else 0
        if event_seq > 10:
            result.add_warning(
                "uwi",
                f"High event sequence number: {event_seq}",
                components.raw_uwi,
                "UWI_EVENT_SEQUENCE",
            )

    def validate_coordinates(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        province: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate NAD83 coordinates.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            province: Optional province code for more specific validation

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata["latitude"] = latitude
        result.metadata["longitude"] = longitude
        result.metadata["province"] = province

        # Check for null values
        if latitude is None:
            result.add_error(
                "latitude",
                "Latitude cannot be null",
                latitude,
                "COORD_NULL",
            )
        if longitude is None:
            result.add_error(
                "longitude",
                "Longitude cannot be null",
                longitude,
                "COORD_NULL",
            )

        if not result.is_valid:
            return result

        # Validate latitude type
        if not isinstance(latitude, (int, float)):
            result.add_error(
                "latitude",
                f"Latitude must be numeric, got {type(latitude).__name__}",
                latitude,
                "COORD_TYPE",
            )
            return result

        # Validate longitude type
        if not isinstance(longitude, (int, float)):
            result.add_error(
                "longitude",
                f"Longitude must be numeric, got {type(longitude).__name__}",
                longitude,
                "COORD_TYPE",
            )
            return result

        # Validate general range
        if not (-90 <= latitude <= 90):
            result.add_error(
                "latitude",
                f"Latitude must be between -90 and 90, got {latitude}",
                latitude,
                "COORD_RANGE",
            )

        if not (-180 <= longitude <= 180):
            result.add_error(
                "longitude",
                f"Longitude must be between -180 and 180, got {longitude}",
                longitude,
                "COORD_RANGE",
            )

        if not result.is_valid:
            return result

        # Validate within Canada bounds
        if not self._is_within_canada(latitude, longitude):
            result.add_error(
                "coordinates",
                f"Coordinates ({latitude}, {longitude}) are outside Canada bounds",
                (latitude, longitude),
                "COORD_OUTSIDE_CANADA",
            )
            return result

        # If province specified, validate within province bounds
        if province and province.upper() in self.PROVINCE_BOUNDS:
            if not self._is_within_province(latitude, longitude, province.upper()):
                result.add_warning(
                    "coordinates",
                    f"Coordinates ({latitude}, {longitude}) may be outside {province} bounds",
                    (latitude, longitude),
                    "COORD_OUTSIDE_PROVINCE",
                )

        return result

    def _is_within_canada(self, latitude: float, longitude: float) -> bool:
        """Check if coordinates are within Canadian bounds."""
        return (
            self.CANADA_BOUNDS["lat_min"] <= latitude <= self.CANADA_BOUNDS["lat_max"]
            and self.CANADA_BOUNDS["lon_min"]
            <= longitude
            <= self.CANADA_BOUNDS["lon_max"]
        )

    def _is_within_province(
        self, latitude: float, longitude: float, province: str
    ) -> bool:
        """Check if coordinates are within province bounds."""
        bounds = self.PROVINCE_BOUNDS.get(province)
        if not bounds:
            return True  # No bounds defined, assume valid

        return (
            bounds["lat_min"] <= latitude <= bounds["lat_max"]
            and bounds["lon_min"] <= longitude <= bounds["lon_max"]
        )

    def validate_province_code(self, province: str) -> ValidationResult:
        """
        Validate a Canadian province or territory code.

        Args:
            province: Two-letter province code

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata["province"] = province

        if not province:
            result.add_error(
                "province",
                "Province code cannot be empty",
                province,
                "PROVINCE_EMPTY",
            )
            return result

        if not isinstance(province, str):
            result.add_error(
                "province",
                f"Province code must be a string, got {type(province).__name__}",
                province,
                "PROVINCE_TYPE",
            )
            return result

        province_upper = province.upper().strip()

        if len(province_upper) != 2:
            result.add_error(
                "province",
                f"Province code must be 2 characters, got '{province}'",
                province,
                "PROVINCE_LENGTH",
            )
            return result

        if province_upper not in self.VALID_PROVINCE_CODES:
            result.add_error(
                "province",
                f"Invalid province code: '{province}'. Valid codes: {', '.join(sorted(self.VALID_PROVINCE_CODES.keys()))}",  # noqa: E501
                province,
                "PROVINCE_INVALID",
            )
            return result

        # Check if province has oil/gas activity
        if province_upper not in self.OIL_GAS_PROVINCES:
            result.add_warning(
                "province",
                f"Province {province_upper} ({self.VALID_PROVINCE_CODES[province_upper]}) has limited oil/gas activity",  # noqa: E501
                province,
                "PROVINCE_NO_OG",
            )

        result.metadata["province_name"] = self.VALID_PROVINCE_CODES[province_upper]
        return result

    def validate_well_status(self, status: str) -> ValidationResult:
        """
        Validate a well status code.

        Args:
            status: Well status code

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata["status"] = status

        if not status:
            result.add_error(
                "status",
                "Well status cannot be empty",
                status,
                "STATUS_EMPTY",
            )
            return result

        status_upper = status.upper().strip()

        if status_upper not in self.VALID_WELL_STATUSES:
            result.add_error(
                "status",
                f"Invalid well status: '{status}'. Valid statuses: {', '.join(sorted(self.VALID_WELL_STATUSES.keys()))}",  # noqa: E501
                status,
                "STATUS_INVALID",
            )
            return result

        result.metadata["status_description"] = self.VALID_WELL_STATUSES[status_upper]
        return result

    def validate_fluid_type(self, fluid_type: str) -> ValidationResult:
        """
        Validate a fluid type code.

        Args:
            fluid_type: Fluid type code

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata["fluid_type"] = fluid_type

        if not fluid_type:
            result.add_error(
                "fluid_type",
                "Fluid type cannot be empty",
                fluid_type,
                "FLUID_EMPTY",
            )
            return result

        fluid_upper = fluid_type.upper().strip()

        if fluid_upper not in self.VALID_FLUID_TYPES:
            result.add_error(
                "fluid_type",
                f"Invalid fluid type: '{fluid_type}'. Valid types: {', '.join(sorted(self.VALID_FLUID_TYPES.keys()))}",  # noqa: E501
                fluid_type,
                "FLUID_INVALID",
            )
            return result

        result.metadata["fluid_description"] = self.VALID_FLUID_TYPES[fluid_upper]
        return result

    def validate_date(
        self,
        date_value: Union[str, datetime, date],
        field_name: str = "date",
        allow_future: bool = False,
        min_year: int = 1900,
    ) -> ValidationResult:
        """
        Validate a date value.

        Args:
            date_value: Date to validate
            field_name: Name of the field for error messages
            allow_future: Whether to allow future dates
            min_year: Minimum allowed year

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata[field_name] = str(date_value)

        if date_value is None:
            result.add_error(
                field_name,
                f"{field_name} cannot be null",
                date_value,
                "DATE_NULL",
            )
            return result

        # Convert to datetime if string
        parsed_date = None
        if isinstance(date_value, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%Y%m%d",
                "%B %d, %Y",
            ]
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    break
                except ValueError:
                    continue

            if parsed_date is None:
                result.add_error(
                    field_name,
                    f"Unable to parse date: '{date_value}'",
                    date_value,
                    "DATE_FORMAT",
                )
                return result
        elif isinstance(date_value, datetime):
            parsed_date = date_value
        elif isinstance(date_value, date):
            parsed_date = datetime.combine(date_value, datetime.min.time())
        else:
            result.add_error(
                field_name,
                f"Invalid date type: {type(date_value).__name__}",
                date_value,
                "DATE_TYPE",
            )
            return result

        # Validate year range
        if parsed_date.year < min_year:
            result.add_error(
                field_name,
                f"Date year must be >= {min_year}, got {parsed_date.year}",
                date_value,
                "DATE_TOO_OLD",
            )

        # Validate future date
        if not allow_future and parsed_date > datetime.now():
            result.add_error(
                field_name,
                f"Future date not allowed: {parsed_date.date()}",
                date_value,
                "DATE_FUTURE",
            )

        result.metadata["parsed_date"] = parsed_date.isoformat()
        return result

    def validate_license_number(
        self, license_number: str, province: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate a well license number.

        Args:
            license_number: License number to validate
            province: Optional province for province-specific validation

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata["license_number"] = license_number

        if not license_number:
            result.add_error(
                "license_number",
                "License number cannot be empty",
                license_number,
                "LICENSE_EMPTY",
            )
            return result

        if not isinstance(license_number, str):
            license_number = str(license_number)

        # Alberta license format: Typically numeric or alphanumeric
        # e.g., "0123456" or "W0123456"
        if province and province.upper() == "AB":
            # AER license pattern
            if not re.match(r"^[WA]?\d{6,8}$", license_number):
                result.add_warning(
                    "license_number",
                    f"License number '{license_number}' may not match AER format",
                    license_number,
                    "LICENSE_FORMAT_AB",
                )

        # BC license format
        elif province and province.upper() == "BC":
            if not re.match(r"^\d{4,6}$", license_number):
                result.add_warning(
                    "license_number",
                    f"License number '{license_number}' may not match BCER format",
                    license_number,
                    "LICENSE_FORMAT_BC",
                )

        return result

    def validate_well_record(self, record: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete well record.

        Args:
            record: Dictionary containing well data

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        result.metadata["record_fields"] = list(record.keys())

        # Validate UWI
        if "uwi" in record:
            uwi_result = self.validate_uwi(record["uwi"])
            result.merge(uwi_result)

        # Validate coordinates
        lat = record.get("latitude") or record.get("lat")
        lon = record.get("longitude") or record.get("lon") or record.get("long")
        province = record.get("province") or record.get("prov")

        if lat is not None and lon is not None:
            coord_result = self.validate_coordinates(lat, lon, province)
            result.merge(coord_result)

        # Validate province
        if province:
            province_result = self.validate_province_code(province)
            result.merge(province_result)

        # Validate status
        status = record.get("status") or record.get("well_status")
        if status:
            status_result = self.validate_well_status(status)
            result.merge(status_result)

        # Validate fluid type
        fluid = record.get("fluid_type") or record.get("fluid")
        if fluid:
            fluid_result = self.validate_fluid_type(fluid)
            result.merge(fluid_result)

        # Validate dates
        for date_field in [
            "spud_date",
            "completion_date",
            "license_date",
            "abandonment_date",
        ]:
            if date_field in record and record[date_field]:
                allow_future = date_field == "completion_date"
                date_result = self.validate_date(
                    record[date_field],
                    date_field,
                    allow_future=allow_future,
                )
                result.merge(date_result)

        # Validate license number
        license_num = record.get("license_number") or record.get("license")
        if license_num:
            license_result = self.validate_license_number(license_num, province)
            result.merge(license_result)

        return result

    def validate_batch(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[ValidationResult]]:
        """
        Validate a batch of well records.

        Args:
            records: List of well record dictionaries

        Returns:
            Tuple of (valid_count, invalid_count, results)
        """
        results = []
        valid_count = 0
        invalid_count = 0

        for record in records:
            result = self.validate_well_record(record)
            results.append(result)
            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        return valid_count, invalid_count, results
