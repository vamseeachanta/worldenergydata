"""Retry decisions use typed contracts rather than matching error messages.

Issue #460 supplies the terminal cases. Counts are obtained by hand: a terminal
result executes once with no sleeps; a transient failure followed by success
executes twice with one sleep. Backoff inputs below are synthetic test inputs,
not service recommendations.

Backoff equation source: AWS Architecture Blog, "Exponential Backoff And
Jitter" (2015), capped backoff equation. These tests retain the existing
uncapped scheduler rule with explicit inputs; no cap or retry budget is adopted.
https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
"""

import json
import zipfile
from datetime import datetime
from http import HTTPStatus
from unittest.mock import Mock, call, patch

import pytest
import requests


def _http_error(status):
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(status.phrase, response=response)


def test_skipped_stub_is_terminal(tmp_path):
    """One stub invocation plus no sleeps; no retry can implement an adapter."""
    from worldenergydata.scheduler.jobs.lng_terminals_refresh import (
        LngTerminalsRefreshJob,
    )
    from worldenergydata.scheduler.monitor import RetryManager

    job = LngTerminalsRefreshJob()
    run = Mock(side_effect=lambda: job.run({"output_dir": str(tmp_path)}))
    # Synthetic budget, as in test_monitor.py::TestRetryManager.
    manager = RetryManager(max_retries=3, backoff_seconds=1)
    with patch("worldenergydata.scheduler.monitor.time.sleep") as sleep:
        result = manager.run_with_retry(run)
    assert result.status == "skipped"
    run.assert_called_once_with()
    sleep.assert_not_called()


def test_missing_eia_credentials_is_terminal(monkeypatch, tmp_path):
    """EIAFeedClient.__init__ raises EIAKeyError before any HTTP request."""
    from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob
    from worldenergydata.scheduler.monitor import RetryManager

    monkeypatch.delenv("EIA_API_KEY", raising=False)
    job = EiaUsRefreshJob()
    run = Mock(side_effect=lambda: job.run({"output_dir": str(tmp_path)}))
    # Synthetic budget, as in test_monitor.py::TestRetryManager.
    manager = RetryManager(max_retries=3, backoff_seconds=1)
    with (
        patch("worldenergydata.scheduler.monitor.time.sleep") as sleep,
        patch("worldenergydata.eia.client.requests.get") as get,
    ):
        result = manager.run_with_retry(run)
    assert result.status == "failure"
    assert result.retryable is False
    assert "EIA_API_KEY not set" in result.error_msg
    run.assert_called_once_with()
    sleep.assert_not_called()
    get.assert_not_called()
    assert not list(tmp_path.iterdir())


def test_unknown_failure_remains_retryable():
    """A runtime failure then success gives two calls and one initial delay."""
    from worldenergydata.scheduler.jobs.base import JobResult
    from worldenergydata.scheduler.monitor import RetryManager

    now = datetime.now()
    success = JobResult("test_refresh", now, now, "success", 0, None)
    run = Mock(side_effect=[RuntimeError("temporary failure"), success])
    # Hand calculation: first delay = input base 1 * 2**0 = 1 second.
    manager = RetryManager(max_retries=3, backoff_seconds=1)
    with patch("worldenergydata.scheduler.monitor.time.sleep") as sleep:
        result = manager.run_with_retry(run)
    assert result is success
    assert run.call_count == 2
    sleep.assert_called_once_with(1)


# HTTP semantics: RFC 9110 (2022), sections 15.5.5 and 15.6.
# This policy terminates a missing configured endpoint within one run;
# it does not claim that HTTP Not Found implies permanent unavailability.
@pytest.mark.parametrize(
    "error,retryable",
    [
        (_http_error(HTTPStatus.NOT_FOUND), False),
        (_http_error(HTTPStatus.SERVICE_UNAVAILABLE), True),
        (_http_error(HTTPStatus.BAD_GATEWAY), True),
        (requests.HTTPError("no response"), True),
        (requests.Timeout("timeout"), True),
        (requests.ConnectionError("connection lost"), True),
        (zipfile.BadZipFile("invalid static archive"), False),
        (RuntimeError("404 in unstructured text"), True),
        (ValueError("unknown processing error"), True),
    ],
)
def test_anp_failure_classification(error, retryable, tmp_path):
    """Hand calculation: terminal = one call, no sleeps; transient exhausts
    three calls with delays 1 * 2**0 = 1 and 1 * 2**1 = 2 seconds.

    Status meanings come from RFC 9110 (2022), sections 15.5.5 and 15.6.
    Invalid ZIP handling follows ANPClient._read_zip and load_cached: the
    same payload may be cached, so repeating it does not repair the archive.
    The year/month and retry budget are synthetic inputs.
    """
    from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob
    from worldenergydata.scheduler.monitor import RetryManager

    job = BrazilAnpRefreshJob()
    run = Mock(
        side_effect=lambda: job.run(
            {"output_dir": str(tmp_path), "year": 2026, "month": 1}
        )
    )
    manager = RetryManager(max_retries=3, backoff_seconds=1)
    with (
        patch("worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient") as client,
        patch("worldenergydata.scheduler.monitor.time.sleep") as sleep,
    ):
        client.return_value.download_month.side_effect = error
        result = manager.run_with_retry(run)
    assert result.status == "failure"
    assert result.retryable is retryable
    assert result.error_msg == str(error)
    assert run.call_count == (3 if retryable else 1)
    assert sleep.call_args_list == ([call(1), call(2)] if retryable else [])


def test_anp_invalid_configuration_is_terminal(tmp_path):
    """Invalid integer input cannot become valid on the next attempt.

    One validation failure implies one invocation and zero client calls/sleeps.
    """
    from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob
    from worldenergydata.scheduler.monitor import RetryManager

    job = BrazilAnpRefreshJob()
    run = Mock(
        side_effect=lambda: job.run(
            {"output_dir": str(tmp_path), "year": "invalid", "month": "invalid"}
        )
    )
    # Synthetic budget; no backoff is expected for rejected configuration.
    manager = RetryManager(max_retries=3, backoff_seconds=1)
    with (
        patch("worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient") as client,
        patch("worldenergydata.scheduler.monitor.time.sleep") as sleep,
    ):
        result = manager.run_with_retry(run)
    assert result.job_name == job.name
    assert result.status == "failure"
    assert result.retryable is False
    run.assert_called_once_with()
    sleep.assert_not_called()
    client.assert_not_called()


@pytest.mark.parametrize("retryable", [True, False])
def test_retryability_is_persisted(retryable, tmp_path):
    """A single input result must retain its flag in both JSON consumers."""
    from worldenergydata.scheduler.jobs.base import JobResult
    from worldenergydata.scheduler.monitor import JobLogger, StatusReporter

    now = datetime.now()
    result = JobResult(
        "test_refresh", now, now, "failure", 0, "test failure", retryable=retryable
    )
    # Synthetic retention input, consistent with existing monitor tests.
    JobLogger(str(tmp_path / "logs"), retention_days=1).log_result(result)
    (log_path,) = (tmp_path / "logs").glob("*.json")
    logged = json.loads(log_path.read_text())
    assert logged["retryable"] is retryable
    status_path = tmp_path / "status.json"
    StatusReporter(str(status_path)).write_status([result])
    reported = json.loads(status_path.read_text())
    assert reported["jobs"][result.job_name]["retryable"] is retryable


@pytest.mark.parametrize("source", ["stub", "eia", "anp", "bsee"])
def test_run_once_records_terminal_source_without_backoff(
    source, monkeypatch, tmp_path
):
    """Independent trace: one job call, zero sleeps, one log and status entry,
    no success manifest. Sources are the issue acceptance cases; BSEE's HTML
    fixture follows classify_payload's documented static contract.
    """
    from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob
    from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob
    from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob
    from worldenergydata.scheduler.jobs.lng_terminals_refresh import (
        LngTerminalsRefreshJob,
    )
    from worldenergydata.scheduler.scheduler import DataScheduler

    monkeypatch.delenv("EIA_API_KEY", raising=False)
    job = {
        "stub": LngTerminalsRefreshJob,
        "eia": EiaUsRefreshJob,
        "anp": BrazilAnpRefreshJob,
        "bsee": BseeRefreshJob,
    }[source]()
    run = Mock(wraps=job.run)
    monkeypatch.setattr(job, "run", run)
    output_dir = tmp_path / "output"
    config_path = tmp_path / "config" / "scheduler" / "config.yml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "jobs": [{"name": job.name, "output_dir": str(output_dir)}],
                "monitoring": {
                    "log_dir": str(tmp_path / "logs"),
                    "status_file": str(tmp_path / "status.json"),
                    # Synthetic retry budget and base, not operational limits.
                    "retry_max": 3,
                    "retry_backoff_seconds": 1,
                },
            }
        )
    )
    scheduler = DataScheduler(str(config_path))
    scheduler.register_job(job)
    with (
        patch("worldenergydata.scheduler.monitor.time.sleep") as sleep,
        patch("worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient") as client,
        patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper") as scraper,
    ):
        client.return_value.download_month.side_effect = _http_error(
            HTTPStatus.NOT_FOUND
        )
        scraper.return_value.download_zip_to_memory.return_value = (
            b"<html>missing</html>"
        )
        result = scheduler.run_once(job.name)
    expected_status = "skipped" if source == "stub" else "failure"
    assert result.status == expected_status
    assert result.job_name == job.name
    run.assert_called_once()
    sleep.assert_not_called()
    assert scheduler.status()["jobs"][job.name]["last_result"] == expected_status
    reported = json.loads((tmp_path / "status.json").read_text())
    detail = reported["jobs"][job.name]
    assert detail["status"] == expected_status
    assert detail["error_msg"] == result.error_msg
    assert detail["retryable"] is result.retryable
    if source != "stub":
        assert result.retryable is False
    (log_path,) = (tmp_path / "logs").glob("*.json")
    assert json.loads(log_path.read_text())["retryable"] is result.retryable
    assert not (output_dir / "manifest.json").exists()


def test_anp_cached_invalid_zip_is_terminal(tmp_path):
    """ANPClient.load_cached reopens the same bytes: one call and no sleeps.

    The cache filename follows ANPClient._cache_key; its date is a synthetic
    input. The fixture contains plain text rather than a ZIP container.
    """
    from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob
    from worldenergydata.scheduler.monitor import RetryManager

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "anp_production_2026_01.zip").write_bytes(b"<html>missing</html>")
    job = BrazilAnpRefreshJob()
    run = Mock(
        side_effect=lambda: job.run(
            {"output_dir": str(tmp_path), "year": 2026, "month": 1}
        )
    )
    # Synthetic budget; cached invalid input cannot recover during backoff.
    manager = RetryManager(max_retries=3, backoff_seconds=1)
    with (
        patch("worldenergydata.scheduler.monitor.time.sleep") as sleep,
        patch("requests.get") as get,
    ):
        result = manager.run_with_retry(run)
    assert result.status == "failure"
    assert result.retryable is False
    run.assert_called_once_with()
    sleep.assert_not_called()
    get.assert_not_called()


def test_transient_eia_error_can_recover(tmp_path):
    """An EIAFeedError then successful ingestion means two calls and one sleep.

    Hand calculation: initial delay = synthetic base 1 * 2**0 = 1 second.
    EIAFeedError is the source client's API failure type, unlike EIAKeyError.
    """
    from worldenergydata.eia.client import EIAFeedError
    from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob
    from worldenergydata.scheduler.monitor import RetryManager

    job = EiaUsRefreshJob()
    run = Mock(side_effect=lambda: job.run({"output_dir": str(tmp_path)}))
    sync = Mock(output_dir=tmp_path)
    sync.run_all.return_value = []
    manager = RetryManager(max_retries=3, backoff_seconds=1)
    with (
        patch("worldenergydata.scheduler.monitor.time.sleep") as sleep,
        patch(
            "worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync",
            side_effect=[EIAFeedError("temporary failure"), sync],
        ),
    ):
        result = manager.run_with_retry(run)
    assert result.status == "success"
    assert run.call_count == 2
    sleep.assert_called_once_with(1)
