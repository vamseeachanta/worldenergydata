# Kansas KGS knowledge-pack issue drafts

These eight drafts resolve the open-item references in [the knowledge pack](agent-pack.md), revision 1, pinned to code revision `72716499230d3457ce90a5bcd23a8a8367bc0bd3`. They describe follow-up work; no issue has been filed by this documentation change. Responsible roles are proposed for assignment by the maintainers.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-16 | Publish draft scopes, responsible roles and acceptance criteria so the pack's open items can be inspected |

## Draft 1: Validate external numeric values and direct-call identities

Responsible role: Data-pipeline maintainer (proposed).

Scope: Input validation gaps; malformed identities, locale-specific numeric separators, nonfinite pressure/depth values, required caller schemas, fractional years and contradictory KIDs. Include S73: missing KIDs must not match through their string representation when several API10 candidates exist.

Section-6 sites: S04, S05, S07, S13, S14, S15, S17, S18, S22, S23, S30, S31, S32, S36, S38, S46, S50, S73.

Acceptance: Add regression checks for each listed gap. With two API10 candidates, one missing well KID and a missing pressure KID, require ambiguous identity flags and missing depth/gradient. Retain the populated-KID fallback check C08 and exercise both parsed-file and direct-call inputs.

## Draft 2: Detect incomplete ingestion and preserve fallback origins

Responsible role: Data-pipeline maintainer (proposed).

Scope: Empty/completeness gaps; empty tables and lookups, dropped counters or flags, skipped coverage keys, same-year ties, optional field/county origins and zero-byte output snapshots.

Section-6 sites: S03, S20, S21, S27, S28, S35, S37, S40, S42, S48, S49, S51, S63, S64, S65, S70.

Acceptance: Add checks distinguishing a valid zero-observation result from incomplete input; expose missing counters and fallback origins, specify tie behaviour, and require a completeness disposition for empty outputs. Retain the documented empty-schema and ambiguity behaviours in C07, C09 and C10.

## Draft 3: Validate raw content and require explicit provenance status

Responsible role: Data-pipeline maintainer (proposed).

Scope: Provenance gaps; swallowed HEAD/revision failures, optional-source exclusion, empty catalogs, unchecked cached/downloaded content, missing headers, absent source/revision metadata and naive timestamps.

Section-6 sites: S01, S02, S34, S55, S57, S58, S59, S60, S61, S62, S69, S71.

Acceptance: Add checks for metadata-request failure, empty/tampered cached data, zero-byte downloads, absent provenance and naive timestamps. Record explicit failure or incomplete status, validate content before reuse or replacement, and preserve digest and timestamp evidence for accepted inputs.

## Draft 4: Make output promotion and cleanup failures observable

Responsible role: Data-pipeline maintainer (proposed).

Scope: Promotion gaps; second-resolution staging collisions, ignored cleanup failures and mixed output generations after a late promotion failure.

Section-6 sites: S66, S68, S72.

Acceptance: Add concurrent staging and injected-failure checks at each promotion boundary. Demonstrate that an accepted packet contains one complete generation, with either the preceding packet retained or the replacement complete; report cleanup failures without losing the original error.

## Draft 5: Qualify pressure, depth, ancillary units and source readiness

Responsible role: Calculations reviewer (proposed).

Scope: U1 pressure/depth datum and atmospheric basis; U2 rate, deliverability and water-production units; U3 coordinate datum, origin and sign conventions; U4 live-source coverage, freshness, rights and readiness. Include the section-6 unit and regional-subset assumptions.

Section-6 sites: S08, S09, S10, S11, S12, S19, S29, S33, S44.

Acceptance: Retain a versioned public unit/datum dictionary and an independent benchmark for any validated example. Record source content digests, coverage/freshness observations and rights/readiness evidence. Keep each unresolved claim UNVERIFIED and label unsupported inputs as assumed, based on previous experience; fixture arithmetic alone does not close U1–U4.

## Draft 6: Map method families and reconcile parallel ingestion routes

Responsible role: Implementation-map maintainer (proposed).

Scope: Section 9 map follow-up and parallel paths: CSV normalization, ZIP well normalization, API/KID resolution, gauge-to-absolute conversion, pressure/depth screening, earliest selection, coverage aggregation and output provenance. Include the separate legacy parser/pipeline and the downstream schema boundary.

Section-6 sites: none.

Acceptance: Add the method families and implementation rows to the implementation map before counting them in a later audit. Classify delegates separately from calculations; document an adapter or another explicit disposition for legacy/package schemas and test any claimed equivalence with common fixtures.

## Draft 7: Define distribution inclusion for knowledge-pack documents

Responsible role: Packaging maintainer (proposed).

Scope: Distribution inclusion: the existing nested Markdown package-data glob matches the pack and this draft list; wheel exclusion has not been established.

Section-6 sites: none.

Acceptance: Inspect an actual built wheel, decide and document whether these documents belong in the distribution, and add an artifact-content check for the chosen policy. If exclusion is required, verify the build configuration excludes both documents while retaining them in the repository.

## Draft 8: Complete documentation codenaming and independent clearance

Responsible role: Documentation maintainer (proposed).

Scope: Documentation codenaming in 7 discovered files and fixture contents; review and reading boundary, remaining wider-document reading, family/deputy appointments, shared-log registration and conversion of all eight drafts to filed issues. Include section 7 lessons and section 8 ownership.

Section-6 sites: none.

Acceptance: Replace identifying terminology with codenames without copying it into issues. Complete the remaining relevant reading, assign family and deputy responsibilities, register the lessons, file the eight drafts and replace their markers with issue numbers. Obtain independent clearance before changing DRAFT status.
