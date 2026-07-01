"""Load curated Texas RRC inputs for field-development metrics."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.lifecycle.io import (
    LIFECYCLE_SPINE_DIR,
    QUALITY_FILENAME as LIFECYCLE_QUALITY_FILENAME,
    SPINE_FILENAME,
    load_lifecycle_spine,
)
from worldenergydata.texas_rrc.production_atlas.io import (
    CSV_FILENAME as PRODUCTION_CSV_FILENAME,
    PARQUET_FILENAME as PRODUCTION_PARQUET_FILENAME,
    PRODUCTION_ATLAS_DIR,
    QUALITY_FILENAME as PRODUCTION_QUALITY_FILENAME,
    load_production_atlas,
)


@dataclass(frozen=True)
class FieldDevelopmentInputs:
    """Curated lifecycle and production inputs for field-development metrics."""

    lifecycle: pd.DataFrame
    production: pd.DataFrame
    lifecycle_quality: dict[str, object]
    production_quality: dict[str, object]
    source_gaps: tuple[str, ...]


def load_field_development_inputs(root: Path | str) -> FieldDevelopmentInputs:
    """Load curated lifecycle and production inputs from a local Texas RRC root."""
    local_root = _local_root(root)
    source_gaps: list[str] = []

    lifecycle = _load_lifecycle(local_root, source_gaps)
    production = _load_production(local_root, source_gaps)
    lifecycle_quality = _load_quality(
        local_root / LIFECYCLE_SPINE_DIR / LIFECYCLE_QUALITY_FILENAME,
        "well_lifecycle_quality",
        source_gaps,
    )
    production_quality = _load_quality(
        local_root / PRODUCTION_ATLAS_DIR / PRODUCTION_QUALITY_FILENAME,
        "production_field_atlas_quality",
        source_gaps,
    )

    return FieldDevelopmentInputs(
        lifecycle=lifecycle,
        production=production,
        lifecycle_quality=lifecycle_quality,
        production_quality=production_quality,
        source_gaps=tuple(source_gaps),
    )


def _local_root(root: Path | str) -> Path:
    value = str(root)
    if "://" in value:
        raise ValueError("Field-development inputs must be local filesystem paths")
    return Path(root)


def _load_lifecycle(root: Path, source_gaps: list[str]) -> pd.DataFrame:
    path = root / LIFECYCLE_SPINE_DIR / SPINE_FILENAME
    if not path.exists():
        source_gaps.append("well_lifecycle_spine")
        return pd.DataFrame()
    return load_lifecycle_spine(path)


def _load_production(root: Path, source_gaps: list[str]) -> pd.DataFrame:
    path = _production_path(root)
    if path is None:
        source_gaps.append("production_field_atlas")
        return pd.DataFrame()
    production = load_production_atlas(path)
    if "aggregation_level" not in production.columns:
        return production.iloc[0:0].copy()
    fields = production[production["aggregation_level"] == "field"].copy()
    return fields.reset_index(drop=True)


def _production_path(root: Path) -> Path | None:
    atlas_dir = root / PRODUCTION_ATLAS_DIR
    parquet_path = atlas_dir / PRODUCTION_PARQUET_FILENAME
    if parquet_path.exists():
        return parquet_path
    csv_path = atlas_dir / PRODUCTION_CSV_FILENAME
    if csv_path.exists():
        return csv_path
    return None


def _load_quality(
    path: Path,
    gap_name: str,
    source_gaps: list[str],
) -> dict[str, object]:
    if not path.exists():
        source_gaps.append(gap_name)
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        source_gaps.append(gap_name)
        return {}
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "FieldDevelopmentInputs",
    "load_field_development_inputs",
]
