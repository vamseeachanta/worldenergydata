"""Tests for email alerting and StatusReporter integration."""
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

from worldenergydata.scheduler.alerting import AlertSender
from worldenergydata.scheduler.jobs.base import JobResult


def _make_job_result(
    name: str,
    status: str = "success",
    records: int = 10,
    error: str | None = None,
) -> JobResult:
    """Create a JobResult for testing."""
    now = datetime(2026, 3, 25, 12, 0, 0)
    return JobResult(
        job_name=name,
        start_time=now,
        end_time=now,
        status=status,
        records_updated=records,
        error_msg=error,
    )


class TestAlertSender:
    """Tests for AlertSender email delivery."""

    @patch("worldenergydata.scheduler.alerting.smtplib.SMTP")
    def test_send_alert_calls_smtp_correctly(self, mock_smtp_class):
        """Test 1: send_alert calls SMTP with correct host/port, starttls, login, send_message."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_pass="secret",
            smtp_port=587,
        )
        sender.send_alert("Test Subject", "Test body")

        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secret")
        mock_server.send_message.assert_called_once()

    @patch("worldenergydata.scheduler.alerting.smtplib.SMTP")
    def test_send_alert_constructs_email_with_subject_and_body(self, mock_smtp_class):
        """Test 2: send_alert constructs email with subject and body as plain text."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_pass="secret",
        )
        sender.send_alert("Alert: failure", "Job X failed")

        # Verify the message object
        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["Subject"] == "Alert: failure"
        assert sent_msg["From"] == "user@example.com"
        assert "user@example.com" in sent_msg["To"]
        # Body should contain the text
        body_payload = sent_msg.get_payload()
        # MIMEMultipart, first part is text
        if isinstance(body_payload, list):
            body_text = body_payload[0].get_payload()
        else:
            body_text = body_payload
        assert "Job X failed" in body_text

    @patch("worldenergydata.scheduler.alerting.smtplib.SMTP")
    def test_send_alert_handles_smtp_failure_gracefully(self, mock_smtp_class):
        """Test 3: AlertSender gracefully handles SMTP connection failure."""
        mock_smtp_class.side_effect = ConnectionRefusedError("Connection refused")

        sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_pass="secret",
        )
        # Should NOT raise
        sender.send_alert("Test", "body")

    def test_alert_sender_noop_when_smtp_not_configured(self):
        """Test 7: AlertSender is no-op when SMTP config is missing."""
        sender = AlertSender(smtp_host=None, smtp_user=None, smtp_pass=None)
        assert sender.enabled is False

        # Should NOT raise, should be silent (log only)
        with patch("worldenergydata.scheduler.alerting.smtplib.SMTP") as mock_smtp:
            sender.send_alert("Test", "body")
            mock_smtp.assert_not_called()


class TestCheckAndAlert:
    """Tests for StatusReporter.check_and_alert integration."""

    @patch("worldenergydata.scheduler.alerting.smtplib.SMTP")
    def test_alert_on_failed_jobs(self, mock_smtp_class):
        """Test 4: check_and_alert fires alert for each failed job."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        from worldenergydata.scheduler.monitor import StatusReporter

        reporter = StatusReporter(status_file="/tmp/test_status.json")
        alert_sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_pass="secret",
        )

        results = [
            _make_job_result("sodir_refresh", status="failure", error="Timeout"),
            _make_job_result("bsee_refresh", status="success"),
        ]

        reporter.check_and_alert(results, alert_sender)

        # Should have at least one call for failure alert
        subjects = [
            c[0][0]["Subject"]
            for c in mock_server.send_message.call_args_list
            if "FAILED" in c[0][0]["Subject"]
        ]
        assert any("sodir_refresh" in s for s in subjects)

    @patch("worldenergydata.scheduler.alerting.smtplib.SMTP")
    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_alert_on_stale_jobs(self, mock_dt, mock_smtp_class):
        """Test 5: check_and_alert fires alert for each stale job."""
        from datetime import timedelta

        frozen_now = datetime(2026, 3, 25, 12, 0, 0)
        mock_dt.now.return_value = frozen_now
        mock_dt.fromisoformat = datetime.fromisoformat

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        from worldenergydata.scheduler.monitor import StatusReporter

        reporter = StatusReporter(status_file="/tmp/test_status_stale.json")
        alert_sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_pass="secret",
        )

        # All jobs succeed but SODIR is stale (40 hours ago, threshold 36h)
        results = [
            _make_job_result("sodir_refresh", status="success"),
            _make_job_result("bsee_refresh", status="success"),
            _make_job_result("eia_us_refresh", status="success"),
        ]
        # Override start_time to be 40 hours ago for sodir
        results[0] = JobResult(
            job_name="sodir_refresh",
            start_time=frozen_now - timedelta(hours=40),
            end_time=frozen_now - timedelta(hours=40),
            status="success",
            records_updated=10,
            error_msg=None,
        )

        reporter.check_and_alert(results, alert_sender)

        # Should have a staleness alert for sodir_refresh
        subjects = [
            c[0][0]["Subject"]
            for c in mock_server.send_message.call_args_list
            if "STALE" in c[0][0]["Subject"]
        ]
        assert any("sodir_refresh" in s for s in subjects)

    @patch("worldenergydata.scheduler.alerting.smtplib.SMTP")
    def test_no_alert_on_partial_success(self, mock_smtp_class):
        """Test 6: No alert for jobs with status=success and records_updated=0 (D-16)."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        from worldenergydata.scheduler.monitor import StatusReporter

        reporter = StatusReporter(status_file="/tmp/test_status_partial.json")
        alert_sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_pass="secret",
        )

        # All recent, all success — one with 0 records (partial success)
        results = [
            _make_job_result("sodir_refresh", status="success", records=0),
            _make_job_result("bsee_refresh", status="success", records=100),
            _make_job_result("eia_us_refresh", status="success", records=50),
        ]

        reporter.check_and_alert(results, alert_sender)

        # No failure alerts should fire (partial success = 0 records with success status)
        failure_subjects = [
            c[0][0]["Subject"]
            for c in mock_server.send_message.call_args_list
            if "FAILED" in c[0][0]["Subject"]
        ]
        assert len(failure_subjects) == 0
