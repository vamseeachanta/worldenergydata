"""Tests for writing Texas RRC field-opportunity outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.texas_rrc.opportunities.io import (
    FIELD_OPPORTUNITY_DIR,
    write_field_opportunity_outputs,
)
from worldenergydata.texas_rrc.opportunities.quality import (
    assess_field_opportunity_quality,
)


def test_writes_staged_rankings_html_quality_and_manifest(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    rankings = _rankings()
    quality = assess_field_opportunity_quality(rankings, source_gaps=())

    manifest = write_field_opportunity_outputs(
        rankings=rankings,
        quality=quality,
        output_root=tmp_path,
        input_paths=(tmp_path / "field_atlas_summary.csv",),
        upstream_manifests=(tmp_path / "manifest.json",),
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc build-field-opportunities",
        code_revision="test-rev",
        generated_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    target = tmp_path / FIELD_OPPORTUNITY_DIR
    assert (target / "field_opportunity_rankings.csv").is_file()
    assert (target / "field_opportunity_rankings.parquet").is_file()
    assert (target / "field_opportunity_summary.html").is_file()
    assert (target / "field_opportunity_quality.json").is_file()
    assert (target / "manifest.json").is_file()
    assert manifest.row_count == 1
    assert manifest.code_revision == "test-rev"

    payload = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert payload["row_count"] == 1
    assert payload["scoring_version"] == "texas_rrc_field_opportunity_v1"
    assert payload["command"] == "worldenergydata texas-rrc build-field-opportunities"


def test_rejects_non_ace_output_without_override(tmp_path: Path) -> None:
    rankings = _rankings()
    quality = assess_field_opportunity_quality(rankings, source_gaps=())

    with pytest.raises(ValueError, match="field-opportunity output_root"):
        write_field_opportunity_outputs(
            rankings=rankings,
            quality=quality,
            output_root=tmp_path,
        )


def test_rewrite_removes_stale_outputs(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    rankings = _rankings()
    quality = assess_field_opportunity_quality(rankings, source_gaps=())

    write_field_opportunity_outputs(
        rankings=rankings,
        quality=quality,
        output_root=tmp_path,
        allow_non_ace_root=True,
        generated_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    stale = tmp_path / FIELD_OPPORTUNITY_DIR / "stale.txt"
    stale.write_text("stale", encoding="utf-8")

    write_field_opportunity_outputs(
        rankings=rankings,
        quality=quality,
        output_root=tmp_path,
        allow_non_ace_root=True,
        generated_at=datetime(2026, 7, 2, 0, 1, tzinfo=timezone.utc),
    )

    assert not stale.exists()


def _rankings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "opportunity_rank": 1,
                "district": "08",
                "field_number": "12345",
                "field_name": "Alpha Field",
                "opportunity_score": 91.2,
                "opportunity_class": "high_priority",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "source_caveats": "direct_rrc_metrics",
                "quality_flags": "",
            }
        ]
    )
