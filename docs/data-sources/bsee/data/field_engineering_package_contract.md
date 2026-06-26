# Field Engineering Package Contract

Contract version: `field-infrastructure-package-v1`

## Purpose

The field engineering package turns a field infrastructure bundle into a
human-facing screening artifact for engineering and product workflows.

Generate it from an existing bundle:

```bash
worldenergydata bsee field-package \
  --bundle reports/bsee/field_infrastructure/stones \
  --output reports/bsee/field_packages/stones
```

Retrieve source PDFs from the package queue:

```bash
worldenergydata bsee retrieve-documents \
  --queue reports/bsee/field_packages/stones/document_queue.csv \
  --output reports/bsee/field_packages/stones
```

Index retrieved source PDFs for engineering terms:

```bash
worldenergydata bsee index-documents \
  --manifest reports/bsee/field_packages/stones/download_manifest.csv \
  --package-dir reports/bsee/field_packages/stones \
  --max-pages 2
```

OCR no-text PDFs when visual scans need searchable text:

```bash
worldenergydata bsee ocr-documents \
  --index reports/bsee/field_packages/stones/source_document_index.csv \
  --package-dir reports/bsee/field_packages/stones \
  --family pipeline_map \
  --max-pages 1
```

## Files

| File | Product use |
|---|---|
| `index.html` | Static engineering package with field context, infrastructure counts, pipeline/appurtenance highlights, document queue, and evidence caveats. |
| `document_queue.csv` | Prioritized retrieval queue for BSEE pipeline maps, ROW files, and plans. |
| `source_documents/` | Retrieved BSEE scanned source PDFs, grouped by document family. |
| `download_manifest.csv` | Audit manifest for retrieved, cached, skipped, or failed source-document rows. |
| `source_document_index.csv` | Searchable per-document index with page counts, extracted text snippets, matched engineering terms, and extraction status. |
| `source_document_ocr_index*.csv` | OCR-derived search indexes for `extracted_no_text` rows, usually run by family and with bounded pages. |

## Document Queue Columns

| Column | Meaning |
|---|---|
| `priority_rank` | Sequential package priority after sorting by document family and segment/document identifiers. |
| `document_family` | BSEE index family: `pipeline_map`, `row`, `plan`, or other indexed family. |
| `document_id` | BSEE scanned document identifier when present. |
| `segment_number` | BSEE pipeline segment number when the document is segment-linked. |
| `lease_number` | Lease number when the document is lease-linked. |
| `row_number` | Right-of-way identifier when present. |
| `control_number` | Plan control number when present. |
| `document_type` | Source document type code or label. |
| `document_date` | Source document date as carried by BSEE. |
| `retrieval_reason` | Product-facing reason to retrieve/review the source document. |
| `retrieval_url` | Candidate direct BSEE scanned-document PDF URL generated from `document_family` and `document_id`. |
| `retrieval_status` | URL provenance; `candidate_pdf_url` means the URL follows the observed BSEE `PDFDocs/Scan/<family>/<thousands>/<doc_id>.pdf` convention. |
| `query_url` | Official BSEE scanned-document query page for the document family. |
| `evidence_confidence` | Original bundle confidence, usually `document_index`. |
| `source_table` | Source BSEE table from the field infrastructure bundle. |

## Download Manifest Columns

| Column | Meaning |
|---|---|
| `priority_rank` | Queue priority copied from `document_queue.csv`. |
| `document_family` | BSEE index family copied from `document_queue.csv`. |
| `document_id` | BSEE scanned document identifier copied from `document_queue.csv`. |
| `retrieval_url` | Direct BSEE PDF URL attempted by the downloader. |
| `local_path` | Relative path to the retrieved or cached PDF under the package output directory. |
| `http_status` | HTTP response status for attempted network downloads. |
| `content_type` | Response content type when supplied by BSEE. |
| `byte_count` | Stored PDF byte count. |
| `sha256` | SHA-256 hash of the stored PDF bytes. |
| `download_status` | `downloaded`, `cached`, `skipped_no_url`, `http_error`, `request_error`, `non_pdf_response`, or `cached_non_pdf`. |
| `error` | Per-row error detail for failed requests. |
| `retrieved_at_utc` | UTC timestamp for the manifest row. |

## Source Document Index Columns

| Column | Meaning |
|---|---|
| `priority_rank` | Queue priority copied from `download_manifest.csv`. |
| `document_family` | BSEE index family copied from `download_manifest.csv`. |
| `document_id` | BSEE scanned document identifier copied from `download_manifest.csv`. |
| `retrieval_url` | Direct BSEE PDF URL copied from the manifest. |
| `local_path` | Relative package path to the source document. |
| `download_status` | Retrieval status copied from the manifest. |
| `page_count` | PDF page count reported by the parser. |
| `extracted_pages` | Number of pages attempted for text extraction. |
| `text_char_count` | Character count after normalizing extracted text. |
| `matched_terms` | Pipe-delimited engineering terms found in extracted text. |
| `engineering_tags` | Pipe-delimited higher-level tags such as `pipeline`, `subsea`, `host`, and `well`. |
| `text_excerpt` | Bounded normalized text snippet for screening. |
| `extraction_status` | `extracted`, `extracted_no_text`, `skipped_download_status`, `skipped_missing_path`, `skipped_missing_file`, or `extraction_error`. |
| `error` | Per-row extraction issue or skip reason. |

## Source Document OCR Columns

| Column | Meaning |
|---|---|
| `priority_rank` | Queue priority copied from `source_document_index.csv`. |
| `document_family` | BSEE document family copied from `source_document_index.csv`. |
| `document_id` | BSEE scanned document identifier copied from `source_document_index.csv`. |
| `local_path` | Relative package path to the source document. |
| `page_count` | PDF page count copied from the source document index. |
| `ocr_pages` | Number of pages rasterized and OCRed. |
| `ocr_char_count` | OCR text character count after normalization. |
| `matched_terms` | Pipe-delimited engineering terms found in OCR text. |
| `engineering_tags` | Pipe-delimited higher-level tags such as `pipeline`, `subsea`, `host`, and `well`. |
| `ocr_excerpt` | Bounded OCR text snippet for screening. |
| `ocr_status` | `ocr_extracted`, `ocr_no_text`, or `ocr_error`. |
| `error` | Per-row OCR issue. |

## BSEE Scanned Document URL Convention

The package generates candidate direct PDF URLs from the observed official
BSEE scanned-document paths:

| Document family | Query page | PDF directory |
|---|---|---|
| `pipeline_map` | `https://www.data.bsee.gov/Other/FileRequestSystem/ScanPipelineMaps.aspx` | `https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/<doc_id // 1000>/<doc_id>.pdf` |
| `row` | `https://www.data.bsee.gov/Other/FileRequestSystem/ScanROW.aspx` | `https://www.data.bsee.gov/PDFDocs/Scan/ROW/<doc_id // 1000>/<doc_id>.pdf` |
| `plan` | `https://www.data.bsee.gov/Other/FileRequestSystem/ScanPlans.aspx` | `https://www.data.bsee.gov/PDFDocs/Scan/PLANS/<doc_id // 1000>/<doc_id>.pdf` |

Example: `DOC_ID=63725` in the plans family maps to
`https://www.data.bsee.gov/PDFDocs/Scan/PLANS/63/63725.pdf`.

## Product Rules

- Use `index.html` for screening, handoff, and product review.
- Use `document_queue.csv` as the next-work list for source document retrieval.
- Use `download_manifest.csv` as the source-document audit trail before
  promoting a package into engineering review.
- Use `source_document_index.csv` for text-searchable source-document triage.
  `extracted_no_text` rows are valid PDFs but need OCR or manual visual review.
- Use OCR indexes as assistive triage only. OCR on engineering drawings is
  noisy and must be checked against the source PDF before design use.
- Do not treat document-index rows as final engineering basis without
  retrieving and reviewing the underlying BSEE documents.
- Treat `retrieval_url` as a generated candidate until the PDF is opened or
  downloaded and reviewed.
- Treat `non_pdf_response` and `cached_non_pdf` rows as unresolved retrieval
  failures even when the HTTP status was `200`; use the `query_url` page or
  BSEE UI to investigate those documents.
- Keep this package downstream of the field infrastructure bundle; do not
  bypass `field_context.json`, `pipeline_segments.csv`, `appurtenances.csv`,
  or `documents.csv`.
