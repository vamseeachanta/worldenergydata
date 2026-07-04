"""CLI support for Kansas KGS pressure-observation builds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from worldenergydata.kansas_kgs.io import (
    PressureObservationOutputManifest,
    write_pressure_observation_outputs,
)
from worldenergydata.kansas_kgs.observations import build_pressure_observations
from worldenergydata.kansas_kgs.pressure import parse_proration_pressure
from worldenergydata.kansas_kgs.raw_sources import (
    DEFAULT_KANSAS_KGS_ROOT,
    ensure_raw_sources,
)
from worldenergydata.kansas_kgs.wells import parse_wells_master


@dataclass(frozen=True)
class PressureObservationBuildResult:
    """Summary from one pressure-observation CLI build."""

    row_count: int
    quality: dict[str, object]
    manifest: PressureObservationOutputManifest | None


def build_pressure_observation_packet(
    root: Path | str = DEFAULT_KANSAS_KGS_ROOT,
    dry_run: bool = False,
    refresh: bool = False,
    allow_non_ace_root: bool = False,
) -> PressureObservationBuildResult:
    """Build normalized and curated Kansas KGS pressure outputs."""
    root_path = Path(root)
    ensure_raw_sources(
        root_path,
        refresh=refresh,
        allow_non_ace_root=allow_non_ace_root,
    )
    raw_manifest_path = root_path / "raw/manifest.json"
    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    pressure_result = parse_proration_pressure(
        root_path / "raw/pressure/kansas_proration_pressures.txt"
    )
    wells = parse_wells_master(root_path / "raw/wells/ks_wells.zip")
    result = build_pressure_observations(pressure_result.normalized, wells)
    combined_quality = {
        **pressure_result.quality,
        **wells.attrs.get("quality", {}),
        **result.quality,
    }
    if dry_run:
        return PressureObservationBuildResult(
            row_count=len(result.observations),
            quality=combined_quality,
            manifest=None,
        )
    manifest = write_pressure_observation_outputs(
        normalized_pressure=pressure_result.normalized,
        normalized_wells=wells,
        observations=result.observations,
        coverage=result.coverage,
        quality=combined_quality,
        output_root=root_path,
        input_paths=[
            raw_manifest_path,
            root_path / "raw/pressure/kansas_proration_pressures.txt",
            root_path / "raw/wells/ks_wells.zip",
        ],
        source_manifest=raw_manifest,
        limitations=_limitations(result.observations),
        allow_non_ace_root=allow_non_ace_root,
        command="worldenergydata kansas-kgs build-pressure-observations",
    )
    return PressureObservationBuildResult(
        row_count=len(result.observations),
        quality=combined_quality,
        manifest=manifest,
    )


def _limitations(observations: pd.DataFrame) -> list[str]:
    if observations.empty or "limitations" not in observations:
        return []
    return sorted(
        {
            limitation
            for value in observations["limitations"].dropna().astype(str)
            for limitation in value.split("|")
            if limitation
        }
    )
