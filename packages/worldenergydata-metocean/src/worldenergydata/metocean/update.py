"""Update retained yearly NDBC snapshots without overwriting source evidence.

The configured end year is an explicit coverage boundary, not a claim of
current conditions. Revisions require refresh=True; ordinary repeats retain
the previously fetched publisher version. Failed downloads remain retryable.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from worldenergydata.metocean.clients.archive_transport import (
    ArchiveLimitError,
    ArchiveTransport,
)
from worldenergydata.metocean.clients.ndbc_client import NDBCClient
from worldenergydata.metocean.database.archive_store import ArchiveStore, _atomic_bytes
from worldenergydata.metocean.source_register import get_source


@contextmanager
def _single_writer(root):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "update.lock"
    with lock.open("x", encoding="utf-8"):
        pass
    try:
        yield
    finally:
        lock.unlink()


def update_archive(config, data_root, *, download=None, source=None, refresh=False):
    """Retain missing yearly resources; resume downloaded-but-unparsed files."""
    source = source if source is not None else get_source("ndbc_archive")
    if not (
        source.get("update_enabled")
        and source.get("terms_rechecked")
        and source.get("account_required") is False
    ):
        raise ValueError("Source is not eligible for automatic updating")
    stations = config.get("stations", [])
    if not stations:
        raise ValueError("At least one station is required")
    for station in stations:
        if not re.fullmatch(r"[A-Za-z0-9]+", station["id"]):
            raise ValueError("Invalid station identifier")
        if not (
            1900
            <= station["start_year"]
            <= station["end_year"]
            < datetime.now(timezone.utc).year
        ):
            raise ValueError("Only completed calendar years may be requested")
    store = ArchiveStore(Path(data_root))
    if store.verify():
        raise ValueError(
            "Archive digest mismatch; retained evidence requires inspection"
        )
    with _single_writer(store.root):
        # Reload under the lock so a completed preceding run cannot be lost.
        store = ArchiveStore(store.root)
        if store.verify():
            raise ValueError(
                "Archive digest mismatch; retained evidence requires inspection"
            )
        with ArchiveTransport() as transport, NDBCClient() as client:
            fetch = download or (
                lambda url, headers=None: client.fetch_resource(url, transport, headers)
            )
            return _update(stations, store, client, fetch, source, refresh)


def _update(stations, store, client, fetch, source, refresh):
    report = {
        "files_fetched": 0,
        "bytes_fetched": 0,
        "files_recovered": 0,
        "records_updated": 0,
        "failures": [],
        "stations": {},
        "coverage_kind": "retained_yearly_snapshots",
    }
    stop = False
    for station in stations:
        station_id = station["id"]
        requested_urls = set()
        for year in range(station["start_year"], station["end_year"] + 1):
            url = (
                f"{client.base_url.rstrip('/')}/view_text_file.php?"
                f"filename={station_id}h{year}.txt.gz&dir=data/historical/stdmet/"
            )
            requested_urls.add(url)
            entry = store.find(url)
            if entry and entry["status"] == "complete" and not refresh:
                continue
            try:
                if entry is None or refresh:
                    conditional = {}
                    if entry:
                        for key, header in (
                            ("etag", "If-None-Match"),
                            ("last-modified", "If-Modified-Since"),
                        ):
                            if entry["headers"].get(key):
                                conditional[header] = entry["headers"][key]
                    response = fetch(url, headers=conditional)
                    if response.status_code == 304:
                        if entry is None or entry["status"] != "complete":
                            raise ValueError(
                                "304 response without complete retained data"
                            )
                        continue
                    if response.status_code != 200:
                        raise ValueError("Unexpected archive response status")
                    entry = store.capture(
                        source["id"],
                        station_id,
                        url,
                        response.content,
                        source,
                        response.headers,
                        response.fetched_at,
                    )
                    report["files_fetched"] += 1
                    report["bytes_fetched"] += len(response.content)
                else:
                    report["files_recovered"] += 1
                content = store._path(entry["raw_path"]).read_bytes()
                rows = client.parse_standard_archive(
                    station_id, content, entry["sha256"]
                )
                # Publisher yearly files can include an adjacent boundary record.
                lower = datetime(year, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
                upper = datetime(year + 1, 1, 1, tzinfo=timezone.utc) + timedelta(
                    days=1
                )
                if any(not lower <= row["observation_time"] < upper for row in rows):
                    raise ValueError("Archive response lies outside its year boundary")
                store.normalize(entry, rows)
                report["records_updated"] += entry["valid_heights"]
            except Exception as exc:
                if "mismatch" in str(exc).lower():
                    raise
                status = getattr(getattr(exc, "response", None), "status_code", None)
                report["failures"].append(
                    {
                        "station_id": station_id,
                        "year": year,
                        "error": type(exc).__name__,
                        "http_status": status,
                    }
                )
                if status in (401, 403) or isinstance(exc, ArchiveLimitError):
                    # A refusal terminates requests to this publisher for the run.
                    stop = True
                    break
        latest_entries = {
            entry["url"]: entry
            for entry in store.entries
            if entry["station_id"] == station_id
            and entry["source_id"] == source["id"]
            and entry["url"] in requested_urls
        }
        complete = [
            entry for entry in latest_entries.values() if entry["status"] == "complete"
        ]
        first = [
            entry["first_timestamp"] for entry in complete if entry["first_timestamp"]
        ]
        last = [
            entry["latest_timestamp"] for entry in complete if entry["latest_timestamp"]
        ]
        report["stations"][station_id] = {
            "first_timestamp": min(first) if first else None,
            "latest_timestamp": max(last) if last else None,
            "valid_heights": sum(entry["valid_heights"] for entry in complete),
            "complete_files": len(complete),
        }
        if stop:
            break
    if report["files_fetched"] or report["files_recovered"] or report["failures"]:
        _atomic_bytes(
            store.root / "last_update.json",
            (json.dumps(report, indent=2) + "\n").encode(),
        )
    return report
