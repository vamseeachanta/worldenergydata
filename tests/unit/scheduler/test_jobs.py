"""Tests for all scheduler job adapters, including LNG terminals."""

from datetime import datetime
from pathlib import Path

import pytest

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob
from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob
from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob
from worldenergydata.scheduler.jobs.lng_terminals_refresh import LngTerminalsRefreshJob
from worldenergydata.scheduler.jobs.metocean_refresh import MetoceanRefreshJob
from worldenergydata.scheduler.jobs.sodir_refresh import SodirRefreshJob
from worldenergydata.scheduler.jobs.ukcs_refresh import UkcsRefreshJob

ALL_JOB_CLASSES = [
    BseeRefreshJob,
    SodirRefreshJob,
    EiaUsRefreshJob,
    BrazilAnpRefreshJob,
    UkcsRefreshJob,
    MetoceanRefreshJob,
    LngTerminalsRefreshJob,
]

ALL_JOB_NAMES = [
    "bsee_refresh",
    "sodir_refresh",
    "eia_us_refresh",
    "brazil_anp_refresh",
    "ukcs_refresh",
    "metocean_refresh",
    "lng_terminals_refresh",
]


class TestJobAdapterInterface:
    @pytest.mark.parametrize("JobClass", ALL_JOB_CLASSES)
    def test_job_is_abstract_subclass(self, JobClass):
        assert issubclass(JobClass, AbstractJob)

    @pytest.mark.parametrize(
        "JobClass,expected_name", zip(ALL_JOB_CLASSES, ALL_JOB_NAMES)
    )
    def test_job_has_correct_name(self, JobClass, expected_name):
        job = JobClass()
        assert job.name == expected_name

    @pytest.mark.parametrize("JobClass", ALL_JOB_CLASSES)
    def test_job_run_returns_job_result(self, JobClass):
        job = JobClass()
        result = job.run(config={})
        assert isinstance(result, JobResult)

    @pytest.mark.parametrize("JobClass", ALL_JOB_CLASSES)
    def test_job_run_result_has_valid_status(self, JobClass):
        job = JobClass()
        result = job.run(config={})
        assert result.status in ("success", "failure", "skipped")

    @pytest.mark.parametrize("JobClass", ALL_JOB_CLASSES)
    def test_job_run_result_has_timestamps(self, JobClass):
        job = JobClass()
        before = datetime.now()
        result = job.run(config={})
        after = datetime.now()
        assert result.start_time >= before
        assert result.end_time <= after

    @pytest.mark.parametrize("JobClass", ALL_JOB_CLASSES)
    def test_job_run_records_updated_is_int(self, JobClass):
        job = JobClass()
        result = job.run(config={})
        assert isinstance(result.records_updated, int)

    @pytest.mark.parametrize("JobClass", ALL_JOB_CLASSES)
    def test_job_run_idempotent_no_crash(self, JobClass):
        """Running twice with same config should not raise."""
        job = JobClass()
        result1 = job.run(config={})
        result2 = job.run(config={})
        assert result1.job_name == result2.job_name

    @pytest.mark.parametrize("JobClass", ALL_JOB_CLASSES)
    def test_job_run_empty_config_does_not_crash(self, JobClass):
        """Jobs should handle empty config gracefully."""
        job = JobClass()
        result = job.run(config={})
        assert result is not None

    @pytest.mark.parametrize(
        "JobClass,expected_path",
        [
            (BseeRefreshJob, "data/modules/bsee"),
            (SodirRefreshJob, "data/modules/sodir"),
            (EiaUsRefreshJob, "data/modules/eia"),
            (BrazilAnpRefreshJob, "data/modules/brazil_anp"),
            (UkcsRefreshJob, "data/modules/ukcs"),
            (MetoceanRefreshJob, "data/modules/metocean"),
            (LngTerminalsRefreshJob, "data/modules/lng_terminals"),
        ],
    )
    def test_job_default_output_dir_matches_modules_convention(
        self, JobClass, expected_path
    ):
        assert Path(JobClass.default_output_dir) == Path(expected_path)


class TestMetoceanJobLocations:
    def test_metocean_accepts_locations_in_config(self):
        job = MetoceanRefreshJob()
        config = {
            "locations": [
                {"lat": 28.5, "lon": -88.5, "name": "GOM"},
                {"lat": 60.0, "lon": 2.0, "name": "NCS"},
            ]
        }
        result = job.run(config=config)
        assert isinstance(result, JobResult)

    def test_metocean_empty_locations_does_not_crash(self):
        job = MetoceanRefreshJob()
        result = job.run(config={"locations": []})
        assert result is not None

    def test_metocean_tier2_stub_returns_skipped(self):
        """Tier 2 stub returns skipped status with zero records."""
        job = MetoceanRefreshJob()
        locations = [
            {"lat": 28.5, "lon": -88.5, "name": "GOM"},
            {"lat": 60.0, "lon": 2.0, "name": "NCS"},
        ]
        result = job.run(config={"locations": locations})
        assert result.status == "skipped"
        assert result.records_updated == 0


class TestBseeJobConfig:
    def test_bsee_accepts_data_path_config(self):
        job = BseeRefreshJob()
        result = job.run(config={"data_path": "/tmp/bsee"})
        assert isinstance(result, JobResult)


class TestEiaUsJobConfig:
    def test_eia_accepts_api_key_config(self):
        job = EiaUsRefreshJob()
        result = job.run(config={"api_key": "test_key_123"})
        assert isinstance(result, JobResult)
