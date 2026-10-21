"""Single-writer content-addressed cache with atomic URL/progress provenance."""

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class FetchResult:
    path: Path
    metadata: dict[str, Any]
    cached: bool


def atomic_json(path: Path, value: Any) -> None:
    """Publish only a complete JSON record; scratch stays beside the target."""
    scratch = path.with_suffix(path.suffix + ".pending")
    with scratch.open("w", encoding="utf-8") as stream:
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
        value = json.loads(path.read_text())
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
        if not payload:
            raise ValueError("Cache integrity: empty payload; preserve for inspection")
        return FetchResult(path, metadata, True)

    def put(
        self,
        url: str,
        payload: bytes,
        headers: Mapping[str, str],
        terms_check: dict[str, Any],
    ) -> FetchResult:
        # Issue #1301 cache contract: a response with no bytes is not reusable.
        if not payload:
            raise ValueError("Cannot cache an empty payload")
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
