"""Tests for Marine Safety module validators."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from worldenergydata.marine_safety.exceptions import (
    InvalidDataError,
    MissingRequiredFieldError,
)
from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    SeverityLevel,
    VesselType,
    WeatherCondition,
)
from worldenergydata.marine_safety.utils.validators import (
    CompanyValidator,
    DocumentValidator,
    IncidentValidator,
    LocationValidator,
    VesselValidator,
    validate_company,
    validate_document,
    validate_incident,
    validate_location,
    validate_vessel,
)


def _base_incident(**overrides):
    """Create minimal valid incident data."""
    data = {
        "source_agency": DataSource.BSEE,
        "source_incident_id": "INC-001",
        "incident_date": date(2020, 6, 15),
        "incident_type": IncidentType.COLLISION,
    }
    data.update(overrides)
    return data


class TestIncidentValidator:
    def test_valid_minimal(self):
        v = IncidentValidator(**_base_incident())
        assert v.source_agency == DataSource.BSEE
        assert v.source_incident_id == "INC-001"
        assert v.incident_type == IncidentType.COLLISION
        assert v.severity_level == SeverityLevel.MODERATE
        assert v.status == IncidentStatus.REPORTED

    def test_valid_with_all_fields(self):
        v = IncidentValidator(
            **_base_incident(
                incident_time=datetime(2020, 6, 15, 14, 30),
                severity_level=4,
                status=IncidentStatus.UNDER_INVESTIGATION,
                title="Test incident",
                description="A test incident",
                vessel_name="Test Vessel",
                vessel_type=VesselType.TANKER,
                imo_number="9074729",
                company_name="Test Co",
                latitude=Decimal("29.0"),
                longitude=Decimal("-90.0"),
                location_name="Gulf of Mexico",
                fatalities=0,
                injuries=2,
                missing_persons=0,
                weather_condition=WeatherCondition.STORM,
                wind_speed_knots=Decimal("45.0"),
                wave_height_meters=Decimal("5.0"),
                sea_state=6,
                metadata={"key": "value"},
            )
        )
        assert v.vessel_name == "Test Vessel"
        assert v.latitude == Decimal("29.0")

    def test_future_date_rejected(self):
        from datetime import timedelta

        future = date.today() + timedelta(days=30)
        with pytest.raises((PydanticValidationError, InvalidDataError)):
            IncidentValidator(**_base_incident(incident_date=future))

    def test_severity_auto_adjust_injuries(self):
        v = IncidentValidator(**_base_incident(injuries=3, severity_level=1))
        assert v.severity_level >= 3

    def test_severity_auto_adjust_fatalities(self):
        v = IncidentValidator(**_base_incident(fatalities=1, severity_level=1))
        assert v.severity_level >= 4

    def test_severity_auto_adjust_missing(self):
        v = IncidentValidator(
            **_base_incident(missing_persons=2, severity_level=1)
        )
        assert v.severity_level >= 4

    def test_no_severity_adjust_when_already_high(self):
        v = IncidentValidator(**_base_incident(injuries=1, severity_level=5))
        assert v.severity_level == 5

    def test_coordinates_both_required(self):
        with pytest.raises((PydanticValidationError, InvalidDataError)):
            IncidentValidator(
                **_base_incident(latitude=Decimal("29.0"), longitude=None)
            )

    def test_coordinates_both_none_ok(self):
        v = IncidentValidator(
            **_base_incident(latitude=None, longitude=None)
        )
        assert v.latitude is None

    def test_empty_source_id_rejected(self):
        with pytest.raises(PydanticValidationError):
            IncidentValidator(**_base_incident(source_incident_id=""))

    def test_severity_out_of_range(self):
        with pytest.raises(PydanticValidationError):
            IncidentValidator(**_base_incident(severity_level=6))

    def test_negative_fatalities(self):
        with pytest.raises(PydanticValidationError):
            IncidentValidator(**_base_incident(fatalities=-1))

    def test_sea_state_out_of_range(self):
        with pytest.raises(PydanticValidationError):
            IncidentValidator(**_base_incident(sea_state=10))

    def test_imo_number_pattern(self):
        with pytest.raises(PydanticValidationError):
            IncidentValidator(**_base_incident(imo_number="ABC"))

    def test_latitude_out_of_range(self):
        with pytest.raises(PydanticValidationError):
            IncidentValidator(
                **_base_incident(
                    latitude=Decimal("100.0"), longitude=Decimal("-90.0")
                )
            )


class TestVesselValidator:
    def test_valid_minimal(self):
        v = VesselValidator(
            vessel_name="Test Vessel", vessel_type=VesselType.TANKER
        )
        assert v.vessel_name == "Test Vessel"
        assert v.is_active is True

    def test_valid_full(self):
        v = VesselValidator(
            vessel_name="Big Ship",
            vessel_type=VesselType.FPSO,
            flag_state="US",
            year_built=2010,
            gross_tonnage=Decimal("50000"),
            company_name="Oil Corp",
            is_active=False,
            metadata={"rig_type": "semi"},
        )
        assert v.year_built == 2010
        assert v.is_active is False

    def test_empty_name_rejected(self):
        with pytest.raises(PydanticValidationError):
            VesselValidator(vessel_name="", vessel_type=VesselType.TUG)

    def test_imo_checksum_valid(self):
        # IMO 9074729: checksum = 9*7+0*6+7*5+4*4+7*3+2*2 = 63+0+35+16+21+4=139, 139%10=9 == v[6]=9
        v = VesselValidator(
            vessel_name="Test",
            vessel_type=VesselType.TANKER,
            imo_number="9074729",
        )
        assert v.imo_number == "9074729"

    def test_imo_checksum_invalid(self):
        # 1234560: checksum = 1*7+2*6+3*5+4*4+5*3+6*2 = 77, 77%10=7 != 0
        with pytest.raises((PydanticValidationError, InvalidDataError)):
            VesselValidator(
                vessel_name="Test",
                vessel_type=VesselType.TANKER,
                imo_number="1234560",
            )

    def test_imo_non_digit_rejected(self):
        with pytest.raises(PydanticValidationError):
            VesselValidator(
                vessel_name="Test",
                vessel_type=VesselType.TANKER,
                imo_number="ABCDEFG",
            )

    def test_year_built_too_old(self):
        with pytest.raises(PydanticValidationError):
            VesselValidator(
                vessel_name="Old Ship",
                vessel_type=VesselType.CARGO_VESSEL,
                year_built=1799,
            )

    def test_negative_tonnage(self):
        with pytest.raises(PydanticValidationError):
            VesselValidator(
                vessel_name="Test",
                vessel_type=VesselType.TUG,
                gross_tonnage=Decimal("-100"),
            )


class TestCompanyValidator:
    def test_valid(self):
        v = CompanyValidator(company_name="Test Corp")
        assert v.company_name == "Test Corp"
        assert v.is_active is True

    def test_with_all_fields(self):
        v = CompanyValidator(
            company_name="Oil Co",
            country="USA",
            company_type="Operator",
            is_active=False,
            metadata={"sector": "upstream"},
        )
        assert v.country == "USA"
        assert v.is_active is False

    def test_empty_name_rejected(self):
        with pytest.raises(PydanticValidationError):
            CompanyValidator(company_name="")


class TestLocationValidator:
    def test_valid_with_name(self):
        v = LocationValidator(location_name="Gulf of Mexico")
        assert v.location_name == "Gulf of Mexico"

    def test_valid_with_coordinates(self):
        v = LocationValidator(
            latitude=Decimal("29.0"), longitude=Decimal("-90.0")
        )
        assert v.latitude == Decimal("29.0")

    def test_valid_with_both(self):
        v = LocationValidator(
            location_name="GoM",
            latitude=Decimal("29.0"),
            longitude=Decimal("-90.0"),
        )
        assert v.location_name == "GoM"

    def test_neither_name_nor_coords_rejected(self):
        with pytest.raises(
            (PydanticValidationError, MissingRequiredFieldError)
        ):
            LocationValidator()

    def test_lat_without_lon_rejected(self):
        with pytest.raises(
            (PydanticValidationError, MissingRequiredFieldError, InvalidDataError)
        ):
            LocationValidator(latitude=Decimal("29.0"))

    def test_lon_without_lat_rejected(self):
        with pytest.raises(
            (PydanticValidationError, MissingRequiredFieldError, InvalidDataError)
        ):
            LocationValidator(longitude=Decimal("-90.0"))

    def test_lat_out_of_range(self):
        with pytest.raises(PydanticValidationError):
            LocationValidator(
                latitude=Decimal("100.0"), longitude=Decimal("-90.0")
            )


class TestDocumentValidator:
    def test_valid(self):
        v = DocumentValidator(
            document_type="report",
            document_url="https://example.com/report.pdf",
        )
        assert v.document_type == "report"

    def test_with_all_fields(self):
        v = DocumentValidator(
            document_type="investigation",
            document_title="Incident Report 2020-001",
            document_url="https://example.com/doc.pdf",
            publication_date=date(2020, 8, 1),
            file_size_bytes=1024000,
            metadata={"pages": 45},
        )
        assert v.file_size_bytes == 1024000

    def test_invalid_url_scheme(self):
        with pytest.raises((PydanticValidationError, InvalidDataError)):
            DocumentValidator(
                document_type="report", document_url="file:///local/path"
            )

    def test_ftp_url_accepted(self):
        v = DocumentValidator(
            document_type="data", document_url="ftp://ftp.example.com/data.csv"
        )
        assert v.document_url.startswith("ftp://")

    def test_negative_file_size(self):
        with pytest.raises(PydanticValidationError):
            DocumentValidator(
                document_type="report",
                document_url="https://x.com/r.pdf",
                file_size_bytes=-1,
            )


class TestConvenienceFunctions:
    def test_validate_incident(self):
        result = validate_incident(_base_incident())
        assert isinstance(result, IncidentValidator)

    def test_validate_vessel(self):
        result = validate_vessel(
            {"vessel_name": "Test", "vessel_type": VesselType.TUG}
        )
        assert isinstance(result, VesselValidator)

    def test_validate_company(self):
        result = validate_company({"company_name": "Test Corp"})
        assert isinstance(result, CompanyValidator)

    def test_validate_location(self):
        result = validate_location({"location_name": "GoM"})
        assert isinstance(result, LocationValidator)

    def test_validate_document(self):
        result = validate_document(
            {
                "document_type": "report",
                "document_url": "https://example.com/r.pdf",
            }
        )
        assert isinstance(result, DocumentValidator)
