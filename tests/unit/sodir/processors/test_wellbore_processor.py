"""Tests for SODIR wellbore processor."""

from worldenergydata.sodir.processors.wellbore_processor import WellboreProcessor


class TestWellboreProcessorInit:
    def test_initial_counts(self):
        wp = WellboreProcessor()
        assert wp.processed_count == 0
        assert wp.error_count == 0

    def test_constants(self):
        assert WellboreProcessor.METERS_TO_FEET == 3.28084
        assert WellboreProcessor.FEET_TO_METERS == 0.3048


class TestNormalizeWellboreStatus:
    def test_pa(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("P&A") == "PLUGGED_AND_ABANDONED"

    def test_pa_short(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("PA") == "PLUGGED_AND_ABANDONED"

    def test_plugged(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("PLUGGED") == "PLUGGED_AND_ABANDONED"

    def test_drilling(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("DRILLING") == "DRILLING"

    def test_active(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("ACTIVE") == "ACTIVE"

    def test_suspended(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("SUSPENDED") == "SUSPENDED"

    def test_ta(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("TA") == "TEMPORARILY_ABANDONED"

    def test_producing(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("PRODUCING") == "PRODUCING"

    def test_production(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("PRODUCTION") == "PRODUCING"

    def test_injection(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("INJECTION") == "INJECTION"

    def test_closed(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("CLOSED") == "CLOSED"

    def test_none(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status(None) == "UNKNOWN"

    def test_empty(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("") == "UNKNOWN"

    def test_unknown(self):
        wp = WellboreProcessor()
        assert wp.normalize_wellbore_status("xyz") == "UNKNOWN"


class TestNormalizePurpose:
    def test_exploration(self):
        wp = WellboreProcessor()
        assert wp.normalize_purpose("EXPLORATION") == "EXPLORATION"

    def test_appraisal(self):
        wp = WellboreProcessor()
        assert wp.normalize_purpose("APPRAISAL") == "APPRAISAL"

    def test_development(self):
        wp = WellboreProcessor()
        assert wp.normalize_purpose("DEVELOPMENT") == "DEVELOPMENT"

    def test_production(self):
        wp = WellboreProcessor()
        assert wp.normalize_purpose("PRODUCTION") == "PRODUCTION"

    def test_none(self):
        wp = WellboreProcessor()
        assert wp.normalize_purpose(None) == "UNKNOWN"

    def test_case_insensitive(self):
        wp = WellboreProcessor()
        assert wp.normalize_purpose("exploration") == "EXPLORATION"


class TestMetersToFeet:
    def test_conversion(self):
        wp = WellboreProcessor()
        result = wp.meters_to_feet(100)
        assert result == round(100 * 3.28084, 2)

    def test_none(self):
        wp = WellboreProcessor()
        assert wp.meters_to_feet(None) is None

    def test_zero(self):
        wp = WellboreProcessor()
        assert wp.meters_to_feet(0) == 0

    def test_string(self):
        wp = WellboreProcessor()
        result = wp.meters_to_feet("100")
        assert result == round(100 * 3.28084, 2)


class TestFeetToMeters:
    def test_conversion(self):
        wp = WellboreProcessor()
        result = wp.feet_to_meters(328.084)
        assert abs(result - 100.0) < 0.1

    def test_none(self):
        wp = WellboreProcessor()
        assert wp.feet_to_meters(None) is None

    def test_zero(self):
        wp = WellboreProcessor()
        assert wp.feet_to_meters(0) == 0


class TestCelsiusToFahrenheit:
    def test_zero(self):
        wp = WellboreProcessor()
        assert wp.celsius_to_fahrenheit(0) == 32.0

    def test_boiling(self):
        wp = WellboreProcessor()
        assert wp.celsius_to_fahrenheit(100) == 212.0

    def test_body_temp(self):
        wp = WellboreProcessor()
        assert wp.celsius_to_fahrenheit(37) == 98.6


class TestCalculateDuration:
    def test_valid(self):
        wp = WellboreProcessor()
        result = wp._calculate_duration("2024-01-01", "2024-01-31")
        assert result == 30

    def test_same_day(self):
        wp = WellboreProcessor()
        assert wp._calculate_duration("2024-01-01", "2024-01-01") == 0

    def test_invalid(self):
        wp = WellboreProcessor()
        assert wp._calculate_duration("bad", "date") is None


class TestIsValidWellboreName:
    def test_valid_simple(self):
        wp = WellboreProcessor()
        assert wp._is_valid_wellbore_name("35/11-1") is True

    def test_valid_with_sidetrack(self):
        wp = WellboreProcessor()
        assert wp._is_valid_wellbore_name("35/11-1 S") is True

    def test_invalid_format(self):
        wp = WellboreProcessor()
        assert wp._is_valid_wellbore_name("Test Well") is False

    def test_empty(self):
        wp = WellboreProcessor()
        assert wp._is_valid_wellbore_name("") is False


class TestValidate:
    def test_valid_minimal(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({"wlbName": "35/11-1"})
        assert valid is True
        assert errors == []

    def test_missing_name(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({})
        assert valid is False
        assert any("wlbName" in e for e in errors)

    def test_invalid_name_format(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({"wlbName": "bad name"})
        assert valid is False
        assert any("Invalid wellbore name" in e for e in errors)

    def test_negative_depth(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({"wlbName": "35/11-1", "wlbTotalDepth": -100})
        assert valid is False
        assert any("negative" in e.lower() for e in errors)

    def test_excessive_depth(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({"wlbName": "35/11-1", "wlbTotalDepth": 20000})
        assert valid is False
        assert any("15km" in e for e in errors)

    def test_latitude_outside_norway(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({"wlbName": "35/11-1", "wlbNsDecDeg": 40.0})
        assert valid is False
        assert any("outside Norwegian" in e for e in errors)

    def test_longitude_outside_norway(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({"wlbName": "35/11-1", "wlbEwDecDeg": 50.0})
        assert valid is False
        assert any("outside Norwegian" in e for e in errors)

    def test_valid_coordinates(self):
        wp = WellboreProcessor()
        valid, errors = wp.validate({
            "wlbName": "35/11-1",
            "wlbNsDecDeg": 60.0,
            "wlbEwDecDeg": 5.0,
        })
        assert valid is True


class TestProcess:
    def test_basic_wellbore(self):
        wp = WellboreProcessor()
        result = wp.process({
            "wlbName": "35/11-1",
            "wlbNpdidWellbore": 12345,
            "wlbStatus": "P&A",
            "wlbPurpose": "EXPLORATION",
            "wlbTotalDepth": 3000,
        })
        assert result is not None
        assert result["wellbore_name"] == "35/11-1"
        assert result["status_normalized"] == "PLUGGED_AND_ABANDONED"
        assert result["purpose_normalized"] == "EXPLORATION"
        assert result["total_depth_m"] == 3000
        assert result["total_depth_ft"] == round(3000 * 3.28084, 2)
        assert result["source"] == "SODIR"

    def test_process_with_temperature(self):
        wp = WellboreProcessor()
        result = wp.process({
            "wlbName": "35/11-1",
            "wlbBottomHoleTemperature": 120,
        })
        assert result is not None
        assert result["bottom_hole_temperature_c"] == 120
        assert result["bottom_hole_temperature_f"] == 248.0

    def test_process_with_drilling_dates(self):
        wp = WellboreProcessor()
        result = wp.process({
            "wlbName": "35/11-1",
            "wlbDrillingStartDate": "2024-01-01",
            "wlbDrillingEndDate": "2024-02-01",
        })
        assert result is not None
        assert result["drilling_duration_days"] == 31

    def test_process_increments_count(self):
        wp = WellboreProcessor()
        wp.process({"wlbName": "35/11-1"})
        assert wp.processed_count == 1


class TestProcessBatch:
    def test_batch(self):
        wp = WellboreProcessor()
        results = wp.process_batch([
            {"wlbName": "35/11-1"},
            {"wlbName": "35/11-2"},
        ])
        assert len(results) == 2

    def test_batch_empty(self):
        wp = WellboreProcessor()
        assert wp.process_batch([]) == []


class TestGetStatistics:
    def test_initial(self):
        wp = WellboreProcessor()
        stats = wp.get_statistics()
        assert stats["processed"] == 0

    def test_after_processing(self):
        wp = WellboreProcessor()
        wp.process({"wlbName": "35/11-1"})
        stats = wp.get_statistics()
        assert stats["processed"] == 1
        assert stats["success_rate"] == 1.0
