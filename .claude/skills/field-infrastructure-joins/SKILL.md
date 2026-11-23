---
name: field-infrastructure-joins
description: Build field-level offshore infrastructure data bundles from local BSEE tables for engineering products. Use when users ask for field structures, platforms, pipelines, risers, jumpers, umbilicals, FMP/MCP systems, appurtenances, or product-ready field infrastructure joins.
---

# Field Infrastructure Joins

Use this skill to turn BSEE field, platform, pipeline, FMP, MCP,
scanned-document, and decom tables into product-ready engineering data.

## Quick Start

From the `worldenergydata` repo root:

```bash
worldenergydata bsee infrastructure-bundle \
  --field "Stones" \
  --output reports/bsee/field_infrastructure/stones
```

The command defaults to downloaded local data at:

`/mnt/ace/worldenergydata/data/modules/bsee/bin`

Override the data root when needed:

```bash
worldenergydata bsee infrastructure-bundle \
  --field "Julia" \
  --data-root /mnt/ace/worldenergydata/data/modules/bsee/bin \
  --output reports/bsee/field_infrastructure/julia
```

Generate the engineering-facing product package from a bundle:

```bash
worldenergydata bsee field-package \
  --bundle reports/bsee/field_infrastructure/stones \
  --output reports/bsee/field_packages/stones
```

Retrieve source PDFs from a package queue:

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

OCR no-text source PDFs when scanned drawings need searchable text:

```bash
worldenergydata bsee ocr-documents \
  --index reports/bsee/field_packages/stones/source_document_index.csv \
  --package-dir reports/bsee/field_packages/stones \
  --family pipeline_map \
  --max-pages 1
```

Import a filled reviewer-ready template after human source-page review:

```bash
worldenergydata bsee import-reviewer-inputs \
  --ready-input reports/bsee/field_packages/field_structure_reviewer_ready13_input_template_julia_stones_saint_malo.csv \
  --decision-log reports/bsee/field_packages/field_structure_basis_review_decision_log_top15_julia_stones_saint_malo.csv \
  --output reports/bsee/field_packages/reviewer_import \
  --sqlite-product reports/bsee/field_packages/field_structure_product_julia_stones_saint_malo.sqlite
```

## Output Contract

The command writes:

- `field_context.json`
- `structures.csv`
- `pipeline_segments.csv`
- `pipeline_locations.csv`
- `appurtenances.csv`
- `documents.csv`
- `engineering_summary.json`

The package command writes:

- `index.html`
- `document_queue.csv` with `retrieval_url`, `retrieval_status`, and
  `query_url` columns for BSEE scanned-document review.
- `download_manifest.csv` and `source_documents/` when
  `retrieve-documents` is run against the queue.
- `source_document_index.csv` when `index-documents` is run against the
  retrieval manifest.
- `source_document_ocr_index*.csv` when `ocr-documents` is run against
  no-text indexed PDFs.
- Derived `field_document_evidence_*.csv` tables when parser and OCR term-hit
  rows are consolidated for downstream engineering joins.
- Derived `field_engineering_join_input_*.csv` and
  `field_structure_candidates_*.csv` tables when document evidence is joined
  back to segment, lease, ROW, appurtenance, and structure context.
- Derived `field_structure_review_queue_*.csv` tables when candidates are
  ranked for manual source-PDF/drawing review.
- Derived `field_structure_review_packet_*.html` reports when the top review
  queue needs local PDF links and product-facing summaries.
- Derived `field_structure_review_workbook_*.csv` and
  `field_structure_review_evidence_*.csv` files when engineering reviewers need
  decision columns plus per-document evidence snippets.
- Derived `field_structure_review_*_geometry*.geojson/.csv/.html` files when
  the review queue needs spatial screening from pipeline route and appurtenance
  coordinates.
- Derived `field_structure_top*_source_contact_sheet/` packets when reviewers
  need fast visual triage of the source PDFs behind the highest-priority
  candidates.
- Derived `field_structure_top*_targeted_pages/` packets when reviewers need
  pages scored by candidate segment IDs and structure terms rather than page-1
  thumbnails only.
- Derived `field_structure_asset_register_top*_draft_*.csv/.html` files when
  top candidates need to be exposed as draft register rows with source-page,
  geometry, and reviewer-decision traceability.
- Derived `field_structure_product_manifest_*.json/.html` files when product
  teams need a stable file catalog, join-key contract, validation status, and
  promotion gate for a field-structure package.
- Derived `field_structure_product_*.sqlite` packages when downstream tools
  need queryable views across the register, evidence, targeted pages, geometry,
  segments, appurtenances, and source documents.
- Derived `field_structure_engineering_review_batch_*.csv/.html` files when a
  reviewer needs a one-row-per-candidate work surface generated from SQLite
  product views.
- Derived `field_structure_basis_page_queue_*.csv/.html` files when reviewers
  need candidate-specific page evidence, thumbnails, excerpts, and blank basis
  decision fields before promoting register rows.
- Derived `field_structure_recommended_basis_page_*.csv/.html` files when
  reviewers need the top-ranked page per candidate as an acceptance/rejection
  starting point, without treating the recommendation as verified evidence.
- Derived `field_structure_field_join_readiness_*.csv/.html` files when
  product teams need one row per candidate with field/segment join key,
  segment context, appurtenance context, geometry coverage, source-document
  coverage, recommended basis page, and blank field-join review fields.
- Derived `field_structure_verified_register_delta_template_*.csv/.html` files
  when reviewers need a promotion queue with explicit basis acceptance,
  verified class/quantity/segment fields, reviewer metadata, and follow-up
  columns before creating a verified register.
- Derived `field_structure_basis_acceptance_workpack_*.csv/.html` files when
  complete recommendation-input rows need to be isolated for immediate
  source-page acceptance review.
- Derived `field_structure_blocked_basis_resolution_queue_*.csv/.html` files
  when fallback or incomplete basis rows need to be worked separately before
  promotion.
- Derived `field_structure_blocked_basis_resolution_pages/` packets when
  blocked fallback PDFs need rendered page images, OCR text, contact sheets,
  and page rankings for manual resolution.
- Derived `field_structure_basis_review_decision_log_*.csv/.html` files when
  product or engineering users need one reviewer-fillable basis decision log
  across ready and blocked routes.
- Derived `field_structure_reviewer_fill_packet_*.csv/.html` files when
  engineering users need a focused human-fill surface for the minimum fields
  required by the promotion gate.
- Derived `field_structure_reviewer_ready*_input_template_*.csv/.html` files
  when ready basis-review rows need a spreadsheet-oriented fill template with
  candidate prefill hints and blank reviewer fields.
- Derived `field_structure_promotion_gate_validation_matrix_*.csv/.html`
  files when products need one row per candidate per required gate field for
  missing-field audits.
- Derived `field_structure_reviewer_input_import_contract_*.csv/.html` files
  when filled reviewer templates need a source-to-target mapping into the
  basis decision log.
- Derived `field_structure_reviewer_*_staging_audit_*.csv/.html` files when
  filled reviewer templates need import-readiness checks before updating the
  decision log.
- `reviewer_ready_input_staging_audit.csv`,
  `basis_review_decision_log_updated.csv`, `promotion_gate_audit.csv`, and
  `verified_field_structure_register.csv`, plus `import_run_manifest.json` and
  `index.html`, under the chosen import output directory when
  `import-reviewer-inputs` validates a filled reviewer template.
- `latest_reviewer_import_*` tables and matching `v_latest_reviewer_import_*`
  views in the SQLite product when `import-reviewer-inputs` is run with
  `--sqlite-product`.
- Derived `field_structure_promotion_gate_audit_*.csv/.html` files when
  products need fail-closed eligibility checks from pending basis decisions to
  verified-register promotion.
- Derived `field_structure_verified_register_*.csv/.html` files when
  downstream tools need a stable verified-asset surface that stays empty until
  human review passes the promotion gate.

For column meanings and product usage, read
[`references/product-contract.md`](references/product-contract.md).

## Join Order

1. Resolve field leases and area/block anchors from
   `deepqual/mv_deep_water_field_leases.bin`.
2. Join direct structures from `platstruc`, `permstruc`, FMP, and MCP.
3. Join pipeline-map docs and decom pipeline rows by lease or area/block.
4. Use collected segment IDs to pull route/appurtenance rows from `pipeloc`.
5. Join scanned ROW docs by segment and scanned plan docs by lease.
6. Preserve `source_table`, `join_key`, and `evidence_confidence` in outputs.

## Engineering Use

Use this bundle for screening and early engineering workflows:

- tieback and host-infrastructure discovery
- riser/appurtenance inventory from `PPL_APURT_TYPE`
- flowline and umbilical proxy discovery from decom endpoints/product codes
- FMP/MCP production measurement context
- decommissioning scope discovery
- document retrieval queues for maps, plans, and ROW files
- source-document term triage for flowline, jumper, riser, umbilical,
  manifold, PLET/FLET, platform, host, well, and subsea references
- OCR triage for image-only pipeline maps and scanned drawings
- field-level evidence filtering with boolean term flags such as `has_jumper`,
  `has_umbilical`, `has_riser`, `has_plet`, and `has_flowline`
- segment-level candidate screening with confidence tiers such as
  `document_text_plus_appurtenance`, `document_text_plus_segment`, and
  `document_text_nonsegment`
- prioritized source-PDF review queues for subsea architecture confirmation
- browser review packets for opening BSEE source PDFs and confirming candidate
  structures
- reviewer workbooks with explicit status, verified class, quantity, notes, and
  follow-up fields
- spatial screening layers for route/appurtenance context before source drawing
  confirmation
- source-PDF contact sheets for visual pre-review before filling the verified
  asset register
- targeted page-hit contact sheets to prioritize the source pages most likely
  to contain candidate structure evidence
- draft asset-register rows for product and engineering sessions, with
  proposed structure class, join keys, source links, targeted pages, geometry
  references, and blank verification fields
- product manifests that let downstream tools ingest the register, evidence,
  targeted pages, and geometry outputs without rediscovering file paths or
  join keys
- SQLite product views such as `v_asset_product_readiness`,
  `v_engineering_review_queue`, `v_asset_segment_context`,
  `v_asset_appurtenance_summary`, `v_asset_source_documents`, and
  `v_asset_geometry_feature_summary`
- SQLite-backed review batches that aggregate source documents, targeted
  pages, segment context, appurtenance summaries, geometry coverage, review
  focus, risk notes, and blank decision fields
- basis page queues that turn targeted page hits into source-page acceptance
  worklists for verified document/page decisions
- recommended basis page views and exports that reduce the first-pass review
  set to one page per candidate while preserving the human acceptance gate
- field-join readiness exports and `v_field_join_readiness` for products that
  need a one-row-per-candidate integration surface before verified-register
  promotion
- verified-register delta templates and `v_verified_register_delta_template`
  for reviewer-fillable promotion queues that keep blocked basis rows separate
  from rows ready for engineering verification
- basis acceptance workpacks and blocker queues that split immediately
  actionable source-page acceptance from rows needing OCR, query-page, or
  replacement-basis follow-up
- blocked basis resolution page packets that render and OCR all candidate pages
  for fallback documents before choosing replacement or accepted basis pages
- basis review decision logs that unify ready basis-acceptance rows and
  blocked-resolution rows into a single pending decision surface
- reviewer-fill packets that route pending basis decisions to humans with
  candidate prefill hints while leaving actual acceptance and promotion fields
  blank
- ready-row input templates that isolate immediately actionable basis-review
  rows and keep reviewer fields blank until source evidence is checked
- promotion gate validation matrices that count missing required fields by
  candidate, route, and field name before rerunning the gate
- reviewer input import contracts that map validated fill-template columns
  back to `basis_review_decision_log`
- reviewer staging audits that block decision-log imports until required
  reviewer fields are present and valid
- executable reviewer input imports that update only `import_ready=1` rows and
  regenerate the fail-closed promotion gate plus verified register outputs after
  match-only identity fields agree with the target decision log
- latest reviewer-import SQLite views that let downstream products query the
  current import run, staging audit, updated decision log, promotion gate, and
  verified-register output
- promotion gate audits that explain why candidate rows are blocked or ready
  for verified-register promotion
- verified field-structure registers that expose only accepted, reviewer-signed
  structures and intentionally return zero rows until review is complete

Do not claim jumpers/risers/umbilicals are fully enumerated unless the
evidence is present in `appurtenances.csv`, `pipeline_segments.csv`, or
the scanned document queue/index.
