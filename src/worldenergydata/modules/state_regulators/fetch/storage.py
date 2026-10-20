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


def _checked_path(path: Path, root: Path) -> Path:
    """Refuse symlinks, including dangling links, before cache filesystem access.

    This checks a stable directory tree; concurrent replacement is unsupported.
    """
    if not path.is_relative_to(root):
        raise ValueError("Cache path must remain within the cache root")
    current = root
    for part in ("", *path.relative_to(root).parts):
        current = current / part
        if current.is_symlink():
            raise ValueError("Cache path must not contain symlinks")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Cache path must remain within the cache root")
    return path


def atomic_json(path: Path, value: Any, *, root: Path) -> None:
    """Publish only a complete JSON record; scratch stays beside the target."""
    path = _checked_path(path, root)
    scratch = _checked_path(path.with_suffix(path.suffix + ".pending"), root)
    with scratch.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    scratch.replace(path)


def read_record(path: Path, *, root: Path, progress: bool = False) -> dict[str, Any]:
    """Reject damaged evidence without replacing or removing the original."""
    path = _checked_path(path, root)
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
        self.root = Path(root).absolute()
        self.objects = _checked_path(self.root / "objects", self.root)
        self.records = _checked_path(self.root / "records", self.root)
        self.objects.mkdir(parents=True, exist_ok=True)
        self.records.mkdir(parents=True, exist_ok=True)
        self.progress = _checked_path(self.root / "progress.json", self.root)
        self.state: dict[str, Any] = (
            read_record(self.progress, root=self.root, progress=True)
            if self.progress.exists()
            else {"completed": {}, "hosts": {}}
        )

    def save(self) -> None:
        atomic_json(self.progress, self.state, root=self.root)

    def _record(self, url: str) -> Path:
        return _checked_path(
            self.records / (hashlib.sha256(url.encode()).hexdigest() + ".json"),
            self.root,
        )

    def get(self, url: str) -> FetchResult | None:
        record = self._record(url)
        if not record.exists():
            return None
        metadata = read_record(record, root=self.root)
        digest = metadata["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Cache integrity: invalid digest")
        path = _checked_path(self.objects / digest, self.root)
        payload = path.read_bytes()
        if (
            metadata["url"] != url
            or hashlib.sha256(payload).hexdigest() != digest
            or len(payload) != metadata["size_bytes"]
        ):
            raise ValueError("Cache integrity verification failed")
        return FetchResult(path, metadata, True)

    def put(
        self,
        url: str,
        payload: bytes,
        headers: Mapping[str, str],
        terms_check: dict[str, Any],
    ) -> FetchResult:
        digest = hashlib.sha256(payload).hexdigest()
        path = _checked_path(self.objects / digest, self.root)
        scratch = _checked_path(path.with_suffix(".pending"), self.root)
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
        atomic_json(self._record(url), metadata, root=self.root)
        verified = self.get(url)
        assert verified is not None
        self.state["completed"][url] = digest
        self.save()
        return FetchResult(verified.path, verified.metadata, False)
