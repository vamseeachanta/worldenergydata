"""Serial, resumable bathymetry curation; unknown digests deny data reuse.

URLs and source terms belong to the catalog/manifest, never to fetch code.
No network request occurs until ``fetch_bathymetry`` is called explicitly.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

from .terrain import TerrainFetchError

MANIFEST_PATH = Path(__file__).with_name("bathymetry_manifest.json")
_USER_AGENT = "worldenergydata-bathymetry-curation/1.0 (public research data)"


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    """Return file records; the bundled manifest remains read-only at runtime."""
    with path.open(encoding="utf-8") as stream:
        return list(json.load(stream)["files"])


def _size(entry: dict[str, Any]) -> int:
    size = entry.get("size_bytes")
    if not isinstance(size, int) or size <= 0:
        raise TerrainFetchError("server HEAD size is not established")
    if entry["head"]["status"] != 200:
        raise TerrainFetchError("source HEAD was refused or unverified")
    return size


def file_sha256(path: Path) -> str:
    """Hash the actual bytes without loading the file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, entry: dict[str, Any]) -> None:
    """Fail closed for missing hashes, size mismatch or changed source bytes."""
    size = _size(entry)
    digest = entry.get("sha256")
    if not digest:
        raise TerrainFetchError("not yet fetched: committed SHA-256 is required")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise TerrainFetchError("invalid manifest SHA-256")
    if not path.is_file() or path.stat().st_size != size:
        raise TerrainFetchError("file size does not match manifest")
    if file_sha256(path) != digest:
        raise TerrainFetchError("file SHA-256 does not match manifest")


def _data_root(data_root: Path | None) -> Path:
    root = data_root or os.environ.get("WORLDENERGYDATA_BATHYMETRY_ROOT")
    if not root:
        raise ValueError("provide data_root or WORLDENERGYDATA_BATHYMETRY_ROOT")
    result = Path(root)
    result.mkdir(parents=True, exist_ok=True)
    return result


def _checked_host(url: str, entry: dict[str, Any]) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise TerrainFetchError("every source hop must use HTTPS")
    try:
        port = parsed.port
    except ValueError as exc:
        raise TerrainFetchError(
            f"rejected redirect target {parsed.hostname}: port is malformed"
        ) from exc
    if (
        parsed.hostname not in entry.get("allowed_hosts", [])
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise TerrainFetchError("source host is not allowed")
    return str(parsed.hostname)


@contextmanager
def _request(http: Any, method: str, entry: dict[str, Any], **kwargs: Any) -> Any:
    url = entry["source_url"]
    for hop in range(4):
        host = _checked_host(url, entry)
        with getattr(http, method)(
            url, timeout=60, allow_redirects=False, **kwargs
        ) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                if hop == 3:
                    raise TerrainFetchError("source redirect limit exceeded")
                location = response.headers.get("Location")
                if not location:
                    raise TerrainFetchError("source redirect has no location")
                url = urljoin(url, location)
                continue
            if url != entry["final_url"] or host != entry["final_host"]:
                raise TerrainFetchError(
                    "source final destination differs from manifest"
                )
            yield response
            return


def _head(http: Any, entry: dict[str, Any]) -> str | None:
    with _request(
        http,
        "head",
        entry,
        headers={"User-Agent": _USER_AGENT, "Accept-Encoding": "identity"},
    ) as response:
        if response.status_code != 200:
            raise TerrainFetchError(f"source HEAD refused: HTTP {response.status_code}")
        if response.headers.get("Content-Length") != str(_size(entry)):
            raise TerrainFetchError("current server size differs from manifest")
        etag = response.headers.get("ETag")
        return etag if etag and not etag.startswith("W/") else None


def _transfer(
    http: Any, entry: dict[str, Any], part: Path, state: Path, etag: str | None
) -> None:
    size = _size(entry)
    offset = part.stat().st_size if part.exists() else 0
    old = json.loads(state.read_text()) if state.exists() else {}
    if offset > size:
        raise TerrainFetchError("partial file exceeds manifest size")
    if offset and (not etag or old.get("etag") != etag):
        offset = 0
    headers = {"User-Agent": _USER_AGENT, "Accept-Encoding": "identity"}
    if offset:
        headers.update({"Range": f"bytes={offset}-", "If-Range": str(etag)})
    with _request(
        http,
        "get",
        entry,
        headers=headers,
        stream=True,
    ) as response:
        if response.status_code in (401, 403, 429):
            raise TerrainFetchError(f"source refused: HTTP {response.status_code}")
        if response.status_code == 200:
            offset = 0
        elif response.status_code == 206 and offset:
            expected = f"bytes {offset}-{size - 1}/{size}"
            if (
                response.headers.get("Content-Range") != expected
                or response.headers.get("ETag") != etag
            ):
                raise TerrainFetchError("invalid resume range or changed validator")
        else:
            raise TerrainFetchError(f"unexpected download HTTP {response.status_code}")
        if response.headers.get("Content-Length") != str(size - offset):
            raise TerrainFetchError("download length differs from manifest")
        if etag and response.headers.get("ETag") != etag:
            raise TerrainFetchError("server validator changed during download")
        state.write_text(json.dumps({"etag": etag}))
        with part.open("ab" if offset else "wb") as stream:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if stream.tell() + len(chunk) > size:
                    raise TerrainFetchError("download exceeds manifest size")
                stream.write(chunk)
    if part.stat().st_size != size:
        raise requests.ConnectionError("incomplete download; partial retained")


def fetch_bathymetry(
    source_id: str,
    filename: str,
    data_root: Path | None = None,
    *,
    manifest_path: Path = MANIFEST_PATH,
    session: Any = None,
    curate: bool = False,
    pause: Any = time.sleep,
) -> Path:
    """Fetch one archive, with at most one transport retry and one connection.

    ``curate=True`` permits downloading an unknown digest for human manifest
    reconciliation. A local observation records the measured hash and UTC date;
    that observation never grants reuse. ``verify_file`` still requires a pinned
    committed digest. Refusals and size disagreement are never retried.
    """
    entries = [
        e
        for e in load_manifest(manifest_path)
        if e["source_id"] == source_id and e["filename"] == filename
    ]
    if len(entries) != 1 or Path(filename).name != filename:
        raise ValueError("select exactly one manifest archive by basename")
    entry = entries[0]
    _size(entry)
    _checked_host(entry["source_url"], entry)
    if not entry.get("sha256") and not curate:
        raise TerrainFetchError("not yet fetched: use explicit curation mode")
    target = _data_root(data_root) / filename
    if target.exists():
        verify_file(target, entry)
        return target
    http = session or requests
    etag = _head(http, entry)
    part = target.with_name(filename + ".part")
    state = target.with_name(filename + ".resume.json")
    if not (part.exists() and part.stat().st_size == _size(entry)):
        for attempt in range(2):
            try:
                _transfer(http, entry, part, state, etag)
                break
            except requests.RequestException:
                if attempt:
                    raise
                pause(3)
    digest = file_sha256(part)
    if entry.get("sha256"):
        verify_file(part, entry)
    _record_observation(target, part, entry, digest)
    part.replace(target)
    return target


def _record_observation(
    target: Path, part: Path, entry: dict[str, Any], digest: str
) -> None:
    observation = {
        "source_url": entry["source_url"],
        "final_url": entry["final_url"],
        "final_host": entry["final_host"],
        "size_bytes": part.stat().st_size,
        "sha256": digest,
        "retrieval_date_utc": datetime.now(timezone.utc).isoformat(),
        "readiness_status": "ready" if entry.get("sha256") else "unverified",
    }
    target.with_name(target.name + ".observation.json").write_text(
        json.dumps(observation, indent=2) + "\n", encoding="utf-8"
    )
