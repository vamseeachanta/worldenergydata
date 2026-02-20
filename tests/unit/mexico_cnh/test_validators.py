"""Tests for Mexico CNH module data validators."""

from worldenergydata.mexico_cnh.validators import (
    MexicoCNHValidator,
    is_valid_clave_pozo,
    is_valid_mexico_coordinates,
    is_valid_contract_id,
)


class TestValidateClavePozo:
    """Tests for MexicoCNHValidator.validate_clave_pozo."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_empty(self):
        valid, err = self.v.validate_clave_pozo("")
        assert valid is False
        assert "empty" in err.lower()

    def test_none(self):
        valid, err = self.v.validate_clave_pozo(None)
        assert valid is False

    def test_too_short(self):
        valid, err = self.v.validate_clave_pozo("AB")
        assert valid is False
        assert "short" in err.lower()

    def test_invalid_characters(self):
        valid, err = self.v.validate_clave_pozo("AKAL C@1001")
        assert valid is False
        assert "Invalid characters" in err

    def test_modern_cnh_format(self):
        valid, err = self.v.validate_clave_pozo("AKAL-C-1001-D")
        assert valid is True
        assert err is None

    def test_legacy_pemex_format(self):
        valid, err = self.v.validate_clave_pozo("CANTARELL101")
        assert valid is True

    def test_legacy_with_hyphen(self):
        valid, err = self.v.validate_clave_pozo("CANTARELL-101")
        assert valid is True

    def test_prefix_numeric(self):
        valid, err = self.v.validate_clave_pozo("AB123456")
        assert valid is True

    def test_with_hyphen_accepted(self):
        # Format with hyphen but not matching strict patterns: accepted if starts with alpha
        valid, err = self.v.validate_clave_pozo("SOME-WELL-KEY")
        assert valid is True

    def test_uppercase_normalized(self):
        valid, err = self.v.validate_clave_pozo("akal-c-1001")
        assert valid is True


class TestValidateMexicoCoordinates:
    """Tests for MexicoCNHValidator.validate_mexico_coordinates."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_none_latitude(self):
        valid, err = self.v.validate_mexico_coordinates(None, -90.0)
        assert valid is False
        assert "missing" in err.lower()

    def test_none_longitude(self):
        valid, err = self.v.validate_mexico_coordinates(20.0, None)
        assert valid is False

    def test_valid_onshore(self):
        valid, err = self.v.validate_mexico_coordinates(19.4, -99.1)
        assert valid is True

    def test_latitude_too_low(self):
        valid, err = self.v.validate_mexico_coordinates(10.0, -99.0)
        assert valid is False
        assert "outside Mexico bounds" in err

    def test_latitude_too_high(self):
        valid, err = self.v.validate_mexico_coordinates(35.0, -99.0)
        assert valid is False

    def test_longitude_too_low(self):
        valid, err = self.v.validate_mexico_coordinates(20.0, -120.0)
        assert valid is False

    def test_longitude_too_high(self):
        valid, err = self.v.validate_mexico_coordinates(20.0, -80.0)
        assert valid is False

    def test_valid_offshore(self):
        valid, err = self.v.validate_mexico_coordinates(22.0, -92.0, offshore_only=True)
        assert valid is True

    def test_offshore_lat_too_low(self):
        valid, err = self.v.validate_mexico_coordinates(15.0, -92.0, offshore_only=True)
        assert valid is False
        assert "Gulf of Mexico" in err

    def test_offshore_lon_too_high(self):
        valid, err = self.v.validate_mexico_coordinates(22.0, -85.0, offshore_only=True)
        assert valid is False

    def test_invalid_format(self):
        valid, err = self.v.validate_mexico_coordinates("abc", -99.0)
        assert valid is False
        assert "Invalid coordinate" in err


class TestValidateUTMZone:
    """Tests for MexicoCNHValidator.validate_utm_zone."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_valid_zone_14(self):
        valid, err = self.v.validate_utm_zone(14)
        assert valid is True

    def test_valid_zone_11(self):
        valid, err = self.v.validate_utm_zone(11)
        assert valid is True

    def test_invalid_zone(self):
        valid, err = self.v.validate_utm_zone(5)
        assert valid is False
        assert "Invalid UTM zone" in err

    def test_all_valid_zones(self):
        for zone in [11, 12, 13, 14, 15, 16]:
            valid, _ = self.v.validate_utm_zone(zone)
            assert valid is True


class TestValidateFieldName:
    """Tests for MexicoCNHValidator.validate_field_name."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_empty(self):
        valid, err = self.v.validate_field_name("")
        assert valid is False

    def test_none(self):
        valid, err = self.v.validate_field_name(None)
        assert valid is False

    def test_too_short(self):
        valid, err = self.v.validate_field_name("A")
        assert valid is False

    def test_too_long(self):
        valid, err = self.v.validate_field_name("X" * 101)
        assert valid is False

    def test_numeric_only(self):
        valid, err = self.v.validate_field_name("12345")
        assert valid is False
        assert "numeric only" in err.lower()

    def test_valid(self):
        valid, err = self.v.validate_field_name("Cantarell")
        assert valid is True


class TestValidateContractId:
    """Tests for MexicoCNHValidator.validate_contract_id."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_empty(self):
        valid, err = self.v.validate_contract_id("")
        assert valid is False

    def test_none(self):
        valid, err = self.v.validate_contract_id(None)
        assert valid is False

    def test_valid_cnh_format(self):
        valid, err = self.v.validate_contract_id("CNH-R01-L01-A1/2015")
        assert valid is True

    def test_invalid_round(self):
        valid, err = self.v.validate_contract_id("CNH-R99-L01-A1/2015")
        assert valid is False
        assert "Invalid contract round" in err

    def test_non_cnh_prefix_accepted(self):
        # Non-CNH prefix contracts are logged as debug but accepted
        valid, err = self.v.validate_contract_id("CUSTOM-CONTRACT-123")
        assert valid is True

    def test_migration_contract(self):
        valid, err = self.v.validate_contract_id("CNH-MIG-001")
        assert valid is True

    def test_assignment_contract(self):
        valid, err = self.v.validate_contract_id("CNH-ASG-001")
        assert valid is True


class TestValidateHydrocarbonType:
    """Tests for MexicoCNHValidator.validate_hydrocarbon_type."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_empty(self):
        valid, err = self.v.validate_hydrocarbon_type("")
        assert valid is False

    def test_none(self):
        valid, err = self.v.validate_hydrocarbon_type(None)
        assert valid is False

    def test_valid_aceite(self):
        valid, err = self.v.validate_hydrocarbon_type("aceite")
        assert valid is True

    def test_valid_gas_asociado(self):
        valid, err = self.v.validate_hydrocarbon_type("gas_asociado")
        assert valid is True

    def test_with_spaces(self):
        valid, err = self.v.validate_hydrocarbon_type("gas asociado")
        assert valid is True

    def test_invalid(self):
        valid, err = self.v.validate_hydrocarbon_type("diesel")
        assert valid is False
        assert "Invalid hydrocarbon type" in err

    def test_case_insensitive(self):
        valid, err = self.v.validate_hydrocarbon_type("ACEITE")
        assert valid is True


class TestValidateProductionVolume:
    """Tests for MexicoCNHValidator.validate_production_volume."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_none_is_optional(self):
        valid, err = self.v.validate_production_volume(None)
        assert valid is True

    def test_valid(self):
        valid, err = self.v.validate_production_volume(1000.0)
        assert valid is True

    def test_negative(self):
        valid, err = self.v.validate_production_volume(-100.0)
        assert valid is False
        assert "negative" in err.lower()

    def test_exceeds_max(self):
        valid, err = self.v.validate_production_volume(600000)
        assert valid is False
        assert "exceeds" in err.lower()

    def test_custom_max(self):
        valid, err = self.v.validate_production_volume(200, max_daily=100)
        assert valid is False

    def test_invalid_format(self):
        valid, err = self.v.validate_production_volume("abc")
        assert valid is False

    def test_zero(self):
        valid, err = self.v.validate_production_volume(0.0)
        assert valid is True


class TestValidateDateRange:
    """Tests for MexicoCNHValidator.validate_date_range."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_empty(self):
        valid, err = self.v.validate_date_range("")
        assert valid is False

    def test_none(self):
        valid, err = self.v.validate_date_range(None)
        assert valid is False

    def test_iso_format(self):
        valid, err = self.v.validate_date_range("2020-06-15")
        assert valid is True

    def test_mexican_format(self):
        valid, err = self.v.validate_date_range("15/06/2020")
        assert valid is True

    def test_compact_format(self):
        valid, err = self.v.validate_date_range("20200615")
        assert valid is True

    def test_unparseable(self):
        valid, err = self.v.validate_date_range("not-a-date")
        assert valid is False

    def test_too_old(self):
        valid, err = self.v.validate_date_range("1850-01-01")
        assert valid is False
        assert "outside valid range" in err


class TestValidateWellData:
    """Tests for MexicoCNHValidator.validate_well_data."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_valid_well(self):
        data = {
            "clave_pozo": "AKAL-C-1001",
            "latitude": 19.4,
            "longitude": -92.0,
            "field_name": "Cantarell",
            "total_depth": 5000,
        }
        valid, errors = self.v.validate_well_data(data)
        assert valid is True
        assert errors == []

    def test_invalid_clave(self):
        data = {"clave_pozo": "!@#"}
        valid, errors = self.v.validate_well_data(data)
        assert valid is False
        assert any("Clave" in e for e in errors)

    def test_invalid_coordinates(self):
        data = {"latitude": 5.0, "longitude": -99.0}
        valid, errors = self.v.validate_well_data(data)
        assert valid is False

    def test_depth_out_of_range(self):
        data = {"total_depth": 20000}
        valid, errors = self.v.validate_well_data(data)
        assert valid is False
        assert any("depth" in e.lower() for e in errors)

    def test_invalid_depth_format(self):
        data = {"total_depth": "abc"}
        valid, errors = self.v.validate_well_data(data)
        assert valid is False

    def test_empty_data(self):
        valid, errors = self.v.validate_well_data({})
        assert valid is True

    def test_spanish_keys(self):
        data = {
            "well_key": "AKAL-C-1001",
            "latitud": 19.4,
            "longitud": -92.0,
            "campo": "Cantarell",
            "profundidad_total": 5000,
        }
        valid, errors = self.v.validate_well_data(data)
        assert valid is True

    def test_increments_counters(self):
        self.v.validate_well_data({"latitude": 19.4, "longitude": -92.0})
        self.v.validate_well_data({"latitude": 5.0, "longitude": -92.0})
        assert self.v.validation_count == 2
        assert self.v.error_count == 1


class TestValidateProductionData:
    """Tests for MexicoCNHValidator.validate_production_data."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_valid_production(self):
        data = {
            "oil_production": 1000.0,
            "gas_production": 5000.0,
            "production_date": "2020-06-15",
        }
        valid, errors = self.v.validate_production_data(data)
        assert valid is True

    def test_negative_production(self):
        data = {"oil_production": -100.0}
        valid, errors = self.v.validate_production_data(data)
        assert valid is False

    def test_invalid_date(self):
        data = {"production_date": "not-a-date"}
        valid, errors = self.v.validate_production_data(data)
        assert valid is False

    def test_spanish_keys(self):
        data = {
            "produccion_aceite": 1000.0,
            "fecha_produccion": "2020-06-15",
        }
        valid, errors = self.v.validate_production_data(data)
        assert valid is True

    def test_empty_data(self):
        valid, errors = self.v.validate_production_data({})
        assert valid is True


class TestNormalizeClavePozo:
    """Tests for MexicoCNHValidator.normalize_clave_pozo."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_empty(self):
        assert self.v.normalize_clave_pozo("") is None

    def test_none(self):
        assert self.v.normalize_clave_pozo(None) is None

    def test_uppercase(self):
        result = self.v.normalize_clave_pozo("akal-c-1001")
        assert result == "AKAL-C-1001"

    def test_spaces_to_hyphens(self):
        result = self.v.normalize_clave_pozo("AKAL C 1001")
        assert " " not in result
        assert "-" in result

    def test_underscores_to_hyphens(self):
        result = self.v.normalize_clave_pozo("AKAL_C_1001")
        assert "_" not in result

    def test_multiple_hyphens_collapsed(self):
        result = self.v.normalize_clave_pozo("AKAL--C--1001")
        assert "--" not in result


class TestGetStatistics:
    """Tests for MexicoCNHValidator.get_statistics."""

    def setup_method(self):
        self.v = MexicoCNHValidator()

    def test_initial(self):
        stats = self.v.get_statistics()
        assert stats["validations"] == 0
        assert stats["errors"] == 0

    def test_after_validations(self):
        self.v.validate_well_data({"latitude": 19.4, "longitude": -92.0})
        self.v.validate_well_data({"latitude": 5.0, "longitude": -92.0})
        stats = self.v.get_statistics()
        assert stats["validations"] == 2
        assert stats["errors"] == 1
        assert stats["success_rate"] == 0.5


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_is_valid_clave_pozo_true(self):
        assert is_valid_clave_pozo("AKAL-C-1001") is True

    def test_is_valid_clave_pozo_false(self):
        assert is_valid_clave_pozo("") is False

    def test_is_valid_mexico_coordinates_true(self):
        assert is_valid_mexico_coordinates(19.4, -92.0) is True

    def test_is_valid_mexico_coordinates_false(self):
        assert is_valid_mexico_coordinates(5.0, -92.0) is False

    def test_is_valid_contract_id_true(self):
        assert is_valid_contract_id("CNH-R01-L01-A1/2015") is True

    def test_is_valid_contract_id_false(self):
        assert is_valid_contract_id("") is False
