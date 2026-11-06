"""Single-writer content-addressed cache with atomic URL/progress provenance."""

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


def validate_response(
    url: str, payload: bytes, headers: Mapping[str, str], status: int = 200
) -> None:
    """Qualify reuse before writing, including old cache objects.

    RFC 9110 (2022), sections 8.3 and 15.3.1 define media type and 200 OK.
    Issue #1301 requires nonempty bodies and rejects error representations.
    No source-specific minimum size is assumed.
    """
    if status != 200:
        raise ValueError("Cannot cache a non-200 response")
    if not payload:
        raise ValueError("Cannot cache an empty payload")
    media = {k.lower(): v for k, v in headers.items()}.get("content-type", "")
    media = media.split(";", 1)[0].strip().lower()
    text = payload.lstrip().lower()
    html = media in {"text/html", "application/xhtml+xml"} or text.startswith(
        (b"<!doctype html", b"<html", b"<head", b"<body", b"<title", b"<h1")
    )
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in {".csv", ".zip", ".txt", ".xls", ".xlsx"} and html:
        raise ValueError("Cannot cache HTML in place of a data file")
    expected_media = {
        ".csv": {
            "text/csv",
            "application/csv",
            "text/plain",
            "application/octet-stream",
        },
        ".zip": {
            "application/zip",
            "application/x-zip-compressed",
            "application/octet-stream",
        },
        ".txt": {"text/plain", "text/csv", "application/octet-stream"},
        ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
        ".xlsx": {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        },
        ".aspx": {"text/html", "application/xhtml+xml"},
        ".html": {"text/html", "application/xhtml+xml"},
        ".htm": {"text/html", "application/xhtml+xml"},
    }
    if media and suffix in expected_media and media not in expected_media[suffix]:
        raise ValueError("Unexpected data-file content-type")
    # Error headings are a conservative rejection rule, not a size heuristic.
    if html:
        headings = re.findall(
            rb"<(?:title|h1)\b[^>]*>(.*?)</(?:title|h1)\s*>", text, re.DOTALL
        )
        for heading in headings:
            heading = re.sub(rb"<[^>]*>", b" ", heading)
            if re.search(
                rb"\b(?:error|denied|unavailable|not found|forbidden)\b", heading
            ):
                raise ValueError("Cannot cache an HTML error page")
    visible = re.sub(rb"<[^>]*>", b" ", text).strip()
    if html and re.match(
        rb"(?:error\b|server error|access denied|service unavailable|not found|forbidden)",
        visible,
    ):
        raise ValueError("Cannot cache an HTML error page")


@dataclass(frozen=True)
class FetchResult:
    path: Path
    metadata: dict[str, Any]
    cached: bool


def atomic_json(path: Path, value: Any) -> None:
    """Publish only a complete JSON record; scratch stays beside the target."""
    scratch = path.with_suffix(path.suffix + ".pending")
    with scratch.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    scratch.replace(path)


def read_record(path: Path, *, progress: bool = False) -> dict[str, Any]:
    """Reject damaged evidence without replacing or removing the original."""
    recovery = (
        "Move it aside explicitly, then wait one full budget window before resuming; "
        "cached objects and per-URL records remain verified on read."
        if progress
        else "Preserve it for inspection; restore verified provenance before reuse."
    )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("expected a mapping")
        if progress:
            validate_progress(value)
        else:
            if (
                not isinstance(value.get("sha256"), str)
                or not isinstance(value.get("url"), str)
                or type(value.get("size_bytes")) is not int
                or value["size_bytes"] < 0
            ):
                raise ValueError("invalid URL record shape")
        return value
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        raise ValueError(f"Cache integrity: invalid {path.name}. {recovery}") from error


def validate_progress(value: dict[str, Any]) -> None:
    """Require finite timestamps and explicit mappings before any reservation."""
    if not isinstance(value.get("completed"), dict) or not isinstance(
        value.get("hosts"), dict
    ):
        raise ValueError("invalid progress mappings")
    for host, state in value["hosts"].items():
        if not isinstance(host, str) or not isinstance(state, dict):
            raise ValueError("invalid host state")
        attempts = state.get("attempts")
        if not isinstance(attempts, list):
            raise ValueError("invalid attempts")
        for number in [state.get("next_at"), *attempts]:
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(number)
                or number < 0
                or number > 253370764800
            ):
                raise ValueError("invalid budget timestamp")


class CacheStore:
    """One cache root per execution owner; simultaneous writers unsupported."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.records = self.root / "records"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.records.mkdir(parents=True, exist_ok=True)
        self.progress = self.root / "progress.json"
        self.state: dict[str, Any] = (
            read_record(self.progress, progress=True)
            if self.progress.exists()
            else {"completed": {}, "hosts": {}}
        )

    def save(self) -> None:
        atomic_json(self.progress, self.state)

    def _record(self, url: str) -> Path:
        return self.records / (hashlib.sha256(url.encode()).hexdigest() + ".json")

    def get(self, url: str) -> FetchResult | None:
        record = self._record(url)
        if not record.exists():
            return None
        metadata = read_record(record)
        digest = metadata["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Cache integrity: invalid digest")
        path = self.objects / digest
        payload = path.read_bytes()
        if (
            metadata["url"] != url
            or hashlib.sha256(payload).hexdigest() != digest
            or len(payload) != metadata["size_bytes"]
        ):
            raise ValueError("Cache integrity verification failed")
        try:
            validate_response(
                url,
                payload,
                metadata.get("response_headers", {}),
                metadata.get("status_code", 200),
            )
        except ValueError:
            # Preserve the old bytes. A miss must still pass permission and budget.
            return None
        return FetchResult(path, metadata, True)

    def put(
        self,
        url: str,
        payload: bytes,
        headers: Mapping[str, str],
        terms_check: dict[str, Any],
        *,
        status: int = 200,
        retry_count: int = 0,
    ) -> FetchResult:
        validate_response(url, payload, headers, status)
        digest = hashlib.sha256(payload).hexdigest()
        path = self.objects / digest
        scratch = path.with_suffix(".pending")
        with scratch.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        scratch.replace(path)
        metadata = {
            "url": url,
            "sha256": digest,
            "size_bytes": len(payload),
            "status_code": status,
            "retry_count": retry_count,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "response_headers": dict(headers),
            "terms_check": terms_check,
        }
        atomic_json(self._record(url), metadata)
        verified = self.get(url)
        assert verified is not None
        self.state["completed"][url] = digest
        self.save()
        return FetchResult(verified.path, verified.metadata, False)
