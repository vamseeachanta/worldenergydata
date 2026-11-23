"""Build searchable engineering indexes from retrieved BSEE source PDFs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

SOURCE_DOCUMENT_INDEX_COLUMNS = [
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

DEFAULT_ENGINEERING_TERMS = [
    "pipeline",
    "flowline",
    "riser",
    "jumper",
    "umbilical",
    "manifold",
    "plet",
    "flet",
    "tie-in",
    "tieback",
    "host",
    "platform",
    "fpso",
    "subsea",
    "well",
    "tree",
]

TERM_TAGS = {
    "pipeline": "pipeline",
    "flowline": "pipeline",
    "riser": "pipeline",
    "jumper": "pipeline",
    "umbilical": "pipeline",
    "manifold": "subsea",
    "plet": "subsea",
    "flet": "subsea",
    "tie-in": "subsea",
    "tieback": "subsea",
    "host": "host",
    "platform": "host",
    "fpso": "host",
    "subsea": "subsea",
    "well": "well",
    "tree": "well",
}

VALID_DOCUMENT_STATUSES = {"downloaded", "cached"}
TextExtractor = Callable[[Path, int], tuple[str, int, int]]


class SourceDocumentIndexError(ValueError):
    """Raised when a source document index cannot be built."""


def build_source_document_index(
    manifest_path: Path | str,
    package_dir: Path | str,
    *,
    output_path: Path | str | None = None,
    terms: list[str] | None = None,
    max_pages: int = 2,
    extract_text: TextExtractor | None = None,
) -> dict[str, Path | int]:
    """Write a searchable index from a BSEE source-document manifest.

    Args:
        manifest_path: `download_manifest.csv` from `retrieve-documents`.
        package_dir: Directory that contains the manifest's relative local paths.
        output_path: Optional CSV output path. Defaults to package_dir/index file.
        terms: Optional term list. Defaults to engineering infrastructure terms.
        max_pages: Maximum pages to extract from each PDF.
        extract_text: Optional extraction function for tests or alternate parsers.
    """
    manifest = Path(manifest_path)
    if not manifest.is_file():
        raise SourceDocumentIndexError(f"Manifest does not exist: {manifest}")
    root = Path(package_dir)
    output = (
        Path(output_path)
        if output_path is not None
        else root / "source_document_index.csv"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest_df = pd.read_csv(manifest)
    _validate_manifest(manifest_df)
    active_terms = _normalize_terms(terms or DEFAULT_ENGINEERING_TERMS)
    extractor = extract_text or _extract_pdf_text

    rows = [
        _index_manifest_row(row, root, active_terms, max_pages, extractor)
        for _, row in manifest_df.iterrows()
    ]
    index = pd.DataFrame(rows, columns=SOURCE_DOCUMENT_INDEX_COLUMNS)
    index.to_csv(output, index=False)

    return {
        "index": output,
        "attempted": int(len(index)),
        "extracted": _count_status(index, "extracted"),
        "no_text": _count_status(index, "extracted_no_text"),
        "skipped": int(
            index["extraction_status"].astype(str).str.startswith("skipped").sum()
        ),
        "errors": _count_status(index, "extraction_error"),
    }


def _validate_manifest(manifest_df: pd.DataFrame) -> None:
    required = {
        "priority_rank",
        "document_family",
        "document_id",
        "retrieval_url",
        "local_path",
        "download_status",
    }
    missing = sorted(required.difference(manifest_df.columns))
    if missing:
        raise SourceDocumentIndexError(f"Manifest missing columns: {missing}")


def _index_manifest_row(
    row: pd.Series,
    package_dir: Path,
    terms: list[str],
    max_pages: int,
    extract_text: TextExtractor,
) -> dict[str, object]:
    base = _base_index_row(row)
    status = _text(row.get("download_status"))
    local_path = _text(row.get("local_path"))
    if status not in VALID_DOCUMENT_STATUSES:
        return {
            **base,
            "extraction_status": "skipped_download_status",
            "error": f"download_status={status}",
        }
    if not local_path:
        return {
            **base,
            "extraction_status": "skipped_missing_path",
            "error": "missing local_path",
        }

    source_path = package_dir / local_path
    if not source_path.is_file():
        return {
            **base,
            "extraction_status": "skipped_missing_file",
            "error": f"missing file: {local_path}",
        }

    try:
        text, page_count, extracted_pages = extract_text(source_path, max_pages)
    except Exception as exc:
        return {**base, "extraction_status": "extraction_error", "error": str(exc)}

    if not text:
        return {
            **base,
            "page_count": page_count,
            "extracted_pages": extracted_pages,
            "extraction_status": "extracted_no_text",
            "error": "no extractable text in selected pages",
        }

    matched_terms = _matched_terms(text, terms)
    tag_terms = _matched_terms(
        text, _normalize_terms(DEFAULT_ENGINEERING_TERMS + terms)
    )
    return {
        **base,
        "page_count": page_count,
        "extracted_pages": extracted_pages,
        "text_char_count": len(text),
        "matched_terms": "|".join(matched_terms),
        "engineering_tags": "|".join(_engineering_tags(tag_terms)),
        "text_excerpt": _excerpt(text),
        "extraction_status": "extracted",
    }


def _base_index_row(row: pd.Series) -> dict[str, object]:
    return {
        "priority_rank": _text(row.get("priority_rank")),
        "document_family": _text(row.get("document_family")),
        "document_id": _text(row.get("document_id")),
        "retrieval_url": _text(row.get("retrieval_url")),
        "local_path": _text(row.get("local_path")),
        "download_status": _text(row.get("download_status")),
        "page_count": 0,
        "extracted_pages": 0,
        "text_char_count": 0,
        "matched_terms": "",
        "engineering_tags": "",
        "text_excerpt": "",
        "extraction_status": "",
        "error": "",
    }


def _extract_pdf_text(path: Path, max_pages: int) -> tuple[str, int, int]:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency declared in project
        raise SourceDocumentIndexError(
            "pdfplumber is required for PDF text extraction"
        ) from exc

    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        pages = pdf.pages[: max(0, max_pages)]
        for page in pages:
            chunks.append(page.extract_text() or "")
    text = "\n".join(chunk for chunk in chunks if chunk)
    return _normalize_space(text), page_count, len(pages)


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    normalized = text.lower()
    return sorted(term for term in terms if term in normalized)


def _engineering_tags(terms: list[str]) -> list[str]:
    tags = {TERM_TAGS.get(term, term) for term in terms}
    return sorted(tag for tag in tags if tag)


def _normalize_terms(terms: list[str]) -> list[str]:
    return sorted({_normalize_space(term).lower() for term in terms if _text(term)})


def _excerpt(text: str, limit: int = 320) -> str:
    normalized = _normalize_space(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _normalize_space(text: str) -> str:
    return " ".join(_text(text).split())


def _count_status(index: pd.DataFrame, status: str) -> int:
    return int((index["extraction_status"] == status).sum())


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
