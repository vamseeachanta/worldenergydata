"""
Data Validators for Marine Safety Module

Provides Pydantic models and validation functions for data integrity.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from worldenergydata.modules.marine_safety import constants
from worldenergydata.modules.marine_safety.exceptions import (
    InvalidDataError,
    MissingRequiredFieldError
)


class IncidentValidator(BaseModel):
    """Validator for incident data"""

    # Required fields
    source_agency: constants.DataSource = Field(..., description="Source agency")
    source_incident_id: str = Field(..., min_length=1, max_length=100)
    incident_date: date = Field(..., description="Date of incident")
    incident_type: constants.IncidentType = Field(..., description="Type of incident")

    # Optional core fields
    incident_time: Optional[datetime] = None
    severity_level: int = Field(
        default=constants.DEFAULT_SEVERITY,
        ge=1,
        le=5,
        description="Severity level 1-5"
    )
    status: constants.IncidentStatus = Field(
        default=constants.DEFAULT_STATUS,
        description="Investigation status"
    )
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=10000)

    # Vessel and company
    vessel_name: Optional[str] = Field(None, max_length=255)
    vessel_type: Optional[constants.VesselType] = None
    imo_number: Optional[str] = Field(None, pattern=r"^\d{7}$")
    company_name: Optional[str] = Field(None, max_length=255)

    # Location
    latitude: Optional[Decimal] = Field(
        None,
        ge=constants.MIN_LATITUDE,
        le=constants.MAX_LATITUDE
    )
    longitude: Optional[Decimal] = Field(
        None,
        ge=constants.MIN_LONGITUDE,
        le=constants.MAX_LONGITUDE
    )
    location_name: Optional[str] = Field(None, max_length=500)

    # Impact
    fatalities: int = Field(default=0, ge=0)
    injuries: int = Field(default=0, ge=0)
    missing_persons: int = Field(default=0, ge=0)
    environmental_impact: Optional[str] = None
    estimated_damage_usd: Optional[Decimal] = Field(None, ge=0)

    # Weather
    weather_condition: Optional[constants.WeatherCondition] = None
    wind_speed_knots: Optional[Decimal] = Field(None, ge=0)
    wave_height_meters: Optional[Decimal] = Field(None, ge=0)
    sea_state: Optional[int] = Field(None, ge=0, le=9)

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("incident_date")
    @classmethod
    def validate_incident_date(cls, v: date) -> date:
        """Ensure incident date is not in the future"""
        if v > date.today():
            raise InvalidDataError(
                field="incident_date",
                value=v,
                reason="Incident date cannot be in the future"
            )
        return v

    @model_validator(mode="after")
    def validate_coordinates(self) -> "IncidentValidator":
        """Ensure both latitude and longitude are provided together"""
        has_lat = self.latitude is not None
        has_lon = self.longitude is not None

        if has_lat != has_lon:
            raise InvalidDataError(
                field="coordinates",
                value=f"lat={self.latitude}, lon={self.longitude}",
                reason="Both latitude and longitude must be provided together"
            )

        return self

    @model_validator(mode="after")
    def validate_casualties(self) -> "IncidentValidator":
        """Ensure severity matches casualty count"""
        total_casualties = self.fatalities + self.injuries + self.missing_persons

        if total_casualties > 0 and self.severity_level < 3:
            # Auto-adjust severity if casualties present
            if self.fatalities > 0 or self.missing_persons > 0:
                self.severity_level = max(self.severity_level, 4)
            else:
                self.severity_level = max(self.severity_level, 3)

        return self


class VesselValidator(BaseModel):
    """Validator for vessel data"""

    vessel_name: str = Field(..., min_length=1, max_length=255)
    vessel_type: constants.VesselType = Field(...)
    imo_number: Optional[str] = Field(None, pattern=r"^\d{7}$")
    flag_state: Optional[str] = Field(None, max_length=5)
    year_built: Optional[int] = Field(None, ge=1800, le=datetime.now().year)
    gross_tonnage: Optional[Decimal] = Field(None, ge=0)
    company_name: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("imo_number")
    @classmethod
    def validate_imo_checksum(cls, v: Optional[str]) -> Optional[str]:
        """Validate IMO number checksum"""
        if v is None:
            return v

        # IMO number checksum algorithm
        if len(v) != 7 or not v.isdigit():
            raise InvalidDataError(
                field="imo_number",
                value=v,
                reason="IMO number must be 7 digits"
            )

        # Calculate checksum
        total = sum(int(v[i]) * (7 - i) for i in range(6))
        check_digit = total % 10

        if check_digit != int(v[6]):
            raise InvalidDataError(
                field="imo_number",
                value=v,
                reason="Invalid IMO number checksum"
            )

        return v


class CompanyValidator(BaseModel):
    """Validator for company data"""

    company_name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    company_type: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None


class LocationValidator(BaseModel):
    """Validator for location data"""

    location_name: Optional[str] = Field(None, max_length=500)
    latitude: Optional[Decimal] = Field(
        None,
        ge=constants.MIN_LATITUDE,
        le=constants.MAX_LATITUDE
    )
    longitude: Optional[Decimal] = Field(
        None,
        ge=constants.MIN_LONGITUDE,
        le=constants.MAX_LONGITUDE
    )
    water_depth_meters: Optional[Decimal] = Field(None, ge=0)
    region_code: Optional[str] = Field(None, max_length=10)
    country_code: Optional[str] = Field(None, max_length=5)
    metadata: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_coordinates(self) -> "LocationValidator":
        """Ensure either name or coordinates are provided"""
        has_coords = self.latitude is not None and self.longitude is not None
        has_name = self.location_name is not None

        if not has_coords and not has_name:
            raise MissingRequiredFieldError(
                field="location_name or coordinates",
            )

        if self.latitude is not None and self.longitude is None:
            raise InvalidDataError(
                field="coordinates",
                value=f"lat={self.latitude}",
                reason="Longitude required when latitude provided"
            )

        if self.longitude is not None and self.latitude is None:
            raise InvalidDataError(
                field="coordinates",
                value=f"lon={self.longitude}",
                reason="Latitude required when longitude provided"
            )

        return self


class DocumentValidator(BaseModel):
    """Validator for document data"""

    document_type: str = Field(..., max_length=50)
    document_title: Optional[str] = Field(None, max_length=500)
    document_url: str = Field(..., max_length=2048)
    publication_date: Optional[date] = None
    file_size_bytes: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("document_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Basic URL validation"""
        if not v.startswith(("http://", "https://", "ftp://")):
            raise InvalidDataError(
                field="document_url",
                value=v,
                reason="URL must start with http://, https://, or ftp://"
            )
        return v


def validate_incident(data: Dict[str, Any]) -> IncidentValidator:
    """
    Validate incident data dictionary.

    Args:
        data: Dictionary containing incident data

    Returns:
        IncidentValidator: Validated incident data

    Raises:
        ValidationError: If validation fails
    """
    return IncidentValidator(**data)


def validate_vessel(data: Dict[str, Any]) -> VesselValidator:
    """Validate vessel data dictionary"""
    return VesselValidator(**data)


def validate_company(data: Dict[str, Any]) -> CompanyValidator:
    """Validate company data dictionary"""
    return CompanyValidator(**data)


def validate_location(data: Dict[str, Any]) -> LocationValidator:
    """Validate location data dictionary"""
    return LocationValidator(**data)


def validate_document(data: Dict[str, Any]) -> DocumentValidator:
    """Validate document data dictionary"""
    return DocumentValidator(**data)
