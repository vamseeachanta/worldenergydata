"""Tests for Texas RRC field-development quality and output persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from worldenergydata.texas_rrc.field_development.sources import (
    FieldDevelopmentInputs,
)


def _inputs(source_gaps: tuple[str, ...] = ()) -> FieldDevelopmentInputs:
    return FieldDevelopmentInputs(
        lifecycle=pd.DataFrame(),
        production=pd.DataFrame(),
        lifecycle_quality={},
        production_quality={},
        source_gaps=source_gaps,
    )


def _metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "production_maturity_class": "growth",
                "source_caveats": (
                    "lease_level_production|no_per_well_allocation|"
                    "water_and_well_count_unavailable_from_pdq"
                ),
                "cumulative_boe": 1000.0,
                "rank_cumulative_boe": 1,
            },
            {
                "district": "09",
                "field_number": "00020001",
                "field_name": "LIFECYCLE ONLY",
                "production_maturity_class": "pre_production",
                "source_caveats": "missing_production|missing_lifecycle_dates",
                "cumulative_boe": pd.NA,
                "rank_cumulative_boe": 2,
            },
        ]
    )


def test_assess_field_development_quality_counts_caveats_and_maturity():
    from worldenergydata.texas_rrc.field_development.quality import (
        assess_field_development_quality,
    )

    report = assess_field_development_quality(
        _metrics(),
        _inputs(source_gaps=("well_lifecycle_quality",)),
    )

    assert report.row_count == 2
    assert report.source_gaps == ("well_lifecycle_quality",)
    assert report.caveat_counts["lease_level_production"] == 1
    assert report.caveat_counts["missing_production"] == 1
    assert report.maturity_counts == {"growth": 1, "pre_production": 1}


def test_write_field_development_outputs_rejects_non_ace_root_by_default(tmp_path):
    from worldenergydata.texas_rrc.field_development.io import (
        write_field_development_outputs,
    )
    from worldenergydata.texas_rrc.field_development.quality import (
        assess_field_development_quality,
    )

    with pytest.raises(ValueError, match="/mnt/ace"):
        write_field_development_outputs(
            _metrics(),
            assess_field_development_quality(_metrics(), _inputs()),
            output_root=tmp_path,
        )


def test_write_field_development_outputs_persists_quality_and_manifest(tmp_path):
    from worldenergydata.texas_rrc.field_development.io import (
        load_field_development_metrics,
        write_field_development_outputs,
    )
    from worldenergydata.texas_rrc.field_development.quality import (
        assess_field_development_quality,
    )

    metrics = _metrics()
    inputs = _inputs(source_gaps=("production_field_atlas_quality",))
    quality = assess_field_development_quality(metrics, inputs)
    lifecycle_path = tmp_path / "curated/well_lifecycle/spine/well_lifecycle_spine.csv"
    production_path = tmp_path / "curated/production/field_atlas/production.parquet"

    manifest = write_field_development_outputs(
        metrics,
        quality,
        output_root=tmp_path,
        generated_at=datetime(2026, 7, 1, 3, 0, tzinfo=timezone.utc),
        input_paths=[lifecycle_path, production_path],
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc build-field-development-metrics",
        code_revision="abc123",
    )

    assert manifest.csv_path == (
        tmp_path
        / "curated"
        / "field_development"
        / "metrics"
        / "field_development_metrics.csv"
    )
    assert manifest.parquet_path.exists()
    assert manifest.quality_path.exists()
    assert manifest.manifest_path.exists()

    reloaded_csv = load_field_development_metrics(manifest.csv_path)
    reloaded_parquet = load_field_development_metrics(manifest.parquet_path)
    assert reloaded_csv.iloc[0]["field_number"] == "00010001"
    assert reloaded_parquet.iloc[0]["field_number"] == "00010001"

    quality_payload = json.loads(manifest.quality_path.read_text(encoding="utf-8"))
    assert quality_payload["row_count"] == 2
    assert quality_payload["source_gaps"] == ["production_field_atlas_quality"]
    assert quality_payload["caveat_counts"]["no_per_well_allocation"] == 1

    manifest_payload = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["generated_at"] == "2026-07-01T03:00:00Z"
    assert manifest_payload["row_count"] == 2
    assert manifest_payload["input_paths"] == [
        str(lifecycle_path),
        str(production_path),
    ]
    assert (
        manifest_payload["command"]
        == "worldenergydata texas-rrc build-field-development-metrics"
    )
    assert manifest_payload["code_revision"] == "abc123"
    assert manifest_payload["quality"]["maturity_counts"]["growth"] == 1
