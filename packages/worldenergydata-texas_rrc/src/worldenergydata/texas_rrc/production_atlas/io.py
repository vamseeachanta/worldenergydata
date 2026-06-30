"""Persist Texas RRC production atlas outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from typing import Iterable, Sequence

import pandas as pd

from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

PRODUCTION_ATLAS_DIR = Path("curated") / "production" / "field_atlas"
CSV_FILENAME = "production_field_atlas.csv"
PARQUET_FILENAME = "production_field_atlas.parquet"
QUALITY_FILENAME = "production_field_atlas_quality.json"
MANIFEST_FILENAME = "manifest.json"
SOURCE_METADATA_FIELDS = (
    "source_id",
    "source_url",
    "download_url",
    "effective_url",
    "checksum_sha256",
    "byte_size",
    "retrieved_at",
    "refresh_cadence",
)


@dataclass(frozen=True)
class ProductionAtlasOutputManifest:
    """Paths and metadata for one production atlas output batch."""

    generated_at: str
    output_root: Path
    csv_path: Path
    parquet_path: Path
    quality_path: Path
    manifest_path: Path
    row_count: int
    input_paths: tuple[str, ...]
    command: str | None
    code_revision: str | None


def write_production_atlas_outputs(
    atlas: pd.DataFrame,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    source_gaps: Sequence[str] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> ProductionAtlasOutputManifest:
    """Write production atlas CSV, Parquet, quality JSON, and manifest."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    target_dir = root / PRODUCTION_ATLAS_DIR
    stamp = _timestamp(generated_at)
    manifest = ProductionAtlasOutputManifest(
        generated_at=stamp,
        output_root=root,
        csv_path=target_dir / CSV_FILENAME,
        parquet_path=target_dir / PARQUET_FILENAME,
        quality_path=target_dir / QUALITY_FILENAME,
        manifest_path=target_dir / MANIFEST_FILENAME,
        row_count=len(atlas),
        input_paths=tuple(str(path) for path in input_paths),
        command=command,
        code_revision=code_revision or _git_revision(),
    )
    staging = target_dir / f".staging-production-field-atlas-{_compact_stamp(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        staging.mkdir(parents=True, exist_ok=False)
        atlas.to_csv(staging / CSV_FILENAME, index=False)
        atlas.to_parquet(staging / PARQUET_FILENAME, index=False)
        _write_json(staging / QUALITY_FILENAME, _quality_payload(atlas, source_gaps))
        _write_json(
            staging / MANIFEST_FILENAME,
            _manifest_payload(manifest, atlas, source_gaps),
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename in (
            CSV_FILENAME,
            PARQUET_FILENAME,
            QUALITY_FILENAME,
            MANIFEST_FILENAME,
        ):
            (staging / filename).replace(target_dir / filename)
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def load_production_atlas(path: Path | str) -> pd.DataFrame:
    """Load a persisted production atlas from CSV or Parquet."""
    atlas_path = Path(path)
    if atlas_path.suffix.lower() == ".parquet":
        return pd.read_parquet(atlas_path)
    return pd.read_csv(atlas_path, dtype=_atlas_dtypes())


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(SOURCE_CATALOG_ROOT.resolve()):
        raise ValueError(
            "Production atlas output_root must stay under "
            f"{SOURCE_CATALOG_ROOT}; pass allow_non_ace_root=True only for "
            "isolated tests or sandbox runs"
        )


def _quality_payload(
    atlas: pd.DataFrame, source_gaps: Sequence[str]
) -> dict[str, object]:
    levels = []
    if "aggregation_level" in atlas:
        levels = sorted(
            str(level) for level in atlas["aggregation_level"].dropna().unique()
        )
    return {
        "row_count": len(atlas),
        "aggregation_levels": levels,
        "source_gaps": list(source_gaps),
        "metric_gaps": _metric_gaps(atlas),
        "source_ids": ["production_pdq"],
    }


def _manifest_payload(
    manifest: ProductionAtlasOutputManifest,
    atlas: pd.DataFrame,
    source_gaps: Sequence[str],
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
        "sources": _source_payloads(manifest.output_root, manifest.input_paths),
        "source_ids": ["production_pdq"],
        "command": manifest.command,
        "code_revision": manifest.code_revision,
        "quality": _quality_payload(atlas, source_gaps),
    }


def _metric_gaps(atlas: pd.DataFrame) -> list[str]:
    gaps = []
    for column in ("cumulative_water_bbl", "well_count_peak"):
        if column in atlas and atlas[column].isna().all():
            gaps.append(
                "water_bbl" if column == "cumulative_water_bbl" else "well_count"
            )
    return gaps


def _source_payloads(
    root: Path, input_paths: tuple[str, ...]
) -> list[dict[str, object]]:
    raw_manifests = _raw_manifest_payloads(root)
    sources = []
    for input_path in input_paths:
        source = {"input_path": input_path}
        raw_manifest_path, raw_manifest = _matching_raw_manifest(
            input_path, raw_manifests
        )
        if raw_manifest:
            source.update(
                {
                    field: raw_manifest[field]
                    for field in SOURCE_METADATA_FIELDS
                    if field in raw_manifest
                }
            )
            source["manifest_path"] = str(raw_manifest_path)
        sources.append(source)
    return sources


def _raw_manifest_payloads(root: Path) -> list[tuple[Path, dict[str, object]]]:
    manifest_dir = root / "manifests"
    if not manifest_dir.exists():
        return []
    payloads = []
    for path in sorted(manifest_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            payloads.append((path, payload))
    return payloads


def _matching_raw_manifest(
    input_path: str,
    raw_manifests: list[tuple[Path, dict[str, object]]],
) -> tuple[Path | None, dict[str, object] | None]:
    input_keys = _path_keys(input_path)
    for path, payload in raw_manifests:
        raw_path = payload.get("raw_path")
        if raw_path and input_keys.intersection(_path_keys(str(raw_path))):
            return path, payload
    return None, None


def _path_keys(value: str) -> set[str]:
    path = Path(value)
    return {str(path), str(path.resolve())}


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
    return f"{revision.stdout.strip()}{suffix}" if revision.stdout.strip() else None


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _timestamp(value: datetime | None) -> str:
    timestamp = value or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact_stamp(stamp: str) -> str:
    return stamp.replace("-", "").replace(":", "")


def _atlas_dtypes() -> dict[str, str]:
    return {
        "district": "string",
        "field_number": "string",
        "field_name": "string",
        "lease_number": "string",
        "lease_name": "string",
        "operator_number": "string",
        "operator_name": "string",
    }
