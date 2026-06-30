"""Persist Texas RRC production atlas outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Iterable, Sequence

import pandas as pd

from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

PRODUCTION_ATLAS_DIR = Path("curated") / "production" / "field_atlas"
CSV_FILENAME = "production_field_atlas.csv"
PARQUET_FILENAME = "production_field_atlas.parquet"
QUALITY_FILENAME = "production_field_atlas_quality.json"
MANIFEST_FILENAME = "manifest.json"


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


def write_production_atlas_outputs(
    atlas: pd.DataFrame,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    source_gaps: Sequence[str] = (),
    allow_non_ace_root: bool = False,
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
        "source_ids": ["production_pdq"],
        "quality": _quality_payload(atlas, source_gaps),
    }


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
