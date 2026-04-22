## Summary
Create a foundation-only v1 disclosure data layer for annual project/operator cost disclosures.

This v1 is limited to:
- a typed disclosure schema for annual as-reported monetary records
- an explicit `scope` field that distinguishes `operator` rows from `project` rows
- a small hand-curated seed dataset that proves both row types and time-series behavior
- minimum row-level provenance and citation rules
- an explicit linkage strategy to the existing sanction-point dataset, without downstream integrations yet

This issue does not include derived analytics, currency normalization, automated ingestion, or module-level consumption in `fdas` / field-economics workflows.

## Why
`src/worldenergydata/cost/data_collection/public_dataset.py` already captures public cost evidence, but it is shaped around one-off sanction-era project datapoints.

That works for calibration inputs, but not for annual disclosure tracking. We need a reliable base model for recurring annual disclosures before adding broader coverage or analytics.

Adversarial review on the original scope found the issue too broad for approval as written. In particular, v1 needs to narrow to the data foundation:
- typed records instead of one loose generic value field
- explicit separation of operator-level vs project-level rows
- stronger provenance requirements
- a clear linkage/defer boundary for follow-on work

## Existing evidence
- `src/worldenergydata/cost/data_collection/public_dataset.py`
  - already uses operator reports, SEC filings, press releases, regulator documents, and public studies as source evidence
  - is currently organized around sanction-style project cost points, not annual disclosure series
- `src/worldenergydata/cost/data_collection/calibration_schema.py`
  - current `CostDataPoint` is sanction-oriented and does not model annual disclosure provenance such as filing type, source URL, page reference, quoted text, or row scope
- Review findings for planning on `#334`
  - the proposed schema needed explicit typing rather than a single loose `metric_value`
  - operator-level and project-level rows needed structural separation
  - v1 should cap the seed dataset to a minimal curated sample
  - linkage to the existing dataset should be defined, while downstream integrations and analytics should be deferred

## Proposed deliverable
Deliver a new disclosure-layer v1 with the following bounded scope:

1. Typed disclosure schema
   - Add a schema for annual as-reported monetary disclosure records with required provenance fields
   - Include an explicit `scope` field with values such as `operator` and `project`
   - Preserve the as-reported metric label
   - Use typed monetary fields rather than one generic untyped `metric_value`
   - Preserve as-reported currency and unit context

2. Minimum required fields
   - `operator`
   - `fiscal_year`
   - `scope`
   - `filing_type`
   - `source_url`
   - `source_title`
   - `page_reference`
   - `quoted_text`
   - `metric_name_normalized`
   - `metric_name_reported`
   - typed monetary value field(s)
   - `currency`
   - `unit` / magnitude scale
   - optional linkage fields such as `project_name`
   - `confidence`

3. Minimal seed dataset
   - Add a small hand-curated seed dataset only
   - Include enough records to prove:
     - at least one multi-year project disclosure series
     - at least one operator-level annual series
     - both `operator` and `project` scope rows
   - Do not target broad operator coverage in v1

4. Provenance rules
   - Every seed record must meet a minimum provenance standard
   - Prefer primary operator/regulator sources over secondary sources
   - Record citation details at the row level, not only dataset-wide notes
   - If a record is as-reported and not normalized, keep it as-reported rather than silently transforming it

5. Explicit linkage strategy
   - Document how project-scope disclosure records may link to existing `CostDataPoint` records
   - V1 may use exact `(operator, project_name)` matching only
   - This issue defines the linkage contract only; it does not require broad backfill or downstream consumer integration

## Acceptance criteria
- A new disclosure schema exists for annual as-reported monetary records with explicit scope typing
- The schema includes an explicit `scope` field that distinguishes `operator` vs `project` rows
- A minimal curated seed dataset exists and validates against the schema
- The seed dataset includes at least one true multi-year project series
- The seed dataset includes at least one operator-level annual series
- Every seed record meets the minimum provenance standard with source identification and row-level citation support
- As-reported currency/unit values are preserved in the seed dataset
- The disclosure layer is clearly separated from the existing sanction-point calibration dataset
- The issue/output documents an explicit linkage strategy to `CostDataPoint`, while leaving downstream integrations deferred

## Out of scope / Follow-ups
Out of scope for this issue:
- currency normalization
- inflation adjustment or cross-currency comparability rules
- automated ingestion, scraping, or SEC/XBRL pipelines
- derived year-over-year views and re-baselining logic
- normalized downstream analytics such as unit-cost metrics
- broad multi-operator historical backfill
- direct integration into `cost`, `fdas`, `lower_tertiary`, or other economics consumers

Planned follow-up issues:
- #335 — linkage model hardening between annual disclosure rows and `CostDataPoint`
- #336 — currency normalization and comparability policy
- #337 — citation standards and automated ingestion
- #338 — downstream analytics views and consumer integration

## Related
- `src/worldenergydata/cost/data_collection/public_dataset.py`
- `src/worldenergydata/cost/data_collection/calibration_schema.py`
- `feat(cost): annual operator disclosures dataset for year-over-year project cost tracking (#334)`
- `WRK-261: BSEE field economics case study — rebuild on calibrated cost data (#143)`
