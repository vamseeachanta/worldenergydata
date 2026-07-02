"""Tests for Texas RRC field-architecture dossier output persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.dossiers.io import (
    FIELD_ARCHITECTURE_DOSSIER_DIR,
    write_field_architecture_dossier_outputs,
)
from worldenergydata.texas_rrc.dossiers.models import FieldArchitectureDossierPage
from worldenergydata.texas_rrc.dossiers.quality import FieldArchitectureDossierQuality


def test_writes_staged_dossier_outputs_quality_aliases_and_manifest(
    tmp_path: Path,
) -> None:
    index = pd.DataFrame(
        [
            {
                "dossier_rank": 1,
                "field_name": "Aguila Vado",
                "district": "05",
                "field_number": "00870500",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "selection_reason": "top_ranked",
                "source_caveats": "lease_allocated",
                "quality_flags": "screening_only",
                "dossier_limitations": "no reserves conclusions",
            }
        ]
    )
    quality = FieldArchitectureDossierQuality(
        row_count=1,
        blocking_source_gaps=(),
        informational_source_gaps=("pdq_water_gap",),
        architecture_class_counts={"high_access_infill_redevelopment": 1},
        selection_reason_counts={"top_ranked": 1},
        caveat_counts={"lease_allocated": 1},
        quality_flag_counts={"screening_only": 1},
        limitation_count=1,
    )
    page = FieldArchitectureDossierPage(
        district="05",
        field_number="00870500",
        field_name="Aguila Vado",
        field_slug="aguila-vado",
        dossier_filename="05-00870500-aguila-vado-dossier.html",
        dossier_path="fields/05-00870500-aguila-vado-dossier.html",
        source_field_atlas_report_path="reports/field_atlas/fields/source.html",
        source_field_atlas_href="../../../reports/field_atlas/fields/source.html",
        summary={},
        source_caveats=("lease_allocated",),
        quality_flags=("screening_only",),
        limitations=("no reserves conclusions",),
    )

    manifest = write_field_architecture_dossier_outputs(
        pages=(page,),
        index=index,
        quality=quality,
        output_root=tmp_path,
        input_paths=[tmp_path / "input.csv"],
        upstream_manifests=[tmp_path / "manifest.json"],
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc build-field-architecture-dossiers",
        code_revision="test-revision",
        selection_policy={"max_fields": 2, "class_coverage_limit": 1},
    )

    output_dir = tmp_path / FIELD_ARCHITECTURE_DOSSIER_DIR
    assert manifest.row_count == 1
    assert (output_dir / "field_architecture_dossier_index.csv").exists()
    assert (output_dir / "field_architecture_dossier_index.parquet").exists()
    assert (output_dir / "field_architecture_dossier_summary.html").exists()
    assert (output_dir / "fields" / page.dossier_filename).exists()
    generic_quality = json.loads((output_dir / "quality.json").read_text())
    component_quality = json.loads(
        (output_dir / "field_architecture_dossier_quality.json").read_text()
    )
    assert generic_quality == component_quality
    manifest_payload = json.loads((output_dir / "manifest.json").read_text())
    assert manifest_payload["quality_path"] == str(output_dir / "quality.json")
    assert manifest_payload["component_quality_path"] == str(
        output_dir / "field_architecture_dossier_quality.json"
    )
    assert manifest_payload["command"] == (
        "worldenergydata texas-rrc build-field-architecture-dossiers"
    )
    assert manifest_payload["selection_policy"] == {
        "max_fields": 2,
        "class_coverage_limit": 1,
    }
    assert manifest_payload["limitations"] == ["no reserves conclusions"]
