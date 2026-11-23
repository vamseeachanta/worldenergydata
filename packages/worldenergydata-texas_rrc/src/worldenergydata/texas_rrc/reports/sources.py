"""Load direct curated inputs for Texas RRC field-atlas reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from worldenergydata.texas_rrc.field_development.io import (
    CSV_FILENAME as FIELD_DEVELOPMENT_CSV,
)
from worldenergydata.texas_rrc.field_development.io import (
    FIELD_DEVELOPMENT_METRICS_DIR,
)
from worldenergydata.texas_rrc.field_development.io import (
    MANIFEST_FILENAME as FIELD_DEVELOPMENT_MANIFEST,
)
from worldenergydata.texas_rrc.field_development.io import (
    PARQUET_FILENAME as FIELD_DEVELOPMENT_PARQUET,
)
from worldenergydata.texas_rrc.field_development.io import (
    load_field_development_metrics,
)
from worldenergydata.texas_rrc.infrastructure.io import (
    CSV_FILENAME as INFRASTRUCTURE_CSV,
)
from worldenergydata.texas_rrc.infrastructure.io import (
    INFRASTRUCTURE_ACCESS_DIR,
)
from worldenergydata.texas_rrc.infrastructure.io import (
    MANIFEST_FILENAME as INFRASTRUCTURE_MANIFEST,
)
from worldenergydata.texas_rrc.infrastructure.io import (
    PARQUET_FILENAME as INFRASTRUCTURE_PARQUET,
)
from worldenergydata.texas_rrc.infrastructure.io import (
    load_infrastructure_access_metrics,
)
from worldenergydata.texas_rrc.production_atlas.io import CSV_FILENAME as PRODUCTION_CSV
from worldenergydata.texas_rrc.production_atlas.io import (
    MANIFEST_FILENAME as PRODUCTION_MANIFEST,
)
from worldenergydata.texas_rrc.production_atlas.io import (
    PARQUET_FILENAME as PRODUCTION_PARQUET,
)
from worldenergydata.texas_rrc.production_atlas.io import (
    PRODUCTION_ATLAS_DIR,
    load_production_atlas,
)

Loader = Callable[[Path], pd.DataFrame]


@dataclass(frozen=True)
class FieldAtlasReportInputs:
    """Direct curated inputs used to publish field-atlas reports."""

    field_development: pd.DataFrame
    infrastructure_access: pd.DataFrame
    production_atlas: pd.DataFrame
    input_paths: tuple[Path, ...]
    source_gaps: tuple[str, ...]


def load_field_atlas_report_inputs(root: Path | str) -> FieldAtlasReportInputs:
    """Load the curated source artifacts used by field-atlas reports."""
    catalog_root = Path(root)
    field_df, field_paths, field_gaps = _load_source(
        catalog_root,
        FIELD_DEVELOPMENT_METRICS_DIR,
        FIELD_DEVELOPMENT_CSV,
        FIELD_DEVELOPMENT_PARQUET,
        FIELD_DEVELOPMENT_MANIFEST,
        load_field_development_metrics,
        "missing_field_development_metrics",
    )
    infra_df, infra_paths, infra_gaps = _load_source(
        catalog_root,
        INFRASTRUCTURE_ACCESS_DIR,
        INFRASTRUCTURE_CSV,
        INFRASTRUCTURE_PARQUET,
        INFRASTRUCTURE_MANIFEST,
        load_infrastructure_access_metrics,
        "missing_infrastructure_access_metrics",
    )
    prod_df, prod_paths, prod_gaps = _load_source(
        catalog_root,
        PRODUCTION_ATLAS_DIR,
        PRODUCTION_CSV,
        PRODUCTION_PARQUET,
        PRODUCTION_MANIFEST,
        load_production_atlas,
        "missing_production_field_atlas",
    )
    return FieldAtlasReportInputs(
        field_development=field_df,
        infrastructure_access=infra_df,
        production_atlas=prod_df,
        input_paths=field_paths + infra_paths + prod_paths,
        source_gaps=field_gaps + infra_gaps + prod_gaps,
    )


def _load_source(
    root: Path,
    source_dir: Path,
    csv_filename: str,
    parquet_filename: str,
    manifest_filename: str,
    loader: Loader,
    missing_gap: str,
) -> tuple[pd.DataFrame, tuple[Path, ...], tuple[str, ...]]:
    directory = root / source_dir
    data_path = _existing_data_path(directory, csv_filename, parquet_filename)
    manifest_path = directory / manifest_filename
    paths = (data_path,) if data_path else ()
    if manifest_path.exists():
        paths = paths + (manifest_path,)
    if data_path is None:
        return pd.DataFrame(), paths, (missing_gap,)
    gaps = _manifest_source_gaps(manifest_path)
    return loader(data_path), paths, gaps


def _existing_data_path(
    directory: Path, csv_filename: str, parquet_filename: str
) -> Path | None:
    parquet_path = directory / parquet_filename
    if parquet_path.exists():
        return parquet_path
    csv_path = directory / csv_filename
    return csv_path if csv_path.exists() else None


def _manifest_source_gaps(manifest_path: Path) -> tuple[str, ...]:
    if not manifest_path.exists():
        return ()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ("unreadable_manifest",)
    gaps = _string_sequence(payload.get("source_gaps"))
    if not gaps and isinstance(payload.get("quality"), dict):
        gaps = _string_sequence(payload["quality"].get("source_gaps"))
    return tuple(gaps)


def _string_sequence(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


__all__ = [
    "FieldAtlasReportInputs",
    "load_field_atlas_report_inputs",
]
