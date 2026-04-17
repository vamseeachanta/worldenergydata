"""Tests for SODIR field processor."""

from worldenergydata.sodir.processors.field_processor import FieldProcessor


class TestFieldProcessorInit:
    def test_initial_counts(self):
        fp = FieldProcessor()
        assert fp.processed_count == 0
        assert fp.error_count == 0

    def test_constants(self):
        assert FieldProcessor.SM3_TO_BARRELS == 6.29
        assert FieldProcessor.BILLION_SM3_TO_BCF == 35.3


class TestNormalizeFieldStatus:
    def test_producing(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("PRODUCING") == "PRODUCING"

    def test_production_maps_to_producing(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("PRODUCTION") == "PRODUCING"

    def test_shut_down(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("SHUT DOWN") == "SHUT_DOWN"

    def test_shutdown(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("SHUTDOWN") == "SHUT_DOWN"

    def test_closed(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("CLOSED") == "SHUT_DOWN"

    def test_pdo_approved(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("PDO APPROVED") == "PDO_APPROVED"

    def test_planning(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("PLANNING") == "PLANNING_PHASE"

    def test_discovery(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("DISCOVERY") == "DISCOVERY"

    def test_abandoned(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("ABANDONED") == "ABANDONED"

    def test_none_returns_unknown(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status(None) == "UNKNOWN"

    def test_empty_returns_unknown(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("") == "UNKNOWN"

    def test_partial_match_producing(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("In Production Phase") == "PRODUCING"

    def test_partial_match_shut(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("Shut down for maintenance") == "SHUT_DOWN"

    def test_partial_match_planning(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("In planning") == "PLANNING_PHASE"

    def test_unknown_status(self):
        fp = FieldProcessor()
        assert fp.normalize_field_status("xyz") == "UNKNOWN"


class TestConvertToMmbbl:
    def test_none(self):
        fp = FieldProcessor()
        assert fp._convert_to_mmbbl(None) is None

    def test_valid_value(self):
        fp = FieldProcessor()
        result = fp._convert_to_mmbbl(10.0)
        assert result == round(10.0 * 6.29, 2)

    def test_zero(self):
        fp = FieldProcessor()
        assert fp._convert_to_mmbbl(0) == 0

    def test_string_value(self):
        fp = FieldProcessor()
        result = fp._convert_to_mmbbl("5.0")
        assert result == round(5.0 * 6.29, 2)

    def test_invalid_string(self):
        fp = FieldProcessor()
        assert fp._convert_to_mmbbl("abc") is None


class TestConvertToBcf:
    def test_none(self):
        fp = FieldProcessor()
        assert fp._convert_to_bcf(None) is None

    def test_valid_value(self):
        fp = FieldProcessor()
        result = fp._convert_to_bcf(1.0)
        assert result == round(1.0 * 35.3, 2)

    def test_zero(self):
        fp = FieldProcessor()
        assert fp._convert_to_bcf(0) == 0

    def test_invalid_string(self):
        fp = FieldProcessor()
        assert fp._convert_to_bcf("abc") is None


class TestSafeFloat:
    def test_none(self):
        fp = FieldProcessor()
        assert fp._safe_float(None) is None

    def test_valid_number(self):
        fp = FieldProcessor()
        assert fp._safe_float(3.14) == 3.14

    def test_string_number(self):
        fp = FieldProcessor()
        assert fp._safe_float("3.14") == 3.14

    def test_invalid(self):
        fp = FieldProcessor()
        assert fp._safe_float("abc") is None

    def test_integer(self):
        fp = FieldProcessor()
        assert fp._safe_float(5) == 5.0


class TestSafeInt:
    def test_none(self):
        fp = FieldProcessor()
        assert fp._safe_int(None) is None

    def test_valid_int(self):
        fp = FieldProcessor()
        assert fp._safe_int(42) == 42

    def test_string_int(self):
        fp = FieldProcessor()
        assert fp._safe_int("42") == 42

    def test_invalid(self):
        fp = FieldProcessor()
        assert fp._safe_int("abc") is None


class TestParseDate:
    def test_none(self):
        fp = FieldProcessor()
        assert fp._parse_date(None) is None

    def test_empty(self):
        fp = FieldProcessor()
        assert fp._parse_date("") is None

    def test_iso_format(self):
        fp = FieldProcessor()
        assert fp._parse_date("2024-01-15") == "2024-01-15"

    def test_slash_format(self):
        fp = FieldProcessor()
        result = fp._parse_date("15/01/2024")
        assert result == "2024-01-15"

    def test_dot_format(self):
        fp = FieldProcessor()
        result = fp._parse_date("15.01.2024")
        assert result == "2024-01-15"

    def test_compact_format(self):
        fp = FieldProcessor()
        result = fp._parse_date("20240115")
        assert result == "2024-01-15"

    def test_unknown_format_returns_as_is(self):
        fp = FieldProcessor()
        result = fp._parse_date("Jan 2024")
        assert result == "Jan 2024"


class TestCalculateRecoveryFactor:
    def test_normal_case(self):
        fp = FieldProcessor()
        # 100 original, 30 remaining -> 70% recovery
        result = fp._calculate_recovery_factor(100.0, 30.0)
        assert result == 0.7

    def test_zero_original(self):
        fp = FieldProcessor()
        assert fp._calculate_recovery_factor(0, 0) is None

    def test_none_original(self):
        fp = FieldProcessor()
        assert fp._calculate_recovery_factor(None, 50) is None

    def test_none_remaining(self):
        fp = FieldProcessor()
        assert fp._calculate_recovery_factor(100, None) is None

    def test_remaining_exceeds_original(self):
        fp = FieldProcessor()
        assert fp._calculate_recovery_factor(100, 150) is None

    def test_fully_depleted(self):
        fp = FieldProcessor()
        assert fp._calculate_recovery_factor(100, 0) == 1.0


class TestValidate:
    def test_valid_minimal(self):
        fp = FieldProcessor()
        valid, errors = fp.validate({"fldName": "Ekofisk"})
        assert valid is True
        assert errors == []

    def test_missing_name(self):
        fp = FieldProcessor()
        valid, errors = fp.validate({})
        assert valid is False
        assert any("fldName" in e for e in errors)

    def test_negative_reserves(self):
        fp = FieldProcessor()
        valid, errors = fp.validate(
            {
                "fldName": "Test",
                "fldOriginalReservesOil": -10,
            }
        )
        assert valid is False
        assert any("Negative" in e for e in errors)

    def test_invalid_numeric_reserves(self):
        fp = FieldProcessor()
        valid, errors = fp.validate(
            {
                "fldName": "Test",
                "fldOriginalReservesOil": "not_a_number",
            }
        )
        assert valid is False
        assert any("Invalid numeric" in e for e in errors)

    def test_remaining_exceeds_original(self):
        fp = FieldProcessor()
        valid, errors = fp.validate(
            {
                "fldName": "Test",
                "fldOriginalReservesOil": 100,
                "fldRemainingReservesOil": 200,
            }
        )
        assert valid is False
        assert any("exceed" in e for e in errors)

    def test_invalid_year(self):
        fp = FieldProcessor()
        valid, errors = fp.validate(
            {
                "fldName": "Test",
                "fldDiscoveryYear": 1800,
            }
        )
        assert valid is False
        assert any("Invalid year" in e for e in errors)

    def test_production_before_discovery(self):
        fp = FieldProcessor()
        valid, errors = fp.validate(
            {
                "fldName": "Test",
                "fldDiscoveryYear": 2000,
                "fldProductionStartYear": 1990,
            }
        )
        assert valid is False
        assert any("before discovery" in e for e in errors)

    def test_cessation_before_production(self):
        fp = FieldProcessor()
        valid, errors = fp.validate(
            {
                "fldName": "Test",
                "fldProductionStartYear": 2010,
                "fldCessationYear": 2005,
            }
        )
        assert valid is False
        assert any("before production" in e for e in errors)


class TestProcess:
    def test_basic_field(self):
        fp = FieldProcessor()
        result = fp.process(
            {
                "fldName": "Ekofisk",
                "fldNpdidField": 12345,
                "fldStatus": "PRODUCING",
                "fldOperatorName": "ConocoPhillips",
            }
        )
        assert result is not None
        assert result["field_name"] == "Ekofisk"
        assert result["field_id"] == 12345
        assert result["status"] == "PRODUCING"
        assert result["source"] == "SODIR"

    def test_process_with_reserves(self):
        fp = FieldProcessor()
        result = fp.process(
            {
                "fldName": "Test",
                "fldOriginalReservesOil": 10.0,
                "fldRemainingReservesOil": 3.0,
            }
        )
        assert result is not None
        assert result["original_reserves_oil_mmbbl"] == round(10.0 * 6.29, 2)
        assert result["remaining_reserves_oil_mmbbl"] == round(3.0 * 6.29, 2)
        assert result["recovery_factor_oil"] == 0.7

    def test_process_increments_count(self):
        fp = FieldProcessor()
        fp.process({"fldName": "Test"})
        assert fp.processed_count == 1

    def test_process_empty_data(self):
        fp = FieldProcessor()
        result = fp.process({})
        assert result is not None
        assert result["field_name"] == ""


class TestProcessBatch:
    def test_batch(self):
        fp = FieldProcessor()
        fields = [
            {"fldName": "Field1"},
            {"fldName": "Field2"},
        ]
        results = fp.process_batch(fields)
        assert len(results) == 2

    def test_batch_empty(self):
        fp = FieldProcessor()
        assert fp.process_batch([]) == []


class TestGetStatistics:
    def test_initial_stats(self):
        fp = FieldProcessor()
        stats = fp.get_statistics()
        assert stats["processed"] == 0
        assert stats["errors"] == 0
        assert stats["success_rate"] == 0

    def test_after_processing(self):
        fp = FieldProcessor()
        fp.process({"fldName": "Test"})
        stats = fp.get_statistics()
        assert stats["processed"] == 1
        assert stats["success_rate"] == 1.0
