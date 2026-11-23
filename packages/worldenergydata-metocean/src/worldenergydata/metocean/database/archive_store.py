"""Versioned raw evidence and long-form Parquet observations outside Git."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA = pa.schema(
    [
        ("station_id", pa.string()),
        ("observation_time", pa.timestamp("us", tz="UTC")),
        ("variable", pa.string()),
        ("value", pa.float64()),
        ("unit", pa.string()),
        ("quality_flag", pa.string()),
        ("source_id", pa.string()),
        ("period_kind", pa.string()),
        ("raw_sha256", pa.string()),
        ("row_number", pa.int64()),
    ]
)


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(content)
    temporary.replace(path)


class ArchiveStore:
    """A single-writer store; manifest completion follows durable file writes."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        for parent in Path(__file__).resolve().parents:
            if (parent / ".git").exists():
                if self.root == parent or parent in self.root.parents:
                    raise ValueError("Archive root must be outside the repository")
                break
        self.manifest_path = self.root / "manifest.json"
        self.entries = []
        if self.manifest_path.exists():
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if payload["schema_version"] != 1:
                raise ValueError("Unsupported archive manifest version")
            self.entries = payload["files"]

    def _path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if path == self.root or self.root not in path.parents:
            raise ValueError("Manifest path leaves the archive root")
        return path

    def _write_manifest(self) -> None:
        content = json.dumps({"schema_version": 1, "files": self.entries}, indent=2)
        _atomic_bytes(self.manifest_path, (content + "\n").encode())

    def find(self, url: str) -> dict | None:
        return next(
            (entry for entry in reversed(self.entries) if entry["url"] == url), None
        )

    def capture(
        self, source_id, station_id, url, content, source, headers=None, fetched_at=None
    ):
        for identifier in (source_id, station_id):
            if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
                raise ValueError("Invalid archive identifier")
        digest = hashlib.sha256(content).hexdigest()
        raw_path = f"raw/{source_id}/{station_id}/{digest}.txt"
        target = self._path(raw_path)
        if (
            target.exists()
            and hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Raw archive digest mismatch")
        if not target.exists():
            _atomic_bytes(target, content)
        entry = {
            "source_id": source_id,
            "station_id": station_id,
            "url": url,
            "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(),
            "bytes": len(content),
            "sha256": digest,
            "terms_note": source["terms_quote"],
            "terms_url": source.get("terms_url"),
            "raw_path": raw_path,
            "normalized_path": f"normalized/{source_id}/{station_id}/{digest}.parquet",
            "status": "downloaded",
            "headers": {
                key.lower(): value
                for key, value in (headers or {}).items()
                if key.lower() in {"etag", "last-modified", "content-type"}
            },
        }
        self.entries.append(entry)
        self._write_manifest()
        return entry

    def normalize(self, entry: dict, rows: list[dict]) -> dict:
        if not rows:
            raise ValueError("An empty parse cannot establish archive coverage")
        for row in rows:
            if any(
                row.get(key) != entry[entry_key]
                for key, entry_key in (
                    ("station_id", "station_id"),
                    ("source_id", "source_id"),
                    ("raw_sha256", "sha256"),
                )
            ):
                raise ValueError("Observation provenance does not match manifest")
            timestamp = row.get("observation_time")
            if not isinstance(timestamp, datetime) or timestamp.utcoffset() is None:
                raise ValueError("Observation timestamp must carry a timezone")
            expected = {"wave_height_m": "m", "wave_period_s": "s"}
            if (
                row.get("variable") not in expected
                or row.get("unit") != expected[row["variable"]]
            ):
                raise ValueError("Observation variable or unit is not supported")
        target = self._path(entry["normalized_path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".parquet.part")
        table = pa.Table.from_pylist(rows, schema=SCHEMA)
        pq.write_table(table, temporary)
        # Read back before declaring the partition complete.
        if pq.read_table(temporary).to_pylist() != rows:
            raise ValueError("Normalized observation readback mismatch")
        temporary.replace(target)
        valid = [
            row
            for row in rows
            if row["variable"] == "wave_height_m" and row["value"] is not None
        ]
        times = [row["observation_time"] for row in valid]
        entry.update(
            status="complete",
            rows=len(rows),
            valid_heights=len(valid),
            first_timestamp=min(times).isoformat() if times else None,
            latest_timestamp=max(times).isoformat() if times else None,
            normalized_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        )
        self._write_manifest()
        return entry

    def save(self, source_id, station_id, url, content, rows, source):
        return self.normalize(
            self.capture(source_id, station_id, url, content, source), rows
        )

    def read_rows(self, entry: dict) -> list[dict]:
        if entry.get("status") != "complete":
            raise ValueError("Incomplete partition cannot supply observations")
        for path_key, digest_key in (
            ("raw_path", "sha256"),
            ("normalized_path", "normalized_sha256"),
        ):
            path = self._path(entry[path_key])
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry[digest_key]:
                raise ValueError("Archive digest mismatch at observation read")
        return pq.read_table(self._path(entry["normalized_path"])).to_pylist()

    def verify(self) -> list[str]:
        errors = []
        for entry in self.entries:
            for path_key, digest_key in (
                ("raw_path", "sha256"),
                ("normalized_path", "normalized_sha256"),
            ):
                if digest_key not in entry:
                    continue
                path = self._path(entry[path_key])
                if (
                    not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest()
                    != entry[digest_key]
                ):
                    errors.append(f"Digest mismatch: {entry[path_key]}")
        return errors
