"""CLI support for publishing Texas RRC field-atlas reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from worldenergydata.texas_rrc.reports.field_atlas import (
    build_field_atlas_pages,
    build_field_atlas_summary,
)
from worldenergydata.texas_rrc.reports.io import (
    FieldAtlasReportOutputManifest,
    write_field_atlas_report_outputs,
)
from worldenergydata.texas_rrc.reports.quality import assess_field_atlas_report_quality
from worldenergydata.texas_rrc.reports.sources import load_field_atlas_report_inputs
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT


@dataclass(frozen=True)
class FieldAtlasReportBuildResult:
    """Result returned by the field-atlas report publisher."""

    row_count: int
    page_count: int
    source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldAtlasReportOutputManifest | None


def run_publish_field_atlas_reports(
    root: Path | str = SOURCE_CATALOG_ROOT,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    dry_run: bool = False,
    require_sources: bool = False,
    allow_non_ace_output: bool = False,
    max_fields: int | None = None,
) -> FieldAtlasReportBuildResult:
    """Build and optionally write Texas RRC field-atlas report outputs."""
    source_root = Path(root)
    target_root = Path(output_root)
    inputs = load_field_atlas_report_inputs(source_root)
    if inputs.source_gaps and (require_sources or not dry_run):
        raise ValueError(
            "Cannot publish field-atlas reports with missing sources: "
            + ", ".join(inputs.source_gaps)
        )
    pages = build_field_atlas_pages(inputs, max_fields=max_fields)
    summary = build_field_atlas_summary(pages)
    quality = assess_field_atlas_report_quality(summary, pages, inputs.source_gaps)
    if dry_run:
        return FieldAtlasReportBuildResult(
            row_count=len(summary),
            page_count=len(pages),
            source_gaps=inputs.source_gaps,
            dry_run=True,
            manifest=None,
        )
    manifest = write_field_atlas_report_outputs(
        pages=pages,
        summary=summary,
        quality=quality,
        output_root=target_root,
        input_paths=inputs.input_paths,
        allow_non_ace_root=allow_non_ace_output,
        command=_command(source_root, target_root, require_sources, max_fields),
    )
    return FieldAtlasReportBuildResult(
        row_count=len(summary),
        page_count=len(pages),
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
        "publish-field-atlas-reports",
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
    "FieldAtlasReportBuildResult",
    "run_publish_field_atlas_reports",
]
