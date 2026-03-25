"""Tests for well data verification configuration."""

import os
import pytest

from worldenergydata.bsee.analysis.well_data_verification.config import (
    VerificationConfig,
)


class TestVerificationConfigDefaults:
    def test_default_config_path(self):
        c = VerificationConfig()
        assert c.config_path is None

    def test_default_validation_rules(self):
        c = VerificationConfig()
        assert "rules" in c.validation_rules
        assert "quality" in c.validation_rules
        assert "thresholds" in c.validation_rules

    def test_default_audit_settings(self):
        c = VerificationConfig()
        assert c.audit_settings["enabled"] is True
        assert c.audit_settings["storage"] == "file"
        assert c.audit_settings["retention_days"] == 365

    def test_default_report_templates(self):
        c = VerificationConfig()
        assert "pdf" in c.report_templates["formats"]
        assert c.report_templates["include_charts"] is True

    def test_default_workflow_steps(self):
        c = VerificationConfig()
        assert len(c.workflow_steps) == 7
        assert c.workflow_steps[0] == "load_data"
        assert c.workflow_steps[-1] == "generate_report"

    def test_default_performance(self):
        c = VerificationConfig()
        assert c.performance["batch_size"] == 1000
        assert c.performance["parallel_workers"] == 4
        assert c.performance["cache_enabled"] is True


class TestVerificationConfigValidate:
    def test_validate_defaults(self):
        c = VerificationConfig()
        assert c.validate() is True

    def test_validate_missing_rules(self):
        c = VerificationConfig()
        del c.validation_rules["rules"]
        with pytest.raises(ValueError, match="Missing 'rules'"):
            c.validate()

    def test_validate_missing_quality(self):
        c = VerificationConfig()
        del c.validation_rules["quality"]
        with pytest.raises(ValueError, match="Missing 'quality'"):
            c.validate()

    def test_validate_empty_workflow(self):
        c = VerificationConfig()
        c.workflow_steps = []
        with pytest.raises(ValueError, match="Workflow steps cannot be empty"):
            c.validate()

    def test_validate_bad_batch_size(self):
        c = VerificationConfig()
        c.performance["batch_size"] = 0
        with pytest.raises(ValueError, match="Batch size must be positive"):
            c.validate()

    def test_validate_bad_parallel_workers(self):
        c = VerificationConfig()
        c.performance["parallel_workers"] = -1
        with pytest.raises(ValueError, match="Parallel workers must be positive"):
            c.validate()


class TestVerificationConfigAccessors:
    def test_get_required_fields(self):
        c = VerificationConfig()
        fields = c.get_required_fields()
        assert "WELL_ID" in fields
        assert "PRODUCTION_DATE" in fields

    def test_get_anomaly_threshold(self):
        c = VerificationConfig()
        assert c.get_anomaly_threshold() == 3.0

    def test_get_production_limits_oil(self):
        c = VerificationConfig()
        limits = c.get_production_limits("oil")
        assert limits["min"] == 0
        assert limits["max"] == 100000
        assert limits["unit"] == "bbl/day"

    def test_get_production_limits_gas(self):
        c = VerificationConfig()
        limits = c.get_production_limits("gas")
        assert limits["max"] == 1000000

    def test_get_production_limits_water(self):
        c = VerificationConfig()
        limits = c.get_production_limits("water")
        assert limits["max"] == 50000

    def test_get_production_limits_unknown(self):
        c = VerificationConfig()
        assert c.get_production_limits("nitrogen") == {}

    def test_to_dict(self):
        c = VerificationConfig()
        d = c.to_dict()
        assert "validation_rules" in d
        assert "audit_settings" in d
        assert "report_templates" in d
        assert "workflow_steps" in d
        assert "performance" in d


class TestVerificationConfigIO:
    def test_save_and_load(self, tmp_path):
        c = VerificationConfig()
        path = str(tmp_path / "test_config.yaml")
        c.save_to_file(path)

        c2 = VerificationConfig()
        c2.load_from_file(path)
        assert c2.workflow_steps == c.workflow_steps

    def test_load_nonexistent_file(self):
        c = VerificationConfig()
        c.load_from_file("/nonexistent/path/config.yaml")
        # Should log warning and keep defaults
        assert c.validate() is True

    def test_save_creates_parent_dirs(self, tmp_path):
        c = VerificationConfig()
        path = str(tmp_path / "sub" / "dir" / "config.yaml")
        c.save_to_file(path)
        assert os.path.exists(path)

    def test_round_trip_preserves_custom_values(self, tmp_path):
        c = VerificationConfig()
        c.workflow_steps = ["step1", "step2"]
        c.performance["batch_size"] = 500
        path = str(tmp_path / "config.yaml")
        c.save_to_file(path)

        c2 = VerificationConfig()
        c2.load_from_file(path)
        assert c2.workflow_steps == ["step1", "step2"]
        assert c2.performance["batch_size"] == 500

    def test_post_init_loads_file(self, tmp_path):
        c = VerificationConfig()
        c.workflow_steps = ["custom_step"]
        path = str(tmp_path / "config.yaml")
        c.save_to_file(path)

        c2 = VerificationConfig(config_path=path)
        assert c2.workflow_steps == ["custom_step"]
