"""Tests for BSEE source document indexing products."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from tests.unit.bsee.pipeline.test_field_package import _load_bsee_command_app


def _manifest_csv(package_dir: Path) -> Path:
    docs_dir = package_dir / "source_documents" / "pipeline_map"
    docs_dir.mkdir(parents=True)
    (docs_dir / "501.pdf").write_bytes(b"%PDF-1.7 fixture")
    (docs_dir / "502.pdf").write_bytes(b"<!DOCTYPE html>")
    manifest = package_dir / "download_manifest.csv"
    pd.DataFrame(
        [
            {
                "priority_rank": 1,
                "document_family": "pipeline_map",
                "document_id": 501,
                "retrieval_url": (
                    "https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/0/501.pdf"
                ),
                "local_path": "source_documents/pipeline_map/501.pdf",
                "download_status": "cached",
            },
            {
                "priority_rank": 2,
                "document_family": "pipeline_map",
                "document_id": 502,
                "retrieval_url": (
                    "https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/0/502.pdf"
                ),
                "local_path": "source_documents/pipeline_map/502.pdf",
                "download_status": "cached_non_pdf",
            },
        ]
    ).to_csv(manifest, index=False)
    return manifest


def test_build_source_document_index_writes_searchable_term_index(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.source_document_index import (
        build_source_document_index,
    )

    manifest = _manifest_csv(tmp_path)

    def fake_extract_text(path: Path, max_pages: int) -> tuple[str, int, int]:
        assert path.name == "501.pdf"
        assert max_pages == 3
        return (
            "Pipeline riser and subsea manifold tie-in near host platform.",
            7,
            3,
        )

    paths = build_source_document_index(
        manifest,
        tmp_path,
        terms=["pipeline", "riser", "manifold", "umbilical"],
        max_pages=3,
        extract_text=fake_extract_text,
    )

    assert paths["index"] == tmp_path / "source_document_index.csv"
    index = pd.read_csv(paths["index"])
    assert index.columns.tolist() == [
        "priority_rank",
        "document_family",
        "document_id",
        "retrieval_url",
        "local_path",
        "download_status",
        "page_count",
        "extracted_pages",
        "text_char_count",
        "matched_terms",
        "engineering_tags",
        "text_excerpt",
        "extraction_status",
        "error",
    ]
    assert index.loc[0, "extraction_status"] == "extracted"
    assert index.loc[0, "page_count"] == 7
    assert index.loc[0, "extracted_pages"] == 3
    assert index.loc[0, "matched_terms"] == "manifold|pipeline|riser"
    assert index.loc[0, "engineering_tags"] == "host|pipeline|subsea"
    assert "subsea manifold tie-in" in index.loc[0, "text_excerpt"]
    assert index.loc[1, "extraction_status"] == "skipped_download_status"
    assert index.loc[1, "error"] == "download_status=cached_non_pdf"


def test_build_source_document_index_flags_pdfs_with_no_extractable_text(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.source_document_index import (
        build_source_document_index,
    )

    manifest = _manifest_csv(tmp_path)

    def fake_extract_text(path: Path, max_pages: int) -> tuple[str, int, int]:
        return "", 2, 2

    paths = build_source_document_index(
        manifest,
        tmp_path,
        max_pages=2,
        extract_text=fake_extract_text,
    )

    index = pd.read_csv(paths["index"])
    assert index.loc[0, "extraction_status"] == "extracted_no_text"
    assert index.loc[0, "error"] == "no extractable text in selected pages"


def test_bsee_index_documents_cli_writes_source_document_index(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline import source_document_index

    manifest = _manifest_csv(tmp_path)
    output = tmp_path / "index-output.csv"
    calls: dict[str, object] = {}

    def fake_build_source_document_index(
        manifest_path: Path,
        package_dir: Path,
        *,
        output_path: Path | None = None,
        terms: list[str] | None = None,
        max_pages: int = 2,
    ) -> dict[str, Path | int]:
        calls.update(
            {
                "manifest_path": manifest_path,
                "package_dir": package_dir,
                "output_path": output_path,
                "terms": terms,
                "max_pages": max_pages,
            }
        )
        pd.DataFrame([{"extraction_status": "extracted"}]).to_csv(
            output_path,
            index=False,
        )
        return {
            "index": output_path,
            "attempted": 1,
            "extracted": 1,
            "skipped": 0,
            "errors": 0,
        }

    monkeypatch.setattr(
        source_document_index,
        "build_source_document_index",
        fake_build_source_document_index,
    )

    result = CliRunner().invoke(
        _load_bsee_command_app(),
        [
            "index-documents",
            "--manifest",
            str(manifest),
            "--package-dir",
            str(tmp_path),
            "--output",
            str(output),
            "--term",
            "riser",
            "--term",
            "pipeline",
            "--max-pages",
            "4",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "source document index" in result.output.lower()
    assert calls == {
        "manifest_path": manifest,
        "package_dir": tmp_path,
        "output_path": output,
        "terms": ["riser", "pipeline"],
        "max_pages": 4,
    }
