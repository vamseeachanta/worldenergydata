"""Tests for writing Texas RRC field-atlas reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.texas_rrc.reports.field_atlas import FieldAtlasPage
from worldenergydata.texas_rrc.reports.io import (
    FIELD_ATLAS_REPORT_DIR,
    write_field_atlas_report_outputs,
)
from worldenergydata.texas_rrc.reports.quality import assess_field_atlas_report_quality


def test_writes_staged_html_summary_quality_and_manifest(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    page = _page()
    summary = pd.DataFrame([page.summary])
    quality = assess_field_atlas_report_quality(
        summary,
        (page,),
        source_gaps=("production_metric_gap",),
    )

    manifest = write_field_atlas_report_outputs(
        pages=(page,),
        summary=summary,
        quality=quality,
        output_root=tmp_path,
        input_paths=(tmp_path / "source.csv",),
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc publish-field-atlas-reports",
        code_revision="test-rev",
    )

    target = tmp_path / FIELD_ATLAS_REPORT_DIR
    assert (target / "index.html").is_file()
    assert (target / "fields" / page.field_page_filename).is_file()
    assert (target / "field_atlas_summary.csv").is_file()
    assert (target / "field_atlas_summary.parquet").is_file()
    assert (target / "field_atlas_report_quality.json").is_file()
    assert manifest.row_count == 1
    assert manifest.page_count == 1
    assert manifest.code_revision == "test-rev"

    payload = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert payload["row_count"] == 1
    assert payload["page_count"] == 1
    assert payload["source_gaps"] == ["production_metric_gap"]
    assert payload["command"] == "worldenergydata texas-rrc publish-field-atlas-reports"


def test_rejects_non_ace_output_without_override(tmp_path: Path) -> None:
    page = _page()
    summary = pd.DataFrame([page.summary])
    quality = assess_field_atlas_report_quality(summary, (page,), source_gaps=())

    with pytest.raises(ValueError, match="Field-atlas report output_root"):
        write_field_atlas_report_outputs(
            pages=(page,),
            summary=summary,
            quality=quality,
            output_root=tmp_path,
        )


def test_rewrite_removes_stale_field_pages(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    page = _page()
    summary = pd.DataFrame([page.summary])
    quality = assess_field_atlas_report_quality(summary, (page,), source_gaps=())

    write_field_atlas_report_outputs(
        pages=(page,),
        summary=summary,
        quality=quality,
        output_root=tmp_path,
        generated_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
        allow_non_ace_root=True,
    )
    stale = tmp_path / FIELD_ATLAS_REPORT_DIR / "fields" / "stale.html"
    stale.write_text("stale", encoding="utf-8")

    write_field_atlas_report_outputs(
        pages=(page,),
        summary=summary,
        quality=quality,
        output_root=tmp_path,
        generated_at=datetime(2026, 7, 2, 0, 1, tzinfo=timezone.utc),
        allow_non_ace_root=True,
    )

    assert not stale.exists()
    assert (
        tmp_path / FIELD_ATLAS_REPORT_DIR / "fields" / page.field_page_filename
    ).is_file()


def _page() -> FieldAtlasPage:
    summary = {
        "district": "08",
        "field_number": "12345",
        "field_name": "Alpha Field",
        "field_slug": "alpha-field",
        "report_path": "fields/08-12345-alpha-field.html",
        "field_page_filename": "08-12345-alpha-field.html",
        "well_count": 10,
        "active_well_count": 7,
        "permit_count": 3,
        "completion_count": 2,
        "production_maturity_class": "late-life",
        "remaining_activity_score": 81.5,
        "rank_cumulative_boe": 1,
        "rank_remaining_activity": 4,
        "rank_well_density_proxy": 7,
        "cumulative_oil_bbl": 1000,
        "cumulative_gas_mcf": 6000,
        "cumulative_condensate_bbl": 25,
        "cumulative_boe": 2025,
        "production_per_well_boe": 202.5,
        "lease_count": 2,
        "operator_count": 2,
        "top_operator_number": "1001",
        "top_operator_name": "Operator A",
        "top_operator_share": 0.75,
        "infrastructure_access_class": "high",
        "infrastructure_access_score": 92.0,
        "nearest_pipeline_distance_miles": 0.8,
        "nearby_pipeline_count_1mi": 1,
        "nearby_pipeline_count_5mi": 4,
        "nearby_pipeline_count_10mi": 10,
        "source_caveats": "direct_rrc_metrics; gis_centroid",
        "quality_flags": "",
    }
    return FieldAtlasPage(
        district="08",
        field_number="12345",
        field_name="Alpha Field",
        field_slug="alpha-field",
        field_page_filename="08-12345-alpha-field.html",
        report_path="fields/08-12345-alpha-field.html",
        summary=summary,
        lease_rows=(),
        source_caveats=("direct_rrc_metrics", "gis_centroid"),
        quality_flags=(),
    )
