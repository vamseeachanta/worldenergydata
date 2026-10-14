"""Synthetic publisher-format fixtures; no publisher data is redistributed."""

import hashlib
import json
import socket
from datetime import datetime, timezone

import httpx
import pytest

from worldenergydata.metocean.clients.ndbc_client import NDBCClient
from worldenergydata.metocean.database.archive_store import ArchiveStore
from worldenergydata.metocean.update import update_archive

SYNTHETIC = (
    b"YY MM DD hh WD WSPD GST WVHT DPD\n24 01 02 03 180 5 99.0 1.5 8.3\n"
    b"24 01 02 03 180 5 99.0 99.00 99.00\n"
)
SOURCE = {
    "id": "ndbc_archive",
    "update_enabled": True,
    "terms_rechecked": True,
    "account_required": False,
    "terms_quote": "Synthetic fixture only",
    "terms_url": "https://example.invalid/terms",
}


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Real connections are forbidden in archive unit tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def test_read_refuses_modified_valid_parquet(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from worldenergydata.metocean.database.archive_store import SCHEMA

    store = ArchiveStore(tmp_path)
    rows = NDBCClient.parse_standard_archive(
        "42001", SYNTHETIC, hashlib.sha256(SYNTHETIC).hexdigest()
    )
    entry = store.save(
        "ndbc_archive", "42001", "https://example.invalid/file", SYNTHETIC, rows, SOURCE
    )
    rows[0]["value"] = 8.0
    pq.write_table(
        pa.Table.from_pylist(rows, schema=SCHEMA), tmp_path / entry["normalized_path"]
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        store.read_rows(entry)


@pytest.mark.parametrize(
    "field,value",
    [
        ("station_id", "42002"),
        ("source_id", "other"),
        ("raw_sha256", "wrong"),
        ("unit", "ft"),
        ("observation_time", datetime(1924, 1, 2)),
    ],
)
def test_normalize_rejects_false_provenance(tmp_path, field, value):
    store = ArchiveStore(tmp_path)
    rows = NDBCClient.parse_standard_archive(
        "42001", SYNTHETIC, hashlib.sha256(SYNTHETIC).hexdigest()
    )
    rows[0][field] = value
    entry = store.capture(
        "ndbc_archive", "42001", "https://example.invalid/file", SYNTHETIC, SOURCE
    )
    with pytest.raises(ValueError):
        store.normalize(entry, rows)
    assert entry["status"] == "downloaded"


def test_failure_report_is_saved(tmp_path):
    config = {"stations": [{"id": "42001", "start_year": 1924, "end_year": 1924}]}

    def refusal(url, headers=None):
        httpx.Response(403, request=httpx.Request("GET", url)).raise_for_status()

    report = update_archive(config, tmp_path, download=refusal, source=SOURCE)
    assert report["stations"]["42001"]["complete_files"] == 0
    assert json.loads((tmp_path / "last_update.json").read_text()) == report


def test_historical_header_year_missing_and_repeated_time():
    rows = NDBCClient.parse_standard_archive("42001", SYNTHETIC, "digest")
    assert len(rows) == 4
    assert rows[0]["observation_time"] == datetime(1924, 1, 2, 3, tzinfo=timezone.utc)
    assert rows[0]["value"] == 1.5
    assert rows[1]["value"] == 8.3
    assert rows[1]["period_kind"] == "dominant"
    assert rows[2]["value"] is None
    assert rows[2]["quality_flag"] == "missing"
    assert rows[2]["observation_time"] == rows[0]["observation_time"]
    assert rows[2]["row_number"] != rows[0]["row_number"]


def test_modern_minutes_and_utc():
    raw = b"#YY MM DD hh mm WVHT DPD\n#yr mo dy hr mn m sec\n2025 12 31 23 50 2.1 9.1\n"
    rows = NDBCClient.parse_standard_archive("42001", raw, "digest")
    assert rows[0]["observation_time"].minute == 50
    assert rows[0]["observation_time"].utcoffset().total_seconds() == 0


def test_unused_trailing_column_may_be_absent():
    raw = b"YYYY MM DD hh WVHT DPD TIDE\n2000 01 01 00 1.2 8.3\n"
    assert NDBCClient.parse_standard_archive("42001", raw, "digest")[0]["value"] == 1.2


def test_yearly_file_retains_adjacent_boundary_row(tmp_path):
    from worldenergydata.metocean.clients.archive_transport import Download

    raw = b"#YY MM DD hh mm WVHT DPD\n2008 12 31 23 50 1 8\n2009 01 01 00 50 2 9\n"

    def download(url, headers=None):
        return Download(url, raw, 200, {}, datetime.now(timezone.utc))

    report = update_archive(
        {"stations": [{"id": "42001", "start_year": 2009, "end_year": 2009}]},
        tmp_path,
        download=download,
        source=SOURCE,
    )
    assert report["failures"] == []
    assert report["stations"]["42001"]["valid_heights"] == 2


def test_html_or_invalid_timestamp_is_not_valid_coverage():
    with pytest.raises(ValueError):
        NDBCClient.parse_standard_archive("42001", b"<html>unavailable</html>", "x")
    with pytest.raises(ValueError):
        NDBCClient.parse_standard_archive(
            "42001", b"YY MM DD hh WVHT DPD\n25 13 01 00 1 2", "x"
        )


def test_store_retains_raw_digest_and_columnar_rows(tmp_path):
    store = ArchiveStore(tmp_path)
    rows = NDBCClient.parse_standard_archive(
        "42001", SYNTHETIC, hashlib.sha256(SYNTHETIC).hexdigest()
    )
    entry = store.save(
        "ndbc_archive", "42001", "https://example.invalid/file", SYNTHETIC, rows, SOURCE
    )
    assert store.read_rows(entry) == rows
    assert (tmp_path / entry["raw_path"]).read_bytes() == SYNTHETIC
    assert entry["sha256"] == hashlib.sha256(SYNTHETIC).hexdigest()
    assert entry["raw_path"].startswith("raw/")
    assert not entry["raw_path"].startswith("/")
    assert store.verify() == []


def test_manifest_retains_only_cache_and_content_headers(tmp_path):
    entry = ArchiveStore(tmp_path).capture(
        "ndbc_archive",
        "42001",
        "https://example.invalid/file",
        SYNTHETIC,
        SOURCE,
        {
            "ETag": "fixture-version",
            "Content-Type": "text/plain",
            "Via": "synthetic-edge",
            "X-Request-ID": "synthetic-request",
        },
    )
    assert entry["headers"] == {"etag": "fixture-version", "content-type": "text/plain"}


def test_update_twice_has_zero_second_requests_and_identical_files(tmp_path):
    calls = []

    def download(url, headers=None):
        calls.append(url)
        from worldenergydata.metocean.clients.archive_transport import Download

        return Download(url, SYNTHETIC, 200, {}, datetime.now(timezone.utc))

    config = {"stations": [{"id": "42001", "start_year": 1924, "end_year": 1924}]}
    first = update_archive(config, tmp_path, download=download, source=SOURCE)
    before = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    second = update_archive(config, tmp_path, download=download, source=SOURCE)
    after = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert len(calls) == 1
    assert first["files_fetched"] == 1
    assert second["files_fetched"] == 0
    assert before == after


def test_refusal_and_unverified_terms_never_mark_coverage(tmp_path):
    config = {"stations": [{"id": "42001", "start_year": 1924, "end_year": 1924}]}

    def refusal(url, headers=None):
        response = httpx.Response(403, request=httpx.Request("GET", url))
        response.raise_for_status()

    report = update_archive(config, tmp_path, download=refusal, source=SOURCE)
    assert report["failures"]
    assert report["files_fetched"] == 0
    assert not ArchiveStore(tmp_path).entries
    with pytest.raises(ValueError, match="eligible"):
        update_archive(
            config,
            tmp_path,
            download=refusal,
            source={**SOURCE, "terms_rechecked": False},
        )


def test_cli_update_delegates_to_archive_service(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from worldenergydata.metocean import update
    from worldenergydata.metocean.cli import app

    config = tmp_path / "config.json"
    config.write_text('{"stations": []}', encoding="utf-8")
    monkeypatch.setattr(
        update, "update_archive", lambda *a, **k: {"files_fetched": 0, "failures": []}
    )
    result = CliRunner().invoke(
        app, ["update", "--config", str(config), "--data-root", str(tmp_path / "store")]
    )
    assert result.exit_code == 0, result.output
    assert '"files_fetched": 0' in result.output


def test_scheduler_archive_configuration_uses_same_service(tmp_path, monkeypatch):
    from worldenergydata.metocean import update
    from worldenergydata.scheduler.jobs.metocean_refresh import MetoceanRefreshJob

    calls = []

    def run(config, data_root):
        calls.append(config)
        return {
            "files_fetched": 1,
            "failures": [],
            "stations": {"42001": {"valid_heights": 2}},
        }

    monkeypatch.setattr(update, "update_archive", run)
    result = MetoceanRefreshJob().run(
        {"archive": {"stations": []}, "data_root": str(tmp_path)}
    )
    assert calls == [{"stations": []}]
    assert result.status == "success"
