"""Retained public NDBC responses with offline replay and digest verification."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

from worldenergydata.bsee.pipeline_screening_io import _json_bytes, _write_once
from worldenergydata.bsee.pipeline_screening_metadata import publisher_metadata


def _response_path(cache, url):
    key = hashlib.sha256(url.encode()).hexdigest()
    return Path(cache) / "responses" / (key + ".json")


def retain_response(cache, url, body, http_status, retrieved_at):
    """Keep response bytes and their public retrieval evidence outside Git."""
    digest = hashlib.sha256(body).hexdigest()
    locator = f"data/worldenergydata/blobs/sha256/{digest[:2]}/{digest}.txt"
    metadata = {
        "source_id": "noaa-ndbc",
        "url": url,
        "http_status": http_status,
        "retrieved_at": retrieved_at,
        "bytes": len(body),
        "sha256": digest,
        "body": locator,
        "record_count": None,
        "source_vintage": {
            "state": "unknown",
            "reason": "No observations have been parsed yet.",
        },
    }
    metadata = publisher_metadata(metadata)
    _write_once(Path(cache) / locator, body)
    _write_once(_response_path(cache, url), _json_bytes(metadata))
    return metadata


def _failure_layer(exit_code, status):
    return (
        {
            6: "name_resolution",
            7: "network_reachability",
            28: "network_timeout",
        }.get(exit_code)
        if exit_code
        else (
            "auth_rejection"
            if status in (401, 403)
            else "application_error" if status >= 400 else None
        )
    )


class _RetainedTransport:
    def __init__(self, cache, allow_network, timeout):
        self.cache = Path(cache)
        self.allow_network = allow_network
        self.timeout = timeout
        self.fatal_error = None
        self.blocked = False

    def _download(self, url):
        directory = self.cache / "transfers"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as stream:
            target = Path(stream.name)
        command = [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            str(self.timeout),
            "--output",
            str(target),
            "--write-out",
            "%{http_code}",
            url,
        ]
        try:
            result = subprocess.run(command, capture_output=True, check=False)
            status = int(result.stdout.strip() or b"0")
            metadata = retain_response(
                self.cache,
                url,
                target.read_bytes(),
                status,
                datetime.now(timezone.utc).isoformat(),
            )
            metadata["curl_exit"] = result.returncode
            metadata["failure_layer"] = _failure_layer(result.returncode, status)
            if result.stderr:
                metadata["transfer_error"] = result.stderr.decode(
                    "utf-8", errors="replace"
                )
            _response_path(self.cache, url).write_bytes(_json_bytes(metadata))
            if result.returncode or status in (401, 403, 429) or status >= 500:
                self.blocked = True
        finally:
            target.unlink(missing_ok=True)

    def __call__(self, request):
        if (
            request.url.host != "www.ndbc.noaa.gov"
            or request.url.username
            or request.url.password
        ):
            raise ValueError("Unexpected public source address")
        url = str(request.url)
        path = _response_path(self.cache, url)
        if not path.exists():
            if not self.allow_network or self.blocked:
                raise FileNotFoundError("NDBC response is not retained")
            self._download(url)
        metadata = json.loads(path.read_text())
        locator = metadata["body"]
        valid = re.fullmatch(
            r"data/worldenergydata/blobs/sha256/[a-f0-9]{2}/[a-f0-9]{64}\.txt", locator
        )
        if not valid or metadata["url"] != url:
            self.fatal_error = "Retained input digest mismatch"
            raise ValueError(self.fatal_error)
        try:
            body = (self.cache / locator).read_bytes()
        except FileNotFoundError as exc:
            self.fatal_error = "Retained input body unavailable"
            raise ValueError(self.fatal_error) from exc
        if (
            len(body) != metadata["bytes"]
            or hashlib.sha256(body).hexdigest() != metadata["sha256"]
        ):
            self.fatal_error = "Retained input digest mismatch"
            raise ValueError(self.fatal_error)
        return httpx.Response(metadata["http_status"] or 503, content=body)


def _record_history_metadata(path, result):
    metadata = json.loads(path.read_text())
    metadata["record_count"] = result.records_count
    if result.data:
        metadata["record_start"] = (
            min(r.observation_time for r in result.data).isoformat() + "Z"
        )
        metadata["record_end"] = (
            max(r.observation_time for r in result.data).isoformat() + "Z"
        )
        metadata["source_vintage"] = {
            "state": "observed",
            "latest_observation": metadata["record_end"],
        }
    path.write_bytes(_json_bytes(metadata))


def fetch_ndbc_histories(station_ids, years, cache, *, allow_network):
    """Use the existing historical client serially; retain each response once.

    A shared connection, auth or service failure stops new requests. Missing
    station-year archives remain isolated. Integrity failures propagate even
    though the existing historical client catches per-year exceptions.
    """
    from worldenergydata.metocean.clients.ndbc_client import NDBCClient

    histories = {}
    with NDBCClient() as client:
        if not allow_network:
            client.config.rate_limit_delay = 0
        transport = _RetainedTransport(
            cache, allow_network, client.config.request_timeout
        )
        client.client.close()
        client.client = httpx.Client(transport=httpx.MockTransport(transport))
        for station_id in sorted(set(station_ids)):
            if not re.fullmatch(r"[A-Za-z0-9]{1,8}", station_id):
                raise ValueError("Invalid station identifier")
            records = []
            for year in sorted(set(years)):
                result = client.fetch_historical(
                    station_id, datetime(year, 1, 1), datetime(year, 12, 31, 23, 59)
                )
                if transport.fatal_error:
                    raise ValueError(transport.fatal_error)
                records.extend(result.data)
                url = f"https://www.ndbc.noaa.gov/view_text_file.php?filename={station_id}h{year}.txt.gz&dir=data/historical/stdmet/"
                path = _response_path(cache, url)
                if path.exists():
                    _record_history_metadata(path, result)
                print(
                    f"NDBC {station_id} {year}: {result.records_count} retained observations",
                    flush=True,
                )
            histories[station_id] = records
    return histories


def retained_input_refs(cache, station_ids, years):
    """Pin the retained station-year bodies used by the historical client."""
    root = Path(cache).resolve()
    refs = []
    for station_id in sorted(set(station_ids)):
        for year in sorted(set(years)):
            url = f"https://www.ndbc.noaa.gov/view_text_file.php?filename={station_id}h{year}.txt.gz&dir=data/historical/stdmet/"
            path = _response_path(root, url)
            if not path.exists():
                continue
            metadata = json.loads(path.read_text())
            body = (root / metadata["body"]).resolve()
            if root not in body.parents:
                raise ValueError("Retained input locator escapes storage")
            raw = body.read_bytes()
            if (
                hashlib.sha256(raw).hexdigest() != metadata["sha256"]
                or len(raw) != metadata["bytes"]
            ):
                raise ValueError("Retained input digest mismatch")
            refs.append(
                {
                    "path": f"sources/ndbc/{station_id}h{year}.txt",
                    "blob": metadata["body"],
                    "bytes": len(raw),
                    "sha256": metadata["sha256"],
                    **publisher_metadata(metadata),
                    "blob": metadata["body"],
                    "path": f"sources/ndbc/{station_id}h{year}.txt",
                }
            )
    return refs
