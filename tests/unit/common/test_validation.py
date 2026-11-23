"""
Tests for worldenergydata.common.validation module.

Tests cover:
- APINumberSchema validates correctly
- CoordinateSchema validates lat/lon
- DateRangeSchema validates dates
- Validation rules work (RequiredRule, RangeRule, etc.)
"""

from datetime import date

import pytest


class TestAPINumberSchema:
    """Tests for APINumberSchema."""

    def test_valid_10_digit_api(self):
        """Test valid 10-digit API number."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="6081141234")

        assert schema.api_number == "6081141234"

    def test_valid_12_digit_api(self):
        """Test valid 12-digit API number."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="608114123400")

        assert schema.api_number == "608114123400"

    def test_valid_14_digit_api(self):
        """Test valid 14-digit API number."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="60811412340001")

        assert schema.api_number == "60811412340001"

    def test_removes_non_digits(self):
        """Test non-digit characters are removed."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="60-811-41234-00")

        assert schema.api_number == "608114123400"

    def test_invalid_length_raises(self):
        """Test invalid length raises validation error."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import APINumberSchema

        with pytest.raises(ValidationError) as exc_info:
            APINumberSchema(api_number="12345")

        assert "10, 12, or 14 digits" in str(exc_info.value)

    def test_state_code_property(self):
        """Test state_code property extracts first 2 digits."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="608114123400")

        assert schema.state_code == "60"

    def test_county_code_property(self):
        """Test county_code property extracts digits 3-5."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="608114123400")

        assert schema.county_code == "811"

    def test_unique_well_property(self):
        """Test unique_well property extracts digits 6-10."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="608114123400")

        assert schema.unique_well == "41234"

    def test_sidetrack_property_with_12_digits(self):
        """Test sidetrack property with 12-digit API."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="608114123401")

        assert schema.sidetrack == "01"

    def test_sidetrack_property_with_10_digits(self):
        """Test sidetrack property returns None for 10-digit API."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="6081141234")

        assert schema.sidetrack is None

    def test_completion_property_with_14_digits(self):
        """Test completion property with 14-digit API."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="60811412340102")

        assert schema.completion == "02"

    def test_completion_property_without_14_digits(self):
        """Test completion property returns None for <14-digit API."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="608114123400")

        assert schema.completion is None

    def test_api_10_property(self):
        """Test api_10 property returns first 10 digits."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="60811412340102")

        assert schema.api_10 == "6081141234"

    def test_api_12_property_with_12_digits(self):
        """Test api_12 property with 12+ digit API."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="60811412340102")

        assert schema.api_12 == "608114123401"

    def test_api_12_property_pads_10_digits(self):
        """Test api_12 property pads 10-digit API with 00."""
        from worldenergydata.common.validation.schemas import APINumberSchema

        schema = APINumberSchema(api_number="6081141234")

        assert schema.api_12 == "608114123400"


class TestCoordinateSchema:
    """Tests for CoordinateSchema."""

    def test_valid_coordinates(self):
        """Test valid coordinates are accepted."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        schema = CoordinateSchema(latitude=29.5, longitude=-88.5)

        assert schema.latitude == 29.5
        assert schema.longitude == -88.5

    def test_default_datum(self):
        """Test default datum is WGS84."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        schema = CoordinateSchema(latitude=0, longitude=0)

        assert schema.datum == "WGS84"

    def test_latitude_range_max(self):
        """Test latitude at maximum boundary."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        schema = CoordinateSchema(latitude=90, longitude=0)

        assert schema.latitude == 90

    def test_latitude_range_min(self):
        """Test latitude at minimum boundary."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        schema = CoordinateSchema(latitude=-90, longitude=0)

        assert schema.latitude == -90

    def test_latitude_out_of_range_high(self):
        """Test latitude > 90 is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import CoordinateSchema

        with pytest.raises(ValidationError):
            CoordinateSchema(latitude=91, longitude=0)

    def test_latitude_out_of_range_low(self):
        """Test latitude < -90 is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import CoordinateSchema

        with pytest.raises(ValidationError):
            CoordinateSchema(latitude=-91, longitude=0)

    def test_longitude_range_max(self):
        """Test longitude at maximum boundary."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        schema = CoordinateSchema(latitude=0, longitude=180)

        assert schema.longitude == 180

    def test_longitude_range_min(self):
        """Test longitude at minimum boundary."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        schema = CoordinateSchema(latitude=0, longitude=-180)

        assert schema.longitude == -180

    def test_longitude_out_of_range_high(self):
        """Test longitude > 180 is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import CoordinateSchema

        with pytest.raises(ValidationError):
            CoordinateSchema(latitude=0, longitude=181)

    def test_longitude_out_of_range_low(self):
        """Test longitude < -180 is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import CoordinateSchema

        with pytest.raises(ValidationError):
            CoordinateSchema(latitude=0, longitude=-181)

    def test_valid_datums(self):
        """Test valid datum values are accepted."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        for datum in ["WGS84", "NAD83", "NAD27"]:
            schema = CoordinateSchema(latitude=0, longitude=0, datum=datum)
            assert schema.datum == datum

    def test_datum_case_insensitive(self):
        """Test datum validation is case insensitive."""
        from worldenergydata.common.validation.schemas import CoordinateSchema

        schema = CoordinateSchema(latitude=0, longitude=0, datum="wgs84")

        assert schema.datum == "WGS84"

    def test_invalid_datum(self):
        """Test invalid datum is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import CoordinateSchema

        with pytest.raises(ValidationError):
            CoordinateSchema(latitude=0, longitude=0, datum="INVALID")


class TestDateRangeSchema:
    """Tests for DateRangeSchema."""

    def test_valid_date_range(self):
        """Test valid date range is accepted."""
        from worldenergydata.common.validation.schemas import DateRangeSchema

        schema = DateRangeSchema(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        assert schema.start_date == date(2023, 1, 1)
        assert schema.end_date == date(2023, 12, 31)

    def test_same_date_valid(self):
        """Test same start and end date is valid."""
        from worldenergydata.common.validation.schemas import DateRangeSchema

        schema = DateRangeSchema(
            start_date=date(2023, 6, 15),
            end_date=date(2023, 6, 15),
        )

        assert schema.start_date == schema.end_date

    def test_start_after_end_invalid(self):
        """Test start date after end date is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import DateRangeSchema

        with pytest.raises(ValidationError) as exc_info:
            DateRangeSchema(
                start_date=date(2023, 12, 31),
                end_date=date(2023, 1, 1),
            )

        assert "start_date must be before" in str(exc_info.value)


class TestProductionSchema:
    """Tests for ProductionSchema."""

    def test_valid_production_record(self):
        """Test valid production record."""
        from worldenergydata.common.validation.schemas import ProductionSchema

        schema = ProductionSchema(
            api_well_number="608114123400",
            production_date="202312",
            oil_volume=1000.0,
            gas_volume=5000.0,
            days_on_production=30,
        )

        assert schema.api_well_number == "608114123400"
        assert schema.production_date == "202312"
        assert schema.oil_volume == 1000.0
        assert schema.days_on_production == 30

    def test_api_must_be_12_digits(self):
        """Test API well number must be 12 digits."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import ProductionSchema

        with pytest.raises(ValidationError) as exc_info:
            ProductionSchema(
                api_well_number="6081141234",  # 10 digits
                production_date="202312",
                oil_volume=1000.0,
                gas_volume=5000.0,
                days_on_production=30,
            )

        assert "12 digits" in str(exc_info.value)

    def test_production_date_format(self):
        """Test production date must be YYYYMM format."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import ProductionSchema

        with pytest.raises(ValidationError):
            ProductionSchema(
                api_well_number="608114123400",
                production_date="2023-12",  # Wrong format
                oil_volume=1000.0,
                gas_volume=5000.0,
                days_on_production=30,
            )

    def test_invalid_month_rejected(self):
        """Test invalid month in production date is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import ProductionSchema

        with pytest.raises(ValidationError):
            ProductionSchema(
                api_well_number="608114123400",
                production_date="202313",  # Month 13
                oil_volume=1000.0,
                gas_volume=5000.0,
                days_on_production=30,
            )

    def test_negative_volume_rejected(self):
        """Test negative volumes are rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import ProductionSchema

        with pytest.raises(ValidationError):
            ProductionSchema(
                api_well_number="608114123400",
                production_date="202312",
                oil_volume=-100.0,
                gas_volume=5000.0,
                days_on_production=30,
            )

    def test_days_on_production_range(self):
        """Test days on production must be 0-31."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import ProductionSchema

        with pytest.raises(ValidationError):
            ProductionSchema(
                api_well_number="608114123400",
                production_date="202312",
                oil_volume=1000.0,
                gas_volume=5000.0,
                days_on_production=32,
            )

    def test_zero_days_zero_production(self):
        """Test zero days requires zero production."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import ProductionSchema

        with pytest.raises(ValidationError):
            ProductionSchema(
                api_well_number="608114123400",
                production_date="202312",
                oil_volume=1000.0,  # Non-zero with 0 days
                gas_volume=5000.0,
                days_on_production=0,
            )


class TestLeaseSchema:
    """Tests for LeaseSchema."""

    def test_valid_lease(self):
        """Test valid lease data."""
        from worldenergydata.common.validation.schemas import LeaseSchema

        schema = LeaseSchema(
            lease_number="OCS-G-12345",
            area_code="GOM",
            block_number="MC 123",
            effective_date=date(2020, 1, 1),
        )

        assert schema.lease_number == "OCS-G-12345"
        assert schema.area_code == "GOM"

    def test_valid_area_codes(self):
        """Test valid OCS area codes."""
        from worldenergydata.common.validation.schemas import LeaseSchema

        for area in ["GOM", "PAC", "ATL", "ALA"]:
            schema = LeaseSchema(
                lease_number="TEST",
                area_code=area,
                block_number="A",
                effective_date=date(2020, 1, 1),
            )
            assert schema.area_code == area

    def test_area_code_case_insensitive(self):
        """Test area code is case insensitive."""
        from worldenergydata.common.validation.schemas import LeaseSchema

        schema = LeaseSchema(
            lease_number="TEST",
            area_code="gom",
            block_number="A",
            effective_date=date(2020, 1, 1),
        )

        assert schema.area_code == "GOM"

    def test_invalid_area_code(self):
        """Test invalid area code is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import LeaseSchema

        with pytest.raises(ValidationError):
            LeaseSchema(
                lease_number="TEST",
                area_code="INVALID",
                block_number="A",
                effective_date=date(2020, 1, 1),
            )

    def test_expiration_before_effective_rejected(self):
        """Test expiration date before effective is rejected."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import LeaseSchema

        with pytest.raises(ValidationError):
            LeaseSchema(
                lease_number="TEST",
                area_code="GOM",
                block_number="A",
                effective_date=date(2020, 1, 1),
                expiration_date=date(2019, 12, 31),
            )


class TestWellSchema:
    """Tests for WellSchema."""

    def test_valid_well(self):
        """Test valid well data."""
        from worldenergydata.common.validation.schemas import WellSchema

        schema = WellSchema(
            api_well_number="608114123400",
            well_name="Test Well #1",
            well_status="ACTIVE",
        )

        assert schema.api_well_number == "608114123400"
        assert schema.well_name == "Test Well #1"
        assert schema.well_status == "ACTIVE"

    def test_valid_well_statuses(self):
        """Test valid well status codes."""
        from worldenergydata.common.validation.schemas import WellSchema

        valid_statuses = [
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
        ]

        for status in valid_statuses:
            schema = WellSchema(
                api_well_number="608114123400",
                well_name="Test",
                well_status=status,
            )
            assert schema.well_status == status

    def test_status_case_insensitive(self):
        """Test status validation is case insensitive."""
        from worldenergydata.common.validation.schemas import WellSchema

        schema = WellSchema(
            api_well_number="608114123400",
            well_name="Test",
            well_status="active",
        )

        assert schema.well_status == "ACTIVE"

    def test_total_depth_range(self):
        """Test total depth range validation."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import WellSchema

        with pytest.raises(ValidationError):
            WellSchema(
                api_well_number="608114123400",
                well_name="Test",
                well_status="ACTIVE",
                total_depth=60000,  # > 50000 limit
            )

    def test_water_depth_range(self):
        """Test water depth range validation."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import WellSchema

        with pytest.raises(ValidationError):
            WellSchema(
                api_well_number="608114123400",
                well_name="Test",
                well_status="ACTIVE",
                water_depth=20000,  # > 15000 limit
            )


class TestFinancialSchema:
    """Tests for FinancialSchema."""

    def test_valid_financial_params(self):
        """Test valid financial parameters."""
        from worldenergydata.common.validation.schemas import FinancialSchema

        schema = FinancialSchema(
            discount_rate=0.10,
            oil_price=75.0,
            gas_price=3.5,
            capex=1_000_000,
            opex=50_000,
            project_life_years=20,
        )

        assert schema.discount_rate == 0.10
        assert schema.royalty_rate == 0.125  # Default

    def test_discount_rate_range(self):
        """Test discount rate must be 0-1."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import FinancialSchema

        with pytest.raises(ValidationError):
            FinancialSchema(
                discount_rate=1.5,
                oil_price=75.0,
                gas_price=3.5,
                capex=1_000_000,
                opex=50_000,
                project_life_years=20,
            )

    def test_oil_price_range(self):
        """Test oil price range validation."""
        from pydantic import ValidationError

        from worldenergydata.common.validation.schemas import FinancialSchema

        with pytest.raises(ValidationError):
            FinancialSchema(
                discount_rate=0.10,
                oil_price=600.0,  # > 500 limit
                gas_price=3.5,
                capex=1_000_000,
                opex=50_000,
                project_life_years=20,
            )


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_basic_initialization(self):
        """Test basic ValidationResult initialization."""
        from worldenergydata.common.validation.validators import ValidationResult

        result = ValidationResult()

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.validated_count == 0
        assert result.failed_count == 0

    def test_add_error(self):
        """Test add_error method."""
        from worldenergydata.common.validation.validators import ValidationResult

        result = ValidationResult()
        result.add_error("field1", "required", "Field is required", "value1", 0)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0]["field"] == "field1"
        assert result.errors[0]["type"] == "required"
        assert result.errors[0]["row"] == 0

    def test_add_warning(self):
        """Test add_warning method."""
        from worldenergydata.common.validation.validators import ValidationResult

        result = ValidationResult()
        result.add_warning("field1", "Value seems high", 1000, 0)

        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1

    def test_merge(self):
        """Test merge method combines results."""
        from worldenergydata.common.validation.validators import ValidationResult

        result1 = ValidationResult(validated_count=10, failed_count=1)
        result1.add_error("f1", "type", "Error 1")

        result2 = ValidationResult(validated_count=5, failed_count=2)
        result2.add_error("f2", "type", "Error 2")
        result2.add_warning("f3", "Warning 1")

        result1.merge(result2)

        assert result1.is_valid is False
        assert result1.validated_count == 15
        assert result1.failed_count == 3
        assert len(result1.errors) == 2
        assert len(result1.warnings) == 1

    def test_to_dict(self):
        """Test to_dict serialization."""
        from worldenergydata.common.validation.validators import ValidationResult

        result = ValidationResult(validated_count=100, failed_count=5)
        result.add_error("field", "type", "Error")

        d = result.to_dict()

        assert d["is_valid"] is False
        assert d["validated_count"] == 100
        assert d["failed_count"] == 5
        assert d["error_count"] == 1


class TestValidateApiNumber:
    """Tests for validate_api_number function."""

    def test_valid_10_digit(self):
        """Test valid 10-digit API number."""
        from worldenergydata.common.validation.validators import validate_api_number

        is_valid, error = validate_api_number("6081141234")

        assert is_valid is True
        assert error is None

    def test_valid_12_digit(self):
        """Test valid 12-digit API number."""
        from worldenergydata.common.validation.validators import validate_api_number

        is_valid, error = validate_api_number("608114123400")

        assert is_valid is True
        assert error is None

    def test_empty_api(self):
        """Test empty API number is invalid."""
        from worldenergydata.common.validation.validators import validate_api_number

        is_valid, error = validate_api_number("")

        assert is_valid is False
        assert "required" in error.lower()

    def test_invalid_length(self):
        """Test invalid length is rejected."""
        from worldenergydata.common.validation.validators import validate_api_number

        is_valid, error = validate_api_number("12345")

        assert is_valid is False
        assert "10, 12, or 14 digits" in error

    def test_required_length(self):
        """Test required_length parameter."""
        from worldenergydata.common.validation.validators import validate_api_number

        is_valid, error = validate_api_number("6081141234", required_length=12)

        assert is_valid is False
        assert "12 digits" in error

    def test_invalid_state_code(self):
        """Test invalid state code is rejected."""
        from worldenergydata.common.validation.validators import validate_api_number

        is_valid, error = validate_api_number("9981141234")  # State 99 invalid

        assert is_valid is False
        assert "state code" in error.lower()


class TestValidateCoordinates:
    """Tests for validate_coordinates function."""

    def test_valid_coordinates(self):
        """Test valid coordinates pass."""
        from worldenergydata.common.validation.validators import validate_coordinates

        is_valid, error = validate_coordinates(29.5, -88.5)

        assert is_valid is True
        assert error is None

    def test_invalid_latitude(self):
        """Test invalid latitude is rejected."""
        from worldenergydata.common.validation.validators import validate_coordinates

        is_valid, error = validate_coordinates(91.0, -88.5)

        assert is_valid is False
        assert "latitude" in error.lower()

    def test_invalid_longitude(self):
        """Test invalid longitude is rejected."""
        from worldenergydata.common.validation.validators import validate_coordinates

        is_valid, error = validate_coordinates(29.5, -181.0)

        assert is_valid is False
        assert "longitude" in error.lower()

    def test_strict_ocean_mode(self):
        """Test strict ocean mode validates GOM region."""
        from worldenergydata.common.validation.validators import validate_coordinates

        # Inside GOM
        is_valid, _ = validate_coordinates(28.0, -88.0, strict_ocean=True)
        assert is_valid is True

        # Outside GOM latitude
        is_valid, error = validate_coordinates(40.0, -88.0, strict_ocean=True)
        assert is_valid is False
        assert "offshore region" in error.lower()


class TestValidateDateFormat:
    """Tests for validate_date_format function."""

    def test_valid_yyyymm(self):
        """Test valid YYYYMM format."""
        from worldenergydata.common.validation.validators import validate_date_format

        is_valid, error = validate_date_format("202312")

        assert is_valid is True
        assert error is None

    def test_valid_custom_format(self):
        """Test valid custom format."""
        from worldenergydata.common.validation.validators import validate_date_format

        is_valid, error = validate_date_format("2023-12-15", "%Y-%m-%d")

        assert is_valid is True
        assert error is None

    def test_invalid_format(self):
        """Test invalid format is rejected."""
        from worldenergydata.common.validation.validators import validate_date_format

        is_valid, error = validate_date_format("12-2023")

        assert is_valid is False
        assert "invalid date format" in error.lower()

    def test_year_out_of_range(self):
        """Test year out of reasonable range."""
        from worldenergydata.common.validation.validators import validate_date_format

        is_valid, error = validate_date_format("180001")

        assert is_valid is False
        assert "out of reasonable range" in error.lower()


class TestRequiredRule:
    """Tests for RequiredRule class."""

    def test_none_fails(self):
        """Test None value fails validation."""
        from worldenergydata.common.validation.rules import RequiredRule

        rule = RequiredRule("field")
        result = rule.validate(None)

        assert result.is_valid is False
        assert result.error_type == "required"

    def test_value_passes(self):
        """Test non-None value passes."""
        from worldenergydata.common.validation.rules import RequiredRule

        rule = RequiredRule("field")
        result = rule.validate("value")

        assert result.is_valid is True

    def test_empty_string_fails_by_default(self):
        """Test empty string fails by default."""
        from worldenergydata.common.validation.rules import RequiredRule

        rule = RequiredRule("field")
        result = rule.validate("")

        assert result.is_valid is False

    def test_empty_string_allowed(self):
        """Test empty string passes when allowed."""
        from worldenergydata.common.validation.rules import RequiredRule

        rule = RequiredRule("field", allow_empty_string=True)
        result = rule.validate("")

        assert result.is_valid is True


class TestRangeRule:
    """Tests for RangeRule class."""

    def test_within_range_passes(self):
        """Test value within range passes."""
        from worldenergydata.common.validation.rules import RangeRule

        rule = RangeRule("field", min_value=0, max_value=100)
        result = rule.validate(50)

        assert result.is_valid is True

    def test_below_min_fails(self):
        """Test value below minimum fails."""
        from worldenergydata.common.validation.rules import RangeRule

        rule = RangeRule("field", min_value=0)
        result = rule.validate(-1)

        assert result.is_valid is False
        assert result.error_type == "range"

    def test_above_max_fails(self):
        """Test value above maximum fails."""
        from worldenergydata.common.validation.rules import RangeRule

        rule = RangeRule("field", max_value=100)
        result = rule.validate(101)

        assert result.is_valid is False
        assert result.error_type == "range"

    def test_exclusive_range(self):
        """Test exclusive range (not inclusive)."""
        from worldenergydata.common.validation.rules import RangeRule

        rule = RangeRule("field", min_value=0, max_value=100, inclusive=False)

        # Boundary values should fail with exclusive
        assert rule.validate(0).is_valid is False
        assert rule.validate(100).is_valid is False
        assert rule.validate(1).is_valid is True

    def test_none_value_passes(self):
        """Test None value passes (use RequiredRule for null checks)."""
        from worldenergydata.common.validation.rules import RangeRule

        rule = RangeRule("field", min_value=0)
        result = rule.validate(None)

        assert result.is_valid is True

    def test_non_numeric_fails(self):
        """Test non-numeric value fails."""
        from worldenergydata.common.validation.rules import RangeRule

        rule = RangeRule("field", min_value=0)
        result = rule.validate("not a number")

        assert result.is_valid is False
        assert result.error_type == "type"


class TestPatternRule:
    """Tests for PatternRule class."""

    def test_matching_pattern_passes(self):
        """Test value matching pattern passes."""
        from worldenergydata.common.validation.rules import PatternRule

        rule = PatternRule("field", r"^\d{10}$")
        result = rule.validate("1234567890")

        assert result.is_valid is True

    def test_non_matching_fails(self):
        """Test value not matching pattern fails."""
        from worldenergydata.common.validation.rules import PatternRule

        rule = PatternRule("field", r"^\d{10}$")
        result = rule.validate("12345")

        assert result.is_valid is False
        assert result.error_type == "pattern"

    def test_none_value_passes(self):
        """Test None value passes."""
        from worldenergydata.common.validation.rules import PatternRule

        rule = PatternRule("field", r"^\d+$")
        result = rule.validate(None)

        assert result.is_valid is True

    def test_non_string_converted(self):
        """Test non-string value is converted to string."""
        from worldenergydata.common.validation.rules import PatternRule

        rule = PatternRule("field", r"^\d+$")
        result = rule.validate(12345)

        assert result.is_valid is True


class TestEnumRule:
    """Tests for EnumRule class."""

    def test_valid_value_passes(self):
        """Test value in allowed set passes."""
        from worldenergydata.common.validation.rules import EnumRule

        rule = EnumRule("field", {"A", "B", "C"})
        result = rule.validate("A")

        assert result.is_valid is True

    def test_invalid_value_fails(self):
        """Test value not in allowed set fails."""
        from worldenergydata.common.validation.rules import EnumRule

        rule = EnumRule("field", {"A", "B", "C"})
        result = rule.validate("D")

        assert result.is_valid is False
        assert result.error_type == "enum"

    def test_case_sensitive_default(self):
        """Test case sensitive by default."""
        from worldenergydata.common.validation.rules import EnumRule

        rule = EnumRule("field", {"A", "B"})

        assert rule.validate("A").is_valid is True
        assert rule.validate("a").is_valid is False

    def test_case_insensitive(self):
        """Test case insensitive option."""
        from worldenergydata.common.validation.rules import EnumRule

        rule = EnumRule("field", {"A", "B"}, case_sensitive=False)

        assert rule.validate("a").is_valid is True
        assert rule.validate("A").is_valid is True

    def test_none_value_passes(self):
        """Test None value passes."""
        from worldenergydata.common.validation.rules import EnumRule

        rule = EnumRule("field", {"A", "B"})
        result = rule.validate(None)

        assert result.is_valid is True


class TestCrossFieldRule:
    """Tests for CrossFieldRule class."""

    def test_valid_cross_field(self):
        """Test valid cross-field relationship passes."""
        from worldenergydata.common.validation.rules import CrossFieldRule

        def start_before_end(record):
            return record["start"] < record["end"]

        rule = CrossFieldRule(
            "start", ["end"], start_before_end, "Start must be before end"
        )
        result = rule.validate(1, {"start": 1, "end": 10})

        assert result.is_valid is True

    def test_invalid_cross_field(self):
        """Test invalid cross-field relationship fails."""
        from worldenergydata.common.validation.rules import CrossFieldRule

        def start_before_end(record):
            return record["start"] < record["end"]

        rule = CrossFieldRule(
            "start", ["end"], start_before_end, "Start must be before end"
        )
        result = rule.validate(10, {"start": 10, "end": 1})

        assert result.is_valid is False
        assert result.error_type == "cross_field"

    def test_missing_record_passes(self):
        """Test missing record skips validation."""
        from worldenergydata.common.validation.rules import CrossFieldRule

        rule = CrossFieldRule("a", ["b"], lambda r: False, "Error")
        result = rule.validate("value", None)

        assert result.is_valid is True

    def test_missing_related_field_passes(self):
        """Test missing related field skips validation."""
        from worldenergydata.common.validation.rules import CrossFieldRule

        rule = CrossFieldRule("a", ["b", "c"], lambda r: False, "Error")
        result = rule.validate("value", {"a": 1, "b": 2})  # Missing "c"

        assert result.is_valid is True


class TestCommonRules:
    """Tests for CommonRules helper class."""

    def test_api_number_10(self):
        """Test api_number_10 rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.api_number_10()

        assert rule.validate("1234567890").is_valid is True
        assert rule.validate("12345").is_valid is False

    def test_api_number_12(self):
        """Test api_number_12 rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.api_number_12()

        assert rule.validate("123456789012").is_valid is True
        assert rule.validate("1234567890").is_valid is False

    def test_production_date(self):
        """Test production_date rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.production_date()

        assert rule.validate("202312").is_valid is True
        assert rule.validate("2023-12").is_valid is False

    def test_positive_number(self):
        """Test positive_number rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.positive_number("volume")

        assert rule.validate(100).is_valid is True
        assert rule.validate(0).is_valid is True
        assert rule.validate(-1).is_valid is False

    def test_percentage(self):
        """Test percentage rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.percentage("rate")

        assert rule.validate(0.5).is_valid is True
        assert rule.validate(1.5).is_valid is False

    def test_latitude(self):
        """Test latitude rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.latitude()

        assert rule.validate(45.0).is_valid is True
        assert rule.validate(91.0).is_valid is False

    def test_longitude(self):
        """Test longitude rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.longitude()

        assert rule.validate(-88.5).is_valid is True
        assert rule.validate(-181.0).is_valid is False

    def test_days_in_month(self):
        """Test days_in_month rule."""
        from worldenergydata.common.validation.rules import CommonRules

        rule = CommonRules.days_in_month()

        assert rule.validate(30).is_valid is True
        assert rule.validate(32).is_valid is False
