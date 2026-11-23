"""CLI support for Texas RRC pressure-observation publishing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from worldenergydata.texas_rrc.pressure_observations.io import (
    PressureObservationOutputManifest,
    write_pressure_observation_outputs,
)
from worldenergydata.texas_rrc.pressure_observations.observations import (
    build_pressure_observations,
)
from worldenergydata.texas_rrc.pressure_observations.quality import (
    build_pressure_coverage,
)
from worldenergydata.texas_rrc.pressure_observations.sources import (
    load_pressure_observation_inputs,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT


@dataclass(frozen=True)
class PressureObservationBuildResult:
    """Result returned by the pressure-observation publisher."""

    row_count: int
    candidate_count: int
    source_gaps: tuple[str, ...]
    source_warnings: tuple[str, ...]
    dry_run: bool
    manifest: PressureObservationOutputManifest | None


def run_build_pressure_observations(
    raw_root: Path | str = SOURCE_CATALOG_ROOT,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    dry_run: bool = False,
    require_sources: bool = False,
    allow_non_ace_output: bool = False,
) -> PressureObservationBuildResult:
    """Build and optionally write Texas RRC pressure-observation outputs."""
    source_root = Path(raw_root)
    target_root = Path(output_root)
    inputs = load_pressure_observation_inputs(source_root)
    if inputs.source_gaps and (require_sources or not dry_run):
        raise ValueError(
            "Cannot build pressure observations with missing sources: "
            + ", ".join(inputs.source_gaps)
        )

    observation_result, coverage, quality = _prepare_pressure_outputs(inputs)
    if dry_run:
        return PressureObservationBuildResult(
            row_count=len(observation_result.observations),
            candidate_count=len(inputs.candidates),
            source_gaps=inputs.source_gaps,
            source_warnings=inputs.source_warnings,
            dry_run=True,
            manifest=None,
        )

    manifest = _write_outputs(
        source_root=source_root,
        target_root=target_root,
        inputs=inputs,
        observations=observation_result.observations,
        coverage=coverage,
        quality=quality,
        allow_non_ace_output=allow_non_ace_output,
        require_sources=require_sources,
    )
    return PressureObservationBuildResult(
        row_count=len(observation_result.observations),
        candidate_count=len(inputs.candidates),
        source_gaps=inputs.source_gaps,
        source_warnings=inputs.source_warnings,
        dry_run=False,
        manifest=manifest,
    )


def _prepare_pressure_outputs(inputs):
    wellbore = _wellbore_for_candidates(inputs.wellbore, inputs.candidates)
    observation_result = build_pressure_observations(inputs.candidates, wellbore)
    coverage = build_pressure_coverage(observation_result.observations)
    quality = _quality_payload(
        inputs.parser_quality,
        observation_result.quality,
        observation_result.observations,
    )
    return observation_result, coverage, quality


def _quality_payload(
    parser_quality: dict[str, int],
    observation_quality: dict[str, int],
    observations,
) -> dict[str, object]:
    quality: dict[str, object] = {}
    quality.update(parser_quality)
    quality.update(observation_quality)
    quality.update(_observation_quality_counts(observations))
    return quality


def _observation_quality_counts(observations) -> dict[str, object]:
    return {
        "pressure_kind_counts": _column_counts(observations, "pressure_kind"),
        "pressure_unit_basis_counts": _column_counts(
            observations, "pressure_unit_basis"
        ),
        "reference_depth_method_counts": _column_counts(
            observations, "reference_depth_method"
        ),
        "gradient_method_counts": _column_counts(observations, "gradient_method"),
    }


def _column_counts(frame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame:
        return {}
    values = frame[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    counts = values.value_counts(sort=False).sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def _write_outputs(
    *,
    source_root: Path,
    target_root: Path,
    inputs,
    observations,
    coverage,
    quality: dict[str, object],
    allow_non_ace_output: bool,
    require_sources: bool,
) -> PressureObservationOutputManifest:
    return write_pressure_observation_outputs(
        observations=observations,
        candidates=inputs.candidates,
        coverage_by_district_decade=coverage.by_district_decade,
        coverage_by_field_decade=coverage.by_field_decade,
        quality=quality,
        output_root=target_root,
        input_paths=inputs.input_paths,
        input_artifacts=inputs.input_artifacts,
        source_gaps=inputs.source_gaps,
        source_warnings=inputs.source_warnings,
        allow_non_ace_root=allow_non_ace_output,
        command=_command(source_root, target_root, require_sources),
    )


def _wellbore_for_candidates(candidates_wellbore, candidates):
    if (
        candidates_wellbore.empty
        or candidates.empty
        or "api14" not in candidates_wellbore
        or "api14" not in candidates
    ):
        return candidates_wellbore
    api14s = set(candidates["api14"].dropna().astype(str))
    if not api14s:
        return candidates_wellbore.iloc[0:0].copy()
    return candidates_wellbore[candidates_wellbore["api14"].astype(str).isin(api14s)]


def _command(root: Path, output_root: Path, require_sources: bool) -> str:
    parts = [
        "worldenergydata",
        "texas-rrc",
        "build-pressure-observations",
        "--raw-root",
        str(root),
        "--output-root",
        str(output_root),
    ]
    if require_sources:
        parts.append("--require-sources")
    return " ".join(parts)


__all__ = [
    "PressureObservationBuildResult",
    "run_build_pressure_observations",
]
