"""CLI support for publishing Texas RRC field-architecture dossiers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.dossiers.io import (
    FieldArchitectureDossierOutputManifest,
    write_field_architecture_dossier_outputs,
)
from worldenergydata.texas_rrc.dossiers.models import (
    build_field_architecture_dossier_index,
    build_field_architecture_dossier_pages,
)
from worldenergydata.texas_rrc.dossiers.quality import (
    assess_field_architecture_dossier_quality,
)
from worldenergydata.texas_rrc.dossiers.selection import select_dossier_candidates
from worldenergydata.texas_rrc.dossiers.sources import (
    load_field_architecture_dossier_inputs,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT


@dataclass(frozen=True)
class FieldArchitectureDossierBuildResult:
    """Result returned by the field-architecture dossier publisher."""

    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldArchitectureDossierOutputManifest | None


def run_build_field_architecture_dossiers(
    root: Path | str = SOURCE_CATALOG_ROOT,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    dry_run: bool = False,
    require_sources: bool = False,
    allow_non_ace_output: bool = False,
    max_fields: int = 25,
    class_coverage_limit: int = 3,
) -> FieldArchitectureDossierBuildResult:
    """Build and optionally write Texas RRC field-architecture dossiers."""
    source_root = Path(root)
    target_root = Path(output_root)
    inputs = load_field_architecture_dossier_inputs(source_root)
    blocking_source_gaps = _dedupe(
        (*inputs.blocking_source_gaps, *_rank_source_gaps(inputs.rankings))
    )
    if blocking_source_gaps and (require_sources or not dry_run):
        raise ValueError(
            "Cannot build field-architecture dossiers with missing sources: "
            + ", ".join(blocking_source_gaps)
        )
    selected = select_dossier_candidates(
        inputs.rankings,
        max_fields=max_fields,
        class_coverage_limit=class_coverage_limit,
    )
    pages = build_field_architecture_dossier_pages(
        selected,
        inputs.field_atlas_summary,
        inputs.field_development_metrics,
        source_links_are_relative=source_root.resolve() == target_root.resolve(),
    )
    index = build_field_architecture_dossier_index(pages)
    quality = assess_field_architecture_dossier_quality(
        index,
        blocking_source_gaps,
        inputs.informational_source_gaps,
    )
    if dry_run:
        return FieldArchitectureDossierBuildResult(
            row_count=len(index),
            blocking_source_gaps=blocking_source_gaps,
            informational_source_gaps=inputs.informational_source_gaps,
            dry_run=True,
            manifest=None,
        )
    if index.empty:
        raise ValueError("Cannot publish field-architecture dossiers: no_dossier_candidates")
    manifest = write_field_architecture_dossier_outputs(
        pages=pages,
        index=index,
        quality=quality,
        output_root=target_root,
        input_paths=inputs.input_paths,
        upstream_manifests=inputs.upstream_manifests,
        selection_policy={
            "max_fields": max_fields,
            "class_coverage_limit": class_coverage_limit,
        },
        allow_non_ace_root=allow_non_ace_output,
        command=_command(
            source_root,
            target_root,
            require_sources,
            max_fields,
            class_coverage_limit,
        ),
    )
    return FieldArchitectureDossierBuildResult(
        row_count=len(index),
        blocking_source_gaps=blocking_source_gaps,
        informational_source_gaps=inputs.informational_source_gaps,
        dry_run=False,
        manifest=manifest,
    )


def _command(
    root: Path,
    output_root: Path,
    require_sources: bool,
    max_fields: int,
    class_coverage_limit: int,
) -> str:
    parts = [
        "worldenergydata",
        "texas-rrc",
        "build-field-architecture-dossiers",
        "--root",
        str(root),
        "--output-root",
        str(output_root),
        "--max-fields",
        str(max_fields),
        "--class-coverage-limit",
        str(class_coverage_limit),
    ]
    if require_sources:
        parts.append("--require-sources")
    return " ".join(parts)


def _rank_source_gaps(rankings: object) -> tuple[str, ...]:
    if not isinstance(rankings, pd.DataFrame):
        return ()
    if rankings.empty or "opportunity_rank" not in rankings:
        return ()
    values = rankings["opportunity_rank"]
    invalid = pd.to_numeric(values, errors="coerce").isna() & values.notna()
    try:
        invalid &= values.astype(str).str.strip().ne("")
    except (TypeError, ValueError):
        pass
    return ("invalid_opportunity_rank",) if bool(invalid.any()) else ()


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


__all__ = [
    "FieldArchitectureDossierBuildResult",
    "run_build_field_architecture_dossiers",
]
