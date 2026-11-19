"""Credential normalization and reporting use synthetic keys and no I/O."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from worldenergydata.scheduler.jobs.base import JobResult
from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob
from worldenergydata.scheduler.monitor import StatusReporter


@pytest.mark.parametrize("config_key", [None, "", " ", "\t"])
@pytest.mark.parametrize("environment_key", [None, "", " ", "\t"])
def test_blank_credentials_skip_without_output(
    config_key, environment_key, monkeypatch
):
    if environment_key is None:
        monkeypatch.delenv("EIA_API_KEY", raising=False)
    else:
        monkeypatch.setenv("EIA_API_KEY", environment_key)
    with (
        patch("worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync") as sync,
        patch.object(EiaUsRefreshJob, "_write_parquet_snapshots") as snapshots,
        patch(
            "worldenergydata.scheduler.jobs.eia_us_refresh.write_refresh_metadata"
        ) as metadata,
    ):
        sync.return_value.run_all.return_value = []
        result = EiaUsRefreshJob().run({"api_key": config_key})
    assert result.status == "skipped"
    assert result.error_msg == "credential_absent"
    assert result.records_updated == 0
    assert result.retryable is False
    sync.assert_not_called()
    snapshots.assert_not_called()
    metadata.assert_not_called()


@pytest.mark.parametrize(
    "config_key,environment_key,expected",
    [
        (None, "environment-fixture", "environment-fixture"),
        ("", "environment-fixture", "environment-fixture"),
        (" ", "environment-fixture", "environment-fixture"),
        ("\t", "environment-fixture", "environment-fixture"),
        (" \t", " environment-fixture\t", "environment-fixture"),
        (" configured-fixture\t", "environment-fixture", "configured-fixture"),
        ("configured-fixture", " ", "configured-fixture"),
        ("configured-fixture", "\t", "configured-fixture"),
    ],
)
def test_normalized_credential_precedence(
    config_key, environment_key, expected, monkeypatch
):
    monkeypatch.setenv("EIA_API_KEY", environment_key)
    with (
        patch("worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync") as sync,
        patch.object(EiaUsRefreshJob, "_write_parquet_snapshots"),
        patch("worldenergydata.scheduler.jobs.eia_us_refresh.write_refresh_metadata"),
    ):
        sync.return_value.run_all.return_value = []
        result = EiaUsRefreshJob().run({"api_key": config_key})
    assert result.status == "success"
    assert sync.call_args.kwargs["api_key"] == expected


@pytest.mark.parametrize("reason", [None, "credential_absent"])
def test_monitor_warns_only_for_missing_credentials(reason, caplog):
    now = datetime.now()
    result = JobResult("eia_us_refresh", now, now, "skipped", 0, reason, False)
    reporter = StatusReporter("unused.json")
    alerts = Mock()
    with (
        patch.object(reporter, "write_status"),
        patch.object(reporter, "_read_status", return_value={}),
        patch("worldenergydata.scheduler.staleness.check_staleness", return_value=[]),
    ):
        reporter.check_and_alert([result], alerts)
    assert ("credential_absent" in caplog.text) == (reason == "credential_absent")
    alerts.send_alert.assert_not_called()
