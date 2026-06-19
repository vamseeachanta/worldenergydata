"""Tests for HseRefreshJob (scheduler adapter for the HSE incident corpus)."""

from __future__ import annotations

from worldenergydata.scheduler.jobs.hse_refresh import HseRefreshJob


class _FakeAcquirer:
    """No-network stand-in for BSEEAcquirer."""

    def __init__(self, rows: int):
        self._rows = rows
        self.downloaded = False

    def download_all(self, output_dir, force=False):
        self.downloaded = True
        return {}

    def verify_data(self, output_dir):
        return {
            "incinv": {
                "status": "ok",
                "files": [{"name": "mv_acc_investigations.txt", "rows": self._rows}],
            }
        }


class _BoomAcquirer:
    def download_all(self, output_dir, force=False):
        raise RuntimeError("network down")

    def verify_data(self, output_dir):  # pragma: no cover
        return {}


def _job(acquirer):
    job = HseRefreshJob()
    job._acquirer = lambda: acquirer  # inject fake
    return job


def test_success_writes_metadata_and_counts_rows(tmp_path):
    acq = _FakeAcquirer(1987)
    result = _job(acq).run({"output_dir": str(tmp_path)})
    assert result.status == "success"
    assert result.records_updated == 1987
    assert acq.downloaded
    assert (tmp_path / "raw" / "bsee").is_dir()
    assert (tmp_path / "_metadata.json").exists()


def test_missing_output_dir_is_skipped():
    result = HseRefreshJob().run({})
    assert result.status == "skipped"
    assert result.records_updated == 0


def test_download_failure_is_retryable(tmp_path):
    result = _job(_BoomAcquirer()).run({"output_dir": str(tmp_path)})
    assert result.status == "failure"
    assert result.retryable is True


def test_zero_rows_is_failure(tmp_path):
    result = _job(_FakeAcquirer(0)).run({"output_dir": str(tmp_path)})
    assert result.status == "failure"
    assert not (tmp_path / "_metadata.json").exists()


def test_registered_in_scheduler_registry():
    from worldenergydata.scheduler.cli import ALL_JOBS

    assert "hse_refresh" in {job.name for job in ALL_JOBS}
