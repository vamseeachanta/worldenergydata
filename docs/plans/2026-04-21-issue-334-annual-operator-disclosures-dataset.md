# Plan for #334: annual operator disclosures dataset for year-over-year project cost tracking

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-21
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/334
> **Review artifacts:** scripts/review/results/2026-04-21-plan-334-codex.md | scripts/review/results/2026-04-21-plan-334-gemini.md

---

## Resource Intelligence Summary

### Existing repo code
- Found: `src/worldenergydata/cost/data_collection/public_dataset.py` — current cost dataset is a curated list of sanctioned-project cost points sourced from annual reports, SEC filings, press releases, NPD/NSTA filings, and BOEM studies; records are keyed to one project cost datapoint at sanction/FID time.
- Found: `src/worldenergydata/cost/data_collection/calibration_schema.py` — `CostDataPoint` models one project cost datapoint with sanction/drilling year, source string, and confidence, but no recurring annual disclosure structure.
- Found: `src/worldenergydata/cost/calibration/cost_predictor.py` — current model consumes `CostDataPoint` records and extracts features from sanction-oriented fields (`water_depth_m`, `well_depth_m`, `year_sanction`, `hpht`, `subsea`, `region`, `rig_type`, `water_depth_band`).
- Found: `src/worldenergydata/cost/data_collection/__init__.py` — current public exports for the data-collection layer are limited to `CostDataPoint` and `load_public_dataset()`.
- Found: `tests/unit/cost/test_cost_predictor.py` and `tests/unit/cost/test_proxy_comparison.py` — existing cost tests assume the sanction-point dataset and predictor workflow.
- Found: `src/worldenergydata/fdas/__init__.py` and `src/worldenergydata/lower_tertiary/npv.py` — downstream economics surfaces already exist, but no actual disclosure-layer consumer exists yet; integration claims must therefore be documented as future-facing, not implemented in this issue.
- Gap: no annual disclosure schema, no annual operator/project time-series dataset, no explicit linkage model from recurring disclosures to `CostDataPoint`, and no dedicated tests for disclosure-style cost tracking.

### Standards
- Not applicable — this is a repository data-modeling and provenance issue rather than an engineering standards-transfer issue.

### LLM Wiki pages consulted
- No relevant wiki pages in this repo were found for cost disclosure schema design; the implementation surface is localized to the `worldenergydata.cost` package.

### Documents consulted
- Issue `#334` — defines the requested outcome: annual-statement-driven year-over-year operator/project cost tracking.
- Issue `#143` (`WRK-261: BSEE field economics case study — rebuild on calibrated cost data`) — confirms there is already downstream demand for richer cost/calibration inputs.
- `README.md` — confirms WorldEnergyData positions economics/reporting as core capabilities and already exposes BSEE/FDAS economic workflows.
- Prior review artifacts `scripts/review/results/2026-04-21-plan-334-codex.md` and `...-gemini.md` — identify the main blockers: overly generic value typing, weak provenance/testing, unclear operator-vs-project row separation, missing linkage/defer strategy, and over-broad v1 scope.

### Gaps identified
- No schema exists for annual disclosure records with explicit `scope`, typed monetary values, source URL/title, page references, quoted text, and as-reported metric labeling.
- No curated seed dataset exists for project cost revisions across multiple years for the same project.
- No curated operator-level annual capex series exists adjacent to the current sanctioned project dataset.
- No tests currently prove a project can be represented as a true time series while preserving operator/project row separation, as-reported currency, and provenance quality.
- No explicit linkage strategy is documented for connecting disclosure rows to existing `CostDataPoint` records.

### Evidence (embedded verification)

**Issue statuses** (verified 2026-04-21T19:37:19-05:00 via `gh issue view`):
- `#334` — OPEN — `feat(cost): annual operator disclosures dataset for year-over-year project cost tracking`
- `#143` — OPEN — `WRK-261: BSEE field economics case study — rebuild on calibrated cost data (WRK-019 + WRK-171)`

**File existence** (verified during planning):
- EXISTS: `src/worldenergydata/cost/data_collection/public_dataset.py`
- EXISTS: `src/worldenergydata/cost/data_collection/calibration_schema.py`
- EXISTS: `src/worldenergydata/cost/calibration/cost_predictor.py`
- EXISTS: `src/worldenergydata/fdas/__init__.py`
- EXISTS: `src/worldenergydata/lower_tertiary/npv.py`
- EXISTS: `tests/unit/cost/test_cost_predictor.py`
- MISSING (new — this plan creates): `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py`
- MISSING (new — this plan creates): `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py`
- MISSING (new — this plan creates): `tests/unit/cost/test_operator_disclosures.py`

**Line excerpts**
```text
public_dataset.py:1-23
ABOUTME: Curated public dataset of sanctioned project cost data points.
ABOUTME: All entries sourced from publicly disclosed operator reports and announcements.
Every entry cites a specific public source (operator annual report, SEC filing,
press release, NPD/NSTA filing, or BOEM study).
...
- Company 10-K / 20-F filings (SEC EDGAR, publicly accessible)
```

```text
public_dataset.py:42-67
# Each entry is a dict ready to unpack into CostDataPoint(**entry).
# Costs are as-reported USD MM at time of FID announcement.
...
"year_sanction": 2017,
...
"source": (
    "BP FID press release Jan 2017; BP Annual Report 2017 p.38 — "
    "'Mad Dog Phase 2 sanctioned at ~$9B revised down from ~$20B'"
),
```

```text
calibration_schema.py:85-153
class CostDataPoint(BaseModel):
    project_name: str
    region: str
    water_depth_m: float
    water_depth_band: WaterDepthBand
    well_depth_m: Optional[float]
    well_depth_band: Optional[WellDepthBand]
    operator: str
    year_sanction: int
    year_drilling: Optional[int]
    rig_type: RigType
    activity_type: ActivityType
    hpht: bool
    subsea: SubseaType
    cost_usd_mm: float
    cost_type: CostType
    source: str
    confidence: Confidence
```

```text
cost_predictor.py:96-126
_extract_features(records: list[CostDataPoint])
    rows.append({
        "water_depth_m": rec.water_depth_m,
        "well_depth_m": ...,
        "year_sanction": float(rec.year_sanction),
        "hpht": 1.0 if rec.hpht else 0.0,
        "subsea": rec.subsea.value,
        "region": rec.region,
        "rig_type": rec.rig_type.value,
        "water_depth_band": rec.water_depth_band.value,
    })
```

**Gap proofs**
- `test -f tests/unit/cost/test_operator_disclosures.py || echo missing` → `missing`
- `test -f src/worldenergydata/cost/data_collection/operator_disclosures_schema.py || echo missing` → `missing`
- `test -f src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py || echo missing` → `missing`

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md` |
| Tests | `tests/unit/cost/test_operator_disclosures.py` |
| Implementation | `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py` |
| Implementation | `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py` |
| Implementation | `src/worldenergydata/cost/data_collection/__init__.py` |
| Plan review — Codex | `scripts/review/results/2026-04-21-plan-334-codex.md` |
| Plan review — Gemini | `scripts/review/results/2026-04-21-plan-334-gemini.md` |

---

## Deliverable

A foundation-only v1 disclosure data layer in `worldenergydata.cost.data_collection` that models annual as-reported monetary disclosures with explicit operator-vs-project scope, strong row-level provenance, a tiny curated seed dataset, and a documented linkage strategy to `CostDataPoint` without changing downstream economics consumers yet.

---

## Scope Boundaries

### In scope now
- A typed disclosure schema for annual as-reported monetary records
- An explicit `scope`/`scope_type` field distinguishing `operator` rows from `project` rows
- Preservation of `as_reported_metric_name` alongside a normalized metric identifier
- Typed monetary value fields (`amount`, `currency`, `magnitude_scale`, `unit`) rather than one generic `metric_value`
- A tiny hand-curated seed dataset proving:
  - at least one multi-year project series
  - at least one multi-year operator annual capex series
  - both operator-level and project-level rows
  - no restated prior-year records in v1 seed scope
- Strong per-record provenance: `source_title`, `source_url`, `page_reference`, `quoted_text`, `confidence`
- A documented derived-only v1 linkage strategy for project-scope rows to existing `CostDataPoint` records via exact `(operator, project_name)` matching
- Public loader/schema exports from `worldenergydata.cost.data_collection`

### Explicitly out of scope for this issue
- Any changes to `cost_predictor.py`
- Any integration into `fdas`, `lower_tertiary`, or field-economics consumers
- Currency normalization, inflation adjustment, rebasing, or cross-currency comparability logic
- Derived analytics/views such as re-baselining, unit-cost metrics, or benchmarking dashboards
- Helper query APIs like `get_project_timeseries()` or `get_operator_annual_metrics()`
- Automated ingestion, XBRL/SEC pipelines, or scraper workflows
- Broad operator coverage; v1 remains a minimal proof dataset only

---

## Linkage Strategy

- V1 uses a derived-only linkage rule; the disclosure schema does not store a nullable `CostDataPoint` reference field.
- The only supported join surface in v1 is exact `(operator, project_name)` matching against the existing `load_public_dataset()` corpus for project-scope rows.
- Operator-scope rows are never linkable to `CostDataPoint` records and must not expose linkage fields.
- V1 does not attempt fuzzy matching, alias reconciliation, or backfilling all historical projects.
- Project rows that do not match exactly remain valid disclosure records but are treated as unlinked.
- Restatements are explicitly out of v1 seed/schema scope: the seed dataset must not include restated prior-year records, and no restatement/versioning fields are introduced in this issue.
- Downstream consumer integration is deferred; this issue only defines and tests the derived linkage contract.

---

## Downstream Integration Surface

- After this issue, downstream consumers in `cost`, `fdas`, and field-economics modules can rely on a stable disclosure schema/loader existing in `worldenergydata.cost.data_collection`.
- The only supported relationship to the current sanction-point model is the exact `(operator, project_name)` linkage contract for project-scope rows.
- No downstream consumer code changes are part of this issue.
- Follow-up issues will separately cover linkage expansion, normalization/comparability, ingestion hardening, and consumer analytics/integration.

---

## Pseudocode

```text
class ScopeType(Enum):
    define OPERATOR and PROJECT

class FilingType(Enum):
    define annual_report, ten_k, twenty_f, investor_presentation, regulator_pdo, regulator_fdp, press_release

class NormalizedMetricName(Enum):
    define operator_upstream_capex_reported, project_total_capex_reported, project_remaining_capex_reported

class OperatorDisclosureRecord(BaseModel):
    validate operator, fiscal_year, scope_type, filing_type
    validate as_reported_metric_name and normalized_metric_name
    validate typed monetary fields: amount, currency, magnitude_scale, unit
    validate provenance fields: source_title, source_url, page_reference, quoted_text, confidence
    if scope_type == PROJECT require project_name
    if scope_type == OPERATOR forbid project_name linkage claims

function load_operator_disclosures_dataset():
    instantiate validated OperatorDisclosureRecord items from a tiny curated raw list
    return records

function linkable_to_cost_datapoint(record, sanctioned_records):
    if record.scope_type != PROJECT return false
    if exact (record.operator, record.project_name) match exists in sanctioned_records return true
    return false

update data_collection exports:
    expose ScopeType, FilingType, NormalizedMetricName, OperatorDisclosureRecord, load_operator_disclosures_dataset
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py` | schema for annual as-reported monetary disclosure records |
| Create | `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py` | tiny curated disclosure-oriented seed dataset + loader |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export new disclosure schema/loader alongside current sanction-point dataset |
| Create | `tests/unit/cost/test_operator_disclosures.py` | TDD coverage for schema, loader, provenance, scope separation, linkage rules, and time-series behavior |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_disclosure_record_requires_money_fields_and_provenance` | schema rejects records missing typed monetary or provenance fields | record missing `amount`, `currency`, `source_url`, or `page_reference` | validation error |
| `test_scope_type_enforces_project_name_rules` | operator rows and project rows are structurally separated | `scope_type=project` without `project_name`; `scope_type=operator` with linkage-only project fields | validation error / rejection |
| `test_as_reported_metric_name_is_preserved` | reported disclosure labels are retained beside normalized metric identifiers | seed dataset record | exact reported label preserved |
| `test_currency_and_magnitude_scale_are_required_for_money_metrics` | monetary disclosures must preserve as-reported value context | seed dataset record | required typed fields present |
| `test_loader_returns_validated_records_from_capped_seed_dataset` | loader returns a tiny validated seed corpus only | seed dataset | non-empty list with <= 12 records |
| `test_project_scope_rows_link_to_existing_cost_datapoint_by_exact_operator_project_match` | v1 linkage strategy is deterministic and derived-only | project-scope rows + `load_public_dataset()` | exact matches only |
| `test_operator_scope_rows_cannot_link_to_cost_datapoint` | operator rows are structurally excluded from sanction-record linkage | operator-scope rows | linkage result is always false |
| `test_unmatched_project_rows_remain_valid_but_unlinked` | unmatched project disclosures remain valid records without false linkage | non-matching project row | valid record + false linkage result |
| `test_every_seed_record_has_source_url_page_reference_and_quote` | provenance minimum is enforced row by row | all seed records | all required provenance fields populated |
| `test_seed_dataset_contains_one_multi_year_project_series` | at least one project has >1 fiscal year record | filtered project rows | two or more years represented |
| `test_seed_dataset_contains_one_multi_year_operator_capex_series` | at least one operator annual capex series exists | filtered operator rows | two or more years represented |
| `test_gap_years_are_not_imputed_by_loader` | loader does not silently fill missing years | sparse time-series example | only explicit records returned |
| `test_seed_dataset_excludes_restated_prior_year_records` | v1 explicitly defers restatements out of schema/seed scope | seed dataset | no restated prior-year rows present |
| `test_public_exports_exist_in_cost_data_collection_only` | v1 remains a data_collection-level API, not a package-root expansion | import check | disclosure names resolve from `worldenergydata.cost.data_collection` |

---

## Acceptance Criteria

- [ ] `tests/unit/cost/test_operator_disclosures.py` passes under the repo test command
- [ ] New schema exists for annual as-reported monetary disclosure records with explicit operator-vs-project scope typing
- [ ] Generic untyped `metric_value` is not used in v1; the schema uses typed monetary fields and preserves `as_reported_metric_name`
- [ ] Curated seed dataset exists, loads successfully, and contains <= 12 records
- [ ] Seed dataset includes at least one project-scope multi-year series whose linkage is evaluated via the derived-only exact `(operator, project_name)` rule against an existing `CostDataPoint`
- [ ] Seed dataset includes at least one operator-scope multi-year annual capex series
- [ ] Every seed record includes minimum provenance: `source_title`, `source_url`, `page_reference`, `quoted_text`, and `confidence`
- [ ] Disclosure layer is exported from `worldenergydata.cost.data_collection` without changing the package-root `worldenergydata.cost` API
- [ ] Plan clearly documents the derived-only linkage strategy and explicitly defers restatements, downstream consumer integration, comparability normalization, and automated ingestion to follow-up issues

---

## Follow-up Issues

- Child issue #335: linkage model hardening between annual disclosure records and `CostDataPoint` sanction records
- Child issue #336: currency normalization and comparability policy for annual disclosures
- Child issue #337: citation standards and automated ingestion for annual operator disclosures
- Child issue #338: downstream analytics views and integration surface for `cost`, `fdas`, and `lower_tertiary`

---

## Adversarial Review Summary

| Provider | Verdict | Key findings |
|---|---|---|
| Codex | MINOR | Approval is close, but v1 must choose one linkage representation (stored vs derived-only) and one restatement contract (explicit representation vs explicit deferral) |
| Gemini | APPROVE | Revised foundation-only scope is now safely bounded; remaining notes are strengthening suggestions around gross/net basis, report date, and validation tests |

**Overall result:** near-pass; one final tightening pass recommended before moving to approval stage

Revisions made based on review:
- reran review against the narrowed local artifact instead of the stale earlier draft
- confirmed package-root export expansion, helper-query APIs, and non-monetary metrics are out of scope for v1
- confirmed child issues #335–#338 successfully hold deferred linkage hardening, normalization, ingestion, and analytics/integration work
- remaining blocker is now limited to restatement treatment in v1; linkage representation is fixed as a derived-only exact-match rule

---

## Risks and Open Questions

- **Risk:** even a tiny hand-curated seed dataset can sprawl if source selection is not capped aggressively.
- **Risk:** operator disclosures vary in wording; preserving both normalized and as-reported metric names is necessary but may still require future mapping rules.
- **Risk:** selected seed records may still surface naming variation that breaks exact-match linkage and must therefore be curated conservatively.
- **Decision:** v1 uses a derived-only exact-match linkage rule; no stored linkage field is added to the disclosure schema.
- **Decision:** restatements are explicitly deferred out of v1 seed/schema scope; no restatement/versioning fields are introduced in this issue, and the seed dataset must exclude restated prior-year records.
- **Open:** should a future restatement model live with ingestion/provenance hardening (#337) or as a separate narrow follow-up?

---

## Complexity: T2

**T2** — this is a bounded multi-file data-model addition with new tests and a tiny curated dataset, but it avoids immediate cross-module integration, automation, and analytics work.
