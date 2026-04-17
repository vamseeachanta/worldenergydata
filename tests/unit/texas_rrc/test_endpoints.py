"""Tests for Texas RRC API endpoint definitions."""

import pytest

from worldenergydata.texas_rrc.endpoints import (
    API_DEFAULTS,
    DATA_TYPE_ENDPOINTS,
    GIS_ENDPOINTS,
    PDQ_ENDPOINTS,
    TEXAS_DISTRICTS,
    TEXAS_FIPS,
    WELL_QUERY_ENDPOINTS,
    build_api_number,
    get_district_info,
    get_pdq_endpoint,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_pdq_endpoints_has_production(self):
        assert "oil_gas_production" in PDQ_ENDPOINTS
        assert "url" in PDQ_ENDPOINTS["oil_gas_production"]

    def test_pdq_endpoints_has_wells(self):
        assert "well_bore_database" in PDQ_ENDPOINTS

    def test_pdq_endpoints_has_drilling_permits(self):
        assert "drilling_permits" in PDQ_ENDPOINTS

    def test_districts_count(self):
        assert len(TEXAS_DISTRICTS) == 12

    def test_district_7b(self):
        assert TEXAS_DISTRICTS["7B"]["headquarters"] == "San Angelo"

    def test_api_defaults(self):
        assert API_DEFAULTS["rate_limit"] == 5
        assert API_DEFAULTS["cache_ttl"] == 86400

    def test_texas_fips_state_code(self):
        assert TEXAS_FIPS["state_code"] == "42"

    def test_data_type_endpoints_mapping(self):
        assert DATA_TYPE_ENDPOINTS["production"] == "oil_gas_production"
        assert DATA_TYPE_ENDPOINTS["wells"] == "well_bore_database"


# ---------------------------------------------------------------------------
# get_pdq_endpoint
# ---------------------------------------------------------------------------


class TestGetPdqEndpoint:
    def test_production(self):
        result = get_pdq_endpoint("production")
        assert "url" in result
        assert "fields" in result

    def test_wells(self):
        result = get_pdq_endpoint("wells")
        assert result["format"] == "zip"

    def test_drilling_permits(self):
        result = get_pdq_endpoint("drilling_permits")
        assert "url" in result

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown data type"):
            get_pdq_endpoint("nonexistent")


# ---------------------------------------------------------------------------
# get_district_info
# ---------------------------------------------------------------------------


class TestGetDistrictInfo:
    def test_district_1(self):
        info = get_district_info("01")
        assert info["headquarters"] == "San Antonio"

    def test_district_8(self):
        info = get_district_info("08")
        assert info["headquarters"] == "Midland"

    def test_single_digit_normalization(self):
        info = get_district_info("1")
        assert info["headquarters"] == "San Antonio"

    def test_district_7b(self):
        info = get_district_info("7B")
        assert info["headquarters"] == "San Angelo"

    def test_case_insensitive(self):
        info = get_district_info("7b")
        assert info["headquarters"] == "San Angelo"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid district code"):
            get_district_info("99")


# ---------------------------------------------------------------------------
# build_api_number
# ---------------------------------------------------------------------------


class TestBuildApiNumber:
    def test_basic(self):
        result = build_api_number("135", "12345")
        assert result == "42-135-12345"

    def test_padding(self):
        result = build_api_number("3", "1")
        assert result == "42-003-00001"

    def test_full_length(self):
        result = build_api_number("329", "99999")
        assert result == "42-329-99999"
