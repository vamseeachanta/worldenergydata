"""Tests for scheduler base module: JobResult and AbstractJob."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult


class ConcreteJob(AbstractJob):
    """Minimal concrete implementation for testing."""

    name = "test_job"

    def run(self, config: dict) -> JobResult:
        return JobResult(
            job_name=self.name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            status="success",
            records_updated=5,
            error_msg=None,
        )


class FailingJob(AbstractJob):
    name = "failing_job"

    def run(self, config: dict) -> JobResult:
        return JobResult(
            job_name=self.name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            status="failure",
            records_updated=0,
            error_msg="Simulated error",
        )


class TestJobResult:
    def test_job_result_creation_success(self):
        now = datetime.now()
        result = JobResult(
            job_name="bsee_refresh",
            start_time=now,
            end_time=now + timedelta(seconds=5),
            status="success",
            records_updated=100,
            error_msg=None,
        )
        assert result.job_name == "bsee_refresh"
        assert result.status == "success"
        assert result.records_updated == 100
        assert result.error_msg is None

    def test_job_result_creation_failure(self):
        now = datetime.now()
        result = JobResult(
            job_name="sodir_refresh",
            start_time=now,
            end_time=now + timedelta(seconds=1),
            status="failure",
            records_updated=0,
            error_msg="Connection timeout",
        )
        assert result.status == "failure"
        assert result.error_msg == "Connection timeout"
        assert result.records_updated == 0

    def test_job_result_skipped_status(self):
        now = datetime.now()
        result = JobResult(
            job_name="eia_us_refresh",
            start_time=now,
            end_time=now,
            status="skipped",
            records_updated=0,
            error_msg=None,
        )
        assert result.status == "skipped"

    def test_job_result_duration_calculation(self):
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 0, 0, 10)
        result = JobResult(
            job_name="test",
            start_time=start,
            end_time=end,
            status="success",
            records_updated=0,
            error_msg=None,
        )
        duration = (result.end_time - result.start_time).total_seconds()
        assert duration == 10.0

    def test_job_result_is_dataclass(self):
        """JobResult must be a dataclass."""
        import dataclasses

        assert dataclasses.is_dataclass(JobResult)


class TestAbstractJob:
    def test_concrete_job_has_name(self):
        job = ConcreteJob()
        assert job.name == "test_job"

    def test_concrete_job_run_returns_result(self):
        job = ConcreteJob()
        result = job.run({})
        assert isinstance(result, JobResult)
        assert result.status == "success"

    def test_failing_job_returns_failure(self):
        job = FailingJob()
        result = job.run({})
        assert result.status == "failure"
        assert result.error_msg == "Simulated error"

    def test_abstract_job_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            AbstractJob()

    def test_is_due_daily_never_run(self):
        """A job never run is always due."""
        job = ConcreteJob()
        assert job.is_due(last_run=None, interval="daily") is True

    def test_is_due_daily_run_recently(self):
        """A job run 2 hours ago is NOT due for daily interval."""
        job = ConcreteJob()
        last = datetime.now() - timedelta(hours=2)
        assert job.is_due(last_run=last, interval="daily") is False

    def test_is_due_daily_run_over_24h_ago(self):
        """A job run 25 hours ago IS due for daily interval."""
        job = ConcreteJob()
        last = datetime.now() - timedelta(hours=25)
        assert job.is_due(last_run=last, interval="daily") is True

    def test_is_due_weekly_run_6_days_ago(self):
        """A job run 6 days ago is NOT due for weekly interval."""
        job = ConcreteJob()
        last = datetime.now() - timedelta(days=6)
        assert job.is_due(last_run=last, interval="weekly") is False

    def test_is_due_weekly_run_8_days_ago(self):
        """A job run 8 days ago IS due for weekly interval."""
        job = ConcreteJob()
        last = datetime.now() - timedelta(days=8)
        assert job.is_due(last_run=last, interval="weekly") is True

    def test_is_due_monthly_run_25_days_ago(self):
        """A job run 25 days ago is NOT due for monthly interval."""
        job = ConcreteJob()
        last = datetime.now() - timedelta(days=25)
        assert job.is_due(last_run=last, interval="monthly") is False

    def test_is_due_monthly_run_31_days_ago(self):
        """A job run 31 days ago IS due for monthly interval."""
        job = ConcreteJob()
        last = datetime.now() - timedelta(days=31)
        assert job.is_due(last_run=last, interval="monthly") is True

    def test_is_due_unknown_interval_defaults_to_due(self):
        """Unknown interval treats job as due to avoid data staleness."""
        job = ConcreteJob()
        last = datetime.now() - timedelta(hours=1)
        assert job.is_due(last_run=last, interval="unknown") is True
