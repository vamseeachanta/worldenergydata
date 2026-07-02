"""CLI support for publishing Texas RRC field-architecture portfolio reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.architecture_portfolio.io import (
    FieldArchitecturePortfolioOutputManifest,
    write_field_architecture_portfolio_outputs,
)
from worldenergydata.texas_rrc.architecture_portfolio.models import (
    build_field_architecture_action_queue,
    summarize_architecture_classes,
    summarize_followup_recommendations,
)
from worldenergydata.texas_rrc.architecture_portfolio.quality import (
    assess_field_architecture_portfolio_quality,
)
from worldenergydata.texas_rrc.architecture_portfolio.sources import (
    load_field_architecture_portfolio_inputs,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT


@dataclass(frozen=True)
class FieldArchitecturePortfolioBuildResult:
    """Result returned by the field-architecture portfolio publisher."""

    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldArchitecturePortfolioOutputManifest | None


def run_build_field_architecture_portfolio(
    root: Path | str = SOURCE_CATALOG_ROOT,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    dry_run: bool = False,
    require_sources: bool = False,
    allow_non_ace_output: bool = False,
) -> FieldArchitecturePortfolioBuildResult:
    """Build and optionally write Texas RRC field-architecture portfolio outputs."""
    source_root = Path(root)
    target_root = Path(output_root)
    inputs = load_field_architecture_portfolio_inputs(source_root)
    blocking_source_gaps = tuple(inputs.blocking_source_gaps)
    informational_source_gaps = _dedupe(
        (*inputs.informational_source_gaps, *_rank_source_gaps(inputs.dossier_index))
    )
    if blocking_source_gaps and (require_sources or not dry_run):
        raise ValueError(
            "Cannot build field-architecture portfolio with missing sources: "
            + ", ".join(blocking_source_gaps)
        )

    action_queue = build_field_architecture_action_queue(
        inputs.dossier_index,
        input_dossier_dir=inputs.input_dossier_dir,
        output_root=target_root,
    )
    class_summary = summarize_architecture_classes(action_queue)
    followup_summary = summarize_followup_recommendations(action_queue)
    quality = assess_field_architecture_portfolio_quality(
        action_queue,
        blocking_source_gaps,
        informational_source_gaps,
    )
    if dry_run:
        return FieldArchitecturePortfolioBuildResult(
            row_count=len(action_queue),
            blocking_source_gaps=blocking_source_gaps,
            informational_source_gaps=informational_source_gaps,
            dry_run=True,
            manifest=None,
        )
    if action_queue.empty:
        raise ValueError(
            "Cannot publish field-architecture portfolio: no_portfolio_rows"
        )
    manifest = write_field_architecture_portfolio_outputs(
        action_queue=action_queue,
        class_summary=class_summary,
        followup_summary=followup_summary,
        quality=quality,
        output_root=target_root,
        input_paths=inputs.input_paths,
        dossier_input_paths=inputs.dossier_input_paths,
        upstream_manifests=inputs.upstream_manifest_paths,
        allow_non_ace_root=allow_non_ace_output,
        command=_command(source_root, target_root, require_sources),
    )
    return FieldArchitecturePortfolioBuildResult(
        row_count=len(action_queue),
        blocking_source_gaps=blocking_source_gaps,
        informational_source_gaps=informational_source_gaps,
        dry_run=False,
        manifest=manifest,
    )


def _command(root: Path, output_root: Path, require_sources: bool) -> str:
    parts = [
        "worldenergydata",
        "texas-rrc",
        "build-field-architecture-portfolio",
        "--root",
        str(root),
        "--output-root",
        str(output_root),
    ]
    if require_sources:
        parts.append("--require-sources")
    return " ".join(parts)


def _rank_source_gaps(dossier_index: object) -> tuple[str, ...]:
    if not isinstance(dossier_index, pd.DataFrame):
        return ()
    if dossier_index.empty or "opportunity_rank" not in dossier_index:
        return ()
    values = dossier_index["opportunity_rank"]
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
    "FieldArchitecturePortfolioBuildResult",
    "run_build_field_architecture_portfolio",
]
