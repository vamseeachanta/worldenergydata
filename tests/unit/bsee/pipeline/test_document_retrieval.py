"""Tests for BSEE scanned document retrieval products."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from tests.unit.bsee.pipeline.test_field_package import _load_bsee_command_app


PDF_BYTES = b"%PDF-1.7\nfield source document\n%%EOF\n"


class _FakeResponse:
    status_code = 200
    headers = {"content-type": "application/pdf"}
    content = PDF_BYTES


class _FakeHtmlResponse:
    status_code = 200
    headers = {"content-type": "text/html; charset=utf-8"}
    content = b"<!DOCTYPE html><html><body>not a pdf</body></html>"


class _FakeClient:
    def __init__(self, response: object | None = None) -> None:
        self.response = response or _FakeResponse()
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, **kwargs: object) -> object:
        self.calls.append((url, kwargs))
        return self.response


def _queue_csv(tmp_path: Path) -> Path:
    queue_path = tmp_path / "document_queue.csv"
    pd.DataFrame(
        [
            {
                "priority_rank": 1,
                "document_family": "pipeline_map",
                "document_id": 501,
                "retrieval_url": (
                    "https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/0/501.pdf"
                ),
                "retrieval_status": "candidate_pdf_url",
            },
            {
                "priority_rank": 2,
                "document_family": "row",
                "document_id": 601,
                "retrieval_url": "",
                "retrieval_status": "query_page_only",
            },
        ]
    ).to_csv(queue_path, index=False)
    return queue_path


def test_download_document_queue_writes_pdfs_and_audit_manifest(
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline.document_retrieval import (
        download_document_queue,
    )

    queue_path = _queue_csv(tmp_path)
    output_dir = tmp_path / "retrieved-documents"
    client = _FakeClient()

    paths = download_document_queue(queue_path, output_dir, client=client)

    assert paths["manifest"] == output_dir / "download_manifest.csv"
    assert paths["documents_dir"] == output_dir / "source_documents"
    assert client.calls == [
        (
            "https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/0/501.pdf",
            {"follow_redirects": True, "timeout": 60.0},
        )
    ]

    pdf_path = output_dir / "source_documents" / "pipeline_map" / "501.pdf"
    assert pdf_path.read_bytes() == PDF_BYTES

    manifest = pd.read_csv(paths["manifest"])
    assert manifest.columns.tolist() == [
        "priority_rank",
        "document_family",
        "document_id",
        "retrieval_url",
        "local_path",
        "http_status",
        "content_type",
        "byte_count",
        "sha256",
        "download_status",
        "error",
        "retrieved_at_utc",
    ]
    assert manifest.loc[0, "download_status"] == "downloaded"
    assert manifest.loc[0, "local_path"] == "source_documents/pipeline_map/501.pdf"
    assert manifest.loc[0, "http_status"] == 200
    assert manifest.loc[0, "byte_count"] == len(PDF_BYTES)
    assert manifest.loc[0, "sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()
    assert manifest.loc[1, "download_status"] == "skipped_no_url"


def test_bsee_retrieve_documents_cli_writes_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from worldenergydata.bsee.pipeline import document_retrieval

    queue_path = _queue_csv(tmp_path)
    output_dir = tmp_path / "cli-retrieved-documents"
    calls: dict[str, object] = {}

    def fake_download_document_queue(
        queue: Path,
        output: Path,
        *,
        limit: int | None = None,
        overwrite: bool = False,
        timeout: float = 60.0,
    ) -> dict[str, Path | int]:
        calls.update(
            {
                "queue": queue,
                "output": output,
                "limit": limit,
                "overwrite": overwrite,
                "timeout": timeout,
            }
        )
        output.mkdir(parents=True, exist_ok=True)
        manifest = output / "download_manifest.csv"
        pd.DataFrame([{"download_status": "downloaded"}]).to_csv(
            manifest,
            index=False,
        )
        return {
            "manifest": manifest,
            "documents_dir": output / "source_documents",
            "attempted": 1,
            "downloaded": 1,
            "cached": 0,
            "skipped": 0,
            "errors": 0,
        }

    monkeypatch.setattr(
        document_retrieval,
        "download_document_queue",
        fake_download_document_queue,
    )

    result = CliRunner().invoke(
        _load_bsee_command_app(),
        [
            "retrieve-documents",
            "--queue",
            str(queue_path),
            "--output",
            str(output_dir),
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "download_manifest.csv" in result.output
    assert calls == {
        "queue": queue_path,
        "output": output_dir,
        "limit": 1,
        "overwrite": False,
        "timeout": 60.0,
    }


def test_download_document_queue_flags_non_pdf_response(tmp_path: Path) -> None:
    from worldenergydata.bsee.pipeline.document_retrieval import (
        download_document_queue,
    )

    queue_path = _queue_csv(tmp_path)
    output_dir = tmp_path / "retrieved-documents"

    paths = download_document_queue(
        queue_path,
        output_dir,
        limit=1,
        client=_FakeClient(_FakeHtmlResponse()),
    )

    manifest = pd.read_csv(paths["manifest"])
    assert manifest.loc[0, "download_status"] == "non_pdf_response"
    assert manifest.loc[0, "error"] == "Response did not start with %PDF"
    assert (
        output_dir / "source_documents" / "pipeline_map" / "501.pdf"
    ).read_bytes() == _FakeHtmlResponse.content
