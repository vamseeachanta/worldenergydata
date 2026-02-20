"""Tests for common validation schemas."""

from datetime import date

import pytest
from pydantic import ValidationError

from worldenergydata.common.validation.schemas import (
    APINumberSchema,
    CoordinateSchema,
    DateRangeSchema,
    FinancialSchema,
    LeaseSchema,
    ProductionSchema,
    WellSchema,
)


class TestAPINumberSchema:
    def test_10_digit(self):
        a = APINumberSchema(api_number="4201312345")
        assert a.api_number == "4201312345"
        assert a.state_code == "42"
        assert a.county_code == "013"
        assert a.unique_well == "12345"

    def test_12_digit(self):
        a = APINumberSchema(api_number="420131234500")
        assert a.sidetrack == "00"
        assert a.api_10 == "4201312345"

    def test_14_digit(self):
        a = APINumberSchema(api_number="42013123450001")
        assert a.completion == "01"
        assert a.api_12 == "420131234500"

    def test_strips_non_digits(self):
        a = APINumberSchema(api_number="42-013-12345")
        assert a.api_number == "4201312345"

    def test_invalid_length(self):
        with pytest.raises(ValidationError, match="10, 12, or 14 digits"):
            APINumberSchema(api_number="12345")

    def test_sidetrack_none_for_10_digit(self):
        a = APINumberSchema(api_number="4201312345")
        assert a.sidetrack is None

    def test_completion_none_for_10_digit(self):
        a = APINumberSchema(api_number="4201312345")
        assert a.completion is None

    def test_api_12_pads_10_digit(self):
        a = APINumberSchema(api_number="4201312345")
        assert a.api_12 == "420131234500"


class TestCoordinateSchema:
    def test_valid(self):
        c = CoordinateSchema(latitude=28.5, longitude=-90.0)
        assert c.datum == "WGS84"

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            CoordinateSchema(latitude=91.0, longitude=0.0)

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            CoordinateSchema(latitude=0.0, longitude=181.0)

    def test_valid_datum(self):
        c = CoordinateSchema(latitude=0.0, longitude=0.0, datum="NAD83")
        assert c.datum == "NAD83"

    def test_invalid_datum(self):
        with pytest.raises(ValidationError, match="Invalid datum"):
            CoordinateSchema(latitude=0.0, longitude=0.0, datum="INVALID")

    def test_datum_case_insensitive(self):
        c = CoordinateSchema(latitude=0.0, longitude=0.0, datum="wgs84")
        assert c.datum == "WGS84"


class TestDateRangeSchema:
    def test_valid(self):
        d = DateRangeSchema(
            start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
        )
        assert d.start_date == date(2024, 1, 1)

    def test_same_day(self):
        d = DateRangeSchema(
            start_date=date(2024, 6, 15), end_date=date(2024, 6, 15),
        )
        assert d.start_date == d.end_date

    def test_invalid_range(self):
        with pytest.raises(ValidationError, match="start_date must be before"):
            DateRangeSchema(
                start_date=date(2024, 12, 31), end_date=date(2024, 1, 1),
            )


class TestProductionSchema:
    def test_valid(self):
        p = ProductionSchema(
            api_well_number="420131234500",
            production_date="202401",
            oil_volume=5000.0,
            gas_volume=10000.0,
            days_on_production=31,
        )
        assert p.oil_volume == 5000.0

    def test_invalid_api_length(self):
        with pytest.raises(ValidationError, match="12 digits"):
            ProductionSchema(
                api_well_number="123",
                production_date="202401",
                oil_volume=0.0, gas_volume=0.0,
                days_on_production=0,
            )

    def test_invalid_production_date_format(self):
        with pytest.raises(ValidationError, match="YYYYMM"):
            ProductionSchema(
                api_well_number="420131234500",
                production_date="2024-01",
                oil_volume=0.0, gas_volume=0.0,
                days_on_production=0,
            )

    def test_invalid_month(self):
        with pytest.raises(ValidationError, match="Invalid month"):
            ProductionSchema(
                api_well_number="420131234500",
                production_date="202413",
                oil_volume=0.0, gas_volume=0.0,
                days_on_production=0,
            )

    def test_negative_oil_volume(self):
        with pytest.raises(ValidationError):
            ProductionSchema(
                api_well_number="420131234500",
                production_date="202401",
                oil_volume=-100.0, gas_volume=0.0,
                days_on_production=1,
            )

    def test_zero_days_with_production_raises(self):
        with pytest.raises(ValidationError, match="days_on_production is 0"):
            ProductionSchema(
                api_well_number="420131234500",
                production_date="202401",
                oil_volume=100.0, gas_volume=0.0,
                days_on_production=0,
            )

    def test_zero_days_zero_volume_ok(self):
        p = ProductionSchema(
            api_well_number="420131234500",
            production_date="202401",
            oil_volume=0.0, gas_volume=0.0,
            days_on_production=0,
        )
        assert p.days_on_production == 0

    def test_days_exceeds_31(self):
        with pytest.raises(ValidationError):
            ProductionSchema(
                api_well_number="420131234500",
                production_date="202401",
                oil_volume=0.0, gas_volume=0.0,
                days_on_production=32,
            )


class TestLeaseSchema:
    def test_valid(self):
        l = LeaseSchema(
            lease_number="G12345",
            area_code="GOM",
            block_number="123",
            effective_date=date(2020, 1, 1),
        )
        assert l.area_code == "GOM"

    def test_area_code_case_insensitive(self):
        l = LeaseSchema(
            lease_number="G12345",
            area_code="gom",
            block_number="123",
            effective_date=date(2020, 1, 1),
        )
        assert l.area_code == "GOM"

    def test_invalid_area_code(self):
        with pytest.raises(ValidationError, match="Invalid area code"):
            LeaseSchema(
                lease_number="G12345",
                area_code="XYZ",
                block_number="123",
                effective_date=date(2020, 1, 1),
            )

    def test_expiration_before_effective(self):
        with pytest.raises(ValidationError, match="Expiration date"):
            LeaseSchema(
                lease_number="G12345",
                area_code="GOM",
                block_number="123",
                effective_date=date(2020, 6, 1),
                expiration_date=date(2020, 1, 1),
            )


class TestWellSchema:
    def test_valid(self):
        w = WellSchema(
            api_well_number="420131234500",
            well_name="Test Well 1",
            well_status="ACTIVE",
            total_depth=15000.0,
        )
        assert w.well_status == "ACTIVE"

    def test_status_case_insensitive(self):
        w = WellSchema(
            api_well_number="420131234500",
            well_name="Test Well",
            well_status="active",
        )
        assert w.well_status == "ACTIVE"

    def test_invalid_status(self):
        with pytest.raises(ValidationError, match="Invalid well status"):
            WellSchema(
                api_well_number="420131234500",
                well_name="Test Well",
                well_status="FLYING",
            )

    def test_depth_out_of_range(self):
        with pytest.raises(ValidationError):
            WellSchema(
                api_well_number="420131234500",
                well_name="Test Well",
                well_status="ACTIVE",
                total_depth=60000.0,
            )


class TestFinancialSchema:
    def test_valid(self):
        f = FinancialSchema(
            discount_rate=0.10,
            oil_price=70.0,
            gas_price=3.5,
            capex=50000000.0,
            opex=10000000.0,
            project_life_years=20,
        )
        assert f.royalty_rate == 0.125
        assert f.working_interest == 1.0

    def test_discount_rate_bounds(self):
        with pytest.raises(ValidationError):
            FinancialSchema(
                discount_rate=1.5,
                oil_price=70.0, gas_price=3.5,
                capex=1000.0, opex=500.0,
                project_life_years=10,
            )

    def test_oil_price_max(self):
        with pytest.raises(ValidationError):
            FinancialSchema(
                discount_rate=0.1,
                oil_price=600.0, gas_price=3.5,
                capex=1000.0, opex=500.0,
                project_life_years=10,
            )
