# Field Infrastructure Bundle Product Contract

Contract version: `field-infrastructure-bundle-v1`

## Files

| File | Product use |
|---|---|
| `field_context.json` | Field identity, BSEE field code, leases, area/block anchors, operator names, average water depth. |
| `structures.csv` | Direct and inferred infrastructure records: platforms/FPSOs, FMP measurement locations, MCP systems, platform decom records. |
| `pipeline_segments.csv` | Pipeline segment inventory from scanned map indexes and decom rows. Includes endpoints, product code, size code, source evidence, and confidence. |
| `pipeline_locations.csv` | Route/location rows for matched segment IDs. Includes lat/lon, sequence, datum code, and appurtenance type. |
| `appurtenances.csv` | Nonblank `PPL_APURT_TYPE` rows from pipeline locations. This is the first place to look for `RISER`, `TIE-IN`, `SUBSEA MANIFOLD`, and related structure classes. |
| `documents.csv` | Evidence queue for scanned pipeline maps, ROW files, and plans. Use this for document retrieval before detailed design claims. |
| `engineering_summary.json` | Product-facing counts, appurtenance types, route bounds, and contract version. |

## Evidence Levels

| `evidence_confidence` | Meaning |
|---|---|
| `direct` | The source row directly describes the asset or location being emitted. |
| `inferred` | The row is linked by lease, area/block, segment, or complex and is useful for screening but needs engineering review. |
| `document_index` | The row points to a scanned document or plan index. Retrieve the source document before relying on details. |

## Join Keys

| `join_key` | Meaning |
|---|---|
| `field_code|lease|area_block` | Direct structure join using any of these anchors. |
| `lease|area_block` | Pipeline/decom/document join through field leases or field area/block anchors. |
| `segment_number` | Pipeline-location or ROW join through a BSEE segment ID. |
| `lease` | Plan document join through field lease. |
| `lease|complex_id` | FMP measurement join through field leases or platform complex. |
| `lease_unit` | MCP system join through lease-unit rows. |
| `area_block|complex_id` | Platform decom join through location or platform complex. |

## Product Rules

- Treat `engineering_summary.json` as the fast screening header.
- Treat `pipeline_segments.csv` as the segment inventory and
  `pipeline_locations.csv` as the route/appurtenance detail.
- Treat `documents.csv` as the next-work queue for plan/map/ROW retrieval.
- Do not merge `document_index` rows into final engineering basis without
  retrieving and reviewing the scanned document.
- Keep all `source_table`, `join_key`, and `evidence_confidence` columns in
  product-facing exports.
- Preserve units: BSEE water depth is feet; `LATITUDE`/`LONGITUDE` are as
  carried by BSEE with the datum code in `nad_year`.

## Structure Discovery Notes

- There is no dedicated first-class BSEE bin table named for jumpers,
  risers, or umbilicals in the current local mirror.
- Riser evidence can appear in `pipeline_locations.csv` /
  `appurtenances.csv` through `PPL_APURT_TYPE`.
- Umbilical/flowline/tieback evidence can appear in
  `pipeline_segments.csv` through product codes and endpoint names such as
  `UMB`, `UMBE`, `UMBH`, `UBEH`, `PLET`, `PLEM`, `manifold`, `FLET`,
  `HIPPS`, `UTA`, and `MFLD`.

# Field Engineering Package Contract

Contract version: `field-infrastructure-package-v1`

Generate the package from an existing bundle:

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

Import filled reviewer inputs only after a human has accepted source-page
evidence:

```bash
worldenergydata bsee import-reviewer-inputs \
  --ready-input reports/bsee/field_packages/field_structure_reviewer_ready13_input_template_julia_stones_saint_malo.csv \
  --decision-log reports/bsee/field_packages/field_structure_basis_review_decision_log_top15_julia_stones_saint_malo.csv \
  --output reports/bsee/field_packages/reviewer_import \
  --sqlite-product reports/bsee/field_packages/field_structure_product_julia_stones_saint_malo.sqlite
```

## Files

| File | Product use |
|---|---|
| `index.html` | Static engineering package with field context, infrastructure counts, pipeline/appurtenance highlights, document queue, and evidence caveats. |
| `document_queue.csv` | Prioritized retrieval queue for BSEE pipeline maps, ROW files, and plans, including candidate direct PDF URLs. |
| `source_documents/` | Retrieved BSEE scanned source PDFs, grouped by document family. |
| `download_manifest.csv` | Audit manifest for retrieved, cached, skipped, or failed source-document rows. |
| `source_document_index.csv` | Searchable per-document index with page counts, text snippets, matched engineering terms, and extraction status. |
| `source_document_ocr_index*.csv` | OCR-derived search indexes for `extracted_no_text` rows, usually run by family and with bounded pages. |
| `field_document_evidence_*.csv` | Consolidated downstream evidence table combining parser and final OCR term-hit rows with source paths, snippets, and boolean engineering-term flags. |
| `field_engineering_join_input_*.csv` | Row-level join table that enriches document evidence with document queue keys, segment endpoints, product codes, appurtenance context, and structure context. |
| `field_structure_candidates_*.csv` | Aggregated candidate screening table for jumpers, risers, umbilicals, PLET/FLET, manifolds, flowlines, and host/tieback context. |
| `field_structure_review_queue_*.csv` | Ranked candidate review queue with source PDF paths, review priority, and recommended manual review action. |
| `field_structure_review_packet_*.html` | Browser review packet for the top ranked candidates, with local source PDF links and BSEE URL links. |
| `field_structure_review_workbook_*.csv` | Reviewer-fillable top-candidate workbook with blank status, verified class, quantity, notes, and follow-up fields. |
| `field_structure_review_evidence_*.csv` | Per-document evidence detail for workbook candidates, including excerpts, local PDF paths, BSEE URLs, and review instructions. |
| `field_structure_review_*_geometry*.geojson/.csv/.html` | Spatial screening layers and summaries for review candidates, built from pipeline route and appurtenance coordinates. |
| `field_structure_top*_source_contact_sheet/` | Source-review packet with PDF page thumbnails, a single PNG contact sheet, a source manifest, and links back to local PDFs/BSEE URLs. |
| `field_structure_top*_targeted_pages/` | Targeted source-page packet with pages scored by candidate segment IDs and structure terms, plus thumbnails and page-hit excerpts. |
| `field_structure_asset_register_top*_draft_*.csv/.html` | Draft register layer that promotes top review candidates into `pending_engineering_review` rows with source, targeted-page, geometry, and reviewer-decision fields. |
| `field_structure_product_manifest_*.json/.html` | Product-ingestion manifest with file catalog, row counts, hashes, validation checks, join keys, column contract, usage rules, known limits, and promotion gate. |
| `field_structure_product_*.sqlite` | Queryable product package with draft register, evidence, targeted pages, geometry features, pipeline segments, appurtenances, source documents, metadata, product views, and optional `latest_reviewer_import_*` tables/views after import publication. |
| `field_structure_engineering_review_batch_*.csv/.html` | One-row-per-candidate engineering review surface generated from SQLite views, with source, targeted-page, segment, appurtenance, geometry, review-focus, risk-note, and blank decision fields. |
| `field_structure_basis_page_queue_*.csv/.html` | Candidate-page review queue generated from SQLite targeted-page rows, with thumbnails, excerpts, source links, matched terms, extraction/render status, and blank basis-decision fields. |
| `field_structure_recommended_basis_page_*.csv/.html` | Top-ranked page per candidate generated from `v_recommended_basis_page`; use as a recommendation pending human acceptance, not as verified evidence. |
| `field_structure_field_join_readiness_*.csv/.html` | One-row-per-candidate product handoff surface for field-level joins, including field/segment join key, segment context, appurtenance context, geometry coverage, source-document coverage, recommended basis page, and blank field-join review fields. |
| `field_structure_verified_register_delta_template_*.csv/.html` | Reviewer-fillable promotion queue with candidate context plus basis acceptance, verified class/quantity/segment, reviewer metadata, and follow-up fields. |
| `field_structure_basis_acceptance_workpack_*.csv/.html` | Immediate source-page acceptance workpack for candidates with complete recommendation inputs. |
| `field_structure_blocked_basis_resolution_queue_*.csv/.html` | Blocker queue for fallback or incomplete basis rows that need replacement basis selection, OCR, or BSEE query follow-up. |
| `field_structure_blocked_basis_resolution_pages/` | Focused packet for blocked rows, with rendered page images, OCR text, contact sheet, page scores, and local source links. |
| `field_structure_basis_review_decision_log_*.csv/.html` | Unified reviewer-fillable basis decision log across ready and blocked routes. |
| `field_structure_reviewer_fill_packet_*.csv/.html` | Focused human-fill packet for the minimum fields required by the promotion gate, with source links and candidate prefill hints. |
| `field_structure_reviewer_ready*_input_template_*.csv/.html` | Spreadsheet-oriented input template for immediately actionable basis-review rows; reviewer fields remain blank. |
| `field_structure_promotion_gate_validation_matrix_*.csv/.html` | One row per candidate per required gate field, used to count missing acceptance and verified-register inputs. |
| `field_structure_reviewer_input_import_contract_*.csv/.html` | Source-to-target mapping for writing validated reviewer input rows back into the basis decision log. |
| `field_structure_reviewer_*_staging_audit_*.csv/.html` | Import-readiness audit that blocks decision-log updates until required fields are present and valid. |
| `reviewer_import/` | Optional CLI output directory from `import-reviewer-inputs`, containing the import staging audit, updated basis decision log, regenerated promotion gate, regenerated verified register, `import_run_manifest.json`, and `index.html`. |
| `field_structure_promotion_gate_audit_*.csv/.html` | Fail-closed audit showing whether each basis-decision row is eligible for verified-register promotion and which required reviewer fields are missing. |
| `field_structure_verified_register_*.csv/.html` | Stable verified-asset register emitted only from rows that pass the promotion gate; an empty register means no candidate has been accepted yet. |

## BSEE Scanned Document URL Convention

The package generates candidate direct PDF URLs from the official BSEE
scanned-document path pattern:

| Document family | Query page | PDF directory |
|---|---|---|
| `pipeline_map` | `https://www.data.bsee.gov/Other/FileRequestSystem/ScanPipelineMaps.aspx` | `https://www.data.bsee.gov/PDFDocs/Scan/PIPEMAPS/<doc_id // 1000>/<doc_id>.pdf` |
| `row` | `https://www.data.bsee.gov/Other/FileRequestSystem/ScanROW.aspx` | `https://www.data.bsee.gov/PDFDocs/Scan/ROW/<doc_id // 1000>/<doc_id>.pdf` |
| `plan` | `https://www.data.bsee.gov/Other/FileRequestSystem/ScanPlans.aspx` | `https://www.data.bsee.gov/PDFDocs/Scan/PLANS/<doc_id // 1000>/<doc_id>.pdf` |

## Product Rules

- Use `index.html` for screening, handoff, and product review.
- Use `document_queue.csv` as the next-work list for source document retrieval.
- Use `download_manifest.csv` as the audit trail before promoting retrieved
  source PDFs into engineering review.
- Use `source_document_index.csv` for text-searchable source-document triage.
  `extracted_no_text` rows are valid PDFs but need OCR or manual visual review.
- Use OCR indexes as assistive triage only. OCR on engineering drawings is
  noisy and must be checked against the source PDF before design use.
- Use `field_document_evidence_*.csv` as the first table for product and
  engineering joins when it exists; keep parser and OCR rows as separate
  evidence sources and exclude pilot OCR rows to avoid duplicate evidence.
- Use `field_engineering_join_input_*.csv` when products need traceable
  field-level joins from document evidence to segment, lease, ROW,
  appurtenance, and structure context.
- Use `field_structure_candidates_*.csv` for ranked engineering screening.
  Treat `document_text_plus_appurtenance` as stronger than
  `document_text_plus_segment`, and treat `document_text_nonsegment` as field
  context that still needs a segment-level or drawing-level confirmation.
- Use `field_structure_review_queue_*.csv` as the first manual review queue
  when a user needs to open source PDFs and confirm subsea architecture details.
- Use `field_structure_review_packet_*.html` for product review and manual
  engineering work sessions; verify that every linked local PDF exists before
  sharing the packet.
- Use `field_structure_review_workbook_*.csv` and
  `field_structure_review_evidence_*.csv` for real engineering review handoff:
  the workbook captures reviewer decisions, while the evidence table preserves
  document-level traceability and snippets.
- Use geometry outputs for spatial screening only. They are generated from BSEE
  pipeline-location/appurtenance rows and must be checked against source maps,
  ROW files, or plans before design use.
- Use source contact sheets to triage visual evidence quickly, not to replace
  opening the source PDF for final engineering confirmation.
- Use targeted page packets after the broad contact sheet; they reduce review
  effort by opening the pages most likely to contain candidate-specific
  structure evidence.
- Use draft asset-register files only after review packets and targeted pages
  exist. They are product-facing engineering worklists, not final asset
  inventories; keep rows in `pending_engineering_review` until the source
  PDFs/drawings have been checked.
- Use product manifests as the integration contract for downstream tools. The
  manifest points to the current register, evidence, targeted-page, geometry,
  contact-sheet, and workbook artifacts and records whether expected source
  links are present.
- Use SQLite product packages when products need repeatable joins. Prefer
  `v_asset_product_readiness` for one-row-per-candidate status,
  `v_engineering_review_queue` for review sessions, `v_asset_segment_context`
  for segment endpoints/product codes, `v_asset_appurtenance_summary` for
  appurtenance screening, `v_asset_source_documents` for source PDFs, and
  `v_asset_geometry_feature_summary` for spatial feature coverage. Use
  `v_field_join_readiness` when downstream products need a single candidate row
  with join status, recommended basis page, and blank join-review fields. Use
  `v_verified_register_delta_template` when a product needs the current
  candidate-to-verified promotion queue. Use `v_basis_acceptance_workpack` and
  `v_blocked_basis_resolution_queue` to route ready basis reviews separately
  from blocked fallback rows. Use `v_basis_review_decision_log` when the
  product needs one pending basis-decision state table across all top
  candidates. Use `v_latest_reviewer_import_run` and related
  `v_latest_reviewer_import_*` views when a reviewer import run has been
  published with `--sqlite-product`; they are the current import-run state, not
  a replacement for the base manifest-backed product tables.
- Use engineering review batches as the working surface for humans. They are
  generated from SQLite views and should be filled with verified class,
  quantity, basis document/page, reviewer notes, and follow-up fields.
- Use basis page queues before final promotion. They help reviewers choose
  which source document/page is accepted as the basis for a verified structure
  claim.
- Use recommended basis page exports to reduce first-pass review to the
  top-ranked page per candidate. Keep the accepted/rejected decision explicit;
  recommendations are not final basis evidence.
- Use field-join readiness exports as the product handoff surface for
  field-level joins. They are still candidate records; do not treat
  `ready_for_field_join_review` as engineering verification.
- Use verified-register delta templates when reviewers are ready to record
  accepted basis evidence and promotion decisions. Keep `promotion_ready = 0`
  until basis acceptance and verification fields are populated.
- Use basis acceptance workpacks for the immediate source-page acceptance
  queue. Use blocked basis resolution queues for fallback pages, missing
  extraction, OCR reruns, or replacement-basis decisions.
- Use blocked basis resolution page packets to inspect all rendered/OCR pages
  for blocked fallback documents before accepting page 1 or selecting a
  replacement basis page.
- Use basis review decision logs as the single basis-decision work surface.
  They do not accept or promote rows automatically; reviewer fields must be
  populated explicitly.
- Use reviewer-fill packets for human review sessions. Candidate prefill fields
  are aids only; source PDFs or drawings must be checked before copying values
  into acceptance, promotion, verified-register, reviewer, or date fields.
- Use ready-row input templates when reviewers need a compact spreadsheet for
  the immediately actionable rows. Do not treat candidate prefill columns as
  accepted values.
- Use promotion gate validation matrices to count exactly which gate fields are
  still missing before rerunning promotion logic.
- Use reviewer input import contracts before writing filled templates back to
  the decision log. Identity columns are match-only guards; required gate
  fields must be validated.
- Use staging audits to block imports until every required field is present
  and valid. Do not update `basis_review_decision_log` from rows that are not
  import-ready.
- Use `worldenergydata bsee import-reviewer-inputs` to apply filled reviewer
  templates. It writes only rows with `import_ready=1`, requires
  `basis_review_decision_id` to resolve exactly one target row, checks
  match-only identity fields before update, leaves blocked rows untouched, and
  regenerates promotion-gate plus verified-register outputs from the updated
  decision log.
- Use promotion gate audits before exposing any candidate as an accepted field
  structure. Required fields are basis acceptance, promotion intent, verified
  structure class, verified quantity, verified segment or asset ID, basis
  evidence type, reviewer, and review date.
- Use verified register exports as the only accepted-asset surface. If the
  verified register is empty, downstream products should treat that as "no
  reviewed structures yet" rather than backfilling from draft candidates.
- Do not treat document-index rows as final engineering basis without
  retrieving and reviewing the underlying BSEE documents.
- Treat `retrieval_url` as a generated candidate until opened or downloaded.
- Treat `non_pdf_response` and `cached_non_pdf` manifest rows as unresolved
  retrieval failures requiring BSEE query-page follow-up.
- Keep this package downstream of the field infrastructure bundle contract.
