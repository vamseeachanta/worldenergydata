"""
Test suite for marine_safety data validation.

Tests coordinate validation, date validation, business logic rules,
and cross-field validation.
"""

from datetime import date
from decimal import Decimal

import pytest

from worldenergydata.marine_safety.utils.validators import (
    CompanyValidator,
    IncidentValidator,
    LocationValidator,
    VesselValidator,
)


class TestIncidentValidator:
    """Test suite for incident data validation."""

    @pytest.mark.unit
    def test_valid_incident_data(self):
        """Test validation of complete valid incident data."""
        validator = IncidentValidator()

        incident_data = {
            "incident_date": date(2024, 1, 15),
            "incident_type": "collision",
            "severity": "moderate",
            "location": "Gulf of Mexico",
            "latitude": Decimal("29.123456"),
            "longitude": Decimal("-94.123456"),
            "casualties": 2,
            "fatalities": 0,
            "injuries": 2,
        }

        result = validator.validate(incident_data)
        assert result.is_valid

    @pytest.mark.unit
    def test_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        validator = IncidentValidator()

        incomplete_data = {
            "incident_type": "collision",
            "severity": "moderate",
            # Missing incident_date and location
        }

        result = validator.validate(incomplete_data)
        assert not result.is_valid
        assert len(result.errors) >= 2

    @pytest.mark.unit
    def test_casualties_validation(self):
        """Test validation of casualty numbers."""
        validator = IncidentValidator()

        # Valid: fatalities + injuries = casualties
        incident_data = {"casualties": 5, "fatalities": 2, "injuries": 3}
        result = validator.validate_casualties(incident_data)
        assert result.is_valid

        # Invalid: sum doesn't match
        incident_data = {"casualties": 5, "fatalities": 2, "injuries": 2}
        result = validator.validate_casualties(incident_data)
        assert not result.is_valid

    @pytest.mark.unit
    def test_negative_casualties(self):
        """Test that negative casualty numbers fail validation."""
        validator = IncidentValidator()

        incident_data = {"casualties": -1, "fatalities": 0, "injuries": 0}

        result = validator.validate_casualties(incident_data)
        assert not result.is_valid

    @pytest.mark.unit
    def test_severity_type_consistency(self):
        """Test validation of severity vs incident type consistency."""
        validator = IncidentValidator()

        # Fire with critical severity and fatalities - valid
        incident = {"incident_type": "fire", "severity": "critical", "fatalities": 3}
        result = validator.validate_severity_consistency(incident)
        assert result.is_valid

        # Minor severity with fatalities - invalid
        incident = {"incident_type": "collision", "severity": "minor", "fatalities": 2}
        result = validator.validate_severity_consistency(incident)
        assert not result.is_valid

    @pytest.mark.unit
    def test_location_validation(self):
        """Test validation of location data."""
        validator = IncidentValidator()

        # Valid location with coordinates
        incident = {
            "location": "Gulf of Mexico",
            "latitude": Decimal("29.0"),
            "longitude": Decimal("-94.0"),
        }
        result = validator.validate_location(incident)
        assert result.is_valid

        # Coordinates without location name
        incident = {"latitude": Decimal("29.0"), "longitude": Decimal("-94.0")}
        result = validator.validate_location(incident)
        assert result.is_valid  # Coordinates are sufficient


class TestVesselValidator:
    """Test suite for vessel data validation."""

    @pytest.mark.unit
    def test_valid_vessel_data(self):
        """Test validation of complete valid vessel data."""
        validator = VesselValidator()

        vessel_data = {
            "name": "Test Vessel",
            "imo_number": "9876543",
            "vessel_type": "Tanker",
            "flag_state": "USA",
            "gross_tonnage": 50000,
            "year_built": 2010,
        }

        result = validator.validate(vessel_data)
        assert result.is_valid

    @pytest.mark.unit
    def test_vessel_name_required(self):
        """Test that vessel name is required."""
        validator = VesselValidator()

        vessel_data = {"imo_number": "9876543", "vessel_type": "Tanker"}

        result = validator.validate(vessel_data)
        assert not result.is_valid

    @pytest.mark.unit
    def test_gross_tonnage_positive(self):
        """Test that gross tonnage must be positive."""
        validator = VesselValidator()

        vessel_data = {"name": "Test Vessel", "gross_tonnage": -1000}

        result = validator.validate_gross_tonnage(vessel_data["gross_tonnage"])
        assert not result.is_valid

    @pytest.mark.unit
    def test_year_built_range(self):
        """Test validation of vessel build year."""
        validator = VesselValidator()

        # Valid year
        result = validator.validate_year_built(2010)
        assert result.is_valid

        # Future year
        result = validator.validate_year_built(2050)
        assert not result.is_valid

        # Too old
        result = validator.validate_year_built(1800)
        assert not result.is_valid


class TestCrossFieldValidation:
    """Test suite for cross-field validation rules."""

    @pytest.mark.unit
    def test_pollution_environmental_impact(self):
        """Test that pollution incidents require environmental impact."""
        validator = IncidentValidator()

        # Pollution with environmental impact - valid
        incident = {
            "incident_type": "pollution",
            "environmental_impact": "Oil spill in Gulf waters",
        }
        result = validator.validate_environmental_consistency(incident)
        assert result.is_valid

        # Pollution without environmental impact - invalid
        incident = {"incident_type": "pollution", "environmental_impact": None}
        result = validator.validate_environmental_consistency(incident)
        assert not result.is_valid

    @pytest.mark.unit
    def test_critical_severity_requires_investigation(self):
        """Test that critical incidents require investigation status."""
        validator = IncidentValidator()

        # Critical with investigation - valid
        incident = {"severity": "critical", "investigation_status": "Open"}
        result = validator.validate_investigation_required(incident)
        assert result.is_valid

        # Critical without investigation - invalid
        incident = {"severity": "critical", "investigation_status": None}
        result = validator.validate_investigation_required(incident)
        assert not result.is_valid

    @pytest.mark.unit
    def test_vessel_incident_consistency(self):
        """Test validation of vessel-incident data consistency."""
        validator = IncidentValidator()

        vessel = {"vessel_type": "Tanker", "flag_state": "USA"}

        incident = {"incident_type": "pollution", "location": "USA waters"}

        result = validator.validate_vessel_incident_consistency(vessel, incident)
        assert result.is_valid


