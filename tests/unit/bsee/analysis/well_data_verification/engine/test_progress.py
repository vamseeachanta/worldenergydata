"""Tests for progress tracking and status reporting."""

from datetime import datetime, timedelta

from worldenergydata.bsee.analysis.well_data_verification.engine.progress import (
    ProgressTracker,
    StepMetrics,
    StepStatus,
)


class TestStepStatus:
    def test_all_statuses(self):
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.IN_PROGRESS.value == "in_progress"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"
        assert StepStatus.CANCELLED.value == "cancelled"

    def test_is_terminal_completed(self):
        assert StepStatus.COMPLETED.is_terminal() is True

    def test_is_terminal_failed(self):
        assert StepStatus.FAILED.is_terminal() is True

    def test_is_terminal_skipped(self):
        assert StepStatus.SKIPPED.is_terminal() is True

    def test_is_terminal_cancelled(self):
        assert StepStatus.CANCELLED.is_terminal() is True

    def test_is_not_terminal_pending(self):
        assert StepStatus.PENDING.is_terminal() is False

    def test_is_not_terminal_in_progress(self):
        assert StepStatus.IN_PROGRESS.is_terminal() is False

    def test_is_successful_completed(self):
        assert StepStatus.COMPLETED.is_successful() is True

    def test_is_successful_skipped(self):
        assert StepStatus.SKIPPED.is_successful() is True

    def test_is_not_successful_failed(self):
        assert StepStatus.FAILED.is_successful() is False

    def test_is_not_successful_pending(self):
        assert StepStatus.PENDING.is_successful() is False


class TestStepMetrics:
    def test_defaults(self):
        m = StepMetrics(step_name="step1")
        assert m.step_name == "step1"
        assert m.status == StepStatus.PENDING
        assert m.start_time is None
        assert m.end_time is None
        assert m.duration_seconds == 0
        assert m.attempts == 0
        assert m.error_count == 0
        assert m.last_error is None

    def test_start(self):
        m = StepMetrics(step_name="step1")
        m.start()
        assert m.status == StepStatus.IN_PROGRESS
        assert m.start_time is not None
        assert m.attempts == 1

    def test_start_multiple_increments_attempts(self):
        m = StepMetrics(step_name="step1")
        m.start()
        m.start()
        assert m.attempts == 2

    def test_complete(self):
        m = StepMetrics(step_name="step1")
        m.start()
        m.complete()
        assert m.status == StepStatus.COMPLETED
        assert m.end_time is not None
        assert m.duration_seconds >= 0

    def test_fail(self):
        m = StepMetrics(step_name="step1")
        m.start()
        m.fail("something broke")
        assert m.status == StepStatus.FAILED
        assert m.error_count == 1
        assert m.last_error == "something broke"
        assert m.end_time is not None

    def test_fail_multiple_increments_count(self):
        m = StepMetrics(step_name="step1")
        m.fail("error 1")
        m.fail("error 2")
        assert m.error_count == 2
        assert m.last_error == "error 2"

    def test_skip(self):
        m = StepMetrics(step_name="step1")
        m.skip()
        assert m.status == StepStatus.SKIPPED
        assert m.end_time is not None


class TestProgressTracker:
    def test_init(self):
        pt = ProgressTracker(total_steps=5)
        assert pt.total_steps == 5
        assert pt.completed_steps == 0
        assert pt.failed_steps == 0
        assert pt.skipped_steps == 0
        assert pt.current_step is None

    def test_start_tracking(self):
        pt = ProgressTracker(total_steps=3)
        pt.start_tracking()
        assert pt.start_time is not None

    def test_mark_step_started(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_step_started("step1")
        assert pt.current_step == "step1"
        assert "step1" in pt.step_metrics
        assert pt.step_metrics["step1"].status == StepStatus.IN_PROGRESS

    def test_mark_step_started_creates_on_first_call(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_step_started("step1")
        assert "step1" in pt.step_order

    def test_mark_completed(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_step_started("step1")
        pt.mark_completed("step1")
        assert pt.completed_steps == 1
        assert pt.current_step is None
        assert pt.step_metrics["step1"].status == StepStatus.COMPLETED

    def test_mark_completed_unknown_step(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_completed("step_new")
        assert pt.completed_steps == 1
        assert "step_new" in pt.step_metrics

    def test_mark_failed(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_step_started("step1")
        pt.mark_failed("step1", "boom")
        assert pt.failed_steps == 1
        assert pt.current_step is None
        assert pt.step_metrics["step1"].status == StepStatus.FAILED

    def test_mark_failed_default_error(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_failed("step1")
        assert pt.step_metrics["step1"].last_error == "Unknown error"

    def test_mark_skipped(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_step_started("step1")
        pt.mark_skipped("step1")
        assert pt.skipped_steps == 1
        assert pt.current_step is None
        assert pt.step_metrics["step1"].status == StepStatus.SKIPPED

    def test_get_percentage_zero_total(self):
        pt = ProgressTracker(total_steps=0)
        assert pt.get_percentage() == 0

    def test_get_percentage_partial(self):
        pt = ProgressTracker(total_steps=4)
        pt.mark_completed("s1")
        pt.mark_skipped("s2")
        # 2 of 4 = 50%
        assert pt.get_percentage() == 50.0

    def test_get_percentage_complete(self):
        pt = ProgressTracker(total_steps=2)
        pt.mark_completed("s1")
        pt.mark_completed("s2")
        assert pt.get_percentage() == 100.0

    def test_get_report_basic(self):
        pt = ProgressTracker(total_steps=3)
        report = pt.get_report()
        assert report["total_steps"] == 3
        assert report["completed_steps"] == 0
        assert report["failed_steps"] == 0
        assert report["skipped_steps"] == 0
        assert report["percentage"] == 0
        assert report["current_step"] is None
        assert report["status"] == "pending"

    def test_get_report_in_progress(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_step_started("s1")
        report = pt.get_report()
        assert report["status"] == "in_progress"

    def test_get_report_completed(self):
        pt = ProgressTracker(total_steps=2)
        pt.mark_completed("s1")
        pt.mark_completed("s2")
        report = pt.get_report()
        assert report["status"] == "completed"

    def test_get_report_failed(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_completed("s1")
        pt.mark_failed("s2", "error")
        report = pt.get_report()
        assert report["status"] == "failed"

    def test_get_report_with_timing(self):
        pt = ProgressTracker(total_steps=3)
        pt.start_tracking()
        pt.mark_step_started("s1")
        pt.mark_completed("s1")
        report = pt.get_report()
        assert "start_time" in report
        assert "elapsed_seconds" in report

    def test_get_report_has_metrics(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_step_started("s1")
        pt.mark_completed("s1")
        report = pt.get_report()
        assert "s1" in report["metrics"]
        assert report["metrics"]["s1"]["status"] == "completed"

    def test_estimate_time_remaining_no_start(self):
        pt = ProgressTracker(total_steps=3)
        assert pt.estimate_time_remaining() is None

    def test_estimate_time_remaining_no_completed(self):
        pt = ProgressTracker(total_steps=3)
        pt.start_tracking()
        assert pt.estimate_time_remaining() is None

    def test_estimate_time_remaining_all_done(self):
        pt = ProgressTracker(total_steps=2)
        pt.start_tracking()
        pt.mark_completed("s1")
        pt.mark_completed("s2")
        assert pt.estimate_time_remaining() == 0

    def test_get_failed_steps(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_failed("s1", "error")
        pt.mark_completed("s2")
        assert pt.get_failed_steps() == ["s1"]

    def test_get_successful_steps(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_completed("s1")
        pt.mark_skipped("s2")
        pt.mark_failed("s3", "error")
        successful = pt.get_successful_steps()
        assert "s1" in successful
        assert "s2" in successful
        assert "s3" not in successful

    def test_format_summary_pending(self):
        pt = ProgressTracker(total_steps=3)
        summary = pt.format_summary()
        assert "0.0%" in summary
        assert "PENDING" in summary

    def test_format_summary_with_failures(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_failed("s1", "something broke")
        summary = pt.format_summary()
        assert "Failed Steps: 1" in summary
        assert "something broke" in summary

    def test_format_summary_with_skipped(self):
        pt = ProgressTracker(total_steps=3)
        pt.mark_skipped("s1")
        summary = pt.format_summary()
        assert "Skipped Steps: 1" in summary

    def test_format_duration_seconds(self):
        pt = ProgressTracker(total_steps=1)
        assert pt._format_duration(30) == "30 seconds"

    def test_format_duration_minutes(self):
        pt = ProgressTracker(total_steps=1)
        assert pt._format_duration(120) == "2.0 minutes"

    def test_format_duration_hours(self):
        pt = ProgressTracker(total_steps=1)
        assert pt._format_duration(7200) == "2.0 hours"
