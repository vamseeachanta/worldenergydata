"""CLI support for publishing Texas RRC field-opportunity rankings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from worldenergydata.texas_rrc.opportunities.io import (
    FieldOpportunityOutputManifest,
    write_field_opportunity_outputs,
)
from worldenergydata.texas_rrc.opportunities.quality import (
    assess_field_opportunity_quality,
)
from worldenergydata.texas_rrc.opportunities.scoring import (
    build_field_opportunity_rankings,
)
from worldenergydata.texas_rrc.opportunities.sources import (
    load_field_opportunity_inputs,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT


@dataclass(frozen=True)
class FieldOpportunityBuildResult:
    """Result returned by the field-opportunity publisher."""

    row_count: int
    source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldOpportunityOutputManifest | None


def run_build_field_opportunities(
    root: Path | str = SOURCE_CATALOG_ROOT,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    dry_run: bool = False,
    require_sources: bool = False,
    allow_non_ace_output: bool = False,
    max_fields: int | None = None,
) -> FieldOpportunityBuildResult:
    """Build and optionally write Texas RRC field-opportunity outputs."""
    source_root = Path(root)
    target_root = Path(output_root)
    inputs = load_field_opportunity_inputs(source_root)
    if inputs.source_gaps and (require_sources or not dry_run):
        raise ValueError(
            "Cannot build field-opportunity rankings with missing sources: "
            + ", ".join(inputs.source_gaps)
        )
    rankings = build_field_opportunity_rankings(inputs)
    if max_fields is not None:
        rankings = rankings.head(max_fields).copy()
    quality = assess_field_opportunity_quality(rankings, inputs.source_gaps)
    if dry_run:
        return FieldOpportunityBuildResult(
            row_count=len(rankings),
            source_gaps=inputs.source_gaps,
            dry_run=True,
            manifest=None,
        )
    manifest = write_field_opportunity_outputs(
        rankings=rankings,
        quality=quality,
        output_root=target_root,
        input_paths=inputs.input_paths,
        upstream_manifests=inputs.upstream_manifests,
        allow_non_ace_root=allow_non_ace_output,
        command=_command(source_root, target_root, require_sources, max_fields),
    )
    return FieldOpportunityBuildResult(
        row_count=len(rankings),
        source_gaps=inputs.source_gaps,
        dry_run=False,
        manifest=manifest,
    )


def _command(
    root: Path,
    output_root: Path,
    require_sources: bool,
    max_fields: int | None,
) -> str:
    parts = [
        "worldenergydata",
        "texas-rrc",
        "build-field-opportunities",
        "--root",
        str(root),
        "--output-root",
        str(output_root),
    ]
    if require_sources:
        parts.append("--require-sources")
    if max_fields is not None:
        parts.extend(["--max-fields", str(max_fields)])
    return " ".join(parts)


__all__ = [
    "FieldOpportunityBuildResult",
    "run_build_field_opportunities",
]
