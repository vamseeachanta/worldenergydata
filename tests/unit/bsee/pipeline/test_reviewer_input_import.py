"""Tests for importing filled BSEE field-structure reviewer inputs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from tests.unit.bsee.pipeline.test_field_package import _load_bsee_command_app


def _decision_log_csv(tmp_path: Path) -> Path:
    path = tmp_path / "basis_review_decision_log.csv"
    pd.DataFrame(
        [
            _decision_row("BRD-01-JULIA-RISER-18918", "DRAFT-JULIA-RISER-18918", "1"),
            _decision_row(
                "BRD-02-SAINT_MALO-RISER-18385",
                "DRAFT-SAINT_MALO-RISER-18385",
                "2",
            ),
        ]
    ).to_csv(path, index=False)
    return path


def _ready_input_csv(tmp_path: Path) -> Path:
    path = tmp_path / "ready13_filled.csv"
    pd.DataFrame(
        [
            {
                "ready_input_id": "R13-01-JULIA-RISER-18918",
                "basis_review_decision_id": "BRD-01-JULIA-RISER-18918",
                "review_sequence": "1",
                "field": "julia",
                "proposed_structure_class": "riser",
                "asset_register_id": "DRAFT-JULIA-RISER-18918",
                "selected_basis_document_family": "row",
                "selected_basis_document_id": "25025",
                "selected_basis_page_number": "54",
                "source_pdf_path": "source_documents/row/25025.pdf",
                "thumbnail_path": "thumbnails/01_25025_p54.png",
                "candidate_basis_evidence_type": "source_pdf_page",
                "candidate_verified_structure_class": "riser",
                "candidate_verified_quantity": "1",
                "candidate_verified_segment_or_asset_id": "18918",
                "basis_page_accepted": "yes",
                "promote_to_verified_register": "yes",
                "basis_evidence_type": "source_pdf_page",
                "verified_structure_class": "riser",
                "verified_quantity": "1",
                "verified_segment_or_asset_id": "18918",
                "basis_reviewer": "engineer.a",
                "basis_review_date": "2026-06-23",
                "basis_decision": "accepted",
                "basis_review_notes": "Confirmed on source page.",
            },
            {
                "ready_input_id": "R13-02-SAINT_MALO-RISER-18385",
                "basis_review_decision_id": "BRD-02-SAINT_MALO-RISER-18385",
                "review_sequence": "2",
                "field": "saint_malo",
                "proposed_structure_class": "riser",
                "asset_register_id": "DRAFT-SAINT_MALO-RISER-18385",
                "selected_basis_document_family": "row",
                "selected_basis_document_id": "24001",
                "selected_basis_page_number": "12",
                "source_pdf_path": "source_documents/row/24001.pdf",
                "thumbnail_path": "thumbnails/02_24001_p12.png",
                "candidate_basis_evidence_type": "source_pdf_page",
                "candidate_verified_structure_class": "riser",
                "candidate_verified_quantity": "1",
                "candidate_verified_segment_or_asset_id": "18385",
            },
        ]
    ).to_csv(path, index=False)
    return path


def test_import_reviewer_ready_inputs_updates_ready_rows_and_regenerates_products(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.reviewer_input_import import (
        import_reviewer_ready_inputs,
    )

    decision_log = _decision_log_csv(tmp_path)
    ready_input = _ready_input_csv(tmp_path)
    output_dir = tmp_path / "imported"

    paths = import_reviewer_ready_inputs(ready_input, decision_log, output_dir)

    assert paths["import_ready"] == 1
    assert paths["import_blocked"] == 1
    assert paths["verified_rows"] == 1
    assert paths["import_manifest"] == output_dir / "import_run_manifest.json"
    assert paths["html_report"] == output_dir / "index.html"

    updated_log = pd.read_csv(paths["updated_decision_log"]).fillna("")
    assert updated_log.loc[0, "basis_page_accepted"] == "yes"
    assert updated_log.loc[0, "verified_structure_class"] == "riser"
    assert updated_log.loc[0, "basis_reviewer"] == "engineer.a"
    assert updated_log.loc[1, "basis_page_accepted"] == ""

    staging = pd.read_csv(paths["staging_audit"]).fillna("")
    assert staging["import_ready"].tolist() == [1, 0]
    assert staging.loc[1, "missing_required_fields"] == (
        "basis_page_accepted|promote_to_verified_register|basis_evidence_type|"
        "verified_structure_class|verified_quantity|verified_segment_or_asset_id|"
        "basis_reviewer|basis_review_date"
    )

    gate = pd.read_csv(paths["promotion_gate_audit"]).fillna("")
    assert gate["promotion_gate_status"].tolist() == [
        "ready_for_verified_register",
        "blocked_pending_review_fields",
    ]

    verified = pd.read_csv(paths["verified_register"], dtype=str).fillna("")
    assert verified["verified_field_structure_id"].tolist() == [
        "VFS-01-JULIA-RISER-18918"
    ]
    assert verified.loc[0, "basis_document_id"] == "25025"

    manifest = json.loads(paths["import_manifest"].read_text(encoding="utf-8"))
    assert manifest["product"] == "bsee_reviewer_input_import"
    assert manifest["counts"] == {
        "import_ready": 1,
        "import_blocked": 1,
        "verified_rows": 1,
    }
    assert manifest["inputs"]["ready_input"].endswith("ready13_filled.csv")
    assert manifest["output_files"]["verified_register"]["rows"] == 1
    assert "sha256" in manifest["output_files"]["staging_audit"]

    html_report = paths["html_report"].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_report
    assert "BSEE Reviewer Input Import" in html_report
    assert "basis_review_decision_log_updated.csv" in html_report
    assert "verified_field_structure_register.csv" in html_report


def test_bsee_import_reviewer_inputs_cli_writes_import_products(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline import reviewer_input_import

    decision_log = _decision_log_csv(tmp_path)
    ready_input = _ready_input_csv(tmp_path)
    output_dir = tmp_path / "cli-import"
    calls: dict[str, object] = {}

    def fake_import_reviewer_ready_inputs(
        ready_input_path: Path,
        decision_log_path: Path,
        output_dir_path: Path,
        *,
        sqlite_product_path: Path | None = None,
    ) -> dict[str, Path | int]:
        calls.update(
            {
                "ready_input": ready_input_path,
                "decision_log": decision_log_path,
                "output": output_dir_path,
                "sqlite_product": sqlite_product_path,
            }
        )
        output_dir_path.mkdir(parents=True)
        updated = output_dir_path / "basis_review_decision_log_updated.csv"
        updated.write_text("basis_review_decision_id\n", encoding="utf-8")
        return {
            "updated_decision_log": updated,
            "staging_audit": output_dir_path / "reviewer_ready_input_staging_audit.csv",
            "promotion_gate_audit": output_dir_path / "promotion_gate_audit.csv",
            "verified_register": output_dir_path
            / "verified_field_structure_register.csv",
            "import_manifest": output_dir_path / "import_run_manifest.json",
            "html_report": output_dir_path / "index.html",
            "import_ready": 1,
            "import_blocked": 1,
            "verified_rows": 1,
        }

    monkeypatch.setattr(
        reviewer_input_import,
        "import_reviewer_ready_inputs",
        fake_import_reviewer_ready_inputs,
    )

    result = CliRunner().invoke(
        _load_bsee_command_app(),
        [
            "import-reviewer-inputs",
            "--ready-input",
            str(ready_input),
            "--decision-log",
            str(decision_log),
            "--output",
            str(output_dir),
            "--sqlite-product",
            str(tmp_path / "field_structure_product.sqlite"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Import Ready" in result.output
    assert "Import manifest" in result.output
    assert "HTML report" in result.output
    assert calls == {
        "ready_input": ready_input,
        "decision_log": decision_log,
        "output": output_dir,
        "sqlite_product": tmp_path / "field_structure_product.sqlite",
    }


def test_import_reviewer_ready_inputs_publishes_latest_import_sqlite_views(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.reviewer_input_import import (
        import_reviewer_ready_inputs,
    )

    decision_log = _decision_log_csv(tmp_path)
    ready_input = _ready_input_csv(tmp_path)
    sqlite_product = tmp_path / "field_structure_product.sqlite"

    paths = import_reviewer_ready_inputs(
        ready_input,
        decision_log,
        tmp_path / "sqlite-import",
        sqlite_product_path=sqlite_product,
    )

    assert paths["sqlite_product"] == sqlite_product
    with sqlite3.connect(sqlite_product) as conn:
        assert conn.execute("pragma integrity_check").fetchone()[0] == "ok"
        assert _sqlite_count(conn, "latest_reviewer_import_run") == 1
        assert _sqlite_count(conn, "latest_reviewer_import_staging_audit") == 2
        assert _sqlite_count(conn, "latest_reviewer_import_decision_log") == 2
        assert _sqlite_count(conn, "latest_reviewer_import_promotion_gate") == 2
        assert _sqlite_count(conn, "latest_reviewer_import_verified_register") == 1
        assert _sqlite_count(conn, "v_latest_reviewer_import_staging_audit") == 2
        assert _sqlite_count(conn, "v_latest_reviewer_import_verified_register") == 1
        run = conn.execute(
            "select import_ready, import_blocked, verified_rows "
            "from v_latest_reviewer_import_run"
        ).fetchone()
        assert run == (1, 1, 1)


def test_import_reviewer_ready_inputs_blocks_identity_mismatches(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.reviewer_input_import import (
        import_reviewer_ready_inputs,
    )

    decision_log = _decision_log_csv(tmp_path)
    ready_input = _ready_input_csv(tmp_path)
    ready_rows = pd.read_csv(ready_input, dtype=str).fillna("")
    ready_rows.loc[0, "asset_register_id"] = "DRAFT-WRONG-RISER-18918"
    ready_rows.to_csv(ready_input, index=False)

    paths = import_reviewer_ready_inputs(
        ready_input,
        decision_log,
        tmp_path / "identity-mismatch",
    )

    assert paths["import_ready"] == 0
    assert paths["import_blocked"] == 2

    staging = pd.read_csv(paths["staging_audit"], dtype=str).fillna("")
    assert staging.loc[0, "missing_required_fields"] == ""
    assert staging.loc[0, "invalid_required_fields"] == "asset_register_id"

    updated_log = pd.read_csv(paths["updated_decision_log"], dtype=str).fillna("")
    assert updated_log.loc[0, "basis_page_accepted"] == ""
    assert updated_log.loc[0, "verified_structure_class"] == ""


def _sqlite_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"select count(*) from {table}").fetchone()[0])


def _decision_row(decision_id: str, asset_id: str, sequence: str) -> dict[str, str]:
    return {
        "basis_review_decision_id": decision_id,
        "basis_review_route": "ready_basis_acceptance_workpack",
        "basis_review_status": "pending_basis_decision",
        "basis_input_status": "complete_recommendation_inputs",
        "asset_register_id": asset_id,
        "verified_register_delta_id": decision_id.replace("BRD", "VRD"),
        "review_sequence": sequence,
        "field": "julia" if "JULIA" in decision_id else "saint_malo",
        "proposed_structure_class": "riser",
        "candidate_class": "riser_candidate",
        "field_join_key": f"field|segment|{sequence}",
        "segment_number": "18918" if sequence == "1" else "18385",
        "selected_basis_document_family": "row",
        "selected_basis_document_id": "25025" if sequence == "1" else "24001",
        "selected_basis_page_number": "54" if sequence == "1" else "12",
        "selected_basis_source": "recommended_basis_page",
        "source_pdf_path": "source_documents/row/25025.pdf",
        "thumbnail_path": f"thumbnails/{sequence}.png",
        "evidence_packet_path": "basis_acceptance.html",
        "basis_page_accepted": "",
        "basis_decision": "",
        "basis_evidence_type": "",
        "observed_structure_class": "",
        "observed_quantity": "",
        "observed_segment_or_asset_id": "",
        "promote_to_verified_register": "",
        "verified_structure_class": "",
        "verified_quantity": "",
        "verified_segment_or_asset_id": "",
        "verified_asset_name": "",
        "verified_asset_role": "",
        "design_basis_reference": "",
        "basis_reviewer": "",
        "basis_review_date": "",
        "basis_review_notes": "",
        "follow_up_required": "",
        "follow_up_owner": "",
    }
