"""Persist Texas RRC infrastructure access metric outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.infrastructure.quality import (
    DIRECT_SOURCE_CAVEATS,
    SCORING_THRESHOLDS_MILES,
    InfrastructureAccessQualityReport,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

INFRASTRUCTURE_ACCESS_DIR = Path("curated") / "infrastructure" / "access"
CSV_FILENAME = "field_infrastructure_access.csv"
PARQUET_FILENAME = "field_infrastructure_access.parquet"
QUALITY_FILENAME = "field_infrastructure_access_quality.json"
MANIFEST_FILENAME = "manifest.json"
METRIC_DTYPES = {
    "district": "string",
    "field_number": "string",
    "field_name": "string",
    "nearest_pipeline_source_county": "string",
    "nearest_pipeline_identifier": "string",
}


@dataclass(frozen=True)
class InfrastructureAccessOutputManifest:
    """Paths and metadata for one infrastructure access output batch."""

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


def write_infrastructure_access_outputs(
    metrics: pd.DataFrame,
    quality: InfrastructureAccessQualityReport,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> InfrastructureAccessOutputManifest:
    """Write CSV, Parquet, quality JSON, and manifest outputs."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    target_dir = root / INFRASTRUCTURE_ACCESS_DIR
    stamp = _timestamp(generated_at)
    manifest = InfrastructureAccessOutputManifest(
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


def load_infrastructure_access_metrics(path: Path | str) -> pd.DataFrame:
    """Load persisted infrastructure access metrics from CSV or Parquet."""
    metrics_path = Path(path)
    if metrics_path.suffix.lower() == ".parquet":
        return pd.read_parquet(metrics_path)
    return pd.read_csv(metrics_path, dtype=METRIC_DTYPES)


def _write_with_staging(
    metrics: pd.DataFrame,
    quality: InfrastructureAccessQualityReport,
    manifest: InfrastructureAccessOutputManifest,
    target_dir: Path,
    stamp: str,
) -> None:
    staging = target_dir / f".staging-infrastructure-access-{_compact_stamp(stamp)}"
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
            "Infrastructure access output_root must stay under "
            f"{SOURCE_CATALOG_ROOT}; pass allow_non_ace_root=True only for "
            "isolated tests or sandbox runs"
        )


def _quality_payload(quality: InfrastructureAccessQualityReport) -> dict[str, object]:
    return asdict(quality)


def _manifest_payload(
    manifest: InfrastructureAccessOutputManifest,
    quality: InfrastructureAccessQualityReport,
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
        "scoring_thresholds_miles": SCORING_THRESHOLDS_MILES,
        "direct_source_caveats": DIRECT_SOURCE_CAVEATS,
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
            timeout=5,
        )
        value = revision.stdout.strip()
        if not value:
            return None
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    except subprocess.TimeoutExpired:
        return value
    suffix = "+dirty" if status.stdout.strip() else ""
    return f"{value}{suffix}"


__all__ = [
    "CSV_FILENAME",
    "INFRASTRUCTURE_ACCESS_DIR",
    "InfrastructureAccessOutputManifest",
    "load_infrastructure_access_metrics",
    "write_infrastructure_access_outputs",
]
