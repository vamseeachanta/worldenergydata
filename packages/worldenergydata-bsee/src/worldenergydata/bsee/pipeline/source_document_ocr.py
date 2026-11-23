"""OCR image-only BSEE source documents into a searchable index."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.bsee.pipeline.source_document_index import (
    DEFAULT_ENGINEERING_TERMS,
    TERM_TAGS,
)

SOURCE_DOCUMENT_OCR_COLUMNS = [
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

OcrTextExtractor = Callable[[Path, int, int], tuple[str, int]]


class SourceDocumentOcrError(ValueError):
    """Raised when OCR indexing cannot be built."""


def build_source_document_ocr_index(
    source_index_path: Path | str,
    package_dir: Path | str,
    *,
    output_path: Path | str | None = None,
    families: list[str] | None = None,
    terms: list[str] | None = None,
    limit: int | None = None,
    max_pages: int = 1,
    dpi: int = 200,
    ocr_text: OcrTextExtractor | None = None,
) -> dict[str, Path | int]:
    """OCR no-text source-document rows and write a searchable CSV index."""
    index_path = Path(source_index_path)
    if not index_path.is_file():
        raise SourceDocumentOcrError(f"Source document index missing: {index_path}")

    root = Path(package_dir)
    output = (
        Path(output_path)
        if output_path is not None
        else root / "source_document_ocr_index.csv"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    source_index = pd.read_csv(index_path)
    _validate_source_index(source_index)
    target_rows = _target_rows(source_index, families, limit)
    active_terms = _normalize_terms(terms or DEFAULT_ENGINEERING_TERMS)
    extractor = ocr_text or _ocr_pdf_text

    rows = [
        _ocr_index_row(row, root, active_terms, max_pages, dpi, extractor)
        for _, row in target_rows.iterrows()
    ]
    ocr_index = pd.DataFrame(rows, columns=SOURCE_DOCUMENT_OCR_COLUMNS)
    ocr_index.to_csv(output, index=False)

    return {
        "index": output,
        "attempted": int(len(ocr_index)),
        "ocr_extracted": _count_status(ocr_index, "ocr_extracted"),
        "ocr_no_text": _count_status(ocr_index, "ocr_no_text"),
        "errors": _count_status(ocr_index, "ocr_error"),
    }


def _validate_source_index(source_index: pd.DataFrame) -> None:
    required = {
        "priority_rank",
        "document_family",
        "document_id",
        "local_path",
        "page_count",
        "extraction_status",
    }
    missing = sorted(required.difference(source_index.columns))
    if missing:
        raise SourceDocumentOcrError(
            f"Source document index missing columns: {missing}"
        )


def _target_rows(
    source_index: pd.DataFrame,
    families: list[str] | None,
    limit: int | None,
) -> pd.DataFrame:
    rows = source_index[source_index["extraction_status"].eq("extracted_no_text")]
    if families:
        family_set = {family.lower() for family in families}
        rows = rows[rows["document_family"].astype(str).str.lower().isin(family_set)]
    return rows.head(limit)


def _ocr_index_row(
    row: pd.Series,
    package_dir: Path,
    terms: list[str],
    max_pages: int,
    dpi: int,
    ocr_text: OcrTextExtractor,
) -> dict[str, object]:
    base = _base_ocr_row(row)
    local_path = _text(row.get("local_path"))
    if not local_path:
        return {**base, "ocr_status": "ocr_error", "error": "missing local_path"}

    source_path = package_dir / local_path
    if not source_path.is_file():
        return {
            **base,
            "ocr_status": "ocr_error",
            "error": f"missing file: {local_path}",
        }

    try:
        text, ocr_pages = ocr_text(source_path, max_pages, dpi)
    except Exception as exc:
        return {**base, "ocr_status": "ocr_error", "error": str(exc)}

    if not text:
        return {
            **base,
            "ocr_pages": ocr_pages,
            "ocr_status": "ocr_no_text",
            "error": "ocr produced no text",
        }

    matched_terms = _matched_terms(text, terms)
    tag_terms = _matched_terms(
        text, _normalize_terms(DEFAULT_ENGINEERING_TERMS + terms)
    )
    return {
        **base,
        "ocr_pages": ocr_pages,
        "ocr_char_count": len(text),
        "matched_terms": "|".join(matched_terms),
        "engineering_tags": "|".join(_engineering_tags(tag_terms)),
        "ocr_excerpt": _excerpt(text),
        "ocr_status": "ocr_extracted",
    }


def _base_ocr_row(row: pd.Series) -> dict[str, object]:
    return {
        "priority_rank": _text(row.get("priority_rank")),
        "document_family": _text(row.get("document_family")),
        "document_id": _text(row.get("document_id")),
        "local_path": _text(row.get("local_path")),
        "page_count": _text(row.get("page_count")),
        "ocr_pages": 0,
        "ocr_char_count": 0,
        "matched_terms": "",
        "engineering_tags": "",
        "ocr_excerpt": "",
        "ocr_status": "",
        "error": "",
    }


def _ocr_pdf_text(path: Path, max_pages: int, dpi: int) -> tuple[str, int]:
    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not pdftoppm or not tesseract:
        raise SourceDocumentOcrError("pdftoppm and tesseract are required for OCR")

    pages = max(0, max_pages)
    chunks: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for page_number in range(1, pages + 1):
            image_prefix = temp_root / f"page_{page_number}"
            _run(
                [
                    pdftoppm,
                    "-f",
                    str(page_number),
                    "-l",
                    str(page_number),
                    "-r",
                    str(dpi),
                    "-png",
                    str(path),
                    str(image_prefix),
                ]
            )
            image_path = _first_image(image_prefix)
            if image_path is None:
                continue
            chunks.append(_run([tesseract, str(image_path), "stdout"]))
    return _normalize_space("\n".join(chunks)), pages


def _run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _first_image(prefix: Path) -> Path | None:
    matches = sorted(prefix.parent.glob(f"{prefix.name}-*.png"))
    return matches[0] if matches else None


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
    return int((index["ocr_status"] == status).sum())


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
