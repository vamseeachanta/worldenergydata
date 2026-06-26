"""Download BSEE scanned documents from field package retrieval queues."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx
import pandas as pd

DOCUMENT_MANIFEST_COLUMNS = [
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


class DocumentRetrievalError(ValueError):
    """Raised when a document queue cannot drive retrieval."""


class DocumentHttpClient(Protocol):
    """Minimal HTTP client interface used by document retrieval."""

    def get(self, url: str, **kwargs: object) -> Any:
        """Return an HTTP response object for the URL."""


def download_document_queue(
    queue: Path | str,
    output: Path | str,
    *,
    limit: int | None = None,
    overwrite: bool = False,
    timeout: float = 60.0,
    client: DocumentHttpClient | None = None,
) -> dict[str, Path | int]:
    """Download PDFs from a field package `document_queue.csv`.

    Args:
        queue: CSV written by `worldenergydata bsee field-package`.
        output: Directory where `source_documents/` and the manifest are written.
        limit: Optional maximum number of queue rows to process.
        overwrite: Redownload documents that already exist.
        timeout: Per-request timeout in seconds.
        client: Optional test or preconfigured HTTP client.
    """
    queue_path = Path(queue)
    if not queue_path.is_file():
        raise DocumentRetrievalError(f"Document queue does not exist: {queue_path}")

    output_dir = Path(output)
    documents_dir = output_dir / "source_documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

    document_queue = pd.read_csv(queue_path).head(limit)
    _validate_queue(document_queue)

    owns_client = client is None
    http_client = client or httpx.Client(headers={"User-Agent": "worldenergydata/field-documents"})
    try:
        manifest_rows = [
            _retrieve_row(row, documents_dir, overwrite, timeout, http_client)
            for _, row in document_queue.iterrows()
        ]
    finally:
        if owns_client and hasattr(http_client, "close"):
            http_client.close()

    manifest = pd.DataFrame(manifest_rows, columns=DOCUMENT_MANIFEST_COLUMNS)
    manifest_path = output_dir / "download_manifest.csv"
    manifest.to_csv(manifest_path, index=False)

    return {
        "manifest": manifest_path,
        "documents_dir": documents_dir,
        "attempted": int(len(manifest)),
        "downloaded": _count_status(manifest, "downloaded"),
        "cached": _count_status(manifest, "cached"),
        "skipped": int(manifest["download_status"].astype(str).str.startswith("skipped").sum()),
        "errors": int(
            manifest["download_status"]
            .isin(["http_error", "request_error", "non_pdf_response", "cached_non_pdf"])
            .sum()
        ),
    }


def _validate_queue(document_queue: pd.DataFrame) -> None:
    required = {"priority_rank", "document_family", "document_id", "retrieval_url"}
    missing = sorted(required.difference(document_queue.columns))
    if missing:
        raise DocumentRetrievalError(f"Document queue missing columns: {missing}")


def _retrieve_row(
    row: pd.Series,
    documents_dir: Path,
    overwrite: bool,
    timeout: float,
    client: DocumentHttpClient,
) -> dict[str, object]:
    family = _safe_name(_text(row.get("document_family")) or "document")
    document_id = _document_id(row.get("document_id"))
    url = _text(row.get("retrieval_url"))
    retrieved_at = _retrieved_at()
    base_row = {
        "priority_rank": _text(row.get("priority_rank")),
        "document_family": _text(row.get("document_family")),
        "document_id": document_id,
        "retrieval_url": url,
        "local_path": "",
        "http_status": "",
        "content_type": "",
        "byte_count": 0,
        "sha256": "",
        "download_status": "",
        "error": "",
        "retrieved_at_utc": retrieved_at,
    }
    if not url:
        return {**base_row, "download_status": "skipped_no_url"}

    local_path = Path("source_documents") / family / f"{document_id}.pdf"
    target = documents_dir / family / f"{document_id}.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        content = target.read_bytes()
        is_pdf = _is_pdf(content)
        return {
            **base_row,
            "local_path": local_path.as_posix(),
            "byte_count": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "download_status": "cached" if is_pdf else "cached_non_pdf",
            "error": "" if is_pdf else "Cached file did not start with %PDF",
        }

    try:
        response = client.get(url, follow_redirects=True, timeout=timeout)
    except Exception as exc:
        return {
            **base_row,
            "local_path": local_path.as_posix(),
            "download_status": "request_error",
            "error": str(exc),
        }

    status_code = int(getattr(response, "status_code", 0) or 0)
    headers = getattr(response, "headers", {})
    content_type = _header(headers, "content-type")
    if status_code != 200:
        return {
            **base_row,
            "local_path": local_path.as_posix(),
            "http_status": status_code,
            "content_type": content_type,
            "download_status": "http_error",
            "error": f"HTTP {status_code}",
        }

    content = bytes(getattr(response, "content", b""))
    target.write_bytes(content)
    is_pdf = _is_pdf(content)
    return {
        **base_row,
        "local_path": local_path.as_posix(),
        "http_status": status_code,
        "content_type": content_type,
        "byte_count": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "download_status": "downloaded" if is_pdf else "non_pdf_response",
        "error": "" if is_pdf else "Response did not start with %PDF",
    }


def _count_status(manifest: pd.DataFrame, status: str) -> int:
    return int((manifest["download_status"] == status).sum())


def _is_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF")


def _document_id(value: Any) -> str:
    text = _text(value)
    try:
        number = float(text)
    except ValueError:
        return _safe_name(text or "unknown")
    if number.is_integer():
        return str(int(number))
    return _safe_name(text)


def _header(headers: Any, name: str) -> str:
    if isinstance(headers, Mapping):
        return _text(headers.get(name) or headers.get(name.title()))
    try:
        return _text(headers.get(name))
    except AttributeError:
        return ""


def _safe_name(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in value)
    return safe.strip("_") or "unknown"


def _retrieved_at() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
