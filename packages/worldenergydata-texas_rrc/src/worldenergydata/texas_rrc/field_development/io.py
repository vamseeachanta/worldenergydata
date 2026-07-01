"""Persist Texas RRC field-development metrics outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.field_development.quality import (
    FieldDevelopmentQualityReport,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

FIELD_DEVELOPMENT_METRICS_DIR = Path("curated") / "field_development" / "metrics"
CSV_FILENAME = "field_development_metrics.csv"
PARQUET_FILENAME = "field_development_metrics.parquet"
QUALITY_FILENAME = "field_development_metrics_quality.json"
MANIFEST_FILENAME = "manifest.json"
METRIC_DTYPES = {
    "district": "string",
    "field_number": "string",
    "field_name": "string",
    "top_operator_number": "string",
    "top_operator_name": "string",
}


@dataclass(frozen=True)
class FieldDevelopmentOutputManifest:
    """Paths and metadata for one field-development metrics output batch."""

    generated_at: str
    output_root: Path
    csv_path: Path
    parquet_path: Path
    quality_path: Path
    manifest_path: Path
    row_count: int
    input_paths: tuple[str, ...]
    source_gaps: tuple[str, ...]
    command: str | None
    code_revision: str | None


def write_field_development_outputs(
    metrics: pd.DataFrame,
    quality: FieldDevelopmentQualityReport,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> FieldDevelopmentOutputManifest:
    """Write field-development CSV, Parquet, quality JSON, and manifest."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    target_dir = root / FIELD_DEVELOPMENT_METRICS_DIR
    stamp = _timestamp(generated_at)
    manifest = FieldDevelopmentOutputManifest(
        generated_at=stamp,
        output_root=root,
        csv_path=target_dir / CSV_FILENAME,
        parquet_path=target_dir / PARQUET_FILENAME,
        quality_path=target_dir / QUALITY_FILENAME,
        manifest_path=target_dir / MANIFEST_FILENAME,
        row_count=len(metrics),
        input_paths=tuple(str(path) for path in input_paths),
        source_gaps=tuple(quality.source_gaps),
        command=command,
        code_revision=code_revision or _git_revision(),
    )
    _write_with_staging(metrics, quality, manifest, target_dir, stamp)
    return manifest


def load_field_development_metrics(path: Path | str) -> pd.DataFrame:
    """Load persisted field-development metrics from CSV or Parquet."""
    metrics_path = Path(path)
    if metrics_path.suffix.lower() == ".parquet":
        return pd.read_parquet(metrics_path)
    return pd.read_csv(metrics_path, dtype=METRIC_DTYPES)


def _write_with_staging(
    metrics: pd.DataFrame,
    quality: FieldDevelopmentQualityReport,
    manifest: FieldDevelopmentOutputManifest,
    target_dir: Path,
    stamp: str,
) -> None:
    staging = target_dir / f".staging-field-development-metrics-{_compact_stamp(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        staging.mkdir(parents=True, exist_ok=False)
        metrics.to_csv(staging / CSV_FILENAME, index=False)
        metrics.to_parquet(staging / PARQUET_FILENAME, index=False)
        _write_json(staging / QUALITY_FILENAME, _quality_payload(quality))
        _write_json(staging / MANIFEST_FILENAME, _manifest_payload(manifest, quality))
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename in (
            CSV_FILENAME,
            PARQUET_FILENAME,
            QUALITY_FILENAME,
            MANIFEST_FILENAME,
        ):
            (staging / filename).replace(target_dir / filename)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(SOURCE_CATALOG_ROOT.resolve()):
        raise ValueError(
            "Field-development output_root must stay under "
            f"{SOURCE_CATALOG_ROOT}; pass allow_non_ace_root=True only for "
            "isolated tests or sandbox runs"
        )


def _quality_payload(quality: FieldDevelopmentQualityReport) -> dict[str, object]:
    return asdict(quality)


def _manifest_payload(
    manifest: FieldDevelopmentOutputManifest,
    quality: FieldDevelopmentQualityReport,
) -> dict[str, object]:
    return {
        "generated_at": manifest.generated_at,
        "output_root": str(manifest.output_root),
        "csv_path": str(manifest.csv_path),
        "parquet_path": str(manifest.parquet_path),
        "quality_path": str(manifest.quality_path),
        "manifest_path": str(manifest.manifest_path),
        "row_count": manifest.row_count,
        "input_paths": list(manifest.input_paths),
        "source_gaps": list(manifest.source_gaps),
        "command": manifest.command,
        "code_revision": manifest.code_revision,
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


def _git_revision() -> str | None:
    repo_root = Path(__file__).resolve().parents[5]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    suffix = "+dirty" if status.stdout.strip() else ""
    value = revision.stdout.strip()
    return f"{value}{suffix}" if value else None


__all__ = [
    "CSV_FILENAME",
    "FIELD_DEVELOPMENT_METRICS_DIR",
    "FieldDevelopmentOutputManifest",
    "load_field_development_metrics",
    "write_field_development_outputs",
]
