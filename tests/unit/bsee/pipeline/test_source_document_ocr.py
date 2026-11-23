"""Tests for OCR indexing of BSEE source documents."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from tests.unit.bsee.pipeline.test_field_package import _load_bsee_command_app


def _source_index_csv(package_dir: Path) -> Path:
    docs_dir = package_dir / "source_documents" / "pipeline_map"
    docs_dir.mkdir(parents=True)
    (docs_dir / "501.pdf").write_bytes(b"%PDF image-only")
    (docs_dir / "502.pdf").write_bytes(b"%PDF text-searchable")
    index = package_dir / "source_document_index.csv"
    pd.DataFrame(
        [
            {
                "priority_rank": 1,
                "document_family": "pipeline_map",
                "document_id": 501,
                "local_path": "source_documents/pipeline_map/501.pdf",
                "page_count": 2,
                "extraction_status": "extracted_no_text",
            },
            {
                "priority_rank": 2,
                "document_family": "pipeline_map",
                "document_id": 502,
                "local_path": "source_documents/pipeline_map/502.pdf",
                "page_count": 2,
                "extraction_status": "extracted",
            },
        ]
    ).to_csv(index, index=False)
    return index


def test_build_source_document_ocr_index_writes_ocr_term_index(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.source_document_ocr import (
        build_source_document_ocr_index,
    )

    index = _source_index_csv(tmp_path)

    def fake_ocr(path: Path, max_pages: int, dpi: int) -> tuple[str, int]:
        assert path.name == "501.pdf"
        assert max_pages == 1
        assert dpi == 200
        return "Jumper manifold riser umbilical pipeline drawing", 1

    paths = build_source_document_ocr_index(
        index,
        tmp_path,
        families=["pipeline_map"],
        terms=["pipeline", "riser", "jumper", "umbilical"],
        max_pages=1,
        dpi=200,
        ocr_text=fake_ocr,
    )

    assert paths["index"] == tmp_path / "source_document_ocr_index.csv"
    ocr = pd.read_csv(paths["index"])
    assert ocr.columns.tolist() == [
        "priority_rank",
        "document_family",
        "document_id",
        "local_path",
        "page_count",
        "ocr_pages",
        "ocr_char_count",
        "matched_terms",
        "engineering_tags",
        "ocr_excerpt",
        "ocr_status",
        "error",
    ]
    assert len(ocr) == 1
    assert ocr.loc[0, "document_id"] == 501
    assert ocr.loc[0, "ocr_pages"] == 1
    assert ocr.loc[0, "matched_terms"] == "jumper|pipeline|riser|umbilical"
    assert ocr.loc[0, "engineering_tags"] == "pipeline|subsea"
    assert "manifold riser" in ocr.loc[0, "ocr_excerpt"]
    assert ocr.loc[0, "ocr_status"] == "ocr_extracted"


def test_bsee_ocr_documents_cli_writes_ocr_index(monkeypatch, tmp_path: Path) -> None:
    from worldenergydata.bsee.pipeline import source_document_ocr

    index = _source_index_csv(tmp_path)
    output = tmp_path / "ocr-output.csv"
    calls: dict[str, object] = {}

    def fake_build_source_document_ocr_index(
        source_index_path: Path,
        package_dir: Path,
        *,
        output_path: Path | None = None,
        families: list[str] | None = None,
        terms: list[str] | None = None,
        limit: int | None = None,
        max_pages: int = 1,
        dpi: int = 200,
    ) -> dict[str, Path | int]:
        calls.update(
            {
                "source_index_path": source_index_path,
                "package_dir": package_dir,
                "output_path": output_path,
                "families": families,
                "terms": terms,
                "limit": limit,
                "max_pages": max_pages,
                "dpi": dpi,
            }
        )
        pd.DataFrame([{"ocr_status": "ocr_extracted"}]).to_csv(output_path, index=False)
        return {
            "index": output_path,
            "attempted": 1,
            "ocr_extracted": 1,
            "ocr_no_text": 0,
            "errors": 0,
        }

    monkeypatch.setattr(
        source_document_ocr,
        "build_source_document_ocr_index",
        fake_build_source_document_ocr_index,
    )

    result = CliRunner().invoke(
        _load_bsee_command_app(),
        [
            "ocr-documents",
            "--index",
            str(index),
            "--package-dir",
            str(tmp_path),
            "--output",
            str(output),
            "--family",
            "pipeline_map",
            "--term",
            "riser",
            "--limit",
            "1",
            "--max-pages",
            "2",
            "--dpi",
            "250",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "ocr index" in result.output.lower()
    assert calls == {
        "source_index_path": index,
        "package_dir": tmp_path,
        "output_path": output,
        "families": ["pipeline_map"],
        "terms": ["riser"],
        "limit": 1,
        "max_pages": 2,
        "dpi": 250,
    }
