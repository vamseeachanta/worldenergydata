"""Tests for SODIR data router module."""

import pytest

from worldenergydata.sodir.data import SodirData

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestSodirDataInit:
    def test_default_init(self):
        sd = SodirData()
        assert sd.config == {}
        assert sd.api_client is None
        assert sd.processors == {}
        assert sd.validator is None
        assert sd.storage is None

    def test_stats_initialized(self):
        sd = SodirData()
        assert sd.stats["collections"] == 0
        assert sd.stats["total_records"] == 0
        assert sd.stats["errors"] == 0
        assert sd.stats["validations_failed"] == 0


# ---------------------------------------------------------------------------
# get_statistics
# ---------------------------------------------------------------------------


class TestGetStatistics:
    def test_initial_stats(self):
        sd = SodirData()
        stats = sd.get_statistics()
        assert stats["collections"] == 0
        assert stats["total_records"] == 0
        assert stats["errors"] == 0
        assert stats["validations_failed"] == 0
        assert stats["success_rate"] == 0.0

    def test_stats_after_increment(self):
        sd = SodirData()
        sd.stats["collections"] = 10
        sd.stats["errors"] = 2
        sd.stats["total_records"] = 100
        stats = sd.get_statistics()
        assert stats["success_rate"] == 0.8

    def test_stats_no_division_by_zero(self):
        sd = SodirData()
        stats = sd.get_statistics()
        # No error with 0 collections
        assert stats["success_rate"] == 0.0


# ---------------------------------------------------------------------------
# validate_* methods (without validator)
# ---------------------------------------------------------------------------


class TestValidateFieldNoValidator:
    def test_returns_valid(self):
        sd = SodirData()
        is_valid, errors = sd.validate_field({"field_name": "Troll"})
        assert is_valid is True
        assert errors == []


class TestValidateDiscoveryNoValidator:
    def test_returns_valid(self):
        sd = SodirData()
        is_valid, errors = sd.validate_discovery({"discovery_name": "Johan Sverdrup"})
        assert is_valid is True
        assert errors == []


class TestValidateSurveyNoValidator:
    def test_returns_valid(self):
        sd = SodirData()
        is_valid, errors = sd.validate_survey({"survey_name": "NPD 2024"})
        assert is_valid is True
        assert errors == []


class TestValidateBlockNoValidator:
    def test_returns_valid(self):
        sd = SodirData()
        is_valid, errors = sd.validate_block({"block_name": "15/3"})
        assert is_valid is True
        assert errors == []

    def test_missing_block_name(self):
        sd = SodirData()
        is_valid, errors = sd.validate_block({})
        assert is_valid is True  # No validator, returns True


class TestValidateWellboreNoValidator:
    def test_returns_valid(self):
        sd = SodirData()
        is_valid, errors = sd.validate_wellbore({"wellbore_name": "15/3-1"})
        assert is_valid is True
        assert errors == []


# ---------------------------------------------------------------------------
# _validate_data (without validator)
# ---------------------------------------------------------------------------


class TestValidateData:
    def test_no_validation_method(self):
        sd = SodirData()
        result = sd._validate_data("unknown_type", [{"id": 1}])
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 0

    def test_known_type_without_validator(self):
        sd = SodirData()
        data = [{"field_name": "Troll"}, {"field_name": "Ekofisk"}]
        result = sd._validate_data("fields", data)
        assert result["valid_count"] == 2
        assert result["invalid_count"] == 0


# ---------------------------------------------------------------------------
# generate_validation_report
# ---------------------------------------------------------------------------


class TestGenerateValidationReport:
    def test_basic(self):
        sd = SodirData()
        data = [{"field_name": "Troll"}]
        report = sd.generate_validation_report(data, "fields")
        assert report["dataset"] == "fields"
        assert report["total_records"] == 1
        assert report["valid_records"] == 1
        assert report["invalid_records"] == 0
        assert report["validation_rate"] == 1.0

    def test_unknown_type(self):
        sd = SodirData()
        report = sd.generate_validation_report([{"a": 1}], "unknown")
        assert report["total_records"] == 1
        assert report["valid_records"] == 1

    def test_empty_data(self):
        sd = SodirData()
        report = sd.generate_validation_report([], "fields")
        assert report["total_records"] == 0
        assert report["validation_rate"] == 0.0


# ---------------------------------------------------------------------------
# collect_dataset (no API)
# ---------------------------------------------------------------------------


class TestCollectDatasetNoAPI:
    def test_no_api_client_raises(self):
        """Without config, collect_dataset tries to initialize components and fails."""
        sd = SodirData()
        # This should try to import api_client and processors
        result = sd.collect_dataset("fields")
        # Should fail gracefully
        assert result["status"] == "failed"
        assert "error" in result
