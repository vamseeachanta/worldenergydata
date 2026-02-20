"""Tests for scheduler config loader and validation."""
import pytest
import yaml
import tempfile
import os
from pathlib import Path

from worldenergydata.scheduler.config import SchedulerConfig, load_config, validate_config


VALID_YAML = """
jobs:
  - name: bsee_refresh
    interval: weekly
    time: "02:00"
    enabled: true
  - name: sodir_refresh
    interval: daily
    time: "03:00"
    enabled: true
  - name: eia_us_refresh
    interval: monthly
    day: 5
    time: "04:00"
    enabled: false
  - name: metocean_refresh
    interval: daily
    time: "01:00"
    enabled: true
    locations:
      - {lat: 28.5, lon: -88.5, name: "GOM"}
      - {lat: 60.0, lon: 2.0, name: "NCS"}

monitoring:
  log_dir: logs/scheduler/
  log_retention_days: 30
  retry_max: 3
  retry_backoff_seconds: 60
  webhook_url: null
  status_file: logs/scheduler/status.json
"""

MISSING_JOBS_YAML = """
monitoring:
  log_dir: logs/scheduler/
"""

INVALID_INTERVAL_YAML = """
jobs:
  - name: bsee_refresh
    interval: hourly
    time: "02:00"
    enabled: true
monitoring:
  log_dir: logs/scheduler/
  log_retention_days: 30
  retry_max: 3
  retry_backoff_seconds: 60
  webhook_url: null
  status_file: logs/scheduler/status.json
"""


def _write_temp_yaml(content: str) -> str:
    """Write YAML content to temp file and return path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(content)
        return f.name


class TestLoadConfig:
    def test_load_valid_config(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            assert isinstance(config, SchedulerConfig)
        finally:
            os.unlink(path)

    def test_load_config_parses_jobs(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            assert len(config.jobs) == 4
        finally:
            os.unlink(path)

    def test_load_config_job_names(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            names = [j["name"] for j in config.jobs]
            assert "bsee_refresh" in names
            assert "sodir_refresh" in names
            assert "eia_us_refresh" in names
            assert "metocean_refresh" in names
        finally:
            os.unlink(path)

    def test_load_config_monitoring_section(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            assert config.monitoring["log_retention_days"] == 30
            assert config.monitoring["retry_max"] == 3
            assert config.monitoring["retry_backoff_seconds"] == 60
        finally:
            os.unlink(path)

    def test_load_config_disabled_job(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            eia = next(j for j in config.jobs if j["name"] == "eia_us_refresh")
            assert eia["enabled"] is False
        finally:
            os.unlink(path)

    def test_load_config_metocean_locations(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            metro = next(j for j in config.jobs if j["name"] == "metocean_refresh")
            assert len(metro["locations"]) == 2
            assert metro["locations"][0]["name"] == "GOM"
        finally:
            os.unlink(path)

    def test_load_config_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yml")

    def test_load_config_missing_jobs_raises(self):
        path = _write_temp_yaml(MISSING_JOBS_YAML)
        try:
            with pytest.raises(ValueError, match="jobs"):
                load_config(path)
        finally:
            os.unlink(path)


class TestValidateConfig:
    def test_validate_valid_config_passes(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            # Should not raise
            validate_config(config)
        finally:
            os.unlink(path)

    def test_validate_invalid_interval_raises(self):
        path = _write_temp_yaml(INVALID_INTERVAL_YAML)
        try:
            config = load_config(path)
            with pytest.raises(ValueError, match="interval"):
                validate_config(config)
        finally:
            os.unlink(path)

    def test_validate_job_missing_name_raises(self):
        yaml_content = """
jobs:
  - interval: daily
    time: "02:00"
    enabled: true
monitoring:
  log_dir: logs/scheduler/
  log_retention_days: 30
  retry_max: 3
  retry_backoff_seconds: 60
  webhook_url: null
  status_file: logs/scheduler/status.json
"""
        path = _write_temp_yaml(yaml_content)
        try:
            with pytest.raises(ValueError, match="name"):
                config = load_config(path)
                validate_config(config)
        finally:
            os.unlink(path)

    def test_validate_retry_max_positive(self):
        """retry_max must be a positive integer."""
        yaml_content = """
jobs:
  - name: bsee_refresh
    interval: daily
    time: "02:00"
    enabled: true
monitoring:
  log_dir: logs/
  log_retention_days: 30
  retry_max: -1
  retry_backoff_seconds: 60
  webhook_url: null
  status_file: logs/scheduler/status.json
"""
        path = _write_temp_yaml(yaml_content)
        try:
            config = load_config(path)
            with pytest.raises(ValueError, match="retry_max"):
                validate_config(config)
        finally:
            os.unlink(path)


class TestSchedulerConfig:
    def test_scheduler_config_get_job_config(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            job_cfg = config.get_job_config("bsee_refresh")
            assert job_cfg is not None
            assert job_cfg["interval"] == "weekly"
        finally:
            os.unlink(path)

    def test_scheduler_config_get_nonexistent_job_returns_none(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            job_cfg = config.get_job_config("nonexistent_job")
            assert job_cfg is None
        finally:
            os.unlink(path)

    def test_scheduler_config_enabled_jobs(self):
        path = _write_temp_yaml(VALID_YAML)
        try:
            config = load_config(path)
            enabled = config.get_enabled_jobs()
            names = [j["name"] for j in enabled]
            assert "bsee_refresh" in names
            assert "eia_us_refresh" not in names  # disabled
        finally:
            os.unlink(path)
