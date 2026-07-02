"""Tests for Texas RRC field-architecture portfolio source loading."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.architecture_portfolio.sources import (
    load_field_architecture_portfolio_inputs,
)
from worldenergydata.texas_rrc.dossiers.io import FIELD_ARCHITECTURE_DOSSIER_DIR


def test_loads_dossier_packet_and_gap_schema(tmp_path: Path) -> None:
    root = _write_portfolio_source_tree(tmp_path)

    inputs = load_field_architecture_portfolio_inputs(root)

    assert inputs.blocking_source_gaps == (
        "top_blocking_gap",
        "nested_blocking_gap",
        "quality_blocking_gap",
    )
    assert inputs.informational_source_gaps == (
        "top_info_gap",
        "nested_info_gap",
        "quality_info_gap",
    )
    assert inputs.input_dossier_dir == root / FIELD_ARCHITECTURE_DOSSIER_DIR
    assert inputs.index_path.name == "field_architecture_dossier_index.csv"
    assert inputs.manifest_path.name == "manifest.json"
    assert inputs.quality_path.name == "quality.json"
    assert [path.name for path in inputs.dossier_page_paths] == [
        "05-00870500-aguila-vado-dossier.html",
        "03-84750500-southern-bay-dossier.html",
    ]
    assert inputs.upstream_manifest_paths == (
        root / "curated" / "reports" / "field_atlas" / "manifest.json",
        root / "curated" / "field_development" / "metrics" / "manifest.json",
        root / "curated" / "infrastructure" / "access" / "manifest.json",
    )
    assert inputs.dossier_input_paths == (
        root / "curated" / "reports" / "field_atlas" / "manifest.json",
        root / "curated" / "field_development" / "metrics" / "manifest.json",
        root / "curated" / "reports" / "field_atlas" / "summary.csv",
    )
    assert len(inputs.dossier_index) == 2
    assert inputs.dossier_index.loc[0, "district"] == "05"
    assert inputs.dossier_index.loc[0, "field_number"] == "00870500"


def _write_portfolio_source_tree(tmp_path: Path) -> Path:
    root = tmp_path / "texas_rrc"
    dossier_dir = root / FIELD_ARCHITECTURE_DOSSIER_DIR
    fields_dir = dossier_dir / "fields"
    fields_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "dossier_path": "fields/05-00870500-aguila-vado-dossier.html",
            },
            {
                "district": "03",
                "field_number": "84750500",
                "field_name": "Southern Bay",
                "dossier_path": "fields/03-84750500-southern-bay-dossier.html",
            },
        ]
    ).to_csv(dossier_dir / "field_architecture_dossier_index.csv", index=False)

    for filename in (
        "05-00870500-aguila-vado-dossier.html",
        "03-84750500-southern-bay-dossier.html",
    ):
        (fields_dir / filename).write_text("<html></html>\n", encoding="utf-8")

    (dossier_dir / "manifest.json").write_text(
        json.dumps(
            {
                "input_paths": [
                    str(root / "curated" / "reports" / "field_atlas" / "manifest.json"),
                    str(
                        root
                        / "curated"
                        / "field_development"
                        / "metrics"
                        / "manifest.json"
                    ),
                    str(root / "curated" / "reports" / "field_atlas" / "summary.csv"),
                ],
                "upstream_manifests": [
                    str(
                        root / "curated" / "infrastructure" / "access" / "manifest.json"
                    ),
                    str(root / "curated" / "reports" / "field_atlas" / "manifest.json"),
                ],
                "blocking_source_gaps": ["top_blocking_gap"],
                "informational_source_gaps": ["top_info_gap"],
                "quality": {
                    "blocking_source_gaps": ["nested_blocking_gap"],
                    "informational_source_gaps": ["nested_info_gap"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (dossier_dir / "quality.json").write_text(
        json.dumps(
            {
                "blocking_source_gaps": ["quality_blocking_gap"],
                "informational_source_gaps": ["quality_info_gap"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return root
