"""Tests for SODIR discovery processor."""

from worldenergydata.sodir.processors.discovery_processor import DiscoveryProcessor


class TestDiscoveryProcessorInit:
    def test_initial_counts(self):
        dp = DiscoveryProcessor()
        assert dp.processed_count == 0
        assert dp.error_count == 0

    def test_constants(self):
        assert DiscoveryProcessor.SM3_TO_BARRELS == 6.29
        assert DiscoveryProcessor.BILLION_SM3_TO_BCF == 35.3


class TestNormalizeHcType:
    def test_oil(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("OIL") == "OIL"

    def test_gas(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("GAS") == "GAS"

    def test_gas_condensate_slash(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("GAS/CONDENSATE") == "GAS_CONDENSATE"

    def test_gas_condensate_space(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("GAS CONDENSATE") == "GAS_CONDENSATE"

    def test_condensate(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("CONDENSATE") == "CONDENSATE"

    def test_oil_gas(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("OIL/GAS") == "OIL_GAS"

    def test_none_returns_unknown(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type(None) == "UNKNOWN"

    def test_empty_returns_unknown(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("") == "UNKNOWN"

    def test_case_insensitive(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("oil") == "OIL"

    def test_partial_oil_gas(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("Oil and Gas bearing") == "OIL_GAS"

    def test_partial_condensate(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("Rich Gas Condensate") == "GAS_CONDENSATE"

    def test_unknown_type(self):
        dp = DiscoveryProcessor()
        assert dp.normalize_hc_type("xyz") == "UNKNOWN"


class TestClassifyDiscoverySize:
    def test_small(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(5) == "SMALL"

    def test_medium(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(25) == "MEDIUM"

    def test_large(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(100) == "LARGE"

    def test_giant(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(300) == "GIANT"

    def test_boundary_small_medium(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(10) == "MEDIUM"

    def test_boundary_medium_large(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(50) == "LARGE"

    def test_boundary_large_giant(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(200) == "GIANT"

    def test_zero(self):
        dp = DiscoveryProcessor()
        assert dp.classify_discovery_size(0) == "SMALL"


class TestCalculateOilEquivalent:
    def test_oil_only(self):
        dp = DiscoveryProcessor()
        result = dp._calculate_oil_equivalent(10.0, None, None, None)
        assert result == round(10.0 * 6.29, 2)

    def test_gas_only(self):
        dp = DiscoveryProcessor()
        result = dp._calculate_oil_equivalent(None, 5.0, None, None)
        assert result == round(5.0 * 6.29, 2)

    def test_all_types(self):
        dp = DiscoveryProcessor()
        result = dp._calculate_oil_equivalent(10.0, 5.0, 2.0, 1.0)
        expected = round((10.0 + 5.0 + 2.0 + 1.0) * 6.29, 2)
        assert result == expected

    def test_all_none(self):
        dp = DiscoveryProcessor()
        result = dp._calculate_oil_equivalent(None, None, None, None)
        assert result == 0.0

    def test_zero_values(self):
        dp = DiscoveryProcessor()
        result = dp._calculate_oil_equivalent(0, 0, 0, 0)
        assert result == 0.0


class TestAssessCommerciality:
    def test_has_field_name(self):
        dp = DiscoveryProcessor()
        data = {"field_name": "Ekofisk"}
        assert dp._assess_commerciality(data) is True

    def test_large_oil_equivalent(self):
        dp = DiscoveryProcessor()
        data = {"oil_equivalent_mmbbl": 50}
        assert dp._assess_commerciality(data) is True

    def test_small_oil_equivalent(self):
        dp = DiscoveryProcessor()
        data = {"oil_equivalent_mmbbl": 5, "discovery_status": ""}
        assert dp._assess_commerciality(data) is False

    def test_development_status(self):
        dp = DiscoveryProcessor()
        data = {"discovery_status": "Under Development"}
        assert dp._assess_commerciality(data) is True

    def test_producing_status(self):
        dp = DiscoveryProcessor()
        data = {"discovery_status": "Producing"}
        assert dp._assess_commerciality(data) is True

    def test_no_indicators(self):
        dp = DiscoveryProcessor()
        data = {"discovery_status": "Abandoned"}
        assert dp._assess_commerciality(data) is False


class TestValidate:
    def test_valid_with_resources(self):
        dp = DiscoveryProcessor()
        valid, errors = dp.validate({
            "dscName": "TestDisc",
            "dscRecoverableOil": 10.0,
        })
        assert valid is True
        assert errors == []

    def test_missing_name(self):
        dp = DiscoveryProcessor()
        valid, errors = dp.validate({"dscRecoverableOil": 10.0})
        assert valid is False
        assert any("dscName" in e for e in errors)

    def test_no_resources(self):
        dp = DiscoveryProcessor()
        valid, errors = dp.validate({"dscName": "Test"})
        assert valid is False
        assert any("no resource" in e.lower() for e in errors)

    def test_negative_resources(self):
        dp = DiscoveryProcessor()
        valid, errors = dp.validate({
            "dscName": "Test",
            "dscRecoverableOil": -5,
        })
        assert valid is False
        assert any("Negative" in e for e in errors)

    def test_invalid_year(self):
        dp = DiscoveryProcessor()
        valid, errors = dp.validate({
            "dscName": "Test",
            "dscRecoverableOil": 10.0,
            "dscDiscoveryYear": 1900,
        })
        assert valid is False
        assert any("Invalid discovery year" in e for e in errors)


class TestProcess:
    def test_basic_discovery(self):
        dp = DiscoveryProcessor()
        result = dp.process({
            "dscName": "TestDisc",
            "dscNpdidDiscovery": 12345,
            "dscHcType": "OIL",
            "dscRecoverableOil": 10.0,
        })
        assert result is not None
        assert result["discovery_name"] == "TestDisc"
        assert result["discovery_id"] == 12345
        assert result["hydrocarbon_type"] == "OIL"
        assert result["source"] == "SODIR"
        assert result["is_commercial"] is not None

    def test_process_increments_count(self):
        dp = DiscoveryProcessor()
        dp.process({"dscName": "Test", "dscStatus": ""})
        assert dp.processed_count == 1

    def test_process_batch(self):
        dp = DiscoveryProcessor()
        results = dp.process_batch([
            {"dscName": "D1", "dscStatus": ""},
            {"dscName": "D2", "dscStatus": ""},
        ])
        assert len(results) == 2

    def test_process_batch_empty(self):
        dp = DiscoveryProcessor()
        assert dp.process_batch([]) == []


class TestConversions:
    def test_convert_to_mmbbl(self):
        dp = DiscoveryProcessor()
        assert dp._convert_to_mmbbl(10.0) == round(10.0 * 6.29, 2)

    def test_convert_to_mmbbl_none(self):
        dp = DiscoveryProcessor()
        assert dp._convert_to_mmbbl(None) is None

    def test_convert_to_bcf(self):
        dp = DiscoveryProcessor()
        assert dp._convert_to_bcf(1.0) == round(1.0 * 35.3, 2)

    def test_convert_to_bcf_none(self):
        dp = DiscoveryProcessor()
        assert dp._convert_to_bcf(None) is None


class TestGetStatistics:
    def test_initial(self):
        dp = DiscoveryProcessor()
        stats = dp.get_statistics()
        assert stats["processed"] == 0
        assert stats["errors"] == 0

    def test_after_processing(self):
        dp = DiscoveryProcessor()
        dp.process({"dscName": "Test", "dscStatus": ""})
        stats = dp.get_statistics()
        assert stats["processed"] == 1
        assert stats["success_rate"] == 1.0
