"""Tests for BSEE field infrastructure package generation."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pandas as pd

from tests.unit.bsee.pipeline.test_field_infrastructure import _fixture_data_root


def _fixture_bundle_dir(tmp_path: Path) -> Path:
    from worldenergydata.bsee.pipeline.field_infrastructure import (
        build_field_infrastructure_bundle,
        write_field_infrastructure_bundle,
    )

    data_root = _fixture_data_root(tmp_path)
    bundle = build_field_infrastructure_bundle("Test Field", data_root=data_root)
    bundle_dir = tmp_path / "bundle"
    write_field_infrastructure_bundle(bundle, bundle_dir)
    return bundle_dir


def test_build_field_package_writes_engineering_report_and_document_queue(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.field_package import build_field_package

    bundle_dir = _fixture_bundle_dir(tmp_path)
    output_dir = tmp_path / "field-package"

    paths = build_field_package(bundle_dir, output_dir)

    assert set(paths) == {"html_report", "document_queue"}
    assert paths["html_report"] == output_dir / "index.html"
    assert paths["document_queue"] == output_dir / "document_queue.csv"

    html_report = paths["html_report"].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_report
    assert "field-infrastructure-package-v1" in html_report
    assert "Test Field" in html_report
    assert "TF001" in html_report
    assert "A Test FPSO" in html_report
    assert "Pipeline Segments" in html_report
    assert "RISER" in html_report
    assert "SUBSEA MANIFOLD" in html_report
    assert "Document Retrieval Queue" in html_report
    assert "Retrieve indexed BSEE documents before detailed design" in html_report
    assert "https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/0/501.pdf" in html_report
    assert "Open PDF" in html_report

    document_queue = pd.read_csv(paths["document_queue"])
    assert document_queue.columns.tolist() == [
        "priority_rank",
        "document_family",
        "document_id",
        "segment_number",
        "lease_number",
        "row_number",
        "control_number",
        "document_type",
        "document_date",
        "retrieval_reason",
        "retrieval_url",
        "retrieval_status",
        "query_url",
        "evidence_confidence",
        "source_table",
    ]
    assert document_queue["priority_rank"].tolist() == [1, 2, 3]
    assert set(document_queue["document_family"]) == {"pipeline_map", "row", "plan"}
    assert document_queue.loc[0, "retrieval_reason"] == (
        "Review pipeline map for segment geometry and appurtenance context"
    )
    assert document_queue.loc[0, "retrieval_url"] == (
        "https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/0/501.pdf"
    )
    assert document_queue.loc[1, "retrieval_url"] == (
        "https://www.data.bsee.gov/PDFDocs/Scan/ROW/0/601.pdf"
    )
    assert document_queue.loc[2, "retrieval_url"] == (
        "https://www.data.bsee.gov/PDFDocs/Scan/PLANS/0/701.pdf"
    )
    assert document_queue["retrieval_status"].tolist() == [
        "candidate_pdf_url",
        "candidate_pdf_url",
        "candidate_pdf_url",
    ]

    summary = json.loads((bundle_dir / "engineering_summary.json").read_text())
    assert summary["document_count"] == len(document_queue)


def test_bsee_field_package_cli_writes_product_files(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    bundle_dir = _fixture_bundle_dir(tmp_path)
    output_dir = tmp_path / "cli-field-package"
    runner = CliRunner()

    result = runner.invoke(
        _load_bsee_command_app(),
        [
            "field-package",
            "--bundle",
            str(bundle_dir),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "field-infrastructure-package-v1" in result.output
    assert (output_dir / "index.html").is_file()
    assert (output_dir / "document_queue.csv").is_file()


def _load_bsee_command_app():
    module_path = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "worldenergydata"
        / "cli"
        / "commands"
        / "bsee.py"
    )
    spec = importlib.util.spec_from_file_location("bsee_command_under_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app
