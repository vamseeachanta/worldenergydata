"""Quality assessment for Texas RRC field-atlas reports."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from worldenergydata.texas_rrc.reports.field_atlas import FieldAtlasPage


@dataclass(frozen=True)
class FieldAtlasReportQuality:
    """Quality summary for a published field-atlas report batch."""

    row_count: int
    page_count: int
    source_gaps: tuple[str, ...]
    missing_infrastructure_count: int
    caveat_counts: dict[str, int]
    quality_flag_counts: dict[str, int]


def assess_field_atlas_report_quality(
    summary: pd.DataFrame,
    pages: tuple[FieldAtlasPage, ...],
    source_gaps: tuple[str, ...],
) -> FieldAtlasReportQuality:
    """Assess quality and caveat counts for a field-atlas report set."""
    caveats = Counter()
    flags = Counter()
    for page in pages:
        caveats.update(page.source_caveats)
        flags.update(page.quality_flags)
    missing_infra = 0
    if "infrastructure_access_class" in summary:
        missing_infra = int(
            (summary["infrastructure_access_class"] == "not_available").sum()
        )
    return FieldAtlasReportQuality(
        row_count=len(summary),
        page_count=len(pages),
        source_gaps=tuple(source_gaps),
        missing_infrastructure_count=missing_infra,
        caveat_counts=dict(sorted(caveats.items())),
        quality_flag_counts=dict(sorted(flags.items())),
    )


__all__ = [
    "FieldAtlasReportQuality",
    "assess_field_atlas_report_quality",
]
