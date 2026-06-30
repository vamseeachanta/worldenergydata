"""Tests for Texas RRC lifecycle output persistence."""

from datetime import datetime, timezone
import json

import pandas as pd
import pytest

from worldenergydata.texas_rrc.lifecycle.quality import LifecycleQualityReport


def test_write_lifecycle_outputs_persists_spine_quality_and_manifest(tmp_path):
    from worldenergydata.texas_rrc.lifecycle.io import (
        load_lifecycle_spine,
        write_lifecycle_outputs,
    )

    spine = pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "api10": "4200100001",
                "field_number": "11111",
                "quality_flags": "",
            }
        ]
    )
    quality = LifecycleQualityReport(
        row_count=1,
        duplicate_api14=0,
        missing_field_id=0,
        missing_lease_id=0,
        missing_operator_id=0,
        invalid_coordinates=0,
        impossible_dates=0,
        permit_without_wellbore=0,
        completion_without_wellbore=0,
        wellbore_without_completion=0,
        source_gaps=("directional_surveys",),
    )

    manifest = write_lifecycle_outputs(
        spine,
        quality,
        output_root=tmp_path,
        generated_at=datetime(2026, 6, 30, 20, 0, tzinfo=timezone.utc),
        input_paths=["raw/wellbore/query/wellbore.zip"],
        allow_non_ace_root=True,
    )

    spine_path = (
        tmp_path / "curated" / "well_lifecycle" / "spine" / "well_lifecycle_spine.csv"
    )
    quality_path = spine_path.with_name("well_lifecycle_quality.json")
    manifest_path = spine_path.with_name("manifest.json")
    assert manifest.spine_path == spine_path
    assert manifest.quality_path == quality_path
    assert manifest.manifest_path == manifest_path
    assert spine_path.exists()
    assert load_lifecycle_spine(spine_path).loc[0, "api14"] == "42001000010000"

    quality_payload = json.loads(quality_path.read_text(encoding="utf-8"))
    assert quality_payload["row_count"] == 1
    assert quality_payload["source_gaps"] == ["directional_surveys"]

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["generated_at"] == "2026-06-30T20:00:00Z"
    assert manifest_payload["row_count"] == 1
    assert manifest_payload["input_paths"] == ["raw/wellbore/query/wellbore.zip"]
    assert not list(tmp_path.rglob(".staging-*"))


def test_write_lifecycle_outputs_rejects_non_ace_root_without_override(tmp_path):
    from worldenergydata.texas_rrc.lifecycle.io import write_lifecycle_outputs

    quality = LifecycleQualityReport(
        row_count=0,
        duplicate_api14=0,
        missing_field_id=0,
        missing_lease_id=0,
        missing_operator_id=0,
        invalid_coordinates=0,
        impossible_dates=0,
        permit_without_wellbore=0,
        completion_without_wellbore=0,
        wellbore_without_completion=0,
        source_gaps=(),
    )

    with pytest.raises(ValueError, match="/mnt/ace"):
        write_lifecycle_outputs(
            pd.DataFrame(),
            quality,
            output_root=tmp_path,
        )
