# Field Structure Inventory: Julia, Stones, and Saint Malo

Verified: 2026-06-23

This exploratory inventory joins local BSEE field, platform, pipeline,
FMP, MCP, scanned-document, and decommissioning tables for three deepwater
fields: Julia, Stones, and Saint Malo.

The inventory is not a new source-of-record. It documents which local
BSEE tables can support field-level offshore infrastructure discovery and
where the joins are strong or weak.

## Local Data Root

All inspected tables are pandas-pickled DataFrames under:

`/mnt/ace/worldenergydata/data/modules/bsee/bin/`

Primary join anchor:

`deepqual/mv_deep_water_field_leases.bin`

## Method

For each field:

1. Resolve `FIELD_NAME_CODE`, field leases, and area/block anchors from
   `deepqual/mv_deep_water_field_leases.bin`.
2. Query platform records by `FIELD_NAME_CODE`, `LEASE_NUMBER`, or
   matching area/block.
3. Query FMP/MCP records by lease, platform complex, or area/block.
4. Query scanned pipeline maps by origin/destination lease or area/block.
5. Query pipeline decom rows by origin/destination lease or area/block.
6. Use pipeline-map and decom segment IDs to retrieve matching point rows
   from `pipeloc/mv_pipelinelocation.bin`.
7. Query scanned ROW and plan indexes by segment or lease.

This method intentionally treats field infrastructure as a discovery
problem. BSEE pipeline-location rows carry `SEGMENT_NUM`, but not field
name or lease. Field linkage must come from maps, decom rows, plans, or
ROW records that include segment IDs plus leases or blocks.

## Summary

| Field | Field code | Leases | Platform rows | Subsea boreholes | FMP locations | MCP systems | Scanned pipeline docs | Pipeline decom rows | Pipeline segments | Pipeline location rows | Scanned ROW docs | Scanned plan docs | Platform decom rows |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Julia | `WR627` | `G20351`, `G20361`, `G25251` | 0 | 0 | 0 | 0 | 24 | 17 | 24 | 6,578 | 10 | 8 | 0 |
| Stones | `WR508` | `G17001`, `G32690` | 1 | 7 | 4 | 3 | 8 | 24 | 26 | 539 | 0 | 43 | 1 |
| Saint Malo | `WR678` | `G18745`, `G18753`, `G21245` | 0 | 14 | 0 | 0 | 35 | 49 | 50 | 4,661 | 17 | 43 | 0 |

## Key Observations

- Stones has a direct platform/structure row for `A (Turritella)`, an
  FPSO in `WR 551`, with `COMPLEX_ID_NUM=2503`.
- Julia has no direct platform row in `platstruc`, but has strong
  pipeline-map, pipeline decom, pipeline-location, ROW, and plan coverage.
- Saint Malo has no direct platform row in `platstruc`, but has strong
  subsea borehole, pipeline-map, pipeline decom, pipeline-location, ROW,
  and plan coverage.
- Field-level pipeline discovery should combine scanned pipeline maps and
  decom pipeline rows. Either one alone misses segments.
- `pipeloc/mv_pipelinelocation.bin` exposes `PPL_APURT_TYPE`; matched
  field segments include `RISER` values for Julia, Stones, and Saint Malo.
- Pipeline decom rows expose subsea endpoint and product-code clues:
  `UMB`, `UMBE`, `UMBH`, `UBEH`, `PLET`, `PLEM`, `manifold`, `FLET`,
  `HIPPS`, `UTA`, and `MFLD` appear in matched or broader rows.
- No dedicated first-class BSEE table named for jumpers, risers, or
  umbilicals was found. Use pipeline appurtenances, decom endpoint names,
  scanned maps, scanned plans, and ROW files as the practical discovery
  path.
- Retrieved source-document packages now exist for all three fields under
  `reports/bsee/field_packages/<field>/`. These include
  `download_manifest.csv`, `source_documents/`, and
  `source_document_index.csv`.

## Retrieved Source Document Packages

| Field | Queue rows | Retrieved PDF rows | Non-PDF rows | Searchable rows | No-text PDF rows | OCR rows | Indexed term highlights |
|---|---:|---:|---:|---:|---:|---:|---|
| Julia | 42 | 42 | 0 | 15 | 27 | 24 | ROW docs include `flet`, `pipeline`, `plet`, `riser`, `subsea`, and `umbilical`; plan docs include `plet`, `subsea`, and `well`. Pipeline-map OCR adds `flowline`, `umbilical`, and `jumper`. |
| Stones | 51 | 50 | 1 | 35 | 15 | 8 | Plan docs include `flowline`, `jumper`, `manifold`, `pipeline`, `subsea`, `umbilical`, `well`, `fpso`, `host`, and `plet`. Pipeline-map OCR adds `flowline`, `jumper`, `manifold`, `umbilical`, `fpso`, and `plet`. |
| Saint Malo | 95 | 95 | 0 | 88 | 7 | 1 | Pipeline-map, ROW, and plan docs include `flowline`, `jumper`, `manifold`, `pipeline`, `platform`, `plet`, `riser`, `subsea`, `umbilical`, and `well`. One no-text pipeline-map OCR row produced survey text but no configured engineering term hits. |

Interpretation:

- `download_manifest.csv` is the retrieval audit trail.
- `source_document_index.csv` is the text-searchable triage layer.
- `extracted_no_text` rows are valid PDFs with no parser text in the
  selected pages; they need OCR or manual visual review and are not negative
  evidence for structures.
- The Stones non-PDF row is plan `DOC_ID=32772`, where the generated direct
  BSEE URL returned a Data Center 404 HTML page.

## Derived Engineering Evidence Table

The tri-field engineering evidence table is:

- `reports/bsee/field_packages/field_document_evidence_julia_stones_saint_malo.csv`

This table merges text-parser term hits from `source_document_index.csv` with
final OCR term hits from `source_document_ocr_index*.csv`, excluding pilot OCR
files. It is intended as the first downstream product table for engineering
joins because every row carries `field`, `document_family`, `document_id`,
source PDF path, retrieval URL, matched terms, engineering tags, excerpt, and
boolean term flags such as `has_jumper`, `has_umbilical`, `has_riser`,
`has_plet`, and `has_flowline`.

| Field | Evidence rows | Parser text rows | OCR text rows |
|---|---:|---:|---:|
| Julia | 39 | 15 | 24 |
| Stones | 43 | 35 | 8 |
| Saint Malo | 87 | 87 | 0 |
| Total | 169 | 137 | 32 |

## Field-Level Engineering Join Products

The tri-field join products are:

- `reports/bsee/field_packages/field_engineering_join_input_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_candidates_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_review_queue_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_review_top60_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_review_packet_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_review_workbook_top60_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_review_evidence_top60_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_review_workbook_top60_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_review_top60_geometry_julia_stones_saint_malo.geojson`
- `reports/bsee/field_packages/field_structure_review_top60_geometry_summary_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_review_top60_geometry_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_top15_source_contact_sheet/index.html`
- `reports/bsee/field_packages/field_structure_top15_source_contact_sheet/contact_sheet_top15.png`
- `reports/bsee/field_packages/field_structure_top15_source_contact_sheet/source_manifest_top15.csv`
- `reports/bsee/field_packages/field_structure_top15_targeted_pages/index.html`
- `reports/bsee/field_packages/field_structure_top15_targeted_pages/targeted_pages_contact_sheet_top15.png`
- `reports/bsee/field_packages/field_structure_top15_targeted_pages/targeted_page_hits_top15.csv`
- `reports/bsee/field_packages/field_structure_asset_register_top15_draft_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_asset_register_top15_draft_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_product_manifest_julia_stones_saint_malo.json`
- `reports/bsee/field_packages/field_structure_product_manifest_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_product_julia_stones_saint_malo.sqlite`
- `reports/bsee/field_packages/field_structure_product_sqlite_readme_julia_stones_saint_malo.md`
- `reports/bsee/field_packages/field_structure_engineering_review_batch_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_engineering_review_batch_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_basis_page_queue_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_basis_page_queue_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_recommended_basis_page_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_recommended_basis_page_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_field_join_readiness_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_field_join_readiness_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_verified_register_delta_template_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_verified_register_delta_template_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_basis_acceptance_workpack_ready13_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_basis_acceptance_workpack_ready13_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_blocked_basis_resolution_queue_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_blocked_basis_resolution_queue_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_blocked_basis_resolution_pages/index.html`
- `reports/bsee/field_packages/field_structure_blocked_basis_resolution_pages/blocked_basis_resolution_pages.csv`
- `reports/bsee/field_packages/field_structure_blocked_basis_resolution_pages/blocked_basis_resolution_pages_contact_sheet.png`
- `reports/bsee/field_packages/field_structure_basis_review_decision_log_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_basis_review_decision_log_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_reviewer_fill_packet_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_reviewer_fill_packet_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_reviewer_ready13_input_template_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_reviewer_ready13_input_template_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_promotion_gate_validation_matrix_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_promotion_gate_validation_matrix_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_reviewer_input_import_contract_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_reviewer_input_import_contract_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_reviewer_ready13_staging_audit_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_reviewer_ready13_staging_audit_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_promotion_gate_audit_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_promotion_gate_audit_top15_julia_stones_saint_malo.html`
- `reports/bsee/field_packages/field_structure_verified_register_top15_julia_stones_saint_malo.csv`
- `reports/bsee/field_packages/field_structure_verified_register_top15_julia_stones_saint_malo.html`

`field_engineering_join_input_julia_stones_saint_malo.csv` enriches each
document-evidence row with `document_queue.csv` keys, segment endpoints,
pipeline product codes, pipeline-location counts, appurtenance counts/types,
and field-level structure context from `reports/bsee/field_infrastructure/`.
This is the row-level traceability table to use before opening PDFs.

`field_structure_candidates_julia_stones_saint_malo.csv` aggregates the same
evidence into candidate classes for engineering screening. Candidate rows are
triage only; the source PDF or drawing remains the engineering basis.

`field_structure_review_queue_julia_stones_saint_malo.csv` is the same
candidate set sorted for manual engineering review. It puts
`document_text_plus_appurtenance` segment candidates first, then
`document_text_plus_segment`, then non-segment field context. The first rows
are appurtenance-backed riser and umbilical candidates.

`field_structure_review_packet_julia_stones_saint_malo.html` is a browser
review packet for the first 60 ranked rows. It links to local source PDFs and
BSEE URLs and includes field, candidate-class, and confidence summaries.
`field_structure_review_top60_julia_stones_saint_malo.csv` is the matching CSV
slice for spreadsheet review.

`field_structure_review_workbook_top60_julia_stones_saint_malo.csv` adds
reviewer-fillable decision columns for the first 60 ranked candidates.
`field_structure_review_evidence_top60_julia_stones_saint_malo.csv` expands
those candidates into supporting document-evidence rows with excerpts, local
PDF paths, and BSEE URLs. The matching HTML workbook shows the same review rows
with evidence snippets for fast source review.

`field_structure_review_top60_geometry_julia_stones_saint_malo.geojson`
exports route and appurtenance geometry for the top 60 review candidates. It is
a spatial screening layer built from `pipeline_locations.csv` and
`appurtenances.csv`, not a drawing substitute. The matching HTML gives an
offline SVG map and summary counts.

`field_structure_top15_source_contact_sheet/index.html` is the first manual
source-review packet. It renders page-1 thumbnails for the unique source PDFs
supporting the top 15 review candidates, links to the local PDFs and BSEE URLs,
and provides a single PNG contact sheet plus source manifest for fast visual
triage.

`field_structure_top15_targeted_pages/index.html` is the targeted source-page
review packet. It scores source PDF pages by candidate segment IDs and structure
terms, renders the best matching pages, and falls back to page 1 when no
searchable hit is available.

`field_structure_asset_register_top15_draft_julia_stones_saint_malo.csv` is
the first draft asset-register layer. It converts the top 15 review candidates
into `pending_engineering_review` register rows with proposed structure class,
segment/lease joins, product-code and appurtenance context, source PDF paths,
targeted page numbers, geometry product links, and blank reviewer decision
fields. The matching HTML file is a product-facing review surface that links to
the targeted page packet, source PDFs, BSEE URLs, geometry screening map, and
reviewer workbook. It is not a final asset inventory.

`field_structure_product_manifest_julia_stones_saint_malo.json` is the
product-ingestion manifest for the field-structure stack. It declares the
primary entity, cross-product join keys, file catalog, row counts, SHA-256
hashes, validation checks, register column contract, usage rules, known limits,
and promotion gate from draft candidate to verified asset. The matching HTML is
a human-readable companion for product and engineering review.

`field_structure_product_julia_stones_saint_malo.sqlite` is the queryable
product package. It loads the top-15 draft register, review evidence, targeted
pages, basis page queue, geometry summary, GeoJSON features, combined field
pipeline segments, combined field appurtenances, source-document rows, and
metadata. Product views include `v_asset_product_readiness`,
`v_engineering_review_queue`, `v_basis_page_queue`,
`v_recommended_basis_page`, `v_field_join_readiness`,
`v_verified_register_delta_template`, `v_basis_acceptance_workpack`,
`v_blocked_basis_resolution_queue`, `v_reviewer_fill_packet`,
`v_reviewer_ready13_input_template`,
`v_promotion_gate_validation_matrix`, `v_reviewer_input_import_contract`,
`v_reviewer_ready13_staging_audit`, `v_promotion_gate_audit`,
`v_verified_field_structure_register`, `v_asset_segment_context`,
`v_asset_appurtenance_summary`, `v_asset_source_documents`, and
`v_asset_geometry_feature_summary`.
After publishing the optional latest reviewer import run, the same SQLite file
also exposes `latest_reviewer_import_run`,
`latest_reviewer_import_staging_audit`, `latest_reviewer_import_decision_log`,
`latest_reviewer_import_promotion_gate`,
`latest_reviewer_import_verified_register`, and matching `v_latest_*` views.
`field_structure_product_sqlite_readme_julia_stones_saint_malo.md` documents
the tables, views, example queries, and promotion gate.

`field_structure_engineering_review_batch_top15_julia_stones_saint_malo.csv`
is the SQLite-backed one-row-per-candidate review surface. It uses
`v_asset_product_readiness` as the spine and aggregates source documents,
targeted pages, segment context, appurtenance summaries, and geometry feature
coverage into 15 draft review rows with blank engineering decision fields. The
matching HTML file is the reviewer-facing batch report.

`field_structure_basis_page_queue_top15_julia_stones_saint_malo.csv` is the
page-level basis selection queue. It explodes the SQLite
`targeted_page_review_sequence` table into 61 candidate-page rows with source
PDF links, BSEE URLs, thumbnail paths, excerpts, matched terms, extraction
status, and blank basis-decision fields. The matching HTML groups the pages by
candidate and renders the targeted thumbnails for source review.

`field_structure_recommended_basis_page_top15_julia_stones_saint_malo.csv` is
the first-pass top-page recommendation layer. It exports the SQLite
`v_recommended_basis_page` view into 15 rows, one per draft candidate. These
rows are recommendations only: they remain `recommended_pending_basis_review`
until a reviewer accepts or rejects the page after opening the source
PDF/drawing. The matching HTML renders the recommended thumbnail, excerpt, PDF
link, and BSEE URL for each candidate.

`field_structure_field_join_readiness_top15_julia_stones_saint_malo.csv` is
the product handoff surface for field-level joins. It exports one row per
top-15 draft candidate with the field/segment join key, segment context,
appurtenance context, geometry counts, source-document coverage, recommended
basis page, and blank field-join review fields. The matching HTML renders the
recommended basis thumbnail beside the join status. Thirteen rows are
`ready_for_field_join_review`; the two Stones umbilical fallback rows are
`needs_basis_input_review` until an engineer confirms the source PDF page.

`field_structure_verified_register_delta_template_top15_julia_stones_saint_malo.csv`
is the reviewer-fillable promotion queue. It starts from the field-join
readiness rows and adds explicit promotion fields such as
`promote_to_verified_register`, `basis_page_accepted`,
`verified_structure_class`, `verified_quantity`,
`verified_segment_or_asset_id`, `verified_asset_name`, reviewer, review date,
notes, and follow-up fields. Thirteen rows are
`pending_engineering_verification`; the two Stones fallback rows remain
`blocked_pending_basis_input_review`. The matching HTML is the product-facing
review surface for this delta queue.

`field_structure_basis_acceptance_workpack_ready13_julia_stones_saint_malo.csv`
is the immediate engineering workpack. It isolates the 13 verified-delta rows
with complete recommendation inputs and adds basis acceptance fields, observed
structure fields, verified asset fields, source PDF links, thumbnails, and
review instructions. The matching HTML renders those pages for source-page
acceptance review.

`field_structure_blocked_basis_resolution_queue_julia_stones_saint_malo.csv`
isolates the two blocked Stones umbilical fallback rows. It preserves the
fallback document/page, source PDF, thumbnail, blocking reason, and fields for
replacement basis document/page or OCR/BSEE follow-up decisions. The matching
HTML keeps these blockers separate from the actionable basis-acceptance
workpack.

`field_structure_blocked_basis_resolution_pages/index.html` is the focused
evidence packet for those two Stones blockers. It renders and OCRs both pages
of pipeline-map docs `19593` and `19592`, ranks the pages for review, links the
local PDFs and OCR text, and provides a contact sheet. For both blocked rows,
page 1 is the top review page; page 2 has no configured term hits.

`field_structure_basis_review_decision_log_top15_julia_stones_saint_malo.csv`
is the unified reviewer-fillable decision log for all 15 candidates. It merges
the 13 ready basis-acceptance rows with the two Stones blocked-resolution
page-1 rows, preserves source PDF and packet links, and leaves acceptance,
observed-structure, verified-register, reviewer, and follow-up fields blank.
The matching HTML is the single basis-decision surface for product and
engineering review.

`field_structure_reviewer_fill_packet_top15_julia_stones_saint_malo.csv` is
the focused human work surface for filling the minimum fields needed by the
promotion gate. It has 15 rows: 13 routed to basis-page acceptance review and 2
routed to blocked-basis resolution review. Candidate prefill columns preserve
the proposed structure class, segment or asset ID, and basis evidence type, but
the actual acceptance, promotion, verified-register, reviewer, and date fields
remain blank until a reviewer verifies the source PDF or drawing. The matching
HTML summarizes the missing fields and links back to source PDFs and
thumbnails.

`field_structure_reviewer_ready13_input_template_julia_stones_saint_malo.csv`
is the immediate fill template for the 13 candidates with complete basis-page
recommendation inputs. It keeps reviewer fields blank but adds candidate
prefill columns for basis acceptance, promotion intent, evidence type, verified
structure class, quantity, and segment or asset ID. Reviewers must open the
linked source PDF or drawing before copying candidate prefill values into the
actual gate fields.

`field_structure_promotion_gate_validation_matrix_top15_julia_stones_saint_malo.csv`
explodes the 15 reviewer-fill rows into one validation row per required
promotion field. The current matrix has 120 rows: 15 candidates times 8
required fields. All 120 checks are missing because no reviewer acceptance or
review metadata has been populated yet. Use this table to count remaining gate
work by candidate, route, and required field name.

`field_structure_reviewer_input_import_contract_julia_stones_saint_malo.csv`
defines the column mapping for writing validated reviewer inputs back into
`basis_review_decision_log`. It has 21 rows covering identity cross-check keys,
8 required promotion-gate fields, and optional observed, verified, design-basis,
notes, and follow-up fields. It is a contract only; it does not update the
decision log or promote rows.

`field_structure_reviewer_ready13_staging_audit_julia_stones_saint_malo.csv`
checks the ready-13 input template against the import contract. It currently
has 13 rows and 0 import-ready rows because all required reviewer fields are
still blank. Use this table before any decision-log import; only rows with
`import_ready=1` should be written back.

The executable import path is `worldenergydata bsee import-reviewer-inputs`.
Given a filled ready-13 template and the current
`field_structure_basis_review_decision_log_top15_julia_stones_saint_malo.csv`,
it writes `reviewer_ready_input_staging_audit.csv`,
`basis_review_decision_log_updated.csv`, `promotion_gate_audit.csv`, and
`verified_field_structure_register.csv` under the chosen output directory. It
also writes `import_run_manifest.json` and `index.html` so product consumers can
inspect counts, hashes, input paths, and output files without opening each CSV.
The importer is fail-closed: only rows passing required-field validation are
written back, `basis_review_decision_id` must resolve exactly one target row,
match-only identity fields such as `asset_register_id` and `review_sequence`
must agree with the target decision log, blocked rows remain unchanged, and the
verified register is regenerated from the updated decision log.

A current run against the blank ready-13 template wrote the optional
`reports/bsee/field_packages/reviewer_import/` output directory. That run
produced 13 staging rows, all blocked; 15 promotion-gate rows, all blocked; and
0 verified-register rows. The run manifest records the same counts plus row
counts, column counts, and SHA-256 hashes for each CSV output. These optional
CLI outputs are not included in the 49-file product manifest.

The same run was also published into
`field_structure_product_julia_stones_saint_malo.sqlite` with
`--sqlite-product`. Current SQLite integrity check is `ok`; the file now has
32 tables and 26 views, including the five `latest_reviewer_import_*` tables
and matching views. `v_latest_reviewer_import_run` reports `import_ready=0`,
`import_blocked=13`, and `verified_rows=0`.

`field_structure_promotion_gate_audit_top15_julia_stones_saint_malo.csv` is
the fail-closed promotion audit derived from the basis review decision log. It
checks each candidate for explicit basis acceptance, promotion intent, verified
class, verified quantity, verified segment or asset ID, basis evidence type,
reviewer, and review date. All 15 current rows are
`blocked_pending_review_fields`, so no candidate can be consumed as a verified
field structure yet. The matching HTML summarizes the missing fields and links
back to source PDFs, thumbnails, and evidence packets.

`field_structure_verified_register_top15_julia_stones_saint_malo.csv` is the
schema-stable verified register surface. It currently has 0 data rows by
design because no basis-review decision has passed the promotion gate. Downstream
products should join to this file or `v_verified_field_structure_register` when
they need verified assets, and treat an empty result as "no reviewed structures
yet" rather than as a product failure.

| Product | Rows | Key split |
|---|---:|---|
| Join input | 169 | 91 segment-level rows; 78 lease-level rows |
| Structure candidates | 177 | 61 `document_text_plus_appurtenance`; 84 `document_text_plus_segment`; 32 `document_text_nonsegment` |
| Structure review queue | 177 | Ranked candidate rows with `review_priority` and `recommended_review_action` |
| Structure review packet | 60 | Top ranked rows with local PDF links; 249 source PDF references checked present |
| Structure review workbook | 60 | Top ranked rows with blank engineering decision columns |
| Structure review evidence | 96 | Supporting evidence rows for the top 60 candidates; all candidates have evidence |
| Structure review geometry | 912 GeoJSON features | 60 route features and 852 appurtenance point features; every top-60 candidate has geometry |
| Top-15 source contact sheet | 25 source PDFs | 15 candidates; 25 unique source PDFs; all thumbnails rendered |
| Top-15 targeted pages | 45 selected pages | 41 pages with segment/term hits; 4 page-1 fallbacks; all thumbnails rendered |
| Top-15 draft asset register | 15 draft rows | 7 riser and 8 umbilical candidates; all pending engineering review with source, targeted-page, and geometry links |
| Product manifest | 49 cataloged files | JSON and HTML manifest with file hashes, validation checks, join keys, column contract, reviewer-fill packet, ready-13 template, validation matrix, import contract, staging audit, promotion gate audit, and verified-register surface |
| SQLite product | 32 tables, 26 views | Base manifest-backed product plus optional latest reviewer import tables/views; `v_latest_reviewer_import_run` currently reports 0 ready, 13 blocked, 0 verified |
| Engineering review batch | 15 draft rows | SQLite-backed one-row-per-candidate review surface with source, targeted-page, segment, appurtenance, geometry, and blank decision fields |
| Basis page queue | 61 candidate-page rows | Candidate-specific source pages with thumbnails, excerpts, source links, and blank basis-decision fields |
| Recommended basis pages | 15 candidate rows | Top-ranked page per candidate; 13 complete recommendation inputs and 2 Stones page-1 fallback recommendations needing extra review |
| Field-join readiness | 15 candidate rows | Product integration surface; 13 ready for field-join review and 2 Stones rows needing basis-input review |
| Verified-register delta template | 15 candidate rows | Promotion queue with 13 pending engineering verification rows and 2 blocked Stones fallback rows |
| Basis acceptance workpack | 13 candidate rows | Immediate source-page acceptance review queue with complete recommendation inputs |
| Blocked basis resolution queue | 2 candidate rows | Stones fallback rows requiring manual basis-page resolution before promotion |
| Blocked basis resolution pages | 4 page rows | Both pages for Stones docs `19593` and `19592`; page 1 ranks first for both blockers |
| Basis review decision log | 15 candidate rows | Single reviewer-fillable basis-decision log; 13 ready-route rows and 2 blocked-resolution-route rows |
| Reviewer fill packet | 15 candidate rows | Human fill surface with 13 basis-acceptance rows and 2 blocked-resolution rows; no automatic promotion |
| Ready-13 reviewer input template | 13 candidate rows | Immediate fill template for complete basis-page recommendation rows; reviewer fields blank |
| Promotion gate validation matrix | 120 validation rows | 15 candidates times 8 required gate fields; all current checks missing |
| Reviewer input import contract | 21 mapping rows | Decision-log import mapping with required fields, validation rules, and update behavior |
| Ready-13 staging audit | 13 candidate rows | Import-readiness audit; 0 rows import-ready while reviewer fields are blank |
| Reviewer input importer | CLI/module | Applies filled reviewer templates only for `import_ready=1` rows and regenerates gate/register outputs |
| Reviewer import CLI run | 6 optional files | Current blank-template run wrote 4 CSVs plus JSON/HTML run summaries: 13 blocked staging rows, 15 blocked gate rows, and 0 verified rows outside the manifest |
| Latest reviewer import SQLite views | 5 tables, 5 views | Queryable latest import run, staging audit, updated decision log, promotion gate, and verified-register outputs |
| Promotion gate audit | 15 candidate rows | Fail-closed audit; all 15 rows blocked pending required reviewer fields |
| Verified field structure register | 0 verified rows | Empty by design until a candidate passes the promotion gate |

Candidate class counts:

| Candidate class | Rows |
|---|---:|
| `jumper_candidate` | 54 |
| `plet_candidate` | 38 |
| `manifold_candidate` | 29 |
| `umbilical_candidate` | 17 |
| `flowline_candidate` | 14 |
| `host_candidate` | 12 |
| `riser_candidate` | 9 |
| `flet_candidate` | 4 |

## Julia

- Field code: `WR627`
- Field leases: `G20351`, `G20361`, `G25251`
- Area/block anchors: `WR 540`, `WR 584`, `WR 627`

| Source family | Count | Interpretation |
|---|---:|---|
| Platform structures | 0 | Direct platform/structure records by field code, lease, or area/block. |
| Permanent platforms | 0 | Permanent-platform support table by area/block. |
| Subsea boreholes | 0 | Subsea borehole support table by area/block. |
| FMP lease links | 0 | Lease-to-FMP measurement links. |
| FMP locations | 0 | Measurement locations by lease links or platform complex. |
| MCP lease-unit rows | 0 | Commingling lease-unit rows by lease. |
| MCP area/block rows | 3 | MCP lease/area/block rows by lease. |
| MCP systems | 0 | System records reached through MCP lease-unit rows. |
| Scanned pipeline-map docs | 24 | Pipeline-map document index rows by lease or area/block. |
| Pipeline decom rows | 17 | Installed/proposed pipeline lifecycle rows by lease or area/block. |
| Pipeline segments | 24 | Unique segment IDs from scanned maps and decom rows. |
| Pipeline location rows | 6,578 | Pipeline-location points for those segment IDs. |
| Scanned ROW docs | 10 | ROW document index rows for those segment IDs. |
| Scanned plan docs | 8 | Plan document index rows by lease. |
| Platform decom rows | 0 | Installed/proposed platform decom rows by area/block or complex. |

Pipeline decom product-code counts:

`{'BLKO': 15, 'UBEH': 2}`

Matched pipeline-location coverage:

- Located segments: 17
- Appurtenance types: `BEND`, `CROSSING`, `FLANGE`, `LEGACY`, `RISER`
- Latitude range: `26.231480` to `26.384607`
- Longitude range: `-91.368890` to `-91.261175`

Representative pipeline decom rows:

| Status | Segment | Origin | Destination | Product code | Size code |
|---|---:|---|---|---|---|
| installed | 18918 | `G20351 WR 584 East FLET` | `G32703 WR 718 A-Jack St. Malo` | `BLKO` | `10` |
| installed | 19265 | `G32703 WR 718 A-Jack St.Malo` | `G20351 WR 584 UTA` | `UBEH` | `08` |
| installed | 19382 | `G20351 WR 584 Well No. XT2` | `G20351 WR 584 Manifold MF1` | `BLKO` | `08` |
| installed | 19395 | `G20351 WR 584 Manifold MF1` | `G20351 WR 584 Pump Station` | `BLKO` | `10` |
| installed | 19398 | `G20351 WR 584 Pump Station` | `G20351 WR 584 East FLET` | `BLKO` | `10` |

Representative scanned plan rows:

| `DOC_ID` | Lease | Area/block | Control number | Doc type | Date received |
|---:|---|---|---|---|---|
| 14672 | `G20351` | `WR 584` | `N-9069` | `EP` | `9/25/2007` |
| 19789 | `G20351` | `WR 584` | `N-9699` | `DOCD` | `2/26/2013` |
| 20019 | `G20351` | `WR 584` | `N-9699` | `SEA` | `8/27/2013` |
| 13761 | `G20361` | `WR 627` | `N-8798` | `EP` | `8/16/2006` |
| 19790 | `G25251` | `WR 540` | `N-9699` | `DOCD` | `2/26/2013` |

## Stones

- Field code: `WR508`
- Field leases: `G17001`, `G32690`
- Area/block anchors: `WR 508`, `WR 464`

| Source family | Count | Interpretation |
|---|---:|---|
| Platform structures | 1 | Direct platform/structure records by field code, lease, or area/block. |
| Permanent platforms | 0 | Permanent-platform support table by area/block. |
| Subsea boreholes | 7 | Subsea borehole support table by area/block. |
| FMP lease links | 0 | Lease-to-FMP measurement links. |
| FMP locations | 4 | Measurement locations by lease links or platform complex. |
| MCP lease-unit rows | 3 | Commingling lease-unit rows by lease. |
| MCP area/block rows | 2 | MCP lease/area/block rows by lease. |
| MCP systems | 3 | System records reached through MCP lease-unit rows. |
| Scanned pipeline-map docs | 8 | Pipeline-map document index rows by lease or area/block. |
| Pipeline decom rows | 24 | Installed/proposed pipeline lifecycle rows by lease or area/block. |
| Pipeline segments | 26 | Unique segment IDs from scanned maps and decom rows. |
| Pipeline location rows | 539 | Pipeline-location points for those segment IDs. |
| Scanned ROW docs | 0 | ROW document index rows for those segment IDs. |
| Scanned plan docs | 43 | Plan document index rows by lease. |
| Platform decom rows | 1 | Installed/proposed platform decom rows by area/block or complex. |

Platform record:

| Area | Block | Field code | Structure | Type | Operator | Complex | Lease | Water depth | Latitude | Longitude |
|---|---:|---|---|---|---|---:|---|---:|---:|---:|
| `WR` | 551 | `WR508` | `A (Turritella)` | `FPSO` | Shell Offshore Inc. | 2503 | `G21861` | 9,560 | 26.42774525 | -90.83349094 |

Subsea borehole sample:

| Operator | Area | Block | Well | Water depth |
|---|---|---:|---|---:|
| Shell Offshore Inc. | `WR` | 508 | `SN206` | 9,587 |
| Shell Offshore Inc. | `WR` | 508 | `SN207` | 9,582 |
| Shell Offshore Inc. | `WR` | 508 | `SN114` | 9,558 |
| Shell Offshore Inc. | `WR` | 508 | `SN109` | 9,553 |

FMP location sample:

| `SN_MEAS_LOC` | FMP number | FMP name | Complex | Area/block | Measurement type | Operator |
|---:|---|---|---:|---|---|---|
| 8467 | `5060812FLR2` | FPSO STONES | 2503 | `WR 551` | `FLV` | Shell Offshore Inc. |
| 8468 | `20608128271` | FPSO STONES | 2503 | `WR 551` | `ACT` | Shell Offshore Inc. |
| 8469 | `01608128271` | FPSO STONES | 2503 | `WR 551` | `INV` | Shell Offshore Inc. |
| 8470 | `3060812H000` | FPSO STONES | 2503 | `WR 551` | `GAS` | Shell Offshore Inc. |

Pipeline decom product-code counts:

`{'BLKO': 21, 'UBEH': 2, 'UMBE': 1}`

Matched pipeline-location coverage:

- Located segments: 26
- Appurtenance types:
  `BLOCK LINE`, `LEGACY`, `PIPELINE SLED`, `RISER`, `SUBSEA MANIFOLD`,
  `WELL`
- Latitude range: `26.427421` to `26.454707`
- Longitude range: `-90.812607` to `-90.770327`

Representative pipeline decom rows:

| Status | Segment | Origin | Destination | Product code | Size code |
|---|---:|---|---|---|---|
| installed | 18973 | `G17001 WR 508 PLET 85201` | `G21861 WR 551 Stones FPSO` | `BLKO` | `08` |
| installed | 18974 | `G17001 WR 508 PLET 85202` | `G21861 WR 551 Stones FPSO` | `BLKO` | `08` |
| installed | 19290 | `G17001 WR 508 Well #6` | `G17001 WR 508 Manifold 85501` | `BLKO` | `07` |
| installed | 19292 | `G21861 WR 551 Stones FPSO TUBE U1` | `G17001 WR 508 UTA 85701` | `UBEH` | `11` |
| installed | 19526 | `G17001 WR 508 #3 PLET - 1` | `G17001 WR 508 MFD-85501` | `BLKO` | `08` |

Platform decom sample:

| Status | Complex | Structure number | Area | Block | Structure | Effective date |
|---|---:|---:|---|---:|---|---|
| installed | 2503 | 1 | `WR` | 551 | `A (Turritella)` | `4/30/2021 8:49:04 AM` |

## Saint Malo

- Field code: `WR678`
- Field leases: `G18745`, `G18753`, `G21245`
- Area/block anchors: `WR 634`, `WR 677`, `WR 678`

| Source family | Count | Interpretation |
|---|---:|---|
| Platform structures | 0 | Direct platform/structure records by field code, lease, or area/block. |
| Permanent platforms | 0 | Permanent-platform support table by area/block. |
| Subsea boreholes | 14 | Subsea borehole support table by area/block. |
| FMP lease links | 0 | Lease-to-FMP measurement links. |
| FMP locations | 0 | Measurement locations by lease links or platform complex. |
| MCP lease-unit rows | 0 | Commingling lease-unit rows by lease. |
| MCP area/block rows | 3 | MCP lease/area/block rows by lease. |
| MCP systems | 0 | System records reached through MCP lease-unit rows. |
| Scanned pipeline-map docs | 35 | Pipeline-map document index rows by lease or area/block. |
| Pipeline decom rows | 49 | Installed/proposed pipeline lifecycle rows by lease or area/block. |
| Pipeline segments | 50 | Unique segment IDs from scanned maps and decom rows. |
| Pipeline location rows | 4,661 | Pipeline-location points for those segment IDs. |
| Scanned ROW docs | 17 | ROW document index rows for those segment IDs. |
| Scanned plan docs | 43 | Plan document index rows by lease. |
| Platform decom rows | 0 | Installed/proposed platform decom rows by area/block or complex. |

Subsea borehole sample:

| Operator | Area | Block | Well | Water depth |
|---|---|---:|---|---:|
| Union Oil Company of California | `WR` | 677 | `PS006` | 7,032 |
| Union Oil Company of California | `WR` | 677 | `PS005` | 7,034 |
| Union Oil Company of California | `WR` | 677 | `PS002` | 7,039 |
| Union Oil Company of California | `WR` | 677 | `PS008` | 7,037 |
| Union Oil Company of California | `WR` | 634 | `PN007` | 6,800 |

Pipeline decom product-code counts:

`{'BLKO': 37, 'H2O': 6, 'UBEH': 3, 'UMBH': 2, 'UMB': 1}`

Matched pipeline-location coverage:

- Located segments: 48
- Appurtenance types:
  `BLOCK LINE`, `CROSSING`, `LEGACY`, `PIPELINE SLED`, `RISER`, `TIE-IN`,
  `WELL`
- Latitude range: `26.208527` to `27.058500`
- Longitude range: `-91.519642` to `-91.071801`

Representative pipeline decom rows:

| Status | Segment | Origin | Destination | Product code | Size code |
|---|---:|---|---|---|---|
| installed | 18385 | `G18753 WR 677 PLET-SMS32-00` | `G32703 WR 718 A-Jack St. Malo` | `BLKO` | `10` |
| installed | 18387 | `G18753 WR 677 Well# PS001` | `G18753 WR 677 MFLD-SMS02-00` | `BLKO` | `07` |
| installed | 18391 | `G18753 WR 677 PLET-SMS37-00` | `G18753 WR 677 MFLD-SMS02-00` | `BLKO` | `10` |
| installed | 18396 | `G18753 WR 677 PS008` | `G18753 WR 677 PLEM (MFLD-SMS01-00)` | `BLKO` | `07` |

Representative scanned plan rows:

| `DOC_ID` | Lease | Area/block | Control number | Doc type | Date received |
|---:|---|---|---|---|---|
| 17684 | `G18745` | `WR 634` | `R-5109` | `EP` | `5/27/2011` |
| 17808 | `G18745` | `WR 634` | `R-5109` | `EP` | `6/24/2011` |
| 17850 | `G18745` | `WR 634` | `R-5109` | `SEA` | `6/24/2011` |
| 18293 | `G18745` | `WR 634` | `N-9584` | `DOCD` | `11/1/2011` |
| 37802 | `G18745` | `WR 634` | `S-7962` | `EP` | `6/18/2019` |

## Recommended Query Pattern

For a field-level structure inventory:

1. Start with `deepqual/mv_deep_water_field_leases.bin`.
2. Collect `FIELD_NAME_CODE`, `LEASE_NUMBER`, and `(AREA_CODE,
   BLOCK_NUMBER)`.
3. Query direct structure tables:
   `platstruc/mv_platstruc_structures.bin`,
   `permstruc/mv_perm_platforms.bin`, and
   `permstruc/mv_subsea_boreholes.bin`.
4. Query production infrastructure:
   `fmp/mv_fmplist_all.bin`, `fmp/mv_fmp_meas_locations_all.bin`,
   `mcpflow/mv_mcpflowleaseunits.bin`,
   `mcpflow/mv_mcpflowareablock.bin`, and
   `mcpflow/mv_mcpflowsystems.bin`.
5. Query pipeline-map and decom rows by lease or area/block:
   `scanneddocs/scan_pipeline_maps.bin`,
   `decomcost/mv_decom_cost_inst_pipe.bin`, and
   `decomcost/mv_decom_cost_prop_pipe.bin`.
6. Collect all segment IDs and then query
   `pipeloc/mv_pipelinelocation.bin` for route/location/appurtenance
   records.
7. Query documents:
   `scanneddocs/scan_row.bin` by segment and
   `scanneddocs/scan_plans.bin` by lease.

This pattern finds more field infrastructure than `platstruc` alone,
especially for subsea tiebacks where no platform row exists at the field
lease/block.
