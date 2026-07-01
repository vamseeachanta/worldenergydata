"""CLI support for building Texas RRC infrastructure access metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
from worldenergydata.texas_rrc.infrastructure.access_metrics import (
    InfrastructureAccessInputs,
    build_infrastructure_access_metrics,
)
from worldenergydata.texas_rrc.infrastructure.gis_sources import (
    load_gis_inputs,
)
from worldenergydata.texas_rrc.infrastructure.io import (
    write_infrastructure_access_outputs,
)
from worldenergydata.texas_rrc.infrastructure.quality import (
    assess_infrastructure_access_quality,
)
from worldenergydata.texas_rrc.lifecycle.io import (
    LIFECYCLE_SPINE_DIR,
)
from worldenergydata.texas_rrc.lifecycle.io import (
    MANIFEST_FILENAME as LIFECYCLE_MANIFEST,
)
from worldenergydata.texas_rrc.lifecycle.io import (
    SPINE_FILENAME,
    load_lifecycle_spine,
)


@dataclass(frozen=True)
class InfrastructureAccessBuildResult:
    """Result returned to the Typer command for printing and exit handling."""

    row_count: int
    source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: object | None


@dataclass(frozen=True)
class CuratedInputs:
    """Curated non-GIS inputs for infrastructure metrics."""

    field_development: pd.DataFrame
    lifecycle: pd.DataFrame
    source_gaps: tuple[str, ...]
    input_paths: tuple[str, ...]


def run_build_infrastructure_access_metrics(
    root: Path,
    output_root: Path,
    dry_run: bool,
    require_sources: bool,
    refresh_gis: bool,
    nearby_radius_miles: float,
    allow_non_ace_output: bool,
    rows_per_page: int,
) -> InfrastructureAccessBuildResult:
    """Build and optionally persist infrastructure access metrics."""
    if refresh_gis:
        refresh_gis_sources(root, rows_per_page)
    curated = load_curated_inputs(root)
    gis = load_gis_inputs(root)
    source_gaps = tuple(dict.fromkeys((*curated.source_gaps, *gis.source_gaps)))
    if source_gaps and (require_sources or not dry_run):
        raise ValueError(f"missing infrastructure sources: {', '.join(source_gaps)}")
    metrics = build_infrastructure_access_metrics(
        InfrastructureAccessInputs(
            field_development=curated.field_development,
            lifecycle=curated.lifecycle,
            well_gis=gis.well_gis,
            pipeline_gis=gis.pipeline_gis,
            source_gaps=source_gaps,
        ),
        nearby_radius_miles=nearby_radius_miles,
    )
    quality = assess_infrastructure_access_quality(
        metrics,
        source_gaps=source_gaps,
        malformed_source_files=gis.malformed_source_files,
    )
    if dry_run:
        return InfrastructureAccessBuildResult(len(metrics), source_gaps, True, None)
    manifest = write_infrastructure_access_outputs(
        metrics,
        quality,
        output_root=output_root,
        input_paths=(*curated.input_paths, *gis.input_paths),
        allow_non_ace_root=allow_non_ace_output,
        command=(
            "worldenergydata texas-rrc build-infrastructure-access-metrics "
            f"--root {root} --output-root {output_root}"
        ),
    )
    return InfrastructureAccessBuildResult(len(metrics), source_gaps, False, manifest)


def refresh_gis_sources(root: Path, rows_per_page: int) -> None:
    """Refresh official RRC well and pipeline GIS directory sources."""
    import worldenergydata.texas_rrc.raw_refresh as raw_refresh

    refresher = raw_refresh.RawSnapshotRefresher(output_root=root)
    for source_id in ("well_gis_layers", "pipeline_gis_layers"):
        refresher.refresh_source(source_id, rows_per_page=rows_per_page)


def load_curated_inputs(root: Path | str) -> CuratedInputs:
    """Load #664 field-development metrics and lifecycle spine."""
    local_root = Path(root)
    source_gaps: list[str] = []
    input_paths: list[str] = []
    field_development = _load_field_development(local_root, source_gaps, input_paths)
    lifecycle = _load_lifecycle(local_root, source_gaps, input_paths)
    return CuratedInputs(
        field_development=field_development,
        lifecycle=lifecycle,
        source_gaps=tuple(source_gaps),
        input_paths=tuple(input_paths),
    )


def _load_field_development(
    root: Path,
    source_gaps: list[str],
    input_paths: list[str],
) -> pd.DataFrame:
    metrics_dir = root / FIELD_DEVELOPMENT_METRICS_DIR
    parquet_path = metrics_dir / FIELD_DEVELOPMENT_PARQUET
    csv_path = metrics_dir / FIELD_DEVELOPMENT_CSV
    path = parquet_path if parquet_path.exists() else csv_path
    if not path.exists():
        source_gaps.append("field_development_metrics")
        return pd.DataFrame()
    input_paths.append(str(path))
    manifest_path = metrics_dir / FIELD_DEVELOPMENT_MANIFEST
    if manifest_path.exists():
        input_paths.append(str(manifest_path))
    return load_field_development_metrics(path)


def _load_lifecycle(
    root: Path,
    source_gaps: list[str],
    input_paths: list[str],
) -> pd.DataFrame:
    spine_dir = root / LIFECYCLE_SPINE_DIR
    spine_path = spine_dir / SPINE_FILENAME
    if not spine_path.exists():
        source_gaps.append("well_lifecycle_spine")
        return pd.DataFrame()
    input_paths.append(str(spine_path))
    manifest_path = spine_dir / LIFECYCLE_MANIFEST
    if manifest_path.exists():
        input_paths.append(str(manifest_path))
    return load_lifecycle_spine(spine_path)


__all__ = [
    "InfrastructureAccessBuildResult",
    "load_curated_inputs",
    "refresh_gis_sources",
    "run_build_infrastructure_access_metrics",
]
