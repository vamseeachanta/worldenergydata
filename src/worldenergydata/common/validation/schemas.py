"""
Validation Schema Definitions for WorldEnergyData

This module defines pydantic-based validation schemas for common
energy data types used across modules.
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class APINumberSchema(BaseModel):
    """
    Schema for validating API well numbers.

    Supports 10, 12, and 14-digit API numbers:
    - 10-digit: State (2) + County (3) + Unique Well (5)
    - 12-digit: 10-digit + Sidetrack (2)
    - 14-digit: 12-digit + Completion (2)
    """

    api_number: str = Field(..., description="API well number")

    @field_validator("api_number")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate API number format."""
        # Remove any non-digit characters
        cleaned = re.sub(r"\D", "", v)

        if len(cleaned) not in (10, 12, 14):
            raise ValueError(
                f"API number must be 10, 12, or 14 digits, got {len(cleaned)}"
            )

        return cleaned

    @property
    def state_code(self) -> str:
        """Extract 2-digit state code."""
        return self.api_number[:2]

    @property
    def county_code(self) -> str:
        """Extract 3-digit county code."""
        return self.api_number[2:5]

    @property
    def unique_well(self) -> str:
        """Extract 5-digit unique well identifier."""
        return self.api_number[5:10]

    @property
    def sidetrack(self) -> Optional[str]:
        """Extract 2-digit sidetrack code if present."""
        if len(self.api_number) >= 12:
            return self.api_number[10:12]
        return None

    @property
    def completion(self) -> Optional[str]:
        """Extract 2-digit completion code if present."""
        if len(self.api_number) >= 14:
            return self.api_number[12:14]
        return None

    @property
    def api_10(self) -> str:
        """Return 10-digit API number."""
        return self.api_number[:10]

    @property
    def api_12(self) -> str:
        """Return 12-digit API number (padded with 00 if needed)."""
        if len(self.api_number) >= 12:
            return self.api_number[:12]
        return self.api_number + "00"


class CoordinateSchema(BaseModel):
    """Schema for validating geographic coordinates."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    datum: str = Field(default="WGS84", description="Coordinate datum")

    @field_validator("datum")
    @classmethod
    def validate_datum(cls, v: str) -> str:
        """Validate coordinate datum."""
        valid_datums = {"WGS84", "NAD83", "NAD27"}
        v = v.upper()
        if v not in valid_datums:
            raise ValueError(f"Invalid datum: {v}. Must be one of {valid_datums}")
        return v


class DateRangeSchema(BaseModel):
    """Schema for validating date ranges."""

    start_date: date = Field(..., description="Start date")
    end_date: date = Field(..., description="End date")

    @model_validator(mode="after")
    def validate_range(self) -> "DateRangeSchema":
        """Validate that start_date is before end_date."""
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class ProductionSchema(BaseModel):
    """
    Schema for validating production data records.

    Based on BSEE production data format.
    """

    api_well_number: str = Field(..., description="12-digit API well number")
    production_date: str = Field(..., description="Production date (YYYYMM)")
    oil_volume: float = Field(..., ge=0, description="Oil production volume in barrels")
    gas_volume: float = Field(..., ge=0, description="Gas production volume in MCF")
    water_volume: Optional[float] = Field(
        default=None, ge=0, description="Water production volume in barrels"
    )
    days_on_production: int = Field(..., ge=0, le=31, description="Days on production")
    lease_number: Optional[str] = Field(default=None, description="Lease number")

    @field_validator("api_well_number")
    @classmethod
    def validate_api(cls, v: str) -> str:
        """Validate API well number format."""
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) != 12:
            raise ValueError("API well number must be 12 digits")
        return cleaned

    @field_validator("production_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate production date format."""
        if not re.match(r"^\d{6}$", v):
            raise ValueError("Production date must be in YYYYMM format")

        # Validate it's a valid date
        year = int(v[:4])
        month = int(v[4:6])

        if year < 1900 or year > 2100:
            raise ValueError(f"Invalid year: {year}")
        if month < 1 or month > 12:
            raise ValueError(f"Invalid month: {month}")

        return v

    @model_validator(mode="after")
    def validate_production_consistency(self) -> "ProductionSchema":
        """Validate production data consistency."""
        # If days on production is 0, volumes should be 0
        if self.days_on_production == 0:
            if self.oil_volume > 0 or self.gas_volume > 0:
                raise ValueError(
                    "Production volumes must be 0 when days_on_production is 0"
                )
        return self


class LeaseSchema(BaseModel):
    """Schema for validating lease data."""

    lease_number: str = Field(..., description="BSEE lease number")
    area_code: str = Field(..., description="OCS area code")
    block_number: str = Field(..., description="Block number")
    effective_date: date = Field(..., description="Lease effective date")
    expiration_date: Optional[date] = Field(
        default=None, description="Lease expiration date"
    )

    @field_validator("area_code")
    @classmethod
    def validate_area(cls, v: str) -> str:
        """Validate OCS area code."""
        valid_areas = {"GOM", "PAC", "ATL", "ALA"}
        v = v.upper()
        if v not in valid_areas:
            raise ValueError(f"Invalid area code: {v}. Must be one of {valid_areas}")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "LeaseSchema":
        """Validate date consistency."""
        if self.expiration_date and self.expiration_date < self.effective_date:
            raise ValueError("Expiration date must be after effective date")
        return self


class WellSchema(BaseModel):
    """Schema for validating well master data."""

    api_well_number: str = Field(..., description="API well number")
    well_name: str = Field(..., max_length=100, description="Well name")
    well_status: str = Field(..., description="Well status code")
    spud_date: Optional[date] = Field(default=None, description="Spud date")
    total_depth: Optional[float] = Field(
        default=None, ge=0, le=50000, description="Total depth in feet"
    )
    water_depth: Optional[float] = Field(
        default=None, ge=0, le=15000, description="Water depth in feet"
    )
    surface_latitude: Optional[float] = Field(
        default=None, ge=-90, le=90, description="Surface latitude"
    )
    surface_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Surface longitude"
    )

    @field_validator("well_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate well status."""
        valid_statuses = {
            "ACTIVE",
            "INACTIVE",
            "PLUGGED",
            "ABANDONED",
            "SUSPENDED",
            "PRODUCING",
            "SHUT-IN",
            "P&A",
            "DRILLING",
            "COMPLETING",
        }
        v = v.upper()
        if v not in valid_statuses:
            raise ValueError(f"Invalid well status: {v}")
        return v


class FinancialSchema(BaseModel):
    """Schema for validating financial analysis parameters."""

    discount_rate: float = Field(..., ge=0, le=1, description="Discount rate (0-1)")
    oil_price: float = Field(..., ge=0, le=500, description="Oil price in $/barrel")
    gas_price: float = Field(..., ge=0, le=50, description="Gas price in $/MCF")
    capex: float = Field(..., ge=0, description="Capital expenditure in $")
    opex: float = Field(..., ge=0, description="Operating expenditure in $")
    royalty_rate: float = Field(
        default=0.125, ge=0, le=0.5, description="Royalty rate (0-0.5)"
    )
    project_life_years: int = Field(
        ..., ge=1, le=100, description="Project life in years"
    )
    working_interest: float = Field(
        default=1.0, ge=0, le=1, description="Working interest (0-1)"
    )
