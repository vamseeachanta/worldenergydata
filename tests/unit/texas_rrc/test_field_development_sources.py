"""Tests for loading Texas RRC field-development input artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_lifecycle(root: Path) -> Path:
    path = (
        root
        / "curated"
        / "well_lifecycle"
        / "spine"
        / "well_lifecycle_spine.csv"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "api10": "4200100001",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "lease_number": "02001",
                "operator_number": "300001",
            }
        ]
    ).to_csv(path, index=False)
    return path


def _production_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "aggregation_level": "field",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "cumulative_boe": 1000.0,
            },
            {
                "aggregation_level": "lease",
                "district": "08",
                "field_number": "00010001",
                "lease_number": "02001",
                "cumulative_boe": 600.0,
            },
        ]
    )


def _write_production_parquet(root: Path) -> Path:
    path = (
        root
        / "curated"
        / "production"
        / "field_atlas"
        / "production_field_atlas.parquet"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    _production_frame().to_parquet(path, index=False)
    return path


def _write_production_csv(root: Path) -> Path:
    path = (
        root
        / "curated"
        / "production"
        / "field_atlas"
        / "production_field_atlas.csv"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    _production_frame().to_csv(path, index=False)
    return path


def test_load_field_development_inputs_reads_complete_curated_artifacts(tmp_path):
    from worldenergydata.texas_rrc.field_development.sources import (
        load_field_development_inputs,
    )

    _write_lifecycle(tmp_path)
    _write_production_parquet(tmp_path)
    _write_json(
        tmp_path
        / "curated/well_lifecycle/spine/well_lifecycle_quality.json",
        {"row_count": 1, "source_gaps": []},
    )
    _write_json(
        tmp_path
        / "curated/production/field_atlas/production_field_atlas_quality.json",
        {"row_count": 2, "metric_gaps": ["water_bbl"]},
    )

    inputs = load_field_development_inputs(tmp_path)

    assert inputs.source_gaps == ()
    assert inputs.lifecycle.iloc[0]["api14"] == "42001000010000"
    assert inputs.lifecycle.iloc[0]["field_number"] == "00010001"
    assert inputs.production["aggregation_level"].tolist() == ["field"]
    assert inputs.production.iloc[0]["field_number"] == "00010001"
    assert inputs.lifecycle_quality["row_count"] == 1
    assert inputs.production_quality["metric_gaps"] == ["water_bbl"]


def test_load_field_development_inputs_reports_missing_lifecycle(tmp_path):
    from worldenergydata.texas_rrc.field_development.sources import (
        load_field_development_inputs,
    )

    _write_production_parquet(tmp_path)

    inputs = load_field_development_inputs(tmp_path)

    assert inputs.lifecycle.empty
    assert inputs.source_gaps == (
        "well_lifecycle_spine",
        "well_lifecycle_quality",
        "production_field_atlas_quality",
    )


def test_load_field_development_inputs_reports_missing_production(tmp_path):
    from worldenergydata.texas_rrc.field_development.sources import (
        load_field_development_inputs,
    )

    _write_lifecycle(tmp_path)

    inputs = load_field_development_inputs(tmp_path)

    assert inputs.production.empty
    assert inputs.source_gaps == (
        "production_field_atlas",
        "well_lifecycle_quality",
        "production_field_atlas_quality",
    )


def test_load_field_development_inputs_reports_missing_quality_json(tmp_path):
    from worldenergydata.texas_rrc.field_development.sources import (
        load_field_development_inputs,
    )

    _write_lifecycle(tmp_path)
    _write_production_parquet(tmp_path)

    inputs = load_field_development_inputs(tmp_path)

    assert inputs.lifecycle_quality == {}
    assert inputs.production_quality == {}
    assert inputs.source_gaps == (
        "well_lifecycle_quality",
        "production_field_atlas_quality",
    )


def test_load_field_development_inputs_falls_back_to_production_csv(tmp_path):
    from worldenergydata.texas_rrc.field_development.sources import (
        load_field_development_inputs,
    )

    _write_lifecycle(tmp_path)
    _write_production_csv(tmp_path)

    inputs = load_field_development_inputs(tmp_path)

    assert inputs.production["aggregation_level"].tolist() == ["field"]
    assert inputs.production.iloc[0]["field_number"] == "00010001"


def test_load_field_development_inputs_rejects_url_like_roots():
    from worldenergydata.texas_rrc.field_development.sources import (
        load_field_development_inputs,
    )

    with pytest.raises(ValueError, match="local filesystem path"):
        load_field_development_inputs("https://www.rrc.texas.gov/data.zip")
