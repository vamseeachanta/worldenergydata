"""Persist Texas RRC lifecycle spine outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.lifecycle.quality import LifecycleQualityReport
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

LIFECYCLE_SPINE_DIR = Path("curated") / "well_lifecycle" / "spine"
SPINE_FILENAME = "well_lifecycle_spine.csv"
QUALITY_FILENAME = "well_lifecycle_quality.json"
MANIFEST_FILENAME = "manifest.json"
API_KEY_DTYPES = {
    "api14": "string",
    "api10": "string",
    "county_code": "string",
    "well_unique_number": "string",
    "sidetrack_code": "string",
    "completion_code": "string",
}


@dataclass(frozen=True)
class LifecycleOutputManifest:
    """Paths and summary metadata for one lifecycle spine output batch."""

    generated_at: str
    output_root: Path
    spine_path: Path
    quality_path: Path
    manifest_path: Path
    row_count: int
    input_paths: tuple[str, ...]


def write_lifecycle_outputs(
    spine: pd.DataFrame,
    quality: LifecycleQualityReport,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
) -> LifecycleOutputManifest:
    """Write lifecycle spine artifacts under the Texas RRC curated data layout."""
    root = Path(output_root)
    target_dir = root / LIFECYCLE_SPINE_DIR
    stamp = _timestamp(generated_at)
    final_spine = target_dir / SPINE_FILENAME
    final_quality = target_dir / QUALITY_FILENAME
    final_manifest = target_dir / MANIFEST_FILENAME
    manifest = LifecycleOutputManifest(
        generated_at=stamp,
        output_root=root,
        spine_path=final_spine,
        quality_path=final_quality,
        manifest_path=final_manifest,
        row_count=len(spine),
        input_paths=tuple(str(path) for path in input_paths),
    )
    staging = target_dir / f".staging-well-lifecycle-spine-{_compact_stamp(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        staging.mkdir(parents=True, exist_ok=False)
        spine.to_csv(staging / SPINE_FILENAME, index=False)
        _write_json(staging / QUALITY_FILENAME, _quality_payload(quality))
        _write_json(staging / MANIFEST_FILENAME, _manifest_payload(manifest, quality))
        target_dir.mkdir(parents=True, exist_ok=True)
        (staging / SPINE_FILENAME).replace(final_spine)
        (staging / QUALITY_FILENAME).replace(final_quality)
        (staging / MANIFEST_FILENAME).replace(final_manifest)
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def load_lifecycle_spine(path: Path | str) -> pd.DataFrame:
    """Load a persisted lifecycle spine while preserving API key strings."""
    return pd.read_csv(path, dtype=API_KEY_DTYPES)


def _quality_payload(quality: LifecycleQualityReport) -> dict[str, object]:
    return asdict(quality)


def _manifest_payload(
    manifest: LifecycleOutputManifest,
    quality: LifecycleQualityReport,
) -> dict[str, object]:
    return {
        "generated_at": manifest.generated_at,
        "output_root": str(manifest.output_root),
        "spine_path": str(manifest.spine_path),
        "quality_path": str(manifest.quality_path),
        "manifest_path": str(manifest.manifest_path),
        "row_count": manifest.row_count,
        "input_paths": list(manifest.input_paths),
        "quality": _quality_payload(quality),
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _timestamp(value: datetime | None) -> str:
    timestamp = value or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact_stamp(stamp: str) -> str:
    return stamp.replace("-", "").replace(":", "")


__all__ = [
    "LifecycleOutputManifest",
    "LIFECYCLE_SPINE_DIR",
    "load_lifecycle_spine",
    "write_lifecycle_outputs",
]
